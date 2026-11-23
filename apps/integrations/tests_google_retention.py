import io
import uuid
from datetime import timedelta
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from django.utils import timezone

from apps.businesses.models import Business
from apps.core.models import AuditLog, ImportJob
from apps.integrations.google_calendar_models import GoogleCalendarBusy, GoogleCalendarMirror
from apps.integrations.google_models import (
    GoogleConnection, GoogleOAuthAttempt, GoogleRetentionFile, GoogleRetentionState, GoogleSheetTransfer,
)
from apps.integrations.google_retention import cleanup_google
from apps.integrations import google_oauth, google_calendar_service
from apps.integrations import tests_google_calendar as calendar_fixtures, tests_google_oauth as oauth_fixtures


class GoogleRetentionTests(TestCase):
    def setUp(self):
        self.now = timezone.now()
        self.actor = get_user_model().objects.create_user(username="retention-owner")
        self.business = Business.objects.create(owner=self.actor, name="Retention", slug="retention")
        self.connection = GoogleConnection.objects.create(business=self.business, actor=self.actor,
            status="connected", subject="private-subject", email="private@example.test")

    def snapshot(self, age=7, *, imported=False, connection=None):
        connection = connection or self.connection
        job = ImportJob.objects.create(business=connection.business, actor=self.actor,
            source_file=SimpleUploadedFile("synthetic.csv", b"name,phone\nSynthetic,77010000000\n"),
            original_filename="private-name.csv", status="imported" if imported else "previewed",
            preview_json={"rows": [{"name": "Private"}]}, mapping_json={"full_name": "name"},
            duplicates_json={"rows": [{"email": "private@example.test"}]}, error="private detail")
        stamp = self.now - timedelta(days=age)
        ImportJob.objects.filter(pk=job.pk).update(created_at=stamp, updated_at=stamp,
            imported_at=stamp if imported else None)
        GoogleSheetTransfer.objects.create(connection=connection, kind="import", import_job=job,
            request_key=uuid.uuid4(), spreadsheet_id="synthetic-spreadsheet")
        job.refresh_from_db()
        return job

    def test_dry_run_is_read_only_and_no_sensitive_output(self):
        job = self.snapshot()
        out = io.StringIO()
        call_command("cleanup_google_data", stdout=out)
        self.assertIn('"snapshots_due": 1', out.getvalue())
        self.assertNotIn("private", out.getvalue())
        job.refresh_from_db()
        self.assertTrue(job.source_file.storage.exists(job.source_file.name))
        self.assertEqual(job.status, "previewed")
        self.assertFalse(GoogleRetentionFile.objects.exists())
        self.assertFalse(GoogleRetentionState.objects.exists())

    def test_snapshot_boundaries_preserve_terminal_summary_and_crm(self):
        expired = self.snapshot()
        young = self.snapshot(age=6)
        completed = self.snapshot(age=30, imported=True)
        recent_completed = self.snapshot(age=29, imported=True)
        names = [expired.source_file.name, completed.source_file.name]
        result = cleanup_google(apply=True, now=self.now)
        self.assertEqual(result["snapshots"], 2)
        self.assertEqual(result["files_deleted"], 2)
        for name in names:
            self.assertFalse(expired.source_file.storage.exists(name))
        expired.refresh_from_db(); completed.refresh_from_db()
        self.assertEqual(expired.status, "cancelled")
        self.assertEqual(completed.status, "imported")
        self.assertTrue(completed.preview_json["retention_expired"])
        self.assertNotIn("rows", completed.preview_json)
        self.assertEqual(expired.duplicates_json, {})
        self.assertEqual(expired.original_filename, "")
        for job in (young, recent_completed):
            job.refresh_from_db()
            self.assertTrue(job.source_file)
        self.assertEqual(cleanup_google(apply=True, now=self.now)["snapshots"], 0)
        self.assertIsNotNone(GoogleRetentionState.objects.get().last_success_at)

    def test_storage_failure_is_durable_and_retryable(self):
        job = self.snapshot()
        storage = job.source_file.storage
        name = job.source_file.name
        with patch.object(storage, "delete", side_effect=OSError("private storage detail")):
            result = cleanup_google(apply=True, now=self.now)
        self.assertEqual(result["files_failed"], 1)
        pending = GoogleRetentionFile.objects.get()
        self.assertEqual(pending.error_code, "storage_delete_failed")
        self.assertEqual(pending.attempts, 1)
        self.assertTrue(storage.exists(name))
        job.refresh_from_db()
        self.assertFalse(job.source_file)
        self.assertTrue(job.preview_json["retention_expired"])
        self.assertNotIn("private storage", str(result))
        self.assertEqual(cleanup_google(apply=True, now=self.now)["files_deleted"], 0)
        self.assertEqual(cleanup_google(apply=True, now=self.now+timedelta(minutes=5))["files_deleted"], 1)
        self.assertFalse(storage.exists(name))
        self.assertFalse(GoogleRetentionFile.objects.exists())

    def test_summary_expires_without_removing_replay_tombstone(self):
        old = self.snapshot(age=90, imported=True)
        recent = self.snapshot(age=89, imported=True)
        transfer = GoogleSheetTransfer.objects.get(import_job=old)
        result = cleanup_google(apply=True, now=self.now)
        self.assertEqual(result["summaries"], 1)
        self.assertFalse(ImportJob.objects.filter(pk=old.pk).exists())
        self.assertTrue(ImportJob.objects.filter(pk=recent.pk).exists())
        transfer.refresh_from_db()
        self.assertEqual(transfer.status, "expired")
        self.assertIsNone(transfer.import_job_id)
        self.assertEqual(transfer.spreadsheet_id, "")
        self.assertEqual(cleanup_google(apply=True, now=self.now)["summaries"], 0)

    def test_mismatched_tenant_reference_is_not_cleaned(self):
        job = self.snapshot(age=100, imported=True)
        other = Business.objects.create(owner=self.actor, name="Other", slug="other-retention")
        ImportJob.objects.filter(pk=job.pk).update(business=other)
        self.assertEqual(cleanup_google(apply=True, now=self.now)["snapshots"], 0)
        job.refresh_from_db()
        self.assertTrue(job.source_file)

    def test_shared_file_and_unrelated_import_are_preserved(self):
        job = self.snapshot()
        unrelated = ImportJob.objects.create(business=self.business, source_file=job.source_file.name)
        result = cleanup_google(apply=True, now=self.now)
        self.assertEqual(result["files_protected"], 1)
        self.assertTrue(unrelated.source_file.storage.exists(unrelated.source_file.name))
        self.assertTrue(ImportJob.objects.filter(pk=unrelated.pk).exists())

    def test_business_scope_and_batch_are_bounded(self):
        self.snapshot(); self.snapshot()
        other = Business.objects.create(owner=self.actor, name="Other", slug="other-retention")
        connection = GoogleConnection.objects.create(business=other, actor=self.actor)
        foreign = self.snapshot(connection=connection)
        result = cleanup_google(apply=True, business_id=self.business.pk, batch_size=1, now=self.now)
        self.assertEqual(result["snapshots"], 1)
        self.assertEqual(result["remaining"]["snapshots_due"], 1)
        foreign.refresh_from_db()
        self.assertTrue(foreign.source_file)
        self.assertFalse(GoogleRetentionState.objects.exists())

    def test_attempt_and_audit_cutoffs_only_google_technical_records(self):
        old = GoogleOAuthAttempt.objects.create(connection=self.connection, revision=uuid.uuid4(),
            encrypted_verifier="synthetic", redirect_uri="https://example.test")
        fresh = GoogleOAuthAttempt.objects.create(connection=self.connection, revision=uuid.uuid4(),
            encrypted_verifier="synthetic", redirect_uri="https://example.test")
        GoogleOAuthAttempt.objects.filter(pk=old.pk).update(created_at=self.now-timedelta(hours=24))
        for entity, provider in [("GoogleConnection", "google_sheets"), ("Client", "google_sheets"), ("GoogleConnection", "other")]:
            audit = AuditLog.objects.create(business=self.business, action="update", category="integration",
                entity_type=entity, metadata={"provider": provider})
            AuditLog.objects.filter(pk=audit.pk).update(created_at=self.now-timedelta(days=90))
        result = cleanup_google(apply=True, now=self.now)
        self.assertEqual(result["attempts"], 1)
        self.assertEqual(result["audits"], 1)
        self.assertTrue(GoogleOAuthAttempt.objects.filter(pk=fresh.pk).exists())
        self.assertEqual(AuditLog.objects.count(), 2)

    def test_cleanup_headroom_respects_maximum_age_without_waiting_for_deadline(self):
        attempts = [GoogleOAuthAttempt.objects.create(connection=self.connection, revision=uuid.uuid4(),
            encrypted_verifier="synthetic", redirect_uri="https://example.test") for _ in range(2)]
        GoogleOAuthAttempt.objects.filter(pk=attempts[0].pk).update(created_at=self.now-timedelta(hours=23, minutes=50))
        GoogleOAuthAttempt.objects.filter(pk=attempts[1].pk).update(created_at=self.now-timedelta(hours=23, minutes=49))
        self.assertEqual(cleanup_google(apply=True, now=self.now)["attempts"], 1)
        self.assertTrue(GoogleOAuthAttempt.objects.filter(pk=attempts[1].pk).exists())

    def test_disconnected_identity_and_transfer_tombstones(self):
        self.connection.status = "disconnected"
        self.connection.disconnected_at = self.now-timedelta(days=30)
        self.connection.save()
        transfer = GoogleSheetTransfer.objects.create(connection=self.connection, kind="export",
            request_key=uuid.uuid4(), spreadsheet_id="private-sheet-id", status="succeeded")
        result = cleanup_google(apply=True, now=self.now)
        self.assertEqual(result["connections"], 1)
        self.connection.refresh_from_db(); transfer.refresh_from_db()
        self.assertTrue(self.connection.subject.startswith("sha256:"))
        self.assertEqual(self.connection.email, "")
        self.assertEqual(len(self.connection.subject), 71)
        self.assertEqual(transfer.status, "expired")
        self.assertEqual(transfer.spreadsheet_id, "")
        self.assertEqual(cleanup_google(apply=True, now=self.now)["connections"], 0)

    @override_settings(GOOGLE_RETENTION_ENABLED=False)
    def test_scheduler_is_disabled_until_activation(self):
        from apps.integrations.tasks import cleanup_google_data
        self.snapshot()
        self.assertEqual(cleanup_google_data(), {"enabled": False})
        self.assertFalse(GoogleRetentionState.objects.exists())

    def test_failed_file_does_not_starve_later_queue_entries(self):
        first = self.snapshot()
        self.snapshot()
        storage = first.source_file.storage
        original = storage.delete
        def fail_first(name):
            if name == first.source_file.name:
                raise OSError("unavailable")
            return original(name)
        with patch.object(storage, "delete", side_effect=fail_first):
            self.assertEqual(cleanup_google(apply=True, batch_size=1, now=self.now)["files_failed"], 1)
            self.assertEqual(cleanup_google(apply=True, batch_size=1, now=self.now)["files_deleted"], 1)

    def test_connection_transfer_scrub_remains_bounded_and_finishes(self):
        self.connection.status = "disconnected"
        self.connection.disconnected_at = self.now-timedelta(days=31)
        self.connection.save()
        for _ in range(2):
            GoogleSheetTransfer.objects.create(connection=self.connection, kind="export",
                request_key=uuid.uuid4(), status="creating")
        self.assertEqual(cleanup_google(apply=True, batch_size=1, now=self.now)["connections"], 1)
        self.assertEqual(GoogleSheetTransfer.objects.filter(status="expired").count(), 1)
        self.assertEqual(cleanup_google(apply=True, batch_size=1, now=self.now)["connections"], 1)
        self.assertEqual(GoogleSheetTransfer.objects.filter(status="expired").count(), 2)

    @override_settings(GOOGLE_RETENTION_ENABLED=True)
    def test_health_check_detects_missing_stale_and_pending_cleanup(self):
        with self.assertRaises(CommandError):
            call_command("cleanup_google_data", check=True, stdout=io.StringIO())
        cleanup_google(apply=True)
        call_command("cleanup_google_data", check=True, stdout=io.StringIO())
        GoogleRetentionState.objects.update(last_success_at=timezone.now()-timedelta(minutes=16))
        with self.assertRaises(CommandError):
            call_command("cleanup_google_data", check=True, stdout=io.StringIO())


