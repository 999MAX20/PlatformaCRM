import re
from zoneinfo import ZoneInfo

from rest_framework.exceptions import ValidationError

from .document_content import BUSINESS_FIELDS, BRANCH_FIELDS
from .document_identity import capture_document_identity
from .credential_snapshot import capture_document_credentials
from .encounter_content import CLINICAL_FIELDS, read_encounter_revision
from .identity_crypto import medical_request_digest


DOCUMENT_FIELDS = (
    "patient.full_name", "patient.date_of_birth", "patient.sex", "patient.address", "patient.iin",
    "clinic.name", "clinic.legal_name", "clinic.tax_id", "clinic.address", "clinic.phone",
    "branch.name", "branch.address", "branch.city", "branch.phone", "doctor.full_name",
    "record.number", "encounter.date", "encounter.time", *[f"clinical.{field}" for field in CLINICAL_FIELDS],
    "clinic.license", "doctor.specialty", "doctor.position", "doctor.qualification",
)
_TOKEN = re.compile(r"\{\{([^{}]{1,128})\}\}")
MAX_TEXT = 131072


def document_source_context(*, business, encounter, source):
    """Internal current data; caller must authorize the patient, encounter and template."""
    return {**capture_document_identity(encounter=encounter, source=source, business=business),
        "medical_credentials": capture_document_credentials(business_id=business.pk, member_id=encounter.primary_clinician_id),
        "business": {field: getattr(business, field) for field in BUSINESS_FIELDS},
        "branch": {field: getattr(encounter.branch, field) for field in BRANCH_FIELDS},
        "doctor": {"member_id": encounter.primary_clinician_id,
                   "name": encounter.primary_clinician.user.full_name},
        "clinical": read_encounter_revision(source)["content"]}


def document_source_digest(*, context, business_id, encounter_id, template_version_id, actor_id):
    return medical_request_digest({"source": context, "encounter_id": encounter_id,
        "template_version_id": template_version_id, "actor_id": actor_id}, business_id=business_id)


def document_snapshot_context(snapshot):
    return {key: snapshot[key] for key in ("patient_identity", "encounter_source", "business", "branch", "clinical")} | {
        "doctor": {"member_id": snapshot["performed_by"]["member_id"], "name": snapshot["performed_by"]["name"]},
        "medical_credentials": snapshot.get("medical_credentials", {"clinic": None, "clinician": None})}


def render_document_text(template_text, context, *, started_at):
    if not isinstance(template_text, str) or len(template_text) > MAX_TEXT:
        raise ValidationError({"template": "Provide template text of at most 131072 characters."})
    patient = context["patient_identity"]
    demographics = patient["demographics"]
    local = started_at.astimezone(ZoneInfo(context["encounter_source"]["timezone"]))
    credentials = context.get("medical_credentials", {})
    clinic = (credentials.get("clinic") or {}).get("content", {})
    clinician = (credentials.get("clinician") or {}).get("content", {})
    values = {"patient.full_name": patient["full_name"], "patient.iin": patient["iin"],
        **{f"patient.{field}": demographics.get(field) for field in ("date_of_birth", "sex", "address")},
        **{f"clinic.{field}": context["business"][field] for field in ("name", "legal_name", "tax_id", "address", "phone")},
        **{f"branch.{field}": context["branch"][field] for field in ("name", "address", "city", "phone")},
        "doctor.full_name": context["doctor"]["name"], "record.number": context["encounter_source"]["record_number"],
        "clinic.license": clinic.get("license"),
        **{f"doctor.{field}": clinician.get(field) for field in ("specialty", "position", "qualification")},
        "encounter.date": local.date().isoformat(), "encounter.time": local.timetz().isoformat(),
        **{f"clinical.{field}": context["clinical"].get(field) for field in CLINICAL_FIELDS}}
    parts, missing, unknown = [], set(), set()
    length, offset = 0, 0

    def append(value):
        nonlocal length
        length += len(value)
        if length > MAX_TEXT:
            raise ValidationError({"document_text": "The rendered document exceeds 131072 characters."})
        parts.append(value)

    for match in _TOKEN.finditer(template_text):
        append(template_text[offset:match.start()])
        field = match.group(1).strip()
        if field not in values:
            unknown.add(field)
            append(match.group())
        else:
            value = values[field]
            if value in (None, ""):
                missing.add(field)
            append(value or "")
        offset = match.end()
    append(template_text[offset:])
    return {"document_text": "".join(parts), "missing_fields": sorted(missing), "unknown_fields": sorted(unknown)}
