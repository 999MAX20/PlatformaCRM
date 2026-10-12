from datetime import datetime, timedelta, timezone as datetime_timezone
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.scheduling.models import Resource
from apps.notifications.models import Notification
from apps.tasks.models import Task


class TaskWorkspaceTests(TestCase):
    @override_settings(CORS_ALLOWED_ORIGINS=["https://tasks.example.test"])
    def test_browser_can_send_version_and_idempotency_headers(self):
        response = self.client.options("/api/tasks/", HTTP_ORIGIN="https://tasks.example.test",
                                       HTTP_ACCESS_CONTROL_REQUEST_METHOD="POST",
                                       HTTP_ACCESS_CONTROL_REQUEST_HEADERS="idempotency-key,x-task-version,content-type")
        allowed = response.headers.get("Access-Control-Allow-Headers", "")
        self.assertIn("idempotency-key", allowed)
        self.assertIn("x-task-version", allowed)

    def setUp(self):
        self.owner = User.objects.create_user(username="workspace-owner", email="workspace-owner@example.test", password="test")
        self.business = Business.objects.create(name="Workspace", owner=self.owner, timezone="Asia/Almaty")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.task = Task.objects.create(business=self.business, title="Follow up", assignee=self.owner,
                                       created_by=self.owner, due_at=timezone.now() - timedelta(hours=1))

    def command(self, action, data=None, **headers):
        return self.api.post(f"/api/tasks/{self.task.id}/{action}/", data or {}, format="json", **headers)

    def test_wait_resume_complete_reopen_preserves_deadline_and_history(self):
        due = self.task.due_at
        response = self.command("wait", {"reason": "Waiting for client", "waiting_until": (timezone.now()+timedelta(days=1)).isoformat()})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["status"], "waiting")
        self.task.refresh_from_db()
        self.assertEqual(self.task.due_at, due)
        self.assertEqual(self.command("resume").data["status"], "in_progress")
        self.assertEqual(self.command("complete").data["status"], "done")
        self.assertEqual(self.command("reopen").data["status"], "open")
        self.assertTrue(ActivityEvent.objects.filter(entity_id=str(self.task.id), metadata__lifecycle_action="task_waiting").exists())

    def test_wait_validation_and_cross_tenant_denial(self):
        self.assertEqual(self.command("wait", {"reason": "x"}).status_code, 400)
        self.assertEqual(self.command("wait", {"reason": "Waiting", "waiting_until": (timezone.now()-timedelta(days=1)).isoformat()}).status_code, 400)
        outsider = User.objects.create_user(username="outsider", email="outsider@example.test")
        self.api.force_authenticate(outsider)
        self.assertIn(self.command("wait", {"reason": "Waiting"}).status_code, (403, 404))
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")

    def test_failed_notification_rolls_back_state_and_activity(self):
        self.api.raise_request_exception = False
        before = ActivityEvent.objects.count()
        with patch("apps.tasks.services.create_task_notification", side_effect=RuntimeError("notification failed")):
            response = self.command("complete")
        self.assertEqual(response.status_code, 500)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "open")
        self.assertEqual(ActivityEvent.objects.count(), before)
        self.assertEqual(Notification.objects.count(), 0)

    def test_command_replay_and_stale_write(self):
        version = self.task.updated_at.isoformat()
        first = self.command("start", HTTP_IDEMPOTENCY_KEY="start-one", HTTP_X_TASK_VERSION=version)
        self.assertEqual(first.status_code, 200, first.data)
        count = Notification.objects.count()
        replay = self.command("start", HTTP_IDEMPOTENCY_KEY="start-one", HTTP_X_TASK_VERSION=version)
        self.assertEqual(replay.status_code, 200, replay.data)
        self.assertEqual(Notification.objects.count(), count)
        stale = self.command("cancel", {"reason": "Changed mind"}, HTTP_X_TASK_VERSION=version)
        self.assertEqual(stale.status_code, 409, stale.data)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "in_progress")

    def test_claim_does_not_implicitly_start_task(self):
        self.task.assignee = None
        self.task.save()
        self.assertEqual(self.command("assign-to-me").data["status"], "open")

    def member(self, role, name=None):
        name = name or role
        user = User.objects.create_user(username=name, email=f"{name}@example.test")
        member = BusinessMember.objects.create(business=self.business, user=user, role=role)
        return user, member

    def test_operator_and_specialist_create_only_for_self(self):
        for role in ("operator", "specialist"):
            user, _ = self.member(role)
            self.api.force_authenticate(user)
            created = self.api.post("/api/tasks/", {"business": self.business.id, "title": "My follow-up"}, format="json")
            self.assertEqual(created.status_code, 201, created.data)
            self.assertEqual(created.data["assignee"], user.id)
            denied = self.api.post("/api/tasks/", {"business": self.business.id, "title": "Not mine", "assignee": self.owner.id}, format="json")
            self.assertEqual(denied.status_code, 403, denied.data)

    def test_custom_create_permission_does_not_require_update_permission(self):
        user, member = self.member("operator", "creator-only")
        role = BusinessRole.objects.create(business=self.business, name="Create only")
        RolePermission.objects.create(business_role=role, resource="tasks", action="update", is_allowed=False, scope="none")
        member.business_role = role
        member.save()
        self.api.force_authenticate(user)
        response = self.api.post("/api/tasks/", {"business": self.business.pk, "title": "Create only"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        options = self.api.get("/api/tasks/assignees/", {"business": self.business.pk, "intent": "create"})
        self.assertEqual(options.status_code, 200, options.data)
        self.assertEqual(options.data, [{"id": user.pk, "name": user.email}])
        task_id = response.data["id"]
        self.assertEqual(self.api.post(f"/api/tasks/{task_id}/start/").status_code, 403)

    def test_snooze_rejects_past_and_does_not_change_deadline(self):
        due = self.task.due_at
        self.assertEqual(self.command("snooze", {"snoozed_until": (timezone.now() - timedelta(hours=1)).isoformat()}).status_code, 400)
        self.assertEqual(self.command("snooze", {"snoozed_until": (timezone.now() + timedelta(hours=1)).isoformat()}).status_code, 200)
        self.task.refresh_from_db()
        self.assertEqual(self.task.due_at, due)

    def test_details_and_assign_reject_same_unavailable_member_atomically(self):
        user, member = self.member("operator")
        member.availability_status = "unavailable"
        member.save()
        old_title = self.task.title
        response = self.api.patch(f"/api/tasks/{self.task.id}/update-details/",
                                  {"title": "Must not save", "assignee": user.id}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(self.command("assign", {"user_id": user.id}).status_code, 409)
        self.task.refresh_from_db()
        self.assertEqual(self.task.title, old_title)
        self.assertEqual(self.task.assignee, self.owner)

    def test_authorship_and_watching_do_not_grant_lifecycle_permission(self):
        operator, _ = self.member("operator")
        self.task.created_by = operator
        self.task.save()
        self.task.watchers.add(operator)
        self.api.force_authenticate(operator)
        detail = self.api.get(f"/api/tasks/{self.task.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertNotIn("complete", detail.data["available_actions"])
        self.assertEqual(self.command("complete").status_code, 403)

    def test_hidden_relation_is_not_disclosed_and_cannot_be_attached(self):
        specialist, _ = self.member("specialist")
        client = Client.objects.create(business=self.business, full_name="Client")
        lead = Lead.objects.create(business=self.business, message="Private lead", client=client, responsible_user=self.owner)
        self.task.assignee = specialist
        self.task.lead = lead
        self.task.save()
        self.api.force_authenticate(specialist)
        detail = self.api.get(f"/api/tasks/{self.task.id}/")
        self.assertEqual(detail.status_code, 200)
        self.assertIsNone(detail.data["lead"])
        self.assertEqual(detail.data["lead_title"], "")
        self.assertFalse(any(item["type"] == "lead" for item in detail.data["relations"]))
        denied = self.api.patch(f"/api/tasks/{self.task.id}/update-details/", {"lead": lead.id}, format="json")
        self.assertEqual(denied.status_code, 403, denied.data)

    def test_specialist_without_account_is_context_not_assignee(self):
        resource = Resource.objects.create(business=self.business, name="Offline specialist")
        response = self.api.patch(f"/api/tasks/{self.task.id}/update-details/", {"specialist": resource.id}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["assignee"], self.owner.id)
        self.assertEqual(response.data["specialist"], resource.id)
        self.assertEqual(response.data["relations"][0]["href"], f"/app/business/resources?resource={resource.id}")

    def test_cross_client_links_rejected_without_changes(self):
        first = Client.objects.create(business=self.business, full_name="First")
        second = Client.objects.create(business=self.business, full_name="Second")
        lead = Lead.objects.create(business=self.business, message="Second lead", client=second)
        response = self.api.patch(f"/api/tasks/{self.task.id}/update-details/", {"client": first.id, "lead": lead.id}, format="json")
        self.assertEqual(response.status_code, 400, response.data)
        self.task.refresh_from_db()
        self.assertIsNone(self.task.client_id)

    def test_personal_created_and_watched_scopes_are_distinct(self):
        operator, _ = self.member("operator")
        created = Task.objects.create(business=self.business, title="Created", created_by=self.owner, assignee=operator)
        watched = Task.objects.create(business=self.business, title="Watched", created_by=operator, assignee=operator)
        watched.watchers.add(self.owner)
        def ids(tab):
            response = self.api.get("/api/tasks/", {"business": self.business.id, "tab": tab})
            self.assertEqual(response.status_code, 200, response.data)
            return {item["id"] for item in response.data["results"]}
        self.assertEqual(ids("my"), {self.task.id})
        self.assertEqual(ids("created"), {self.task.id, created.id})
        self.assertEqual(ids("watching"), {watched.id})

    def test_business_day_buckets_do_not_overlap_and_waiting_stays_active(self):
        now = datetime(2026, 10, 12, 18, 30, tzinfo=datetime_timezone.utc)  # 23:30 Almaty
        self.task.due_at = now - timedelta(hours=1)
        self.task.status = "waiting"
        self.task.snoozed_until = now + timedelta(days=1)
        self.task.save()
        Task.objects.create(business=self.business, title="Today", due_at=now + timedelta(minutes=15))
        Task.objects.create(business=self.business, title="Tomorrow", due_at=now + timedelta(hours=1))
        Task.objects.create(business=self.business, title="Done", status="done")
        Task.objects.create(business=self.business, title="Cancelled", status="cancelled")
        with patch("django.utils.timezone.now", return_value=now):
            summary = self.api.get("/api/tasks/summary/", {"business": self.business.id})
            today = self.api.get("/api/tasks/", {"business": self.business.id, "bucket": "today"})
        self.assertEqual(summary.status_code, 200, summary.data)
        self.assertEqual({key: summary.data[key] for key in ("active", "overdue", "today", "later", "done", "cancelled")},
                         {"active": 3, "overdue": 1, "today": 1, "later": 1, "done": 1, "cancelled": 1})
        self.assertEqual([item["title"] for item in today.data["results"]], ["Today"])

    def test_waiting_return_date_reminds_once_without_resuming_or_moving_due(self):
        from apps.tasks.reminders import enqueue_due_task_reminders
        self.task.status = "waiting"
        self.task.waiting_until = timezone.now() - timedelta(minutes=1)
        self.task.save()
        due = self.task.due_at
        self.assertEqual(enqueue_due_task_reminders(), 1)
        self.assertEqual(enqueue_due_task_reminders(), 0)
        self.task.refresh_from_db()
        self.assertEqual(self.task.status, "waiting")
        self.assertEqual(self.task.due_at, due)
