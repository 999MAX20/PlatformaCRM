import json
from unittest.mock import patch

from django.test import SimpleTestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.bots.outbound_delivery import retry_outbound_message
from apps.integrations.providers.base import ProviderConfigurationError
from apps.integrations import tests_meta_delivery as base_delivery
from apps.integrations.whatsapp.sandbox_recipients import meta_test_recipient


class MetaTestRecipientConfigurationTests(SimpleTestCase):
    @override_settings(WHATSAPP_META_TEST_RECIPIENT_ALIASES={})
    def test_default_preserves_all_recipients(self):
        for recipient in ("77015550101", "12025550101", "76125550101"):
            self.assertEqual(meta_test_recipient("test-sender", recipient), recipient)

    @override_settings(WHATSAPP_META_TEST_RECIPIENT_ALIASES={"test-sender": {"77015550101": "787015550101"}})
    def test_mapping_requires_both_sender_and_exact_recipient(self):
        self.assertEqual(meta_test_recipient("test-sender", "77015550101"), "787015550101")
        self.assertEqual(meta_test_recipient("live-sender", "77015550101"), "77015550101")
        self.assertEqual(meta_test_recipient("test-sender", "77015550102"), "77015550102")

    def test_configuration_cannot_forward_to_another_number(self):
        for aliases in ([], {"sender": []}, {"sender": {"77015550101": "787015550102"}},
                        {"sender": {"77015550101": None}}, {"sender": {"12025550101": "782025550101"}}):
            recipient = "12025550101" if isinstance(aliases, dict) and "12025550101" in aliases.get("sender", {}) else "77015550101"
            with self.subTest(aliases=aliases), self.settings(WHATSAPP_META_TEST_RECIPIENT_ALIASES=aliases):
                with self.assertRaises(ProviderConfigurationError):
                    meta_test_recipient("sender", recipient)


@override_settings(WHATSAPP_ENABLED=True, WHATSAPP_GRAPH_BASE_URL="https://graph.facebook.com", OUTBOUND_MESSAGES_RUN_INLINE=False)
class MetaTestRecipientDeliveryTests(TransactionTestCase):
    setUp = base_delivery.MetaDeliveryTests.setUp
    response = base_delivery.MetaDeliveryTests.response
    deliver = base_delivery.MetaDeliveryTests.deliver
    receipt = base_delivery.MetaDeliveryTests.receipt

    def mapping(self):
        phone_id = self.channel.config_json.get("phone_number_id") or self.channel.external_id
        return {str(phone_id): {"77015550101": "787015550101"}}

    def test_alias_send_keeps_canonical_conversation_and_receipt_identity(self):
        with self.settings(WHATSAPP_META_TEST_RECIPIENT_ALIASES=self.mapping()):
            http = self.deliver(result=self.response({"messages": [{"id": "wamid.sent"}],
                "contacts": [{"input": "787015550101", "wa_id": "77015550101"}]}))
        self.assertEqual(json.loads(http.call_args.args[0].data)["to"], "787015550101")
        self.assertEqual(self.message.status, "accepted")
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.external_user_id, "77015550101")
        self.receipt("delivered")
        self.message.refresh_from_db()
        self.assertIsNotNone(self.message.delivered_at)
        self.assertEqual(self.message.status, "sent")
        self.assertEqual(self.conversation.messages.filter(direction="outbound").count(), 1)

    def test_invalid_alias_is_rejected_before_any_provider_call(self):
        mapping = self.mapping()
        next(iter(mapping.values()))["77015550101"] = "787015550102"
        with self.settings(WHATSAPP_META_TEST_RECIPIENT_ALIASES=mapping):
            http = self.deliver()
        http.assert_not_called()
        self.assertEqual(self.message.status, "failed")
        self.assertIn("preserve", self.message.error_text)

    def test_unconfirmed_alias_acceptance_is_unknown_and_never_blindly_retried(self):
        for contacts in (None, [], [{"wa_id": "77015550102"}]):
            with self.subTest(contacts=contacts):
                self.message.status = "queued"
                self.message.payload_json = {"sent_by_user_id": self.owner.pk}
                self.message.save()
                with self.settings(WHATSAPP_META_TEST_RECIPIENT_ALIASES=self.mapping()):
                    self.deliver(result=self.response({"messages": [{"id": "wamid.sent"}], "contacts": contacts}))
                self.assertEqual(self.message.status, "delivery_unknown")
                with patch("apps.integrations.providers.whatsapp.urllib_request.urlopen") as http:
                    with self.assertRaises(ValidationError):
                        retry_outbound_message(self.message, actor=self.owner)
                http.assert_not_called()

    def test_other_sender_does_not_apply_mapping_or_require_alias_contacts(self):
        with self.settings(WHATSAPP_META_TEST_RECIPIENT_ALIASES={"another-sender": {"77015550101": "787015550101"}}):
            http = self.deliver()
        self.assertEqual(json.loads(http.call_args.args[0].data)["to"], "77015550101")
        self.assertEqual(self.message.status, "accepted")
