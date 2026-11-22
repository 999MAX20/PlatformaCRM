from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings

from . import tests_participation_notifications as fixtures
from .models import TreatmentParticipation
from .tests_patient_services import key


@override_settings(MEDICAL_DATA_KEYS={"test": key(7)}, MEDICAL_DATA_ACTIVE_KEY_ID="test",
                   MEDICAL_IDENTITY_INDEX_KEY=key(8))
class ParticipationDeclineMigrationTests(TransactionTestCase):
    propose = fixtures.ParticipationNotificationTests.propose

    def test_existing_decline_keeps_history_without_fabricated_reason(self):
        fixtures.ParticipationNotificationTests.setUpTestData.__func__(type(self))
        item, _ = self.propose()
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        target = [("medical", "0016_participation_notice")]
        try:
            executor.migrate(target)
            old = executor.loader.project_state(target).apps.get_model("medical", "TreatmentParticipation")
            old.objects.filter(pk=item.pk).update(state="declined", revision=2,
                closed_at=item.proposed_at, closed_by_id=self.recipient.pk)
            MigrationExecutor(connection).migrate(leaves)
            restored = TreatmentParticipation.objects.get(pk=item.pk)
            self.assertEqual((restored.state, restored.revision, restored.closed_by_id),
                             ("declined", 2, self.recipient.pk))
            self.assertEqual(restored.decline_reason_encrypted, "")
        finally:
            MigrationExecutor(connection).migrate(leaves)
