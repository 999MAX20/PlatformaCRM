from django.test import TestCase, override_settings
from django.utils import timezone
from django.db import connection
from django.test.utils import CaptureQueriesContext
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.automations.models import AutomationRun
from apps.businesses.models import Business


class PlatformListTests(TestCase):
    def setUp(self):
        self.platform = User.objects.create_user(username="s02-platform", email="s02-platform@example.com", role=User.Roles.PLATFORM_MANAGER)
        self.owner = User.objects.create_user(username="s02-owner", email="s02-owner@example.com", role=User.Roles.BUSINESS_OWNER)
        self.api = APIClient()
        self.api.force_authenticate(self.platform)
        for index in range(5):
            Business.objects.create(owner=self.owner, name=f"Clinic {index}", slug=f"s02-{index}")

    def test_search_paginates_all_matches_with_stable_order(self):
        first = self.api.get("/api/platform/merchants/", {"search": "Clinic", "page_size": 2})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["count"], 5)
        self.assertEqual(len(first.data["results"]), 2)
        second = self.api.get("/api/platform/merchants/", {"search": "Clinic", "page_size": 2, "page": 2})
        self.assertEqual(second.status_code, 200)
        self.assertTrue(set(row["id"] for row in first.data["results"]).isdisjoint(row["id"] for row in second.data["results"]))
        match = self.api.get("/api/platform/merchants/", {"search": "Clinic 0"})
        self.assertEqual(match.data["count"], 1)
        self.assertEqual(match.data["results"][0]["name"], "Clinic 0")
        self.assertEqual(self.api.get("/api/platform/merchants/", {"search": "absent"}).data["count"], 0)

    def test_invalid_filter_is_400_and_merchant_is_denied(self):
        for params in ({"status": "invalid"}, {"page_size": "many"}, {"page_size": 0}, {"page_size": 101}):
            with self.subTest(params=params):
                self.assertEqual(self.api.get("/api/platform/merchants/", params).status_code, 400)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get("/api/platform/merchants/", {"search": "Clinic"}).status_code, 403)

    def test_overview_reports_real_failed_runs(self):
        AutomationRun.objects.create(business=Business.objects.first(), trigger_type="lead_created", status=AutomationRun.Statuses.FAILED, run_after=timezone.now())
        response = self.api.get("/api/platform/overview/")
        self.assertEqual(response.status_code, 200)
        self.assertGreaterEqual(response.data["errors"]["count"], 1)

    def test_overview_includes_businesses_beyond_500_without_per_business_queries(self):
        Business.objects.bulk_create([
            Business(owner=self.owner, name=f"Extra {index}", slug=f"s02-extra-{index}")
            for index in range(501)
        ])
        with CaptureQueriesContext(connection) as queries:
            response = self.api.get("/api/platform/overview/")
        self.assertEqual(response.status_code, 200)
        summary = response.data["operations_summary"]
        self.assertEqual(summary["total_monitored"], 506)
        self.assertEqual(summary["no_sales_data_merchants"], 506)
        self.assertLess(len(queries), 50)


class PlatformSupportJournalTests(TestCase):
    @override_settings(CORS_ALLOWED_ORIGINS=["http://localhost:5173"])
    def test_support_preflight_allows_step_up_header_only_for_allowed_origin(self):
        for origin, allowed in (("http://localhost:5173", True), ("https://untrusted.example", False)):
            response = self.client.options(
                "/api/platform/merchants/1/support-actions/",
                HTTP_ORIGIN=origin,
                HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
                HTTP_ACCESS_CONTROL_REQUEST_HEADERS="authorization,content-type,x-zani-mfa-step-up",
            )
            if allowed:
                self.assertEqual(response.headers["access-control-allow-origin"], origin)
                self.assertIn("x-zani-mfa-step-up", response.headers["access-control-allow-headers"])
            else:
                self.assertNotIn("access-control-allow-origin", response.headers)

    def setUp(self):
        from apps.core import tests_platform_operations
        self.f = tests_platform_operations.PlatformOperationsDashboardTests()
        self.f.setUp()
        self.f.api.force_authenticate(self.f.platform)
        self.url = f"/api/platform/merchants/{self.f.business.pk}/support-actions/"

    def test_journal_is_paginated_business_scoped_and_merchant_denied(self):
        from apps.core.models import AuditLog
        other = Business.objects.create(owner=self.f.owner, name="Other", slug="s02-journal-other")
        for index in range(7):
            AuditLog.objects.create(business=self.f.business, actor=self.f.platform,
                action="update", entity_type="platform_support_action", entity_id=str(self.f.business.pk), metadata={"note": f"Note {index}"})
        AuditLog.objects.create(business=other, action="update", entity_type="platform_support_action", metadata={"note": "Foreign note"})
        first = self.f.api.get(self.url, {"page_size": 5})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["count"], 7)
        second = self.f.api.get(self.url, {"page_size": 5, "page": 2})
        self.assertEqual(len(second.data["results"]), 2)
        self.assertNotIn("Foreign note", str(first.data) + str(second.data))
        self.assertEqual(self.f.api.post(self.url, {"note": "Denied"}).status_code, 403)
        self.f.api.force_authenticate(self.f.owner)
        self.assertEqual(self.f.api.get(self.url).status_code, 403)

    def test_invalid_notes_return_400_without_audit(self):
        from apps.core.models import AuditLog
        self.f._allow_support_notes()
        step_up = self.f._authenticate_platform_with_step_up()
        before = AuditLog.objects.filter(entity_type="platform_support_action").count()
        for payload in ({"note": []}, {"note": " "}, {"note": "a" * 4001}, {"note": "Valid", "action_type": {"invalid": True}}):
            with self.subTest(payload_type=type(payload["note"]).__name__):
                response = self.f.api.post(self.url, payload, format="json", **step_up)
                self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(AuditLog.objects.filter(entity_type="platform_support_action").count(), before)
