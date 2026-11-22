from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from . import tests_template_services as fixtures
from .document_templates import read_template_revision
from .models import MedicalDocumentTemplate, MedicalDocumentTemplateRevision
from .template_services import save_personal_template_draft
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class TemplateAvailabilityMigrationTests(TransactionTestCase):
    def test_roundtrip_preserves_existing_versions_and_defaults_active(self):
        fixtures.PersonalTemplateServiceTests.setUpTestData.__func__(type(self))
        version, _ = save_personal_template_draft(actor=self.doctor, business_id=self.business.pk,
            title="Synthetic", text="Synthetic", idempotency_key="migration")
        before = read_template_revision(version)
        encrypted = version.snapshot_encrypted
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        target = [("medical", "0026_credential_confirmation")]
        try:
            executor.migrate(target)
            old = executor.loader.project_state(target).apps.get_model("medical", "MedicalDocumentTemplateRevision")
            self.assertEqual(old.objects.get(pk=version.pk).snapshot_encrypted, encrypted)
            MigrationExecutor(connection).migrate(leaves)
            template = MedicalDocumentTemplate.objects.get(pk=version.template_id)
            self.assertTrue(template.is_active)
            self.assertEqual(template.availability_revision, 0)
            self.assertEqual(read_template_revision(MedicalDocumentTemplateRevision.objects.get(pk=version.pk)), before)
        finally:
            MigrationExecutor(connection).migrate(leaves)
