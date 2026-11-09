"""Business App messages are already sent; importing them must never enqueue delivery."""
import re

from django.db.models import Q
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from apps.bots.models import BotConversation, BotMessage
from apps.integrations.ycloud import client
from apps.integrations.ycloud.models import YCloudConnection, YCloudDispatch


APP_SOURCE = "whatsapp_business_app"
CONTENT_TYPES = {"text", "image", "video", "audio", "document", "sticker", "location", "contacts", "reaction"}


def app_message(binding, data):
    if binding.onboarding_type != YCloudConnection.OnboardingTypes.APP:
        return None
    return BotMessage.objects.select_for_update().filter(
        conversation__business_id=binding.channel.bot.business_id,
        conversation__bot_id=binding.channel.bot_id,
        conversation__channel="whatsapp",
        direction="outbound", payload_json__source=APP_SOURCE,
    ).filter(Q(external_message_id=data.get("wamid") or data.get("id")) |
             Q(payload_json__ycloud_id=data.get("id"))).first()


def record_app_message(binding, data):
    from apps.integrations.ycloud.events import current_channel
    from apps.bots.inbox_service import handoff_conversation, register_bot_message
    from apps.billing.models import UsageCounter
    from apps.billing.usage import increment_usage

    channel = current_channel(binding, active=False)
    if binding.status != "connected" or binding.onboarding_type != YCloudConnection.OnboardingTypes.APP:
        raise client.YCloudError("coexistence_not_enabled")
    if data.get("wabaId") != binding.waba_id or data.get("from") != binding.phone_number:
        raise client.YCloudError("binding_conflict")
    recipient, provider_id, wamid = data.get("to"), data.get("id"), data.get("wamid")
    if (not isinstance(recipient, str) or not re.fullmatch(r"\+[1-9][0-9]{7,14}", recipient)
            or not isinstance(provider_id, str) or not 0 < len(provider_id) <= 255
            or not isinstance(wamid, str) or not 0 < len(wamid) <= 255):
        raise client.YCloudError("invalid_message")
    if data.get("status") not in {"sent", "delivered", "read"}:
        raise client.YCloudError("app_message_not_sent")
    sent_at = parse_datetime(data.get("sendTime", "")) if isinstance(data.get("sendTime"), str) else None
    if not sent_at or not timezone.is_aware(sent_at) or sent_at > timezone.now() + timezone.timedelta(minutes=5):
        raise client.YCloudError("invalid_message_time")
    kind = data.get("type")
    if not isinstance(kind, str) or kind not in CONTENT_TYPES:
        raise client.YCloudError("unsupported_message_type")
    text = (data.get("text") or {}).get("body") if isinstance(data.get("text"), dict) else None
    if kind == "text" and (not isinstance(text, str) or not text or len(text) > 4096):
        raise client.YCloudError("invalid_message")
    previous = app_message(binding, data)
    if previous:
        if previous.external_message_id != wamid or previous.conversation.external_user_id != recipient:
            raise client.YCloudError("message_identity_conflict")
        return previous
    # An API delivery reported on an app stream is a receipt, never a second staff reply.
    if YCloudDispatch.objects.filter(connection=binding).filter(Q(provider_id=provider_id) | Q(wamid=wamid)).exists():
        from apps.integrations.ycloud.dispatch import apply_status
        apply_status(binding, data)
        return None
    conversation, created = BotConversation.objects.get_or_create(
        business=channel.bot.business, bot=channel.bot, channel="whatsapp", external_user_id=recipient,
        defaults={"bot_enabled": False},
    )
    if created:
        increment_usage(channel.bot.business, UsageCounter.Metrics.CONVERSATIONS)
    conversation = BotConversation.objects.select_for_update().get(pk=conversation.pk)
    previous_last, previous_outbound = conversation.last_message_at, conversation.last_outbound_at
    message = BotMessage.objects.create(
        conversation=conversation, direction="outbound", sender_type="manager", status="sent",
        text=text if kind == "text" else f"[WhatsApp Business App: {kind}]",
        external_message_id=wamid, sent_at=sent_at,
        payload_json={"source": APP_SOURCE, "ycloud_id": provider_id, "ycloud_wamid": wamid,
                      "content_type": kind, "content_unavailable": kind != "text", "ycloud_status": "sent"},
    )
    BotMessage.objects.filter(pk=message.pk).update(created_at=sent_at)
    message.created_at = sent_at
    register_bot_message(message)
    # Late provider events must not move an existing conversation backwards in time.
    conversation.refresh_from_db()
    conversation.last_message_at = max(sent_at, previous_last or sent_at)
    conversation.last_outbound_at = max(sent_at, previous_outbound or sent_at)
    conversation.save(update_fields=["last_message_at", "last_outbound_at"])
    handoff_conversation(conversation, reason="Ответ из WhatsApp Business App: диалог ведёт сотрудник.")
    conversation.messages.filter(direction="outbound", sender_type__in=["bot", "ai"],
                                 status__in=["queued", "retry_scheduled"]).update(
        status="cancelled", error_text="Staff replied in WhatsApp Business App.", delivery_next_retry_at=None)
    return message


def apply_app_status(binding, data):
    message = app_message(binding, data)
    if message is None:
        return False
    if message.conversation.external_user_id != data.get("to"):
        raise client.YCloudError("message_identity_conflict")
    if data.get("wamid") and data["wamid"] != message.external_message_id:
        raise client.YCloudError("message_identity_conflict")
    state = data.get("status")
    ranks = {"sent": 1, "delivered": 2, "read": 3}
    if ranks.get(state, 0) > ranks.get(message.payload_json.get("ycloud_status"), 0):
        from apps.integrations.ycloud.dispatch import _timestamp
        message.payload_json = {**message.payload_json, "ycloud_status": state}
        message.delivered_at = message.delivered_at or _timestamp(data.get("deliverTime"))
        if state == "read":
            message.read_at = message.read_at or _timestamp(data.get("readTime"))
        message.save(update_fields=["payload_json", "delivered_at", "read_at"])
    return True
