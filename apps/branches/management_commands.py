"""One transaction for each Management form, including its cross-catalog links."""
from django.db import transaction
from rest_framework.exceptions import NotFound, ValidationError

from apps.activities.services import write_activity_event
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.capabilities import assert_resource_enabled
from apps.businesses.models import Business
from apps.core.audit import write_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.scheduling.models import Resource, WorkingHours, ScheduleException
from apps.scheduling.resource_services import create_resource, update_resource
from apps.services.models import Service
from .access import assert_all_branch_access, assert_branch_access
from .configuration import save_assignment, save_offer
from .models import Branch, ScheduleDay, ServiceResourceRequirement, SpecialistBranch
from .services import create_branch, update_branch

ROOM_TYPES = {"room", "hall", "box"}


def authorize_write(business, actor, instance=None):
    Business.objects.select_for_update().get(pk=business.pk)
    if instance is not None and instance.pk:
        instance.refresh_from_db()
    assert_resource_enabled(business, Resources.SETTINGS)
    assert_can(actor, business, Resources.SETTINGS, Actions.UPDATE, obj=instance)


def entity(model, business, identifier, **filters):
    item = model.objects.filter(business=business, pk=identifier, **filters).first()
    if item is None:
        raise NotFound("Object is not available.")
    return item


def locations(business, actor, values):
    ids = [value["branch"] for value in values]
    if len(ids) != len(set(ids)):
        raise ValidationError({"locations": "Choose each branch once."})
    result = {}
    for identifier in ids:
        branch = entity(Branch, business, identifier)
        assert_branch_access(actor, business, branch)
        if branch.archived_at or branch.uses_business_defaults:
            raise ValidationError({"locations": "Select a current configured branch."})
        result[identifier] = branch
    return result


def record_change(request, item, created):
    action = AuditLog.Actions.CREATE if created else AuditLog.Actions.UPDATE
    write_audit_log(request, action, item, metadata={"kind": "management_configuration"})
    write_activity_event(request, f"{item.__class__.__name__.lower()}.{'created' if created else 'updated'}", item)


def save_room_options(branch, service, ids):
    ids = set(ids)
    rooms = Resource.objects.filter(business=branch.business, branch=branch, pk__in=ids,
        resource_type__in=ROOM_TYPES, is_active=True, retired_at__isnull=True, archived_at__isnull=True)
    if rooms.count() != len(ids):
        raise ValidationError({"room_ids": "Select active rooms in this branch."})
    # Only this form changes legacy room requirements into an alternative pool.
    # Equipment requirements and already-booked reservation snapshots stay intact.
    ServiceResourceRequirement.objects.filter(branch=branch, service=service, resource__resource_type__in=ROOM_TYPES).exclude(resource_id__in=ids).delete()
    for room in rooms:
        ServiceResourceRequirement.objects.update_or_create(branch=branch, service=service, resource=room,
            defaults={"is_alternative": True})


@transaction.atomic
def save_service(*, business, request, values):
    values = dict(values)
    identifier = values.pop("id", None)
    values.pop("business", None)
    location_values = values.pop("locations")
    service = entity(Service, business, identifier) if identifier else None
    authorize_write(business, request.user, service or Service(business=business))
    assert_all_branch_access(request.user, business)
    if service and service.is_archived:
        raise InvalidTransition("Restore the service before editing it.")
    branches = locations(business, request.user, location_values)
    if service and values.get("is_active") is False:
        from .management_lifecycle import assert_no_future
        assert_no_future(service)
    if service is None:
        service = Service.objects.create(business=business, **values)
    else:
        for key, value in values.items():
            setattr(service, key, value)
        service.save()
    from .management_lifecycle import assert_no_future
    removed = service.branch_offers.filter(is_active=True).exclude(branch_id__in=branches)
    for offer in removed:
        assert_no_future(service, branch=offer.branch)
    removed.update(is_active=False)
    for item in location_values:
        branch = branches[item["branch"]]
        save_offer(branch=branch, actor=request.user, service_id=service.pk,
            duration_minutes=service.duration_minutes, price_from=service.price_from)
        people = set(item["specialist_ids"])
        selected = Resource.objects.filter(business=business, pk__in=people, resource_type="staff", retired_at__isnull=True, archived_at__isnull=True)
        if selected.count() != len(people):
            raise ValidationError({"specialist_ids": "Select current specialists of this business."})
        links = {link.resource_id: link for link in SpecialistBranch.objects.filter(branch=branch).prefetch_related("services")}
        affected = people | {pk for pk, link in links.items() if service.pk in {row.pk for row in link.services.all()}}
        for resource_id in affected:
            old = links.get(resource_id)
            services = {row.pk for row in old.services.all()} if old else set()
            services.discard(service.pk)
            if resource_id in people:
                services.add(service.pk)
            save_assignment(branch=branch, actor=request.user, resource_id=resource_id, service_ids=sorted(services),
                is_active=True if resource_id in people else old.is_active)
        if service.requires_room:
            save_room_options(branch, service, item["room_ids"])
        else:
            ServiceResourceRequirement.objects.filter(branch=branch, service=service, is_alternative=True).delete()
    record_change(request, service, identifier is None)
    return service


