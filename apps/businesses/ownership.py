"""Ordinary, consent-based transfer of a business; no identity recovery bypass."""
import hashlib
import json
from datetime import timedelta

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.mfa import validate_step_up_token
from apps.accounts.models import User
from apps.accounts.session_security import revoke_user_refresh_sessions
from apps.businesses.access import normalize_role, owner_business_role
from apps.businesses.models import Business, BusinessMember, BusinessOwnershipTransfer, BusinessRole
from apps.core.audit import write_audit_log
from apps.core.domain_errors import DomainAPIException
from apps.core.models import AuditLog
from apps.core.permissions import is_platform_admin
from apps.support.models import SupportCase


class OwnershipConflict(DomainAPIException):
    status_code = 409
    default_detail = "Ownership or access changed. Cancel this request and prepare a new one."
    error_code = "request_conflict"
    default_code = error_code
    category = "conflict"


def active_actor(request, *, lock=False):
    users = User.objects.select_for_update() if lock else User.objects.all()
    actor = get_object_or_404(users, pk=request.user.pk, is_active=True)
    if actor.auth_epoch != request.user.auth_epoch:
        raise PermissionDenied("Sign in again before continuing.")
    return actor


def platform_actor(request):
    actor = active_actor(request, lock=True)
    if not is_platform_admin(actor):
        raise PermissionDenied("Only a platform administrator can transfer ownership.")
    validate_step_up_token(actor, request.headers.get("X-Zani-MFA-Step-Up", ""))
    return actor


def employee_role(business, role_id):
    if role_id is None:
        return None
    role = get_object_or_404(BusinessRole.objects.select_for_update(), pk=role_id, business=business, is_active=True)
    if role.preset_key == BusinessMember.Roles.OWNER:
        raise ValidationError({"previous_owner_business_role_id": "Choose an employee role, not owner."})
    return role


def role_key(role):
    if role is None:
        return ""
    key = normalize_role(role.preset_key)
    return key if key in BusinessMember.Roles.values and key != "owner" else BusinessMember.Roles.SPECIALIST


def state_revision(business, new_owner_id, previous_role_id):
    members = list(BusinessMember.objects.filter(business=business, user_id__in=[business.owner_id, new_owner_id])
                   .order_by("pk").values("id", "user_id", "role", "business_role_id", "is_active", "updated_at"))
    role_ids = {row["business_role_id"] for row in members} | {previous_role_id}
    roles = list(BusinessRole.objects.select_for_update().filter(pk__in=[pk for pk in role_ids if pk]).order_by("pk")
                 .values("id", "business_id", "name", "preset_key", "is_active", "permissions_json", "updated_at"))
    from apps.businesses.models import RolePermission
    permissions = list(RolePermission.objects.select_for_update().filter(business_role_id__in=role_ids - {None}).order_by("pk")
                       .values("business_role_id", "resource", "action", "scope", "is_allowed"))
    return hashlib.sha256(json.dumps({"owner": business.owner_id, "members": members,
        "roles": roles, "permissions": permissions}, sort_keys=True, default=str).encode()).hexdigest()


def audit(request, transfer, event):
    write_audit_log(request, AuditLog.Actions.UPDATE, transfer, business=transfer.business, metadata={
        "kind": "business_ownership_transfer", "event": event, "transfer_id": str(transfer.pk),
        "support_case_id": transfer.support_case_id, "previous_owner_id": transfer.previous_owner_id,
        "new_owner_id": transfer.new_owner_id, "previous_owner_role": transfer.previous_owner_role,
        "previous_owner_business_role_id": transfer.previous_owner_business_role_id,
        "category": AuditLog.Categories.ACCESS, "risk_level": AuditLog.RiskLevels.CRITICAL,
    })


def valid_participants(business, new_owner_id):
    people = {user.pk: user for user in User.objects.select_for_update().filter(
        pk__in=[business.owner_id, new_owner_id]).order_by("pk")}
    if new_owner_id == business.owner_id or len(people) != 2:
        raise ValidationError({"new_owner_id": "Choose a different active participant."})
    if any(not user.is_active or user.is_platform_user for user in people.values()):
        raise ValidationError({"new_owner_id": "Both participants must have active merchant accounts."})
    members = {member.user_id: member for member in BusinessMember.objects.select_for_update()
               .filter(business=business, user_id__in=people).order_by("pk")}
    if new_owner_id not in members or not members[new_owner_id].is_active:
        raise ValidationError({"new_owner_id": "The recipient must be an active member of this business."})
    if business.owner_id not in members or not members[business.owner_id].is_active:
        raise ValidationError("The current owner needs an active membership before transfer.")
    return people, members


@transaction.atomic
def prepare_transfer(request, business_id, *, new_owner_id, expected_owner_id,
                     previous_owner_business_role_id, support_case_id, reason):
    actor = platform_actor(request)
    business = get_object_or_404(Business.objects.select_for_update(no_key=True), pk=business_id)
    if business.owner_id != expected_owner_id:
        raise OwnershipConflict()
    valid_participants(business, new_owner_id)
    previous_role = employee_role(business, previous_owner_business_role_id)
    case = get_object_or_404(SupportCase, pk=support_case_id, business=business)
    pending = BusinessOwnershipTransfer.objects.filter(business=business, status="pending").first()
    if pending:
        if pending.expires_at > timezone.now():
            raise OwnershipConflict("A transfer is already awaiting confirmation.")
        pending.status = "cancelled"
        pending.cancelled_at = timezone.now()
        pending.save(update_fields=["status", "cancelled_at", "updated_at"])
        audit(request, pending, "expired")
    transfer = BusinessOwnershipTransfer.objects.create(
        business=business, previous_owner_id=business.owner_id, new_owner_id=new_owner_id,
        created_by=actor, support_case=case, reason=reason,
        previous_owner_role=role_key(previous_role), previous_owner_business_role=previous_role,
        expected_revision=state_revision(business, new_owner_id, previous_owner_business_role_id),
        expires_at=timezone.now() + timedelta(hours=24),
    )
    audit(request, transfer, "prepared")
    return transfer


