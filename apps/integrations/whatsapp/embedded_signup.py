import json
import hashlib
import re
from datetime import timedelta
from uuid import uuid4
from urllib import parse, request as urllib_request
from urllib.error import URLError

from django.conf import settings
from django.core import signing
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone

from apps.bots.models import Bot, BotChannel
from apps.bots.lifecycle import ensure_bot_channel
from apps.businesses.access import Actions, Resources, assert_can
from apps.core.production_rules import is_safe_public_https_url
from apps.integrations.models import BusinessConnector, WhatsAppSignupAttempt
from apps.integrations.channel_boundary import current_channel_setup, lock_channel_for_setup
from apps.integrations.connectors import create_or_update_credential
from apps.integrations.whatsapp.signup_graph import activate_signup_number, validate_signup_assets
from apps.integrations.whatsapp_credentials import get_whatsapp_connector, store_whatsapp_access_token


SIGNING_SALT = "zani.whatsapp.embedded-signup"


def build_embedded_signup_state(*, business, user, redirect_uri, bot_channel=None, onboarding_mode="cloud", expected_phone=""):
    if onboarding_mode not in {"cloud", "coexistence"}:
        raise ValueError("Unsupported WhatsApp onboarding mode.")
    if onboarding_mode == "coexistence" and not re.fullmatch(r"\+[1-9][0-9]{7,14}", expected_phone):
        raise ValueError("An international Business App number is required.")
    channel = resolve_embedded_signup_channel(business=business, state_payload={"bot_channel_id": bot_channel.pk if bot_channel else None})
    with transaction.atomic():
        channel = lock_channel_for_setup(channel)
        channel.signup_attempts.filter(consumed_at__isnull=True).update(consumed_at=timezone.now(), finished_at=timezone.now())
        attempt = WhatsAppSignupAttempt.objects.create(
            channel=channel, user=user, channel_revision=channel.updated_at,
            channel_fingerprint=_channel_fingerprint(channel),
        )
    return signing.dumps(
        {
            "business_id": business.id,
            "user_id": user.id,
            "redirect_uri": redirect_uri,
            "bot_channel_id": channel.pk,
            "attempt_id": str(attempt.pk),
            "onboarding_mode": onboarding_mode,
            "expected_phone": expected_phone if onboarding_mode == "coexistence" else "",
            "iat": timezone.now().isoformat(),
        },
        salt=SIGNING_SALT,
    )


def load_embedded_signup_state(state, max_age=1800):
    try:
        return signing.loads(state, salt=SIGNING_SALT, max_age=max_age)
    except signing.BadSignature as exc:
        raise ValueError("WhatsApp signup state is invalid or expired.") from exc


def build_embedded_signup_url(*, business, user, redirect_uri, bot_channel=None, onboarding_mode="cloud", expected_phone=""):
    state = build_embedded_signup_state(business=business, user=user, redirect_uri=redirect_uri, bot_channel=bot_channel,
                                       onboarding_mode=onboarding_mode, expected_phone=expected_phone)
    params = {
        "client_id": settings.META_APP_ID,
        "redirect_uri": redirect_uri,
        "state": state,
        "response_type": "code",
        "scope": "whatsapp_business_management,whatsapp_business_messaging",
    }
    if settings.WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID:
        params["config_id"] = settings.WHATSAPP_EMBEDDED_SIGNUP_CONFIG_ID
    return f"{settings.WHATSAPP_EMBEDDED_SIGNUP_LOGIN_URL}?{parse.urlencode(params)}", state


def exchange_code_for_access_token(*, code, redirect_uri):
    if not settings.META_APP_ID or not settings.META_APP_SECRET:
        raise ValueError("META_APP_ID and META_APP_SECRET must be configured.")
    url = _graph_url(
        "oauth/access_token",
        {
            "client_id": settings.META_APP_ID,
            "client_secret": settings.META_APP_SECRET,
            "code": code,
        },
    )
    with urllib_request.urlopen(url, timeout=15) as response:
        return json.loads(response.read().decode("utf-8"))


def resolve_embedded_signup_channel(*, business, state_payload):
    channel_id = state_payload.get("bot_channel_id")
    if channel_id:
        channel = BotChannel.objects.select_related("bot").filter(
            id=channel_id,
            bot__business=business,
            channel=BotChannel.Channels.WHATSAPP,
        ).first()
        if channel is None:
            raise ValueError("The selected WhatsApp channel is no longer available.")
        return channel

    bot = Bot.objects.filter(business=business).order_by("id").first()
    if bot is None:
        bot = Bot.objects.create(business=business, name="WhatsApp bot", status=Bot.Statuses.DRAFT, default_language="ru", settings_json={})
    channel, _ = ensure_bot_channel(
        bot=bot,
        channel_type=BotChannel.Channels.WHATSAPP,
    )
    return channel


