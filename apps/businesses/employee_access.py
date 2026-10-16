"""Consent-bound repairs of employee access within one Business."""
import hashlib
import json
import uuid
from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.accounts.recovery import platform_actor
from apps.billing.entitlements import EntitlementMetrics, assert_entitlement_allows
from apps.businesses.models import Business, BusinessMember, BusinessInvitation, BusinessRole, EmployeeAccessRepair, RolePermission
from apps.businesses.ownership import OwnershipConflict, active_actor, role_key
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog
from apps.support.models import SupportCase


CONSENT_ACTIONS = {"restore", "role", "reissue"}
REPAIR_ACTIONS = CONSENT_ACTIONS | {"disable", "revoke"}


def revision(business, target):
    fields = ("user_id", "role", "business_role_id", "is_active", "updated_at") if isinstance(target, BusinessMember) else (
        "email", "role", "business_role_id", "team_id", "token", "expires_at", "accepted_at", "revoked_at", "updated_at")
    state = {field: getattr(target, field) for field in fields}
    state.update(owner=business.owner_id, target=target.pk)
    if isinstance(target, BusinessMember):
        state["user"] = list(User.objects.filter(pk=target.user_id).values("is_active", "role", "is_superuser", "auth_epoch"))
    return hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()


def request_revision(business, target, role):
    state = {"target": revision(business, target)}
    if role:
        state["role"] = [role.pk, role.name, role.preset_key, role.is_active, role.permissions_json, str(role.updated_at)]
        state["permissions"] = list(RolePermission.objects.select_for_update().filter(business_role=role).order_by("pk").values(
            "resource", "action", "scope", "is_allowed"))
    return hashlib.sha256(json.dumps(state, sort_keys=True, default=str).encode()).hexdigest()


def target_for(business, action, target_id):
    model = BusinessMember if action in {"disable", "restore", "role"} else BusinessInvitation
    target = get_object_or_404(model.objects.select_for_update(), business=business, pk=target_id)
    if isinstance(target, BusinessMember):
        # A person may own one business and be an employee in another. Lock
        # both participants in stable order even across different Businesses.
        people = {person.pk: person for person in User.objects.select_for_update().filter(
            pk__in=[business.owner_id, target.user_id]).order_by("pk")}
        target.user = people[target.user_id]
        if target.user_id == business.owner_id or target.role == "owner" or target.user.is_platform_user:
            raise PermissionDenied("The owner and platform accounts cannot be repaired here.")
        if action in {"restore", "role"} and not target.user.is_active:
            raise ValidationError("The account is globally disabled; business repair cannot unlock it.")
        if action == "disable" and not target.is_active or action == "restore" and target.is_active:
            raise ValidationError("Membership already has this state.")
    else:
        if target.accepted_at:
            raise ValidationError("Accepted invitations cannot be repaired.")
        if action == "revoke" and target.revoked_at:
            raise ValidationError("Invitation is already revoked.")
        if target.role == "owner" or target.email.casefold() == business.owner.email.casefold():
            raise PermissionDenied("An owner invitation cannot be repaired here.")
        if action == "reissue" and BusinessMember.objects.filter(business=business, user__email__iexact=target.email, is_active=True).exists():
            raise ValidationError("The recipient already has active access.")
    return target


def selected_role(business, role_id):
    if role_id is None:
        return None
    role = get_object_or_404(BusinessRole.objects.select_for_update(), business=business, pk=role_id, is_active=True)
    if role.preset_key == "owner":
        raise ValidationError("Choose an employee role.")
    return role


def audit(request, item, event):
    write_audit_log(request, AuditLog.Actions.UPDATE, item, business=item.business, metadata={
        "kind": "employee_access_repair", "event": event, "request_id": str(item.pk),
        "operation": item.action, "target_id": item.target_id,
        "target_role_id": item.target_role_id, "support_case_id": item.support_case_id,
        "reason": item.reason, "category": AuditLog.Categories.ACCESS, "risk_level": AuditLog.RiskLevels.HIGH})


