"""Versioned plan commands. Undated steps have no booking side effects."""
import json
from django.core.serializers.json import DjangoJSONEncoder
from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.activities.services import create_activity_event
from apps.businesses.access import Actions
from apps.businesses.models import Business
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import CRMCommandResult, run_idempotent_crm_command
from apps.core.models import AuditLog
from apps.scheduling.models import VisitPlan, VisitPlanStep, Resource
from apps.scheduling.plan_access import assert_plan_change, assert_plan_context, assert_step_access
from apps.scheduling.record_commands import create_record, validate_responsible, UNSPECIFIED_PRICE


def _effect(plan, actor, command, *, reason="", details=None):
    metadata = {"command": command, "revision": plan.revision, "reason": reason, **(details or {})}
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=plan,
                          metadata=json.loads(json.dumps(metadata, cls=DjangoJSONEncoder)))
    create_activity_event(business=plan.business, client=plan.client, actor=actor,
                          instance=plan, event_type="visit_plan_changed", category="appointment",
                          text="Visit plan updated", metadata={"command": command, "revision": plan.revision})


def _validate_step(plan, actor, data, *, action=Actions.CREATE):
    if set(data) - {"service", "resource", "branch", "responsible_user"}:
        raise ValidationError({"steps": "Unsupported step fields."})
    service = data.get("service")
    resource, branch = data.get("resource"), data.get("branch")
    if service is None:
        raise ValidationError({"service": "Select a service."})
    for obj in (service, resource, branch):
        if obj is not None:
            obj.refresh_from_db()
            if obj.business_id != plan.business_id:
                raise ValidationError({"steps": "All links must belong to this business."})
    if not service.is_active or service.is_archived:
        raise ValidationError({"service": "Select an active service."})
    if resource and (not resource.is_active or resource.retired_at or resource.resource_type != Resource.ResourceTypes.STAFF):
        raise ValidationError({"resource": "Select an active specialist."})
    if branch:
        from apps.branches.schedule import booking_terms
        booking_terms(plan.business, service, resource, branch)
    responsible = data.get("responsible_user")
    if responsible:
        responsible.refresh_from_db()
        validate_responsible(business=plan.business, actor=actor, user=responsible)
    step = VisitPlanStep(plan=plan, service=service, resource=resource, branch=branch, responsible_user=responsible)
    assert_step_access(plan, step, actor, action)
    return step


def _key(key):
    if not str(key or "").strip():
        raise ValidationError({"idempotency_key": "Idempotency-Key is required."})


@transaction.atomic
def create_plan(*, business, actor, client, steps, idempotency_key, responsible_user=None):
    _key(idempotency_key)
    business = Business.objects.select_for_update().get(pk=business.pk)
    client.refresh_from_db()
    if client.business_id != business.pk or client.is_archived:
        raise ValidationError({"client": "Select an active client of this business."})
    plan = VisitPlan(business=business, client=client, responsible_user=responsible_user or actor, created_by=actor)
    plan.responsible_user.refresh_from_db()
    assert_plan_context(plan, actor)
    validate_responsible(business=business, actor=actor, user=plan.responsible_user)
    if not isinstance(steps, list) or len(steps) > 100:
        raise ValidationError({"steps": "Provide up to 100 steps."})
    validated = [_validate_step(plan, actor, data) for data in steps]
    if not validated:
        assert_step_access(plan, None, actor, Actions.CREATE)

    def operation():
        plan.save()
        for index, step in enumerate(validated, 1):
            step.plan = plan
            step.position = index
            step.save()
        _effect(plan, actor, "create")
        return CRMCommandResult(data={}, status_code=201, resource=plan)

    result = run_idempotent_crm_command(business=business, actor=actor, action="visit_plan.create",
        idempotency_key=idempotency_key, payload={"client": client, "steps": steps, "responsible_user": responsible_user}, operation=operation)
    current = VisitPlan.objects.get(pk=result.resource_id if result.replayed else result.resource.pk)
    assert_plan_change(current, actor, Actions.CREATE)
    return current, result.replayed


