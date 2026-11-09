from unittest.mock import patch
from uuid import uuid4

from django.db import transaction
from django.test import TestCase, override_settings
from redis import RedisError
from rest_framework.exceptions import NotFound

from apps.notifications.announcements import revoke_announcement
from apps.notifications.personal_services import change_personal_state, read_personal_feed
from apps.notifications.realtime import _publish, announcement_channel
from apps.notifications.tests_personal_services import PersonalNotificationFixtures


@override_settings(NOTIFICATION_EVENTS_ENABLED=True)
class AnnouncementInvalidationTests(PersonalNotificationFixtures, TestCase):
    @patch("apps.notifications.realtime._publish")
    def test_publish_and_revoke_signal_only_after_commit_and_only_once(self, publish):
        key = uuid4()
        with self.captureOnCommitCallbacks(execute=True):
            announcement = self.publish(publication_key=key)
            publish.assert_not_called()
        publish.assert_called_once_with(self.business.pk)
        publish.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            self.publish(publication_key=key)
        publish.assert_not_called()
        with self.captureOnCommitCallbacks(execute=True):
            revoke_announcement(actor=self.owner, business=self.business, notification_id=announcement.pk)
            revoke_announcement(actor=self.owner, business=self.business, notification_id=announcement.pk)
            publish.assert_not_called()
        publish.assert_called_once_with(self.business.pk)

    @patch("apps.notifications.realtime._publish")
    def test_all_receipt_transitions_signal_but_idempotent_replay_does_not(self, publish):
        announcement = self.publish()
        for action in ("read", "open", "acknowledge", "unread"):
            publish.reset_mock()
            with self.captureOnCommitCallbacks(execute=True):
                self.change(announcement, action)
                self.change(announcement, action)
                publish.assert_not_called()
            publish.assert_called_once_with(self.business.pk)

    @patch("apps.notifications.realtime._publish")
    def test_rollback_keeps_receipt_and_broker_unchanged(self, publish):
        announcement = self.publish()
        with self.captureOnCommitCallbacks(execute=True):
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    self.change(announcement, "open")
                    raise RuntimeError("rollback")
        publish.assert_not_called()
        self.assertIsNone(self.state(announcement).opened_at)
        self.assertIsNone(self.state(announcement).read_at)

    @patch("apps.notifications.realtime._publish")
    def test_read_all_batches_emit_one_signal_and_no_op_emits_none(self, publish):
        self.publish()
        self.publish()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(read_personal_feed(actor=self.staff, business=self.business), 2)
            publish.assert_not_called()
        publish.assert_called_once_with(self.business.pk)
        publish.reset_mock()
        with self.captureOnCommitCallbacks(execute=True):
            self.assertEqual(read_personal_feed(actor=self.staff, business=self.business), 0)
        publish.assert_not_called()

    @patch("apps.notifications.realtime._publish")
    def test_work_receipts_and_forbidden_foreign_receipts_do_not_broadcast(self, publish):
        work = self.work()
        announcement = self.publish()
        with self.captureOnCommitCallbacks(execute=True):
            self.change(work, "read")
            with self.assertRaises(NotFound):
                change_personal_state(actor=self.outsider, business=self.foreign,
                                      notification_id=announcement.pk, action="read")
        publish.assert_not_called()

    @override_settings(NOTIFICATION_EVENTS_ENABLED=False)
    @patch("apps.notifications.realtime._publish")
    def test_disabled_transport_preserves_crm_behavior(self, publish):
        with self.captureOnCommitCallbacks(execute=True):
            announcement = self.publish()
            self.change(announcement, "read")
        publish.assert_not_called()
        self.assertIsNotNone(self.state(announcement).read_at)

    @patch("apps.notifications.realtime.Redis.from_url", side_effect=RedisError("secret URL"))
    def test_broker_outage_does_not_fail_commit_or_log_secrets(self, _client):
        announcement = self.publish()
        with self.assertLogs("apps.notifications.realtime", level="WARNING") as logs:
            with self.captureOnCommitCallbacks(execute=True):
                self.change(announcement, "read")
        self.assertIsNotNone(self.state(announcement).read_at)
        self.assertNotIn("secret URL", " ".join(logs.output))

    @override_settings(NOTIFICATION_EVENTS_NAMESPACE="test:isolated")
    @patch("apps.notifications.realtime.Redis.from_url")
    def test_payload_is_only_invalidation_and_channel_is_business_scoped(self, factory):
        _publish(self.business.pk)
        factory.return_value.__enter__.return_value.publish.assert_called_once_with(
            f"test:isolated:announcements:{self.business.pk}", "changed")
        self.assertNotEqual(announcement_channel(self.business.pk), announcement_channel(self.foreign.pk))
