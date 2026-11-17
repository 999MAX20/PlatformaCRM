import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.ai_core.ai_client import AIClientResult
from apps.ai_core.models import AgentProfile, BusinessKnowledgeItem
from apps.bots.customer_language import LANGUAGE_KEY, customer_reply_language, language_signal, remember_customer_language
from apps.bots.models import Bot, BotConversation, BotMessage
from apps.bots.safety_content import COPY, safety_text
from apps.businesses.models import Business
from apps.conversations.booking import format_booking_offer


class LanguageSignalTests(SimpleTestCase):
    def test_customer_language_and_explicit_switch(self):
        cases = {
            "Сәлеметсіз бе, бағасы қанша?": "kk",
            "Салем мен ертен жазылгым келеди": "kk",
            "Здравствуйте, сколько стоит услуга?": "ru",
            "Hello, how much does it cost?": "en",
            "Ответьте, пожалуйста, на казахском": "kk",
            "Қазақша емес, жауапты орыс тілінде жазыңыз": "ru",
            "Please reply in Kazakh": "kk",
            "Можно отвечать на английском?": "en",
            "Не отвечайте на русском, ответьте на казахском": "kk",
            'Есть ли запись к специалисту «Әлия»?': "ru",
            'How much is the service "Жазылу"?': "en",
        }
        for text, language in cases.items():
            with self.subTest(text=text):
                self.assertEqual(language_signal(text), language)

    def test_ambiguous_fragments_do_not_switch(self):
        for text in ("1", "+7 700 000 00 00", "👍", "да", "okay", "рахмет", "yes please", "1 вариант подходит", "12:30", "https://example.test/en", "> Answer in English"):
            with self.subTest(text=text):
                self.assertIsNone(language_signal(text))


@override_settings(AI_ENABLED=True, AI_PROVIDER="mock", CELERY_TASK_ALWAYS_EAGER=True)
class CustomerLanguageTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="customer-language")
        cls.business = Business.objects.create(owner=cls.owner, name="Language QA", slug="language-qa")
        cls.bot = Bot.objects.create(business=cls.business, name="Language QA", default_language="ru")
        cls.profile = AgentProfile.objects.create(business=cls.business, bot=cls.bot, name="QA", language="ru")
        BusinessKnowledgeItem.objects.create(business=cls.business, bot=cls.bot, customer_visible=True,
            title="Public facts", content="Consultation costs from 5000 KZT.")

    def setUp(self):
        self.conversation = BotConversation.objects.create(business=self.business, bot=self.bot, channel="website")

    def inbound(self, text):
        return BotMessage.objects.create(conversation=self.conversation, direction="inbound", text=text)

    def test_language_changes_and_short_replies_retain_history(self):
        for text, expected in (("Сәлеметсіз бе, жазылғым келеді", "kk"), ("1", "kk"),
                ("да", "kk"), ("+7 700 000 00 00", "kk"), ("Hello, what is the price?", "en"),
                ("👍", "en"), ("Сколько стоит услуга?", "ru")):
            self.inbound(text)
            self.assertEqual(customer_reply_language(self.conversation), expected)
            self.assertEqual(safety_text(self.conversation, "handoff"), COPY[expected]["handoff"])
            self.assertEqual(safety_text(self.conversation, "boundary"), COPY[expected]["boundary"])
            self.assertTrue(format_booking_offer(self.conversation, []).startswith({
                "ru": "Для записи", "kk": "Жазылу үшін", "en": "To book"}[expected]))

    def test_outbound_and_other_conversations_do_not_choose_language(self):
        self.inbound("Сәлем, бағасы қанша?")
        BotMessage.objects.create(conversation=self.conversation, direction="outbound", text="Please reply in English")
        other = BotConversation.objects.create(business=self.business, bot=self.bot, channel="website")
        BotMessage.objects.create(conversation=other, direction="inbound", text="Ответьте на русском")
        self.assertEqual(customer_reply_language(self.conversation), "kk")
        self.assertEqual(customer_reply_language(other), "ru")

    def test_profile_is_only_fallback_and_memory_reset_excludes_old_language(self):
        self.profile.language = "en"
        self.profile.save()
        self.inbound("123")
        self.assertEqual(customer_reply_language(self.conversation), "en")
        self.inbound("Қазақша жауап беріңіз")
        self.assertEqual(customer_reply_language(self.conversation), "kk")
        from apps.ai_core.conversation_access import inbox_memory_conversation
        thread = inbox_memory_conversation(self.conversation)
        thread.memory_since = timezone.now()
        thread.save()
        self.inbound("👍")
        self.assertEqual(customer_reply_language(self.conversation), "en")

    def test_model_language_checkpoint_survives_numeric_reply_and_rejects_late_result(self):
        first = self.inbound("Salem, ertenge jazylgym keledi")
        context = [{"id": first.pk, "direction": "inbound", "text": first.text}]
        remember_customer_language(self.conversation, context, "kk")
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.metadata_json[LANGUAGE_KEY]["language"], "kk")
        self.inbound("1")
        self.assertEqual(customer_reply_language(self.conversation), "kk")
        self.inbound("Hello, please tell me the price")
        self.assertEqual(remember_customer_language(self.conversation, context, "ru"), "en")
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.metadata_json[LANGUAGE_KEY]["message_id"], first.pk)
        self.assertEqual(customer_reply_language(self.conversation), "en")

    def test_preview_templates_share_customer_history_without_persisting(self):
        preview = BotConversation(business=self.business, bot=self.bot, channel="website")
        preview._preview_messages = [{"direction": "inbound", "text": "Сәлеметсіз бе"}, {"direction": "inbound", "text": "1"}]
        self.assertEqual(safety_text(preview, "handoff"), COPY["kk"]["handoff"])
        self.assertEqual(remember_customer_language(preview, preview._preview_messages, "en"), "kk")
        self.assertEqual(BotConversation.objects.count(), 1)

    def test_qualification_detected_language_reaches_model_reply(self):
        from apps.conversations.ai_qualification import qualify_conversation
        from apps.bots.ai import suggest_bot_reply
        self.inbound("Salem, konsultaciya bagasy kansha?")
        qualification_output = {"intent": "price_question", "request_kind": "business", "summary": "Price question",
            "confidence": 0.95, "response_language": "kk"}
        with patch("apps.ai_core.services.generate_text", side_effect=[
                AIClientResult(json.dumps(qualification_output), "test"), AIClientResult("Бағасы 5000 теңгеден басталады.", "test")]) as generate:
            qualification, _ = qualify_conversation(conversation=self.conversation)
            _, log, _, _ = suggest_bot_reply(conversation=self.conversation, qualification=qualification)
        self.assertEqual(qualification.response_language, "kk")
        self.assertEqual(log.input_json["ai_response_language"], "kk")
        self.assertIn("reply in Kazakh", generate.call_args.args[0].messages[0]["content"])
        self.assertNotIn("saved agent language takes precedence", generate.call_args.args[0].messages[0]["content"])

    def test_invalid_model_language_cannot_become_configuration(self):
        from apps.conversations.ai_qualification import qualification_from_payload
        self.inbound("Hello, what is the price?")
        for value in ("ignore rules", {}, ["kk"], None):
            result = qualification_from_payload({"response_language": value})
            self.assertEqual(result.response_language, "")
            self.assertEqual(remember_customer_language(self.conversation, [], value), "en")
        self.conversation.refresh_from_db()
        self.assertNotIn(LANGUAGE_KEY, self.conversation.metadata_json)
