"""Per-device JWT tracking and revocation; account-wide epochs remain authoritative."""
from datetime import datetime, timedelta, timezone as dt_timezone
from ipaddress import ip_address
from uuid import UUID

from django.conf import settings
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccountSession, User


def _request_metadata(request):
    if request is None:
        return {"user_agent": "", "ip_address": None}
    # REMOTE_ADDR is the directly observed peer; do not trust arbitrary forwarded IPs.
    try:
        address = str(ip_address(request.META.get("REMOTE_ADDR", "")))
    except ValueError:
        address = None
    return {"user_agent": str(request.META.get("HTTP_USER_AGENT", ""))[:512], "ip_address": address}


def attach_device_session(user, refresh, request=None):
    if not settings.AUTH_DEVICE_SESSIONS_ENABLED:
        return
    session = AccountSession.objects.create(
        user=user, auth_epoch=user.auth_epoch, refresh_jti=refresh["jti"],
        last_seen_at=timezone.now(),
        expires_at=datetime.fromtimestamp(refresh["exp"], tz=dt_timezone.utc),
        **_request_metadata(request),
    )
    refresh["sid"] = str(session.pk)
    # for_user() saves before custom claims are attached. Persist the final token.
    OutstandingToken.objects.filter(jti=refresh["jti"]).update(token=str(refresh))


def active_device_session(user, token, *, lock=False):
    sid = token.payload.get("sid")
    if not sid:
        return None  # Pre-rollout access is governed by auth_epoch until expiry.
    try:
        sid = UUID(str(sid))
    except (ValueError, TypeError, AttributeError):
        raise TokenError("Invalid device session.") from None
    query = AccountSession.objects.filter(
        pk=sid, user=user, auth_epoch=user.auth_epoch,
        revoked_at__isnull=True, expires_at__gt=timezone.now(),
    )
    if lock:
        query = query.select_for_update()
    session = query.first()
    if session is None:
        raise TokenError("Device session is no longer active.")
    return session


def validate_access_device(user, token):
    # Once a sid is present, never bypass its revocation check even if rollout is disabled.
    if not token.payload.get("sid"):
        return
    session = active_device_session(user, token)
    if session.last_seen_at < timezone.now() - timedelta(minutes=1):
        AccountSession.objects.filter(pk=session.pk, revoked_at__isnull=True).update(last_seen_at=timezone.now())


@transaction.atomic
def refresh_browser_session(request, data, serializer):
    from apps.accounts.mfa import requires_mfa
    from apps.accounts.session_security import token_matches_auth_epoch

    raw = data.get("refresh")
    if not raw:
        serializer.is_valid(raise_exception=True)
        return serializer.validated_data
    refresh = RefreshToken(raw)
    user = User.objects.select_for_update().filter(pk=refresh.payload.get(api_settings.USER_ID_CLAIM)).first()
    if not user or not token_matches_auth_epoch(user, refresh):
        raise TokenError("Session epoch is no longer valid.")
    if requires_mfa(user) and not refresh.payload.get("mfa_verified"):
        raise TokenError("MFA verification is required.")
    session = active_device_session(user, refresh, lock=True)
    # Recheck blacklist after acquiring the user lock; concurrent rotation must not fork.
    refresh = RefreshToken(raw)
    if session is None and settings.AUTH_DEVICE_SESSIONS_ENABLED:
        attach_device_session(user, refresh, request)
        serializer.initial_data["refresh"] = str(refresh)
        session = active_device_session(user, refresh, lock=True)
    serializer.is_valid(raise_exception=True)
    result = dict(serializer.validated_data)
    if session:
        rotated = RefreshToken(result.get("refresh", str(refresh)))
        session.refresh_jti = rotated["jti"]
        session.expires_at = datetime.fromtimestamp(rotated["exp"], tz=dt_timezone.utc)
        session.last_seen_at = timezone.now()
        session.save(update_fields=["refresh_jti", "expires_at", "last_seen_at"])
    return result


def device_session_list(user, token):
    if not settings.AUTH_DEVICE_SESSIONS_ENABLED:
        return {"available": False, "sessions": [], "legacy_count": 0}
    sessions = AccountSession.objects.filter(user=user, auth_epoch=user.auth_epoch, revoked_at__isnull=True, expires_at__gt=timezone.now()).order_by("-last_seen_at")
    items = list(sessions)
    legacy_count = OutstandingToken.objects.filter(user=user, expires_at__gt=timezone.now(), blacklistedtoken__isnull=True).exclude(jti__in=[item.refresh_jti for item in items]).count()
    current = str(token.get("sid", "")) if token else ""
    return {"available": True, "legacy_count": legacy_count, "sessions": [
        {"id": str(item.pk), "user_agent": item.user_agent, "ip_address": item.ip_address,
         "created_at": item.created_at, "last_seen_at": item.last_seen_at, "is_current": str(item.pk) == current}
        for item in items
    ]}


@transaction.atomic
def revoke_device_session(request, session_id, *, code=""):
    from apps.accounts.auth_views import record_security_event
    from apps.accounts.mfa import has_confirmed_mfa, verify_user_factor

    if not settings.AUTH_DEVICE_SESSIONS_ENABLED:
        raise NotFound()
    user = User.objects.select_for_update().get(pk=request.user.pk)
    session = AccountSession.objects.select_for_update().filter(pk=session_id, user=user).first()
    if session is None:
        raise NotFound()
    if request.auth and str(request.auth.get("sid", "")) == str(session.pk):
        raise ValidationError({"detail": "Use sign out to end the current session."})
    if session.revoked_at is not None:
        return  # Idempotent for an already-revoked own session.
    if has_confirmed_mfa(user) and not verify_user_factor(user, code, allow_recovery=True):
        raise ValidationError({"code": "The verification code is invalid."})
    session.revoked_at = timezone.now()
    session.save(update_fields=["revoked_at"])
    outstanding = OutstandingToken.objects.filter(user=user, jti=session.refresh_jti).first()
    if outstanding:
        BlacklistedToken.objects.get_or_create(token=outstanding)
    record_security_event(request, user=user, event="device_session_revoked", sessions_revoked=1, metadata={"session_id": str(session.pk)})
