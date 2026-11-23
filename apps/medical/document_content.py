import json
import re

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import InvalidTransition
from .encounter_content import read_encounter_revision, validate_clinical_draft
from .credential_snapshot import capture_document_credentials, validate_document_credentials
from .document_identity import capture_document_identity, validate_document_identity, validate_encounter_source
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalDocument, MedicalDocumentRevision, MedicalEncounterRevision


BUSINESS_FIELDS = ("name", "legal_name", "tax_id", "address", "phone", "brand_color", "brand_logo_url")
BRANCH_FIELDS = ("name", "address", "city", "phone")


def validate_document_template(value, code):
    # Template text is stored as data; this layer never evaluates or renders it.
    if not isinstance(value, dict) or set(value) != {"code", "version", "title", "text"}:
        raise ValidationError({"template": "Provide a versioned template snapshot."})
    if (not isinstance(code, str) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", code)
            or value["code"] != code or type(value["version"]) is not int or value["version"] < 1
            or not isinstance(value["title"], str) or not 1 <= len(value["title"]) <= 255 or not value["title"].strip()
            or not isinstance(value["text"], str) or len(value["text"]) > 131072):
        raise ValidationError({"template": "Provide valid template fields."})
    return dict(value)


def validate_document_source(source, template, text):
    if not isinstance(source, dict) or set(source) != {
            "template_id", "version_id", "revision", "review_id", "approved_by", "approved_at"}:
        raise ValidationError({"template_source": "Provide an approved template source."})
    if any(type(source[key]) is not int or source[key] <= 0 for key in source if key != "approved_at"):
        raise ValidationError({"template_source": "Provide valid source identifiers."})
    if source["revision"] != template["version"]:
        raise ValidationError({"template_source": "The source revision must match the template."})
    try:
        timestamp = parse_datetime(source["approved_at"]) if isinstance(source["approved_at"], str) else None
    except ValueError:
        timestamp = None
    if timestamp is None or timestamp.tzinfo is None:
        raise ValidationError({"template_source": "Provide the approval timestamp."})
    if not isinstance(text, str) or len(text) > 131072:
        raise ValidationError({"document_text": "Provide document text of at most 131072 characters."})
    return dict(source)


def _binding(version, document, schema=1):
    return {"schema": schema, "business_id": document.business_id, "document_id": document.pk,
        "encounter_id": document.encounter_id, "template_code": document.template_code,
        "version_id": version.pk, "revision": version.revision,
        "source_version_id": version.source_version_id, "author_id": version.author_id,
        "created_at": version.created_at.isoformat()}


