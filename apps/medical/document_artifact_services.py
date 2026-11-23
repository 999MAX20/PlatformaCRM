import base64
import binascii
import hashlib
import logging

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.billing.storage import get_storage_limit_mb, get_storage_usage_bytes
from apps.core.domain_errors import DomainAPIException, InvalidTransition
from apps.core.models import FileAttachment
from apps.core.file_scanning import FileQuarantined, open_clean_attachment
from .audit import write_patient_audit
from .document_artifact_access import document_artifact_access
from .document_artifact_content import register_document_artifact, read_document_artifact_manifest, verify_document_artifact_bytes
from .document_content import read_document_revision
from .document_pdf import DocumentRenderUnavailable, render_draft_pdf, render_signing_pdf
from .document_signing_prerequisites import assert_document_signing_prerequisites
from .role_access import assert_medical_branch_permission
from .document_docx import render_draft_docx
from .document_logo import DocumentLogoUnavailable, capture_document_logo
from .document_print_snapshot import draft_print_snapshot
from .file_services import MedicalFileStorageUnavailable
from .models import MedicalDocumentArtifact
from .identity_crypto import MedicalDataUnavailable


class DocumentPDFUnavailable(DomainAPIException):
    status_code = 503
    error_code = "medical_document_render_unavailable"
    default_detail = "This saved document could not be rendered."
    category = "temporary"


def _version_logo(version, snapshot):
    existing = MedicalDocumentArtifact.objects.filter(version=version).order_by("pk").first()
    if existing is None:
        return capture_document_logo(snapshot["business"]["brand_logo_url"])
    encoded = read_document_artifact_manifest(existing)["logo"]
    if not snapshot["business"]["brand_logo_url"]:
        if encoded is not None:
            raise MedicalDataUnavailable()
        return None
    try:
        if not isinstance(encoded, str):
            raise ValueError
        logo = base64.b64decode(encoded, validate=True)
        if not 0 < len(logo) <= 2 * 1024 * 1024:
            raise ValueError
        return logo
    except (ValueError, binascii.Error):
        raise MedicalDataUnavailable() from None


DOCX_CONTENT_TYPE = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"


def assert_editable_docx(context):
    document = context.version.document
    encounter = document.encounter
    if (document.state != "draft" or document.revision != context.version.revision
            or encounter.record.state != "active"
            or encounter.state != "draft" and context.correction is None):
        raise InvalidTransition("Select a current editable draft for DOCX export.")
    snapshot = read_document_revision(context.version)
    rules = snapshot.get("document_rules")
    if not rules or not rules["docx_allowed"] or not snapshot.get("template_source"):
        raise PermissionDenied("Editable export is not allowed for this document.")


def document_artifact_can_docx(**scope):
    with transaction.atomic():
        try:
            assert_editable_docx(document_artifact_access(action="export", **scope))
            return True
        except (PermissionDenied, InvalidTransition):
            return False


def prepare_document_draft_pdf(**scope):
    return _prepare_document_draft(format="pdf", **scope)


def prepare_document_draft_docx(**scope):
    return _prepare_document_draft(format="docx", **scope)


def prepare_document_signing_pdf(**scope):
    return _prepare_document_draft(format="pdf", rendition="signing", **scope)


