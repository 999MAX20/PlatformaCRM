from django.test import TestCase, override_settings
from unittest.mock import patch
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.automations import tests as fixtures
from apps.automations.engine import _create_follow_up, process_automation_run
from apps.automations.models import AutomationAction, AutomationRule, AutomationRun
from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents
from apps.notifications.models import Notification
from apps.scheduling.models import Appointment
from apps.scheduling.services import create_appointment_follow_up_task
from apps.tasks.models import Task


class FollowUpPolicyTests(TestCase):
    def setUp(self):
        self.f = fixtures.AutomationFoundationTests()
        self.f.setUp()
        self.f.api.force_authenticate(self.f.owner)
        self.appointment = Appointment.objects.create(
            business=self.f.business, client=self.f.client, service=self.f.service,
            start_at=timezone.now(), end_at=timezone.now() + timezone.timedelta(hours=1))

    def rule(self, trigger=AutomationRule.TriggerTypes.APPOINTMENT_COMPLETED, explicit=False):
        actions = [{"action_type": AutomationAction.ActionTypes.CREATE_FOLLOW_UP,
                    "config": {"title": "Rule must not overwrite", "due_in_days": 5}}]
        if explicit:
            actions.append({"action_type": AutomationAction.ActionTypes.CREATE_TASK,
                            "config": {"title": "Explicit separate task"}})
        return self.f._rule(trigger, actions)

    def test_inline_complete_reuses_builtin_and_keeps_explicit_task(self):
        self.rule(explicit=True)
        response = self.f.api.post(f"/api/appointments/{self.appointment.pk}/complete/")
        self.assertEqual(response.status_code, 200, response.data)
        tasks = Task.objects.filter(appointment=self.appointment)
        self.assertEqual(tasks.count(), 2)
        built_in = tasks.exclude(title="Explicit separate task").get()
        self.assertIn("completed appointment", built_in.title)
        run = AutomationRun.objects.get()
        self.assertEqual(run.status, AutomationRun.Statuses.SUCCESS)
        self.assertEqual(run.action_results[0]["task_id"], built_in.pk)

    def test_inline_cancel_has_one_follow_up_with_original_reason(self):
        self.rule(AutomationRule.TriggerTypes.APPOINTMENT_CANCELLED)
        response = self.f.api.post(f"/api/appointments/{self.appointment.pk}/cancel/", {"reason": "Client unavailable"})
        self.assertEqual(response.status_code, 200, response.data)
        task = Task.objects.get(appointment=self.appointment)
        self.assertIn("Client unavailable", task.description)
        self.assertIn("cancelled appointment", task.title)

    @override_settings(AUTOMATIONS_RUN_INLINE=False)
    def test_delayed_rule_preserves_staff_edits_completed_status_and_effects(self):
        self.rule()
        self.assertEqual(self.f.api.post(f"/api/appointments/{self.appointment.pk}/complete/").status_code, 200)
        task = Task.objects.get(appointment=self.appointment)
        Task.objects.filter(pk=task.pk).update(title="Staff edited", status=Task.Statuses.DONE)
        before = (ActivityEvent.objects.filter(event_type=ActivityEvents.TASK_CREATED).count(), Notification.objects.count())
        run = process_automation_run(AutomationRun.objects.get().pk)
        self.assertEqual(run.status, AutomationRun.Statuses.SUCCESS, run.error)
        self.assertEqual(run.action_results[0]["task_id"], task.pk)
        task.refresh_from_db()
        self.assertEqual((task.title, task.status), ("Staff edited", Task.Statuses.DONE))
        for _ in range(2):
            reused = create_appointment_follow_up_task(appointment=self.appointment, actor=self.f.owner)
            self.assertEqual(reused.pk, task.pk)
        self.assertEqual(Task.objects.filter(appointment=self.appointment).count(), 1)
        self.assertEqual(before, (ActivityEvent.objects.filter(event_type=ActivityEvents.TASK_CREATED).count(), Notification.objects.count()))

    def test_follow_up_rejects_foreign_business_before_reuse(self):
        from apps.businesses.models import Business
        other = Business.objects.create(owner=self.f.owner, name="Other", slug="other-follow-up")
        self.appointment.status = Appointment.Statuses.COMPLETED
        self.appointment.save(update_fields=["status"])
        action = self.rule().actions.get()
        with self.assertRaises(ValidationError):
            _create_follow_up(action, business=other, entity=self.appointment, payload={})
        self.assertFalse(Task.objects.filter(appointment=self.appointment).exists())

    def test_nonterminal_follow_up_keeps_rule_configuration(self):
        action = self.rule().actions.get()
        task = _create_follow_up(action, business=self.f.business, entity=self.appointment, payload={})
        self.assertEqual(task.title, "Rule must not overwrite")
        self.assertEqual(task.appointment_id, self.appointment.pk)

    def test_builtin_failure_rolls_back_task_and_retry_creates_one(self):
        self.appointment.status = Appointment.Statuses.NO_SHOW
        self.appointment.save(update_fields=["status"])
        with patch("apps.scheduling.services.create_activity_event", side_effect=RuntimeError("history unavailable")):
            with self.assertRaises(RuntimeError):
                create_appointment_follow_up_task(appointment=self.appointment, actor=self.f.owner)
        self.assertFalse(Task.objects.filter(appointment=self.appointment).exists())
        task = create_appointment_follow_up_task(appointment=self.appointment, actor=self.f.owner)
        Task.objects.filter(pk=task.pk).update(is_archived=True)
        reused = create_appointment_follow_up_task(appointment=self.appointment, actor=self.f.owner)
        self.assertEqual(reused.pk, task.pk)
        self.assertTrue(reused.is_archived)
        self.assertEqual(Task.objects.filter(appointment=self.appointment).count(), 1)
