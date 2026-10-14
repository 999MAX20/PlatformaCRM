from django.db.models import Count, Max, Q
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.leads.models import Lead, LeadForm, LeadFormSubmissionError
from apps.tasks.models import Task
from apps.bots.models import BotConversation
from apps.integrations.models import BusinessConnector, BusinessEvent
from apps.core.models import AuditLog
from apps.integrations.sanitization import sanitize_error_text

def _merchant_counts(business):
    return _merchant_counts_many([business])[business.pk]


def _merchant_counts_many(businesses):
    """Batch operational counts for exactly the selected businesses."""
    businesses = list(businesses)
    fields = ("lead_count", "new_leads", "clients_count", "open_tasks",
              "unread_conversations", "handoff_conversations", "failed_connectors",
              "pending_connectors", "connected_connectors", "form_errors", "lead_forms", "sales_events")
    result = {item.pk: {**dict.fromkeys(fields, 0), "latest_activity_at": None} for item in businesses}
    if not result:
        return result

    def collect(model, metrics, *, latest=False):
        values = dict(metrics)
        if latest:
            values["latest"] = Max("created_at" if model is BusinessEvent else "updated_at")
        for row in model.objects.filter(business_id__in=result).values("business_id").annotate(**values):
            counts = result[row.pop("business_id")]
            timestamp = row.pop("latest", None)
            if timestamp:
                counts["latest_activity_at"] = max(counts["latest_activity_at"] or timestamp, timestamp)
            counts.update(row)

    collect(Lead, {"lead_count": Count("pk", filter=Q(is_archived=False)),
                   "new_leads": Count("pk", filter=Q(is_archived=False, status=Lead.Statuses.NEW))}, latest=True)
    collect(Client, {"clients_count": Count("pk", filter=Q(is_archived=False))})
    collect(Task, {"open_tasks": Count("pk", filter=Q(is_archived=False, status__in=[Task.Statuses.OPEN, Task.Statuses.IN_PROGRESS, Task.Statuses.WAITING]))}, latest=True)
    collect(BotConversation, {
        "unread_conversations": Count("pk", filter=Q(is_archived=False, unread_count__gt=0)),
        "handoff_conversations": Count("pk", filter=Q(is_archived=False, handoff_required=True))}, latest=True)
    collect(BusinessConnector, {
        "failed_connectors": Count("pk", filter=Q(status__in=[BusinessConnector.Statuses.FAILED, BusinessConnector.Statuses.EXPIRED_CREDENTIALS])),
        "pending_connectors": Count("pk", filter=Q(status=BusinessConnector.Statuses.NEEDS_ATTENTION)),
        "connected_connectors": Count("pk", filter=Q(status__in=[BusinessConnector.Statuses.CONNECTED, BusinessConnector.Statuses.SYNCING]))})
    collect(LeadFormSubmissionError, {"form_errors": Count("pk")})
    collect(LeadForm, {"lead_forms": Count("pk", filter=Q(is_active=True))})
    collect(BusinessEvent, {"sales_events": Count("pk", filter=Q(event_type__in=["sale.recorded", "sale_recorded"]))}, latest=True)
    for business in businesses:
        result[business.pk]["latest_activity_at"] = result[business.pk]["latest_activity_at"] or business.updated_at
    return result


def _merchant_health(business, counts, subscription=None):
    checks = {
        "has_owner": bool(business.owner_id),
        "has_landing": bool(business.landing_id or business.landing_domain),
        "has_lead_form": counts["lead_forms"] > 0,
        "has_leads": counts["lead_count"] > 0,
        "has_sales_data": counts["sales_events"] > 0,
        "has_connected_source": counts["connected_connectors"] > 0 or counts["pending_connectors"] > 0,
        "has_subscription": bool(subscription),
    }
    score = round((sum(1 for value in checks.values() if value) / len(checks)) * 100)
    blockers = []
    if not checks["has_lead_form"]:
        blockers.append("Нет активной формы заявок")
    if counts["form_errors"]:
        blockers.append(f"Ошибки формы заявок: {counts['form_errors']}")
    if counts["failed_connectors"]:
        blockers.append(f"Интеграции требуют внимания: {counts['failed_connectors']}")
    if not checks["has_sales_data"]:
        blockers.append("Нет загруженных продаж")
    if counts["handoff_conversations"]:
        blockers.append(f"Диалоги ждут оператора: {counts['handoff_conversations']}")

    if blockers:
        status = "attention"
    elif score >= 75:
        status = "healthy"
    elif score >= 45:
        status = "setup"
    else:
        status = "risk"

    if blockers:
        next_action = blockers[0]
    elif counts["new_leads"]:
        next_action = "Проверить новые заявки"
    elif not checks["has_sales_data"]:
        next_action = "Загрузить продажи Excel/CSV"
    else:
        next_action = "Мониторить активность пилота"

    return {
        "score": score,
        "status": status,
        "checks": checks,
        "blockers": blockers[:5],
        "next_action": next_action,
    }


