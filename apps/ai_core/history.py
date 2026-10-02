"""Full-period, permission-scoped evidence for the historical AI analyst."""
from datetime import timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Count, Q, Sum
from django.db.models.functions import TruncDate, TruncMonth
from django.utils import timezone

from apps.ai_core.crm_tools import ENTITIES
from apps.ai_core.workflows import assert_workflow_enabled
from apps.analytics.financial_metrics import financial_report
from apps.analytics.manual_finance import business_period, period_payments
from apps.businesses.access import Actions, Resources, assert_can, can, scope_queryset
from apps.businesses.capabilities import resource_is_enabled


def operational_period(business, user, start, end, sources):
    lower, upper = business_period(business, start, end)
    metrics = {}
    for entity, spec in ENTITIES.items():
        if entity not in sources or not resource_is_enabled(business, entity) or not can(user, business, entity, Actions.VIEW).allowed:
            continue
        queryset = scope_queryset(spec.model.objects.filter(business=business), user, business, entity, Actions.VIEW)
        field = "start_at" if entity == "appointments" else "created_at"
        period = queryset.filter(**{f"{field}__gte": lower, f"{field}__lt": upper})
        metrics[entity] = {"count": period.count(), "date_field": field, "includes_archived": True,
            "source_id": f"HISTORY-{entity}", "current_statuses": {}}
        if entity != "clients":
            metrics[entity]["current_statuses"] = dict(period.values_list("status").annotate(count=Count("pk")))
    return metrics


def comparison(current, previous):
    output = {}
    for field in ("receipts", "refunds", "net_receipts"):
        now, before = current.get(field), previous.get(field)
        if now is None or before is None:
            output[field] = {"absolute": None, "percent": None}
            continue
        difference = Decimal(now) - Decimal(before)
        output[field] = {"absolute": str(difference),
            "percent": str((difference / abs(Decimal(before)) * 100).quantize(Decimal("0.01"))) if Decimal(before) else None}
    return output


def manual_series(business, start, end):
    monthly = (end - start).days > 92
    bucket = TruncMonth("occurred_at", tzinfo=ZoneInfo(business.timezone)) if monthly else TruncDate("occurred_at", tzinfo=ZoneInfo(business.timezone))
    rows = period_payments(business, start, end).annotate(bucket=bucket).values("bucket").annotate(
        receipts=Sum("amount", filter=Q(kind="receipt")), refunds=Sum("amount", filter=Q(kind="refund")), count=Count("pk")).order_by("bucket")
    result = []
    for row in rows:
        receipts, refunds = row["receipts"] or Decimal("0"), row["refunds"] or Decimal("0")
        result.append({"period": row["bucket"].date().isoformat() if monthly else row["bucket"].isoformat(),
            "receipts": str(receipts), "refunds": str(refunds), "net_receipts": str(receipts - refunds), "count": row["count"]})
    return {"granularity": "month" if monthly else "day", "zero_buckets_omitted": True, "points": result}


def build_history_report(*, business, user, start, end):
    assert_can(user, business, Resources.AI_ANALYST, Actions.VIEW)
    config = assert_workflow_enabled(business, "analyst")
    length = end - start + timedelta(days=1)
    previous_start, previous_end = start - length, start - timedelta(days=1)
    current = financial_report(business, user=user, start_date=start, end_date=end)
    previous = financial_report(business, user=user, start_date=previous_start, end_date=previous_end)
    operations = operational_period(business, user, start, end, config["sources"])
    previous_operations = operational_period(business, user, previous_start, previous_end, config["sources"])
    for key, metric in operations.items():
        metric["previous_count"] = previous_operations[key]["count"]
        metric["difference"] = metric["count"] - metric["previous_count"]
    series = {"granularity": None, "points": [], "reason": "source_has_no_verified_series"}
    if business.financial_source_mode == "manual" and current["state"] == "available":
        series = manual_series(business, start, end)
    return {"period": {"start": start.isoformat(), "end": end.isoformat()},
        "previous_period": {"start": previous_start.isoformat(), "end": previous_end.isoformat()},
        "timezone": business.timezone, "generated_at": timezone.now().isoformat(),
        "financial": current, "previous_financial": previous, "financial_change": comparison(current, previous),
        "profit": {"state": "unavailable", "reason": "expenses_not_recorded"},
        "debt": {"state": "unavailable", "reason": "accruals_not_recorded"},
        "operations": operations, "series": series,
        "coverage": "all_accessible_records_in_period", "status_basis": "current_status_of_period_records",
        "sources": [{"id": f"HISTORY-{key}", "entity": key, "period": {"start": start.isoformat(), "end": end.isoformat()}, "count": value["count"]} for key, value in operations.items()],
        "state": "available" if any(value["count"] for value in operations.values()) or current["state"] != "unavailable" else "no_data"}


def explain_history(*, business, user, start, end, question):
    import json
    from rest_framework.exceptions import PermissionDenied
    from apps.ai_core.services import run_ai_request

    report = build_history_report(business=business, user=user, start=start, end=end)
    if report["state"] == "no_data":
        return {"answer": "", "sources": [], "provider_state": "no_data", "report": report}
    contract = (
        " This is a historical report over all permitted records of the exact requested period."
        " Current_statuses are today's states of records from that period, not their historical state at period end."
        " Manual finance covers recorded journal operations only; it is not independently verified accounting completeness."
        " Net receipts are receipts minus refunds, never profit, revenue accrual, balance or debt. Profit and debt are unavailable."
        " Never infer cash from clients, deal amounts, services or events. Respect unavailable/stale states and currency."
        " Explain only supplied deterministic totals and differences. Do not invent causes or forecasts."
    )
    result, log = run_ai_request(business=business, user=user, prompt_type="business_history_analyst",
        user_input=question, input_json={"crm_context": {"summary": report}}, response_contract=contract)
    business.refresh_from_db()
    fresh = build_history_report(business=business, user=user, start=start, end=end)
    def signature(value):
        value = {**value}
        value.pop("generated_at", None)
        for key in ("financial", "previous_financial"):
            value[key] = {k: v for k, v in value[key].items() if k != "as_of"}
        return json.dumps(value, sort_keys=True, default=str)
    if signature(report) != signature(fresh):
        raise PermissionDenied("Report sources or access changed while preparing the answer. Request a fresh report.")
    return {"answer": result.output_text, "sources": result.sources, "provider_state": result.provider_state,
        "is_mock": result.is_mock, "log_id": log.pk, "report": report}
