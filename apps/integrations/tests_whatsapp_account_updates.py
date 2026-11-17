from copy import deepcopy

from django.test import TestCase, override_settings

from apps.bots.models import BotMessage
from apps.integrations.models import IntegrationEventLog
from apps.integrations import tests_whatsapp_binding as binding


@override_settings(WHATSAPP_ENABLED=False, WHATSAPP_WEBHOOK_SECRET="", WHATSAPP_APP_SECRET="synthetic-app-signing-key")
class WhatsAppAccountUpdateTests(TestCase):
    setUp = binding.WhatsAppTenantBindingTests.setUp
    post = binding.WhatsAppTenantBindingTests.post
    value = binding.WhatsAppTenantBindingTests.value

    def payload(self, account="account-1"):
        return {"object": "whatsapp_business_account", "entry": [{"id": account, "changes": [{
            "field": "account_update", "value": {"event": "PARTNER_ADDED", "waba_info": {
                "waba_id": account, "owner_business_id": "provider-business", "access_token": "never-record-this",
            }},
        }]}]}

    def test_signed_pre_onboarding_event_is_retained_without_tenant_or_message(self):
        for _ in range(2):
            response = self.post(self.payload(), signed=True)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["account_updates"], 1)
        self.assertFalse(BotMessage.objects.exists())
        for log in IntegrationEventLog.objects.all():
            self.assertIsNone(log.business_id)
            self.assertNotIn("never-record-this", str(log.payload_json))
            self.assertEqual(log.payload_json["owner_business_id"], "provider-business")

    def test_channel_secret_cannot_submit_account_events(self):
        self.assertEqual(self.post(self.payload()).status_code, 403)
        self.assertFalse(IntegrationEventLog.objects.exists())

    def test_known_account_logs_only_to_bound_tenant_even_when_paused(self):
        self.other_channel.config_json["business_account_id"] = "account-1"
        self.other_channel.status = "paused"
        self.other_channel.save()
        self.assertEqual(self.post(self.payload(), signed=True).status_code, 200)
        self.assertEqual(IntegrationEventLog.objects.get().business_id, self.other_business.pk)
        self.other_channel.refresh_from_db()
        self.assertEqual(self.other_channel.status, "paused")

    def test_mismatched_account_and_malformed_metadata_reject_before_logging(self):
        for invalid in ([], {"waba_id": "other"}, {"owner_business_id": {"bad": True}}):
            payload = self.payload()
            payload["entry"][0]["changes"][0]["value"]["waba_info"] = invalid
            self.assertEqual(self.post(payload, signed=True).status_code, 400)
        self.assertFalse(IntegrationEventLog.objects.exists())

    def test_mixed_envelope_preserves_message_processing_and_preflight(self):
        payload = self.payload()
        payload["entry"][0]["changes"].append({"field": "messages", "value": self.value()})
        bad = deepcopy(payload)
        bad["entry"][0]["changes"][1]["value"]["metadata"]["phone_number_id"] = "unknown"
        self.assertEqual(self.post(bad, signed=True).status_code, 400)
        self.assertFalse(IntegrationEventLog.objects.exists())
        self.assertFalse(BotMessage.objects.exists())
        self.assertEqual(self.post(payload, signed=True).status_code, 200)
        self.assertEqual(BotMessage.objects.count(), 1)

    def test_invalid_later_account_update_rolls_back_earlier_message(self):
        payload = self.payload()
        payload["entry"][0]["changes"].insert(0, {"field": "messages", "value": self.value()})
        payload["entry"][0]["changes"][1]["value"]["event"] = []
        self.assertEqual(self.post(payload, signed=True).status_code, 400)
        self.assertFalse(BotMessage.objects.exists())
        self.assertFalse(IntegrationEventLog.objects.exists())

    def test_account_event_cannot_hide_messages(self):
        payload = self.payload()
        payload["entry"][0]["changes"][0]["value"].update(self.value())
        self.assertEqual(self.post(payload, signed=True).status_code, 400)
        self.assertFalse(BotMessage.objects.exists())
