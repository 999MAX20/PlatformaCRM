"""One-hour recovery for answered, ordinary staff handoffs only."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from apps.bots.models import BotConversation, BotMessage
from apps.bots.safety_state import _locked


IDLE_PERIOD = timedelta(hours=1)
RECOVERY_FIELDS = ["handoff_resume_started_at", "ai_resume_at", "ai_resume_actor"]


def cancel_recovery(current):
    current.handoff_resume_started_at = None
    current.ai_resume_at = None
    current.ai_resume_actor = None


def _answered_at(current, *, message_id=None):
    """Failed/queued messages and system notices cannot resolve human attention."""
    if not current.handoff_resume_started_at:
        return None
    last = current.messages.filter(sender_type__in=["client", "manager"]).order_by("-created_at", "-pk").first()
    if (not last or (message_id is not None and last.pk != message_id)
            or last.sender_type != "manager" or last.direction != "outbound"
            or last.status != "sent" or last.created_at < current.handoff_resume_started_at):
        return None
    return max(last.created_at, last.sent_at or last.created_at)


@transaction.atomic
def schedule_after_staff_delivery(message):
    if message.sender_type != BotMessage.SenderTypes.MANAGER or message.status != BotMessage.Statuses.SENT:
        return
    from django.contrib.auth import get_user_model
    from apps.businesses.access import Actions, Resources, can
    current = _locked(message.conversation)
    if not current.handoff_required or current.bot_enabled or current.is_archived or current.status != "open":
        return
    answered_at = _answered_at(current, message_id=message.pk)
    if not answered_at:
        return
    actor = get_user_model().objects.filter(pk=(message.payload_json or {}).get("sent_by_user_id"), is_active=True).first()
    if actor is None or not all(can(actor, current.business, resource, action, obj=current).allowed for resource, action in (
        (Resources.CONVERSATIONS, Actions.UPDATE), (Resources.AI_ASSISTANT, Actions.SUGGEST))):
        return
    current.ai_resume_at = answered_at + IDLE_PERIOD
    current.ai_resume_actor = actor
    current.save(update_fields=["ai_resume_at", "ai_resume_actor", "updated_at"])


@transaction.atomic
def resume_due_conversation(conversation, *, now=None):
    from apps.bots.customer_safety import set_customer_ai_state
    from rest_framework.exceptions import PermissionDenied, ValidationError
    current = _locked(conversation)
    now = now or timezone.now()
    if not current.ai_resume_at or current.ai_resume_at > now:
        return False
    answered_at = _answered_at(current)
    if (not current.handoff_required or current.bot_enabled or current.is_archived or current.status != "open"
            or (current.ai_safety_state or {}).get("reason") or not current.ai_resume_actor_id
            or not current.ai_resume_actor.is_active):
        cancel_recovery(current)
        current.save(update_fields=[*RECOVERY_FIELDS, "updated_at"])
        return False
    if not answered_at or answered_at + IDLE_PERIOD > now:
        current.ai_resume_at = None
        current.save(update_fields=["ai_resume_at", "updated_at"])
        return False
    try:
        # A savepoint preserves all-or-nothing state/audit if an existing guard denies.
        with transaction.atomic():
            set_customer_ai_state(conversation=current, actor=current.ai_resume_actor, enabled=True,
                                  automatic_recovery=True)
    except (PermissionDenied, ValidationError):
        # No busy retry or surprise resume after readiness/permission later changes.
        cancel_recovery(current)
        current.save(update_fields=[*RECOVERY_FIELDS, "updated_at"])
        return False
    return True


def resume_due_conversations(*, limit=100, now=None):
    now = now or timezone.now()
    candidates = BotConversation.objects.filter(ai_resume_at__lte=now).order_by("ai_resume_at", "pk")[:max(1, min(limit, 1000))]
    return sum(resume_due_conversation(item, now=now) for item in candidates)
