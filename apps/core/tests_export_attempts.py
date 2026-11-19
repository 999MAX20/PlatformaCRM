from unittest.mock import patch
from concurrent.futures import ThreadPoolExecutor
from threading import Event, current_thread

from django.db import connection, connections
from django.db.models.query import QuerySet
from django.db.migrations.executor import MigrationExecutor
from django.http import HttpResponse
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.core.export_jobs import process_export_job, request_entity_export
from apps.core.models import ExportJob


class ExportAttemptTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="attempt-owner", email="attempt@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Attempts", slug="attempts")
        self.job = ExportJob.objects.create(business=self.business, actor=self.owner, kind="entity", export_key="clients")
        self.storage = self.job.result_file.storage
        self.addCleanup(self.cleanup_files)
        self.files = []

    def cleanup_files(self):
        for name in self.files:
            self.storage.delete(name)

    def reclaim_and_succeed(self):
        ExportJob.objects.filter(pk=self.job.pk).update(started_at=timezone.now() - timezone.timedelta(days=1))
        with patch("apps.core.export_jobs.export_entity_response", return_value=HttpResponse(b"name\nnew winner\n")):
            winner = process_export_job(self.job.pk)
        self.files.append(winner.result_file.name)
        return winner

    def assert_winner(self, winner):
        self.job.refresh_from_db()
        self.files.append(self.job.result_file.name)
        self.assertEqual(self.job.status, "succeeded")
        self.assertEqual(self.job.result_file.name, winner.result_file.name)
        self.assertEqual(self.job.completed_at, winner.completed_at)
        self.assertEqual(self.job.parameters_json, winner.parameters_json)
        with self.storage.open(self.job.result_file.name) as stream:
            self.assertEqual(stream.read(), b"name\nnew winner\n")

    def test_stale_success_cannot_replace_winner(self):
        winners = []
        def generate(*args, **kwargs):
            winners.append(self.reclaim_and_succeed())
            return HttpResponse(b"name\nold result\n")
        with patch("apps.core.export_jobs.export_entity_response", side_effect=generate):
            returned = process_export_job(self.job.pk)
        self.files.append(returned.result_file.name)
        self.assert_winner(winners[0])
        api = APIClient()
        api.force_authenticate(self.owner)
        detail = api.get(f"/api/export-jobs/{self.job.pk}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("claim_token", detail.data)
        download = api.get(f"/api/export-jobs/{self.job.pk}/download/")
        self.assertEqual(download.status_code, 200)
        self.assertEqual(b"".join(download.streaming_content), b"name\nnew winner\n")
        download.close()

    def test_stale_failure_cannot_mark_new_success_failed(self):
        winners = []
        def generate(*args, **kwargs):
            winners.append(self.reclaim_and_succeed())
            raise ValueError("old attempt failure")
        with patch("apps.core.export_jobs.export_entity_response", side_effect=generate):
            process_export_job(self.job.pk)
        self.assert_winner(winners[0])

    def test_current_failure_and_explicit_requeue_can_succeed(self):
        with patch("apps.core.export_jobs.export_entity_response", side_effect=ValueError("generation failed")):
            failed = process_export_job(self.job.pk)
        self.assertEqual(failed.status, "failed")
        self.assertFalse(failed.result_file)
        ExportJob.objects.filter(pk=self.job.pk).update(status="pending")
        with patch("apps.core.export_jobs.export_entity_response", return_value=HttpResponse(b"name\nretry\n")):
            result = process_export_job(self.job.pk)
        self.files.append(result.result_file.name)
        self.assertEqual(result.status, "succeeded")
        self.assertEqual(result.error, "")

    def test_claim_lost_after_storage_save_deletes_only_own_file(self):
        save = self.storage.save
        outputs, winners = [], []
        def write(name, content, **kwargs):
            saved = save(name, content, **kwargs)
            outputs.append(saved)
            self.files.append(saved)
            if len(outputs) == 1:
                winners.append(self.reclaim_and_succeed())
            return saved
        with patch.object(self.storage, "save", side_effect=write), \
             patch("apps.core.export_jobs.export_entity_response", return_value=HttpResponse(b"name\nold\n")):
            process_export_job(self.job.pk)
        self.assert_winner(winners[0])
        self.assertNotEqual(outputs[0], winners[0].result_file.name)
        self.assertFalse(self.storage.exists(outputs[0]))
        self.assertTrue(self.storage.exists(winners[0].result_file.name))

    def test_database_finalize_failure_cleans_unpublished_output(self):
        update, save = QuerySet.update, self.storage.save
        outputs = []
        def write(name, content, **kwargs):
            saved = save(name, content, **kwargs)
            outputs.append(saved)
            self.files.append(saved)
            return saved
        def finalize(query, **kwargs):
            if query.model is ExportJob and kwargs.get("status") == "succeeded":
                raise RuntimeError("synthetic finalization failure")
            return update(query, **kwargs)
        with patch.object(QuerySet, "update", finalize), patch.object(self.storage, "save", side_effect=write), \
             patch("apps.core.export_jobs.export_entity_response", return_value=HttpResponse(b"name\noutput\n")):
            result = process_export_job(self.job.pk)
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.result_file)
        self.assertEqual(len(outputs), 1)
        self.assertFalse(self.storage.exists(outputs[0]))

    def test_current_running_claim_cannot_be_claimed_twice(self):
        def generate(*args, **kwargs):
            current = process_export_job(self.job.pk)
            self.assertEqual(current.status, "running")
            self.assertIsNotNone(current.claim_token)
            return HttpResponse(b"name\nonce\n")
        with patch("apps.core.export_jobs.export_entity_response", side_effect=generate) as generator:
            result = process_export_job(self.job.pk)
        self.files.append(result.result_file.name)
        self.assertEqual(generator.call_count, 1)
        self.assertEqual(result.status, "succeeded")

    @override_settings(EXPORT_SYNC_MAX_ROWS=0, EXPORT_MAX_ROWS=1)
    def test_growth_after_enqueue_rejects_export_before_generation(self):
        Client.objects.create(business=self.business, full_name="First")
        _, job = request_entity_export(business=self.business, actor=self.owner, export_key="clients")
        Client.objects.create(business=self.business, full_name="Second")
        with patch("apps.core.export_jobs.export_entity_response") as generate:
            result = process_export_job(job.pk)
        self.assertEqual(result.status, "failed")
        self.assertIn("cannot exceed", result.error)
        self.assertFalse(result.result_file)
        generate.assert_not_called()

    @override_settings(EXPORT_MAX_ROWS=1)
    def test_growth_during_generation_does_not_publish_over_limit(self):
        with patch("apps.core.export_jobs.export_entity_response", return_value=HttpResponse(b"name\nfirst\nsecond\n")), \
             patch.object(self.storage, "save") as save:
            result = process_export_job(self.job.pk)
        self.assertEqual(result.status, "failed")
        self.assertFalse(result.result_file)
        save.assert_not_called()

    @override_settings(EXPORT_MAX_ROWS=1)
    def test_exact_limit_counts_multiline_quoted_csv_as_one_record(self):
        Client.objects.create(business=self.business, full_name='First\n"Second"\r\nThird')
        result = process_export_job(self.job.pk)
        self.files.append(result.result_file.name)
        self.assertEqual(result.status, "succeeded", result.error)
        self.assertEqual(result.row_count, 1)

    @override_settings(EXPORT_MAX_ROWS=1)
    def test_empty_export_succeeds_with_zero_records(self):
        result = process_export_job(self.job.pk)
        self.files.append(result.result_file.name)
        self.assertEqual(result.status, "succeeded", result.error)
        self.assertEqual(result.row_count, 0)

    @override_settings(EXPORT_MAX_ROWS=1)
    def test_large_text_field_preserves_export_and_record_count(self):
        notes = 'Long notes with "quotes"\r\nand newlines\n' * 6000
        Client.objects.create(business=self.business, full_name="Large notes", notes=notes)
        result = process_export_job(self.job.pk)
        self.files.append(result.result_file.name)
        self.assertEqual(result.status, "succeeded", result.error)
        self.assertEqual(result.row_count, 1)
        with self.storage.open(result.result_file.name) as stream:
            self.assertIn(notes.replace('"', '""').encode(), stream.read())


