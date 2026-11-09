"""Personal state changes never confer authority over notification content."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.notifications.models import Notification, NotificationRecipient
from apps.notifications.personal_selectors import personal_states
from apps.notifications.realtime import notify_announcement_change


@transaction.atomic
def change_personal_state(*, actor, business, notification_id, action):
    if action not in {"open", "read", "unread", "acknowledge"}:
        raise ValidationError("Unknown notification action.")
    visible = personal_states(actor=actor, business=business).filter(notification_id=notification_id)
    state = NotificationRecipient.objects.select_for_update().filter(pk__in=visible.values("pk")).first()
    if state is None:
        raise NotFound()
    notification = Notification.objects.select_for_update().get(pk=state.notification_id)
    if notification.revoked_at is not None or notification.status == Notification.Statuses.CANCELLED:
        raise NotFound()
    now = timezone.now()
    fields = []
    if action == "acknowledge":
        if notification.kind != Notification.Kinds.ANNOUNCEMENT or state.opened_at is None:
            raise InvalidTransition("Open the announcement before acknowledging it.")
        if state.acknowledged_at is None:
            state.acknowledged_at = now
            fields.append("acknowledged_at")
    if action == "open" and state.opened_at is None:
        state.opened_at = now
        fields.append("opened_at")
    if action in {"open", "read", "acknowledge"} and state.read_at is None:
        state.read_at = now
        fields.append("read_at")
    if action == "unread" and state.read_at is not None:
        state.read_at = None
        fields.append("read_at")
    if fields:
        state.save(update_fields=fields)
    if "acknowledged_at" in fields:
        write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=state, business=business,
                              metadata={"kind": "notification_acknowledged", "notification_id": notification.pk})
    if fields and notification.kind == Notification.Kinds.ANNOUNCEMENT:
        notify_announcement_change(business.pk)
    state.notification = notification
    return state


@transaction.atomic
def read_personal_feed(*, actor, business):
    started_at = timezone.now()
    visible = personal_states(actor=actor, business=business, now=started_at).filter(
        received_at__lte=started_at, read_at__isnull=True,
    )
    candidates = list(visible.values_list("pk", "notification__kind"))
    ids = [pk for pk, _kind in candidates]
    updated = 0
    for offset in range(0, len(ids), 500):
        # Re-intersect the original access query and unread predicate at the write.
        updated += visible.filter(pk__in=ids[offset:offset + 500]).update(read_at=started_at)
    if updated and any(kind == Notification.Kinds.ANNOUNCEMENT for _pk, kind in candidates):
        notify_announcement_change(business.pk)
    return updated
