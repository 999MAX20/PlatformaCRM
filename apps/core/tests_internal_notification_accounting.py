from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from django.contrib.auth import get_user_model
from apps.businesses.models import Business
from apps.notifications.models import Notification, NotificationRecipient
from apps.notifications.delivery import process_due_notifications, claim_notification, deliver_notification
from apps.core.operations_health import _queue_summary

class InternalAccountingTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username='internal-accounting')
        self.business = Business.objects.create(owner=self.user, name='Test', slug='internal-accounting')

    def make(self, channel='system', **kwargs):
        return Notification.objects.create(business=self.business, recipient=self.user, channel=channel,
            text='History must survive', send_at=timezone.now(), **kwargs)

    def test_published_unread_does_not_warn_and_delivery_never_changes_history(self):
        n = self.make()
        before = list(Notification.objects.values())
        states = list(NotificationRecipient.objects.values())
        with patch('apps.notifications.delivery._deliver') as provider, patch('apps.notifications.delivery._write_delivery_activity') as activity:
            for _ in range(2):
                self.assertEqual(process_due_notifications(), [])
                self.assertIsNone(claim_notification(n.pk))
                self.assertEqual(deliver_notification(n)['status'], 'skipped')
                self.assertEqual(deliver_notification(n, claimed=True)['status'], 'skipped')
            provider.assert_not_called(); activity.assert_not_called()
        q = _queue_summary()
        self.assertEqual(q['notifications']['due'], 0)
        self.assertEqual(q['internal_notifications']['published'], 1)
        self.assertEqual(q['status'], 'healthy')
        self.assertEqual(list(Notification.objects.values()), before)
        self.assertEqual(list(NotificationRecipient.objects.values()), states)

    def test_read_state_and_old_internal_retry_are_preserved(self):
        n = self.make(status='retry_scheduled', next_retry_at=timezone.now())
        NotificationRecipient.objects.filter(notification=n).update(read_at=timezone.now())
        before = list(NotificationRecipient.objects.values())
        self.assertEqual(process_due_notifications(), [])
        self.assertEqual(_queue_summary()['notifications']['retry_scheduled'], 0)
        self.assertEqual(list(NotificationRecipient.objects.values()), before)

    def test_external_states_still_warn_fail_and_claim(self):
        n = self.make(channel='email')
        self.assertEqual(_queue_summary()['status'], 'warning')
        self.assertEqual(_queue_summary()['notifications']['due'], 1)
        self.assertIsNotNone(claim_notification(n.pk))
        n.status='retry_scheduled';n.save(update_fields=['status'])
        self.assertEqual(_queue_summary()['notifications']['retry_scheduled'], 1)
        n.status='failed';n.save(update_fields=['status'])
        self.assertEqual(_queue_summary()['notifications']['failed'], 1)
        self.assertEqual(_queue_summary()['status'], 'critical')

    def test_missing_publication_and_internal_failure_remain_visible(self):
        n = self.make()
        NotificationRecipient.objects.filter(notification=n).delete()
        self.assertEqual(_queue_summary()['internal_notifications']['missing_recipients'], 1)
        self.assertEqual(_queue_summary()['status'], 'critical')
        NotificationRecipient.objects.create(notification=n,user=self.user)
        n.status='failed';n.save(update_fields=['status'])
        self.assertEqual(_queue_summary()['internal_notifications']['failed'], 1)
        self.assertEqual(_queue_summary()['status'], 'critical')
