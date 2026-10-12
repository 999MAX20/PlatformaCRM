"""Explicit first-location adoption; later branches start with no bookable services."""
from apps.scheduling.models import Appointment, Resource, WorkingHours, ScheduleException
from apps.services.models import Service
from .models import BranchService, SpecialistBranch, ScheduleDay


def _intervals(row):
    return [] if row.is_day_off else [{"start": row.start_time.strftime("%H:%M"), "end": row.end_time.strftime("%H:%M")}]


def _union(intervals):
    merged = []
    for item in sorted(intervals, key=lambda value: value["start"]):
        if merged and item["start"] <= merged[-1]["end"]:
            merged[-1]["end"] = max(merged[-1]["end"], item["end"])
        else:
            merged.append(dict(item))
    return merged


def adopt_first_branch(branch):
    business = branch.business
    service_ids = []
    for service in Service.objects.filter(business=business):
        BranchService.objects.get_or_create(branch=branch, service=service, defaults={
            "business": business, "price_from": service.price_from,
            "duration_minutes": service.duration_minutes, "is_active": service.is_active and not service.is_archived})
        service_ids.append(service.pk)
    resources = list(Resource.objects.filter(business=business, resource_type="staff"))
    for resource in resources:
        link, _ = SpecialistBranch.objects.get_or_create(branch=branch, resource=resource,
                                                        defaults={"business": business, "is_active": resource.retired_at is None})
        link.services.set(service_ids)
    rows = {(row.resource_id, row.weekday): row for row in WorkingHours.objects.filter(business=business)}
    for weekday in range(7):
        common = rows.get((None, weekday))
        opening = _intervals(common) if common else []
        for resource in resources:
            row = rows.get((resource.pk, weekday), common)
            intervals = _intervals(row) if row else []
            opening.extend(intervals)
            ScheduleDay.objects.get_or_create(branch=branch, resource=resource, weekday=weekday,
                defaults={"business": business, "intervals": intervals})
        # Legacy staff hours override rather than intersect company hours. Adopt
        # the union for the original location to preserve those existing slots.
        ScheduleDay.objects.get_or_create(branch=branch, resource=None, weekday=weekday,
            defaults={"business": business, "intervals": _union(opening)})
    for row in ScheduleException.objects.filter(business=business):
        ScheduleDay.objects.get_or_create(branch=branch, resource=row.resource, date=row.date,
                                           defaults={"business": business, "intervals": _intervals(row)})
    dates = ScheduleException.objects.filter(business=business).values_list("date", flat=True).distinct()
    for date in dates:
        from .schedule import day_intervals
        opening = list(day_intervals(branch, None, weekday=date.weekday()))
        for resource in resources:
            opening.extend(day_intervals(branch, resource, date=date))
        ScheduleDay.objects.get_or_create(branch=branch, resource=None, date=date,
            defaults={"business": business, "intervals": _union(opening)})
    for visit in Appointment.objects.filter(business=business, branch__isnull=True).select_related("service"):
        visit.branch = branch
        visit.branch_name = branch.name
        visit.branch_address = branch.address
        if not visit.booked_duration_minutes:
            visit.booked_price = visit.service.price_from
            visit.booked_duration_minutes = max(1, round((visit.end_at - visit.start_at).total_seconds() / 60))
        visit.save(update_fields=["branch", "branch_name", "branch_address", "booked_price", "booked_duration_minutes"])
