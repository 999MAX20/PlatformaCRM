from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError, transaction
from django.db.models import F, Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.branches.access import accessible_branches
from apps.core.domain_errors import ModuleDisabled
from apps.core.domain_errors import DomainAPIException
from apps.notifications.models import Notification
from apps.notifications.routing import filter_notification_recipients
from apps.scheduling.models import Appointment, Resource
from .models import MedicalAuditEvent, MedicalParticipationNotice, MedicalRoleAssignment, TreatmentParticipation
from .participation_reads import _rows
from .role_access import assert_medical_role_permission


ROUTE = "/app/medical/participations"
INCOMING = ("participation_proposed", "participation_withdrawn", "participation_ended")
REPLIES = ("participation_accepted", "participation_declined")


def notice_url(notification_id):
    return f"{ROUTE}?notification={notification_id}"


class MedicalNotificationUnavailable(DomainAPIException):
    status_code = 503
    error_code = "medical_notification_unavailable"
    default_code = error_code
    default_detail = "Notification storage is unavailable. The operation was not completed."
    category = "temporary"


def notify_participation_event(event):
    try:
        return _notify_participation_event(event)
    except DatabaseError:
        raise MedicalNotificationUnavailable() from None


@transaction.atomic
def _notify_participation_event(event):
    event = MedicalAuditEvent.objects.select_for_update().select_related(
        "business", "participation__member__user", "participation__proposed_by").get(pk=event.pk)
    if event.action not in INCOMING + REPLIES or event.result != "success" or event.participation_id is None:
        raise ValueError("A successful participation transition is required.")
    existing = MedicalParticipationNotice.objects.filter(event=event).first()
    if existing:
        return existing.notification
    item = event.participation
    if not _rows(event.business).filter(pk=item.pk, patient_id=event.patient_id,
                                       revision=event.participation_revision).exists():
        raise ValueError("The event must describe this business's current participation.")
    recipient = item.proposed_by if event.action in REPLIES else item.member.user
    try:
        role = assert_medical_role_permission(recipient, event.business, "medical_participation", "view")
    except (PermissionDenied, ModuleDisabled):
        return None
    if role.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
        return None
    if not filter_notification_recipients(business=event.business, users=[recipient],
            category=Notification.Categories.SYSTEM, priority=Notification.Priorities.NORMAL):
        return None
    notification = Notification.objects.create(business=event.business, recipient=recipient,
        channel=Notification.Channels.SYSTEM, category=Notification.Categories.SYSTEM,
        kind=Notification.Kinds.WORK, priority=Notification.Priorities.NORMAL,
        text="", send_at=timezone.now(), status=Notification.Statuses.SENT,
        action_url=ROUTE, publication_key=event.event_id)
    notification.action_url = notice_url(notification.pk)
    notification.save(update_fields=["action_url"])
    MedicalParticipationNotice.objects.create(notification=notification, event=event)
    return notification


def _current_proposals(actor, business, role, branches):
    rows = _rows(business).filter(proposed_by=actor)
    try:
        assert_medical_role_permission(actor, business, "medical_participation", "create")
    except (PermissionDenied, ModuleDisabled):
        return rows.none()
    if role.kind == MedicalRoleAssignment.Kinds.HEAD:
        return rows.filter(branch_id__in=branches.values("pk"))
    appointments = Appointment.objects.filter(business=business, client__business=business,
        service__business=business, resource__business=business,
        resource__resource_type=Resource.ResourceTypes.STAFF, resource__linked_user=actor,
        branch_id__in=branches.values("pk"), is_archived=False,
        status__in=("created", "confirmed", "rescheduled"), end_at__gt=F("start_at"))
    participations = _rows(business).filter(member_id=role.member_id, state="active",
        branch_id__in=branches.values("pk"), accepted_at__lte=timezone.now(),
        accepted_at__gte=F("proposed_at"), closed_at__isnull=True, closed_by__isnull=True)
    return rows.filter(
        Q(source_appointment_id__in=appointments.values("pk"),
          source_appointment__client_id=F("patient__client_id"), source_participation__isnull=True) |
        Q(source_participation_id__in=participations.values("pk"),
          source_participation__patient_id=F("patient_id"), source_appointment__isnull=True))


class ParticipationNotificationSource:
    related_paths = ("medical_participation_notice__event",)

    @staticmethod
    def filter_ids(*, actor, business, notification_ids):
        notices = MedicalParticipationNotice.objects.filter(notification_id__in=notification_ids)
        claimed = set(notices.values_list("notification_id", flat=True))
        if not claimed:
            return claimed, set()
        try:
            role = assert_medical_role_permission(actor, business, "medical_participation", "view")
        except (PermissionDenied, ModuleDisabled):
            return claimed, set()
        if role.kind not in (MedicalRoleAssignment.Kinds.DOCTOR, MedicalRoleAssignment.Kinds.HEAD):
            return claimed, set()
        branches = accessible_branches(actor, business)
        if not role.all_branches:
            branches = branches.filter(medical_assignments__pk=role.assignment_id)
        incoming = _rows(business).filter(member_id=role.member_id, branch_id__in=branches.values("pk"))
        outgoing = _current_proposals(actor, business, role,
            branches.filter(is_active=True, archived_at__isnull=True))
        notices = notices.filter(notification__business=business, notification__recipient=actor,
            notification__channel="system", notification__kind="work", notification__category="system",
            notification__author__isnull=True, notification__client__isnull=True,
            notification__appointment__isnull=True, event__business=business, event__result="success",
            event__patient_id=F("event__participation__patient_id"),
            event__participation_revision__lte=F("event__participation__revision"),
            event__participation__proposed_at__lte=timezone.now()).filter(
                Q(event__action__in=INCOMING, event__participation_id__in=incoming.values("pk")) |
                Q(event__action__in=REPLIES, event__participation_id__in=outgoing.values("pk")))
        allowed = {pk for pk, url in notices.values_list("notification_id", "notification__action_url")
                   if url == notice_url(pk)}
        return claimed, allowed

    @staticmethod
    def presentation(notification):
        try:
            notice = notification.medical_participation_notice
        except ObjectDoesNotExist:
            return None
        event = notice.event
        if (notification.channel != "system" or notification.kind != "work" or
                notification.business_id != event.business_id or event.action not in INCOMING + REPLIES or
                notification.action_url != notice_url(notification.pk)):
            return {"message_key": "notification.work.notifications", "action_url": ""}
        return {"message_key": "medical.notifications." + event.action,
                "action_url": notice_url(notification.pk)}
