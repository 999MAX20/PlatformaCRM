"""Normalize YCloud history into the side-effect-free WhatsApp history importer."""
import re

from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.bots.models import BotMessage
from apps.integrations.whatsapp.coexistence_messages import import_message
from apps.integrations.ycloud import client
from apps.integrations.ycloud.coexistence import CONTENT_TYPES
from apps.integrations.ycloud.models import YCloudConnection


def record_history(connection, payload):
    from apps.integrations.ycloud.events import current_channel

    channel = current_channel(connection, active=False)
    if connection.status != "connected" or connection.onboarding_type != YCloudConnection.OnboardingTypes.APP:
        raise client.YCloudError("coexistence_not_enabled")
    outbound = "whatsappMessage" in payload
    data = payload["whatsappMessage" if outbound else "whatsappInboundMessage"]
    business_number = data.get("from" if outbound else "to")
    recipient = data.get("to" if outbound else "from")
    if data.get("wabaId") != connection.waba_id or business_number != connection.phone_number:
        raise client.YCloudError("binding_conflict")
    identifier, provider_id, kind = data.get("wamid"), data.get("id"), data.get("type")
    if (not isinstance(recipient, str) or not re.fullmatch(r"\+[1-9][0-9]{7,14}", recipient)
            or recipient == business_number
            or not isinstance(identifier, str) or not 0 < len(identifier) <= 255
            or not isinstance(provider_id, str) or not 0 < len(provider_id) <= 255
            or not isinstance(kind, str) or kind not in CONTENT_TYPES | {"media_placeholder"}):
        raise client.YCloudError("invalid_message")
    try:
        sent_at = parse_datetime(data.get("sendTime", "")) if isinstance(data.get("sendTime"), str) else None
    except ValueError:
        sent_at = None
    if not sent_at or not timezone.is_aware(sent_at) or sent_at > timezone.now() + timezone.timedelta(minutes=5):
        raise client.YCloudError("invalid_message_time")
    text = (data.get("text") or {}).get("body") if isinstance(data.get("text"), dict) else None
    if kind == "text" and (not isinstance(text, str) or not text or len(text) > 4096):
        raise client.YCloudError("invalid_message")
    if not isinstance(data.get("status", ""), str):
        raise client.YCloudError("invalid_message")
    previous = BotMessage.objects.filter(
        conversation__business_id=channel.bot.business_id, conversation__bot_id=channel.bot_id,
        conversation__channel="whatsapp", external_message_id=identifier,
    ).select_related("conversation").first()
    if previous and (previous.direction != ("outbound" if outbound else "inbound")
                     or previous.conversation.external_user_id != recipient):
        raise client.YCloudError("message_identity_conflict")
    # History arriving after a live message must never overwrite its state or content.
    if previous:
        return previous
    message = import_message(channel, {
        "id": identifier, "recipient": recipient, "outbound": outbound, "time": sent_at,
        "type": kind, "text": text if kind == "text" else f"[WhatsApp: {kind}]",
        "history": True, "history_status": data.get("status", ""), "media": {},
    })
    message.payload_json.update(ycloud_id=provider_id, ycloud_wamid=identifier,
                                content_unavailable=kind != "text", history_provider="ycloud")
    message.save(update_fields=["payload_json"])
    return message


def history_status(connection):
    """Report observed work, not completion inferred from an unrouteable progress ping."""
    if connection is None:
        return {"messages": 0, "pending_events": 0, "failed_events": 0}
    events = connection.events.filter(kind="whatsapp.smb.history")
    messages = BotMessage.objects.filter(
        conversation__business_id=connection.channel.bot.business_id,
        conversation__bot_id=connection.channel.bot_id, conversation__channel="whatsapp",
        payload_json__history_provider="ycloud",
        payload_json__whatsapp_phone_number_id=connection.channel.external_id,
    ).count()
    return {"messages": messages, "pending_events": events.filter(status="pending").count(),
            "failed_events": events.filter(status="failed").count()}
