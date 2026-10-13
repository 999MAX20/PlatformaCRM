"""Validated deal workspace filters over the existing scoped read model."""
from django.db.models import Q

from apps.core.crm_filters import amount_range, archive_filter, assignment_filter, business_date_range, choice, values
from apps.core.work_queues import no_next_action_deals_queryset, sla_overdue_deals_queryset
from apps.crm.models import Deal
from apps.crm.selectors import stale_deals_queryset


def deal_workspace_queryset(queryset, request):
    params = request.query_params
    queryset = archive_filter(queryset, params)
    queryset = assignment_filter(queryset, params, field="owner_id", user=request.user)
    pipelines = values(params, "pipeline", ids=True)
    if pipelines:
        queryset = queryset.filter(pipeline_id__in=pipelines)
    stages = values(params, "stage", ids=True)
    if stages:
        queryset = queryset.filter(stage_id__in=stages)
    statuses = values(params, "statuses", choices=[*Deal.Statuses.values, "all"])
    if "all" not in statuses:
        queryset = queryset.filter(status__in=statuses or [Deal.Statuses.OPEN])
    sources = values(params, "source")
    if sources:
        queryset = queryset.filter(source__in=sources)
    search = (params.get("search") or "").strip()
    if search:
        queryset = queryset.filter(Q(title__icontains=search) | Q(source__icontains=search)
            | Q(client__full_name__icontains=search) | Q(client__phone__icontains=search) | Q(client__email__icontains=search))
    queryset = amount_range(queryset, params)
    queryset = business_date_range(queryset, params)
    queryset = business_date_range(queryset, params, prefix="expected_close", field="expected_close_at", date_field=True)
    reasons = values(params, "attention_reason", choices=("sla", "no_action", "closing"))
    if reasons:
        opened = queryset.filter(status=Deal.Statuses.OPEN, is_archived=False)
        condition = Q(pk__in=[])
        if "sla" in reasons:
            condition |= Q(pk__in=sla_overdue_deals_queryset(opened).values("pk"))
        if "no_action" in reasons:
            condition |= Q(pk__in=no_next_action_deals_queryset(opened).values("pk"))
        if "closing" in reasons:
            # Same definition as the existing stale-deal selector.
            from django.utils import timezone
            condition |= Q(status="open", is_archived=False, expected_close_at__lt=timezone.now().date())
        queryset = queryset.filter(condition)
    quick = choice(params, "quick", ("all", "hot", "no_tasks"), "all")
    if quick == "hot":
        queryset = stale_deals_queryset(queryset.filter(is_archived=False))
    elif quick == "no_tasks":
        queryset = no_next_action_deals_queryset(queryset.filter(status="open", is_archived=False))
    ordering = choice(params, "ordering", ("-updated_at", "updated_at", "-created_at", "created_at", "amount", "-amount", "expected_close_at", "-expected_close_at"), "-updated_at")
    return queryset.order_by(ordering, "-pk")
