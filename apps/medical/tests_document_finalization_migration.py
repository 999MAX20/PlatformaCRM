from django.db import connection
from django.test import TransactionTestCase, override_settings
from . import tests_document_finalization as fixtures
from .tests_patient_services import key
from .models import MedicalDocumentFinalization
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
    MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False, MEDICAL_SYNTHETIC_SIGNING_ENABLED=True, ENVIRONMENT="test")
class FinalizationMigrationTests(TransactionTestCase):
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

    def test_empty_roundtrip_and_populated_reverse_guard(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        MigrationExecutor(connection).migrate([("medical", "0048_document_signing_sessions")])
        MigrationExecutor(connection).migrate(leaves)
        item, _ = self.finalize()
        with self.assertRaisesMessage(IrreversibleError, "Finalized documents exist"):
            MigrationExecutor(connection).migrate([("medical", "0048_document_signing_sessions")])
        self.assertEqual(MedicalDocumentFinalization.objects.get(pk=item.pk).evidence_encrypted, item.evidence_encrypted)
