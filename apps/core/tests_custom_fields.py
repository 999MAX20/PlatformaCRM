from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.core.models import CustomFieldDefinition, CustomFieldValue


class CustomFieldsFoundationTests(TestCase):
    def make_field(self, **kwargs):
        return CustomFieldDefinition.objects.create(business=self.business, entity_type="client",
                                                    key="extra", label="Extra", **kwargs)

    def save_value(self, definition, **kwargs):
        return self.api.post("/api/custom-field-values/bulk-upsert/", {
            "business": self.business.pk, "entity_type": definition.entity_type,
            "entity_id": str(self.client.pk),
            "values": [{"definition": definition.pk, "value_json": {"value": "value"}}], **kwargs,
        }, format="json")

    def test_missing_and_foreign_entity_rejected_even_with_local_definition(self):
        definition = self.make_field()
        foreign = Client.objects.create(business=self.other_business, full_name="Foreign")
        for entity_id in (str(foreign.pk), "9999999", "invalid", "9" * 63, f"0{self.client.pk}"):
            self.assertEqual(self.save_value(definition, entity_id=entity_id).status_code, 400)
        self.assertFalse(CustomFieldValue.objects.exists())

    def test_extended_types_preserve_typed_values_and_reject_invalid_input(self):
        cases = [
            ("multiselect", {"options": ["A", "B"]}, ["A", "B"], "A,B"),
            ("datetime", {}, "2026-10-08T12:30:00+05:00", "2026-02-30T12:30:00+05:00"),
            ("date", {}, "2026-10-08", "2026-02-30"),
            ("email", {}, "customer@example.test", "invalid"),
            ("url", {}, "https://example.test/profile", "invalid"),
            ("money", {}, "12.50", True),
        ]
        for field_type, options, valid, invalid in cases:
            with self.subTest(field_type=field_type):
                definition = CustomFieldDefinition.objects.create(business=self.business, entity_type="client", key=field_type, label=field_type, field_type=field_type, options_json=options)
                self.assertEqual(self.save_value(definition, values=[{"definition": definition.pk, "value_json": {"value": valid}}]).status_code, 200)
                self.assertEqual(self.save_value(definition, values=[{"definition": definition.pk, "value_json": {"value": invalid}}]).status_code, 400)
                self.assertEqual(CustomFieldValue.objects.get(definition=definition).value_json["value"], valid)

    def test_settings_lists_honor_selected_business_for_multi_business_owner(self):
        from apps.conversations.models import QuickReplyTemplate
        from apps.notifications.models import NotificationPreference

        self.other_business.owner = self.owner
        self.other_business.save()
        for business in (self.business, self.other_business):
            definition = CustomFieldDefinition.objects.create(business=business, entity_type="client", key="local", label="Local")
            client = Client.objects.create(business=business, full_name="Local")
            CustomFieldValue.objects.create(business=business, definition=definition, entity_type="client", entity_id=str(client.pk))
            QuickReplyTemplate.objects.create(business=business, title="Local", text="Reply")
            NotificationPreference.objects.create(business=business, user=self.owner, category="sales", in_app_enabled=business == self.business)
        for endpoint in ("custom-fields", "custom-field-values", "quick-replies", "notification-preferences"):
            for business in (self.business, self.other_business):
                response = self.api.get(f"/api/{endpoint}/", {"business": business.pk})
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.data["count"], 1, endpoint)
                self.assertEqual(response.data["results"][0]["business"], business.pk)
            self.assertEqual(self.api.get(f"/api/{endpoint}/", {"business": "invalid"}).status_code, 400)

    def test_read_scope_and_update_permission_apply_to_values(self):
        from apps.businesses.models import BusinessRole, RolePermission
        from apps.leads.models import Lead
        role = BusinessRole.objects.create(business=self.business, name="Scoped")
        BusinessMember.objects.filter(business=self.business, user=self.manager).update(business_role=role)
        for resource, action, scope in (("settings", "view", "business"), ("leads", "view", "own"), ("leads", "update", "own")):
            RolePermission.objects.create(business_role=role, resource=resource, action=action, scope=scope)
        lead = Lead.objects.create(business=self.business, client=self.client, responsible_user=self.owner)
        definition = CustomFieldDefinition.objects.create(business=self.business, entity_type="lead", key="secret", label="Secret")
        value = CustomFieldValue.objects.create(business=self.business, definition=definition, entity_type="lead", entity_id=str(lead.pk), value_json={"value": "private"})
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.save_value(definition, entity_id=str(lead.pk)).status_code, 403)
        self.assertEqual(self.api.get("/api/custom-field-values/").data["count"], 0)
        self.assertEqual(self.api.get(f"/api/custom-field-values/{value.pk}/").status_code, 404)
        lead.responsible_user = self.manager
        lead.save()
        self.assertEqual(self.save_value(definition, entity_id=str(lead.pk)).status_code, 200)
        RolePermission.objects.filter(business_role=role, resource="leads", action="update").update(is_allowed=False)
        self.assertEqual(self.save_value(definition, entity_id=str(lead.pk)).status_code, 403)
        card = self.api.get(f"/api/leads/{lead.pk}/crm-card/")
        self.assertFalse(card.data["custom_fields"][0]["can_edit"])

    def test_direct_value_mutation_enforces_field_roles_and_identity(self):
        definition = self.make_field(permissions_json={"edit_roles": ["owner"]})
        self.assertEqual(self.save_value(definition).status_code, 200)
        value = CustomFieldValue.objects.get(definition=definition)
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.api.patch(f"/api/custom-field-values/{value.pk}/", {"value_json": {"value": "blocked"}}, format="json").status_code, 403)
        self.assertEqual(self.api.delete(f"/api/custom-field-values/{value.pk}/").status_code, 403)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.api.patch(f"/api/custom-field-values/{value.pk}/", {"entity_id": "999"}, format="json").status_code, 400)
        definition.is_active = False
        definition.save()
        self.assertEqual(self.save_value(definition).status_code, 400)
        value.refresh_from_db()
        self.assertEqual(value.value_json, {"value": "value"})

    def test_definition_validation_and_retention(self):
        definition = self.make_field(field_type="select", options_json={"options": [{"value": "A", "label": "Alpha"}, "B"]})
        self.assertEqual(self.save_value(definition, values=[{"definition": definition.pk, "value_json": {"value": "A"}}]).status_code, 200)
        url = f"/api/custom-fields/{definition.pk}/"
        for payload in ({"field_type": "number"}, {"entity_type": "deal"}, {"key": "changed"},
                        {"options_json": {"options": ["B"]}}, {"options_json": []},
                        {"options_json": {"options": ["A", "A"]}}, {"permissions_json": {"edit_roles": ["not-a-role"]}}):
            self.assertEqual(self.api.patch(url, payload, format="json").status_code, 400, payload)
        self.assertEqual(self.api.delete(url).status_code, 400)
        self.assertEqual(self.api.patch(url, {"is_active": False}, format="json").status_code, 200)
        self.assertEqual(CustomFieldValue.objects.get(definition=definition).value_json, {"value": "A"})

    def test_bulk_audit_failure_rolls_back_values(self):
        from unittest.mock import patch
        definition = self.make_field()
        with patch("apps.core.custom_field_views.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            self.assertEqual(self.save_value(definition).status_code, 500)
        self.assertFalse(CustomFieldValue.objects.filter(definition=definition).exists())

    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(
            username="custom-fields-owner",
            email="custom-fields-owner@example.com",
            password="pass",
            role=User.Roles.BUSINESS_OWNER,
        )
        self.other_owner = User.objects.create_user(
            username="custom-fields-other",
            email="custom-fields-other@example.com",
            password="pass",
            role=User.Roles.BUSINESS_OWNER,
        )
        self.manager = User.objects.create_user(
            username="custom-fields-manager",
            email="custom-fields-manager@example.com",
            password="pass",
            role=User.Roles.BUSINESS_MANAGER,
        )
        self.business = Business.objects.create(owner=self.owner, name="Fields Clinic", slug="fields-clinic")
        self.other_business = Business.objects.create(owner=self.other_owner, name="Other Fields", slug="other-fields")
        BusinessMember.objects.create(business=self.business, user=self.owner, role=BusinessMember.Roles.OWNER)
        BusinessMember.objects.create(business=self.business, user=self.manager, role=BusinessMember.Roles.MANAGER)
        BusinessMember.objects.create(business=self.other_business, user=self.other_owner, role=BusinessMember.Roles.OWNER)
        self.client = Client.objects.create(business=self.business, full_name="Custom Client")
        self.api.force_authenticate(self.owner)

    def test_business_can_create_client_custom_field(self):
        response = self.api.post(
            "/api/custom-fields/",
            {
                "business": self.business.id,
                "entity_type": CustomFieldDefinition.EntityTypes.CLIENT,
                "key": "loyalty_level",
                "label": "Loyalty level",
                "field_type": CustomFieldDefinition.FieldTypes.SELECT,
                "options_json": {"options": ["A", "B"]},
            },
            format="json",
        )

        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.data["key"], "loyalty_level")

    def test_bulk_upsert_saves_value_for_client_and_card_returns_it(self):
        definition = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="birthday",
            label="Birthday",
            field_type=CustomFieldDefinition.FieldTypes.DATE,
        )

        response = self.api.post(
            "/api/custom-field-values/bulk-upsert/",
            {
                "business": self.business.id,
                "entity_type": "client",
                "entity_id": str(self.client.id),
                "values": [{"definition": definition.id, "value_json": {"value": "2026-05-14"}}],
            },
            format="json",
        )
        card_response = self.api.get(f"/api/clients/{self.client.id}/crm-card/")

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CustomFieldValue.objects.filter(definition=definition, entity_id=str(self.client.id)).exists())
        self.assertEqual(card_response.status_code, 200)
        self.assertEqual(card_response.data["custom_fields"][0]["definition"]["key"], "birthday")
        self.assertEqual(card_response.data["custom_fields"][0]["value"]["value_json"]["value"], "2026-05-14")

    def test_bulk_upsert_validates_custom_field_value_type(self):
        definition = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="birthday",
            label="Birthday",
            field_type=CustomFieldDefinition.FieldTypes.DATE,
        )

        response = self.api.post(
            "/api/custom-field-values/bulk-upsert/",
            {
                "business": self.business.id,
                "entity_type": "client",
                "entity_id": str(self.client.id),
                "values": [{"definition": definition.id, "value_json": {"value": "not-a-date"}}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomFieldValue.objects.filter(definition=definition, entity_id=str(self.client.id)).exists())

    def test_bulk_upsert_validates_select_options_and_normalizes_numbers(self):
        select_definition = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="loyalty",
            label="Loyalty",
            field_type=CustomFieldDefinition.FieldTypes.SELECT,
            options_json={"options": ["A", "B"]},
        )
        number_definition = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="score",
            label="Score",
            field_type=CustomFieldDefinition.FieldTypes.NUMBER,
        )

        invalid = self.api.post(
            "/api/custom-field-values/bulk-upsert/",
            {
                "business": self.business.id,
                "entity_type": "client",
                "entity_id": str(self.client.id),
                "values": [{"definition": select_definition.id, "value_json": {"value": "C"}}],
            },
            format="json",
        )
        valid = self.api.post(
            "/api/custom-field-values/bulk-upsert/",
            {
                "business": self.business.id,
                "entity_type": "client",
                "entity_id": str(self.client.id),
                "values": [
                    {"definition": select_definition.id, "value_json": {"value": "A"}},
                    {"definition": number_definition.id, "value_json": {"value": "10,5"}},
                ],
            },
            format="json",
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(CustomFieldValue.objects.get(definition=number_definition).value_json["value"], "10.5")

    def test_bulk_upsert_requires_json_boolean_for_boolean_fields(self):
        definition = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="consent",
            label="Consent",
            field_type=CustomFieldDefinition.FieldTypes.BOOLEAN,
        )

        invalid = self.api.post(
            "/api/custom-field-values/bulk-upsert/",
            {
                "business": self.business.id,
                "entity_type": "client",
                "entity_id": str(self.client.id),
                "values": [{"definition": definition.id, "value_json": {"value": "true"}}],
            },
            format="json",
        )
        valid = self.api.post(
            "/api/custom-field-values/bulk-upsert/",
            {
                "business": self.business.id,
                "entity_type": "client",
                "entity_id": str(self.client.id),
                "values": [{"definition": definition.id, "value_json": {"value": True}}],
            },
            format="json",
        )

        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(valid.status_code, 200)
        self.assertIs(CustomFieldValue.objects.get(definition=definition).value_json["value"], True)

    def test_bulk_upsert_is_atomic_when_one_value_is_invalid(self):
        text_definition = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="notes",
            label="Notes",
            field_type=CustomFieldDefinition.FieldTypes.TEXT,
        )
        date_definition = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="next_date",
            label="Next date",
            field_type=CustomFieldDefinition.FieldTypes.DATE,
        )

        response = self.api.post(
            "/api/custom-field-values/bulk-upsert/",
            {
                "business": self.business.id,
                "entity_type": "client",
                "entity_id": str(self.client.id),
                "values": [
                    {"definition": text_definition.id, "value_json": {"value": "Saved only if all valid"}},
                    {"definition": date_definition.id, "value_json": {"value": "tomorrow"}},
                ],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)
        self.assertFalse(CustomFieldValue.objects.filter(definition=text_definition, entity_id=str(self.client.id)).exists())

    def test_custom_fields_are_tenant_filtered(self):
        CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="visible",
            label="Visible",
        )
        CustomFieldDefinition.objects.create(
            business=self.other_business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="hidden",
            label="Hidden",
        )

        response = self.api.get("/api/custom-fields/", {"entity_type": "client"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["key"], "visible")

    def test_bulk_upsert_rejects_foreign_definition(self):
        definition = CustomFieldDefinition.objects.create(
            business=self.other_business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="foreign",
            label="Foreign",
        )

        response = self.api.post(
            "/api/custom-field-values/bulk-upsert/",
            {
                "business": self.business.id,
                "entity_type": "client",
                "entity_id": str(self.client.id),
                "values": [{"definition": definition.id, "value_json": {"value": "x"}}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 400)

    def test_custom_field_view_roles_hide_definition_and_value(self):
        owner_only = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="owner_private",
            label="Owner private",
            permissions_json={"view_roles": [BusinessMember.Roles.OWNER], "edit_roles": [BusinessMember.Roles.OWNER]},
        )
        manager_visible = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="manager_visible",
            label="Manager visible",
            permissions_json={"view_roles": [BusinessMember.Roles.MANAGER], "edit_roles": [BusinessMember.Roles.OWNER]},
        )
        CustomFieldValue.objects.create(
            business=self.business,
            definition=owner_only,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            entity_id=str(self.client.id),
            value_json={"value": "secret"},
        )
        CustomFieldValue.objects.create(
            business=self.business,
            definition=manager_visible,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            entity_id=str(self.client.id),
            value_json={"value": "visible"},
        )
        self.api.force_authenticate(self.manager)

        definitions_response = self.api.get("/api/custom-fields/", {"entity_type": "client"})
        values_response = self.api.get(
            "/api/custom-field-values/",
            {"entity_type": "client", "entity_id": str(self.client.id)},
        )

        self.assertEqual(definitions_response.status_code, 200)
        self.assertEqual([item["key"] for item in definitions_response.data["results"]], ["manager_visible"])
        self.assertEqual(values_response.status_code, 200)
        self.assertEqual([item["definition"] for item in values_response.data["results"]], [manager_visible.id])

    def test_custom_field_edit_roles_block_bulk_upsert(self):
        definition = CustomFieldDefinition.objects.create(
            business=self.business,
            entity_type=CustomFieldDefinition.EntityTypes.CLIENT,
            key="owner_edit_only",
            label="Owner edit only",
            permissions_json={"view_roles": [BusinessMember.Roles.MANAGER], "edit_roles": [BusinessMember.Roles.OWNER]},
        )
        self.api.force_authenticate(self.manager)

        response = self.api.post(
            "/api/custom-field-values/bulk-upsert/",
            {
                "business": self.business.id,
                "entity_type": "client",
                "entity_id": str(self.client.id),
                "values": [{"definition": definition.id, "value_json": {"value": "blocked"}}],
            },
            format="json",
        )

        self.assertEqual(response.status_code, 403)
        self.assertFalse(CustomFieldValue.objects.filter(definition=definition, entity_id=str(self.client.id)).exists())
