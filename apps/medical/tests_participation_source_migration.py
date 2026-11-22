from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from . import tests_participation_services as fixtures
from .models import TreatmentParticipation


class ParticipationSourceMigrationTests(TransactionTestCase):
    def test_existing_proposal_survives_roundtrip_without_invented_source(self):
        fixtures.ParticipationCommandTests.setUpTestData.__func__(type(self))
        item = TreatmentParticipation.objects.create(patient=self.patient, member=self.target,
            branch=self.first, proposed_by=self.doctor, reason_encrypted="opaque-existing-value")
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("medical", "0014_participation_closure")])
            executor = MigrationExecutor(connection)
            old_model = executor.loader.project_state(
                [("medical", "0014_participation_closure")]).apps.get_model("medical", "TreatmentParticipation")
            previous = old_model.objects.get(pk=item.pk)
            self.assertEqual(previous.reason_encrypted, "opaque-existing-value")
            executor.migrate([("medical", "0015_participation_source")])
            migrated_model = executor.loader.project_state(
                [("medical", "0015_participation_source")]).apps.get_model("medical", "TreatmentParticipation")
            item = migrated_model.objects.get(pk=item.pk)
            self.assertEqual((item.state, item.revision, item.reason_encrypted),
                             ("pending", 1, "opaque-existing-value"))
            self.assertIsNone(item.source_appointment_id)
            self.assertIsNone(item.source_participation_id)
            self.appointment.refresh_from_db()
            self.assertEqual(self.appointment.client_id, self.patient.client_id)
        finally:
            MigrationExecutor(connection).migrate(leaves)
