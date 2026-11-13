from concurrent.futures import FIRST_COMPLETED, ThreadPoolExecutor, wait
from threading import Barrier, Event
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, connections
from django.test import TransactionTestCase, override_settings
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.core.models import AuditLog
from apps.notifications import delivery
from apps.notifications.models import Notification
from apps.notifications.tests_delivery_lifecycle import DeliveryFixtures
from apps.notifications.views import NotificationViewSet


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL concurrent connections")
@override_settings(NOTIFICATION_DELIVERY_STALE_LOCK_SECONDS=900)
class NotificationDeliveryConcurrencyTests(DeliveryFixtures, TransactionTestCase):
    def worker(self, callback):
        connections.close_all()
        try:
            return callback()
        finally:
            connections.close_all()

    def retry_request(self, notification_id):
        api = APIClient()
        api.force_authenticate(User.objects.get(pk=self.owner.pk))
        return api.post(f"/api/notifications/{notification_id}/retry/?business={self.business.pk}")

    def test_overlapping_retry_requests_have_one_send_and_do_not_hold_lock_during_io(self):
        failed = self.external(status="failed")
        selected = Barrier(2)
        sending = Event()
        release = Event()
        original_get = NotificationViewSet.get_object

        def select(view):
            obj = original_get(view)
            selected.wait(timeout=15)
            return obj

        def provider(_):
            sending.set()
            if not release.wait(15):
                raise AssertionError("Provider was not released")
            return {"ok": True}

        with patch.object(NotificationViewSet, "get_object", select), \
                patch("apps.notifications.delivery._deliver", side_effect=provider) as send, \
                ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.worker, lambda: self.retry_request(failed.pk)) for _ in range(2)]
            try:
                self.assertTrue(sending.wait(15))
                finished, _ = wait(futures, timeout=10, return_when=FIRST_COMPLETED)
                self.assertEqual(len(finished), 1)
                self.assertEqual(next(iter(finished)).result().status_code, 400)
            finally:
                release.set()
            self.assertEqual(sorted(future.result(timeout=15).status_code for future in futures), [200, 400])
        send.assert_called_once()
        failed.refresh_from_db()
        self.assertEqual(failed.status, "sent")
        self.assertEqual(AuditLog.objects.filter(metadata__kind="notification_manual_retry").count(), 1)

    def test_periodic_worker_cannot_claim_a_manual_retry_in_flight(self):
        failed = self.external(status="failed")
        sending = Event()
        release = Event()

        def provider(_):
            sending.set()
            if not release.wait(15):
                raise AssertionError("Provider was not released")
            return {"ok": True}

        with patch("apps.notifications.delivery._deliver", side_effect=provider) as send, ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.worker, lambda: self.retry_request(failed.pk))
            try:
                self.assertTrue(sending.wait(15))
                self.assertEqual(delivery.process_due_notifications(), [])
            finally:
                release.set()
            self.assertEqual(future.result(timeout=15).status_code, 200)
        send.assert_called_once()

    def test_two_recovery_workers_record_one_terminal_failure_and_alert(self):
        claimed = self.stale_claim()
        selected = Barrier(2)
        original = delivery._record_delivery_failure

        def fail(notification, **kwargs):
            selected.wait(timeout=15)
            return original(notification, **kwargs)

        with patch("apps.notifications.delivery._record_delivery_failure", side_effect=fail), ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(self.worker, delivery.recover_stale_notifications) for _ in range(2)]
            self.assertEqual(sorted(len(future.result(timeout=20)) for future in futures), [0, 1])
        self.assertEqual(self.failure_events(claimed).count(), 1)
        self.assertEqual(Notification.objects.filter(channel="system").count(), 1)
