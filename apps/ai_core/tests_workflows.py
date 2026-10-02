from unittest.mock import patch
from django.test import TestCase
from rest_framework.exceptions import PermissionDenied
from apps.ai_core import tests as fixtures
from apps.ai_core.models import AgentProfile, AIToolCallLog
from apps.ai_core.assistant import build_crm_context
from apps.ai_core.tool_registry import suggest_tool_calls, assert_tool_execution_allowed
from apps.ai_core.serializers import AgentProfileSerializer
from apps.bots.ai import get_agent_profile
from apps.bots.models import Bot, BotConversation
from apps.ai_core.services import run_ai_request
from apps.ai_core.ai_client import AIClientResult


class InternalWorkflowTests(TestCase):
    def setUp(self):
        fixtures.AICoreFoundationTests.setUp(self)
        self.profile = AgentProfile.objects.create(business=self.business, name="Staff", rules_json={"scenario": "employee", "sources": ["tasks"]}, allowed_tools_json={"tools": ["create_task"]})

    def test_sources_and_disabled_workflow_are_enforced(self):
        context = build_crm_context(self.business, user=self.owner)
        self.assertNotIn("clients_count", context["summary"])
        self.assertNotIn("latest_leads", context)
        self.assertIn("tasks", context)
        self.profile.is_active = False; self.profile.save()
        with self.assertRaises(PermissionDenied):
            build_crm_context(self.business, user=self.owner)

    def test_capabilities_rechecked_after_suggestion(self):
        logs = suggest_tool_calls(business=self.business, user=self.owner, message="Follow up")
        self.assertEqual([log.tool_name for log in logs], ["create_task"])
        self.profile.allowed_tools_json = {"tools": []}; self.profile.save()
        with self.assertRaises(PermissionDenied):
            assert_tool_execution_allowed(logs[0], self.owner)

    def test_internal_profile_never_becomes_messenger_fallback(self):
        bot = Bot.objects.create(business=self.business, name="Messenger")
        conversation = BotConversation.objects.create(business=self.business, bot=bot, channel="website")
        self.assertIsNone(get_agent_profile(conversation))
        fallback = AgentProfile.objects.create(business=self.business, name="Legacy", rules_json=["Keep legacy rules"])
        self.assertEqual(get_agent_profile(conversation).id, fallback.id)

    def test_invalid_scenario_and_analyst_mutation_are_rejected(self):
        for rules, tools in [({"scenario": "unknown"}, []), ({"scenario": "analyst"}, ["create_task"]), ({"scenario": "employee", "sources": ["foreign"]}, [])]:
            data = {"business": self.business.id, "name": "Invalid", "rules_json": rules, "allowed_tools_json": {"tools": tools}}
            self.assertFalse(AgentProfileSerializer(data=data).is_valid())

    def test_stale_internal_reply_is_not_returned(self):
        def generate(*args, **kwargs):
            self.profile.is_active = False; self.profile.save()
            return AIClientResult(output_text="Old answer", model="mock", tokens_used=0, is_mock=True, provider="mock")
        with patch("apps.ai_core.services.generate_text", side_effect=generate):
            with self.assertRaises(PermissionDenied):
                run_ai_request(business=self.business, user=self.owner, prompt_type="crm_assistant", user_input="Hello", input_json={"crm_context": {"summary": {}}})

    def test_disabled_status_matches_execution(self):
        self.profile.is_active = False; self.profile.save()
        self.api.force_authenticate(self.owner)
        response = self.api.get("/api/ai/assistant/status/", {"business": self.business.id})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["enabled"])
        self.assertFalse(response.data["ready"])
