"""YCloud text transport, durable send intent and monotonic delivery receipts."""
from uuid import UUID

from django.db import connection as database, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.bots.models import BotMessage
from apps.integrations.channel_boundary import lock_channel_for_setup
from apps.integrations.ycloud import client
from apps.integrations.ycloud.models import YCloudConnection, YCloudDispatch


RANK = {"submitting": 0, "unknown": 0, "accepted": 1, "sent": 2, "rejected": 2.5, "delivered": 3, "read": 4}


def send_text(channel, recipient_id, text, payload):
    if not client.configured():
        return {"ok": False, "reason": "YCloud setup required.", "retryable": False}
    if database.in_atomic_block:
        return {"ok": False, "reason": "YCloud delivery requires a committed outbox.", "retryable": False}
    if not payload.get("zani_message_id") or payload.get("whatsapp_template_name"):
        return {"ok": False, "reason": "This YCloud stage supports Inbox text only.", "retryable": False}
    from apps.integrations.ycloud.events import current_channel
    from apps.integrations.providers.whatsapp import WhatsAppProvider
    try:
        with transaction.atomic():
            channel = lock_channel_for_setup(channel)
            binding = YCloudConnection.objects.select_for_update().select_related("channel__bot__business").get(channel=channel)
            current_channel(binding)
            message = BotMessage.objects.select_for_update().get(pk=payload["zani_message_id"],
                conversation__bot=channel.bot, conversation__business=channel.bot.business,
                conversation__channel="whatsapp", conversation__external_user_id=recipient_id, direction="outbound")
            if message.text != text or message.status != BotMessage.Statuses.DELIVERING:
                raise client.YCloudError("message_changed")
            if message.sender_type == BotMessage.SenderTypes.MANAGER:
                from django.contrib.auth import get_user_model
                from apps.businesses.access import Actions, Resources, can
                actor = get_user_model().objects.filter(pk=(message.payload_json or {}).get("sent_by_user_id"), is_active=True).first()
                if actor is None or not all(can(actor, channel.bot.business, Resources.CONVERSATIONS, action, obj=message.conversation) for action in (Actions.VIEW, Actions.UPDATE)):
                    raise client.YCloudError("permission_revoked")
            previous = YCloudDispatch.objects.filter(message=message).order_by("-pk").first()
            if previous and previous.state not in {"rejected", "rate_limited"}:
                # Covers a crash after send intent was committed, even before HTTP returned.
                _project(previous, message)
                return {"transport": "ycloud", "ok": previous.state in {"accepted", "sent", "delivered", "read"}}
            if not WhatsAppProvider()._within_customer_service_window(channel, recipient_id):
                raise client.YCloudError("service_window_closed")
            latest_inbound = message.conversation.messages.filter(direction="inbound").order_by("-created_at", "-pk").first()
            if latest_inbound:
                source_time = ((latest_inbound.payload_json or {}).get("whatsapp_payload") or {}).get("ycloud_sent_at")
                if source_time and _timestamp(source_time) < timezone.now() - timezone.timedelta(hours=24):
                    raise client.YCloudError("service_window_closed")
            attempt = YCloudDispatch.objects.create(message=message, connection=binding)
            _project(attempt, message)
    except (YCloudConnection.DoesNotExist, BotMessage.DoesNotExist, client.YCloudError) as exc:
        return {"ok": False, "reason": str(exc) if isinstance(exc, client.YCloudError) else "Channel not connected.", "retryable": False}
    try:
        result = client.call("POST", "/whatsapp/messages", {"from": binding.phone_number, "to": recipient_id,
            "type": "text", "text": {"body": text}, "externalId": str(attempt.correlation_id)})
        if not isinstance(result.get("id"), str) or not 0 < len(result["id"]) <= 255:
            raise client.YCloudError("invalid_provider_response", ambiguous=True)
        with transaction.atomic():
            lock_channel_for_setup(channel)
            attempt = YCloudDispatch.objects.select_for_update().get(pk=attempt.pk)
            if attempt.provider_id and attempt.provider_id != result["id"]:
                raise client.YCloudError("provider_identity_conflict", ambiguous=True)
            attempt.provider_id = result["id"]
            attempt.wamid = str(result.get("wamid") or attempt.wamid)[:255]
            state = result.get("status")
            state = state if state in {"accepted", "sent", "delivered", "read"} else "accepted"
            if RANK.get(state, 0) > RANK.get(attempt.state, 0):
                attempt.state = state
            attempt.save()
            _project(attempt)
    except Exception as exc:
        # Unknown POST outcomes are terminal locally until a signed receipt resolves them.
        # Only an explicit HTTP rejection is safe for another attempt.
        with transaction.atomic():
            lock_channel_for_setup(channel)
            attempt = YCloudDispatch.objects.select_for_update().get(pk=attempt.pk)
            if attempt.state == "submitting":
                attempt.state = ("rate_limited" if exc.code == "rate_limited" else "rejected") if isinstance(exc, client.YCloudError) and not exc.ambiguous else "unknown"
                attempt.error_code = exc.code if isinstance(exc, client.YCloudError) else "provider_unavailable"
                attempt.save()
                _project(attempt, data={"retry_after": getattr(exc, "retry_after", 0)})
    return {"transport": "ycloud", "ok": attempt.state in {"accepted", "sent", "delivered", "read"}}