def _merchant_support_workflow(business, counts, health):
    priority = "low"
    if health["status"] == "risk" or counts["failed_connectors"] or counts["form_errors"]:
        priority = "high"
    elif health["status"] == "attention" or counts["handoff_conversations"] or counts["new_leads"] or counts["pending_connectors"]:
        priority = "medium"

    next_steps = []
    if counts["form_errors"]:
        next_steps.append({"key": "fix_forms", "label": "Проверить ошибки формы", "href": f"/platform/merchants/{business.id}"})
    if counts["handoff_conversations"]:
        next_steps.append({"key": "answer_inbox", "label": "Помочь с диалогами handoff", "href": "/app/inbox"})
    if counts["failed_connectors"]:
        next_steps.append({"key": "fix_connectors", "label": "Проверить failed connectors", "href": "/app/integrations"})
    if counts["pending_connectors"]:
        next_steps.append({"key": "review_connection_requests", "label": "Проверить заявки на подключение", "href": f"/platform/merchants/{business.id}"})
    if not health["checks"].get("has_sales_data"):
        next_steps.append({"key": "request_sales_upload", "label": "Попросить клиента загрузить Excel/CSV продаж", "href": "/app/settings#data-tools"})
    if counts["new_leads"]:
        next_steps.append({"key": "check_new_leads", "label": "Проверить новые заявки", "href": "/app/leads"})
    if not next_steps:
        next_steps.append({"key": "monitor", "label": "Мониторить пилот и активность", "href": f"/platform/merchants/{business.id}"})

    recent_actions = [
        {
            "id": log.id,
            "action_type": log.metadata.get("action_type", "support_note"),
            "note": sanitize_error_text(log.metadata.get("note", "")),
            "status": log.metadata.get("status", "logged"),
            "created_at": log.created_at,
            "actor_email": log.actor.email if log.actor else None,
        }
        for log in AuditLog.objects.filter(business=business, entity_type="platform_support_action").select_related("actor")[:5]
    ]
    return {
        "priority": priority,
        "summary": health["next_action"],
        "next_steps": next_steps[:5],
        "recent_actions": recent_actions,
    }


def _platform_operations_summary(since):
    businesses = list(Business.objects.select_related("owner", "subscription"))
    total = len(businesses)
    counts_by_id = _merchant_counts_many(businesses)
    attention = 0
    risk = 0
    no_sales_data = 0
    with_form_errors = 0
    handoff = 0
    for business in businesses:
        subscription = getattr(business, "subscription", None)
        counts = counts_by_id[business.pk]
        health = _merchant_health(business, counts, subscription=subscription)
        attention += 1 if health["status"] == "attention" else 0
        risk += 1 if health["status"] == "risk" else 0
        no_sales_data += 1 if not health["checks"]["has_sales_data"] else 0
        with_form_errors += 1 if counts["form_errors"] else 0
        handoff += counts["handoff_conversations"]
    return {
        "total_monitored": total,
        "attention_merchants": attention,
        "risk_merchants": risk,
        "no_sales_data_merchants": no_sales_data,
        "form_error_merchants": with_form_errors,
        "handoff_conversations": handoff,
        "new_leads_30d": Lead.objects.filter(created_at__gte=since, is_archived=False).count(),
        "form_errors_30d": LeadFormSubmissionError.objects.filter(created_at__gte=since).count(),
        "failed_connectors": BusinessConnector.objects.filter(status__in=[BusinessConnector.Statuses.FAILED, BusinessConnector.Statuses.EXPIRED_CREDENTIALS]).count(),
    }


def platform_failure_summary():
    """Persisted failed jobs/events, not a claim about live provider health."""
    from apps.automations.models import AutomationRun
    from apps.integrations.models import IntegrationEventLog
    from apps.notifications.models import Notification
    from apps.core.models import ExportJob

    counts = {
        "automations": AutomationRun.objects.filter(status=AutomationRun.Statuses.FAILED).count(),
        "notifications": Notification.objects.filter(status=Notification.Statuses.FAILED).count(),
        "integrations": IntegrationEventLog.objects.filter(status=IntegrationEventLog.Statuses.FAILED).count(),
        "exports": ExportJob.objects.filter(status=ExportJob.Statuses.FAILED).count(),
    }
    return {"count": sum(counts.values()), "items": [], "by_type": counts}
