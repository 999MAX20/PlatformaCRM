"""Owner/admin announcements, with fixed audience and immutable publication."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from uuid import UUID

from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import IdempotencyConflict
from apps.core.models import AuditLog
from apps.notifications.models import Notification
from apps.notifications.personal_selectors import can_manage_announcements, personal_business
from apps.notifications.realtime import notify_announcement_change


def assert_announcement_manager(*, actor, business):
    personal_business(actor=actor, business_id=business.pk)
    if not can_manage_announcements(actor=actor, business=business):
        raise PermissionDenied("Only the business owner or administrator can manage announcements.")


@transaction.atomic
def publish_announcement(*, actor, business, text, priority, publication_key):
    # Serialize publication retries per Business; no duplicate content/audit/audience.
    business = Business.objects.select_for_update().get(pk=business.pk)
    assert_announcement_manager(actor=actor, business=business)
    if not isinstance(text, str) or not text.strip() or len(text) > 4000:
        raise ValidationError({"text": "Enter announcement text of at most 4000 characters."})
    if priority not in Notification.Priorities.values:
        raise ValidationError({"priority": "Invalid priority."})
    try:
        publication_key = UUID(str(publication_key))
    except (ValueError, TypeError, AttributeError):
        raise ValidationError({"publication_key": "A publication key is required."})
    existing = Notification.objects.filter(business=business, publication_key=publication_key).first()
    if existing is not None:
        if existing.author_id != actor.pk or existing.text != text or existing.priority != priority:
            raise IdempotencyConflict("The publication key was already used for another announcement.")
        return existing, False
    now = timezone.now()
    notification = Notification.objects.create(
        business=business, kind=Notification.Kinds.ANNOUNCEMENT, author=actor,
        publication_key=publication_key, text=text, priority=priority, category=Notification.Categories.SYSTEM,
        channel=Notification.Channels.SYSTEM, send_at=now, status=Notification.Statuses.SENT, delivered_at=now,
    )
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.CREATE, instance=notification,
                         metadata={"kind": "announcement_published", "recipient_count": notification.recipient_states.count()})
    notify_announcement_change(business.pk)
    return notification, True


@transaction.atomic
def revoke_announcement(*, actor, business, notification_id):
    assert_announcement_manager(actor=actor, business=business)
    notification = Notification.objects.select_for_update().filter(
        pk=notification_id, business=business, kind=Notification.Kinds.ANNOUNCEMENT,
    ).first()
    if notification is None:
        raise NotFound()
    if notification.revoked_at is None:
        notification.revoked_at = timezone.now()
        notification.save(update_fields=["revoked_at", "updated_at"])
        write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=notification,
                             metadata={"kind": "announcement_revoked"})
        notify_announcement_change(business.pk)
    return notification
