from datetime import timedelta

from django.db import IntegrityError, transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.businesses.models import Business
from apps.integrations import google_calendar_provider as provider, google_oauth
from apps.integrations.google_calendar_access import assert_connection, specialist
from apps.integrations.google_calendar_models import GoogleCalendarBinding
from apps.integrations.google_models import GoogleConnection


def binding_status(binding):
    return {"id": str(binding.pk), "resource_id": binding.resource_id,
        "resource_name": binding.resource.name, "calendar_name": binding.calendar_name,
        "enabled": binding.enabled, "last_sync_at": binding.last_sync_at,
        "stale": not binding.last_sync_at or binding.last_sync_at < timezone.now() - timedelta(minutes=5),
        "pending": binding.mirrors.filter(state="pending").exists(),
        "coverage_start": binding.coverage_start, "coverage_end": binding.coverage_end,
        "error_code": binding.error_code, "next_sync_at": binding.next_sync_at}


def list_calendars(connection, actor):
    assert_connection(connection, actor)
    token = google_oauth.access_token(connection, actor)
    return [{"id": item["id"], "name": item.get("summary", ""), "timezone": item.get("timeZone", "")}
            for item in provider.calendars(token)]


def bind(connection, actor, *, resource_id, calendar_id):
    resource = specialist(connection, actor, resource_id)
    token = google_oauth.access_token(connection, actor)
    info = provider.calendar_info(token, calendar_id)
    if info.get("id") != calendar_id:
        raise ValidationError("Select the calendar from the current Google account list.")
    try:
        with transaction.atomic():
            Business.objects.select_for_update().get(pk=connection.business_id)
            current = GoogleConnection.objects.select_for_update().get(pk=connection.pk)
            specialist(current, actor, resource_id)
            if current.revision != connection.revision or current.status != "connected":
                raise ValidationError("Google connection changed. Connect again.")
            existing = GoogleCalendarBinding.objects.filter(resource=resource).first()
            if existing:
                if existing.connection_id != current.pk or existing.calendar_id != calendar_id:
                    raise ValidationError("This specialist already has a calendar binding.")
                return binding_status(existing)
            binding = GoogleCalendarBinding.objects.create(connection=current, resource=resource,
                calendar_id=calendar_id, calendar_name=info.get("summary", "")[:255],
                timezone=info["timeZone"], next_sync_at=timezone.now())
            google_oauth.audit(current, actor, "google_calendar_bound")
            return binding_status(binding)
    except IntegrityError:
        raise ValidationError("This calendar or specialist is already connected.") from None


def set_enabled(connection, actor, *, binding_id, enabled):
    assert_connection(connection, actor)
    with transaction.atomic():
        Business.objects.select_for_update().get(pk=connection.business_id)
        binding = GoogleCalendarBinding.objects.select_for_update().filter(
            pk=binding_id, connection=connection).first()
        if binding is None:
            raise ValidationError("Select a calendar binding of this connection.")
        binding.enabled = enabled
        if enabled:
            specialist(connection, actor, binding.resource_id)
            binding.last_sync_at = None
            binding.next_sync_at = timezone.now()
        else:
            binding.busy.all().delete()
            binding.coverage_start = binding.coverage_end = None
            binding.last_sync_at = None
            binding.next_sync_at = None
        binding.save(update_fields=["enabled", "last_sync_at", "next_sync_at", "coverage_start", "coverage_end"])
        google_oauth.audit(connection, actor, "google_calendar_enabled" if enabled else "google_calendar_disabled")
        return binding_status(binding)
