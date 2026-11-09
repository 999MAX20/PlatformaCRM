"""Persist a fixed internal audience in the notification producer's transaction."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone


def create_recipient_states(notifications, *, using="default"):
    from apps.accounts.models import User
    from apps.businesses.models import BusinessMember
    from apps.notifications.models import Notification, NotificationRecipient

    with transaction.atomic(using=using):
        for notification in notifications:
            if notification.pk is None or notification.channel != Notification.Channels.SYSTEM:
                continue
            row = Notification.objects.using(using).select_for_update().get(pk=notification.pk)
            if row.audience_fixed_at is not None:
                continue
            members = BusinessMember.objects.using(using).filter(
                business_id=row.business_id, is_active=True, user__is_active=True,
            ).values_list("user_id", flat=True)
            users = User.objects.using(using).filter(is_active=True).filter(Q(pk__in=members) | Q(pk=row.business.owner_id))
            if row.recipient_id is not None:
                users = users.filter(pk=row.recipient_id)
            NotificationRecipient.objects.using(using).bulk_create([
                NotificationRecipient(notification_id=row.pk, user_id=user_id,
                                      received_at=row.created_at, read_at=row.read_at)
                for user_id in users.values_list("pk", flat=True)
            ], ignore_conflicts=True)
            notification.audience_fixed_at = timezone.now()
            Notification.objects.using(using).filter(pk=row.pk).update(audience_fixed_at=notification.audience_fixed_at)
