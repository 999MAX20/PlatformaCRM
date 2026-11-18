from datetime import time, timedelta
from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.access import ensure_default_roles
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.models import Resource, WorkingHours
from apps.scheduling.plan_services import change_plan, create_plan
from apps.scheduling.services import apply_appointment_status
from apps.services.models import Service
from .models import Payment, PlanAllocation, PlanTerms
from .plan_balances import plan_money_projection, refundable, source_balance, retained_balance
from .plan_pricing import distribute, preview_terms
from .services import record_payment


class PlanPaymentTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="plan-money", email="plan-money@example.test", role="business_owner")
        cls.business = Business.objects.create(owner=cls.owner, name="Plan money", slug="plan-money", timezone="UTC")
        ensure_default_roles(cls.business)
        cls.customer = Client.objects.create(business=cls.business, full_name="Synthetic client")
        cls.service = Service.objects.create(business=cls.business, name="Consultation", price_from=100, duration_minutes=30)
        cls.specialist = Resource.objects.create(business=cls.business, name="Specialist")
        for day in range(7):
            WorkingHours.objects.create(business=cls.business, weekday=day, start_time=time(8), end_time=time(20))

    def plan(self, count=2):
        return create_plan(business=self.business, actor=self.owner, client=self.customer,
            steps=[{"service": self.service} for _ in range(count)], idempotency_key=str(uuid4()))[0]

    def command(self, plan, command, data, **overrides):
        plan.refresh_from_db()
        return change_plan(plan=plan, actor=self.owner, command=command,
            expected_revision=plan.revision, idempotency_key=str(uuid4()), data=data, **overrides)[0]

    def terms(self, plan, mode="package", amount="150.00", bases=None):
        plan.refresh_from_db()
        data = {"mode": mode, "total": amount, "base_prices": bases or [
            {"step": s.pk, "amount": "100.00"} for s in plan.steps.filter(removed_at__isnull=True)],
            "consent": True, "reason": "Client agreed"}
        data["preview_hash"] = preview_terms(plan, self.owner, data)["preview_hash"]
        return self.command(plan, "accept-terms", data)

    def receipt(self, plan, amount="100.00", **extra):
        plan.refresh_from_db()
        return record_payment(actor=self.owner, data={"business": self.business.pk,
            "client": self.customer.pk, "plan": plan.pk, "expected_revision": plan.revision,
            "amount": amount, "currency": "KZT", "method": "cash", "occurred_at": timezone.now(),
            "submission_id": uuid4(), **extra})[0]

    def schedule(self, plan, step):
        start = (timezone.now() + timedelta(days=3)).replace(hour=10 + step.position, minute=0, second=0, microsecond=0)
        self.command(plan, "schedule", {"step_id": step.pk, "start_at": start,
            "resource": self.specialist, "expected_price": Decimal("100"), "expected_duration_minutes": 30})
        step.refresh_from_db()
        return step.appointment

    def complete(self, appointment):
        return apply_appointment_status(appointment=appointment, actor=self.owner,
            status_value="completed", event_type="appointment_completed", text="Completed",
            reason="Actual visit finished early")

    def test_distribution_exact_and_order_independent(self):
        self.assertEqual(distribute({2: Decimal(200), 1: Decimal(100)}, Decimal(100)), {1: Decimal("33.33"), 2: Decimal("66.67")})
        self.assertEqual(distribute({3: Decimal(1), 2: Decimal(1), 1: Decimal(1)}, Decimal("0.02")),
            {1: Decimal("0.01"), 2: Decimal("0.01"), 3: Decimal(0)})
        with self.assertRaises(ValidationError):
            distribute({1: Decimal(0)}, Decimal(1))

    def test_completion_once_and_refund_cannot_spend_allocation(self):
        plan = self.terms(self.plan())
        receipt = self.receipt(plan)
        visit = self.schedule(plan, plan.steps.first())
        self.complete(visit)
        self.assertEqual(PlanAllocation.objects.get().amount, Decimal(75))
        self.assertEqual(refundable(receipt), Decimal(25))
        with self.assertRaises(InvalidTransition):
            self.complete(visit)
        with self.assertRaises(ValidationError):
            record_payment(actor=self.owner, data={"business": self.business.pk, "original": receipt.pk,
                "amount": "26", "method": "cash", "occurred_at": timezone.now(), "reason": "Refund", "submission_id": uuid4()})
        self.assertEqual(Payment.objects.count(), 1)

    def test_late_payment_settles_debt_not_a_second_receipt(self):
        plan = self.terms(self.plan())
        self.complete(self.schedule(plan, plan.steps.first()))
        self.assertFalse(PlanAllocation.objects.exists())
        receipt = self.receipt(plan, "30")
        self.assertEqual(PlanAllocation.objects.get().amount, Decimal(30))
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(refundable(receipt), Decimal(0))

    def test_completed_price_frozen_and_future_repriced(self):
        plan = self.terms(self.plan())
        self.complete(self.schedule(plan, plan.steps.first()))
        self.terms(plan, amount="200")
        latest = PlanTerms.objects.latest("pk")
        self.assertEqual([Decimal(x["amount"]) for x in latest.lines], [Decimal(75), Decimal(125)])
        with self.assertRaises(ValidationError):
            self.terms(plan, amount="70")

    def test_stale_preview_and_missing_consent(self):
        plan = self.plan()
        data = {"mode": "package", "total": "150", "base_prices": [{"step": s.pk, "amount": "100"} for s in plan.steps.all()]}
        data["preview_hash"] = preview_terms(plan, self.owner, data)["preview_hash"]
        with self.assertRaises(ValidationError):
            self.command(plan, "accept-terms", data)
        data.update(consent=True, reason="Agreed", preview_hash="old")
        with self.assertRaises(InvalidTransition):
            self.command(plan, "accept-terms", data)
        self.assertFalse(PlanTerms.objects.exists())

    def test_retain_transfer_same_client_and_refund(self):
        source = self.terms(self.plan())
        receipt = self.receipt(source)
        self.command(source, "settle-remainder", {"receipt": receipt.pk, "amount": "100",
            "choice": "retain", "consent": True, "reason": "Client chose future visits"})
        target = self.terms(self.plan())
        source.refresh_from_db()
        self.command(target, "use-credit", {"source_plan": source.pk, "source_revision": source.revision,
            "receipt": receipt.pk, "amount": "60", "consent": True, "reason": "Client agreed"})
        self.assertEqual(source_balance(source, receipt), Decimal(40))
        self.assertEqual(source_balance(target, receipt), Decimal(60))
        self.assertEqual(Payment.objects.count(), 1)
        self.command(target, "settle-remainder", {"receipt": receipt.pk, "amount": "20", "choice": "refund",
            "consent": True, "reason": "Client requested refund"})
        receipt.refresh_from_db()
        self.assertEqual(receipt.refunded_amount, Decimal(20))
        self.assertEqual(source_balance(target, receipt), Decimal(40))

    def test_payment_audit_failure_rolls_back_allocations(self):
        plan = self.terms(self.plan())
        self.complete(self.schedule(plan, plan.steps.first()))
        with patch("apps.payments.services.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.receipt(plan)
        self.assertFalse(Payment.objects.exists())
        self.assertFalse(PlanAllocation.objects.exists())

    def test_foreign_actor_cannot_read_money(self):
        plan = self.terms(self.plan())
        other = User.objects.create_user(username="foreign-money", email="foreign-money@example.test", role="business_owner")
        self.assertIsNone(plan_money_projection(plan, other))
        with self.assertRaises(PermissionDenied):
            preview_terms(plan, other, {})

    def test_api_preview_accept_and_read(self):
        plan = self.plan()
        api = APIClient()
        api.force_authenticate(self.owner)
        data = {"expected_revision": plan.revision, "mode": "per_visit", "base_prices": [
            {"step": s.pk, "amount": "100"} for s in plan.steps.all()], "consent": True, "reason": "Agreed"}
        url = f"/api/visit-plans/{plan.pk}"
        preview = api.post(f"{url}/preview-terms/?business={self.business.pk}", data, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        draft = api.post(f"{url}/preview-terms/?business={self.business.pk}", {**data, "reason": "", "consent": False}, format="json")
        self.assertEqual(draft.status_code, 200, draft.data)
        self.assertFalse(PlanTerms.objects.exists())
        data["preview_hash"] = preview.data["preview_hash"]
        response = api.post(f"{url}/commands/accept-terms/?business={self.business.pk}", data,
            format="json", HTTP_IDEMPOTENCY_KEY="terms")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(Decimal(response.data["money"]["terms"]["total"]), Decimal(200))
        replay = api.post(f"{url}/commands/accept-terms/?business={self.business.pk}", data,
            format="json", HTTP_IDEMPOTENCY_KEY="terms")
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertEqual(PlanTerms.objects.count(), 1)

    def test_zero_bases_reject_positive_package_but_allow_free_plan(self):
        plan = self.plan()
        bases = [{"step": s.pk, "amount": "0"} for s in plan.steps.all()]
        with self.assertRaises(ValidationError):
            self.terms(plan, amount="1", bases=bases)
        self.terms(plan, amount="0", bases=bases)
        self.assertEqual(PlanTerms.objects.get().total, 0)
        self.assertFalse(Payment.objects.exists())

    def test_refund_before_retention_does_not_reduce_new_retention(self):
        plan = self.terms(self.plan())
        receipt = self.receipt(plan)
        self.command(plan, "settle-remainder", {"receipt": receipt.pk, "amount": "30", "choice": "refund",
            "consent": True, "reason": "Refund requested"})
        self.command(plan, "settle-remainder", {"receipt": receipt.pk, "amount": "70", "choice": "retain",
            "consent": True, "reason": "Retain remaining funds"})
        self.assertEqual(retained_balance(plan, receipt), Decimal(70))
        self.complete(self.schedule(plan, plan.steps.first()))
        self.assertFalse(PlanAllocation.objects.exists())

    def test_plan_currency_stays_fixed_after_business_currency_changes(self):
        plan = self.terms(self.plan())
        self.business.currency = "USD"
        self.business.save(update_fields=["currency"])
        receipt = self.receipt(plan)
        self.assertEqual(receipt.currency, "KZT")
        with self.assertRaises(ValidationError):
            self.receipt(plan, currency="USD")

    def test_stale_payment_and_idempotent_retry(self):
        plan = self.terms(self.plan())
        data = {"business": self.business.pk, "client": self.customer.pk, "plan": plan.pk,
            "expected_revision": plan.revision, "amount": "100", "currency": "KZT", "method": "cash",
            "occurred_at": timezone.now(), "submission_id": uuid4()}
        first, replay = record_payment(actor=self.owner, data=data)
        second, replay = record_payment(actor=self.owner, data=data)
        self.assertTrue(replay)
        self.assertEqual(first.pk, second.pk)
        with self.assertRaises(InvalidTransition):
            record_payment(actor=self.owner, data={**data, "submission_id": uuid4()})
        self.assertEqual(Payment.objects.count(), 1)

    def test_cancel_does_not_allocate_or_refund_and_archive_requires_decision(self):
        from apps.core.domain_errors import UnfinishedWork
        plan = self.terms(self.plan())
        receipt = self.receipt(plan)
        visit = self.schedule(plan, plan.steps.first())
        apply_appointment_status(appointment=visit, actor=self.owner, status_value="cancelled",
            event_type="appointment_cancelled", text="Cancelled", reason="Client cancelled")
        self.assertFalse(PlanAllocation.objects.exists())
        self.assertEqual(Payment.objects.count(), 1)
        with self.assertRaises(UnfinishedWork):
            self.command(plan, "archive", {"reason": "Cancelled"})
        self.command(plan, "settle-remainder", {"receipt": receipt.pk, "amount": "100", "choice": "retain",
            "consent": True, "reason": "Retain for future"})
        self.command(plan, "archive", {"reason": "Cancelled"})
        plan.refresh_from_db()
        self.assertTrue(plan.is_archived)

    def test_merge_preserves_sources_terms_and_allocations(self):
        from apps.clients.services import merge_clients
        plan = self.terms(self.plan())
        receipt = self.receipt(plan)
        self.complete(self.schedule(plan, plan.steps.first()))
        target = Client.objects.create(business=self.business, full_name="Merge target")
        merge_clients(target_client=target, duplicate_client=self.customer, actor=self.owner)
        plan.refresh_from_db()
        receipt.refresh_from_db()
        self.assertEqual(plan.client_id, target.pk)
        self.assertEqual(receipt.client_id, target.pk)
        self.assertEqual(source_balance(plan, receipt), Decimal(25))
        self.assertEqual(Decimal(plan_money_projection(plan, self.owner)["allocated"]), Decimal(75))

    def test_manager_cannot_refund_or_retain_and_revoked_view_hides_money(self):
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        manager = User.objects.create_user(username="money-manager", role="business_manager")
        role = BusinessRole.objects.get(business=self.business, preset_key="manager")
        BusinessMember.objects.create(business=self.business, user=manager, role="manager", business_role=role)
        plan = self.terms(self.plan())
        receipt = self.receipt(plan)
        with self.assertRaises(PermissionDenied):
            change_plan(plan=plan, actor=manager, command="settle-remainder", expected_revision=plan.revision,
                idempotency_key="manager-retain", data={"receipt": receipt.pk, "amount": "100", "choice": "retain", "reason": "Agreed", "consent": True})
        RolePermission.objects.update_or_create(business_role=role, resource="payments", action="view", defaults={"scope": "none"})
        self.assertIsNone(plan_money_projection(plan, manager))

    def test_credit_transfer_to_another_client_is_rejected(self):
        source = self.terms(self.plan())
        receipt = self.receipt(source)
        self.command(source, "settle-remainder", {"receipt": receipt.pk, "amount": "100", "choice": "retain", "consent": True, "reason": "Future"})
        customer = Client.objects.create(business=self.business, full_name="Other client")
        target = create_plan(business=self.business, actor=self.owner, client=customer,
            steps=[{"service": self.service}], idempotency_key="other-client")[0]
        self.terms(target)
        source.refresh_from_db()
        with self.assertRaises(ValidationError):
            self.command(target, "use-credit", {"source_plan": source.pk, "source_revision": source.revision,
                "receipt": receipt.pk, "amount": "100", "consent": True, "reason": "Wrong client"})
        self.assertEqual(source_balance(source, receipt), Decimal(100))

    def test_existing_unlinked_visit_receipt_requires_reconciliation(self):
        plan = self.plan()
        visit = self.schedule(plan, plan.steps.first())
        receipt, _ = record_payment(actor=self.owner, data={"business": self.business.pk,
            "client": self.customer.pk, "appointment": visit.pk, "amount": "100", "currency": "KZT",
            "method": "cash", "occurred_at": timezone.now(), "submission_id": uuid4()})
        with self.assertRaises(ValidationError):
            self.terms(plan)
        receipt.refresh_from_db()
        self.assertIsNone(receipt.plan_id)
        self.assertFalse(PlanTerms.objects.exists())
