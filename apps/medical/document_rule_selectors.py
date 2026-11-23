from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import PermissionDenied, ValidationError

from .document_rule_content import MOMENTS, REVIEWERS, SIGNERS, read_rule_revision
from .document_rule_services import audit_rule, rule_context
from .models import MedicalDocumentKind, MedicalDocumentRuleRevision
from .role_access import assert_medical_role_permission


def _page(before_id, limit):
    if (before_id is not None and (type(before_id) is not int or before_id <= 0)) or type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"page": "Select a positive cursor and a page size up to 50."})


@transaction.atomic
def document_rule_access(*, actor, business_id):
    from .document_rendering import DOCUMENT_FIELDS

    business = rule_context(actor=actor, business_id=business_id)
    try:
        permission = assert_medical_role_permission(actor, business, "medical_documents", "approve")
        allowed = permission.scope == "business"
    except PermissionDenied:
        allowed = False
    return {"business_id": business.pk, "actions": {"view": True, "save": allowed},
        "validation": "synthetic", "fields": DOCUMENT_FIELDS, "moments": MOMENTS,
        "reviewers": REVIEWERS, "signers": SIGNERS}


@transaction.atomic
def list_document_rules(*, actor, business_id, before_id=None, limit=20, q=""):
    _page(before_id, limit)
    if not isinstance(q, str) or len(q) > 255:
        raise ValidationError({"q": "Provide a search of at most 255 characters."})
    business = rule_context(actor=actor, business_id=business_id)
    versions = MedicalDocumentRuleRevision.objects.select_related("kind").filter(kind__business=business,
        revision=F("kind__revision"))
    rows, cursor = [], before_id
    while True:
        batch = list((versions.filter(kind_id__lt=cursor) if cursor is not None else versions).order_by("-kind_id")[:50])
        if not batch:
            return {"results": rows, "next_before_id": None}
        for version in batch:
            payload = read_rule_revision(version)
            audit_rule(actor=actor, business=business, version=version)
            if q.strip().casefold() not in payload["content"]["name"].casefold():
                continue
            if len(rows) == limit:
                return {"results": rows, "next_before_id": rows[-1]["kind_id"]}
            rows.append(payload)
        if len(batch) < 50:
            return {"results": rows, "next_before_id": None}
        cursor = batch[-1].kind_id


@transaction.atomic
def document_rule_history(*, actor, business_id, kind_id, before_id=None, limit=20):
    _page(before_id, limit)
    business = rule_context(actor=actor, business_id=business_id)
    if type(kind_id) is not int or kind_id <= 0:
        raise ValidationError({"kind": "Select a document kind."})
    kind = MedicalDocumentKind.objects.filter(pk=kind_id, business=business).first()
    if kind is None:
        raise PermissionDenied()
    versions = MedicalDocumentRuleRevision.objects.select_related("kind").filter(kind=kind)
    if before_id is not None:
        versions = versions.filter(pk__lt=before_id)
    page = list(versions.order_by("-pk")[:limit + 1])
    rows = []
    for version in page[:limit]:
        rows.append(read_rule_revision(version))
        audit_rule(actor=actor, business=business, version=version)
    return {"kind_id": kind.pk, "current_revision": kind.revision, "results": rows,
        "next_before_id": page[limit - 1].pk if len(page) > limit else None}
