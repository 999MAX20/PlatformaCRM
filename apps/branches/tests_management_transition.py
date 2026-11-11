from datetime import time

from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.scheduling.models import Resource
from apps.services.models import Service
from .single_location import ensure_initial_location


class ManagementInitialLocationTests(TestCase):
    def test_new_location_is_ordinary_and_later_specialist_has_no_implicit_services(self):
        owner = User.objects.create_user(username="management-onboarding")
        business = Business.objects.create(owner=owner, name="Point", slug="management-onboarding", city="Almaty")
        branch = ensure_initial_location(business)
        self.assertFalse(branch.uses_business_defaults)
        self.assertEqual(branch.city, "Almaty")
        self.assertEqual(ensure_initial_location(business).pk, branch.pk)
        Service.objects.create(business=business, name="Consultation")
        resource = Resource.objects.create(business=business, name="Assistant", profession="Assistant")
        self.assertFalse(branch.specialist_assignments.filter(resource=resource).exists())
        self.assertFalse(branch.service_offers.exists())
        business.address = "Other address"
        business.save(update_fields=["address"])
        branch.refresh_from_db()
        self.assertEqual(branch.address, "")


class ManagementTransitionMigrationTests(TransactionTestCase):
    def test_preserves_legacy_eligibility_hours_and_membership_without_inventing_new_defaults(self):
        before = [("branches", "0005_management_room_options"), ("scheduling", "0014_management_catalog"), ("services", "0003_management_room_options")]
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        executor.migrate(before)
        try:
            loader = MigrationExecutor(connection).loader
            state = loader.project_state(list(loader.applied_migrations)).apps
            UserModel, BusinessModel = state.get_model("accounts", "User"), state.get_model("businesses", "Business")
            owner = UserModel.objects.create(username="management-migration", email="management-migration@example.test")
            business = BusinessModel.objects.create(owner=owner, name="Point", slug="management-migration", city="Almaty")
            branch = state.get_model("branches", "Branch").objects.create(business=business, name="Point", uses_business_defaults=True)
            service = state.get_model("services", "Service").objects.create(business=business, name="Service", duration_minutes=45, price_from=25000)
            resource = state.get_model("scheduling", "Resource").objects.create(business=business, name="Staff")
            room = state.get_model("scheduling", "Resource").objects.create(business=business, name="Room", resource_type="room")
            state.get_model("scheduling", "WorkingHours").objects.create(business=business, weekday=0, start_time=time(9), end_time=time(18))
            member = state.get_model("businesses", "BusinessMember").objects.create(business=business, user=owner, role="owner")
            MigrationExecutor(connection).migrate(leaves)
            current = MigrationExecutor(connection).loader.project_state(leaves).apps
            branch = current.get_model("branches", "Branch").objects.get(pk=branch.pk)
            self.assertFalse(branch.uses_business_defaults)
            self.assertEqual(branch.city, "Almaty")
            offer = current.get_model("branches", "BranchService").objects.get(branch=branch, service_id=service.pk)
            self.assertEqual(offer.duration_minutes, 45)
            self.assertEqual(offer.price_from, 25000)
            assignment = current.get_model("branches", "SpecialistBranch").objects.get(branch=branch, resource_id=resource.pk)
            self.assertEqual(list(assignment.services.values_list("pk", flat=True)), [service.pk])
            day = current.get_model("branches", "ScheduleDay").objects.get(branch=branch, resource_id=resource.pk, weekday=0)
            self.assertEqual(day.intervals, [{"start": "09:00", "end": "18:00"}])
            self.assertEqual(current.get_model("scheduling", "Resource").objects.get(pk=room.pk).branch_id, branch.pk)
            self.assertTrue(current.get_model("branches", "BranchAccess").objects.get(member_id=member.pk).branches.filter(pk=branch.pk).exists())
            self.assertFalse(current.get_model("scheduling", "AppointmentResource").objects.exists())
        finally:
            MigrationExecutor(connection).migrate(leaves)
