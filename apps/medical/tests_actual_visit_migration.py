from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
from django.test import TransactionTestCase, override_settings

from . import tests_actual_visits as fixtures
from .models import MedicalActualVisit
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test", MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ActualVisitMigrationTests(TransactionTestCase):
    create = fixtures.ActualVisitTests.create

    def setUp(self):
        fixtures.ActualVisitTests.setUpTestData.__func__(self)
        fixtures.ActualVisitTests.setUp(self)

    def test_empty_roundtrip_and_history_reverse_guard(self):
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(leaves))
        MigrationExecutor(connection).migrate([("medical", "0050_encounter_completion")])
        MigrationExecutor(connection).migrate(leaves)
        self.create()
        proof = MedicalActualVisit.objects.get().evidence_encrypted
        with self.assertRaisesMessage(IrreversibleError, "Actual visit history exists"):
            MigrationExecutor(connection).migrate([("medical", "0050_encounter_completion")])
        self.assertEqual(MedicalActualVisit.objects.get().evidence_encrypted, proof)
