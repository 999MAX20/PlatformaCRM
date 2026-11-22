import json

from django.core.exceptions import ValidationError as ModelValidationError
from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import InvalidTransition
from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalCredentialProfile, MedicalCredentialRevision


def validate_credential_content(content, *, clinician):
    limits = {"specialty": 255, "position": 255, "qualification": 4000} if clinician else {"license": 4000}
    if not isinstance(content, dict) or set(content) != set(limits):
        raise ValidationError({"credentials": "Provide the fields for this profile scope."})
    if any(not isinstance(content[key], str) or len(content[key]) > limit for key, limit in limits.items()):
        raise ValidationError({"credentials": "Provide credential text within the field limits."})
    return dict(content)


def _binding(version, profile):
    return {"schema": 1, "business_id": profile.business_id, "profile_id": profile.pk,
        "member_id": profile.member_id, "version_id": version.pk, "revision": version.revision,
        "author_id": version.author_id, "created_at": version.created_at.isoformat()}


@transaction.atomic
def append_credential_revision(*, profile, author, content, reason=""):
    """Internal storage; caller must authorize and audit. This does not confirm credentials."""
    Business.objects.select_for_update().get(pk=profile.business_id)
    current = MedicalCredentialProfile.objects.select_for_update().get(pk=profile.pk, business_id=profile.business_id)
    current.full_clean()
    if current.revision != profile.revision:
        raise InvalidTransition("The credentials changed; reload the current revision.")
    content = validate_credential_content(content, clinician=current.member_id is not None)
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide a reason of at most 2000 characters."})
    if not BusinessMember.objects.filter(business_id=current.business_id, user_id=author.pk,
                                         is_active=True, user__is_active=True).exists():
        raise ValidationError({"author": "Select an active member of this business."})
    staging = encrypt_medical_value("{}", business_id=current.business_id,
        subject_id=current.pk, purpose="credential_staging")
    version = MedicalCredentialRevision.objects.create(profile=current, revision=current.revision + 1,
        author=author, content_encrypted=staging)
    payload = {**_binding(version, current), "content": content, "reason": reason}
    version.content_encrypted = encrypt_medical_value(json.dumps(payload, ensure_ascii=False, sort_keys=True),
        business_id=current.business_id, subject_id=version.pk, purpose="medical_credentials")
    version.save(update_fields=["content_encrypted"])
    current.revision = version.revision
    current.save(update_fields=["revision", "updated_at"])
    return version


def read_credential_revision(version):
    """Internal decryptor; caller must authorize and audit the exact version."""
    try:
        current = MedicalCredentialRevision.objects.select_related("profile").get(pk=version.pk)
        profile = current.profile
        profile.clean()
        if current.revision > profile.revision:
            raise ValueError
        payload = json.loads(decrypt_medical_value(current.content_encrypted,
            business_id=profile.business_id, subject_id=current.pk, purpose="medical_credentials"))
        expected = _binding(current, profile)
        if not isinstance(payload, dict) or set(payload) != set(expected) | {"content", "reason"}:
            raise ValueError
        if any(type(payload[key]) is not type(value) or payload[key] != value for key, value in expected.items()):
            raise ValueError
        content = validate_credential_content(payload["content"], clinician=profile.member_id is not None)
        if not isinstance(payload["reason"], str) or len(payload["reason"]) > 2000:
            raise ValueError
        return {"content": content, "reason": payload["reason"]}
    except (MedicalCredentialRevision.DoesNotExist, ModelValidationError, ValidationError,
            ValueError, TypeError, KeyError):
        raise MedicalDataUnavailable() from None
