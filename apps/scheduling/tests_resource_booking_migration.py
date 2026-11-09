from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class PhysicalResourceMigrationTests(TransactionTestCase):
    def test_only_unambiguous_locations_are_backfilled_and_requirements_are_not_invented(self):
        previous = [("branches", "0003_automatic_initial_location"), ("scheduling", "0012_unique_business_working_hours")]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        executor.migrate(previous)
        try:
            executor = MigrationExecutor(connection)
            state = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
            User, Business = state.get_model("accounts", "User"), state.get_model("businesses", "Business")
            Branch, Resource = state.get_model("branches", "Branch"), state.get_model("scheduling", "Resource")
            owner = User.objects.create(username="resource-migration", email="resource-migration@example.test")
            single = Business.objects.create(owner=owner, name="One", slug="resource-migration-one")
            network = Business.objects.create(owner=owner, name="Network", slug="resource-migration-network")
            branch = Branch.objects.create(business=single, name="Primary", uses_business_defaults=True)
            Branch.objects.create(business=network, name="First")
            Branch.objects.create(business=network, name="Second")
            room = Resource.objects.create(business=single, name="Room", resource_type="room")
            staff = Resource.objects.create(business=single, name="Staff", resource_type="staff")
            unknown = Resource.objects.create(business=network, name="Device", resource_type="equipment")
            MigrationExecutor(connection).migrate(leaves)
            state = MigrationExecutor(connection).loader.project_state(leaves).apps
            Resource = state.get_model("scheduling", "Resource")
            self.assertEqual(Resource.objects.get(pk=room.pk).branch_id, branch.pk)
            self.assertIsNone(Resource.objects.get(pk=staff.pk).branch_id)
            self.assertIsNone(Resource.objects.get(pk=unknown.pk).branch_id)
            self.assertFalse(state.get_model("branches", "ServiceResourceRequirement").objects.exists())
            self.assertFalse(state.get_model("scheduling", "AppointmentResource").objects.exists())
            MigrationExecutor(connection).migrate(previous)
            old = MigrationExecutor(connection).loader.project_state(previous).apps
            self.assertEqual(old.get_model("scheduling", "Resource").objects.count(), 3)
        finally:
            MigrationExecutor(connection).migrate(leaves)
