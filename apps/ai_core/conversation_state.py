"""Persisted conversation transitions; model calls never hold database locks."""
from contextlib import contextmanager
import hashlib
import json

from django.conf import settings
from django.db import connection, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.ai_core.agent_runtime import bind_agent
from apps.ai_core.conversation_access import memory_access_fingerprint, staff_conversation
from apps.ai_core.models import AgentConversation, AgentTurn, AIJob, AIToolCallLog, ApprovalRequest
from apps.ai_core.workflows import assert_workflow_enabled, workflow_fingerprint
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import IdempotencyConflict
from apps.core.models import AuditLog


RUNNING = (AgentTurn.Statuses.PREPARING, AgentTurn.Statuses.EXECUTING)
OPEN = RUNNING + (AgentTurn.Statuses.CLARIFYING, AgentTurn.Statuses.AWAITING_CONFIRMATION)


@contextmanager
def locked_conversation(conversation_id, user, *, write=True):
    # Keep the same Business -> entity lock order as CRM execution and deletion.
    thread = staff_conversation(conversation_id=conversation_id, user=user, write=write)
    with transaction.atomic():
        if connection.vendor == "sqlite":
            # SQLite ignores SELECT FOR UPDATE. Acquire its writer reservation
            # before reading state, so concurrent duplicate requests serialize.
            Business.objects.filter(pk=thread.business_id).update(updated_at=F("updated_at"))
        Business.objects.select_for_update().get(pk=thread.business_id)
        yield staff_conversation(conversation_id=conversation_id, user=user, lock=True, write=write)


def assert_turn_access(thread, user, mode):
    resource = Resources.AI_ANALYST if mode == "analytics" else Resources.AI_ASSISTANT
    assert_can(user, thread.business, resource, Actions.VIEW if mode == "analytics" else Actions.SUGGEST)
    with bind_agent(thread.agent_id):
        return assert_workflow_enabled(thread.business, "analyst" if mode == "analytics" else "employee")


def _reject_pending_tools(turn, user):
    pending = turn.tool_calls.filter(status=AIToolCallLog.Statuses.SUGGESTED)
    ApprovalRequest.objects.filter(ai_tool_call_log__in=pending, status__in=["pending", "approved"]).update(
        status="rejected", rejected_by=user, rejected_at=timezone.now(), reason="Conversation action cancelled.", updated_at=timezone.now())
    pending.update(status=AIToolCallLog.Statuses.REJECTED, error="Conversation action cancelled.")


def stop_turn(turn, user, *, status=AgentTurn.Statuses.CANCELLED):
    _reject_pending_tools(turn, user)
    turn.status = status
    turn.completed_at = timezone.now()
    turn.save(update_fields=["status", "completed_at", "updated_at"])
    AIJob.objects.filter(prompt_type="agent_conversation", business=turn.conversation.business,
        input_json__runtime_context__turn_id=turn.pk, status__in=["pending", "running", "retry_scheduled"]).update(
        status=AIJob.Statuses.FAILED, error="Conversation request cancelled.", completed_at=timezone.now(),
        locked_at=None, next_retry_at=None, updated_at=timezone.now())
    write_actor_audit_log(actor=user, action=AuditLog.Actions.UPDATE, instance=turn,
                         metadata={"kind": "ai_conversation_cancel", "status": status})


def recover_interrupted(thread):
    cutoff = timezone.now() - timezone.timedelta(seconds=max(300, settings.AI_HTTP_TIMEOUT_SECONDS * 8))
    # Execution is transactionally committed; an abandoned provider preparation
    # may have incurred cost, so recovery never repeats it automatically.
    expired = thread.turns.filter(status=AgentTurn.Statuses.PREPARING, updated_at__lt=cutoff)
    if expired.exists():
        expired.update(status=AgentTurn.Statuses.FAILED, error_code="interrupted", completed_at=timezone.now(), updated_at=timezone.now())


def conversation_job(turn, *, key):
    thread = turn.conversation
    with bind_agent(thread.agent_id):
        from apps.ai_core.agent_runtime import agent_binding
        runtime = {"_agent": agent_binding(thread.business), "turn_id": turn.pk, "conversation_id": str(thread.pk)}
    job, created = AIJob.objects.get_or_create(business=thread.business, idempotency_key=key,
        defaults={"user": thread.owner, "prompt_type": "agent_conversation", "max_attempts": 1,
                  "input_json": {"user_input": turn.message, "runtime_context": runtime}})
    if not created and (job.user_id != thread.owner_id or job.input_json.get("runtime_context", {}).get("turn_id") != turn.pk):
        raise IdempotencyConflict()
    return job, created


def dispatch_conversation_job(job):
    from apps.ai_core.services import process_ai_job
    from apps.ai_core.tasks import process_ai_job_task
    if settings.AI_PROVIDER == "mock" or not settings.AI_QUEUE_LIVE_REQUESTS:
        process_ai_job(job.pk)
    else:
        def enqueue():
            try:
                process_ai_job_task.apply_async(args=[job.pk], queue="ai")
            except Exception:
                AIJob.objects.filter(pk=job.pk, status="pending").update(status="failed", error="AI queue is unavailable.", completed_at=timezone.now())
                fail_turn(job.input_json["runtime_context"]["turn_id"], "queue_unavailable")
        transaction.on_commit(enqueue)


