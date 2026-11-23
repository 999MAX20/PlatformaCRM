from datetime import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.scheduling.models import Appointment
from .appointment_access import assert_appointment_medical_basis
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .encounter_content import append_encounter_revision, validate_clinical_draft
from .identity_crypto import medical_request_digest
from .models import DentalMedicalRecord, MedicalEncounter, MedicalEncounterRevision, MedicalRoleAssignment, PatientProfile
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_branch_permission, assert_medical_role_permission


@transaction.atomic
def open_primary_encounter(*, actor, business_id, patient_id, record_id, appointment_id,
                           expected_patient_revision, expected_appointment_updated_at,
                           idempotency_key, content=None):
    identifiers = [business_id, patient_id, record_id, appointment_id,
                   expected_patient_revision]
    if any(type(value) is not int or value <= 0 for value in identifiers):
        raise ValidationError({"encounter": "Provide valid identifiers and revisions."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not isinstance(expected_appointment_updated_at, datetime) or timezone.is_naive(expected_appointment_updated_at):
        raise ValidationError({"expected_appointment_updated_at": "Provide the appointment timestamp with timezone."})
    content = validate_clinical_draft({} if content is None else content)
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    context = assert_medical_role_permission(actor, business, "medical_records", "create")
    patient = PatientProfile.objects.select_for_update().filter(pk=patient_id,
        business=business, client__business_id=business_id).first()
    if patient is None:
        raise NotFound()
    appointment = Appointment.objects.select_for_update().filter(pk=appointment_id,
        business=business, client_id=patient.client_id).first()
    if appointment is None:
        raise PermissionDenied()
    assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
        appointment_id=appointment_id, action="create")
    record = DentalMedicalRecord.objects.select_for_update().filter(pk=record_id,
        business=business, patient=patient).first()
    if record is None:
        raise PermissionDenied()

    assert_verified_clinical_identity(patient)

    def operation():
        if patient.revision != expected_patient_revision or appointment.updated_at != expected_appointment_updated_at:
            raise InvalidTransition("Patient or appointment changed; review the current values.")
        if record.state != DentalMedicalRecord.States.ACTIVE:
            raise InvalidTransition("The medical record is archived.")
        if MedicalEncounter.objects.filter(appointment=appointment).exists():
            raise InvalidTransition("A primary encounter already exists for this appointment.")
        encounter = MedicalEncounter(business=business, patient=patient, record=record,
            appointment=appointment, branch_id=appointment.branch_id, primary_clinician_id=context.member_id)
        encounter.full_clean()
        encounter.save(force_insert=True)
        version = append_encounter_revision(encounter=encounter, author=actor, content=content)
        write_patient_audit(actor=actor, business=business, patient=patient,
            action="encounter_opened", encounter_version=version)
        return CRMCommandResult(data={}, status_code=201, resource=version)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.encounter.open",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "record": record_id, "appointment": appointment_id,
            "patient_revision": expected_patient_revision, "appointment_updated_at": expected_appointment_updated_at,
            "content_digest": medical_request_digest({"content": content}, business_id=business_id)},
        operation=operation)
    version = MedicalEncounterRevision.objects.get(encounter__business=business,
        encounter__patient=patient, encounter__appointment=appointment,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return version, result.replayed


@transaction.atomic
def save_primary_encounter_draft(*, actor, business_id, patient_id, encounter_id,
                                 expected_revision, content, idempotency_key, reason="",
                                 participation_id=None, correction_access_id=None):
    """Save only the primary clinician's draft, preserving prior versions and authorship."""
    identifiers = [business_id, patient_id, encounter_id, expected_revision]
    if participation_id is not None:
        identifiers.append(participation_id)
    if correction_access_id is not None:
        identifiers.append(correction_access_id)
        if participation_id is not None:
            raise ValidationError({"basis": "Select one access basis."})
    if any(type(value) is not int or value <= 0 for value in identifiers):
        raise ValidationError({"encounter": "Provide valid identifiers and revision."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    content = validate_clinical_draft(content)
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide at most 2000 characters."})
    business, patient, encounter, correction_access = primary_draft_context(actor=actor, business_id=business_id,
        patient_id=patient_id, encounter_id=encounter_id, participation_id=participation_id,
        correction_access_id=correction_access_id)

    def operation():
        if encounter.revision != expected_revision or encounter.state != MedicalEncounter.States.DRAFT:
            raise InvalidTransition("The encounter changed; review its current draft.")
        if encounter.record.state != "active":
            raise InvalidTransition("The medical record is archived.")
        encounter.revision += 1
        encounter.save(update_fields=["revision", "updated_at"])
        version = append_encounter_revision(encounter=encounter, author=actor, content=content, reason=reason)
        write_patient_audit(actor=actor, business=business, patient=patient,
            action="encounter_draft_saved", encounter_version=version, correction_access=correction_access)
        return CRMCommandResult(data={}, resource=version)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.encounter.primary_draft",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"encounter": encounter_id, "patient": patient_id, "revision": expected_revision,
            "participation": participation_id,
            **({"correction_access": correction_access_id} if correction_access_id is not None else {}),
            "content_digest": medical_request_digest({"content": content, "reason": reason}, business_id=business_id)},
        operation=operation)
    version = MedicalEncounterRevision.objects.get(encounter=encounter,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return version, result.replayed


def primary_draft_context(*, actor, business_id, patient_id, encounter_id,
                          participation_id=None, correction_access_id=None):
    """Authorize a primary draft command inside its caller's atomic transaction."""
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    context = assert_medical_role_permission(actor, business, "medical_records", "update")
    if context.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        raise PermissionDenied()
    patient = PatientProfile.objects.select_for_update().filter(pk=patient_id,
        business=business, client__business_id=business_id).first()
    if patient is None:
        raise NotFound()
    encounter = MedicalEncounter.objects.select_for_update().filter(pk=encounter_id,
        patient=patient, business=business, primary_clinician_id=context.member_id).first()
    if encounter is None:
        raise PermissionDenied()
    encounter.clean()
    assert_medical_branch_permission(actor, business, "medical_records", "update", branch=encounter.branch)
    correction_access = None
    if correction_access_id is not None:
        from .correction_access_context import assert_correction_access
        correction_access = assert_correction_access(actor=actor, business=business,
            request_id=correction_access_id, encounter_id=encounter_id, action="update")
    elif participation_id is None:
        assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=encounter.appointment_id, action="update")
    else:
        basis = assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=participation_id, action="update")
        if basis.branch_id != encounter.branch_id:
            raise PermissionDenied()

    assert_verified_clinical_identity(patient)
    return business, patient, encounter, correction_access
