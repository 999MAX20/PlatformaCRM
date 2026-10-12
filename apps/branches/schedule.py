"""Deterministic local-time schedules and Business-wide specialist travel."""
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.domain_errors import ScheduleConflict
from apps.scheduling.models import Appointment
from .models import Branch, BranchService, BranchTravelTime, ScheduleDay, SpecialistAbsence, SpecialistBranch


def resolve_branch(business, branch=None):
    if branch is not None:
        if branch.business_id != business.pk:
            raise ValidationError({"branch": "Select a branch of this business."})
        current = Branch.objects.filter(pk=branch.pk, business=business, is_active=True, archived_at__isnull=True).first()
        if current is None:
            raise ValidationError({"branch": "The branch is unavailable for new bookings."})
        return current
    if not Branch.objects.filter(business=business).exists():
        return None  # Legacy/no-location setup, never infer among several branches.
    branches = list(Branch.objects.filter(business=business, is_active=True, archived_at__isnull=True)[:2])
    if len(branches) != 1:
        raise ValidationError({"branch": "Select a branch before choosing an appointment time."})
    return branches[0]


def booking_terms(business, service, resource, branch=None, *, appointment=None):
    branch = resolve_branch(business, branch)
    if branch is None:
        return None, service.duration_minutes, service.price_from
    offer = BranchService.objects.filter(business=business, branch=branch, service=service, is_active=True).first()
    if offer is None:
        raise ValidationError({"service": "This service is unavailable at the selected branch."})
    if resource is not None and not SpecialistBranch.objects.filter(
        business=business, branch=branch, resource=resource, is_active=True, services=service,
    ).exists():
        raise ValidationError({"resource": "Select a specialist who offers this service at this branch."})
    if appointment and appointment.branch_id == branch.pk and appointment.booked_duration_minutes:
        return branch, appointment.booked_duration_minutes, appointment.booked_price
    return branch, offer.duration_minutes, offer.price_from


def appointment_snapshot(business, service, resource, branch=None, *, appointment=None):
    branch, duration, price = booking_terms(business, service, resource, branch, appointment=appointment)
    return {"branch": branch, "branch_name": branch.name if branch else "",
            "branch_address": branch.address if branch else "", "booked_price": price,
            "booked_duration_minutes": duration}


def normalize_intervals(intervals):
    if not isinstance(intervals, list) or len(intervals) > 24:
        raise ValidationError({"intervals": "Provide up to 24 time intervals."})
    result = []
    for item in intervals:
        try:
            start = datetime.strptime(item["start"], "%H:%M").time()
            end = datetime.strptime(item["end"], "%H:%M").time()
        except (KeyError, TypeError, ValueError):
            raise ValidationError({"intervals": "Use start/end times in HH:MM format."})
        if start >= end:
            raise ValidationError({"intervals": "Start must precede end; split overnight work into separate dates."})
        result.append({"start": start.strftime("%H:%M"), "end": end.strftime("%H:%M")})
    result.sort(key=lambda item: item["start"])
    if any(left["end"] > right["start"] for left, right in zip(result, result[1:])):
        raise ValidationError({"intervals": "Working intervals must not overlap."})
    return result


def day_intervals(branch, resource, *, date=None, weekday=None):
    query = ScheduleDay.objects.filter(branch=branch, resource=resource)
    row = query.filter(date=date).first() if date is not None else None
    if row is None:
        row = query.filter(date__isnull=True, weekday=date.weekday() if date else weekday).first()
    return row.intervals if row else []


def travel_minutes(business, left_id, right_id):
    if left_id == right_id:
        return 0
    if left_id is None or right_id is None:
        return None
    row = BranchTravelTime.objects.filter(business=business, from_branch_id=min(left_id, right_id),
                                         to_branch_id=max(left_id, right_id)).first()
    return row.minutes if row else None


def _minute(value):
    hours, minutes = value.split(":")
    return int(hours) * 60 + int(minutes)


