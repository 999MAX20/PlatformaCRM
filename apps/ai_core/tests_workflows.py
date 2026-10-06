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
        self.agent = Bot.objects.create(business=self.business, name="Staff", status="active", settings_json={"scenario": "crm"})
        self.profile = AgentProfile.objects.create(business=self.business, bot=self.agent, name="Staff", rules_json={"sources": ["tasks"]}, allowed_tools_json={"tools": ["create_task"]})

    def test_sources_and_disabled_workflow_are_enforced(self):
        context = build_crm_context(self.business, user=self.owner)
        self.assertNotIn("clients_count", context["summary"])
        self.assertNotIn("latest_leads", context)
        self.assertIn("tasks", context)
        self.profile.is_active = False; self.profile.save()
        with self.assertRaises(PermissionDenied):
            build_crm_context(self.business, user=self.owner)

    def test_prompt_dates_are_converted_to_business_timezone_before_generation(self):
        from datetime import datetime, timedelta, timezone as utc_timezone
        from apps.tasks.models import Task
        from apps.clients.models import Client
        from apps.services.models import Service
        from apps.scheduling.models import Appointment
        self.business.timezone = "Asia/Almaty"
        self.business.save(update_fields=["timezone"])
        self.profile.rules_json = {"sources": ["tasks", "appointments"]}
        self.profile.save()
        start = datetime(2026, 10, 8, 10, tzinfo=utc_timezone.utc)
        task = Task.objects.create(business=self.business, title="Local deadline",
                                   due_at=start)
        client = Client.objects.create(business=self.business, full_name="Local client")
        service = Service.objects.create(business=self.business, name="Local service", duration_minutes=30)
        Appointment.objects.create(business=self.business, client=client, service=service,
                                   start_at=start, end_at=start+timedelta(minutes=30))
        with patch("django.utils.timezone.now", return_value=start-timedelta(days=1)):
            context = build_crm_context(self.business, user=self.owner)
        row = next(row for row in context["tasks"] if row["id"] == task.pk)
        self.assertEqual(row["due_at"], "2026-10-08T15:00:00+05:00")
        self.assertEqual(context["upcoming_appointments"][0]["start_at"], "2026-10-08T15:00:00+05:00")

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
        AgentProfile.objects.create(business=self.business, name="Legacy", rules_json=["Keep legacy rules"])
        self.assertIsNone(get_agent_profile(conversation))

    def test_invalid_scenario_and_analyst_mutation_are_rejected(self):
        for rules, tools in [({"scenario": "unknown"}, []), ({"scenario": "analyst"}, ["create_task"]), ({"scenario": "employee", "sources": ["foreign"]}, [])]:
            data = {"business": self.business.id, "name": "Invalid", "rules_json": rules, "allowed_tools_json": {"tools": tools}}
            self.assertFalse(AgentProfileSerializer(data=data).is_valid())

    def test_stale_internal_reply_is_not_returned(self):
        context = build_crm_context(self.business, user=self.owner)
        def generate(*args, **kwargs):
            self.profile.is_active = False; self.profile.save()
            return AIClientResult(output_text="Old answer", model="mock", tokens_used=0, is_mock=True, provider="mock")
        with patch("apps.ai_core.services.generate_text", side_effect=generate) as provider:
            with self.assertRaises(PermissionDenied):
                run_ai_request(business=self.business, user=self.owner, prompt_type="crm_assistant", user_input="Hello", input_json={"crm_context": context})
        provider.assert_called_once()

    def test_disabled_status_matches_execution(self):
        self.profile.is_active = False; self.profile.save()
        self.api.force_authenticate(self.owner)
        response = self.api.get("/api/ai/assistant/status/", {"business": self.business.id})
        self.assertEqual(response.status_code, 200)
        self.assertFalse(response.data["enabled"])
        self.assertFalse(response.data["ready"])
