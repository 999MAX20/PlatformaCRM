"""Best-effort invalidation only: the database/API remain the source of truth."""
import logging
from functools import partial

from django.conf import settings
from django.db import transaction
from redis import Redis, RedisError

logger = logging.getLogger(__name__)


def announcement_channel(business_id):
    return f"{settings.NOTIFICATION_EVENTS_NAMESPACE}:announcements:{int(business_id)}"


def _publish(business_id):
    try:
        with Redis.from_url(settings.NOTIFICATION_EVENTS_REDIS_URL,
                            socket_connect_timeout=0.5, socket_timeout=0.5) as client:
            client.publish(announcement_channel(business_id), "changed")
    except (RedisError, OSError):
        # Never log a connection URL, credentials or receipt contents. A broker
        # outage must not turn a committed receipt into a failed user command.
        logger.warning("announcement_invalidation_unavailable", extra={"business_id": business_id})


def notify_announcement_change(business_id):
    if settings.NOTIFICATION_EVENTS_ENABLED:
        transaction.on_commit(partial(_publish, int(business_id)))
