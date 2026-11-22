import json

from django.db import DatabaseError, transaction
from django.db.models import OuterRef, Subquery
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from .audit import MedicalAuditUnavailable
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value, medical_request_digest
from .models import MedicalAuditEvent, MedicalDocumentTemplate, MedicalDocumentTemplateRevision, MedicalTemplateAvailabilityRevision
from .template_services import _context, _identifier, assert_common_template_context, read_template_version_payload
from .template_search import search_template_page, template_search_filters


@transaction.atomic
def list_managed_templates(*, actor, business_id, before_id=None, limit=20,
                           q="", language="", category="", specialty="", service_id=None, activity="all"):
    business, context = _context(actor, business_id, "approve")
    assert_common_template_context(actor, business, context)
    if activity not in ("all", "active", "inactive"):
        raise ValidationError({"activity": "Select all, active or inactive templates."})
    latest = MedicalDocumentTemplateRevision.objects.filter(template_id=OuterRef("template_id"),
        review__state="approved").order_by("-revision").values("pk")[:1]
    versions = MedicalDocumentTemplateRevision.objects.select_related("template").filter(
        template__business=business, pk=Subquery(latest))
    if activity != "all":
        versions = versions.filter(template__is_active=activity == "active")
    filters = template_search_filters(q=q, language=language, category=category,
        specialty=specialty, service_id=service_id)
    return search_template_page(actor=actor, business=business, versions=versions, filters=filters,
                                before_id=before_id, limit=limit)


def _target(*, actor, business_id, template_id):
    _identifier(template_id)
    business, context = _context(actor, business_id, "approve")
    assert_common_template_context(actor, business, context)
    template = MedicalDocumentTemplate.objects.select_for_update().filter(pk=template_id, business=business).first()
    if template is None:
        raise PermissionDenied()
    versions = MedicalDocumentTemplateRevision.objects.select_related("template").filter(template=template)
    if template.owner_member_id is not None:
        versions = versions.filter(review__state="approved")
    version = versions.order_by("-revision").first()
    if version is None:
        raise PermissionDenied()
    return business, template, version


def _binding(change):
    return {"schema": 1, "business_id": change.template.business_id, "template_id": change.template_id,
        "template_version_id": change.template_version_id, "id": change.pk, "revision": change.revision,
        "is_active": change.is_active, "actor_id": change.actor_id, "created_at": change.created_at.isoformat()}


def _read(change):
    try:
        if change.template_version.template_id != change.template_id or change.revision > change.template.availability_revision:
            raise ValueError
        payload = json.loads(decrypt_medical_value(change.reason_encrypted, business_id=change.template.business_id,
            subject_id=change.pk, purpose="template_availability"))
        expected = _binding(change)
        if not isinstance(payload, dict) or set(payload) != set(expected) | {"reason"}:
            raise ValueError
        if any(type(payload[key]) is not type(value) or payload[key] != value for key, value in expected.items()):
            raise ValueError
        if not isinstance(payload["reason"], str) or not payload["reason"].strip() or len(payload["reason"]) > 2000:
            raise ValueError
        return payload
    except (ValueError, TypeError, KeyError):
        raise MedicalDataUnavailable() from None


def _audit(*, actor, business, change, action):
    if (change.template.business_id != business.pk or change.template_version.template_id != change.template_id
            or change.revision > change.template.availability_revision):
        raise ValueError("Availability audit requires consistent template links.")
    if action != "read" and (action != ("template_activated" if change.is_active else "template_deactivated")
            or change.actor_id != actor.pk or change.revision != change.template.availability_revision):
        raise ValueError("Availability audit requires the actor's current change.")
    try:
        event = MedicalAuditEvent.objects.create(business=business, actor=actor, template_version=change.template_version,
            template_availability=change, action=action, result="success")
        if event is None or event.pk is None:
            raise MedicalAuditUnavailable()
    except DatabaseError:
        raise MedicalAuditUnavailable() from None


@transaction.atomic
def set_template_availability(*, actor, business_id, template_id, is_active, expected_revision, reason, idempotency_key):
    business, template, version = _target(actor=actor, business_id=business_id, template_id=template_id)
    if type(is_active) is not bool or type(expected_revision) is not int or expected_revision < 0:
        raise ValidationError({"availability": "Provide the target activity and current availability revision."})
    if not isinstance(reason, str) or not reason.strip() or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})

    def operation():
        if template.availability_revision != expected_revision or template.is_active == is_active:
            raise InvalidTransition("The template activity changed; reload before continuing.")
        read_template_version_payload(actor=actor, business=business, version=version)
        staging = encrypt_medical_value("{}", business_id=business_id, subject_id=template.pk, purpose="availability_staging")
        template.is_active = is_active
        template.availability_revision += 1
        template.save(update_fields=["is_active", "availability_revision", "updated_at"])
        change = MedicalTemplateAvailabilityRevision.objects.create(template=template, template_version=version,
            revision=template.availability_revision, is_active=is_active, actor=actor, reason_encrypted=staging)
        change.reason_encrypted = encrypt_medical_value(json.dumps(_binding(change) | {"reason": reason}, ensure_ascii=False, sort_keys=True),
            business_id=business_id, subject_id=change.pk, purpose="template_availability")
        change.save(update_fields=["reason_encrypted"])
        _audit(actor=actor, business=business, change=change,
               action="template_activated" if is_active else "template_deactivated")
        return CRMCommandResult(data={}, status_code=200, resource=change)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.template.availability",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"template_id": template_id, "is_active": is_active, "expected_revision": expected_revision,
            "reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)}, operation=operation)
    change = MedicalTemplateAvailabilityRevision.objects.get(template__business=business,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return change, result.replayed


@transaction.atomic
def list_template_availability(*, actor, business_id, template_id, before_revision=None, limit=20):
    business, template, _ = _target(actor=actor, business_id=business_id, template_id=template_id)
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})
    versions = MedicalTemplateAvailabilityRevision.objects.select_related("template", "template_version").filter(template=template).order_by("-revision")
    if before_revision is not None:
        _identifier(before_revision)
        versions = versions.filter(revision__lt=before_revision)
    page = list(versions[:limit + 1])
    rows = []
    for change in page[:limit]:
        _audit(actor=actor, business=business, change=change, action="read")
        rows.append(_read(change))
    return {"template_id": template.pk, "is_active": template.is_active, "revision": template.availability_revision,
        "results": rows, "next_before_revision": page[limit - 1].revision if len(page) > limit else None}
