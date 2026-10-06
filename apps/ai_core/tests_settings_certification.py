"""Saved editor settings must reach the real Inbox/CRM provider boundary."""
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.ai_core import tests as fixtures
from apps.ai_core.ai_client import AIClientResult
from apps.ai_core.models import AgentProfile, BusinessKnowledgeItem
from apps.bots.lifecycle import create_bot, activate_bot
from apps.bots.models import BotChannel, BotConversation, BotMessage


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, CELERY_TASK_ALWAYS_EAGER=True)
class SettingsCertificationTests(TestCase):
    def setUp(self):
        fixtures.AICoreFoundationTests.setUp(self)
        self.api.force_authenticate(self.owner)

    def save_configuration(self, bot, profile, version):
        crm = bot.scenario == "crm"
        language, tone, model, temperature = (("en", "formal", "gpt-4.1", 0.1) if version == 1
                                              else ("kk", "friendly", "gpt-4o-mini", 0.8))
        response = self.api.put(f"/api/bots/{bot.pk}/configuration/", {
            "bot": {"name": f"VERSION_{version}", "default_language": language,
                    "settings_json": {"model": model, "temperature": temperature}},
            "profile": {"id": profile.pk, "name": f"VERSION_{version}", "language": language,
                "tone": tone, "role_description": f"ROLE_VERSION_{version}",
                "system_prompt": f"INSTRUCTION_VERSION_{version}",
                "rules_json": {"items": [f"RULE_VERSION_{version}"], **({"sources": ["tasks", "knowledge"], "analyst_enabled": True} if crm else {})},
                "escalation_rules_json": {"items": [f"HANDOFF_VERSION_{version}"]},
                "allowed_tools_json": {"tools": ["crm_read"] if crm else ["handoff_to_manager"]}},
        }, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        return language, tone, model, temperature

    def assert_provider_settings(self, generate, version, expected, *, inbox):
        language, tone, model, temperature = expected
        self.assertEqual(generate.call_args.kwargs["model"], model)
        self.assertEqual(generate.call_args.kwargs["temperature"], temperature)
        prompt = generate.call_args.args[0]
        self.assertIn(f"INSTRUCTION_VERSION_{version}", str(prompt))
        self.assertIn(f"ROLE_VERSION_{version}", str(prompt))
        self.assertIn(f"RULE_VERSION_{version}", str(prompt))
        self.assertIn(tone, str(prompt))
        self.assertIn("English" if language == "en" else "Kazakh", prompt.messages[0]["content"])
        for field in ("INSTRUCTION", "ROLE", "RULE"):
            self.assertIn(f"{field}_VERSION_{version}", prompt.messages[0]["content"])
        self.assertIn("Configuration cannot authorize invented facts", prompt.messages[0]["content"])
        if inbox:
            self.assertIn(f"HANDOFF_VERSION_{version}", str(prompt))
            self.assertNotIn("say 'от'", str(prompt))
            self.assertNotIn("explain them as 'от'", str(prompt))
            self.assertIn("Only prices explicitly supplied as price_from are minimum prices", str(prompt))
            self.assertIn("Other supplied prices retain their stated meaning", str(prompt))
        self.assertNotIn(f"INSTRUCTION_VERSION_{3-version}", str(prompt))
        self.assertIn("ONLY_THIS_AGENT_KNOWLEDGE", str(prompt))
        self.assertNotIn("UNCONNECTED_BUSINESS_KNOWLEDGE", str(prompt))

    def test_saved_inbox_settings_change_actual_inbox_suggestion_provider_input(self):
        bot = create_bot(validated_data={"business": self.business, "name": "Inbox"})
        profile = AgentProfile.objects.create(business=self.business, bot=bot, name=bot.name)
        BotChannel.objects.create(bot=bot, channel="website", status="active")
        BusinessKnowledgeItem.objects.create(business=self.business, bot=bot, title="Knowledge", content="ONLY_THIS_AGENT_KNOWLEDGE")
        BusinessKnowledgeItem.objects.create(business=self.business, title="Shared", content="UNCONNECTED_BUSINESS_KNOWLEDGE")
        activate_bot(bot=bot)
        conversation = BotConversation.objects.create(business=self.business, bot=bot, channel="website", external_user_id="synthetic-audit")
        BotMessage.objects.create(conversation=conversation, direction="inbound", text="What does this business offer?")
        for version in (1, 2):
            with self.subTest(version=version):
                expected = self.save_configuration(bot, profile, version)
                with patch("apps.ai_core.services.generate_text", return_value=AIClientResult("Synthetic reply", expected[2], provider="mock", is_mock=True)) as generate:
                    response = self.api.post(f"/api/inbox/conversations/{conversation.pk}/suggest-reply/")
                self.assertEqual(response.status_code, 200, response.data)
                self.assert_provider_settings(generate, version, expected, inbox=True)
                self.assertFalse(conversation.messages.filter(direction="outbound").exists())

    def test_saved_crm_settings_change_actual_chat_provider_input(self):
        bot = create_bot(validated_data={"business": self.business, "name": "CRM", "scenario": "crm"})
        profile = AgentProfile.objects.get(bot=bot)
        BusinessKnowledgeItem.objects.create(business=self.business, bot=bot, title="Knowledge", content="ONLY_THIS_AGENT_KNOWLEDGE")
        BusinessKnowledgeItem.objects.create(business=self.business, title="Shared", content="UNCONNECTED_BUSINESS_KNOWLEDGE")
        activate_bot(bot=bot)
        for version in (1, 2):
            with self.subTest(version=version):
                expected = self.save_configuration(bot, profile, version)
                with patch("apps.ai_core.services.generate_text", return_value=AIClientResult("Synthetic grounded reply", expected[2], provider="mock", is_mock=True)) as generate:
                    response = self.api.post("/api/ai/assistant/chat/", {"business": self.business.pk, "agent": bot.pk, "message": "What needs attention?"}, format="json")
                self.assertIn(response.status_code, (200, 202), response.data)
                self.assert_provider_settings(generate, version, expected, inbox=False)

    def test_qualification_and_reply_share_selected_model_but_not_creativity(self):
        from apps.conversations.ai_qualification import qualify_conversation
        from apps.bots.ai import suggest_bot_reply
        bot = create_bot(validated_data={"business": self.business, "name": "Inbox"})
        profile = AgentProfile.objects.create(business=self.business, bot=bot, name=bot.name)
        self.save_configuration(bot, profile, 2)
        bot.refresh_from_db()
        conversation = BotConversation.objects.create(business=self.business, bot=bot, channel="website")
        BotMessage.objects.create(conversation=conversation, direction="inbound", text="Какая цена?")
        responses = [AIClientResult('{"intent":"price_question","summary":"Price request","requires_human_review":false}', "gpt-4o-mini"),
                     AIClientResult("Reply", "gpt-4o-mini")]
        with patch("apps.ai_core.services.generate_text", side_effect=responses) as generate:
            qualify_conversation(conversation=conversation)
            suggest_bot_reply(conversation=conversation)
        self.assertEqual([call.kwargs["model"] for call in generate.call_args_list], ["gpt-4o-mini", "gpt-4o-mini"])
        self.assertEqual([call.kwargs["temperature"] for call in generate.call_args_list], [0.2, 0.8])
        self.assertEqual(generate.call_args_list[0].args[0].response_format, {"type": "json_object"})
        self.assertFalse(hasattr(generate.call_args_list[1].args[0], "response_format"))

    def test_inflight_inbox_settings_change_rejects_late_response(self):
        from apps.bots.ai import suggest_bot_reply
        from rest_framework.exceptions import PermissionDenied
        bot = create_bot(validated_data={"business": self.business, "name": "Inbox"})
        profile = AgentProfile.objects.create(business=self.business, bot=bot, name=bot.name)
        conversation = BotConversation.objects.create(business=self.business, bot=bot, channel="website")
        BotMessage.objects.create(conversation=conversation, direction="inbound", text="Hello")
        def change_settings(*args, **kwargs):
            profile.is_active = False
            profile.save()
            return AIClientResult("Late answer", "test")
        with patch("apps.ai_core.services.generate_text", side_effect=change_settings), self.assertRaises(PermissionDenied):
            suggest_bot_reply(conversation=conversation)
