from django.db import connection
from django.contrib.auth import get_user_model
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from apps.businesses.models import Business


class GoogleRetentionMigrationTests(TransactionTestCase):
    def test_existing_disconnected_timestamp_backfill_without_deletion(self):
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        user = get_user_model().objects.create_user(username="migration-retention")
        business = Business.objects.create(owner=user, name="Migration", slug="migration-retention")
        try:
            executor.migrate([("integrations", "0014_google_calendar")])
            old = executor.loader.project_state([("integrations", "0014_google_calendar")]).apps
            Connection = old.get_model("integrations", "GoogleConnection")
            disconnected = Connection.objects.create(business_id=business.pk, actor_id=user.pk, subject="keep-subject")
            connected = Connection.objects.create(business_id=business.pk, actor_id=user.pk,
                provider="google_calendar", status="connected")
            stamp = disconnected.updated_at
            executor = MigrationExecutor(connection)
            executor.migrate([("integrations", "0015_google_retention")])
            current = executor.loader.project_state([("integrations", "0015_google_retention")]).apps
            Connection = current.get_model("integrations", "GoogleConnection")
            result = Connection.objects.get(pk=disconnected.pk)
            self.assertEqual(result.disconnected_at, stamp)
            self.assertEqual(result.subject, "keep-subject")
            self.assertIsNone(Connection.objects.get(pk=connected.pk).disconnected_at)
            self.assertFalse(current.get_model("integrations", "GoogleRetentionFile").objects.exists())
        finally:
            MigrationExecutor(connection).migrate(leaves)
