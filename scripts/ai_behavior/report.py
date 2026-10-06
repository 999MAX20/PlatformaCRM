"""Summarize retained synthetic evidence; HTTP success is not semantic acceptance."""
import difflib
import itertools
import json
import hashlib
import re
from collections import Counter
from decimal import Decimal
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
DIRECTORY = ROOT / "output/ai-agents-behavior-20261006"

# These are manual conclusions from the captured responses, not a generic LLM judge.
LIMITATIONS = {
    "sources-all": "PARTIAL: entity titles are paraphrased as if exact; timestamps now use business local time.",
    "role-inbox-reception": "PARTIAL: role-specific contrast is weak; factual next steps are grounded.",
    "role-inbox-analyst": "PARTIAL: little analyst-role contrast; service minimum price is occasionally phrased as a fixed price.",
    "role-crm-reception": "PARTIAL: factual response, but weak contrast with the analyst role.",
    "role-crm-analyst": "PARTIAL: factual response, but weak contrast with the receptionist role.",
    "tone-second-crm-formal": "LIMITED: identical short address/hours answer in the matched friendly sample.",
    "tone-second-crm-friendly": "LIMITED: identical short address/hours answer in the matched formal sample.",
    "multiturn-crm-first": "UNSUPPORTED: staff chat has no durable conversational memory; earlier samples also failed source validation.",
    "multiturn-crm-followup": "UNSUPPORTED: honest no-history response, not a successful multi-turn conversation.",
    "qualification-model-boundary": "LIMITED: classifier uses environment smart model/temperature, independently of saved reply settings.",
    "pipeline-reply-enabled": "PASS for reply generation; website mock delivery is not live messenger delivery.",
    "pipeline-reply-limit": "PASS for the character bound; raw truncation is not a guarantee of a complete final sentence.",
    "pipeline-booking-details-missing": "PASS for no invented appointment; final booking chain has separate failed cases.",
}


def temperature_metrics(rows):
    metrics = []
    for scenario in ("inbox", "crm"):
        for temperature in ("0.1", "0.8"):
            selected = [row for row in rows if row["id"].startswith(f"temperature-{scenario}-{temperature}-")]
            if not selected:
                continue
            texts = [row.get("text", "") for row in selected]
            hashes = {call["prompt_sha256"] for row in selected for call in row["provider_calls"]}
            distances = [1-difflib.SequenceMatcher(None, a, b).ratio() for a, b in itertools.combinations(texts, 2)]
            assert len(selected) == 12 and len(hashes) == 1 and all(row["machine_result"] == "pass" for row in selected)
            metrics.append({"scenario": scenario, "temperature": float(temperature), "samples": len(selected),
                            "unique_answers": len(set(texts)), "mean_pairwise_character_distance": round(sum(distances)/len(distances), 6),
                            "prompt_hash_count": len(hashes), "price_currency_refund_retained": all("731" in value and "KZT" in value and "14" in value for value in texts)})
    return metrics


def main():
    rows = [json.loads(line) for line in (DIRECTORY / "cases.jsonl").read_text(encoding="utf8").splitlines()]
    latest = {row["id"]: row for row in rows}
    ledger = json.loads((DIRECTORY / "budget.json").read_text())
    total = sum((Decimal(row["charged_or_reserved_usd"]) for row in ledger), Decimal(0))
    assert total <= Decimal("3")
    summary = {"unique_cases": len(latest), "case_attempts": len(rows), "provider_requests": len(ledger),
               "charged_or_reserved_usd": str(total), "budget_usd": "3", "transport_states": dict(Counter(row["state"] for row in ledger)),
               "latest_machine_results": dict(Counter(row["machine_result"] for row in latest.values())),
               "latest_machine_failures": [key for key, row in latest.items() if row["machine_result"] != "pass"],
               "manual_limitations": LIMITATIONS,
               "baseline_temperature": temperature_metrics([row for row in rows if row.get("run_id", "baseline") == "baseline"]),
               "final_temperature": temperature_metrics(list(latest.values()))}
    transports = [json.loads(line) for line in (DIRECTORY / "transport.jsonl").read_text(encoding="utf8").splitlines()]
    last_transport = {row["case"]: row for row in transports}
    summary["temperature_prompt_control"] = {}
    for scenario in ("inbox", "crm"):
        hashes = set()
        for key, row in last_transport.items():
            if not key.startswith(f"temperature-{scenario}-"):
                continue
            messages = [{**message, "content": re.sub(r'("temperature"\s*:\s*)(?:0\.1|0\.8)', r'\1<TEMPERATURE>', message["content"])} for message in row["messages"]]
            hashes.add(hashlib.sha256(json.dumps(messages, ensure_ascii=False, sort_keys=True).encode()).hexdigest())
        assert len(hashes) == 1
        summary["temperature_prompt_control"][scenario] = "One prompt hash across both arms after masking only saved-temperature metadata; user question and business facts unchanged."
    (DIRECTORY / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf8")
    lines = ["# AI Agents — case evidence, 06.10.2026", "",
             f"{len(latest)} unique cases; {len(rows)} retained attempts; {len(ledger)} provider requests; USD {total} charged/reserved.", "",
             "Latest attempts are shown below. Failed earlier attempts remain in cases.jsonl and transport.jsonl.",
             "PASS is scoped to each stated check. Manual LIMITATIONS and UNSUPPORTED cases prevent an overall green acceptance.", "",
             "The test clock is 2026-10-07 10:00 UTC; all records are synthetic and disposable. Booking delivery receipts are controlled, not real messenger evidence.", ""]
    for key, row in latest.items():
        result = row["machine_result"]
        assessment = "FAIL: expected behavior was not achieved." if result != "pass" else LIMITATIONS.get(key, "PASS for the stated case rubric.")
        lines += [f"## {key}", "", f"Machine: **{result}**. Review: {assessment}", "",
                  f"Run: `{row.get('run_id', 'baseline')}`. Provider calls: {len(row['provider_calls'])}.", "", row.get("rubric", ""), ""]
        delta = {name: row["after"][name]-count for name, count in row["before"].items() if row["after"][name] != count}
        if delta:
            lines += ["Database count changes: `"+json.dumps(delta)+"`.", ""]
        if row.get("text"):
            lines += ["> "+row["text"].replace("\n", "\n> "), ""]
        else:
            data = row.get("data", {"error": row.get("detail")})
            selected = {name: data[name] for name in ("evaluation_input", "decision", "reason", "status", "handoff", "actual_record", "actual_entities", "booking", "selected_slot", "delivery_receipt", "outgoing", "code", "detail", "errors") if name in data}
            lines += ["```json", json.dumps(selected or data, ensure_ascii=False, indent=2, default=str), "```", ""]
    (DIRECTORY / "case-review.md").write_text("\n".join(lines), encoding="utf8")
    print(json.dumps({key: summary[key] for key in ("unique_cases", "case_attempts", "provider_requests", "charged_or_reserved_usd", "latest_machine_results", "latest_machine_failures")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
