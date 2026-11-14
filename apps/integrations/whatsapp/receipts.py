from django.db import transaction

from apps.bots.models import BotMessage
from apps.integrations.sanitization import sanitize_config, sanitize_error_text


RANK = {"sent": 1, "failed": 2, "delivered": 3, "read": 4}


@transaction.atomic
def apply_receipt(channel, item):
    from apps.integrations.whatsapp import _whatsapp_timestamp, _whatsapp_status_error

    message_id, status = str(item.get("id") or ""), item.get("status")
    if not message_id or status not in RANK:
        return 0
    candidates = BotMessage.objects.filter(
        conversation__business=channel.bot.business, conversation__bot=channel.bot,
        conversation__channel="whatsapp", direction="outbound",
    )
    correlation = item.get("biz_opaque_callback_data")
    if correlation:
        message = candidates.filter(payload_json__meta_attempt__id=correlation).first()
    else:
        message = candidates.filter(external_message_id=message_id).first()
    if not message:
        return 0
    from apps.bots.safety_state import _locked

    _locked(message.conversation)
    message = BotMessage.objects.select_for_update().get(pk=message.pk)
    payload = dict(message.payload_json or {})
    attempt = dict(payload.get("meta_attempt") or {})
    if correlation and attempt.get("id") != correlation:
        return 0
    if not correlation and message.external_message_id != message_id:
        return 0
    if attempt and attempt.get("channel_id") != channel.pk:
        return 0
    if message.external_message_id and message.external_message_id != message_id:
        return 0
    recipient = str(item.get("recipient_id") or "").lstrip("+")
    if recipient and recipient != message.conversation.external_user_id.lstrip("+"):
        return 0
    previous = (payload.get("whatsapp_status") or {}).get("status")
    rank = 4 if message.read_at else 3 if message.delivered_at else RANK.get(previous, 0)
    if RANK[status] <= rank:
        return 0
    timestamp = _whatsapp_timestamp(item.get("timestamp"))
    was_sent = message.status == BotMessage.Statuses.SENT
    payload["whatsapp_status"] = sanitize_config(item)
    if attempt:
        attempt["state"] = status
        payload["meta_attempt"] = attempt
    message.payload_json = payload
    message.external_message_id = message_id
    message.delivery_locked_at = None
    message.delivery_next_retry_at = None
    if status == "failed":
        message.status = BotMessage.Statuses.FAILED
        message.error_text = sanitize_error_text(_whatsapp_status_error(item))
    else:
        message.status = BotMessage.Statuses.SENT
        message.error_text = ""
        message.sent_at = message.sent_at or timestamp
        if status in {"delivered", "read"}:
            message.delivered_at = message.delivered_at or timestamp
        if status == "read":
            message.read_at = message.read_at or timestamp
    message.save(update_fields=["payload_json", "external_message_id", "status", "error_text",
        "sent_at", "delivered_at", "read_at", "delivery_locked_at", "delivery_next_retry_at"])
    if not was_sent and message.status == BotMessage.Statuses.SENT and message.sender_type == BotMessage.SenderTypes.MANAGER:
        from apps.bots.handoff_recovery import schedule_after_staff_delivery

        schedule_after_staff_delivery(message)
    return 1
