import uuid

from django.db import transaction
from django.db.models import F
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.services.models import Service
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .document_content import validate_document_template
from .document_templates import append_template_revision, read_template_revision
from .identity_crypto import MedicalDataUnavailable, medical_request_digest
from .models import MedicalDocumentTemplate, MedicalDocumentTemplateRevision, MedicalRoleAssignment
from .role_access import assert_medical_role_permission
from .template_audit import write_template_audit
from .template_metadata import capture_template_metadata
from .template_search import template_search_filters, search_template_page


def _identifier(value):
    if type(value) is not int or value <= 0:
        raise ValidationError({"template": "Provide valid identifiers and revisions."})


def _context(actor, business_id, action):
    _identifier(business_id)
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    context = assert_medical_role_permission(actor, business, "medical_documents", action)
    if context.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        raise PermissionDenied()
    return business, context


@transaction.atomic
def personal_template_workspace_access(*, actor, business_id):
    business, context = _context(actor, business_id, "view")
    actions = {"view": True}
    for action in ("create", "update"):
        try:
            assert_medical_role_permission(actor, business, "medical_documents", action)
        except PermissionDenied:
            actions[action] = False
        else:
            actions[action] = True
    try:
        approval = assert_medical_role_permission(actor, business, "medical_documents", "approve")
        actions["approve"] = approval.scope == "business" and context.scope == "business"
    except PermissionDenied:
        actions["approve"] = False
    return {"business_id": business.pk, "member_id": context.member_id,
            "kind": context.kind, "actions": actions}


@transaction.atomic
def template_service_options(*, actor, business_id, before_id=None, limit=20, q=""):
    business, _ = _context(actor, business_id, "view")
    if before_id is not None:
        _identifier(before_id)
    if type(limit) is not int or not 1 <= limit <= 50 or not isinstance(q, str) or len(q) > 255:
        raise ValidationError({"services": "Provide a valid search and page size."})
    services = Service.objects.filter(business=business).order_by("-pk")
    if q.strip():
        services = services.filter(name__icontains=q.strip())
    if before_id is not None:
        services = services.filter(pk__lt=before_id)
    page = list(services.values("id", "name")[:limit + 1])
    return {"results": page[:limit], "next_before_id": page[limit - 1]["id"] if len(page) > limit else None}


def save_personal_template_draft(*, actor, business_id, title, text, idempotency_key,
                                 template_id=None, expected_revision=None, reason="", metadata=None):
    return _save_template_draft(actor=actor, business_id=business_id, title=title, text=text,
        idempotency_key=idempotency_key, template_id=template_id, expected_revision=expected_revision, reason=reason,
        metadata=metadata)


def assert_common_template_context(actor, business, context):
    viewing = assert_medical_role_permission(actor, business, "medical_documents", "view")
    if context.kind != MedicalRoleAssignment.Kinds.HEAD or context.scope != "business" or viewing.scope != "business":
        raise PermissionDenied()


@transaction.atomic
def _save_template_draft(*, actor, business_id, title, text, idempotency_key,
                         template_id=None, expected_revision=None, reason="", common=False, metadata=None):
    if template_id is not None:
        _identifier(template_id)
        _identifier(expected_revision)
    elif expected_revision is not None:
        raise ValidationError({"expected_revision": "A new template has no expected revision."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})
    validate_document_template({"code": "draft", "version": 1, "title": title, "text": text}, "draft")
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    action = "create" if template_id is None else "update"
    business, context = _context(actor, business_id, action)
    if common:
        assert_common_template_context(actor, business, context)
    owner_id = None if common else context.member_id
    template = None
    if template_id is not None:
        template = MedicalDocumentTemplate.objects.select_for_update().filter(pk=template_id,
            business=business, owner_member_id=owner_id).first()
        if template is None:
            raise PermissionDenied()

    def operation():
        if template is not None and template.revision != expected_revision:
            raise InvalidTransition("The template changed; reload its current revision.")
        classification = capture_template_metadata(metadata, business_id=business_id) if metadata is not None else None
        if metadata is None and template is not None:
            previous = MedicalDocumentTemplateRevision.objects.filter(template=template, revision=template.revision).first()
            if previous is None:
                raise MedicalDataUnavailable()
            classification = read_template_revision(previous).get("metadata")
        draft = template or MedicalDocumentTemplate.objects.create(business=business,
            owner_member_id=owner_id, code=("common_" if common else "personal_") + uuid.uuid4().hex)
        version = append_template_revision(template=draft, author=actor, title=title, text=text, reason=reason,
                                           metadata=classification)
        write_template_audit(actor=actor, business=business, version=version,
            action="template_draft_created" if template is None else "template_draft_saved")
        return CRMCommandResult(data={}, status_code=201 if template is None else 200, resource=version)

    result = run_idempotent_crm_command(business=business, actor=actor,
        action=("medical.template.common." if common else "medical.template.") + action,
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"template": template_id, "revision": expected_revision,
            "content_digest": medical_request_digest({"title": title, "text": text, "reason": reason,
                **({"metadata": metadata} if metadata is not None else {})}, business_id=business_id)},
        operation=operation)
    version = MedicalDocumentTemplateRevision.objects.get(template__business=business,
        template__owner_member_id=owner_id, pk=result.resource_id if result.replayed else result.resource.pk)
    return version, result.replayed


