from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase
from apps.accounts.models import User
from apps.businesses.models import Business


class TaskWorkspaceMigrationTests(TransactionTestCase):
    def test_existing_task_history_and_assignment_survive_additive_migration(self):
        user = User.objects.create_user(username="migration-owner", email="migration@example.test")
        business = Business.objects.create(name="Migration", owner=user)
        previous = [("tasks", "0010_scheduled_reminder_delivery")]
        current = [("tasks", "0011_task_specialist_task_waiting_reason_and_more")]
        executor = MigrationExecutor(connection)
        executor.migrate(previous)
        try:
            old = executor.loader.project_state(previous).apps
            task = old.get_model("tasks", "Task").objects.create(business_id=business.pk, title="Preserved task", status="done", assignee_id=user.pk, created_by_id=user.pk)
            task.watchers.add(user.pk)
            comment = old.get_model("tasks", "TaskComment").objects.create(task_id=task.pk, author_id=user.pk, text="Preserved comment")
            executor = MigrationExecutor(connection)
            executor.migrate(current)
            new = executor.loader.project_state(current).apps
            restored = new.get_model("tasks", "Task").objects.get(pk=task.pk)
            self.assertEqual((restored.title, restored.status, restored.assignee_id), ("Preserved task", "done", user.pk))
            self.assertEqual(restored.waiting_reason, "")
            self.assertIsNone(restored.waiting_until)
            self.assertIsNone(restored.specialist_id)
            self.assertEqual(list(restored.watchers.values_list("pk", flat=True)), [user.pk])
            self.assertEqual(new.get_model("tasks", "TaskComment").objects.get(pk=comment.pk).text, "Preserved comment")
        finally:
            MigrationExecutor(connection).migrate(current)
