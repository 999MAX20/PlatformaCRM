"""External delivery deadlines shared by recovery and service monitoring."""
from django.conf import settings
from django.db.models import Q
from django.utils import timezone

from apps.notifications.models import Notification


def delivery_stale_cutoff(now):
    return now - timezone.timedelta(seconds=max(60, settings.NOTIFICATION_DELIVERY_STALE_LOCK_SECONDS))


def stale_delivery_condition(cutoff):
    return Q(status=Notification.Statuses.SENDING) & (
        Q(locked_at__lte=cutoff)
        | Q(locked_at__isnull=True, updated_at__lte=cutoff)
    )


def stale_external_deliveries(*, now):
    return Notification.objects.exclude(channel=Notification.Channels.SYSTEM).filter(
        stale_delivery_condition(delivery_stale_cutoff(now)),
    )


def overdue_external_deliveries(*, now):
    cutoff = delivery_stale_cutoff(now)
    return Notification.objects.exclude(channel=Notification.Channels.SYSTEM).filter(
        Q(status=Notification.Statuses.PENDING, send_at__lte=cutoff)
        | Q(status=Notification.Statuses.RETRY_SCHEDULED, next_retry_at__lte=cutoff)
        | stale_delivery_condition(cutoff),
    )
