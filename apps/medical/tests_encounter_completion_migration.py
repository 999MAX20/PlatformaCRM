from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
from django.test import TransactionTestCase, override_settings

from . import tests_encounter_completion as fixtures
from .models import MedicalAuditEvent
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class EncounterCompletionMigrationTests(TransactionTestCase):
    complete = fixtures.EncounterCompletionTests.complete

    def setUp(self):
        fixtures.EncounterCompletionTests.setUpTestData.__func__(self)
        fixtures.EncounterCompletionTests.setUp(self)

    def test_empty_roundtrip_and_completed_history_guard(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        MigrationExecutor(connection).migrate([("medical", "0049_document_finalization")])
        MigrationExecutor(connection).migrate(leaves)
        self.complete()
        with self.assertRaisesMessage(IrreversibleError, "Completed encounters exist"):
            MigrationExecutor(connection).migrate([("medical", "0049_document_finalization")])
        self.assertEqual(MedicalAuditEvent.objects.filter(action="encounter_finalized").count(), 1)
