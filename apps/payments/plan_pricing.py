from decimal import Decimal, InvalidOperation

from rest_framework.exceptions import ValidationError

from apps.core.idempotency import canonical_request_hash
from .plan_balances import ZERO, composition, current_terms, plan_money_projection


def money(value, *, positive=False):
    try:
        result = Decimal(str(value))
        valid = result.is_finite() and ZERO <= result <= Decimal("999999999999.99")
        valid = valid and result == result.quantize(Decimal("0.01")) and (not positive or result > 0)
    except (InvalidOperation, ValueError, TypeError):
        valid = False
    if not valid:
        raise ValidationError({"amount": "Use a valid amount with at most two decimal places."})
    return result.quantize(Decimal("0.01"))


def distribute(bases, amount):
    basis = sum(bases.values(), ZERO)
    if not basis:
        if amount:
            raise ValidationError({"base_prices": "A positive package requires nonzero base prices."})
        return {key: ZERO for key in bases}
    denominator = int(basis * 100)
    shares = {key: divmod(int(amount * 100) * int(value * 100), denominator) for key, value in bases.items()}
    cents = {key: share[0] for key, share in shares.items()}
    remainder = int(amount * 100) - sum(cents.values())
    for key in sorted(shares, key=lambda key: (-shares[key][1], key))[:remainder]:
        cents[key] += 1
    return {key: Decimal(value) / 100 for key, value in cents.items()}


def price_plan(plan, data):
    mode = data.get("mode")
    if mode not in {"package", "per_visit"}:
        raise ValidationError({"mode": "Select a payment mode."})
    steps = list(plan.steps.filter(removed_at__isnull=True).select_related("appointment", "service").order_by("pk"))
    if not steps:
        raise ValidationError({"steps": "Add a visit before accepting payment terms."})
    values = data.get("base_prices", [])
    bases = {item["step"]: money(item["amount"]) for item in values}
    if len(values) != len(bases) or set(bases) != {step.pk for step in steps}:
        raise ValidationError({"base_prices": "Supply each current step exactly once."})
    prior = current_terms(plan)
    if prior is None:
        from .models import Payment
        if Payment.objects.filter(business_id=plan.business_id, plan__isnull=True,
                appointment_id__in=[step.appointment_id for step in steps if step.appointment_id]).exists():
            raise ValidationError({"legacy_payments": "Existing visit payments require explicit reconciliation before accepting plan terms."})
    old = {line["step"]: line for line in prior.lines} if prior else {}
    frozen = {}
    for step in steps:
        if step.appointment_id and step.appointment.status == "completed":
            if step.pk not in old:
                raise ValidationError({"steps": "Completed legacy visits need explicit reconciliation."})
            frozen[step.pk] = money(old[step.pk]["amount"])
            if bases[step.pk] != money(old[step.pk]["base"]):
                raise ValidationError({"base_prices": "Completed visit prices are immutable."})
    future = {key: value for key, value in bases.items() if key not in frozen}
    frozen_total = sum(frozen.values(), ZERO)
    total = money(data.get("total")) if mode == "package" else money(frozen_total + sum(future.values(), ZERO))
    if total < frozen_total:
        raise ValidationError({"total": "Total cannot be below completed visit prices."})
    if not future and total != frozen_total:
        raise ValidationError({"total": "Completed visit prices are immutable."})
    amounts = {**frozen, **(distribute(future, total - frozen_total) if mode == "package" else future)}
    currency = prior.currency if prior else plan.business.currency
    return {"mode": mode, "currency": currency, "total": str(total), "composition": composition(plan),
        "lines": [{"step": step.pk, "base": str(bases[step.pk]), "amount": str(amounts[step.pk]),
            "frozen": step.pk in frozen} for step in steps]}


def preview_terms(plan, actor, data):
    from .plan_balances import assert_plan_money
    from apps.businesses.access import Actions
    from apps.scheduling.plan_access import assert_plan_change
    assert_plan_money(plan, actor, Actions.CREATE)
    assert_plan_change(plan, actor)
    priced = price_plan(plan, data)
    balance = plan_money_projection(plan, actor)
    return {**priced, "balance": {key: balance[key] for key in ("received", "refunded", "allocated", "unallocated", "retained")},
        "preview_hash": canonical_request_hash({"plan": plan.pk, "revision": plan.revision,
        "priced": priced, "balance": balance})}
