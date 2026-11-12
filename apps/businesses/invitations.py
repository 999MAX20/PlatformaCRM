"""Invitation issue, rotation and bounded transactional-email delivery."""
from datetime import timedelta
from smtplib import SMTPException
from urllib.parse import urlsplit
from uuid import uuid4

from django.conf import settings
from django.core.mail import get_connection, send_mail
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import Throttled, ValidationError

from apps.billing.entitlements import EntitlementMetrics, assert_entitlement_allows
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business, BusinessInvitation, BusinessMember, BusinessRole
from apps.core.audit import write_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog

INVITATION_LIFETIME = timedelta(hours=24)


def assert_available(invitation):
    if invitation.role == BusinessMember.Roles.OWNER:
        raise ValidationError("Ownership cannot be granted through an invitation.")
    role = invitation.business_role
    if role and (role.business_id != invitation.business_id or not role.is_active or role.preset_key == "owner"):
        raise ValidationError("The invitation role is no longer available.")
    team = invitation.team
    if team and (team.business_id != invitation.business_id or not team.is_active):
        raise ValidationError("The invitation team is no longer available.")
    if BusinessMember.objects.filter(business_id=invitation.business_id, user__email__iexact=invitation.email, is_active=True).exists():
        raise ValidationError("This user is already an active member of the business.")


@transaction.atomic
def issue_invitation(request, serializer):
    business = Business.objects.select_for_update().get(pk=serializer.validated_data["business"].pk)
    assert_can(request.user, business, Resources.TEAM, Actions.MANAGE)
    assert_entitlement_allows(business, EntitlementMetrics.USERS)
    # Repeat duplicate/member validation under the same business lock as acceptance.
    serializer.validate(dict(serializer.validated_data))
    role = serializer.validated_data.get("role", BusinessMember.Roles.SPECIALIST)
    business_role = serializer.validated_data.get("business_role") or BusinessRole.objects.filter(
        business=business, preset_key=role, is_active=True,
    ).first()
    invitation = serializer.save(invited_by=request.user, business_role=business_role,
        expires_at=timezone.now() + INVITATION_LIFETIME,
        delivery_status="pending" if serializer.validated_data.get("delivery_channel") == "email" else "not_requested")
    assert_available(invitation)
    write_audit_log(request, AuditLog.Actions.CREATE, invitation, business=business)
    queue_delivery(invitation, request)
    return invitation


@transaction.atomic
def resend_invitation(request, invitation, *, revision):
    business = Business.objects.select_for_update().get(pk=invitation.business_id)
    invitation = BusinessInvitation.objects.select_for_update().get(pk=invitation.pk)
    assert_can(request.user, business, Resources.TEAM, Actions.MANAGE)
    if invitation.updated_at != revision:
        raise InvalidTransition("Invitation changed. Refresh the list before sending again.")
    if invitation.accepted_at or invitation.revoked_at:
        raise InvalidTransition("An accepted or revoked invitation cannot be resent.")
    assert_available(invitation)
    assert_entitlement_allows(business, EntitlementMetrics.USERS)
    if invitation.delivery_attempted_at:
        remaining = 60 - (timezone.now() - invitation.delivery_attempted_at).total_seconds()
        if remaining > 0:
            raise Throttled(wait=remaining)
    invitation.token = uuid4()
    invitation.expires_at = timezone.now() + INVITATION_LIFETIME
    invitation.delivery_channel = "email"
    invitation.delivery_status = "pending"
    invitation.delivery_error = ""
    invitation.save(update_fields=["token", "expires_at", "delivery_channel", "delivery_status", "delivery_error", "updated_at"])
    write_audit_log(request, AuditLog.Actions.UPDATE, invitation, business=business, metadata={"event": "invitation_resent"})
    queue_delivery(invitation, request)
    return invitation


def queue_delivery(invitation, request):
    if invitation.delivery_channel == "email":
        # A rolled-back invitation must never leave a usable link in a mailbox.
        transaction.on_commit(lambda: deliver_invitation(invitation.pk, invitation.token, request))