def complete_embedded_signup(*, business, user, code, state, redirect_uri, phone_number_id, waba_id="", display_phone_number="", registration_pin=""):
    state_payload = load_embedded_signup_state(state)
    if state_payload["business_id"] != business.id or state_payload["user_id"] != user.id:
        raise ValueError("WhatsApp embedded signup state does not match the current user or business.")
    if state_payload.get("redirect_uri") != redirect_uri:
        raise ValueError("WhatsApp embedded signup redirect_uri mismatch.")
    coexistence = state_payload.get("onboarding_mode") == "coexistence"
    if not waba_id or (not coexistence and (not phone_number_id or len(registration_pin) != 6 or not registration_pin.isascii() or not registration_pin.isdigit())):
        raise ValueError("A phone number, WhatsApp account and six-digit PIN are required.")
    channel = resolve_embedded_signup_channel(business=business, state_payload=state_payload)
    attempt = _claim_attempt(channel, user, state_payload)
    try:
        token_payload = exchange_code_for_access_token(code=code, redirect_uri=redirect_uri)
        if not isinstance(token_payload, dict):
            raise ValueError("Meta returned an invalid token response.")
        access_token = token_payload.get("access_token", "")
        if not isinstance(access_token, str) or not access_token:
            raise ValueError("Meta did not return an access token.")
        options = {"coexistence": True, "expected_phone": state_payload.get("expected_phone", "")} if coexistence else {}
        phone, expires_at = validate_signup_assets(access_token, phone_number_id, waba_id, **options)
        if coexistence:
            phone_number_id = str(phone["id"])
        _reserve_phone(channel, attempt, phone_number_id)
        activate_signup_number(access_token, phone_number_id, waba_id, registration_pin, coexistence=coexistence)
        return _save_connection(channel, attempt, user, access_token, expires_at, phone_number_id, waba_id, phone["display_phone_number"],
                                registration_pin, coexistence=coexistence)
    except (URLError, OSError, TypeError, KeyError, AttributeError) as exc:
        raise ValueError("WhatsApp connection could not be completed. Restart setup.") from exc
    finally:
        WhatsAppSignupAttempt.objects.filter(pk=attempt.pk).update(finished_at=timezone.now())


def _claim_attempt(channel, user, payload):
    with transaction.atomic():
        current = lock_channel_for_setup(channel)
        attempt = WhatsAppSignupAttempt.objects.select_for_update().filter(
            pk=payload.get("attempt_id"), channel=current, user=user, consumed_at__isnull=True,
        ).first()
        if attempt is None or attempt.channel_revision != current.updated_at or attempt.channel_fingerprint != _channel_fingerprint(current):
            raise ValueError("WhatsApp setup has changed or this attempt was already used.")
        current.signup_attempts.filter(
            consumed_at__lt=timezone.now() - timedelta(minutes=30), finished_at__isnull=True,
        ).update(finished_at=timezone.now())
        if current.signup_attempts.filter(consumed_at__isnull=False, finished_at__isnull=True).exists():
            raise ValueError("WhatsApp setup is already running.")
        attempt.consumed_at = timezone.now()
        attempt.save(update_fields=["consumed_at"])
        return attempt


def _reserve_phone(channel, attempt, phone_number_id):
    try:
        with current_channel_setup(channel) as current:
            _assert_attempt_running(attempt, current)
            if BotChannel.objects.filter(channel=BotChannel.Channels.WHATSAPP).exclude(pk=current.pk).filter(
                Q(external_id=phone_number_id) | Q(config_json__phone_number_id=phone_number_id)
            ).exists():
                raise ValueError("This phone number is already connected to another channel.")
            WhatsAppSignupAttempt.objects.filter(channel=current, phone_number_id=phone_number_id).update(phone_number_id=None)
            attempt.phone_number_id = phone_number_id
            attempt.save(update_fields=["phone_number_id"])
    except IntegrityError as exc:
        raise ValueError("This phone number is already being connected.") from exc


