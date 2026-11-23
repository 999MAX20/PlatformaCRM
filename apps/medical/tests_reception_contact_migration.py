from django.db import connection
from django.db.migrations.exceptions import IrreversibleError
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from .models import ReceptionContactAttempt
from . import tests_reception_models as fixtures


class ReceptionContactMigrationTests(TransactionTestCase):
    def setUp(self):
        fixtures.ReceptionRequestIntegrityTests.setUpTestData.__func__(self)
        self.leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda: MigrationExecutor(connection).migrate(self.leaves))

    request = fixtures.ReceptionRequestIntegrityTests.request

    def test_roundtrip_and_populated_reverse_guard(self):
        item = self.request(); item.save()
        MigrationExecutor(connection).migrate([("medical", "0053_document_issuance")])
        MigrationExecutor(connection).migrate(self.leaves)
        item.refresh_from_db(); self.assertEqual(item.contact_cycle, 1)
        attempt = ReceptionContactAttempt.objects.create(request=item, cycle=1, actor=self.doctor,
            outcome="no_answer", note="Synthetic migration contact")
        with self.assertRaisesMessage(IrreversibleError, "Reception contact history exists"):
            MigrationExecutor(connection).migrate([("medical", "0053_document_issuance")])
        self.assertTrue(ReceptionContactAttempt.objects.filter(pk=attempt.pk).exists())
