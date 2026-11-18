from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied, ValidationError
from rest_framework.test import APIClient

from apps.core.domain_errors import InvalidTransition, UnfinishedWork
from apps.scheduling.plan_services import change_plan
from .models import Payment, PlanAllocation
from .plan_balances import plan_money_projection
from .plan_termination import preview_termination
from .tests_plan_payments import PlanPaymentTests


class PlanTerminationTests(TestCase):
    setUpTestData = classmethod(PlanPaymentTests.setUpTestData.__func__)
    plan = PlanPaymentTests.plan
    command = PlanPaymentTests.command
    terms = PlanPaymentTests.terms
    receipt = PlanPaymentTests.receipt
    schedule = PlanPaymentTests.schedule
    complete = PlanPaymentTests.complete

    def close(self, plan, command="terminate", **extra):
        plan.refresh_from_db()
        data = {"consent": True, "reason": "Client declined", **extra}
        data["preview_hash"] = preview_termination(plan, self.owner, command, data)["preview_hash"]
        return self.command(plan, command, data)

    def test_refusal_preserves_other_prices_then_termination_retains_surplus(self):
        plan = self.terms(self.plan(3), amount="90000")
        source = self.receipt(plan, "45000")
        steps = list(plan.steps.all())
        completed = self.schedule(plan, steps[0])
        self.complete(completed)
        future = self.schedule(plan, steps[1])
        with patch("apps.scheduling.services.run_appointment_cancelled_automations") as auto:
            plan = self.close(plan, "refuse-service", step_id=steps[1].pk)
        auto.assert_not_called()
        future.refresh_from_db()
        self.assertEqual(future.status, "cancelled")
        money = plan_money_projection(plan, self.owner)
        self.assertEqual(Decimal(money["terms"]["total"]), 60000)
        self.assertEqual(Decimal(money["remaining"]), 15000)
        self.assertTrue(all(Decimal(line["amount"]) == 30000 for line in money["terms"]["lines"]))
        plan = self.close(plan)
        self.assertIsNotNone(plan.terminated_at)
        money = plan_money_projection(plan, self.owner)
        self.assertEqual(Decimal(money["terms"]["total"]), 30000)
        self.assertEqual(Decimal(money["allocated"]), 30000)
        self.assertEqual(Decimal(money["unallocated"]), 15000)
        self.assertEqual(Decimal(money["remaining"]), 0)
        self.assertEqual(Payment.objects.count(), 1)
        with self.assertRaises(UnfinishedWork):
            self.command(plan, "archive", {"reason": "Close"})
        self.command(plan, "settle-remainder", {"receipt": source.pk, "choice": "refund", "amount": "15000", "consent": True, "reason": "Client requested refund"})
        self.command(plan, "archive", {"reason": "Resolved"})
        plan = self.command(plan, "restore", {"reason": "Inspect history"})
        self.assertIsNotNone(plan.terminated_at)
        with self.assertRaises(InvalidTransition):
            self.command(plan, "revise", {"add": [{"service": self.service}], "reason": "New", "consent": True})

    def test_debt_survives_and_only_exact_remaining_payment_allowed(self):
        plan = self.terms(self.plan(), amount="60000")
        self.receipt(plan, "20000")
        self.complete(self.schedule(plan, plan.steps.first()))
        plan = self.close(plan)
        self.assertEqual(Decimal(plan_money_projection(plan, self.owner)["remaining"]), 10000)
        with self.assertRaises(UnfinishedWork):
            self.command(plan, "archive", {"reason": "Close"})
        with self.assertRaises(ValidationError):
            self.receipt(plan, "10001")
        self.receipt(plan, "10000")
        with self.assertRaises(ValidationError):
            self.receipt(plan, "1")
        self.assertEqual(Decimal(plan_money_projection(plan, self.owner)["remaining"]), 0)

    def test_zero_services_and_separate_retention(self):
        plan = self.terms(self.plan(1), amount="100")
        receipt = self.receipt(plan)
        plan = self.close(plan)
        money = plan_money_projection(plan, self.owner)
        self.assertEqual(money["terms"]["lines"], [])
        self.assertTrue(money["terms_current"])
        self.assertEqual(Decimal(money["unallocated"]), 100)
        self.assertEqual(Decimal(money["retained"]), 0)
        self.command(plan, "settle-remainder", {"receipt": receipt.pk, "choice": "retain", "amount": "100", "consent": True, "reason": "Client keeps credit"})
        self.command(plan, "archive", {"reason": "Resolved"})
        self.close(self.plan(0))

    def test_completed_refusal_and_legacy_remove_bypass_rejected(self):
        plan = self.terms(self.plan())
        step = plan.steps.first()
        self.complete(self.schedule(plan, step))
        with self.assertRaises(InvalidTransition):
            self.close(plan, "refuse-service", step_id=step.pk)
        with self.assertRaises(InvalidTransition):
            self.command(plan, "revise", {"remove": [plan.steps.last().pk], "reason": "Remove", "consent": True})

    def test_stale_balance_consent_rollback_and_replay(self):
        plan = self.terms(self.plan())
        data = {"consent": True, "reason": "Client decision"}
        data["preview_hash"] = preview_termination(plan, self.owner, "terminate", data)["preview_hash"]
        self.receipt(plan)
        with self.assertRaises(InvalidTransition):
            self.command(plan, "terminate", data)
        plan.refresh_from_db()
        data["preview_hash"] = preview_termination(plan, self.owner, "terminate", data)["preview_hash"]
        with self.assertRaises(ValidationError):
            self.command(plan, "terminate", {**data, "consent": False})
        with patch("apps.scheduling.plan_services._effect", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.command(plan, "terminate", data)
        plan.refresh_from_db()
        self.assertIsNone(plan.terminated_at)
        self.assertFalse(plan.steps.filter(removed_at__isnull=False).exists())
        args = dict(plan=plan, actor=self.owner, command="terminate", expected_revision=plan.revision, idempotency_key=str(uuid4()), data=data)
        result, replay = change_plan(**args)
        again, replay = change_plan(**args)
        self.assertTrue(replay)
        self.assertEqual(result.revision, again.revision)

    def test_cancelled_time_rebooks_price_and_earmarked_money_once(self):
        from apps.scheduling.services import apply_appointment_status
        plan = self.terms(self.plan(), amount="150")
        step = plan.steps.first()
        old = self.schedule(plan, step)
        self.receipt(plan, "75", appointment=old.pk)
        apply_appointment_status(appointment=old, actor=self.owner, status_value="cancelled", event_type="appointment_cancelled", text="Cancelled", reason="New time needed")
        plan = self.command(plan, "rebook", {"step_id": step.pk, "consent": True, "reason": "Choose a new time"})
        replacement = plan.steps.get(rebooked_from=step)
        self.assertEqual(Decimal(plan_money_projection(plan, self.owner)["terms"]["total"]), 150)
        self.complete(self.schedule(plan, replacement))
        self.assertEqual(PlanAllocation.objects.get().amount, 75)
        old.refresh_from_db()
        self.assertEqual(old.status, "cancelled")
        with self.assertRaises(InvalidTransition):
            self.command(plan, "rebook", {"step_id": step.pk, "consent": True, "reason": "Duplicate"})

    def test_earmarked_refused_advance_does_not_hide_rendered_debt(self):
        plan = self.terms(self.plan(), amount="150")
        steps = list(plan.steps.all())
        self.complete(self.schedule(plan, steps[0]))
        future = self.schedule(plan, steps[1])
        self.receipt(plan, "100", appointment=future.pk)
        plan = self.close(plan, "refuse-service", step_id=steps[1].pk)
        self.assertEqual(Decimal(plan_money_projection(plan, self.owner)["remaining"]), 75)
        plan = self.close(plan)
        money = plan_money_projection(plan, self.owner)
        self.assertEqual(Decimal(money["remaining"]), 75)
        self.assertEqual(Decimal(money["unallocated"]), 100)

    def test_owner_and_tenant_api_boundary(self):
        from apps.accounts.models import User
        plan = self.terms(self.plan())
        outsider = User.objects.create_user(username="termination-other", email="termination-other@example.test")
        with self.assertRaises(PermissionDenied):
            preview_termination(plan, outsider, "terminate", {})
        api = APIClient()
        api.force_authenticate(outsider)
        url = f"/api/visit-plans/{plan.pk}/preview-correction/terminate/?business={self.business.pk}"
        self.assertIn(api.post(url, {"expected_revision": plan.revision}, format="json").status_code, [403, 404])
        api.force_authenticate(self.owner)
        self.assertEqual(api.post(url, {"expected_revision": plan.revision}, format="json").status_code, 200)

    def test_manager_with_money_grant_cannot_refuse_or_terminate(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        manager = User.objects.create_user(username="plan-termination-manager", role="business_manager")
        role = BusinessRole.objects.get(business=self.business, preset_key="manager")
        BusinessMember.objects.create(business=self.business, user=manager, role="manager", business_role=role)
        RolePermission.objects.update_or_create(business_role=role, resource="payments", action="manage", defaults={"scope": "all"})
        plan = self.terms(self.plan())
        api = APIClient()
        api.force_authenticate(manager)
        for command in ("refuse-service", "terminate"):
            payload = {"expected_revision": plan.revision, "step_id": plan.steps.first().pk, "consent": True, "reason": "Denied"}
            for path in ("preview-correction", "commands"):
                self.assertEqual(api.post(f"/api/visit-plans/{plan.pk}/{path}/{command}/?business={self.business.pk}", payload, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code, 403)

    def test_terminated_payment_cannot_target_an_already_paid_visit(self):
        plan = self.terms(self.plan(3), amount="90000")
        steps = list(plan.steps.all())
        first = self.schedule(plan, steps[0])
        second = self.schedule(plan, steps[1])
        self.complete(first)
        self.complete(second)
        self.receipt(plan, "30000")
        plan = self.close(plan)
        with self.assertRaises(ValidationError):
            self.receipt(plan, "30000", appointment=first.pk)
        self.receipt(plan, "30000", appointment=second.pk)
        self.assertEqual(Decimal(plan_money_projection(plan, self.owner)["remaining"]), 0)

    def test_retained_balance_transfers_to_new_plan_without_new_receipt(self):
        plan = self.terms(self.plan(1), amount="100")
        receipt = self.receipt(plan)
        plan = self.close(plan)
        plan = self.command(plan, "settle-remainder", {"receipt": receipt.pk, "choice": "retain", "amount": "100", "consent": True, "reason": "Future services"})
        target = self.terms(self.plan(1), amount="100")
        self.command(target, "use-credit", {"source_plan": plan.pk, "source_revision": plan.revision, "receipt": receipt.pk, "amount": "100", "reason": "Client agreed new plan", "consent": True})
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(Decimal(plan_money_projection(target, self.owner)["incoming_credit"]), 100)
        self.assertEqual(Decimal(plan_money_projection(plan, self.owner)["unallocated"]), 0)


from django.test import TransactionTestCase, skipUnlessDBFeature
from .tests_plan_concurrency import PlanMoneyConcurrencyTests


@skipUnlessDBFeature("has_select_for_update")
class PlanTerminationConcurrencyTests(TransactionTestCase):
    setUp = PlanMoneyConcurrencyTests.setUp
    parallel = PlanMoneyConcurrencyTests.parallel
    completion = PlanMoneyConcurrencyTests.completion
    refund = PlanMoneyConcurrencyTests.refund
    plan = PlanPaymentTests.plan
    command = PlanPaymentTests.command
    terms = PlanPaymentTests.terms
    receipt = PlanPaymentTests.receipt
    schedule = PlanPaymentTests.schedule
    complete = PlanPaymentTests.complete

    def prepare(self):
        self.current.refresh_from_db()
        data = {"consent": True, "reason": "Client declined"}
        data["preview_hash"] = preview_termination(self.current, self.owner, "terminate", data)["preview_hash"]
        return dict(plan=self.current, actor=self.owner, command="terminate", expected_revision=self.current.revision, idempotency_key=str(uuid4()), data=data)

    def test_termination_against_completion(self):
        args = self.prepare()
        results = self.parallel([lambda: change_plan(**args), self.completion])
        self.assertEqual(sorted(results), [200, 409])
        self.current.refresh_from_db()
        self.visit.refresh_from_db()
        self.assertEqual(self.visit.status, "cancelled" if self.current.terminated_at else "completed")
        self.assertEqual(PlanAllocation.objects.count(), 0 if self.current.terminated_at else 1)

    def test_termination_against_refund_requires_fresh_preview(self):
        args = self.prepare()
        results = self.parallel([lambda: change_plan(**args), self.refund])
        self.assertIn(results[0], [200, 409])
        self.assertEqual(results[1], 200)
        self.source.refresh_from_db()
        self.assertEqual(self.source.refunded_amount, 100)

    def test_same_termination_identity_runs_once(self):
        args = self.prepare()
        revision = self.current.revision
        self.assertEqual(self.parallel([lambda: change_plan(**args)] * 2), [200, 200])
        self.current.refresh_from_db()
        self.assertEqual(self.current.revision, revision + 1)
