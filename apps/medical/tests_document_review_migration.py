from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from . import tests_document_review as fixtures
from .models import MedicalDocument, MedicalDocumentRevision, MedicalDocumentReviewTransition
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentReviewMigrationTests(TransactionTestCase):
    def setUp(self):
        fixtures.DocumentReviewTests.setUpTestData.__func__(self)
        fixtures.DocumentReviewTests.setUp(self)
        self.leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))

    change = fixtures.DocumentReviewTests.change

    def test_empty_review_roundtrip_preserves_draft(self):
        encrypted = self.version.snapshot_encrypted
        MigrationExecutor(connection).migrate([("medical", "0038_document_export_audit_constraints")])
        MigrationExecutor(connection).migrate(self.leaves)
        document = MedicalDocument.objects.get(pk=self.version.document_id)
        self.assertEqual((document.state, document.state_revision), ("draft", 1))
        self.assertEqual(MedicalDocumentRevision.objects.get(pk=self.version.pk).snapshot_encrypted, encrypted)
        self.assertFalse(self.change()[1])

    def test_review_history_blocks_reverse(self):
        item, _ = self.change()
        with self.assertRaisesMessage(IrreversibleError, "Document review history exists"):
            MigrationExecutor(connection).migrate([("medical", "0038_document_export_audit_constraints")])
        self.assertTrue(MedicalDocumentReviewTransition.objects.filter(pk=item.pk).exists())

    def test_confirmation_history_blocks_reverse_even_after_return_to_draft(self):
        self.change()
        item, _ = self.change(target="reviewed", expected_state_revision=2, idempotency_key="confirm")
        self.change(target="draft", expected_state_revision=3, reason="Return", idempotency_key="return")
        with self.assertRaisesMessage(IrreversibleError, "Clinician confirmation history exists"):
            MigrationExecutor(connection).migrate([("medical", "0039_document_review_transitions")])
        self.assertTrue(MedicalDocumentReviewTransition.objects.filter(pk=item.pk, state="reviewed").exists())
