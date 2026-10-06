"""Exact, explicit confirmation over the existing approval/domain transaction."""
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.ai_core.agent_runtime import bind_agent
from apps.ai_core.audit import audit_ai_tool_execution, audit_approval_decision, audit_approval_request_created
from apps.ai_core.conversation_copy import conversation_text
from apps.ai_core.conversation_state import assert_current_turn, conversation_job, locked_conversation
from apps.ai_core.crm_tools import request_context
from apps.ai_core.models import AgentTurn, AIToolCallLog, ApprovalRequest
from apps.ai_core.tool_registry import execute_tool_call_once, tool_call_fingerprint
from apps.ai_core.workflows import assert_workflow_enabled
from apps.businesses.access import Actions, Resources, assert_can
from apps.core.domain_errors import IdempotencyConflict


def _approve(log, user, request):
    now = timezone.now()
    approval = ApprovalRequest.objects.create(business=log.business, requested_by=user, approved_by=user,
        approved_at=now, action_type=ApprovalRequest.ActionTypes.AI_PIPELINE,
        ai_tool_call_log=log, status=ApprovalRequest.Statuses.APPROVED,
        expires_at=now + timezone.timedelta(minutes=30), source_object_type="AIToolCallLog", source_object_id=str(log.pk),
        payload={"tool_call_id": log.pk, "tool_fingerprint": tool_call_fingerprint(log), "requested_user_id": user.pk})
    audit_approval_request_created(request, approval)
    audit_approval_decision(request, approval, decision="approved")
    return approval


def confirm_turn(*, conversation_id, turn_id, user, actions, expected_revision):
    job = None
    with locked_conversation(conversation_id, user) as thread, bind_agent(thread.agent_id):
        turn = thread.turns.filter(pk=turn_id).first()
        if turn is None or expected_revision != thread.revision or turn.sequence != thread.revision:
            raise IdempotencyConflict("This proposal has been replaced. Review the latest request.")
        assert_can(user, thread.business, Resources.AI_PIPELINE, Actions.APPROVE)
        assert_can(user, thread.business, Resources.AI_PIPELINE, Actions.EXECUTE)
        selected = []
        for action in actions:
            log = turn.tool_calls.filter(pk=action["id"], user=user, business=thread.business).first()
            if log is None or action["fingerprint"] != tool_call_fingerprint(log):
                raise IdempotencyConflict("The reviewed action changed. Review it again.")
            selected.append(log)
        if not selected or len({log.pk for log in selected}) != len(selected):
            raise ValidationError("Select each reviewed action once.")
        # A lost HTTP response can be recovered without another approval/write.
        if all(log.status == AIToolCallLog.Statuses.EXECUTED for log in selected):
            return turn, None
        assert_current_turn(thread, turn, statuses=(AgentTurn.Statuses.AWAITING_CONFIRMATION,))
        if turn.updated_at < timezone.now() - timezone.timedelta(minutes=30):
            raise IdempotencyConflict("This proposal expired. Prepare a fresh request.")
        if any(log.status not in {AIToolCallLog.Statuses.SUGGESTED, AIToolCallLog.Statuses.EXECUTED} for log in selected):
            raise ValidationError("Only current reviewed proposals can execute.")
        config = assert_workflow_enabled(thread.business, "employee")
        turn.status = AgentTurn.Statuses.EXECUTING
        turn.save(update_fields=["status", "updated_at"])
        request = request_context(user)
        failed = False
        # UI order cannot reorder a dependency or execution sequence.
        positions = {step.get("tool_call_id"): index for index, step in enumerate(turn.plan_json.get("steps", []))}
        for log in sorted(selected, key=lambda item: positions.get(item.pk, 999)):
            if log.status == AIToolCallLog.Statuses.EXECUTED:
                continue
            approval = _approve(log, user, request)
            outcome, duplicate = execute_tool_call_once(log.pk, user, approval_id=approval.pk)
            audit_ai_tool_execution(request, outcome, extra_metadata={"approval_id": approval.pk, "duplicate_execution": duplicate})
            if outcome.status != AIToolCallLog.Statuses.EXECUTED:
                failed = True
                break
        logs = {log.pk: log for log in turn.tool_calls.all()}
        completed = 0
        for step in turn.plan_json.get("steps", []):
            log = logs.get(step.get("tool_call_id"))
            step["completed"] = bool(log and log.status == AIToolCallLog.Statuses.EXECUTED)
            completed += int(step["completed"])
            if step["completed"]:
                reference = {"entity": log.output_json.get("entity"), "id": log.output_json.get("entity_id")}
                if reference not in turn.references_json:
                    turn.references_json.append(reference)
        if failed:
            turn.status, turn.error_code = AgentTurn.Statuses.FAILED, "action_failed"
            turn.response = conversation_text("partial", config.get("language")) if completed else ""
        elif completed == len(turn.plan_json["steps"]):
            turn.status = AgentTurn.Statuses.COMPLETED
            turn.response = conversation_text("completed", config.get("language"))
            turn.completed_at = timezone.now()
        elif any(log.status == AIToolCallLog.Statuses.SUGGESTED for log in logs.values()):
            turn.status = AgentTurn.Statuses.AWAITING_CONFIRMATION
            turn.response = conversation_text("review", config.get("language"))
        else:
            turn.status = AgentTurn.Statuses.PREPARING
            turn.response = conversation_text("partial", config.get("language"))
            job, _ = conversation_job(turn, key=f"agent-continue:{turn.pk}:{completed}")
        turn.save()
        thread.save(update_fields=["updated_at"])
    return turn, job
