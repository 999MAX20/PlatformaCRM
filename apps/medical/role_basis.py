import json

from rest_framework.exceptions import ValidationError

from .identity_crypto import MedicalDataUnavailable, decrypt_medical_value, encrypt_medical_value
from .models import MedicalRoleRevision


def validate_role_reason(reason, *, required=False):
    if not isinstance(reason, str) or len(reason) > 2000 or (required and not reason.strip()):
        raise ValidationError({"reason": "Provide the reason for this medical role decision (at most 2000 characters)."})


def record_role_reason(*, business, assignment, actor, action, reason):
    encrypted = encrypt_medical_value(json.dumps({"reason": reason, "revision": assignment.revision,
        "action": action}, ensure_ascii=False), business_id=business.pk,
        subject_id=assignment.pk, purpose="medical_role_reason")
    return MedicalRoleRevision.objects.create(assignment=assignment, revision=assignment.revision,
        actor=actor, action=action, reason_encrypted=encrypted)


def read_role_reason(row, *, business_id):
    try:
        value = json.loads(decrypt_medical_value(row.reason_encrypted, business_id=business_id,
            subject_id=row.assignment_id, purpose="medical_role_reason"))
        if (not isinstance(value, dict) or set(value) != {"reason", "revision", "action"}
                or value["revision"] != row.revision or value["action"] != row.action
                or not isinstance(value["reason"], str) or not value["reason"].strip()
                or len(value["reason"]) > 2000):
            raise ValueError
        return value["reason"]
    except (ValueError, TypeError):
        raise MedicalDataUnavailable() from None
