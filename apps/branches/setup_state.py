from django.db.models import BooleanField, Case, Exists, OuterRef, When

from apps.scheduling.models import Resource, WorkingHours
from apps.services.models import Service
from .models import BranchService, ScheduleDay, SpecialistBranch


def with_setup_state(queryset):
    return queryset.annotate(
        _setup_services=Case(When(uses_business_defaults=True, then=Exists(Service.objects.filter(
            business_id=OuterRef("business_id"), is_active=True, is_archived=False))),
            default=Exists(BranchService.objects.filter(branch_id=OuterRef("pk"), is_active=True,
                service__is_active=True, service__is_archived=False)), output_field=BooleanField()),
        _setup_staff=Case(When(uses_business_defaults=True, then=Exists(Resource.objects.filter(
            business_id=OuterRef("business_id"), resource_type="staff", is_active=True, retired_at__isnull=True))),
            default=Exists(SpecialistBranch.objects.filter(branch_id=OuterRef("pk"), is_active=True,
                resource__is_active=True, resource__retired_at__isnull=True)), output_field=BooleanField()),
        _setup_hours=Case(When(uses_business_defaults=True, then=Exists(WorkingHours.objects.filter(
            business_id=OuterRef("business_id"), resource__isnull=True, is_day_off=False))),
            default=Exists(ScheduleDay.objects.filter(branch_id=OuterRef("pk"), resource__isnull=True).exclude(intervals=[])),
            output_field=BooleanField()),
    )