@transaction.atomic
def read_personal_template_version(*, actor, business_id, version_id):
    _identifier(version_id)
    business, context = _context(actor, business_id, "view")
    version = MedicalDocumentTemplateRevision.objects.select_related("template").filter(pk=version_id,
        template__business=business, template__owner_member_id=context.member_id).first()
    if version is None:
        raise PermissionDenied()
    return read_template_version_payload(actor=actor, business=business, version=version)


def read_template_version_payload(*, actor, business, version):
    """Internal audited payload; the caller must authorize the version's visibility."""
    write_template_audit(actor=actor, business=business, version=version, action="read")
    snapshot = read_template_revision(version)
    from .template_reviews import read_review_decision
    from .models import MedicalTemplateReview
    review = MedicalTemplateReview.objects.filter(version=version).first()
    summary = None
    if review is not None:
        summary = {"state": review.state, "submitted_at": review.submitted_at.isoformat(),
            "decided_at": review.decided_at.isoformat() if review.decided_at else None,
            "decision_reason": read_review_decision(review, snapshot["template"])}
    return {"template_id": version.template_id, "version_id": version.pk, "revision": version.revision,
        "current_revision": version.template.revision, "author_id": version.author_id,
        "created_at": version.created_at, "review": summary,
        "availability": {"is_active": version.template.is_active, "revision": version.template.availability_revision}, **snapshot}


@transaction.atomic
def list_personal_template_drafts(*, actor, business_id, before_id=None, limit=20,
                                  q="", language="", category="", specialty="", service_id=None):
    if before_id is not None:
        _identifier(before_id)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})
    business, context = _context(actor, business_id, "view")
    filters = template_search_filters(q=q, language=language, category=category, specialty=specialty, service_id=service_id)
    if any(filters.values()):
        versions = MedicalDocumentTemplateRevision.objects.select_related("template").filter(
            template__business=business, template__owner_member_id=context.member_id, revision=F("template__revision"))
        return search_template_page(actor=actor, business=business, versions=versions, filters=filters,
                                    before_id=before_id, limit=limit)
    templates = MedicalDocumentTemplate.objects.filter(business=business, owner_member_id=context.member_id,
        revision__gte=1).order_by("-pk")
    if before_id is not None:
        templates = templates.filter(pk__lt=before_id)
    page = list(templates[:limit + 1])
    versions = {item.template_id: item for item in MedicalDocumentTemplateRevision.objects.select_related("template").filter(
        template_id__in=[item.pk for item in page[:limit]], revision=F("template__revision"))}
    rows = []
    for template in page[:limit]:
        version = versions.get(template.pk)
        if version is None:
            raise MedicalDataUnavailable()
        write_template_audit(actor=actor, business=business, version=version, action="read")
        content = read_template_revision(version)["template"]
        rows.append({"template_id": template.pk, "version_id": version.pk, "revision": version.revision,
                     "title": content["title"], "created_at": version.created_at})
    return {"results": rows, "next_before_id": rows[-1]["template_id"] if len(page) > limit else None}


def list_personal_template_versions(*, actor, business_id, template_id, before_revision=None, limit=20):
    return _list_template_versions(actor=actor, business_id=business_id, template_id=template_id,
                                   before_revision=before_revision, limit=limit)


@transaction.atomic
def _list_template_versions(*, actor, business_id, template_id, before_revision=None, limit=20, common=False):
    _identifier(template_id)
    if before_revision is not None:
        _identifier(before_revision)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})
    business, context = _context(actor, business_id, "view")
    if common:
        assert_common_template_context(actor, business, context)
    template = MedicalDocumentTemplate.objects.filter(pk=template_id,
        business=business, owner_member_id=None if common else context.member_id).first()
    if template is None:
        raise PermissionDenied()
    versions = MedicalDocumentTemplateRevision.objects.filter(template=template,
        revision__lte=template.revision).order_by("-revision")
    if not versions.filter(revision=template.revision).exists():
        raise MedicalDataUnavailable()
    if before_revision is not None:
        versions = versions.filter(revision__lt=before_revision)
    page = list(versions[:limit + 1])
    for version in page[:limit]:
        write_template_audit(actor=actor, business=business, version=version, action="read")
    rows = [{"version_id": version.pk, "revision": version.revision,
             "author_id": version.author_id, "created_at": version.created_at} for version in page[:limit]]
    return {"template_id": template.pk, "current_revision": template.revision, "results": rows,
            "next_before_revision": rows[-1]["revision"] if len(page) > limit else None}
