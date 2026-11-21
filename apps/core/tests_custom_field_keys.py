from django.test import TestCase
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.core.models import CustomFieldDefinition
from apps.core.serializers import CustomFieldDefinitionSerializer


class CustomFieldKeyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="field-key-owner", email="field-key-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Keys", slug="field-keys")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def create(self, label, **extra):
        return self.api.post("/api/custom-fields/", {"business": self.business.pk,
            "entity_type": "client", "label": label, "field_type": "text", **extra}, format="json")

    def test_multilingual_names_get_distinct_keys_without_client_slug(self):
        keys = []
        for label in ("QA Первое поле", "QA Второе поле", "Қосымша өріс", "Название", "English", "Я" * 128):
            response = self.create(label)
            self.assertEqual(response.status_code, 201, response.data)
            keys.append(response.data["key"])
            self.assertRegex(keys[-1], r"^[a-zA-Z0-9_-]{1,64}$")
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual(CustomFieldDefinition.objects.count(), len(keys))

    def test_explicit_key_validation_and_tenant_entity_uniqueness(self):
        self.assertEqual(self.create("One", key="x" * 64).status_code, 201)
        for key in ("x" * 65, "ключ", "with spaces", ""):
            response = self.create("Invalid", key=key)
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn("key", response.data)
        duplicate = self.create("Duplicate", key="x" * 64)
        self.assertEqual(duplicate.status_code, 400)
        self.assertIn("key", duplicate.data)
        self.assertEqual(self.create("Other entity", key="x" * 64, entity_type="service").status_code, 201)
        other = Business.objects.create(owner=self.owner, name="Other", slug="other-field-keys")
        self.assertEqual(self.create("Other business", key="x" * 64, business=other.pk).status_code, 201)

    def test_stale_validation_duplicate_insert_is_a_key_error_not_integrity_error(self):
        data = {"business": self.business.pk, "entity_type": "client", "label": "Concurrent", "key": "explicit"}
        first = CustomFieldDefinitionSerializer(data=data)
        second = CustomFieldDefinitionSerializer(data=data)
        self.assertTrue(first.is_valid(), first.errors)
        self.assertTrue(second.is_valid(), second.errors)
        first.save()
        with self.assertRaises(ValidationError) as caught:
            second.save()
        self.assertIn("key", caught.exception.detail)
        self.assertEqual(CustomFieldDefinition.objects.count(), 1)

    def test_label_update_preserves_key_values_and_filter(self):
        from apps.clients.models import Client
        from apps.core.models import CustomFieldValue
        result = self.create("Before", options_json={"display": {"in_filters": True}})
        self.assertEqual(result.status_code, 201, result.data)
        definition = CustomFieldDefinition.objects.get(pk=result.data["id"])
        client = Client.objects.create(business=self.business, full_name="Client")
        value = CustomFieldValue.objects.create(business=self.business, definition=definition,
            entity_type="client", entity_id=str(client.pk), value_json={"value": "kept"})
        for method in (self.api.patch, self.api.put):
            response = method(f"/api/custom-fields/{definition.pk}/", {"business": self.business.pk,
                "entity_type": "client", "label": "After", "field_type": "text"}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["key"], definition.key)
        value.refresh_from_db()
        self.assertEqual(value.value_json, {"value": "kept"})
        response = self.api.get("/api/clients/", {"business": self.business.pk, "custom_field": definition.pk,
            "custom_operator": "equals", "custom_value": "kept"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data["results"]], [client.pk])

    def test_unauthorized_business_cannot_create_generated_field(self):
        foreign = User.objects.create_user(username="foreign-field-owner", email="foreign-field-owner@example.test")
        self.api.force_authenticate(foreign)
        self.assertEqual(self.create("Denied").status_code, 403)
        self.assertFalse(CustomFieldDefinition.objects.exists())