def _save_connection(channel, attempt, user, access_token, expires_at, phone_number_id, waba_id, display_phone_number, registration_pin, *, coexistence=False):
    with current_channel_setup(channel) as channel:
        _assert_attempt_running(attempt, channel)
        user.refresh_from_db()
        if not user.is_active:
            raise ValueError("The account is no longer active.")
        assert_can(user, channel.bot.business, Resources.INTEGRATIONS, Actions.MANAGE)
        channel.status = BotChannel.Statuses.ACTIVE
        channel.external_id = phone_number_id
        channel.config_json = {
            "provider_mode": "meta_cloud",
            "phone_number_id": phone_number_id,
            "access_token_configured": True,
            "business_account_id": waba_id,
            "display_phone_number": display_phone_number,
            "embedded_signup": True,
            "onboarding_mode": "coexistence" if coexistence else "cloud",
            "setup_revision": uuid4().hex,
            "connection_verified": True,
        }
        channel.save(update_fields=["status", "external_id", "config_json", "updated_at"])
        store_whatsapp_access_token(channel, access_token, expires_at=expires_at)
        connector = get_whatsapp_connector(channel)
        if not coexistence:
            create_or_update_credential(connector, "registration_pin", registration_pin)
        else:
            connector.credentials.filter(key="registration_pin").delete()
        safe_config = dict(connector.config_json or {})
        safe_config.update(
            {
                "bot_channel_id": channel.id,
                "provider_mode": "meta_cloud",
                "phone_number_id_configured": True,
                "access_token_configured": True,
                "business_account_id_configured": bool(waba_id),
                "embedded_signup": True,
                "last_operation": "embedded_signup_complete",
            }
        )
        connector.status = BusinessConnector.Statuses.CONNECTED
        connector.capability = BusinessConnector.Capabilities.COMMUNICATIONS
        connector.auth_type = BusinessConnector.AuthTypes.OAUTH
        connector.config_json = safe_config
        connector.last_error = ""
        connector.connected_at = connector.connected_at or timezone.now()
        connector.save(update_fields=["status", "capability", "auth_type", "config_json", "last_error", "connected_at", "updated_at"])
        WhatsAppSignupAttempt.objects.filter(channel=channel).exclude(pk=attempt.pk).update(phone_number_id=None)
        WhatsAppSignupAttempt.objects.filter(pk=attempt.pk).update(succeeded=True)
        if coexistence:
            from apps.integrations.models import WhatsAppCoexistenceSync
            from apps.integrations.tasks import start_whatsapp_coexistence_sync
            sync = WhatsAppCoexistenceSync.objects.create(channel=channel, setup_revision=channel.config_json["setup_revision"],
                                                         phone_number_id=phone_number_id, waba_id=waba_id)
            transaction.on_commit(lambda: start_whatsapp_coexistence_sync.delay(sync.pk))
        return channel, connector


def _channel_fingerprint(channel):
    snapshot = [channel.bot_id, channel.channel, channel.status, channel.external_id, channel.config_json]
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True).encode()).hexdigest()


def _assert_attempt_running(attempt, channel):
    if attempt.channel_fingerprint != _channel_fingerprint(channel) or not WhatsAppSignupAttempt.objects.filter(
        pk=attempt.pk, consumed_at__isnull=False, finished_at__isnull=True,
    ).exists():
        raise ValueError("WhatsApp setup attempt is no longer current.")


def validate_signup_phone_number(access_token, phone_number_id):
    url = _graph_url(parse.quote(phone_number_id, safe=""), {"fields": "id,display_phone_number"})
    request = urllib_request.Request(url, headers={"Authorization": f"Bearer {access_token}"}, method="GET")
    try:
        with urllib_request.urlopen(request, timeout=15) as response:
            payload = json.loads(response.read().decode("utf-8"))
        valid = isinstance(payload, dict) and str(payload.get("id")) == phone_number_id and bool(payload.get("display_phone_number"))
    except (URLError, ValueError, TypeError) as exc:
        raise ValueError("The selected WhatsApp phone number could not be verified.") from exc
    if not valid:
        raise ValueError("The selected WhatsApp phone number could not be verified.")


def _graph_url(edge, params):
    base = str(settings.WHATSAPP_GRAPH_BASE_URL or "").strip().rstrip("/")
    if not is_safe_public_https_url(base):
        raise ValueError("WHATSAPP_GRAPH_BASE_URL must be a public HTTPS URL.")
    version = settings.WHATSAPP_GRAPH_API_VERSION.strip("/")
    return f"{base}/{version}/{edge}?{parse.urlencode(params)}"
