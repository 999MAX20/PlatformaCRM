from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment, Resource
from apps.scheduling.record_commands import create_record
from .identity_crypto import medical_request_digest
from .reception_claims import reception_request_context


@transaction.atomic
def book_reception_request(*, actor, business_id, request_id, expected_revision, resource_id,
                           start_at, expected_price, expected_duration_minutes, confirmed, idempotency_key):
    if (any(type(value) is not int or value <= 0 for value in
            (expected_revision, resource_id, expected_duration_minutes)) or confirmed is not True):
        raise ValidationError({"booking": "Provide current booking terms and explicitly confirm."})
    if not isinstance(start_at, datetime) or timezone.is_naive(start_at):
        raise ValidationError({"start_at": "Provide a timestamp with timezone."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    try:
        price = None if expected_price is None else Decimal(str(expected_price))
        if price is not None and (not price.is_finite() or price < 0):
            raise ValueError
    except (ValueError, InvalidOperation):
        raise ValidationError({"expected_price": "Provide the displayed price."}) from None
    actor, business, member, item = reception_request_context(actor=actor, business_id=business_id,
        request_id=request_id)
    if item.assignee_id != member.pk:
        raise PermissionDenied()
    assert_resource_enabled(business, Resources.APPOINTMENTS)
    assert_can(actor, business, Resources.APPOINTMENTS, Actions.CREATE)
    resource = Resource.objects.filter(pk=resource_id, business=business, resource_type="staff").first()
    if resource is None:
        raise PermissionDenied()
    if item.booked_appointment_id:
        assert_can(actor, business, Resources.APPOINTMENTS, Actions.VIEW, obj=item.booked_appointment)

    def operation():
        if item.revision != expected_revision or item.state != "pending" or item.booked_appointment_id is not None:
            raise InvalidTransition("The request changed; review its current booking and owner.")
        appointment = create_record(business=business, actor=actor, client=item.patient.client,
            service=item.service, resource=resource, branch=item.branch, start_at=start_at,
            responsible_user=actor, expected_price=price, expected_duration_minutes=expected_duration_minutes)
        assert_can(actor, business, Resources.APPOINTMENTS, Actions.VIEW, obj=appointment)
        item.booked_appointment, item.state, item.closed_at = appointment, "booked", timezone.now()
        item.revision += 1
        item.full_clean()
        item.save(update_fields=["booked_appointment", "state", "closed_at", "revision"])
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.UPDATE, instance=item,
            metadata={"kind": "medical_follow_up_booked", "revision": item.revision, "state": item.state})
        return CRMCommandResult(data={}, resource=appointment)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.reception.book",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"request": request_id, "revision": expected_revision, "resource": resource_id,
            "start_at": start_at.isoformat(), "price": str(price) if price is not None else None,
            "duration": expected_duration_minutes}, operation=operation)
    appointment = Appointment.objects.get(business=business, client_id=item.patient.client_id,
        pk=result.resource_id if result.replayed else result.resource.pk)
    assert_can(actor, business, Resources.APPOINTMENTS, Actions.VIEW, obj=appointment)
    item.refresh_from_db()
    return item, appointment, result.replayed
