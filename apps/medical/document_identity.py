import json
from datetime import date
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils.dateparse import parse_datetime

from .clinical_identity import assert_verified_clinical_identity
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, iin_digest
from .models import PatientProfile


def _positive(value):
    if type(value) is not int or value < 1:
        raise ValueError


def _timestamp(value):
    parsed = parse_datetime(value) if isinstance(value, str) else None
    if parsed is None or parsed.tzinfo is None:
        raise ValueError


def validate_document_identity(value, *, patient_id):
    if not isinstance(value, dict) or set(value) != {
            "patient_id", "client_id", "revision", "client_updated_at", "full_name",
            "demographics", "iin", "identity_status", "verified_at", "verified_by_id"}:
        raise ValueError
    for key in ("patient_id", "client_id", "revision", "verified_by_id"):
        _positive(value[key])
    if value["patient_id"] != patient_id or value["identity_status"] != "verified":
        raise ValueError
    if not isinstance(value["full_name"], str) or not 1 <= len(value["full_name"]) <= 255:
        raise ValueError
    _timestamp(value["verified_at"])
    _timestamp(value["client_updated_at"])
    identifier = value["iin"]
    if identifier is not None and (not isinstance(identifier, str) or len(identifier) != 12
                                   or not identifier.isascii() or not identifier.isdecimal()):
        raise ValueError
    fields = value["demographics"]
    limits = {"date_of_birth": 10, "sex": 32, "address": 2000}
    if not isinstance(fields, dict) or set(fields) - set(limits):
        raise ValueError
    for key, field in fields.items():
        if not isinstance(field, str) or not field or len(field) > limits[key]:
            raise ValueError
        if key == "date_of_birth" and date.fromisoformat(field).isoformat() != field:
            raise ValueError


def validate_encounter_source(value, *, source):
    if not isinstance(value, dict) or set(value) != {"version_id", "revision", "record_number", "started_at", "timezone"}:
        raise ValueError
    for key in ("version_id", "revision"):
        _positive(value[key])
    if value["version_id"] != source.pk or value["revision"] != source.revision:
        raise ValueError
    if not isinstance(value["record_number"], str) or not 1 <= len(value["record_number"]) <= 64:
        raise ValueError
    _timestamp(value["started_at"])
    if not isinstance(value["timezone"], str):
        raise ValueError
    try:
        ZoneInfo(value["timezone"])
    except (ZoneInfoNotFoundError, ValueError):
        raise ValueError from None


def capture_document_identity(*, encounter, source, business):
    """Internal snapshot builder; caller authorizes and audits the document transaction."""
    patient = PatientProfile.objects.select_for_update().select_related("client").filter(
        pk=encounter.patient_id, business=business, client__business=business).first()
    if patient is None:
        raise MedicalDataUnavailable()
    assert_verified_clinical_identity(patient)
    client = patient.client
    context = {"business_id": business.pk, "subject_id": client.pk}
    try:
        demographics = json.loads(decrypt_medical_value(patient.demographics_encrypted,
            purpose="demographics", **context)) if patient.demographics_encrypted else {}
        identifier = decrypt_medical_value(patient.iin_encrypted, purpose="iin", **context) if patient.iin_encrypted else None
        if (identifier is None) != (patient.iin_digest is None):
            raise ValueError
        identity = {"patient_id": patient.pk, "client_id": client.pk, "revision": patient.revision,
            "client_updated_at": client.updated_at.isoformat(), "full_name": client.full_name,
            "demographics": demographics, "iin": identifier, "identity_status": patient.identity_status,
            "verified_at": patient.verified_at.isoformat(), "verified_by_id": patient.verified_by_id}
        validate_document_identity(identity, patient_id=patient.pk)
        if identifier is not None and iin_digest(identifier, business_id=business.pk) != patient.iin_digest:
            raise ValueError
        clinical_source = {"version_id": source.pk, "revision": source.revision,
            "record_number": encounter.record.number, "started_at": encounter.started_at.isoformat(),
            "timezone": business.timezone}
        validate_encounter_source(clinical_source, source=source)
        return {"patient_identity": identity, "encounter_source": clinical_source}
    except (ValueError, TypeError, KeyError):
        raise MedicalDataUnavailable() from None
