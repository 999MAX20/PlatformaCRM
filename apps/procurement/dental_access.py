from django.contrib.auth import get_user_model
from rest_framework.exceptions import PermissionDenied
from apps.branches.models import Branch
from apps.businesses.models import Business
from apps.medical.role_access import assert_medical_branch_permission


def doctor_context(actor, business_id, branch_id):
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    actor = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    business = Business.objects.select_for_update().filter(pk=business_id).first()
    branch = Branch.objects.filter(pk=branch_id, business=business, is_active=True, archived_at__isnull=True).first()
    if actor is None or actor.is_platform_user or business is None or branch is None:
        raise PermissionDenied()
    role = assert_medical_branch_permission(actor, business, "medical_records", "create", branch=branch)
    if role.kind not in ("doctor", "head"):
        raise PermissionDenied()
    return actor, business, branch
