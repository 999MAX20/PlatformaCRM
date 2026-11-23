import logging

from django.db import transaction
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.billing.storage import get_storage_limit_mb, get_storage_usage_bytes
from apps.core.domain_errors import DomainAPIException, InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import FileAttachment, safe_original_filename
from .audit import write_patient_audit
from .clinical_identity import assert_verified_clinical_identity
from .file_access import medical_file_context
from .file_content import append_file_revision, read_file_metadata, validate_file_metadata
from .file_policy import checked_upload
from .identity_crypto import medical_request_digest
from .models import DentalMedicalRecord, MedicalAttachment, MedicalAttachmentRevision, MedicalEncounter
from .role_access import assert_medical_branch_permission


class MedicalFileStorageUnavailable(DomainAPIException):
    status_code = 503
    error_code = "medical_file_storage_unavailable"
    default_detail = "Medical file storage is temporarily unavailable."
    category = "temporary"
    retryable = True


def medical_file_upload_target(*, actor, context, record_id, encounter_id=None):
    if type(record_id) is not int or record_id <= 0 or (encounter_id is not None and
            (type(encounter_id) is not int or encounter_id <= 0)):
        raise ValidationError({"file": "Provide valid medical record and encounter identifiers."})
    assert_verified_clinical_identity(context.patient)
    record = DentalMedicalRecord.objects.filter(pk=record_id, business=context.business,
                                                 patient=context.patient).first()
    if record is None:
        raise PermissionDenied()
    encounter = None
    if encounter_id is not None:
        encounter = MedicalEncounter.objects.select_related("branch").filter(pk=encounter_id,
            business=context.business, patient=context.patient, record=record,
            branch=context.branch, primary_clinician_id=context.role.member_id).first()
        if encounter is None:
            raise PermissionDenied()
        encounter.clean()
        if context.correction is None and encounter.state != "draft":
            raise InvalidTransition("A finalized encounter requires an authorized correction.")
    if context.correction is not None and encounter_id != context.correction.encounter_id:
        raise PermissionDenied()
    return record, encounter