def validate_specialist_schedule(resource):
    """Validate recurring and explicit dates together under the Business write lock."""
    branches = list(Branch.objects.filter(specialist_assignments__resource=resource,
                                         specialist_assignments__is_active=True, is_active=True, archived_at__isnull=True))
    dates = set(ScheduleDay.objects.filter(branch__in=branches, date__isnull=False)
                .filter(Q(resource=resource) | Q(resource__isnull=True)).values_list("date", flat=True))
    for weekday, date in [(day, None) for day in range(7)] + [(None, day) for day in dates]:
        periods = []
        for branch in branches:
            for interval in day_intervals(branch, resource, date=date, weekday=weekday):
                periods.append((_minute(interval["start"]), _minute(interval["end"]), branch.pk))
        periods.sort()
        for previous, following in zip(periods, periods[1:]):
            if previous[2] == following[2]:
                continue
            travel = travel_minutes(resource.business, previous[2], following[2])
            if travel is None or following[0] < previous[1] + travel:
                raise ScheduleConflict("Specialist shifts overlap or leave insufficient travel time.",
                                       errors={"intervals": "Configure travel time and leave enough time between branches."})


def resource_absent(resource, date, branch=None):
    return (SpecialistAbsence.objects.filter(business=resource.business, resource=resource, starts_on__lte=date, ends_on__gte=date)
            .filter(Q(branch__isnull=True) | Q(branch=branch)).exists())


def _windows(branch, resource, date):
    from apps.scheduling.availability import business_zone
    if resource_absent(resource, date, branch):
        return []
    branch_hours = day_intervals(branch, None, date=date)
    staff_hours = day_intervals(branch, resource, date=date)
    zone = business_zone(branch.business)
    windows = []
    for staff in staff_hours:
        for opening in branch_hours:
            start, end = max(staff["start"], opening["start"]), min(staff["end"], opening["end"])
            if start < end:
                windows.append((timezone.make_aware(datetime.combine(date, datetime.strptime(start, "%H:%M").time()), zone),
                                timezone.make_aware(datetime.combine(date, datetime.strptime(end, "%H:%M").time()), zone)))
    return sorted(windows)


def _conflicts(business, branch, resource, start, end, *, exclude=None):
    from apps.scheduling.availability import business_zone
    visits = Appointment.objects.filter(business=business, resource=resource)
    visits = visits.exclude(status__in=[Appointment.Statuses.CANCELLED, Appointment.Statuses.RESCHEDULED])
    if exclude:
        visits = visits.exclude(pk=exclude.pk)
    zone = business_zone(business)
    # At most one day of configured travel; global specialist occupancy is
    # deliberately independent of the actor's branch filter and visibility.
    visits = visits.filter(start_at__lt=end + timedelta(days=1), end_at__gt=start - timedelta(days=1))
    for visit in visits.only("start_at", "end_at", "branch_id"):
        if start < visit.end_at and end > visit.start_at:
            return True
        travel = travel_minutes(business, branch.pk, visit.branch_id)
        if travel is None:
            if visit.start_at.astimezone(zone).date() == start.astimezone(zone).date():
                return True
            continue
        if start < visit.end_at + timedelta(minutes=travel) and end > visit.start_at - timedelta(minutes=travel):
            return True
    return False


def branch_available_slots(business, service, date, *, resource, branch, after_time=None, exclude_appointment=None):
    from apps.scheduling.availability import SLOT_STEP_MINUTES, business_zone
    branch, duration, _ = booking_terms(business, service, resource, branch, appointment=exclude_appointment)
    result = []
    for start, end in _windows(branch, resource, date):
        current = start
        if after_time:
            threshold = after_time if isinstance(after_time, datetime) else datetime.combine(date, after_time)
            if timezone.is_naive(threshold):
                threshold = timezone.make_aware(threshold, business_zone(business))
            while current < threshold:
                current += timedelta(minutes=SLOT_STEP_MINUTES)
        while current + timedelta(minutes=duration) <= end:
            finish = current + timedelta(minutes=duration)
            if not _conflicts(business, branch, resource, current, finish, exclude=exclude_appointment):
                result.append(current)
            current += timedelta(minutes=SLOT_STEP_MINUTES)
    return sorted(set(result))


def validate_branch_slot(business, service, start, *, resource, branch, exclude_appointment=None):
    from apps.scheduling.availability import business_zone
    branch, duration, _ = booking_terms(business, service, resource, branch, appointment=exclude_appointment)
    zone = business_zone(business)
    if timezone.is_naive(start):
        start = timezone.make_aware(start, zone)
    end = start + timedelta(minutes=duration)
    windows = _windows(branch, resource, start.astimezone(zone).date())
    if not any(start >= lower and end <= upper for lower, upper in windows):
        raise ScheduleConflict(errors={"start_at": "Select a time inside branch and specialist working hours."})
    if _conflicts(business, branch, resource, start, end, exclude=exclude_appointment):
        raise ScheduleConflict(errors={"start_at": "The specialist is busy or needs travel time."})
    return end
