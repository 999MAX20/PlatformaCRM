from unittest import skipUnless

from django.db import connection
from django.test import TransactionTestCase, override_settings

from . import tests_document_head_review as fixtures
from . import tests_order_concurrency as concurrency
from .document_head_review import current_review_submission
from .models import MedicalAuditEvent, MedicalDocumentHeadConfirmation
from .tests_patient_services import key


@skipUnless(connection.vendor == "postgresql", "Head review races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentHeadConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.DocumentHeadReviewTests.setUpTestData.__func__(self)
        fixtures.DocumentHeadReviewTests.setUp(self)
        self.prepare()

    rules = fixtures.DocumentHeadReviewTests.rules
    save = fixtures.DocumentHeadReviewTests.save
    prepare = fixtures.DocumentHeadReviewTests.prepare
    change = fixtures.DocumentHeadReviewTests.change
    confirm = fixtures.DocumentHeadReviewTests.confirm
    parallel = concurrency.OrderConcurrencyTests.parallel

    def test_same_command_replays_one_confirmation_and_audit(self):
        self.assertCountEqual(self.parallel([lambda: self.confirm()[1], lambda: self.confirm()[1]]), [False, True])
        self.assertEqual(MedicalDocumentHeadConfirmation.objects.count(), 1)
        self.assertEqual(MedicalAuditEvent.objects.filter(action="document_head_confirmed").count(), 1)

    def test_distinct_commands_cannot_double_confirm(self):
        self.assertCountEqual(self.parallel([lambda: self.confirm(idempotency_key="one")[1],
            lambda: self.confirm(idempotency_key="two")[1]]), [False, "conflict"])
        self.assertEqual(MedicalDocumentHeadConfirmation.objects.count(), 1)

    def test_return_leaves_no_current_confirmation_after_race(self):
        result = self.parallel([lambda: self.confirm()[1], lambda: self.change(target="draft",
            expected_state_revision=2, reason="Synthetic return", idempotency_key="return")[1]])
        self.assertIn(result[0], (False, "conflict"))
        self.assertFalse(result[1])
        self.version.document.refresh_from_db()
        self.assertEqual(self.version.document.state, "draft")
        self.assertIsNone(current_review_submission(self.version))
        self.assertEqual(MedicalDocumentHeadConfirmation.objects.count(), 1 if result[0] is False else 0)
