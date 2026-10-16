import uuid
from datetime import timedelta
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
import pyotp
from django.db import DatabaseError
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from apps.accounts.models import User, MfaDevice
from apps.accounts.mfa import issue_step_up_token
from apps.integrations.credential_encryption import encrypt_credential_value
from apps.businesses.models import Business, BusinessMember
from apps.billing.models import BillingOffer, BillingOrder, BillingReceipt, Subscription, SubscriptionPlan
from apps.billing.commerce import create_order, record_bank, CommerceUnavailable
from apps.billing.application import apply_order, attempt_application, recover
from apps.core.domain_errors import IdempotencyConflict
from apps.core.models import AuditLog
from apps.support.models import SupportCase


class CommerceFixture:
    def setUp(self):
        self.now = timezone.now()
        self.owner = User.objects.create_user(username="buyer", email="buyer@example.com", role="business_owner")
        self.admin = User.objects.create_user(username="admin", email="admin@example.com", role="platform_admin")
        self.manager = User.objects.create_user(username="manager", email="manager@example.com", role="platform_manager")
        self.business = Business.objects.create(owner=self.owner, name="Billing", slug="billing-order", status="active")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.other = Business.objects.create(owner=self.manager, name="Other", slug="billing-other")
        self.plan, _ = SubscriptionPlan.objects.get_or_create(code="growth", defaults={"name":"Growth"})
        self.sub = Subscription.objects.create(business=self.business, plan=self.plan, status="overdue")
        self.offer = BillingOffer.objects.create(business=self.business, plan=self.plan, amount=Decimal("12000.00"),currency="KZT",
            period_start=self.now-timedelta(hours=1),period_end=self.now+timedelta(days=30),expires_at=self.now+timedelta(days=1),
            approval_reference="TEST ONLY agreed terms",is_active=True,
            seller={"name":"TEST seller", "tax_id":"000000000000", "account_key":"test-account", "bank":"TEST bank", "iban":"TEST-NOT-AN-ACCOUNT", "bic":"TEST"})
        self.case = SupportCase.objects.create(business=self.business,created_by=self.admin,requester=self.owner,source="platform",subject="Payment")
        self.requests = {}
        for person in (self.admin,self.manager):
            secret=pyotp.random_base32()
            MfaDevice.objects.create(user=person, encrypted_secret=encrypt_credential_value(secret),confirmed_at=self.now)
            self.requests[person.pk]=SimpleNamespace(user=person,headers={"X-Zani-MFA-Step-Up":issue_step_up_token(person,pyotp.TOTP(secret).now())})
        self.buyer={"kind":"company", "name":"TEST buyer", "tax_id":"000000000001", "email":"buyer@example.com"}
        self.request=SimpleNamespace(user=self.owner,headers={})

    def order(self):
        return create_order(self.request,self.business.pk,request_id=uuid.uuid4(),offer_id=self.offer.pk,buyer=self.buyer)

    def bank(self, order, **changes):
        values=dict(support_case_id=self.case.pk,reason="Verified TEST bank entry",reference="bank-1",amount=order.amount,
                    currency=order.currency,received_at=self.now)
        values.update(changes)
        return record_bank(self.requests[self.admin.pk],self.business.pk,order.pk,**values)


