from django.db.models import Q

from apps.businesses.access import Actions, Resources, can, scope_queryset
from apps.core.archive import can_hard_delete
from apps.scheduling.models import Resource, WorkingHours, ScheduleException
from apps.services.models import Service
from .access import accessible_branches
from .config_serializers import AssignmentSerializer, OfferSerializer
from .management_commands import ROOM_TYPES
from .models import Branch, BranchService, ScheduleDay, ServiceResourceRequirement, SpecialistBranch
from .serializers import BranchSerializer


def management_catalog(*, business, request):
    from .setup_state import with_setup_state
    actor = request.user
    branches = with_setup_state(accessible_branches(actor, business)).select_related("business")
    branch_ids = set(branches.values_list("pk", flat=True))
    full_scope = not Branch.objects.filter(business=business).exclude(pk__in=branch_ids).exists()
    may_update = can(actor, business, Resources.SETTINGS, Actions.UPDATE).allowed
    services = scope_queryset(Service.objects.filter(business=business), actor, business, Resources.SETTINGS)
    resources = scope_queryset(Resource.objects.filter(business=business), actor, business, Resources.SETTINGS)
    if not full_scope:
        services = services.filter(branch_offers__branch_id__in=branch_ids).distinct()
        resources = resources.filter(Q(branch_id__in=branch_ids) | Q(branch_assignments__branch_id__in=branch_ids)).distinct()
    services = list(services.order_by("name", "pk"))
    resources = list(resources.order_by("name", "pk"))
    assignments = list(SpecialistBranch.objects.filter(branch_id__in=branch_ids).select_related("resource").prefetch_related("services"))
    editable_staff_ids = {item.pk for item in resources if item.resource_type == "staff"}
    editable_staff_ids -= set(SpecialistBranch.objects.filter(resource_id__in=editable_staff_ids).exclude(branch_id__in=branch_ids).values_list("resource_id", flat=True))
    scheduled_ids = set(ScheduleDay.objects.filter(resource_id__in=[row.pk for row in resources]).values_list("resource_id", flat=True))
    scheduled_ids |= set(WorkingHours.objects.filter(resource_id__in=[row.pk for row in resources]).values_list("resource_id", flat=True))
    scheduled_ids |= set(ScheduleException.objects.filter(resource_id__in=[row.pk for row in resources]).values_list("resource_id", flat=True))
    working_pairs = set(ScheduleDay.objects.filter(branch_id__in=branch_ids).exclude(intervals=[]).values_list("branch_id", "resource_id"))
    return {
        "scheduled_pairs": [{"branch": branch, "resource": resource} for branch, resource in sorted(working_pairs, key=lambda pair: (pair[0], pair[1] or 0))],
        "branches": BranchSerializer(branches, many=True, context={"request": request}).data,
        "services": [{"id": row.pk, "name": row.name, "description": row.description,
            "duration_minutes": row.duration_minutes, "price_from": str(row.price_from) if row.price_from is not None else None,
            "is_active": row.is_active, "is_archived": row.is_archived, "requires_room": row.requires_room,
            "can_manage": may_update and full_scope and can(actor, business, Resources.SETTINGS, Actions.UPDATE, obj=row).allowed} for row in services],
        "resources": [{"id": row.pk, "name": row.name, "resource_type": row.resource_type, "branch": row.branch_id,
            "profession": row.profession, "public_description": row.public_description, "contact_phone": row.contact_phone,
            "is_active": row.is_active, "retired_at": row.retired_at, "archived_at": row.archived_at,
            "inherit_schedule": row.pk not in scheduled_ids,
            "can_manage": may_update and (row.pk in editable_staff_ids if row.resource_type == "staff" else row.branch_id in branch_ids)
                and can(actor, business, Resources.SETTINGS, Actions.UPDATE, obj=row).allowed}
            for row in resources if row.resource_type == "staff" or row.resource_type in ROOM_TYPES],
        "offers": OfferSerializer(BranchService.objects.filter(branch_id__in=branch_ids).select_related("service"), many=True).data,
        "assignments": AssignmentSerializer(assignments, many=True).data,
        "room_options": list(ServiceResourceRequirement.objects.filter(branch_id__in=branch_ids,
            resource__resource_type__in=ROOM_TYPES).values("branch_id", "service_id", "resource_id", "is_alternative")),
        "can_create_service": may_update and full_scope,
        "can_create_resource": may_update and bool(branch_ids),
        "can_delete": can_hard_delete(actor, business, Resources.SETTINGS),
        "timezone": business.timezone,
    }
