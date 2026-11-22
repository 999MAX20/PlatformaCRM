from django.contrib.auth import get_user_model
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.businesses.models import Business
from apps.clients.models import Client
from .models import PatientProfile


class PatientIdentityMigrationTests(TransactionTestCase):
    def test_empty_medical_schema_roundtrip_preserves_existing_crm_without_backfill(self):
        owner = get_user_model().objects.create_user(username="medical-migration")
        business = Business.objects.create(owner=owner, name="Synthetic migration clinic", slug="medical-migration")
        client = Client.objects.create(business=business, full_name="Synthetic existing client", phone="+77000000001")
        identity = (client.pk, client.business_id, client.full_name, client.phone)
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        try:
            executor.migrate([("medical", None)])
            self.assertNotIn("medical_patientprofile", connection.introspection.table_names())
            MigrationExecutor(connection).migrate([("medical", "0001_patient_identity")])
            self.assertFalse(PatientProfile.objects.exists())
            client.refresh_from_db()
            self.assertEqual((client.pk, client.business_id, client.full_name, client.phone), identity)
            MigrationExecutor(connection).migrate([("medical", None)])
            self.assertTrue(Client.objects.filter(pk=client.pk, business=business).exists())
        finally:
            MigrationExecutor(connection).migrate(leaves)
