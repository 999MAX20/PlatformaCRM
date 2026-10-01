"""Server-owned limits for persistent merchant browser sessions."""
from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.exceptions import TokenError


def uses_persistent_session_policy(user):
    return user.is_merchant_user and not user.is_superuser


def session_deadline(session, *, activity_at=None):
    return min(
        (activity_at or session.last_seen_at) + timedelta(days=settings.AUTH_SESSION_IDLE_DAYS),
        session.created_at + timedelta(days=settings.AUTH_SESSION_ABSOLUTE_DAYS),
    )


def assert_session_policy(user, session):
    if uses_persistent_session_policy(user) and session_deadline(session) <= timezone.now():
        raise TokenError("Browser session has expired.")
