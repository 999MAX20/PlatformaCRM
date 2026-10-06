from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.ai_core.conversation_state import assert_current_turn, cancel_turn, reset_memory, retry_turn, start_turn
from apps.ai_core.models import AgentTurn, AIJob, AIToolCallLog, ApprovalRequest
from apps.ai_core import tests_conversation_memory as fixtures
from apps.core.domain_errors import IdempotencyConflict


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True)
class ConversationStateTests(TestCase):
    setUp = fixtures.ConversationMemoryTests.setUp

    def start(self, key="request", message="Создай задачу", **kwargs):
        return start_turn(conversation_id=self.thread.pk, user=self.owner, message=message, idempotency_key=key, **kwargs)

    def test_duplicate_request_reuses_turn_and_does_not_dispatch_another_job(self):
        turn, job = self.start()
        duplicate, second_job = self.start()
        self.assertEqual(turn.pk, duplicate.pk)
        self.assertIsNone(second_job)
        self.assertEqual(AIJob.objects.count(), 1)
        self.assertEqual(job.max_attempts, 1)
        with self.assertRaises(IdempotencyConflict):
            self.start(message="Другой запрос")
        with self.assertRaises(IdempotencyConflict):
            self.start(key="second")

    def test_cancel_rejects_proposal_approval_and_late_job(self):
        turn, job = self.start()
        turn.status = "awaiting_confirmation"
        turn.save()
        log = AIToolCallLog.objects.create(business=self.business, user=self.owner, tool_name="crm_create")
        turn.tool_calls.add(log)
        approval = ApprovalRequest.objects.create(business=self.business, requested_by=self.owner,
            action_type="ai_pipeline", ai_tool_call_log=log)
        cancel_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner)
        for record in (turn, job, log, approval):
            record.refresh_from_db()
        self.assertEqual(turn.status, "cancelled")
        self.assertEqual(job.status, "failed")
        self.assertEqual(log.status, "rejected")
        self.assertEqual(approval.status, "rejected")
        self.thread.refresh_from_db()
        with self.assertRaises(PermissionDenied):
            assert_current_turn(self.thread, turn)

    def test_new_message_replaces_unconfirmed_action_and_advances_revision(self):
        turn, _ = self.start()
        turn.status = "clarifying"
        turn.context_json = {"question": "Как назвать задачу?"}
        turn.save()
        newer, _ = self.start(key="answer", message="Позвонить клиенту")
        turn.refresh_from_db()
        self.assertEqual(turn.status, "superseded")
        self.assertEqual(newer.sequence, turn.sequence + 1)

    def test_reset_preserves_history_but_revokes_inflight_result(self):
        turn, _ = self.start()
        reset_memory(conversation_id=self.thread.pk, user=self.owner)
        self.thread.refresh_from_db()
        turn.refresh_from_db()
        self.assertEqual(self.thread.memory_epoch, 1)
        self.assertEqual(self.thread.turns.count(), 1)
        with self.assertRaises(PermissionDenied):
            assert_current_turn(self.thread, turn)

    def test_explicit_retry_is_idempotent_and_never_automatic(self):
        turn, job = self.start()
        turn.status = "failed"
        turn.save()
        job.status = "failed"
        job.save()
        retried, second_job = retry_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner, idempotency_key="retry-once")
        again, third_job = retry_turn(conversation_id=self.thread.pk, turn_id=turn.pk, user=self.owner, idempotency_key="retry-once")
        self.assertEqual(retried.pk, again.pk)
        self.assertIsNone(third_job)
        self.assertEqual(second_job.max_attempts, 1)
        self.assertEqual(AIJob.objects.count(), 2)

    def test_abandoned_provider_request_requires_explicit_new_request(self):
        turn, _ = self.start()
        AgentTurn.objects.filter(pk=turn.pk).update(updated_at=timezone.now() - timezone.timedelta(hours=1))
        newer, job = self.start(key="new", message="Попробуй ещё раз")
        turn.refresh_from_db()
        self.assertEqual(turn.status, "failed")
        self.assertEqual(turn.error_code, "interrupted")
        self.assertNotEqual(newer.pk, turn.pk)
        self.assertEqual(job.max_attempts, 1)
