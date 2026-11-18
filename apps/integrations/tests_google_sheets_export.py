import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business
from apps.clients.models import Client
from apps.integrations.credential_encryption import encrypt_credential_value
from apps.integrations.google_http import GoogleError
from apps.integrations.google_models import GoogleConnection, GoogleSheetTransfer


class GoogleSheetsExportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="export-google", email="export-google@example.com", role="business_owner")
        self.business = Business.objects.create(owner=self.user, name="Export", slug="google-export")
        self.connection = GoogleConnection.objects.create(business=self.business, actor=self.user, status="connected",
            encrypted_refresh=encrypt_credential_value("refresh"), encrypted_access=encrypt_credential_value("access"),
            access_expires_at=timezone.now()+timedelta(hours=1))
        Client.objects.create(business=self.business, full_name="=IMPORTXML(1)", phone="+77012223344")
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.key = str(uuid.uuid4())
        self.created = 0
        self.writes = []
        self.ambiguous = False
        self.fail_write = False
        self.remote = patch("apps.integrations.google_sheets_export.google_request", side_effect=self.respond).start()
        patch("apps.integrations.google_sheets_export.read_metadata", return_value={"sheets": [
            {"sheetId": 0, "gridProperties": {"rowCount": 1000, "columnCount": 26}}]}).start()
        self.addCleanup(patch.stopall)

    def respond(self, url, **kwargs):
        if "drive/v3/files?fields=id" in url:
            self.created += 1
            if self.ambiguous:
                raise GoogleError()
            return {"id": "export_spreadsheet_id"}
        if "drive/v3/files?" in url:
            return {"files": [{"id": "export_spreadsheet_id"}]}
        if self.fail_write:
            raise GoogleError()
        self.writes.append(kwargs["payload"])
        return {}

    def submit(self, **changes):
        return self.api.post(f"/api/integrations/google/connections/{self.connection.pk}/sheets/export/",
            {"request_key": self.key, **changes}, format="json")

    def test_create_replay_refresh_and_string_cells(self):
        response = self.submit()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["row_count"], 1)
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(self.submit(refresh=True).status_code, 200)
        self.assertEqual(self.created, 1)
        self.assertEqual(len(self.writes), 2)
        update = self.writes[0]["requests"][1]["updateCells"]
        self.assertEqual(update["range"], {"sheetId": 0})
        for row in update["rows"]:
            for cell in row["values"]:
                self.assertEqual(list(cell["userEnteredValue"]), ["stringValue"])

    def test_ambiguous_create_recovers_without_duplicate(self):
        self.ambiguous = True
        self.assertEqual(self.submit().status_code, 503)
        self.assertEqual(GoogleSheetTransfer.objects.get().status, "creating")
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(self.created, 1)

    def test_missing_recovery_result_never_recreates(self):
        self.ambiguous = True
        self.assertEqual(self.submit().status_code, 503)
        self.remote.return_value = {"files": []}
        self.remote.side_effect = None
        self.assertEqual(self.submit().status_code, 400)
        self.assertEqual(GoogleSheetTransfer.objects.get().status, "creating")
        self.assertNotEqual(self.remote.call_args.kwargs.get("method"), "POST")

    def test_failed_write_keeps_target_for_retry(self):
        self.fail_write = True
        self.assertEqual(self.submit().status_code, 503)
        self.assertEqual(GoogleSheetTransfer.objects.get().spreadsheet_id, "export_spreadsheet_id")
        self.fail_write = False
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(self.created, 1)

    def test_other_actor_cannot_export_or_read_history(self):
        other = get_user_model().objects.create_user(username="other-export", email="other-export@example.com", role="business_owner")
        self.api.force_authenticate(other)
        self.assertEqual(self.submit().status_code, 404)
        self.assertEqual(self.api.get(f"/api/integrations/google/connections/{self.connection.pk}/sheets/exports/").status_code, 404)
        self.assertFalse(self.remote.called)
