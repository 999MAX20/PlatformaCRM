"""Record account notifications without treating them as channel activation."""
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.bots.models import BotChannel
from apps.integrations.models import IntegrationEventLog
from apps.integrations.whatsapp_routing import VerifiedWhatsAppWebhook


def prepare_account_update(entry, value, auth_context):
    if not isinstance(auth_context, VerifiedWhatsAppWebhook) or auth_context.mode != "meta":
        raise PermissionDenied("Account updates require a Meta signature.")
    waba_id = entry.get("id")
    event = value.get("event")
    info = value.get("waba_info", {})
    if (not isinstance(waba_id, str) or not waba_id or len(waba_id) > 255
            or not isinstance(event, str) or not event or len(event) > 128
            or not isinstance(info, dict)):
        raise ValidationError("Invalid WhatsApp account update.")
    if info.get("waba_id") not in (None, waba_id):
        raise ValidationError("WhatsApp account identifiers do not match.")
    safe = {"field": "account_update", "waba_id": waba_id, "event": event}
    for key in ("owner_business_id", "partner_app_id"):
        if key in info:
            if not isinstance(info[key], str) or len(info[key]) > 255:
                raise ValidationError("Invalid WhatsApp account metadata.")
            safe[key] = info[key]
    channels = BotChannel.objects.filter(
        channel=BotChannel.Channels.WHATSAPP, config_json__business_account_id=waba_id,
    )
    businesses = set(channels.exclude(
        pk__in=channels.filter(config_json__provider_mode="ycloud").values("pk"),
    ).values_list("bot__business_id", flat=True))
    # Signup can emit this before the local channel exists. Keep that event
    # unassigned; provider business IDs are not CRM tenant IDs.
    business_id = next(iter(businesses)) if len(businesses) == 1 else None
    return business_id, safe


def record_account_updates(updates):
    for business_id, payload in updates:
        IntegrationEventLog.objects.create(
            business_id=business_id, provider="whatsapp", channel="whatsapp",
            direction=IntegrationEventLog.Directions.INBOUND,
            status=IntegrationEventLog.Statuses.PROCESSED, payload_json=payload,
        )
