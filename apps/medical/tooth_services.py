from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .appointment_access import assert_appointment_medical_basis
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .identity_crypto import MedicalDataUnavailable, medical_request_digest
from .models import DentalToothHistory, DentalToothState, FDI_TOOTH_NUMBERS, MedicalEncounter, MedicalRoleAssignment, PatientProfile
from .participation_access import assert_treatment_medical_basis
from .role_access import assert_medical_branch_permission, assert_medical_role_permission
from .tooth_content import append_tooth_history, read_tooth_history, validate_tooth_content
from .tooth_policy import surface_evidence


@transaction.atomic
def save_primary_tooth_observation(*, actor, business_id, patient_id, encounter_id, tooth,
        expected_patient_revision, expected_encounter_revision, expected_tooth_revision,
        observation, idempotency_key, surface="", surface_reference="", reason="", participation_id=None, tooth_status=None):
    identifiers = [business_id, patient_id, encounter_id, expected_patient_revision, expected_encounter_revision]
    if participation_id is not None:
        identifiers.append(participation_id)
    if (any(type(value) is not int or value <= 0 for value in identifiers)
            or type(expected_tooth_revision) is not int or expected_tooth_revision < 0
            or type(tooth) is not int or tooth not in FDI_TOOTH_NUMBERS):
        raise ValidationError({"observation": "Provide valid identifiers and revisions."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    content = {"observation": observation, "reason": reason}
    if tooth_status is not None:
        if surface:
            raise ValidationError({"tooth_status": "Tooth state applies to the whole tooth."})
        content["tooth_status"] = tooth_status
    content = validate_tooth_content(content)
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
        business=business, patient=patient, primary_clinician_id=context.member_id).first()
    if encounter is None:
        raise PermissionDenied()
    encounter.clean()
    assert_medical_branch_permission(actor, business, "medical_records", "update", branch=encounter.branch)
    if participation_id is None:
        assert_appointment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            appointment_id=encounter.appointment_id, action="update")
    else:
        basis = assert_treatment_medical_basis(actor=actor, business=business, patient_id=patient_id,
            participation_id=participation_id, action="update")
        if basis.branch_id != encounter.branch_id:
            raise PermissionDenied()
    assert_verified_clinical_identity(patient)
    protocol = surface_evidence(business_id=business_id, tooth=tooth, surface=surface, reference=surface_reference)

    def operation():
        effective_status = tooth_status
        if (patient.revision != expected_patient_revision or encounter.revision != expected_encounter_revision
                or encounter.state != "draft" or encounter.record.state != "active"):
            raise InvalidTransition("The patient or encounter changed; review the current draft.")
        state = DentalToothState.objects.select_for_update().filter(business=business,
            patient=patient, tooth=tooth, surface=surface).first()
        if state is None:
            if expected_tooth_revision != 0:
                raise InvalidTransition("The tooth state changed; reload its current revision.")
            state = DentalToothState(business=business, patient=patient, tooth=tooth, surface=surface)
            state.full_clean(); state.save()
        else:
            if state.revision != expected_tooth_revision:
                raise InvalidTransition("The tooth state changed; reload its current revision.")
            if effective_status is None and not surface:
                previous = DentalToothHistory.objects.filter(tooth_state=state, revision=state.revision).first()
                if previous is None:
                    raise MedicalDataUnavailable()
                effective_status = read_tooth_history(previous).get("tooth_status")
            state.revision += 1
            state.save(update_fields=["revision", "updated_at"])
        history = append_tooth_history(tooth_state=state, encounter=encounter, author=actor,
            observation=observation, reason=reason, surface_protocol=protocol, tooth_status=effective_status)
        write_patient_audit(actor=actor, business=business, patient=patient,
            action="tooth_observation_saved", tooth_history=history)
        return CRMCommandResult(data={}, resource=history)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.tooth.primary_observation",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"patient": patient_id, "encounter": encounter_id, "tooth": tooth, "surface": surface,
            "patient_revision": expected_patient_revision, "encounter_revision": expected_encounter_revision,
            "tooth_revision": expected_tooth_revision, "participation": participation_id,
            "content_digest": medical_request_digest({"content": content, "surface_protocol": protocol}, business_id=business_id)},
        operation=operation)
    history = DentalToothHistory.objects.get(tooth_state__business=business, tooth_state__patient=patient,
        encounter=encounter, pk=result.resource_id if result.replayed else result.resource.pk)
    return history, result.replayed
