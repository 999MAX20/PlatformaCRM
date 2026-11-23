"""Internal artifact binding; public callers must authorize, audit and own blob cleanup."""
import base64
import hashlib
import json
import re

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction

from apps.businesses.models import Business
from apps.core.models import FileAttachment
from .document_content import read_document_revision
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value, medical_request_digest
from .models import MedicalDocumentArtifact, MedicalDocumentRevision


def _binding(item):
    return {"schema": 1, "artifact_id": item.pk, "version_id": item.version_id,
        "business_id": item.version.document.business_id, "attachment_id": item.attachment_id,
        "storage_name": item.attachment.file.name, "format": item.format, "language": item.language,
        "sha256": item.sha256, "size": item.size}


@transaction.atomic
def register_document_artifact(*, version, attachment, format, language, sha256, renderer, captured_logo=None):
    business = Business.objects.select_for_update().get(pk=version.document.business_id)
    version = MedicalDocumentRevision.objects.select_for_update().select_related("document").get(
        pk=version.pk, document__business=business)
    attachment = FileAttachment.objects.select_for_update().get(pk=attachment.pk, business=business)
    snapshot = read_document_revision(version)
    if not isinstance(sha256, str) or not re.fullmatch(r"[0-9a-f]{64}", sha256):
        raise ModelValidationError("Provide the exact artifact checksum.")
    if not isinstance(renderer, str) or not re.fullmatch(r"[a-z0-9._-]{1,64}", renderer):
        raise ModelValidationError("Provide the artifact renderer version.")
    configured_logo = bool(snapshot["business"]["brand_logo_url"])
    if (configured_logo != (captured_logo is not None) or captured_logo is not None and
            (not isinstance(captured_logo, bytes) or not 0 < len(captured_logo) <= 2 * 1024 * 1024)):
        raise ModelValidationError("Bind the captured logo of this saved revision.")
    staging = encrypt_medical_value("{}", business_id=business.pk, subject_id=version.pk,
                                    purpose="document_artifact_staging")
    item = MedicalDocumentArtifact(version=version, attachment=attachment, format=format, language=language,
        sha256=sha256, size=attachment.size, manifest_encrypted=staging)
    item.full_clean()
    item.save(force_insert=True)
    manifest = {**_binding(item), "renderer": renderer,
        "snapshot_digest": medical_request_digest(snapshot, business_id=business.pk),
        "logo": base64.b64encode(captured_logo).decode("ascii") if captured_logo is not None else None}
    item.manifest_encrypted = encrypt_medical_value(json.dumps(manifest, sort_keys=True),
        business_id=business.pk, subject_id=item.pk, purpose="document_artifact_manifest")
    item.save(update_fields=["manifest_encrypted"])
    return item


def read_document_artifact_manifest(item):
    try:
        item = MedicalDocumentArtifact.objects.select_related("version__document", "attachment").get(pk=item.pk)
        item.full_clean()
        business_id = item.version.document.business_id
        payload = json.loads(decrypt_medical_value(item.manifest_encrypted, business_id=business_id,
            subject_id=item.pk, purpose="document_artifact_manifest"))
        expected = _binding(item)
        if not isinstance(payload, dict) or set(payload) != {*expected, "renderer", "snapshot_digest", "logo"}:
            raise ValueError
        if any(type(payload[key]) is not type(value) or payload[key] != value for key, value in expected.items()):
            raise ValueError
        snapshot = read_document_revision(item.version)
        if payload["snapshot_digest"] != medical_request_digest(snapshot, business_id=business_id):
            raise ValueError
        return payload
    except (ModelValidationError, ValueError, TypeError, KeyError, MedicalDocumentArtifact.DoesNotExist):
        raise MedicalDataUnavailable() from None


def verify_document_artifact_bytes(item, content):
    """Run after current ACL, durable audit and the existing clean-file scanner gate."""
    manifest = read_document_artifact_manifest(item)
    if (not isinstance(content, bytes) or len(content) != manifest["size"]
            or hashlib.sha256(content).hexdigest() != manifest["sha256"]):
        raise MedicalDataUnavailable()
    return content
