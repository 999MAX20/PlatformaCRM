import json
from io import BytesIO
from datetime import timedelta
from unittest.mock import MagicMock, patch
from urllib.error import HTTPError

from django.test import TransactionTestCase, override_settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bots.models import BotConversation, BotMessage
from apps.bots.outbound_delivery import create_outbound_message, deliver_outbound_message, recover_stale_outbound_messages, retry_outbound_message
from apps.integrations.tests import WhatsAppIntegrationFoundationTests
from apps.integrations.whatsapp.meta_delivery import begin_attempt
from apps.integrations.whatsapp.receipts import apply_receipt


@override_settings(WHATSAPP_ENABLED=True, WHATSAPP_GRAPH_BASE_URL="https://graph.facebook.com", OUTBOUND_MESSAGES_RUN_INLINE=False)
class MetaDeliveryTests(TransactionTestCase):
    def setUp(self):
        WhatsAppIntegrationFoundationTests.setUp(self)
        self.channel.config_json["provider_mode"] = "meta_cloud"
        self.channel.save()
        self.conversation = BotConversation.objects.create(business=self.business, bot=self.bot,
            channel="whatsapp", external_user_id="77015550101", last_inbound_at=timezone.now())
        BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="hello")
        self.message = BotMessage.objects.create(conversation=self.conversation, direction="outbound",
            sender_type="manager", text="reply", status="queued", delivery_max_attempts=3,
            payload_json={"sent_by_user_id": self.owner.pk})
        self.credentials = patch("apps.integrations.providers.whatsapp.get_whatsapp_access_token", return_value="synthetic-token")
        self.credentials.start()
        self.addCleanup(self.credentials.stop)

    def response(self, body=None):
        response = MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps(body if body is not None else {"messages": [{"id": "wamid.sent"}]}).encode()
        return response

    def deliver(self, *, result=None, error=None):
        with patch("apps.integrations.providers.whatsapp.urllib_request.urlopen", return_value=result or self.response(), side_effect=error) as http:
            deliver_outbound_message(self.message.pk)
            self.message.refresh_from_db()
            return http

    def receipt(self, status, **extra):
        self.message.refresh_from_db()
        correlation = self.message.payload_json["meta_attempt"]["id"]
        return apply_receipt(self.channel, {"id": "wamid.sent", "status": status,
            "recipient_id": self.conversation.external_user_id, "biz_opaque_callback_data": correlation,
            "timestamp": "1800000000", **extra})

    def test_success_is_accepted_until_signed_receipt_and_claim_is_single_winner(self):
        http = self.deliver()
        self.assertEqual(self.message.status, "accepted")
        self.assertIsNone(self.message.sent_at)
        sent = json.loads(http.call_args.args[0].data)
        self.assertEqual(sent["biz_opaque_callback_data"], self.message.payload_json["meta_attempt"]["id"])
        with patch("apps.integrations.providers.whatsapp.urllib_request.urlopen") as again:
            deliver_outbound_message(self.message.pk)
            again.assert_not_called()
        self.receipt("read")
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, "sent")
        self.assertIsNotNone(self.message.read_at)

    def test_timeout_blocks_automatic_and_manual_retry_then_receipt_recovers(self):
        self.deliver(error=TimeoutError("ambiguous response"))
        self.assertEqual(self.message.status, "delivery_unknown")
        self.assertIsNone(self.message.delivery_next_retry_at)
        with self.assertRaises(ValidationError):
            retry_outbound_message(self.message, actor=self.owner)
        with patch("apps.integrations.providers.whatsapp.urllib_request.urlopen") as http:
            deliver_outbound_message(self.message.pk)
            http.assert_not_called()
        self.receipt("delivered")
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, "sent")

    def test_missing_success_id_and_server_error_are_unknown(self):
        for response, error in [(self.response({}), None), (None, HTTPError("https://example.invalid", 503, "bad", {}, None))]:
            with self.subTest(error=error):
                self.message.status = "queued"
                self.message.payload_json = {"sent_by_user_id": self.owner.pk}
                self.message.save()
                self.deliver(result=response, error=error)
                self.assertEqual(self.message.status, "delivery_unknown")

    def test_explicit_rate_limit_retries_but_auth_rejection_does_not(self):
        self.deliver(error=HTTPError("https://example.invalid", 429, "rate", {}, None))
        self.assertEqual(self.message.status, "retry_scheduled")
        self.assertIsNotNone(self.message.delivery_next_retry_at)
        self.message.delivery_next_retry_at = timezone.now() - timedelta(seconds=1)
        self.message.save()
        self.deliver(error=HTTPError("https://example.invalid", 401, "auth", {}, None))
        self.assertEqual(self.message.status, "failed")
        self.assertEqual(self.message.delivery_attempts, 2)

    def test_rate_limit_respects_attempt_limit(self):
        self.message.delivery_attempts = 2
        self.message.save()
        self.deliver(error=HTTPError("https://example.invalid", 429, "rate", {}, None))
        self.assertEqual(self.message.status, "failed")
        self.assertIsNone(self.message.delivery_next_retry_at)

    def test_graph_rate_limit_code_on_http_400_is_retryable(self):
        error = HTTPError("https://example.invalid", 400, "rate", {}, BytesIO(b'{"error":{"code":130429}}'))
        self.deliver(error=error)
        self.assertEqual(self.message.status, "retry_scheduled")

    @override_settings(OUTBOUND_MESSAGES_RUN_INLINE=True)
    def test_send_waits_for_commit_and_rollback_sends_nothing(self):
        with patch("apps.integrations.providers.whatsapp.urllib_request.urlopen", return_value=self.response()) as http:
            with transaction.atomic():
                created = create_outbound_message(self.conversation, text="after commit", user=self.owner)
                http.assert_not_called()
            self.assertEqual(http.call_count, 1)
            created.refresh_from_db()
            self.assertEqual(created.status, "accepted")
            with self.assertRaises(RuntimeError):
                with transaction.atomic():
                    create_outbound_message(self.conversation, text="rollback", user=self.owner)
                    raise RuntimeError("rollback")
            self.assertEqual(http.call_count, 1)
        self.assertFalse(BotMessage.objects.filter(text="rollback").exists())

    def test_crash_after_intent_never_resends(self):
        self.message.status = "delivering"
        self.message.delivery_locked_at = timezone.now() - timedelta(hours=1)
        self.message.save()
        begin_attempt(self.message, self.channel)
        recover_stale_outbound_messages()
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, "delivery_unknown")
        with self.assertRaises(ValidationError):
            retry_outbound_message(self.message, actor=self.owner)

    def test_receipt_before_http_response_is_not_overwritten(self):
        def receive(request, **kwargs):
            self.receipt("read")
            raise TimeoutError("late timeout")
        self.deliver(error=receive)
        self.assertEqual(self.message.status, "sent")
        self.assertIsNotNone(self.message.read_at)

    def test_late_failed_or_sent_receipt_does_not_regress_read(self):
        self.deliver()
        self.receipt("read")
        self.assertEqual(self.receipt("failed"), 0)
        self.assertEqual(self.receipt("sent"), 0)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, "sent")
        self.assertEqual(self.message.payload_json["whatsapp_status"]["status"], "read")

    def test_receipt_wrong_recipient_or_attempt_is_ignored(self):
        self.deliver()
        self.assertEqual(self.receipt("read", recipient_id="other"), 0)
        self.assertEqual(self.receipt("read", biz_opaque_callback_data="old-attempt"), 0)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, "accepted")

    def test_revoked_sender_or_disabled_channel_never_calls_provider(self):
        self.owner.is_active = False
        self.owner.save()
        http = self.deliver()
        http.assert_not_called()
        self.assertEqual(self.message.status, "failed")
        self.owner.is_active = True
        self.owner.save()
        self.channel.status = "disabled"
        self.channel.save()
        self.message.status = "queued"
        self.message.save()
        self.deliver().assert_not_called()

    def test_active_foreign_actor_cannot_send(self):
        self.message.payload_json = {"sent_by_user_id": self.other_owner.pk}
        self.message.save()
        self.deliver().assert_not_called()
        self.assertEqual(self.message.status, "failed")

    def test_closed_customer_service_window_does_not_send_or_retry(self):
        self.conversation.last_inbound_at = timezone.now() - timedelta(hours=25)
        self.conversation.save()
        self.deliver().assert_not_called()
        self.assertEqual(self.message.status, "failed")
        self.assertIsNone(self.message.delivery_next_retry_at)

    def test_previous_attempt_receipt_cannot_update_retry(self):
        self.deliver()
        previous = self.message.payload_json["meta_attempt"]["id"]
        self.receipt("failed")
        with patch("apps.bots.tasks.process_outbound_message_task.delay"):
            retry_outbound_message(self.message, actor=self.owner)
        self.deliver(result=self.response({"messages": [{"id": "wamid.new"}]}))
        self.assertEqual(self.receipt("read", biz_opaque_callback_data=previous), 0)
        self.message.refresh_from_db()
        self.assertEqual(self.message.status, "accepted")
        self.assertEqual(self.message.external_message_id, "wamid.new")