@transaction.atomic
def change_plan(*, plan, actor, command, expected_revision, idempotency_key, data):
    _key(idempotency_key)
    business = Business.objects.select_for_update().get(pk=plan.business_id)
    plan = VisitPlan.objects.select_for_update(of=("self",)).select_related("business", "client").get(pk=plan.pk, business=business)
    assert_plan_change(plan, actor)
    if plan.client.is_archived:
        raise ValidationError({"client": "The client is archived."})

    def operation():
        if plan.revision != expected_revision:
            raise InvalidTransition("The plan changed. Refresh before submitting again.")
        if plan.is_archived and command != "restore":
            raise InvalidTransition("The plan is archived.")
        before = list(plan.steps.values("id", "service_id", "resource_id", "branch_id", "responsible_user_id", "removed_at", "appointment_id"))
        if command == "schedule":
            _schedule(plan, actor, data)
        elif command == "revise":
            _revise(plan, actor, data)
        elif command == "responsible":
            _responsible(plan, actor, data)
        elif command in {"archive", "restore"}:
            if not str(data.get("reason", "")).strip():
                raise ValidationError({"reason": "Provide a reason."})
            if command == "archive" and plan.steps.filter(appointment__status__in=["created", "confirmed", "rescheduled"], appointment__is_archived=False).exists():
                raise InvalidTransition("Resolve scheduled visits before archiving the plan.")
            plan.is_archived = command == "archive"
            plan.archived_at = timezone.now() if plan.is_archived else None
            plan.archived_by = actor if plan.is_archived else None
            plan.archive_reason = data["reason"] if plan.is_archived else ""
        else:
            raise ValidationError({"command": "Unsupported command."})
        plan.revision += 1
        plan.save()
        after = list(plan.steps.values("id", "service_id", "resource_id", "branch_id", "responsible_user_id", "removed_at", "appointment_id"))
        _effect(plan, actor, command, reason=data.get("reason", ""), details={"step_id": data.get("step_id"), "before": before, "after": after})
        return CRMCommandResult(data={}, resource=plan)

    result = run_idempotent_crm_command(business=business, actor=actor, action=f"visit_plan.{command}",
        idempotency_key=idempotency_key, payload={"plan": plan.pk, "revision": expected_revision, "data": data}, operation=operation)
    plan.refresh_from_db()
    return plan, result.replayed


def _schedule(plan, actor, data):
    if not {"step_id", "start_at", "expected_price", "expected_duration_minutes"}.issubset(data):
        raise ValidationError("Step, time and current booking terms are required.")
    step = plan.steps.select_for_update().filter(pk=data.get("step_id"), removed_at__isnull=True).first()
    if step is None:
        raise ValidationError({"step_id": "Select a current step of this plan."})
    if step.appointment_id:
        raise InvalidTransition("This step already has an appointment; its history cannot be replaced.")
    appointment = create_record(business=plan.business, actor=actor, client=plan.client,
        service=step.service, resource=data.get("resource") or step.resource,
        branch=data.get("branch") or step.branch, start_at=data["start_at"],
        notes=data.get("notes", ""),
        responsible_user=step.responsible_user or plan.responsible_user,
        expected_price=data.get("expected_price", UNSPECIFIED_PRICE),
        expected_duration_minutes=data.get("expected_duration_minutes"))
    step.appointment = appointment
    step.save(update_fields=["appointment", "updated_at"])


def _revise(plan, actor, data):
    if data.get("consent") is not True or not str(data.get("reason", "")).strip():
        raise ValidationError({"consent": "Confirm the changed composition and provide a reason."})
    changes, additions, removals = data.get("changes", []), data.get("add", []), data.get("remove", [])
    ids = [item.get("id") for item in changes] + removals
    if len(ids) != len(set(ids)):
        raise ValidationError({"steps": "Each step may be changed only once."})
    selected = {s.pk: s for s in plan.steps.select_for_update().filter(pk__in=ids)}
    if set(ids) != set(selected):
        raise ValidationError({"steps": "Unknown step ID."})
    if any(s.appointment_id or s.removed_at for s in selected.values()):
        raise InvalidTransition("Use appointment commands for scheduled steps; retained history cannot be replaced.")
    if plan.steps.filter(removed_at__isnull=True).count() - len(removals) + len(additions) > 100:
        raise ValidationError({"steps": "A plan supports up to 100 current steps."})
    for item in changes:
        step = selected[item["id"]]
        values = {name: getattr(step, name) for name in ("service", "branch", "resource", "responsible_user")}
        values.update({key: value for key, value in item.items() if key != "id"})
        candidate = _validate_step(plan, actor, values, action=Actions.UPDATE)
        for name in values:
            setattr(step, name, getattr(candidate, name))
        step.save()
    for step_id in removals:
        step = selected[step_id]
        step.removed_at = timezone.now()
        step.save(update_fields=["removed_at", "updated_at"])
    last = plan.steps.order_by("-position").first()
    position = last.position if last else 0
    for item in additions:
        step = _validate_step(plan, actor, item)
        position += 1
        step.position = position
        step.save()


def _responsible(plan, actor, data):
    user = data.get("responsible_user")
    if user is None:
        raise ValidationError({"responsible_user": "Select an active responsible member."})
    user.refresh_from_db()
    validate_responsible(business=plan.business, actor=actor, user=user)
    selected = data.get("step_ids", [])
    steps = list(plan.steps.filter(pk__in=selected))
    if len(steps) != len(set(selected)):
        raise ValidationError({"step_ids": "Unknown step ID."})
    for step in steps:
        if step.responsible_user_id or step.removed_at:
            raise ValidationError({"step_ids": "Explicit overrides and removed steps are retained."})
        if step.appointment_id:
            appointment = step.appointment
            if appointment.status in {"completed", "cancelled", "no_show"} or appointment.is_archived:
                raise InvalidTransition("Terminal visits retain their responsible member.")
            appointment.responsible_user = user
            appointment.save(update_fields=["responsible_user", "updated_at"])
            from apps.scheduling.services import schedule_appointment_followups
            schedule_appointment_followups(appointment)
    plan.responsible_user = user
