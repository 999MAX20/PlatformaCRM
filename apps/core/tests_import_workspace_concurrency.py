from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.accounts.models import User
from apps.clients.models import Client
from apps.core import tests_import_workspace_engine as fixtures
from apps.core.import_workspace.engine import confirm_workspace, preview_workspace
from apps.core.import_workspace.operations import process_operation, request_operation
from apps.core.models import ImportWorkspace
from apps.scheduling.models import Appointment


@skipUnlessDBFeature("has_select_for_update")
class ImportWorkspaceConcurrencyTests(TransactionTestCase):
    setUp = fixtures.ImportWorkspaceEngineTests.setUp
    source = fixtures.ImportWorkspaceEngineTests.source
    four_sources = fixtures.ImportWorkspaceEngineTests.four_sources

    def parallel(self, operation):
        barrier = Barrier(2)

        def execute():
            try:
                barrier.wait(timeout=10)
                return operation()
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(execute) for _ in range(2)]
            return [job.result(timeout=30) for job in jobs]

    def test_simultaneous_confirmation_creates_linked_records_once(self):
        self.four_sources()
        workspace = preview_workspace(workspace_id=self.workspace.pk, actor=self.owner, version=self.workspace.version)
        self.assertTrue(workspace.report_json["ready"], workspace.report_json)

        def confirm():
            actor = User.objects.get(pk=self.owner.pk)
            return confirm_workspace(workspace_id=workspace.pk, actor=actor, version=workspace.version).result_json

        outcomes = self.parallel(confirm)
        self.assertEqual(outcomes[0], outcomes[1])
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_duplicate_worker_delivery_finishes_one_operation(self):
        self.source("clients", [{"full_name": "Concurrent import"}])
        from unittest.mock import patch
        with patch("apps.core.import_workspace.operations.enqueue"):
            workspace = request_operation(workspace_id=self.workspace.pk, actor=self.owner,
                version=self.workspace.version, action="preview")
        operation_id = workspace.operation_json["id"]
        self.parallel(lambda: process_operation(workspace.pk, operation_id))
        workspace.refresh_from_db()
        self.assertEqual(workspace.operation_json["status"], "succeeded")
        self.assertEqual(workspace.state, ImportWorkspace.States.READY)
        self.assertFalse(Client.objects.exists())
