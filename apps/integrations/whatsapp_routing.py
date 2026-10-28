"""Carry verified webhook identity through routing, without retaining credentials."""
from dataclasses import dataclass

from django.db.models import Q
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.bots.models import BotChannel


@dataclass(frozen=True)
class VerifiedWhatsAppWebhook:
    mode: str
    channel_id: int | None = None
    bot_id: int | None = None
    business_id: int | None = None


def resolve_whatsapp_channel(auth_context, phone_number_id=""):
    if not isinstance(auth_context, VerifiedWhatsAppWebhook):
        raise PermissionDenied("WhatsApp webhook authentication is required.")
    candidates = BotChannel.objects.select_related("bot", "bot__business").filter(
        channel=BotChannel.Channels.WHATSAPP, status=BotChannel.Statuses.ACTIVE,
    )
    phone_number_id = str(phone_number_id or "")
    if auth_context.mode in {"channel", "ycloud"}:
        channel = candidates.filter(
            pk=auth_context.channel_id, bot_id=auth_context.bot_id,
            bot__business_id=auth_context.business_id,
        ).first()
        if channel is None:
            raise PermissionDenied("WhatsApp authenticated channel is unavailable.")
        is_ycloud = (channel.config_json or {}).get("provider_mode") == "ycloud"
        if is_ycloud != (auth_context.mode == "ycloud"):
            raise PermissionDenied("WhatsApp authentication does not match this provider.")
        aliases = {str(channel.external_id or ""), str((channel.config_json or {}).get("phone_number_id") or "")}
        if phone_number_id and phone_number_id not in aliases:
            raise PermissionDenied("WhatsApp webhook route does not match its authenticated channel.")
        return channel
    if auth_context.mode not in {"meta", "internal"}:
        raise PermissionDenied("WhatsApp webhook authentication is required.")
    if not phone_number_id:
        raise PermissionDenied("WhatsApp phone number id is required.")
    matches = list(candidates.exclude(pk__in=candidates.filter(config_json__provider_mode="ycloud").values("pk")).filter(
        Q(config_json__phone_number_id=phone_number_id) | Q(external_id=phone_number_id),
    )[:2])
    if len(matches) != 1:
        raise ValidationError("WhatsApp channel was not uniquely resolved.")
    return matches[0]


def verified_whatsapp_routes(payload, auth_context):
    """Resolve all changes before any effects; each payload copy has one route."""
    routes = []
    for entry in payload.get("entry") or []:
        for change in entry.get("changes") or []:
            value = change.get("value") or {}
            phone_number_id = (value.get("metadata") or {}).get("phone_number_id") or ""
            channel = resolve_whatsapp_channel(auth_context, phone_number_id)
            # Keep the matching provider envelope, never another business's changes.
            portion = {
                **{k: v for k, v in payload.items() if k != "entry"},
                "entry": [{**{k: v for k, v in entry.items() if k != "changes"}, "changes": [change]}],
            }
            routes.append((channel, value, portion))
    if not routes:
        phone_number_id = payload.get("phone_number_id") or (payload.get("metadata") or {}).get("phone_number_id") or ""
        routes.append((resolve_whatsapp_channel(auth_context, phone_number_id), {}, payload))
    return routes
