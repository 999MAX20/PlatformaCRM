"""Recheck exact approval inside the command transaction, including worker calls."""
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.ai_core.models import ApprovalRequest
from apps.businesses.access import Actions, Resources, assert_can


def validate_locked_approval(log, user, approval_id):
    from apps.ai_core.tool_registry import tool_call_fingerprint
    assert_can(user, log.business, Resources.AI_PIPELINE, Actions.EXECUTE, obj=log)
    approval = ApprovalRequest.objects.select_for_update().filter(pk=approval_id,
        business=log.business, ai_tool_call_log=log, requested_by=user,
        action_type=ApprovalRequest.ActionTypes.AI_PIPELINE).first()
    if (approval is None or log.user_id != user.pk
            or approval.status not in {ApprovalRequest.Statuses.APPROVED, ApprovalRequest.Statuses.EXECUTED}
            or (approval.expires_at and approval.expires_at <= timezone.now())
            or not isinstance(approval.payload, dict)
            or approval.payload.get("tool_fingerprint") != tool_call_fingerprint(log)
            or approval.approved_by_id is None):
        raise PermissionDenied("A current approval for this exact command is required.")
    assert_can(approval.approved_by, log.business, Resources.AI_PIPELINE, Actions.APPROVE, obj=log)
    return approval
