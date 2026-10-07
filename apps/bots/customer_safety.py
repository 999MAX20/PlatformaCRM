"""Customer handoff and conversation-boundary decisions over existing Inbox."""
from django.db import transaction
from rest_framework.exceptions import PermissionDenied

from apps.bots.models import BotConversation
from apps.bots.safety_content import obvious_risk, safety_text
from apps.bots.safety_policy import safety_policy
from apps.bots.safety_state import admit_message, count_off_topic, _locked, _save


@transaction.atomic
def safety_handoff(conversation, reason):
    from apps.ai_core.inbox_runtime import assert_current_inbound
    from apps.bots.inbox_service import handoff_conversation
    current = _locked(conversation)
    assert_current_inbound(current)
    state = dict(current.ai_safety_state or {})
    state["reason"] = reason
    _save(current, state)
    handoff_conversation(current, reason=safety_text(current, reason))
    conversation.refresh_from_db()
    return current


def before_inbound(conversation, message):
    reason = admit_message(conversation=conversation, message=message)
    if reason:
        return reason
    return obvious_risk(message.text)


def qualification_boundary(conversation, message, qualification):
    kind = qualification.request_kind
    if kind in {"security", "private_record", "uncertain"}:
        return {"security": "security_request", "private_record": "private_record_request", "uncertain": "uncertain"}[kind]
    if kind == "off_topic":
        count = count_off_topic(conversation=conversation, message_id=message.pk)
        policy = safety_policy(conversation.bot)
        if count >= policy["off_topic_handoff_after"]:
            return "off_topic"
        return "first_off_topic" if count == 1 and policy["allow_first_off_topic"] else "boundary_reply"
    return "social_reply" if kind == "social" else ""


def assert_customer_context(*, business, bot_id, conversation_id):
    conversation = BotConversation.objects.select_related("bot", "business").filter(
        pk=conversation_id, business=business, bot_id=bot_id).first()
    if conversation is None:
        raise PermissionDenied("Customer conversation is unavailable.")
    return conversation


@transaction.atomic
def set_customer_ai_state(*, conversation, actor, enabled):
    from apps.ai_core.models import AgentConversation, AgentTurn
    from apps.bots.safety_state import reset_behavior_for_staff
    from apps.businesses.access import Actions, Resources, assert_can
    from apps.core.audit import write_actor_audit_log
    from apps.core.models import AuditLog
    from apps.activities.services import create_activity_event
    from django.utils import timezone
    from rest_framework.exceptions import ValidationError
    current = _locked(conversation)
    assert_can(actor, current.business, Resources.CONVERSATIONS, Actions.UPDATE, obj=current)
    assert_can(actor, current.business, Resources.AI_ASSISTANT, Actions.SUGGEST, obj=current)
    if current.is_archived or current.status != BotConversation.Statuses.OPEN:
        raise ValidationError("Reopen this conversation before changing AI state.")
    if enabled:
        from apps.bots.lifecycle import is_bot_runtime_ready
        if not is_bot_runtime_ready(current.bot) or not current.bot.channels.filter(channel=current.channel, status="active").exists():
            raise ValidationError("The agent and channel must be ready before resuming AI.")
        if current.bot_enabled and not current.handoff_required:
            return current
        current = reset_behavior_for_staff(conversation=current, actor=actor)
    elif not current.bot_enabled:
        return current
    # A pause followed by resume must not revive old in-flight or queued answers.
    thread = AgentConversation.objects.select_for_update().filter(inbox_conversation=current).first()
    if thread:
        thread.revision += 1
        thread.save(update_fields=["revision", "updated_at"])
        thread.turns.filter(status=AgentTurn.Statuses.PREPARING).update(status=AgentTurn.Statuses.CANCELLED, completed_at=timezone.now())
    current.bot_enabled = enabled
    if enabled:
        current.handoff_required = False
        current.handoff_reason = ""
    current.save(update_fields=["bot_enabled", "handoff_required", "handoff_reason", "updated_at"])
    metadata = {"kind": "customer_ai_state", "enabled": enabled, "usage_preserved": True}
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=current, metadata=metadata)
    create_activity_event(business=current.business, actor=actor, instance=current, event_type="customer_ai_state",
                          source="inbox", metadata=metadata)
    return current
