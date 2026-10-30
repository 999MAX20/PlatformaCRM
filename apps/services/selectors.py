"""Complete service workspace read projections over current permitted rows."""
from math import floor

from django.db.models import Avg, Count, IntegerField, OuterRef, Q, Subquery, Value
from django.db.models.functions import Coalesce

from apps.businesses.access import Resources
from apps.core.crm_read_scope import readable_queryset
from apps.core.permissions import accessible_businesses, platform_admin_has_global_access
from apps.scheduling.models import Appointment


def with_appointment_counts(queryset, *, actor):
    appointments = Appointment.objects.filter(is_archived=False)
    if not platform_admin_has_global_access(actor):
        permitted = appointments.none().distinct()
        for business in accessible_businesses(actor):
            permitted |= readable_queryset(
                appointments, actor=actor, business=business, resource=Resources.APPOINTMENTS,
            ).distinct()
        appointments = permitted
    # Correlate both keys even for inconsistent legacy links. Never count a foreign visit.
    counts = appointments.filter(service_id=OuterRef('pk'), business_id=OuterRef('business_id')).order_by().values('service_id').annotate(
        total=Count('pk', distinct=True),
    ).values('total')
    return queryset.annotate(appointment_count=Coalesce(Subquery(counts, output_field=IntegerField()), Value(0)))


def service_summary(queryset):
    """Same filters and permission scope as the list, before pagination."""
    active = Q(is_active=True, is_archived=False)
    result = queryset.aggregate(
        active=Count('pk', filter=active, distinct=True),
        average_duration_minutes=Avg('duration_minutes', filter=active),
        used_in_bookings=Count('pk', filter=Q(appointment_count__gt=0), distinct=True),
    )
    average = result['average_duration_minutes']
    result['average_duration_minutes'] = floor(average + 0.5) if average is not None else None
    return result
