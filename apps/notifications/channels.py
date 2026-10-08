"""Local delivery configuration checks. These never contact a provider or migrate credentials."""
from django.conf import settings

from apps.bots.models import Bot, BotChannel
from apps.integrations.credential_encryption import ConnectorCredentialError, decrypt_connector_credential
from apps.integrations.models import BusinessConnector


def _has_usable_credential(channel, key):
    connector = BusinessConnector.objects.filter(
        business_id=channel.bot.business_id, provider=channel.channel, config_json__bot_channel_id=channel.pk,
    ).first()
    if connector:
        if connector.status != BusinessConnector.Statuses.CONNECTED:
            return False
        credential = connector.credentials.filter(key=key).first()
        if credential:
            try:
                return bool(decrypt_connector_credential(credential))
            except ConnectorCredentialError:
                return False
    return bool((channel.config_json or {}).get(key))


def active_delivery_channel(business, channel_type):
    if channel_type == "telegram" and not settings.TELEGRAM_ENABLED:
        return None
    if channel_type == "whatsapp" and not settings.WHATSAPP_ENABLED:
        return None
    if channel_type not in {"telegram", "whatsapp"}:
        return None
    channels = BotChannel.objects.select_related("bot").filter(
        bot__business=business, bot__status=Bot.Statuses.ACTIVE,
        channel=channel_type, status=BotChannel.Statuses.ACTIVE,
    ).exclude(bot__settings_json__has_key="_deleted_at").order_by("-updated_at", "-pk")
    for channel in channels:
        config = channel.config_json or {}
        if channel_type == "whatsapp" and (config.get("provider_mode") != "meta_cloud" or not (config.get("phone_number_id") or channel.external_id)):
            continue
        if _has_usable_credential(channel, "bot_token" if channel_type == "telegram" else "access_token"):
            return channel
    return None


def email_delivery_configured():
    backend = str(settings.EMAIL_BACKEND)
    return backend not in {
        "django.core.mail.backends.console.EmailBackend", "django.core.mail.backends.locmem.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend", "django.core.mail.backends.dummy.EmailBackend",
    } and bool(settings.EMAIL_HOST)


def available_appointment_channels(business):
    result = ["auto", "system"]
    result.extend(channel for channel in ("telegram", "whatsapp") if active_delivery_channel(business, channel))
    if email_delivery_configured():
        result.append("email")
    return result


def preferred_client_delivery_channel(client):
    if client.telegram_id and active_delivery_channel(client.business, "telegram"):
        return "telegram"
    if client.whatsapp_id and active_delivery_channel(client.business, "whatsapp"):
        return "whatsapp"
    if client.email and email_delivery_configured():
        return "email"
    return "system"
