from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.branches.access import accessible_branches
from apps.branches.models import BranchAccess
from apps.businesses.capabilities import resource_is_enabled
from apps.businesses.models import BusinessMember, BusinessRole
from .models import MedicalRoleAssignment, MedicalRoleRevision
from .role_basis import read_role_reason
from .role_access import MEDICAL_PERMISSION_ACTIONS, medical_action_allowed
from .role_services import _identifier, _owner_context, _snapshot


def _page_inputs(after_id, limit, query):
    if after_id is not None:
        _identifier(after_id, "after_id")
    if type(limit) is not int or not 1 <= limit <= 50:
        raise ValidationError({"limit": "Select a page size from 1 to 50."})
    if not isinstance(query, str) or len(query) > 100:
        raise ValidationError({"query": "Provide at most 100 characters."})


def _page(rows, limit, project):
    rows = list(rows.order_by("pk")[:limit + 1])
    return {"results": [project(row) for row in rows[:limit]],
            "next_after_id": rows[limit - 1].pk if len(rows) > limit else None}


def _member(business, member_id):
    _identifier(member_id, "member_id")
    member = BusinessMember.objects.select_related("user").filter(business=business, pk=member_id).first()
    if member is None:
        raise NotFound()
    return member


def _member_data(member):
    return {"id": member.pk, "name": member.user.full_name,
            "is_active": member.is_active, "account_active": member.user.is_active}


@transaction.atomic
def read_medical_role_workspace(*, actor, business_id):
    _, business = _owner_context(actor, business_id, require_module=False)
    return {"can_assign": resource_is_enabled(business, "medical_records"),
            "permissions_by_kind": {kind: [
                {"resource": resource, "actions": sorted(action for action in actions
                    if medical_action_allowed(kind, resource, action))}
                for resource, actions in MEDICAL_PERMISSION_ACTIONS.items()
                if any(medical_action_allowed(kind, resource, action) for action in actions)
            ] for kind in MedicalRoleAssignment.Kinds.values}}


@transaction.atomic
def read_medical_role_definitions(*, actor, business_id, after_id=None, limit=20, query=""):
    _, business = _owner_context(actor, business_id, require_module=False)
    _page_inputs(after_id, limit, query)
    rows = BusinessRole.objects.filter(business=business,
        preset_key__in=[f"medical_{kind}" for kind in MedicalRoleAssignment.Kinds.values]).prefetch_related("permissions")
    if after_id is not None:
        rows = rows.filter(pk__gt=after_id)
    if query.strip():
        rows = rows.filter(name__icontains=query.strip())
    return _page(rows, limit, lambda role: {"id": role.pk, "name": role.name, "is_active": role.is_active,
        "kind": role.preset_key.removeprefix("medical_"),
        "permissions": [{"resource": rule.resource, "action": rule.action, "scope": rule.scope,
                         "is_allowed": rule.is_allowed} for rule in role.permissions.all()]})


@transaction.atomic
def read_medical_role_members(*, actor, business_id, after_id=None, limit=20, query=""):
    _, business = _owner_context(actor, business_id, require_module=False)
    _page_inputs(after_id, limit, query)
    rows = BusinessMember.objects.filter(business=business).select_related("user")
    if after_id is not None:
        rows = rows.filter(pk__gt=after_id)
    if query.strip():
        rows = rows.filter(user__full_name__icontains=query.strip())
    return _page(rows, limit, _member_data)


@transaction.atomic
def read_medical_role_member_context(*, actor, business_id, member_id):
    actor, business = _owner_context(actor, business_id, require_module=False)
    member = _member(business, member_id)
    assignment = MedicalRoleAssignment.objects.select_related("business_role").filter(member=member).first()
    if assignment is not None and assignment.business_role.business_id != business.pk:
        raise NotFound()
    can_assign = (resource_is_enabled(business, "medical_records") and member.is_active
                  and member.user.is_active and not member.user.is_platform_user and member.user_id != actor.pk)
    return {"member": _member_data(member), "assignment": _snapshot(assignment),
            "role_name": assignment.business_role.name if assignment else None,
            "role_active": assignment.business_role.is_active if assignment else None,
            "can_assign": can_assign, "can_revoke": assignment is not None and assignment.revoked_at is None,
            "can_assign_all_branches": can_assign and BranchAccess.objects.filter(member=member, all_branches=True).exists()}


@transaction.atomic
def read_medical_role_member_branches(*, actor, business_id, member_id, after_id=None, limit=20, query=""):
    _, business = _owner_context(actor, business_id, require_module=False)
    _page_inputs(after_id, limit, query)
    member = _member(business, member_id)
    rows = accessible_branches(member.user, business, active_only=True)
    if after_id is not None:
        rows = rows.filter(pk__gt=after_id)
    if query.strip():
        rows = rows.filter(name__icontains=query.strip())
    return _page(rows, limit, lambda branch: {"id": branch.pk, "name": branch.name})


@transaction.atomic
def read_medical_role_history(*, actor, business_id, member_id, after_id=None, limit=20):
    _, business = _owner_context(actor, business_id, require_module=False)
    _page_inputs(after_id, limit, "")
    member = _member(business, member_id)
    rows = MedicalRoleRevision.objects.filter(assignment__member=member,
        assignment__business_role__business=business).select_related("actor")
    if after_id is not None:
        rows = rows.filter(pk__gt=after_id)
    return _page(rows, limit, lambda row: {"id": row.pk, "revision": row.revision,
        "action": row.action, "actor_name": row.actor.full_name, "created_at": row.created_at,
        "reason": read_role_reason(row, business_id=business.pk)})
