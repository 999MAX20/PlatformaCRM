from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from . import tests_role_services as fixtures
from .models import MedicalRoleAssignment, MedicalRoleRevision
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class MedicalRoleBasisMigrationTests(TransactionTestCase):
    define = fixtures.MedicalRoleServiceTests.define
    assign = fixtures.MedicalRoleServiceTests.assign

    def test_existing_assignment_is_preserved_without_fabricated_decision(self):
        fixtures.MedicalRoleServiceTests.setUpTestData.__func__(type(self))
        role, _ = self.define()
        assignment, _ = self.assign(role)
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        target = [("medical", "0018_participation_work_direction")]
        try:
            executor.migrate(target)
            old = executor.loader.project_state(target).apps.get_model("medical", "MedicalRoleAssignment")
            existing = old.objects.get(pk=assignment.pk)
            self.assertEqual(existing.revision, 1)
            MigrationExecutor(connection).migrate(leaves)
            restored = MedicalRoleAssignment.objects.get(pk=assignment.pk)
            self.assertEqual(restored.business_role_id, role.pk)
            self.assertEqual(list(restored.branches.values_list("pk", flat=True)), [self.branch.pk])
            self.assertFalse(MedicalRoleRevision.objects.exists())
        finally:
            MigrationExecutor(connection).migrate(leaves)
