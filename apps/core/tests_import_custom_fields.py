from django.test import TestCase
from rest_framework.test import APIClient
from apps.core import tests_custom_fields as fixtures
from apps.core.models import CustomFieldDefinition, CustomFieldValue
from apps.scheduling.models import Resource
from apps.services.models import Service


class ImportedCustomFieldTests(TestCase):
    setUp = fixtures.CustomFieldsFoundationTests.setUp

    def make(self, kind, entity):
        definition = CustomFieldDefinition.objects.create(business=self.business, entity_type=kind,
            key=kind, label=kind)
        response = self.api.post("/api/custom-field-values/bulk-upsert/", {
            "business": self.business.pk, "entity_type": kind, "entity_id": str(entity.pk),
            "values": [{"definition": definition.pk, "value_json": {"value": "Imported"}}],
        }, format="json")
        return definition, response

    def test_service_and_specialist_values_are_readable_editable_and_archivable(self):
        for kind, entity in (("service", Service.objects.create(business=self.business, name="Service")),
                             ("specialist", Resource.objects.create(business=self.business, name="Specialist", resource_type="staff"))):
            definition, response = self.make(kind, entity)
            self.assertEqual(response.status_code, 200, response.data)
            value = CustomFieldValue.objects.get(definition=definition)
            self.assertEqual(self.api.get(f"/api/custom-field-values/{value.pk}/").status_code, 200)
            response = self.api.patch(f"/api/custom-field-values/{value.pk}/", {"value_json": {"value": "Edited"}}, format="json")
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(self.api.patch(f"/api/custom-fields/{definition.pk}/", {"is_active": False}, format="json").status_code, 200)
            self.assertEqual(self.api.get(f"/api/custom-field-values/{value.pk}/").data["value_json"], {"value": "Edited"})
            self.assertEqual(self.api.patch(f"/api/custom-field-values/{value.pk}/", {"value_json": {"value": "Blocked"}}, format="json").status_code, 400)

    def test_nonstaff_and_foreign_targets_are_rejected_and_hidden(self):
        entities = [("specialist", Resource.objects.create(business=self.business, name="Equipment", resource_type="equipment")),
                    ("service", Service.objects.create(business=self.other_business, name="Foreign"))]
        for kind, entity in entities:
            definition, response = self.make(kind, entity)
            self.assertEqual(response.status_code, 400, response.data)
            value = CustomFieldValue.objects.create(business=self.business, definition=definition, entity_type=kind, entity_id=str(entity.pk), value_json={"value": "Invisible"})
            self.assertEqual(self.api.get(f"/api/custom-field-values/{value.pk}/").status_code, 404)
        self.assertEqual(self.api.get("/api/custom-field-values/").data["count"], 0)

    def test_revoked_field_role_and_missing_target_hide_values(self):
        entity = Service.objects.create(business=self.business, name="Service")
        definition, response = self.make("service", entity)
        self.assertEqual(response.status_code, 200)
        value = CustomFieldValue.objects.get(definition=definition)
        definition.permissions_json = {"view_roles": ["owner"]}
        definition.save()
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.api.get(f"/api/custom-field-values/{value.pk}/").status_code, 404)
        self.api.force_authenticate(self.owner)
        entity.delete()
        self.assertEqual(self.api.get(f"/api/custom-field-values/{value.pk}/").status_code, 404)

    def test_context_has_current_field_roles_and_rejects_foreign_targets(self):
        entity = Service.objects.create(business=self.business, name="Service")
        definition, response = self.make("service", entity)
        self.assertEqual(response.status_code, 200)
        params = {"business": self.business.pk, "entity_type": "service", "ids": [entity.pk]}
        response = self.api.get("/api/custom-field-values/context/", params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(len(response.data["values"]), 1)
        self.assertTrue(response.data["editable_entities"][str(entity.pk)])
        definition.permissions_json = {"edit_roles": ["owner"]}
        definition.save()
        self.api.force_authenticate(self.manager)
        response = self.api.get("/api/custom-field-values/context/", params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn(definition.pk, response.data["editable_fields"])
        foreign = Service.objects.create(business=self.other_business, name="Foreign")
        self.assertEqual(self.api.get("/api/custom-field-values/context/", {**params, "ids": [foreign.pk]}).status_code, 400)
        self.assertEqual(self.api.get("/api/custom-field-values/context/", {**params, "ids": list(range(1, 102))}).status_code, 400)

    def test_filters_run_before_pagination_and_obey_permissions(self):
        entities = [Service.objects.create(business=self.business, name=f"Service {index}") for index in range(3)]
        field = CustomFieldDefinition.objects.create(business=self.business, entity_type="service", key="score", label="Score", field_type="number", options_json={"display": {"in_filters": True}})
        for entity, value in zip(entities, ["2", "10.00"]):
            CustomFieldValue.objects.create(business=self.business, definition=field, entity_type="service", entity_id=str(entity.pk), value_json={"value": value})
        params = {"business": self.business.pk, "custom_field": field.pk, "custom_operator": "gte", "custom_value": "9", "page_size": 1}
        response = self.api.get("/api/services/", params)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], entities[1].pk)
        self.assertEqual(self.api.get("/api/services/", {**params, "custom_operator": "equals", "custom_value": "10"}).data["count"], 1)
        self.assertEqual(self.api.get("/api/services/", {**params, "custom_operator": "is_empty"}).data["count"], 1)
        self.assertEqual(self.api.get("/api/services/", {**params, "custom_operator": "contains"}).status_code, 400)
        field.permissions_json = {"view_roles": ["owner"]}
        field.save()
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.api.get("/api/services/", params).status_code, 403)

    def test_ordered_filters_reject_empty_and_invalid_bounds(self):
        for kind in ("number", "money", "date"):
            field = CustomFieldDefinition.objects.create(business=self.business, entity_type="service",
                key=kind, label=kind, field_type=kind, options_json={"display": {"in_filters": True}})
            for operator in ("gte", "lte"):
                for value in ("", "  ", "invalid"):
                    with self.subTest(kind=kind, operator=operator, value=value):
                        response = self.api.get("/api/services/", {"business": self.business.pk,
                            "custom_field": field.pk, "custom_operator": operator, "custom_value": value})
                        self.assertEqual(response.status_code, 400, response.data)

    def test_multiselect_filters_validate_array_and_preserve_scope(self):
        import json
        field = CustomFieldDefinition.objects.create(business=self.business, entity_type="service",
            key="tags", label="Tags", field_type="multiselect",
            options_json={"options": ["A", "B"], "display": {"in_filters": True}})
        entities = []
        for index, value in enumerate((["A"], ["A", "B"], [])):
            entity = Service.objects.create(business=self.business, name=f"Tagged {index}")
            entities.append(entity)
            CustomFieldValue.objects.create(business=self.business, definition=field, entity_type="service",
                entity_id=str(entity.pk), value_json={"value": value})
        params = {"business": self.business.pk, "custom_field": field.pk, "custom_operator": "equals"}
        for raw, expected in (("A", entities[0]), (json.dumps(["A"]), entities[0]), (json.dumps(["A", "B"]), entities[1])):
            response = self.api.get("/api/services/", {**params, "custom_value": raw})
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual([row["id"] for row in response.data["results"]], [expected.pk])
        response = self.api.get("/api/services/", {**params, "custom_operator": "is_empty"})
        self.assertEqual([row["id"] for row in response.data["results"]], [entities[2].pk])
        for raw in ('["unknown"]', '[1]', '{}', 'null', '["A"'):
            self.assertEqual(self.api.get("/api/services/", {**params, "custom_value": raw}).status_code, 400)
        field.permissions_json = {"view_roles": ["owner"]}
        field.save()
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.api.get("/api/services/", {**params, "custom_value": '["A"]'}).status_code, 403)
        self.api.force_authenticate(self.other_owner)
        self.assertEqual(self.api.get("/api/services/", {**params, "custom_value": '["A"]'}).status_code, 403)

    def test_exports_include_typed_fields_and_recheck_download_roles(self):
        import csv, io
        from django.test import override_settings
        from unittest.mock import patch
        from apps.core.export_jobs import request_entity_export, process_export_job
        from apps.core.export_access import assert_export_download_access
        from rest_framework.exceptions import PermissionDenied
        entity = Service.objects.create(business=self.business, name="Service")
        field, response = self.make("service", entity)
        self.assertEqual(response.status_code, 200)
        value = CustomFieldValue.objects.get(definition=field)
        value.value_json = {"value": "=SUM(1,2)"}
        value.save()
        response = self.api.get("/api/export/services/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200)
        rows = list(csv.reader(io.StringIO(response.content.decode())))
        self.assertIn("custom.service", rows[0])
        self.assertTrue(rows[1][-1].startswith("'="))
        with override_settings(EXPORT_SYNC_MAX_ROWS=0), patch("apps.core.tasks.process_export_job_task.delay"):
            response, job = request_entity_export(business=self.business, actor=self.manager, export_key="services")
        job = process_export_job(job.pk)
        self.assertEqual(job.status, "succeeded", job.error)
        assert_export_download_access(job, self.manager)
        field.permissions_json = {"view_roles": ["owner"]}
        field.save()
        with self.assertRaises(PermissionDenied):
            assert_export_download_access(job, self.manager)
        job.result_file.delete(save=False)

    def test_display_settings_reject_malformed_flags_and_preserve_saved_value(self):
        entity = Service.objects.create(business=self.business, name="Service")
        field, response = self.make("service", entity)
        self.assertEqual(response.status_code, 200)
        for display in [[], "invalid", {"in_filters": "false"}, {"unknown": True}]:
            response = self.api.patch(f"/api/custom-fields/{field.pk}/", {"options_json": {"display": display}}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        response = self.api.patch(f"/api/custom-fields/{field.pk}/", {"options_json": {
            "display": {"in_card": True, "in_table": False, "in_filters": True, "in_calendar": False}}}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(CustomFieldValue.objects.get(definition=field).value_json["value"], "Imported")
