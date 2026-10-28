from unittest.mock import patch

from django.db import transaction
from django.test import TransactionTestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bots.models import BotConversation, BotMessage
from apps.bots.outbound_delivery import create_outbound_message, deliver_outbound_message, retry_outbound_message, recover_stale_outbound_messages
from apps.integrations import tests as foundation
from apps.integrations.ycloud import client
from apps.integrations.ycloud.dispatch import apply_status
from apps.integrations.ycloud.models import YCloudConnection, YCloudDispatch


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-secret", OUTBOUND_MESSAGES_RUN_INLINE=True)
class YCloudDispatchTests(TransactionTestCase):
    def setUp(self):
        foundation.WhatsAppIntegrationFoundationTests.setUp(self)
        self.channel.config_json = {"provider_mode": "ycloud", "setup_revision": "revision", "connection_verified": True}
        self.channel.save()
        self.binding = YCloudConnection.objects.create(channel=self.channel, initiated_by=self.owner,
            setup_revision="revision", status="connected", expires_at=timezone.now(),
            waba_id="waba-1", phone_id="phone-1", phone_number="+77010000000")
        self.conversation = BotConversation.objects.create(business=self.business, bot=self.bot,
            channel="whatsapp", external_user_id="+77012223344", last_inbound_at=timezone.now())

    def send(self):
        return create_outbound_message(self.conversation, text="Hello", user=self.owner)

    def receipt(self, message, status="delivered", **changes):
        attempt = YCloudDispatch.objects.filter(message=message).latest("pk")
        data = {"id": "yc-1", "externalId": str(attempt.correlation_id), "wabaId": "waba-1",
            "from": "+77010000000", "to": "+77012223344", "wamid": "wamid.1", "status": status, **changes}
        with transaction.atomic():
            apply_status(self.binding, data)
        message.refresh_from_db()

    def test_acceptance_is_not_sent_and_receipts_do_not_regress(self):
        with patch.object(client, "call", return_value={"id": "yc-1", "status": "accepted"}) as network:
            message = self.send()
        self.assertEqual(network.call_count, 1)
        self.assertEqual(message.status, "accepted")
        self.assertIsNone(message.sent_at)
        with self.assertRaises(ValidationError):
            retry_outbound_message(message, actor=self.owner)
        self.receipt(message, "read")
        self.assertEqual(message.status, "sent")
        self.assertIsNotNone(message.read_at)
        read_at = message.read_at
        self.receipt(message, "sent")
        self.receipt(message, "failed")
        self.assertEqual(message.status, "sent")
        self.assertEqual(message.read_at, read_at)
        self.assertEqual(message.payload_json["ycloud_status"], "read")

    def test_ambiguous_timeout_never_retries_and_receipt_resolves(self):
        with patch.object(client, "call", side_effect=client.YCloudError(ambiguous=True)) as network:
            message = self.send()
            recover_stale_outbound_messages(now=timezone.now()+timezone.timedelta(hours=2))
            deliver_outbound_message(message.pk)
        self.assertEqual(network.call_count, 1)
        self.assertEqual(message.status, "delivery_unknown")
        with self.assertRaises(ValidationError):
            retry_outbound_message(message, actor=self.owner)
        self.receipt(message)
        self.assertEqual(message.status, "sent")

    def test_receipt_before_http_response_is_not_overwritten(self):
        def response(*args):
            message = BotMessage.objects.get(direction="outbound")
            self.receipt(message, "read")
            return {"id": "yc-1", "status": "accepted"}
        with patch.object(client, "call", side_effect=response):
            message = self.send()
        self.assertEqual(message.payload_json["ycloud_status"], "read")
        self.assertIsNotNone(message.read_at)

    def test_http_is_after_commit_and_rollback_sends_nothing(self):
        with patch.object(client, "call", return_value={"id": "yc-1"}) as network:
            with self.assertRaises(RuntimeError), transaction.atomic():
                self.send()
                network.assert_not_called()
                raise RuntimeError("rollback")
            network.assert_not_called()
            self.assertFalse(BotMessage.objects.exists())
            with transaction.atomic():
                self.send()
                network.assert_not_called()
            network.assert_called_once()

    def test_rate_limit_uses_delayed_safe_retry(self):
        with patch.object(client, "call", side_effect=client.YCloudError("rate_limited", retryable=True, retry_after=120)):
            message = self.send()
        self.assertEqual(message.status, "retry_scheduled")
        self.assertGreater(message.delivery_next_retry_at, timezone.now()+timezone.timedelta(seconds=100))
        message.delivery_next_retry_at = timezone.now()
        message.save(update_fields=["delivery_next_retry_at"])
        with patch.object(client, "call", return_value={"id": "yc-2", "status": "accepted"}) as network:
            deliver_outbound_message(message.pk)
        self.assertEqual(network.call_count, 1)
        self.assertEqual(YCloudDispatch.objects.filter(message=message).count(), 2)

    def test_closed_window_and_paused_channel_never_call_provider(self):
        self.conversation.last_inbound_at = timezone.now()-timezone.timedelta(days=2)
        self.conversation.save()
        with patch.object(client, "call") as network:
            message = self.send()
            self.assertEqual(message.status, "failed")
            network.assert_not_called()
        self.conversation.last_inbound_at = timezone.now()
        self.conversation.save()
        self.channel.status = "paused"
        self.channel.save()
        with patch.object(client, "call") as network:
            self.assertEqual(self.send().status, "failed")
            network.assert_not_called()

    def test_foreign_receipt_cannot_change_message(self):
        with patch.object(client, "call", return_value={"id": "yc-1"}):
            message = self.send()
        for changes in [{"to": "+77019999999"}, {"wabaId": "foreign"}, {"from": "+77019999999"}]:
            with self.assertRaises(client.YCloudError):
                self.receipt(message, **changes)
        message.refresh_from_db()
        self.assertEqual(message.status, "accepted")

    def test_disabled_provider_does_not_fall_back_to_mock(self):
        with override_settings(YCLOUD_ENABLED=False), patch.object(client, "call") as network:
            message = self.send()
            self.assertEqual(message.status, "failed")
            network.assert_not_called()

    def test_permission_revocation_before_worker_prevents_send(self):
        with override_settings(OUTBOUND_MESSAGES_RUN_INLINE=False), patch("apps.bots.tasks.process_outbound_message_task.delay"):
            message = self.send()
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        with patch.object(client, "call") as network:
            message = deliver_outbound_message(message.pk)
            network.assert_not_called()
        self.assertEqual(message.status, "failed")
        self.assertEqual(message.error_text, "permission_revoked")

    def test_old_inbound_delivery_does_not_reopen_customer_service_window(self):
        BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Old message",
            payload_json={"whatsapp_payload": {"ycloud_sent_at": (timezone.now()-timezone.timedelta(days=2)).isoformat()}})
        with patch.object(client, "call") as network:
            self.assertEqual(self.send().status, "failed")
            network.assert_not_called()

    def test_failure_receipt_cannot_be_reopened_by_late_acceptance(self):
        def response(*args):
            self.receipt(BotMessage.objects.get(direction="outbound"), "failed")
            return {"id": "yc-1", "status": "accepted"}
        with patch.object(client, "call", side_effect=response):
            message = self.send()
        self.assertEqual(message.status, "failed")
        self.receipt(message, "accepted")
        self.assertEqual(message.status, "failed")
        self.receipt(message, "delivered")
        self.assertEqual(message.status, "sent")
