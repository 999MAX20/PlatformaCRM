from decimal import Decimal
from django.db import DatabaseError, IntegrityError, transaction
from django.shortcuts import get_object_or_404
from django.views.decorators.cache import never_cache
from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from apps.billing import card_payments
from apps.billing.application import attempt_application, recover
from apps.billing.commerce import audit, create_order, record_bank, merchant_business, operator
from apps.billing.commerce_selectors import snapshot, order_projection
from apps.billing.models import BillingAttempt
from apps.businesses.access import Actions
from apps.businesses.ownership import active_actor
from apps.core.permissions import IsPlatformUser, is_platform_admin
from apps.core.platform_details import StrictFieldsMixin
from apps.core.platform_crm_views import audited_response


class Buyer(StrictFieldsMixin,serializers.Serializer):
    kind=serializers.ChoiceField(choices=["person","company","sole_trader"])
    name=serializers.CharField(max_length=255)
    tax_id=serializers.CharField(max_length=64,allow_blank=True,default="")
    email=serializers.EmailField()

    def validate(self,attrs):
        if attrs["kind"] != "person" and not attrs["tax_id"]:
            raise serializers.ValidationError({"tax_id":"Buyer registration identifier is required."})
        return attrs


class Create(StrictFieldsMixin,serializers.Serializer):
    request_id=serializers.UUIDField()
    offer_id=serializers.UUIDField()
    buyer=Buyer()


class Case(StrictFieldsMixin,serializers.Serializer):
    support_case_id=serializers.IntegerField(min_value=1,max_value=9223372036854775807)
    reason=serializers.CharField(max_length=2000)


class Bank(Case):
    reference=serializers.CharField(max_length=128)
    amount=serializers.DecimalField(max_digits=12,decimal_places=2,min_value=Decimal("0.01"))
    currency=serializers.RegexField(r"^[A-Z]{3}$")
    received_at=serializers.DateTimeField()


class Page(StrictFieldsMixin,serializers.Serializer):
    page=serializers.IntegerField(min_value=1,default=1,max_value=1000000)


def data(serializer,values):
    item=serializer(data=values);item.is_valid(raise_exception=True);return item.validated_data


def mutate(fn):
    try:return Response(fn())
    except IntegrityError:return Response({"detail":"This payment or order has already been recorded.","code":"idempotency_conflict","category":"conflict"},status=409)
    except DatabaseError:return Response({"detail":"Payment records are temporarily unavailable.","code":"temporary_service_failure","category":"temporary"},status=503)


@never_cache
@api_view(["GET","POST"])
@permission_classes([IsAuthenticated])
def merchant_orders(request,business_id):
    if request.method == "GET":
        _,business=merchant_business(request,business_id)
        return Response(snapshot(business,**data(Page,request.query_params)))
    return mutate(lambda:order_projection(create_order(request,business_id,**data(Create,request.data))))


@never_cache
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def merchant_card(request,business_id,order_id,action):
    def run():
        data(StrictEmpty,request.data)
        if action == "checkout":
            card_payments.start_checkout(request,business_id,order_id)
        elif action == "reconcile":
            merchant_business(request,business_id,Actions.MANAGE)
            attempt=get_object_or_404(BillingAttempt.objects.order_by("-created_at"),order_id=order_id,order__business_id=business_id)
            card_payments.reconcile_attempt(attempt.pk)
        else:raise serializers.ValidationError("Unknown payment action.")
        _,business=merchant_business(request,business_id)
        return snapshot(business)
    return mutate(run)


class StrictEmpty(StrictFieldsMixin,serializers.Serializer):
    pass


@never_cache
@api_view(["GET"])
@permission_classes([IsPlatformUser])
def platform_orders(request,business_id):
    actor=active_actor(request)
    params=data(Page,request.query_params)
    return audited_response(request,business_id,"billing_orders",lambda b:snapshot(b,platform=True,can_confirm_bank=is_platform_admin(actor),**params))


@never_cache
@api_view(["POST"])
@permission_classes([IsPlatformUser])
def platform_payment_action(request,business_id,order_id,action):
    def run():
        if action == "confirm-bank":
            values=data(Bank,request.data)
            order=record_bank(request,business_id,order_id,**values)
            order=attempt_application(business_id,order.pk)
        elif action == "recover":
            order=recover(request,business_id,order_id,**data(Case,request.data))
        elif action == "reconcile":
            with transaction.atomic():
                values=data(Case,request.data)
                actor,_,case=operator(request,business_id,values["support_case_id"],values["reason"])
                attempt=get_object_or_404(BillingAttempt.objects.order_by("-created_at"),order_id=order_id,order__business_id=business_id)
                audit(attempt.order,"reconciliation_requested",actor=actor,case=case,reason=values["reason"])
            order=card_payments.reconcile_attempt(attempt.pk)
        else:raise serializers.ValidationError("Unknown payment action.")
        return order_projection(order,platform=True)
    return mutate(run)


class PaymentNotificationThrottle(SimpleRateThrottle):
    rate="60/min"
    def get_cache_key(self,request,view):return "billing-notify:"+self.get_ident(request)


@never_cache
@api_view(["POST"])
@permission_classes([AllowAny])
@throttle_classes([PaymentNotificationThrottle])
def card_notification(request,provider):
    def run():
        card_payments.receive_notification(provider,request.body,dict(request.headers))
        return {"received":True}
    return mutate(run)
