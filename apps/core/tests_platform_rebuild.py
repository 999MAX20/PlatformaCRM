from unittest.mock import patch

from django.db import connection, OperationalError
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.billing.models import Subscription, SubscriptionPlan
from apps.core.models import ServiceComponentState
from apps.core.platform_reads import read_platform_source
from apps.core.platform_selectors import _merchant_counts, _merchant_health
from apps.core.service_status import COMPONENTS, business_service_status, business_service_status_many
from apps.integrations.models import BusinessConnector
from apps.leads.models import LeadFormSubmissionError


class PlatformReadModelTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="rebuild-owner", email="rebuild-owner@example.com", role=User.Roles.BUSINESS_OWNER)
        self.platform = User.objects.create_user(username="rebuild-staff", email="rebuild-staff@example.com", role=User.Roles.PLATFORM_MANAGER)
        self.business = Business.objects.create(name="Clinic without optional setup", slug="rebuild-clinic", owner=self.owner)
        self.other = Business.objects.create(name="Other clinic", slug="rebuild-other", owner=self.owner)
        self.api = APIClient()
        self.api.force_authenticate(self.platform)

    def test_optional_features_and_no_activity_are_not_failures_or_fabricated_activity(self):
        response = self.api.get(f"/api/platform/merchants/{self.business.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["health"]["status"], "clear")
        self.assertEqual(response.data["health"]["blockers"], [])
        self.assertIsNone(response.data["health"]["score"])
        self.assertEqual(response.data["service_status"]["status"], "unknown")
        self.assertIsNone(response.data["latest_activity_at"])
        self.assertNotIn("request_sales_upload", [step["key"] for step in response.data["support_workflow"]["next_steps"]])
        self.assertEqual(response.data["operations"]["lead_count"], 0)

    def test_failed_source_keeps_other_counts_and_does_not_report_zero_or_clear(self):
        with patch("apps.core.platform_selectors.BusinessConnector.objects.filter", side_effect=OperationalError("secret-value")):
            response = self.api.get(f"/api/platform/merchants/{self.business.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["operations"]["failed_connectors"])
        self.assertEqual(response.data["operations"]["lead_count"], 0)
        self.assertEqual(response.data["health"]["status"], "unknown")
        self.assertIn("integrations.businessconnector", response.data["operations"]["unavailable_sources"])
        self.assertNotIn("secret-value", str(response.data))

    def test_form_error_window_and_business_scope(self):
        old = LeadFormSubmissionError.objects.create(business=self.business, error_message="old error")
        LeadFormSubmissionError.objects.filter(pk=old.pk).update(created_at=timezone.now()-timezone.timedelta(days=31))
        LeadFormSubmissionError.objects.create(business=self.other, error_message="other error")
        counts = _merchant_counts(self.business)
        self.assertEqual(counts["form_errors"], 0)
        self.assertEqual(_merchant_health(self.business, counts)["status"], "clear")
        LeadFormSubmissionError.objects.create(business=self.business, error_message="recent error")
        self.assertEqual(_merchant_counts(self.business)["form_errors"], 1)

    def test_pending_connector_is_setup_not_connected_or_service_failure(self):
        BusinessConnector.objects.create(business=self.business, name="Pending", provider="website", capability="sales", status="needs_attention")
        response = self.api.get(f"/api/platform/merchants/{self.business.pk}/")
        self.assertFalse(response.data["health"]["checks"]["has_connected_source"])
        self.assertEqual(response.data["health"]["status"], "clear")
        self.assertEqual(response.data["operations"]["pending_connectors"], 1)
        self.assertEqual(response.data["service_status"]["status"], "unknown")

    def test_batched_service_matches_existing_contract_and_excludes_other_clinic(self):
        now = timezone.now()
        for component in COMPONENTS:
            ServiceComponentState.objects.create(business=self.business, component=component, observed_at=now, state="healthy")
        ServiceComponentState.objects.create(business=self.other, component=COMPONENTS[0], observed_at=now, state="degraded")
        batch = business_service_status_many([self.business.pk], now=now)
        self.assertEqual(batch[self.business.pk], business_service_status(self.business, now=now))
        self.assertNotIn(self.other.pk, batch)
        stale = business_service_status_many([self.business.pk], now=now+timezone.timedelta(seconds=181))
        self.assertEqual(stale[self.business.pk]["status"], "unknown")
        self.assertEqual(stale[self.business.pk]["components"][0]["last_state"], "healthy")

    def test_missing_service_schema_does_not_hide_clinics_or_operations(self):
        with patch("apps.core.platform_selectors.business_service_status_many", side_effect=OperationalError("missing table private")):
            response = self.api.get("/api/platform/merchants/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(response.data["results"][0]["service_status"]["status"], "unknown")
        self.assertEqual(response.data["results"][0]["operations"]["lead_count"], 0)
        self.assertNotIn("private", str(response.data))
        with patch("apps.core.operations_health.platform_service_status", side_effect=OperationalError("missing table private")):
            response = self.api.get("/api/platform/operations-health/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["service_status"]["status"], "unknown")
        self.assertEqual(response.data["runtime"]["queue"]["automation_runs"]["pending"], 0)
        self.assertEqual(response.data["unavailable_sources"], ["service_status"])

    def test_failed_queue_has_null_measurements_and_keeps_other_sources(self):
        with patch("apps.core.operations_health._queue_summary", side_effect=OperationalError("private error")):
            response = self.api.get("/api/platform/operations-health/")
        self.assertIsNone(response.data["runtime"]["queue"]["automation_runs"]["pending"])
        self.assertEqual(response.data["summary"]["active_support_grants"], 0)
        self.assertEqual(response.data["unavailable_sources"], ["queue"])
        self.assertNotIn("private error", str(response.data))

    def test_database_error_savepoint_allows_later_reads_in_same_transaction(self):
        def bad_query():
            with connection.cursor() as cursor:
                cursor.execute("SELECT missing_column FROM definitely_missing_platform_table")
        self.assertIsNone(read_platform_source(bad_query))
        self.assertEqual(Business.objects.count(), 2)

    def test_overview_keeps_totals_when_optional_monitor_unavailable(self):
        with patch("apps.core.platform_views.platform_service_status", side_effect=OperationalError("private")):
            response = self.api.get("/api/platform/overview/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["total_businesses"], 2)
        self.assertEqual(response.data["operations_summary"]["attention_merchants"], 0)
        self.assertEqual(response.data["service_status"]["status"], "unknown")
        self.assertNotIn("private", str(response.data))

    def test_clinic_user_cannot_access_platform_read_models(self):
        self.api.force_authenticate(self.owner)
        for url in ("overview/", "merchants/", f"merchants/{self.business.pk}/", "operations-health/"):
            with self.subTest(url=url):
                self.assertEqual(self.api.get(f"/api/platform/{url}").status_code, 403)

    def test_paid_financial_logic_is_preserved_and_separate_from_service(self):
        plan = SubscriptionPlan.objects.create(code="rebuild-paid", name="Paid", monthly_price=4200)
        Subscription.objects.create(business=self.business, plan=plan, status=Subscription.Statuses.ACTIVE)
        Subscription.objects.create(business=self.other, plan=plan, status=Subscription.Statuses.TRIAL)
        response = self.api.get("/api/platform/overview/")
        self.assertEqual(float(response.data["mrr_estimate"]), 4200)
        self.assertEqual(response.data["active_subscriptions"], 1)
        self.assertEqual(response.data["service_status"]["status"], "unknown")
        self.assertEqual(response.data["operations_summary"]["attention_merchants"], 0)

    def test_partial_summary_does_not_count_unavailable_sources_as_empty(self):
        with patch("apps.core.platform_selectors.BusinessEvent.objects.filter", side_effect=OperationalError("private")), patch(
            "apps.core.platform_selectors.LeadFormSubmissionError.objects.filter", side_effect=OperationalError("private")), patch(
            "apps.core.platform_selectors.BusinessConnector.objects.filter", side_effect=OperationalError("private")):
            response = self.api.get("/api/platform/overview/")
        self.assertEqual(response.status_code, 200)
        summary = response.data["operations_summary"]
        for field in ("attention_merchants", "no_sales_data_merchants", "form_error_merchants", "form_errors_30d", "failed_connectors"):
            self.assertIsNone(summary[field], field)
        self.assertEqual(summary["total_monitored"], 2)
        self.assertEqual(summary["handoff_conversations"], 0)

    def test_status_filter_is_server_scoped_and_stable(self):
        self.business.status = Business.Statuses.ACTIVE
        self.business.save(update_fields=["status"])
        response = self.api.get("/api/platform/merchants/", {"status": "active"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual([row["id"] for row in response.data["results"]], [self.business.pk])

    def test_billing_source_failure_does_not_hide_operational_overview(self):
        def unavailable_billing(execute, sql, params, many, context):
            if "billing_subscription" in sql:
                raise OperationalError("missing optional table private")
            return execute(sql, params, many, context)
        with connection.execute_wrapper(unavailable_billing):
            response = self.api.get("/api/platform/overview/")
        self.assertEqual(response.status_code, 200)
        self.assertIsNone(response.data["mrr_estimate"])
        self.assertIsNone(response.data["active_subscriptions"])
        self.assertEqual(response.data["total_businesses"], 2)
        self.assertEqual(response.data["operations_summary"]["attention_merchants"], 0)
        self.assertNotIn("private", str(response.data))