@override_settings(GOOGLE_CALENDAR_ENABLED=True)
class CalendarRetentionTests(TestCase):
    setUp = calendar_fixtures.CalendarSyncTests.setUp
    write = calendar_fixtures.CalendarSyncTests.write
    delete = calendar_fixtures.CalendarSyncTests.delete
    run_sync = calendar_fixtures.CalendarSyncTests.run_sync

    def test_pause_and_disconnect_clear_busy_but_preserve_mirror_ids(self):
        self.run_sync()
        mirror = GoogleCalendarMirror.objects.get()
        original = (mirror.pk, mirror.event_id, mirror.generation)
        GoogleCalendarBusy.objects.create(binding=self.binding, start_at=self.start, end_at=self.start+timedelta(hours=1))
        google_calendar_service.set_enabled(self.connection, self.actor, binding_id=self.binding.pk, enabled=False)
        self.assertFalse(self.binding.busy.exists())
        google_calendar_service.set_enabled(self.connection, self.actor, binding_id=self.binding.pk, enabled=True)
        GoogleCalendarBusy.objects.create(binding=self.binding, start_at=self.start, end_at=self.start+timedelta(hours=1))
        with patch.object(google_oauth, "google_request", return_value={}):
            google_oauth.disconnect(self.connection, self.actor)
        self.assertFalse(self.binding.busy.exists())
        self.connection.refresh_from_db()
        self.connection.subject = "calendar-subject"
        self.connection.disconnected_at = timezone.now()-timedelta(days=31)
        self.connection.save()
        cleanup_google(apply=True)
        mirror.refresh_from_db()
        self.assertEqual((mirror.pk, mirror.event_id, mirror.generation), original)
        self.assertTrue(self.appointment.__class__.objects.filter(pk=self.appointment.pk).exists())
        self.assertFalse(self.delete_mock.called)
        self.connection.refresh_from_db()
        self.connection.status = "connected"
        self.connection.encrypted_access = calendar_fixtures.encrypt_credential_value("access")
        self.connection.encrypted_refresh = calendar_fixtures.encrypt_credential_value("refresh")
        self.connection.access_expires_at = timezone.now()+timedelta(hours=1)
        self.connection.save()
        self.run_sync()
        mirror.refresh_from_db()
        self.assertEqual((mirror.pk, mirror.event_id, mirror.generation), original)
        self.assertEqual(self.write_mock.call_count, 1)
        self.binding.refresh_from_db()
        self.assertEqual(self.binding.calendar_name, "Work")


