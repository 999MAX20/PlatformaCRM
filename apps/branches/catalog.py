"""Read projections for shared single-point and explicitly configured catalogs."""
from dataclasses import dataclass

from apps.scheduling.models import Resource, ScheduleException, WorkingHours
from apps.services.models import Service
from .compatibility import _intervals, _union
from .models import BranchService, SpecialistBranch, SpecialistAbsence


@dataclass
class Offer:
    branch: object
    service: object
    duration_minutes: int
    price_from: object

    @property
    def branch_id(self):
        return self.branch.pk

    @property
    def service_id(self):
        return self.service.pk


@dataclass
class Assignment:
    branch: object
    resource: object
    service_ids: list

    @property
    def branch_id(self):
        return self.branch.pk

    @property
    def resource_id(self):
        return self.resource.pk


def booking_offers(branches):
    branches = [branch for branch in branches if branch.is_active and branch.archived_at is None]
    explicit = [branch for branch in branches if not branch.uses_business_defaults]
    rows = [Offer(row.branch, row.service, row.duration_minutes, row.price_from)
        for row in BranchService.objects.filter(branch__in=explicit, is_active=True,
            service__is_active=True, service__is_archived=False).select_related("branch", "service")]
    for branch in branches:
        if branch.uses_business_defaults:
            rows.extend(Offer(branch, service, service.duration_minutes, service.price_from)
                for service in Service.objects.filter(business=branch.business, is_active=True, is_archived=False).order_by("name", "pk"))
    return rows


def booking_assignments(branches):
    branches = [branch for branch in branches if branch.is_active and branch.archived_at is None]
    explicit = [branch for branch in branches if not branch.uses_business_defaults]
    rows = [Assignment(row.branch, row.resource, [service.pk for service in row.services.all()])
        for row in SpecialistBranch.objects.filter(branch__in=explicit, is_active=True,
            resource__is_active=True, resource__retired_at__isnull=True, resource__resource_type="staff")
            .select_related("branch", "resource").prefetch_related("services")]
    for branch in branches:
        if branch.uses_business_defaults:
            service_ids = list(Service.objects.filter(business=branch.business, is_active=True, is_archived=False).values_list("pk", flat=True))
            rows.extend(Assignment(branch, resource, service_ids) for resource in Resource.objects.filter(
                business=branch.business, is_active=True, retired_at__isnull=True, resource_type="staff").order_by("name", "pk"))
    return rows


def automatic_days(branch, resources):
    hours = {(row.resource_id, row.weekday): row for row in WorkingHours.objects.filter(business=branch.business)}
    exceptions = {(row.resource_id, row.date): row for row in ScheduleException.objects.filter(business=branch.business)}
    dates = sorted({date for _, date in exceptions})
    result = []
    for weekday, date in [(day, None) for day in range(7)] + [(day.weekday(), day) for day in dates]:
        common = hours.get((None, weekday))
        opening = _intervals(common) if common else []
        for resource in resources:
            row = exceptions.get((resource.pk, date)) if date else None
            row = row or hours.get((resource.pk, weekday), common)
            intervals = _intervals(row) if row else []
            opening.extend(intervals)
            result.append({"id": len(result) + 1, "branch": branch.pk, "resource": resource.pk,
                "weekday": None if date else weekday, "date": str(date) if date else None, "intervals": intervals})
        result.append({"id": len(result) + 1, "branch": branch.pk, "resource": None,
            "weekday": None if date else weekday, "date": str(date) if date else None, "intervals": _union(opening)})
    return result


def automatic_catalog(branch):
    from django.db.models import Q
    offers, assignments = booking_offers([branch]), booking_assignments([branch])
    return {
        "offers": [{"id": row.service_id, "branch": branch.pk, "service": row.service_id,
            "service_name": row.service.name, "duration_minutes": row.duration_minutes,
            "price_from": str(row.price_from) if row.price_from is not None else None, "is_active": True} for row in offers],
        "assignments": [{"id": row.resource_id, "branch": branch.pk, "resource": row.resource_id,
            "resource_name": row.resource.name, "service_ids": row.service_ids, "is_active": True} for row in assignments],
        "days": automatic_days(branch, [row.resource for row in assignments]) if assignments else [],
        "absences": list(SpecialistAbsence.objects.filter(business=branch.business,
            resource_id__in=[row.resource_id for row in assignments]).filter(Q(branch=branch) | Q(branch__isnull=True))
            .values("resource_id", "starts_on", "ends_on")),
    }
