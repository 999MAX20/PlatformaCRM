from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.integrations import tests_google_calendar as fixtures
from apps.integrations.google_calendar_models import GoogleCalendarBinding
from apps.integrations.google_models import GoogleOAuthAttempt
from apps.scheduling.models import Resource


@override_settings(GOOGLE_CALENDAR_ENABLED=True)
class CalendarApiTests(TestCase):
    write = fixtures.CalendarSyncTests.write
    delete = fixtures.CalendarSyncTests.delete

    def setUp(self):
        fixtures.CalendarSyncTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.actor)
        self.base = f"/api/integrations/google/connections/{self.connection.pk}/calendar/"

    def test_bind_confirmation_required_and_retry_is_idempotent(self):
        data = {"resource_id": self.resource.pk, "calendar_id": self.info["id"]}
        self.assertEqual(self.api.post(self.base + "bind/", data).status_code, 400)
        data["confirm_data_export"] = False
        self.assertEqual(self.api.post(self.base + "bind/", data).status_code, 400)
        data["confirm_data_export"] = True
        first = self.api.post(self.base + "bind/", data)
        second = self.api.post(self.base + "bind/", data)
        self.assertEqual(first.status_code, 200, first.data)
        self.assertEqual(first.data["id"], second.data["id"])
        self.assertEqual(GoogleCalendarBinding.objects.count(), 1)

    def test_status_minimizes_data_and_sync_only_queues(self):
        result = self.api.get(self.base + "bindings/")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result["Cache-Control"], "no-store")
        self.assertNotIn("refresh", str(result.data))
        self.assertNotIn(self.client.phone, str(result.data))
        result = self.api.post(self.base + "sync/", {"binding_id": self.binding.pk})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data, {"queued": True})
        self.write_mock.assert_not_called()

    def test_other_actor_cannot_read_or_mutate_binding(self):
        other = get_user_model().objects.create_user(username="other-calendar", email="other-calendar@example.test")
        self.api.force_authenticate(other)
        self.assertEqual(self.api.get(self.base + "bindings/").status_code, 404)
        self.assertEqual(self.api.post(self.base + "sync/", {"binding_id": self.binding.pk}).status_code, 404)
        self.write_mock.assert_not_called()

    def test_pause_and_resume_require_first_refresh(self):
        data = {"binding_id": str(self.binding.pk), "enabled": False}
        result = self.api.post(self.base + "enabled/", data, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertFalse(result.data["enabled"])
        data["enabled"] = True
        result = self.api.post(self.base + "enabled/", data, format="json")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertTrue(result.data["stale"])

    @override_settings(GOOGLE_CALENDAR_ENABLED=False)
    def test_runtime_off_denies_grant_and_writes_but_allows_pause(self):
        result = self.api.post("/api/integrations/google/start/", {
            "business": self.business.pk, "provider": "google_calendar"}, format="json")
        self.assertEqual(result.status_code, 400, result.data)
        self.assertEqual(GoogleOAuthAttempt.objects.count(), 0)
        self.assertEqual(self.api.get(self.base + "calendars/").status_code, 400)
        self.assertEqual(self.api.post(self.base + "sync/", {"binding_id": self.binding.pk}).status_code, 400)
        result = self.api.post(self.base + "enabled/", {"binding_id": str(self.binding.pk), "enabled": False}, format="json")
        self.assertEqual(result.status_code, 200, result.data)

    def test_inactive_specialist_cannot_be_bound(self):
        resource = Resource.objects.create(business=self.business, name="Inactive", is_active=False)
        result = self.api.post(self.base + "bind/", {"resource_id": resource.pk,
            "calendar_id": self.info["id"], "confirm_data_export": True}, format="json")
        self.assertEqual(result.status_code, 400, result.data)
