"""Physical locations and exact resource requirements; existing reservations are snapshots."""
from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.scheduling.models import Resource
from apps.services.models import Service
from .access import assert_branch_access, assert_all_branch_access
from .models import Branch, ServiceResourceRequirement


def physical_resources(branch):
    location = Q(branch=branch)
    if branch.uses_business_defaults:
        location |= Q(branch__isnull=True)
    return Resource.objects.filter(location, business=branch.business).exclude(resource_type="staff")


def validate_resource_location(*, business, attributes, instance=None, actor=None):
    kind = attributes.get("resource_type", instance.resource_type if instance else "staff")
    branch = attributes.get("branch", instance.branch if instance else None)
    if kind == "staff":
        if branch is not None:
            raise ValidationError({"branch": "Use specialist assignments for staff locations."})
        return None
    if branch is None:
        locations = list(Branch.objects.filter(business=business, is_active=True, archived_at__isnull=True)[:2])
        if len(locations) == 1:
            branch = locations[0]
        elif locations:
            raise ValidationError({"branch": "Select a location for this resource."})
    if branch is not None:
        if branch.business_id != business.pk or not branch.is_active or branch.archived_at:
            raise ValidationError({"branch": "Select an active location of this business."})
        if actor is not None:
            assert_branch_access(actor, business, branch, active=True)
    elif actor is not None:
        assert_all_branch_access(actor, business)
    return branch


def validate_resource_change(resource, attributes, *, actor=None):
    if resource.branch_id and actor is not None:
        assert_branch_access(actor, resource.business, resource.branch)
    branch = validate_resource_location(business=resource.business, attributes=attributes, instance=resource, actor=actor)
    new_type = attributes.get("resource_type", resource.resource_type)
    moving = getattr(branch, "pk", None) != resource.branch_id
    changing_type = new_type != resource.resource_type
    deactivating = not attributes.get("is_active", resource.is_active)
    if changing_type and (resource.reservations.exists() or resource.service_requirements.exists()):
        raise InvalidTransition("A resource with requirements or reservation history cannot change type.")
    if moving and resource.service_requirements.exists():
        raise InvalidTransition("Remove this resource from service requirements before moving it.")
    if moving or deactivating:
        if resource.reservations.filter(appointment__end_at__gt=timezone.now()).exclude(
                appointment__status__in=["cancelled", "rescheduled"]).exists():
            raise InvalidTransition("Reschedule or cancel future reservations before moving or deactivating this resource.")
    return branch


@transaction.atomic
def save_resource_requirements(*, branch, actor, service_id, resource_ids):
    Business.objects.select_for_update().get(pk=branch.business_id)
    branch = Branch.objects.get(pk=branch.pk)
    assert_can(actor, branch.business, Resources.SETTINGS, Actions.UPDATE)
    assert_branch_access(actor, branch.business, branch, active=True)
    service = Service.objects.filter(pk=service_id, business=branch.business, is_active=True, is_archived=False).first()
    if service is None or (not branch.uses_business_defaults and not branch.service_offers.filter(service=service, is_active=True).exists()):
        raise ValidationError({"service": "Select a service available at this location."})
    ids = set(resource_ids)
    resources = list(physical_resources(branch).filter(pk__in=ids, is_active=True, retired_at__isnull=True))
    if len(resources) != len(ids):
        raise ValidationError({"resource_ids": "Select active rooms or equipment belonging to this location."})
    ServiceResourceRequirement.objects.filter(branch=branch, service=service).exclude(resource_id__in=ids).delete()
    for resource in resources:
        ServiceResourceRequirement.objects.get_or_create(branch=branch, service=service, resource=resource)
    write_actor_audit_log(actor=actor, business=branch.business, action=AuditLog.Actions.UPDATE, instance=service,
        metadata={"kind": "service_resource_requirements", "branch_id": branch.pk, "resource_ids": sorted(ids)})
    return sorted(ids)


def resource_configuration(branch):
    return {
        "physical_resources": list(physical_resources(branch).values("id", "name", "resource_type", "is_active", "branch")),
        "resource_requirements": list(branch.resource_requirements.values("service_id", "resource_id")),
    }


def physical_schedule_projection(branch):
    from apps.scheduling.resource_booking import ResourceCalendar

    resources = list(physical_resources(branch))
    if not resources:
        return []
    calendar = ResourceCalendar(branch.business, branch, resources)
    dates = {date for _, date in calendar.exceptions} | {date for _, _, date in calendar.days if date is not None}
    result = []
    for resource in resources:
        for weekday, date in [(day, None) for day in range(7)] + [(None, day) for day in sorted(dates)]:
            if (resource.pk, weekday, date) in calendar.days:
                continue
            result.append({"id": -(len(result) + 1), "branch": branch.pk, "resource": resource.pk,
                "weekday": weekday, "date": str(date) if date else None,
                "intervals": calendar.intervals(resource, date.weekday() if date else weekday, date)})
    return result
