from datetime import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.branches.access import assert_branch_access
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment
from .identity_crypto import medical_request_digest
from .models import ReceptionBookingRequest
from .reception_claims import reception_request_context


@transaction.atomic
def link_reception_appointment(*, actor, business_id, request_id, expected_revision, appointment_id,
                               expected_updated_at, confirmed, idempotency_key):
    if (any(type(value) is not int or value <= 0 for value in (expected_revision, appointment_id))
            or confirmed is not True):
        raise ValidationError({"booking": "Select an appointment and explicitly confirm its link."})
    if not isinstance(expected_updated_at, datetime) or timezone.is_naive(expected_updated_at):
        raise ValidationError({"expected_updated_at": "Provide the displayed appointment timestamp."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    actor, business, member, item = reception_request_context(actor=actor, business_id=business_id,
        request_id=request_id)
    if item.assignee_id != member.pk:
        raise PermissionDenied()
    assert_resource_enabled(business, Resources.APPOINTMENTS)
    appointment = Appointment.objects.select_for_update().filter(pk=appointment_id, business=business,
        client_id=item.patient.client_id, service__business=business, branch__business=business,
        resource__business=business).first()
    if appointment is None:
        raise PermissionDenied()
    for action in (Actions.VIEW, Actions.UPDATE):
        assert_can(actor, business, Resources.APPOINTMENTS, action, obj=appointment)
    assert_branch_access(actor, business, appointment.branch, active=True)

    def operation():
        if item.revision != expected_revision or item.state != "pending" or item.booked_appointment_id is not None:
            raise InvalidTransition("The request changed; review its current booking and owner.")
        if (appointment.updated_at != expected_updated_at or appointment.pk == item.source_appointment_id
                or appointment.branch_id != item.branch_id or appointment.service_id != item.service_id
                or appointment.is_archived or appointment.status not in ("created", "confirmed", "rescheduled")
                or appointment.start_at <= timezone.now() or appointment.end_at <= appointment.start_at
                or appointment.resource.resource_type != "staff"):
            raise InvalidTransition("Select a current follow-up appointment matching this request.")
        if ReceptionBookingRequest.objects.filter(booked_appointment=appointment).exists():
            raise InvalidTransition("This appointment is already linked to a follow-up request.")
        item.booked_appointment, item.state, item.closed_at = appointment, "booked", timezone.now()
        item.revision += 1
        item.full_clean()
        item.save(update_fields=["booked_appointment", "state", "closed_at", "revision"])
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.UPDATE, instance=item,
            metadata={"kind": "medical_follow_up_linked", "revision": item.revision, "state": item.state})
        from .reception_notifications import notify_reception
        notify_reception(item, "changed")
        return CRMCommandResult(data={}, resource=appointment)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.reception.link",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"request": request_id, "revision": expected_revision, "appointment": appointment_id,
            "updated_at": expected_updated_at.isoformat()}, operation=operation)
    item.refresh_from_db()
    return item, appointment, result.replayed
