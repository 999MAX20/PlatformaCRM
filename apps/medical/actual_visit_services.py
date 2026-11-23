import json
from datetime import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.models import Branch
from apps.businesses.access import assert_can
from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.scheduling.models import Appointment, Resource
from apps.scheduling.record_commands import create_record
from apps.services.models import Service
from .actual_visit_access import validate_actual_recording
from .audit import write_patient_audit
from .identity_crypto import encrypt_medical_value, decrypt_medical_value, medical_request_digest, MedicalDataUnavailable
from .models import MedicalActualVisit, PatientProfile
from .role_access import assert_medical_branch_permission


def actual_visit_evidence(item):
    try:
        value = json.loads(decrypt_medical_value(item.evidence_encrypted, business_id=item.appointment.business_id,
            subject_id=item.appointment_id, purpose="actual_visit"))
        if (set(value) != {"appointment_id", "patient_id", "business_id", "started_at", "actor_id", "reason"}
                or value["appointment_id"] != item.appointment_id or value["patient_id"] != item.patient_id
                or value["business_id"] != item.appointment.business_id or value["actor_id"] != item.recorded_by_id
                or datetime.fromisoformat(value["started_at"]) != item.started_at
                or item.patient.client_id != item.appointment.client_id
                or item.patient.business_id != item.appointment.business_id
                or not isinstance(value["reason"], str) or len(value["reason"]) > 2000):
            raise ValueError
        return value
    except (ValueError, TypeError, KeyError):
        raise MedicalDataUnavailable() from None


def _context(actor, business_id, client_id, branch_id):
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    branch = Branch.objects.filter(business=business, pk=branch_id).first()
    role = assert_medical_branch_permission(actor, business, "medical_patients", "create", branch=branch)
    if role.kind not in ("doctor", "head", "reception"):
        raise PermissionDenied()
    patient = PatientProfile.objects.select_related("client").filter(business=business, client_id=client_id,
        client__business=business, client__is_archived=False).first()
    if patient is None:
        raise NotFound()
    assert_can(actor, business, "clients", "view", obj=patient.client)
    assert_can(actor, business, "appointments", "create")
    return business, branch, patient, role


@transaction.atomic
def actual_visit_context(*, actor, business_id, client_id, branch_id):
    business, branch, patient, role = _context(actor, business_id, client_id, branch_id)
    resources = Resource.objects.filter(business=business, resource_type="staff", is_active=True,
        retired_at__isnull=True, linked_user__isnull=False).select_related("linked_user")
    if role.kind == "doctor":
        resources = resources.filter(linked_user=actor)
    eligible = []
    for resource in resources:
        try:
            clinician = assert_medical_branch_permission(resource.linked_user, business, "medical_records", "create", branch=branch)
        except PermissionDenied:
            continue
        if clinician.kind in ("doctor", "head"):
            eligible.append(resource.pk)
    write_patient_audit(actor=actor, business=business, patient=patient, action="read")
    return {"patient_id": patient.pk, "patient_revision": patient.revision,
        "earlier_allowed": role.kind == "head", "resource_ids": eligible, "now": timezone.now()}


@transaction.atomic
def create_actual_visit(*, actor, business_id, client_id, branch_id, service_id, resource_id, start_at,
                        expected_patient_revision, expected_price, expected_duration_minutes, idempotency_key, reason=""):
    identifiers = (business_id, client_id, branch_id, service_id, resource_id, expected_patient_revision, expected_duration_minutes)
    if any(type(value) is not int or value < 1 for value in identifiers):
        raise ValidationError({"visit": "Provide valid references and revisions."})
    if not isinstance(start_at, datetime) or timezone.is_naive(start_at):
        raise ValidationError({"start_at": "Provide the actual start with timezone."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    business, branch, patient, _ = _context(actor, business_id, client_id, branch_id)
    service = Service.objects.filter(business=business, pk=service_id).first()
    resource = Resource.objects.filter(business=business, pk=resource_id).select_related("linked_user").first()
    if service is None or resource is None:
        raise PermissionDenied()
    validate_actual_recording(mode="medical_actual", business=business, actor=actor, client=patient.client,
        resource=resource, branch=branch, start_at=start_at, reason=reason)

    def operation():
        if patient.revision != expected_patient_revision:
            raise InvalidTransition("The patient's identity changed; reload it first.")
        appointment = create_record(business=business, actor=actor, client=patient.client, service=service,
            resource=resource, branch=branch, start_at=start_at, expected_price=expected_price,
            expected_duration_minutes=expected_duration_minutes, creation_mode="medical_actual", creation_reason=reason)
        evidence = {"appointment_id": appointment.pk, "patient_id": patient.pk, "business_id": business.pk,
            "started_at": start_at.isoformat(), "actor_id": actor.pk, "reason": reason}
        MedicalActualVisit.objects.create(appointment=appointment, patient=patient, recorded_by=actor, started_at=start_at,
            evidence_encrypted=encrypt_medical_value(json.dumps(evidence, ensure_ascii=False), business_id=business.pk,
                subject_id=appointment.pk, purpose="actual_visit"))
        write_patient_audit(actor=actor, business=business, patient=patient, action="read")
        return CRMCommandResult(data={}, status_code=201, resource=appointment)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.actual_visit.create",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"client": client_id, "branch": branch_id, "service": service_id, "resource": resource_id,
            "start_at": start_at, "patient_revision": expected_patient_revision, "price": expected_price,
            "duration": expected_duration_minutes, "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)},
        operation=operation)
    appointment = Appointment.objects.get(business=business, client=patient.client,
        pk=result.resource_id if result.replayed else result.resource.pk)
    assert_can(actor, business, "appointments", "view", obj=appointment)
    return {"id": appointment.pk, "start_at": appointment.start_at, "replayed": result.replayed}
