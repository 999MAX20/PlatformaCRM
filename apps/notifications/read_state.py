"""Notification read-state changes using the existing per-object authority."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.access import Actions, Resources, can
from apps.businesses.capabilities import resource_is_enabled
from apps.core.permissions import accessible_businesses
from apps.notifications.models import Notification


@transaction.atomic
def mark_allowed_notifications_read(*, actor, queryset):
    resource = Resources.NOTIFICATIONS
    businesses = [
        business for business in accessible_businesses(actor)
        if resource_is_enabled(business, resource)
        and can(actor, business, resource, Actions.VIEW).allowed
        and can(actor, business, resource, Actions.UPDATE).allowed
    ]
    # Admission must not depend on whether the current filter has unread rows.
    if not businesses:
        raise PermissionDenied("You do not have permission to update notifications.")

    visible = queryset.filter(business__in=businesses, read_at__isnull=True)
    # The VIEW query may contain DISTINCT/joins. Lock plain Notification rows so
    # recipient/read-state changes cannot race the object decision on PostgreSQL.
    candidates = Notification.objects.filter(
        pk__in=visible.order_by().values("pk"), read_at__isnull=True,
    ).select_related("business").select_for_update(of=("self",)).order_by("pk")
    allowed_ids = [
        notification.pk for notification in candidates.iterator(chunk_size=500)
        if can(actor, notification.business, resource, Actions.VIEW, obj=notification).allowed
        and can(actor, notification.business, resource, Actions.UPDATE, obj=notification).allowed
    ]
    # Canonical object checks intentionally retain UPDATE on unowned/shared rows,
    # including TEAM scope, which the generic scope_queryset filter omits.
    now = timezone.now()
    updated = 0
    for start in range(0, len(allowed_ids), 500):
        updated += visible.filter(pk__in=allowed_ids[start:start + 500]).update(
            read_at=now, updated_at=now,
        )
    return updated
