"""Internal reception deadlines; callers authorize and persist the request separately."""
from datetime import datetime, timedelta, timezone as datetime_timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.branches.models import Branch, ScheduleDay
from apps.branches.schedule import day_intervals, normalize_intervals
from apps.scheduling.models import WorkingHours


def reception_acceptance_deadline(*, business, branch_id, requested_at, patient_in_clinic):
    if (type(branch_id) is not int or branch_id <= 0 or type(patient_in_clinic) is not bool
            or not isinstance(requested_at, datetime) or timezone.is_naive(requested_at)):
        raise ValidationError({"deadline": "Provide a branch, an aware request time and the patient presence flag."})
    branch = Branch.objects.filter(pk=branch_id, business=business, is_active=True, archived_at__isnull=True).first()
    if branch is None:
        raise ValidationError({"branch": "Select an active branch of this business."})
    instant = requested_at.astimezone(datetime_timezone.utc)
    if patient_in_clinic:
        return instant + timedelta(minutes=5)
    try:
        zone = ZoneInfo(business.timezone)
    except (ZoneInfoNotFoundError, ValueError, TypeError):
        raise ValidationError({"timezone": "Configure the business timezone before calculating working time."}) from None
    business_hours = None
    if branch.uses_business_defaults:
        business_hours = {row.weekday: row for row in WorkingHours.objects.filter(business=business, resource__isnull=True)}
        if not any(not row.is_day_off and row.start_time < row.end_time for row in business_hours.values()):
            return None
    elif not ScheduleDay.objects.filter(business=business, branch=branch, resource__isnull=True).exclude(intervals=[]).exists():
        return None
    remaining = timedelta(minutes=30)
    day = instant.astimezone(zone).date()
    # A missing opening within a year is unresolved configuration, never a made-up due date.
    for offset in range(366):
        date = day + timedelta(days=offset)
        if business_hours is None:
            intervals = normalize_intervals(day_intervals(branch, None, date=date))
        else:
            row = business_hours.get(date.weekday())
            intervals = [] if row is None or row.is_day_off else normalize_intervals([
                {"start": row.start_time.strftime("%H:%M"), "end": row.end_time.strftime("%H:%M")}])
        for interval in intervals:
            start, end = [datetime.combine(date, datetime.strptime(interval[key], "%H:%M").time(), zone)
                          .astimezone(datetime_timezone.utc) for key in ("start", "end")]
            start = max(start, instant)
            available = end - start
            if available <= timedelta(0):
                continue
            if available >= remaining:
                return start + remaining
            remaining -= available
    return None
