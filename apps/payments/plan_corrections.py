"""Owner-confirmed corrections, executed by the locked plan command boundary."""
from decimal import Decimal

from django.db.models import Q
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.access import Actions, Resources, assert_can, user_is_business_owner
from apps.core.domain_errors import InvalidTransition
from apps.core.idempotency import canonical_request_hash
from apps.scheduling.plan_access import assert_plan_change
from .models import Payment, PlanAllocation, PlanCompletionCorrection, PlanLegacyAttachment, PlanRemainderDecision, PlanTerms
from .plan_balances import ZERO, assert_plan_money, composition, current_terms, net_allocated, plan_money_projection, plan_sources, source_balance, retained_balance, receipt_plan
from .selectors import payment_queryset


def assert_owner_money(plan, actor):
    if not user_is_business_owner(actor, plan.business):
        raise PermissionDenied("Only the business owner can confirm this correction.")
    assert_plan_money(plan, actor, Actions.MANAGE)
    assert_plan_change(plan, actor)


def legacy_options(plan, actor):
    assert_owner_money(plan, actor)
    currency = current_terms(plan).currency if current_terms(plan) else plan.business.currency
    visits = plan.steps.filter(removed_at__isnull=True,
        appointment__status__in=["created", "confirmed", "rescheduled"], appointment__is_archived=False).values("appointment_id")
    return payment_queryset(actor, plan.business).filter(client=plan.client, currency=currency,
        kind="receipt", source="manual", plan__isnull=True, plan_attachment__isnull=True,
        deal__isnull=True, allocations__isnull=True).filter(
            Q(appointment__isnull=True) | Q(appointment_id__in=visits)).order_by("occurred_at", "pk")


def _selected_receipt(plan, actor, receipt_id):
    receipt = legacy_options(plan, actor).filter(pk=receipt_id).first()
    if receipt is None or receipt.amount <= receipt.refunded_amount:
        raise ValidationError({"receipt": "Select an unambiguous available manual receipt."})
    assert_can(actor, plan.business, Resources.PAYMENTS, Actions.MANAGE, obj=receipt)
    return receipt


def _selected_completion(plan, step_id):
    step = plan.steps.select_related("appointment").filter(pk=step_id, removed_at__isnull=True).first()
    if step is None or not step.appointment_id or step.appointment.status != "completed" or step.appointment.is_archived:
        raise InvalidTransition("Select a completed, active visit of this plan.")
    from .plan_services import require_current_terms
    terms = require_current_terms(plan)
    line = next((line for line in terms.lines if line["step"] == step.pk), None)
    if line is None or hasattr(step, "completion_correction"):
        raise InvalidTransition("This visit cannot be corrected again.")
    return step, terms, Decimal(line["amount"])


def _earmarked_remainder(plan, appointment):
    return [(receipt, source_balance(plan, receipt) - retained_balance(plan, receipt))
        for receipt in plan_sources(plan).filter(appointment=appointment)
        if receipt_plan(receipt) and receipt_plan(receipt).pk == plan.pk]


def preview_correction(plan, actor, command, data):
    assert_owner_money(plan, actor)
    if plan.is_archived or plan.client.is_archived:
        raise InvalidTransition("Restore the plan and client before correcting it.")
    before = plan_money_projection(plan, actor)
    if command == "annul-completion":
        step, terms, price = _selected_completion(plan, data.get("step_id"))
        released = net_allocated(PlanAllocation.objects.filter(appointment=step.appointment))
        newly_retained = released + sum((amount for _, amount in _earmarked_remainder(plan, step.appointment)), ZERO)
        result = {"step_id": step.pk, "appointment": step.appointment_id,
            "total_before": str(terms.total), "total_after": str(terms.total - price),
            "allocated_before": before["allocated"], "allocated_after": str(Decimal(before["allocated"]) - released),
            "retained_before": before["retained"], "retained_after": str(Decimal(before["retained"]) + newly_retained),
            "released": str(released), "removed_price": str(price), "currency": terms.currency}
    elif command == "attach-legacy":
        receipt = _selected_receipt(plan, actor, data.get("receipt"))
        amount = receipt.amount - receipt.refunded_amount
        result = {"receipt": receipt.pk, "original_amount": str(receipt.amount),
            "refunded_before": str(receipt.refunded_amount), "amount": str(amount), "currency": receipt.currency,
            "remaining_before": before["remaining"], "remaining_after": str(max(ZERO, Decimal(before["remaining"]) - amount))}
    else:
        raise ValidationError({"command": "Unsupported correction."})
    result["preview_hash"] = canonical_request_hash({"plan": plan.pk, "revision": plan.revision,
        "command": command, "result": result, "balance": before})
    return result


