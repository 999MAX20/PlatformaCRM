"""Verified own-account login changes. Identity and business links stay intact."""
import secrets
from datetime import timedelta
from smtplib import SMTPException

from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.exceptions import ValidationError

from apps.accounts.auth_views import record_security_event
from apps.accounts.mfa import has_confirmed_mfa, issue_session, verify_user_factor
from apps.accounts.models import EmailChangeChallenge, User
from apps.accounts.session_security import revoke_user_refresh_sessions
from apps.core.domain_errors import TemporaryServiceFailure


def _code_hash(user_id, email, code):
    return salted_hmac("accounts.email-change.v1", f"{user_id}:{email}:{code}", algorithm="sha256").hexdigest()


def _check_address(user, email):
    if email.casefold() == user.email.casefold() or User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
        raise ValidationError({"new_email": "This email cannot be used."})


@transaction.atomic
def request_email_change(request, *, new_email, current_password, mfa_code=""):
    if settings.EMAIL_BACKEND in {
        "django.core.mail.backends.console.EmailBackend",
        "django.core.mail.backends.filebased.EmailBackend",
        "django.core.mail.backends.dummy.EmailBackend",
    }:
        raise TemporaryServiceFailure("Email delivery is not configured.")
    user = User.objects.select_for_update().get(pk=request.user.pk)
    if not user.check_password(current_password):
        raise ValidationError({"current_password": "Current password is incorrect."})
    if has_confirmed_mfa(user) and not verify_user_factor(user, mfa_code, allow_recovery=True):
        raise ValidationError({"mfa_code": "The verification code is invalid."})
    email = new_email.strip().lower()
    _check_address(user, email)
    code = f"{secrets.randbelow(1_000_000):06d}"
    EmailChangeChallenge.objects.update_or_create(user=user, defaults={
        "new_email": email, "code_hash": _code_hash(user.pk, email, code),
        "auth_epoch": user.auth_epoch, "expires_at": timezone.now() + timedelta(minutes=10), "failed_attempts": 0,
    })
    # Delivery failure rolls back the pending request; no codes in API/logs.
    try:
        sent = send_mail(
            "PlatformaCRM: confirm your email",
            f"Your confirmation code: {code}\nExpires in 10 minutes.",
            settings.DEFAULT_FROM_EMAIL, [email], fail_silently=False,
            connection=get_connection(timeout=10),
        )
        if sent != 1:
            raise OSError("Delivery not accepted")
    except (SMTPException, OSError):
        raise TemporaryServiceFailure("Email delivery is unavailable. Try again later.") from None
    record_security_event(request, user=user, event="email_change_requested")
    return {"ok": True, "expires_in": 600}


def confirm_email_change(request, *, code):
    # Invalid attempts must commit before returning the validation error.
    failure = False
    with transaction.atomic():
        user = User.objects.select_for_update().get(pk=request.user.pk)
        challenge = EmailChangeChallenge.objects.select_for_update().filter(user=user).first()
        if not challenge or challenge.expires_at <= timezone.now() or challenge.failed_attempts >= 5 or challenge.auth_epoch != user.auth_epoch:
            failure = True
        elif not constant_time_compare(challenge.code_hash, _code_hash(user.pk, challenge.new_email, code)):
            challenge.failed_attempts += 1
            challenge.save(update_fields=["failed_attempts"])
            failure = True
        else:
            _check_address(user, challenge.new_email)
            try:
                with transaction.atomic():
                    user.email = challenge.new_email
                    user.save(update_fields=["email"])
            except IntegrityError:
                raise ValidationError({"new_email": "This email cannot be used."}) from None
            revoked = revoke_user_refresh_sessions(user)
            challenge.delete()
            refresh = issue_session(user, mfa_verified=has_confirmed_mfa(user), request=request)
            record_security_event(request, user=user, event="email_changed", sessions_revoked=revoked)
    if failure:
        raise ValidationError({"code": "The code is invalid or expired. Request a new code."})
    return user, refresh
