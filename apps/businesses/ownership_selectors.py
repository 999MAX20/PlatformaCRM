from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import User
from apps.businesses.models import BusinessMember, BusinessOwnershipTransfer, BusinessRole
from apps.core.permissions import is_platform_admin


def person(user):
    return {"id": user.pk, "name": user.full_name or user.email, "email": user.email}


def transfer_rows():
    return BusinessOwnershipTransfer.objects.select_related(
        "business", "previous_owner", "new_owner", "previous_owner_business_role")


def transfer_projection(transfer, actor):
    status = transfer.status
    if status == "pending" and transfer.expires_at <= timezone.now():
        status = "expired"
    pending = status == "pending"
    participant = actor.pk in {transfer.previous_owner_id, transfer.new_owner_id}
    confirmed = transfer.previous_owner_confirmed_at if actor.pk == transfer.previous_owner_id else transfer.new_owner_confirmed_at
    return {
        "id": str(transfer.pk), "business": {"id": transfer.business_id, "name": transfer.business.name, "timezone": transfer.business.timezone},
        "previous_owner": person(transfer.previous_owner), "new_owner": person(transfer.new_owner),
        "previous_owner_role": transfer.previous_owner_role,
        "previous_owner_business_role": ({"id": transfer.previous_owner_business_role_id,
            "name": transfer.previous_owner_business_role.name} if transfer.previous_owner_business_role_id else None),
        "reason": transfer.reason, "support_case_id": transfer.support_case_id, "status": status,
        "previous_owner_confirmed_at": transfer.previous_owner_confirmed_at,
        "new_owner_confirmed_at": transfer.new_owner_confirmed_at,
        "expires_at": transfer.expires_at, "completed_at": transfer.completed_at,
        "actions": {"confirm": pending and participant and confirmed is None,
                    "decline": pending and participant,
                    "cancel": transfer.status == "pending" and is_platform_admin(actor),
                    "execute": pending and is_platform_admin(actor) and bool(
                        transfer.previous_owner_confirmed_at and transfer.new_owner_confirmed_at)},
    }


def platform_ownership(business, actor):
    actor = User.objects.get(pk=actor.pk)
    candidates = BusinessMember.objects.filter(business=business, is_active=True, user__is_active=True,
        user__is_superuser=False).exclude(user_id=business.owner_id).exclude(
        user__role__in=["platform_admin", "platform_manager"]).select_related("user").order_by("user__email")
    return {"owner": person(business.owner), "can_prepare": is_platform_admin(actor),
            "candidates": [person(member.user) for member in candidates],
            "employee_roles": list(BusinessRole.objects.filter(business=business, is_active=True)
                .exclude(preset_key="owner").values("id", "name")),
            "transfers": [transfer_projection(row, actor) for row in transfer_rows().filter(business=business)[:20]]}


def own_transfers(actor):
    return [transfer_projection(row, actor) for row in transfer_rows().filter(
        Q(previous_owner=actor) | Q(new_owner=actor))[:20]]
