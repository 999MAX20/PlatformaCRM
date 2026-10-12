from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.tasks.models import Task
from apps.tasks import tests_workspace


@skipUnlessDBFeature("has_select_for_update")
class TaskConcurrentCommandsTests(TransactionTestCase):
    def test_same_version_allows_only_one_competing_change(self):
        fixture = tests_workspace.TaskWorkspaceTests()
        fixture.setUp()
        version = fixture.task.updated_at.isoformat()
        barrier = Barrier(2)

        def update(title):
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(fixture.owner)
                barrier.wait(timeout=15)
                result = api.patch(f"/api/tasks/{fixture.task.pk}/update-details/",
                                   {"title": title}, format="json", HTTP_X_TASK_VERSION=version)
                return result.status_code, title
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(update, title) for title in ("First edit", "Second edit")]
            results = [future.result(timeout=30) for future in pending]
        self.assertEqual(sorted(code for code, _ in results), [200, 409])
        winner = next(title for code, title in results if code == 200)
        self.assertEqual(Task.objects.get(pk=fixture.task.pk).title, winner)
