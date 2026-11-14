"""Persist a Meta send intent before HTTP; ambiguous outcomes must not be resent."""
from uuid import uuid4

from django.db import connection, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bots.models import BotChannel, BotMessage


def begin_attempt(message, channel):
    if connection.in_atomic_block:
        raise ValidationError("Meta delivery requires a committed outbox.")
    with transaction.atomic():
        current = BotMessage.objects.select_for_update().get(pk=message.pk)
        active = BotChannel.objects.filter(pk=channel.pk, bot_id=current.conversation.bot_id,
            bot__business_id=current.conversation.business_id, status="active",
            config_json__provider_mode="meta_cloud").exists()
        if not active or current.status != BotMessage.Statuses.DELIVERING:
            raise ValidationError("WhatsApp channel or message is no longer available.")
        if current.sender_type == BotMessage.SenderTypes.MANAGER:
            from django.contrib.auth import get_user_model
            from apps.businesses.access import Actions, Resources, can

            actor = get_user_model().objects.filter(pk=(current.payload_json or {}).get("sent_by_user_id"), is_active=True).first()
            if actor is None or not all(can(actor, current.conversation.business, Resources.CONVERSATIONS,
                    action, obj=current.conversation).allowed for action in (Actions.VIEW, Actions.UPDATE)):
                raise ValidationError("Message sender no longer has permission.")
        previous = (current.payload_json or {}).get("meta_attempt") or {}
        if previous and previous.get("state") not in {"rejected", "rate_limited", "failed"}:
            raise ValidationError("Wait for provider confirmation before sending again.")
        attempt = {"id": str(uuid4()), "state": "submitting", "channel_id": channel.pk}
        current.payload_json = {**(current.payload_json or {}), "meta_attempt": attempt}
        current.payload_json.pop("whatsapp_status", None)
        current.external_message_id = ""
        current.sent_at = current.delivered_at = current.read_at = None
        current.save(update_fields=["payload_json", "external_message_id", "sent_at", "delivered_at", "read_at"])
    return attempt["id"]


@transaction.atomic
def finish_attempt(message, result):
    current = BotMessage.objects.select_for_update().get(pk=message.pk)
    payload = dict(current.payload_json or {})
    attempt = dict(payload.get("meta_attempt") or {})
    if not attempt or attempt.get("id") != result.get("meta_attempt_id"):
        return current
    # A signed receipt can beat the HTTP response, including an ambiguous failure.
    if attempt.get("state") in {"sent", "delivered", "read", "failed"}:
        return current
    from apps.integrations.sanitization import sanitize_error_payload, sanitize_error_text

    current.delivery_locked_at = None
    current.delivery_next_retry_at = None
    if result.get("ok") and result.get("provider_message_id"):
        attempt["state"] = "accepted"
        current.external_message_id = result["provider_message_id"]
        current.status = BotMessage.Statuses.ACCEPTED
        current.error_text = ""
    elif result.get("delivery_unknown"):
        attempt["state"] = "unknown"
        current.status = BotMessage.Statuses.DELIVERY_UNKNOWN
        current.error_text = "WhatsApp delivery outcome is unknown. Wait for provider confirmation."
    else:
        attempt["state"] = "rate_limited" if result.get("retryable") else "rejected"
        current.error_text = sanitize_error_text(result.get("reason") or "WhatsApp delivery failed.")
        if result.get("retryable") and current.delivery_attempts < current.delivery_max_attempts:
            from apps.bots.outbound_delivery import _retry_delay_seconds

            current.status = BotMessage.Statuses.RETRY_SCHEDULED
            current.delivery_next_retry_at = timezone.now() + timezone.timedelta(seconds=_retry_delay_seconds(current.delivery_attempts))
        else:
            current.status = BotMessage.Statuses.FAILED
    payload.update(meta_attempt=attempt, provider_result=sanitize_error_payload(result), delivery_mode="provider")
    current.payload_json = payload
    current.save(update_fields=["payload_json", "external_message_id", "status", "error_text", "delivery_locked_at", "delivery_next_retry_at"])
    return current