def _prepare_document_draft(*, actor, business_id, patient_id, version_id, language, format, rendition="draft", **basis):
    if not isinstance(language, str) or language not in {"ru", "kk", "en"}:
        raise ValidationError({"language": "Select a supported document language."})
    stored = []
    try:
        with transaction.atomic(durable=True):
            context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
                version_id=version_id, action="export" if format == "docx" else "view", **basis)
            if format == "docx":
                assert_editable_docx(context)
            if rendition == "signing":
                assert_medical_branch_permission(actor, context.business, "medical_documents", "sign",
                    branch=context.version.document.encounter.branch)
                if context.correction is not None or context.version.document.encounter.record.state != "active":
                    raise PermissionDenied()
                assert_document_signing_prerequisites(context.version)
            if context.version.document.state not in {"draft", "ready_for_review", "reviewed"}:
                raise InvalidTransition("Select an unsigned document for this operation.")
            item = MedicalDocumentArtifact.objects.filter(version=context.version, format=format, language=language, rendition=rendition).first()
            replayed = item is not None
            if item is not None:
                read_document_artifact_manifest(item)
            else:
                snapshot = read_document_revision(context.version)
                try:
                    logo = _version_logo(context.version, snapshot)
                    data = draft_print_snapshot(snapshot=snapshot, revision=context.version.revision,
                        created_at=context.version.created_at, language=language, captured_logo=logo)
                    body = (render_signing_pdf(data) if rendition == "signing" else
                        render_draft_docx(data) if format == "docx" else render_draft_pdf(data))
                except (DocumentRenderUnavailable, DocumentLogoUnavailable):
                    raise DocumentPDFUnavailable() from None
                limit = get_storage_limit_mb(context.business)
                if limit is not None and get_storage_usage_bytes(context.business) + len(body) > limit * 1024 * 1024:
                    raise ValidationError({"file": "Storage limit exceeded."})
                filename = f"document.{format}"
                blob = FileAttachment(business=context.business, uploaded_by=actor, original_name=filename,
                    content_type=DOCX_CONTENT_TYPE if format == "docx" else "application/pdf", size=len(body), entity_type="medical_document_artifact",
                    entity_id=str(context.version.pk))
                try:
                    blob.file.save(filename, ContentFile(body), save=False)
                except Exception:
                    raise MedicalFileStorageUnavailable() from None
                stored.append((blob.file.storage, blob.file.name))
                blob.save(force_insert=True)
                item = register_document_artifact(version=context.version, attachment=blob, format=format,
                    language=language, sha256=hashlib.sha256(body).hexdigest(), renderer=f"{rendition}-{format}-v1", captured_logo=logo,
                    rendition=rendition)
            write_patient_audit(actor=actor, business=context.business, patient=context.patient, action="read",
                document_version=context.version, correction_access=context.correction)
        return item, replayed
    except Exception:
        for storage, name in stored:
            try:
                storage.delete(name)
            except Exception:
                logging.getLogger(__name__).error("medical_document_rollback_cleanup_unavailable")
        raise


def read_document_draft_pdf(**scope):
    return _read_document_draft(format="pdf", **scope)


def read_document_draft_docx(**scope):
    return _read_document_draft(format="docx", purpose="download", **scope)


def _read_document_draft(*, actor, business_id, patient_id, version_id, language, format, purpose="preview", **basis):
    """Preview or staff export of exact bytes; never a patient delivery operation."""
    if purpose not in {"preview", "download", "print"}:
        raise ValidationError({"purpose": "Select a supported document operation."})
    if not isinstance(language, str) or language not in {"ru", "kk", "en"}:
        raise ValidationError({"language": "Select a supported document language."})
    source = None
    try:
        with transaction.atomic(durable=True):
            context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
                version_id=version_id, action="view" if purpose == "preview" else "export", **basis)
            if format == "docx":
                assert_editable_docx(context)
            item = MedicalDocumentArtifact.objects.select_related("attachment").filter(
                version=context.version, format=format, language=language, rendition="draft").first()
            if item is None:
                raise NotFound()
            read_document_artifact_manifest(item)
            quarantined = False
            try:
                source = open_clean_attachment(item.attachment, memory_only=True)
            except FileQuarantined:
                quarantined = True
            if not quarantined:
                body = verify_document_artifact_bytes(item, source.read())
                audit_action = {"preview": "read", "download": "document_exported", "print": "document_print_requested"}[purpose]
                write_patient_audit(actor=actor, business=context.business, patient=context.patient, action=audit_action,
                    document_version=context.version, correction_access=context.correction)
        if quarantined:
            # Preserve the scanner's new quarantine state instead of rolling it back.
            raise FileQuarantined()
        return body
    finally:
        if source is not None:
            source.close()
