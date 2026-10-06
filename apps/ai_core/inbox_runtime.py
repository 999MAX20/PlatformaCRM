"""One durable attempt per inbound message, with late-result suppression."""
from contextvars import ContextVar
import hashlib

from django.db import transaction
from django.db.models import Max
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.ai_core.conversation_access import inbox_memory_conversation, memory_access_fingerprint
from apps.ai_core.models import AgentConversation, AgentTurn
from apps.bots.models import BotConversation, BotMessage
from apps.businesses.models import Business


_attempt = ContextVar("inbox_agent_attempt", default=None)


@transaction.atomic
def reset_inbox_memory(*, conversation, actor):
    from apps.businesses.access import Actions, Resources, assert_can
    from apps.core.audit import write_actor_audit_log
    from apps.core.models import AuditLog
    Business.objects.select_for_update().get(pk=conversation.business_id)
    conversation = BotConversation.objects.select_for_update().select_related("business", "bot").get(pk=conversation.pk)
    assert_can(actor, conversation.business, Resources.CONVERSATIONS, Actions.UPDATE, obj=conversation)
    assert_can(actor, conversation.business, Resources.AI_ASSISTANT, Actions.SUGGEST, obj=conversation)
    thread = inbox_memory_conversation(conversation)
    thread.memory_epoch += 1
    thread.memory_since = timezone.now()
    thread.memory_json = {}
    thread.save(update_fields=["memory_epoch", "memory_since", "memory_json", "updated_at"])
    thread.turns.filter(status=AgentTurn.Statuses.PREPARING).update(status=AgentTurn.Statuses.CANCELLED, completed_at=timezone.now())
    metadata = dict(conversation.metadata_json or {})
    booking = dict(metadata.get("auto_booking") or {})
    for key in ("offered_slots", "offered_at", "offer_message_id", "runtime_fingerprint"):
        booking.pop(key, None)
    if booking:
        metadata["auto_booking"] = booking
    else:
        metadata.pop("auto_booking", None)
    conversation.metadata_json = metadata
    conversation.save(update_fields=["metadata_json", "updated_at"])
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=conversation,
                         metadata={"kind": "ai_memory_reset", "history_preserved": True})
    return conversation


def inbound_binding():
    return _attempt.get()


def is_current_inbound(conversation):
    binding = inbound_binding()
    if binding is None:
        return True
    if binding["conversation_id"] != conversation.pk:
        return False
    latest = conversation.messages.filter(direction=BotMessage.Directions.INBOUND).order_by("-created_at", "-pk").values_list("pk", flat=True).first()
    return latest == binding["message_id"] and AgentTurn.objects.filter(
        pk=binding["turn_id"], status=AgentTurn.Statuses.PREPARING,
        conversation__memory_epoch=binding["epoch"], conversation__revision=binding["revision"]).exists()


def assert_current_inbound(conversation):
    if not is_current_inbound(conversation):
        raise PermissionDenied("A newer customer message replaced this request.")


