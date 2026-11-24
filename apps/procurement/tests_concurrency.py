from unittest import skipUnless
from django.db import connection
from django.test import TransactionTestCase, override_settings
from apps.medical.tests_patient_services import key
from apps.medical.tests_order_concurrency import OrderConcurrencyTests
from .tests_requests import PurchaseRequestTests
from .models import PurchaseRequest, PurchaseRequestHistory


@skipUnless(connection.vendor == "postgresql", "Requires PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test":key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class PurchaseConcurrencyTests(TransactionTestCase):
    parallel = OrderConcurrencyTests.parallel
    create = PurchaseRequestTests.create
    change = PurchaseRequestTests.change

    def setUp(self):
        PurchaseRequestTests.setUpTestData.__func__(self)
        PurchaseRequestTests.setUp(self)

    def test_repeated_create_has_one_request_and_history(self):
        results=self.parallel([lambda:self.create()[0].pk,lambda:self.create()[0].pk])
        self.assertEqual(results[0],results[1])
        self.assertEqual(PurchaseRequest.objects.count(),1)
        self.assertEqual(PurchaseRequestHistory.objects.count(),1)

    def test_competing_edit_and_cancel_has_one_winner(self):
        from apps.core.domain_errors import InvalidTransition
        item,_=self.create()
        def change(action):
            try:
                self.change(item,action=action,fields={} if action=="cancel" else self.fields|{"quantity":"15"},idempotency_key=action)
                return "ok"
            except InvalidTransition:
                return "conflict"
        self.assertCountEqual(self.parallel([lambda:change("edit"),lambda:change("cancel")]),["ok","conflict"])
        self.assertEqual(PurchaseRequestHistory.objects.count(),2)
