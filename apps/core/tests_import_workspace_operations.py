from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.core import tests_import_workspace_engine as fixtures
from apps.core.import_workspace.operations import request_operation, process_operation, enqueue
from apps.core.import_workspace.drafts import correct_source, StaleImportVersion
from apps.clients.models import Client


class ImportOperationTests(TestCase):
    setUp = fixtures.ImportWorkspaceEngineTests.setUp
    source = fixtures.ImportWorkspaceEngineTests.source

    def schedule(self, action):
        self.workspace.refresh_from_db()
        self.workspace = request_operation(workspace_id=self.workspace.pk, actor=self.owner,
            version=self.workspace.version, action=action)
        return self.workspace.operation_json["id"]

    def test_background_preview_and_confirmation_replay_once(self):
        source = self.source("clients", [{"full_name": "Imported"}])
        operation = self.schedule("preview")
        self.assertEqual(self.schedule("preview"), operation)
        with self.assertRaises(StaleImportVersion):
            correct_source(workspace_id=self.workspace.pk, source_id=source.pk, actor=self.owner,
                version=self.workspace.version, corrections={}, excluded=[])
        process_operation(self.workspace.pk, operation)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.state, "ready")
        self.assertEqual(self.workspace.operation_json["status"], "succeeded")
        self.assertFalse(Client.objects.exists())
        operation = self.schedule("confirm")
        process_operation(self.workspace.pk, operation)
        process_operation(self.workspace.pk, operation)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.state, "imported")
        self.assertEqual(Client.objects.count(), 1)

    def test_worker_failure_rolls_back_and_can_be_retried(self):
        self.source("clients", [{"full_name": "Imported"}])
        operation = self.schedule("preview")
        with patch("apps.core.import_workspace.engine.ImportRunner.run", side_effect=RuntimeError("private source text")):
            process_operation(self.workspace.pk, operation)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.operation_json["error"], "operation_failed")
        self.assertNotIn("private", str(self.workspace.operation_json))
        retry = self.schedule("preview")
        self.assertNotEqual(retry, operation)
        process_operation(self.workspace.pk, operation)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.operation_json["status"], "pending")
        process_operation(self.workspace.pk, retry)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.state, "ready")

    def test_stale_running_attempt_is_reclaimed_but_fresh_attempt_is_not(self):
        self.source("clients", [{"full_name": "Imported"}])
        operation = self.schedule("preview")
        self.workspace.operation_json.update(status="running", started_at=timezone.now().isoformat(), claim_token="old")
        self.workspace.save()
        process_operation(self.workspace.pk, operation)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.operation_json["claim_token"], "old")
        self.workspace.operation_json["started_at"] = (timezone.now() - timezone.timedelta(minutes=6)).isoformat()
        self.workspace.save()
        process_operation(self.workspace.pk, operation)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.operation_json["status"], "succeeded")
        self.assertNotEqual(self.workspace.operation_json["claim_token"], "old")

    def test_queue_failure_is_visible_and_does_not_change_business_data(self):
        self.source("clients", [{"full_name": "Imported"}])
        operation = self.schedule("preview")
        with patch("apps.core.tasks.process_import_workspace_task.delay", side_effect=RuntimeError("private broker detail")):
            enqueue(self.workspace.pk, operation)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.operation_json["status"], "failed")
        self.assertEqual(self.workspace.operation_json["error"], "queue_unavailable")
        self.assertFalse(Client.objects.exists())

    def test_actor_disabled_after_enqueue_cannot_process_source(self):
        self.source("clients", [{"full_name": "Imported"}])
        operation = self.schedule("preview")
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        process_operation(self.workspace.pk, operation)
        self.workspace.refresh_from_db()
        self.assertEqual(self.workspace.operation_json["status"], "failed")
        self.assertEqual(self.workspace.operation_json["error"], "access_changed")
        self.assertFalse(Client.objects.exists())
