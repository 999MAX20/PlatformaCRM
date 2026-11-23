from django.db import connection
from django.test import TransactionTestCase, override_settings
from . import tests_document_finalization as fixtures
from .tests_patient_services import key
from .models import MedicalDocumentFinalization
from unittest import skipUnless
from . import tests_order_concurrency as races


@skipUnless(connection.vendor == "postgresql", "Finalization races require PostgreSQL row locks")
@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
class FinalizationConcurrencyTests(TransactionTestCase):
    parallel = races.OrderConcurrencyTests.parallel
    rules = fixtures.DocumentFinalizationTests.rules
    save = fixtures.DocumentFinalizationTests.save
    prepare = fixtures.DocumentFinalizationTests.prepare
    change = fixtures.DocumentFinalizationTests.change
    confirm = fixtures.DocumentFinalizationTests.confirm
    render = fixtures.DocumentFinalizationTests.render
    start = fixtures.DocumentFinalizationTests.start
    advance = fixtures.DocumentFinalizationTests.advance
    finalize = fixtures.DocumentFinalizationTests.finalize
    no_signers = fixtures.DocumentFinalizationTests.no_signers

    def setUp(self):
        fixtures.DocumentFinalizationTests.setUpTestData.__func__(self)
        fixtures.DocumentFinalizationTests.setUp(self)
        self.no_signers()

    def test_same_command_finalizes_once(self):
        self.assertCountEqual(self.parallel([lambda: self.finalize()[1], lambda: self.finalize()[1]]), [False, True])
        self.assertEqual(MedicalDocumentFinalization.objects.count(), 1)

    def test_distinct_commands_have_one_winner(self):
        self.assertCountEqual(self.parallel([lambda: self.finalize(idempotency_key="one")[1],
            lambda: self.finalize(idempotency_key="two")[1]]), [False, "conflict"])
        self.assertEqual(MedicalDocumentFinalization.objects.count(), 1)

    def test_return_and_finalize_cannot_both_commit(self):
        self.assertCountEqual(self.parallel([lambda: self.finalize()[1], lambda: self.change(
            target="draft", expected_state_revision=3, reason="Synthetic correction", idempotency_key="return")[1]]), [False, "conflict"])
        self.version.document.refresh_from_db()
        self.assertEqual(MedicalDocumentFinalization.objects.count(), 1 if self.version.document.state == "finalized" else 0)
