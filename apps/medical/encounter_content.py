import json
from uuid import UUID

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalEncounter, MedicalEncounterRevision, FDI_TOOTH_NUMBERS


CLINICAL_FIELDS = ("complaints", "anamnesis", "allergies", "contraindications", "examination", "diagnosis", "procedures", "plan", "epicrisis")
CLINICAL_TEXT_FIELDS = frozenset(CLINICAL_FIELDS)
CLINICAL_TEXT_LIMIT = 32768


def validate_clinical_draft(content):
    if not isinstance(content, dict) or set(content) - (CLINICAL_TEXT_FIELDS | {"not_applicable", "plan_steps"}):
        raise ValidationError({"content": "Provide supported clinical fields."})
    values = {key: value for key, value in content.items() if key in CLINICAL_TEXT_FIELDS}
    if any(not isinstance(value, str) or len(value) > CLINICAL_TEXT_LIMIT for value in values.values()):
        raise ValidationError({"content": "Each clinical field must be text of at most 32768 characters."})
    if "not_applicable" in content:
        reasons = content["not_applicable"]
        if (not isinstance(reasons, dict) or set(reasons) - CLINICAL_TEXT_FIELDS or
                any(not isinstance(reason, str) or not reason.strip() or len(reason) > 2000
                    or bool(values.get(field, "").strip()) for field, reason in reasons.items())):
            raise ValidationError({"content": "A non-applicable section needs a reason of at most 2000 characters and no clinical text."})
        values["not_applicable"] = dict(reasons)
    if "plan_steps" in content:
        steps = content["plan_steps"]
        if not isinstance(steps, list) or len(steps) > 100:
            raise ValidationError({"content": "Provide at most 100 clinical plan steps."})
        seen = set()
        for step in steps:
            if (not isinstance(step, dict) or not {"id", "description"} <= set(step)
                    or set(step) - {"id", "description", "visit_step", "teeth"}
                    or not isinstance(step["id"], str) or not isinstance(step["description"], str)
                    or len(step["description"]) > 4000):
                raise ValidationError({"content": "Provide a step identifier and description of at most 4000 characters."})
            try:
                canonical = str(UUID(step["id"]))
            except ValueError:
                raise ValidationError({"content": "Provide a valid step identifier."}) from None
            if canonical != step["id"] or canonical in seen:
                raise ValidationError({"content": "Step identifiers must be canonical and unique."})
            seen.add(canonical)
            if "teeth" in step:
                teeth = step["teeth"]
                if (not isinstance(teeth, list) or len(teeth) > len(FDI_TOOTH_NUMBERS)
                        or any(type(tooth) is not int or tooth not in FDI_TOOTH_NUMBERS for tooth in teeth)
                        or len(teeth) != len(set(teeth))):
                    raise ValidationError({"content": "Select unique permanent or primary FDI tooth numbers."})
            if "visit_step" in step:
                link = step["visit_step"]
                if (not isinstance(link, dict) or set(link) != {"id", "plan_id", "position", "service_name"}
                        or any(type(link[key]) is not int or link[key] <= 0 for key in ("id", "plan_id", "position"))
                        or not isinstance(link["service_name"], str) or len(link["service_name"]) > 255):
                    raise ValidationError({"content": "Provide a valid visit step snapshot."})
        if steps and "plan" in values.get("not_applicable", {}):
            raise ValidationError({"content": "A non-applicable plan cannot contain steps."})
        values["plan_steps"] = [dict(step) for step in steps]
    return values


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
    from .clinical_plan_links import validate_plan_links_for_write, store_plan_links
    validate_plan_links_for_write(encounter=current, actor=author, content=content)
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
    store_plan_links(version=version, content=content)
    from .clinical_plan_teeth import store_plan_teeth
    store_plan_teeth(version=version, content=content)
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
        from .clinical_plan_links import verify_plan_links
        verify_plan_links(version=current, content=content)
        from .clinical_plan_teeth import verify_plan_teeth
        verify_plan_teeth(version=current, content=content)
        reason = decrypt_medical_value(current.reason_encrypted, business_id=encounter.business_id,
            subject_id=current.pk, purpose="encounter_reason")
        if len(reason) > 2000:
            raise ValueError
        return {"content": content, "reason": reason}
    except (MedicalEncounterRevision.DoesNotExist, ModelValidationError, ValidationError, ValueError, TypeError, KeyError):
        raise MedicalDataUnavailable() from None
