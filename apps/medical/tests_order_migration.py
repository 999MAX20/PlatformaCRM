from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.businesses.models import Business
from apps.clients.models import Client


class OrderMigrationTests(TransactionTestCase):
    def test_empty_order_schema_roundtrip_preserves_existing_crm(self):
        owner = get_user_model().objects.create_user(username="order-migration")
        business = Business.objects.create(owner=owner, name="Synthetic clinic", slug="order-migration")
        client = Client.objects.create(business=business, full_name="Synthetic existing client")
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("medical", "0029_correction_access")])
            self.assertNotIn("medical_medicalorder", connection.introspection.table_names())
            MigrationExecutor(connection).migrate([("medical", "0030_medical_order_drafts")])
            self.assertIn("medical_medicalorderrevision", connection.introspection.table_names())
            self.assertTrue(Client.objects.filter(pk=client.pk, business=business, full_name=client.full_name).exists())
            MigrationExecutor(connection).migrate([("medical", "0029_correction_access")])
            self.assertTrue(Client.objects.filter(pk=client.pk, business=business).exists())
        finally:
            MigrationExecutor(connection).migrate(leaves)
