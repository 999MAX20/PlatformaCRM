"""SaaS orders with explicit terms; no implicit price or period policy."""
import hashlib
import json
import re
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.mfa import validate_step_up_token
from apps.billing.models import BillingOffer, BillingOrder, BillingReceipt, BillingEvent, Subscription
from apps.businesses.access import Actions, Resources, assert_can
from apps.businesses.models import Business
from apps.businesses.ownership import active_actor
from apps.core.audit import write_actor_audit_log
from apps.core.domain_errors import DomainAPIException, IdempotencyConflict
from apps.core.models import AuditLog
from apps.core.permissions import accessible_businesses, is_platform_admin
from apps.support.access import assert_platform_actor
from apps.support.models import SupportCase


class CommerceUnavailable(DomainAPIException):
    status_code = 409
    error_code = "billing_not_configured"
    default_code = error_code
    default_detail = "Payment collection is not configured."
    category = "conflict"


def require_commerce():
    if not getattr(settings, "BILLING_COMMERCE_ENABLED", False):
        raise CommerceUnavailable()


def subscription_revision(subscription):
    state = None if subscription is None else [subscription.pk, subscription.plan_id, subscription.status,
        str(subscription.started_at), str(subscription.next_payment_at), str(subscription.cancelled_at)]
    return hashlib.sha256(json.dumps(state).encode()).hexdigest()


def audit(order, kind, *, actor=None, case=None, code="", reason=""):
    BillingEvent.objects.create(order=order, kind=kind, code=code, actor=actor, support_case=case, reason=reason)
    # Server confirmations have no human request; they still require durable audit.
    write_actor_audit_log(actor=actor, action=AuditLog.Actions.UPDATE, instance=order, business=order.business,
        metadata={"kind": "billing_payment", "event": kind, "code": code,
                  "order_id": str(order.pk), "support_case_id": case.pk if case else None,
                  "category": AuditLog.Categories.DATA, "risk_level": AuditLog.RiskLevels.HIGH})


def merchant_business(request, business_id, action=Actions.VIEW, *, lock=False):
    actor = active_actor(request)
    rows = Business.objects.filter(pk__in=accessible_businesses(actor).values("pk"))
    if lock:
        rows = rows.select_for_update()
    business = get_object_or_404(rows, pk=business_id)
    assert_can(actor, business, Resources.BILLING, action)
    return actor, business


def operator(request, business_id, case_id, reason, *, admin=False):
    actor = active_actor(request, lock=True)
    assert_platform_actor(actor)
    if admin and not is_platform_admin(actor):
        raise PermissionDenied("Only platform administrators can confirm bank receipts.")
    validate_step_up_token(actor, request.headers.get("X-Zani-MFA-Step-Up", ""))
    if not reason.strip():
        raise ValidationError({"reason": "A reason is required."})
    business = get_object_or_404(Business.objects.select_for_update(), pk=business_id)
    case = get_object_or_404(SupportCase.objects.select_for_update(), pk=case_id, business=business)
    if case.status == "resolved":
        raise ValidationError("Reopen the support case first.")
    return actor, business, case


def seller_terms(offer):
    value = offer.seller
    allowed = {"name", "tax_id", "bank", "iban", "bic", "account_key"}
    if not isinstance(value, dict) or set(value) - allowed or not all(isinstance(v, str) and len(v) <= 255 for v in value.values()):
        raise CommerceUnavailable()
    if not all(value.get(k, "").strip() for k in ("name", "tax_id", "account_key")):
        raise CommerceUnavailable()
    return dict(value)


def validate_offer(offer):
    if not offer.is_active or not offer.approval_reference.strip() or not offer.plan.is_active:
        raise CommerceUnavailable()
    if offer.expires_at <= timezone.now() or offer.period_end <= timezone.now():
        raise ValidationError("The offer has expired.")
    if not re.fullmatch(r"[A-Z]{3}", offer.currency) or offer.amount <= 0 or offer.period_start >= offer.period_end:
        raise CommerceUnavailable()
    return seller_terms(offer)


@transaction.atomic
def create_order(request, business_id, *, request_id, offer_id, buyer):
    require_commerce()
    actor, business = merchant_business(request, business_id, Actions.MANAGE, lock=True)
    existing = BillingOrder.objects.filter(pk=request_id).first()
    if existing:
        if existing.business_id != business.pk or str(existing.offer_id) != str(offer_id) or existing.buyer != buyer:
            raise IdempotencyConflict()
        return existing
    offer = get_object_or_404(BillingOffer.objects.select_for_update(), pk=offer_id, business=business)
    seller = validate_offer(offer)
    if BillingOrder.objects.filter(offer=offer).exists():
        raise IdempotencyConflict("An order already exists for this offer.")
    if buyer.get("kind") not in {"person", "company", "sole_trader"}:
        raise ValidationError("Unknown buyer type.")
    subscription = Subscription.objects.select_for_update().filter(business=business).first()
    item = BillingOrder.objects.create(id=request_id, offer=offer, business=business, plan=offer.plan,
        amount=offer.amount, currency=offer.currency, period_start=offer.period_start, period_end=offer.period_end,
        expires_at=offer.expires_at, buyer=buyer, created_by=actor, subscription_revision=subscription_revision(subscription),
        terms={"approval_reference": offer.approval_reference, "seller": seller, "plan_name": offer.plan.name,
               "plan_code": offer.plan.code, "limits": offer.plan.limits_json, "features": offer.plan.features_json})
    audit(item, "order_created", actor=actor)
    return item


def locked_order(business_id, order_id):
    business = get_object_or_404(Business.objects.select_for_update(), pk=business_id)
    return get_object_or_404(BillingOrder.objects.select_for_update(), pk=order_id, business=business)


def financial_state(order):
    receipts = list(order.receipts.order_by("pk")[:2])
    if not receipts:
        return "awaiting"
    if len(receipts) != 1:
        return "multiple_payments"
    row = receipts[0]
    if row.status != "confirmed":
        return row.status
    if row.amount != order.amount or row.currency != order.currency:
        return "amount_mismatch"
    return "confirmed"


@transaction.atomic
def record_bank(request, business_id, order_id, *, support_case_id, reason, reference, amount, currency, received_at):
    require_commerce()
    actor, business, case = operator(request, business_id, support_case_id, reason, admin=True)
    order = get_object_or_404(BillingOrder.objects.select_for_update(), pk=order_id, business=business)
    if amount <= 0 or received_at > timezone.now() or not reference.strip():
        raise ValidationError("Provide the actual positive bank receipt and its date.")
    seller = order.terms["seller"]
    if not all(seller.get(k) for k in ("bank", "iban", "bic")):
        raise CommerceUnavailable()
    existing = BillingReceipt.objects.filter(source="bank", merchant=seller["account_key"], reference=reference).first()
    if existing:
        if existing.order_id != order.pk or existing.amount != amount or existing.currency != currency or existing.received_at != received_at:
            raise IdempotencyConflict()
        return order
    BillingReceipt.objects.create(order=order, source="bank", merchant=seller["account_key"], reference=reference,
        amount=amount, currency=currency, received_at=received_at, confirmed_by=actor, support_case=case, reason=reason)
    audit(order, "bank_confirmed", actor=actor, case=case, reason=reason)
    return order
