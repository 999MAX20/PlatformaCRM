from unittest.mock import patch

from django.db import IntegrityError, transaction
from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core import tests as foundation
from apps.ai_core.conversation_access import create_voice_conversation, staff_conversation
from apps.ai_core.models import AgentConversation
from apps.bots.models import Bot


@override_settings(AI_ENABLED=True, VOICE_INPUT_ENABLED=True, OPENROUTER_API_KEY="test-only",
                   OPENROUTER_BASE_URL="https://openrouter.ai/api/v1")
class VoiceInterfaceAccessTests(TestCase):
    setUp = foundation.AICoreFoundationTests.setUp

    def test_readiness_and_private_thread_require_no_bot(self):
        self.api.force_authenticate(self.owner)
        response = self.api.get("/api/ai/speech/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ready"])
        self.assertNotIn("agent", response.data)
        response = self.api.post("/api/ai/conversations/", {"business": self.business.pk, "kind": "voice"})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data["agent"])
        self.assertEqual(response.data["kind"], "voice")
        self.assertFalse(Bot.all_objects.exists())
        detail = self.api.get(f'/api/ai/conversations/{response.data["id"]}/')
        self.assertEqual(detail.status_code, 200)

    def test_voice_scope_rejects_agent_and_foreign_business(self):
        self.api.force_authenticate(self.owner)
        for values, status in (({"agent": 1}, 400), ({"mode": "analytics"}, 400),
                               ({"business": self.other_business.pk}, 403)):
            response = self.api.post("/api/ai/conversations/", {"business": self.business.pk, "kind": "voice", **values})
            self.assertEqual(response.status_code, status, response.data)
        self.assertFalse(AgentConversation.objects.exists())

    def test_history_is_private_and_disabled_account_denied(self):
        thread = create_voice_conversation(business=self.business, user=self.owner)
        self.api.force_authenticate(self.other_owner)
        self.assertEqual(self.api.get(f"/api/ai/conversations/{thread.pk}/").status_code, 404)
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            staff_conversation(conversation_id=thread.pk, user=self.owner)

    def test_database_rejects_staff_without_agent_and_voice_with_agent(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            AgentConversation.objects.create(business=self.business, owner=self.owner, kind="staff")
        bot = Bot.objects.create(business=self.business, name="Paused", status="paused", settings_json={"scenario": "crm"})
        with self.assertRaises(IntegrityError), transaction.atomic():
            AgentConversation.objects.create(business=self.business, owner=self.owner, kind="voice", agent=bot)

    def test_paused_agent_has_no_effect_on_speech(self):
        Bot.objects.create(business=self.business, name="Paused", status="paused", settings_json={"scenario": "crm"})
        self.api.force_authenticate(self.owner)
        response = self.api.get("/api/ai/speech/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ready"])
        self.assertIsNone(create_voice_conversation(business=self.business, user=self.owner).agent_id)


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceInterfaceExecutionTests(TestCase):
    def setUp(self):
        foundation.AICoreFoundationTests.setUp(self)
        self.thread = create_voice_conversation(business=self.business, user=self.owner)

    def prepare(self, *, key="initial", context=None, message="Create Call task"):
        from apps.ai_core.conversation_state import start_turn
        from apps.ai_core.services import process_ai_job
        from apps.ai_core.tests_conversation_execution import action_route, create_step, create_plan
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message=message,
                               idempotency_key=key, context=context)
        with patch("apps.ai_core.services.generate_text", side_effect=[action_route(create_step()), create_plan(title="Call")]) as generate:
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        return turn, job, generate

    def confirm(self, turn):
        from apps.ai_core.conversation_actions import confirm_turn
        from apps.ai_core.tool_registry import tool_call_fingerprint
        return confirm_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner,
            expected_revision=turn.sequence, actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)} for log in turn.tool_calls.all()])

    def test_no_agent_prepare_confirm_replay_and_history(self):
        from apps.tasks.models import Task
        from apps.ai_core.services import process_ai_job
        turn, job, _ = self.prepare(context={"origin": "text"})
        self.assertEqual(turn.context_json["origin"], "voice")
        self.assertFalse(Task.objects.exists())
        self.assertEqual(job.input_json["runtime_context"]["_agent"]["runtime"], "interface_voice")
        self.assertEqual(turn.tool_calls.get().input_json["_agent"]["runtime"], "interface_voice")
        self.confirm(turn)
        self.confirm(turn)
        process_ai_job(job.pk)
        self.assertEqual(Task.objects.count(), 1)
        self.assertFalse(Bot.all_objects.exists())
        self.api.force_authenticate(self.owner)
        result = self.api.get(f"/api/ai/conversations/{self.thread.pk}/")
        self.assertEqual(result.status_code, 200)
        self.assertFalse(result.data["turns"][0]["redacted"])

    def test_agent_added_paused_or_deleted_after_prepare_cannot_change_voice(self):
        from apps.ai_core.models import AgentProfile, BusinessKnowledgeItem
        from apps.tasks.models import Task
        turn, _, _ = self.prepare()
        bot = Bot.objects.create(business=self.business, name="Paused", status="paused",
                                 settings_json={"scenario": "crm", "model": "unrelated-model", "_deleted_at": "2026-11-05"})
        AgentProfile.objects.create(business=self.business, bot=bot, name="Disabled", is_active=False,
                                    system_prompt="UNRELATED_PRIVATE_INSTRUCTIONS")
        BusinessKnowledgeItem.objects.create(business=self.business, bot=bot, title="Secret", content="UNRELATED_PRIVATE_KNOWLEDGE")
        self.confirm(turn)
        self.assertEqual(Task.objects.count(), 1)
        _, _, generate = self.prepare(key="second")
        self.assertNotIn("UNRELATED_PRIVATE", str(generate.call_args_list))
        self.assertNotIn("unrelated-model", str(generate.call_args_list))

    def test_voice_policy_cannot_be_disabled_by_omitting_origin(self):
        from apps.ai_core.conversation_state import start_turn
        from apps.ai_core.services import process_ai_job
        from apps.ai_core.tests_conversation_execution import action_route, create_step
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message="Delete a client", idempotency_key="unsafe")
        with patch("apps.ai_core.services.generate_text", return_value=action_route({**create_step("clients"), "operation": "archive"})):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        self.assertEqual(turn.status, "failed")
        self.assertFalse(turn.tool_calls.exists())

    def test_revocation_and_voice_disable_prevent_confirm(self):
        from apps.tasks.models import Task
        turn, _, _ = self.prepare()
        with override_settings(VOICE_INPUT_ENABLED=False), self.assertRaises(PermissionDenied):
            self.confirm(turn)
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            self.confirm(turn)
        self.assertFalse(Task.objects.exists())

    def test_confirmation_rolls_back_domain_changes_on_audit_failure(self):
        from apps.tasks.models import Task
        turn, _, _ = self.prepare()
        with patch("apps.ai_core.conversation_actions.audit_ai_tool_execution", side_effect=RuntimeError("test rollback")):
            with self.assertRaises(RuntimeError):
                self.confirm(turn)
        self.assertFalse(Task.objects.exists())
        turn.refresh_from_db()
        self.assertEqual(turn.status, "awaiting_confirmation")
        self.confirm(turn)
        self.assertEqual(Task.objects.count(), 1)
