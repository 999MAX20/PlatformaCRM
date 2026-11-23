from django.db import transaction
from django.utils.dateparse import parse_datetime

from .audit import write_patient_audit
from .document_artifact_access import document_artifact_access
from .document_content import read_document_revision
from .document_rendering import document_snapshot_context, render_document_text


def snapshot_required_fields(snapshot):
    """Inspect a validated immutable snapshot; never fill from current CRM data."""
    rules = snapshot.get("document_rules")
    if rules is None:
        return None
    context = document_snapshot_context(snapshot)
    started_at = parse_datetime(snapshot["encounter_source"]["started_at"])
    fields = []
    for field in rules["rule"]["required_fields"]:
        rendered = render_document_text("{{" + field + "}}", context, started_at=started_at)
        fields.append({"field": field, "present": bool(rendered["document_text"].strip())
            and not rendered["missing_fields"] and not rendered["unknown_fields"]})
    return fields


@transaction.atomic
def read_document_requirements(*, actor, business_id, patient_id, version_id, **basis):
    context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
        version_id=version_id, **basis)
    snapshot = read_document_revision(context.version)
    fields = snapshot_required_fields(snapshot)
    rules = snapshot.get("document_rules")
    document = context.version.document
    write_patient_audit(actor=actor, business=context.business, patient=context.patient,
        action="read", document_version=context.version, correction_access=context.correction)
    return {"version_id": context.version.pk, "revision": context.version.revision,
        "current": context.version.revision == document.revision, "document_state": document.state,
        "state_revision": document.state_revision, "configured": fields is not None,
        "fields": fields or [], "fields_complete": fields is not None and all(item["present"] for item in fields),
        "rule_version_id": rules["version_id"] if rules else None}
