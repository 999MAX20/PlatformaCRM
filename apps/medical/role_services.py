from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError

from apps.branches.access import accessible_branches
from apps.branches.models import BranchAccess
from apps.businesses.capabilities import assert_resource_enabled
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from .models import MedicalRoleAssignment
from .role_access import medical_action_allowed
from .role_basis import record_role_reason, validate_role_reason
from .identity_crypto import medical_request_digest


def _owner_context(actor, business_id, *, require_module=True):
    _identifier(business_id, "business")
    if not actor or not actor.is_authenticated:
        raise PermissionDenied()
    current = get_user_model().objects.filter(pk=actor.pk, is_active=True).first()
    if current is None or current.is_platform_user:
        raise PermissionDenied()
    business = Business.objects.select_for_update().filter(pk=business_id, owner_id=current.pk).first()
    if business is None:
        raise PermissionDenied()
    if require_module:
        assert_resource_enabled(business, "medical_records")
    return current, business


def _identifier(value, field):
    if type(value) is not int or value <= 0:
        raise ValidationError({field: "Select an existing record."})


def _key(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 128:
        raise ValidationError({"idempotency_key": "Provide an idempotency key of at most 128 characters."})


def _revision(assignment, expected):
    if type(expected) is not int or expected < 0:
        raise ValidationError({"expected_revision": "Provide the current revision, or 0 for a new assignment."})
    if expected != (assignment.revision if assignment else 0):
        raise InvalidTransition("The medical assignment changed. Reload it before saving.")


def _rules(kind, permissions):
    if kind not in MedicalRoleAssignment.Kinds.values or not isinstance(permissions, list) or not 1 <= len(permissions) <= 64:
        raise ValidationError({"permissions": "Select a medical role kind and explicit permissions."})
    result = []
    seen = set()
    for item in permissions:
        if not isinstance(item, dict) or set(item) != {"resource", "action", "scope"}:
            raise ValidationError({"permissions": "Each permission requires resource, action and scope."})
        resource, action, scope = item["resource"], item["action"], item["scope"]
        if not all(isinstance(value, str) for value in (resource, action, scope)):
            raise ValidationError({"permissions": "Invalid permission."})
        if not medical_action_allowed(kind, resource, action) or scope not in {"own", "team", "business"}:
            raise ValidationError({"permissions": "This permission is not available for the selected medical role."})
        if (resource, action) in seen:
            raise ValidationError({"permissions": "Select each action once."})
        seen.add((resource, action))
        result.append({"resource": resource, "action": action, "scope": scope})
    return sorted(result, key=lambda item: (item["resource"], item["action"]))


def _audit(actor, business, instance, kind, before, after):
    write_actor_audit_log(actor=actor, business=business, instance=instance, action=AuditLog.Actions.UPDATE,
        metadata={"kind": kind, "category": AuditLog.Categories.ACCESS, "risk_level": AuditLog.RiskLevels.HIGH,
                  "before": before, "after": after})


def _snapshot(assignment):
    if assignment is None:
        return None
    return {"member": assignment.member_id, "role": assignment.business_role_id, "kind": assignment.kind,
            "all_branches": assignment.all_branches, "branches": sorted(assignment.branches.values_list("pk", flat=True)),
            "revision": assignment.revision, "granted_by": assignment.granted_by_id,
            "granted_at": assignment.granted_at.isoformat(),
            "revoked_at": assignment.revoked_at.isoformat() if assignment.revoked_at else None}


@transaction.atomic
def create_medical_role(*, actor, business_id, name, kind, permissions, idempotency_key):
    actor, business = _owner_context(actor, business_id)
    _key(idempotency_key)
    if not isinstance(name, str) or not name.strip() or len(name.strip()) > 128:
        raise ValidationError({"name": "Provide a role name of at most 128 characters."})
    name = name.strip()
    rules = _rules(kind, permissions)

    def operation():
        if BusinessRole.objects.filter(business=business, name=name).exists():
            raise ValidationError({"name": "A role with this name already exists."})
        role = BusinessRole.objects.create(business=business, name=name, preset_key=f"medical_{kind}")
        RolePermission.objects.bulk_create([RolePermission(business_role=role, **rule) for rule in rules])
        _audit(actor, business, role, "medical_role_defined", None, {"role": role.pk, "kind": kind, "permissions": rules})
        return CRMCommandResult(data={}, status_code=201, resource=role)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.role.define",
        idempotency_key=idempotency_key, payload={"name": name, "kind": kind, "permissions": rules}, operation=operation)
    role = BusinessRole.objects.filter(business=business, pk=result.resource_id if result.replayed else result.resource.pk).first()
    if role is None:
        raise InvalidTransition("This medical role no longer exists.")
    return role, result.replayed