def locked_transfer(transfer_id, business_id=None):
    # The Business lock also serializes profile repair and ordinary member writes.
    lookup = BusinessOwnershipTransfer.objects.filter(pk=transfer_id)
    if business_id is not None:
        lookup = lookup.filter(business_id=business_id)
    reference = get_object_or_404(lookup.only("business_id"))
    business = get_object_or_404(Business.objects.select_for_update(no_key=True), pk=reference.business_id)
    transfer = get_object_or_404(BusinessOwnershipTransfer.objects.select_for_update(), pk=transfer_id, business=business)
    transfer.business = business
    return business, transfer


def assert_current(business, transfer):
    if transfer.status != "pending" or transfer.expires_at <= timezone.now():
        raise OwnershipConflict("This transfer is no longer pending.")
    if business.owner_id != transfer.previous_owner_id:
        raise OwnershipConflict()
    people, members = valid_participants(business, transfer.new_owner_id)
    employee_role(business, transfer.previous_owner_business_role_id)
    if state_revision(business, transfer.new_owner_id, transfer.previous_owner_business_role_id) != transfer.expected_revision:
        raise OwnershipConflict()
    return people, members


@transaction.atomic
def participant_decision(request, transfer_id, *, decision):
    if decision not in {"confirm", "decline"}:
        raise ValidationError({"decision": "Choose confirm or decline."})
    actor = active_actor(request)
    # An unrelated authenticated user must not even resolve the business/terms.
    from django.db.models import Q
    get_object_or_404(BusinessOwnershipTransfer.objects.filter(
        Q(previous_owner=actor) | Q(new_owner=actor)), pk=transfer_id)
    business, transfer = locked_transfer(transfer_id)
    active_actor(request)
    if transfer.status != "pending":
        raise OwnershipConflict("This transfer is no longer pending.")
    if decision == "decline":
        transfer.status = "cancelled"
        transfer.cancelled_at = timezone.now()
        transfer.save(update_fields=["status", "cancelled_at", "updated_at"])
        audit(request, transfer, "declined")
        return transfer
    people, _ = assert_current(business, transfer)
    if actor.auth_epoch != people[actor.pk].auth_epoch:
        raise OwnershipConflict("Authentication changed. Sign in again.")
    actor = people[actor.pk]
    prefix = "previous_owner" if actor.pk == transfer.previous_owner_id else "new_owner"
    confirmed = f"{prefix}_confirmed_at"
    epoch = f"{prefix}_auth_epoch"
    if getattr(transfer, confirmed) is not None:
        if getattr(transfer, epoch) != actor.auth_epoch:
            raise OwnershipConflict("Authentication changed. Prepare a new transfer.")
        return transfer
    setattr(transfer, confirmed, timezone.now())
    setattr(transfer, epoch, actor.auth_epoch)
    transfer.save(update_fields=[confirmed, epoch, "updated_at"])
    audit(request, transfer, f"{prefix}_confirmed")
    return transfer


@transaction.atomic
def finish_transfer(request, business_id, transfer_id, *, action):
    if action not in {"execute", "cancel"}:
        raise ValidationError({"action": "Choose execute or cancel."})
    platform_actor(request)
    business, transfer = locked_transfer(transfer_id, business_id)
    if transfer.status != "pending":
        raise OwnershipConflict("This transfer is no longer pending.")
    if action == "cancel":
        transfer.status = "cancelled"
        transfer.cancelled_at = timezone.now()
        transfer.save(update_fields=["status", "cancelled_at", "updated_at"])
        audit(request, transfer, "cancelled")
        return transfer
    people, members = assert_current(business, transfer)
    for prefix in ("previous_owner", "new_owner"):
        if not getattr(transfer, f"{prefix}_confirmed_at"):
            raise ValidationError("Both participants must confirm these terms before transfer.")
        if getattr(transfer, f"{prefix}_auth_epoch") != people[getattr(transfer, f"{prefix}_id")].auth_epoch:
            raise OwnershipConflict("A participant's authentication changed. Prepare a new transfer.")
    previous = members[transfer.previous_owner_id]
    previous.role = transfer.previous_owner_role or BusinessMember.Roles.SPECIALIST
    previous.business_role_id = transfer.previous_owner_business_role_id
    previous.is_active = bool(transfer.previous_owner_role)
    previous.save(update_fields=["role", "business_role", "is_active", "updated_at"])
    recipient = members[transfer.new_owner_id]
    recipient.role = BusinessMember.Roles.OWNER
    recipient.business_role = owner_business_role(business)
    recipient.save(update_fields=["role", "business_role", "updated_at"])
    business.owner_id = transfer.new_owner_id
    business.save(update_fields=["owner", "updated_at"])
    # Re-login uses current memberships and the new owner's privileged MFA policy.
    for person in people.values():
        revoke_user_refresh_sessions(person)
    transfer.status = "completed"
    transfer.completed_at = timezone.now()
    transfer.save(update_fields=["status", "completed_at", "updated_at"])
    audit(request, transfer, "completed")
    return transfer
