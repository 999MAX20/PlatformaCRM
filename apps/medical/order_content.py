import json
import re

from rest_framework.exceptions import ValidationError

from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .document_content import validate_document_source, validate_document_template


ORDER_KINDS = ("medication", "imaging", "laboratory", "consultation", "hygiene", "follow_up", "other")
MEDICATION_FIELDS = ("name", "dose", "route", "frequency", "duration")


def validate_order_content(content):
    if not isinstance(content, dict) or set(content) != {"kind", "text", "medication"}:
        raise ValidationError({"content": "Provide order kind, text and medication fields."})
    if content["kind"] not in ORDER_KINDS:
        raise ValidationError({"content": "Select a supported order kind."})
    if not isinstance(content["text"], str) or len(content["text"]) > 32768:
        raise ValidationError({"content": "Provide text of at most 32768 characters."})
    medication = content["medication"]
    if not isinstance(medication, dict) or set(medication) - set(MEDICATION_FIELDS):
        raise ValidationError({"content": "Provide supported medication fields."})
    if any(not isinstance(value, str) or len(value) > 2000 for value in medication.values()):
        raise ValidationError({"content": "Medication fields must be text of at most 2000 characters."})
    if content["kind"] != "medication" and medication:
        raise ValidationError({"content": "Medication fields require a medication order."})
    return {"kind": content["kind"], "text": content["text"], "medication": dict(medication)}


def _metadata(version):
    order = version.order
    return {"schema": 2 if version.template_version_id else 1, "business_id": order.business_id, "encounter_id": order.encounter_id,
            "order_id": order.pk, "version_id": version.pk, "revision": version.revision,
            "author_id": version.author_id, "created_at": version.created_at.isoformat(),
            **({"template_version_id": version.template_version_id, "source_version_id": version.source_version_id}
               if version.template_version_id else {})}


def _template_source(version, value, text):
    if not isinstance(value, dict) or set(value) != {"template", "approval", "source_digest"}:
        raise ValidationError({"template_source": "Provide the exact template provenance."})
    template = validate_document_template(value["template"],
        value["template"].get("code") if isinstance(value["template"], dict) else None)
    approval = validate_document_source(value["approval"], template, text)
    if (approval["version_id"] != version.template_version_id or not version.source_version_id or
            not isinstance(value["source_digest"], str) or not re.fullmatch(r"[a-f0-9]{64}", value["source_digest"])):
        raise ValidationError({"template_source": "The source does not match this order version."})
    return value


def encrypt_order_revision(version, *, content, reason, template_source=None):
    payload = {**_metadata(version), "content": validate_order_content(content), "reason": reason}
    if version.template_version_id:
        payload["template_source"] = _template_source(version, template_source, content["text"])
    return encrypt_medical_value(json.dumps(payload, ensure_ascii=False, sort_keys=True),
        business_id=version.order.business_id, subject_id=version.pk, purpose="order_content")


def read_order_revision(version):
    try:
        data = json.loads(decrypt_medical_value(version.content_encrypted,
            business_id=version.order.business_id, subject_id=version.pk, purpose="order_content"))
        metadata = _metadata(version)
        extra = {"template_source"} if version.template_version_id else set()
        if not isinstance(data, dict) or set(data) != set(metadata) | {"content", "reason"} | extra:
            raise ValueError
        if any(type(data[key]) is not type(value) or data[key] != value for key, value in metadata.items()):
            raise ValueError
        if not isinstance(data["reason"], str) or len(data["reason"]) > 2000:
            raise ValueError
        result = {"content": validate_order_content(data["content"]), "reason": data["reason"]}
        if version.template_version_id:
            result["template_source"] = _template_source(version, data["template_source"], data["content"]["text"])
        return result
    except (ValueError, TypeError, KeyError, ValidationError):
        raise MedicalDataUnavailable() from None
