"""Durable checkout attempts and verified server reconciliation, independent of bank."""
from decimal import Decimal
import re
from django.db import transaction
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.billing import providers
from apps.billing.application import attempt_application
from apps.billing.commerce import audit, financial_state, locked_order, merchant_business, require_commerce, CommerceUnavailable
from apps.billing.models import BillingAttempt, BillingReceipt
from apps.businesses.access import Actions
from apps.core.domain_errors import IdempotencyConflict, ProviderUnavailable


def start_checkout(request, business_id, order_id):
    require_commerce()
    gateway = providers.adapter()
    with transaction.atomic():
        actor, _ = merchant_business(request, business_id, Actions.MANAGE, lock=True)
        order = locked_order(business_id, order_id)
        if order.applied_at or financial_state(order) != "awaiting" or order.expires_at <= timezone.now():
            raise ValidationError("This order cannot start another payment.")
        previous = order.attempts.filter(status__in=["creating", "pending", "unknown"]).first()
        if previous:
            # Never create a second payment while the first result is uncertain.
            return previous
        attempt = BillingAttempt.objects.create(order=order, provider=gateway.key, merchant=gateway.merchant)
        audit(order, "checkout_started", actor=actor)
    try:
        result = providers.safe_checkout(gateway.create_checkout(attempt_id=attempt.pk, order_id=order.pk,
                                        amount=order.amount, currency=order.currency), gateway)
    except Exception:
        # A timeout may have happened AFTER the gateway created the payment.
        with transaction.atomic():
            order = locked_order(business_id, order_id)
            attempt = BillingAttempt.objects.select_for_update().get(pk=attempt.pk)
            if attempt.status == "creating":
                attempt.status = "unknown"
                attempt.failure_code = "checkout_uncertain"
                attempt.save(update_fields=["status", "failure_code", "updated_at"])
                audit(order, "checkout_uncertain", actor=actor)
        return attempt
    with transaction.atomic():
        order = locked_order(business_id, order_id)
        attempt = BillingAttempt.objects.select_for_update().get(pk=attempt.pk)
        if attempt.status == "creating":
            attempt.status = "pending"
            attempt.checkout_url = result.url
            attempt.external_id = result.external_id
            attempt.save(update_fields=["status", "checkout_url", "external_id", "updated_at"])
        return attempt


def reconcile_attempt(attempt_id):
    # Call only after merchant/operator authorization or adapter notification authentication.
    require_commerce()
    gateway = providers.adapter()
    attempt = get_object_or_404(BillingAttempt.objects.select_related("order"), pk=attempt_id,
                                 provider=gateway.key, merchant=gateway.merchant)
    try:
        result = gateway.lookup(attempt_id=attempt.pk)
    except Exception:
        raise ProviderUnavailable("Payment status is temporarily unavailable.") from None
    if (str(result.attempt_id) != str(attempt.pk) or str(result.order_id) != str(attempt.order_id)
            or result.status not in {"pending", "failed", "confirmed", "refunded", "disputed"}
            or not isinstance(result.amount, Decimal) or not result.amount.is_finite()
            or result.amount <= 0 or result.amount > Decimal("9999999999.99")
            or result.amount != result.amount.quantize(Decimal("0.01"))
            or not re.fullmatch(r"[A-Z]{3}", result.currency)):
        raise ValidationError("Payment verification returned inconsistent data.")
    with transaction.atomic():
        order = locked_order(attempt.order.business_id, attempt.order_id)
        attempt = BillingAttempt.objects.select_for_update().get(pk=attempt.pk)
        if result.status in {"confirmed", "refunded", "disputed"}:
            if not result.reference or len(result.reference) > 128 or timezone.is_naive(result.received_at) or result.received_at > timezone.now():
                raise ValidationError("Payment verification returned inconsistent data.")
            receipt = BillingReceipt.objects.select_for_update().filter(source=gateway.key, merchant=gateway.merchant,
                                                                       reference=result.reference).first()
            if receipt:
                if receipt.order_id != order.pk or receipt.amount != result.amount or receipt.currency != result.currency:
                    raise IdempotencyConflict()
                # A stale success must never erase a refund/dispute. Resolution needs separate policy.
                if receipt.status == "confirmed" and result.status != "confirmed":
                    receipt.status = result.status
                    receipt.save(update_fields=["status", "updated_at"])
                    audit(order, "payment_review", code=result.status)
            else:
                receipt = BillingReceipt.objects.create(order=order,source=gateway.key,merchant=gateway.merchant,
                    reference=result.reference,amount=result.amount,currency=result.currency,status=result.status,received_at=result.received_at)
                audit(order, "card_verified", code=result.status)
            attempt.status = receipt.status
            attempt.checkout_url = ""
        elif attempt.status not in {"confirmed", "refunded", "disputed"}:
            attempt.status = result.status
            if result.status == "failed":
                attempt.checkout_url = ""
        attempt.failure_code = ""
        attempt.save(update_fields=["status", "checkout_url", "failure_code", "updated_at"])
    return attempt_application(order.business_id, order.pk)


def receive_notification(provider, body, headers):
    gateway = providers.adapter()
    if provider != gateway.key or len(body) > 65536:
        raise PermissionDenied("Invalid payment notification.")
    try:
        attempt_id = gateway.authenticate_notification(body=body, headers=headers)
    except Exception:
        raise PermissionDenied("Invalid payment notification.") from None
    # Do not trust a redirect, supplied amount/tenant, or even stale event status.
    return reconcile_attempt(attempt_id)
