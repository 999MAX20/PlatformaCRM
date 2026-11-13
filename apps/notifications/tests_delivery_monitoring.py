from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.models import ServiceComponentState
from apps.core.service_status import observe_business_service, overdue_work_counts
from apps.notifications.delivery import process_due_notifications
from apps.notifications.models import Notification
from apps.notifications.tests_delivery_lifecycle import DeliveryFixtures


@override_settings(NOTIFICATION_DELIVERY_STALE_LOCK_SECONDS=900)
class NotificationDeliveryMonitoringTests(DeliveryFixtures, TestCase):
    def test_published_internal_work_is_not_an_external_queue_incident(self):
        notification = self.work(actor=self.owner)
        Notification.objects.filter(pk=notification.pk).update(send_at=timezone.now() - timezone.timedelta(days=1))
        before = list(notification.recipient_states.values())
        self.assertEqual(overdue_work_counts(self.business, now=timezone.now())["notifications"], 0)
        self.assertEqual(observe_business_service(self.business.pk), [])
        self.assertEqual(ServiceComponentState.objects.get(business=self.business, component="notifications").state, "healthy")
        self.assertEqual(list(notification.recipient_states.values()), before)
        self.assertEqual(process_due_notifications(), [])

    def test_monitor_counts_only_current_business_overdue_external_work(self):
        now = timezone.now()
        old = now - timezone.timedelta(hours=1)
        self.external()
        self.external(status="retry_scheduled", next_retry_at=old)
        self.external(status="sending", locked_at=old)
        missing_lock = self.external(status="sending")
        Notification.objects.filter(pk=missing_lock.pk).update(updated_at=old)
        self.external(send_at=now + timezone.timedelta(hours=1))
        self.external(status="retry_scheduled", next_retry_at=now + timezone.timedelta(hours=1))
        self.external(status="sending", locked_at=now)
        self.external(status="sending")
        for status in ("sent", "failed", "cancelled"):
            self.external(status=status)
        for status in ("pending", "sending", "retry_scheduled"):
            self.work(actor=self.owner, status=status, locked_at=old, next_retry_at=old)
        self.external(business=self.foreign, client=None)
        self.assertEqual(overdue_work_counts(self.business, now=now)["notifications"], 4)

    def test_existing_false_internal_incident_recovers_without_changing_history(self):
        old = timezone.now() - timezone.timedelta(hours=1)
        notification = self.work(actor=self.owner)
        Notification.objects.filter(pk=notification.pk).update(send_at=old)
        ServiceComponentState.objects.create(business=self.business, component="notifications", state="degraded",
                                             episode=1, started_at=old, observed_at=old, affected_count=1)
        before = Notification.objects.values().get(pk=notification.pk)
        transitions = observe_business_service(self.business.pk)
        self.assertEqual([(row.component, transition) for row, transition in transitions], [("notifications", "recovered")])
        self.assertEqual(Notification.objects.values().get(pk=notification.pk), before)
        self.assertEqual(observe_business_service(self.business.pk), [])

    def test_stale_send_recovery_closes_queue_incident_without_claiming_delivery_success(self):
        claimed = self.stale_claim()
        self.assertEqual(overdue_work_counts(self.business, now=timezone.now())["notifications"], 1)
        observe_business_service(self.business.pk)
        with patch("apps.notifications.delivery._deliver") as provider:
            self.assertEqual(process_due_notifications()[0]["status"], "failed")
        provider.assert_not_called()
        transitions = observe_business_service(self.business.pk)
        self.assertEqual([(row.component, transition) for row, transition in transitions], [("notifications", "recovered")])
        claimed.refresh_from_db()
        self.assertEqual(claimed.status, "failed")
        self.assertIsNone(claimed.delivered_at)
