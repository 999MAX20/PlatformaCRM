from apps.core.domain_errors import InvalidTransition
from .document_content import read_document_revision
from .document_head_review import document_review_submission
from .document_requirements import snapshot_required_fields
from .models import MedicalDocumentHeadConfirmation


def document_signing_prerequisites(version):
    """Content/review readiness only; caller enforces action ACL and lifecycle under locks."""
    snapshot = read_document_revision(version)
    rules = snapshot.get("document_rules")
    fields = snapshot_required_fields(snapshot)
    document = version.document
    submission = document_review_submission(version)
    blockers = []
    if rules is None:
        blockers.append("rules_missing")
    if version.revision != document.revision:
        blockers.append("version_outdated")
    missing_fields = [item["field"] for item in fields or [] if not item["present"]]
    if missing_fields:
        blockers.append("required_fields_missing")
    if submission is None or document.state != "reviewed":
        blockers.append("primary_review_missing")
    head_required = rules is not None and "medical_head" in rules["rule"]["reviewers"]
    if head_required and (submission is None or not MedicalDocumentHeadConfirmation.objects.filter(submission=submission).exists()):
        blockers.append("head_review_missing")
    return {"ready": not blockers, "blockers": blockers, "missing_fields": missing_fields,
        "submission_id": submission.pk if submission else None,
        "rule_version_id": rules["version_id"] if rules else None,
        "signers": list(rules["rule"]["signers"]) if rules else []}


def assert_document_signing_prerequisites(version):
    prerequisites = document_signing_prerequisites(version)
    if not prerequisites["ready"]:
        raise InvalidTransition("Document requirements or exact-version reviews are incomplete.")
    return prerequisites
