from rest_framework.exceptions import ValidationError

from .document_rule_content import read_rule_revision, validate_rule
from .identity_crypto import MedicalDataUnavailable


def capture_document_rules(*, document, template_source):
    """Called under the document writer's business lock, for a new document only."""
    from .models import MedicalDocumentRuleRevision, MedicalDocumentTemplate

    template = MedicalDocumentTemplate.objects.select_related("document_kind").filter(
        pk=template_source["template_id"], business_id=document.business_id,
        code=document.template_code).first()
    if template is None:
        raise MedicalDataUnavailable()
    if template.document_kind_id is None:
        return None
    if template.document_kind.business_id != document.business_id:
        raise MedicalDataUnavailable()
    version = MedicalDocumentRuleRevision.objects.filter(kind=template.document_kind,
        revision=template.document_kind.revision).first()
    if version is None:
        raise MedicalDataUnavailable()
    content = read_rule_revision(version)["content"]
    if template.pk not in [item["id"] for item in content["templates"]]:
        raise MedicalDataUnavailable()
    service_id = document.encounter.appointment.service_id
    selected = next((item["rule"] for item in content["services"] if item["id"] == service_id), content["default"])
    return {"business_id": document.business_id, "kind_id": version.kind_id, "version_id": version.pk,
        "revision": version.revision, "name": content["name"], "validation": content["validation"],
        "docx_allowed": content["docx_allowed"], "service_id": service_id, "rule": selected}


def validate_document_rules(value, *, business_id):
    if value is None:
        return None
    if not isinstance(value, dict) or set(value) != {"business_id", "kind_id", "version_id", "revision",
            "name", "validation", "docx_allowed", "service_id", "rule"}:
        raise ValidationError({"document_rules": "Provide captured document rules."})
    if (any(type(value[key]) is not int or value[key] <= 0 for key in
            ("business_id", "kind_id", "version_id", "revision", "service_id"))
            or value["business_id"] != business_id or value["validation"] != "synthetic"
            or type(value["docx_allowed"]) is not bool or not isinstance(value["name"], str)
            or not value["name"].strip() or len(value["name"]) > 255):
        raise ValidationError({"document_rules": "Provide valid rule identity and settings."})
    return {**value, "rule": validate_rule(value["rule"])}
