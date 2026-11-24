from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
from django.test import TransactionTestCase, override_settings
from .tests_procurement_prompt import ProcurementPromptTests
from .tests_patient_services import key
from .procurement_prompt import claim_prompt, MedicalProcurementPrompt


@override_settings(MEDICAL_DATA_KEYS={"test":key(7)},MEDICAL_DATA_ACTIVE_KEY_ID="test",MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ProcurementPromptMigrationTests(TransactionTestCase):
    complete=ProcurementPromptTests.complete
    def test_claim_preserved_on_reverse(self):
        leaves=MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda:MigrationExecutor(connection).migrate(leaves))
        MigrationExecutor(connection).migrate([("medical","0056_reception_referring_specialist")])
        MigrationExecutor(connection).migrate(leaves)
        ProcurementPromptTests.setUpTestData.__func__(self)
        ProcurementPromptTests.setUp(self)
        self.complete();claim_prompt(**self.scope)
        with self.assertRaisesMessage(IrreversibleError,"Prompt claims exist"):
            MigrationExecutor(connection).migrate([("medical","0056_reception_referring_specialist")])
        self.assertEqual(MedicalProcurementPrompt.objects.count(),1)