def _project(attempt, message=None, data=None):
    message = message or BotMessage.objects.select_for_update().select_related("conversation").get(pk=attempt.message_id)
    data = data or {}
    previous_status = message.status
    if attempt.state in {"submitting", "unknown"}:
        message.status = BotMessage.Statuses.DELIVERY_UNKNOWN
    elif attempt.state == "accepted":
        message.status = BotMessage.Statuses.ACCEPTED
    elif attempt.state in {"sent", "delivered", "read"}:
        message.status = BotMessage.Statuses.SENT
        message.sent_at = message.sent_at or _timestamp(data.get("sendTime"))
        if attempt.state in {"delivered", "read"}:
            message.delivered_at = message.delivered_at or _timestamp(data.get("deliverTime"))
        if attempt.state == "read":
            message.read_at = message.read_at or _timestamp(data.get("readTime"))
    else:
        message.status = BotMessage.Statuses.FAILED
    message.external_message_id = attempt.provider_id or message.external_message_id
    message.error_text = attempt.error_code if message.status in {BotMessage.Statuses.FAILED, BotMessage.Statuses.DELIVERY_UNKNOWN} else ""
    message.delivery_locked_at = None
    message.delivery_next_retry_at = None
    if attempt.state == "rate_limited" and message.delivery_attempts < message.delivery_max_attempts:
        message.status = BotMessage.Statuses.RETRY_SCHEDULED
        message.delivery_next_retry_at = timezone.now() + timezone.timedelta(seconds=max(30, min(int(data.get("retry_after") or 0), 86400)))
    message.payload_json = {**(message.payload_json or {}), "ycloud_status": attempt.state, "ycloud_wamid": attempt.wamid}
    message.save(update_fields=["status", "sent_at", "delivered_at", "read_at", "external_message_id", "error_text", "delivery_locked_at", "delivery_next_retry_at", "payload_json"])
    if previous_status != BotMessage.Statuses.SENT and message.status == BotMessage.Statuses.SENT and message.sender_type == BotMessage.SenderTypes.MANAGER:
        from apps.bots.handoff_recovery import schedule_after_staff_delivery
        schedule_after_staff_delivery(message)


def _timestamp(value):
    parsed = parse_datetime(value) if isinstance(value, str) else None
    return parsed if parsed and timezone.is_aware(parsed) else timezone.now()


def apply_status(binding, data):
    from apps.integrations.ycloud.events import current_channel
    current_channel(binding, active=False)  # Receipts remain useful while the channel is paused.
    if data.get("wabaId") != binding.waba_id or data.get("from") != binding.phone_number:
        raise client.YCloudError("binding_conflict")
    provider_id = data.get("id")
    if not isinstance(provider_id, str) or not 0 < len(provider_id) <= 255:
        raise client.YCloudError("invalid_message")
    attempts = YCloudDispatch.objects.select_for_update().filter(connection=binding)
    attempt = attempts.filter(provider_id=provider_id).first()
    if attempt is None:
        try:
            correlation = UUID(str(data.get("externalId", "")))
        except ValueError:
            raise client.YCloudError("unknown_dispatch", retryable=True) from None
        attempt = attempts.filter(correlation_id=correlation).first()
    if attempt is None:
        raise client.YCloudError("unknown_dispatch", retryable=True)
    message = BotMessage.objects.select_for_update().select_related("conversation").get(pk=attempt.message_id)
    if data.get("to") != message.conversation.external_user_id or (attempt.provider_id and attempt.provider_id != provider_id):
        raise client.YCloudError("binding_conflict")
    state = data.get("status")
    if state not in {"accepted", "sent", "delivered", "read", "failed"}:
        return
    attempt.provider_id = provider_id
    attempt.wamid = str(data.get("wamid") or attempt.wamid)[:255]
    if state == "failed":
        if RANK.get(attempt.state, 0) < RANK["delivered"]:
            attempt.state, attempt.error_code = "rejected", "provider_rejected"
    elif RANK[state] > RANK.get(attempt.state, 0):
        attempt.state, attempt.error_code = state, ""
    attempt.save()
    # Old receipts remain historical evidence after a deliberate retry.
    if not YCloudDispatch.objects.filter(message=message, pk__gt=attempt.pk).exists():
        _project(attempt, message, data)
