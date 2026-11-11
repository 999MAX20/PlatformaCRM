from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.ai_core.models import AgentProfile, BusinessKnowledgeItem
from apps.bots import tests_readiness as fixtures
from apps.bots.lifecycle import get_bot_readiness, is_bot_runtime_ready, create_bot
from apps.bots.models import Bot, BotChannel, BotConversation


@override_settings(AI_ENABLED=True, AI_PROVIDER="mock")
class AgentReadinessDiagnosticsTests(TestCase):
    def setUp(self):
        fixtures.BotReadinessAPITests.setUp(self)
        self.profile = AgentProfile.objects.create(business=self.business, bot=self.bot, name="Profile")
        BotChannel.objects.create(bot=self.bot, channel="website", status="active")
        BusinessKnowledgeItem.objects.create(business=self.business, bot=self.bot, title="Public facts",
                                            content="Opening hours", customer_visible=True)

    def readiness(self):
        response = self.api.get(f"/api/bots/{self.bot.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        return response.data["readiness"]

    def test_mock_is_explicit_and_does_not_claim_live_verification(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("Readiness must not call providers")):
            state = self.readiness()
        self.assertTrue(state["is_ready"])
        self.assertTrue(state["configured_ready"])
        self.assertEqual(state["provider"]["state"], "mock")
        self.assertFalse(state["provider"]["live_verified"])

    def test_provider_missing_key_url_or_disabled_blocks_activation_and_runtime(self):
        for overrides, expected in (
            ({"AI_ENABLED": False}, "disabled"),
            ({"AI_PROVIDER": "openai", "OPENAI_API_KEY": ""}, "not_configured"),
            ({"AI_PROVIDER": "openai", "OPENAI_API_KEY": "private-value", "OPENAI_BASE_URL": ""}, "not_configured"),
            ({"AI_PROVIDER": "unknown-provider"}, "not_configured"),
        ):
            with self.subTest(overrides=list(overrides)), override_settings(**overrides):
                state = self.readiness()
                self.assertTrue(state["configured_ready"])
                self.assertFalse(state["is_ready"])
                self.assertEqual(state["provider"]["state"], expected)
                self.assertEqual(self.api.post(f"/api/bots/{self.bot.pk}/activate/").status_code, 409)
                self.bot.status = "active"
                self.assertFalse(is_bot_runtime_ready(self.bot))
                self.assertNotIn("private-value", str(state))
        self.assertEqual(self.api.post(f"/api/bots/{self.bot.pk}/activate/").status_code, 200)

    @override_settings(AI_PROVIDER="openrouter", OPENROUTER_API_KEY="private-token",
                       OPENROUTER_BASE_URL="https://provider.invalid/api", AI_DEFAULT_MODEL_TIER="fast",
                       AI_FAST_MODEL="vendor/fast", AI_SMART_MODEL="vendor/smart", AI_CHEAP_MODEL="vendor/cheap")
    def test_effective_model_and_options_match_generation_without_network(self):
        state = self.readiness()["provider"]
        self.assertEqual(state["state"], "configured")
        self.assertEqual(state["model"], "vendor/fast")
        self.assertEqual([item["value"] for item in state["model_options"]], ["vendor/smart", "vendor/fast", "vendor/cheap"])
        self.assertNotIn("private-token", str(state))
        self.assertNotIn("provider.invalid", str(state))
        self.bot.settings_json = {"model": "gpt-4.1"}
        self.bot.save()
        self.assertEqual(self.readiness()["provider"]["model"], "openai/gpt-4.1")

    @override_settings(AI_MODEL="", AI_FAST_MODEL="", AI_SMART_MODEL="", AI_CHEAP_MODEL="")
    def test_missing_model_is_not_ready(self):
        self.assertEqual(self.readiness()["provider"]["state"], "model_missing")
        self.assertFalse(self.readiness()["is_ready"])

    def enable_booking(self):
        self.profile.allowed_tools_json = {"tools": ["create_appointment"]}
        self.profile.save()
        self.bot.settings_json = {"auto_crm_pipeline": {"enabled": True, "mode": "lead_task",
            "creation_policy": "automatic", "create_appointment": True}}
        self.bot.save()

    def test_booking_warnings_do_not_disable_other_functions_and_clear_after_configuration(self):
        self.enable_booking()
        state = self.readiness()
        self.assertTrue(state["is_ready"])
        self.assertEqual(state["booking"]["missing"], ["responsible", "authorization"])
        self.business.ai_booking_responsible_user = self.owner
        self.business.save()
        self.bot.settings_json["_automatic_actor_id"] = self.owner.pk
        self.bot.save()
        self.assertTrue(self.readiness()["booking"]["setup_ready"])
        self.owner.is_active = False
        self.owner.save()
        # Service check: a revoked actor must be rechecked independently of API authentication.
        self.bot.refresh_from_db()
        self.assertEqual(get_bot_readiness(self.bot, include_diagnostics=True)["booking"]["missing"],
                         ["responsible", "authorization"])

    def test_foreign_booking_responsible_is_not_exposed(self):
        self.enable_booking()
        self.business.ai_booking_responsible_user = self.other_owner
        self.business.save()
        self.bot.refresh_from_db()
        state = get_bot_readiness(self.bot, include_diagnostics=True)
        self.assertIn("responsible", state["booking"]["missing"])
        self.assertNotIn(self.other_owner.email, str(state))

    def test_crm_directory_exposes_analytics_state_without_instructions(self):
        agent = create_bot(validated_data={"business": self.business, "name": "CRM", "scenario": "crm"})
        AgentProfile.objects.filter(bot=agent).update(rules_json={"analyst_enabled": False}, system_prompt="private instruction")
        response = self.api.get("/api/ai/agents/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertFalse(response.data[0]["readiness"]["analytics_enabled"])
        self.assertNotIn("private instruction", str(response.data))

    def test_other_business_diagnostics_remain_inaccessible(self):
        self.api.force_authenticate(self.other_owner)
        self.assertEqual(self.api.get(f"/api/bots/{self.bot.pk}/").status_code, 404)

    def test_agent_inbox_summary_counts_only_accessible_selected_agent(self):
        sibling = Bot.objects.create(business=self.business, name="Sibling")
        foreign = Bot.objects.create(business=self.other_business, name="Foreign")
        for bot in (self.bot, sibling, foreign):
            BotConversation.objects.create(business=bot.business, bot=bot, channel="website", handoff_required=True)
        response = self.api.get("/api/inbox/conversations/summary/", {"bot": self.bot.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 1)
        self.assertEqual(response.data["handoff_required"], 1)
        response = self.api.get("/api/inbox/conversations/summary/", {"bot": foreign.pk})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total"], 0)
