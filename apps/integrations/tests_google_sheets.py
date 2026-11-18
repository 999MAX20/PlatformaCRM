import tempfile
import uuid
from datetime import timedelta
from unittest.mock import patch
from types import SimpleNamespace

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.models import ImportJob
from apps.integrations.credential_encryption import encrypt_credential_value
from apps.integrations.google_http import GoogleError
from apps.integrations.google_models import GoogleConnection, GoogleSheetTransfer


class GoogleSheetsImportTests(TestCase):
    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.settings = override_settings(MEDIA_ROOT=self.media.name)
        self.settings.enable()
        self.addCleanup(self.settings.disable)
        patch("apps.core.antivirus.scan_stream", return_value=SimpleNamespace(clean=True)).start()
        self.user = get_user_model().objects.create_user(username="sheets-owner", email="sheets@example.com", role="business_owner")
        self.business = Business.objects.create(owner=self.user, name="Sheets", slug="sheets-import")
        self.member = BusinessMember.objects.create(business=self.business, user=self.user, role="owner")
        self.connection = GoogleConnection.objects.create(business=self.business, actor=self.user, status="connected",
            encrypted_refresh=encrypt_credential_value("refresh"), encrypted_access=encrypt_credential_value("access"),
            access_expires_at=timezone.now()+timedelta(hours=1))
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.rows = [["full_name", "phone"], ["Example Client", "+77011112233"]]
        self.grid_rows = 1000
        self.remote = patch("apps.integrations.google_sheets.google_request", side_effect=self.respond).start()
        self.addCleanup(patch.stopall)
        self.key = str(uuid.uuid4())

    def respond(self, url, **kwargs):
        if "/values/" in url:
            return {"values": self.rows}
        return {"properties": {"title": "Clients"}, "sheets": [{"properties": {
            "sheetId": 0, "title": "Client's sheet", "sheetType": "GRID",
            "gridProperties": {"rowCount": self.grid_rows, "columnCount": 26}}}]}

    def submit(self, **changes):
        data = {"file_id": "selected_google_file", "sheet_id": 0, "request_key": self.key, **changes}
        return self.api.post(f"/api/integrations/google/connections/{self.connection.pk}/sheets/import/", data, format="json")

    def test_snapshot_replay_and_standard_confirm(self):
        response = self.submit()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "previewed")
        self.assertFalse(Client.objects.exists())
        self.assertEqual(self.submit().data["id"], response.data["id"])
        self.assertEqual(self.remote.call_count, 2)
        self.assertEqual(ImportJob.objects.count(), 1)
        self.assertEqual(GoogleSheetTransfer.objects.count(), 1)
        result = self.api.post(f'/api/import-jobs/{response.data["id"]}/confirm/', {}, format="json")
        self.assertEqual(result.status_code, 200, getattr(result, "data", None))
        self.assertEqual(Client.objects.count(), 1)

    def test_reused_key_different_source_rejected(self):
        self.assertEqual(self.submit().status_code, 200)
        self.assertEqual(self.submit(file_id="another_google_file").status_code, 400)
        self.assertEqual(ImportJob.objects.count(), 1)

    def test_limits_and_headers_do_not_create_partial_jobs(self):
        self.grid_rows = 6000
        self.assertEqual(self.submit().status_code, 400)
        self.assertEqual(self.remote.call_count, 1)
        self.grid_rows = 1000
        self.rows = [["phone", "phone"], ["a", "b"]]
        self.assertEqual(self.submit().status_code, 400)
        self.assertFalse(ImportJob.objects.exists())

    def test_remote_failure_is_safe_to_retry(self):
        self.remote.side_effect = GoogleError()
        self.assertEqual(self.submit().status_code, 503)
        self.assertFalse(ImportJob.objects.exists())
        self.remote.side_effect = self.respond
        self.assertEqual(self.submit().status_code, 200)

    def test_actor_isolation_and_disconnected_credentials(self):
        outsider = get_user_model().objects.create_user(username="sheet-other", email="sheet-other@example.com", role="business_owner")
        self.api.force_authenticate(outsider)
        self.assertEqual(self.submit().status_code, 404)
        self.assertFalse(self.remote.called)
        self.api.force_authenticate(self.user)
        self.connection.status = "disconnected"
        self.connection.save()
        self.assertEqual(self.submit().status_code, 400)
        self.assertFalse(self.remote.called)

    def test_integration_manager_without_client_rights_is_denied(self):
        staff = get_user_model().objects.create_user(username="sheets-staff", email="sheets-staff@example.com", role="staff")
        role = BusinessRole.objects.create(business=self.business, name="Integrations only")
        RolePermission.objects.create(business_role=role, resource="integrations", action="manage", scope="business")
        BusinessMember.objects.create(business=self.business, user=staff, role="specialist", business_role=role)
        self.connection.actor = staff
        self.connection.save()
        self.api.force_authenticate(staff)
        self.assertEqual(self.submit().status_code, 403)
        self.assertFalse(self.remote.called)

    def test_scanner_failure_rolls_back_snapshot_and_file(self):
        from apps.core.antivirus import ScanUnavailable
        from pathlib import Path
        with patch("apps.core.antivirus.scan_stream", side_effect=ScanUnavailable()):
            self.assertEqual(self.submit().status_code, 503)
        self.assertFalse(ImportJob.objects.exists())
        self.assertFalse(GoogleSheetTransfer.objects.exists())
        self.assertFalse(list(Path(self.media.name).rglob("*.csv")))
