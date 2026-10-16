"""Apply a confirmed order once, preserving separately committed payment evidence."""
from django.db import DatabaseError, transaction
from django.utils import timezone
from apps.billing.commerce import audit, financial_state, locked_order, operator, require_commerce, subscription_revision
from apps.billing.models import BillingOrder, Subscription, SubscriptionPlan


def block(order, code, *, actor=None, case=None):
    if order.application_status != "blocked" or order.application_code != code:
        order.application_status = "blocked"
        order.application_code = code
        order.save(update_fields=["application_status", "application_code", "updated_at"])
        audit(order, "application_blocked", actor=actor, case=case, code=code)
    return order


@transaction.atomic
def apply_order(business_id, order_id, *, actor=None, case=None):
    require_commerce()
    order = locked_order(business_id, order_id)
    if order.applied_at:
        # A later refund/overpayment is visible in financial_state, never a new grant.
        return order
    state = financial_state(order)
    if state == "awaiting":
        return order
    if state != "confirmed":
        return block(order, state, actor=actor, case=case)
    if order.receipts.get().received_at > order.expires_at:
        return block(order, "late_payment", actor=actor, case=case)
    now = timezone.now()
    if order.period_start > now:
        return block(order, "period_not_started", actor=actor, case=case)
    if order.period_end <= now:
        return block(order, "period_expired", actor=actor, case=case)
    if order.business.status in {"blocked", "inactive"}:
        return block(order, "business_restricted", actor=actor, case=case)
    subscription = Subscription.objects.select_for_update().filter(business_id=business_id).first()
    if subscription and subscription.status in {"paused", "cancelled"}:
        return block(order, "subscription_restricted", actor=actor, case=case)
    if subscription_revision(subscription) != order.subscription_revision:
        return block(order, "subscription_changed", actor=actor, case=case)
    plan = SubscriptionPlan.objects.select_for_update().get(pk=order.plan_id)
    if not plan.is_active or plan.limits_json != order.terms["limits"] or plan.features_json != order.terms["features"]:
        return block(order, "plan_changed", actor=actor, case=case)
    if subscription and subscription.status == "active" and subscription.next_payment_at and subscription.next_payment_at > order.period_start:
        return block(order, "period_overlap", actor=actor, case=case)
    if subscription is None:
        subscription = Subscription(business_id=business_id)
    subscription.plan_id = order.plan_id
    subscription.status = "active"
    subscription.started_at = subscription.started_at or order.period_start
    subscription.next_payment_at = order.period_end
    subscription.save()
    order.applied_at = now
    order.application_status = "applied"
    order.application_code = ""
    order.save(update_fields=["applied_at", "application_status", "application_code", "updated_at"])
    audit(order, "application_completed", actor=actor, case=case)
    return order


def attempt_application(business_id, order_id, *, actor=None, case=None):
    try:
        return apply_order(business_id, order_id, actor=actor, case=case)
    except DatabaseError:
        # The receipt is in a previous committed transaction. Never log DB/provider text.
        with transaction.atomic():
            order = locked_order(business_id, order_id)
            if not order.applied_at:
                order.application_status = "failed"
                order.application_code = "temporary_failure"
                order.save(update_fields=["application_status", "application_code", "updated_at"])
                audit(order, "application_failed", actor=actor, case=case, code="temporary_failure")
            return order


def recover(request, business_id, order_id, *, support_case_id, reason):
    # Authorization and the application share locks; a failure rolls back all writes.
    with transaction.atomic():
        actor, _, case = operator(request, business_id, support_case_id, reason)
        order = locked_order(business_id, order_id)
        audit(order, "recovery_requested", actor=actor, case=case, reason=reason)
        return apply_order(business_id, order_id, actor=actor, case=case)
