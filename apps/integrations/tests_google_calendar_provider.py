from datetime import datetime, timezone
from unittest.mock import patch

from django.test import SimpleTestCase

from apps.integrations import google_calendar_provider as provider
from apps.integrations.google_http import GoogleError


class CalendarProviderTests(SimpleTestCase):
    def test_all_day_uses_calendar_zone_and_exclusive_end(self):
        start, end = provider.event_interval({"start": {"date": "2026-11-23"},
            "end": {"date": "2026-11-24"}}, "Asia/Almaty")
        self.assertEqual(start.hour, 0)
        self.assertEqual((end - start).total_seconds(), 86400)
        self.assertEqual(start.utcoffset().total_seconds(), 18000)

    def test_transparent_cancelled_declined_are_free(self):
        for event in ({"status": "cancelled"}, {"transparency": "transparent"},
                      {"attendees": [{"self": True, "responseStatus": "declined"}]}):
            self.assertIsNone(provider.event_interval(event, "UTC"))

    def test_invalid_intervals_fail_closed(self):
        for event in ({}, {"start": {"dateTime": "2026-11-23T10:00:00"}, "end": {}},
                      {"start": {"date": "2026-11-24"}, "end": {"date": "2026-11-23"}}):
            with self.assertRaises(GoogleError):
                provider.event_interval(event, "UTC")

    @patch.object(provider, "google_request")
    def test_pagination_and_minimized_event_fields(self, request):
        request.side_effect = [{"items": [{"id": "one"}], "nextPageToken": "next"}, {"items": [{"id": "two"}]}]
        start = datetime(2026, 11, 23, tzinfo=timezone.utc)
        result = provider.events("secret", "specialist@example.test", start, start)
        self.assertEqual([item["id"] for item in result], ["one", "two"])
        self.assertIn("pageToken=next", request.call_args.args[0])
        self.assertIn("specialist%40example.test", request.call_args.args[0])
        self.assertNotIn("description", request.call_args.args[0])
        self.assertNotIn("summary", request.call_args.args[0])

    @patch.object(provider, "google_request", return_value={"nextPageToken": "same"})
    def test_repeating_page_is_error_not_partial_success(self, request):
        with self.assertRaises(GoogleError):
            list(provider.pages("https://www.googleapis.com/calendar/v3/test", "secret", {}))
        self.assertEqual(request.call_count, 2)

    @patch.object(provider, "google_request", return_value={})
    def test_write_uses_reserved_id_and_conditional_update(self, request):
        provider.write_event("secret", "calendar", "reserved", {"summary": "Name"})
        self.assertEqual(request.call_args.kwargs["payload"]["id"], "reserved")
        provider.write_event("secret", "calendar", "reserved", {"summary": "Name"}, {"etag": '"v2"'})
        self.assertEqual(request.call_args.kwargs["if_match"], '"v2"')
        self.assertEqual(request.call_args.kwargs["method"], "PUT")

    @patch.object(provider, "google_request", side_effect=GoogleError(status=410))
    def test_gone_event_requires_new_identity(self, request):
        self.assertEqual(provider.get_event("secret", "calendar", "reserved"),
                         {"id": "reserved", "status": "cancelled"})

    @patch.object(provider, "google_request", side_effect=GoogleError(status=404))
    def test_missing_event_preserves_reserved_identity(self, request):
        self.assertIsNone(provider.get_event("secret", "calendar", "reserved"))

    @patch.object(provider, "google_request", side_effect=GoogleError(status=410))
    def test_delete_is_idempotent(self, request):
        provider.delete_event("secret", "calendar", "reserved", {"etag": '"v2"'})
