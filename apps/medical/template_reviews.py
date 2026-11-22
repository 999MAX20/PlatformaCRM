import hashlib
import json

from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .document_templates import read_template_revision
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value, medical_request_digest
from .models import MedicalDocumentTemplateRevision, MedicalTemplateReview
from .role_access import assert_medical_role_permission
from .template_audit import write_template_audit
from .template_services import _context, _identifier, assert_common_template_context


def _key(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})


def _version(business, version_id):
    _identifier(version_id)
    version = MedicalDocumentTemplateRevision.objects.select_related("template").filter(
        pk=version_id, template__business=business).first()
    if version is None:
        raise PermissionDenied()
    return version


def _head(actor, business):
    approval = assert_medical_role_permission(actor, business, "medical_documents", "approve")
    viewing = assert_medical_role_permission(actor, business, "medical_documents", "view")
    if approval.scope != "business" or viewing.scope != "business":
        raise PermissionDenied()


def _digest(content):
    return hashlib.sha256(json.dumps(content, ensure_ascii=False, sort_keys=True,
                                    separators=(",", ":")).encode("utf-8")).hexdigest()


def _binding(review):
    return {"schema": 1, "review_id": review.pk, "version_id": review.version_id,
            "submitted_by": review.submitted_by_id, "submitted_at": review.submitted_at.isoformat(),
            "state": review.state, "decided_by": review.decided_by_id,
            "decided_at": review.decided_at.isoformat() if review.decided_at else None}


def read_review_decision(review, content):
    """Internal receipt verification; callers authorize and audit the exact version first."""
    if review.state == "pending":
        if review.decided_by_id is not None or review.decided_at is not None or review.decision_encrypted:
            raise MedicalDataUnavailable()
        return ""
    try:
        expected = _binding(review)
        payload = json.loads(decrypt_medical_value(review.decision_encrypted,
            business_id=review.version.template.business_id, subject_id=review.pk, purpose="template_review"))
        if not isinstance(payload, dict) or set(payload) != set(expected) | {"reason", "content_digest"}:
            raise ValueError
        if any(type(payload[key]) is not type(value) or payload[key] != value for key, value in expected.items()):
            raise ValueError
        if review.state not in {"approved", "rejected"} or payload["content_digest"] != _digest(content):
            raise ValueError
        reason = payload["reason"]
        if not isinstance(reason, str) or len(reason) > 2000 or (review.state == "rejected" and not reason.strip()):
            raise ValueError
        return reason
    except (ValueError, TypeError, KeyError, AttributeError):
        raise MedicalDataUnavailable() from None


def submit_personal_template(*, actor, business_id, version_id, idempotency_key):
    return _submit_template(actor=actor, business_id=business_id, version_id=version_id,
                            idempotency_key=idempotency_key)


