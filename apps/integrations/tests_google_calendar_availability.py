from datetime import timedelta, time

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.core.domain_errors import ScheduleConflict, TemporaryServiceFailure
from apps.integrations import tests_google_calendar as fixtures
from apps.integrations.google_calendar_availability import filter_slots, validate_slot
from apps.integrations.google_calendar_models import GoogleCalendarBusy
from apps.integrations.google_http import GoogleError
from apps.scheduling.availability import get_available_slots, validate_appointment_availability
from apps.scheduling.models import WorkingHours


@override_settings(GOOGLE_CALENDAR_ENABLED=True)
class GoogleBusyBookingTests(TestCase):
    write = fixtures.CalendarSyncTests.write
    delete = fixtures.CalendarSyncTests.delete

    def setUp(self):
        fixtures.CalendarSyncTests.setUp(self)
        self.binding.last_sync_at = timezone.now()
        self.binding.coverage_start = self.start - timedelta(days=2)
        self.binding.coverage_end = self.start + timedelta(days=90)
        self.binding.save()
        self.busy_start = self.start + timedelta(hours=1)
        GoogleCalendarBusy.objects.create(binding=self.binding, start_at=self.busy_start,
                                          end_at=self.busy_start+timedelta(minutes=30))

    def test_slot_boundaries_and_stale_snapshot(self):
        slots = [self.busy_start-timedelta(minutes=30), self.busy_start, self.busy_start+timedelta(minutes=30)]
        self.assertEqual(filter_slots(self.business, self.resource, slots, 30), [slots[0], slots[2]])
        with self.assertRaises(ScheduleConflict):
            validate_slot(self.business, self.resource, self.busy_start, self.busy_start+timedelta(minutes=30))
        self.binding.last_sync_at = timezone.now()-timedelta(minutes=6)
        self.binding.save()
        with self.assertRaises(TemporaryServiceFailure):
            validate_slot(self.business, self.resource, slots[0], self.busy_start)

    def test_scheduling_domain_rejects_external_busy_and_filters_slots(self):
        from apps.scheduling.availability import business_zone
        local = self.busy_start.astimezone(business_zone(self.business))
        WorkingHours.objects.create(business=self.business, resource=self.resource, weekday=local.weekday(),
                                    start_time=time(0), end_time=time(23, 59))
        with self.assertRaises(ScheduleConflict):
            validate_appointment_availability(self.business, self.service, self.busy_start, resource=self.resource)
        slots = get_available_slots(self.business, self.service, local.date(), resource=self.resource)
        self.assertNotIn(self.busy_start, slots)

    def test_explicit_pause_releases_external_blocks(self):
        self.binding.enabled = False
        self.binding.save()
        validate_slot(self.business, self.resource, self.busy_start, self.busy_start+timedelta(minutes=30))

    def test_outside_coverage_is_not_claimed_free(self):
        self.events_mock.side_effect = GoogleError()
        with self.assertRaises(TemporaryServiceFailure):
            validate_slot(self.business, self.resource, self.start+timedelta(days=91), self.start+timedelta(days=92))

    def test_outside_coverage_fetches_real_busy_range(self):
        start, end = self.start+timedelta(days=120), self.start+timedelta(days=120, hours=1)
        self.external = [{"id": "future", "start": {"dateTime": start.isoformat()}, "end": {"dateTime": end.isoformat()}}]
        with self.assertRaises(ScheduleConflict):
            validate_slot(self.business, self.resource, start, end)
        self.assertEqual(self.events_mock.call_args.args[2:], (start, end))
