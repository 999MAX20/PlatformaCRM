from datetime import datetime, timezone as datetime_timezone
from uuid import uuid4
import re

from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime
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
def start(channel, actor, *, onboarding_type=YCloudConnection.OnboardingTypes.PLATFORM, expected_phone_number=""):
    channel = lock_channel_for_setup(channel)
    actor = _current_actor(channel, actor)
    if onboarding_type not in YCloudConnection.OnboardingTypes.values:
        raise ValidationError({"onboarding_type": "Choose a supported connection method."})
    if not isinstance(expected_phone_number, str):
        raise ValidationError({"expected_phone_number": "Use an international phone number."})
    expected_phone_number = expected_phone_number.strip()
    if (expected_phone_number and not re.fullmatch(r"\+[1-9][0-9]{7,14}", expected_phone_number)) or (
        onboarding_type == YCloudConnection.OnboardingTypes.APP and not expected_phone_number
    ):
        raise ValidationError({"expected_phone_number": "Use an international phone number, for example +77010000000."})
    if (channel.channel != "whatsapp" or channel.status == "active" or channel.external_id
            or (channel.config_json or {}).get("connection_verified")):
        raise ValidationError("Use an inactive WhatsApp channel for onboarding.")
    connection = YCloudConnection.objects.filter(channel=channel).first()
    if connection and (connection.waba_id or connection.expires_at > timezone.now()):
        raise ValidationError("A connection already exists or signup is still pending.")
    # Stable for this attempt; rotate on expiry so an old link cannot bind a new attempt.
    revision = uuid4().hex
    customer_id = uuid4()
    result = client.create_link(customer_id, onboarding_type)
    try:
        raw_expiry = result["expiresAt"]
        if isinstance(raw_expiry, str) and not raw_expiry.isdecimal():
            expiry = datetime.fromisoformat(raw_expiry)
        else:
            expiry = datetime.fromtimestamp(int(raw_expiry) / 1000, tz=datetime_timezone.utc)
    except (KeyError, ValueError, TypeError, OSError, OverflowError):
        raise client.YCloudError("invalid_provider_response") from None
    if timezone.is_naive(expiry) or expiry <= timezone.now() or expiry > timezone.now() + timezone.timedelta(hours=3):
        raise client.YCloudError("invalid_provider_response")
    channel.config_json = {"provider_mode": "ycloud", "setup_revision": revision, "connection_verified": False}
    channel.status = BotChannel.Statuses.DRAFT
    channel.external_id = ""
    channel.save(update_fields=["config_json", "status", "external_id", "updated_at"])
    connection, _ = YCloudConnection.objects.update_or_create(channel=channel, defaults={
        "customer_id": customer_id, "initiated_by": actor, "setup_revision": revision,
        "expires_at": expiry, "status": "pending", "last_error": "",
        "onboarding_type": onboarding_type, "expected_phone_number": expected_phone_number,
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
def confirm(connection, account, *, event_time=None):
    channel = lock_channel_for_setup(connection.channel)
    connection = YCloudConnection.objects.select_for_update().select_related("initiated_by").get(pk=connection.pk)
    actor = _current_actor(channel, connection.initiated_by)
    if (channel.config_json or {}).get("setup_revision") != connection.setup_revision:
        raise client.YCloudError("setup_changed")
    if connection.status == "connected":
        if connection.waba_id != account.get("id"):
            raise client.YCloudError("binding_conflict")
        return
    if connection.status != "pending":
        raise client.YCloudError("setup_changed")
    if connection.expires_at <= (event_time or timezone.now()):
        raise client.YCloudError("signup_expired")
    if account.get("paymentMethodAttached") is not True:
        raise client.YCloudError("payment_not_attached", retryable=True)
    waba_id = str(account.get("id") or "")
    if not waba_id:
        raise client.YCloudError("invalid_provider_response")
    number = client.connected_number(waba_id)
    if connection.expected_phone_number and number["phoneNumber"] != connection.expected_phone_number:
        raise client.YCloudError("phone_number_mismatch")
    if not str(number["phoneNumber"]).startswith("+"):
        raise client.YCloudError("invalid_provider_response")
    connection.waba_id = waba_id
    connection.phone_id = str(number["id"])
    connection.phone_number = number["phoneNumber"]
    connection.status = "connected"
    connection.last_error = ""
    connection.save()
    channel.config_json.update({"phone_number_id": connection.phone_id, "business_account_id": waba_id,
        "display_phone_number": connection.phone_number, "connection_verified": True,
        "binding_event_time": (event_time or timezone.now()).isoformat()})
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


def apply_partner_removal(connection, account, event_time):
    channel = lock_channel_for_setup(connection.channel)
    if (connection.status != "connected" or connection.waba_id != account.get("id")
            or (channel.config_json or {}).get("setup_revision") != connection.setup_revision
            or (channel.config_json or {}).get("provider_mode") != "ycloud"):
        return
    connector = get_whatsapp_connector(channel)
    binding_time = parse_datetime(channel.config_json.get("binding_event_time", "")) or connector.connected_at
    if not binding_time or not event_time or event_time <= binding_time:
        return
    revision = uuid4().hex
    connection.status = "disconnected"
    connection.setup_revision = revision
    connection.customer_id = uuid4()
    connection.expires_at = timezone.now()
    connection.waba_id = connection.phone_id = connection.phone_number = connection.last_error = ""
    connection.save()
    channel.config_json = {"provider_mode": "ycloud", "setup_revision": revision, "connection_verified": False}
    channel.external_id = ""
    channel.status = BotChannel.Statuses.DRAFT
    channel.save(update_fields=["config_json", "external_id", "status", "updated_at"])
    connector.status = BusinessConnector.Statuses.DISCONNECTED
    connector.connected_at = None
    connector.last_error = ""
    connector.save(update_fields=["status", "connected_at", "last_error", "updated_at"])
    write_actor_audit_log(actor=None, action=AuditLog.Actions.UPDATE, instance=channel,
        business=channel.bot.business, metadata={"provider": "ycloud", "event": "partner_removed"})


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
