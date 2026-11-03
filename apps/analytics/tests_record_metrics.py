import csv
import io

from django.test import TestCase

from apps.analytics.tests_workspace import AnalyticsWorkspaceTests
from apps.businesses.models import BusinessCapability


class RecordMetricsTests(TestCase):
    setUp = AnalyticsWorkspaceTests.setUp
    report = AnalyticsWorkspaceTests.report
    appointment = AnalyticsWorkspaceTests.appointment

    def test_record_sources_team_and_rates_use_visit_dates_and_responsible_user(self):
        self.appointment(source="manual", status="completed", responsible_user=self.owner)
        self.appointment(source="manual", status="rescheduled", responsible_user=self.owner)
        self.appointment(source="website", status="no_show")
        self.appointment(at="2026-11-01T10:00:00+05:00", source="website", status="completed")
        result = self.report().data
        self.assertEqual(result["appointments"]["total"], 3)
        self.assertEqual(result["appointments"]["completed"], 1)
        self.assertEqual(result["appointments"]["completion_rate"], 33.3)
        self.assertEqual(result["record_sources"], [
            {"source": "manual", "total": 2, "completed": 1, "cancelled": 0, "no_show": 0},
            {"source": "website", "total": 1, "completed": 0, "cancelled": 0, "no_show": 1},
        ])
        owner = next(row for row in result["team"]["rows"] if row["id"] == self.owner.pk)
        self.assertEqual(owner["appointments"], 2)
        self.assertEqual(owner["completed_appointments"], 1)

    def test_new_export_has_record_schema_and_keeps_old_schema(self):
        self.appointment(source="manual", status="completed")
        params = {"business": self.business.pk, "start": "2026-10-01", "end": "2026-10-14"}
        response = self.api.get("/api/analytics/reports/export/", {**params, "report": "records_sources"})
        self.assertEqual(response.status_code, 200)
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertEqual(rows[0]["total"], "1")
        self.assertNotIn("leads", rows[0])
        legacy = self.api.get("/api/analytics/reports/export/", {**params, "report": "workspace_sources"})
        self.assertEqual(legacy.status_code, 200)
        self.assertIn("leads", legacy.content.decode().splitlines()[0])

    def test_disabled_appointment_module_does_not_leak_zero_as_available_data(self):
        self.appointment(source="manual", status="completed")
        BusinessCapability.objects.update_or_create(business=self.business, module_key="appointments", defaults={"is_enabled": False})
        result = self.report().data
        self.assertFalse(result["availability"]["appointments"])
        self.assertIsNone(result["appointments"]["completed"])
        self.assertIsNone(result["appointments"]["completion_rate"])
        self.assertIsNone(result["current"]["pending_records"])
        self.assertEqual(result["record_sources"], [])
        self.assertTrue(all(row["appointments"] is None for row in result["team"]["rows"]))
