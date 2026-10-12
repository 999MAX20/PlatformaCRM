"""Branch grants narrow existing permissions; they never confer a role permission."""
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import BusinessMember
from apps.core.permissions import platform_admin_has_global_access, user_can_access_business
from .models import Branch, BranchAccess


def accessible_branches(user, business, *, active_only=False):
    branches = Branch.objects.filter(business=business)
    if active_only:
        branches = branches.filter(is_active=True, archived_at__isnull=True)
    if not user_can_access_business(user, business):
        return branches.none()
    if business.owner_id == user.pk or platform_admin_has_global_access(user):
        return branches
    member = BusinessMember.objects.filter(business=business, user=user, is_active=True).first()
    if member is None:
        return branches.none()
    grant = BranchAccess.objects.filter(member=member).first()
    if grant is None:
        return branches.none()
    return branches if grant.all_branches else branches.filter(access_grants=grant)


def assert_branch_access(user, business, branch, *, active=False):
    if branch is None or branch.business_id != business.pk:
        raise ValidationError({"branch": "Select a branch of this business."})
    if not accessible_branches(user, business, active_only=active).filter(pk=branch.pk).exists():
        raise PermissionDenied("This branch is outside your permitted scope.")


def assert_all_branch_access(user, business):
    """Shared staff/catalog changes affect every branch and require network scope."""
    if business.owner_id == user.pk or platform_admin_has_global_access(user):
        return
    if Branch.objects.filter(business=business).exclude(pk__in=accessible_branches(user, business)).exists():
        raise PermissionDenied("This change affects branches outside your permitted scope.")


def assert_network_grant(user, business):
    """Adding locations or granting future locations requires an explicit network grant."""
    if business.owner_id == user.pk or platform_admin_has_global_access(user):
        return
    if not BranchAccess.objects.filter(member__business=business, member__user=user,
                                      member__is_active=True, all_branches=True).exists():
        raise PermissionDenied("This change requires access to all current and future branches.")


def branch_write_allowed(user, business, obj):
    model = getattr(getattr(obj, "_meta", None), "label_lower", "")
    if model == "services.service":
        return not Branch.objects.filter(business=business).exclude(pk__in=accessible_branches(user, business)).exists()
    if model == "scheduling.resource" and obj.pk:
        return not obj.branch_assignments.exclude(branch__in=accessible_branches(user, business)).exists()
    branch_id = getattr(obj, "branch_id", None)
    if branch_id is None:
        return True
    return accessible_branches(user, business).filter(pk=branch_id).exists()
