import json
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.ai_core import tests_conversation_memory as fixtures
from apps.ai_core.ai_client import AIClientResult
from apps.ai_core.conversation_actions import confirm_turn
from apps.ai_core.conversation_state import cancel_turn, retry_turn, start_turn
from apps.ai_core.models import AgentProfile, AIToolCallLog
from apps.ai_core.services import process_ai_job
from apps.ai_core.tool_registry import tool_call_fingerprint
from apps.clients.models import Client
from apps.tasks.models import Task


def output(value):
    return AIClientResult(json.dumps(value), "test", provider="test")


def action_route(*steps):
    return output({"intent": "actions", "question": "", "steps": list(steps), "read": None, "period": None})


def create_step(entity="tasks", request="Create Call task", after=None):
    return {"entity": entity, "operation": "create", "target_id": None, "query": "", "request": request, "after": after}


def create_plan(entity="tasks", **values):
    return output({"tool": "crm_create", "arguments": {"entity": entity, "values": values}, "question": ""})


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class ConversationExecutionTests(TestCase):
    def setUp(self):
        fixtures.ConversationMemoryTests.setUp(self)
        profile = AgentProfile.objects.get(bot=self.agent)
        profile.allowed_tools_json = {"tools": ["crm_read", "crm_create", "crm_update", "crm_transition", "crm_archive", "crm_restore"]}
        profile.save()

    def prepare(self, responses, *, message="Create Call task"):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message=message, idempotency_key="initial")
        with patch("apps.ai_core.services.generate_text", side_effect=responses) as generate:
            process_ai_job(job.pk)
        turn.refresh_from_db()
        return turn, job, generate

    def confirm(self, turn, logs=None):
        logs = list(logs if logs is not None else turn.tool_calls.filter(status="suggested"))
        return confirm_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner,
            expected_revision=turn.sequence, actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)} for log in logs])

    def test_period_route_uses_historical_selector_instead_of_current_crm(self):
        from apps.ai_core.conversation_router import parse_route
        result = parse_route(json.dumps({"intent": "answer", "question": "", "steps": [], "read": None,
            "period": {"start": "2026-10-01", "end": "2026-10-07"}}), {"available_records": {}, "fresh_references": []})
        self.assertEqual(result["intent"], "analytics")

    def test_action_is_reviewed_then_executed_once_and_job_replay_is_read_only(self):
        turn, job, generate = self.prepare([action_route(create_step()), create_plan(title="Call")])
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.assertFalse(Task.objects.exists())
        self.assertEqual(turn.tool_calls.count(), 1)
        with patch("apps.ai_core.services.generate_text") as provider:
            process_ai_job(job.pk)
        provider.assert_not_called()
        log = turn.tool_calls.get()
        completed, next_job = self.confirm(turn, [log])
        self.assertEqual(completed.status, "completed")
        self.assertIsNone(next_job)
        self.assertEqual(Task.objects.get().title, "Call")
        self.confirm(completed, [log])
        self.assertEqual(Task.objects.count(), 1)

    def test_missing_title_asks_question_and_creates_no_command(self):
        turn, _, _ = self.prepare([action_route(create_step()), create_plan(title="")])
        self.assertEqual(turn.status, "clarifying", turn.error_code)
        self.assertTrue(turn.response)
        self.assertFalse(turn.tool_calls.exists())
        self.assertFalse(Task.objects.exists())

    def test_dependent_action_waits_for_actual_parent_result_and_new_confirmation(self):
        turn, _, _ = self.prepare([action_route(create_step("clients", "Create Mira"), create_step(request="Create Call task for that new client", after=0)),
                                  create_plan("clients", full_name="Mira")])
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.assertEqual(turn.tool_calls.count(), 1)
        turn, next_job = self.confirm(turn)
        self.assertEqual(turn.status, "preparing")
        client = Client.objects.get(full_name="Mira")
        self.assertFalse(Task.objects.exists())
        with patch("apps.ai_core.services.generate_text", return_value=create_plan(title="Call", client=client.pk)) as provider:
            process_ai_job(next_job.pk)
        self.assertEqual(provider.call_count, 1)
        self.assertIn("Mira", str(provider.call_args.args[0]))
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        turn, _ = self.confirm(turn)
        self.assertEqual(turn.status, "completed")
        self.assertEqual(Task.objects.get().client_id, client.pk)
        self.assertEqual(Client.objects.count(), 1)

    def test_partial_domain_failure_preserves_completed_step_and_retry_only_reprepares_failed_step(self):
        turn, _, _ = self.prepare([action_route(create_step(request="Create One"), create_step(request="Create Two")),
                                  create_plan(title="One"), create_plan(title="Two")])
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        from apps.ai_core.crm_writes import save_details
        calls = []
        def fail_second(serializer, **kwargs):
            calls.append(serializer.validated_data["title"])
            if len(calls) == 2:
                raise ValidationError("Temporary synthetic conflict")
            return save_details(serializer, **kwargs)
        with patch("apps.ai_core.crm_writes.save_details", side_effect=fail_second):
            turn, _ = self.confirm(turn)
        self.assertEqual(turn.status, "failed")
        self.assertEqual(list(Task.objects.values_list("title", flat=True)), ["One"])
        turn, job = retry_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner, idempotency_key="retry-partial")
        with patch("apps.ai_core.services.generate_text", return_value=create_plan(title="Two")) as provider:
            process_ai_job(job.pk)
        self.assertEqual(provider.call_count, 1)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        turn, _ = self.confirm(turn)
        self.assertEqual(turn.status, "completed")
        self.assertEqual(set(Task.objects.values_list("title", flat=True)), {"One", "Two"})
        self.assertEqual(Task.objects.count(), 2)

    def test_cancel_during_provider_call_prevents_next_call_and_late_proposal(self):
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message="Create task", idempotency_key="cancel-me")
        def cancel_while_responding(*args, **kwargs):
            cancel_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner)
            return action_route(create_step())
        with patch("apps.ai_core.services.generate_text", side_effect=cancel_while_responding) as provider:
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "cancelled")
        self.assertEqual(provider.call_count, 1)
        self.assertFalse(AIToolCallLog.objects.exists())
        self.assertFalse(Task.objects.exists())

    def test_invalid_router_shape_fails_without_mutation_or_automatic_retry(self):
        turn, job, generate = self.prepare([output({"intent": "actions", "steps": [{"entity": "tasks", "operation": "create", "request": "Unsafe", "after": 3}]})])
        self.assertEqual(turn.status, "failed")
        self.assertEqual(turn.error_code, "invalid_action_plan")
        job.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertEqual(job.attempts, 1)
        self.assertFalse(Task.objects.exists())
