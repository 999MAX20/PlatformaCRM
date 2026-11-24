from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.db.migrations.exceptions import IrreversibleError
from django.test import TransactionTestCase
from apps.medical import tests_reception_models as fixtures
from .models import PurchaseRequest


class ProcurementMigrationTests(TransactionTestCase):
    def test_empty_reverse_and_populated_history_guard(self):
        leaves=MigrationExecutor(connection).loader.graph.leaf_nodes()
        self.addCleanup(lambda:MigrationExecutor(connection).migrate(leaves))
        MigrationExecutor(connection).migrate([("procurement",None)])
        MigrationExecutor(connection).migrate(leaves)
        fixtures.ReceptionRequestIntegrityTests.setUpTestData.__func__(self)
        item=PurchaseRequest.objects.create(business=self.business,branch=self.first,author=self.doctor)
        with self.assertRaisesMessage(IrreversibleError,"Purchase requests exist"):
            MigrationExecutor(connection).migrate([("procurement",None)])
        self.assertTrue(PurchaseRequest.objects.filter(pk=item.pk).exists())
