from unittest.mock import patch

from django.db import OperationalError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.core.models import ServiceComponentState
from apps.core.platform_overview import overview_attention
from apps.core.service_status import COMPONENTS
from apps.support.models import SupportCase


class OperatorOverviewTests(TestCase):
    def setUp(self):
        self.operator = User.objects.create_user(username="overview-operator", email="overview-operator@example.com", role="platform_manager")
        self.owner = User.objects.create_user(username="overview-owner", email="overview-owner@example.com", role="business_owner")
        self.clinic = self.business("Main")
        self.other = self.business("Other")
        self.now = timezone.now()
        self.api = APIClient()
        self.api.force_authenticate(self.operator)

    def business(self, name):
        return Business.objects.create(name=name, slug=f"overview-{name}", owner=self.owner)

    def observation(self, business, component, state="healthy", **kwargs):
        return ServiceComponentState.objects.create(business=business, component=component, state=state,
            observed_at=kwargs.get("observed_at", self.now), episode=1, started_at=self.now)

    def support(self, business, **kwargs):
        return SupportCase.objects.create(business=business, created_by=self.operator, requester=self.owner,
            source="platform", subject="Help", **kwargs)

    def test_clinic_counts_match_filters_distinct_and_unknown_precedence(self):
        self.observation(self.clinic, COMPONENTS[0], "degraded")
        self.observation(self.clinic, COMPONENTS[1], "degraded")
        self.observation(self.other, COMPONENTS[0], "degraded", observed_at=self.now-timezone.timedelta(minutes=4))
        healthy = self.business("Healthy")
        for component in COMPONENTS:
            self.observation(healthy, component)
        data = self.api.get("/api/platform/overview/").data
        attention = data["attention"]["clinics"]
        self.assertEqual((attention["degraded"], attention["unknown"], attention["count"]), (1, 1, 2))
        self.assertEqual(attention["results"][0]["id"], self.clinic.pk)
        for status, count in (("degraded", 1), ("unknown", 1), ("attention", 2), ("healthy", 1)):
            response = self.api.get("/api/platform/merchants/", {"service": status})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], count)
            if status != "attention":
                self.assertTrue(all(row["service_status"]["status"] == status for row in response.data["results"]))
        self.assertEqual(data["service_status"]["businesses"]["degraded"], attention["degraded"])
        self.assertEqual(data["service_status"]["businesses"]["unknown"], attention["unknown"])

    def test_future_missing_recovery_and_combined_filters(self):
        row = self.observation(self.clinic, COMPONENTS[0], "degraded", observed_at=self.now+timezone.timedelta(minutes=5))
        self.assertEqual(overview_attention(self.operator)["clinics"]["unknown"], 2)
        row.observed_at=self.now; row.save(update_fields=["observed_at"])
        response = self.api.get("/api/platform/merchants/", {"service": "degraded", "search": "Other"})
        self.assertEqual(response.data["count"], 0)
        row.state="healthy"; row.save(update_fields=["state"])
        self.assertEqual(overview_attention(self.operator)["clinics"]["degraded"], 0)
        self.assertEqual(self.api.get("/api/platform/merchants/", {"service": "bad"}).status_code, 400)

    def test_support_metrics_match_destination_and_include_responsible(self):
        self.support(self.clinic)
        self.support(self.other, status="waiting_clinic", assigned_to=self.operator)
        self.support(self.other, status="resolved", resolved_at=self.now)
        summary = overview_attention(self.operator)["support"]
        self.assertEqual((summary["count"], summary["unassigned"], summary["waiting_clinic"]), (2, 1, 1))
        self.assertEqual(summary["results"][0]["assignee"]["id"], self.operator.pk)
        self.assertTrue(summary["results"][0]["assignee"]["available"])
        for filters, key in (({"status": "active"}, "count"), ({"status": "active", "assignee": "unassigned"}, "unassigned"), ({"status": "waiting_clinic"}, "waiting_clinic")):
            response = self.api.get("/api/platform/support-cases/", filters)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.data["count"], summary[key])

    def test_bounded_previews_keep_full_counts_and_stable_order(self):
        for i in range(13):
            self.business(f"Paged{i}")
            self.support(self.clinic)
        result = overview_attention(self.operator)
        self.assertEqual(result["clinics"]["count"], 15)
        self.assertEqual(len(result["clinics"]["results"]), 6)
        self.assertEqual(result["support"]["count"], 13)
        self.assertEqual(len(result["support"]["results"]), 6)
        self.assertEqual(result["clinics"]["results"], overview_attention(self.operator)["clinics"]["results"])

    def test_partial_sources_do_not_hide_other_sources_or_expose_exception(self):
        for source, other in (("clinic_attention", "support"), ("support_attention", "clinics")):
            with patch(f"apps.core.platform_overview.{source}", side_effect=OperationalError("PRIVATE_ERROR")):
                result = overview_attention(self.operator)
            self.assertIsNotNone(result[other])
            self.assertEqual(len(result["unavailable_sources"]), 1)
            self.assertNotIn("PRIVATE_ERROR", str(result))
        self.assertEqual(overview_attention(self.operator)["unavailable_sources"], [])

    def test_inactive_assignee_and_safe_projection(self):
        user=User.objects.create_user(username="former-operator", email="former@example.com", role="staff")
        self.support(self.clinic, assigned_to=user)
        row=overview_attention(self.operator)["support"]["results"][0]
        self.assertFalse(row["assignee"]["available"])
        self.assertEqual(set(row), {"id", "subject", "business_id", "business_name", "status", "updated_at", "assignee"})

    def test_query_budget_is_constant_and_empty_is_zero(self):
        self.assertEqual(overview_attention(self.operator)["support"]["count"], 0)
        with CaptureQueriesContext(connection) as first:
            overview_attention(self.operator)
        for i in range(12):
            self.support(self.business(f"Load{i}"), assigned_to=self.operator)
        with CaptureQueriesContext(connection) as many:
            overview_attention(self.operator)
        self.assertLessEqual(len(many), len(first)+1)
        self.assertLessEqual(len(many), 14)

    def test_component_snapshot_links_and_missing_link_table(self):
        self.observation(self.clinic, COMPONENTS[0], "degraded")
        from apps.support.incidents import link_incident
        case = self.support(self.clinic)
        link_incident(actor=self.operator, case_id=case.pk, business_id=self.clinic.pk, component=COMPONENTS[0], episode=1)
        clinics=overview_attention(self.operator)["clinics"]
        component=clinics["results"][0]["components"][0]
        self.assertEqual(component["linked_cases"], 1)
        self.assertEqual(component["observed_at"], self.now)
        self.assertEqual(component["episode"], 1)
        with patch("apps.core.platform_overview.linked_counts", side_effect=OperationalError("private")):
            clinics=overview_attention(self.operator)["clinics"]
        self.assertEqual(clinics["degraded"], 1)
        self.assertFalse(clinics["links_available"])
        self.assertIsNone(clinics["results"][0]["components"][0]["linked_cases"])

    def test_clinic_role_denied_and_role_loss(self):
        for actor in (self.owner, self.operator):
            actor.role="staff"; actor.save(update_fields=["role"])
            self.api.force_authenticate(actor)
            self.assertEqual(self.api.get("/api/platform/overview/").status_code, 403)
            self.assertEqual(self.api.get("/api/platform/merchants/", {"service":"unknown"}).status_code, 403)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.get("/api/platform/overview/").status_code, 401)
