"""Import provider history without triggering new-message automation or delivery."""
from datetime import datetime, timezone as datetime_timezone
import re

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bots.models import BotConversation, BotMessage


def phone_digits(value):
    if not isinstance(value, str):
        return ""
    number = re.sub(r"[+ ()-]", "", value)
    return number if re.fullmatch(r"[1-9][0-9]{7,14}", number) else ""


def message_time(value):
    try:
        result = datetime.fromtimestamp(int(value), tz=datetime_timezone.utc)
    except (ValueError, TypeError, OSError, OverflowError) as exc:
        raise ValidationError("Invalid WhatsApp message timestamp.") from exc
    if result > timezone.now() + timezone.timedelta(minutes=5):
        raise ValidationError("WhatsApp message timestamp is in the future.")
    return result


def prepare_message(data, *, business_phone, recipient="", history=False):
    if not isinstance(data, dict):
        raise ValidationError("Invalid WhatsApp message.")
    identifier, kind = data.get("id"), data.get("type")
    if not isinstance(identifier, str) or not 0 < len(identifier) <= 255 or not isinstance(kind, str):
        raise ValidationError("Invalid WhatsApp message identity.")
    sender = phone_digits(data.get("from"))
    outbound = sender == business_phone
    recipient = phone_digits(recipient) if history else phone_digits(data.get("to"))
    if not recipient or not sender or (sender != recipient and not outbound) or (not history and not outbound):
        raise ValidationError("WhatsApp message participants do not match the thread.")
    contents = data.get(kind) or {}
    if not isinstance(contents, dict):
        raise ValidationError("Invalid WhatsApp message content.")
    text = contents.get("body") if kind == "text" else contents.get("caption", "")
    if not isinstance(text, str) or len(text) > 65536 or (kind == "text" and not text):
        raise ValidationError("Invalid WhatsApp message text.")
    history_context = data.get("history_context") or {}
    if not isinstance(history_context, dict):
        raise ValidationError("Invalid WhatsApp history context.")
    receipt = history_context.get("status")
    receipt = receipt if isinstance(receipt, str) else ""
    return {
        "id": identifier, "recipient": recipient, "outbound": outbound,
        "time": message_time(data.get("timestamp")), "type": kind,
        "text": text or f"[WhatsApp: {kind}]", "history": history,
        "history_status": receipt,
        "media": {key: contents[key] for key in ("id", "mime_type", "sha256", "filename") if isinstance(contents.get(key), str)},
    }


@transaction.atomic
def import_message(channel, item):
    from apps.businesses.models import Business
    from apps.bots.inbox_service import register_bot_message

    # Same lock ordering as Inbox and channel setup; serializes conversation creation.
    Business.objects.select_for_update().get(pk=channel.bot.business_id)
    conversation, created = BotConversation.objects.get_or_create(
        business_id=channel.bot.business_id, bot_id=channel.bot_id, channel="whatsapp",
        external_user_id=item["recipient"], defaults={"bot_enabled": False},
    )
    conversation = BotConversation.objects.select_for_update().get(pk=conversation.pk)
    direction = "outbound" if item["outbound"] else "inbound"
    existing = conversation.messages.filter(external_message_id=item["id"], direction=direction).first()
    if existing:
        if existing.payload_json.get("source") == "whatsapp_history" and item["type"] != "media_placeholder":
            existing.text = item["text"]
            existing.payload_json = {**existing.payload_json, "content_type": item["type"], "media": item["media"]}
            existing.save(update_fields=["text", "payload_json"])
            if not item["history"]:
                existing.status, existing.sent_at = "sent", item["time"]
                existing.payload_json.update(source="whatsapp_business_app", historical=False)
                existing.save(update_fields=["status", "sent_at", "payload_json"])
                _staff_handoff(conversation)
        return existing
    status = "received"
    if item["outbound"]:
        status = "sent"
        if item["history"]:
            receipt = item.get("history_status", "")
            status = "sent" if receipt in {"sent", "delivered", "read", "played"} else "failed" if receipt in {"error", "failed"} else "delivery_unknown"
    message = BotMessage.objects.create(
        conversation=conversation, direction=direction, sender_type="manager" if item["outbound"] else "client",
        text=item["text"], external_message_id=item["id"], status=status,
        sent_at=item["time"] if status == "sent" else None,
        payload_json={"source": "whatsapp_history" if item["history"] else "whatsapp_business_app",
                      "content_type": item["type"], "media": item["media"], "historical": item["history"],
                      "history_status": item.get("history_status", ""),
                      "whatsapp_phone_number_id": channel.external_id},
    )
    BotMessage.objects.filter(pk=message.pk).update(created_at=item["time"])
    message.created_at = item["time"]
    previous_last, previous_outbound = conversation.last_message_at, conversation.last_outbound_at
    if not item["history"]:
        register_bot_message(message)
        _staff_handoff(conversation)
    # History never updates last_inbound_at/unread, consent, CRM lifecycle or AI.
    conversation.refresh_from_db()
    conversation.last_message_at = max(item["time"], previous_last or item["time"])
    fields = ["last_message_at"]
    if item["outbound"]:
        conversation.last_outbound_at = max(item["time"], previous_outbound or item["time"])
        fields.append("last_outbound_at")
    conversation.save(update_fields=fields)
    return message


def _staff_handoff(conversation):
    from apps.bots.inbox_service import handoff_conversation
    handoff_conversation(conversation, reason="Ответ из WhatsApp Business App: диалог ведёт сотрудник.")
    conversation.messages.filter(direction="outbound", sender_type__in=["bot", "ai"], status__in=["queued", "retry_scheduled"]).update(
        status="cancelled", error_text="Staff replied in WhatsApp Business App.", delivery_next_retry_at=None,
    )