@transaction.atomic
def _submit_template(*, actor, business_id, version_id, idempotency_key, common=False):
    _key(idempotency_key)
    business, context = _context(actor, business_id, "update")
    assert_medical_role_permission(actor, business, "medical_documents", "view")
    version = _version(business, version_id)
    if common:
        assert_common_template_context(actor, business, context)
    if version.template.owner_member_id != (None if common else context.member_id):
        raise PermissionDenied()

    def operation():
        if version.revision != version.template.revision:
            raise InvalidTransition("The template changed; submit its current version.")
        if MedicalTemplateReview.objects.filter(version=version).exists():
            raise InvalidTransition("This version already has a review. Read its current decision.")
        read_template_revision(version)
        review = MedicalTemplateReview(version=version, submitted_by=actor)
        review.save()
        review.full_clean()
        write_template_audit(actor=actor, business=business, version=version, action="template_submitted")
        return CRMCommandResult(data={}, status_code=201, resource=review)

    result = run_idempotent_crm_command(business=business, actor=actor,
        action="medical.template.common.submit" if common else "medical.template.submit",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"version": version_id}, operation=operation)
    review = MedicalTemplateReview.objects.get(version__template__business=business,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return review, result.replayed


@transaction.atomic
def decide_template_review(*, actor, business_id, version_id, decision, reason, idempotency_key):
    _key(idempotency_key)
    if not isinstance(decision, str) or decision not in {"approved", "rejected"}:
        raise ValidationError({"decision": "Select approve or reject."})
    if not isinstance(reason, str) or len(reason) > 2000 or (decision == "rejected" and not reason.strip()):
        raise ValidationError({"reason": "Provide a reason for rejection, at most 2000 characters."})
    business, _ = _context(actor, business_id, "approve")
    _head(actor, business)
    version = _version(business, version_id)
    review = MedicalTemplateReview.objects.select_for_update().filter(version=version).first()
    if review is None:
        raise PermissionDenied()

    def operation():
        if review.state != "pending":
            raise InvalidTransition("This template version already has a decision.")
        if version.revision != version.template.revision:
            raise InvalidTransition("The template changed; review its new submitted version.")
        content = read_template_revision(version)["template"]
        review.state = decision
        review.decided_by = actor
        review.decided_at = timezone.now()
        review.decision_encrypted = encrypt_medical_value(json.dumps({**_binding(review),
            "reason": reason, "content_digest": _digest(content)}, ensure_ascii=False, sort_keys=True),
            business_id=business_id, subject_id=review.pk, purpose="template_review")
        review.full_clean()
        review.save(update_fields=["state", "decided_by", "decided_at", "decision_encrypted"])
        write_template_audit(actor=actor, business=business, version=version, action="template_" + decision)
        return CRMCommandResult(data={}, status_code=200, resource=review)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.template.decide",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"version": version_id, "decision": decision,
                 "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}, operation=operation)
    review.refresh_from_db()
    return review, result.replayed


@transaction.atomic
def read_submitted_template(*, actor, business_id, version_id):
    business, context = _context(actor, business_id, "view")
    version = _version(business, version_id)
    review = MedicalTemplateReview.objects.filter(version=version).first()
    if review is None:
        raise PermissionDenied()
    if version.template.owner_member_id != context.member_id:
        _head(actor, business)
    write_template_audit(actor=actor, business=business, version=version, action="read")
    snapshot = read_template_revision(version)
    reason = read_review_decision(review, snapshot["template"])
    return {"review_id": review.pk, "version_id": version.pk, "template_id": version.template_id,
            "revision": version.revision, "current_revision": version.template.revision,
            "state": review.state, "submitted_by": review.submitted_by_id,
            "submitted_at": review.submitted_at.isoformat(), "decided_by": review.decided_by_id,
            "decided_at": review.decided_at.isoformat() if review.decided_at else None,
            "decision_reason": reason, **snapshot}


@transaction.atomic
def list_pending_template_reviews(*, actor, business_id, before_id=None, limit=20):
    if before_id is not None:
        _identifier(before_id)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})
    business, _ = _context(actor, business_id, "view")
    _head(actor, business)
    reviews = MedicalTemplateReview.objects.select_related("version__template").filter(
        version__template__business=business, state="pending",
        version__revision=F("version__template__revision")).order_by("-pk")
    if before_id is not None:
        reviews = reviews.filter(pk__lt=before_id)
    page = list(reviews[:limit + 1])
    results = []
    for review in page[:limit]:
        version = review.version
        write_template_audit(actor=actor, business=business, version=version, action="read")
        snapshot = read_template_revision(version)
        read_review_decision(review, snapshot["template"])
        results.append({"review_id": review.pk, "version_id": version.pk,
            "template_id": version.template_id, "revision": version.revision,
            "title": snapshot["template"]["title"], "state": review.state,
            "submitted_by": review.submitted_by_id, "submitted_at": review.submitted_at.isoformat()})
    return {"results": results,
            "next_before_id": page[limit - 1].pk if len(page) > limit else None}