@transaction.atomic
def prepare(request, business_id, *, action, target_id, target_role_id, support_case_id, expected_revision, reason, request_id):
    if action not in REPAIR_ACTIONS or not reason.strip() or len(reason) > 2000:
        raise ValidationError("Choose a supported action and record the reason.")
    actor = platform_actor(request)
    business = get_object_or_404(Business.objects.select_for_update(), pk=business_id)
    existing = EmployeeAccessRepair.objects.filter(pk=request_id, business=business, prepared_by=actor).first()
    if existing:
        if (existing.action, existing.target_id, existing.target_role_id if action == "role" else None,
            existing.support_case_id, existing.reason) != (action, target_id, target_role_id, support_case_id, reason):
            raise OwnershipConflict()
        return existing
    target = target_for(business, action, target_id)
    if revision(business, target) != expected_revision:
        raise OwnershipConflict()
    case = get_object_or_404(SupportCase, pk=support_case_id, business=business)
    if case.status == "resolved":
        raise ValidationError("Reopen the support case first.")
    if action != "role" and target_role_id is not None or action == "role" and target_role_id is None:
        raise ValidationError({"target_role_id": "A target role is required only for a role change."})
    role = selected_role(business, target_role_id if action == "role" else target.business_role_id) if action in CONSENT_ACTIONS else None
    if action == "role" and role.pk == target.business_role_id:
        raise ValidationError("Choose a different role.")
    owner = User.objects.select_for_update().get(pk=business.owner_id)
    if action in CONSENT_ACTIONS and (not owner.is_active or not BusinessMember.objects.filter(
            business=business, user=owner, is_active=True).exists()):
        raise ValidationError("The current owner must be able to confirm this request.")
    person = target.user if isinstance(target, BusinessMember) else target
    item = EmployeeAccessRepair.objects.create(id=request_id, business=business,
        target_id=target.pk, target_name=person.full_name or person.email, target_email=person.email,
        target_role_id=role.pk if role else None, target_role_name=role.name if role else "",
        target_role_key=role_key(role) if action == "role" else target.role,
        action=action, support_case=case, reason=reason,
        revision=request_revision(business, target, role), owner=owner, owner_epoch=owner.auth_epoch,
        prepared_by=actor, expires_at=timezone.now() + timedelta(hours=24))
    audit(request, item, "prepared")
    return item


def locked_request(business_id, repair_id):
    business = get_object_or_404(Business.objects.select_for_update(), pk=business_id)
    item = get_object_or_404(EmployeeAccessRepair.objects.select_for_update(), pk=repair_id, business=business)
    return business, item


def current(business, item):
    if item.status != "pending" or item.expires_at <= timezone.now() or item.owner_id != business.owner_id:
        raise OwnershipConflict()
    target = target_for(business, item.action, item.target_id)
    role = selected_role(business, item.target_role_id)
    owner = User.objects.select_for_update().get(pk=item.owner_id)
    if item.action in CONSENT_ACTIONS and (not owner.is_active or owner.auth_epoch != item.owner_epoch or
            not BusinessMember.objects.filter(business=business, user=owner, is_active=True).exists()):
        raise OwnershipConflict()
    if request_revision(business, target, role) != item.revision:
        raise OwnershipConflict()
    return target, role


@transaction.atomic
def owner_decide(request, repair_id, decision):
    if decision not in {"confirm", "decline"}:
        raise ValidationError("Choose confirm or decline.")
    actor = active_actor(request)
    stub = get_object_or_404(EmployeeAccessRepair, pk=repair_id, owner=actor, action__in=CONSENT_ACTIONS)
    business, item = locked_request(stub.business_id, repair_id)
    current(business, item)
    # Recheck authentication after acquiring owner locks.
    active_actor(request)
    if item.owner_confirmed_at:
        raise OwnershipConflict()
    if decision == "confirm":
        item.owner_confirmed_at = timezone.now()
    else:
        item.status = "declined"
    item.save(update_fields=["owner_confirmed_at", "status", "updated_at"])
    audit(request, item, decision)
    return item


@transaction.atomic
def operate(request, business_id, repair_id, action):
    if action not in {"execute", "cancel"}:
        raise ValidationError("Choose execute or cancel.")
    actor = platform_actor(request)
    business, item = locked_request(business_id, repair_id)
    if item.status == "completed" and action == "execute" or item.status == "cancelled" and action == "cancel":
        return item
    if item.status != "pending":
        raise OwnershipConflict()
    if action == "cancel":
        item.status = "cancelled"
    else:
        target, role = current(business, item)
        if item.support_case.status == "resolved" or item.action in CONSENT_ACTIONS and not item.owner_confirmed_at:
            raise ValidationError("An open case and required owner confirmation are needed.")
        if item.action == "restore":
            assert_entitlement_allows(business, EntitlementMetrics.USERS)
        if item.action in {"disable", "restore"}:
            target.is_active = item.action == "restore"
            target.save(update_fields=["is_active", "updated_at"])
        elif item.action == "role":
            target.business_role = role
            target.role = role_key(role)
            target.save(update_fields=["business_role", "role", "updated_at"])
        elif item.action == "revoke":
            target.revoked_at = timezone.now()
            target.save(update_fields=["revoked_at", "updated_at"])
        else:
            if target.team_id and (target.team.business_id != business.pk or not target.team.is_active):
                raise ValidationError("The invitation team is inactive.")
            target.token = uuid.uuid4()
            target.revoked_at = None
            target.expires_at = timezone.now() + timedelta(days=7)
            target.save(update_fields=["token", "revoked_at", "expires_at", "updated_at"])
        item.status = "completed"
        item.completed_at = timezone.now()
        item.executed_by = actor
    item.save(update_fields=["status", "completed_at", "executed_by", "updated_at"])
    audit(request, item, item.status)
    return item
