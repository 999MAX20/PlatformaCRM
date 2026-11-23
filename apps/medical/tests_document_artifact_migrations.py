from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from . import tests_document_artifact_generation as fixtures
from .audit import write_patient_audit
from .document_artifact_content import read_document_artifact_manifest
from .document_content import read_document_revision
from .models import MedicalAuditEvent, MedicalDocumentArtifact, MedicalDocumentRevision
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8), USE_S3=False)
class DocumentArtifactMigrationTests(TransactionTestCase):
    def setUp(self):
        fixtures.DocumentArtifactGenerationTests.setUpTestData.__func__(self)
        fixtures.DocumentArtifactGenerationTests.setUp(self)
        self.leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))

    def test_empty_artifacts_roundtrip_preserves_existing_documents_and_audit(self):
        encrypted = self.version.snapshot_encrypted
        snapshot = read_document_revision(self.version)
        audits = list(MedicalAuditEvent.objects.order_by("pk").values_list("event_id", "action", "document_version_id"))
        target = [("medical", "0035_medical_file_teeth")]
        executor = MigrationExecutor(connection)
        executor.migrate(target)
        old = executor.loader.project_state(target).apps.get_model("medical", "MedicalDocumentRevision")
        self.assertEqual(old.objects.get(pk=self.version.pk).snapshot_encrypted, encrypted)
        MigrationExecutor(connection).migrate(self.leaves)
        self.assertEqual(read_document_revision(MedicalDocumentRevision.objects.get(pk=self.version.pk)), snapshot)
        self.assertEqual(list(MedicalAuditEvent.objects.order_by("pk").values_list("event_id", "action", "document_version_id")), audits)
        self.assertFalse(MedicalDocumentArtifact.objects.exists())
        self.assertIsNotNone(fixtures.DocumentArtifactGenerationTests.prepare(self)[0].pk)

    def test_populated_artifacts_block_destructive_reverse_without_losing_bytes(self):
        item = fixtures.DocumentArtifactGenerationTests.prepare(self)[0]
        manifest = read_document_artifact_manifest(item)
        with item.attachment.file.open("rb") as source:
            before = source.read()
        with self.assertRaisesMessage(IrreversibleError, "Document artifacts exist"):
            MigrationExecutor(connection).migrate([("medical", "0035_medical_file_teeth")])
        MigrationExecutor(connection).migrate(self.leaves)
        restored = MedicalDocumentArtifact.objects.get(pk=item.pk)
        self.assertEqual(read_document_artifact_manifest(restored), manifest)
        with restored.attachment.file.open("rb") as source:
            self.assertEqual(source.read(), before)

    def test_export_audit_blocks_reverse_before_constraints_change(self):
        event = write_patient_audit(actor=self.doctor, business=self.business, patient=self.patient,
            action="document_exported", document_version=self.version)
        with self.assertRaisesMessage(IrreversibleError, "Document export audit exists"):
            MigrationExecutor(connection).migrate([("medical", "0037_document_export_audit")])
        self.assertTrue(MedicalAuditEvent.objects.filter(pk=event.pk, document_version=self.version).exists())
        self.assertTrue(MigrationExecutor(connection).loader.applied_migrations.get(("medical", "0038_document_export_audit_constraints")))
        self.assertIsNotNone(write_patient_audit(actor=self.doctor, business=self.business, patient=self.patient,
            action="document_print_requested", document_version=self.version).pk)
