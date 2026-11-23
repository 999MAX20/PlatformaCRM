from datetime import datetime

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.scheduling.services import complete_appointment
from .audit import write_patient_audit
from .encounter_completion_requirements import encounter_completion_requirements
from .encounter_services import primary_draft_context
from .identity_crypto import medical_request_digest, MedicalDataUnavailable
from .models import MedicalEncounterRevision


def _current_version(encounter):
    version = MedicalEncounterRevision.objects.filter(encounter=encounter, revision=encounter.revision).first()
    if version is None:
        raise MedicalDataUnavailable()
    return version


@transaction.atomic
def read_encounter_completion(*, actor, business_id, patient_id, encounter_id, participation_id=None):
    business, patient, encounter, _ = primary_draft_context(actor=actor, business_id=business_id,
        patient_id=patient_id, encounter_id=encounter_id, participation_id=participation_id)
    version = _current_version(encounter)
    write_patient_audit(actor=actor, business=business, patient=patient, action="read", encounter_version=version)
    return {**encounter_completion_requirements(version), "revision": encounter.revision,
        "appointment_updated_at": encounter.appointment.updated_at,
        "early": timezone.now() < encounter.appointment.end_at, "state": encounter.state}


@transaction.atomic
def complete_primary_encounter(*, actor, business_id, patient_id, encounter_id, expected_revision,
                               expected_appointment_updated_at, idempotency_key, reason="", participation_id=None):
    if type(expected_revision) is not int or expected_revision < 1:
        raise ValidationError({"expected_revision": "Provide the current encounter revision."})
    if not isinstance(expected_appointment_updated_at, datetime) or timezone.is_naive(expected_appointment_updated_at):
        raise ValidationError({"expected_appointment_updated_at": "Provide the appointment timestamp with timezone."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    if not isinstance(reason, str) or len(reason) > 500:
        raise ValidationError({"reason": "Provide at most 500 characters."})
    business, patient, encounter, _ = primary_draft_context(actor=actor, business_id=business_id,
        patient_id=patient_id, encounter_id=encounter_id, participation_id=participation_id)

    def operation():
        if encounter.state != "draft" or encounter.revision != expected_revision:
            raise InvalidTransition("The encounter changed; reload its current version.")
        if encounter.record.state != "active":
            raise InvalidTransition("The medical record is archived.")
        version = _current_version(encounter)
        requirements = encounter_completion_requirements(version)
        if not requirements["ready"]:
            raise InvalidTransition("Complete the required clinical sections and documents.", errors=requirements)
        now = timezone.now()
        encounter.state = "finalized"
        encounter.ended_at = now
        encounter.finalized_at = now
        encounter.finalized_by = actor
        encounter.save(update_fields=["state", "ended_at", "finalized_at", "finalized_by", "updated_at"])
        write_patient_audit(actor=actor, business=business, patient=patient,
            action="encounter_finalized", encounter_version=version)
        complete_appointment(appointment=encounter.appointment, actor=actor,
            expected_updated_at=expected_appointment_updated_at, reason=reason)
        return CRMCommandResult(data={}, resource=version)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.encounter.complete",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"encounter": encounter_id, "patient": patient_id, "revision": expected_revision,
            "appointment_updated_at": expected_appointment_updated_at, "participation": participation_id,
            "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}, operation=operation)
    version = MedicalEncounterRevision.objects.get(encounter=encounter,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return version, result.replayed
