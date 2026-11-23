import uuid
from datetime import timedelta

from django.conf import settings
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import APIException, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.integrations import google_calendar_provider as provider, google_oauth
from apps.integrations.google_calendar_access import appointments, assert_connection, specialist
from apps.integrations.google_calendar_models import GoogleCalendarBinding, GoogleCalendarBusy, GoogleCalendarMirror
from apps.integrations.google_http import GoogleError
from apps.integrations.google_models import GoogleConnection
from apps.scheduling.models import Appointment


def _locked_binding(binding_id):
    initial = GoogleCalendarBinding.objects.select_related("connection").get(pk=binding_id)
    Business.objects.select_for_update().get(pk=initial.connection.business_id)
    connection = GoogleConnection.objects.select_for_update().select_related("business", "actor").get(pk=initial.connection_id)
    binding = GoogleCalendarBinding.objects.select_for_update().select_related("resource").get(pk=binding_id)
    assert_connection(connection, connection.actor)
    specialist(connection, connection.actor, binding.resource_id)
    if not binding.enabled or connection.status != "connected":
        raise ValidationError("Reconnect or enable Google Calendar.")
    binding.connection = connection
    return binding


def _marker(mirror):
    return {"platformaMirror": str(mirror.pk)}


def _payload(mirror, appointment):
    return {"summary": f"{appointment.client.full_name}: {appointment.service.name}",
        "start": {"dateTime": appointment.start_at.isoformat()},
        "end": {"dateTime": appointment.end_at.isoformat()},
        "visibility": "private", "transparency": "opaque", "status": "confirmed",
        "description": "", "location": "", "attendees": [],
        "reminders": {"useDefault": False},
        "extendedProperties": {"private": _marker(mirror)}}


def _matches(remote, payload, zone):
    if not remote:
        return False
    if provider.event_interval(remote, zone) != provider.event_interval(payload, zone):
        return False
    defaults = {"description": "", "location": "", "attendees": []}
    return all(remote.get(key, defaults.get(key)) == value
               for key, value in payload.items() if key not in {"start", "end"})


def external_intervals(binding, events, zone):
    owned = dict(binding.mirrors.values_list("event_id", "id"))
    intervals = []
    for event in events:
        mirror_id = owned.get(event.get("id"))
        if mirror_id and event.get("extendedProperties", {}).get("private", {}).get("platformaMirror") == str(mirror_id):
            continue
        interval = provider.event_interval(event, zone)
        if interval:
            intervals.append(interval)
    return intervals


def _sync_appointment(binding_id, appointment_id):
    # Reserve the event identity durably before a network request; a timeout or
    # worker crash must discover this same event rather than insert a duplicate.
    with transaction.atomic():
        binding = _locked_binding(binding_id)
        appointment = appointments(binding.connection).filter(pk=appointment_id).first()
        if appointment is None:
            raise ValidationError("Appointment access changed. Review the calendar connection.")
        mirror, _ = GoogleCalendarMirror.objects.get_or_create(binding=binding, appointment=appointment,
            defaults={"event_id": uuid.uuid4().hex})
    with transaction.atomic():
        binding = _locked_binding(binding_id)
        connection = binding.connection
        appointment = appointments(connection).select_related("client", "service").filter(pk=appointment_id).first()
        if appointment is None:
            raise ValidationError("Appointment access changed. Review the calendar connection.")
        assert_can(connection.actor, connection.business, Resources.CLIENTS, Actions.VIEW, obj=appointment.client)
        mirror = GoogleCalendarMirror.objects.select_for_update().get(pk=mirror.pk)
        active = (appointment.resource_id == binding.resource_id and not appointment.is_archived
                  and appointment.status not in {Appointment.Statuses.CANCELLED, Appointment.Statuses.RESCHEDULED})
        token = google_oauth.access_token(connection, connection.actor)
        remote = provider.get_event(token, binding.calendar_id, mirror.event_id)
        if remote and remote.get("status") != "cancelled":
            if remote.get("extendedProperties", {}).get("private", {}) != _marker(mirror):
                raise ValidationError("Calendar event ownership changed. Review the connection.")
            if remote.get("attendees"):
                raise ValidationError("Remove added event guests before retrying calendar synchronization.")
        if not active:
            if remote and remote.get("status") != "cancelled":
                provider.delete_event(token, binding.calendar_id, mirror.event_id, remote)
            mirror.state = "deleted"
        elif remote and remote.get("status") == "cancelled":
            # A deleted Google ID cannot be reused. Commit the new reservation
            # without sending it; the next retry will create exactly that ID.
            mirror.generation += 1
            mirror.event_id = uuid.uuid4().hex
            mirror.state = "pending"
        else:
            payload = _payload(mirror, appointment)
            changed = not _matches(remote, payload, binding.timezone)
            if changed:
                provider.write_event(token, binding.calendar_id, mirror.event_id, payload, existing=remote)
            mirror.state = "synced"
        mirror.synced_at = timezone.now() if mirror.state != "pending" else None
        mirror.save(update_fields=["state", "generation", "event_id", "synced_at"])


