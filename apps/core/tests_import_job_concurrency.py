from concurrent.futures import ThreadPoolExecutor
import tempfile
from threading import Barrier, Event, local
from time import monotonic, sleep
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import close_old_connections, connection, transaction
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature
from rest_framework.test import APIClient
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core import import_export
from apps.core.models import AuditLog, ImportJob
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

    def assert_waiting_confirm_recovers(self, failure_point):
        written, release, waiter_started = Event(), Event(), Event()
        thread = local()
        waiter_pid = []
        committed_callbacks = []
        initial = ImportJob.objects.get(pk=self.job_id)
        original_lock = import_export._locked_import_job
        original_write = getattr(import_export, failure_point)

        def locked(*args, **kwargs):
            if thread.role == "waiting":
                with connection.cursor() as cursor:
                    cursor.execute("SELECT pg_backend_pid()")
                    waiter_pid.append(cursor.fetchone()[0])
                waiter_started.set()
            job = original_lock(*args, **kwargs)
            if thread.role == "waiting":
                self.assertEqual(job.status, initial.status)
                self.assertEqual(job.preview_json, initial.preview_json)
                self.assertEqual(job.imported_count, 0)
                self.assertIsNone(job.imported_at)
                self.assertFalse(Client.objects.filter(business=self.business).exists())
                self.assertFalse(ConnectorSyncRun.objects.filter(business=self.business).exists())
                self.assertFalse(BusinessEvent.objects.filter(business=self.business).exists())
                self.assertFalse(AuditLog.objects.filter(
                    business=self.business, metadata__kind="import_confirmed",
                ).exists())
            return job

        def write_then_fail(*args, **kwargs):
            result = original_write(*args, **kwargs)
            role = thread.role
            transaction.on_commit(lambda: committed_callbacks.append(role))
            if role == "failing":
                self.assertTrue(Client.objects.filter(business=self.business).exists())
                self.assertTrue(BusinessEvent.objects.filter(business=self.business).exists())
                self.assertTrue(ConnectorSyncRun.objects.filter(business=self.business).exists())
                if failure_point == "write_audit_log":
                    self.assertEqual(ImportJob.objects.get(pk=self.job_id).status, "imported")
                    self.assertTrue(AuditLog.objects.filter(
                        business=self.business, metadata__kind="import_confirmed",
                    ).exists())
                written.set()
                if not release.wait(timeout=20):
                    raise AssertionError("Waiting confirm never reached the PostgreSQL lock")
                raise ValidationError("Injected transactional import failure")
            return result

        def confirm(role):
            close_old_connections()
            thread.role = role
            try:
                api = APIClient()
                api.force_authenticate(User.objects.get(pk=self.owner.pk))
                return api.post(f"/api/import-jobs/{self.job_id}/confirm/").status_code
            finally:
                close_old_connections()

        with patch.object(import_export, "_locked_import_job", side_effect=locked), patch.object(
            import_export, failure_point, side_effect=write_then_fail,
        ), ThreadPoolExecutor(max_workers=2) as pool:
            failing = pool.submit(confirm, "failing")
            try:
                self.assertTrue(written.wait(timeout=20))
                waiting = pool.submit(confirm, "waiting")
                self.assertTrue(waiter_started.wait(timeout=20))
                deadline = monotonic() + 10
                blocked = False
                while monotonic() < deadline:
                    with connection.cursor() as cursor:
                        cursor.execute("SELECT cardinality(pg_blocking_pids(%s)) > 0", [waiter_pid[0]])
                        blocked = cursor.fetchone()[0]
                    if blocked:
                        break
                    sleep(0.02)
                self.assertTrue(blocked, "Second confirm must actually wait for the first transaction")
                self.assertFalse(waiting.done())
            finally:
                release.set()
            self.assertEqual(failing.result(timeout=20), 400)
            self.assertEqual(waiting.result(timeout=20), 200)

        self.assert_imported_once()
        job = ImportJob.objects.get(pk=self.job_id)
        self.assertEqual(job.imported_count, 1)
        self.assertEqual(job.preview_json["import_summary"]["created"], 1)
        self.assertIsNotNone(job.imported_at)
        sync = ConnectorSyncRun.objects.get(business=self.business)
        self.assertEqual(sync.status, ConnectorSyncRun.Statuses.SUCCEEDED)
        self.assertEqual(sync.events_processed, 1)
        self.assertEqual(AuditLog.objects.filter(
            business=self.business, metadata__kind="import_confirmed",
        ).count(), 1)
        self.assertEqual(committed_callbacks, ["waiting"])
        self.assertEqual(confirm("replay"), 400)
        self.assert_imported_once()

    def test_waiting_confirm_recovers_after_row_failure(self):
        self.assert_waiting_confirm_recovers("import_client_row")

    def test_waiting_confirm_recovers_after_final_audit_failure(self):
        self.assert_waiting_confirm_recovers("write_audit_log")
