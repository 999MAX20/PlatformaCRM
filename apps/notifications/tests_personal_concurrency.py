from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest import skipUnless
from unittest.mock import patch
from uuid import uuid4

from django.db import connection, connections
from django.db.models.query import QuerySet
from django.test import TransactionTestCase

from apps.accounts.models import User
from apps.businesses.capabilities import ensure_business_capabilities
from apps.businesses.models import Business
from apps.core.models import AuditLog
from apps.notifications.announcements import publish_announcement
from apps.notifications.models import Notification, NotificationRecipient
from apps.notifications.personal_services import change_personal_state, read_personal_feed
from apps.notifications.tests_personal_services import PersonalNotificationFixtures


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks and concurrent connections")
class PersonalNotificationConcurrencyTests(PersonalNotificationFixtures, TransactionTestCase):
    def setUp(self):
        super().setUp()
        ensure_business_capabilities(self.business)

    def worker(self, callback, actor_id):
        connections.close_all()
        try:
            return callback(User.objects.get(pk=actor_id), Business.objects.get(pk=self.business.pk))
        finally:
            connections.close_all()

    def test_read_all_does_not_consume_concurrent_new_announcement(self):
        initial = self.publish()
        selected = Event()
        inserted = Event()
        original_update = QuerySet.update

        def pause_at_write(queryset, **fields):
            if queryset.model is NotificationRecipient and "read_at" in fields:
                selected.set()
                if not inserted.wait(15):
                    raise AssertionError("Concurrent announcement did not finish")
            return original_update(queryset, **fields)

        with patch.object(QuerySet, "update", pause_at_write), ThreadPoolExecutor(max_workers=1) as pool:
            pending = pool.submit(self.worker, lambda actor, business: read_personal_feed(actor=actor, business=business), self.staff.pk)
            try:
                self.assertTrue(selected.wait(15))
                arrival = self.publish(text="Arrived during read-all")
            finally:
                inserted.set()
            self.assertEqual(pending.result(timeout=15), 1)
        self.assertIsNotNone(self.state(initial).read_at)
        self.assertIsNone(self.state(arrival).read_at)
        self.assertIsNone(self.state(initial, self.peer).read_at)

    def test_concurrent_publication_retry_has_one_audience_and_audit(self):
        key = uuid4()

        def publish(actor, business):
            notification, created = publish_announcement(actor=actor, business=business, text="Concurrent",
                                                         priority="normal", publication_key=key)
            return notification.pk, created

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=15) for future in [pool.submit(self.worker, publish, self.owner.pk) for _ in range(2)]]
        self.assertEqual(len({pk for pk, _ in results}), 1)
        self.assertEqual(sum(created for _, created in results), 1)
        self.assertEqual(Notification.objects.count(), 1)
        self.assertEqual(NotificationRecipient.objects.count(), 5)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="announcement_published").count(), 1)

    def test_concurrent_acknowledgement_records_one_confirmation(self):
        notification = self.publish()
        self.change(notification, "open")

        def acknowledge(actor, business):
            return change_personal_state(actor=actor, business=business, notification_id=notification.pk,
                                         action="acknowledge").acknowledged_at

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = [future.result(timeout=15) for future in [pool.submit(self.worker, acknowledge, self.staff.pk) for _ in range(2)]]
        self.assertEqual(results[0], results[1])
        self.assertEqual(AuditLog.objects.filter(metadata__kind="notification_acknowledged").count(), 1)
