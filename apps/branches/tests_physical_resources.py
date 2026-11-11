from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.core.models import AuditLog
from apps.scheduling.models import Resource
from apps.scheduling.resource_services import create_resource
from apps.services.models import Service
from .models import BranchAccess, ServiceResourceRequirement
from .physical_resources import save_resource_requirements
from .services import create_branch
from .tests_legacy_fixtures import ensure_legacy_initial_location as ensure_initial_location


class PhysicalResourceConfigurationTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="resource-owner", email="resource-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Business", slug="physical-resources")
        self.branch = ensure_initial_location(self.business)
        self.service = Service.objects.create(business=self.business, name="Service")
        self.room = create_resource(business=self.business, name="Room", resource_type="room")
        self.equipment = create_resource(business=self.business, name="Device", resource_type="equipment")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.url = f"/api/branches/{self.branch.pk}/resource-requirements/"

    def requirements(self, ids, **extra):
        return self.api.post(self.url, {"service": self.service.pk, "resource_ids": ids, **extra}, format="json")

    def test_single_point_resource_creation_assigns_location_without_extra_input(self):
        response = self.api.post("/api/resources/", {"business": self.business.pk,
            "name": "Room two", "resource_type": "room"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["branch"], self.branch.pk)

    def test_exact_requirements_are_idempotent_and_audited(self):
        for _ in range(2):
            response = self.requirements([self.room.pk, self.equipment.pk])
            self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(ServiceResourceRequirement.objects.count(), 2)
        self.assertTrue(AuditLog.objects.filter(metadata__kind="service_resource_requirements").exists())
        configuration = self.api.get(f"/api/branches/{self.branch.pk}/configuration/")
        self.assertEqual(configuration.status_code, 200, configuration.data)
        self.assertEqual(len(configuration.data["physical_resources"]), 2)
        self.assertEqual(len(configuration.data["resource_requirements"]), 2)
        self.assertEqual(configuration.data["offers"][0]["service"], self.service.pk)

    def test_staff_inactive_and_foreign_resources_are_rejected(self):
        staff = create_resource(business=self.business, name="Staff")
        inactive = create_resource(business=self.business, name="Offline", resource_type="equipment", is_active=False)
        other = Business.objects.create(owner=self.owner, name="Other", slug="physical-other")
        foreign = Resource.objects.create(business=other, name="Foreign", resource_type="room")
        for resource in (staff, inactive, foreign):
            with self.subTest(resource=resource.name):
                self.assertEqual(self.requirements([resource.pk]).status_code, 400)
        self.assertFalse(ServiceResourceRequirement.objects.exists())

    def test_service_must_belong_to_business(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="physical-other")
        service = Service.objects.create(business=other, name="Other")
        self.assertEqual(self.requirements([self.room.pk], service=service.pk).status_code, 400)

    def test_second_location_preserves_primary_resources_and_requirements(self):
        self.assertEqual(self.requirements([self.room.pk]).status_code, 200)
        legacy = Resource.objects.create(business=self.business, name="Legacy device", resource_type="equipment")
        second = create_branch(business=self.business, actor=self.owner, name="Second")
        legacy.refresh_from_db()
        self.assertEqual(legacy.branch_id, self.branch.pk)
        self.assertTrue(self.branch.resource_requirements.filter(resource=self.room).exists())
        self.assertFalse(second.resource_requirements.exists())
        self.assertFalse(second.physical_resources.exists())
        self.assertEqual(self.api.post("/api/resources/", {"business": self.business.pk,
            "name": "Unlocated", "resource_type": "room"}, format="json").status_code, 400)
        response = self.api.post("/api/resources/", {"business": self.business.pk,
            "name": "Second room", "resource_type": "room", "branch": second.pk}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(self.requirements([response.data["id"]]).status_code, 400)

    def test_requirement_blocks_move_until_removed(self):
        second = create_branch(business=self.business, actor=self.owner, name="Second")
        self.assertEqual(self.requirements([self.room.pk]).status_code, 200)
        response = self.api.patch(f"/api/resources/{self.room.pk}/", {"branch": second.pk}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(self.requirements([]).status_code, 200)
        response = self.api.patch(f"/api/resources/{self.room.pk}/", {"branch": second.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_role_and_branch_denial(self):
        user = User.objects.create_user(username="limited-resources", email="limited-resources@example.test")
        member = BusinessMember.objects.create(business=self.business, user=user, role="admin")
        BranchAccess.objects.create(member=member)
        self.api.force_authenticate(user)
        self.assertEqual(self.requirements([self.room.pk]).status_code, 403)
        self.assertEqual(self.api.patch(f"/api/resources/{self.room.pk}/", {"name": "No"}, format="json").status_code, 403)
        member.role = "viewer"
        member.save()
        self.assertEqual(self.requirements([self.room.pk]).status_code, 404)
        self.assertFalse(ServiceResourceRequirement.objects.exists())

    def test_foreign_branch_and_staff_location_assignment_are_rejected(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="physical-other")
        foreign = ensure_initial_location(other)
        response = self.api.patch(f"/api/resources/{self.room.pk}/", {"branch": foreign.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        response = self.api.post("/api/resources/", {"business": self.business.pk,
            "name": "Staff", "resource_type": "staff", "branch": self.branch.pk}, format="json")
        self.assertEqual(response.status_code, 400, response.data)

    def test_audit_failure_rolls_back_requirement_changes(self):
        with patch("apps.branches.physical_resources.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                save_resource_requirements(branch=self.branch, actor=self.owner, service_id=self.service.pk, resource_ids=[self.room.pk])
        self.assertFalse(ServiceResourceRequirement.objects.exists())

    def test_setup_state_and_catalog_are_backed_by_current_configuration(self):
        from datetime import time
        from apps.scheduling.models import WorkingHours

        self.assertEqual(self.api.get(f"/api/branches/{self.branch.pk}/").data["setup_state"], "incomplete")
        create_resource(business=self.business, name="Specialist")
        WorkingHours.objects.create(business=self.business, weekday=0, start_time=time(9), end_time=time(18))
        self.assertEqual(self.api.get(f"/api/branches/{self.branch.pk}/").data["setup_state"], "configured")
        self.requirements([self.room.pk])
        catalog = self.api.get(f"/api/branches/{self.branch.pk}/catalog/")
        self.assertEqual(catalog.status_code, 200, catalog.data)
        self.assertEqual(catalog.data["resource_requirements"], [{"service_id": self.service.pk, "resource_id": self.room.pk}])
        second = create_branch(business=self.business, actor=self.owner, name="Second")
        self.assertEqual(self.api.get(f"/api/branches/{second.pk}/").data["setup_state"], "incomplete")
