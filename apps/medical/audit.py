from django.core.exceptions import ValidationError as ModelValidationError
from django.db import DatabaseError

from apps.core.domain_errors import DomainAPIException
from .models import DentalToothHistory, DentalMedicalRecord, MedicalAuditEvent, PatientProfile, PatientRepresentative, TreatmentParticipation, MedicalEncounterRevision


class MedicalAuditUnavailable(DomainAPIException):
    status_code = 503
    error_code = "medical_audit_unavailable"
    default_code = error_code
    default_detail = "Medical audit is unavailable. The operation was not completed."
    category = "temporary"


def write_patient_audit(*, actor, business, patient, action, representative=None, participation=None, encounter_version=None, record=None, tooth_history=None):
    if action not in MedicalAuditEvent.Actions.values or action == MedicalAuditEvent.Actions.ACCESS_DENIED:
        raise ValueError("Select a supported successful patient action.")
    if not patient.pk or not PatientProfile.objects.filter(pk=patient.pk, business_id=business.pk).exists():
        raise ValueError("Audit patient must belong to this business.")
    if representative is not None and not PatientRepresentative.objects.filter(
            pk=representative.pk, patient=patient, representative_client__business_id=business.pk).exists():
        raise ValueError("Audit representative must belong to this patient and business.")
    if action in {MedicalAuditEvent.Actions.REPRESENTATIVE_VERIFIED, MedicalAuditEvent.Actions.REPRESENTATIVE_REVOKED} and representative is None:
        raise ValueError("A representative action requires its representation.")
    if participation is not None:
        if representative is not None or not TreatmentParticipation.objects.filter(
                pk=participation.pk, patient=patient, patient__client__business_id=business.pk,
                member__business_id=business.pk, branch__business_id=business.pk).exists():
            raise ValueError("Audit participation must belong to this patient and business.")
    if action.startswith("participation_") and participation is None:
        raise ValueError("A participation action requires its participation.")
    if action == MedicalAuditEvent.Actions.PARTICIPATION_ENDED and not TreatmentParticipation.objects.filter(
            pk=participation.pk, state="ended", revision=participation.revision, closed_by=actor,
            remaining_responsible__business_id=business.pk).exclude(closure_reason_encrypted="").exists():
        raise ValueError("A participation end event requires its current closure and responsible member.")
    if action.startswith("encounter_") and encounter_version is None:
        raise ValueError("An encounter action requires its clinical version.")
    if encounter_version is not None:
        version = MedicalEncounterRevision.objects.select_related("encounter").filter(
            pk=encounter_version.pk, encounter__business_id=business.pk, encounter__patient=patient).first()
        if version is None or representative is not None or participation is not None:
            raise ValueError("Audit clinical version must belong to this patient and business.")
        try:
            version.encounter.clean()
        except ModelValidationError:
            raise ValueError("Audit encounter links must be consistent.") from None
        if version.revision > version.encounter.revision:
            raise ValueError("Audit clinical version exceeds the encounter revision.")
        if action.startswith("encounter_") and (version.encounter.state != "draft" or version.revision != version.encounter.revision):
            raise ValueError("A draft write event requires the current draft version.")
    if action == MedicalAuditEvent.Actions.RECORD_OPENED and record is None:
        raise ValueError("A record action requires its medical record.")
    if record is not None:
        if any(item is not None for item in (representative, participation, encounter_version)) or not DentalMedicalRecord.objects.filter(
                pk=record.pk, business=business, patient=patient, patient__client__business_id=business.pk).exists():
            raise ValueError("Audit record must belong to this patient and business.")
    if action == MedicalAuditEvent.Actions.TOOTH_OBSERVATION_SAVED and tooth_history is None:
        raise ValueError("A tooth write action requires its observation version.")
    if tooth_history is not None:
        if any(item is not None for item in (representative, participation, encounter_version, record)):
            raise ValueError("Audit tooth history cannot be mixed with other entity references.")
        if action not in {MedicalAuditEvent.Actions.READ, MedicalAuditEvent.Actions.TOOTH_OBSERVATION_SAVED}:
            raise ValueError("Select a tooth observation read or write action.")
        history = DentalToothHistory.objects.select_related("tooth_state", "encounter").filter(
            pk=tooth_history.pk, tooth_state__business=business, tooth_state__patient=patient,
            encounter__business=business, encounter__patient=patient).first()
        if history is None:
            raise ValueError("Audit tooth history must belong to this patient and business.")
        try:
            history.full_clean()
        except ModelValidationError:
            raise ValueError("Audit tooth history links must be consistent.") from None
        if action == MedicalAuditEvent.Actions.TOOTH_OBSERVATION_SAVED and (
                history.revision != history.tooth_state.revision or history.encounter.state != "draft"):
            raise ValueError("A tooth write event requires the current revision in a draft encounter.")
    try:
        event = MedicalAuditEvent.objects.create(business=business, actor=actor, patient=patient,
            patient_revision=patient.revision, action=action, result="success", representative=representative,
            representative_revision=representative.revision if representative else None,
            participation=participation, participation_revision=participation.revision if participation else None,
            encounter_version=encounter_version, record=record, tooth_history=tooth_history)
        if event is None or event.pk is None:
            raise MedicalAuditUnavailable()
        return event
    except DatabaseError:
        raise MedicalAuditUnavailable() from None
