from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings
from django.utils import timezone

from apps.accounts.models import User
from apps.analytics.models import ReportWidget
from apps.analytics import tests as fixtures
from apps.businesses.models import BusinessCapability, BusinessMember
from apps.crm.models import Deal
from apps.leads.models import Lead
from apps.scheduling.models import Appointment
from apps.tasks.models import Task
from apps.core.models import ExportJob
from apps.core.export_jobs import process_export_job


class AnalyticsWorkspaceTests(TestCase):
    setUp = fixtures.OwnerDashboardAnalyticsTests.setUp

    def report(self, **params):
        return self.api.get("/api/analytics/reports/summary/", {
            "business": self.business.pk, "view": "workspace", "start": "2026-10-01", "end": "2026-10-14", **params,
        })

    def lead(self, at="2026-10-01T00:00:00+05:00", **kwargs):
        row = Lead.objects.create(business=self.business, client=self.client, **kwargs)
        Lead.objects.filter(pk=row.pk).update(created_at=datetime.fromisoformat(at))
        return row

    def deal(self, lead=None, at="2026-10-02T10:00:00+05:00", **kwargs):
        row = Deal.objects.create(business=self.business, client=self.client, pipeline=self.pipeline,
                                  stage=self.stage, lead=lead, title="Result", **kwargs)
        Deal.objects.filter(pk=row.pk).update(created_at=datetime.fromisoformat(at))
        return row

    def appointment(self, at="2026-10-01T00:00:00+05:00", **kwargs):
        start = datetime.fromisoformat(at)
        return Appointment.objects.create(business=self.business, client=self.client, service=self.service,
                                          start_at=start, end_at=start + timedelta(hours=1), **kwargs)

    def test_event_dates_and_archive_preserve_history(self):
        lead = self.lead(is_archived=True)
        self.deal(lead, at="2026-09-01T10:00:00+05:00", is_archived=True,
                  status=Deal.Statuses.WON, won_at=datetime(2026, 10, 3, tzinfo=ZoneInfo("Asia/Almaty")))
        self.deal(status=Deal.Statuses.WON, won_at=datetime(2026, 9, 3, tzinfo=ZoneInfo("Asia/Almaty")))
        appointment = self.appointment(is_archived=True, status=Appointment.Statuses.COMPLETED)
        Appointment.objects.filter(pk=appointment.pk).update(created_at=datetime(2026, 9, 1, tzinfo=ZoneInfo("Asia/Almaty")))
        self.appointment(at="2026-11-01T10:00:00+05:00")
        result = self.report()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["leads"]["total"], 1)
        self.assertEqual(result.data["deals"]["won"], 1)
        self.assertEqual(result.data["appointments"]["total"], 1)
        self.assertEqual(result.data["current"]["new_leads"], 0)
        self.assertEqual(ReportWidget.objects.count(), 0, "GET workspace must not create widgets")

    def test_distinct_cohort_conversion_does_not_count_later_or_unrelated_deals(self):
        first = self.lead()
        later = self.lead()
        self.deal(first)
        self.deal(first)
        self.deal(later, at="2026-10-15T00:00:00+05:00")
        self.deal()
        result = self.report().data
        self.assertEqual(result["leads"], {"total": 2, "converted": 1, "conversion_rate": 50.0})
        self.assertEqual(result["sources"][0]["conversion_rate"], 50.0)

    def test_business_timezone_boundaries_are_inclusive_days(self):
        for at in ("2026-09-30T18:59:59+00:00", "2026-09-30T19:00:00+00:00",
                   "2026-10-14T18:59:59+00:00", "2026-10-14T19:00:00+00:00"):
            self.lead(at=at)
            self.appointment(at=at)
        result = self.report().data
        self.assertEqual(result["leads"]["total"], 2)
        self.assertEqual(result["appointments"]["total"], 2)

    def test_services_count_beyond_first_page(self):
        for _ in range(53):
            self.appointment(status=Appointment.Statuses.NO_SHOW)
        result = self.report().data
        self.assertEqual(result["services"][0]["total"], 53)
        self.assertEqual(result["appointments"]["no_show_rate"], 100.0)

    def test_invalid_dates_rejected(self):
        for params in ({"start": "2026-02-30"}, {"start": "bad"}, {"start": "2026-11-01"},
                       {"start": "2000-01-01"}, {"end": "2026-13-01"}):
            with self.subTest(params=params):
                self.assertEqual(self.report(**params).status_code, 400)

    def test_empty_report_has_undefined_rates_and_unavailable_finance(self):
        result = self.report().data
        self.assertEqual(result["leads"]["total"], 0)
        self.assertIsNone(result["leads"]["conversion_rate"])
        self.assertIsNone(result["appointments"]["no_show_rate"])
        self.assertEqual(result["financial"]["state"], "unavailable")
        self.assertIsNone(result["financial"]["receipts"])

    def test_current_tasks_ignore_report_period_but_respect_snooze_and_archive(self):
        for extra in ({}, {"is_archived": True}, {"snoozed_until": timezone.now() + timedelta(days=1)}):
            Task.objects.create(business=self.business, title="Due", assignee=self.owner,
                                due_at=timezone.now() - timedelta(hours=1), **extra)
        result = self.report(start="2020-01-01", end="2020-01-10").data
        self.assertEqual(result["current"]["overdue_tasks"], 1)

    def test_foreign_tenant_and_operator_denied(self):
        self.assertEqual(self.report(business=self.other_business.pk).status_code, 400)
        operator = User.objects.create_user(username="operator", email="operator@example.com", password="pass")
        BusinessMember.objects.create(business=self.business, user=operator, role=BusinessMember.Roles.OPERATOR)
        self.api.force_authenticate(operator)
        self.assertEqual(self.report().status_code, 403)

    def test_manager_cannot_see_other_owner_records_or_team_counts(self):
        manager = User.objects.create_user(username="manager", email="manager@example.com", password="pass")
        BusinessMember.objects.create(business=self.business, user=manager, role=BusinessMember.Roles.MANAGER)
        mine = self.lead(responsible_user=manager)
        self.lead(responsible_user=self.owner)
        self.deal(mine, owner=self.owner)
        self.api.force_authenticate(manager)
        result = self.report().data
        self.assertEqual(result["leads"]["total"], 1)
        self.assertEqual(result["leads"]["converted"], 0)
        self.assertEqual([row["id"] for row in result["team"]["rows"]], [manager.pk])
        self.assertIsNone(result["financial"]["receipts"])

    def test_disabled_resource_is_unavailable_not_zero(self):
        self.lead()
        BusinessCapability.objects.update_or_create(business=self.business, module_key="deals", defaults={"is_enabled": False})
        result = self.report().data
        self.assertFalse(result["availability"]["deals"])
        self.assertIsNone(result["deals"]["won"])
        self.assertIsNone(result["leads"]["converted"])
        self.assertIsNone(result["sources"][0]["converted"])

    def export(self, **params):
        return self.api.get("/api/analytics/reports/export/", {
            "business": self.business.pk, "report": "workspace_sources", "start": "2026-10-01", "end": "2026-10-14", **params,
        })

    @override_settings(REPORT_EXPORT_SYNC_MAX_DAYS=30)
    def test_csv_matches_period_and_distinct_conversion(self):
        import csv, io
        lead = self.lead()
        self.deal(lead)
        self.deal(lead)
        self.lead(at="2026-09-01T00:00:00+05:00")
        response = self.export()
        self.assertEqual(response.status_code, 200)
        rows = list(csv.DictReader(io.StringIO(response.content.decode())))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["leads"], "1")
        self.assertEqual(rows[0]["converted"], "1")
        self.assertEqual(rows[0]["start"], "2026-10-01")

    @override_settings(REPORT_EXPORT_SYNC_MAX_DAYS=2)
    def test_queued_export_preserves_period_and_uses_workspace(self):
        self.lead()
        response = self.export()
        self.assertEqual(response.status_code, 202)
        job = process_export_job(response.data["id"])
        self.assertEqual(job.status, ExportJob.Statuses.SUCCEEDED)
        with job.result_file.open("rb") as result:
            content = result.read().decode()
        self.assertIn("conversion_rate", content)
        self.assertIn("2026-10-01", content)
        download = self.api.get(f"/api/export-jobs/{job.pk}/download/", {"business": self.business.pk})
        self.assertEqual(download.status_code, 200)
        self.assertIn(b"conversion_rate", b"".join(download.streaming_content))
        denied = self.api.get(f"/api/export-jobs/{job.pk}/download/", {"business": self.other_business.pk})
        self.assertEqual(denied.status_code, 404)

    def test_workspace_export_rejects_invalid_date(self):
        self.assertEqual(self.export(start="2026-02-30").status_code, 400)
