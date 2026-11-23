from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from .models import ReceptionBookingRequest
from . import tests_reception_models as fixtures


class ReceptionMigrationTests(TransactionTestCase):
    def setUp(self):
        fixtures.ReceptionRequestIntegrityTests.setUpTestData.__func__(self)
        self.leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))

    request = fixtures.ReceptionRequestIntegrityTests.request

    def test_empty_roundtrip_preserves_source_entities(self):
        MigrationExecutor(connection).migrate([("medical", "0042_assistant_invitation_notification")])
        MigrationExecutor(connection).migrate(self.leaves)
        self.patient.refresh_from_db()
        self.appointment.refresh_from_db()
        item = self.request()
        item.full_clean()
        item.save()
        self.assertEqual(item.source_appointment_id, self.appointment.pk)

    def test_request_history_prevents_destructive_reverse(self):
        item = self.request()
        item.save()
        with self.assertRaisesMessage(IrreversibleError, "Reception request history exists"):
            MigrationExecutor(connection).migrate([("medical", "0042_assistant_invitation_notification")])
        self.assertTrue(ReceptionBookingRequest.objects.filter(pk=item.pk).exists())
