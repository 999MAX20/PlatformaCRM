"""Financial plan effects run under the existing Business/plan transaction lock."""
import uuid

from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.businesses.access import Actions
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.plan_access import assert_plan_change
from .models import Payment, PlanAllocation, PlanCreditTransfer, PlanRemainderDecision, PlanTerms
from .plan_balances import (
    ZERO, assert_plan_money, composition, current_terms, net_allocated, plan_sources,
    retained_balance, source_balance,
)
from .plan_pricing import money, preview_terms


def accept_terms(plan, actor, data):
    if data.get("consent") is not True or not str(data.get("reason", "")).strip():
        raise ValidationError({"consent": "Confirm the terms and provide a reason."})
    preview = preview_terms(plan, actor, data)
    if data.get("preview_hash") != preview["preview_hash"]:
        raise InvalidTransition("Payment terms changed. Review the calculation again.")
    prior = current_terms(plan)
    PlanTerms.objects.create(plan=plan, revision=plan.revision + 1, previous=prior,
        mode=preview["mode"], currency=preview["currency"], total=preview["total"],
        lines=preview["lines"], composition=preview["composition"],
        reason=data["reason"].strip(), consent=True, actor=actor)


def require_current_terms(plan):
    terms = current_terms(plan)
    if not terms or terms.composition != composition(plan):
        raise InvalidTransition("Review and accept current plan payment terms first.")
    return terms


def allocate_completed(plan, actor, *, appointment=None):
    terms = current_terms(plan)
    if terms is None:
        return
    terms = require_current_terms(plan)
    prices = {line["step"]: money(line["amount"]) for line in terms.lines}
    steps = plan.steps.filter(appointment__status="completed", removed_at__isnull=True).select_related("appointment").order_by("appointment__start_at", "pk")
    if appointment is not None:
        steps = steps.filter(appointment=appointment)
    sources = list(plan_sources(plan).select_for_update())
    for step in steps:
        due = prices[step.pk] - net_allocated(PlanAllocation.objects.filter(appointment=step.appointment))
        for receipt in sources:
            if due <= 0:
                break
            # A retained remainder needs an explicit transfer before reuse.
            available = source_balance(plan, receipt) - retained_balance(plan, receipt)
            if receipt.plan_id == plan.pk and receipt.appointment_id and receipt.appointment_id != step.appointment_id:
                continue
            amount = min(due, available)
            if amount > 0:
                PlanAllocation.objects.create(receipt=receipt, terms=terms, appointment=step.appointment,
                    amount=amount, actor=actor)
                due -= amount


def settle_remainder(plan, actor, data):
    assert_plan_money(plan, actor, Actions.MANAGE)
    if data.get("consent") is not True or not str(data.get("reason", "")).strip():
        raise ValidationError({"consent": "Record the client's choice and reason."})
    receipt = plan_sources(plan).filter(pk=data.get("receipt")).first()
    if receipt is None:
        raise ValidationError({"receipt": "Select an available source of this plan."})
    amount = money(data.get("amount"), positive=True)
    choice = data.get("choice")
    if choice not in {"retain", "refund"}:
        raise ValidationError({"choice": "Choose refund or retain explicitly."})
    available = source_balance(plan, receipt)
    if choice == "retain":
        available -= retained_balance(plan, receipt)
    if amount > available:
        raise ValidationError({"amount": "The remainder is no longer available."})
    refund = None
    if choice == "refund":
        from .services import record_payment
        refund, _ = record_payment(actor=actor, data={"business": plan.business_id,
            "original": receipt.pk, "refund_plan": plan.pk, "amount": amount,
            "submission_id": uuid.uuid4(), "occurred_at": timezone.now(), "method": receipt.method,
            "reason": data["reason"]}, touch_plan=False)
    PlanRemainderDecision.objects.create(plan=plan, receipt=receipt, amount=amount, choice=choice,
        refund=refund, reason=data["reason"].strip(), consent=True, actor=actor)


def use_credit(plan, actor, data):
    from apps.scheduling.models import VisitPlan
    assert_plan_money(plan, actor, Actions.CREATE)
    require_current_terms(plan)
    source = VisitPlan.objects.select_for_update().filter(pk=data.get("source_plan"),
        business_id=plan.business_id, client_id=plan.client_id).first()
    if source is None or source.pk == plan.pk:
        raise ValidationError({"source_plan": "Select another plan of this client and business."})
    assert_plan_money(source, actor, Actions.MANAGE)
    assert_plan_change(source, actor)
    if source.revision != data.get("source_revision"):
        raise InvalidTransition("The source plan changed. Refresh its balance.")
    receipt = plan_sources(source).filter(pk=data.get("receipt")).first()
    amount = money(data.get("amount"), positive=True)
    if not receipt or amount > retained_balance(source, receipt):
        raise ValidationError({"amount": "Select an available retained amount."})
    if receipt.currency != require_current_terms(plan).currency:
        raise ValidationError({"receipt": "Currencies must match."})
    if data.get("consent") is not True or not str(data.get("reason", "")).strip():
        raise ValidationError({"consent": "Confirm the transfer and provide a reason."})
    PlanCreditTransfer.objects.create(receipt=receipt, source_plan=source, target_plan=plan,
        amount=amount, reason=data["reason"].strip(), actor=actor)
    source.revision += 1
    source.save(update_fields=["revision", "updated_at"])
    from apps.scheduling.plan_services import _effect
    _effect(source, actor, "credit-transferred", reason=data["reason"])
    allocate_completed(plan, actor)
