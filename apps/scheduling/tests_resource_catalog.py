from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.branches.models import Branch, BranchAccess, SpecialistBranch
from apps.scheduling.models import Resource
from apps.services.models import Service
from apps.branches.models import BranchService


class ResourceCatalogTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="catalog-owner", email="catalog@example.test", password="test")
        self.business = Business.objects.create(owner=self.owner, name="Catalog", slug="catalog")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.branch = Branch.objects.create(business=self.business, name="First")
        self.other = Branch.objects.create(business=self.business, name="Second")
        self.staff = Resource.objects.create(business=self.business, name="Specialist", resource_type="staff")
        SpecialistBranch.objects.create(business=self.business, branch=self.branch, resource=self.staff)
        self.room = Resource.objects.create(business=self.business, branch=self.branch, name="Room", resource_type="room")
        self.equipment = Resource.objects.create(business=self.business, branch=self.other, name="Equipment", resource_type="equipment")
        self.client = APIClient()
        self.client.force_authenticate(self.owner)

    def rows(self, **params):
        response = self.client.get("/api/resources/", {"business": self.business.id, **params})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_group_pagination_and_search(self):
        data = self.rows(resource_group="physical", page_size=1)
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["results"]), 1)
        self.assertEqual(data["summary"]["staff"], 0)
        self.assertEqual(self.rows(resource_group="staff")["results"][0]["id"], self.staff.id)
        self.assertEqual(self.rows(resource_group="physical", search="Specialist")["count"], 0)

    def test_branch_assignments_and_physical_location(self):
        data = self.rows(branch=self.branch.id)
        self.assertEqual({row["id"] for row in data["results"]}, {self.staff.id, self.room.id})
        self.assertEqual(self.rows(branch=self.other.id, resource_group="staff")["count"], 0)
        self.assertEqual(self.rows(branch=self.branch.id, resource_group="physical")["count"], 1)

    def test_invalid_and_foreign_filters(self):
        for params in ({"resource_group": "invalid"}, {"branch": "not-an-id"}):
            self.assertEqual(self.client.get("/api/resources/", params).status_code, 400)
        foreign = Business.objects.create(owner=self.owner, name="Other business", slug="other-catalog")
        branch = Branch.objects.create(business=foreign, name="Foreign")
        Resource.objects.create(business=foreign, branch=branch, name="Private", resource_type="room")
        self.assertEqual(self.rows(branch=branch.id)["count"], 0)

    def test_unauthenticated_denied(self):
        self.client.force_authenticate(None)
        self.assertIn(self.client.get("/api/resources/", {"resource_group": "physical"}).status_code, (401, 403))

    def test_branch_grant_does_not_expand_scope(self):
        admin = User.objects.create_user(username="catalog-admin", email="catalog-admin@example.test")
        member = BusinessMember.objects.create(business=self.business, user=admin, role="admin")
        grant = BranchAccess.objects.create(member=member)
        grant.branches.add(self.branch)
        self.client.force_authenticate(admin)
        self.assertEqual(self.rows(branch=self.branch.id, resource_group="physical")["count"], 1)
        response = self.client.get("/api/resources/", {"business": self.business.id, "branch": self.other.id})
        self.assertEqual(response.status_code, 403)

    def test_automatic_branch_includes_unassigned_specialists(self):
        Branch.objects.filter(pk=self.branch.pk).update(uses_business_defaults=True)
        unassigned = Resource.objects.create(business=self.business, name="Unassigned", resource_type="staff")
        ids = {row["id"] for row in self.rows(branch=self.branch.id, resource_group="staff")["results"]}
        self.assertEqual(ids, {self.staff.id, unassigned.id})

    def test_automatic_branch_without_business_filter_stays_in_business(self):
        Branch.objects.filter(pk=self.branch.pk).update(uses_business_defaults=True)
        legacy_room = Resource.objects.create(business=self.business, name="Legacy room", resource_type="room")
        other = Business.objects.create(owner=self.owner, name="Owned other", slug="catalog-owned-other")
        Resource.objects.create(business=other, name="Other staff", resource_type="staff")
        Resource.objects.create(business=other, name="Other room", resource_type="room")
        response = self.client.get("/api/resources/", {"branch": self.branch.id})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({row["id"] for row in response.data["results"]}, {self.staff.id, self.room.id, legacy_room.id})

    def test_service_catalog_branch_and_global(self):
        offered = Service.objects.create(business=self.business, name="Offered")
        Service.objects.create(business=self.business, name="Global")
        BranchService.objects.create(business=self.business, branch=self.branch, service=offered, duration_minutes=30)
        response = self.client.get("/api/services/", {"business": self.business.id, "branch": self.branch.id})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data["results"]], [offered.id])
        self.assertEqual(self.client.get("/api/services/", {"business": self.business.id}).data["count"], 2)
        Branch.objects.filter(pk=self.other.pk).update(uses_business_defaults=True)
        self.assertEqual(self.client.get("/api/services/", {"business": self.business.id, "branch": self.other.id}).data["count"], 2)

    def test_service_branch_scope_invalid_and_foreign(self):
        admin = User.objects.create_user(username="service-admin", email="service-admin@example.test")
        member = BusinessMember.objects.create(business=self.business, user=admin, role="admin")
        grant = BranchAccess.objects.create(member=member)
        grant.branches.add(self.branch)
        self.client.force_authenticate(admin)
        self.assertEqual(self.client.get("/api/services/", {"business": self.business.id, "branch": self.other.id}).status_code, 403)
        self.assertEqual(self.client.get("/api/services/", {"branch": "invalid"}).status_code, 400)
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="service-foreign")
        branch = Branch.objects.create(business=foreign, name="Foreign")
        self.assertEqual(self.client.get("/api/services/", {"business": self.business.id, "branch": branch.id}).data["count"], 0)
