"""Validated read-only filters shared by the three CRM workspaces.

These helpers only narrow an already permission-scoped queryset.
"""
from datetime import date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from zoneinfo import ZoneInfo

from django.db.models import Q
from rest_framework.exceptions import ValidationError


def values(params, key, *, choices=None, ids=False):
    raw = params.getlist(key) if hasattr(params, "getlist") else [params.get(key, "")]
    result = list(dict.fromkeys(part.strip() for item in raw for part in str(item).split(",") if part.strip()))
    if len(result) > 100:
        raise ValidationError({key: "Select at most 100 values."})
    if choices is not None and any(item not in choices for item in result):
        raise ValidationError({key: "Invalid filter value."})
    if ids:
        if any(not item.isdecimal() or not 0 < int(item) <= 9223372036854775807 for item in result):
            raise ValidationError({key: "Select valid positive identifiers."})
        return [int(item) for item in result]
    return result


def choice(params, key, choices, default=""):
    value = params.get(key, default)
    if value not in choices:
        raise ValidationError({key: "Invalid filter value."})
    return value


def dates(params, prefix):
    parsed = []
    for suffix in ("from", "to"):
        key = f"{prefix}_{suffix}"
        raw = params.get(key)
        try:
            parsed.append(date.fromisoformat(raw) if raw else None)
        except (ValueError, TypeError):
            raise ValidationError({key: "Use a valid YYYY-MM-DD date."})
    start, end = parsed
    if start and end and start > end:
        raise ValidationError({f"{prefix}_to": "End date must not precede start date."})
    if end == date.max:
        raise ValidationError({f"{prefix}_to": "Date is outside the supported range."})
    return start, end


def business_date_range(queryset, params, *, prefix="created", field="created_at", date_field=False):
    start, end = dates(params, prefix)
    if not start and not end:
        return queryset
    if date_field:
        if start:
            queryset = queryset.filter(**{f"{field}__gte": start})
        if end:
            queryset = queryset.filter(**{f"{field}__lte": end})
        return queryset
    # Each business has its own local day boundaries, including DST transitions.
    condition = Q(pk__in=[])
    for business_id, timezone_name in queryset.order_by().values_list("business_id", "business__timezone").distinct():
        zone = ZoneInfo(timezone_name or "UTC")
        part = Q(business_id=business_id)
        if start:
            part &= Q(**{f"{field}__gte": datetime.combine(start, time.min, zone)})
        if end:
            part &= Q(**{f"{field}__lt": datetime.combine(end + timedelta(days=1), time.min, zone)})
        condition |= part
    return queryset.filter(condition)


def archive_filter(queryset, params):
    mode = choice(params, "archive", ("active", "archived", "all"), "active")
    if mode == "active":
        return queryset.filter(is_archived=False)
    if mode == "archived":
        return queryset.filter(is_archived=True)
    return queryset


def assignment_filter(queryset, params, *, field, user):
    scope = choice(params, "scope", ("all", "mine"), "all")
    if scope == "mine":
        queryset = queryset.filter(**{field: user.pk})
    selected = values(params, "assignees")
    if selected:
        condition = Q(pk__in=[])
        for item in selected:
            if item == "unassigned":
                condition |= Q(**{f"{field}__isnull": True})
            elif item.isdecimal() and 0 < int(item) <= 9223372036854775807:
                condition |= Q(**{field: int(item)})
            else:
                raise ValidationError({"assignees": "Invalid assignee."})
        queryset = queryset.filter(condition)
    return queryset


def amount_range(queryset, params):
    bounds = []
    for key in ("amount_min", "amount_max"):
        raw = params.get(key)
        try:
            value = Decimal(raw) if raw not in (None, "") else None
            if value is not None and (not value.is_finite() or value < 0):
                raise InvalidOperation
        except (InvalidOperation, ValueError, TypeError):
            raise ValidationError({key: "Use a non-negative finite amount."})
        bounds.append(value)
    lower, upper = bounds
    if lower is not None and upper is not None and lower > upper:
        raise ValidationError({"amount_max": "Maximum must not be less than minimum."})
    if lower is not None:
        queryset = queryset.filter(amount__gte=lower)
    if upper is not None:
        queryset = queryset.filter(amount__lte=upper)
    return queryset
