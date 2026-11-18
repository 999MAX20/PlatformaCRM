"""Agreed-price exclusions inside the Business/plan command transaction."""
from decimal import Decimal

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import canonical_request_hash
from apps.core.models import AuditLog
from .models import PlanTerms
from .plan_balances import ZERO, composition, current_terms, plan_money_projection, refused_advance
from .plan_corrections import assert_owner_money


def _selection(plan, command, data):
    if plan.terminated_at or plan.is_archived or plan.client.is_archived:
        raise InvalidTransition("Select an active plan and client.")
    steps = list(plan.steps.filter(removed_at__isnull=True).select_related("appointment"))
    if command == "refuse-service":
        steps = [step for step in steps if step.pk == data.get("step_id")]
        if not steps or (steps[0].appointment_id and steps[0].appointment.status == "completed"):
            raise InvalidTransition("Select an unrendered service of this plan.")
    elif command == "terminate":
        steps = [step for step in steps if not step.appointment_id or step.appointment.status != "completed"]
    else:
        raise ValidationError({"command": "Unsupported plan closure."})
    terms = current_terms(plan)
    if terms and terms.composition != composition(plan):
        raise InvalidTransition("Accept current prices before excluding services.")
    # Rendered services without agreed terms cannot acquire an invented zero price.
    if not terms and plan.steps.filter(removed_at__isnull=True, appointment__status="completed").exists():
        raise InvalidTransition("Resolve the rendered service prices before closing the plan.")
    return steps, terms


def preview_termination(plan, actor, command, data):
    assert_owner_money(plan, actor)
    steps, terms = _selection(plan, command, data)
    selected = {step.pk for step in steps}
    before = plan_money_projection(plan, actor)
    total = terms.total if terms else ZERO
    removed = sum((Decimal(line["amount"]) for line in terms.lines if line["step"] in selected), ZERO) if terms else ZERO
    after = total - removed
    result = {"total_before": str(total), "total_after": str(after),
        "allocated_before": before["allocated"], "allocated_after": before["allocated"],
        "remaining_before": before["remaining"],
        "remaining_after": str(max(ZERO, after - Decimal(before["allocated"]) - (ZERO if command == "terminate" else Decimal(before["unallocated"]) - Decimal(before["retained"]) - refused_advance(plan, selected)))),
        "unallocated": before["unallocated"], "retained": before["retained"],
        "removed_price": str(removed), "currency": terms.currency if terms else plan.business.currency,
        "steps": [{"id": step.pk, "service_name": step.service.name,
            "appointment": step.appointment_id, "status": step.appointment.status if step.appointment_id else "unscheduled",
            "start_at": step.appointment.start_at.isoformat() if step.appointment_id else None} for step in steps]}
    result["preview_hash"] = canonical_request_hash({"plan": plan.pk, "revision": plan.revision,
        "command": command, "result": result, "balance": before})
    return result


def close_services(plan, actor, command, data):
    if data.get("consent") is not True or not str(data.get("reason", "")).strip():
        raise ValidationError({"consent": "Confirm the client's decision and provide a reason."})
    preview = preview_termination(plan, actor, command, data)
    if data.get("preview_hash") != preview["preview_hash"]:
        raise InvalidTransition("The plan or balance changed. Review the decision again.")
    steps, terms = _selection(plan, command, data)
    selected = {step.pk for step in steps}
    reason = data["reason"].strip()
    for step in steps:
        if step.appointment_id:
            _cancel_for_refusal(step.appointment, actor, plan, reason)
        step.removed_at = timezone.now()
        step.refusal_reason = reason
        step.save(update_fields=["removed_at", "refusal_reason", "updated_at"])
    if terms:
        PlanTerms.objects.create(plan=plan, revision=plan.revision + 1, previous=terms,
            mode=terms.mode, currency=terms.currency, total=preview["total_after"],
            lines=[line for line in terms.lines if line["step"] not in selected],
            composition=composition(plan), reason=reason, consent=True, actor=actor)
    if command == "terminate":
        plan.terminated_at, plan.terminated_by, plan.termination_reason = timezone.now(), actor, reason


def _cancel_for_refusal(appointment, actor, plan, reason):
    from apps.scheduling.services import cancel_appointment_followups, create_appointment_activity
    previous = appointment.status
    if previous not in {"cancelled", "no_show"}:
        appointment.status = "cancelled"
        appointment.save(update_fields=["status", "updated_at"])
        create_appointment_activity(appointment=appointment, actor=actor,
            event_type="appointment_service_refused", text="Service refused",
            previous_status=previous, metadata={"reason": reason, "plan_id": plan.pk})
        write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=appointment,
            metadata={"kind": "lifecycle", "event_type": "appointment_service_refused",
                "from": previous, "to": "cancelled", "reason": reason, "plan_id": plan.pk})
    cancel_appointment_followups(appointment)
