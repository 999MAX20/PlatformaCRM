"""Budgeted, observable real transport. Headers/credentials are never persisted."""
import hashlib
import io
import json
import time
from decimal import Decimal
from urllib import request
from urllib.parse import urlsplit


class BudgetStop(RuntimeError):
    pass


class Transport:
    def __init__(self, directory, *, live, budget="3", max_calls=500):
        self.directory, self.live = directory, live
        self.budget, self.max_calls = Decimal(budget), max_calls
        if not self.budget.is_finite() or self.budget <= 0:
            raise ValueError("Budget must be finite and positive")
        self.original = request.urlopen
        self.case = "unassigned"
        self.calls = []
        self.prices = {}
        self.ledger_path = directory / ("budget.json" if live else "dry-budget.json")
        self.ledger = json.loads(self.ledger_path.read_text()) if self.ledger_path.exists() else []

    def load_prices(self):
        if not self.live:
            return
        with self.original("https://openrouter.ai/api/v1/models", timeout=30) as response:
            data = json.loads(response.read())
        allowed = {"openai/gpt-4o-mini", "openai/gpt-4.1-mini", "openai/gpt-4.1"}
        self.prices = {row["id"]: row["pricing"] for row in data["data"] if row["id"] in allowed}
        if set(self.prices) != allowed:
            raise BudgetStop("Required model prices unavailable; no paid requests permitted")
        (self.directory / "provider-prices.json").write_text(json.dumps(self.prices, indent=2))

    def persist(self):
        temporary = self.ledger_path.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.ledger, indent=2))
        temporary.replace(self.ledger_path)

    def __call__(self, req, *args, **kwargs):
        if not isinstance(req, request.Request):
            raise BudgetStop("Unplanned external request")
        url = urlsplit(req.full_url)
        if url.scheme != "https" or url.hostname != "openrouter.ai" or url.path != "/api/v1/chat/completions":
            raise BudgetStop("Evaluation permits only configured OpenRouter completions")
        payload = json.loads(req.data)
        model = payload["model"]
        if model not in {"openai/gpt-4o-mini", "openai/gpt-4.1-mini", "openai/gpt-4.1"}:
            raise BudgetStop("Unexpected model; inspect mapping before spending")
        prompt = json.dumps(payload["messages"], ensure_ascii=False, sort_keys=True)
        # UTF-8 bytes plus generous protocol overhead is a conservative text-token
        # reservation. Completion tokens are bounded in the outgoing payload.
        input_bound = len(prompt.encode()) + 1024
        price = self.prices.get(model, {"prompt": "0", "completion": "0", "request": "0"})
        reserve = Decimal(price["prompt"]) * input_bound + Decimal(price["completion"]) * payload["max_tokens"] + Decimal(price.get("request", "0"))
        spent = sum(Decimal(row["charged_or_reserved_usd"]) for row in self.ledger)
        if len(self.ledger) >= self.max_calls or spent + reserve > self.budget:
            raise BudgetStop("Authorized request/cost ceiling reached before next call")
        row = {"case": self.case, "run_id": getattr(self, "run_id", "baseline"), "model": model, "temperature": payload["temperature"],
               "prompt_sha256": hashlib.sha256(prompt.encode()).hexdigest(),
               "charged_or_reserved_usd": str(reserve), "state": "reserved"}
        self.ledger.append(row)
        self.persist()
        started = time.monotonic()
        if self.live:
            with self.original(req, *args, **kwargs) as response:
                raw = response.read()
            data = json.loads(raw)
        else:
            data = {"model": model, "choices": [{"message": {"content": "Synthetic transport dry run"}, "finish_reason": "stop"}], "usage": {"total_tokens": 0, "cost": 0}}
            raw = json.dumps(data).encode()
        usage = data.get("usage", {})
        cost = usage.get("cost")
        if cost is None and "prompt_tokens" in usage and "completion_tokens" in usage:
            cost = Decimal(price["prompt"]) * usage["prompt_tokens"] + Decimal(price["completion"]) * usage["completion_tokens"] + Decimal(price.get("request", "0"))
        if cost is not None:
            row["charged_or_reserved_usd"] = str(Decimal(str(cost)))
        row.update(state="received", tokens=usage.get("total_tokens"), elapsed_seconds=round(time.monotonic()-started, 3), returned_model=data.get("model"))
        self.persist()
        # Only synthetic fixture data is allowed in this explicitly requested artifact.
        trace = {**row, "messages": payload["messages"], "provider_response": data}
        self.calls.append(trace)
        with (self.directory / ("transport.jsonl" if self.live else "dry-transport.jsonl")).open("a", encoding="utf8") as stream:
            stream.write(json.dumps(trace, ensure_ascii=False) + "\n")
        return io.BytesIO(raw)
