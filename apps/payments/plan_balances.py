"""Derived balances; receipts remain the only source of received money."""
from decimal import Decimal

from django.db.models import Q, Sum
from rest_framework.exceptions import PermissionDenied

from apps.businesses.access import Actions, Resources, assert_can, can_view_sensitive_field
from apps.scheduling.plan_access import assert_plan_change
from .models import Payment, PlanAllocation, PlanCreditTransfer
from .selectors import payment_business, payment_queryset

ZERO = Decimal("0.00")


def total(query, field="amount"):
    return query.aggregate(value=Sum(field))["value"] or ZERO


def net_allocated(query):
    return total(query.filter(reversal_of__isnull=True)) - total(query.filter(reversal_of__isnull=False))


def refundable(receipt):
    return receipt.amount - receipt.refunded_amount - net_allocated(receipt.allocations.all())


def plan_sources(plan):
    return Payment.objects.filter(business_id=plan.business_id, client_id=plan.client_id, kind="receipt").filter(
        Q(plan=plan) | Q(plan_attachment__plan=plan) | Q(pk__in=PlanCreditTransfer.objects.filter(target_plan=plan).values("receipt_id"))).order_by("occurred_at", "pk")


def receipt_plan(receipt):
    if receipt.plan_id:
        return receipt.plan
    attachment = getattr(receipt, "plan_attachment", None)
    return attachment.plan if attachment else None


def source_balance(plan, receipt):
    initial = receipt.amount if receipt.plan_id == plan.pk else ZERO
    attachment = getattr(receipt, "plan_attachment", None)
    if attachment and attachment.plan_id == plan.pk:
        initial += attachment.amount
    incoming = total(PlanCreditTransfer.objects.filter(receipt=receipt, target_plan=plan))
    outgoing = total(PlanCreditTransfer.objects.filter(receipt=receipt, source_plan=plan))
    refunds = total(receipt.refunds.filter(plan=plan))
    allocated = net_allocated(receipt.allocations.filter(terms__plan=plan))
    return initial + incoming - outgoing - refunds - allocated


def retained_balance(plan, receipt):
    events = [(row.created_at, row.pk, row.amount) for row in
        plan.remainder_decisions.filter(receipt=receipt, choice="retain")]
    events += [(row.created_at, row.pk, -row.amount) for row in
        plan.remainder_decisions.filter(receipt=receipt, choice="reuse")]
    events += [(row.created_at, row.pk, -row.amount) for row in
        PlanCreditTransfer.objects.filter(receipt=receipt, source_plan=plan)]
    events += [(row.created_at, row.pk, -row.amount) for row in receipt.refunds.filter(plan=plan)]
    retained = ZERO
    for _, _, delta in sorted(events):
        retained = max(ZERO, retained + delta)
    return min(source_balance(plan, receipt), retained)


def assert_plan_money(plan, actor, action=Actions.VIEW):
    if action != Actions.VIEW:
        payment_business(actor, plan.business_id, Actions.VIEW)
    payment_business(actor, plan.business_id, action)
    if not can_view_sensitive_field(actor, plan.business, Resources.PAYMENTS, "amount"):
        raise PermissionDenied("Financial field access is required.")
    assert_plan_change(plan, actor, Actions.VIEW)
    candidate = Payment(business=plan.business, client=plan.client, created_by=actor)
    assert_can(actor, plan.business, Resources.PAYMENTS, action, obj=candidate)
    sources = plan_sources(plan)
    visible = payment_queryset(actor, plan.business)
    if sources.exclude(pk__in=visible.values("pk")).exists():
        raise PermissionDenied("All payment sources must be available.")


def composition(plan):
    return [{"id": s.pk, "service": s.service_id} for s in plan.steps.filter(removed_at__isnull=True).order_by("pk")]


def current_terms(plan):
    return plan.payment_terms.order_by("-revision", "-pk").first()


def plan_money_projection(plan, actor):
    try:
        assert_plan_money(plan, actor)
    except PermissionDenied:
        return None
    terms = current_terms(plan)
    sources = list(plan_sources(plan))
    received = sum((r.amount if r.plan_id == plan.pk else ZERO for r in sources), ZERO)
    incoming = total(plan.incoming_credit.all())
    attached = total(plan.legacy_attachments.all())
    outgoing = total(plan.outgoing_credit.all())
    refunded = total(plan.payments.filter(kind="refund"))
    allocated = net_allocated(PlanAllocation.objects.filter(terms__plan=plan))
    unallocated = sum((source_balance(plan, r) for r in sources), ZERO)
    retained = sum((retained_balance(plan, r) for r in sources), ZERO)
    permissions = {}
    from apps.businesses.access import user_is_business_owner
    for name, action in (("can_receive", Actions.CREATE), ("can_manage", Actions.MANAGE)):
        try:
            assert_plan_money(plan, actor, action)
            assert_plan_change(plan, actor)
            permissions[name] = True
        except PermissionDenied:
            permissions[name] = False
    permissions["can_correct"] = permissions["can_manage"] and user_is_business_owner(actor, plan.business)
    return {"terms": None if terms is None else {"id": terms.pk, "mode": terms.mode,
        "currency": terms.currency, "total": str(terms.total), "lines": terms.lines,
        "revision": terms.revision, "reason": terms.reason, "created_at": terms.created_at},
        "terms_current": bool(terms and terms.composition == composition(plan)),
        "received": str(received), "attached": str(attached), "incoming_credit": str(incoming), "outgoing_credit": str(outgoing),
        "refunded": str(refunded), "allocated": str(allocated), "unallocated": str(unallocated),
        "retained": str(retained), "remaining": str(max(ZERO, (terms.total if terms else ZERO) - allocated - unallocated + retained)),
        "sources": [{"id": r.pk, "amount": str(r.amount), "available": str(source_balance(plan, r)),
            "retained": str(retained_balance(plan, r)), "method": r.method, "occurred_at": r.occurred_at} for r in sources],
        "allocations": [{"id": a.pk, "appointment": a.appointment_id, "amount": str(a.amount),
            "reversal_of": a.reversal_of_id, "created_at": a.created_at}
            for a in PlanAllocation.objects.filter(terms__plan=plan).order_by("pk")], **permissions}
