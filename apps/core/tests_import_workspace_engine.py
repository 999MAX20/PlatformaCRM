from datetime import time, timedelta
from unittest.mock import patch

from django.test import TestCase
from django.db import IntegrityError
from django.utils import timezone
from rest_framework.exceptions import APIException

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.import_workspace.drafts import add_source, create_workspace, StaleImportVersion
from apps.core.import_workspace.engine import confirm_workspace, preview_workspace
from apps.core.import_workspace.schema import configure_source
from apps.core.models import CustomFieldDefinition, CustomFieldValue
from apps.core.import_workspace.profiles import save_profile, apply_profile
from apps.notifications.models import Notification
from apps.scheduling.models import Appointment, Resource, WorkingHours
from apps.services.models import Service


class ImportWorkspaceEngineTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="engine-owner", email="engine@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Engine", slug="engine", timezone="UTC")
        self.workspace = create_workspace(business=self.business, actor=self.owner)
        for day in range(7):
            WorkingHours.objects.create(business=self.business, weekday=day, start_time=time(8), end_time=time(20))
        self.start = (timezone.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0).isoformat()

    def source(self, kind, rows, *, fields=None, resolutions=None):
        self.workspace, source = add_source(workspace_id=self.workspace.pk, actor=self.owner, version=self.workspace.version,
            entity_type=kind, rows=rows, filename=kind + ".csv")
        self.workspace, source = configure_source(workspace_id=self.workspace.pk, source_id=source.pk, actor=self.owner,
            version=self.workspace.version, entity_type=kind, mapping={key: key for key in rows[0]},
            fields=fields or [], columns=[], resolutions=resolutions or {})
        return source

    def four_sources(self):
        self.source("clients", [{"external_id": "C1", "full_name": "Client", "phone": "+77010000001", "custom.category": "Regular"}],
            fields=[{"key": "category", "label": "Category", "field_type": "select", "options": ["Regular", "New"]}])
        self.source("services", [{"external_id": "S1", "name": "Service", "duration_minutes": "30", "price_from": "0"}])
        self.source("specialists", [{"external_id": "P1", "name": "Specialist"}])
        self.source("appointments", [{"client_ref": "C1", "service_ref": "S1", "specialist_ref": "P1", "start_at": self.start}])

    def preview(self):
        self.workspace = preview_workspace(workspace_id=self.workspace.pk, actor=self.owner, version=self.workspace.version)
        return self.workspace.report_json

    def confirm(self):
        self.workspace = confirm_workspace(workspace_id=self.workspace.pk, actor=self.owner, version=self.workspace.version)
        return self.workspace.result_json

    def test_four_linked_entities_preview_is_transient_and_confirm_replay_is_safe(self):
        self.four_sources()
        report = self.preview()
        self.assertTrue(report["ready"], report["errors"])
        for model in (Client, Service, Resource, Appointment, CustomFieldDefinition, CustomFieldValue):
            self.assertEqual(model.objects.count(), 0, model.__name__)
        self.assertTrue(all("id" not in row for row in report["rows"]))
        result = self.confirm()
        self.assertEqual(result["summary"]["created"], 4)
        record = Appointment.objects.get()
        self.assertEqual(record.client.full_name, "Client")
        self.assertEqual(record.service.name, "Service")
        self.assertEqual(record.resource.name, "Specialist")
        self.assertEqual(CustomFieldValue.objects.get().value_json, {"value": "Regular"})
        self.assertEqual(User.objects.count(), 1)
        self.assertFalse(Notification.objects.exists())
        self.assertEqual(self.confirm(), result)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_all_rows_are_checked_not_just_the_preview_sample(self):
        rows = [{"full_name": f"Client {number}", "email": f"c{number}@example.test"} for number in range(12)]
        rows[-1]["email"] = "not-email"
        self.source("clients", rows)
        report = self.preview()
        self.assertFalse(report["ready"])
        self.assertEqual(report["errors"][0]["row"], 12)
        self.assertFalse(Client.objects.exists())
        with self.assertRaises(APIException):
            self.confirm()

    def test_calendar_labels_are_staged_then_saved_on_confirmation(self):
        self.source("clients", [{"external_id": "C1", "full_name": "Client"}])
        self.source("services", [{"external_id": "S1", "name": "Service", "duration_minutes": "30"}])
        self.source("specialists", [{"external_id": "P1", "name": "Specialist"}])
        self.source("appointments", [{"client_ref": "C1", "service_ref": "S1", "specialist_ref": "P1",
            "start_at": self.start, "custom.room": "Room A"}],
            fields=[{"key": "room", "label": "Room", "field_type": "text", "in_calendar": True}])
        self.assertTrue(self.preview()["ready"])
        self.assertFalse(CustomFieldDefinition.objects.exists())
        self.confirm()
        definition = CustomFieldDefinition.objects.get(key="room")
        self.assertTrue(definition.options_json["display"]["in_calendar"])
        self.assertEqual(CustomFieldValue.objects.get(definition=definition).value_json["value"], "Room A")

    def test_database_conflict_is_safe_row_error_and_rolls_back(self):
        self.source("clients", [{"full_name": "One"}])
        with patch("apps.core.import_workspace.engine.write_basic_entity", side_effect=IntegrityError("private database constraint")):
            report = self.preview()
        self.assertFalse(report["ready"])
        self.assertIn("conflict", report["errors"][0]["errors"])
        self.assertNotIn("private database", str(report))
        self.assertFalse(Client.objects.exists())

    def test_exact_source_in_new_workspace_reuses_record_without_overwriting(self):
        rows = [{"full_name": "First name"}]
        self.source("clients", rows)
        self.assertTrue(self.preview()["ready"])
        self.confirm()
        client = Client.objects.get()
        client.full_name = "Manually corrected"
        client.save()
        self.workspace = create_workspace(business=self.business, actor=self.owner)
        self.source("clients", rows)
        report = self.preview()
        self.assertTrue(report["ready"], report)
        self.assertEqual(report["rows"][0]["outcome"], "unchanged")
        self.assertEqual(report["rows"][0]["values"]["full_name"], "Manually corrected")
        self.confirm()
        self.assertEqual(Client.objects.count(), 1)

    def test_profile_links_changed_source_by_identifier_and_preserves_manual_values(self):
        source = self.source("clients", [{"external_id": "stable1", "full_name": "First"}])
        self.workspace = save_profile(workspace_id=self.workspace.pk, actor=self.owner, version=self.workspace.version,
            source_id=source.pk, name="Source system")
        source.refresh_from_db()
        profile_id = source.profile_id
        self.assertTrue(self.preview()["ready"])
        self.confirm()
        self.workspace = create_workspace(business=self.business, actor=self.owner)
        source = self.source("clients", [{"external_id": "stable1", "full_name": "Changed source"}])
        self.workspace = apply_profile(workspace_id=self.workspace.pk, actor=self.owner, version=self.workspace.version,
            source_id=source.pk, profile_id=profile_id)
        report = self.preview()
        self.assertTrue(report["ready"], report)
        self.assertEqual(report["rows"][0]["values"]["full_name"], "First")
        self.confirm()
        self.assertEqual(Client.objects.count(), 1)

    def test_contact_match_requires_explicit_decision_and_fill_preview_shows_actual_result(self):
        existing = Client.objects.create(business=self.business, full_name="Existing", phone="+77010000001")
        source = self.source("clients", [{"full_name": "Replacement", "phone": "+77010000001", "email": "new@example.test"}])
        self.assertFalse(self.preview()["ready"])
        self.workspace, _ = configure_source(workspace_id=self.workspace.pk, source_id=source.pk, actor=self.owner,
            version=self.workspace.version, entity_type="clients", mapping=source.mapping_json, fields=[], columns=[],
            resolutions={"1": {"action": "fill", "target_id": existing.pk}})
        report = self.preview()
        self.assertTrue(report["ready"], report["errors"])
        self.assertEqual(report["rows"][0]["values"]["full_name"], "Existing")
        existing.refresh_from_db()
        self.assertEqual(existing.email, "")
        self.confirm()
        existing.refresh_from_db()
        self.assertEqual(existing.full_name, "Existing")
        self.assertEqual(existing.email, "new@example.test")

    def test_existing_record_change_requires_a_new_preview(self):
        existing = Client.objects.create(business=self.business, full_name="Existing", phone="+77010000001")
        self.source("clients", [{"full_name": "Replacement", "phone": "+77010000001"}],
            resolutions={"1": {"action": "update", "target_id": existing.pk, "update_fields": ["full_name"]}})
        self.assertTrue(self.preview()["ready"])
        existing.notes = "Changed outside import"
        existing.save()
        with self.assertRaises(StaleImportVersion):
            self.confirm()
        existing.refresh_from_db()
        self.assertEqual(existing.full_name, "Existing")

    def test_missing_reference_does_not_create_partial_objects(self):
        self.source("clients", [{"full_name": "Client"}])
        self.source("appointments", [{"client_ref": "missing", "service_ref": "missing", "specialist_ref": "missing", "start_at": self.start}])
        self.assertFalse(self.preview()["ready"])
        self.assertFalse(Client.objects.exists())

    def test_repreview_changes_version_so_old_confirmation_is_rejected(self):
        self.source("clients", [{"full_name": "Client"}])
        self.preview()
        old = self.workspace.version
        self.preview()
        with self.assertRaises(StaleImportVersion):
            confirm_workspace(workspace_id=self.workspace.pk, actor=self.owner, version=old)

    def test_failure_during_actual_confirmation_rolls_back_the_whole_bundle(self):
        self.four_sources()
        self.assertTrue(self.preview()["ready"])
        from apps.scheduling.import_commands import create_imported_record
        calls = 0

        def failure_after_simulation(**kwargs):
            nonlocal calls
            calls += 1
            if calls == 2:
                raise RuntimeError("isolated fault")
            return create_imported_record(**kwargs)

        with patch("apps.core.import_workspace.engine.create_imported_record", side_effect=failure_after_simulation), self.assertRaises(RuntimeError):
            self.confirm()
        for model in (Client, Service, Resource, Appointment, CustomFieldDefinition, CustomFieldValue):
            self.assertEqual(model.objects.count(), 0, model.__name__)

    def test_custom_field_changes_require_review_before_overwrite(self):
        existing = Client.objects.create(business=self.business, full_name="Existing")
        field = CustomFieldDefinition.objects.create(business=self.business, entity_type="client", key="code", label="Code")
        value = CustomFieldValue.objects.create(business=self.business, definition=field, entity_type="client", entity_id=str(existing.pk), value_json={"value": "Before"})
        self.source("clients", [{"full_name": "Existing", "custom.code": "After"}],
            fields=[{"key": "code", "label": "Code", "field_type": "text", "definition_id": field.pk}],
            resolutions={"1": {"action": "update", "target_id": existing.pk, "update_fields": ["custom.code"]}})
        report = self.preview()
        self.assertTrue(report["ready"], report["errors"])
        self.assertEqual(report["rows"][0]["before_custom"], {"code": {"value": "Before"}})
        value.value_json = {"value": "Changed elsewhere"}
        value.save()
        with self.assertRaises(StaleImportVersion):
            self.confirm()
        value.refresh_from_db()
        self.assertEqual(value.value_json, {"value": "Changed elsewhere"})
