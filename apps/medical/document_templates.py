import json

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import InvalidTransition
from .document_content import validate_document_template
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalDocumentTemplate, MedicalDocumentTemplateRevision


def _binding(version, template):
    return {"schema": 1, "business_id": template.business_id, "template_id": template.pk,
        "owner_member_id": template.owner_member_id, "code": template.code,
        "version_id": version.pk, "revision": version.revision, "author_id": version.author_id,
        "created_at": version.created_at.isoformat()}


@transaction.atomic
def append_template_revision(*, template, author, title, text, reason=""):
    """Internal storage; the caller supplies authorization and audit, not clinical approval."""
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    Business.objects.select_for_update().get(pk=template.business_id)
    current = MedicalDocumentTemplate.objects.select_for_update().get(pk=template.pk, business_id=template.business_id)
    current.full_clean()
    if current.revision != template.revision:
        raise InvalidTransition("The template changed; reload its current revision.")
    content = validate_document_template({"code": current.code, "version": current.revision + 1,
        "title": title, "text": text}, current.code)
    member = BusinessMember.objects.filter(business_id=current.business_id, user_id=author.pk,
        is_active=True, user__is_active=True).first()
    if member is None:
        raise ValidationError({"author": "Select an active member of this business."})
    staging = encrypt_medical_value("{}", business_id=current.business_id,
        subject_id=current.pk, purpose="template_staging")
    version = MedicalDocumentTemplateRevision.objects.create(template=current, revision=current.revision + 1,
        author_id=member.user_id, snapshot_encrypted=staging)
    payload = {**_binding(version, current), "content": content, "reason": reason}
    version.snapshot_encrypted = encrypt_medical_value(json.dumps(payload, ensure_ascii=False, sort_keys=True),
        business_id=current.business_id, subject_id=version.pk, purpose="document_template")
    version.save(update_fields=["snapshot_encrypted"])
    current.revision = version.revision
    current.save(update_fields=["revision", "updated_at"])
    return version


def read_template_revision(version):
    """Internal decryptor; callers must authorize the template scope and audit access."""
    try:
        current = MedicalDocumentTemplateRevision.objects.select_related("template").get(pk=version.pk)
        template = current.template
        template.clean()
        if current.revision > template.revision:
            raise ValueError
        payload = json.loads(decrypt_medical_value(current.snapshot_encrypted,
            business_id=template.business_id, subject_id=current.pk, purpose="document_template"))
        expected = _binding(current, template)
        if not isinstance(payload, dict) or set(payload) != set(expected) | {"content", "reason"}:
            raise ValueError
        if any(type(payload[key]) is not type(value) or payload[key] != value for key, value in expected.items()):
            raise ValueError
        content = validate_document_template(payload["content"], template.code)
        if content["version"] != current.revision or not isinstance(payload["reason"], str) or len(payload["reason"]) > 2000:
            raise ValueError
        return {"template": content, "reason": payload["reason"]}
    except (MedicalDocumentTemplateRevision.DoesNotExist, ModelValidationError, ValidationError,
            ValueError, TypeError, KeyError):
        raise MedicalDataUnavailable() from None
