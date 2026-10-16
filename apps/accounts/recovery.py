"""Support-assisted recovery of a verified person's existing account."""
import hashlib
import json
import secrets
from datetime import timedelta
from smtplib import SMTPException
from urllib.parse import urlsplit

from django.conf import settings
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.core.mail import get_connection, send_mail
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.utils.crypto import constant_time_compare, salted_hmac
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.mfa import validate_step_up_token
from apps.accounts.models import AccountRecovery, EmailChangeChallenge, MfaChallenge, MfaDevice, MfaRecoveryCode, SocialIdentity, User
from apps.accounts.session_security import revoke_user_refresh_sessions
from apps.businesses.models import Business, BusinessMember
from apps.businesses.ownership import OwnershipConflict, active_actor
from apps.core.audit import write_audit_log, write_actor_audit_log
from apps.core.models import AuditLog
from apps.support.access import assert_platform_actor
from apps.support.models import SupportCase


def linked_businesses(user):
    return Business.objects.filter(Q(owner=user) | Q(members__user=user)).distinct()


def revision(user):
    snapshot = {"email": user.email, "active": user.is_active, "epoch": user.auth_epoch,
                "role": user.role, "superuser": user.is_superuser,
                "owners": list(Business.objects.filter(owner=user).order_by("pk").values_list("pk", flat=True)),
                "members": list(BusinessMember.objects.filter(user=user).order_by("pk").values(
                    "pk", "business_id", "role", "business_role_id", "is_active", "updated_at"))}
    return hashlib.sha256(json.dumps(snapshot, sort_keys=True, default=str).encode()).hexdigest()


def platform_actor(request):
    actor = active_actor(request, lock=True)
    assert_platform_actor(actor)
    validate_step_up_token(actor, request.headers.get("X-Zani-MFA-Step-Up", ""))
    return actor


def target(business, user_id, *, lock=False):
    users = User.objects.select_for_update() if lock else User.objects.all()
    user = get_object_or_404(users, pk=user_id)
    if not (business.owner_id == user.pk or BusinessMember.objects.filter(business=business, user=user, is_active=True).exists()):
        raise PermissionDenied("An active business participant is required.")
    if not user.is_active or user.is_platform_user:
        raise PermissionDenied("This account cannot be recovered through business support.")
    return user


def audit(request, item, event):
    metadata = {
        "kind": "account_recovery", "event": event, "recovery_id": str(item.pk),
        "user_id": item.user_id, "support_case_id": item.support_case_id,
        "category": AuditLog.Categories.ACCESS, "risk_level": AuditLog.RiskLevels.HIGH,
    }
    if event == "completed":
        write_actor_audit_log(actor=item.user, action=AuditLog.Actions.UPDATE, instance=item, business=item.business, metadata=metadata)
    else:
        write_audit_log(request, AuditLog.Actions.UPDATE, item, business=item.business, metadata=metadata)


def current(item, user, business):
    if item.expires_at <= timezone.now() or item.revision != revision(user) or business.owner_id != item.owner_id:
        raise OwnershipConflict()
    target(business, user.pk)
    if item.owner_required:
        owner = User.objects.get(pk=item.owner_id)
        if not owner.is_active or owner.auth_epoch != item.owner_epoch:
            raise OwnershipConflict()


def check_email(user, email):
    if email.casefold() == user.email.casefold() or User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
        raise ValidationError({"new_email": "Choose a new, available email address."})


@transaction.atomic
def prepare(request, business_id, *, user_id, support_case_id, new_email, expected_revision, reason, verified_reference=""):
    actor = platform_actor(request)
    business = get_object_or_404(Business.objects.select_for_update(), pk=business_id)
    user = target(business, user_id, lock=True)
    case = get_object_or_404(SupportCase, pk=support_case_id, business=business, requester=user)
    if case.status == "resolved":
        raise ValidationError({"support_case_id": "Reopen the support case first."})
    if expected_revision != revision(user):
        raise OwnershipConflict()
    email = new_email.strip().lower()
    check_email(user, email)
    owner = User.objects.get(pk=business.owner_id)
    owner_required = user.pk != owner.pk
    identity_required = not owner_required or linked_businesses(user).count() > 1
    if identity_required and not verified_reference.strip():
        raise ValidationError({"verified_reference": "Record the basis of identity verification against previously verified records."})
    if owner_required and not owner.is_active:
        raise ValidationError("The current owner must be able to confirm this request.")
    AccountRecovery.objects.filter(user=user, status__in=["pending", "sent"], expires_at__lte=timezone.now()).update(status="cancelled", token_hash="")
    if AccountRecovery.objects.filter(user=user, status__in=["pending", "sent"]).exists():
        raise OwnershipConflict()
    item = AccountRecovery.objects.create(business=business, user=user, support_case=case, prepared_by=actor,
        owner=owner, owner_required=owner_required, owner_epoch=owner.auth_epoch,
        identity_required=identity_required, verified_reference=verified_reference.strip(),
        new_email=email, revision=expected_revision, reason=reason,
        expires_at=timezone.now() + timedelta(hours=24))
    audit(request, item, "prepared")
    return item


