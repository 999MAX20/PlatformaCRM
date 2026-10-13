"""Analytics page aggregates. Event periods and current queues are kept separate."""
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from django.db.models import Count, Exists, OuterRef, Q
from django.utils import timezone
from rest_framework import serializers

from apps.analytics.crm_metrics import _scoped, _visible_performance_members, _performance_scope
from apps.analytics.financial_metrics import financial_report
from apps.bots.models import BotConversation
from apps.businesses.access import Actions, Resources, can
from apps.businesses.capabilities import resource_is_enabled
from apps.core.date_ranges import parse_bounded_date_range
from apps.core.work_queues import overdue_tasks_queryset
from apps.crm.models import Deal
from apps.leads.models import Lead
from apps.scheduling.models import Appointment
from apps.tasks.models import Task


class WorkspacePeriod(serializers.Serializer):
    start = serializers.DateField(required=False)
    end = serializers.DateField(required=False)


def workspace_period(business, params):
    period = WorkspacePeriod(data={key: params[key] for key in ("start", "end") if params.get(key)})
    period.is_valid(raise_exception=True)
    values = {key: value.isoformat() for key, value in period.validated_data.items()}
    values.setdefault("end", timezone.localdate(timezone=ZoneInfo(business.timezone)).isoformat())
    return parse_bounded_date_range(values, default_days=30)


def _bounds(business, start, end):
    tz = ZoneInfo(business.timezone)
    return datetime.combine(start, time.min, tz), datetime.combine(end + timedelta(days=1), time.min, tz)


def _during(queryset, field, bounds):
    return queryset.filter(**{f"{field}__gte": bounds[0], f"{field}__lt": bounds[1]})


def _rate(numerator, denominator):
    return round(numerator * 100 / denominator, 1) if denominator else None


def _by(queryset, field):
    return {row[field]: row["count"] for row in queryset.order_by().values(field).annotate(count=Count("pk", distinct=True))}


