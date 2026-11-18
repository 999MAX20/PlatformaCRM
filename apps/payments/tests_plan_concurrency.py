from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier
from uuid import uuid4

from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.scheduling.models import Appointment
from .tests_plan_payments import PlanPaymentTests
from .models import Payment, PlanAllocation
from .plan_balances import net_allocated, refundable
from .services import record_payment


@skipUnlessDBFeature("has_select_for_update")
class PlanMoneyConcurrencyTests(TransactionTestCase):
    plan = PlanPaymentTests.plan
    command = PlanPaymentTests.command
    terms = PlanPaymentTests.terms
    receipt = PlanPaymentTests.receipt
    schedule = PlanPaymentTests.schedule
    complete = PlanPaymentTests.complete

    def setUp(self):
        PlanPaymentTests.setUpTestData.__func__(type(self))
        self.current = self.terms(self.plan(1), amount="100")
        self.source = self.receipt(self.current)
        self.visit = self.schedule(self.current, self.current.steps.get())

    def parallel(self, operations):
        barrier = Barrier(len(operations))
        def run(operation):
            connections.close_all()
            try:
                barrier.wait(timeout=20)
                try:
                    operation()
                    return 200
                except APIException as error:
                    return error.status_code
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=len(operations)) as pool:
            futures = [pool.submit(run, operation) for operation in operations]
            return [future.result(timeout=60) for future in futures]

    def completion(self):
        self.complete(Appointment.objects.get(pk=self.visit.pk))

    def refund(self):
        record_payment(actor=self.owner, data={"business": self.business.pk, "original": self.source.pk,
            "amount": "100", "method": "cash", "occurred_at": timezone.now(),
            "reason": "Client requested refund", "submission_id": uuid4()})

    def test_complete_against_complete_allocates_once(self):
        self.assertEqual(sorted(self.parallel([self.completion, self.completion])), [200, 409])
        self.assertEqual(PlanAllocation.objects.count(), 1)
        self.assertEqual(net_allocated(PlanAllocation.objects.all()), Decimal(100))

    def test_refund_against_complete_never_overspends(self):
        results = self.parallel([self.refund, self.completion])
        self.assertIn(results[0], [200, 400])
        self.assertEqual(results[1], 200)
        self.source.refresh_from_db()
        allocated = net_allocated(self.source.allocations.all())
        self.assertEqual(self.source.refunded_amount + allocated, Decimal(100))
        self.assertEqual(refundable(self.source), 0)

    def test_two_receipts_with_same_identity_record_once(self):
        self.current.refresh_from_db()
        data = {"business": self.business.pk, "client": self.customer.pk, "plan": self.current.pk,
            "expected_revision": self.current.revision, "amount": "50", "currency": "KZT",
            "method": "cash", "occurred_at": timezone.now(), "submission_id": uuid4()}
        self.assertEqual(self.parallel([lambda: record_payment(actor=self.owner, data=data)] * 2), [200, 200])
        self.assertEqual(Payment.objects.filter(submission_id=data["submission_id"]).count(), 1)

    def test_two_plan_attachments_never_reuse_the_same_legacy_receipt(self):
        from .plan_corrections import preview_correction
        from .models import PlanLegacyAttachment
        from apps.scheduling.plan_services import change_plan
        receipt, _ = record_payment(actor=self.owner, data={"business": self.business.pk,
            "client": self.customer.pk, "amount": "50", "currency": "KZT", "method": "cash",
            "occurred_at": timezone.now(), "submission_id": uuid4()})
        targets = [self.current, self.terms(self.plan(1), amount="100")]
        commands = []
        for target in targets:
            target.refresh_from_db()
            data = {"receipt": receipt.pk, "reason": "Owner verified", "consent": True}
            data["preview_hash"] = preview_correction(target, self.owner, "attach-legacy", data)["preview_hash"]
            commands.append(dict(plan=target, actor=self.owner, command="attach-legacy", data=data,
                expected_revision=target.revision, idempotency_key=str(uuid4())))
        results = self.parallel([lambda args=args: change_plan(**args) for args in commands])
        self.assertEqual(sorted(results), [200, 400])
        self.assertEqual(PlanLegacyAttachment.objects.filter(receipt=receipt).count(), 1)

    def test_annul_against_refund_preserves_receipt_balance(self):
        from .plan_corrections import preview_correction
        from .plan_balances import source_balance
        from .models import PlanCompletionCorrection
        from apps.scheduling.plan_services import change_plan
        self.completion()
        self.current.refresh_from_db()
        data = {"step_id": self.current.steps.get().pk, "reason": "Mistaken completion", "consent": True}
        data["preview_hash"] = preview_correction(self.current, self.owner, "annul-completion", data)["preview_hash"]
        args = dict(plan=self.current, actor=self.owner, command="annul-completion", data=data,
            expected_revision=self.current.revision, idempotency_key=str(uuid4()))
        results = self.parallel([lambda: change_plan(**args), self.refund])
        self.assertEqual(results[0], 200)
        self.assertIn(results[1], [200, 400])
        self.source.refresh_from_db()
        self.assertEqual(net_allocated(self.source.allocations.all()), 0)
        self.assertEqual(self.source.refunded_amount + source_balance(self.current, self.source), 100)
        self.assertEqual(PlanCompletionCorrection.objects.count(), 1)

    def test_legacy_attachment_against_refund_preserves_full_remainder(self):
        from .plan_corrections import preview_correction
        from .plan_balances import source_balance
        from .models import PlanLegacyAttachment
        from apps.scheduling.plan_services import change_plan
        receipt, _ = record_payment(actor=self.owner, data={"business": self.business.pk,
            "client": self.customer.pk, "amount": "50", "currency": "KZT", "method": "cash",
            "occurred_at": timezone.now(), "submission_id": uuid4()})
        self.current.refresh_from_db()
        data = {"receipt": receipt.pk, "reason": "Owner verified", "consent": True}
        data["preview_hash"] = preview_correction(self.current, self.owner, "attach-legacy", data)["preview_hash"]
        args = dict(plan=self.current, actor=self.owner, command="attach-legacy", data=data,
            expected_revision=self.current.revision, idempotency_key=str(uuid4()))
        def refund():
            record_payment(actor=self.owner, data={"business": self.business.pk, "original": receipt.pk,
                "amount": "20", "method": "cash", "occurred_at": timezone.now(),
                "reason": "Client refund", "submission_id": uuid4()})
        results = self.parallel([lambda: change_plan(**args), refund])
        self.assertIn(results[0], [200, 409])
        self.assertEqual(results[1], 200)
        receipt.refresh_from_db()
        self.assertEqual(receipt.refunded_amount, 20)
        if results[0] == 200:
            self.assertEqual(source_balance(self.current, receipt), 30)
        else:
            self.assertFalse(PlanLegacyAttachment.objects.filter(receipt=receipt).exists())
