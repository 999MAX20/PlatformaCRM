from uuid import uuid4

from django.core.exceptions import ObjectDoesNotExist
from django.db import DatabaseError, transaction
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied

from apps.branches.access import accessible_branches
from apps.core.domain_errors import ModuleDisabled
from apps.notifications.models import Notification
from apps.notifications.routing import filter_notification_recipients
from .models import AppointmentAssistant
from .participation_notifications import MedicalNotificationUnavailable
from .role_access import assert_medical_role_permission


ROUTE = "/app/medical/assistants"


def notify_assistant_invitation(item):
    try:
        return _notify_assistant_invitation(item)
    except DatabaseError:
        raise MedicalNotificationUnavailable() from None


@transaction.atomic
def _notify_assistant_invitation(item):
    item = AppointmentAssistant.objects.select_for_update().select_related(
        "business", "assignment__member__user").get(pk=item.pk)
    if item.invitation_notification_id:
        return item.invitation_notification
    if item.state != "pending":
        return None
    recipient = item.assignment.member.user
    if not filter_notification_recipients(business=item.business, users=[recipient],
            category=Notification.Categories.SYSTEM, priority=Notification.Priorities.NORMAL):
        return None
    notice = Notification.objects.create(business=item.business, recipient=recipient,
        channel=Notification.Channels.SYSTEM, category=Notification.Categories.SYSTEM,
        kind=Notification.Kinds.WORK, priority=Notification.Priorities.NORMAL,
        text="", send_at=timezone.now(), status=Notification.Statuses.SENT,
        action_url=ROUTE, publication_key=uuid4())
    item.invitation_notification = notice
    item.save(update_fields=["invitation_notification"])
    return notice


class AssistantNotificationSource:
    related_paths = ("medical_assistant_invitation",)

    @staticmethod
    def filter_ids(*, actor, business, notification_ids):
        items = AppointmentAssistant.objects.filter(invitation_notification_id__in=notification_ids)
        claimed = set(items.values_list("invitation_notification_id", flat=True))
        if not claimed:
            return claimed, set()
        try:
            role = assert_medical_role_permission(actor, business, "medical_records", "view")
        except (PermissionDenied, ModuleDisabled):
            return claimed, set()
        if role.kind != "assistant":
            return claimed, set()
        branches = accessible_branches(actor, business).filter(is_active=True, archived_at__isnull=True)
        if not role.all_branches:
            branches = branches.filter(medical_assignments__pk=role.assignment_id)
        items = items.filter(business=business, patient__business=business,
            patient__client__business=business, assignment_id=role.assignment_id,
            assignment__member__business=business, assignment__member__user=actor,
            branch__business=business, branch_id__in=branches.values("pk"),
            invitation_notification__business=business, invitation_notification__recipient=actor,
            invitation_notification__channel="system", invitation_notification__kind="work",
            invitation_notification__category="system", invitation_notification__author__isnull=True,
            invitation_notification__client__isnull=True, invitation_notification__appointment__isnull=True,
            invitation_notification__action_url=ROUTE)
        return claimed, set(items.values_list("invitation_notification_id", flat=True))

    @staticmethod
    def presentation(notification):
        try:
            item = notification.medical_assistant_invitation
        except ObjectDoesNotExist:
            return None
        if (notification.business_id != item.business_id or notification.channel != "system" or
                notification.kind != "work" or notification.action_url != ROUTE):
            return {"message_key": "notification.work.notifications", "action_url": ""}
        return {"message_key": "medical.notifications.assistant_invited", "action_url": ROUTE}
