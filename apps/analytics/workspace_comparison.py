"""Previous calendar period, using the workspace's existing read boundaries."""
from datetime import timedelta
from decimal import Decimal

from django.db.models import Count, Q

from apps.analytics.crm_metrics import _scoped, _visible_performance_members
from apps.analytics.financial_metrics import financial_report
from apps.businesses.access import Resources
from apps.scheduling.models import Appointment


def previous_period(start, end):
    try:
        previous_end = start - timedelta(days=1)
        previous_start = start - timedelta(days=(end - start).days + 1)
    except OverflowError:
        return None
    return (previous_start, previous_end) if previous_start.year >= 2 else None


def build_workspace_comparison(business, *, user, start_date, end_date, current, now):
    from apps.analytics.workspace import _bounds, _during, _by, _rate

    period = previous_period(start_date, end_date)
    if period is None:
        return {"available": False, "reason": "date_boundary", "period": None}
    start, end = period
    records = _during(_scoped(Appointment.objects.filter(business=business), user, business,
                              Resources.APPOINTMENTS), "start_at", _bounds(business, start, end))
    available = current["availability"][Resources.APPOINTMENTS]
    counts = _by(records, "status")
    total = sum(counts.values())
    appointments = {
        "total": total, "completed": counts.get("completed", 0),
        "completion_rate": _rate(counts.get("completed", 0), total),
        "no_show_rate": _rate(counts.get("no_show", 0), total), "by_status": counts,
    }
    if not available:
        appointments = {key: None for key in appointments}
    services = list(records.order_by().values("service_id", "service__name").annotate(
        total=Count("pk", distinct=True), completed=Count("pk", distinct=True, filter=Q(status="completed")),
        no_show=Count("pk", distinct=True, filter=Q(status="no_show")),
    ).order_by("-total", "service_id"))
    sources = list(records.order_by().values("source").annotate(
        total=Count("pk", distinct=True), completed=Count("pk", distinct=True, filter=Q(status="completed")),
        cancelled=Count("pk", distinct=True, filter=Q(status="cancelled")),
        no_show=Count("pk", distinct=True, filter=Q(status="no_show")),
    ).order_by("-total", "source"))
    totals = _by(records, "responsible_user_id")
    completed = _by(records.filter(status="completed"), "responsible_user_id")
    team = [{"id": member.user_id, "appointments": totals.get(member.user_id, 0) if available else None,
             "completed_appointments": completed.get(member.user_id, 0) if available else None}
            for member in _visible_performance_members(business=business, user=user)]
    financial = financial_report(business, user=user, start_date=start, end_date=end, now=now)
    money = current["financial"]
    comparable = (money["state"] == financial["state"] == "available"
                  and money["currency"] == financial["currency"] and money["source"] == financial["source"])
    changes = {key: str(Decimal(money[key]) - Decimal(financial[key])) if comparable else None
               for key in ("receipts", "refunds", "net_receipts")}
    return {"available": True, "period": {"start": start.isoformat(), "end": end.isoformat(),
            "timezone": business.timezone}, "appointments": appointments, "services": services,
            "record_sources": sources, "team": team, "financial": financial, "financial_changes": changes}
