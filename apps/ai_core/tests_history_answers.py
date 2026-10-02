import json
from unittest.mock import patch

from django.test import TestCase

from apps.ai_core import tests as fixtures
from apps.ai_core.ai_client import AIClientResult, AIClientError
from apps.analytics import tests_manual_finance as finance_fixtures


class HistoryAnswerTests(TestCase):
    def setUp(self):
        finance_fixtures.SelectedFinancialSourceTests.setUp(self)

    def answer(self):
        return self.api.post("/api/ai/analyst/history/", {"business": self.business.pk,
            "start": "2026-09-01", "end": "2026-09-30", "question": "What changed in receipts?"}, format="json")

    def test_answer_uses_full_report_and_verified_source_ids(self):
        finance_fixtures.SelectedFinancialSourceTests.payment(self, "100.25")
        result = AIClientResult(output_text=json.dumps({"answer": "Recorded receipts are 100.25 KZT; profit is unavailable.", "source_ids": ["CRM-summary"], "no_data": False}), model="test", provider="test")
        with patch("apps.ai_core.services.generate_text", return_value=result) as provider:
            response = self.answer()
        self.assertEqual(response.status_code, 200, response.data)
        prompt = provider.call_args.args[0]
        self.assertIn("recorded_manual_operations", str(prompt))
        self.assertIn("never profit", prompt.messages[0]["content"])
        self.assertEqual(response.data["sources"][0]["id"], "CRM-summary")

    def test_source_change_while_generating_discards_answer(self):
        def generate(*args, **kwargs):
            self.business.financial_source_mode = "external"
            self.business.save()
            return AIClientResult(output_text=json.dumps({"answer": "Old report", "source_ids": ["CRM-summary"]}), model="test", provider="test")
        with patch("apps.ai_core.services.generate_text", side_effect=generate):
            response = self.answer()
        self.assertEqual(response.status_code, 403)

    def test_unknown_citation_and_provider_failure_are_not_success(self):
        result = AIClientResult(output_text=json.dumps({"answer": "Invented", "source_ids": ["Foreign-record"]}), model="test", provider="test")
        with patch("apps.ai_core.services.generate_text", return_value=result):
            self.assertEqual(self.answer().status_code, 503)
        with patch("apps.ai_core.services.generate_text", side_effect=AIClientError()):
            self.assertEqual(self.answer().status_code, 503)

    def test_no_sources_skips_provider(self):
        self.business.financial_source_mode = "external"
        self.business.save()
        with patch("apps.ai_core.services.generate_text") as provider:
            response = self.answer()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["provider_state"], "no_data")
        provider.assert_not_called()
