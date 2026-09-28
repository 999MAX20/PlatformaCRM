from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessCapability, BusinessMember
from apps.notifications.models import Notification, NotificationPreference
from apps.notifications.tasks import process_due_notifications_task
from apps.tasks.models import Task, TaskReminderDelivery
from apps.tasks.reminders import enqueue_due_task_reminders
from apps.tasks.services import create_routed_task_notifications


class ScheduledTaskReminderTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="reminder-owner", email="reminder-owner@example.com", password="pass")
        self.business = Business.objects.create(owner=self.owner, name="Reminder clinic", slug="reminder-clinic")
        BusinessMember.objects.create(business=self.business, user=self.owner, role=BusinessMember.Roles.OWNER)
        self.task = Task.objects.create(
            business=self.business, title="Call client", assignee=self.owner,
            reminder_at=timezone.now() - timedelta(minutes=1),
        )

    def test_notification_tick_delivers_due_task_reminder_once(self):
        process_due_notifications_task.run()
        process_due_notifications_task.run()
        reminders = Notification.objects.filter(
            business=self.business, category=Notification.Categories.TASKS,
            action_url=f"/app/tasks?task={self.task.pk}",
        )
        self.assertEqual(reminders.count(), 1)
        self.assertEqual(reminders.get().recipient_id, self.owner.pk)
        self.assertEqual(reminders.get().status, Notification.Statuses.SENT)

    def test_future_missing_closed_archived_and_snoozed_reminders_are_not_sent(self):
        now = timezone.now()
        for change in [
            {"reminder_at": now + timedelta(hours=1)}, {"reminder_at": None},
            {"status": Task.Statuses.DONE}, {"status": Task.Statuses.CANCELLED},
            {"is_archived": True}, {"snoozed_until": now + timedelta(hours=1)},
        ]:
            with self.subTest(change=change):
                Task.objects.filter(pk=self.task.pk).update(
                    reminder_at=now - timedelta(minutes=1), status=Task.Statuses.OPEN,
                    is_archived=False, snoozed_until=None,
                )
                Task.objects.filter(pk=self.task.pk).update(**change)
                self.assertEqual(enqueue_due_task_reminders(now=now), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_snooze_expiry_and_changed_reminder_rearm_without_replaying_old_tick(self):
        now = timezone.now()
        Task.objects.filter(pk=self.task.pk).update(snoozed_until=now)
        self.assertEqual(enqueue_due_task_reminders(now=now), 1)
        self.assertEqual(enqueue_due_task_reminders(now=now), 0)
        later = now + timedelta(hours=1)
        Task.objects.filter(pk=self.task.pk).update(reminder_at=later)
        self.assertEqual(enqueue_due_task_reminders(now=now), 0)
        self.assertEqual(enqueue_due_task_reminders(now=later), 1)
        self.assertEqual(enqueue_due_task_reminders(now=later), 0)
        self.assertEqual(Notification.objects.count(), 2)

    def test_failed_notification_insert_rolls_back_marker_and_partial_effects(self):
        def fail_after_insert(**kwargs):
            create_routed_task_notifications(**kwargs)
            raise RuntimeError("simulated interruption before commit")

        with patch("apps.tasks.reminders.create_routed_task_notifications", side_effect=fail_after_insert):
            with self.assertRaises(RuntimeError):
                enqueue_due_task_reminders()
        self.task.refresh_from_db()
        self.assertFalse(TaskReminderDelivery.objects.filter(task=self.task).exists())
        self.assertEqual(Notification.objects.count(), 0)
        self.assertEqual(enqueue_due_task_reminders(), 1)

    def test_notification_preferences_consume_normal_reminder_but_urgent_is_routed(self):
        preference = NotificationPreference.objects.create(
            business=self.business, user=self.owner, category=Notification.Categories.TASKS,
            in_app_enabled=False,
        )
        self.assertEqual(enqueue_due_task_reminders(), 0)
        preference.in_app_enabled = True
        preference.save()
        self.assertEqual(enqueue_due_task_reminders(), 0)
        preference.in_app_enabled = False
        preference.save()
        Task.objects.filter(pk=self.task.pk).update(
            reminder_at=timezone.now(), priority=Task.Priorities.URGENT,
        )
        self.assertEqual(enqueue_due_task_reminders(), 1)

    def test_disabled_module_does_not_consume_reminder_or_starve_other_business(self):
        BusinessCapability.objects.update_or_create(
            business=self.business, module_key="tasks", defaults={"is_enabled": False},
        )
        other = User.objects.create_user(username="other-reminder-owner", email="other-reminder@example.com", password="pass")
        business = Business.objects.create(owner=other, name="Other", slug="other-reminder")
        BusinessMember.objects.create(business=business, user=other, role=BusinessMember.Roles.OWNER)
        other_task = Task.objects.create(business=business, assignee=other, title="Other task", reminder_at=timezone.now())
        self.assertEqual(enqueue_due_task_reminders(limit=1), 1)
        notification = Notification.objects.get()
        self.assertEqual((notification.business_id, notification.recipient_id), (business.pk, other.pk))
        self.assertIn(str(other_task.pk), notification.action_url)
        self.task.refresh_from_db()
        self.assertFalse(TaskReminderDelivery.objects.filter(task=self.task).exists())

    def test_inactive_assignee_keeps_assignment_and_notifies_existing_fallback(self):
        staff = User.objects.create_user(username="inactive-reminder-staff", email="inactive-reminder@example.com", password="pass")
        BusinessMember.objects.create(business=self.business, user=staff, role=BusinessMember.Roles.OPERATOR, is_active=False)
        Task.objects.filter(pk=self.task.pk).update(assignee=staff)
        self.assertEqual(enqueue_due_task_reminders(), 1)
        self.assertEqual(Notification.objects.get().recipient_id, self.owner.pk)
        self.task.refresh_from_db()
        self.assertEqual(self.task.assignee_id, staff.pk)

    def test_stale_scan_rechecks_task_before_emitting(self):
        from apps.tasks.reminders import _due_reminders

        calls = 0
        def complete_after_scan(now):
            nonlocal calls
            calls += 1
            if calls == 2:
                Task.objects.filter(pk=self.task.pk).update(status=Task.Statuses.DONE)
            return _due_reminders(now)

        with patch("apps.tasks.reminders._due_reminders", side_effect=complete_after_scan):
            self.assertEqual(enqueue_due_task_reminders(), 0)
        self.assertEqual(Notification.objects.count(), 0)

    def test_concurrent_details_save_cannot_erase_delivery_receipt(self):
        stale_editor = Task.objects.get(pk=self.task.pk)
        self.assertEqual(enqueue_due_task_reminders(), 1)
        stale_editor.description = "Edited while notification tick ran"
        stale_editor.save()
        self.assertEqual(enqueue_due_task_reminders(), 0)
        self.assertEqual(Notification.objects.count(), 1)

    def test_inactive_assignee_fallback_does_not_broadcast_to_unrelated_specialists(self):
        users = {}
        for role, active in [("operator", False), ("manager", True), ("specialist", True)]:
            users[role] = User.objects.create_user(username=role, email=f"{role}@reminder.example", password="pass")
            BusinessMember.objects.create(business=self.business, user=users[role], role=role, is_active=active)
        Task.objects.filter(pk=self.task.pk).update(assignee=users["operator"])
        enqueue_due_task_reminders()
        self.assertEqual(list(Notification.objects.values_list("recipient_id", flat=True)), [users["manager"].pk])
