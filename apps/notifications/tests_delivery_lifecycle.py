from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.activities.models import ActivityEvent
from apps.clients.models import Client
from apps.core.models import AuditLog
from apps.notifications.delivery import (
    claim_notification, deliver_notification, process_due_notifications,
    recover_stale_notifications, retry_notification,
)
from apps.notifications.models import Notification
from apps.notifications.tests_personal_services import PersonalNotificationFixtures


class DeliveryFixtures(PersonalNotificationFixtures):
    def setUp(self):
        super().setUp()
        self.customer = Client.objects.create(business=self.business, full_name="Delivery test", email="delivery@example.test")

    def external(self, **changes):
        values = dict(business=self.business, client=self.customer, channel="email", text="Delivery test",
                      send_at=timezone.now() - timezone.timedelta(hours=1))
        values.update(changes)
        return Notification.objects.create(**values)

    def stale_claim(self, **changes):
        notification = self.external(**changes)
        return claim_notification(notification.pk, now=timezone.now() - timezone.timedelta(minutes=30))

    def failure_events(self, notification):
        return ActivityEvent.objects.filter(event_type="notification_failed", metadata__notification_id=notification.pk)


@override_settings(NOTIFICATION_DELIVERY_STALE_LOCK_SECONDS=900)
class NotificationDeliveryLifecycleTests(DeliveryFixtures, TestCase):
    def test_retry_cannot_reuse_a_stale_failed_snapshot(self):
        failed = self.external(status="failed", attempts=3, failed_at=timezone.now())
        stale = Notification.objects.get(pk=failed.pk)
        with patch("apps.notifications.delivery._deliver", return_value={"ok": True}) as provider:
            self.assertEqual(retry_notification(failed, actor=self.owner)["status"], "sent")
            self.assertIsNone(retry_notification(stale, actor=self.owner))
        provider.assert_called_once()
        self.assertEqual(AuditLog.objects.filter(metadata__kind="notification_manual_retry").count(), 1)

    def test_stale_retry_does_not_claim_a_new_terminal_failure(self):
        failed = self.external(status="failed", max_attempts=1)
        stale = Notification.objects.get(pk=failed.pk)
        with patch("apps.notifications.delivery._deliver", return_value={"ok": False, "retryable": False}) as provider:
            self.assertEqual(retry_notification(failed, actor=self.owner)["status"], "failed")
            self.assertIsNone(retry_notification(stale, actor=self.owner))
            provider.assert_called_once()
            # A fresh explicit command may retry the new failure.
            failed.refresh_from_db()
            self.assertEqual(retry_notification(failed, actor=self.owner)["status"], "failed")
            self.assertEqual(provider.call_count, 2)

    def test_retry_requires_current_manage_and_business_membership(self):
        failed = self.external(status="failed")
        with patch("apps.notifications.delivery._deliver") as provider:
            for actor in (self.staff, self.outsider):
                with self.subTest(actor=actor.pk), self.assertRaises(PermissionDenied):
                    retry_notification(failed, actor=actor)
        provider.assert_not_called()
        failed.refresh_from_db()
        self.assertEqual(failed.status, "failed")

    def test_direct_retry_rejects_internal_notifications(self):
        work = self.work(actor=self.owner, status="failed")
        with self.assertRaises(ValidationError):
            retry_notification(work, actor=self.owner)

    def test_retry_api_preserves_state_when_not_failed(self):
        api = APIClient()
        api.force_authenticate(self.owner)
        for status in ("pending", "sending", "sent", "cancelled", "retry_scheduled"):
            notification = self.external(status=status)
            before = Notification.objects.values().get(pk=notification.pk)
            with self.subTest(status=status), patch("apps.notifications.delivery._deliver") as provider:
                response = api.post(f"/api/notifications/{notification.pk}/retry/?business={self.business.pk}")
                self.assertEqual(response.status_code, 400)
                provider.assert_not_called()
            self.assertEqual(Notification.objects.values().get(pk=notification.pk), before)

    def test_retry_audit_failure_rolls_back_before_provider_call(self):
        failed = self.external(status="failed", attempts=3)
        before = Notification.objects.values().get(pk=failed.pk)
        with patch("apps.notifications.delivery.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")), \
                patch("apps.notifications.delivery._deliver") as provider, self.assertRaises(RuntimeError):
            retry_notification(failed, actor=self.owner)
        provider.assert_not_called()
        self.assertEqual(Notification.objects.values().get(pk=failed.pk), before)

    def test_stale_delivery_fails_once_without_automatic_resend_then_allows_manual_retry(self):
        claimed = self.stale_claim()
        with patch("apps.notifications.delivery._deliver") as provider:
            result = process_due_notifications()
            self.assertEqual(result[0]["status"], "failed")
            self.assertEqual(process_due_notifications(), [])
            provider.assert_not_called()
        claimed.refresh_from_db()
        self.assertIsNone(claimed.locked_at)
        self.assertIsNone(claimed.next_retry_at)
        self.assertEqual(claimed.attempts, 1)
        self.assertIn("unknown", claimed.last_error)
        self.assertEqual(self.failure_events(claimed).count(), 1)
        self.assertEqual(Notification.objects.filter(channel="system").count(), 1)
        with patch("apps.notifications.delivery._deliver", return_value={"ok": True}) as provider:
            self.assertEqual(retry_notification(claimed, actor=self.owner)["status"], "sent")
        provider.assert_called_once()

    def test_recovery_excludes_current_claims_internal_and_terminal_states(self):
        current = claim_notification(self.external().pk)
        for status in ("pending", "sent", "failed", "cancelled", "retry_scheduled"):
            self.external(status=status)
        self.work(actor=self.owner, status="sending", locked_at=timezone.now() - timezone.timedelta(days=1))
        before = list(Notification.objects.order_by("pk").values())
        self.assertEqual(recover_stale_notifications(), [])
        self.assertEqual(list(Notification.objects.order_by("pk").values()), before)
        self.assertEqual(Notification.objects.get(pk=current.pk).status, "sending")

    def test_missing_lock_uses_last_update_deadline(self):
        stale = self.external(status="sending")
        current = self.external(status="sending")
        Notification.objects.filter(pk=stale.pk).update(updated_at=timezone.now() - timezone.timedelta(hours=1))
        results = recover_stale_notifications()
        self.assertEqual([row["notification_id"] for row in results], [stale.pk])
        current.refresh_from_db()
        self.assertEqual(current.status, "sending")

    def test_recovery_preserves_batch_limit_and_zero_is_no_op(self):
        self.stale_claim()
        self.stale_claim()
        self.external()
        with patch("apps.notifications.delivery._deliver") as provider:
            self.assertEqual(process_due_notifications(limit=0), [])
            self.assertEqual(len(process_due_notifications(limit=1)), 1)
            provider.assert_not_called()
        self.assertEqual(Notification.objects.filter(status="sending").count(), 1)
        self.assertEqual(Notification.objects.filter(channel="email", status="pending").count(), 1)

    def test_late_provider_ack_cannot_overwrite_recovered_claim(self):
        claimed = self.stale_claim()

        def acknowledged_after_recovery(_):
            self.assertEqual(len(recover_stale_notifications()), 1)
            return {"ok": True, "message_id": "late-ack"}

        with patch("apps.notifications.delivery._deliver", side_effect=acknowledged_after_recovery):
            self.assertEqual(deliver_notification(claimed, claimed=True)["status"], "skipped")
        claimed.refresh_from_db()
        self.assertEqual(claimed.status, "failed")
        self.assertEqual(self.failure_events(claimed).count(), 1)
        self.assertTrue(ActivityEvent.objects.filter(event_type="notification_claim_revoked",
                                                     metadata__notification_id=claimed.pk).exists())

    def test_exception_exhaustion_alerts_once_and_redacts_provider_error(self):
        claimed = claim_notification(self.external(max_attempts=1).pk)
        stale = Notification.objects.get(pk=claimed.pk)
        with patch("apps.notifications.delivery._deliver", side_effect=RuntimeError("token=synthetic-secret")):
            result = deliver_notification(claimed, claimed=True)
        self.assertEqual(result["status"], "failed")
        self.assertNotIn("synthetic-secret", str(result))
        alert = Notification.objects.get(channel="system")
        self.assertEqual(alert.recipient_id, self.admin.pk)
        self.assertNotIn("synthetic-secret", alert.text)
        self.assertEqual(self.failure_events(claimed).count(), 1)
        self.assertNotIn("synthetic-secret", str(self.failure_events(claimed).get().metadata))
        with patch("apps.notifications.delivery._deliver") as provider:
            self.assertEqual(deliver_notification(stale, claimed=True)["status"], "skipped")
        provider.assert_not_called()
        self.assertEqual(Notification.objects.filter(channel="system").count(), 1)

    def test_retryable_exception_does_not_alert_before_attempt_limit(self):
        notification = self.external()
        with patch("apps.notifications.delivery._deliver", side_effect=RuntimeError("temporary")):
            self.assertEqual(deliver_notification(notification)["status"], "retry_scheduled")
        notification.refresh_from_db()
        self.assertIsNotNone(notification.next_retry_at)
        self.assertFalse(Notification.objects.filter(channel="system").exists())

    def test_returned_terminal_failure_still_alerts_once(self):
        notification = self.external()
        with patch("apps.notifications.delivery._deliver", return_value={"ok": False, "retryable": False, "reason": "rejected"}):
            self.assertEqual(deliver_notification(notification)["status"], "failed")
        self.assertEqual(Notification.objects.filter(channel="system").count(), 1)
        self.assertEqual(self.failure_events(notification).count(), 1)

    def test_terminal_failure_effects_roll_back_together(self):
        for target in ("_notify_delivery_failure", "_write_delivery_activity"):
            notification = self.external(max_attempts=1)
            claimed = claim_notification(notification.pk)
            before = Notification.objects.values().get(pk=notification.pk)
            with self.subTest(target=target), patch("apps.notifications.delivery._deliver", return_value={"ok": False}), \
                    patch("apps.notifications.delivery." + target, side_effect=RuntimeError("storage unavailable")), \
                    self.assertRaises(RuntimeError):
                deliver_notification(claimed, claimed=True)
            self.assertEqual(Notification.objects.values().get(pk=notification.pk), before)
            self.assertFalse(Notification.objects.filter(channel="system").exists())
            self.assertFalse(self.failure_events(notification).exists())

    def test_recovery_rolls_back_with_failed_alert_and_can_repeat(self):
        claimed = self.stale_claim()
        with patch("apps.notifications.delivery._notify_delivery_failure", side_effect=RuntimeError("storage unavailable")), \
                self.assertRaises(RuntimeError):
            recover_stale_notifications()
        claimed.refresh_from_db()
        self.assertEqual(claimed.status, "sending")
        self.assertEqual(len(recover_stale_notifications()), 1)
        self.assertEqual(self.failure_events(claimed).count(), 1)
