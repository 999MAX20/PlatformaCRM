import json

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business
from apps.core.domain_errors import InvalidTransition
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import FDI_TOOTH_NUMBERS, MedicalAttachment, MedicalAttachmentRevision, MedicalAttachmentTooth


def validate_file_metadata(value):
    if not isinstance(value, dict) or set(value) != {"name", "description", "teeth", "reason"}:
        raise ValidationError({"metadata": "Provide the filename, description, teeth and reason."})
    for field, limit in (("name", 255), ("description", 4000), ("reason", 2000)):
        if not isinstance(value[field], str) or len(value[field]) > limit:
            raise ValidationError({field: f"Provide text of at most {limit} characters."})
    if not value["name"].strip() or any(char in value["name"] for char in ("/", "\\", "\r", "\n", "\0")):
        raise ValidationError({"name": "Provide a filename without a path or control characters."})
    teeth = value["teeth"]
    if (not isinstance(teeth, list) or len(teeth) > len(FDI_TOOTH_NUMBERS)
            or any(type(tooth) is not int or tooth not in FDI_TOOTH_NUMBERS for tooth in teeth)
            or len(set(teeth)) != len(teeth)):
        raise ValidationError({"teeth": "Select distinct supported FDI tooth numbers."})
    return {**value, "teeth": list(teeth)}


@transaction.atomic
def append_file_revision(*, medical_file, author, metadata):
    metadata = validate_file_metadata(metadata)
    Business.objects.select_for_update().get(pk=medical_file.business_id)
    current = MedicalAttachment.objects.select_for_update().get(pk=medical_file.pk,
                                                               business_id=medical_file.business_id)
    if current.revision != medical_file.revision:
        raise InvalidTransition("The medical file changed; reload its current revision.")
    current.clean()
    if current.revision > 1 and not metadata["reason"].strip():
        raise ValidationError({"reason": "Explain the metadata correction."})
    staging = encrypt_medical_value("{}", business_id=current.business_id,
                                    subject_id=current.pk, purpose="file_metadata_staging")
    version = MedicalAttachmentRevision.objects.create(medical_file=current, revision=current.revision,
                                                       author=author, metadata_encrypted=staging)
    payload = {"file_id": current.pk, "patient_id": current.patient_id, "revision": version.revision,
               "author_id": version.author_id, "attachment_id": current.attachment_id, "metadata": metadata}
    version.metadata_encrypted = encrypt_medical_value(json.dumps(payload, ensure_ascii=False, sort_keys=True),
        business_id=current.business_id, subject_id=version.pk, purpose="file_metadata")
    version.full_clean()
    version.save(update_fields=["metadata_encrypted"])
    MedicalAttachmentTooth.objects.bulk_create([
        MedicalAttachmentTooth(version=version, tooth=tooth) for tooth in metadata["teeth"]])
    return version


def read_file_metadata(version):
    try:
        version.clean()
        item = version.medical_file
        payload = json.loads(decrypt_medical_value(version.metadata_encrypted, business_id=item.business_id,
                                                   subject_id=version.pk, purpose="file_metadata"))
        expected = {"file_id": item.pk, "patient_id": item.patient_id, "revision": version.revision,
                    "author_id": version.author_id, "attachment_id": item.attachment_id}
        if not isinstance(payload, dict) or set(payload) != {*expected, "metadata"}:
            raise ValueError
        if any(payload[key] != value for key, value in expected.items()):
            raise ValueError
        metadata = validate_file_metadata(payload["metadata"])
        if {link.tooth for link in version.tooth_links.all()} != set(metadata["teeth"]):
            raise ValueError
        return metadata
    except (ModelValidationError, ValidationError, TypeError, ValueError, KeyError):
        raise MedicalDataUnavailable() from None
