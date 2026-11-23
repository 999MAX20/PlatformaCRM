import base64
import hashlib
import secrets
import uuid
from datetime import timedelta
from urllib.parse import urlencode, urlsplit

from django.conf import settings
from django.core import signing
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog
from apps.integrations.credential_encryption import encrypt_credential_value, decrypt_credential_value
from apps.integrations.google_http import GoogleError, google_request
from apps.integrations.google_models import GoogleConnection, GoogleOAuthAttempt


SHEETS_SCOPE = "https://www.googleapis.com/auth/drive.file"
CALENDAR_SCOPES = (
    "https://www.googleapis.com/auth/calendar.calendarlist.readonly",
    "https://www.googleapis.com/auth/calendar.events",
)
SCOPES = {
    "google_sheets": ("openid", "email", SHEETS_SCOPE),
    "google_calendar": ("openid", "email", *CALENDAR_SCOPES),
}
SALT = "platforma.google.integration"


def assert_access(actor, business):
    assert_can(actor, business, Resources.INTEGRATIONS, Actions.MANAGE)
    assert_resource_enabled(business, Resources.INTEGRATIONS)


def configuration():
    client = settings.GOOGLE_INTEGRATION_CLIENT_ID
    secret = settings.GOOGLE_INTEGRATION_CLIENT_SECRET
    redirect = settings.GOOGLE_INTEGRATION_REDIRECT_URI
    parts = urlsplit(redirect)
    local = settings.DEBUG and parts.hostname in {"localhost", "127.0.0.1"} and parts.scheme == "http"
    if not client or not secret or not parts.netloc or not (parts.scheme == "https" or local) or parts.fragment or parts.username:
        raise ValidationError("Google integration is not configured.")
    return client, secret, redirect


def status(connection):
    return {"id": connection.pk, "provider": connection.provider, "status": connection.status,
            "email": connection.email, "last_sync_at": connection.last_sync_at}


@transaction.atomic
def start(*, actor, business, provider="google_sheets"):
    assert_access(actor, business)
    if provider not in SCOPES:
        raise ValidationError("This Google connector is not available yet.")
    if provider == "google_calendar" and not settings.GOOGLE_CALENDAR_ENABLED:
        raise ValidationError("Google Calendar synchronization is not enabled.")
    client, _, redirect = configuration()
    connection, _ = GoogleConnection.objects.get_or_create(business=business, actor=actor, provider=provider)
    connection = GoogleConnection.objects.select_for_update().get(pk=connection.pk)
    connection.revision = uuid.uuid4()
    connection.save(update_fields=["revision", "updated_at"])
    verifier = secrets.token_urlsafe(64)
    attempt = GoogleOAuthAttempt.objects.create(connection=connection, revision=connection.revision,
        encrypted_verifier=encrypt_credential_value(verifier), redirect_uri=redirect)
    state = signing.dumps({"attempt": str(attempt.pk), "actor": actor.pk, "business": business.pk}, salt=SALT)
    challenge = base64.urlsafe_b64encode(hashlib.sha256(verifier.encode()).digest()).rstrip(b"=").decode()
    return {"authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode({
        "client_id": client, "redirect_uri": redirect, "response_type": "code", "scope": " ".join(SCOPES[provider]),
        "state": state, "code_challenge": challenge, "code_challenge_method": "S256",
        "access_type": "offline", "prompt": "consent select_account", "include_granted_scopes": "false"})}


