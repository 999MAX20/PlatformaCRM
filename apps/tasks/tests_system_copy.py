from types import SimpleNamespace
from django.test import TestCase
from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents
from apps.businesses.models import Business
from apps.scheduling.services import _appointment_follow_up_task_spec
from apps.tasks.models import Task
from apps.tasks.system_copy import follow_up_copy, follow_up_events


class SystemTaskCopyTests(TestCase):
    def test_generated_copy_preserves_edits_and_requires_matching_provenance(self):
        for status in ("cancelled", "no_show", "completed"):
            spec = _appointment_follow_up_task_spec(SimpleNamespace(id=9, status=status), reason="User reason")
            task = SimpleNamespace(pk=3, business_id=1, appointment_id=9,
                                   title=spec["title"], description=spec["description"])
            events = {(1, "3"): {"appointment_id": 9, "appointment_status": status, "reason": "User reason"}}
            self.assertEqual(follow_up_copy(task, events)["status"], status)
            self.assertIsNone(follow_up_copy(task, {}))
            self.assertIsNone(follow_up_copy(task, {(2, "3"): events[(1, "3")]}))
            task.title = "My title"
            self.assertFalse(follow_up_copy(task, events)["title"])
            task.description = "My notes"
            self.assertIsNone(follow_up_copy(task, events))

    def test_event_loading_is_batched_and_business_scoped(self):
        user = User.objects.create_user(username="system-copy", email="copy@example.com")
        business = Business.objects.create(owner=user, name="Copy", slug="copy")
        other = Business.objects.create(owner=user, name="Other", slug="other-copy")
        tasks = [Task.objects.create(business=business, title=f"Task {index}") for index in range(3)]
        for task in tasks:
            ActivityEvent.objects.create(business=business, event_type=ActivityEvents.TASK_CREATED,
                entity_type="Task", entity_id=str(task.pk), metadata={"appointment_id": 9})
        ActivityEvent.objects.create(business=other, event_type=ActivityEvents.TASK_CREATED,
            entity_type="Task", entity_id=str(tasks[0].pk), metadata={"reason": "Private"})
        with self.assertNumQueries(1):
            events = follow_up_events(tasks)
        self.assertEqual(len(events), 3)
        self.assertNotIn((other.pk, str(tasks[0].pk)), events)
