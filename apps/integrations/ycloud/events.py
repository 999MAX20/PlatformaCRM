"""Bounded transactional event processing, recovered by the periodic task."""
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from rest_framework.exceptions import APIException

from apps.integrations.channel_boundary import lock_channel_business
from apps.bots.models import BotChannel
from apps.integrations.ycloud import client, onboarding
from apps.integrations.ycloud.models import YCloudConnection, YCloudEvent


def current_channel(connection, *, active=True):
    channel = connection.channel
    config = channel.config_json or {}
    if (channel.bot.is_deleted or channel.bot.business.status not in {"active", "trial"}
            or config.get("provider_mode") != "ycloud"
            or config.get("setup_revision") != connection.setup_revision
            or (active and (channel.status != "active" or connection.status != "connected"))):
        raise client.YCloudError("channel_unavailable", retryable=channel.status == "paused")
    return channel


@transaction.atomic
def process(event_id):
    initial = YCloudEvent.objects.select_related("connection__channel__bot__business").get(pk=event_id)
    lock_channel_business(initial.connection.channel.bot.business_id)
    BotChannel.objects.select_for_update().get(pk=initial.connection.channel_id)
    connection = YCloudConnection.objects.select_for_update().select_related("channel__bot__business", "initiated_by").get(pk=initial.connection_id)
    event = YCloudEvent.objects.select_for_update().get(pk=event_id)
    if event.status != "pending" or event.next_attempt_at > timezone.now():
        return
    event.attempts += 1
    try:
        with transaction.atomic():
            if event.kind == "whatsapp.business_account.updated":
                account = event.payload["whatsappBusinessAccount"]
                if str(connection.customer_id) != account.get("partnerCustomerId"):
                    raise client.YCloudError("setup_changed")
                if account.get("updateEvent") == "PARTNER_ADDED":
                    onboarding.confirm(connection, account)
            elif event.kind == "whatsapp.inbound_message.received":
                inbound(connection, event.payload["whatsappInboundMessage"])
            else:
                from apps.integrations.ycloud.dispatch import apply_status
                apply_status(connection, event.payload["whatsappMessage"])
        event.status = "processed"
        event.error_code = ""
    except Exception as exc:
        event.error_code = exc.code if isinstance(exc, client.YCloudError) else "processing_rejected"
        retryable = exc.retryable if isinstance(exc, client.YCloudError) else not isinstance(exc, (APIException, IntegrityError))
        event.status = "pending" if retryable and event.attempts < 6 else "failed"
        event.next_attempt_at = timezone.now() + timezone.timedelta(seconds=min(30 * 2 ** event.attempts, 1800))
        if event.kind == "whatsapp.business_account.updated":
            YCloudConnection.objects.filter(pk=connection.pk).update(last_error=event.error_code)
    event.save(update_fields=["status", "attempts", "next_attempt_at", "error_code"])


def inbound(connection, data):
    channel = current_channel(connection)
    if data.get("wabaId") != connection.waba_id or data.get("to") != connection.phone_number:
        raise client.YCloudError("binding_conflict")
    if data.get("type") != "text":
        raise client.YCloudError("unsupported_message_type")
    text = (data.get("text") or {}).get("body") if isinstance(data.get("text"), dict) else None
    sender, message_id = data.get("from"), data.get("wamid") or data.get("id")
    if not isinstance(text, str) or not text or len(text) > 4096 or not isinstance(sender, str) or not sender or not isinstance(message_id, str) or not 0 < len(message_id) <= 255:
        raise client.YCloudError("invalid_message")
    sent_at = parse_datetime(data.get("sendTime", "")) if isinstance(data.get("sendTime"), str) else None
    if sent_at is None or not timezone.is_aware(sent_at) or sent_at > timezone.now() + timezone.timedelta(minutes=5):
        raise client.YCloudError("invalid_message_time")
    from apps.integrations.whatsapp import save_whatsapp_inbound_message
    from apps.integrations.whatsapp_routing import VerifiedWhatsAppWebhook
    # Reuse the existing Inbox/CRM/AI path after the YCloud route has been verified.
    profile = data.get("customerProfile")
    payload = {"phone_number_id": connection.phone_id, "message_id": message_id, "text": text, "ycloud_sent_at": sent_at.isoformat(),
        "contact": {"id": sender, "name": str(profile.get("name") or "")[:255] if isinstance(profile, dict) else ""}}
    return save_whatsapp_inbound_message(payload, VerifiedWhatsAppWebhook(
        mode="ycloud", channel_id=channel.pk, bot_id=channel.bot_id, business_id=channel.bot.business_id,
    ))


def process_due(limit=100):
    if not client.configured():
        return 0
    ids = list(YCloudEvent.objects.filter(status="pending", next_attempt_at__lte=timezone.now()).order_by("pk").values_list("pk", flat=True)[:max(0, min(limit, 500))])
    for event_id in ids:
        process(event_id)
    return len(ids)