def mail_body(invitation, link):
    language = invitation.business.language
    role = invitation.business_role.name if invitation.business_role else invitation.role
    if language == "kk":
        return "PlatformaCRM: бизнеске шақыру", (
            f'Сізді «{invitation.business.name}» бизнесіне шақырды.\nРөл: {role}\n'
            f'Шақыруды қабылдау: {link}\nСілтеме берілген сәттен бастап 24 сағат жарамды.\n'
            'Тіркелгіңіз болса, осы email арқылы кіріңіз. Әйтпесе, құпиясөзді өзіңіз орнатыңыз.\n'
            'Бұл шақыруды күтпесеңіз, хатты елемеңіз.'
        )
    if language == "en":
        return "PlatformaCRM: business invitation", (
            f'You are invited to "{invitation.business.name}".\nRole: {role}\n'
            f'Accept invitation: {link}\nThis link expires 24 hours after issue.\n'
            'Already have an account? Sign in with this email. Otherwise, choose your own password.\n'
            'If you were not expecting this invitation, ignore this email.'
        )
    return "PlatformaCRM: приглашение в бизнес", (
        f'Вас пригласили в «{invitation.business.name}».\nРоль: {role}\n'
        f'Принять приглашение: {link}\nСсылка действует 24 часа с момента выпуска.\n'
        'Если аккаунт уже есть, войдите с этим email. Если нет — задайте свой пароль.\n'
        'Если вы не ожидали приглашения, проигнорируйте письмо.'
    )


@transaction.atomic
def deliver_invitation(invitation_id, token, request):
    stub = BusinessInvitation.objects.filter(pk=invitation_id).values("business_id").first()
    if not stub:
        return
    Business.objects.select_for_update().get(pk=stub["business_id"])
    invitation = BusinessInvitation.objects.select_for_update(of=("self",)).select_related("business", "business_role").get(pk=invitation_id)
    if invitation.token != token or not invitation.is_pending or invitation.delivery_status != "pending":
        return
    base = settings.FRONTEND_URL.rstrip("/")
    parsed = urlsplit(base)
    local = settings.ENVIRONMENT in {"local", "development", "test"}
    valid_url = bool(parsed.hostname and not parsed.username and not parsed.password and not parsed.query and not parsed.fragment
        and (parsed.scheme == "https" or (local and parsed.scheme == "http" and parsed.hostname in {"localhost", "127.0.0.1"})))
    backend = settings.EMAIL_BACKEND
    configured = backend not in {"django.core.mail.backends.console.EmailBackend", "django.core.mail.backends.filebased.EmailBackend", "django.core.mail.backends.dummy.EmailBackend"}
    if backend == "django.core.mail.backends.locmem.EmailBackend":
        configured = local
    if backend == "django.core.mail.backends.smtp.EmailBackend":
        configured = bool(settings.EMAIL_HOST)
    invitation.delivery_status = "failed"
    invitation.delivery_error = "not_configured"
    invitation.delivery_attempted_at = timezone.now()
    if configured and valid_url:
        subject, body = mail_body(invitation, f"{base}/invite/{invitation.token}")
        invitation.delivery_error = "unavailable"
        try:
            sent = send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [invitation.email],
                fail_silently=False, connection=get_connection(timeout=10))
            if sent == 1:
                invitation.delivery_status = "accepted"
                invitation.delivery_error = ""
        except (SMTPException, OSError, ValueError):
            pass  # Never persist provider errors: they can contain credentials or bearer links.
    invitation.save(update_fields=["delivery_status", "delivery_error", "delivery_attempted_at", "updated_at"])
    write_audit_log(request, AuditLog.Actions.UPDATE, invitation, business=invitation.business,
        metadata={"event": "invitation_email", "delivery_status": invitation.delivery_status, "error": invitation.delivery_error})
