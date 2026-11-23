from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business, BusinessMember
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from .identity_crypto import medical_request_digest
from .models import ReceptionBookingRequest
from .patient_selectors import reception_context


def reception_request_context(*, actor, business_id, request_id, action="update"):
    """Resolve an organizational request inside the caller's atomic transaction."""
    if any(type(value) is not int or value <= 0 for value in (business_id, request_id)):
        raise ValidationError({"request": "Select a valid business and request."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise PermissionDenied()
    item = ReceptionBookingRequest.objects.select_for_update().select_related("patient__client").filter(
        pk=request_id, business=business, patient__business=business, patient__client__business=business,
        source_appointment__business=business, branch__business=business).first()
    if item is None:
        raise PermissionDenied()
    actor, _, _ = reception_context(actor=actor, business_id=business_id, branch_id=item.branch_id, action=action)
    client = item.patient.client
    if client.is_archived:
        raise PermissionDenied()
    assert_can(actor, business, Resources.CLIENTS, Actions.VIEW, obj=client)
    member = BusinessMember.objects.get(business=business, user=actor, is_active=True)
    return actor, business, member, item


@transaction.atomic
def claim_reception_request(*, actor, business_id, request_id, expected_revision, idempotency_key):
    if type(expected_revision) is not int or expected_revision <= 0:
        raise ValidationError({"expected_revision": "Provide the current request revision."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    actor, business, member, item = reception_request_context(actor=actor, business_id=business_id,
        request_id=request_id)

    def operation():
        if item.revision != expected_revision or item.state not in ("new", "pending") or item.assignee_id is not None:
            raise InvalidTransition("The request changed or has already been accepted; review its current state.")
        item.assignee, item.claimed_at, item.state = member, timezone.now(), "pending"
        item.revision += 1
        item.full_clean()
        item.save(update_fields=["assignee", "claimed_at", "state", "revision"])
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.UPDATE, instance=item,
            metadata={"kind": "medical_follow_up_claimed", "revision": item.revision, "state": item.state})
        return CRMCommandResult(data={}, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.reception.claim",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"request": request_id, "revision": expected_revision}, operation=operation)
    item.refresh_from_db()
    return item, result.replayed
