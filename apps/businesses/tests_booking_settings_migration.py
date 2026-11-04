from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase

from apps.accounts.models import User
from apps.businesses.models import Business


class BookingSettingsMigrationTests(TransactionTestCase):
    def test_existing_business_remains_unassigned_and_history_is_preserved(self):
        owner = User.objects.create_user(username="migration-owner", email="migration-owner@example.test")
        business = Business.objects.create(owner=owner, name="Existing business", slug="booking-migration")
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        previous = ("businesses", "0013_employee_access_repair")
        executor.migrate([previous])
        try:
            old = executor.loader.project_state([previous]).apps.get_model("businesses", "Business")
            row = old.objects.get(pk=business.pk)
            self.assertEqual(row.name, "Existing business")
            before = row.created_at
        finally:
            MigrationExecutor(connection).migrate(leaves)
        business.refresh_from_db()
        self.assertIsNone(business.ai_booking_responsible_user_id)
        self.assertEqual(business.created_at, before)
        self.assertEqual(business.owner_id, owner.pk)
