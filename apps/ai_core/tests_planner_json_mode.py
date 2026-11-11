import io
import json
from unittest.mock import patch

from django.test import SimpleTestCase, TestCase, override_settings

from apps.ai_core import tests as fixtures
from apps.ai_core.conversation_access import create_voice_conversation
from apps.ai_core.conversation_state import start_turn
from apps.ai_core.models import AIToolCallLog
from apps.ai_core.runtime_policy import generation_policy
from apps.ai_core.services import process_ai_job
from apps.clients.models import Client


@override_settings(AI_DEFAULT_MODEL_TIER="fast", AI_FAST_MODEL="openai/gpt-4o-mini",
                   AI_SMART_MODEL="openai/gpt-4.1", AI_PROMPT_MODEL_TIERS='{"crm_action_plan":"smart"}')
class PlannerModelSelectionTests(SimpleTestCase):
    def test_resolved_default_and_prompt_tiers_enable_json(self):
        for stage, model in (("agent_turn_plan", "openai/gpt-4o-mini"), ("crm_action_plan", "openai/gpt-4.1")):
            with self.subTest(stage=stage):
                policy = generation_policy(prompt_type=stage)
                self.assertEqual(policy.model, model)
                self.assertTrue(policy.json_output)

    def test_explicit_tier_model_and_unknown_capabilities_preserve_precedence(self):
        policy = generation_policy(prompt_type="crm_action_plan", model_tier="fast")
        self.assertEqual(policy.model, "openai/gpt-4o-mini")
        self.assertTrue(policy.json_output)
        policy = generation_policy(prompt_type="crm_action_plan", model="custom/model", model_tier="smart")
        self.assertEqual(policy.model, "custom/model")
        self.assertFalse(policy.json_output)
        self.assertFalse(generation_policy(prompt_type="plain_text").json_output)


@override_settings(AI_PROVIDER="openrouter", AI_ENABLED=True, VOICE_INPUT_ENABLED=True,
    AI_QUEUE_LIVE_REQUESTS=False, OPENROUTER_API_KEY="synthetic-test-key",
    OPENROUTER_BASE_URL="https://openrouter.ai/api/v1", AI_DEFAULT_MODEL_TIER="fast",
    AI_FAST_MODEL="openai/gpt-4o-mini", AI_PROMPT_MODEL_TIERS="{}")
class VoicePlannerWireTests(TestCase):
    setUp = fixtures.AICoreFoundationTests.setUp

    def run_plan(self, plan):
        thread = create_voice_conversation(business=self.business, user=self.owner)
        turn, job = start_turn(conversation_id=thread.pk, user=self.owner,
            message="Создай клиента Мария Соколова, телефон +77012345678",
            idempotency_key="client", context={"execution": "direct"})
        route = {"intent": "actions", "question": "", "steps": [{"entity": "clients",
            "operation": "create", "target_id": None, "query": "", "request": turn.message,
            "after": None}], "period": None, "read": None}
        responses = [io.BytesIO(json.dumps({"choices": [{"message": {"content": content}}]}).encode())
                     for content in (json.dumps(route), plan)]
        with patch("apps.ai_core.providers.compatible.request.urlopen", side_effect=responses) as send:
            process_ai_job(job.pk)
        self.assertEqual(send.call_count, 2)
        for call in send.call_args_list:
            payload = json.loads(call.args[0].data)
            self.assertEqual(payload["model"], "openai/gpt-4o-mini")
            self.assertEqual(payload["response_format"], {"type": "json_object"})
        turn.refresh_from_db()
        replay, next_job = start_turn(conversation_id=thread.pk, user=self.owner,
            message=turn.message, idempotency_key="client", context={"execution": "direct"})
        self.assertEqual(replay.pk, turn.pk)
        self.assertIsNone(next_job)
        return turn

    def test_default_voice_route_and_field_plan_use_json_and_execute_once(self):
        plan = {"tool": "crm_create", "arguments": {"entity": "clients",
            "values": {"full_name": "Мария Соколова", "phone": "+77012345678"}}, "question": ""}
        turn = self.run_plan(json.dumps(plan))
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Client.objects.get().phone, "+77012345678")
        self.assertEqual(Client.objects.get().full_name, "Мария Соколова")

    def test_captured_malformed_json_remains_rejected_without_partial_write(self):
        turn = self.run_plan('{"tool":"crm_create","arguments":{"entity":"clients",'
            '"values":{"full_name":"Мария Соколова","phone":"+77012345678"}},{"question":""}}')
        self.assertEqual(turn.status, "failed")
        self.assertFalse(Client.objects.exists())
        self.assertFalse(AIToolCallLog.objects.exists())
