"""Actual row-lock behavior; run in a disposable PostgreSQL database."""
from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier, local
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents
from apps.businesses.models import Business
from apps.core import tests_crm_server_scenarios
from apps.crm.models import Deal
from apps.leads.models import Lead
from apps.leads.services import create_deal_from_lead
from apps.payments import tests as payment_tests
from apps.payments.models import Payment


@skipUnlessDBFeature("has_select_for_update")
class CRMServerConcurrencyTests(TransactionTestCase):
    def setUp(self):
        self.fixture = tests_crm_server_scenarios.CRMServerScenarioFixture()
        self.fixture.setUp()

    def parallel(self, operations):
        def execute(operation):
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(self.fixture.owner)
                response = operation(api)
                return response.status_code, response.data
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(execute, operation) for operation in operations]
            return [future.result(timeout=45) for future in futures]

    def synchronize_business_lock(self):
        barrier = Barrier(2)
        thread = local()
        original = Business.objects.select_for_update

        def acquire(*args, **kwargs):
            if not getattr(thread, "synchronized", False):
                thread.synchronized = True
                barrier.wait(timeout=20)
            return original(*args, **kwargs)

        return patch.object(Business.objects, "select_for_update", side_effect=acquire)

    def test_two_create_deal_commands_keep_one_linked_deal(self):
        barrier = Barrier(2)

        def create(**kwargs):
            barrier.wait(timeout=20)
            return create_deal_from_lead(**kwargs)

        url = f"/api/leads/{self.fixture.lead.pk}/create-deal/"
        with patch("apps.leads.views.create_deal_from_lead", side_effect=create):
            results = self.parallel([
                lambda api: api.post(url, {"amount": "100.00"}, format="json", HTTP_IDEMPOTENCY_KEY="first"),
                lambda api: api.post(url, {"amount": "100.00"}, format="json", HTTP_IDEMPOTENCY_KEY="second"),
            ])
        self.assertEqual(sorted(code for code, _ in results), [200, 201], results)
        self.assertEqual(results[0][1]["id"], results[1][1]["id"])
        self.assertEqual(Deal.objects.filter(lead=self.fixture.lead).count(), 1)
        self.assertEqual(ActivityEvent.objects.filter(event_type=ActivityEvents.DEAL_CREATED_FROM_LEAD).count(), 1)

    def test_two_lost_commands_preserve_single_transition(self):
        url = f"/api/leads/{self.fixture.lead.pk}/mark-lost/"
        with self.synchronize_business_lock():
            results = self.parallel([lambda api: api.post(url, {"lost_reason": "No longer needed"})] * 2)
        self.assertEqual([code for code, _ in results], [200, 200], results)
        lead = Lead.objects.get(pk=self.fixture.lead.pk)
        self.assertEqual(lead.previous_status, Lead.Statuses.NEW)
        self.assertEqual(ActivityEvent.objects.filter(event_type=ActivityEvents.LEAD_LOST).count(), 1)

    def test_detail_edit_and_stage_change_preserve_both_results(self):
        url = f"/api/deals/{self.fixture.deal.pk}/"
        with self.synchronize_business_lock():
            results = self.parallel([
                lambda api: api.patch(url, {"notes": "New note", "amount": "250.00"}, format="json"),
                lambda api: api.post(f"{url}mark-won/", {}, format="json"),
            ])
        self.assertEqual([code for code, _ in results], [200, 200], results)
        deal = Deal.objects.get(pk=self.fixture.deal.pk)
        self.assertEqual(deal.status, Deal.Statuses.WON)
        self.assertEqual(deal.notes, "New note")
        self.assertEqual(deal.amount, Decimal("250.00"))


@skipUnlessDBFeature("has_select_for_update")
class CRMRefundConcurrencyTests(TransactionTestCase):
    def test_competing_refunds_cannot_exceed_received_money(self):
        fixture = payment_tests.PaymentFlowTests()
        fixture.setUp()
        original = fixture.receipt(amount="100.00")
        barrier = Barrier(2)

        def refund():
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(fixture.owner)
                payload = fixture.refund(original, amount="70.00")
                barrier.wait(timeout=20)
                response = api.post(fixture.url, payload, format="json")
                return response.status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(refund) for _ in range(2)]
            results = [future.result(timeout=45) for future in futures]
        self.assertEqual(sorted(results), [201, 400])
        original.refresh_from_db()
        self.assertEqual(original.refunded_amount, Decimal("70.00"))
        self.assertEqual(Payment.objects.filter(original=original).count(), 1)