@transaction.atomic
def append_document_revision(*, document, source_version, author, template, reason="",
                             template_source=None, document_text=None):
    """Internal storage: caller must authorize and audit within its outer transaction."""
    template = validate_document_template(template, document.template_code)
    if template_source is not None:
        template_source = validate_document_source(template_source, template, document_text)
    elif document_text is not None:
        raise ValidationError({"document_text": "Select an approved template source."})
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    business = Business.objects.select_for_update().get(pk=document.business_id)
    current = MedicalDocument.objects.select_for_update().get(pk=document.pk, business=business)
    current.full_clean()
    if current.revision != document.revision or current.state != "draft" or current.template_code != template["code"]:
        raise InvalidTransition("The document changed; reload its current revision.")
    source = MedicalEncounterRevision.objects.select_related(
        "encounter__branch", "encounter__primary_clinician__user").get(pk=source_version.pk)
    encounter = source.encounter
    if encounter.pk != current.encounter_id or encounter.business_id != business.pk:
        raise ValidationError({"source": "Select a clinical revision of this encounter."})
    if source.revision != encounter.revision:
        raise InvalidTransition("The clinical source changed; reload its current revision.")
    member = BusinessMember.objects.select_related("user").filter(
        business=business, user_id=author.pk, is_active=True, user__is_active=True).first()
    if member is None:
        raise ValidationError({"author": "Select an active member of this business."})
    clinical = read_encounter_revision(source)["content"]
    staging = encrypt_medical_value("{}", business_id=business.pk,
        subject_id=current.pk, purpose="document_staging")
    version = MedicalDocumentRevision.objects.create(document=current, revision=current.revision + 1,
        source_version=source, author=member.user, snapshot_encrypted=staging)
    payload = {**_binding(version, current, schema=5 if template_source is not None else 1), "snapshot": {
        "template": template, "clinical": clinical, "reason": reason,
        "business": {field: getattr(business, field) for field in BUSINESS_FIELDS},
        "branch": {field: getattr(encounter.branch, field) for field in BRANCH_FIELDS},
        "patient_id": encounter.patient_id, "record_id": encounter.record_id,
        "branch_id": encounter.branch_id, "appointment_id": encounter.appointment_id,
        "prepared_by": {"member_id": member.pk, "user_id": member.user_id, "name": member.user.full_name},
        "performed_by": {"member_id": encounter.primary_clinician_id,
            "user_id": encounter.primary_clinician.user_id, "name": encounter.primary_clinician.user.full_name},
    }}
    if template_source is not None:
        from .document_rule_snapshot import capture_document_rules
        if current.revision:
            previous = MedicalDocumentRevision.objects.filter(document=current, revision=current.revision).first()
            if previous is None:
                raise MedicalDataUnavailable()
            captured_rules = read_document_revision(previous).get("document_rules")
        else:
            captured_rules = capture_document_rules(document=current, template_source=template_source)
        payload["snapshot"]["document_rules"] = captured_rules
        payload["snapshot"].update(template_source=template_source, document_text=document_text)
        payload["snapshot"].update(capture_document_identity(encounter=encounter, source=source, business=business))
        payload["snapshot"]["medical_credentials"] = capture_document_credentials(
            business_id=business.pk, member_id=encounter.primary_clinician_id)
    version.snapshot_encrypted = encrypt_medical_value(json.dumps(payload, ensure_ascii=False, sort_keys=True),
        business_id=business.pk, subject_id=version.pk, purpose="document_snapshot")
    version.save(update_fields=["snapshot_encrypted"])
    current.revision = version.revision
    current.save(update_fields=["revision", "updated_at"])
    return version


@transaction.atomic
def append_document_text_correction(*, document, author, document_text, reason, correction_origin=None):
    """Internal storage for a narrow correction: retain the captured clinical source."""
    business = Business.objects.select_for_update().get(pk=document.business_id)
    current = MedicalDocument.objects.select_for_update().get(pk=document.pk, business=business)
    current.full_clean()
    if current.revision != document.revision or current.state != "draft":
        raise InvalidTransition("The document changed; reload its current draft.")
    previous = MedicalDocumentRevision.objects.filter(document=current, revision=current.revision).first()
    if previous is None:
        raise MedicalDataUnavailable()
    snapshot = read_document_revision(previous)
    from .document_corrections import correction_source, link_correction
    corrected_source = correction_origin or correction_source(previous)
    if "template_source" not in snapshot:
        raise InvalidTransition("This document has no approved text source for correction.")
    validate_document_source(snapshot["template_source"], snapshot["template"], document_text)
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    member = BusinessMember.objects.select_related("user").filter(
        business=business, user_id=author.pk, is_active=True, user__is_active=True).first()
    if member is None:
        raise ValidationError({"author": "Select an active member of this business."})
    snapshot.update(document_text=document_text, reason=reason,
        prepared_by={"member_id": member.pk, "user_id": member.user_id, "name": member.user.full_name})
    schema = 5 if "document_rules" in snapshot else 4 if "medical_credentials" in snapshot else 3 if "patient_identity" in snapshot else 2
    staging = encrypt_medical_value("{}", business_id=business.pk, subject_id=current.pk, purpose="document_staging")
    version = MedicalDocumentRevision.objects.create(document=current, revision=current.revision + 1,
        source_version=previous.source_version, author=member.user, snapshot_encrypted=staging)
    payload = {**_binding(version, current, schema=schema), "snapshot": snapshot}
    version.snapshot_encrypted = encrypt_medical_value(json.dumps(payload, ensure_ascii=False, sort_keys=True),
        business_id=business.pk, subject_id=version.pk, purpose="document_snapshot")
    version.save(update_fields=["snapshot_encrypted"])
    current.revision = version.revision
    current.save(update_fields=["revision", "updated_at"])
    if corrected_source is not None:
        link_correction(version, corrected_source)
    return version


