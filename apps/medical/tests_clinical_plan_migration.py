from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.businesses.models import Business
from apps.clients.models import Client


class ClinicalPlanMigrationTests(TransactionTestCase):
    def test_empty_tooth_index_roundtrip_preserves_existing_clients(self):
        owner = get_user_model().objects.create_user(username="plan-tooth-migration")
        business = Business.objects.create(owner=owner, name="Synthetic", slug="plan-tooth-migration")
        client = Client.objects.create(business=business, full_name="Synthetic preserved client")
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([("medical", "0031_clinical_plan_visit_links")])
            self.assertNotIn("medical_medicalplantoothlink", connection.introspection.table_names())
            MigrationExecutor(connection).migrate([("medical", "0032_clinical_plan_tooth_links")])
            self.assertIn("medical_medicalplantoothlink", connection.introspection.table_names())
            self.assertTrue(Client.objects.filter(pk=client.pk, business=business).exists())
        finally:
            MigrationExecutor(connection).migrate(leaves)

    def test_empty_link_table_roundtrip_preserves_existing_clients(self):
        owner = get_user_model().objects.create_user(username="plan-link-migration")
        business = Business.objects.create(owner=owner, name="Synthetic", slug="plan-link-migration")
        client = Client.objects.create(business=business, full_name="Synthetic preserved client")
        leaves = MigrationExecutor(connection).loader.graph.leaf_nodes()
        try:
            MigrationExecutor(connection).migrate([("medical", "0030_medical_order_drafts")])
            self.assertNotIn("medical_medicalplansteplink", connection.introspection.table_names())
            MigrationExecutor(connection).migrate([("medical", "0031_clinical_plan_visit_links")])
            self.assertIn("medical_medicalplansteplink", connection.introspection.table_names())
            self.assertTrue(Client.objects.filter(pk=client.pk, business=business).exists())
        finally:
            MigrationExecutor(connection).migrate(leaves)
