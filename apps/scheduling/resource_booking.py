"""Shared physical-resource availability and appointment reservation snapshots."""
from datetime import datetime, timedelta

from django.db.models import Q
from django.utils import timezone

from apps.branches.models import ScheduleDay, ServiceResourceRequirement
from apps.core.domain_errors import ScheduleConflict
from .models import Appointment, AppointmentResource, Resource, ScheduleException, WorkingHours


def required_resources(business, service, branch, *, appointment=None):
    if appointment is not None and appointment.branch_id == getattr(branch, "pk", None) and appointment.service_id == service.pk:
        return [row.resource for row in appointment.reserved_resources.select_related("resource")]
    if branch is None:
        return []
    return [row.resource for row in ServiceResourceRequirement.objects.filter(
        branch=branch, service=service).select_related("resource").order_by("resource_id")]


def _intervals(row):
    return [] if row.is_day_off else [{"start": row.start_time.strftime("%H:%M"), "end": row.end_time.strftime("%H:%M")}]


class ResourceCalendar:
    def __init__(self, business, branch, resources, *, date=None):
        from .availability import business_zone

        self.zone = business_zone(business)
        self.explicit = branch is not None and not branch.uses_business_defaults
        ids = [resource.pk for resource in resources]
        scope = Q(resource_id__in=ids) | Q(resource__isnull=True)
        self.hours = {(row.resource_id, row.weekday): _intervals(row)
            for row in WorkingHours.objects.filter(scope, business=business)}
        exceptions = ScheduleException.objects.filter(business=business, resource_id__in=ids)
        if date is not None:
            exceptions = exceptions.filter(date=date)
        self.exceptions = {(row.resource_id, row.date): _intervals(row) for row in exceptions}
        self.days = {(row.resource_id, row.weekday, row.date): row.intervals
            for row in ScheduleDay.objects.filter(scope, branch=branch)} if self.explicit else {}

    def intervals(self, resource, weekday, date=None):
        missing = object()
        intervals = self.days.get((resource.pk, None, date), missing) if date else missing
        if intervals is missing:
            intervals = self.days.get((resource.pk, weekday, None), missing)
        if intervals is missing:
            intervals = self.exceptions.get((resource.pk, date), self.hours.get((resource.pk, weekday)))
            if intervals is None and not self.explicit:
                intervals = self.hours.get((None, weekday), [])
        if self.explicit:
            opening = self.days.get((None, None, date), self.days.get((None, weekday, None), [])) if date else self.days.get((None, weekday, None), [])
            intervals = opening if intervals is None else [
                {"start": max(left["start"], right["start"]), "end": min(left["end"], right["end"])}
                for left in opening for right in intervals
                if max(left["start"], right["start"]) < min(left["end"], right["end"])
            ]
        return intervals or []

    def windows(self, resource, date):
        return [(timezone.make_aware(datetime.combine(date, datetime.strptime(item["start"], "%H:%M").time()), self.zone),
                 timezone.make_aware(datetime.combine(date, datetime.strptime(item["end"], "%H:%M").time()), self.zone))
                for item in self.intervals(resource, date.weekday(), date)]


class ResourceAvailability:
    def __init__(self, business, branch, resources, start, end, *, exclude=None):
        from .availability import business_zone

        self.resources = resources
        self.valid = True
        self.windows = {}
        self.busy = []
        if not resources:
            return
        date = start.astimezone(business_zone(business)).date()
        for resource in resources:
            same_location = branch and (resource.branch_id == branch.pk or (branch.uses_business_defaults and resource.branch_id is None))
            if (resource.business_id != business.pk or resource.resource_type == Resource.ResourceTypes.STAFF
                    or not resource.is_active or resource.retired_at or not same_location):
                self.valid = False
                return
        calendar = ResourceCalendar(business, branch, resources, date=date)
        self.windows = {resource.pk: calendar.windows(resource, date) for resource in resources}
        ids = [resource.pk for resource in resources]
        busy = Appointment.objects.filter(business=business, start_at__lt=end, end_at__gt=start).exclude(
            status__in=[Appointment.Statuses.CANCELLED, Appointment.Statuses.RESCHEDULED])
        if exclude is not None:
            busy = busy.exclude(pk=exclude.pk)
        self.busy = list(busy.filter(Q(reserved_resources__resource_id__in=ids) | Q(resource_id__in=ids))
                         .values_list("start_at", "end_at").distinct())

    def permits(self, start, end):
        return self.valid and all(any(start >= lower and end <= upper for lower, upper in windows)
            for windows in self.windows.values()) and not any(start < upper and end > lower for lower, upper in self.busy)


def filter_resource_slots(business, service, branch, slots, duration, *, exclude_appointment=None):
    if not slots:
        return slots
    resources = required_resources(business, service, branch, appointment=exclude_appointment)
    if not resources:
        return slots
    delta = timedelta(minutes=duration)
    availability = ResourceAvailability(business, branch, resources, min(slots), max(slots) + delta, exclude=exclude_appointment)
    return [start for start in slots if availability.permits(start, start + delta)]


def validate_resource_availability(business, service, branch, start, end, *, exclude_appointment=None, preserve_snapshot=True):
    resources = required_resources(business, service, branch, appointment=exclude_appointment if preserve_snapshot else None)
    availability = ResourceAvailability(business, branch, resources, start, end, exclude=exclude_appointment)
    if not availability.permits(start, end):
        raise ScheduleConflict(errors={"start_at": "Required room or equipment is unavailable. Select another time or review the service resources."})
    return resources


def set_reserved_resources(appointment, resources):
    """Caller holds the Business scheduling lock and has validated this interval."""
    ids = [resource.pk for resource in resources]
    appointment.reserved_resources.exclude(resource_id__in=ids).delete()
    for resource in resources:
        AppointmentResource.objects.get_or_create(appointment=appointment, resource=resource,
            defaults={"resource_name": resource.name})


def reserve_appointment_resources(appointment):
    resources = validate_resource_availability(appointment.business, appointment.service, appointment.branch,
        appointment.start_at, appointment.end_at, exclude_appointment=appointment, preserve_snapshot=False)
    set_reserved_resources(appointment, resources)
