import json

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import DentalToothHistory, DentalToothState, MedicalEncounter


def validate_tooth_content(content):
    if not isinstance(content, dict) or not {"observation", "reason"} <= set(content) or set(content) - {"observation", "reason", "surface_protocol"}:
        raise ValidationError({"content": "Provide an observation and a correction reason field."})
    if (not isinstance(content["observation"], str) or not content["observation"].strip()
            or len(content["observation"]) > 32768 or not isinstance(content["reason"], str)
            or len(content["reason"]) > 2000):
        raise ValidationError({"content": "Provide observation text up to 32768 characters and reason up to 2000."})
    if "surface_protocol" in content:
        protocol = content["surface_protocol"]
        if (not isinstance(protocol, dict) or set(protocol) != {"reference", "approval_reference"}
                or any(not isinstance(value, str) or not value.strip() or len(value) > 200 for value in protocol.values())):
            raise ValidationError({"content": "Provide the approved surface protocol references."})
    return dict(content)


def _metadata(history):
    state, encounter = history.tooth_state, history.encounter
    return {"schema": 1, "business_id": state.business_id, "patient_id": state.patient_id,
        "tooth_state_id": state.pk, "tooth": state.tooth, "surface": state.surface,
        "history_id": history.pk, "revision": history.revision, "previous_id": history.previous_id,
        "encounter_id": encounter.pk, "record_id": encounter.record_id, "appointment_id": encounter.appointment_id,
        "branch_id": encounter.branch_id, "primary_clinician_id": encounter.primary_clinician_id,
        "author_id": history.author_id, "observed_at": history.observed_at.isoformat(),
        "created_at": history.created_at.isoformat()}


@transaction.atomic
def append_tooth_history(*, tooth_state, encounter, author, observation, reason="", observed_at=None, surface_protocol=None):
    """Internal storage step; caller authorizes and audits in the enclosing transaction."""
    content = {"observation": observation, "reason": reason}
    if surface_protocol is not None:
        content["surface_protocol"] = surface_protocol
    content = validate_tooth_content(content)
    Business.objects.select_for_update().get(pk=tooth_state.business_id)
    state = DentalToothState.objects.select_for_update().get(pk=tooth_state.pk, business_id=tooth_state.business_id)
    if state.revision != tooth_state.revision:
        raise InvalidTransition("The tooth state changed; reload its current revision.")
    current_encounter = MedicalEncounter.objects.select_for_update().get(pk=encounter.pk,
        business_id=state.business_id, patient_id=state.patient_id)
    previous = None
    if state.revision > 1:
        previous = DentalToothHistory.objects.filter(tooth_state=state, revision=state.revision - 1).first()
        if previous is None:
            raise MedicalDataUnavailable()
    staging = encrypt_medical_value("{}", business_id=state.business_id, subject_id=state.pk, purpose="tooth_staging")
    history = DentalToothHistory(tooth_state=state, encounter=current_encounter, revision=state.revision,
        previous=previous, author=author, content_encrypted=staging)
    if observed_at is not None:
        history.observed_at = observed_at
    history.full_clean()
    history.save()
    history.refresh_from_db()
    history.content_encrypted = encrypt_medical_value(json.dumps({**_metadata(history), "content": content},
        ensure_ascii=False, sort_keys=True), business_id=state.business_id, subject_id=history.pk, purpose="tooth_content")
    history.save(update_fields=["content_encrypted"])
    return history


def read_tooth_history(history):
    """Internal decryptor; caller establishes access and durable read audit first."""
    try:
        current = DentalToothHistory.objects.select_related("tooth_state", "encounter").get(pk=history.pk)
        current.full_clean()
        state = current.tooth_state
        data = json.loads(decrypt_medical_value(current.content_encrypted, business_id=state.business_id,
            subject_id=current.pk, purpose="tooth_content"))
        expected = _metadata(current)
        if not isinstance(data, dict) or set(data) != set(expected) | {"content"}:
            raise ValueError
        if any(type(data[key]) is not type(value) or data[key] != value for key, value in expected.items()):
            raise ValueError
        return validate_tooth_content(data["content"])
    except (DentalToothHistory.DoesNotExist, ModelValidationError, ValidationError, ValueError, TypeError, KeyError):
        raise MedicalDataUnavailable() from None
