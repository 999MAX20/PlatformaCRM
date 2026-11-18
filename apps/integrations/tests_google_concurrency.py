from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from urllib.parse import parse_qs, urlsplit

from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.core.models import ImportJob
from apps.integrations.google_models import GoogleConnection, GoogleSheetTransfer
from apps.integrations import tests_google_oauth as oauth_fixtures
from apps.integrations import tests_google_sheets as import_fixtures
from apps.integrations import tests_google_sheets_export as export_fixtures


def race(user, path, payload):
    barrier = Barrier(2)

    def submit():
        close_old_connections()
        try:
            api = APIClient()
            api.force_authenticate(user)
            barrier.wait(timeout=15)
            response = api.post(path, payload, format="json")
            return response.status_code
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(submit) for _ in range(2)]
        return sorted(future.result(timeout=40) for future in futures)


@skipUnlessDBFeature("has_select_for_update")
@override_settings(GOOGLE_INTEGRATION_CLIENT_ID="google-client", GOOGLE_INTEGRATION_CLIENT_SECRET="private-secret",
                   GOOGLE_INTEGRATION_REDIRECT_URI="https://crm.example.com/app/integrations/google/callback")
class GoogleOAuthConcurrencyTests(TransactionTestCase):
    setUp = oauth_fixtures.GoogleOAuthTests.setUp
    respond = oauth_fixtures.GoogleOAuthTests.respond

    def test_callback_consumed_once(self):
        response = self.api.post("/api/integrations/google/start/", {"business": self.business.pk}, format="json")
        state = parse_qs(urlsplit(response.data["authorization_url"]).query)["state"][0]
        self.assertEqual(race(self.user, "/api/integrations/google/complete/", {"state": state, "code": "code"}), [200, 400])
        self.assertEqual(self.remote.call_count, 2)
        self.assertEqual(GoogleConnection.objects.get().status, "connected")


@skipUnlessDBFeature("has_select_for_update")
class GoogleExportConcurrencyTests(TransactionTestCase):
    setUp = export_fixtures.GoogleSheetsExportTests.setUp
    respond = export_fixtures.GoogleSheetsExportTests.respond

    def test_parallel_export_creates_and_writes_once(self):
        statuses = race(self.user, f"/api/integrations/google/connections/{self.connection.pk}/sheets/export/",
                        {"request_key": self.key})
        self.assertEqual(statuses, [200, 200])
        self.assertEqual(self.created, 1)
        self.assertEqual(len(self.writes), 1)
        self.assertEqual(GoogleSheetTransfer.objects.count(), 1)


@skipUnlessDBFeature("has_select_for_update")
class GoogleImportConcurrencyTests(TransactionTestCase):
    setUp = import_fixtures.GoogleSheetsImportTests.setUp
    respond = import_fixtures.GoogleSheetsImportTests.respond

    def test_parallel_import_reads_one_snapshot(self):
        statuses = race(self.user, f"/api/integrations/google/connections/{self.connection.pk}/sheets/import/",
                        {"request_key": self.key, "file_id": "selected_google_file", "sheet_id": 0})
        self.assertEqual(statuses, [200, 200])
        self.assertEqual(self.remote.call_count, 2)
        self.assertEqual(GoogleSheetTransfer.objects.count(), 1)
        self.assertEqual(ImportJob.objects.count(), 1)
