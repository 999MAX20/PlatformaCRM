from decimal import Decimal, InvalidOperation

from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.activities.services import create_activity_event
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.audit import write_actor_audit_log
from apps.core.idempotency import canonical_request_hash, CRMCommandConflict
from apps.core.models import AuditLog
from apps.core.domain_errors import InvalidTransition
from apps.crm.models import Deal
from apps.scheduling.models import Appointment
from .models import Payment
from .selectors import payment_business, payment_queryset, visible_entities


@transaction.atomic
def record_payment(*, actor, data, touch_plan=True):
    original_id = data.get("original")
    action = Actions.MANAGE if original_id else Actions.CREATE
    business = payment_business(actor, data["business"], action)
    # All ledger writers lock the same row: prevents over-refund and concurrent
    # submissions even when they use distinct command identities.
    Business.objects.select_for_update().get(pk=business.pk)
    request_hash = canonical_request_hash({**data, "actor": actor.pk})
    existing = Payment.objects.filter(business=business, submission_id=data["submission_id"]).first()
    if existing:
        if existing.request_hash != request_hash:
            raise CRMCommandConflict("Submission identity already belongs to different payment data.")
        from .plan_balances import assert_plan_money, receipt_plan
        existing_plan = receipt_plan(existing)
        if existing_plan:
            assert_plan_money(existing_plan, actor, action)
        return get_object_or_404(payment_queryset(actor, business), pk=existing.pk), True

    try:
        amount = Decimal(data["amount"])
    except (InvalidOperation, ValueError):
        raise ValidationError({"amount": "Enter a valid amount."})
    if not amount.is_finite() or amount <= 0 or amount > Decimal("999999999999.99") or amount != amount.quantize(Decimal("0.01")):
        raise ValidationError({"amount": "Enter a positive amount with up to two decimal places."})
    if data["occurred_at"] > timezone.now():
        raise ValidationError({"occurred_at": "A received payment cannot be in the future."})
    if data["method"] not in Payment.Methods.values:
        raise ValidationError({"method": "Invalid payment method."})

    original = None
    plan = None
    if original_id:
        original = get_object_or_404(payment_queryset(actor, business), pk=original_id)
        assert_can(actor, business, Resources.PAYMENTS, Actions.MANAGE, obj=original)
        if original.kind != Payment.Kinds.RECEIPT or original.source != "manual":
            raise ValidationError({"original": "Only manual receipts can be refunded here."})
        if not data.get("reason", "").strip():
            raise ValidationError({"reason": "A refund reason is required."})
        from .plan_balances import refundable
        if amount > refundable(original):
            raise ValidationError({"amount": "Refund exceeds the remaining received amount."})
        if data["occurred_at"] < original.occurred_at:
            raise ValidationError({"occurred_at": "Refund cannot precede receipt."})
        client, deal, appointment, currency = original.client, original.deal, original.appointment, original.currency
        from .plan_balances import receipt_plan
        origin_plan = receipt_plan(original)
        if origin_plan:
            from apps.scheduling.models import VisitPlan
            from .plan_balances import assert_plan_money, source_balance
            plan = get_object_or_404(VisitPlan.objects.select_for_update(),
                pk=data.get("refund_plan") or origin_plan.pk, business=business, client=client)
            assert_plan_money(plan, actor, Actions.MANAGE)
            if plan.pk != origin_plan.pk:
                appointment = None
            if amount > source_balance(plan, original):
                raise ValidationError({"amount": "Refund exceeds the unallocated plan balance."})
    else:
        client = get_object_or_404(
            visible_entities(Client, actor, business, Resources.CLIENTS).select_for_update(),
            pk=data.get("client"), is_archived=False,
        )
        if data.get("deal") and data.get("appointment"):
            raise ValidationError({"deal": "Select a deal or an appointment, not both."})
        deal = _link(Deal, data.get("deal"), actor, business, Resources.DEALS, client)
        appointment = _link(Appointment, data.get("appointment"), actor, business, Resources.APPOINTMENTS, client)
        currency = business.currency
        if not data.get("plan") and data.get("currency") != currency:
            raise ValidationError({"currency": "Use the current business currency."})
        if deal and deal.currency != currency:
            raise ValidationError({"deal": "Deal currency does not match the payment currency."})
        if data.get("plan"):
            from apps.scheduling.models import VisitPlan
            from apps.scheduling.plan_access import assert_plan_change
            from .plan_balances import assert_plan_money
            from .plan_services import require_current_terms
            plan = get_object_or_404(VisitPlan.objects.select_for_update(), pk=data["plan"],
                business=business, client=client, is_archived=False)
            assert_plan_money(plan, actor, Actions.CREATE)
            assert_plan_change(plan, actor)
            if plan.revision != data.get("expected_revision"):
                raise InvalidTransition("The plan changed. Review its current terms.")
            terms = require_current_terms(plan)
            currency = terms.currency
            if data.get("currency") != currency or deal:
                raise ValidationError({"plan": "Plan currency must match; a deal cannot also be linked."})
            if appointment and not plan.steps.filter(appointment=appointment, removed_at__isnull=True).exists():
                raise ValidationError({"appointment": "Select a visit of this plan."})
        elif appointment and hasattr(appointment, "visit_plan_step") and appointment.visit_plan_step.plan.payment_terms.exists():
            raise ValidationError({"plan": "Record this visit payment through its plan."})

    payment = Payment(
        business=business, client=client, deal=deal, appointment=appointment, plan=plan,
        original=original, kind=Payment.Kinds.REFUND if original else Payment.Kinds.RECEIPT,
        amount=amount, currency=currency, occurred_at=data["occurred_at"],
        method=data["method"], note=data.get("note", "").strip(),
        reason=data.get("reason", "").strip() if original else "",
        created_by=actor, submission_id=data["submission_id"], request_hash=request_hash,
    )
    assert_can(actor, business, Resources.PAYMENTS, action, obj=payment if not original else original)
    payment.save(force_insert=True)
    if original:
        original.refunded_amount += amount
        original.save(update_fields=["refunded_amount"])
    if plan is not None:
        if not original:
            from .plan_services import allocate_completed
            allocate_completed(plan, actor)
        if touch_plan:
            from apps.scheduling.plan_lifecycle import touch_appointment_plan
            touch_appointment_plan(plan)
    event_type = "client_payment_refunded" if original else "client_payment_recorded"
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.CREATE, instance=payment,
                          metadata={"event_type": event_type, "original_id": original_id, "risk_level": "high"})
    # Client timeline has broader permissions than financial records: no amount,
    # note/reason or provider data is copied into that surface.
    create_activity_event(business=business, client=client, actor=actor, instance=payment,
                          event_type=event_type, metadata={"payment_id": payment.pk})
    return payment, False


def _link(model, pk, actor, business, resource, client):
    if not pk:
        return None
    return get_object_or_404(visible_entities(model, actor, business, resource),
                            pk=pk, client=client, is_archived=False)
