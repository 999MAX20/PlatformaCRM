from datetime import timedelta
from unittest.mock import patch

from django.db import OperationalError, connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.automations.models import AutomationRun
from apps.businesses.models import Business
from apps.core.models import ServiceComponentState
from apps.integrations.models import BusinessConnector, IntegrationEventLog, WebhookDeliveryLog, WebhookEndpoint
from apps.support.incidents import link_incident
from apps.support.services import create_case


class PlatformWorklistTests(TestCase):
    url = "/api/platform/operations-worklist/"

    def setUp(self):
        self.staff = User.objects.create_user(username="worklist-staff", email="worklist-staff@example.com", role="platform_manager")
        self.owner = User.objects.create_user(username="worklist-owner", email="worklist-owner@example.com", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="North clinic", slug="worklist-north")
        self.other = Business.objects.create(owner=self.owner, name="South clinic", slug="worklist-south")
        self.now = timezone.now()
        self.api = APIClient()
        self.api.force_authenticate(self.staff)

    def state(self, business=None, component="exports", **kwargs):
        return ServiceComponentState.objects.create(business=business or self.business, component=component,
            **{"episode": 1, "state": "degraded", "started_at": self.now-timedelta(minutes=10), "observed_at": self.now, "affected_count": 2, **kwargs})

    def test_complete_count_pagination_and_stable_order_beyond_ten(self):
        for index in range(13):
            business = Business.objects.create(owner=self.owner, name=f"Paged {index}", slug=f"worklist-{index}")
            self.state(business)
        first = self.api.get(self.url, {"page_size": 10})
        self.assertEqual(first.status_code, 200)
        self.assertEqual(first.data["count"], 13)
        second = self.api.get(self.url, {"page_size": 10, "page": 2})
        ids = [row["id"] for row in first.data["results"]+second.data["results"]]
        self.assertEqual(len(set(ids)), 13)
        self.assertEqual(ids, sorted(ids))

    def test_business_component_and_freshness_filter(self):
        self.state()
        self.state(component="files", observed_at=self.now-timedelta(minutes=4))
        self.state(self.other)
        response = self.api.get(self.url, {"business": self.business.pk, "component": "files", "freshness": "unknown"})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["status"], "unknown")
        self.assertEqual(response.data["results"][0]["business_name"], self.business.name)
        self.assertEqual(self.api.get(self.url, {"search": "South"}).data["count"], 1)
        self.assertEqual(self.api.get(self.url, {"search": str(self.business.pk)}).data["count"], 2)
        self.assertEqual(self.api.get(self.url, {"business": self.other.pk, "component": "files"}).data["count"], 0)

    def test_recovery_stale_and_future_are_not_live_failures(self):
        self.state(state="healthy")
        self.state(component="files", state="healthy", observed_at=self.now-timedelta(minutes=4))
        self.state(self.other, observed_at=self.now+timedelta(minutes=1))
        self.assertEqual(self.api.get(self.url, {"freshness": "fresh"}).data["count"], 0)
        unknown = self.api.get(self.url, {"freshness": "unknown"}).data
        self.assertEqual(unknown["count"], 2)
        self.assertTrue(all(row["status"] == "unknown" for row in unknown["results"]))

    def test_case_counts_are_scoped_to_business_component_and_episode(self):
        self.state(); self.state(self.other)
        case = create_case(actor=self.staff, business_id=self.business.pk, subject="Help", text="private question", idempotency_key="case", platform=True).data["case_id"]
        link_incident(actor=self.staff, case_id=case, business_id=self.business.pk, component="exports", episode=1)
        rows = self.api.get(self.url).data["results"]
        self.assertEqual({row["business_id"]: row["linked_cases"] for row in rows}, {self.business.pk: 1, self.other.pk: 0})
        self.assertNotIn("private question", str(rows))
        ServiceComponentState.objects.filter(business=self.business).update(episode=2)
        self.assertEqual(self.api.get(self.url, {"business": self.business.pk}).data["results"][0]["linked_cases"], 0)

    def test_connector_count_is_full_not_preview_size(self):
        for index in range(13):
            BusinessConnector.objects.create(business=self.business, name=f"Source {index}", provider=f"provider-{index}", status="failed")
        result = self.api.get(self.url, {"source": "connectors", "page_size": 10})
        self.assertEqual(result.data["count"], 13)
        self.assertEqual(len(result.data["results"]), 10)
        health = self.api.get('/api/platform/operations-health/')
        self.assertEqual(health.data['summary']['connector_requests'], 13)
        self.assertEqual(len(health.data['work_queue']['connector_requests']), 10)

    def test_history_period_includes_both_utc_dates_and_excludes_other_business(self):
        recent = AutomationRun.objects.create(business=self.business, trigger_type="manual", status="failed", error="PRIVATE_ERROR")
        old = AutomationRun.objects.create(business=self.business, trigger_type="manual", status="failed")
        AutomationRun.objects.filter(pk=old.pk).update(created_at=self.now-timedelta(days=31))
        AutomationRun.objects.create(business=self.other, trigger_type="manual", status="failed")
        AutomationRun.objects.create(business=self.business, trigger_type="manual", status="pending")
        response = self.api.get(self.url, {"source": "automations", "business": self.business.pk})
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], recent.pk)
        self.assertEqual(response.data["period"]["timezone"], "UTC")
        self.assertNotIn('PRIVATE_ERROR', str(response.data))
        day = (self.now-timedelta(days=31)).date().isoformat()
        self.assertEqual(self.api.get(self.url, {"source": "automations", "date_from": day, "date_to": day}).data["count"], 1)

    def test_integration_and_webhook_failures_are_inspectable_without_payload(self):
        IntegrationEventLog.objects.create(business=self.business, provider="telegram", direction="outbound", status="failed", payload_json={"text": "PRIVATE_TEXT"})
        IntegrationEventLog.objects.create(business=None, provider="telegram", direction="inbound", status="failed")
        endpoint = WebhookEndpoint.objects.create(business=self.business, name="endpoint", url="https://example.com/private", secret="PRIVATE_SECRET")
        WebhookDeliveryLog.objects.create(business=self.business, endpoint=endpoint, status="failed", event_type="lead.created", idempotency_key="worklist-hook", error="PRIVATE_ERROR")
        for source, count in (("integrations", 2), ("webhooks", 1)):
            data = self.api.get(self.url, {"source": source}).data
            self.assertEqual(data["count"], count)
            self.assertNotIn("PRIVATE_", str(data))
            self.assertNotIn("example.com/private", str(data))
        self.assertEqual(self.api.get(self.url, {"source": "integrations", "business": self.business.pk}).data["count"], 1)

    def test_invalid_filters_and_mutations_rejected(self):
        for params in ({"source": "bad"}, {"business": 0}, {"page": 0}, {"page_size": 101}, {"freshness": "bad"},
                       {"source": "webhooks", "component": "files"}, {"date_from": "2026-01-01"},
                       {"source": "automations", "date_from": "bad"},
                       {"source": "automations", "date_from": "2025-01-01", "date_to": "2026-01-02"},
                       {"source": "automations", "date_to": "9999-12-31"}):
            with self.subTest(params=params):
                self.assertEqual(self.api.get(self.url, params).status_code, 400)
        self.assertEqual(self.api.post(self.url, {}).status_code, 405)

    def test_unauthorized_and_lost_role(self):
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.get(self.url).status_code, 403)
        self.staff.role = 'staff'; self.staff.save(update_fields=['role'])
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.get(self.url).status_code, 403)
        self.api.force_authenticate(None)
        self.assertEqual(self.api.get(self.url).status_code, 401)

    def test_missing_source_is_unknown_and_recovers(self):
        self.state()
        with patch('apps.core.platform_worklists.worklist_queryset', side_effect=OperationalError('PRIVATE_DB_ERROR')):
            data = self.api.get(self.url).data
        self.assertIsNone(data['count'])
        self.assertEqual(data['unavailable_sources'], ['incidents'])
        self.assertNotIn('PRIVATE_DB_ERROR', str(data))
        self.assertEqual(self.api.get(self.url).data['count'], 1)
        with patch('apps.core.platform_worklists.linked_counts', side_effect=OperationalError('missing support table')):
            data = self.api.get(self.url).data
        self.assertEqual(data['count'], 1)
        self.assertIsNone(data['results'][0]['linked_cases'])
        self.assertEqual(data['unavailable_sources'], ['incident_links'])

    def test_query_count_does_not_grow_per_business(self):
        self.state()
        with CaptureQueriesContext(connection) as first:
            self.api.get(self.url)
        for index in range(12):
            business = Business.objects.create(owner=self.owner, name=f"Load {index}", slug=f"worklist-load-{index}")
            self.state(business)
        with CaptureQueriesContext(connection) as many:
            result = self.api.get(self.url)
        self.assertEqual(result.data['count'], 13)
        self.assertLessEqual(len(many), len(first)+1)
        self.assertLessEqual(len(many), 14)
