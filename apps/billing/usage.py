from datetime import date

from django.db.models import F

from apps.billing.entitlements import check_entitlement
from apps.billing.models import UsageCounter
from apps.billing.storage import storage_usage_summary


def current_period(today=None):
    today = today or date.today()
    start = today.replace(day=1)
    if start.month == 12:
        end = start.replace(year=start.year + 1, month=1)
    else:
        end = start.replace(month=start.month + 1)
    return start, end


def increment_usage(business, metric, amount=1):
    period_start, period_end = current_period()
    counter, _ = UsageCounter.objects.get_or_create(
        business=business,
        period_start=period_start,
        period_end=period_end,
        metric=metric,
        defaults={"value": 0},
    )
    UsageCounter.objects.filter(id=counter.id).update(value=F("value") + amount)
    counter.refresh_from_db(fields=["value"])
    return counter


def check_limit(business, metric):
    period_start, period_end = current_period()
    entitlement = check_entitlement(business, metric, requested=0)
    value = entitlement.value
    is_monthly = metric in {UsageCounter.Metrics.AI_REQUESTS, UsageCounter.Metrics.BOT_MESSAGES, UsageCounter.Metrics.CONVERSATIONS}
    limit = entitlement.limit
    return {
        "metric": metric,
        "value": value,
        "limit": limit,
        "is_limited": limit is not None,
        "is_over_limit": bool(limit is not None and value >= int(limit)),
        "period_kind": "month" if is_monthly else "current",
        "period_start": period_start if is_monthly else None,
        "period_end": period_end if is_monthly else None,
    }


def usage_summary(business):
    summary = [
        check_limit(business, metric)
        for metric in [
            UsageCounter.Metrics.AI_REQUESTS,
            UsageCounter.Metrics.BOT_MESSAGES,
            UsageCounter.Metrics.USERS,
            UsageCounter.Metrics.CONVERSATIONS,
        ]
    ]
    summary.append(storage_usage_summary(business))
    return summary
