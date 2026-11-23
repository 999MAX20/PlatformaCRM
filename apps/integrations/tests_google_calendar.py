import copy
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.integrations.credential_encryption import encrypt_credential_value
from apps.integrations.google_calendar_models import GoogleCalendarBinding, GoogleCalendarMirror
from apps.integrations import google_calendar_service as service, google_calendar_sync as sync
from apps.integrations.google_http import GoogleError
from apps.integrations.google_models import GoogleConnection
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service


@override_settings(GOOGLE_CALENDAR_ENABLED=True)
class CalendarSyncTests(TestCase):
    def setUp(self):
        self.actor = get_user_model().objects.create_user(username="calendar-owner", email="calendar@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.actor, name="Calendar", slug="calendar-test")
        BusinessMember.objects.create(business=self.business, user=self.actor, role="owner")
        self.resource = Resource.objects.create(business=self.business, name="Specialist")
        self.connection = GoogleConnection.objects.create(business=self.business, actor=self.actor,
            provider="google_calendar", status="connected", encrypted_refresh=encrypt_credential_value("refresh"),
            encrypted_access=encrypt_credential_value("access"), access_expires_at=timezone.now()+timedelta(hours=1))
        self.client = Client.objects.create(business=self.business, full_name="Test Client", phone="+77010000000", notes="medical-private")
        self.service = Service.objects.create(business=self.business, name="Consultation")
        self.start = (timezone.now()+timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)
        self.appointment = Appointment.objects.create(business=self.business, client=self.client, service=self.service,
            resource=self.resource, start_at=self.start, end_at=self.start+timedelta(minutes=30), notes="private-note")
        self.info = {"id": "calendar@example.test", "summary": "Work", "timeZone": "Asia/Almaty", "accessRole": "owner"}
        self.remote_events = {}
        self.external = []
        self.info_mock = patch.object(sync.provider, "calendar_info", return_value=self.info).start()
        self.get_mock = patch.object(sync.provider, "get_event", side_effect=lambda token, calendar, event: copy.deepcopy(self.remote_events.get(event))).start()
        self.write_mock = patch.object(sync.provider, "write_event", side_effect=self.write).start()
        self.delete_mock = patch.object(sync.provider, "delete_event", side_effect=self.delete).start()
        self.events_mock = patch.object(sync.provider, "events", side_effect=lambda *args: list(self.remote_events.values()) + self.external).start()
        self.addCleanup(patch.stopall)
        result = service.bind(self.connection, self.actor, resource_id=self.resource.pk, calendar_id=self.info["id"])
        self.binding = GoogleCalendarBinding.objects.get(pk=result["id"])

    def write(self, token, calendar, event_id, payload, existing=None):
        event = {**copy.deepcopy(payload), "id": event_id, "etag": '"version"'}
        self.remote_events[event_id] = event
        return event

    def delete(self, token, calendar, event_id, existing):
        self.remote_events[event_id] = {"id": event_id, "status": "cancelled"}

    def run_sync(self):
        return sync.sync_binding(self.binding.pk)

    def test_export_replay_privacy_and_busy_excludes_own_copy(self):
        self.run_sync()
        self.run_sync()
        self.assertEqual(self.write_mock.call_count, 1)
        payload = self.write_mock.call_args.args[3]
        self.assertEqual(payload["summary"], "Test Client: Consultation")
        self.assertNotIn(self.client.phone, str(payload))
        self.assertNotIn("private-note", str(payload))
        self.assertEqual(payload["attendees"], [])
        self.assertEqual(self.binding.busy.count(), 0)
        self.assertEqual(GoogleCalendarMirror.objects.count(), 1)

    def test_ambiguous_insert_reuses_reserved_identity(self):
        def ambiguous(*args, **kwargs):
            self.write(*args, **kwargs)
            raise GoogleError()
        self.write_mock.side_effect = ambiguous
        with self.assertRaises(GoogleError):
            self.run_sync()
        reserved = GoogleCalendarMirror.objects.get().event_id
        self.write_mock.side_effect = self.write
        self.run_sync()
        self.assertEqual(len(self.remote_events), 1)
        self.assertEqual(GoogleCalendarMirror.objects.get().event_id, reserved)

    def test_external_edit_is_repaired_without_modifying_crm(self):
        self.run_sync()
        event = next(iter(self.remote_events.values()))
        event["summary"] = "Edited in Google"
        self.run_sync()
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.start_at, self.start)
        self.assertEqual(next(iter(self.remote_events.values()))["summary"], "Test Client: Consultation")

    def test_external_delete_reserves_replacement_before_retry(self):
        self.run_sync()
        original = GoogleCalendarMirror.objects.get().event_id
        self.remote_events[original] = {"id": original, "status": "cancelled"}
        self.run_sync()
        new_id = GoogleCalendarMirror.objects.get().event_id
        self.assertNotEqual(new_id, original)
        self.assertNotIn(new_id, self.remote_events)
        self.run_sync()
        self.assertIn(new_id, self.remote_events)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Statuses.CREATED)

    def test_cancel_removes_only_owned_event(self):
        self.run_sync()
        self.appointment.status = Appointment.Statuses.CANCELLED
        self.appointment.save(update_fields=["status"])
        self.run_sync()
        self.assertEqual(self.delete_mock.call_count, 1)
        self.assertEqual(GoogleCalendarMirror.objects.get().state, "deleted")

    def test_provider_normalized_dates_and_omitted_empty_fields_do_not_rewrite(self):
        self.run_sync()
        event = next(iter(self.remote_events.values()))
        for key in ("start", "end"):
            event[key]["dateTime"] = event[key]["dateTime"].replace("+00:00", "Z")
            event[key]["timeZone"] = "UTC"
        for key in ("description", "location", "attendees"):
            del event[key]
        self.run_sync()
        self.assertEqual(self.write_mock.call_count, 1)

    def test_added_guests_prevent_update_and_delete(self):
        self.run_sync()
        next(iter(self.remote_events.values()))["attendees"] = [{"email": "guest@example.test"}]
        self.appointment.status = Appointment.Statuses.CANCELLED
        self.appointment.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            self.run_sync()
        self.assertEqual(self.write_mock.call_count, 1)
        self.delete_mock.assert_not_called()

    def test_revoked_credentials_survive_sync_rollback(self):
        self.get_mock.side_effect = GoogleError(revoked=True)
        with self.assertRaises(GoogleError):
            self.run_sync()
        self.connection.refresh_from_db()
        self.assertEqual(self.connection.status, "expired_credentials")

    def test_inactive_actor_stops_exports(self):
        self.actor.is_active = False
        self.actor.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            self.run_sync()
        self.get_mock.assert_not_called()

    def test_future_appointment_is_exported_beyond_busy_cache_horizon(self):
        self.appointment.start_at += timedelta(days=120)
        self.appointment.end_at += timedelta(days=120)
        self.appointment.save(update_fields=["start_at", "end_at"])
        self.run_sync()
        self.assertEqual(self.write_mock.call_count, 1)

    def test_reassignment_removes_previous_specialist_copy(self):
        self.run_sync()
        self.appointment.resource = Resource.objects.create(business=self.business, name="Replacement")
        self.appointment.save(update_fields=["resource"])
        self.run_sync()
        self.assertEqual(self.delete_mock.call_count, 1)

    def test_pending_replacement_is_visible_in_binding_status(self):
        self.run_sync()
        original = GoogleCalendarMirror.objects.get().event_id
        self.remote_events[original] = {"id": original, "status": "cancelled"}
        self.run_sync()
        self.binding.refresh_from_db()
        self.assertTrue(service.binding_status(self.binding)["pending"])

    def test_foreign_marker_and_guests_block_overwrite(self):
        self.run_sync()
        event = next(iter(self.remote_events.values()))
        event["extendedProperties"] = {}
        with self.assertRaises(ValidationError):
            self.run_sync()
        self.assertEqual(self.write_mock.call_count, 1)
        self.assertEqual(self.delete_mock.call_count, 0)

    def test_busy_snapshot_is_atomic_on_provider_failure(self):
        self.external = [{"id": "external", "start": {"dateTime": self.start.isoformat()},
                          "end": {"dateTime": (self.start+timedelta(hours=1)).isoformat()}}]
        self.run_sync()
        self.binding.refresh_from_db()
        previous = self.binding.last_sync_at
        self.assertEqual(self.binding.busy.count(), 1)
        self.events_mock.side_effect = GoogleError()
        with self.assertRaises(GoogleError):
            self.run_sync()
        self.binding.refresh_from_db()
        self.assertEqual(self.binding.busy.count(), 1)
        self.assertEqual(self.binding.last_sync_at, previous)
        self.assertEqual(self.binding.error_code, "sync_failed")

    def test_foreign_specialist_and_calendar_reuse_rejected(self):
        other = Business.objects.create(owner=self.actor, name="Other", slug="calendar-other")
        resource = Resource.objects.create(business=other, name="Foreign")
        with self.assertRaises(ValidationError):
            service.bind(self.connection, self.actor, resource_id=resource.pk, calendar_id=self.info["id"])
        second = Resource.objects.create(business=self.business, name="Second")
        with self.assertRaises(ValidationError):
            service.bind(self.connection, self.actor, resource_id=second.pk, calendar_id=self.info["id"])
        self.assertEqual(GoogleCalendarBinding.objects.count(), 1)

    def test_disabled_connection_and_actor_revocation_prevent_remote_calls(self):
        self.connection.status = "disconnected"
        self.connection.save(update_fields=["status"])
        with self.assertRaises(ValidationError):
            self.run_sync()
        self.assertFalse(self.get_mock.called)
        self.assertFalse(self.write_mock.called)

    @override_settings(GOOGLE_CALENDAR_ENABLED=False)
    def test_disabled_runtime_has_no_external_effects(self):
        self.assertEqual(sync.process_due(), {"synced": 0, "failed": 0})
        with self.assertRaises(ValidationError):
            self.run_sync()
        self.assertFalse(self.write_mock.called)
