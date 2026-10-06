from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core import tests as fixtures
from apps.ai_core.agent_runtime import bind_agent
from apps.ai_core.ai_client import AIClientResult
from apps.ai_core.models import AgentProfile, AIJob
from apps.ai_core.services import create_ai_job, process_ai_job, run_ai_request
from apps.ai_core.tool_registry import suggest_tool_calls, assert_tool_execution_allowed
from apps.ai_core.workflows import workflow_settings
from apps.bots.lifecycle import create_bot, activate_bot, pause_bot
from apps.bots.models import Bot


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True)
class AgentRuntimeTests(TestCase):
    def setUp(self):
        fixtures.AICoreFoundationTests.setUp(self)
        self.agent = create_bot(validated_data={"business": self.business, "name": "CRM", "scenario": "crm"})
        self.profile = AgentProfile.objects.get(bot=self.agent)
        activate_bot(bot=self.agent)
        self.api.force_authenticate(self.owner)

    def test_explicit_agent_rejects_wrong_business_customer_and_unknown(self):
        customer = Bot.objects.create(business=self.business, name="Inbox")
        foreign = create_bot(validated_data={"business": self.other_business, "name": "Foreign", "scenario": "crm"})
        for agent in (customer.pk, foreign.pk, 999999):
            response = self.api.get("/api/ai/assistant/status/", {"business": self.business.pk, "agent": agent})
            self.assertEqual(response.status_code, 403, response.data)
        # The previous failed request must not leak its binding to this request.
        self.assertEqual(self.api.get("/api/ai/assistant/status/", {"business": self.business.pk, "agent": self.agent.pk}).status_code, 200)

    def test_own_sources_model_and_style_override_legacy_profile(self):
        AgentProfile.objects.create(business=self.business, name="Legacy", rules_json={"scenario": "employee"}, system_prompt="Legacy instruction")
        self.profile.rules_json = {"sources": ["tasks"], "analyst_enabled": False}
        self.profile.system_prompt = "Use the selected profile"
        self.profile.save()
        self.agent.settings_json.update(model="selected-model", temperature=0.15)
        self.agent.save()
        with bind_agent(self.agent.pk):
            config = workflow_settings(self.business, "employee")
            self.assertEqual(config["sources"], ["tasks"])
            self.assertFalse(workflow_settings(self.business, "analyst")["enabled"])
            with patch("apps.ai_core.services.generate_text", return_value=AIClientResult(output_text="Answer", model="selected-model", tokens_used=0, is_mock=True, provider="mock")) as generate:
                run_ai_request(business=self.business, user=self.owner, prompt_type="crm_assistant", user_input="Hello")
            self.assertEqual(generate.call_args.kwargs["model"], "selected-model")
        self.assertEqual(generate.call_args.kwargs["temperature"], 0.15)
        self.assertIn("Use the selected profile", str(generate.call_args.args[0]))

        response = self.api.get("/api/ai/assistant/status/", {"business": self.business.pk, "agent": self.agent.pk})
        self.assertEqual(response.data["sources"], ["tasks"])
        self.assertEqual(response.data["tools"], ["crm_read"])
        self.assertEqual(response.data["model"], "selected-model")

    def test_pause_blocks_explicit_and_business_level_runtime(self):
        pause_bot(bot=self.agent)
        for agent in ({"agent": self.agent.pk}, {}):
            response = self.api.get("/api/ai/assistant/status/", {"business": self.business.pk, **agent})
            self.assertFalse(response.data["ready"])
            response = self.api.get("/api/ai/crm/read/", {"business": self.business.pk, "entity": "tasks", **agent})
            self.assertEqual(response.status_code, 403)

    def test_command_binds_settings_and_revokes_old_confirmation(self):
        self.profile.allowed_tools_json = {"tools": ["crm_create"]}
        self.profile.save()
        with bind_agent(self.agent.pk):
            log = suggest_tool_calls(business=self.business, user=self.owner, tool_name="crm_create", arguments={"entity": "tasks", "values": {"title": "Review"}})[0]
        self.assertEqual(log.input_json["_agent"]["agent_id"], self.agent.pk)
        assert_tool_execution_allowed(log, self.owner)
        self.profile.tone = "friendly"
        self.profile.save()
        with self.assertRaises(PermissionDenied):
            assert_tool_execution_allowed(log, self.owner)

    def test_queued_request_retains_agent_and_rejects_changed_configuration(self):
        with bind_agent(self.agent.pk), patch("apps.ai_core.tasks.process_ai_job_task.apply_async"):
            job, _ = create_ai_job(business=self.business, user=self.owner, prompt_type="crm_assistant", user_input="Hello")
        self.assertEqual(job.input_json["runtime_context"]["_agent"]["agent_id"], self.agent.pk)
        pause_bot(bot=self.agent)
        with patch("apps.ai_core.services.generate_text") as generate:
            completed = process_ai_job(job.pk)
        self.assertEqual(completed.status, AIJob.Statuses.FAILED)
        generate.assert_not_called()

    def test_runtime_directory_omits_configuration_and_other_business(self):
        response = self.api.get("/api/ai/agents/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data], [self.agent.pk])
        self.assertNotIn("settings_json", response.data[0])
        self.assertEqual(self.api.get("/api/ai/agents/", {"business": self.other_business.pk}).status_code, 403)

    def test_queued_request_uses_its_saved_agent_and_resets_context(self):
        self.agent.settings_json.update(model="queue-model", temperature=0.2)
        self.agent.save()
        with bind_agent(self.agent.pk), patch("apps.ai_core.tasks.process_ai_job_task.apply_async"):
            job, _ = create_ai_job(business=self.business, user=self.owner, prompt_type="crm_assistant", user_input="Hello", idempotency_key="bound-job")
            replay, created = create_ai_job(business=self.business, user=self.owner, prompt_type="crm_assistant", user_input="Hello", idempotency_key="bound-job")
            self.assertEqual(replay.pk, job.pk)
            self.assertFalse(created)
        with patch("apps.ai_core.services.generate_text", return_value=AIClientResult(output_text="Answer", model="queue-model", tokens_used=0, is_mock=True, provider="mock")) as generate:
            completed = process_ai_job(job.pk)
        self.assertEqual(completed.status, AIJob.Statuses.SUCCEEDED)
        self.assertEqual(generate.call_args.kwargs["model"], "queue-model")
        self.assertEqual(completed.request_log.input_json["_agent"]["agent_id"], self.agent.pk)
        self.assertTrue(workflow_settings(self.other_business, "employee")["enabled"])

    def test_api_sources_analytics_and_command_metadata_cannot_be_bypassed(self):
        self.profile.rules_json = {"sources": ["tasks"], "analyst_enabled": False}
        self.profile.allowed_tools_json = {"tools": ["crm_read", "crm_create"]}
        self.profile.save()
        read = self.api.get("/api/ai/crm/read/", {"business": self.business.pk, "agent": self.agent.pk, "entity": "clients"})
        self.assertEqual(read.status_code, 403)
        history = self.api.get("/api/ai/analyst/history/", {"business": self.business.pk, "agent": self.agent.pk, "start": "2026-01-01", "end": "2026-01-31"})
        self.assertEqual(history.status_code, 403)
        forged = self.api.post("/api/ai/tools/suggest/", {"business": self.business.pk, "agent": self.agent.pk, "tool_name": "crm_create",
            "arguments": {"entity": "tasks", "values": {"title": "Untrusted"}, "_agent": {"agent_id": 999999}}}, format="json")
        self.assertEqual(forged.status_code, 400)
