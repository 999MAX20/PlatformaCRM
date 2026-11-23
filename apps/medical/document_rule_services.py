import json

from django.db import DatabaseError, transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.services.models import Service
from .audit import MedicalAuditUnavailable
from .document_rule_content import read_rule_revision, rule_binding, validate_rule_content
from .identity_crypto import encrypt_medical_value, medical_request_digest
from .models import MedicalAuditEvent, MedicalDocumentKind, MedicalDocumentRuleRevision, MedicalDocumentTemplate
from .role_access import assert_medical_role_permission


def rule_context(*, actor, business_id, write=False):
    if type(business_id) is not int or business_id <= 0:
        raise ValidationError({"business": "Select a business."})
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    if business is None:
        raise NotFound()
    context = assert_medical_role_permission(actor, business, "medical_documents", "view")
    if context.kind != "head" or context.scope != "business":
        raise PermissionDenied()
    if write:
        approval = assert_medical_role_permission(actor, business, "medical_documents", "approve")
        if approval.scope != "business":
            raise PermissionDenied()
    return business


def audit_rule(*, actor, business, version, write=False):
    if version.kind.business_id != business.pk:
        raise ValueError("The rules must belong to the audited business.")
    try:
        event = MedicalAuditEvent.objects.create(actor=actor, business=business, document_rule_version=version,
            action="document_rules_saved" if write else "read", result="success")
        if event is None or event.pk is None:
            raise MedicalAuditUnavailable()
    except DatabaseError:
        raise MedicalAuditUnavailable() from None


@transaction.atomic
def save_document_rules(*, actor, business_id, content, template_ids, reason, idempotency_key,
                        kind_id=None, expected_revision=None):
    if ((kind_id is not None and (type(kind_id) is not int or kind_id <= 0
            or type(expected_revision) is not int or expected_revision <= 0))
            or (kind_id is None and expected_revision is not None)):
        raise ValidationError({"revision": "Select the document kind and its current revision."})
    if (not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128
            or not isinstance(reason, str) or not reason.strip() or len(reason) > 2000):
        raise ValidationError({"reason": "Provide a reason and an idempotency key."})
    if not isinstance(content, dict) or set(content) - {"name", "docx_allowed", "default", "services"}:
        raise ValidationError({"content": "Provide the document rule settings."})
    if not {"name", "default", "services"}.issubset(content):
        raise ValidationError({"content": "Provide a name, default requirements and service rules."})
    business = rule_context(actor=actor, business_id=business_id, write=True)
    kind = None
    if kind_id is not None:
        kind = MedicalDocumentKind.objects.select_for_update().filter(pk=kind_id, business=business).first()
        if kind is None:
            raise PermissionDenied()

    def operation():
        from .template_services import read_template_version_payload

        if kind is not None and kind.revision != expected_revision:
            raise InvalidTransition("Document rules changed; reload their current revision.")
        if (not isinstance(template_ids, list) or len(template_ids) > 100
                or any(type(pk) is not int or pk <= 0 for pk in template_ids) or len(set(template_ids)) != len(template_ids)):
            raise ValidationError({"template_ids": "Select at most 100 distinct templates."})
        rows = content["services"]
        if (not isinstance(rows, list) or len(rows) > 50 or any(not isinstance(row, dict)
                or set(row) != {"service_id", "rule"} or type(row["service_id"]) is not int
                or row["service_id"] <= 0 for row in rows)):
            raise ValidationError({"services": "Select service-specific requirements."})
        names = dict(Service.objects.filter(business=business, pk__in=[row["service_id"] for row in rows])
            .values_list("pk", "name"))
        if any(row["service_id"] not in names for row in rows):
            raise PermissionDenied()
        templates = list(MedicalDocumentTemplate.objects.select_for_update().filter(business=business, pk__in=template_ids))
        if len(templates) != len(template_ids):
            raise PermissionDenied()
        template_names = []
        for template in templates:
            if template.document_kind_id not in (None, kind_id):
                raise InvalidTransition("A selected template belongs to another document kind.")
            versions = template.versions.all()
            if template.owner_member_id is not None:
                versions = versions.filter(review__state="approved")
            selected = versions.order_by("-revision").first()
            if selected is None:
                raise PermissionDenied()
            selected_payload = read_template_version_payload(actor=actor, business=business, version=selected)
            template_names.append({"id": template.pk, "title": selected_payload["template"]["title"]})
        captured = validate_rule_content({"name": content["name"], "docx_allowed": content.get("docx_allowed", False),
            "validation": "synthetic", "default": content["default"], "templates": template_names,
            "services": [{"id": row["service_id"], "name": names[row["service_id"]], "rule": row["rule"]} for row in rows]})
        current = kind or MedicalDocumentKind.objects.create(business=business)
        staging = encrypt_medical_value("{}", business_id=business.pk, subject_id=current.pk, purpose="document_rules_staging")
        version = MedicalDocumentRuleRevision.objects.create(kind=current, revision=current.revision + 1,
            author=actor, snapshot_encrypted=staging)
        payload = {**rule_binding(version), "content": captured, "reason": reason.strip()}
        version.snapshot_encrypted = encrypt_medical_value(json.dumps(payload, ensure_ascii=False, sort_keys=True),
            business_id=business.pk, subject_id=version.pk, purpose="document_rules")
        version.save(update_fields=["snapshot_encrypted"])
        current.revision = version.revision
        current.save(update_fields=["revision"])
        MedicalDocumentTemplate.objects.filter(business=business, document_kind=current).exclude(pk__in=template_ids).update(document_kind=None)
        MedicalDocumentTemplate.objects.filter(business=business, pk__in=template_ids).update(document_kind=current)
        audit_rule(actor=actor, business=business, version=version, write=True)
        return CRMCommandResult(data={}, status_code=201 if kind is None else 200, resource=version)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.document.rules.save",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business.pk),
        payload={"kind": kind_id, "revision": expected_revision, "content_digest": medical_request_digest(
            {"content": content, "templates": template_ids, "reason": reason.strip()}, business_id=business.pk)},
        operation=operation)
    version = MedicalDocumentRuleRevision.objects.select_related("kind").get(kind__business=business,
        pk=result.resource_id if result.replayed else result.resource.pk)
    return version, result.replayed


@transaction.atomic
def read_document_rules(*, actor, business_id, version_id):
    business = rule_context(actor=actor, business_id=business_id)
    if type(version_id) is not int or version_id <= 0:
        raise ValidationError({"version": "Select a valid rules version."})
    version = MedicalDocumentRuleRevision.objects.select_related("kind").filter(pk=version_id, kind__business=business).first()
    if version is None:
        raise PermissionDenied()
    payload = read_rule_revision(version)
    audit_rule(actor=actor, business=business, version=version)
    return payload