@override_settings(BILLING_COMMERCE_ENABLED=True)
class CommerceTests(CommerceFixture,TestCase):
    def test_order_terms_and_bank_application_once(self):
        order=self.order(); self.bank(order)
        result=apply_order(self.business.pk,order.pk)
        self.assertEqual(result.application_status,"applied")
        self.sub.refresh_from_db(); self.assertEqual(self.sub.next_payment_at,self.offer.period_end)
        self.assertEqual(self.sub.status,"active")
        self.bank(order); apply_order(self.business.pk,order.pk)
        self.assertEqual(BillingReceipt.objects.count(),1)
        self.assertEqual(order.events.filter(kind="application_completed").count(),1)
        self.assertTrue(AuditLog.objects.filter(metadata__event="application_completed").exists())

    def test_creation_disabled_unapproved_and_expired(self):
        with override_settings(BILLING_COMMERCE_ENABLED=False),self.assertRaises(CommerceUnavailable): self.order()
        self.offer.approval_reference="";self.offer.save()
        with self.assertRaises(CommerceUnavailable):self.order()
        self.offer.approval_reference="test";self.offer.expires_at=self.now-timedelta(seconds=1);self.offer.save()
        with self.assertRaises(ValidationError):self.order()

    def test_order_idempotency_conflict_and_tenant(self):
        order=self.order()
        same=create_order(self.request,self.business.pk,request_id=order.pk,offer_id=self.offer.pk,buyer=self.buyer)
        self.assertEqual(same.pk,order.pk)
        with self.assertRaises(IdempotencyConflict):
            create_order(self.request,self.business.pk,request_id=order.pk,offer_id=self.offer.pk,buyer={**self.buyer,"name":"changed"})
        from django.http import Http404
        with self.assertRaises(Http404):create_order(self.request,self.other.pk,request_id=uuid.uuid4(),offer_id=self.offer.pk,buyer=self.buyer)

    def test_bank_requires_admin_mfa_and_open_same_business_case(self):
        order=self.order();req=self.requests[self.manager.pk]
        with self.assertRaises(PermissionDenied):
            record_bank(req,self.business.pk,order.pk,support_case_id=self.case.pk,reason="test",reference="x",amount=order.amount,currency="KZT",received_at=self.now)
        req=self.requests[self.admin.pk];token=req.headers.pop("X-Zani-MFA-Step-Up")
        from apps.accounts.mfa import MfaStepUpRequired
        with self.assertRaises(MfaStepUpRequired):self.bank(order)
        req.headers["X-Zani-MFA-Step-Up"]=token
        self.case.status="resolved";self.case.resolved_at=self.now;self.case.save()
        with self.assertRaises(ValidationError):self.bank(order)
        self.assertFalse(BillingReceipt.objects.exists())

    def test_amount_currency_and_multiple_receipts_require_review(self):
        order=self.order();self.bank(order,amount=Decimal("100"))
        self.assertEqual(apply_order(self.business.pk,order.pk).application_code,"amount_mismatch")
        self.bank(order,reference="bank-2",amount=Decimal("11900"))
        self.assertEqual(apply_order(self.business.pk,order.pk).application_code,"multiple_payments")
        self.sub.refresh_from_db();self.assertEqual(self.sub.status,"overdue")

    def test_receipt_audit_failure_rolls_back(self):
        order=self.order()
        with patch("apps.billing.commerce.write_actor_audit_log",side_effect=DatabaseError),self.assertRaises(DatabaseError):self.bank(order)
        self.assertFalse(BillingReceipt.objects.exists())

    def test_application_audit_failure_keeps_payment_and_recovery(self):
        order=self.order();self.bank(order)
        with patch("apps.billing.application.audit",side_effect=DatabaseError),self.assertRaises(DatabaseError):apply_order(self.business.pk,order.pk)
        self.sub.refresh_from_db();self.assertEqual(self.sub.status,"overdue")
        self.assertEqual(BillingReceipt.objects.count(),1)
        with patch("apps.billing.application.apply_order",side_effect=DatabaseError):
            self.assertEqual(attempt_application(self.business.pk,order.pk).application_status,"failed")
        result=recover(self.requests[self.manager.pk],self.business.pk,order.pk,support_case_id=self.case.pk,reason="Retry failed activation")
        self.assertEqual(result.application_status,"applied")

    def test_preserve_business_block_and_subscription_pause(self):
        order=self.order();self.bank(order)
        self.business.status="blocked";self.business.save()
        self.assertEqual(apply_order(self.business.pk,order.pk).application_code,"business_restricted")
        self.business.status="active";self.business.save()
        self.sub.status="paused";self.sub.save()
        self.assertEqual(apply_order(self.business.pk,order.pk).application_code,"subscription_restricted")
        self.sub.refresh_from_db();self.assertEqual(self.sub.status,"paused")

    def test_no_current_time_period_reset_or_stale_plan(self):
        order=self.order();self.bank(order)
        self.plan.limits_json={"users":999};self.plan.save()
        self.assertEqual(apply_order(self.business.pk,order.pk).application_code,"plan_changed")
        BillingOrder.objects.filter(pk=order.pk).update(period_end=self.now-timedelta(minutes=1),period_start=self.now-timedelta(days=30))
        self.assertEqual(apply_order(self.business.pk,order.pk).application_code,"period_expired")



