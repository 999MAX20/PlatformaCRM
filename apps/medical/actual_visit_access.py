from datetime import datetime

from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.scheduling.availability import business_zone
from .role_access import assert_medical_branch_permission


def validate_actual_recording(*, mode, business, actor, client, resource, branch, start_at, reason):
    if mode != "medical_actual":
        return False
    context = assert_medical_branch_permission(actor, business, "medical_patients", "create", branch=branch)
    if context.kind not in ("doctor", "head", "reception"):
        raise PermissionDenied()
    if client.business_id != business.pk or resource.business_id != business.pk:
        raise PermissionDenied()
    if context.kind == "doctor" and resource.linked_user_id != actor.pk:
        raise PermissionDenied()
    if resource.linked_user_id is None:
        raise PermissionDenied()
    clinician = assert_medical_branch_permission(resource.linked_user, business, "medical_records", "create", branch=branch)
    if clinician.kind not in ("doctor", "head"):
        raise PermissionDenied()
    if not isinstance(start_at, datetime) or timezone.is_naive(start_at) or start_at > timezone.now():
        raise ValidationError({"start_at": "Provide the actual start time, not a future time."})
    if not isinstance(reason, str) or len(reason) > 2000:
        raise ValidationError({"reason": "Provide an explanation of at most 2000 characters."})
    zone = business_zone(business)
    if start_at.astimezone(zone).date() != timezone.now().astimezone(zone).date():
        if context.kind != "head":
            raise PermissionDenied()
        if not reason.strip():
            raise ValidationError({"reason": "Explain the earlier recording date."})
    return True
