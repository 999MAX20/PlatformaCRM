from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import AccountRecovery, EmailChangeChallenge, User
from apps.accounts.mfa import has_confirmed_mfa
from apps.accounts.recovery import linked_businesses, revision
from apps.businesses.models import BusinessMember


def projection(item, *, platform=False):
    expired = item.status in {"pending", "sent"} and item.expires_at <= timezone.now()
    data = {"id": str(item.pk), "business_id": item.business_id, "business_name": item.business.name,
            "user_id": item.user_id, "user_name": item.user.full_name or item.user.email,
            "new_email": item.new_email, "status": "expired" if expired else item.status,
            "owner_required": item.owner_required, "owner_confirmed_at": item.owner_confirmed_at,
            "expires_at": item.expires_at, "completed_at": item.completed_at,
            "delivery_status": item.delivery_status, "last_attempt_at": item.last_attempt_at,
            "support_case_id": item.support_case_id}
    if platform:
        data.update(reason=item.reason, verified_reference=item.verified_reference,
                    identity_required=item.identity_required, prepared_by_id=item.prepared_by_id,
                    executed_by_id=item.executed_by_id)
    return data


def platform_snapshot(business):
    ids = BusinessMember.objects.filter(business=business, is_active=True).values("user_id")
    users = User.objects.filter(Q(pk=business.owner_id) | Q(pk__in=ids)).filter(is_active=True).order_by("pk")
    candidates = []
    for user in users:
        if user.is_platform_user:
            continue
        pending = EmailChangeChallenge.objects.filter(user=user).first()
        state = "none" if pending is None else "expired" if pending.expires_at <= timezone.now() else "invalidated" if pending.auth_epoch != user.auth_epoch or pending.failed_attempts >= 5 else "pending"
        candidates.append({"id": user.pk, "name": user.full_name or user.email, "email": user.email,
            "revision": revision(user), "owner_required": user.pk != business.owner_id,
            "identity_required": user.pk == business.owner_id or linked_businesses(user).count() > 1,
            "mfa_enabled": has_confirmed_mfa(user), "email_change_status": state,
            "email_change_expires_at": pending.expires_at if pending else None})
    rows = AccountRecovery.objects.filter(business=business).select_related("user", "business").order_by("-created_at")[:50]
    return {"candidates": candidates, "requests": [projection(row, platform=True) for row in rows]}
