from django.utils import timezone

from apps.core.domain_errors import InvalidTransition
from apps.scheduling.availability import business_zone
from apps.scheduling.models import Appointment
from apps.scheduling.resource_booking import ResourceCalendar
from .models import SpecialistAbsence
from .schedule import _windows


def assert_future_hours(branch, resource=None, *, date=None, weekday=None):
    visits = Appointment.objects.filter(business=branch.business, branch=branch,
        status__in=["created", "confirmed"], end_at__gt=timezone.now()).select_related("resource").prefetch_related("reserved_resources__resource")
    zone = business_zone(branch.business)
    for visit in visits:
        local_date = visit.start_at.astimezone(zone).date()
        if date is not None and date != local_date or weekday is not None and weekday != local_date.weekday():
            continue
        reserved = [row.resource for row in visit.reserved_resources.all()]
        if resource is not None and resource.pk != visit.resource_id and resource.pk not in {row.pk for row in reserved}:
            continue
        if visit.resource and not any(visit.start_at >= lower and visit.end_at <= upper for lower, upper in _windows(branch, visit.resource, local_date)):
            raise InvalidTransition("The new hours conflict with future appointments. Reschedule them first.")
        calendar = ResourceCalendar(branch.business, branch, reserved, date=local_date)
        for room in reserved:
            absent = SpecialistAbsence.objects.filter(resource=room, starts_on__lte=local_date, ends_on__gte=local_date).exists()
            if absent or not any(visit.start_at >= lower and visit.end_at <= upper for lower, upper in calendar.windows(room, local_date)):
                raise InvalidTransition("The new room hours conflict with future appointments. Reschedule them first.")
