from django.db import transaction
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import BusinessRole, RolePermission
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog


@transaction.atomic
def update_role_visibility(*, request, role, permission_ids, scope):
    """Change selected scopes atomically without granting any new action."""
    role = BusinessRole.objects.select_for_update(of=("self",)).select_related("business").get(pk=role.pk)
    assert_can(request.user, role.business, Resources.TEAM, Actions.MANAGE)
    if scope not in RolePermission.Scopes.values:
        raise ValidationError({"scope": "Invalid scope."})
    permissions = list(role.permissions.select_for_update().filter(pk__in=permission_ids))
    if not permission_ids or len(set(permission_ids)) != len(permission_ids) or len(permissions) != len(permission_ids):
        raise ValidationError({"permission_ids": "Select distinct permissions belonging to this role."})
    changed = [permission for permission in permissions if permission.scope != scope]
    if changed:
        before = [{"id": item.pk, "scope": item.scope, "is_allowed": item.is_allowed} for item in changed]
        for item in changed:
            item.scope = scope
        RolePermission.objects.bulk_update(changed, ["scope"])
        write_audit_log(request, AuditLog.Actions.UPDATE, role, metadata={
            "kind": "role_visibility", "before": before, "scope": scope,
            "permission_ids": [item.pk for item in changed],
        })
    return role