@override_settings(GOOGLE_INTEGRATION_CLIENT_ID="google-client", GOOGLE_INTEGRATION_CLIENT_SECRET="private-secret",
                   GOOGLE_INTEGRATION_REDIRECT_URI="https://crm.example.com/app/integrations/google/callback")
class RetainedIdentityOAuthTests(TestCase):
    setUp = oauth_fixtures.GoogleOAuthTests.setUp
    respond = oauth_fixtures.GoogleOAuthTests.respond
    start = oauth_fixtures.GoogleOAuthTests.start
    complete = oauth_fixtures.GoogleOAuthTests.complete

    def test_cleaned_identity_accepts_same_account_and_rejects_another(self):
        self.assertEqual(self.complete(self.start()["state"][0]).status_code, 200)
        connection = GoogleConnection.objects.get()
        google_oauth.disconnect(connection, self.user)
        GoogleConnection.objects.filter(pk=connection.pk).update(disconnected_at=timezone.now()-timedelta(days=31))
        cleanup_google(apply=True)
        connection.refresh_from_db()
        self.assertTrue(connection.subject.startswith("sha256:"))
        original = self.respond
        self.remote.side_effect = lambda url, **kw: ({"sub": "wrong", "email": "wrong@example.test", "email_verified": True}
            if url.endswith("userinfo") else original(url, **kw))
        self.assertEqual(self.complete(self.start()["state"][0]).status_code, 400)
        self.remote.side_effect = original
        self.assertEqual(self.complete(self.start()["state"][0]).status_code, 200)
        connection.refresh_from_db()
        self.assertIsNone(connection.disconnected_at)

    def test_expired_export_replay_cannot_create_file(self):
        self.assertEqual(self.complete(self.start()["state"][0]).status_code, 200)
        connection = GoogleConnection.objects.get()
        transfer = GoogleSheetTransfer.objects.create(connection=connection, kind="export",
            request_key=uuid.uuid4(), status="expired")
        self.remote.reset_mock()
        with patch("apps.integrations.google_sheets_export.google_request") as provider:
            response = self.api.post(f"/api/integrations/google/connections/{connection.pk}/sheets/export/",
                {"request_key": str(transfer.request_key)}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(provider.called)
