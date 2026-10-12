from datetime import datetime, time, timedelta

from django.db import transaction
from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business, BusinessMember
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog
from apps.scheduling.availability import business_zone
from apps.scheduling.models import Appointment, Resource
from .access import accessible_branches, assert_branch_access
from .models import Branch, SpecialistAbsence


def assert_staff_scope(actor, resource):
    assert_can(actor, resource.business, Resources.SETTINGS, Actions.UPDATE)
    assignments = resource.branch_assignments.filter(is_active=True)
    if assignments.exclude(branch__in=accessible_branches(actor, resource.business)).exists():
        raise PermissionDenied("This specialist works in branches outside your permitted scope.")


def future_appointments(resource, *, starts_on=None, ends_on=None, branch=None):
    query = Appointment.objects.filter(business=resource.business, resource=resource,
        is_archived=False, status__in=[Appointment.Statuses.CREATED, Appointment.Statuses.CONFIRMED], end_at__gt=timezone.now())
    zone = business_zone(resource.business)
    if starts_on:
        query = query.filter(end_at__gt=timezone.make_aware(datetime.combine(starts_on, time.min), zone))
    if ends_on:
        query = query.filter(start_at__lt=timezone.make_aware(datetime.combine(ends_on + timedelta(days=1), time.min), zone))
    if branch:
        query = query.filter(branch=branch)
    return query.order_by("start_at", "id")


def pending_work(resource):
    counts = {"appointments": future_appointments(resource).count(), "tasks": 0, "leads": 0, "deals": 0, "conversations": 0}
    if resource.linked_user_id:
        from apps.tasks.models import Task
        from apps.leads.models import Lead
        from apps.crm.models import Deal
        from apps.bots.models import BotConversation
        counts.update(
            tasks=Task.objects.filter(business=resource.business, assignee_id=resource.linked_user_id, is_archived=False, status__in=["open", "in_progress", "waiting"]).count(),
            leads=Lead.objects.filter(business=resource.business, responsible_user_id=resource.linked_user_id, is_archived=False).exclude(status__in=["closed", "lost"]).count(),
            deals=Deal.objects.filter(business=resource.business, owner_id=resource.linked_user_id, is_archived=False, status="open").count(),
            conversations=BotConversation.objects.filter(business=resource.business, assigned_to_id=resource.linked_user_id, is_archived=False, status="open").count(),
        )
    return counts


@transaction.atomic
def add_absence(*, resource, actor, starts_on, ends_on, branch=None, reason="unavailable"):
    Business.objects.select_for_update().get(pk=resource.business_id)
    resource = Resource.objects.select_for_update().get(pk=resource.pk)
    if branch:
        assert_can(actor, resource.business, Resources.SETTINGS, Actions.UPDATE)
        assert_branch_access(actor, resource.business, branch)
        if not resource.branch_assignments.filter(branch=branch, is_active=True).exists():
            raise ValidationError({"branch": "The specialist is not assigned to this branch."})
    else:
        assert_staff_scope(actor, resource)
    if resource.retired_at or resource.resource_type != "staff":
        raise ValidationError({"resource": "Select a current specialist."})
    if starts_on > ends_on or reason not in {"unavailable", "vacation", "sick"}:
        raise ValidationError({"ends_on": "Use an ordered absence period and valid reason."})
    absence, _ = SpecialistAbsence.objects.get_or_create(business=resource.business, resource=resource, branch=branch,
        starts_on=starts_on, ends_on=ends_on, reason=reason)
    write_actor_audit_log(actor=actor, business=resource.business, action=AuditLog.Actions.UPDATE, instance=resource,
        metadata={"kind": "specialist_absence", "absence_id": absence.pk, "starts_on": str(starts_on), "ends_on": str(ends_on), "branch_id": branch.pk if branch else None})
    return absence


@transaction.atomic
def remove_absence(*, resource, actor, absence_id):
    Business.objects.select_for_update().get(pk=resource.business_id)
    absence = SpecialistAbsence.objects.filter(resource=resource, business=resource.business, pk=absence_id).first()
    if absence is None:
        raise ValidationError({"absence": "Absence is not available."})
    if absence.branch_id:
        assert_can(actor, resource.business, Resources.SETTINGS, Actions.UPDATE)
        assert_branch_access(actor, resource.business, absence.branch)
    else:
        assert_staff_scope(actor, resource)
    write_actor_audit_log(actor=actor, business=resource.business, action=AuditLog.Actions.UPDATE, instance=resource,
        metadata={"kind": "specialist_absence_removed", "absence_id": absence.pk})
    absence.delete()


@transaction.atomic
def retire_specialist(*, resource, actor, disable_access=False):
    Business.objects.select_for_update().get(pk=resource.business_id)
    resource = Resource.objects.select_for_update().get(pk=resource.pk)
    assert_staff_scope(actor, resource)
    if resource.resource_type != "staff":
        raise ValidationError({"resource": "Only specialists use this action."})
    if resource.retired_at:
        return resource
    if any(pending_work(resource).values()):
        raise InvalidTransition("Review future appointments and assigned work before retirement.",
                                errors={"resource": "Pause new bookings, then reassign or close pending work."})
    if disable_access and resource.linked_user_id:
        assert_can(actor, resource.business, Resources.TEAM, Actions.MANAGE)
        if resource.linked_user_id == resource.business.owner_id:
            raise ValidationError({"disable_access": "The business owner's access cannot be disabled."})
        BusinessMember.objects.filter(business=resource.business, user_id=resource.linked_user_id).update(is_active=False)
    resource.is_active = False
    resource.retired_at = timezone.now()
    resource.save(update_fields=["is_active", "retired_at", "updated_at"])
    resource.branch_assignments.update(is_active=False)
    write_actor_audit_log(actor=actor, business=resource.business, action=AuditLog.Actions.UPDATE, instance=resource,
        metadata={"kind": "specialist_retired", "disable_business_access": disable_access})
    return resource


@transaction.atomic
def change_branch_state(*, branch, actor, state):
    Business.objects.select_for_update().get(pk=branch.business_id)
    branch = Branch.objects.select_for_update().get(pk=branch.pk)
    assert_can(actor, branch.business, Resources.SETTINGS, Actions.UPDATE)
    assert_branch_access(actor, branch.business, branch)
    if state not in {"active", "paused", "archived"}:
        raise ValidationError({"state": "Choose active, paused or archived."})
    if state == "archived" and branch.appointments.filter(is_archived=False, end_at__gt=timezone.now(), status__in=["created", "confirmed"]).exists():
        raise InvalidTransition("Review future appointments before archiving the branch.")
    branch.is_active = state == "active"
    branch.archived_at = timezone.now() if state == "archived" else None
    branch.save(update_fields=["is_active", "archived_at", "updated_at"])
    if state == "active":
        from .schedule import validate_specialist_schedule
        for assignment in branch.specialist_assignments.filter(is_active=True).select_related("resource"):
            validate_specialist_schedule(assignment.resource)
    write_actor_audit_log(actor=actor, business=branch.business, action=AuditLog.Actions.UPDATE, instance=branch,
        metadata={"kind": "branch_state", "state": state})
    return branch
