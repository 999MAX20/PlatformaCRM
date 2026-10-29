"""AUD08: real paged reads for async Client consumers, synthetic data only."""
from django.test import TestCase
from rest_framework.test import APIClient
from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client


class ClientSearchPaginationTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="search-owner", email="search-owner@example.invalid")
        cls.actor = User.objects.create_user(username="search-reader", email="search-reader@example.invalid", role="business_operator")
        cls.business = Business.objects.create(owner=cls.owner, name="Search A", slug="search-a")
        cls.other = Business.objects.create(owner=cls.owner, name="Search B", slug="search-b")
        cls.role = BusinessRole.objects.create(business=cls.business, name="Client reader")
        BusinessMember.objects.create(business=cls.business, user=cls.actor, role="operator", business_role=cls.role)
        cls.permission = RolePermission.objects.create(business_role=cls.role, resource="clients", action="view", scope="business")
        cls.old = Client.objects.create(business=cls.business, full_name="Old searchable client", phone="+77015559999", email="old@example.invalid")
        for i in range(105):
            Client.objects.create(business=cls.business, full_name=f"Page client {i:03}")
        cls.hidden = Client.objects.create(business=cls.other, full_name="Old searchable foreign")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def get_page(self, **kwargs):
        response = self.api.get("/api/clients/", {"business": self.business.pk, "page_size": 20, "ordering": "-created_at", **kwargs})
        self.assertEqual(response.status_code, 200, response.data)
        return response.data

    def test_old_record_is_searchable_outside_first_page(self):
        self.assertNotIn(self.old.pk, [row["id"] for row in self.get_page()["results"]])
        for term in ["Old searchable", "77015559999", "old@example.invalid"]:
            with self.subTest(term=term):
                data = self.get_page(q=term)
                self.assertEqual(data["count"], 1)
                self.assertEqual([row["id"] for row in data["results"]], [self.old.pk])

    def test_pagination_visits_all_rows_once(self):
        ids = []
        for page in range(1, 7):
            data = self.get_page(page=page)
            ids.extend(row["id"] for row in data["results"])
            self.assertEqual(bool(data["next"]), page < 6)
        self.assertEqual(len(ids), 106)
        self.assertEqual(len(set(ids)), 106)
        self.assertIn(self.old.pk, ids)
        self.assertNotIn(self.hidden.pk, ids)

    def test_empty_and_invalid_page_are_distinct(self):
        self.assertEqual(self.get_page(q="no-such-synthetic-client")["results"], [])
        self.assertEqual(self.api.get("/api/clients/", {"business": self.business.pk, "page": 999}).status_code, 404)

    def test_selected_old_detail_and_foreign_detail(self):
        response = self.api.get(f"/api/clients/{self.old.pk}/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["full_name"], self.old.full_name)
        self.assertEqual(self.api.get(f"/api/clients/{self.hidden.pk}/").status_code, 404)

    def test_current_read_denial_applies_to_search_and_selected_detail(self):
        self.permission.is_allowed = False
        self.permission.scope = "none"
        self.permission.save()
        response = self.api.get("/api/clients/", {"business": self.business.pk, "q": "Old"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["results"], [])
        self.assertEqual(response.data["count"], 0)
        self.assertEqual(response.data["summary"]["total"], 0)
        self.assertIn(self.api.get(f"/api/clients/{self.old.pk}/").status_code, [403, 404])

    def test_explicit_business_filter_does_not_mix_two_accessible_businesses(self):
        other_role = BusinessRole.objects.create(business=self.other, name="Other reader")
        RolePermission.objects.create(business_role=other_role, resource="clients", action="view", scope="business")
        BusinessMember.objects.create(business=self.other, user=self.actor, role="operator", business_role=other_role)
        data = self.get_page(q="Old")
        self.assertEqual([row["id"] for row in data["results"]], [self.old.pk])
        other = self.get_page(q="Old", business=self.other.pk)
        self.assertEqual([row["id"] for row in other["results"]], [self.hidden.pk])

    def test_malformed_business_filter_is_invalid_input(self):
        for value in ["wrong", "0", "-1", "999999999999999999999999999999"]:
            with self.subTest(value=value):
                self.assertEqual(self.api.get("/api/clients/", {"business": value}).status_code, 400)

    def test_foreign_filter_and_archived_search_remain_empty(self):
        self.assertEqual(self.get_page(business=self.other.pk)["results"], [])
        self.old.is_archived = True
        self.old.save(update_fields=["is_archived"])
        self.assertEqual(self.get_page(q="Old")["results"], [])
