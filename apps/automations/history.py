"""Read projections over the caller's already-authorized automation queryset."""
from django.db.models import Count, Q


def filter_history(queryset, filters):
    if 'business' in filters:
        queryset = queryset.filter(business_id=filters['business'])
    for field in ('status', 'trigger_type'):
        if filters.get(field):
            queryset = queryset.filter(**{field: filters[field]})
    return queryset.order_by('-created_at', '-pk')


def run_summary(queryset):
    return queryset.aggregate(
        total=Count('pk', distinct=True),
        failed=Count('pk', filter=Q(status__in=['failed', 'error', 'cancelled', 'blocked']), distinct=True),
        retryable=Count('pk', filter=Q(status__in=['failed', 'cancelled']), distinct=True),
    )


def rule_summary(queryset):
    return queryset.aggregate(
        total=Count('pk', distinct=True),
        active=Count('pk', filter=Q(is_active=True), distinct=True),
    )
