from datetime import datetime, timezone as datetime_timezone
from uuid import uuid4

from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.bots.models import BotChannel
from apps.integrations.channel_boundary import lock_channel_for_setup
from apps.integrations.whatsapp_credentials import get_whatsapp_connector
from apps.integrations.models import BusinessConnector
from apps.integrations.ycloud import client
from apps.integrations.ycloud.models import YCloudConnection
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog


def _current_actor(channel, actor):
    from django.contrib.auth import get_user_model

    actor = get_user_model().objects.filter(pk=getattr(actor, "pk", None), is_active=True).first()
    if actor is None:
        raise PermissionDenied("An active account is required.")
    assert_can(actor, channel.bot.business, Resources.INTEGRATIONS, Actions.MANAGE)
    return actor


@transaction.atomic
def start(channel, actor):
    channel = lock_channel_for_setup(channel)
    actor = _current_actor(channel, actor)
    if channel.channel != "whatsapp" or channel.status == "active":
        raise ValidationError("Use an inactive WhatsApp channel for onboarding.")
    connection = YCloudConnection.objects.filter(channel=channel).first()
    if connection and (connection.waba_id or connection.expires_at > timezone.now()):
        raise ValidationError("A connection already exists or signup is still pending.")
    # Stable for this attempt; rotate on expiry so an old link cannot bind a new attempt.
    revision = uuid4().hex
    customer_id = uuid4()
    result = client.create_link(customer_id)
    try:
        expiry = datetime.fromtimestamp(int(result["expiresAt"]) / 1000, tz=datetime_timezone.utc)
    except (KeyError, ValueError, TypeError, OSError, OverflowError):
        raise client.YCloudError("invalid_provider_response") from None
    if expiry <= timezone.now() or expiry > timezone.now() + timezone.timedelta(hours=3):
        raise client.YCloudError("invalid_provider_response")
    channel.config_json = {"provider_mode": "ycloud", "setup_revision": revision, "connection_verified": False}
    channel.status = BotChannel.Statuses.DRAFT
    channel.external_id = ""
    channel.save(update_fields=["config_json", "status", "external_id", "updated_at"])
    connection, _ = YCloudConnection.objects.update_or_create(channel=channel, defaults={
        "customer_id": customer_id, "initiated_by": actor, "setup_revision": revision,
        "expires_at": expiry, "status": "pending", "last_error": "",
    })
    connector = get_whatsapp_connector(channel)
    connector.config_json = {"bot_channel_id": channel.id, "provider_mode": "ycloud"}
    connector.status = BusinessConnector.Statuses.PROVIDER_CONFIGURING
    connector.auth_type = BusinessConnector.AuthTypes.TOKEN
    connector.save(update_fields=["config_json", "status", "auth_type", "updated_at"])
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=channel,
        business=channel.bot.business, metadata={"provider": "ycloud", "event": "signup_started"})
    # Never persist onboardingUrl: it contains a short-lived credential.
    return {"onboarding_url": result["onboardingUrl"], "expires_at": expiry}


@transaction.atomic
def confirm(connection, account):
    channel = lock_channel_for_setup(connection.channel)
    connection = YCloudConnection.objects.select_for_update().select_related("initiated_by").get(pk=connection.pk)
    actor = _current_actor(channel, connection.initiated_by)
    if (channel.config_json or {}).get("setup_revision") != connection.setup_revision:
        raise client.YCloudError("setup_changed")
    if connection.status == "connected":
        if connection.waba_id != account.get("id"):
            raise client.YCloudError("binding_conflict")
        return
    if connection.expires_at <= timezone.now():
        raise client.YCloudError("signup_expired")
    if account.get("paymentMethodAttached") is not True:
        raise client.YCloudError("payment_not_attached", retryable=True)
    waba_id = str(account.get("id") or "")
    if not waba_id:
        raise client.YCloudError("invalid_provider_response")
    number = client.connected_number(waba_id)
    if not str(number["phoneNumber"]).startswith("+"):
        raise client.YCloudError("invalid_provider_response")
    connection.waba_id = waba_id
    connection.phone_id = str(number["id"])
    connection.phone_number = number["phoneNumber"]
    connection.status = "connected"
    connection.last_error = ""
    connection.save()
    channel.config_json.update({"phone_number_id": connection.phone_id, "business_account_id": waba_id,
        "display_phone_number": connection.phone_number, "connection_verified": True})
    channel.external_id = connection.phone_id
    channel.status = BotChannel.Statuses.ACTIVE
    channel.save(update_fields=["config_json", "external_id", "status", "updated_at"])
    connector = get_whatsapp_connector(channel)
    connector.status = BusinessConnector.Statuses.CONNECTED
    connector.connected_at = timezone.now()
    connector.last_error = ""
    connector.save(update_fields=["status", "connected_at", "last_error", "updated_at"])
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=channel,
        business=channel.bot.business, metadata={"provider": "ycloud", "event": "signup_confirmed"})


@transaction.atomic
def recover(channel, actor, action):
    channel = lock_channel_for_setup(channel)
    actor = _current_actor(channel, actor)
    connection = YCloudConnection.objects.select_for_update().filter(channel=channel).first()
    if connection is None:
        raise ValidationError("No connection attempt.")
    if action == "cancel":
        if connection.status == "connected":
            raise ValidationError("Pause a connected channel instead.")
        connection.status, connection.last_error = "cancelled", ""
        connection.expires_at = timezone.now()
        connection.customer_id = uuid4()
        connection.save()
        channel.config_json = {"provider_mode": "ycloud", "setup_revision": uuid4().hex, "connection_verified": False}
        channel.save(update_fields=["config_json", "updated_at"])
    elif action == "retry_events":
        from apps.integrations.ycloud.models import YCloudEvent
        if (channel.config_json or {}).get("setup_revision") != connection.setup_revision:
            raise ValidationError("Channel setup changed.")
        YCloudEvent.objects.filter(connection=connection, status="failed").update(status="pending", attempts=0, next_attempt_at=timezone.now())
        connection.last_error = ""
        connection.save(update_fields=["last_error"])
    else:
        raise ValidationError("Unknown recovery action.")
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=channel,
        business=channel.bot.business, metadata={"provider": "ycloud", "event": action})
