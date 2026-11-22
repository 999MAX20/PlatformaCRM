from django.db import transaction
from django.db.models import F, OuterRef, Q, Subquery
from rest_framework.exceptions import PermissionDenied, ValidationError

from .models import MedicalDocumentTemplateRevision
from .role_access import assert_medical_role_permission
from .template_reviews import _submit_template
from .template_services import (
    _context, _identifier, _save_template_draft, _list_template_versions, assert_common_template_context,
    read_template_version_payload,
)


@transaction.atomic
def common_template_workspace_access(*, actor, business_id):
    business, context = _context(actor, business_id, "view")
    assert_common_template_context(actor, business, context)
    actions = {"view": True}
    for action in ("create", "update", "approve"):
        try:
            permission = assert_medical_role_permission(actor, business, "medical_documents", action)
            actions[action] = permission.scope == "business"
        except PermissionDenied:
            actions[action] = False
    return {"business_id": business.pk, "member_id": context.member_id, "kind": context.kind, "actions": actions}


def list_common_template_versions(*, actor, business_id, template_id, before_revision=None, limit=20):
    return _list_template_versions(actor=actor, business_id=business_id, template_id=template_id,
                                   before_revision=before_revision, limit=limit, common=True)


def save_common_template_draft(*, actor, business_id, title, text, idempotency_key,
                               template_id=None, expected_revision=None, reason="", metadata=None):
    return _save_template_draft(actor=actor, business_id=business_id, title=title, text=text,
        idempotency_key=idempotency_key, template_id=template_id, expected_revision=expected_revision,
        reason=reason, common=True, metadata=metadata)


def submit_common_template(*, actor, business_id, version_id, idempotency_key):
    return _submit_template(actor=actor, business_id=business_id, version_id=version_id,
                            idempotency_key=idempotency_key, common=True)


@transaction.atomic
def read_common_template_version(*, actor, business_id, version_id):
    _identifier(version_id)
    business, context = _context(actor, business_id, "view")
    assert_common_template_context(actor, business, context)
    version = MedicalDocumentTemplateRevision.objects.select_related("template").filter(
        pk=version_id, template__business=business, template__owner_member__isnull=True).first()
    if version is None:
        raise PermissionDenied()
    return read_template_version_payload(actor=actor, business=business, version=version)


@transaction.atomic
def read_approved_template_version(*, actor, business_id, version_id):
    _identifier(version_id)
    business, context = _context(actor, business_id, "view")
    version = _visible_approved_versions(business, context).filter(pk=version_id).first()
    if version is None:
        raise PermissionDenied()
    return read_template_version_payload(actor=actor, business=business, version=version)


def _visible_approved_versions(business, context):
    return MedicalDocumentTemplateRevision.objects.select_related("template").filter(
        template__business=business, review__state="approved").filter(
            Q(template__owner_member__isnull=True) | Q(template__owner_member_id=context.member_id))


def _page(*, actor, business, versions, before_id, limit):
    if before_id is not None:
        _identifier(before_id)
        versions = versions.filter(template_id__lt=before_id)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})
    page = list(versions.order_by("-template_id")[:limit + 1])
    results = []
    for version in page[:limit]:
        payload = read_template_version_payload(actor=actor, business=business, version=version)
        results.append({"template_id": version.template_id, "version_id": version.pk,
            "revision": version.revision, "current_revision": version.template.revision,
            "title": payload["template"]["title"], "created_at": version.created_at,
            "review": payload["review"]})
    return {"results": results, "next_before_id": page[limit - 1].template_id if len(page) > limit else None}


@transaction.atomic
def list_common_template_drafts(*, actor, business_id, before_id=None, limit=20):
    business, context = _context(actor, business_id, "view")
    assert_common_template_context(actor, business, context)
    versions = MedicalDocumentTemplateRevision.objects.select_related("template").filter(
        template__business=business, template__owner_member__isnull=True,
        revision=F("template__revision"))
    return _page(actor=actor, business=business, versions=versions, before_id=before_id, limit=limit)


@transaction.atomic
def list_approved_templates(*, actor, business_id, before_id=None, limit=20):
    business, context = _context(actor, business_id, "view")
    latest = MedicalDocumentTemplateRevision.objects.filter(template_id=OuterRef("template_id"),
        review__state="approved").order_by("-revision").values("pk")[:1]
    versions = _visible_approved_versions(business, context).filter(pk=Subquery(latest))
    return _page(actor=actor, business=business, versions=versions, before_id=before_id, limit=limit)
