import json
import uuid

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from .audit_reserve import ReserveUnavailable
from .identity_crypto import decrypt_medical_value


MAX_RESERVE_BYTES = 16384
REFERENCE_FIELDS = frozenset({
    "business_id", "actor_id", "patient_id", "patient_revision", "representative_id",
    "representative_revision", "participation_id", "participation_revision", "encounter_version_id",
    "record_id", "tooth_history_id", "document_version_id", "order_version_id", "file_version_id",
    "identity_correction_id", "correction_access_id", "correction_access_revision",
})


def recover_reserved_read(body, *, expected_event_id):
    """Verify one archived object without mutating or querying the operational database."""
    try:
        if not isinstance(body, bytes) or not 0 < len(body) <= MAX_RESERVE_BYTES:
            raise ValueError
        if str(uuid.UUID(expected_event_id)) != expected_event_id:
            raise ValueError
        envelope = json.loads(body)
        if not isinstance(envelope, dict) or set(envelope) != {"schema", "business_id", "patient_id", "encrypted_event"}:
            raise ValueError
        if type(envelope["schema"]) is not int or envelope["schema"] != 1:
            raise ValueError
        business, patient = envelope["business_id"], envelope["patient_id"]
        if any(type(value) is not int or value <= 0 for value in (business, patient)):
            raise ValueError
        payload = json.loads(decrypt_medical_value(envelope["encrypted_event"],
            business_id=business, subject_id=patient, purpose="read_audit_reserve"))
        if not isinstance(payload, dict) or set(payload) != {"schema", "event_id", "occurred_at", "action", "result", "references"}:
            raise ValueError
        if (type(payload["schema"]) is not int or payload["schema"] != 1 or payload["event_id"] != expected_event_id
                or payload["action"] != "read" or payload["result"] != "authorized"):
            raise ValueError
        occurred = parse_datetime(payload["occurred_at"])
        if occurred is None or timezone.is_naive(occurred):
            raise ValueError
        references = payload["references"]
        if not isinstance(references, dict) or set(references) != REFERENCE_FIELDS:
            raise ValueError
        if any(value is not None and (type(value) is not int or value <= 0) for value in references.values()):
            raise ValueError
        if (references["business_id"] != business or references["patient_id"] != patient
                or references["actor_id"] is None or references["patient_revision"] is None):
            raise ValueError
        return payload
    except Exception:
        raise ReserveUnavailable() from None
