from datetime import date, datetime
from decimal import Decimal
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone

from apps.ai_core import tests as fixtures
from apps.analytics.financial_metrics import financial_report
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.integrations.models import BusinessConnector
from apps.payments.models import Payment


class SelectedFinancialSourceTests(TestCase):
    def setUp(self):
        fixtures.AICoreFoundationTests.setUp(self)
        self.business.financial_source_mode = "manual"
        self.business.timezone = "Asia/Almaty"
        self.business.save()
        self.person = Client.objects.create(business=self.business, full_name="Journal client")
        self.api.force_authenticate(self.owner)

    def payment(self, amount, *, kind="receipt", original=None, occurred_at=None, business=None, currency="KZT"):
        return Payment.objects.create(business=business or self.business, client=self.person,
            amount=Decimal(amount), currency=currency, kind=kind, original=original,
            occurred_at=occurred_at or timezone.make_aware(datetime(2026, 9, 20, 10)), method="cash",
            submission_id=uuid4(), request_hash="test", created_by=self.owner)

    def report(self, actor=None):
        return financial_report(self.business, user=actor or self.owner, start_date=date(2026, 9, 1), end_date=date(2026, 9, 30))

    def test_manual_selection_sums_recorded_cash_without_profit_or_debt(self):
        receipt = self.payment("100.50")
        self.payment("20.25", kind="refund", original=receipt)
        self.payment("999", occurred_at=timezone.make_aware(datetime(2026, 8, 20)))
        report = self.report()
        self.assertEqual(report["state"], "available")
        self.assertEqual(Decimal(report["receipts"]), Decimal("100.50"))
        self.assertEqual(Decimal(report["refunds"]), Decimal("20.25"))
        self.assertEqual(Decimal(report["net_receipts"]), Decimal("80.25"))
        self.assertEqual(report["coverage"], "recorded_manual_operations")
        self.assertIsNone(report["profit"])
        self.assertIsNone(report["debt"])
        self.assertIsNone(report["last_successful_sync_at"])

    def test_external_selection_never_falls_back_to_manual(self):
        self.payment("100")
        self.business.financial_source_mode = "external"
        self.business.save()
        report = self.report()
        self.assertEqual(report["state"], "unavailable")
        self.assertIsNone(report["receipts"])

    def test_empty_manual_journal_is_zero_recorded_operations(self):
        report = self.report()
        self.assertEqual(report["state"], "available")
        self.assertEqual(report["operation_count"], 0)
        self.assertEqual(Decimal(report["net_receipts"]), 0)

    def test_foreign_actor_sees_no_source_or_amounts(self):
        self.payment("100")
        report = self.report(self.other_owner)
        self.assertEqual(report["reason"], "permission_denied")
        self.assertIsNone(report["source"])
        self.assertIsNone(report["receipts"])

    def test_currency_mismatch_does_not_mix_money(self):
        self.payment("100", currency="USD")
        report = self.report()
        self.assertEqual(report["reason"], "currency_mismatch")
        self.assertIsNone(report["receipts"])

    def test_period_uses_business_timezone(self):
        self.payment("100", occurred_at=datetime.fromisoformat("2026-08-31T20:00:00+00:00"))
        self.payment("999", occurred_at=datetime.fromisoformat("2026-09-30T20:00:00+00:00"))
        self.assertEqual(Decimal(self.report()["receipts"]), Decimal("100"))

    def test_business_api_persists_source_and_rejects_foreign_connector(self):
        foreign = BusinessConnector.objects.create(business=self.other_business, name="Other source", provider="1c", capability="finance")
        response = self.api.patch(f"/api/businesses/{self.business.pk}/", {"financial_source_mode": "external", "financial_connector": foreign.pk}, format="json")
        self.assertEqual(response.status_code, 400)
        response = self.api.patch(f"/api/businesses/{self.business.pk}/", {"financial_source_mode": "manual"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Business.objects.get(pk=self.business.pk).financial_source_mode, "manual")