def build_analytics_workspace(business, *, user, start_date, end_date, now=None):
    now = now or timezone.now()
    bounds = _bounds(business, start_date, end_date)
    models = {
        Resources.LEADS: Lead, Resources.DEALS: Deal, Resources.APPOINTMENTS: Appointment,
        Resources.TASKS: Task, Resources.CONVERSATIONS: BotConversation,
    }
    availability = {
        resource: resource_is_enabled(business, resource) and can(user, business, resource, Actions.VIEW).allowed
        for resource in models
    }
    scoped = {resource: _scoped(model.objects.filter(business=business), user, business, resource)
              for resource, model in models.items()}
    leads = _during(scoped[Resources.LEADS], "created_at", bounds)
    deals = scoped[Resources.DEALS]
    # One lead counts once, even with several deals. Conversions after the report
    # end are excluded; a visible deal must reference a visible cohort lead.
    leads = leads.annotate(has_deal=Exists(deals.filter(lead_id=OuterRef("pk"), created_at__lt=bounds[1])))
    appointments = _during(scoped[Resources.APPOINTMENTS], "start_at", bounds)
    won = _during(deals.filter(status=Deal.Statuses.WON), "won_at", bounds)
    lost = _during(deals.filter(status=Deal.Statuses.LOST), "lost_at", bounds)
    current_deals = deals.filter(is_archived=False, status=Deal.Statuses.OPEN)
    tasks = scoped[Resources.TASKS].filter(is_archived=False).exclude(status__in=[Task.Statuses.DONE, Task.Statuses.CANCELLED])
    overdue = overdue_tasks_queryset(queryset=tasks, now=now)
    conversations = scoped[Resources.CONVERSATIONS].filter(is_archived=False, status=BotConversation.Statuses.OPEN)
    unanswered = conversations.filter(Q(unread_count__gt=0) | Q(handoff_required=True)).distinct()
    lead_counts = leads.aggregate(total=Count("pk", distinct=True), converted=Count("pk", distinct=True, filter=Q(has_deal=True)))
    appointment_counts = _by(appointments, "status")
    appointment_total = sum(appointment_counts.values())
    source_rows = list(leads.order_by().values("source").annotate(
        leads=Count("pk", distinct=True), converted=Count("pk", distinct=True, filter=Q(has_deal=True)),
    ).order_by("-leads", "source"))
    conversion_available = availability[Resources.LEADS] and availability[Resources.DEALS]
    for row in source_rows:
        row["conversion_rate"] = _rate(row["converted"], row["leads"]) if conversion_available else None
        if not conversion_available:
            row["converted"] = None
    # Service names come only from accessible appointments, not an unscoped catalog.
    service_rows = list(appointments.order_by().values("service_id", "service__name").annotate(
        total=Count("pk", distinct=True),
        completed=Count("pk", distinct=True, filter=Q(status=Appointment.Statuses.COMPLETED)),
        no_show=Count("pk", distinct=True, filter=Q(status=Appointment.Statuses.NO_SHOW)),
    ).order_by("-total", "service_id"))
    team = _team_rows(business, user, leads, won, lost, tasks, overdue, unanswered, availability)
    return {
        "business": business.pk,
        "period": {"start": start_date.isoformat(), "end": end_date.isoformat(), "timezone": business.timezone},
        "generated_at": now.isoformat(), "availability": availability,
        "leads": {
            "total": lead_counts["total"] if availability[Resources.LEADS] else None,
            "converted": lead_counts["converted"] if conversion_available else None,
            "conversion_rate": _rate(lead_counts["converted"], lead_counts["total"]) if conversion_available else None,
        },
        "deals": {"won": won.count() if availability[Resources.DEALS] else None,
                  "lost": lost.count() if availability[Resources.DEALS] else None,
                  "open_now": current_deals.count() if availability[Resources.DEALS] else None},
        "appointments": {
            "total": appointment_total if availability[Resources.APPOINTMENTS] else None,
            "by_status": appointment_counts if availability[Resources.APPOINTMENTS] else None,
            "no_show_rate": _rate(appointment_counts.get(Appointment.Statuses.NO_SHOW, 0), appointment_total)
                            if availability[Resources.APPOINTMENTS] else None,
        },
        "sources": source_rows, "services": service_rows,
        "team": team,
        "current": {
            "new_leads": scoped[Resources.LEADS].filter(is_archived=False, status=Lead.Statuses.NEW).count()
                         if availability[Resources.LEADS] else None,
            "overdue_tasks": overdue.count() if availability[Resources.TASKS] else None,
            "unanswered": unanswered.count() if availability[Resources.CONVERSATIONS] else None,
        },
        "financial": financial_report(business, user=user, start_date=start_date, end_date=end_date, now=now),
    }


def _team_rows(business, user, leads, won, lost, tasks, overdue, unanswered, availability):
    members = _visible_performance_members(business=business, user=user).select_related("user").order_by("user__full_name", "pk")
    # Apply record scope FIRST, then the established team-report member boundary.
    maps = {
        "leads": (Resources.LEADS, _by(leads, "responsible_user_id")),
        "converted": (Resources.DEALS, _by(leads.filter(has_deal=True), "responsible_user_id")),
        "won": (Resources.DEALS, _by(won, "owner_id")),
        "lost": (Resources.DEALS, _by(lost, "owner_id")),
        "open_tasks": (Resources.TASKS, _by(tasks, "assignee_id")),
        "overdue_tasks": (Resources.TASKS, _by(overdue, "assignee_id")),
        "unanswered": (Resources.CONVERSATIONS, _by(unanswered, "assigned_to_id")),
    }
    rows = []
    for member in members:
        row = {"id": member.user_id, "name": member.user.full_name or member.user.email, "role": member.role}
        row.update({key: values.get(member.user_id, 0) if availability[resource] else None
                    for key, (resource, values) in maps.items()})
        if not availability[Resources.LEADS]:
            row["converted"] = None
        row["conversion_rate"] = _rate(row["converted"], row["leads"]) if row["leads"] is not None and row["converted"] is not None else None
        rows.append(row)
    return {"available": bool(rows), "scope": _performance_scope(business=business, user=user), "rows": rows}
