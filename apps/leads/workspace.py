"""Read model for the unified lead filter toolbar."""
from django.db.models import BooleanField, Case, Count, Q, Value, When
from django.utils import timezone

from apps.core.crm_filters import archive_filter, assignment_filter, business_date_range, choice, values
from apps.core.work_queues import OPEN_LEAD_STATUSES
from apps.leads.models import Lead
from apps.leads.selectors import annotate_lead_next_task


def lead_workspace_queryset(queryset, request, *, apply_quick=True):
    params = request.query_params
    queryset = annotate_lead_next_task(queryset, actor=request.user)
    opened = Q(is_archived=False, status__in=OPEN_LEAD_STATUSES)
    reasons = {
        "unassigned": opened & Q(responsible_user__isnull=True),
        "no_action": opened & Q(next_task_id__isnull=True),
        "overdue_action": opened & Q(next_task_due_at__lt=timezone.now()),
    }
    queryset = queryset.annotate(**{
        f"attention_{key}": Case(When(condition, then=Value(True)), default=Value(False), output_field=BooleanField())
        for key, condition in reasons.items()
    })
    queryset = archive_filter(queryset, params)
    queryset = assignment_filter(queryset, params, field="responsible_user_id", user=request.user)
    queryset = business_date_range(queryset, params)
    statuses = values(params, "statuses", choices=[*Lead.Statuses.values, "all"])
    if "all" not in statuses:
        queryset = queryset.filter(status__in=statuses or OPEN_LEAD_STATUSES)
    sources = values(params, "source", choices=Lead.Sources.values)
    if sources:
        queryset = queryset.filter(source__in=sources)
    search = (params.get("search") or "").strip()
    if search:
        queryset = queryset.filter(Q(client__full_name__icontains=search) | Q(client__phone__icontains=search)
            | Q(client__email__icontains=search) | Q(message__icontains=search) | Q(service__name__icontains=search))
    selected_reasons = values(params, "attention_reason", choices=reasons)
    if selected_reasons:
        condition = Q(pk__in=[])
        for reason in selected_reasons:
            condition |= Q(**{f"attention_{reason}": True})
        queryset = queryset.filter(condition)
    quick = choice(params, "quick", ("all", "new", "in_progress", "attention"), "all")
    if apply_quick:
        if quick == "new":
            queryset = queryset.filter(status="new")
        elif quick == "in_progress":
            queryset = queryset.filter(status__in=["contacted", "in_progress"])
        elif quick == "attention":
            queryset = queryset.filter(Q(attention_unassigned=True) | Q(attention_no_action=True) | Q(attention_overdue_action=True))
    ordering = choice(params, "ordering", ("-created_at", "created_at", "-updated_at", "updated_at", "status", "-status", "source", "-source"), "-created_at")
    return queryset.order_by(ordering, "-pk")


def lead_workspace_summary(queryset):
    return queryset.aggregate(
        total=Count("pk", distinct=True),
        new=Count("pk", filter=Q(status="new"), distinct=True),
        in_progress=Count("pk", filter=Q(status__in=["contacted", "in_progress"]), distinct=True),
        attention=Count("pk", filter=Q(attention_unassigned=True) | Q(attention_no_action=True) | Q(attention_overdue_action=True), distinct=True),
    )
