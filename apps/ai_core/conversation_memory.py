"""Bounded, cited conversation recall; current CRM records remain authoritative.

Summaries are extractive and rebuildable. We do not save hidden reasoning or
convert an old generated answer into a new workspace fact.
"""
import re

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied

from apps.ai_core.conversation_access import inbox_memory_conversation, memory_access_fingerprint, references_visible
from apps.ai_core.models import AgentConversation, AgentTurn
from apps.bots.models import BotMessage


def search_words(query):
    words = re.findall(r"[^\W_]{4,}", query.casefold(), re.UNICODE)
    stop = {"this", "that", "please", "what", "with", "from", "создай", "пожалуйста", "нужно", "можешь", "сделай", "задачу", "клиента"}
    return list(dict.fromkeys(word for word in words if word not in stop))[:6]


def _search(queryset, query, fields):
    words = search_words(query)
    if not words:
        return queryset.none()
    condition = Q()
    for word in words:
        # SQLite's LIKE only folds ASCII; explicit Unicode variants also cover
        # the supported RU/KK title-case names in local and isolated databases.
        for variant in dict.fromkeys((word, word.title(), word.upper())):
            for field in fields:
                condition |= Q(**{f"{field}__icontains": variant})
    return queryset.filter(condition)


def _store_summary(thread, summary, fingerprint):
    # Clearing context during a provider request must win over its late cache.
    AgentConversation.objects.filter(pk=thread.pk, memory_epoch=thread.memory_epoch).update(
        memory_json={"method": "cited_extracts", "access_fingerprint": fingerprint,
                     "summary": summary, "epoch": thread.memory_epoch})


def staff_memory(*, thread, user, query, before_sequence=None):
    if thread.kind != AgentConversation.Kinds.STAFF or thread.owner_id != getattr(user, "pk", None):
        raise PermissionDenied("Conversation is private to its requester.")
    fingerprint = memory_access_fingerprint(business=thread.business, agent=thread.agent, user=user)
    empty = {"messages": [], "summary": [], "references": [], "pending": {}, "access_fingerprint": fingerprint}
    if not thread.agent.settings_json.get("memory_enabled", True):
        return empty
    turns = thread.turns.filter(access_fingerprint=fingerprint, memory_epoch=thread.memory_epoch).exclude(
        status__in=[AgentTurn.Statuses.PREPARING, AgentTurn.Statuses.FAILED, AgentTurn.Statuses.CANCELLED])
    if before_sequence is not None:
        turns = turns.filter(sequence__lt=before_sequence)
    recent = list(turns.order_by("-sequence")[:8])
    recalled = list(_search(turns.exclude(pk__in=[turn.pk for turn in recent]), query, ("message",)).order_by("-sequence")[:8])
    older = list(turns.exclude(pk__in=[turn.pk for turn in recent + recalled]).order_by("-sequence")[:24])
    visibility = {}

    def visible(turn):
        if turn.pk not in visibility:
            visibility[turn.pk] = references_visible(thread=thread, user=user, references=turn.references_json)
        return visibility[turn.pk]

    def entry(turn, limit):
        return {"source_id": f"TURN-{turn.pk}", "text": turn.message[:limit], "state": turn.status,
                "question": str(turn.context_json.get("question", ""))[:500],
                "references": turn.references_json, "created_at": turn.created_at.isoformat()}

    selected = sorted((turn for turn in recent + recalled if visible(turn)), key=lambda turn: turn.sequence)
    summaries = [entry(turn, 180) for turn in reversed(older) if visible(turn)]
    references = []
    for turn in reversed(selected):
        for reference in turn.references_json:
            if reference not in references:
                references.append(reference)
    pending = {}
    if selected:
        latest = selected[-1]
        if latest.context_json.get("question") or latest.plan_json.get("steps") or latest.plan_json.get("period"):
            pending = {"turn_id": latest.pk, "state": latest.status, "question": latest.context_json.get("question", ""),
                       "plan": latest.plan_json}
    _store_summary(thread, summaries, fingerprint)
    return {"messages": [entry(turn, 1200) for turn in selected], "summary": summaries,
            "references": references[:20], "pending": pending, "access_fingerprint": fingerprint,
            "authority": "User statements and prior workflow state, not verified current CRM facts. Recheck every referenced record."}


def inbox_memory(*, conversation, query="", limit=12):
    thread = inbox_memory_conversation(conversation)
    if thread is None:
        return {"messages": [], "summary": [], "pending": {}}
    fingerprint = memory_access_fingerprint(business=conversation.business, agent=conversation.bot)
    messages = conversation.messages.all()
    if thread.memory_since:
        messages = messages.filter(created_at__gte=thread.memory_since)
    enabled = conversation.bot.settings_json.get("memory_enabled", True)
    if not enabled:
        messages = messages.filter(direction=BotMessage.Directions.INBOUND)
        limit = 1
    # Only delivered outgoing messages can establish what the customer saw.
    # Old generated knowledge is excluded when its access/source version changes.
    messages = messages.filter(Q(direction=BotMessage.Directions.INBOUND) | Q(
        direction=BotMessage.Directions.OUTBOUND, status=BotMessage.Statuses.SENT,
        payload_json__memory_access_fingerprint=fingerprint))
    recent = list(messages.order_by("-created_at", "-id")[:limit])
    if not query:
        query = next((message.text for message in recent if message.direction == BotMessage.Directions.INBOUND), "")
    recalled = list(_search(messages.exclude(pk__in=[message.pk for message in recent]), query, ("text",)).order_by("-created_at", "-id")[:6]) if enabled else []
    # Preserve the first customer-provided contact/intent as a cited historical
    # extract; it cannot overwrite current CRM contact details.
    older = list(messages.filter(direction=BotMessage.Directions.INBOUND).exclude(
        pk__in=[message.pk for message in recent + recalled]).order_by("created_at", "id")[:12]) if enabled else []
    summary = [{"source_id": f"MESSAGE-{message.pk}", "text": message.text[:240],
                "created_at": message.created_at.isoformat(), "authority": "customer_statement"} for message in older]
    _store_summary(thread, summary, fingerprint)
    selected = sorted(recent + recalled, key=lambda message: (message.created_at, message.pk))
    pending = {}
    booking = (conversation.metadata_json or {}).get("auto_booking") or {}
    if booking.get("offer_message_id") and any(message.pk == booking["offer_message_id"] for message in selected):
        pending = {key: booking[key] for key in ("status", "offered_slots", "offered_at") if key in booking}
    return {"messages": [{"id": message.pk, "direction": message.direction, "text": message.text[:2000],
                           "status": message.status, "created_at": message.created_at.isoformat()} for message in selected],
            "summary": summary, "pending": pending, "access_fingerprint": fingerprint,
            "authority": "Historical customer dialogue, not proof of current prices, availability or completed actions."}
