from copy import deepcopy
from django.test import TestCase, override_settings

from apps.integrations.tests_whatsapp_binding import WhatsAppTenantBindingTests
from apps.bots.models import BotMessage
from apps.integrations.models import BusinessEvent


@override_settings(WHATSAPP_ENABLED=False, WHATSAPP_WEBHOOK_SECRET="", WHATSAPP_APP_SECRET="synthetic-app-signing-key")
class WhatsAppBatchTests(TestCase):
    setUp = WhatsAppTenantBindingTests.setUp
    value = WhatsAppTenantBindingTests.value
    payload = WhatsAppTenantBindingTests.payload
    post = WhatsAppTenantBindingTests.post
    outbound = WhatsAppTenantBindingTests.outbound

    def test_all_messages_in_all_entries_are_saved_once(self):
        value = self.value(message_id="one")
        second = deepcopy(value["messages"][0])
        second["id"] = "two"
        value["messages"].append(second)
        payload = self.payload(value)
        payload["entry"].extend(self.payload(self.value("other-phone", message_id="three"))["entry"])
        for _ in range(2):
            response = self.post(payload, signed=True)
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(set(BotMessage.objects.values_list("external_message_id", flat=True)), {"one", "two", "three"})
        self.assertEqual(BusinessEvent.objects.filter(event_type="message.received").count(), 3)

    def test_mixed_status_and_message_are_both_processed(self):
        outbound = self.outbound(self.bot)
        value = self.value(message_id="incoming")
        value.update(self.value(status=True))
        response = self.post(self.payload(value))
        self.assertEqual(response.status_code, 200, response.data)
        outbound.refresh_from_db()
        self.assertIsNotNone(outbound.read_at)
        self.assertTrue(BotMessage.objects.filter(external_message_id="incoming").exists())

    def test_invalid_later_message_rejects_before_any_effect(self):
        value = self.value()
        value["messages"].append({"id": "bad", "type": "text", "text": {"body": "bad"}})
        response = self.post(self.payload(value))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BotMessage.objects.exists())

    def test_contacts_are_matched_to_each_sender(self):
        value = self.value()
        value["contacts"] = [{"wa_id": "another", "profile": {"name": "Wrong"}}, {"wa_id": "synthetic-sender", "profile": {"name": "Correct"}}]
        self.assertEqual(self.post(self.payload(value)).status_code, 200)
        self.assertEqual(BotMessage.objects.get().payload_json["whatsapp_sender_name"], "Correct")

    def test_malformed_later_status_rejects_whole_packet(self):
        for malformed in ["bad", [None], [{"value": "bad"}]]:
            with self.subTest(malformed=malformed):
                value = self.value()
                value["statuses"] = malformed
                if malformed == [{"value": "bad"}]:
                    value["messages"][0]["text"] = []
                response = self.post(self.payload(value))
                self.assertEqual(response.status_code, 400)
                self.assertFalse(BotMessage.objects.exists())

    def test_unsupported_media_does_not_silently_acknowledge_other_messages(self):
        value = self.value()
        value["messages"].append({"id": "audio", "from": "synthetic-sender", "type": "audio", "audio": {"id": "media"}})
        response = self.post(self.payload(value))
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BotMessage.objects.exists())
