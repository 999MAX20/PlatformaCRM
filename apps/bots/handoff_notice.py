"""Fixed customer acknowledgement; independent of model availability and content."""
from django.db import transaction

from apps.bots.models import BotMessage


NOTICE_SOURCE = "customer_handoff_notice_inbound_id"


@transaction.atomic
def send_customer_handoff_notice(*, conversation, message, fingerprint, idempotency_key):
    from apps.ai_core.inbox_runtime import is_current_inbound
    from apps.bots.inbox_service import send_outbound_message
    from apps.bots.runtime_configuration import agent_runtime_fingerprint
    from apps.bots.safety_content import safety_text
    from apps.bots.safety_state import _locked
    from apps.conversations.auto_pipeline import resolve_auto_pipeline_config

    current = _locked(conversation)
    channel = current.bot.channels.filter(channel=current.channel).first()
    config = resolve_auto_pipeline_config(conversation=current, channel=channel)
    if not (is_current_inbound(current) and _eligible(current) and config.enabled
            and config.mode != "off" and config.auto_send_reply
            and fingerprint == agent_runtime_fingerprint(current)):
        return None
    current.metadata_json = {**(current.metadata_json or {}), NOTICE_SOURCE: message.pk}
    current.save(update_fields=["metadata_json", "updated_at"])
    return send_outbound_message(current, safety_text(current, "handoff"), user=None,
        sender_type=BotMessage.SenderTypes.SYSTEM, idempotency_key=idempotency_key,
        runtime_fingerprint=fingerprint, handoff_notice=True)


def _eligible(conversation):
    from apps.bots.lifecycle import is_bot_runtime_ready
    return (conversation.handoff_required and not conversation.bot_enabled
            and conversation.status == "open" and not conversation.is_archived
            and conversation.business_id == conversation.bot.business_id
            and conversation.bot.scenario == "inbox" and is_bot_runtime_ready(conversation.bot)
            and conversation.bot.channels.filter(channel=conversation.channel, status="active").exists())


def notice_is_current(message):
    from apps.ai_core.models import AgentConversation
    from apps.bots.runtime_configuration import agent_runtime_fingerprint

    conversation = message.conversation
    payload = message.payload_json or {}
    return (_eligible(conversation)
            and payload["customer_handoff_notice"] == (conversation.metadata_json or {}).get(NOTICE_SOURCE)
            and payload.get("agent_runtime_fingerprint") == agent_runtime_fingerprint(conversation)
            and AgentConversation.objects.filter(inbox_conversation=conversation,
                memory_epoch=payload.get("customer_handoff_epoch")).exists()
            and not conversation.messages.filter(direction="outbound", sender_type="manager",
                created_at__gte=message.created_at).exists())
