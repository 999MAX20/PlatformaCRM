from datetime import date

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from apps.scheduling.models import Resource
from apps.services.models import Service
from .encounter_services import primary_draft_context
from .identity_crypto import medical_request_digest
from .models import ReceptionBookingRequest
from .reception_deadlines import reception_acceptance_deadline


@transaction.atomic
def request_primary_follow_up(*, actor, business_id, patient_id, encounter_id, expected_revision,
                              service_id, preferred_resource_id, recommended_from, recommended_until,
                              patient_in_clinic, idempotency_key, duration_minutes=None, participation_id=None):
    identifiers = [business_id, patient_id, encounter_id, expected_revision, service_id, preferred_resource_id]
    if participation_id is not None:
        identifiers.append(participation_id)
    if any(type(value) is not int or value <= 0 for value in identifiers):
        raise ValidationError({"request": "Provide valid identifiers and the current encounter revision."})
    if (type(recommended_from) is not date or type(recommended_until) is not date or
            recommended_until < recommended_from):
        raise ValidationError({"period": "Provide a valid recommended date range."})
    if type(patient_in_clinic) is not bool:
        raise ValidationError({"patient_in_clinic": "Provide whether the patient is at the clinic."})
    if duration_minutes is not None and (type(duration_minutes) is not int or duration_minutes <= 0):
        raise ValidationError({"duration_minutes": "Provide a positive duration."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})

    business, patient, encounter, _ = primary_draft_context(actor=actor, business_id=business_id,
        patient_id=patient_id, encounter_id=encounter_id, participation_id=participation_id)
    service = Service.objects.filter(pk=service_id, business=business).first()
    preferred = Resource.objects.filter(pk=preferred_resource_id, business=business, resource_type="staff").first()
    if service is None or preferred is None:
        raise PermissionDenied()

    def operation():
        if encounter.state != "draft" or encounter.revision != expected_revision or encounter.record.state != "active":
            raise InvalidTransition("The encounter changed; review its current version.")
        existing = ReceptionBookingRequest.objects.filter(business=business, patient=patient,
            source_appointment_id=encounter.appointment_id, service=service, state__in=["new", "pending"]).first()
        if existing is not None:
            return CRMCommandResult(data={"existing": True}, resource=existing)
        now = timezone.now()
        item = ReceptionBookingRequest(business=business, patient=patient,
            source_appointment_id=encounter.appointment_id, branch=encounter.branch,
            referring_clinician_id=encounter.primary_clinician_id, created_by=actor,
            created_at=now, service=service, preferred_resource=preferred,
            recommended_from=recommended_from, recommended_until=recommended_until,
            duration_minutes=duration_minutes, patient_in_clinic=patient_in_clinic,
            acceptance_due_at=reception_acceptance_deadline(business=business, branch_id=encounter.branch_id,
                requested_at=now, patient_in_clinic=patient_in_clinic))
        item.full_clean()
        item.save(force_insert=True)
        write_actor_audit_log(actor=actor, business=business, action=AuditLog.Actions.CREATE, instance=item,
            metadata={"kind": "medical_follow_up_requested", "revision": item.revision, "state": item.state})
        from .reception_notifications import notify_reception
        notify_reception(item, "new")
        return CRMCommandResult(data={"existing": False}, status_code=201, resource=item)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.reception.request",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "encounter": encounter_id, "revision": expected_revision,
            "service": service_id, "resource": preferred_resource_id, "from": recommended_from.isoformat(),
            "until": recommended_until.isoformat(), "duration": duration_minutes,
            "onsite": patient_in_clinic, "participation": participation_id}, operation=operation)
    item = ReceptionBookingRequest.objects.get(business=business, patient=patient,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return item, result.replayed or result.data["existing"]
