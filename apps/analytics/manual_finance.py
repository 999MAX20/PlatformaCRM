"""Exact cash movement in the explicitly selected manual journal, not profit."""
from datetime import datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from django.db.models import Count, Max, Q, Sum
from django.utils import timezone

from apps.businesses.access import Actions, Resources, can
from apps.businesses.capabilities import resource_is_enabled
from apps.businesses.models import RolePermission
from apps.payments.models import Payment


def business_period(business, start_date, end_date):
    zone = ZoneInfo(business.timezone)
    return (datetime.combine(start_date, time.min, tzinfo=zone),
        datetime.combine(end_date + timedelta(days=1), time.min, tzinfo=zone))


def manual_finance_allowed(business, user):
    return all(resource_is_enabled(business, resource)
        and (permission := can(user, business, resource, Actions.VIEW)).allowed
        and permission.scope == RolePermission.Scopes.BUSINESS
        for resource in (Resources.PAYMENTS, Resources.CLIENTS))


def period_payments(business, start_date, end_date):
    start, end = business_period(business, start_date, end_date)
    return Payment.objects.filter(business=business, occurred_at__gte=start, occurred_at__lt=end)


def manual_financial_report(business, *, user, start_date, end_date, result):
    if not manual_finance_allowed(business, user):
        return {**result, "reason": "permission_denied"}
    queryset = period_payments(business, start_date, end_date)
    source = {"id": None, "name": "manual", "provider": "manual"}
    base = {**result, "source": source, "coverage": "recorded_manual_operations",
        "profit": None, "debt": None, "profit_reason": "expenses_not_recorded", "debt_reason": "accruals_not_recorded"}
    if queryset.exclude(currency=business.currency).exists():
        return {**base, "reason": "currency_mismatch"}
    sums = queryset.aggregate(receipts=Sum("amount", filter=Q(kind="receipt")),
        refunds=Sum("amount", filter=Q(kind="refund")), count=Count("pk"), recorded_at=Max("created_at"))
    receipts, refunds = sums["receipts"] or Decimal("0.00"), sums["refunds"] or Decimal("0.00")
    return {**base, "state": "available", "reason": None,
        "receipts": str(receipts), "refunds": str(refunds), "net_receipts": str(receipts - refunds),
        "operation_count": sums["count"], "as_of": timezone.now().isoformat(),
        "last_recorded_at": sums["recorded_at"].isoformat() if sums["recorded_at"] else None}
