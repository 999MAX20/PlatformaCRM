from datetime import datetime

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.automations.engine import run_automations_for_event
from apps.automations.models import AutomationRule
from apps.billing.models import UsageCounter
from apps.billing.usage import increment_usage
from apps.bots.models import BotChannel, BotConversation, BotMessage
from apps.conversations.auto_pipeline import maybe_run_auto_pipeline
from apps.integrations.crm_mapping import record_message_received_event
from apps.integrations.message_idempotency import create_inbound_message_once, find_existing_inbound_message
from apps.integrations.models import IntegrationEventLog
from apps.integrations.sanitization import sanitize_config
from apps.integrations.whatsapp_credentials import (
    get_whatsapp_access_token,
    get_whatsapp_connector,
    has_whatsapp_access_token,
    store_whatsapp_access_token,
)
from apps.integrations.whatsapp_routing import verified_whatsapp_routes
from apps.notifications.delivery import handle_appointment_followup_reply
from apps.outreach.consent import record_inbound_consent


def verify_whatsapp_secret(request):
    from apps.integrations.providers.whatsapp import WhatsAppProvider

    return WhatsAppProvider().verify_webhook(request)


def parse_inbound_message(payload, headers=None):
    from apps.integrations.providers.whatsapp import WhatsAppProvider

    parsed = WhatsAppProvider().parse_webhook(payload, headers=headers or {})
    if not parsed.get("sender_id"):
        raise ValidationError("WhatsApp sender id is missing.")
    if not parsed.get("text"):
        raise ValidationError("WhatsApp message text is missing.")
    return parsed


def process_whatsapp_statuses(payload, auth_context=None):
    routes = verified_whatsapp_routes(payload, auth_context)
    batches = [(channel, value.get("statuses") or [], portion) for channel, value, portion in routes if value.get("statuses")]
    if not batches:
        return None
    processed = 0
    for channel, statuses, portion in batches:
        processed += _process_whatsapp_status_batch(channel, statuses, portion)
    return {"processed": processed, "statuses": sum(len(statuses) for _, statuses, _ in batches)}


def _process_whatsapp_status_batch(channel, statuses, payload):
    business = channel.bot.business
    safe_payload = sanitize_config(payload)
    processed = 0
    for item in statuses:
        message_id = str(item.get("id") or "")
        status = str(item.get("status") or "")
        if not message_id:
            continue
        message = BotMessage.objects.filter(
            conversation__business=business,
            conversation__bot=channel.bot,
            conversation__channel=BotConversation.Channels.WHATSAPP,
            direction=BotMessage.Directions.OUTBOUND,
            external_message_id=message_id,
        ).first()
        if not message:
            continue
        timestamp = _whatsapp_timestamp(item.get("timestamp"))
        update_fields = ["payload_json"]
        payload_json = dict(message.payload_json or {})
        payload_json["whatsapp_status"] = sanitize_config(item)
        message.payload_json = payload_json
        if status == "sent":
            message.status = BotMessage.Statuses.SENT
            message.sent_at = message.sent_at or timestamp
            update_fields.extend(["status", "sent_at"])
        elif status == "delivered":
            message.status = BotMessage.Statuses.SENT
            message.delivered_at = message.delivered_at or timestamp
            update_fields.extend(["status", "delivered_at"])
        elif status == "read":
            message.status = BotMessage.Statuses.SENT
            message.read_at = message.read_at or timestamp
            message.delivered_at = message.delivered_at or timestamp
            update_fields.extend(["status", "read_at", "delivered_at"])
        elif status == "failed":
            message.status = BotMessage.Statuses.FAILED
            message.error_text = _whatsapp_status_error(item)
            update_fields.extend(["status", "error_text"])
        message.save(update_fields=list(dict.fromkeys(update_fields)))
        processed += 1

    IntegrationEventLog.objects.create(
        business=business,
        provider=BotChannel.Channels.WHATSAPP,
        channel=BotChannel.Channels.WHATSAPP,
        direction=IntegrationEventLog.Directions.INBOUND,
        payload_json={"payload": safe_payload, "statuses": len(statuses), "processed": processed},
        status=IntegrationEventLog.Statuses.PROCESSED,
    )
    return processed


def _whatsapp_timestamp(value):
    try:
        if value:
            return datetime.fromtimestamp(int(value), tz=timezone.get_current_timezone())
    except (TypeError, ValueError, OSError):
        pass
    return timezone.now()


