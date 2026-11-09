import re

from apps.core.models import ServiceComponentState
from apps.notifications.models import Notification


def service_message_key(notification, context):
    """Project a server-owned service reference without replaying stored text."""
    if (notification.kind != Notification.Kinds.WORK
            or notification.category != Notification.Categories.SYSTEM
            or notification.channel != Notification.Channels.SYSTEM
            or notification.author_id or notification.client_id or notification.appointment_id
            or notification.action_url):
        return None
    match = re.fullmatch(r"service-status:([1-9][0-9]*):([1-9][0-9]*):(started|recovered)",
                         notification.provider_reference or "")
    if not match:
        return None
    state_id, episode, transition = match.groups()
    cache = context.setdefault("service_message_states", {})
    if notification.business_id not in cache:
        cache[notification.business_id] = {
            str(pk): (component, current_episode)
            for pk, component, current_episode in ServiceComponentState.objects.filter(
                business_id=notification.business_id,
            ).values_list("pk", "component", "episode")
        }
    state = cache[notification.business_id].get(state_id)
    if not state or state[0] not in ServiceComponentState.Components.values or int(episode) > state[1]:
        return None
    return f"notification.service.{state[0]}.{transition}"
