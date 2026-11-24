from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import BusinessMember
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from .identity_crypto import medical_request_digest
from .patient_selectors import reception_context
from .reception_claims import reception_request_context


def reception_recipient(*, business, item, member_id):
    target = BusinessMember.objects.select_related("user").filter(pk=member_id,
        business=business, is_active=True, user__is_active=True).first()
    if target is None:
        raise PermissionDenied()
    reception_context(actor=target.user, business_id=business.pk, branch_id=item.branch_id, action="update")
    assert_can(target.user, business, Resources.CLIENTS, Actions.VIEW, obj=item.patient.client)
    return target


@transaction.atomic
def transfer_reception_request(*, actor, business_id, request_id, expected_revision,
                               assignee_id, reason, idempotency_key):
    if type(expected_revision) is not int or expected_revision <= 0:
        raise ValidationError({"expected_revision": "Provide the current request revision."})
    if assignee_id is not None and (type(assignee_id) is not int or assignee_id <= 0):
        raise ValidationError({"assignee_id": "Select a recipient or explicitly release to the queue."})
    if not isinstance(reason, str) or not reason.strip() or len(reason.strip()) > 1000:
        raise ValidationError({"reason": "Provide an organizational reason of at most 1000 characters."})
    reason = reason.strip()
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    actor, business, member, item = reception_request_context(actor=actor, business_id=business_id,
        request_id=request_id)

    def operation():
        if item.assignee_id != member.pk:
            raise PermissionDenied()
        if item.revision != expected_revision or item.state != "pending":
            raise InvalidTransition("The request changed; review its current state.")
        target = None
        if assignee_id is not None:
            if assignee_id == member.pk:
                raise ValidationError({"assignee_id": "Select another recipient."})
            target = reception_recipient(business=business, item=item, member_id=assignee_id)
        previous = item.assignee_id
        item.assignee = target
        item.claimed_at = timezone.now() if target else None
        item.state = "pending" if target else "new"
        item.revision += 1
        item.full_clean()
        item.save(update_fields=["assignee", "claimed_at", "state", "revision"])
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.UPDATE, instance=item,
            metadata={"kind": "medical_follow_up_transferred", "revision": item.revision,
                "from_member_id": previous, "to_member_id": assignee_id, "reason": reason, "state": item.state})
        from .reception_notifications import notify_reception
        notify_reception(item, "changed")
        return CRMCommandResult(data={}, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.reception.transfer",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"request": request_id, "revision": expected_revision, "assignee": assignee_id, "reason": reason},
        operation=operation)
    item.refresh_from_db()
    return item, result.replayed
