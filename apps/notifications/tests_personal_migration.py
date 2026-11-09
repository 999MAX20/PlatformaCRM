from importlib import import_module

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from django.utils import timezone


class PersonalNotificationMigrationTests(TransactionTestCase):
    def test_legacy_audience_and_read_state_are_preserved_without_resending(self):
        old_target = [("notifications", "0005_notification_attempts_notification_delivered_at_and_more")]
        new_target = [("notifications", "0007_backfill_personal_recipients")]
        executor = MigrationExecutor(connection)
        executor.migrate(old_target)
        try:
            executor = MigrationExecutor(connection)
            old = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
            User = old.get_model("accounts", "User")
            Business = old.get_model("businesses", "Business")
            Member = old.get_model("businesses", "BusinessMember")
            Notification = old.get_model("notifications", "Notification")
            owner = User.objects.create(username="migration-owner", email="migration-owner@example.com")
            staff = User.objects.create(username="migration-staff", email="migration-staff@example.com")
            inactive = User.objects.create(username="migration-inactive", email="migration-inactive@example.com")
            business = Business.objects.create(name="Migration", slug="notification-migration", owner=owner)
            Member.objects.create(business=business, user=staff, role="specialist")
            Member.objects.create(business=business, user=inactive, role="specialist", is_active=False)
            now = timezone.now()
            shared = Notification.objects.create(business=business, text="Legacy shared", channel="system",
                                                 send_at=now, read_at=now, status="sent", delivered_at=now)
            personal = Notification.objects.create(business=business, recipient=staff, text="Legacy personal",
                                                   channel="system", send_at=now, status="pending")
            outbound = Notification.objects.create(business=business, text="Client delivery", channel="email",
                                                   send_at=now, status="failed", attempts=2)
            original = list(Notification.objects.order_by("pk").values("pk", "read_at", "status", "attempts", "delivered_at", "send_at"))
            executor = MigrationExecutor(connection)
            executor.migrate(new_target)
            executor = MigrationExecutor(connection)
            current = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
            Recipient = current.get_model("notifications", "NotificationRecipient")
            CurrentNotification = current.get_model("notifications", "Notification")
            self.assertEqual(Recipient.objects.count(), 3)
            self.assertSetEqual(set(Recipient.objects.filter(notification_id=shared.pk).values_list("user_id", flat=True)), {owner.pk, staff.pk})
            for state in Recipient.objects.filter(notification_id=shared.pk):
                self.assertEqual(state.read_at, now)
                self.assertEqual(state.received_at, shared.created_at)
                self.assertIsNone(state.opened_at)
                self.assertIsNone(state.acknowledged_at)
            self.assertIsNone(Recipient.objects.get(notification_id=personal.pk, user_id=staff.pk).read_at)
            self.assertFalse(Recipient.objects.filter(notification_id=outbound.pk).exists())
            self.assertEqual(original, list(CurrentNotification.objects.order_by("pk").values("pk", "read_at", "status", "attempts", "delivered_at", "send_at")))
            # Re-running a backfill cannot retroactively subscribe new members.
            current.get_model("businesses", "BusinessMember").objects.filter(user_id=inactive.pk).update(is_active=True)
            with connection.schema_editor() as schema_editor:
                import_module("apps.notifications.migrations.0007_backfill_personal_recipients").backfill(current, schema_editor)
            self.assertEqual(Recipient.objects.count(), 3)
        finally:
            MigrationExecutor(connection).migrate(new_target)
