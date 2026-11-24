from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import ModuleDisabled
from apps.notifications.models import Notification
from apps.notifications.routing import filter_notification_recipients
from .models import ReceptionBookingRequest, ReceptionNotice, TreatmentParticipation
from .patient_selectors import reception_context
from .appointment_access import assert_appointment_medical_basis
from .participation_access import assert_treatment_medical_basis


ROUTE = "/app/medical/reception"


def notice_access(actor, item):
    if (not actor.is_active or item.patient.client.is_archived or item.patient.business_id != item.business_id
            or item.patient.client.business_id != item.business_id):
        raise PermissionDenied()
    assert_can(actor, item.business, Resources.CLIENTS, Actions.VIEW, obj=item.patient.client)
    if item.referring_clinician.user_id == actor.pk:
        try:
            assert_appointment_medical_basis(actor=actor, business=item.business, patient_id=item.patient_id,
                appointment_id=item.source_appointment_id)
            return "doctor"
        except PermissionDenied:
            for identifier in TreatmentParticipation.objects.filter(business=item.business, patient=item.patient,
                    member=item.referring_clinician, state="active").values_list("pk", flat=True):
                try:
                    assert_treatment_medical_basis(actor=actor, business=item.business,
                        patient_id=item.patient_id, participation_id=identifier)
                    return "doctor"
                except PermissionDenied:
                    continue
            raise PermissionDenied() from None
    reception_context(actor=actor, business_id=item.business_id, branch_id=item.branch_id, action="view")
    return "reception"


def notify_reception(item, kind, recipients=None):
    from .participation_notifications import MedicalNotificationUnavailable
    try:
        return _notify_reception(item, kind, recipients)
    except DatabaseError:
        raise MedicalNotificationUnavailable() from None


@transaction.atomic
def _notify_reception(item, kind, recipients=None):
    if recipients is None:
        if kind == "new":
            recipients = [row.user for row in BusinessMember.objects.select_related("user").filter(
                business_id=item.business_id, is_active=True, user__is_active=True,
                medical_role_assignment__kind="reception", medical_role_assignment__revoked_at__isnull=True)]
        else:
            recipients = [item.referring_clinician.user] + ([item.assignee.user] if item.assignee_id else [])
    for recipient in {user.pk: user for user in recipients}.values():
        try: notice_access(recipient, item)
        except (PermissionDenied, ModuleDisabled): continue
        if ReceptionNotice.objects.filter(request=item, revision=item.revision, kind=kind, recipient=recipient).exists(): continue
        priority = Notification.Priorities.HIGH if kind == "escalated" else Notification.Priorities.NORMAL
        if not filter_notification_recipients(business=item.business, users=[recipient], category="system", priority=priority): continue
        notice = Notification.objects.create(business=item.business, recipient=recipient, channel="system",
            category="system", kind="work", priority=priority, text="", send_at=timezone.now(),
            status="sent", action_url=ROUTE, publication_key=uuid4())
        ReceptionNotice.objects.create(request=item, revision=item.revision, kind=kind,
            recipient=recipient, notification=notice)


@transaction.atomic
def escalate_reception_request(request_id):
    from .reception_duties import current_duty_recipient
    business_id = ReceptionBookingRequest.objects.filter(pk=request_id).values_list("business_id", flat=True).first()
    if business_id is None: return False
    Business.objects.select_for_update().get(pk=business_id)
    item = ReceptionBookingRequest.objects.select_for_update().select_related("business", "branch", "patient__client").get(pk=request_id)
    now = timezone.now()
    if item.state not in ("new", "pending") or item.assignee_id or item.acceptance_due_at is None or item.acceptance_due_at > now:
        return False
    recipient = current_duty_recipient(item, now)
    if recipient is None: return False
    before = item.notices.count()
    notify_reception(item, "escalated", [recipient.user])
    return item.notices.count() > before


class ReceptionNotificationSource:
    related_paths = ("medical_reception_notice__request__patient__client", "medical_reception_notice__request__referring_clinician__user")

    @staticmethod
    def filter_ids(*, actor, business, notification_ids):
        rows = ReceptionNotice.objects.filter(notification_id__in=notification_ids).select_related(
            "notification", "request__business", "request__patient__client", "request__referring_clinician__user")
        claimed, allowed = set(), set()
        for row in rows:
            claimed.add(row.notification_id)
            notice, item = row.notification, row.request
            if (item.business_id != business.pk or row.recipient_id != actor.pk or notice.recipient_id != actor.pk
                    or notice.business_id != business.pk or notice.action_url != ROUTE or notice.channel != "system"
                    or notice.kind != "work" or notice.client_id or notice.appointment_id or notice.author_id): continue
            try: notice_access(actor, item)
            except (PermissionDenied, ModuleDisabled): continue
            allowed.add(row.notification_id)
        return claimed, allowed

    @staticmethod
    def presentation(notification):
        try: row = notification.medical_reception_notice
        except ObjectDoesNotExist: return None
        item = row.request
        if (notification.business_id != item.business_id or notification.recipient_id != row.recipient_id or
                notification.channel != "system" or notification.kind != "work" or notification.action_url != ROUTE):
            return {"message_key": "notification.work.notifications", "action_url": ""}
        doctor = item.referring_clinician.user_id == notification.recipient_id
        url = f"/app/clients/{item.patient.client_id}" if doctor else f"{ROUTE}?branch={item.branch_id}&request={item.pk}"
        return {"message_key": f"medical.reception.notice.{row.kind}{'.onsite' if row.kind == 'new' and item.patient_in_clinic else ''}",
            "message_params": {"patient": item.patient.client.full_name,
                "initiator": item.referring_clinician.user.full_name or item.referring_clinician.user.get_full_name()}, "action_url": url}