def read_document_revision(version):
    """Internal decryptor: caller must establish current access and durable read audit."""
    try:
        current = MedicalDocumentRevision.objects.select_related("document__encounter", "source_version").get(pk=version.pk)
        document = current.document
        document.clean()
        if current.revision > document.revision or current.source_version.encounter_id != document.encounter_id:
            raise ValueError
        payload = json.loads(decrypt_medical_value(current.snapshot_encrypted,
            business_id=document.business_id, subject_id=current.pk, purpose="document_snapshot"))
        if not isinstance(payload, dict) or type(payload.get("schema")) is not int or payload["schema"] not in (1, 2, 3, 4, 5):
            raise ValueError
        expected = _binding(current, document, schema=payload["schema"])
        if not isinstance(payload, dict) or set(payload) != set(expected) | {"snapshot"}:
            raise ValueError
        if any(type(payload[key]) is not type(value) or payload[key] != value for key, value in expected.items()):
            raise ValueError
        snapshot = payload["snapshot"]
        fields = {
                "template", "clinical", "reason", "business", "branch", "patient_id", "record_id",
                "branch_id", "appointment_id", "prepared_by", "performed_by"}
        if payload["schema"] >= 2:
            fields |= {"template_source", "document_text"}
        if payload["schema"] >= 3:
            fields |= {"patient_identity", "encounter_source"}
        if payload["schema"] >= 4:
            fields.add("medical_credentials")
        if payload["schema"] >= 5:
            fields.add("document_rules")
        if not isinstance(snapshot, dict) or set(snapshot) != fields:
            raise ValueError
        validate_document_template(snapshot["template"], document.template_code)
        if payload["schema"] >= 2:
            validate_document_source(snapshot["template_source"], snapshot["template"], snapshot["document_text"])
        if payload["schema"] >= 3:
            validate_document_identity(snapshot["patient_identity"], patient_id=document.encounter.patient_id)
            validate_encounter_source(snapshot["encounter_source"], source=current.source_version)
        validate_clinical_draft(snapshot["clinical"])
        if not isinstance(snapshot["reason"], str) or len(snapshot["reason"]) > 2000:
            raise ValueError
        for field, keys in (("business", BUSINESS_FIELDS), ("branch", BRANCH_FIELDS)):
            if not isinstance(snapshot[field], dict) or set(snapshot[field]) != set(keys):
                raise ValueError
            if any(not isinstance(value, str) for value in snapshot[field].values()):
                raise ValueError
        for field in ("patient_id", "record_id", "branch_id", "appointment_id"):
            if type(snapshot[field]) is not int or snapshot[field] <= 0:
                raise ValueError
        if any(snapshot[field] != getattr(document.encounter, field) for field in ("patient_id", "record_id")):
            raise ValueError
        for field in ("prepared_by", "performed_by"):
            person = snapshot[field]
            if not isinstance(person, dict) or set(person) != {"member_id", "user_id", "name"}:
                raise ValueError
            if any(type(person[key]) is not int or person[key] <= 0 for key in ("member_id", "user_id")):
                raise ValueError
            if not isinstance(person["name"], str):
                raise ValueError
        if snapshot["prepared_by"]["user_id"] != current.author_id:
            raise ValueError
        if payload["schema"] >= 4:
            validate_document_credentials(snapshot["medical_credentials"], business_id=document.business_id,
                member_id=snapshot["performed_by"]["member_id"])
        if payload["schema"] >= 5:
            from .document_rule_snapshot import validate_document_rules
            validate_document_rules(snapshot["document_rules"], business_id=document.business_id)
        return snapshot
    except (MedicalDocumentRevision.DoesNotExist, ModelValidationError, ValidationError, ValueError, TypeError, KeyError):
        raise MedicalDataUnavailable() from None