@transaction.atomic
def assign_medical_role(*, actor, business_id, member_id, role_id, branch_ids, all_branches,
                        expected_revision, idempotency_key, reason=""):
    actor, business = _owner_context(actor, business_id)
    validate_role_reason(reason)
    _identifier(member_id, "member")
    _identifier(role_id, "role")
    _key(idempotency_key)
    member = BusinessMember.objects.select_for_update(of=("self",)).select_related("user").filter(
        business=business, pk=member_id, is_active=True, user__is_active=True).first()
    if member is None:
        raise NotFound()
    if member.user_id == actor.pk or member.user.is_platform_user:
        raise PermissionDenied()
    role = BusinessRole.objects.select_for_update().filter(business=business, pk=role_id, is_active=True).first()
    if role is None or not role.preset_key.startswith("medical_"):
        raise ValidationError({"role": "Select an active medical role of this business."})
    kind = role.preset_key.removeprefix("medical_")
    permissions = list(role.permissions.values("resource", "action", "scope", "is_allowed"))
    _rules(kind, [{key: row[key] for key in ("resource", "action", "scope")} for row in permissions if row["is_allowed"]])
    if type(all_branches) is not bool or not isinstance(branch_ids, list) or any(type(pk) is not int or pk <= 0 for pk in branch_ids):
        raise ValidationError({"branches": "Select valid branches and an explicit network scope."})
    if len(set(branch_ids)) != len(branch_ids) or (all_branches and branch_ids) or (not all_branches and not branch_ids):
        raise ValidationError({"branches": "Select distinct branches or all branches."})
    if all_branches:
        if not BranchAccess.objects.filter(member=member, all_branches=True).exists():
            raise ValidationError({"branches": "Grant the employee CRM network access first."})
    else:
        allowed = accessible_branches(member.user, business, active_only=True).filter(pk__in=branch_ids)
        if allowed.count() != len(branch_ids):
            raise ValidationError({"branches": "Select active branches available to the employee in this business."})
    assignment = MedicalRoleAssignment.objects.select_for_update().filter(member=member).first()

    def operation():
        nonlocal assignment
        validate_role_reason(reason, required=True)
        _revision(assignment, expected_revision)
        before = _snapshot(assignment)
        if (assignment is not None and assignment.revoked_at is None and assignment.business_role_id == role.pk and
                assignment.kind == kind and assignment.all_branches == all_branches and
                before["branches"] == sorted(branch_ids)):
            return CRMCommandResult(data={}, resource=assignment)
        if assignment is None:
            assignment = MedicalRoleAssignment(member=member, business_role=role, kind=kind, granted_by=actor)
        else:
            assignment.business_role, assignment.kind = role, kind
            assignment.granted_by, assignment.granted_at = actor, timezone.now()
            assignment.revoked_at = None
            assignment.revision += 1
        assignment.all_branches = all_branches
        assignment.full_clean(exclude=["branches"])
        assignment.save()
        assignment.branches.set(branch_ids)
        record_role_reason(business=business, assignment=assignment, actor=actor, action="grant", reason=reason)
        _audit(actor, business, assignment, "medical_role_assigned", before, _snapshot(assignment))
        return CRMCommandResult(data={}, resource=assignment)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.role.assign",
        idempotency_key=idempotency_key, payload={"member": member_id, "role": role_id, "branches": sorted(branch_ids),
            "all_branches": all_branches, "expected_revision": expected_revision,
            **({"reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)} if reason else {})},
        operation=operation)
    current = MedicalRoleAssignment.objects.get(member=member, pk=result.resource_id if result.replayed else result.resource.pk)
    return current, result.replayed


@transaction.atomic
def revoke_medical_role(*, actor, business_id, member_id, expected_revision, idempotency_key, reason=""):
    actor, business = _owner_context(actor, business_id, require_module=False)
    validate_role_reason(reason)
    _identifier(member_id, "member")
    _key(idempotency_key)
    member = BusinessMember.objects.select_for_update().filter(business=business, pk=member_id).first()
    if member is None:
        raise NotFound()
    assignment = MedicalRoleAssignment.objects.select_for_update().filter(member=member).first()
    if assignment is None:
        raise NotFound()

    def operation():
        validate_role_reason(reason, required=True)
        _revision(assignment, expected_revision)
        if assignment.revoked_at is None:
            before = _snapshot(assignment)
            assignment.revoked_at = timezone.now()
            assignment.revision += 1
            assignment.save(update_fields=["revoked_at", "revision", "updated_at"])
            record_role_reason(business=business, assignment=assignment, actor=actor, action="revoke", reason=reason)
            _audit(actor, business, assignment, "medical_role_revoked", before, _snapshot(assignment))
        return CRMCommandResult(data={}, resource=assignment)

    result = run_idempotent_crm_command(business=business, actor=actor, action="medical.role.revoke",
        idempotency_key=idempotency_key, payload={"member": member_id, "expected_revision": expected_revision,
            **({"reason_digest": medical_request_digest({"reason": reason}, business_id=business_id)} if reason else {})},
        operation=operation)
    assignment.refresh_from_db()
    return assignment, result.replayed