@skipUnlessDBFeature("has_select_for_update")
class ExportAttemptConcurrencyTests(TransactionTestCase):
    cleanup_files = ExportAttemptTests.cleanup_files
    assert_winner = ExportAttemptTests.assert_winner

    def setUp(self):
        ExportAttemptTests.setUp(self)

    def race(self, fail):
        main = current_thread()
        generating, newer_done = Event(), Event()
        original_save = self.storage.save
        outputs = []
        def write(name, content, **kwargs):
            saved = original_save(name, content, **kwargs)
            outputs.append(saved)
            self.files.append(saved)
            return saved
        def generate(*args, **kwargs):
            if current_thread() is main:
                return HttpResponse(b"name\nnew winner\n")
            generating.set()
            self.assertTrue(newer_done.wait(20))
            if fail:
                raise ValueError("stale worker failed")
            return HttpResponse(b"name\nold result\n")
        def worker():
            connections.close_all()
            try:
                return process_export_job(self.job.pk)
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=1) as pool, patch.object(self.storage, "save", side_effect=write), \
             patch("apps.core.export_jobs.export_entity_response", side_effect=generate):
            future = pool.submit(worker)
            self.assertTrue(generating.wait(20))
            old_token = ExportJob.objects.get(pk=self.job.pk).claim_token
            try:
                ExportJob.objects.filter(pk=self.job.pk).update(started_at=timezone.now() - timezone.timedelta(days=1))
                winner = process_export_job(self.job.pk)
            finally:
                newer_done.set()
            returned = future.result(timeout=25)
        self.assertNotEqual(old_token, winner.claim_token)
        self.assertEqual(returned.result_file.name, winner.result_file.name)
        self.assert_winner(winner)
        for name in outputs:
            self.assertEqual(self.storage.exists(name), name == winner.result_file.name)

    def test_old_success_after_new_worker_commit(self):
        self.race(False)

    def test_old_failure_after_new_worker_commit(self):
        self.race(True)