def sync_binding(binding_id):
    if not settings.GOOGLE_CALENDAR_ENABLED:
        raise ValidationError("Google Calendar synchronization is not enabled.")
    started = timezone.now()
    start, end = started - timedelta(days=1), started + timedelta(days=90)
    try:
        with transaction.atomic():
            binding = _locked_binding(binding_id)
            connection = binding.connection
            token = google_oauth.access_token(connection, connection.actor)
            info = provider.calendar_info(token, binding.calendar_id)
            candidates = appointments(connection).filter(
                Q(resource=binding.resource, end_at__gt=start)
                | Q(googlecalendarmirror__binding=binding, end_at__gt=start)
            ).distinct().order_by("pk")
            ids = list(candidates.values_list("pk", flat=True)[:1001])
            if len(ids) > 1000:
                raise ValidationError("Calendar synchronization capacity exceeded. Contact support.")
        for appointment_id in ids:
            _sync_appointment(binding_id, appointment_id)
        # Fetch after writes, so newly created CRM copies are excluded by durable ID.
        with transaction.atomic():
            binding = _locked_binding(binding_id)
            token = google_oauth.access_token(binding.connection, binding.connection.actor)
            remote = provider.events(token, binding.calendar_id, start, end)
            intervals = external_intervals(binding, remote, info["timeZone"])
            binding.busy.all().delete()
            GoogleCalendarBusy.objects.bulk_create([
                GoogleCalendarBusy(binding=binding, start_at=left, end_at=right) for left, right in intervals])
            binding.timezone = info["timeZone"]
            binding.calendar_name = info.get("summary", "")[:255]
            binding.last_sync_at = started
            binding.coverage_start, binding.coverage_end = start, end
            binding.error_code, binding.failures = "", 0
            binding.next_sync_at = timezone.now() + timedelta(seconds=60)
            binding.save(update_fields=["timezone", "calendar_name", "last_sync_at", "coverage_start", "coverage_end",
                                       "error_code", "failures", "next_sync_at"])
            connection.last_sync_at = started
            connection.save(update_fields=["last_sync_at", "updated_at"])
        return {"appointments": len(ids), "busy_intervals": len(intervals)}
    except (APIException, GoogleConnection.DoesNotExist) as exc:
        with transaction.atomic():
            # Token refresh happens inside the sync transaction; persist revoked
            # status after rollback, without overwriting a concurrent reconnect.
            if isinstance(exc, GoogleError) and exc.revoked and "connection" in locals():
                GoogleConnection.objects.filter(pk=connection.pk, revision=connection.revision,
                    status="connected").update(status="expired_credentials", updated_at=timezone.now())
            binding = GoogleCalendarBinding.objects.select_for_update().get(pk=binding_id)
            binding.failures += 1
            binding.error_code = "sync_failed"
            binding.next_sync_at = timezone.now() + timedelta(seconds=min(3600, 60 * 2 ** min(binding.failures, 6)))
            binding.save(update_fields=["failures", "error_code", "next_sync_at"])
        raise


def process_due():
    if not settings.GOOGLE_CALENDAR_ENABLED:
        return {"synced": 0, "failed": 0}
    ids = GoogleCalendarBinding.objects.filter(enabled=True, connection__status="connected").filter(
        Q(next_sync_at__isnull=True) | Q(next_sync_at__lte=timezone.now())
    ).order_by("next_sync_at").values_list("pk", flat=True)[:20]
    result = {"synced": 0, "failed": 0}
    for binding_id in list(ids):
        try:
            sync_binding(binding_id)
            result["synced"] += 1
        except APIException:
            result["failed"] += 1
    return result
