from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from . import tests_document_head_review as fixtures
from .models import MedicalDocumentHeadConfirmation, MedicalDocumentRevision, MedicalAuditEvent
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentHeadMigrationTests(TransactionTestCase):
    def setUp(self):
        fixtures.DocumentHeadReviewTests.setUpTestData.__func__(self)
        fixtures.DocumentHeadReviewTests.setUp(self)
        self.prepare()
        self.leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))

    rules = fixtures.DocumentHeadReviewTests.rules
    save = fixtures.DocumentHeadReviewTests.save
    prepare = fixtures.DocumentHeadReviewTests.prepare
    change = fixtures.DocumentHeadReviewTests.change
    confirm = fixtures.DocumentHeadReviewTests.confirm

    def test_empty_roundtrip_preserves_exact_document_and_allows_confirmation(self):
        encrypted = self.version.snapshot_encrypted
        MigrationExecutor(connection).migrate([("medical", "0044_document_rules")])
        MigrationExecutor(connection).migrate(self.leaves)
        self.assertEqual(MedicalDocumentRevision.objects.get(pk=self.version.pk).snapshot_encrypted, encrypted)
        self.assertFalse(self.confirm()[1])

    def test_confirmed_history_refuses_reverse_even_after_return(self):
        confirmation, _ = self.confirm()
        self.change(target="draft", expected_state_revision=2, reason="Synthetic return", idempotency_key="return")
        with self.assertRaisesMessage(IrreversibleError, "Medical head confirmation history exists"):
            MigrationExecutor(connection).migrate([("medical", "0044_document_rules")])
        self.assertTrue(MedicalDocumentHeadConfirmation.objects.filter(pk=confirmation.pk).exists())
        self.assertEqual(MedicalAuditEvent.objects.filter(action="document_head_confirmed").count(), 1)