def upload_medical_file(*, actor, business_id, patient_id, record_id, uploaded_file, expected_patient_revision,
                        idempotency_key, description="", teeth=None, encounter_id=None, reason="", **basis):
    if any(type(value) is not int or value <= 0 for value in (record_id, expected_patient_revision)):
        raise ValidationError({"file": "Provide valid record and patient revision identifiers."})
    if encounter_id is not None and (type(encounter_id) is not int or encounter_id <= 0):
        raise ValidationError({"encounter_id": "Provide a positive encounter identifier."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide a command key of at most 128 characters."})
    stored = []
    try:
        # The durable boundary makes a failed database commit clean up its newly stored blob.
        with transaction.atomic(durable=True):
            context = medical_file_context(actor=actor, business_id=business_id, patient_id=patient_id,
                                           action="create", **basis)
            record, encounter = medical_file_upload_target(actor=actor, context=context,
                record_id=record_id, encounter_id=encounter_id)
            metadata = validate_file_metadata({"name": safe_original_filename(uploaded_file.name),
                "description": description, "teeth": [] if teeth is None else teeth, "reason": reason})
            extension, content_type, digest, size = checked_upload(uploaded_file)
            if context.correction is not None and not reason.strip():
                raise PermissionDenied()

            def operation():
                if context.patient.revision != expected_patient_revision or record.state != "active":
                    raise InvalidTransition("Patient or medical record changed; review the current state.")
                limit_mb = get_storage_limit_mb(context.business)
                if limit_mb is not None and get_storage_usage_bytes(context.business) + size > limit_mb * 1024 * 1024:
                    raise ValidationError({"file": "Storage limit exceeded."})
                opaque_name = f"attachment.{extension}"
                blob = FileAttachment(business=context.business, uploaded_by=actor, original_name=opaque_name,
                    content_type=content_type, size=size, entity_type="medical_attachment", entity_id="pending")
                try:
                    blob.file.save(opaque_name, uploaded_file, save=False)
                except Exception:
                    raise MedicalFileStorageUnavailable() from None
                stored.append((blob.file.storage, blob.file.name))
                blob.save(force_insert=True)
                item = MedicalAttachment(business=context.business, patient=context.patient, record=record,
                    branch=context.branch, encounter=encounter, attachment=blob, created_by=actor)
                item.full_clean()
                item.save(force_insert=True)
                blob.entity_id = str(item.pk)
                blob.save(update_fields=["entity_id"])
                version = append_file_revision(medical_file=item, author=actor, metadata=metadata)
                write_patient_audit(actor=actor, business=context.business, patient=context.patient,
                    action="file_uploaded", file_version=version, correction_access=context.correction)
                return CRMCommandResult(data={}, status_code=201, resource=version)

            result = run_idempotent_crm_command(business=context.business, actor=actor, action="medical.file.upload",
                idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
                payload={"patient": patient_id, "record": record_id, "encounter": encounter_id,
                    "basis": basis, "patient_revision": expected_patient_revision,
                    "content_digest": medical_request_digest({"sha256": digest, "size": size, "metadata": metadata},
                                                             business_id=business_id)}, operation=operation)
            version = MedicalAttachmentRevision.objects.get(pk=result.resource_id if result.replayed else result.resource.pk,
                                                             medical_file__in=context.files())
        return version, result.replayed
    except Exception:
        for storage, name in stored:
            try:
                storage.delete(name)
            except Exception:
                logging.getLogger(__name__).error("medical_file_rollback_cleanup_unavailable")
        raise


def assert_file_metadata_editable(*, actor, context, item):
    if item.created_by_id != actor.pk:
        raise PermissionDenied()
    assert_medical_branch_permission(actor, context.business, "medical_files", "create", branch=item.branch)
    assert_medical_branch_permission(actor, context.business, "medical_records", "view", branch=item.branch)
    if item.encounter_id and item.encounter.state != "draft" and context.correction is None:
        raise InvalidTransition("A finalized encounter requires an authorized correction.")


@transaction.atomic
def update_medical_file_metadata(*, actor, business_id, patient_id, file_id, expected_revision,
                                 description, teeth, reason, idempotency_key, **basis):
    if any(type(value) is not int or value <= 0 for value in (file_id, expected_revision)):
        raise ValidationError({"file": "Provide a valid file and revision."})
    if not isinstance(reason, str) or not reason.strip():
        raise ValidationError({"reason": "Explain the metadata correction."})
    if not isinstance(idempotency_key, str) or not idempotency_key.strip() or len(idempotency_key) > 128:
        raise ValidationError({"idempotency_key": "Provide a command key of at most 128 characters."})
    context = medical_file_context(actor=actor, business_id=business_id, patient_id=patient_id,
                                   action="create", **basis)
    item = context.files().select_for_update(of=("self",)).select_related("encounter").filter(pk=file_id, created_by=actor).first()
    if item is None:
        raise PermissionDenied()
    assert_file_metadata_editable(actor=actor, context=context, item=item)
    current = MedicalAttachmentRevision.objects.get(medical_file=item, revision=item.revision)
    metadata = validate_file_metadata({**read_file_metadata(current), "description": description,
                                       "teeth": teeth, "reason": reason})

    def operation():
        if item.revision != expected_revision:
            raise InvalidTransition("The medical file changed; reload its current revision.")
        item.revision += 1
        item.save(update_fields=["revision", "updated_at"])
        version = append_file_revision(medical_file=item, author=actor, metadata=metadata)
        write_patient_audit(actor=actor, business=context.business, patient=context.patient,
            action="file_metadata_updated", file_version=version, correction_access=context.correction)
        return CRMCommandResult(data={}, resource=version)

    result = run_idempotent_crm_command(business=context.business, actor=actor, action="medical.file.metadata",
        idempotency_key=medical_request_digest({"key": idempotency_key}, business_id=business_id),
        payload={"file": file_id, "basis": basis, "revision": expected_revision,
                 "metadata_digest": medical_request_digest(metadata, business_id=business_id)}, operation=operation)
    return MedicalAttachmentRevision.objects.get(pk=result.resource_id if result.replayed else result.resource.pk,
                                                  medical_file=item), result.replayed
