"""Durable admission counters, independent of chat memory and billing counters.

All writes lock Business then conversation, matching Inbox turn admission. Calls
are reserved before provider I/O and never refunded after an uncertain attempt.
Only hashes/codes/timestamps are stored here, never customer text or credentials.
"""
import hashlib
import unicodedata

from django.db import connection, transaction
from django.db.models import F
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.bots.models import Bot, BotConversation, BotMessage
from apps.bots.safety_policy import safety_policy
from apps.businesses.models import Business


def _locked(conversation):
    if connection.vendor == "sqlite":
        Business.objects.filter(pk=conversation.business_id).update(updated_at=F("updated_at"))
    Business.objects.select_for_update().get(pk=conversation.business_id)
    current = BotConversation.objects.select_for_update().select_related("business", "bot").get(
        pk=conversation.pk, business_id=conversation.business_id)
    if current.bot.business_id != current.business_id or current.bot.scenario != Bot.Scenarios.INBOX:
        raise PermissionDenied("Customer safety scope is invalid.")
    return current


def _save(conversation, state):
    conversation.ai_safety_state = state
    conversation.save(update_fields=["ai_safety_state", "updated_at"])


def _recent_calls(state, now):
    return [entry for entry in state.get("calls", []) if entry["at"] > now - 86400]


def normalized_message(text):
    return " ".join(unicodedata.normalize("NFKC", text).casefold().split())


@transaction.atomic
def admit_message(*, conversation, message):
    current = _locked(conversation)
    if message.conversation_id != current.pk or message.direction != BotMessage.Directions.INBOUND:
        raise PermissionDenied("The incoming message is unavailable.")
    from apps.ai_core.inbox_runtime import assert_current_inbound
    assert_current_inbound(current)
    policy = safety_policy(current.bot)
    state = dict(current.ai_safety_state or {})
    now = timezone.now().timestamp()
    recent = [item for item in state.get("messages", []) if item["at"] > now - 60]
    existing = next((item for item in recent if item["id"] == message.pk), None)
    if existing:
        return existing["decision"]
    text = normalized_message(message.text)
    digest = hashlib.sha256(text.encode()).hexdigest()
    repeats = sum(item["hash"] == digest for item in recent)
    reason = ""
    if len(message.text) > policy["max_message_chars"]:
        reason = "message_too_long"
    elif len(recent) >= policy["messages_per_minute"]:
        reason = "message_burst"
    elif len(text) >= 12 and repeats + 1 >= policy["repeat_handoff_after"]:
        reason = "repeated_messages"
    elif len(text) >= 12 and repeats:
        reason = "duplicate_text"
    state["messages"] = (recent + [{"id": message.pk, "at": now, "hash": digest, "decision": reason}])[-31:]
    _save(current, state)
    return reason


@transaction.atomic
def count_off_topic(*, conversation, message_id):
    current = _locked(conversation)
    from apps.ai_core.inbox_runtime import assert_current_inbound
    assert_current_inbound(current)
    state = dict(current.ai_safety_state or {})
    # Turn idempotency rejects earlier duplicates; this also protects direct retries.
    if state.get("last_off_topic_message", 0) < message_id:
        state["off_topic_count"] = min(3, state.get("off_topic_count", 0) + 1)
        state["last_off_topic_message"] = message_id
        _save(current, state)
    return state.get("off_topic_count", 0)


@transaction.atomic
def reserve_call(*, conversation, stage):
    current = _locked(conversation)
    from apps.ai_core.inbox_runtime import assert_current_inbound
    assert_current_inbound(current)
    state = dict(current.ai_safety_state or {})
    now = timezone.now().timestamp()
    calls = _recent_calls(state, now)
    if len(calls) >= safety_policy(current.bot)["calls_per_24h"]:
        return False
    state["calls"] = calls + [{"at": now, "stage": stage[:64]}]
    _save(current, state)
    return True


def usage(conversation):
    calls = _recent_calls(conversation.ai_safety_state or {}, timezone.now().timestamp())
    limit = safety_policy(conversation.bot)["calls_per_24h"]
    return {"calls_used": len(calls), "calls_limit": limit, "calls_remaining": max(0, limit - len(calls)),
            "next_call_available_at": timezone.datetime.fromtimestamp(calls[len(calls) - limit]["at"] + 86400, tz=timezone.get_current_timezone()).isoformat() if calls and len(calls) >= limit else None}


@transaction.atomic
def reset_behavior_for_staff(*, conversation, actor):
    from apps.businesses.access import Actions, Resources, assert_can
    current = _locked(conversation)
    assert_can(actor, current.business, Resources.CONVERSATIONS, Actions.UPDATE, obj=current)
    assert_can(actor, current.business, Resources.AI_ASSISTANT, Actions.SUGGEST, obj=current)
    if not usage(current)["calls_remaining"]:
        raise ValidationError("The conversation AI call limit is reached. Continue manually until capacity returns.")
    state = dict(current.ai_safety_state or {})
    state["off_topic_count"] = 0
    state["last_off_topic_message"] = current.messages.filter(direction="inbound").order_by("-pk").values_list("pk", flat=True).first() or 0
    state.pop("messages", None)
    state.pop("reason", None)
    _save(current, state)
    return current
