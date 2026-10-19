from concurrent.futures import ThreadPoolExecutor
import tempfile
from threading import Barrier, local
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.models import ImportJob
from apps.integrations.models import BusinessEvent, ConnectorSyncRun


@skipUnlessDBFeature("has_select_for_update")
class ImportJobConcurrencyTests(TransactionTestCase):
    def setUp(self):
        media = tempfile.TemporaryDirectory()
        self.addCleanup(media.cleanup)
        settings = override_settings(MEDIA_ROOT=media.name)
        settings.enable()
        self.addCleanup(settings.disable)
        scanner = patch("apps.core.antivirus.scan_stream", return_value=SimpleNamespace(clean=True))
        scanner.start()
        self.addCleanup(scanner.stop)
        self.owner = User.objects.create_user(username="import-race", email="import-race@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Import race", slug="import-race")
        api = APIClient()
        api.force_authenticate(self.owner)
        response = api.post("/api/import-jobs/", {
            "business": self.business.pk, "entity_type": "clients",
            "source_file": SimpleUploadedFile("clients.csv", b"full_name\nConcurrent client\n", content_type="text/csv"),
        }, format="multipart")
        self.assertEqual(response.status_code, 201, response.data)
        self.job_id = response.data["id"]

    def race(self, actions):
        barrier, thread = Barrier(2), local()
        original = ImportJob.objects.select_for_update
        def lock(*args, **kwargs):
            if not getattr(thread, "ready", False):
                thread.ready = True
                barrier.wait(timeout=20)
            return original(*args, **kwargs)
        def run(action):
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(User.objects.get(pk=self.owner.pk))
                return api.post(f"/api/import-jobs/{self.job_id}/{action}/").status_code
            finally:
                close_old_connections()
        with patch.object(ImportJob.objects, "select_for_update", side_effect=lock):
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(run, action) for action in actions]
                return [future.result(timeout=45) for future in futures]

    def assert_imported_once(self):
        self.assertEqual(ImportJob.objects.get(pk=self.job_id).status, "imported")
        self.assertEqual(Client.objects.filter(business=self.business).count(), 1)
        self.assertEqual(ConnectorSyncRun.objects.filter(business=self.business).count(), 1)
        self.assertEqual(BusinessEvent.objects.filter(business=self.business, event_type="client.imported").count(), 1)

    def test_two_confirmations_execute_one_import(self):
        self.assertEqual(sorted(self.race(["confirm", "confirm"])), [200, 400])
        self.assert_imported_once()

    def test_preview_cannot_reopen_concurrent_confirmation(self):
        self.assertIn(self.race(["preview", "confirm"]), ([200, 200], [400, 200]))
        self.assert_imported_once()
