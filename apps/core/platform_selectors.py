from django.db.models import Count, Max, Q
from django.utils import timezone
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.leads.models import Lead, LeadForm, LeadFormSubmissionError
from apps.tasks.models import Task
from apps.bots.models import BotConversation
from apps.integrations.models import BusinessConnector, BusinessEvent
from apps.core.models import AuditLog
from apps.integrations.sanitization import sanitize_error_text
from apps.core.platform_reads import read_platform_source
from apps.core.service_status import business_service_status_many

def _merchant_counts(business):
    return _merchant_counts_many([business])[business.pk]


def _merchant_counts_many(businesses):
    """Batch operational counts for exactly the selected businesses."""
    businesses = list(businesses)
    fields = ("lead_count", "new_leads", "clients_count", "open_tasks",
              "unread_conversations", "handoff_conversations", "failed_connectors",
              "pending_connectors", "connected_connectors", "form_errors", "lead_forms", "sales_events")
    result = {item.pk: {**dict.fromkeys(fields, 0), "latest_activity_at": None,
                        "unavailable_sources": []} for item in businesses}
    if not result:
        return result

    def collect(model, metrics, *, latest=False):
        values = dict(metrics)
        if latest:
            values["latest"] = Max("created_at" if model is BusinessEvent else "updated_at")
        rows = read_platform_source(lambda: list(model.objects.filter(business_id__in=result)
                                                 .values("business_id").annotate(**values)))
        if rows is None:
            for counts in result.values():
                counts.update(dict.fromkeys(metrics, None))
                counts["unavailable_sources"].append(model._meta.label_lower)
            return
        for row in rows:
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
    collect(LeadFormSubmissionError, {"form_errors": Count("pk", filter=Q(
        created_at__gte=timezone.now() - timezone.timedelta(days=30)))})
    collect(LeadForm, {"lead_forms": Count("pk", filter=Q(is_active=True))})
    collect(BusinessEvent, {"sales_events": Count("pk", filter=Q(event_type__in=["sale.recorded", "sale_recorded"]))}, latest=True)
    for counts in result.values():
        if any(source in counts["unavailable_sources"] for source in
               ("leads.lead", "tasks.task", "bots.botconversation", "integrations.businessevent")):
            counts["latest_activity_at"] = None
    return result


def _merchant_health(business, counts, subscription=None):
    checks = {
        "has_owner": bool(business.owner_id),
        "has_landing": bool(business.landing_id or business.landing_domain),
        "has_lead_form": None if counts["lead_forms"] is None else counts["lead_forms"] > 0,
        "has_leads": None if counts["lead_count"] is None else counts["lead_count"] > 0,
        "has_sales_data": None if counts["sales_events"] is None else counts["sales_events"] > 0,
        "has_connected_source": None if counts["connected_connectors"] is None else counts["connected_connectors"] > 0,
        "has_subscription": bool(subscription),
    }
    blockers = []
    if counts["form_errors"]:
        blockers.append(f"Ошибки формы заявок: {counts['form_errors']}")
    if counts["failed_connectors"]:
        blockers.append(f"Интеграции требуют внимания: {counts['failed_connectors']}")
    status = "attention" if blockers else "unknown" if counts.get("unavailable_sources") else "clear"

    if blockers:
        next_action = blockers[0]
    elif counts["new_leads"]:
        next_action = "Проверить новые заявки"
    elif status == "unknown":
        next_action = "Часть данных недоступна"
    else:
        next_action = "Мониторить активность пилота"

    return {
        # Retained for compatibility, no synthetic readiness percentage.
        "score": None,
        "scope": "recorded_signals",
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
    if counts["new_leads"]:
        next_steps.append({"key": "check_new_leads", "label": "Проверить новые заявки", "href": "/app/leads"})
    if not next_steps:
        next_steps.append({"key": "refresh" if counts.get("unavailable_sources") else "monitor", "label": health["next_action"], "href": f"/platform/merchants/{business.id}"})
    # A platform diagnostic never implies access to the currently selected CRM tenant.
    for step in next_steps:
        step["href"] = f"/platform/merchants/{business.id}"

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
    # Operational counts must not depend on the optional billing source.
    businesses = list(Business.objects.all())
    total = len(businesses)
    counts_by_id = _merchant_counts_many(businesses)
    attention = 0
    risk = 0
    no_sales_data = 0
    with_form_errors = 0
    for business in businesses:
        counts = counts_by_id[business.pk]
        health = _merchant_health(business, counts)
        attention += 1 if health["status"] == "attention" else 0
        risk += 1 if health["status"] == "risk" else 0
        no_sales_data += 1 if health["checks"]["has_sales_data"] is False else 0
        with_form_errors += 1 if counts["form_errors"] else 0
    unavailable_sources = sorted({source for counts in counts_by_id.values() for source in counts["unavailable_sources"]})
    def total_count(field):
        values = [counts[field] for counts in counts_by_id.values()]
        return None if any(value is None for value in values) else sum(values)
    return {
        "total_monitored": total,
        "attention_merchants": None if any(counts["failed_connectors"] is None or counts["form_errors"] is None for counts in counts_by_id.values()) else attention,
        "risk_merchants": risk,
        "no_sales_data_merchants": None if any(counts["sales_events"] is None for counts in counts_by_id.values()) else no_sales_data,
        "form_error_merchants": None if any(counts["form_errors"] is None for counts in counts_by_id.values()) else with_form_errors,
        "handoff_conversations": total_count("handoff_conversations"),
        "new_leads_30d": read_platform_source(lambda: Lead.objects.filter(created_at__gte=since, is_archived=False).count()),
        "form_errors_30d": total_count("form_errors"),
        "failed_connectors": total_count("failed_connectors"),
        "unavailable_sources": unavailable_sources,
    }


def platform_failure_summary():
    """Persisted failed jobs/events, not a claim about live provider health."""
    from apps.automations.models import AutomationRun
    from apps.integrations.models import IntegrationEventLog
    from apps.notifications.models import Notification
    from apps.core.models import ExportJob

    counts = {
        "automations": read_platform_source(lambda: AutomationRun.objects.filter(status=AutomationRun.Statuses.FAILED).count()),
        "notifications": read_platform_source(lambda: Notification.objects.filter(status=Notification.Statuses.FAILED).count()),
        "integrations": read_platform_source(lambda: IntegrationEventLog.objects.filter(status=IntegrationEventLog.Statuses.FAILED).count()),
        "exports": read_platform_source(lambda: ExportJob.objects.filter(status=ExportJob.Statuses.FAILED).count()),
    }
    return {"count": None if None in counts.values() else sum(counts.values()), "items": [], "by_type": counts}


def platform_clinic_service_statuses(businesses):
    ids = [business.pk for business in businesses]
    statuses = read_platform_source(lambda: business_service_status_many(ids))
    if statuses is not None:
        return statuses
    return {pk: {"status": "unknown", "components": [], "source_available": False} for pk in ids}
