from datetime import datetime, time, timedelta, timezone

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class InitialLocationMigrationTests(TransactionTestCase):
    def test_backfill_preserves_archived_locations_and_reverse_keeps_bookable_history(self):
        previous = ("branches", "0002_branchservice_branchtraveltime_scheduleday_and_more")
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        executor.migrate([previous])
        try:
            executor = MigrationExecutor(connection)
            state = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
            User = state.get_model("accounts", "User")
            Business = state.get_model("businesses", "Business")
            Branch = state.get_model("branches", "Branch")
            owner = User.objects.create(username="location-migration", email="location-migration@example.test")
            business = Business.objects.create(owner=owner, name="Existing single point", slug="single-point-migration", address="Address")
            archived_business = Business.objects.create(owner=owner, name="Archived network", slug="archived-network")
            archived = Branch.objects.create(business=archived_business, name="Closed", is_active=False,
                archived_at=datetime(2020, 1, 1, tzinfo=timezone.utc))
            state.get_model("businesses", "BusinessMember").objects.create(business=business, user=owner, role="owner")
            service = state.get_model("services", "Service").objects.create(business=business, name="Visit", duration_minutes=30, price_from=100)
            resource = state.get_model("scheduling", "Resource").objects.create(business=business, name="Specialist", resource_type="staff")
            state.get_model("scheduling", "WorkingHours").objects.create(business=business, weekday=0, start_time=time(9), end_time=time(18))
            MigrationExecutor(connection).migrate(leaves)
            state = MigrationExecutor(connection).loader.project_state(leaves).apps
            Branch = state.get_model("branches", "Branch")
            primary = Branch.objects.get(business_id=business.pk)
            self.assertTrue(primary.uses_business_defaults)
            self.assertEqual(primary.address, "Address")
            self.assertEqual(Branch.objects.filter(business_id=archived_business.pk).count(), 1)
            self.assertFalse(Branch.objects.get(pk=archived.pk).is_active)
            self.assertFalse(Branch.objects.get(pk=archived.pk).uses_business_defaults)
            client = state.get_model("clients", "Client").objects.create(business_id=business.pk, full_name="History client")
            start = datetime(2030, 1, 7, 12, tzinfo=timezone.utc)
            visit = state.get_model("scheduling", "Appointment").objects.create(business_id=business.pk,
                client_id=client.pk, service_id=service.pk, resource_id=resource.pk, start_at=start,
                end_at=start + timedelta(minutes=30), branch_id=primary.pk, status="confirmed", booked_price=100, booked_duration_minutes=30)
            MigrationExecutor(connection).migrate([previous])
            executor = MigrationExecutor(connection)
            old = executor.loader.project_state(list(executor.loader.applied_migrations)).apps
            self.assertEqual(old.get_model("branches", "Branch").objects.get(pk=primary.pk).name, primary.name)
            self.assertEqual(old.get_model("branches", "BranchService").objects.get(branch_id=primary.pk).price_from, 100)
            self.assertTrue(old.get_model("branches", "SpecialistBranch").objects.filter(branch_id=primary.pk, resource_id=resource.pk).exists())
            day = old.get_model("branches", "ScheduleDay").objects.get(branch_id=primary.pk, resource_id=resource.pk, weekday=0)
            self.assertEqual(day.intervals, [{"start": "09:00", "end": "18:00"}])
            saved = old.get_model("scheduling", "Appointment").objects.get(pk=visit.pk)
            self.assertEqual((saved.branch_id, saved.status, saved.booked_price), (primary.pk, "confirmed", 100))
        finally:
            MigrationExecutor(connection).migrate(leaves)
