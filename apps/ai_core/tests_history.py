from datetime import date, datetime
from decimal import Decimal

from django.utils import timezone

from apps.analytics.tests_manual_finance import SelectedFinancialSourceTests
from apps.clients.models import Client
from apps.ai_core.models import AgentProfile


class HistoricalAnalystTests(SelectedFinancialSourceTests):
    def history(self, **params):
        return self.api.get("/api/ai/analyst/history/", {"business": self.business.pk,
            "start": "2026-09-01", "end": "2026-09-30", **params})

    def test_full_period_not_short_context_and_comparison_is_exact(self):
        receipt = self.payment("120")
        self.payment("20", kind="refund", original=receipt)
        self.payment("50", occurred_at=timezone.make_aware(datetime(2026, 8, 10)))
        Client.objects.bulk_create([Client(business=self.business, full_name=f"Historical {i}") for i in range(30)])
        Client.objects.filter(business=self.business).update(created_at=timezone.make_aware(datetime(2026, 9, 10)))
        Client.objects.filter(pk=self.person.pk).update(is_archived=True)
        response = self.history()
        self.assertEqual(response.status_code, 200, response.data)
        data = response.data
        self.assertEqual(data["operations"]["clients"]["count"], 31)
        self.assertEqual(Decimal(data["financial_change"]["net_receipts"]["absolute"]), Decimal("50"))
        self.assertEqual(Decimal(data["financial_change"]["net_receipts"]["percent"]), Decimal("100"))
        self.assertEqual(len(data["series"]["points"]), 1)
        self.assertEqual(Decimal(data["series"]["points"][0]["net_receipts"]), Decimal("100"))
        self.assertEqual(data["profit"]["state"], "unavailable")
        self.assertEqual(data["debt"]["state"], "unavailable")

    def test_invalid_and_excessive_ranges_are_rejected(self):
        for params in ({"start": "2026-10-01"}, {"start": "2000-01-01"}, {"start": "invalid"}, {"start": "0001-01-01", "end": "0001-02-01"}):
            self.assertEqual(self.history(**params).status_code, 400)

    def test_no_data_does_not_call_provider(self):
        from unittest.mock import patch
        self.business.financial_source_mode = "external"
        self.business.save()
        with patch("apps.ai_core.services.generate_text", side_effect=AssertionError("No paid call")):
            result = self.history()
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.data["state"], "no_data")
        self.assertIsNone(result.data["financial_change"]["receipts"]["percent"])

    def test_source_switch_is_respected_on_next_report_and_disabled_analyst_denies(self):
        self.payment("100")
        self.assertEqual(self.history().data["financial"]["state"], "available")
        self.business.financial_source_mode = "external"
        self.business.save()
        self.assertEqual(self.history().data["financial"]["state"], "unavailable")
        AgentProfile.objects.create(business=self.business, name="Off", is_active=False, rules_json={"scenario": "analyst"})
        self.assertEqual(self.history().status_code, 403)

    def test_history_rejects_other_business(self):
        self.api.force_authenticate(self.other_owner)
        self.assertEqual(self.history().status_code, 403)