def run_inbound_once(*, conversation, message, channel, run):
    from apps.conversations.auto_pipeline import AutoPipelineDecision
    if message.conversation_id != conversation.pk or message.direction != BotMessage.Directions.INBOUND:
        raise PermissionDenied("The inbound message does not belong to this conversation.")
    with transaction.atomic():
        Business.objects.select_for_update().get(pk=conversation.business_id)
        conversation = BotConversation.objects.select_for_update().select_related("business", "bot").get(pk=conversation.pk)
        thread = inbox_memory_conversation(conversation)
        thread = AgentConversation.objects.select_for_update().get(pk=thread.pk)
        existing = thread.turns.filter(idempotency_key=f"message:{message.pk}").first()
        if existing:
            return _replay(existing, conversation)
        latest = conversation.messages.filter(direction=BotMessage.Directions.INBOUND).order_by("-created_at", "-pk").values_list("pk", flat=True).first()
        if latest != message.pk:
            return AutoPipelineDecision(status="skipped_superseded", reason="A newer customer message is available.")
        thread.turns.filter(status=AgentTurn.Statuses.PREPARING).update(status=AgentTurn.Statuses.SUPERSEDED, completed_at=timezone.now())
        thread.revision += 1
        thread.save(update_fields=["revision", "updated_at"])
        turn = AgentTurn.objects.create(conversation=thread, sequence=(thread.turns.aggregate(value=Max("sequence"))["value"] or 0) + 1,
            idempotency_key=f"message:{message.pk}", request_hash=hashlib.sha256(message.text.encode()).hexdigest(),
            message="", mode="inbox", memory_epoch=thread.memory_epoch,
            access_fingerprint=memory_access_fingerprint(business=conversation.business, agent=conversation.bot),
            context_json={"inbound_message_id": message.pk})
    token = _attempt.set({"conversation_id": conversation.pk, "message_id": message.pk, "turn_id": turn.pk,
                          "epoch": thread.memory_epoch, "revision": thread.revision})
    try:
        decision = run(conversation=conversation, message=message, channel=channel)
        payload = {"status": decision.status, "reason": decision.reason, "ai_log_id": decision.ai_log_id,
                   "confirmation_policy": decision.confirmation_policy,
                   "qualification": decision.qualification.to_dict() if decision.qualification else None,
                   "reply_message_id": decision.reply_message.pk if decision.reply_message else None,
                   "reply_error": decision.reply_error}
        if decision.booking:
            payload["booking"] = {"status": decision.booking.status, "reason": decision.booking.reason,
                "appointment_id": decision.booking.appointment.pk if decision.booking.appointment else None,
                "confirmation_message_id": decision.booking.confirmation_message.pk if decision.booking.confirmation_message else None}
        if decision.result:
            payload["result"] = {key: getattr(decision.result, key).pk if getattr(decision.result, key) else None
                                 for key in ("client", "lead", "deal", "task")}
            payload["result"]["created"] = decision.result.created
        AgentTurn.objects.filter(pk=turn.pk, status=AgentTurn.Statuses.PREPARING).update(
            status=AgentTurn.Statuses.COMPLETED, plan_json=payload, completed_at=timezone.now())
        return decision
    except Exception:
        AgentTurn.objects.filter(pk=turn.pk, status=AgentTurn.Statuses.PREPARING).update(
            status=AgentTurn.Statuses.FAILED, error_code="inbox_interrupted", completed_at=timezone.now())
        raise
    finally:
        _attempt.reset(token)


def _replay(turn, conversation):
    from apps.conversations.auto_pipeline import AutoPipelineDecision
    from apps.conversations.ai_qualification import qualification_from_payload
    from apps.conversations.booking import BookingResult
    from apps.conversations.pipeline import ConversationPipelineResult
    from apps.clients.models import Client
    from apps.leads.models import Lead
    from apps.crm.models import Deal
    from apps.tasks.models import Task
    from apps.scheduling.models import Appointment
    if turn.status != AgentTurn.Statuses.COMPLETED:
        return AutoPipelineDecision(status=f"skipped_{turn.status}", reason="This inbound request was already accepted; no automatic replay.")
    payload = turn.plan_json
    decision = AutoPipelineDecision(status=payload["status"], reason=payload["reason"],
        ai_log_id=payload.get("ai_log_id"), confirmation_policy=payload.get("confirmation_policy"),
        qualification=qualification_from_payload(payload["qualification"]) if payload.get("qualification") else None,
        reply_message=conversation.messages.filter(pk=payload.get("reply_message_id")).first(), reply_error=payload.get("reply_error", ""))
    if payload.get("result"):
        data = payload["result"]
        records = {key: model.objects.filter(business_id=conversation.business_id, pk=data.get(key)).first()
                   for key, model in (("client", Client), ("lead", Lead), ("deal", Deal), ("task", Task))}
        decision.result = ConversationPipelineResult(conversation=conversation, **records,
            created={key: False for key in data["created"]}, qualification=decision.qualification)
    if payload.get("booking"):
        data = payload["booking"]
        decision.booking = BookingResult(status=data["status"], reason=data["reason"],
            appointment=Appointment.objects.filter(business_id=conversation.business_id, pk=data.get("appointment_id")).first(),
            confirmation_message=conversation.messages.filter(pk=data.get("confirmation_message_id")).first())
    return decision
