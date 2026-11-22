import json

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalEncounter, MedicalEncounterRevision


CLINICAL_FIELDS = ("complaints", "anamnesis", "allergies", "contraindications", "examination", "diagnosis", "procedures", "plan", "epicrisis")
CLINICAL_TEXT_FIELDS = frozenset(CLINICAL_FIELDS)
CLINICAL_TEXT_LIMIT = 32768


def validate_clinical_draft(content):
    if not isinstance(content, dict) or set(content) - CLINICAL_TEXT_FIELDS:
        raise ValidationError({"content": "Provide supported clinical fields."})
    if any(not isinstance(value, str) or len(value) > CLINICAL_TEXT_LIMIT for value in content.values()):
        raise ValidationError({"content": "Each clinical field must be text of at most 32768 characters."})
    return dict(content)


def _metadata(version, encounter):
    return {"schema": 1, "business_id": encounter.business_id, "encounter_id": encounter.pk,
        "patient_id": encounter.patient_id, "record_id": encounter.record_id,
        "appointment_id": encounter.appointment_id, "branch_id": encounter.branch_id,
        "primary_clinician_id": encounter.primary_clinician_id, "version_id": version.pk,
        "revision": version.revision, "author_id": version.author_id,
        "created_at": version.created_at.isoformat()}


@transaction.atomic
def append_encounter_revision(*, encounter, author, content, reason=""):
    """Internal storage step; the caller must authorize and audit in its outer transaction."""
    content = validate_clinical_draft(content)
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    Business.objects.select_for_update().get(pk=encounter.business_id)
    current = MedicalEncounter.objects.select_for_update().get(pk=encounter.pk, business_id=encounter.business_id)
    if current.revision != encounter.revision:
        raise InvalidTransition("The encounter changed; reload its current revision.")
    current.clean()
    staging = encrypt_medical_value("{}", business_id=current.business_id,
        subject_id=current.pk, purpose="encounter_staging")
    version = MedicalEncounterRevision.objects.create(encounter=current, revision=current.revision,
        author=author, content_encrypted=staging)
    payload = {**_metadata(version, current), "content": content}
    version.content_encrypted = encrypt_medical_value(json.dumps(payload, ensure_ascii=False, sort_keys=True),
        business_id=current.business_id, subject_id=version.pk, purpose="encounter_content")
    version.reason_encrypted = encrypt_medical_value(reason, business_id=current.business_id,
        subject_id=version.pk, purpose="encounter_reason")
    version.save(update_fields=["content_encrypted", "reason_encrypted"])
    return version


def read_encounter_revision(version):
    """Internal decryptor; callers must establish access and a durable read audit first."""
    try:
        current = MedicalEncounterRevision.objects.select_related("encounter").get(pk=version.pk)
        encounter = current.encounter
        if current.revision > encounter.revision:
            raise ValueError
        encounter.clean()
        data = json.loads(decrypt_medical_value(current.content_encrypted,
            business_id=encounter.business_id, subject_id=current.pk, purpose="encounter_content"))
        expected = _metadata(current, encounter)
        if not isinstance(data, dict) or set(data) != set(expected) | {"content"}:
            raise ValueError
        if any(type(data[key]) is not type(value) or data[key] != value for key, value in expected.items()):
            raise ValueError
        content = validate_clinical_draft(data["content"])
        reason = decrypt_medical_value(current.reason_encrypted, business_id=encounter.business_id,
            subject_id=current.pk, purpose="encounter_reason")
        if len(reason) > 2000:
            raise ValueError
        return {"content": content, "reason": reason}
    except (MedicalEncounterRevision.DoesNotExist, ModelValidationError, ValidationError, ValueError, TypeError, KeyError):
        raise MedicalDataUnavailable() from None
