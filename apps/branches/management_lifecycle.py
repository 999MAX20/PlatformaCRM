from django.db import transaction
from django.db.models import Q
from django.db.models.deletion import ProtectedError
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.activities.services import write_activity_event
from apps.core.archive import can_hard_delete
from apps.core.audit import write_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from .access import assert_all_branch_access, assert_branch_access
from .management_commands import ROOM_TYPES, authorize_write, entity
from .models import Branch
from .staff_lifecycle import assert_staff_scope, change_branch_state


def related_visits(item):
    query = Appointment.objects.filter(business=item.business)
    if isinstance(item, Service):
        return query.filter(service=item)
    if isinstance(item, Branch):
        return query.filter(branch=item)
    return query.filter(Q(resource=item) | Q(reserved_resources__resource=item)).distinct()


def assert_no_future(item, *, branch=None):
    query = related_visits(item).filter(status__in=["created", "confirmed"], end_at__gt=timezone.now())
    if branch is not None:
        query = query.filter(branch=branch)
    if query.exists():
        raise InvalidTransition("Reschedule or cancel future appointments before changing availability.",
            errors={"future_appointments": query.count()})


@transaction.atomic
def change_state(*, business, request, kind, identifier, operation):
    model = {"services": Service, "staff": Resource, "rooms": Resource, "branches": Branch}[kind]
    filters = {"resource_type": "staff"} if kind == "staff" else {"resource_type__in": ROOM_TYPES} if kind == "rooms" else {}
    item = entity(model, business, identifier, **filters)
    authorize_write(business, request.user, item)
    if kind == "services":
        assert_all_branch_access(request.user, business)
    elif kind == "staff":
        assert_staff_scope(request.user, item)
    else:
        assert_branch_access(request.user, business, item if kind == "branches" else item.branch)
    if isinstance(item, Resource) and item.retired_at:
        raise InvalidTransition("Retirement is a separate historical state; it cannot be restored here.")
    if operation in {"deactivate", "archive", "delete"}:
        assert_no_future(item)
    if operation == "delete":
        if not can_hard_delete(request.user, business, "settings"):
            raise PermissionDenied("Only an administrator can permanently delete an unused object.")
        if related_visits(item).exists():
            raise InvalidTransition("This object has appointment history. Archive it instead.")
        if kind == "branches":
            if Branch.objects.filter(business=business).count() <= 1:
                raise InvalidTransition("Keep at least one branch.")
            if item.physical_resources.exists() or item.service_offers.filter(is_active=True).exists() or item.specialist_assignments.filter(is_active=True).exists():
                raise InvalidTransition("Remove this branch's services, specialists and rooms first.")
        write_audit_log(request, AuditLog.Actions.DELETE, item, metadata={"kind": "management_unused_delete"})
        write_activity_event(request, f"{item.__class__.__name__.lower()}.deleted", item)
        try:
            if kind == "services":
                item.resource_requirements.all().delete()
                item.branch_offers.all().delete()
                item.specialist_assignments.clear()
            elif kind in {"staff", "rooms"}:
                item.service_requirements.all().delete()
                item.branch_assignments.all().delete()
                item.branch_schedule_days.all().delete()
                item.absences.all().delete()
            else:
                item.resource_requirements.all().delete()
                item.service_offers.all().delete()
                item.specialist_assignments.all().delete()
                item.schedule_days.all().delete()
                item.travel_from.all().delete()
                item.travel_to.all().delete()
                item.absences.all().delete()
            item.delete()
        except ProtectedError:
            raise InvalidTransition("This object is used by other records. Archive it instead.") from None
        return
    if kind == "services":
        from apps.services.services import archive_service, restore_service, set_service_active
        if operation == "archive":
            archive_service(request=request, service=item)
        elif operation == "restore":
            restore_service(request=request, service=item)
        else:
            set_service_active(request=request, service=item, is_active=operation == "activate")
        return
    if kind == "branches":
        return change_branch_state(branch=item, actor=request.user,
            state={"archive": "archived", "restore": "paused", "deactivate": "paused", "activate": "active"}[operation])
    if item.archived_at and operation != "restore":
        raise ValidationError({"operation": "Restore the resource before changing its state."})
    if operation == "archive":
        item.archived_at, item.is_active = timezone.now(), False
    elif operation == "restore":
        item.archived_at, item.is_active = None, False
    else:
        item.is_active = operation == "activate"
    item.save(update_fields=["archived_at", "is_active", "updated_at"])
    write_audit_log(request, AuditLog.Actions.UPDATE, item, metadata={"kind": "management_lifecycle", "operation": operation})
    write_activity_event(request, f"resource.{operation}", item)