@transaction.atomic
def save_specialist(*, business, request, values):
    values = dict(values)
    identifier = values.pop("id", None)
    values.pop("business", None)
    location_values = values.pop("locations")
    resource = entity(Resource, business, identifier, resource_type="staff") if identifier else None
    authorize_write(business, request.user, resource or Resource(business=business))
    if resource:
        from .staff_lifecycle import assert_staff_scope
        assert_staff_scope(request.user, resource)
        if resource.retired_at:
            raise InvalidTransition("Retired specialists remain in history.")
    branches = locations(business, request.user, location_values)
    if resource is None:
        resource = create_resource(business=business, actor=request.user, resource_type="staff", **values)
        # New explicit assignments require their own hours; no inherited staff shift.
        WorkingHours.objects.filter(resource=resource).delete()
    else:
        resource = update_resource(resource=resource, actor=request.user, attributes=values)
    for link in resource.branch_assignments.filter(is_active=True).exclude(branch_id__in=branches):
        save_assignment(branch=link.branch, actor=request.user, resource_id=resource.pk, service_ids=[], is_active=False)
    for item in location_values:
        save_assignment(branch=branches[item["branch"]], actor=request.user, resource_id=resource.pk,
            service_ids=item["service_ids"], is_active=True)
    record_change(request, resource, identifier is None)
    return resource


@transaction.atomic
def save_room(*, business, request, values):
    values = dict(values)
    identifier = values.pop("id", None)
    values.pop("business", None)
    service_ids = set(values.pop("service_ids"))
    inherit = values.pop("inherit_schedule")
    branch = entity(Branch, business, values.pop("branch"))
    resource = entity(Resource, business, identifier, resource_type__in=ROOM_TYPES) if identifier else None
    authorize_write(business, request.user, resource or Resource(business=business, branch=branch, resource_type="room"))
    assert_branch_access(request.user, business, branch)
    if branch.archived_at:
        raise ValidationError({"branch": "Restore this branch before adding a room."})
    services = Service.objects.filter(business=business, pk__in=service_ids, is_archived=False,
        branch_offers__branch=branch, branch_offers__is_active=True).distinct()
    if services.count() != len(service_ids):
        raise ValidationError({"service_ids": "Select services offered in this branch."})
    resource = (update_resource(resource=resource, actor=request.user, attributes={**values, "branch": branch}) if resource else
        create_resource(business=business, actor=request.user, resource_type="room", branch=branch, **values))
    if not inherit and not (ScheduleDay.objects.filter(resource=resource).exists() or WorkingHours.objects.filter(resource=resource).exists() or ScheduleException.objects.filter(resource=resource).exists()):
        ScheduleDay.objects.bulk_create([ScheduleDay(business=business, branch=branch, resource=resource, weekday=day, intervals=[]) for day in range(7)])
    if inherit:
        ScheduleDay.objects.filter(resource=resource).delete()
        WorkingHours.objects.filter(resource=resource).delete()
        ScheduleException.objects.filter(resource=resource).delete()
        from .management_schedule import assert_future_hours
        assert_future_hours(branch, resource)
    existing = ServiceResourceRequirement.objects.filter(resource=resource)
    existing.exclude(service_id__in=service_ids).delete()
    for service in services:
        requirement, created = ServiceResourceRequirement.objects.get_or_create(branch=branch, service=service, resource=resource,
            defaults={"is_alternative": True})
        if requirement.is_alternative:
            service.requires_room = True
            service.save(update_fields=["requires_room", "updated_at"])
    record_change(request, resource, identifier is None)
    return resource


@transaction.atomic
def save_branch(*, business, request, values):
    values = dict(values)
    identifier = values.pop("id", None)
    values.pop("business", None)
    service_ids = set(values.pop("service_ids"))
    specialist_ids = set(values.pop("specialist_ids"))
    branch = entity(Branch, business, identifier) if identifier else None
    authorize_write(business, request.user, branch)
    active = values.pop("is_active", None)
    if branch and active is False:
        from .management_lifecycle import assert_no_future
        assert_no_future(branch)
    branch = update_branch(branch=branch, actor=request.user, changes=values) if branch else create_branch(business=business, actor=request.user, **values)
    assert_branch_access(request.user, business, branch)
    if active is not None and active != branch.is_active:
        from .staff_lifecycle import change_branch_state
        branch = change_branch_state(branch=branch, actor=request.user, state="active" if active else "paused")
    services = Service.objects.filter(business=business, pk__in=service_ids, is_archived=False)
    specialists = Resource.objects.filter(business=business, pk__in=specialist_ids, resource_type="staff", retired_at__isnull=True, archived_at__isnull=True)
    if services.count() != len(service_ids) or specialists.count() != len(specialist_ids):
        raise ValidationError({"service_ids": "Choose current services and specialists from this business."})
    from .management_lifecycle import assert_no_future
    for offer in branch.service_offers.filter(is_active=True).exclude(service_id__in=service_ids):
        assert_no_future(offer.service, branch=branch)
        offer.is_active = False
        offer.save(update_fields=["is_active", "updated_at"])
    for service in services:
        current = branch.service_offers.filter(service=service).first()
        save_offer(branch=branch, actor=request.user, service_id=service.pk,
            duration_minutes=current.duration_minutes if current else service.duration_minutes,
            price_from=current.price_from if current else service.price_from)
    for link in branch.specialist_assignments.all().prefetch_related("services"):
        if link.resource_id not in specialist_ids:
            save_assignment(branch=branch, actor=request.user, resource_id=link.resource_id, service_ids=[], is_active=False)
        else:
            save_assignment(branch=branch, actor=request.user, resource_id=link.resource_id,
                service_ids=[row.pk for row in link.services.all() if row.pk in service_ids], is_active=True)
            specialist_ids.discard(link.resource_id)
    for resource_id in specialist_ids:
        save_assignment(branch=branch, actor=request.user, resource_id=resource_id, service_ids=[], is_active=True)
    record_change(request, branch, identifier is None)
    return branch
