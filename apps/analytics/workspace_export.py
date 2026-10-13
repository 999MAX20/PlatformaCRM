"""CSV projections of the same period/scopes rendered by the Analytics page."""
import csv
import io

from django.http import HttpResponse

from apps.analytics.workspace import build_analytics_workspace
from apps.core.csv_safety import safe_csv_cell


WORKSPACE_REPORTS = {
    "workspace_overview", "workspace_sources", "workspace_services", "workspace_team", "workspace_finance",
}


def export_workspace_csv(business, report_key, *, user, start_date, end_date):
    data = build_analytics_workspace(business, user=user, start_date=start_date, end_date=end_date)
    if report_key == "workspace_sources":
        fields, rows = ["source", "leads", "converted", "conversion_rate"], data["sources"]
    elif report_key == "workspace_services":
        fields, rows = ["service_id", "service__name", "total", "completed", "no_show"], data["services"]
    elif report_key == "workspace_team":
        fields = ["id", "name", "role", "leads", "converted", "conversion_rate", "won", "lost", "open_tasks", "overdue_tasks", "unanswered"]
        rows = data["team"]["rows"]
    elif report_key == "workspace_finance":
        fields = ["state", "reason", "currency", "receipts", "refunds", "net_receipts"]
        rows = [data["financial"]]
    else:
        fields = ["metric", "value", "basis"]
        rows = [
            {"metric": "leads", "value": data["leads"]["total"], "basis": "created_in_period"},
            {"metric": "lead_to_deal_rate", "value": data["leads"]["conversion_rate"], "basis": "cohort_converted_by_period_end"},
            {"metric": "won_deals", "value": data["deals"]["won"], "basis": "won_at_in_period_current_status"},
            {"metric": "lost_deals", "value": data["deals"]["lost"], "basis": "lost_at_in_period_current_status"},
            {"metric": "appointments", "value": data["appointments"]["total"], "basis": "visit_start_in_period"},
            {"metric": "no_show_rate", "value": data["appointments"]["no_show_rate"], "basis": "all_visits_in_period"},
            {"metric": "open_deals", "value": data["deals"]["open_now"], "basis": "current"},
            *({"metric": key, "value": value, "basis": "current"} for key, value in data["current"].items()),
        ]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=["start", "end", "timezone", "generated_at", *fields])
    writer.writeheader()
    for row in rows:
        values = {**data["period"], "generated_at": data["generated_at"], **row}
        writer.writerow({field: safe_csv_cell(values.get(field, "")) for field in writer.fieldnames})
    response = HttpResponse(buffer.getvalue(), content_type="text/csv; charset=utf-8")
    response["Content-Disposition"] = f'attachment; filename="{report_key}.csv"'
    return response
