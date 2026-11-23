from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from . import tests_document_rule_snapshots as fixtures
from .document_content import read_document_revision
from .models import MedicalDocumentKind, MedicalDocumentTemplate
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class DocumentRuleMigrationTests(TransactionTestCase):
    def setUp(self):
        fixtures.DocumentRuleSnapshotTests.setUpTestData.__func__(self)
        fixtures.DocumentRuleSnapshotTests.setUp(self)
        self.leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))

    def test_empty_matrix_roundtrip_preserves_document_and_template(self):
        version = fixtures.DocumentRuleSnapshotTests.save(self)
        before = read_document_revision(version)
        target = [("medical", "0043_reception_booking_request")]
        MigrationExecutor(connection).migrate(target)
        MigrationExecutor(connection).migrate(self.leaves)
        self.assertEqual(read_document_revision(version), before)
        self.assertIsNone(MedicalDocumentTemplate.objects.get(pk=self.template.template_id).document_kind_id)

    def test_populated_matrix_blocks_destructive_reverse(self):
        rules = fixtures.DocumentRuleSnapshotTests.rules(self)
        with self.assertRaisesMessage(IrreversibleError, "Document rule history exists"):
            MigrationExecutor(connection).migrate([("medical", "0043_reception_booking_request")])
        self.assertEqual(MedicalDocumentKind.objects.get(pk=rules.kind_id).revision, 1)
        self.assertEqual(MedicalDocumentTemplate.objects.get(pk=self.template.template_id).document_kind_id, rules.kind_id)
