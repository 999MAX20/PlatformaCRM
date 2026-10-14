"""Queue transport must follow the CRM transaction, not escape its rollback."""
from unittest.mock import patch

from django.db import transaction
from django.test import TestCase, override_settings

from apps.accounts.models import User
from apps.automations.engine import run_automations_for_event
from apps.automations.models import AutomationRule, AutomationRun
from apps.businesses.models import Business


@override_settings(AUTOMATIONS_RUN_INLINE=False)
class AutomationDispatchCommitTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="dispatch-owner", email="dispatch-owner@example.com")
        self.business = Business.objects.create(owner=self.owner, name="Dispatch", slug="dispatch")
        self.rule = AutomationRule.objects.create(business=self.business, name="After commit",
            trigger_type=AutomationRule.TriggerTypes.LEAD_CREATED, is_active=True)

    def emit(self):
        return run_automations_for_event(business=self.business,
            trigger_type=AutomationRule.TriggerTypes.LEAD_CREATED, payload={"lead_id": 1})[0]

    def test_dispatch_waits_until_crm_transaction_commits(self):
        with patch("apps.automations.tasks.process_automation_run_task.apply_async") as dispatch:
            with self.captureOnCommitCallbacks(execute=True):
                with transaction.atomic():
                    run = self.emit()
                    dispatch.assert_not_called()
            dispatch.assert_called_once_with(args=[run.pk], eta=run.run_after)

    def test_rollback_discards_pending_dispatch(self):
        with patch("apps.automations.tasks.process_automation_run_task.apply_async") as dispatch:
            with self.captureOnCommitCallbacks(execute=True):
                with self.assertRaises(RuntimeError):
                    with transaction.atomic():
                        self.emit()
                        raise RuntimeError("CRM command failed")
            dispatch.assert_not_called()
        self.assertFalse(AutomationRun.objects.exists())

    def test_transport_failure_keeps_durable_pending_run_for_recovery(self):
        with patch("apps.automations.tasks.process_automation_run_task.apply_async", side_effect=RuntimeError("queue unavailable")):
            with self.captureOnCommitCallbacks(execute=True):
                run = self.emit()
        run.refresh_from_db()
        self.assertEqual(run.status, AutomationRun.Statuses.PENDING)
        self.assertIsNotNone(run.run_after)
