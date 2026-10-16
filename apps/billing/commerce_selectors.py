from django.conf import settings
from django.utils import timezone
from apps.billing.models import BillingOffer, BillingOrder, Subscription
from apps.billing.commerce import financial_state, validate_offer, CommerceUnavailable
from apps.billing.entitlements import entitlement_summary
from rest_framework.exceptions import ValidationError


def order_projection(order, *, platform=False):
    data = {"id":str(order.pk),"amount":str(order.amount),"currency":order.currency,
        "plan":order.terms["plan_name"],"period_start":order.period_start,"period_end":order.period_end,
        "expires_at":order.expires_at,"created_at":order.created_at,"buyer":order.buyer,
        "seller":{k:v for k,v in order.terms["seller"].items() if k != "account_key"},
        "payment_status":financial_state(order),"application_status":order.application_status,
        "application_code":order.application_code,"applied_at":order.applied_at,
        "attempts":[{"id":str(a.pk),"status":a.status,"failure_code":a.failure_code,
                     **({"checkout_url":a.checkout_url} if not platform and a.status == "pending" else {})}
                    for a in order.attempts.order_by("-created_at")[:10]],
        "receipts":[{"id":r.pk,"source":("bank" if r.source == "bank" else "card"),"amount":str(r.amount),
                     "currency":r.currency,"status":r.status,"received_at":r.received_at,
                     **({"reference":r.reference,"confirmed_by":r.confirmed_by_id,"support_case_id":r.support_case_id,"reason":r.reason} if platform else {})}
                    for r in order.receipts.order_by("-created_at")[:30]],
        "receipt_count":order.receipts.count(),
        "events":[{"kind":e.kind,"code":e.code,"created_at":e.created_at,
                   **({"actor":e.actor_id,"support_case_id":e.support_case_id,"reason":e.reason} if platform else {})}
                  for e in order.events.order_by("-created_at")[:30]]}
    return data


def snapshot(business, *, platform=False, page=1, can_confirm_bank=False):
    enabled = bool(getattr(settings,"BILLING_COMMERCE_ENABLED",False))
    offers=[]
    if enabled:
        rows=BillingOffer.objects.select_related("plan").filter(business=business,is_active=True,expires_at__gt=timezone.now(),
            period_end__gt=timezone.now(),billingorder__isnull=True).order_by("expires_at","pk")[:50]
        for row in rows:
            try:validate_offer(row)
            except (CommerceUnavailable,ValidationError):continue
            offers.append({"id":str(row.pk),"plan":row.plan.name,"amount":str(row.amount),"currency":row.currency,
                           "period_start":row.period_start,"period_end":row.period_end,"expires_at":row.expires_at})
    subscription=Subscription.objects.select_related("plan").filter(business=business).first()
    orders=BillingOrder.objects.filter(business=business).select_related("plan").order_by("-created_at","-pk")
    return {"enabled":enabled,"card_available":enabled and getattr(settings,"BILLING_CARD_ADAPTER",None) is not None,
            "can_confirm_bank":can_confirm_bank,"offers":offers,"count":orders.count(),"page":page,
            "orders":[order_projection(o,platform=platform) for o in orders[(page-1)*10:page*10]],
            "subscription":None if not subscription else {"plan":subscription.plan.name,"status":subscription.status,
                "next_payment_at":subscription.next_payment_at,"technical_entitlements":entitlement_summary(business)},
            "business_status":business.status,"commercial_expiry_enforced":False}
