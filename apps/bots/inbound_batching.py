"""Durable, opt-in debounce before the existing idempotent Inbox pipeline."""
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.ai_core.conversation_access import inbox_memory_conversation
from apps.ai_core.inbox_runtime import inbound_binding, run_inbound_once
from apps.bots.models import BotConversation, BotMessage, InboundMessageBatch
from apps.bots.runtime_configuration import agent_runtime_fingerprint
from apps.bots.safety_state import _locked


def _staff_message_id(conversation):
    return conversation.messages.filter(sender_type=BotMessage.SenderTypes.MANAGER).order_by("-pk").values_list("pk", flat=True).first() or 0


@transaction.atomic
def queue_inbound(*, conversation, message, channel=None):
    from apps.bots.customer_safety import before_inbound
    from apps.conversations.auto_pipeline import AutoPipelineDecision, _guard_conversation_state, resolve_auto_pipeline_config

    if message.conversation_id != conversation.pk or message.direction != BotMessage.Directions.INBOUND:
        raise PermissionDenied("The inbound message does not belong to this conversation.")
    # Existing agents retain immediate processing without allocating a batch/thread.
    conversation.refresh_from_db()
    conversation.bot.refresh_from_db()
    seconds = (conversation.bot.settings_json or {}).get("inbound_wait_seconds", 0)
    if type(seconds) is not int or seconds not in (2, 3, 5):
        return None
    conversation = _locked(conversation)
    latest = conversation.messages.filter(direction="inbound").order_by("-created_at", "-pk").first()
    if latest.pk != message.pk:
        return AutoPipelineDecision(status="skipped_superseded", reason="A newer customer message is available.")
    config = resolve_auto_pipeline_config(conversation=conversation, channel=channel)
    if not config.enabled or config.mode == "off" or _guard_conversation_state(conversation):
        InboundMessageBatch.objects.filter(conversation=conversation).update(pending=False)
        return None
    thread = inbox_memory_conversation(conversation)
    if thread.turns.filter(idempotency_key=f"message:{message.pk}").exists():
        return None
    batch = InboundMessageBatch.objects.filter(conversation=conversation).first()
    if batch and batch.last_message_id == message.pk:
        return AutoPipelineDecision(status="queued_batch" if batch.pending else "skipped_batch", reason="This message was already accepted.")
    # Admission is idempotent and counts every raw message, including bursts.
    if before_inbound(conversation, message):
        InboundMessageBatch.objects.filter(conversation=conversation).update(pending=False)
        return None
    now = timezone.now()
    fingerprint = agent_runtime_fingerprint(conversation)
    staff_id = _staff_message_id(conversation)
    reusable = bool(batch and batch.pending and batch.runtime_fingerprint == fingerprint
                    and batch.memory_epoch == thread.memory_epoch and batch.revision == thread.revision
                    and batch.staff_message_id == staff_id)
    started = batch.started_at if reusable else now
    InboundMessageBatch.objects.update_or_create(conversation=conversation, defaults={
        "first_message_id": batch.first_message_id if reusable else message.pk,
        "last_message_id": message.pk, "started_at": started,
        "due_at": min(now + timedelta(seconds=seconds), started + timedelta(seconds=15)),
        "pending": True, "runtime_fingerprint": fingerprint,
        "memory_epoch": thread.memory_epoch, "revision": thread.revision, "staff_message_id": staff_id,
    })
    return AutoPipelineDecision(status="queued_batch", reason="Waiting for consecutive customer messages.")


def process_batch(conversation_id):
    from apps.conversations.auto_pipeline import AutoPipelineDecision, _run_auto_pipeline

    with transaction.atomic():
        conversation = BotConversation.objects.select_related("business", "bot").filter(pk=conversation_id).first()
        if conversation is None:
            return None
        conversation = _locked(conversation)
        batch = InboundMessageBatch.objects.filter(conversation=conversation, pending=True, due_at__lte=timezone.now()).first()
        if batch is None:
            return None
        message = conversation.messages.get(pk=batch.last_message_id, direction="inbound")
        message_ids = list(conversation.messages.filter(direction="inbound", pk__gte=batch.first_message_id,
                                                       pk__lte=batch.last_message_id).order_by("created_at", "pk").values_list("pk", flat=True))

    def run(**kwargs):
        current = kwargs["conversation"]
        binding = inbound_binding()
        if (agent_runtime_fingerprint(current) != batch.runtime_fingerprint
                or binding["epoch"] != batch.memory_epoch or binding["revision"] != batch.revision + 1
                or _staff_message_id(current) != batch.staff_message_id):
            return AutoPipelineDecision(status="skipped_configuration_changed", reason="Waiting batch was cancelled by a state change.")
        return _run_auto_pipeline(**kwargs)

    def admitted():
        InboundMessageBatch.objects.filter(pk=batch.pk, last_message_id=message.pk).update(pending=False)

    result = run_inbound_once(conversation=conversation, message=message, channel=None, run=run,
                              batch_message_ids=message_ids, batch_staff_message_id=batch.staff_message_id, on_admitted=admitted)
    # Replayed or superseded turns also retire their old queue entry, never a newer group.
    admitted()
    return result


def process_due_batches(limit=20):
    ids = list(InboundMessageBatch.objects.filter(pending=True, due_at__lte=timezone.now())
               .order_by("due_at").values_list("conversation_id", flat=True)[:limit])
    return [process_batch(conversation_id) for conversation_id in ids]
