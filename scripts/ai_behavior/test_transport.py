import io
import json
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from urllib.request import Request
from scripts.ai_behavior.transport import BudgetStop, Transport


class TransportBudgetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.transport = Transport(self.directory, live=True)
        self.transport.prices = {"openai/gpt-4o-mini": {"prompt": "0.000001", "completion": "0.000002"}}
        self.sent = 0

    def req(self, url="https://openrouter.ai/api/v1/chat/completions"):
        return Request(url, data=json.dumps({"model": "openai/gpt-4o-mini", "temperature": 0.1, "max_tokens": 100,
                        "messages": [{"role": "user", "content": "Synthetic question"}]}).encode(), headers={"Authorization": "Bearer NEVER_RECORD_THIS"})

    def respond(self, *args, **kwargs):
        self.sent += 1
        return io.BytesIO(json.dumps({"model": "openai/gpt-4o-mini", "choices": [], "usage": {"cost": 0.001, "total_tokens": 20}}).encode())

    def test_over_budget_and_request_limit_block_before_transport(self):
        self.transport.original = self.respond
        self.transport.ledger = [{"charged_or_reserved_usd": "3"}]
        with self.assertRaises(BudgetStop): self.transport(self.req())
        self.assertEqual(self.sent, 0)
        self.transport.ledger = [{"charged_or_reserved_usd": "0"}] * self.transport.max_calls
        with self.assertRaises(BudgetStop): self.transport(self.req())
        self.assertEqual(self.sent, 0)

    def test_success_records_cost_and_never_auth_headers(self):
        self.transport.original = self.respond
        self.transport(self.req())
        saved = "".join(path.read_text() for path in self.directory.iterdir())
        self.assertNotIn("NEVER_RECORD_THIS", saved)
        self.assertEqual(self.transport.ledger[0]["charged_or_reserved_usd"], "0.001")
        restored = Transport(self.directory, live=True)
        self.assertEqual(len(restored.ledger), 1)

    def test_uncertain_failure_keeps_cost_reservation(self):
        def fail(*args, **kwargs): raise TimeoutError("Synthetic timeout")
        self.transport.original = fail
        with self.assertRaises(TimeoutError): self.transport(self.req())
        restored = Transport(self.directory, live=True)
        self.assertEqual(restored.ledger[0]["state"], "reserved")
        self.assertGreater(float(restored.ledger[0]["charged_or_reserved_usd"]), 0)

    def test_other_network_destination_rejected_before_send(self):
        self.transport.original = self.respond
        with self.assertRaises(BudgetStop): self.transport(self.req("https://example.invalid/send"))
        self.assertEqual(self.sent, 0)

    def test_one_dollar_ceiling_survives_restart_and_counts_uncertain_attempts(self):
        self.transport = Transport(self.directory, live=True, budget="1")
        self.transport.prices = {"openai/gpt-4o-mini": {"prompt": "0.000001", "completion": "0.000002"}}
        self.transport.ledger = [{"charged_or_reserved_usd": "0.999", "state": "reserved"}]
        self.transport.persist()
        restored = Transport(self.directory, live=True, budget="1")
        restored.prices = self.transport.prices
        restored.original = self.respond
        with self.assertRaises(BudgetStop):
            restored(self.req())
        self.assertEqual(self.sent, 0)
        self.assertEqual(len(restored.ledger), 1)

    def test_invalid_budget_cannot_disable_ceiling(self):
        for value in ("NaN", "Infinity", "-1", "0"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                Transport(self.directory, live=True, budget=value)


if __name__ == "__main__": unittest.main()
