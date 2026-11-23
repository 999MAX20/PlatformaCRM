import hashlib
from io import BytesIO

from django.db import DatabaseError, transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.core.antivirus import ScanUnavailable, scan_stream
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from .audit import MedicalAuditUnavailable
from .common_template_services import read_approved_template_version, read_common_template_version
from .document_artifact_services import DocumentPDFUnavailable
from .document_docx import render_draft_docx
from .document_pdf import DraftPrintData, DocumentRenderUnavailable
from .document_rule_content import read_rule_revision
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalDocumentRuleRevision, MedicalDocumentTemplateRevision
from .template_services import _context, _identifier, assert_common_template_context, read_personal_template_version


def _visible_version(*, actor, business_id, version_id, action):
    _identifier(version_id)
    business, context = _context(actor, business_id, action)
    version = MedicalDocumentTemplateRevision.objects.select_related("template__document_kind").filter(
        pk=version_id, template__business=business).first()
    if version is None:
        raise PermissionDenied()
    template = version.template
    if template.owner_member_id == context.member_id:
        reader = read_personal_template_version
    elif template.owner_member_id is None:
        if context.kind == "head":
            assert_common_template_context(actor, business, context)
        reader = read_common_template_version if context.kind == "head" else read_approved_template_version
    else:
        raise PermissionDenied()
    payload = reader(actor=actor, business_id=business_id, version_id=version_id)
    return business, version, payload["template"]


def _export_context(**scope):
    business, version, payload = _visible_version(action="export", **scope)
    template = version.template
    if not template.is_active:
        raise InvalidTransition("Template use is suspended.")
    kind = template.document_kind
    if kind is None:
        raise PermissionDenied("Editable export is not allowed for this template.")
    if kind.business_id != business.pk:
        raise MedicalDataUnavailable()
    rules = MedicalDocumentRuleRevision.objects.filter(kind=kind, revision=kind.revision).first()
    if rules is None:
        raise MedicalDataUnavailable()
    content = read_rule_revision(rules)["content"]
    if not content["docx_allowed"] or template.pk not in {item["id"] for item in content["templates"]}:
        raise PermissionDenied("Editable export is not allowed for this template.")
    return business, version, rules, payload


@transaction.atomic
def template_docx_access(**scope):
    _visible_version(action="view", **scope)
    try:
        _export_context(**scope)
    except (PermissionDenied, InvalidTransition):
        return {"can_docx": False}
    return {"can_docx": True}


def download_template_docx(*, actor, business_id, version_id, language):
    if not isinstance(language, str) or language not in {"ru", "kk", "en"}:
        raise ValidationError({"language": "Select a supported document language."})
    scope = dict(actor=actor, business_id=business_id, version_id=version_id)
    with transaction.atomic():
        _, version, rules, content = _export_context(**scope)
    try:
        body = render_draft_docx(DraftPrintData(title=content["title"], text=content["text"],
            clinic_lines=(), identity_lines=(), created_at=version.created_at, language=language))
        digest = hashlib.sha256(body).hexdigest()
        verdict = scan_stream(BytesIO(body))
        if not verdict.clean or verdict.sha256 != digest or verdict.size != len(body):
            raise ScanUnavailable()
    except (DocumentRenderUnavailable, ScanUnavailable):
        raise DocumentPDFUnavailable() from None
    with transaction.atomic():
        business, current, current_rules, current_content = _export_context(**scope)
        if (current_rules.pk != rules.pk or current.snapshot_encrypted != version.snapshot_encrypted
                or current_content != content):
            raise InvalidTransition("Template export rules changed; retry the operation.")
        try:
            event = AuditLog.objects.create(business=business, actor=actor, action=AuditLog.Actions.DOWNLOAD,
                entity_type="medical_template_version", entity_id=str(version.pk),
                metadata={"template_id": version.template_id, "revision": version.revision,
                    "rule_version_id": rules.pk, "format": "docx", "language": language,
                    "renderer": "draft-docx-v1", "sha256": digest, "size": len(body)})
            if event is None or event.pk is None:
                raise MedicalAuditUnavailable()
        except DatabaseError:
            raise MedicalAuditUnavailable() from None
    return body
