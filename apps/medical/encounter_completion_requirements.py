from django.db.models import F

from .document_content import read_document_revision
from .document_finalization_services import finalization_evidence
from .document_rule_content import read_rule_revision
from .encounter_content import CLINICAL_FIELDS, read_encounter_revision
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocumentFinalization, MedicalDocumentRevision, MedicalDocumentRuleRevision


COMPLETION_MOMENTS = frozenset(("before_treatment", "before_completion"))


def encounter_completion_requirements(version):
    """Readiness under the caller's business lock; this is not an access grant."""
    encounter = version.encounter
    if version.revision != encounter.revision:
        raise MedicalDataUnavailable()
    content = read_encounter_revision(version)["content"]
    missing = [field for field in CLINICAL_FIELDS
        if not content.get(field, "").strip() and not content.get("not_applicable", {}).get(field, "").strip()]
    documents, captured_kinds = [], set()
    versions = MedicalDocumentRevision.objects.select_related("document__encounter").filter(
        document__business_id=encounter.business_id, document__encounter=encounter,
        revision=F("document__revision")).order_by("document_id")
    for document_version in versions:
        rules = read_document_revision(document_version).get("document_rules")
        if rules is None:
            continue
        captured_kinds.add(rules["kind_id"])
        if rules["rule"]["required_at"] not in COMPLETION_MOMENTS:
            continue
        finalization = MedicalDocumentFinalization.objects.select_related("artifact__attachment").filter(version=document_version).first()
        ready = (document_version.document.state == "finalized" and finalization is not None
            and finalization.artifact.attachment.scan_status == "clean"
            and finalization.artifact.attachment.scan_sha256 == finalization.artifact.sha256)
        if ready:
            finalization_evidence(finalization)
        documents.append({"kind_id": rules["kind_id"], "name": rules["name"],
            "version_id": document_version.pk, "ready": ready,
            "blocker": None if ready else "document_not_finalized"})

    # Existing documents retain their captured matrix; current rules identify only
    # kinds that have not yet been instantiated for this encounter.
    current_rules = MedicalDocumentRuleRevision.objects.select_related("kind").filter(
        kind__business_id=encounter.business_id, revision=F("kind__revision")).exclude(kind_id__in=captured_kinds)
    for rule_version in current_rules.order_by("kind_id"):
        matrix = read_rule_revision(rule_version)["content"]
        rule = next((item["rule"] for item in matrix["services"]
            if item["id"] == encounter.appointment.service_id), matrix["default"])
        if rule["required_at"] in COMPLETION_MOMENTS:
            documents.append({"kind_id": rule_version.kind_id, "name": matrix["name"],
                "version_id": None, "ready": False, "blocker": "document_missing"})
    return {"ready": not missing and all(item["ready"] for item in documents),
        "missing_fields": missing, "documents": documents}
