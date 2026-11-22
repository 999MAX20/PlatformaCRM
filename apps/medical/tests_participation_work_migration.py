from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from . import tests_participation_notifications as fixtures
from .models import TreatmentParticipation
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationWorkMigrationTests(TransactionTestCase):
    propose = fixtures.ParticipationNotificationTests.propose

    def test_existing_invitation_retains_source_without_invented_work(self):
        fixtures.ParticipationNotificationTests.setUpTestData.__func__(type(self))
        item, _ = self.propose()
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        target = [("medical", "0017_participation_decline_reason")]
        try:
            executor.migrate(target)
            old = executor.loader.project_state(target).apps.get_model("medical", "TreatmentParticipation")
            previous = old.objects.get(pk=item.pk)
            self.assertEqual(previous.source_appointment_id, self.appointment.pk)
            self.assertEqual(previous.state, "pending")
            MigrationExecutor(connection).migrate(leaves)
            restored = TreatmentParticipation.objects.get(pk=item.pk)
            self.assertEqual(restored.work_direction_encrypted, "")
            self.assertIsNone(restored.planned_work_date)
            self.assertEqual(restored.reason_encrypted, previous.reason_encrypted)
            self.assertEqual(restored.proposed_by_id, previous.proposed_by_id)
        finally:
            MigrationExecutor(connection).migrate(leaves)
