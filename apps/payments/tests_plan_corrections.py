from decimal import Decimal
from unittest.mock import patch
from uuid import uuid4

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.core.domain_errors import InvalidTransition
from apps.scheduling.plan_services import change_plan
from .models import Payment, PlanAllocation, PlanCompletionCorrection, PlanLegacyAttachment
from .plan_balances import plan_money_projection, source_balance, retained_balance
from .plan_corrections import preview_correction, legacy_options
from .services import record_payment
from .tests_plan_payments import PlanPaymentTests


class PlanCorrectionTests(TestCase):
    setUpTestData = classmethod(PlanPaymentTests.setUpTestData.__func__)
    plan = PlanPaymentTests.plan
    command = PlanPaymentTests.command
    terms = PlanPaymentTests.terms
    receipt = PlanPaymentTests.receipt
    schedule = PlanPaymentTests.schedule
    complete = PlanPaymentTests.complete

    def correction(self, plan, command, **data):
        plan.refresh_from_db()
        data.update(consent=True, reason="Owner verified correction")
        data["preview_hash"] = preview_correction(plan, self.owner, command, data)["preview_hash"]
        return self.command(plan, command, data)

    def legacy(self, **extra):
        return record_payment(actor=self.owner, data={"business": self.business.pk,
            "client": self.customer.pk, "amount": "100", "currency": "KZT", "method": "cash",
            "occurred_at": timezone.now(), "submission_id": uuid4(), **extra})[0]

    def refund(self, receipt, amount="20"):
        return record_payment(actor=self.owner, data={"business": self.business.pk,
            "original": receipt.pk, "amount": amount, "method": "cash", "occurred_at": timezone.now(),
            "reason": "Client refund", "submission_id": uuid4()})[0]

    def completed_plan(self):
        plan = self.terms(self.plan(), amount="150")
        receipt = self.receipt(plan)
        step = plan.steps.first()
        visit = self.schedule(plan, step)
        self.complete(visit)
        return plan, receipt, step, visit

    def test_annul_reverses_and_retains_without_repricing_or_external_effects(self):
        plan, receipt, step, visit = self.completed_plan()
        before_events = ActivityEvent.objects.filter(event_type="appointment_completed").count()
        with patch("apps.scheduling.services.run_appointment_cancelled_automations") as automations, \
             patch("apps.scheduling.services.notify_appointment_responsible") as notify:
            plan = self.correction(plan, "annul-completion", step_id=step.pk)
        automations.assert_not_called()
        notify.assert_not_called()
        visit.refresh_from_db()
        self.assertEqual(visit.status, "cancelled")
        money = plan_money_projection(plan, self.owner)
        self.assertEqual(money["terms"]["total"], "75.00")
        self.assertEqual(Decimal(money["allocated"]), Decimal("0.00"))
        self.assertEqual(Decimal(money["retained"]), 75)
        self.assertEqual(Decimal(money["unallocated"]), 100)
        self.assertEqual(Decimal(money["terms"]["lines"][0]["amount"]), Decimal("75.00"))
        self.assertEqual(Payment.objects.count(), 1)
        self.assertEqual(PlanAllocation.objects.count(), 2)
        self.assertEqual(ActivityEvent.objects.filter(event_type="appointment_completed").count(), before_events)
        self.assertEqual(PlanCompletionCorrection.objects.count(), 1)
        with self.assertRaises(InvalidTransition):
            self.correction(plan, "annul-completion", step_id=step.pk)
        with self.assertRaises(ValidationError):
            self.command(plan, "create-replacement", {"step_id": step.pk})
        self.command(plan, "create-replacement", {"step_id": step.pk, "consent": True, "reason": "New visit agreed"})
        correction = PlanCompletionCorrection.objects.get(step=step)
        self.assertIsNotNone(correction.replacement_id)
        self.assertIsNone(correction.replacement.appointment_id)
        self.assertFalse(plan_money_projection(plan, self.owner)["terms_current"])

    def test_annul_rollback_on_audit_failure(self):
        plan, receipt, step, visit = self.completed_plan()
        with patch("apps.scheduling.plan_services._effect", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.correction(plan, "annul-completion", step_id=step.pk)
        visit.refresh_from_db()
        self.assertEqual(visit.status, "completed")
        self.assertFalse(PlanCompletionCorrection.objects.exists())
        self.assertEqual(PlanAllocation.objects.count(), 1)

    def test_annul_preserves_sent_followups_and_records_reason(self):
        from apps.notifications.models import Notification
        from apps.scheduling.services import APPOINTMENT_THANK_YOU_LABEL
        from apps.core.models import AuditLog
        plan, receipt, step, visit = self.completed_plan()
        rows = [Notification.objects.create(business=self.business, appointment=visit, client=self.customer,
            text="Thank you", send_at=timezone.now(), action_label=APPOINTMENT_THANK_YOU_LABEL, status=status)
            for status in ("pending", "sent")]
        self.correction(plan, "annul-completion", step_id=step.pk)
        for row in rows:
            row.refresh_from_db()
        self.assertEqual([row.status for row in rows], ["cancelled", "sent"])
        event = ActivityEvent.objects.get(event_type="appointment_completion_corrected")
        self.assertEqual(event.metadata["reason"], "Owner verified correction")
        self.assertTrue(AuditLog.objects.filter(metadata__event_type="appointment_completion_corrected",
            metadata__reason="Owner verified correction").exists())

    def test_attachment_rolls_back_and_annul_replay_is_once(self):
        plan, receipt, step, visit = self.completed_plan()
        legacy = self.legacy()
        with patch("apps.scheduling.plan_services._effect", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                self.correction(plan, "attach-legacy", receipt=legacy.pk)
        self.assertFalse(PlanLegacyAttachment.objects.exists())
        plan.refresh_from_db()
        data = {"step_id": step.pk, "reason": "Mistaken completion", "consent": True}
        data["preview_hash"] = preview_correction(plan, self.owner, "annul-completion", data)["preview_hash"]
        args = dict(plan=plan, actor=self.owner, command="annul-completion", data=data,
            expected_revision=plan.revision, idempotency_key=str(uuid4()))
        self.assertFalse(change_plan(**args)[1])
        self.assertTrue(change_plan(**args)[1])
        self.assertEqual(PlanCompletionCorrection.objects.count(), 1)
        self.assertEqual(PlanAllocation.objects.count(), 2)

    def test_attach_preserves_original_and_prior_refunds_and_bounds_new_refund(self):
        plan = self.terms(self.plan(), amount="150")
        receipt = self.legacy()
        old_refund = self.refund(receipt)
        receipt.refresh_from_db()
        snapshot = (receipt.amount, receipt.occurred_at, receipt.created_at, receipt.plan_id, receipt.request_hash)
        plan = self.correction(plan, "attach-legacy", receipt=receipt.pk)
        receipt.refresh_from_db()
        self.assertEqual(snapshot, (receipt.amount, receipt.occurred_at, receipt.created_at, receipt.plan_id, receipt.request_hash))
        self.assertEqual(source_balance(plan, receipt), 80)
        self.assertEqual(Decimal(plan_money_projection(plan, self.owner)["attached"]), Decimal("80"))
        old_refund.refresh_from_db()
        self.assertIsNone(old_refund.plan_id)
        self.refund(receipt, "30")
        self.assertEqual(source_balance(plan, receipt), 50)
        with self.assertRaises(ValidationError):
            self.refund(receipt, "51")
        self.assertEqual(Payment.objects.filter(kind="receipt").count(), 1)
        self.assertEqual(PlanLegacyAttachment.objects.count(), 1)
        with self.assertRaises(ValidationError):
            self.correction(self.plan(), "attach-legacy", receipt=receipt.pk)

    def test_linked_unfinished_legacy_can_be_attached_before_initial_terms(self):
        plan = self.plan(1)
        step = plan.steps.get()
        visit = self.schedule(plan, step)
        receipt = self.legacy(appointment=visit.pk)
        self.refund(receipt, "20")
        with self.assertRaises(ValidationError):
            self.terms(plan, amount="100")
        plan = self.correction(plan, "attach-legacy", receipt=receipt.pk)
        plan = self.terms(plan, amount="100")
        self.complete(visit)
        self.assertEqual(source_balance(plan, receipt), 0)
        self.assertEqual(visit.payment_allocations.get().amount, 80)
        self.assertEqual(Payment.objects.filter(kind="receipt").count(), 1)

    def test_attached_advance_without_terms_blocks_archive_until_decision(self):
        from apps.core.domain_errors import UnfinishedWork
        plan = self.correction(self.plan(1), "attach-legacy", receipt=self.legacy().pk)
        with self.assertRaises(UnfinishedWork):
            self.command(plan, "archive", {"reason": "Stop plan"})
        receipt = PlanLegacyAttachment.objects.get(plan=plan).receipt
        plan = self.command(plan, "settle-remainder", {"receipt": receipt.pk, "amount": "100",
            "choice": "retain", "consent": True, "reason": "Keep for future visits"})
        plan = self.command(plan, "archive", {"reason": "Stop plan"})
        self.assertTrue(plan.is_archived)

    def test_completed_legacy_and_foreign_actor_denied(self):
        plan = self.plan(1)
        visit = self.schedule(plan, plan.steps.get())
        receipt = self.legacy(appointment=visit.pk)
        self.complete(visit)
        self.assertFalse(legacy_options(plan, self.owner).filter(pk=receipt.pk).exists())
        self.refund(receipt, "100")
        with self.assertRaises(ValidationError):
            self.terms(plan, amount="200")
        outsider = User.objects.create_user(username="other-correction-owner")
        with self.assertRaises(PermissionDenied):
            preview_correction(plan, outsider, "attach-legacy", {"receipt": receipt.pk})

    def test_preview_refund_staleness_consent_and_replay(self):
        plan = self.terms(self.plan())
        receipt = self.legacy()
        plan.refresh_from_db()
        data = {"receipt": receipt.pk, "reason": "Verified", "consent": True}
        data["preview_hash"] = preview_correction(plan, self.owner, "attach-legacy", data)["preview_hash"]
        self.refund(receipt)
        with self.assertRaises(InvalidTransition):
            self.command(plan, "attach-legacy", data)
        data["preview_hash"] = preview_correction(plan, self.owner, "attach-legacy", data)["preview_hash"]
        args = dict(plan=plan, actor=self.owner, command="attach-legacy", expected_revision=plan.revision,
            idempotency_key=str(uuid4()), data=data)
        self.assertFalse(change_plan(**args)[1])
        self.assertTrue(change_plan(**args)[1])
        self.assertEqual(PlanLegacyAttachment.objects.count(), 1)

    def test_api_owner_only_even_with_manager_financial_grant(self):
        from rest_framework.test import APIClient
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        manager = User.objects.create_user(username="correction-manager", role="business_manager")
        role = BusinessRole.objects.get(business=self.business, preset_key="manager")
        BusinessMember.objects.create(business=self.business, user=manager, role="manager", business_role=role)
        RolePermission.objects.update_or_create(business_role=role, resource="payments", action="manage", defaults={"scope": "all"})
        plan = self.terms(self.plan())
        receipt = self.legacy()
        api = APIClient()
        api.force_authenticate(manager)
        url = f"/api/visit-plans/{plan.pk}/legacy-payment-options/?business={self.business.pk}"
        self.assertEqual(api.get(url).status_code, 403)
        plan.refresh_from_db()
        denied = {"expected_revision": plan.revision, "receipt": receipt.pk, "reason": "Denied", "consent": True}
        self.assertEqual(api.post(f"/api/visit-plans/{plan.pk}/preview-correction/attach-legacy/?business={self.business.pk}",
            denied, format="json").status_code, 403)
        for command in ("attach-legacy", "annul-completion", "create-replacement"):
            self.assertEqual(api.post(f"/api/visit-plans/{plan.pk}/commands/{command}/?business={self.business.pk}",
                denied, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4())).status_code, 403)
        api.force_authenticate(self.owner)
        self.assertEqual(api.get(url).data["results"][0]["id"], receipt.pk)
        plan.refresh_from_db()
        data = {"expected_revision": plan.revision, "receipt": receipt.pk}
        preview = api.post(f"/api/visit-plans/{plan.pk}/preview-correction/attach-legacy/?business={self.business.pk}", data, format="json")
        self.assertEqual(preview.status_code, 200, preview.data)
        data.update(preview_hash=preview.data["preview_hash"], consent=True, reason="Verified unused advance")
        result = api.post(f"/api/visit-plans/{plan.pk}/commands/attach-legacy/?business={self.business.pk}",
            data, format="json", HTTP_IDEMPOTENCY_KEY=str(uuid4()))
        self.assertEqual(result.status_code, 200, result.data)

    def test_missing_consent_cross_client_currency_and_no_partial_attachment(self):
        from apps.clients.models import Client
        plan = self.terms(self.plan())
        receipt = self.legacy()
        data = {"receipt": receipt.pk, "reason": "Checked"}
        data["preview_hash"] = preview_correction(plan, self.owner, "attach-legacy", data)["preview_hash"]
        with self.assertRaises(ValidationError):
            self.command(plan, "attach-legacy", data)
        with self.assertRaises(ValidationError):
            self.correction(plan, "attach-legacy", receipt=receipt.pk, amount="50")
        receipt.client = Client.objects.create(business=self.business, full_name="Different client")
        receipt.save(update_fields=["client"])
        with self.assertRaises(ValidationError):
            self.correction(plan, "attach-legacy", receipt=receipt.pk)
        receipt.client = self.customer
        receipt.currency = "USD"
        receipt.save(update_fields=["client", "currency"])
        with self.assertRaises(ValidationError):
            self.correction(plan, "attach-legacy", receipt=receipt.pk)
        from apps.businesses.models import Business
        foreign_owner = User.objects.create_user(username="foreign-legacy-owner", email="foreign-legacy@example.test")
        foreign_business = Business.objects.create(owner=foreign_owner, name="Foreign", slug="foreign-legacy")
        receipt.business = foreign_business
        receipt.client = Client.objects.create(business=foreign_business, full_name="Foreign client")
        receipt.currency = "KZT"
        receipt.save(update_fields=["business", "client", "currency"])
        with self.assertRaises(ValidationError):
            self.correction(plan, "attach-legacy", receipt=receipt.pk)
        self.assertFalse(PlanLegacyAttachment.objects.exists())

    def test_cash_report_unchanged_and_completed_service_estimate_removed(self):
        from apps.analytics.financial_metrics import financial_report
        from apps.scheduling.valuation import appointment_price_expression
        from django.db.models import Sum
        self.business.financial_source_mode = "manual"
        self.business.save(update_fields=["financial_source_mode"])
        plan, receipt, step, visit = self.completed_plan()
        day = timezone.now().date()
        before = financial_report(self.business, user=self.owner, start_date=day, end_date=day)
        self.correction(plan, "annul-completion", step_id=step.pk)
        after = financial_report(self.business, user=self.owner, start_date=day, end_date=day)
        self.assertEqual(before["net_receipts"], after["net_receipts"])
        self.assertEqual(before["operation_count"], after["operation_count"])
        self.assertFalse(self.business.appointments.filter(status="completed").exists())
        self.assertIsNone(self.business.appointments.filter(status="completed").aggregate(value=Sum(appointment_price_expression()))["value"])

    def test_earmarked_receipt_retained_then_explicitly_reused_for_replacement(self):
        plan = self.terms(self.plan(1), amount="75")
        step = plan.steps.get()
        visit = self.schedule(plan, step)
        receipt = self.receipt(plan, appointment=visit.pk)
        self.complete(visit)
        plan = self.correction(plan, "annul-completion", step_id=step.pk)
        self.assertEqual(retained_balance(plan, receipt), 100)
        plan = self.command(plan, "create-replacement", {"step_id": step.pk, "consent": True, "reason": "New visit agreed"})
        replacement = PlanCompletionCorrection.objects.get(step=step).replacement
        plan = self.terms(plan, amount="75")
        new_visit = self.schedule(plan, replacement)
        self.complete(new_visit)
        self.assertEqual(retained_balance(plan, receipt), 100)
        self.assertFalse(new_visit.payment_allocations.exists())
        self.command(plan, "settle-remainder", {"receipt": receipt.pk, "amount": "75", "choice": "reuse",
            "reason": "Client approved replacement", "consent": True})
        self.assertEqual(retained_balance(plan, receipt), 25)
        self.assertEqual(new_visit.payment_allocations.get().amount, 75)
        self.assertEqual(Payment.objects.filter(kind="receipt").count(), 1)