class FakeCard:
    """Only registered by isolated tests; never selected by production settings."""
    key="test-card"
    merchant="test-terminal"
    checkout_hosts=frozenset({"payments.example.com"})
    def __init__(self):self.results={};self.calls=0;self.fail=False
    def create_checkout(self,**kw):
        from apps.billing.providers import PaymentResult,Checkout
        self.calls+=1
        self.results[kw["attempt_id"]]=PaymentResult(attempt_id=kw["attempt_id"],order_id=kw["order_id"],
            reference=str(kw["attempt_id"]),amount=kw["amount"],currency=kw["currency"],status="pending",received_at=timezone.now())
        if self.fail:raise TimeoutError("DO NOT LEAK provider secret")
        return Checkout(str(kw["attempt_id"]),"https://payments.example.com/pay/"+str(kw["attempt_id"]))
    def lookup(self,*,attempt_id):return self.results[attempt_id]
    def authenticate_notification(self,*,body,headers):
        import hmac,hashlib
        expected=hmac.new(b"isolated-test-key",body,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(headers.get("X-Test-Signature",""),expected):raise ValueError("not authentic")
        return uuid.UUID(body.decode())
    def settle(self,attempt,status="confirmed",**changes):
        from dataclasses import replace
        self.results[attempt.pk]=replace(self.results[attempt.pk],status=status,**changes)


@override_settings(BILLING_COMMERCE_ENABLED=True)
class CardCommerceTests(CommerceFixture,TestCase):
    def setUp(self):
        super().setUp();self.gateway=FakeCard()
        self.settings_override=override_settings(BILLING_CARD_ADAPTER=self.gateway);self.settings_override.enable();self.addCleanup(self.settings_override.disable)

    def checkout(self):
        from apps.billing.card_payments import start_checkout
        self.item=self.order()
        return start_checkout(self.request,self.business.pk,self.item.pk)

    def test_card_confirm_reconcile_and_duplicate_once(self):
        from apps.billing.card_payments import reconcile_attempt,start_checkout
        attempt=self.checkout()
        self.assertEqual(start_checkout(self.request,self.business.pk,self.item.pk).pk,attempt.pk)
        self.assertEqual(self.gateway.calls,1)
        self.gateway.settle(attempt)
        self.assertEqual(reconcile_attempt(attempt.pk).application_status,"applied")
        reconcile_attempt(attempt.pk)
        self.assertEqual(BillingReceipt.objects.count(),1)
        self.assertEqual(self.item.events.filter(kind="application_completed").count(),1)

    def test_unknown_checkout_does_not_retry_charge(self):
        from apps.billing.card_payments import start_checkout,reconcile_attempt
        self.gateway.fail=True;attempt=self.checkout()
        self.assertEqual(attempt.status,"unknown");self.assertEqual(attempt.checkout_url,"")
        start_checkout(self.request,self.business.pk,self.item.pk)
        self.assertEqual(self.gateway.calls,1)
        self.gateway.settle(attempt)
        self.assertEqual(reconcile_attempt(attempt.pk).application_status,"applied")

    def test_bank_plus_card_is_review_without_double_period(self):
        from apps.billing.card_payments import reconcile_attempt
        from apps.billing.commerce import financial_state
        attempt=self.checkout();self.bank(self.item);apply_order(self.business.pk,self.item.pk)
        self.gateway.settle(attempt);result=reconcile_attempt(attempt.pk)
        self.assertEqual(financial_state(result),"multiple_payments")
        self.assertEqual(self.item.events.filter(kind="application_completed").count(),1)

    def test_refund_before_success_never_grants_and_stale_success_cannot_erase(self):
        from apps.billing.card_payments import reconcile_attempt
        attempt=self.checkout();self.gateway.settle(attempt,"refunded")
        self.assertEqual(reconcile_attempt(attempt.pk).application_code,"refunded")
        self.gateway.settle(attempt,"confirmed")
        self.assertEqual(reconcile_attempt(attempt.pk).application_code,"refunded")
        self.assertEqual(BillingReceipt.objects.get().status,"refunded")

    def test_refund_after_application_preserves_for_manual_policy(self):
        from apps.billing.card_payments import reconcile_attempt
        from apps.billing.commerce import financial_state
        attempt=self.checkout();self.gateway.settle(attempt);reconcile_attempt(attempt.pk)
        self.gateway.settle(attempt,"refunded");result=reconcile_attempt(attempt.pk)
        self.assertEqual(financial_state(result),"refunded");self.assertIsNotNone(result.applied_at)
        self.assertEqual(self.item.events.filter(kind="application_completed").count(),1)

    def test_untrusted_notification_no_receipt(self):
        from apps.billing.card_payments import receive_notification
        attempt=self.checkout()
        with self.assertRaises(PermissionDenied):receive_notification(self.gateway.key,str(attempt.pk).encode(),{})
        self.assertEqual(BillingReceipt.objects.count(),0)

    def test_wrong_order_currency_and_unsafe_checkout(self):
        from apps.billing.card_payments import reconcile_attempt
        attempt=self.checkout();self.gateway.settle(attempt,order_id=uuid.uuid4())
        with self.assertRaises(ValidationError):reconcile_attempt(attempt.pk)
        self.gateway.settle(attempt,order_id=self.item.pk,currency="USD")
        self.assertEqual(reconcile_attempt(attempt.pk).application_code,"amount_mismatch")
        from apps.billing.providers import Checkout,safe_checkout
        with self.assertRaises(CommerceUnavailable):safe_checkout(Checkout("id","https://attacker.example/pay"),self.gateway)

    def test_unconfigured_provider_is_unavailable(self):
        from apps.billing.card_payments import start_checkout
        order=self.order()
        with override_settings(BILLING_CARD_ADAPTER=None),self.assertRaises(CommerceUnavailable):
            start_checkout(self.request,self.business.pk,order.pk)
        self.assertFalse(order.attempts.exists())


@override_settings(BILLING_COMMERCE_ENABLED=True)
class CommerceApiTests(CommerceFixture,TestCase):
    def setUp(self):
        super().setUp()
        from rest_framework.test import APIClient
        self.api=APIClient();self.api.force_authenticate(self.owner)
        self.root=f"/api/billing/businesses/{self.business.pk}/orders/"
        self.platform=f"/api/platform/merchants/{self.business.pk}/billing-orders/"

    def test_create_cannot_override_money_or_read_foreign_business(self):
        values={"request_id":str(uuid.uuid4()),"offer_id":str(self.offer.pk),"buyer":self.buyer}
        self.assertEqual(self.api.post(self.root,{**values,"amount":"1.00"},format="json").status_code,400)
        response=self.api.post(self.root,values,format="json");self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(self.api.get(f"/api/billing/businesses/{self.other.pk}/orders/").status_code,404)
        self.assertEqual(self.api.get(self.platform).status_code,403)

    def test_platform_read_is_audited_and_bank_confirm_applies(self):
        order=self.order();self.api.force_authenticate(self.admin)
        response=self.api.get(self.platform);self.assertEqual(response.status_code,200,response.data)
        self.assertFalse(response.data["commercial_expiry_enforced"])
        self.assertTrue(AuditLog.objects.filter(metadata__resource="billing_orders").exists())
        with patch("apps.core.platform_crm_views.write_audit_log",side_effect=DatabaseError):
            self.assertEqual(self.api.get(self.platform).status_code,503)
        values={"support_case_id":self.case.pk,"reason":"TEST receipt checked","reference":"ref-api","amount":"12000.00","currency":"KZT","received_at":self.now.isoformat()}
        response=self.api.post(f"{self.platform}{order.pk}/confirm-bank/",values,format="json",
            HTTP_X_ZANI_MFA_STEP_UP=self.requests[self.admin.pk].headers["X-Zani-MFA-Step-Up"])
        self.assertEqual(response.status_code,200,response.data)
        self.assertEqual(response.data["application_status"],"applied")

    def test_notification_signature_and_lookup_not_browser_return(self):
        import hmac,hashlib
        from apps.billing.card_payments import start_checkout
        gateway=FakeCard()
        with override_settings(BILLING_CARD_ADAPTER=gateway):
            order=self.order();attempt=start_checkout(self.request,self.business.pk,order.pk);gateway.settle(attempt)
            self.api.force_authenticate(None)
            url="/api/billing/card-notifications/test-card/";body=str(attempt.pk).encode()
            self.assertEqual(self.api.post(url,body,content_type="text/plain").status_code,403)
            signature=hmac.new(b"isolated-test-key",body,hashlib.sha256).hexdigest()
            response=self.api.post(url,body,content_type="text/plain",HTTP_X_TEST_SIGNATURE=signature)
            self.assertEqual(response.status_code,200,response.data)
            order.refresh_from_db();self.assertEqual(order.application_status,"applied")


@override_settings(BILLING_COMMERCE_ENABLED=True)
class CommerceGuardTests(CommerceFixture,TestCase):
    def test_bank_wrong_currency_stale_session_and_foreign_case(self):
        order=self.order()
        User.objects.filter(pk=self.admin.pk).update(auth_epoch=self.admin.auth_epoch+1)
        with self.assertRaises(PermissionDenied):self.bank(order)
        User.objects.filter(pk=self.admin.pk).update(auth_epoch=self.admin.auth_epoch)
        other_case=SupportCase.objects.create(business=self.other,created_by=self.manager,requester=self.manager,source="platform",subject="Other")
        from django.http import Http404
        with self.assertRaises(Http404):self.bank(order,support_case_id=other_case.pk)
        self.bank(order,currency="USD")
        self.assertEqual(apply_order(self.business.pk,order.pk).application_code,"amount_mismatch")

    def test_order_preserves_terms_and_stale_subscription_blocks(self):
        order=self.order();self.offer.amount=Decimal("20000");self.offer.save()
        order.refresh_from_db();self.assertEqual(order.amount,Decimal("12000"))
        self.bank(order);self.sub.next_payment_at=self.now+timedelta(days=100);self.sub.save()
        self.assertEqual(apply_order(self.business.pk,order.pk).application_code,"subscription_changed")

    def test_late_payment_no_invented_period_and_duplicate_reference_conflict(self):
        order=self.order();BillingOrder.objects.filter(pk=order.pk).update(expires_at=self.now-timedelta(minutes=1))
        self.bank(order)
        self.assertEqual(apply_order(self.business.pk,order.pk).application_code,"late_payment")
        with self.assertRaises(IdempotencyConflict):self.bank(order,amount=Decimal("1"))

    def test_sensitive_metadata_absent_from_merchant_and_audit(self):
        from apps.billing.commerce_selectors import order_projection
        import json
        order=self.order();self.bank(order,reference="BANK-PRIVATE-REF",reason="PRIVATE-CASE-DETAIL")
        payload=json.dumps(order_projection(order),default=str)
        self.assertNotIn("BANK-PRIVATE-REF",payload);self.assertNotIn("PRIVATE-CASE-DETAIL",payload)
        self.assertNotIn("test-account",payload)
        logs=json.dumps(list(AuditLog.objects.values_list("metadata",flat=True)))
        self.assertNotIn("BANK-PRIVATE-REF",logs);self.assertNotIn(self.buyer["email"],logs)
