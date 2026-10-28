"""Synthetic HTTP regressions for authenticated WhatsApp tenant routing."""
import hashlib
import hmac
import json

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.bots.models import Bot, BotChannel, BotConversation, BotMessage
from apps.integrations.models import BusinessEvent, IntegrationEventLog
from apps.integrations import tests as foundation
from apps.integrations.whatsapp_routing import VerifiedWhatsAppWebhook, resolve_whatsapp_channel


@override_settings(WHATSAPP_ENABLED=False, WHATSAPP_WEBHOOK_SECRET="", WHATSAPP_APP_SECRET="synthetic-app-signing-key")
class WhatsAppTenantBindingTests(TestCase):
    def setUp(self):
        foundation.WhatsAppIntegrationFoundationTests.setUp(self)
        self.other_bot = Bot.objects.create(business=self.other_business, name="Other bot")
        self.other_channel = BotChannel.objects.create(
            bot=self.other_bot, channel="whatsapp", status="active",
            config_json={"webhook_secret": "synthetic-other-secret", "phone_number_id": "other-phone"},
        )

    def value(self, phone="dev-phone", *, status=False, message_id="synthetic-message"):
        result = {"metadata": {"phone_number_id": phone}}
        if status:
            result["statuses"] = [{"id": message_id, "status": "read", "timestamp": "1700000000"}]
        else:
            result["messages"] = [{"id": message_id, "from": "synthetic-sender", "type": "text", "text": {"body": "Hello"}}]
        return result

    def payload(self, *values):
        return {"object": "whatsapp_business_account", "entry": [{"changes": [{"value": v} for v in values]}]}

    def post(self, payload, *, signed=False, secret="whatsapp-secret"):
        body = json.dumps(payload).encode()
        headers = {"HTTP_X_ZANI_WHATSAPP_SECRET": secret}
        if signed:
            headers["HTTP_X_HUB_SIGNATURE_256"] = "sha256=" + hmac.new(b"synthetic-app-signing-key", body, hashlib.sha256).hexdigest()
        return self.api.generic("POST", "/api/integrations/whatsapp/webhook/", body, content_type="application/json", **headers)

    def outbound(self, bot=None, message_id="synthetic-message"):
        bot = bot or self.other_bot
        conversation = BotConversation.objects.create(business=bot.business, bot=bot, channel="whatsapp", external_user_id="synthetic-recipient")
        return BotMessage.objects.create(conversation=conversation, direction="outbound", status="sent", external_message_id=message_id, text="Synthetic")

    def assert_rejected_without_effects(self, payload):
        before = (BotConversation.objects.count(), BotMessage.objects.count(), BusinessEvent.objects.count(), IntegrationEventLog.objects.count())
        response = self.post(payload)
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(before, (BotConversation.objects.count(), BotMessage.objects.count(), BusinessEvent.objects.count(), IntegrationEventLog.objects.count()))

    def test_channel_secret_cannot_route_inbound_to_other_business(self):
        self.assert_rejected_without_effects(self.payload(self.value("other-phone")))

    def test_channel_secret_cannot_update_other_business_status(self):
        message = self.outbound()
        self.assert_rejected_without_effects(self.payload(self.value("other-phone", status=True)))
        message.refresh_from_db()
        self.assertIsNone(message.read_at)

    def test_later_mismatched_metadata_rejects_before_first_status_write(self):
        message = self.outbound(self.bot)
        self.assert_rejected_without_effects(self.payload(self.value(status=True), self.value("other-phone", status=True)))
        message.refresh_from_db()
        self.assertIsNone(message.read_at)

    def test_ignored_later_message_is_also_preflighted(self):
        self.assert_rejected_without_effects(self.payload(self.value(), self.value("other-phone")))

    def test_mixed_status_and_message_preflight(self):
        self.outbound(self.bot)
        self.assert_rejected_without_effects(self.payload(self.value(status=True), self.value("other-phone")))

    def test_unknown_route_does_not_fall_back_to_secret(self):
        self.assert_rejected_without_effects(self.payload(self.value("unknown-phone")))

    def test_valid_channel_inbound_remains_idempotent(self):
        payload = self.payload(self.value())
        self.assertEqual(self.post(payload).status_code, 200)
        self.assertEqual(self.post(payload).status_code, 200)
        self.assertEqual(BotMessage.objects.filter(direction="inbound").count(), 1)
        self.assertEqual(BusinessEvent.objects.filter(event_type="message.received").count(), 1)

    def test_generic_channel_secret_message_remains_supported(self):
        self.assertEqual(self.post({"message_id": "generic", "from": "synthetic-sender", "text": "Hello"}).status_code, 200)
        self.assertEqual(BotMessage.objects.get().conversation.business_id, self.business.id)

    def test_signed_multi_business_statuses_keep_routes_and_log_privacy(self):
        first = self.outbound(self.bot)
        second = self.outbound()
        payload = self.payload(self.value(status=True), self.value("other-phone", status=True))
        response = self.post(payload, signed=True)
        self.assertEqual(response.status_code, 200, response.data)
        first.refresh_from_db(); second.refresh_from_db()
        self.assertIsNotNone(first.read_at)
        self.assertIsNotNone(second.read_at)
        for business, forbidden in ((self.business, "other-phone"), (self.other_business, "dev-phone")):
            logs = IntegrationEventLog.objects.filter(business=business, direction="inbound")
            self.assertTrue(logs.exists())
            self.assertNotIn(forbidden, json.dumps(list(logs.values_list("payload_json", flat=True))))

    def test_status_cannot_update_other_bot_in_same_business(self):
        sibling = Bot.objects.create(business=self.business, name="Sibling")
        message = self.outbound(sibling)
        response = self.post(self.payload(self.value(status=True)))
        self.assertEqual(response.status_code, 200)
        message.refresh_from_db()
        self.assertIsNone(message.read_at)

    def test_signed_ambiguous_phone_is_rejected_before_effects(self):
        self.other_channel.config_json["phone_number_id"] = "dev-phone"
        self.other_channel.save(update_fields=["config_json"])
        response = self.post(self.payload(self.value()), signed=True)
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(BotMessage.objects.exists())

    def test_invalid_signature_does_not_fall_back_to_valid_secret(self):
        response = self.api.post("/api/integrations/whatsapp/webhook/", self.payload(self.value()), format="json", HTTP_X_ZANI_WHATSAPP_SECRET="whatsapp-secret", HTTP_X_HUB_SIGNATURE_256="sha256=invalid")
        self.assertEqual(response.status_code, 403)
        self.assertFalse(BotMessage.objects.exists())

    @override_settings(WHATSAPP_WEBHOOK_SECRET="synthetic-global-secret")
    def test_configured_global_internal_route_remains_supported(self):
        response = self.post(self.payload(self.value("other-phone")), secret="synthetic-global-secret")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(BotMessage.objects.get().conversation.business_id, self.other_business.id)

    def test_external_id_alias_remains_supported(self):
        self.channel.external_id = "external-alias"
        self.channel.save(update_fields=["external_id"])
        response = self.post(self.payload(self.value("external-alias")))
        self.assertEqual(response.status_code, 200, response.data)

    def test_signed_inbound_retains_only_selected_change(self):
        response = self.post(self.payload(self.value(), self.value("other-phone")), signed=True)
        self.assertEqual(response.status_code, 200, response.data)
        message = BotMessage.objects.get()
        self.assertEqual(message.conversation.business_id, self.business.id)
        self.assertNotIn("other-phone", json.dumps(message.payload_json))
        self.assertNotIn("other-phone", json.dumps(list(IntegrationEventLog.objects.values_list("payload_json", flat=True))))

    def test_signed_later_unknown_route_rejects_before_status_effect(self):
        message = self.outbound(self.bot)
        response = self.post(self.payload(self.value(status=True), self.value("unknown-phone", status=True)), signed=True)
        self.assertEqual(response.status_code, 400, response.data)
        message.refresh_from_db()
        self.assertIsNone(message.read_at)
        self.assertFalse(IntegrationEventLog.objects.exists())

    def test_bound_context_revalidates_active_and_business_binding(self):
        context = VerifiedWhatsAppWebhook("channel", self.channel.pk, self.bot.pk, self.business.pk)
        self.channel.status = "paused"
        self.channel.save(update_fields=["status"])
        with self.assertRaises(PermissionDenied):
            resolve_whatsapp_channel(context, "dev-phone")
        self.channel.status = "active"
        self.channel.bot = self.other_bot
        self.other_channel.delete()
        self.channel.save(update_fields=["status", "bot"])
        with self.assertRaises(PermissionDenied):
            resolve_whatsapp_channel(context, "dev-phone")

    def test_unverified_raw_secret_is_not_a_service_auth_context(self):
        with self.assertRaises(PermissionDenied):
            resolve_whatsapp_channel("whatsapp-secret", "other-phone")

    def test_global_signed_message_requires_route(self):
        response = self.post({"from": "synthetic-sender", "text": "Hello"}, signed=True)
        self.assertEqual(response.status_code, 403)
        self.assertFalse(BotMessage.objects.exists())

    def test_generic_route_mismatch_is_rejected(self):
        self.assert_rejected_without_effects({"phone_number_id": "other-phone", "from": "synthetic-sender", "text": "Hello"})
