import json

from rest_framework.exceptions import ValidationError

from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value


MOMENTS = ("optional", "before_treatment", "before_completion", "before_issue")
REVIEWERS = ("primary_clinician", "medical_head")
SIGNERS = ("primary_clinician", "patient_or_representative", "medical_head")


def _distinct(values, allowed, field):
    if (not isinstance(values, list) or any(not isinstance(value, str) or value not in allowed for value in values)
            or len(set(values)) != len(values)):
        raise ValidationError({field: "Select distinct supported values."})
    return list(values)


def validate_rule(value):
    from .document_rendering import DOCUMENT_FIELDS

    if not isinstance(value, dict) or set(value) != {"required_at", "required_fields", "reviewers", "signers", "issuable"}:
        raise ValidationError({"rules": "Provide the document requirements, reviewers, signers and issuance rule."})
    if value["required_at"] not in MOMENTS or type(value["issuable"]) is not bool:
        raise ValidationError({"rules": "Select an obligation moment and issuance permission."})
    fields = _distinct(value["required_fields"], DOCUMENT_FIELDS, "required_fields")
    reviewers = _distinct(value["reviewers"], REVIEWERS, "reviewers")
    signers = _distinct(value["signers"], SIGNERS, "signers")
    if "primary_clinician" not in reviewers:
        raise ValidationError({"reviewers": "The primary clinician must confirm the document contents."})
    if value["required_at"] == "before_issue" and not value["issuable"]:
        raise ValidationError({"issuable": "An internal document cannot be required for issuance."})
    return {**value, "required_fields": fields, "reviewers": reviewers, "signers": signers}


def validate_rule_content(value):
    if not isinstance(value, dict) or set(value) != {"name", "docx_allowed", "validation", "default", "services", "templates"}:
        raise ValidationError({"rules": "Provide a versioned document rule matrix."})
    if (not isinstance(value["name"], str) or not value["name"].strip() or len(value["name"]) > 255
            or type(value["docx_allowed"]) is not bool or value["validation"] != "synthetic"):
        raise ValidationError({"rules": "Provide a name and explicit draft export permission for the test matrix."})
    services = value["services"]
    if not isinstance(services, list) or len(services) > 50:
        raise ValidationError({"services": "Provide at most 50 service-specific rules."})
    seen, rows = set(), []
    for item in services:
        if (not isinstance(item, dict) or set(item) != {"id", "name", "rule"}
                or type(item["id"]) is not int or item["id"] <= 0 or item["id"] in seen
                or not isinstance(item["name"], str) or not item["name"] or len(item["name"]) > 255):
            raise ValidationError({"services": "Provide distinct service snapshots."})
        seen.add(item["id"])
        rows.append({**item, "rule": validate_rule(item["rule"])})
    templates = value["templates"]
    if (not isinstance(templates, list) or len(templates) > 100 or any(not isinstance(item, dict)
            or set(item) != {"id", "title"} or type(item["id"]) is not int or item["id"] <= 0
            or not isinstance(item["title"], str) or not item["title"].strip() or len(item["title"]) > 255 for item in templates)
            or len({item["id"] for item in templates}) != len(templates)):
        raise ValidationError({"template_ids": "Select at most 100 distinct templates."})
    return {**value, "default": validate_rule(value["default"]), "services": rows, "templates": [dict(item) for item in templates]}


def rule_binding(version):
    return {"schema": 1, "business_id": version.kind.business_id, "kind_id": version.kind_id,
        "version_id": version.pk, "revision": version.revision, "author_id": version.author_id,
        "created_at": version.created_at.isoformat()}


def read_rule_revision(version):
    """Internal decoder; the caller authorizes and audits access."""
    from .models import MedicalDocumentRuleRevision

    try:
        version = MedicalDocumentRuleRevision.objects.select_related("kind").get(pk=version.pk)
        payload = json.loads(decrypt_medical_value(version.snapshot_encrypted,
            business_id=version.kind.business_id, subject_id=version.pk, purpose="document_rules"))
        binding = rule_binding(version)
        if (version.revision > version.kind.revision or not isinstance(payload, dict)
                or set(payload) != set(binding) | {"content", "reason"}
                or any(type(payload[key]) is not type(item) or payload[key] != item for key, item in binding.items())
                or not isinstance(payload["reason"], str) or len(payload["reason"]) > 2000):
            raise ValueError
        return {**binding, "content": validate_rule_content(payload["content"]), "reason": payload["reason"]}
    except (MedicalDocumentRuleRevision.DoesNotExist, ValueError, TypeError, KeyError, ValidationError):
        raise MedicalDataUnavailable() from None