class ExportAttemptMigrationTests(TransactionTestCase):
    def test_existing_export_result_and_history_survive_nullable_token(self):
        owner = User.objects.create_user(username="migration-export", email="migration-export@example.test")
        business = Business.objects.create(owner=owner, name="Existing exports", slug="existing-exports")
        job = ExportJob.objects.create(business=business, actor=owner, kind="entity", export_key="clients",
            status="succeeded", result_file="exports/existing.csv", row_count=17,
            parameters_json={"expected_rows": 17})
        executor = MigrationExecutor(connection)
        leaves = executor.loader.graph.leaf_nodes()
        previous = ("core", "0012_service_component_state")
        executor.migrate([previous])
        try:
            model = executor.loader.project_state([previous]).apps.get_model("core", "ExportJob")
            old = model.objects.get(pk=job.pk)
            self.assertEqual(old.result_file.name, "exports/existing.csv")
            before = old.created_at
        finally:
            MigrationExecutor(connection).migrate(leaves)
        job.refresh_from_db()
        self.assertIsNone(job.claim_token)
        self.assertEqual((job.status, job.row_count, job.parameters_json), ("succeeded", 17, {"expected_rows": 17}))
        self.assertEqual(job.result_file.name, "exports/existing.csv")
        self.assertEqual(job.created_at, before)
