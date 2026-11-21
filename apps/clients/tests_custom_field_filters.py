from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.core.models import CustomFieldDefinition, CustomFieldValue


class ClientCustomFilterTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="filter-owner", email="filter-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Filters", slug="filters")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.clients = [Client.objects.create(business=self.business, full_name=f"Filter {i}", source="manual") for i in range(3)]

    def field(self, kind, values):
        field = CustomFieldDefinition.objects.create(business=self.business, key=kind, label=kind,
            entity_type="client", field_type=kind,
            options_json={"display": {"in_filters": True}, "options": ["A", "B"]})
        for client, value in zip(self.clients, values):
            CustomFieldValue.objects.create(business=self.business, definition=field, entity_type="client",
                entity_id=str(client.pk), value_json={"value": value})
        return field

    def query(self, field, **params):
        return self.api.get("/api/clients/", {"business": self.business.pk, "workspace": "true",
            "source": "manual", "archive": "active", "custom_field": field.pk,
            "custom_operator": "equals", "custom_value": "A", "page_size": 1, **params})

    def test_typed_filters_summary_pagination_and_standard_conditions(self):
        for kind, values, operator, value in [
            ("text", ["Alpha", "Alpine"], "contains", "Al"),
            ("number", ["12", "20"], "gte", "10"),
            ("select", ["A", "A"], "equals", "A"),
            ("date", ["2026-11-20", "2026-11-21"], "lte", "2026-11-21"),
        ]:
            field = self.field(kind, values)
            response = self.query(field, custom_operator=operator, custom_value=value)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["count"], 2)
            self.assertEqual(response.data["summary"]["total"], 2)
            self.assertEqual(len(response.data["results"]), 1)
            second = self.query(field, custom_operator=operator, custom_value=value, page=2)
            self.assertEqual(second.status_code, 200, second.data)
            self.assertNotEqual(response.data["results"][0]["id"], second.data["results"][0]["id"])
            empty = self.query(field, custom_operator="is_empty")
            self.assertEqual(empty.data["count"], 1)
            self.assertEqual(empty.data["results"][0]["id"], self.clients[2].pk)
            none = self.query(field, custom_operator=operator, custom_value=value, source="website")
            self.assertEqual(none.data["count"], 0)
            self.assertEqual(none.data["summary"]["total"], 0)

    def test_unavailable_field_ids_and_invalid_values_are_rejected(self):
        field = self.field("select", ["A"])
        self.assertEqual(self.query(field, custom_value="invalid").status_code, 400)
        self.assertEqual(self.query(field, custom_operator="gte").status_code, 400)
        field.is_active = False
        field.save()
        self.assertEqual(self.query(field).status_code, 403)
        field.is_active = True
        field.options_json = {"display": {"in_filters": False}, "options": ["A"]}
        field.save()
        self.assertEqual(self.query(field).status_code, 400)
        field.options_json["display"]["in_filters"] = True
        field.permissions_json = {"view_roles": ["owner"]}
        field.save()
        manager = User.objects.create_user(username="filter-manager", email="filter-manager@example.test")
        BusinessMember.objects.create(business=self.business, user=manager, role="manager")
        self.api.force_authenticate(manager)
        self.assertEqual(self.query(field).status_code, 403)
        foreign = User.objects.create_user(username="filter-foreign", email="filter-foreign@example.test")
        Business.objects.create(owner=foreign, name="Foreign", slug="filter-foreign")
        self.api.force_authenticate(foreign)
        self.assertEqual(self.query(field).status_code, 403)
