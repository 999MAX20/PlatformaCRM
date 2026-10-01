from django.db import transaction
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.settings import api_settings
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken, OutstandingToken
from rest_framework_simplejwt.tokens import RefreshToken

from apps.accounts.models import AccountSession, User


def token_matches_auth_epoch(user, token):
    """Return whether a JWT belongs to the user's current revocation epoch."""
    try:
        token_epoch = int(token.payload.get("auth_epoch"))
    except (TypeError, ValueError):
        return False
    return token_epoch == int(user.auth_epoch)


@transaction.atomic
def blacklist_refresh_token(raw_token):
    """End the presented browser session without signing out other devices."""
    if not raw_token:
        return None, False

    try:
        refresh = RefreshToken(raw_token)
    except TokenError:
        return None, False

    user_id = refresh.payload.get(api_settings.USER_ID_CLAIM)
    user = None
    if user_id is not None:
        user = User.objects.filter(**{api_settings.USER_ID_FIELD: user_id}).first()

    if user is None:
        _, created = refresh.blacklist()
        return None, int(created)

    user = User.objects.select_for_update().get(pk=user.pk)
    sid = refresh.payload.get("sid")
    if sid:
        session = AccountSession.objects.select_for_update().filter(
            pk=sid, user=user, auth_epoch=user.auth_epoch, revoked_at__isnull=True,
        ).first()
        if session is None:
            return user, 0
        session.revoked_at = timezone.now()
        session.save(update_fields=["revoked_at"])
        outstanding = OutstandingToken.objects.filter(user=user, jti=session.refresh_jti).first()
        if outstanding:
            BlacklistedToken.objects.get_or_create(token=outstanding)
        return user, 1
    # Old, untracked credentials retain the established immediate-revocation
    # guarantee. A refresh upgrades them before normal browser use.
    return user, revoke_user_refresh_sessions(user)


@transaction.atomic
def revoke_user_refresh_sessions(user):
    """Blacklist refresh sessions and advance the epoch checked by every JWT."""
    locked_user = User.objects.select_for_update().get(pk=user.pk)
    tokens = list(
        OutstandingToken.objects.select_for_update()
        .filter(user=locked_user, expires_at__gt=timezone.now(), blacklistedtoken__isnull=True)
        .only("id")
    )
    BlacklistedToken.objects.bulk_create(
        [BlacklistedToken(token=token) for token in tokens],
        ignore_conflicts=True,
    )
    locked_user.auth_epoch += 1
    locked_user.save(update_fields=["auth_epoch"])
    user.auth_epoch = locked_user.auth_epoch
    return len(tokens)


@transaction.atomic
def update_password_and_revoke_sessions(user, password, *, issue_replacement=False):
    """Change a password and revoke prior refresh sessions as one transaction."""
    user.set_password(password)
    user.save(update_fields=["password"])
    revoked_sessions = revoke_user_refresh_sessions(user)
    replacement = RefreshToken.for_user(user) if issue_replacement else None
    if replacement is not None:
        replacement["auth_epoch"] = int(user.auth_epoch)
    return revoked_sessions, replacement