def start_turn(*, conversation_id, user, message, idempotency_key, mode="work", context=None):
    context = context or {}
    request_hash = hashlib.sha256(json.dumps([message, mode, context], sort_keys=True).encode()).hexdigest()
    with locked_conversation(conversation_id, user) as thread:
        assert_turn_access(thread, user, mode)
        existing = thread.turns.filter(idempotency_key=idempotency_key).first()
        if existing:
            if existing.request_hash != request_hash:
                raise IdempotencyConflict("This request key belongs to a different message.")
            return existing, None
        recover_interrupted(thread)
        if thread.turns.filter(status__in=RUNNING).exists():
            raise IdempotencyConflict("Wait for the current request or cancel it.")
        for previous in thread.turns.filter(status__in=OPEN):
            stop_turn(previous, user, status=AgentTurn.Statuses.SUPERSEDED)
        thread.revision += 1
        if not thread.title:
            thread.title = " ".join(message.split())[:120]
        thread.save(update_fields=["revision", "title", "updated_at"])
        with bind_agent(thread.agent_id):
            version = workflow_fingerprint(thread.business, "analyst" if mode == "analytics" else "employee")
        turn = AgentTurn.objects.create(conversation=thread, sequence=thread.revision, idempotency_key=idempotency_key,
            request_hash=request_hash, message=message, mode=mode, context_json=context, memory_epoch=thread.memory_epoch,
            access_fingerprint=memory_access_fingerprint(business=thread.business, agent=thread.agent, user=user),
            runtime_fingerprint=version)
        job, _ = conversation_job(turn, key=f"agent-turn:{turn.pk}")
    return turn, job


def cancel_turn(*, conversation_id, turn_id, user):
    with locked_conversation(conversation_id, user, write=False) as thread:
        turn = thread.turns.filter(pk=turn_id).first()
        if turn is None:
            raise ValidationError("Turn is unavailable.")
        if turn.status in OPEN or turn.status == AgentTurn.Statuses.FAILED:
            stop_turn(turn, user)
            thread.save(update_fields=["updated_at"])
        return turn


def reset_memory(*, conversation_id, user):
    with locked_conversation(conversation_id, user, write=False) as thread:
        for turn in thread.turns.filter(status__in=OPEN):
            stop_turn(turn, user)
        thread.memory_epoch += 1
        thread.memory_since = timezone.now()
        thread.memory_json = {}
        thread.save(update_fields=["memory_epoch", "memory_since", "memory_json", "updated_at"])
        write_actor_audit_log(actor=user, action=AuditLog.Actions.UPDATE, instance=thread,
                             metadata={"kind": "ai_memory_reset", "history_preserved": True})
        return thread


def retry_turn(*, conversation_id, turn_id, user, idempotency_key):
    with locked_conversation(conversation_id, user) as thread:
        turn = thread.turns.filter(pk=turn_id).first()
        if turn is None:
            raise ValidationError("Turn is unavailable.")
        key = f"agent-retry:{turn.pk}:{idempotency_key}"
        if AIJob.objects.filter(business=thread.business, idempotency_key=key, user=user).exists():
            return turn, None
        if turn.status != AgentTurn.Statuses.FAILED or turn.sequence != thread.revision or turn.memory_epoch != thread.memory_epoch:
            raise ValidationError("This request cannot be retried. Send a new message.")
        assert_turn_access(thread, user, turn.mode)
        with bind_agent(thread.agent_id):
            turn.runtime_fingerprint = workflow_fingerprint(thread.business, "analyst" if turn.mode == "analytics" else "employee")
        turn.access_fingerprint = memory_access_fingerprint(business=thread.business, agent=thread.agent, user=user)
        turn.status = AgentTurn.Statuses.PREPARING
        turn.error_code = ""
        turn.completed_at = None
        turn.save(update_fields=["runtime_fingerprint", "access_fingerprint", "status", "error_code", "completed_at", "updated_at"])
        job, _ = conversation_job(turn, key=key)
    return turn, job


def fail_turn(turn_id, code):
    AgentTurn.objects.filter(pk=turn_id, status=AgentTurn.Statuses.PREPARING).update(
        status=AgentTurn.Statuses.FAILED, error_code=code, completed_at=timezone.now(), updated_at=timezone.now())


def assert_current_turn(thread, turn, *, statuses=(AgentTurn.Statuses.PREPARING,)):
    if turn.status not in statuses or turn.memory_epoch != thread.memory_epoch or turn.sequence != thread.revision:
        raise PermissionDenied("This conversation request is no longer current.")
    assert_turn_access(thread, thread.owner, turn.mode)
    with bind_agent(thread.agent_id):
        version = workflow_fingerprint(thread.business, "analyst" if turn.mode == "analytics" else "employee")
    access = memory_access_fingerprint(business=thread.business, agent=thread.agent, user=thread.owner)
    if version != turn.runtime_fingerprint or access != turn.access_fingerprint:
        raise PermissionDenied("Agent sources or permissions changed. Send a new request.")
