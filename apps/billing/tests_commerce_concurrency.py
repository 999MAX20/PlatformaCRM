from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest import skipUnless
from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings
from apps.billing.tests_commerce import CommerceFixture, FakeCard
from apps.billing.application import apply_order
from apps.billing.card_payments import start_checkout, reconcile_attempt
from apps.billing.models import BillingReceipt


@skipUnless(connection.vendor == "postgresql", "Real row locks require PostgreSQL")
@override_settings(BILLING_COMMERCE_ENABLED=True)
class CommerceConcurrencyTests(CommerceFixture,TransactionTestCase):
    def race(self, first, second):
        barrier=Barrier(2)
        def run(fn):
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return fn()
            finally:close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures=[pool.submit(run,fn) for fn in (first,second)]
            return [f.result(timeout=20) for f in futures]

    def test_two_confirmations_and_applications_once(self):
        order=self.order()
        def run():
            self.bank(order)
            return apply_order(self.business.pk,order.pk).application_status
        self.assertEqual(self.race(run,run),["applied","applied"])
        self.assertEqual(BillingReceipt.objects.count(),1)
        self.assertEqual(order.events.filter(kind="application_completed").count(),1)

    def test_duplicate_card_delivery_and_recovery_once(self):
        gateway=FakeCard();order=self.order()
        with override_settings(BILLING_CARD_ADAPTER=gateway):
            attempt=start_checkout(self.request,self.business.pk,order.pk);gateway.settle(attempt)
            def run():return reconcile_attempt(attempt.pk).application_status
            self.assertEqual(self.race(run,run),["applied","applied"])
        self.assertEqual(BillingReceipt.objects.count(),1)
        self.assertEqual(order.events.filter(kind="application_completed").count(),1)

    def test_bank_and_card_do_not_double_period(self):
        gateway=FakeCard();order=self.order()
        with override_settings(BILLING_CARD_ADAPTER=gateway):
            attempt=start_checkout(self.request,self.business.pk,order.pk);gateway.settle(attempt)
            def bank():self.bank(order);return apply_order(self.business.pk,order.pk).application_status
            self.race(bank,lambda:reconcile_attempt(attempt.pk).application_status)
        self.assertEqual(BillingReceipt.objects.count(),2)
        self.assertLessEqual(order.events.filter(kind="application_completed").count(),1)
        self.sub.refresh_from_db()
        self.assertIn(self.sub.next_payment_at,[None,order.period_end])
