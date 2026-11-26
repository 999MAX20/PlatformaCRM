from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.exceptions import PermissionDenied

from apps.ai_core import tests as foundation
from apps.ai_core.conversation_access import create_voice_conversation
from apps.ai_core.conversation_actions import confirm_turn
from apps.ai_core.conversation_state import start_turn
from apps.ai_core.services import process_ai_job
from apps.ai_core.tests_conversation_execution import action_route, create_step, output
from apps.ai_core.tool_registry import tool_call_fingerprint
from apps.tasks.models import Task


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, VOICE_INPUT_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class VoiceTaskTransitionTests(TestCase):
    def setUp(self):
        foundation.AICoreFoundationTests.setUp(self)
        self.thread = create_voice_conversation(business=self.business, user=self.owner)
        self.task = Task.objects.create(business=self.business, title="Call supplier")

    def prepare(self, action="complete", reason=""):
        message = f"{action} task #{self.task.pk}" + (f": {reason}" if reason else "")
        step = {**create_step(), "operation": "transition", "target_id": self.task.pk, "request": message}
        proposal = output({"tool": "crm_transition", "arguments": {
            "entity": "tasks", "entity_id": self.task.pk, "action": action,
            "values": {}, "reason": reason}, "question": ""})
        turn, job = start_turn(conversation_id=self.thread.pk, user=self.owner, message=message,
            idempotency_key="task-transition", context={"execution": "direct"})
        with patch("apps.ai_core.services.generate_text", side_effect=[action_route(step), proposal]):
            process_ai_job(job.pk)
        turn.refresh_from_db()
        return turn

    def confirm(self, turn):
        return confirm_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner,
            expected_revision=turn.sequence, actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}
                for log in turn.tool_calls.all()])[0]

    def test_completion_requires_review_and_replay_preserves_completion(self):
        turn = self.prepare()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.assertEqual(turn.tool_calls.get().input_json["before"]["title"], self.task.title)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")
        turn = self.confirm(turn)
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "done")
        self.assertEqual(self.task.completed_by, self.owner)
        completed_at = self.task.completed_at
        self.confirm(turn)
        self.task.refresh_from_db()
        self.assertEqual(self.task.completed_at, completed_at)

    def test_cancellation_preserves_reason_and_requires_review(self):
        turn = self.prepare("cancel", "No longer needed")
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")
        turn = self.confirm(turn)
        self.assertEqual(turn.status, "completed", turn.error_code)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "cancelled")
        self.assertEqual(self.task.cancel_reason, "No longer needed")

    def test_direct_confirmation_cannot_bypass_review(self):
        turn = self.prepare()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        log = turn.tool_calls.get()
        with self.assertRaises(PermissionDenied):
            confirm_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner,
                expected_revision=turn.sequence, _direct=True,
                actions=[{"id": log.pk, "fingerprint": tool_call_fingerprint(log)}])
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")

    def test_missing_cancel_reason_does_not_propose_or_write(self):
        turn = self.prepare("cancel")
        self.assertNotEqual(turn.status, "awaiting_confirmation")
        self.assertFalse(turn.tool_calls.exists())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")

    def test_other_task_transitions_remain_unavailable(self):
        from apps.ai_core.voice_policy import validate_voice_proposal
        for action in ("start", "reopen", "assign", "delete"):
            with self.subTest(action=action), self.assertRaises(PermissionDenied):
                validate_voice_proposal({"origin": "voice"}, "crm_transition",
                    {"entity": "tasks", "action": action})

    def test_foreign_task_does_not_prepare_or_write(self):
        self.task = Task.objects.create(business=self.other_business, title="Foreign task")
        turn = self.prepare()
        self.assertNotEqual(turn.status, "awaiting_confirmation")
        self.assertFalse(turn.tool_calls.exists())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")

    def test_changed_task_cannot_execute_stale_review(self):
        turn = self.prepare()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.task.title = "Changed independently"
        self.task.save(update_fields=["title", "updated_at"])
        turn = self.confirm(turn)
        self.assertEqual(turn.status, "failed")
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")

    def test_audit_failure_rolls_back_task_and_approval(self):
        from apps.ai_core.models import ApprovalRequest
        turn = self.prepare()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        with patch("apps.ai_core.conversation_actions.audit_ai_tool_execution", side_effect=RuntimeError("test rollback")):
            with self.assertRaises(RuntimeError):
                self.confirm(turn)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")
        self.assertIsNone(self.task.completed_at)
        self.assertFalse(ApprovalRequest.objects.exists())

    def test_revoked_actor_cannot_confirm(self):
        turn = self.prepare()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            self.confirm(turn)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")

    def limited_actor(self, *, update=True, approve=True):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        user = User.objects.create_user(username="formy-limited", password="pass", role="staff")
        role = BusinessRole.objects.create(business=self.business, name="Formy task reviewer")
        for resource, action, allowed in (("ai_assistant", "suggest", True),
                ("ai_pipeline", "suggest", True), ("ai_pipeline", "approve", approve),
                ("ai_pipeline", "execute", True), ("tasks", "view", True), ("tasks", "update", update)):
            RolePermission.objects.create(business_role=role, resource=resource, action=action,
                scope="business" if allowed else "none", is_allowed=allowed)
        BusinessMember.objects.create(business=self.business, user=user, role="specialist", business_role=role)
        self.owner = user
        self.thread = create_voice_conversation(business=self.business, user=user)

    def test_task_update_permission_is_required(self):
        self.limited_actor(update=False)
        turn = self.prepare()
        self.assertNotEqual(turn.status, "awaiting_confirmation")
        self.assertFalse(turn.tool_calls.exists())
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")

    def test_approval_permission_is_required(self):
        self.limited_actor(approve=False)
        turn = self.prepare()
        self.assertEqual(turn.status, "awaiting_confirmation", turn.error_code)
        with self.assertRaises(PermissionDenied):
            self.confirm(turn)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")
