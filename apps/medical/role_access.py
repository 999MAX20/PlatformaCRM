from dataclasses import dataclass

from django.contrib.auth import get_user_model
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.branches.access import accessible_branches
from apps.branches.models import Branch
from apps.businesses.capabilities import assert_resource_enabled
from apps.businesses.models import Business, RolePermission
from .models import MedicalRoleAssignment


MEDICAL_PERMISSION_ACTIONS = {
    "medical_patients": frozenset({"view", "create", "update", "approve"}),
    "medical_records": frozenset({"view", "create", "update", "manage"}),
    "medical_documents": frozenset({"view", "create", "update", "sign", "issue", "export"}),
    "medical_prescriptions": frozenset({"view", "create", "update", "sign"}),
    "medical_files": frozenset({"view", "create", "export"}),
    "medical_participation": frozenset({"view", "create", "update", "approve", "manage"}),
}

_ASSISTANT_ACTIONS = {
    "medical_patients": frozenset({"view"}),
    "medical_records": frozenset({"view", "create", "update"}),
    "medical_documents": frozenset({"create", "update"}),
    "medical_prescriptions": frozenset({"create", "update"}),
    "medical_files": frozenset({"view", "create"}),
}
_RECEPTION_ACTIONS = {
    "medical_patients": MEDICAL_PERMISSION_ACTIONS["medical_patients"],
    "medical_documents": frozenset({"issue"}),
}


def medical_action_allowed(kind, resource, action):
    if kind not in MedicalRoleAssignment.Kinds.values:
        return False
    limits = {MedicalRoleAssignment.Kinds.ASSISTANT: _ASSISTANT_ACTIONS,
              MedicalRoleAssignment.Kinds.RECEPTION: _RECEPTION_ACTIONS}.get(kind, MEDICAL_PERMISSION_ACTIONS)
    return action in limits.get(resource, ())


@dataclass(frozen=True)
class MedicalRoleContext:
    assignment_id: int
    member_id: int
    business_id: int
    user_id: int
    kind: str
    scope: str
    all_branches: bool


def assert_medical_role_permission(user, business, resource, action):
    """Role prerequisite only: patient/encounter access needs its own basis and audit."""
    if (not user or not user.is_authenticated or business is None or
            action not in MEDICAL_PERMISSION_ACTIONS.get(resource, ())):
        raise PermissionDenied()
    assignment = MedicalRoleAssignment.objects.select_related("member__user").filter(
        member__business_id=business.pk, member__user_id=user.pk, member__is_active=True,
        member__user__is_active=True, business_role__is_active=True,
        business_role__business_id=F("member__business_id"), revoked_at__isnull=True,
        granted_at__lte=timezone.now(), kind__in=MedicalRoleAssignment.Kinds.values,
    ).first()
    if (assignment is None or assignment.member.user.is_platform_user or
            assignment.granted_by_id == assignment.member.user_id):
        raise PermissionDenied()
    if not medical_action_allowed(assignment.kind, resource, action):
        raise PermissionDenied()
    assert_resource_enabled(business, "medical_records")
    permission = RolePermission.objects.filter(
        business_role_id=assignment.business_role_id, resource=resource, action=action,
        is_allowed=True, scope__in=(RolePermission.Scopes.OWN, RolePermission.Scopes.TEAM, RolePermission.Scopes.BUSINESS),
    ).first()
    if permission is None:
        raise PermissionDenied()
    return MedicalRoleContext(assignment.pk, assignment.member_id, business.pk, user.pk,
                              assignment.kind, permission.scope, assignment.all_branches)


def assert_medical_branch_permission(user, business, resource, action, *, branch, require_active=True):
    context = assert_medical_role_permission(user, business, resource, action)
    branches = Branch.objects.filter(business_id=business.pk, pk=getattr(branch, "pk", None))
    if require_active:
        branches = branches.filter(is_active=True, archived_at__isnull=True)
    if not context.all_branches:
        branches = branches.filter(medical_assignments__pk=context.assignment_id)
    current_business = Business.objects.get(pk=business.pk)
    current_user = get_user_model().objects.get(pk=context.user_id)
    branches = branches.filter(pk__in=accessible_branches(current_user, current_business).values("pk"))
    if not branches.exists():
        raise PermissionDenied()
    return context
