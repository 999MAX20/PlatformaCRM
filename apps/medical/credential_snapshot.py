from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import ValidationError

from .credential_content import read_credential_revision, validate_credential_content
from .identity_crypto import MedicalDataUnavailable
from .models import MedicalCredentialProfile, MedicalCredentialRevision


def capture_document_credentials(*, business_id, member_id):
    """Internal document source; caller authorizes and audits the document operation."""
    result = {}
    for scope, target in (("clinic", None), ("clinician", member_id)):
        profile = MedicalCredentialProfile.objects.filter(business_id=business_id, member_id=target).first()
        version = (MedicalCredentialRevision.objects.filter(profile=profile, revision=profile.revision).first()
                   if profile and profile.revision else None)
        if profile and profile.revision and version is None:
            raise MedicalDataUnavailable()
        if version is None or (version.confirmed_by_id is None and version.confirmed_at is None):
            result[scope] = None
            continue
        if version.confirmed_by_id is None or version.confirmed_at is None:
            raise MedicalDataUnavailable()
        result[scope] = {"version_id": version.pk, "profile_id": profile.pk, "business_id": business_id,
            "member_id": target, "revision": version.revision, "confirmed_by_id": version.confirmed_by_id,
            "confirmed_at": version.confirmed_at.isoformat(), "content": read_credential_revision(version)["content"]}
    validate_document_credentials(result, business_id=business_id, member_id=member_id)
    return result


def validate_document_credentials(value, *, business_id, member_id):
    try:
        if not isinstance(value, dict) or set(value) != {"clinic", "clinician"}:
            raise ValueError
        for scope, target in (("clinic", None), ("clinician", member_id)):
            item = value[scope]
            if item is None:
                continue
            if not isinstance(item, dict) or set(item) != {"version_id", "profile_id", "business_id",
                    "member_id", "revision", "confirmed_by_id", "confirmed_at", "content"}:
                raise ValueError
            if any(type(item[key]) is not int or item[key] <= 0 for key in
                   ("version_id", "profile_id", "business_id", "revision", "confirmed_by_id")):
                raise ValueError
            if item["business_id"] != business_id or type(item["member_id"]) is not type(target) or item["member_id"] != target:
                raise ValueError
            timestamp = parse_datetime(item["confirmed_at"]) if isinstance(item["confirmed_at"], str) else None
            if timestamp is None or timestamp.tzinfo is None:
                raise ValueError
            content = validate_credential_content(item["content"], clinician=target is not None)
            required = ("specialty", "position") if target is not None else ("license",)
            if any(not content[key].strip() for key in required):
                raise ValueError
    except (ValueError, TypeError, KeyError, ValidationError):
        raise MedicalDataUnavailable() from None
