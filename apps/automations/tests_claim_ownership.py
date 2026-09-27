"""Deterministic interleavings for a paused worker losing its persisted claim."""

from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.automations.engine import (
    cancel_automation_run,
    process_automation_run,
    recover_stale_automation_runs,
    retry_automation_run,
)
from apps.automations.models import AutomationAction, AutomationRule, AutomationRun
from apps.businesses.models import Business, BusinessMember
from apps.tasks.models import Task


class AutomationClaimOwnershipTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="claim-owner", email="claim@example.com")
        self.business = Business.objects.create(owner=owner, name="Claim clinic", slug="claim-clinic")
        BusinessMember.objects.create(business=self.business, user=owner, role=BusinessMember.Roles.OWNER)
        rule = AutomationRule.objects.create(
            business=self.business, name="Claim rule", trigger_type="lead_created", is_active=True,
        )
        AutomationAction.objects.create(
            rule=rule, action_type=AutomationAction.ActionTypes.CREATE_TASK,
            config={"title": "One recovered task"},
        )
        self.run = AutomationRun.objects.create(
            business=self.business, rule=rule, trigger_type="lead_created",
            idempotency_key="claim-interleaving", run_after=timezone.now(),
        )

    def test_resumed_worker_cannot_replay_action_completed_by_replacement(self):
        interleaved = False

        def replace_worker(*args, **kwargs):
            nonlocal interleaved
            if not interleaved:
                interleaved = True
                AutomationRun.objects.filter(pk=self.run.pk).update(
                    locked_at=timezone.now() - timezone.timedelta(hours=1),
                )
                self.assertEqual(recover_stale_automation_runs(), 1)
                replacement = process_automation_run(self.run.pk)
                self.assertEqual(replacement.status, AutomationRun.Statuses.SUCCESS)
            return True

        with patch("apps.automations.engine._conditions_match", side_effect=replace_worker):
            process_automation_run(self.run.pk)

        self.run.refresh_from_db()
        self.assertEqual(Task.objects.filter(business=self.business, title="One recovered task").count(), 1)
        self.assertEqual(self.run.current_action_index, 1)
        self.assertEqual(self.run.status, AutomationRun.Statuses.SUCCESS)
        self.assertEqual(self.run.attempts, 2)

    def test_cancelled_claim_cannot_execute_or_overwrite_cancellation(self):
        def cancel_worker(*args, **kwargs):
            cancel_automation_run(AutomationRun.objects.get(pk=self.run.pk))
            return True

        with patch("apps.automations.engine._conditions_match", side_effect=cancel_worker):
            process_automation_run(self.run.pk)

        self.run.refresh_from_db()
        self.assertEqual(self.run.status, AutomationRun.Statuses.CANCELLED)
        self.assertFalse(Task.objects.filter(business=self.business, title="One recovered task").exists())
        self.assertEqual(self.run.current_action_index, 0)

    def test_stale_cancel_request_cannot_overwrite_completed_run(self):
        process_automation_run(self.run.pk)
        cancel_automation_run(self.run)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, AutomationRun.Statuses.SUCCESS)

    def test_stale_retry_request_cannot_reopen_completed_run(self):
        process_automation_run(self.run.pk)
        self.run.status = AutomationRun.Statuses.FAILED
        retry_automation_run(self.run)
        self.run.refresh_from_db()
        self.assertEqual(self.run.status, AutomationRun.Statuses.SUCCESS)
        self.assertEqual(self.run.attempts, 1)
