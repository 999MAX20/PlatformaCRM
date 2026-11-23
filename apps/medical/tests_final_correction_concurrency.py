from unittest import skipUnless

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
from django.test import TransactionTestCase, override_settings

from .tests_final_document_corrections import FinalDocumentCorrectionTests as fixtures
from .tests_order_concurrency import OrderConcurrencyTests
from .tests_patient_services import key
from .models import MedicalDocumentCorrection


class CorrectionFixture:
    rules, save, prepare = fixtures.rules, fixtures.save, fixtures.prepare
    change, confirm, render = fixtures.change, fixtures.confirm, fixtures.render
    start, advance, finalize = fixtures.start, fixtures.advance, fixtures.finalize
    sign_all, no_signers, correct = fixtures.sign_all, fixtures.no_signers, fixtures.correct

    def setUp(self):
        fixtures.setUpTestData.__func__(self)
        fixtures.setUp(self)
        self.no_signers()
        self.finalize()


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
@skipUnless(connection.vendor == "postgresql", "Correction concurrency requires PostgreSQL row locks")
class FinalCorrectionConcurrencyTests(CorrectionFixture, TransactionTestCase):
    parallel = OrderConcurrencyTests.parallel

    def test_duplicate_request_creates_one_revision(self):
        self.assertCountEqual(self.parallel([lambda: self.correct()[1], lambda: self.correct()[1]]), [False, True])
        self.assertEqual(MedicalDocumentCorrection.objects.count(), 1)

    def test_competing_corrections_cannot_replace_current_version(self):
        self.assertCountEqual(self.parallel([lambda: self.correct()[1],
            lambda: self.correct(idempotency_key="competing")[1]]), [False, "conflict"])
        self.assertEqual(MedicalDocumentCorrection.objects.count(), 1)


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
class FinalCorrectionMigrationTests(CorrectionFixture, TransactionTestCase):
    def test_empty_roundtrip_and_populated_history_guard(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        MigrationExecutor(connection).migrate([("medical", "0051_actual_visit")])
        MigrationExecutor(connection).migrate(leaves)
        self.correct()
        proof = MedicalDocumentCorrection.objects.get().evidence_encrypted
        with self.assertRaisesMessage(IrreversibleError, "Final document corrections exist"):
            MigrationExecutor(connection).migrate([("medical", "0051_actual_visit")])
        self.assertEqual(MedicalDocumentCorrection.objects.get().evidence_encrypted, proof)
