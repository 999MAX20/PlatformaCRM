import json

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value
from .models import PatientRepresentative
from .identity_policy import _localized_label


def assert_representative_authority(*, business_id, patient_id, representative_client_id, representative_id, permission):
    """Authority prerequisite only; the issuing/opening flow must also authenticate its recipient and audit access."""
    if (any(type(value) is not int or value <= 0 for value in
            (business_id, patient_id, representative_client_id, representative_id)) or
            not isinstance(permission, str) or not permission):
        raise PermissionDenied()
    now = timezone.now()
    relation = PatientRepresentative.objects.filter(pk=representative_id,
        patient_id=patient_id, patient__business_id=business_id, patient__client__business_id=business_id,
        representative_client_id=representative_client_id, representative_client__business_id=business_id,
        revoked_at__isnull=True, verified_at__lte=now, valid_from__lte=now).first()
    if relation is None or (relation.valid_until is not None and relation.valid_until <= now):
        raise PermissionDenied()
    authority = read_representative_authority(relation, business_id=business_id)
    if permission not in authority["permissions"]:
        raise PermissionDenied()


def read_representative_authority(relation, *, business_id):
    """Internal decoding; callers must authorize and audit before exposing any projection."""
    try:
        authority = json.loads(decrypt_medical_value(relation.authority_encrypted, business_id=business_id,
            subject_id=relation.pk, purpose="representative_authority"))
        if (not isinstance(authority, dict) or authority.get("patient_id") != relation.patient_id or
                authority.get("representative_client_id") != relation.representative_client_id or
                authority.get("valid_from") != relation.valid_from.isoformat() or
                authority.get("valid_until") != (relation.valid_until.isoformat() if relation.valid_until else None) or
                not isinstance(authority.get("permissions"), list) or
                any(not isinstance(value, str) for value in authority["permissions"])):
            raise ValueError
        labels = authority.get("permission_labels")
        if labels is not None:
            if not isinstance(labels, dict) or set(labels) != set(authority["permissions"]):
                raise ValueError
            for label in labels.values():
                _localized_label(label)
    except (ValueError, TypeError):
        raise MedicalDataUnavailable() from None
    return authority
