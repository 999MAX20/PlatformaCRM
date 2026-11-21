from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.models import Business, BusinessMember, BusinessCapability, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.tasks.models import Task


class TaskHistoryAccessTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="history-owner", email="history-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="History A", slug="history-a")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.reader = User.objects.create_user(username="history-reader", email="history-reader@example.test")
        self.member = BusinessMember.objects.create(business=self.business, user=self.reader, role="operator")
        self.task = Task.objects.create(business=self.business, title="Own task", assignee=self.reader, created_by=self.reader)
        self.event = ActivityEvent.objects.create(business=self.business, actor=self.owner, entity_type="Task",
                                                  entity_id=str(self.task.pk), event_type="task_created", text="Created task")
        self.api = APIClient()
        self.api.force_authenticate(self.reader)

    def history(self, task=None, **params):
        return self.api.get("/api/activity-events/", {"entity_type": "Task", "entity_id": (task or self.task).pk, **params})

    def test_operator_reads_own_task_history_without_analytics(self):
        response = self.history()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.event.pk)

    def test_roles_read_exact_task_history_with_and_without_business(self):
        for role in ("admin", "manager", "operator", "specialist"):
            self.member.role = role
            self.member.save(update_fields=["role"])
            for params in ({}, {"business": self.business.pk}):
                with self.subTest(role=role, params=params):
                    response = self.history(**params)
                    self.assertEqual(response.status_code, 200, response.data)
                    self.assertEqual(response.data["count"], 1)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.history().data["count"], 1)

    def test_unreadable_missing_and_foreign_tasks_return_not_found(self):
        hidden = Task.objects.create(business=self.business, title="Hidden", assignee=self.owner, created_by=self.owner)
        foreign = Business.objects.create(owner=self.owner, name="History B", slug="history-b")
        foreign_task = Task.objects.create(business=foreign, title="Foreign", assignee=self.owner)
        for identifier in (hidden.pk, foreign_task.pk, 999999, "invalid", "9" * 30):
            with self.subTest(identifier=identifier):
                response = self.history(entity_id=identifier)
                self.assertEqual(response.status_code, 404, response.data)

    def test_empty_history_and_revoked_task_scope_are_distinct(self):
        self.event.delete()
        self.assertEqual(self.history().data["count"], 0)
        Task.objects.filter(pk=self.task.pk).update(assignee=self.owner, created_by=self.owner)
        self.assertEqual(self.history().status_code, 404)

    def test_exact_history_does_not_grant_general_analytics_or_event_writes(self):
        for params in ({}, {"entity_type": "Task"}, {"entity_id": self.task.pk}):
            self.assertEqual(self.api.get("/api/activity-events/", params).data["count"], 0)
        self.assertEqual(self.api.get("/api/activity-events/", {"business": self.business.pk}).status_code, 403)
        self.assertEqual(self.api.get(f"/api/activity-events/{self.event.pk}/").status_code, 404)
        self.assertEqual(self.api.get("/api/activity-events/actors/", {"entity_type": "Task", "entity_id": self.task.pk}).data["count"], 0)
        response = self.api.post("/api/activity-events/", {"business": self.business.pk, "entity_type": "Task",
                                                        "entity_id": self.task.pk, "event_type": "task_created"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)

    def test_task_capability_required_but_analytics_capability_not_required(self):
        BusinessCapability.objects.update_or_create(business=self.business, module_key="analytics", defaults={"is_enabled": False})
        self.assertEqual(self.history(business=self.business.pk).data["count"], 1)
        BusinessCapability.objects.update_or_create(business=self.business, module_key="tasks", defaults={"is_enabled": False})
        self.assertEqual(self.history().status_code, 404)

    def test_pagination_never_counts_events_from_another_business(self):
        foreign = Business.objects.create(owner=self.owner, name="History B", slug="history-b")
        ActivityEvent.objects.create(business=foreign, entity_type="Task", entity_id=str(self.task.pk), event_type="task_created")
        response = self.history(page_size=1)
        self.assertEqual(response.data["count"], 1)
        self.assertIsNone(response.data["next"])
        self.assertEqual(self.history(business=foreign.pk).status_code, 404)

    def test_existing_client_redaction_is_preserved_for_task_only_role(self):
        role = BusinessRole.objects.create(business=self.business, name="Task history reader")
        RolePermission.objects.create(business_role=role, resource="tasks", action="view", is_allowed=True, scope="own")
        RolePermission.objects.create(business_role=role, resource="clients", action="view", is_allowed=False, scope="business")
        self.member.business_role = role
        self.member.save(update_fields=["business_role"])
        customer = Client.objects.create(business=self.business, full_name="Private customer")
        self.event.client = customer
        self.event.text = "Private customer"
        self.event.metadata = {"client_name": "Private customer", "phone": "+77019998877"}
        self.event.save()
        response = self.history()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        self.assertNotIn("Private customer", str(response.data))
        self.assertNotIn("+77019998877", str(response.data))
