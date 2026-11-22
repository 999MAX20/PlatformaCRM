from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from . import tests_credential_content as fixtures
from .credential_content import read_credential_revision
from .models import MedicalCredentialRevision
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test")
class CredentialConfirmationMigrationTests(TransactionTestCase):
    def test_roundtrip_preserves_existing_encrypted_history_without_confirmation(self):
        fixtures.CredentialContentTests.setUpTestData.__func__(type(self))
        version = fixtures.CredentialContentTests.append(self)
        before = read_credential_revision(version)
        encrypted = version.content_encrypted
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        target = [("medical", "0025_credential_profiles")]
        try:
            executor.migrate(target)
            old = executor.loader.project_state(target).apps.get_model("medical", "MedicalCredentialRevision")
            self.assertEqual(old.objects.get(pk=version.pk).content_encrypted, encrypted)
            MigrationExecutor(connection).migrate(leaves)
            restored = MedicalCredentialRevision.objects.get(pk=version.pk)
            self.assertIsNone(restored.confirmed_by_id)
            self.assertIsNone(restored.confirmed_at)
            self.assertEqual(read_credential_revision(restored), before)
        finally:
            MigrationExecutor(connection).migrate(leaves)