def _whatsapp_status_error(item):
    errors = item.get("errors") or []
    if not errors:
        return "WhatsApp delivery failed."
    error = errors[0]
    return str(error.get("title") or error.get("message") or error.get("code") or "WhatsApp delivery failed.")


def save_whatsapp_inbound_message(payload, auth_context=None, headers=None):
    routes = verified_whatsapp_routes(payload, auth_context)
    channel, _, payload = next((route for route in routes if route[1].get("messages")), routes[0])
    parsed = parse_inbound_message(payload, headers=headers)
    safe_payload = sanitize_config(payload)
    business = channel.bot.business

    conversation, created = BotConversation.objects.get_or_create(
        business=business,
        bot=channel.bot,
        channel=BotConversation.Channels.WHATSAPP,
        external_user_id=parsed["sender_id"],
        defaults={"status": BotConversation.Statuses.OPEN},
    )
    if created:
        increment_usage(business, UsageCounter.Metrics.CONVERSATIONS)
    conversation.updated_at = timezone.now()
    conversation.save(update_fields=["updated_at"])

    external_message_id = parsed.get("message_id", "")
    existing_message = find_existing_inbound_message(conversation, external_message_id)
    if existing_message:
        IntegrationEventLog.objects.create(
            business=conversation.business,
            provider=BotChannel.Channels.WHATSAPP,
            channel=BotChannel.Channels.WHATSAPP,
            direction=IntegrationEventLog.Directions.INBOUND,
            payload_json={
                "payload": safe_payload,
                "conversation_id": conversation.id,
                "message_id": existing_message.id,
                "duplicate": True,
            },
            status=IntegrationEventLog.Statuses.PROCESSED,
        )
        return conversation, existing_message

    message, created_message = create_inbound_message_once(
        conversation=conversation,
        text=parsed["text"],
        external_message_id=external_message_id,
        payload_json={
            "whatsapp_payload": safe_payload,
            "whatsapp_sender_id": parsed["sender_id"],
            "whatsapp_sender_name": parsed.get("sender_name", ""),
            "whatsapp_phone_number_id": parsed.get("phone_number_id", ""),
            "whatsapp_display_phone_number": parsed.get("display_phone_number", ""),
        },
        status=BotMessage.Statuses.RECEIVED,
    )
    if not created_message:
        IntegrationEventLog.objects.create(
            business=conversation.business,
            provider=BotChannel.Channels.WHATSAPP,
            channel=BotChannel.Channels.WHATSAPP,
            direction=IntegrationEventLog.Directions.INBOUND,
            payload_json={
                "payload": safe_payload,
                "conversation_id": conversation.id,
                "message_id": message.id,
                "duplicate": True,
            },
            status=IntegrationEventLog.Statuses.PROCESSED,
        )
        return conversation, message
    from apps.bots.inbox_service import register_bot_message

    register_bot_message(message)
    handle_appointment_followup_reply(
        business=conversation.business,
        channel=BotConversation.Channels.WHATSAPP,
        external_user_id=conversation.external_user_id,
        text=message.text,
    )
    maybe_run_auto_pipeline(conversation=conversation, message=message, channel=channel)
    record_inbound_consent(
        business=conversation.business,
        channel=BotConversation.Channels.WHATSAPP,
        external_user_id=conversation.external_user_id,
        text=message.text,
        conversation=conversation,
    )
    record_message_received_event(conversation=conversation, message=message, provider=BotConversation.Channels.WHATSAPP)
    IntegrationEventLog.objects.create(
        business=conversation.business,
        provider=BotChannel.Channels.WHATSAPP,
        channel=BotChannel.Channels.WHATSAPP,
        direction=IntegrationEventLog.Directions.INBOUND,
        payload_json={"payload": safe_payload, "conversation_id": conversation.id, "message_id": message.id},
        status=IntegrationEventLog.Statuses.PROCESSED,
    )
    run_automations_for_event(
        business=conversation.business,
        trigger_type=AutomationRule.TriggerTypes.BOT_MESSAGE_RECEIVED,
        entity=conversation,
        payload={
            "trigger_type": AutomationRule.TriggerTypes.BOT_MESSAGE_RECEIVED,
            "conversation_id": conversation.id,
            "message_id": message.id,
            "text": message.text,
        },
    )
    return conversation, message


def send_whatsapp_message(channel, recipient_id, text):
    from apps.integrations.providers.whatsapp import WhatsAppProvider

    return WhatsAppProvider().send_message(channel, recipient_id, text)