def _confirmed_preview(plan, actor, command, data):
    if data.get("consent") is not True or not str(data.get("reason", "")).strip():
        raise ValidationError({"consent": "Confirm the correction and provide a reason."})
    preview = preview_correction(plan, actor, command, data)
    if preview["preview_hash"] != data.get("preview_hash"):
        raise InvalidTransition("The balance changed. Review the correction again.")
    return preview


def attach_legacy(plan, actor, data):
    preview = _confirmed_preview(plan, actor, "attach-legacy", data)
    if "amount" in data and Decimal(data["amount"]) != Decimal(preview["amount"]):
        raise ValidationError({"amount": "Attach the entire available remainder."})
    receipt = _selected_receipt(plan, actor, data["receipt"])
    PlanLegacyAttachment.objects.create(plan=plan, receipt=receipt, amount=preview["amount"],
        refunded_before=receipt.refunded_amount, actor=actor, reason=data["reason"].strip())
    from .plan_services import allocate_completed
    allocate_completed(plan, actor)


def annul_completion(plan, actor, data):
    preview = _confirmed_preview(plan, actor, "annul-completion", data)
    step, terms, price = _selected_completion(plan, data["step_id"])
    appointment = step.appointment
    assert_can(actor, plan.business, Resources.APPOINTMENTS, Actions.UPDATE, obj=appointment)
    for receipt, amount in _earmarked_remainder(plan, appointment):
        if amount > 0:
            PlanRemainderDecision.objects.create(plan=plan, receipt=receipt, amount=amount,
                choice="retain", reason=data["reason"].strip(), consent=True, actor=actor)
    allocations = PlanAllocation.objects.filter(appointment=appointment, reversal_of__isnull=True, reversal__isnull=True)
    for original in allocations:
        PlanAllocation.objects.create(receipt=original.receipt, terms=original.terms,
            appointment=appointment, amount=original.amount, reversal_of=original, actor=actor)
        PlanRemainderDecision.objects.create(plan=plan, receipt=original.receipt, amount=original.amount,
            choice="retain", reason=data["reason"].strip(), consent=True, actor=actor)
    step.removed_at = timezone.now()
    step.save(update_fields=["removed_at", "updated_at"])
    corrected = PlanTerms.objects.create(plan=plan, revision=plan.revision + 1, previous=terms,
        mode=terms.mode, currency=terms.currency, total=terms.total - price,
        lines=[line for line in terms.lines if line["step"] != step.pk], composition=composition(plan),
        reason=data["reason"].strip(), consent=True, actor=actor)
    PlanCompletionCorrection.objects.create(step=step, terms=corrected, removed_price=price,
        released_amount=preview["released"], reason=data["reason"].strip(), actor=actor)
    from apps.scheduling.services import cancel_appointment_followups, create_appointment_activity
    appointment.status = "cancelled"
    appointment.save(update_fields=["status", "updated_at"])
    cancel_appointment_followups(appointment)
    create_appointment_activity(appointment=appointment, actor=actor,
        event_type="appointment_completion_corrected", text="Erroneous completion annulled",
        previous_status="completed", metadata={"reason": data["reason"].strip(), "plan_id": plan.pk})
    from apps.core.audit import write_actor_audit_log
    from apps.core.models import AuditLog
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=appointment,
        metadata={"kind": "lifecycle", "event_type": "appointment_completion_corrected",
                  "from": "completed", "to": "cancelled", "reason": data["reason"].strip(),
                  "plan_id": plan.pk, "risk_level": "high"})


def create_replacement(plan, actor, data):
    assert_owner_money(plan, actor)
    if data.get("consent") is not True or not str(data.get("reason", "")).strip():
        raise ValidationError({"consent": "Confirm the replacement and provide a reason."})
    correction = PlanCompletionCorrection.objects.select_related("step").filter(
        step__plan=plan, step_id=data.get("step_id")).first()
    if correction is None or correction.replacement_id:
        raise InvalidTransition("Select a corrected visit without a replacement.")
    if plan.steps.filter(removed_at__isnull=True).count() >= 100:
        raise ValidationError({"steps": "A plan supports up to 100 current steps."})
    from apps.scheduling.plan_services import _validate_step
    step = correction.step
    replacement = _validate_step(plan, actor, {name: getattr(step, name)
        for name in ("service", "resource", "branch", "responsible_user")})
    replacement.position = plan.steps.order_by("-position").first().position + 1
    replacement.save()
    correction.replacement = replacement
    correction.save(update_fields=["replacement"])
