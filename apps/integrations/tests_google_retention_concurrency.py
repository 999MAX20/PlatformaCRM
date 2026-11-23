import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Event
from unittest.mock import patch

from django.db import close_old_connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business
from apps.core import import_export, tests_client_import_permissions as fixtures
from apps.core.models import ImportJob
from apps.integrations.google_models import GoogleConnection, GoogleSheetTransfer
from apps.integrations.google_retention import cleanup_google


@skipUnlessDBFeature("has_select_for_update_skip_locked")
class GoogleRetentionConcurrencyTests(TransactionTestCase):
    setUp = fixtures.ClientImportPermissionTests.setUp
    upload = fixtures.ClientImportPermissionTests.upload

    def test_inflight_confirmation_keeps_snapshot_and_new_completion_deadline(self):
        job = self.upload([{"full_name": "Synthetic", "phone": "+77010000006"}])
        connection = GoogleConnection.objects.create(business=self.business, actor=self.actor)
        GoogleSheetTransfer.objects.create(connection=connection, kind="import", import_job=job,
            request_key=uuid.uuid4())
        ImportJob.objects.filter(pk=job.pk).update(created_at=timezone.now()-timedelta(days=8))
        entered, release = Event(), Event()
        original = import_export.read_tabular_file
        def paused_read(file):
            entered.set()
            if not release.wait(30):
                raise RuntimeError("Test release timed out")
            return original(file)
        def confirm():
            close_old_connections()
            try:
                api = APIClient(); api.force_authenticate(self.actor)
                return api.post(f"/api/import-jobs/{job.pk}/confirm/").status_code
            finally:
                close_old_connections()
        with patch.object(import_export, "read_tabular_file", side_effect=paused_read):
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(confirm)
                try:
                    self.assertTrue(entered.wait(15))
                    self.assertEqual(cleanup_google(apply=True)["snapshots"], 0)
                finally:
                    release.set()
                self.assertEqual(future.result(timeout=30), 200)
        self.assertEqual(cleanup_google(apply=True)["snapshots"], 0)
        job.refresh_from_db()
        self.assertEqual(job.status, "imported")
        self.assertTrue(job.source_file.storage.exists(job.source_file.name))

    def test_reconnect_wins_before_cleanup_lock_and_prevents_scrub(self):
        connection = GoogleConnection.objects.create(business=self.business, actor=self.actor,
            subject="keep-subject", email="keep@example.test", status="disconnected",
            disconnected_at=timezone.now()-timedelta(days=31))
        entered = Event()
        original = Business.objects.select_for_update
        def signal_lock(*args, **kwargs):
            entered.set()
            return original(*args, **kwargs)
        def cleanup():
            close_old_connections()
            try:
                return cleanup_google(apply=True)
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                Business.objects.select_for_update().get(pk=self.business.pk)
                with patch.object(Business.objects, "select_for_update", side_effect=signal_lock):
                    future = pool.submit(cleanup)
                    self.assertTrue(entered.wait(15))
                GoogleConnection.objects.filter(pk=connection.pk).update(status="connected", disconnected_at=None)
            self.assertEqual(future.result(timeout=30)["connections"], 0)
        connection.refresh_from_db()
        self.assertEqual(connection.subject, "keep-subject")
        self.assertEqual(connection.email, "keep@example.test")