def locked_item(business_id, recovery_id):
    business = get_object_or_404(Business.objects.select_for_update(), pk=business_id)
    # Every recovery path locks Business -> User -> request, matching membership writes.
    stub = get_object_or_404(AccountRecovery, pk=recovery_id, business=business)
    # Keep owner consent valid throughout completion, including concurrent epoch revocation.
    participants = {person.pk: person for person in User.objects.select_for_update().filter(
        pk__in=[stub.user_id, stub.owner_id]).order_by("pk")}
    user = participants[stub.user_id]
    item = AccountRecovery.objects.select_for_update().get(pk=stub.pk)
    return business, user, item


@transaction.atomic
def owner_decide(request, recovery_id, decision):
    actor = active_actor(request)
    stub = get_object_or_404(AccountRecovery, pk=recovery_id, owner=actor, owner_required=True)
    business, user, item = locked_item(stub.business_id, recovery_id)
    current(item, user, business)
    if item.status != "pending" or item.owner_confirmed_at:
        raise OwnershipConflict()
    if decision == "confirm":
        item.owner_confirmed_at = timezone.now()
    else:
        item.status = "declined"
    item.save(update_fields=["owner_confirmed_at", "status"])
    audit(request, item, decision)
    return item


def token_hash(raw):
    return salted_hmac("accounts.support-recovery.v1", raw, algorithm="sha256").hexdigest()


@transaction.atomic
def operate(request, business_id, recovery_id, action):
    actor = platform_actor(request)
    business, user, item = locked_item(business_id, recovery_id)
    if item.status not in ["pending", "sent"]:
        raise OwnershipConflict()
    if action == "cancel":
        item.status = "cancelled"
        item.token_hash = ""
        item.save(update_fields=["status", "token_hash"])
        audit(request, item, "cancelled")
        return item
    current(item, user, business)
    if item.support_case.status == "resolved" or (item.owner_required and not item.owner_confirmed_at):
        raise ValidationError("An open support case and owner confirmation are required.")
    check_email(user, item.new_email)
    if item.last_attempt_at and timezone.now() - item.last_attempt_at < timedelta(seconds=60):
        raise ValidationError("Wait one minute before retrying delivery.")
    raw = secrets.token_urlsafe(32)
    # A retry invalidates the preceding link even when transport subsequently fails.
    item.token_hash = ""
    item.token_expires_at = None
    item.last_attempt_at = timezone.now()
    item.delivery_status = "unavailable"
    item.status = "pending"
    base = getattr(settings, "FRONTEND_URL", "").rstrip("/")
    parsed = urlsplit(base)
    configured = bool(parsed.hostname) and not parsed.username and not parsed.query and not parsed.fragment and (parsed.scheme == "https" or (parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"})) and settings.EMAIL_BACKEND not in {
        "django.core.mail.backends.console.EmailBackend", "django.core.mail.backends.filebased.EmailBackend", "django.core.mail.backends.dummy.EmailBackend"}
    if configured:
        link = f"{base}/recover-account#{item.pk}/{raw}"
        try:
            sent = send_mail("PlatformaCRM: account recovery", f"Confirm your new email and set a password:\n{link}\nExpires in 30 minutes.",
                settings.DEFAULT_FROM_EMAIL, [item.new_email], fail_silently=False, connection=get_connection(timeout=10))
            if sent == 1:
                item.delivery_status = "accepted"
                item.status = "sent"
                item.token_hash = token_hash(raw)
                item.token_expires_at = min(item.expires_at, timezone.now() + timedelta(minutes=30))
        except (SMTPException, OSError):
            pass  # Persist only a safe category, never the provider's raw exception.
    item.executed_by = actor
    item.save(update_fields=["token_hash", "token_expires_at", "last_attempt_at", "delivery_status", "status", "executed_by"])
    audit(request, item, "delivery_accepted" if item.status == "sent" else "delivery_unavailable")
    return item


@transaction.atomic
def complete(request, recovery_id, *, token, password):
    stub = get_object_or_404(AccountRecovery, pk=recovery_id)
    business, user, item = locked_item(stub.business_id, recovery_id)
    if item.status != "sent" or not item.token_hash or not item.token_expires_at or item.token_expires_at <= timezone.now() or not constant_time_compare(item.token_hash, token_hash(token)):
        raise ValidationError("The recovery link is invalid or expired.")
    current(item, user, business)
    if item.support_case.status == "resolved":
        raise OwnershipConflict()
    check_email(user, item.new_email)
    try:
        validate_password(password, user=user)
    except DjangoValidationError as exc:
        raise ValidationError({"password": exc.messages}) from None
    user.email = item.new_email
    user.set_password(password)
    try:
        with transaction.atomic():
            user.save(update_fields=["email", "password"])
    except IntegrityError:
        raise ValidationError("The email address is no longer available.") from None
    revoke_user_refresh_sessions(user)
    MfaChallenge.objects.filter(user=user, consumed_at__isnull=True).update(consumed_at=timezone.now())
    MfaRecoveryCode.objects.filter(user=user).delete()
    MfaDevice.objects.filter(user=user).delete()
    EmailChangeChallenge.objects.filter(user=user).delete()
    SocialIdentity.objects.filter(user=user).delete()
    item.status = "completed"
    item.token_hash = ""
    item.completed_at = timezone.now()
    item.save(update_fields=["status", "token_hash", "completed_at"])
    audit(request, item, "completed")
    # No JWT is issued: next sign-in follows the normal mandatory MFA enrollment.
    return item
