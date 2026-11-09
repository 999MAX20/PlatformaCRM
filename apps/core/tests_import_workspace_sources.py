from io import BytesIO
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.core.import_workspace.schema import configure_source
from apps.core.import_workspace.uploads import upload_sources
from apps.core.models import CustomFieldDefinition
from apps.core.tests_import_workspace_drafts import ImportWorkspaceDraftTests


class ImportWorkspaceSourceTests(TestCase):
    setUp = ImportWorkspaceDraftTests.setUp
    source = ImportWorkspaceDraftTests.source

    def configure(self, source, **kwargs):
        data = dict(workspace_id=self.workspace.pk, source_id=source.pk, actor=self.owner,
            version=self.workspace.version, entity_type="clients", mapping={"full_name": "Name"},
            fields=[], columns=["full_name"], resolutions={})
        data.update(kwargs)
        return configure_source(**data)

    def test_field_definition_is_only_staged_and_mapping_uses_declared_fields(self):
        source = self.source()
        workspace, source = self.configure(source, fields=[{"key": "category", "label": "Category", "field_type": "text"}],
            mapping={"full_name": "Name", "custom.category": "Phone"}, columns=["custom.category", "full_name"])
        self.assertEqual(source.mapping_json["custom.category"], "Phone")
        self.assertEqual(workspace.version, 3)
        self.assertFalse(CustomFieldDefinition.objects.exists())

    def test_unknown_targets_duplicate_keys_and_invalid_decisions_are_rejected(self):
        source = self.source()
        cases = [dict(mapping={"is_staff": "Name"}), dict(mapping={"full_name": "missing"}),
            dict(columns=["full_name", "full_name"]), dict(resolutions={"1": {"action": "delete"}}),
            dict(fields=[{"key": "x", "label": "X", "field_type": "select", "options": []}]),
            dict(fields=[{"key": "x", "label": "X", "field_type": "text"}] * 2)]
        for kwargs in cases:
            with self.subTest(kwargs=kwargs), self.assertRaises(ValidationError):
                self.configure(source, **kwargs)
        source.refresh_from_db()
        self.assertEqual(source.mapping_json, {})

    def test_existing_definition_must_belong_to_same_business_and_entity(self):
        source = self.source()
        definition = CustomFieldDefinition.objects.create(business=self.business, entity_type="appointment", key="x", label="X")
        with self.assertRaises(ValidationError):
            self.configure(source, fields=[{"key": "x", "label": "X", "field_type": "text", "definition_id": definition.pk}])

    @patch("apps.core.import_workspace.uploads.scan_stream", return_value=SimpleNamespace(clean=True))
    def test_all_workbook_sheets_are_staged_without_live_entities(self, scanner):
        from openpyxl import Workbook
        workbook = Workbook()
        workbook.active.title = "Clients"
        workbook.active.append(["Name", "Phone"])
        workbook.active.append(["One", "+77010000001"])
        sheet = workbook.create_sheet("Specialists")
        sheet.append(["Name"])
        sheet.append(["Two"])
        stream = BytesIO()
        workbook.save(stream)
        workbook.close()
        upload = SimpleUploadedFile("data.xlsx", stream.getvalue(), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")
        workspace, sources = upload_sources(workspace_id=self.workspace.pk, actor=self.owner,
            version=self.workspace.version, upload=upload, entity_type="clients")
        self.assertEqual([source.sheet_name for source in sources], ["Clients", "Specialists"])
        self.assertEqual(sources[1].rows_json, [{"Name": "Two"}])
        self.assertEqual(workspace.version, 3)
        scanner.assert_called_once()

    @patch("apps.core.import_workspace.uploads.scan_stream", return_value=SimpleNamespace(clean=False))
    def test_blocked_file_creates_no_source(self, scanner):
        upload = SimpleUploadedFile("data.csv", b"Name\nOne\n", content_type="text/csv")
        with self.assertRaises(ValidationError):
            upload_sources(workspace_id=self.workspace.pk, actor=self.owner, version=self.workspace.version,
                upload=upload, entity_type="clients")
        self.assertFalse(self.workspace.sources.exists())

    @patch("apps.core.import_workspace.uploads.scan_stream", return_value=SimpleNamespace(clean=True))
    def test_ambiguous_headers_and_ragged_csv_do_not_silently_drop_cells(self, scanner):
        for content in [b"Name,Name\nOne,Two\n", b"Name\nOne,Two\n", b"Name,Phone\nOne\n"]:
            with self.subTest(content=content), self.assertRaises(ValidationError):
                upload_sources(workspace_id=self.workspace.pk, actor=self.owner, version=self.workspace.version,
                    upload=SimpleUploadedFile("data.csv", content, content_type="text/csv"), entity_type="clients")
        self.assertFalse(self.workspace.sources.exists())
