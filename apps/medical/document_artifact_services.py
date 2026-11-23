import base64
import binascii
import hashlib
import logging

from django.core.files.base import ContentFile
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.billing.storage import get_storage_limit_mb, get_storage_usage_bytes
from apps.core.domain_errors import DomainAPIException, InvalidTransition
from apps.core.models import FileAttachment
from apps.core.file_scanning import FileQuarantined, open_clean_attachment
from .audit import write_patient_audit
from .document_artifact_access import document_artifact_access
from .document_artifact_content import register_document_artifact, read_document_artifact_manifest, verify_document_artifact_bytes
from .document_content import read_document_revision
from .document_pdf import DocumentRenderUnavailable, render_draft_pdf
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


def prepare_document_draft_pdf(*, actor, business_id, patient_id, version_id, language, **basis):
    if not isinstance(language, str) or language not in {"ru", "kk", "en"}:
        raise ValidationError({"language": "Select a supported document language."})
    stored = []
    try:
        with transaction.atomic(durable=True):
            context = document_artifact_access(actor=actor, business_id=business_id, patient_id=patient_id,
                version_id=version_id, **basis)
            if context.version.document.state not in {"draft", "ready_for_review", "reviewed"}:
                raise InvalidTransition("Select an unsigned document for this operation.")
            item = MedicalDocumentArtifact.objects.filter(version=context.version, format="pdf", language=language).first()
            replayed = item is not None
            if item is not None:
                read_document_artifact_manifest(item)
            else:
                snapshot = read_document_revision(context.version)
                try:
                    logo = _version_logo(context.version, snapshot)
                    data = draft_print_snapshot(snapshot=snapshot, revision=context.version.revision,
                        created_at=context.version.created_at, language=language, captured_logo=logo)
                    body = render_draft_pdf(data)
                except (DocumentRenderUnavailable, DocumentLogoUnavailable):
                    raise DocumentPDFUnavailable() from None
                limit = get_storage_limit_mb(context.business)
                if limit is not None and get_storage_usage_bytes(context.business) + len(body) > limit * 1024 * 1024:
                    raise ValidationError({"file": "Storage limit exceeded."})
                blob = FileAttachment(business=context.business, uploaded_by=actor, original_name="document.pdf",
                    content_type="application/pdf", size=len(body), entity_type="medical_document_artifact",
                    entity_id=str(context.version.pk))
                try:
                    blob.file.save("document.pdf", ContentFile(body), save=False)
                except Exception:
                    raise MedicalFileStorageUnavailable() from None
                stored.append((blob.file.storage, blob.file.name))
                blob.save(force_insert=True)
                item = register_document_artifact(version=context.version, attachment=blob, format="pdf",
                    language=language, sha256=hashlib.sha256(body).hexdigest(), renderer="draft-pdf-v1", captured_logo=logo)
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


def read_document_draft_pdf(*, actor, business_id, patient_id, version_id, language, purpose="preview", **basis):
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
            item = MedicalDocumentArtifact.objects.select_related("attachment").filter(
                version=context.version, format="pdf", language=language).first()
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
