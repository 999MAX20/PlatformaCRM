from django.db import transaction
from django.utils import timezone

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.audit import write_audit_log
from apps.core.models import AuditLog
from apps.notifications.models import Notification
from apps.scheduling.models import Appointment, AppointmentMessageSetting


UNFINISHED_DELIVERY_STATUSES = [Notification.Statuses.PENDING, Notification.Statuses.RETRY_SCHEDULED, Notification.Statuses.SENDING]


def appointment_notification_scenario(notification):
    from apps.scheduling.services import APPOINTMENT_MESSAGE_DEFAULTS
    if not notification.appointment_id:
        return None
    for scenario, defaults in APPOINTMENT_MESSAGE_DEFAULTS.items():
        if notification.action_label == defaults["label"]:
            return scenario
    return AppointmentMessageSetting.objects.filter(business_id=notification.business_id, label=notification.action_label).values_list("scenario", flat=True).first()


def appointment_notification_is_current(notification, scenario):
    from apps.scheduling.services import get_appointment_message_setting
    appointment = Appointment.objects.select_related("business").filter(pk=notification.appointment_id, business_id=notification.business_id, is_archived=False).first()
    if appointment is None or not get_appointment_message_setting(appointment.business, scenario).is_enabled:
        return False
    if scenario == AppointmentMessageSetting.Scenarios.THANK_YOU:
        return appointment.status == Appointment.Statuses.COMPLETED
    return appointment.status not in {Appointment.Statuses.CANCELLED, Appointment.Statuses.COMPLETED, Appointment.Statuses.NO_SHOW} and appointment.start_at > timezone.now()


@transaction.atomic
def update_appointment_message_setting(*, request, setting, changes):
    from apps.scheduling.services import APPOINTMENT_MESSAGE_DEFAULTS, queue_appointment_message

    Business.objects.select_for_update().get(pk=setting.business_id)
    setting = AppointmentMessageSetting.objects.select_for_update().select_related("business").get(pk=setting.pk)
    assert_can(request.user, setting.business, Resources.SETTINGS, Actions.UPDATE)
    changes = {key: value for key, value in changes.items() if getattr(setting, key) != value}
    if not changes:
        return setting
    for key, value in changes.items():
        setattr(setting, key, value)
    setting.save(update_fields=[*changes, "updated_at"])
    labels = {setting.label, APPOINTMENT_MESSAGE_DEFAULTS[setting.scenario]["label"]}
    unfinished = Notification.objects.filter(business=setting.business, appointment__isnull=False, action_label__in=labels, status__in=UNFINISHED_DELIVERY_STATUSES)
    appointment_ids = set(unfinished.exclude(appointment=None).values_list("appointment_id", flat=True))
    now = timezone.now()
    unfinished.update(status=Notification.Statuses.CANCELLED, next_retry_at=None, locked_at=None, updated_at=now)
    appointments = Appointment.objects.filter(business=setting.business, is_archived=False).select_related("business", "client", "service", "resource", "lead", "lead__responsible_user")
    if setting.scenario == AppointmentMessageSetting.Scenarios.THANK_YOU:
        # Reconcile already scheduled follow-ups only; never backfill historical visits.
        appointments = appointments.filter(pk__in=appointment_ids, status=Appointment.Statuses.COMPLETED)
    else:
        appointments = appointments.filter(start_at__gt=now).exclude(status__in=[Appointment.Statuses.CANCELLED, Appointment.Statuses.COMPLETED, Appointment.Statuses.NO_SHOW])
    if setting.is_enabled:
        for appointment in appointments:
            already_sent = Notification.objects.filter(appointment=appointment, business=setting.business, action_label__in=labels, status=Notification.Statuses.SENT).exists()
            if appointment.pk in appointment_ids or not already_sent:
                queue_appointment_message(appointment, setting)
    write_audit_log(request, AuditLog.Actions.UPDATE, setting, metadata={"fields": sorted(changes), "scenario": setting.scenario})
    return setting
