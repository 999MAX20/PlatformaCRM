from datetime import timedelta

from django.conf import settings
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.core.domain_errors import ScheduleConflict, TemporaryServiceFailure
from apps.integrations.google_calendar_models import GoogleCalendarBinding


def busy_intervals(business, resource, start, end):
    if not settings.GOOGLE_CALENDAR_ENABLED or resource is None:
        return []
    binding = GoogleCalendarBinding.objects.select_related("connection").filter(
        resource=resource, resource__business=business, connection__business=business, enabled=True).first()
    if binding is None or binding.connection.status == "disconnected":
        return []
    if (binding.connection.status != "connected" or not binding.last_sync_at
            or binding.last_sync_at < timezone.now() - timedelta(minutes=5)
            or not binding.coverage_start or not binding.coverage_end):
        raise TemporaryServiceFailure("Google Calendar availability is not current. Refresh the calendar connection and try again.")
    if start < binding.coverage_start or end > binding.coverage_end:
        from apps.integrations import google_calendar_provider as provider, google_oauth
        from apps.integrations.google_calendar_access import assert_connection
        from apps.integrations.google_calendar_sync import external_intervals

        # The periodic snapshot is bounded, but booking is not restricted to its
        # horizon. Fetch the requested range; never infer free time from a miss.
        try:
            assert_connection(binding.connection, binding.connection.actor)
            token = google_oauth.access_token(binding.connection, binding.connection.actor)
            info = provider.calendar_info(token, binding.calendar_id)
            return external_intervals(binding, provider.events(token, binding.calendar_id, start, end), info["timeZone"])
        except APIException:
            raise TemporaryServiceFailure("Google Calendar availability could not be checked. Try again later.") from None
    return list(binding.busy.filter(start_at__lt=end, end_at__gt=start).values_list("start_at", "end_at"))


def validate_slot(business, resource, start, end):
    if busy_intervals(business, resource, start, end):
        raise ScheduleConflict(errors={"start_at": "The specialist is busy in Google Calendar. Select another time."})


def filter_slots(business, resource, slots, minutes):
    if not slots:
        return slots
    duration = timedelta(minutes=minutes)
    intervals = busy_intervals(business, resource, min(slots), max(slots) + duration)
    return [start for start in slots if not any(start < right and start + duration > left for left, right in intervals)]
