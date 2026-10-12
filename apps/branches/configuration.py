"""Atomic branch configuration through existing settings/team permissions."""
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.models import AuditLog
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.models import Resource
from apps.services.models import Service
from .access import assert_branch_access
from .models import Branch, BranchService, BranchTravelTime, ScheduleDay, SpecialistBranch
from .schedule import normalize_intervals, validate_specialist_schedule


def _lock_and_authorize(branch, actor):
    Business.objects.select_for_update().get(pk=branch.business_id)
    assert_can(actor, branch.business, Resources.SETTINGS, Actions.UPDATE)
    assert_branch_access(actor, branch.business, branch, active=True)


def _audit(actor, branch, instance, kind):
    write_actor_audit_log(actor=actor, business=branch.business, action=AuditLog.Actions.UPDATE,
                         instance=instance, metadata={"kind": kind, "branch_id": branch.pk})


def _staff(branch, resource_id):
    resource = Resource.objects.filter(business=branch.business, pk=resource_id, resource_type="staff", retired_at__isnull=True).first()
    if resource is None:
        raise ValidationError({"resource": "Select a current specialist of this business."})
    return resource


@transaction.atomic
def save_offer(*, branch, actor, service_id, duration_minutes, price_from, is_active=True):
    _lock_and_authorize(branch, actor)
    service = Service.objects.filter(business=branch.business, pk=service_id, is_archived=False).first()
    if service is None:
        raise ValidationError({"service": "Select a service of this business."})
    if duration_minutes < 1 or duration_minutes > 1440 or (price_from is not None and price_from < 0):
        raise ValidationError({"duration_minutes": "Use a positive duration and a non-negative price."})
    offer, _ = BranchService.objects.update_or_create(branch=branch, service=service, defaults={
        "business": branch.business, "duration_minutes": duration_minutes, "price_from": price_from, "is_active": is_active})
    _audit(actor, branch, offer, "branch_service")
    return offer


@transaction.atomic
def save_assignment(*, branch, actor, resource_id, service_ids, is_active=True):
    _lock_and_authorize(branch, actor)
    resource = _staff(branch, resource_id)
    service_ids = set(service_ids)
    services = Service.objects.filter(business=branch.business, pk__in=service_ids, is_archived=False,
                                      branch_offers__branch=branch, branch_offers__is_active=True).distinct()
    if services.count() != len(service_ids):
        raise ValidationError({"service_ids": "Select services offered by this branch."})
    from .staff_lifecycle import future_appointments
    affected = future_appointments(resource, branch=branch)
    if is_active:
        affected = affected.exclude(service_id__in=service_ids)
    if affected.exists():
        raise InvalidTransition("Reassign or cancel affected future visits before removing this assignment or service.")
    link, _ = SpecialistBranch.objects.update_or_create(branch=branch, resource=resource, defaults={
        "business": branch.business, "is_active": is_active})
    link.services.set(services)
    if is_active:
        validate_specialist_schedule(resource)
    _audit(actor, branch, link, "specialist_branch")
    return link


@transaction.atomic
def save_schedule_day(*, branch, actor, resource_id=None, weekday=None, date=None, intervals=None, remove=False):
    _lock_and_authorize(branch, actor)
    if (date is None) == (weekday is None) or (weekday is not None and weekday not in range(7)):
        raise ValidationError({"weekday": "Choose one weekday or one date."})
    resource = _staff(branch, resource_id) if resource_id is not None else None
    if resource and not SpecialistBranch.objects.filter(branch=branch, resource=resource, is_active=True).exists():
        raise ValidationError({"resource": "Assign this specialist to the branch first."})
    values = {"branch": branch, "resource": resource, "weekday": weekday, "date": date}
    if remove:
        if date is None:
            raise ValidationError({"date": "Only date overrides can be removed; use empty intervals for a day off."})
        ScheduleDay.objects.filter(**values).delete()
        row = None
    else:
        row, _ = ScheduleDay.objects.update_or_create(**values, defaults={"business": branch.business, "intervals": normalize_intervals(intervals)})
    if resource:
        validate_specialist_schedule(resource)
    _audit(actor, branch, row or branch, "branch_schedule")
    return row


@transaction.atomic
def save_travel_time(*, branch, actor, other_id, minutes):
    _lock_and_authorize(branch, actor)
    other = Branch.objects.filter(business=branch.business, pk=other_id).exclude(pk=branch.pk).first()
    if other is None:
        raise ValidationError({"other_branch": "Select another branch of this business."})
    assert_branch_access(actor, branch.business, other, active=True)
    if minutes < 0 or minutes > 1440:
        raise ValidationError({"minutes": "Travel time must be between 0 and 1440 minutes."})
    row, _ = BranchTravelTime.objects.update_or_create(business=branch.business,
        from_branch_id=min(branch.pk, other.pk), to_branch_id=max(branch.pk, other.pk), defaults={"minutes": minutes})
    # Do not silently make previously valid shifts impossible.
    for resource in Resource.objects.filter(branch_assignments__branch__in=[branch, other], branch_assignments__is_active=True).distinct():
        validate_specialist_schedule(resource)
    _audit(actor, branch, row, "branch_travel")
    return row