def complete(*, actor, code, state):
    try:
        data = signing.loads(state, salt=SALT, max_age=600)
        attempt_id = uuid.UUID(data["attempt"])
        if data["actor"] != actor.pk:
            raise ValueError()
    except (signing.BadSignature, KeyError, TypeError, ValueError):
        raise ValidationError("Google connection attempt expired or is invalid.") from None
    with transaction.atomic():
        attempt = GoogleOAuthAttempt.objects.select_for_update().select_related("connection__business").filter(pk=attempt_id).first()
        if not attempt or attempt.connection.actor_id != actor.pk or attempt.connection.business_id != data["business"]:
            raise NotFound()
        connection = GoogleConnection.objects.select_for_update().get(pk=attempt.connection_id)
        assert_access(actor, connection.business)
        if connection.provider == "google_calendar" and not settings.GOOGLE_CALENDAR_ENABLED:
            raise ValidationError("Google Calendar synchronization is not enabled.")
        if attempt.consumed_at or attempt.revision != connection.revision or attempt.created_at < timezone.now() - timedelta(minutes=10):
            raise ValidationError("Start a new Google connection attempt.")
        attempt.consumed_at = timezone.now()
        attempt.save(update_fields=["consumed_at"])
    # Consume before contacting Google: an ambiguous exchange cannot replay a code.
    client, secret, redirect = configuration()
    if redirect != attempt.redirect_uri:
        raise ValidationError("Google configuration changed. Connect again.")
    tokens = google_request("https://oauth2.googleapis.com/token", method="POST", form=True, payload={
        "client_id": client, "client_secret": secret, "code": code, "redirect_uri": redirect,
        "grant_type": "authorization_code", "code_verifier": decrypt_credential_value(attempt.encrypted_verifier)})
    access, refresh = tokens.get("access_token"), tokens.get("refresh_token")
    scopes = str(tokens.get("scope", "")).split()
    required_scopes = set(SCOPES[connection.provider]) - {"openid", "email"}
    if not access or not refresh or not required_scopes.issubset(scopes):
        raise ValidationError("Google did not grant the required offline access. Connect again and allow access.")
    identity = google_request("https://openidconnect.googleapis.com/v1/userinfo", token=access)
    if not identity.get("sub") or not identity.get("email") or identity.get("email_verified") is not True:
        raise ValidationError("Google account identity could not be verified.")
    with transaction.atomic():
        connection = GoogleConnection.objects.select_for_update().get(pk=connection.pk)
        assert_access(actor, connection.business)
        if connection.revision != attempt.revision:
            raise ValidationError("Google connection changed. Connect again.")
        if connection.subject and connection.subject != identity["sub"]:
            raise ValidationError("Reconnect the same Google account used for this connection.")
        connection.subject, connection.email = identity["sub"], identity["email"]
        connection.encrypted_refresh = encrypt_credential_value(refresh)
        connection.encrypted_access = encrypt_credential_value(access)
        connection.access_expires_at = timezone.now() + timedelta(seconds=min(int(tokens.get("expires_in", 3600)), 3600))
        connection.scopes, connection.status = scopes, "connected"
        connection.save()
        audit(connection, actor, "google_connected")
    return status(connection)


def audit(connection, actor, kind):
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=connection,
                         business=connection.business, metadata={"kind": kind, "provider": connection.provider})


def access_token(connection, actor):
    error = None
    with transaction.atomic():
        connection = GoogleConnection.objects.select_for_update().get(pk=connection.pk, actor=actor)
        assert_access(actor, connection.business)
        if connection.status != "connected" or not connection.encrypted_refresh:
            raise ValidationError("Reconnect Google to continue.")
        if connection.access_expires_at and connection.access_expires_at > timezone.now() + timedelta(seconds=90):
            return decrypt_credential_value(connection.encrypted_access)
        client, secret, _ = configuration()
        try:
            tokens = google_request("https://oauth2.googleapis.com/token", method="POST", form=True, payload={
                "client_id": client, "client_secret": secret, "grant_type": "refresh_token",
                "refresh_token": decrypt_credential_value(connection.encrypted_refresh)})
            token = tokens.get("access_token")
            if not token:
                raise GoogleError()
            connection.encrypted_access = encrypt_credential_value(token)
            connection.access_expires_at = timezone.now() + timedelta(seconds=min(int(tokens.get("expires_in", 3600)), 3600))
            connection.save(update_fields=["encrypted_access", "access_expires_at", "updated_at"])
        except GoogleError as exc:
            error = exc
            if exc.revoked:
                connection.status = "expired_credentials"
                connection.save(update_fields=["status", "updated_at"])
    if error:
        raise error
    return token


@transaction.atomic
def disconnect(connection, actor):
    connection = GoogleConnection.objects.select_for_update().get(pk=connection.pk, actor=actor)
    assert_access(actor, connection.business)
    revoked = True
    if connection.encrypted_refresh:
        try:
            google_request("https://oauth2.googleapis.com/revoke", method="POST", form=True,
                payload={"token": decrypt_credential_value(connection.encrypted_refresh)})
        except GoogleError:
            # Local disconnection must still succeed while Google is unavailable.
            revoked = False
    connection.revision = uuid.uuid4()
    connection.status = "disconnected"
    connection.encrypted_access = connection.encrypted_refresh = ""
    connection.access_expires_at = None
    connection.save()
    audit(connection, actor, "google_disconnected")
    return {**status(connection), "google_revoked": revoked}
