from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import BusinessMember
from apps.clients.models import Client
from apps.core.models import ImportWorkspace
from apps.core.antivirus import ScanUnavailable
from apps.core import tests_import_workspace_drafts as draft_fixtures


class ImportWorkspaceAPITests(TestCase):
    def setUp(self):
        draft_fixtures.ImportWorkspaceDraftTests.setUp(self)
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.url = f"/api/import-workspaces/{self.workspace.pk}/"

    @patch("apps.core.import_workspace.uploads.scan_stream", side_effect=ScanUnavailable())
    def test_scanner_outage_has_specific_code_and_preserves_draft(self, scanner):
        version = self.workspace.version
        response = self.api.post(self.url + "upload/", {
            "version": version, "entity_type": "clients",
            "file": SimpleUploadedFile("clients.csv", b"Name,Phone\nTest,+12025550101\n", content_type="text/csv"),
        }, format="multipart")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data["code"], "file_scan_unavailable")
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.version, version)
        self.assertFalse(self.workspace.sources.exists())
        self.assertFalse(Client.objects.exists())

    @patch("apps.core.import_workspace.uploads.scan_stream", return_value=SimpleNamespace(clean=True))
    def test_upload_configure_correct_reload_and_cancel_preserve_working_data(self, scanner):
        response = self.api.post(self.url + "upload/", {"version": 1, "entity_type": "clients",
            "file": SimpleUploadedFile("clients.csv", b"Name,Phone\nOne,+77010000001\n", content_type="text/csv")}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        source = response.data["sources"][0]
        response = self.api.post(self.url + "configure/", {"version": 2, "source_id": source["id"], "entity_type": "clients",
            "mapping": {"full_name": "Name", "phone": "Phone"}}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.api.post(self.url + "correct/", {"version": 3, "source_id": source["id"],
            "corrections": {"1": {"Name": "Corrected"}}, "excluded": []}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        rows = self.api.get(self.url + "rows/", {"source_id": source["id"]})
        self.assertEqual(rows.data["results"][0]["original"]["Name"], "One")
        self.assertEqual(rows.data["results"][0]["values"]["Name"], "Corrected")
        self.assertFalse(Client.objects.exists())
        response = self.api.post(self.url + "cancel/", {"version": 4}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["state"], "cancelled")
        self.assertEqual(response.data["sources"], [])
        self.assertFalse(Client.objects.exists())

    def test_foreign_actor_cannot_read_or_mutate_draft(self):
        other = User.objects.create_user(username="foreign-import", email="foreign-import@example.test", role="business_owner")
        self.api.force_authenticate(other)
        self.assertEqual(self.api.get(self.url).status_code, 404)
        self.assertEqual(self.api.post(self.url + "cancel/", {"version": 1}, format="json").status_code, 404)

    def test_member_without_integration_manage_cannot_create(self):
        staff = User.objects.create_user(username="import-staff", email="import-staff@example.test", role="manager")
        BusinessMember.objects.create(business=self.business, user=staff, role="operator")
        self.api.force_authenticate(staff)
        response = self.api.post("/api/import-workspaces/", {"business": self.business.pk}, format="json")
        self.assertEqual(response.status_code, 403, response.data)

    def test_malformed_create_and_version_are_validation_errors(self):
        response = self.api.post("/api/import-workspaces/", [], format="json")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(self.api.post(self.url + "cancel/", {"version": "bad"}, format="json").status_code, 400)
        self.assertEqual(self.api.post(self.url + "duplicate_source/", [], format="json").status_code, 400)
        self.assertEqual(self.api.post(self.url + "cancel/", {"version": 2}, format="json").status_code, 409)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.state, "draft")

    def test_generic_mutations_cannot_bypass_state_or_edit_source(self):
        for method in (self.api.patch, self.api.put, self.api.delete):
            self.assertEqual(method(self.url, {"state": "imported"}, format="json").status_code, 405)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.state, "draft")

    def test_list_is_business_scoped_and_paged(self):
        response = self.api.get("/api/import-workspaces/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.workspace.pk)
        self.assertNotIn("sources", response.data["results"][0])

    @patch("apps.core.import_workspace.uploads.scan_stream", return_value=SimpleNamespace(clean=True))
    def test_atomic_save_rolls_back_mapping_on_invalid_correction(self, scanner):
        uploaded = self.api.post(self.url + "upload/", {"version": 1, "entity_type": "clients",
            "file": SimpleUploadedFile("clients.csv", b"Name,Code\nOne,001\n", content_type="text/csv")}, format="multipart")
        self.assertEqual(uploaded.status_code, 200)
        source = uploaded.data["sources"][0]
        self.assertEqual(source["suggested_mapping"]["clients"]["full_name"], "Name")
        self.assertEqual(source["suggested_types"]["Code"], "text")
        payload = {"version": 2, "source_id": source["id"], "entity_type": "clients",
            "mapping": {"full_name": "Name"}, "corrections": {"9": {"Name": "Invalid row"}}, "excluded": []}
        response = self.api.post(self.url + "save_source/", payload, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.version, 2)
        self.assertEqual(self.workspace.sources.get().mapping_json, {})
        payload["corrections"] = {"1": {"Name": "Changed"}}
        response = self.api.post(self.url + "save_source/", payload, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["sources"][0]["mapping"], {"full_name": "Name"})
        self.assertEqual(response.data["sources"][0]["corrections"], payload["corrections"])

    @patch("apps.core.import_workspace.uploads.scan_stream", return_value=SimpleNamespace(clean=True))
    def test_reachable_preview_confirm_replay_and_current_read_boundary(self, scanner):
        response = self.api.post(self.url + "upload/", {"version": 1, "entity_type": "clients",
            "file": SimpleUploadedFile("clients.csv", b"Name\nOne\n", content_type="text/csv")}, format="multipart")
        self.assertEqual(response.status_code, 200, response.data)
        source_id = response.data["sources"][0]["id"]
        response = self.api.post(self.url + "configure/", {"version": 2, "source_id": source_id,
            "entity_type": "clients", "mapping": {"full_name": "Name"}}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        response = self.api.post(self.url + "preview/", {"version": 3}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(response.data["report"]["ready"])
        self.assertFalse(Client.objects.exists())
        version = response.data["version"]
        response = self.api.post(self.url + "confirm/", {"version": version}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["state"], "imported")
        self.assertEqual(Client.objects.get().full_name, "One")
        self.assertEqual(self.api.post(self.url + "confirm/", {"version": version}, format="json").status_code, 200)
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(self.api.post(self.url + "preview/", {"version": version}, format="json").status_code, 400)

    def test_reference_choices_show_prepared_source_rows_and_scope_crm_records(self):
        source = draft_fixtures.ImportWorkspaceDraftTests.source(self)
        source.mapping_json = {"full_name": "Name"}
        source.corrections_json = {"1": {"Name": "Corrected"}}
        source.excluded_json = [2]
        source.save()
        response = self.api.get(self.url + "references/", {"entity_type": "clients"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertIn("Corrected", response.data["results"][0]["label"])
        reference = response.data["results"][0]["reference"]
        self.assertEqual(reference, f"row:{source.pk}:1")
        self.assertEqual(self.api.get(self.url + "references/", {"entity_type": "services", "reference": reference}).data["count"], 0)
        client = Client.objects.create(business=self.business, full_name="Existing")
        response = self.api.get(self.url + "references/", {"entity_type": "clients", "reference": f"crm:{client.pk}"})
        self.assertEqual(response.data["results"][0]["label"], "Existing")
        self.assertEqual(self.api.get(self.url + "references/", {"entity_type": "clients", "reference": "crm:99999999"}).status_code, 400)

    def test_remove_source_invalidates_preview_without_touching_working_data(self):
        source = draft_fixtures.ImportWorkspaceDraftTests.source(self)
        source.mapping_json = {"full_name": "Name"}
        source.save()
        response = self.api.post(self.url + "preview/", {"version": self.workspace.version}, format="json")
        self.assertEqual(response.status_code, 200)
        response = self.api.post(self.url + "remove_source/", {"version": response.data["version"], "source_id": source.pk}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["sources"], [])
        self.assertEqual(response.data["state"], "draft")
        self.assertEqual(response.data["report"], {})
        self.assertFalse(Client.objects.exists())
