from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from apps.leads import tests_crm_light
from apps.activities.models import Note, ActivityEvent
from apps.core.models import AuditLog, CRMCommandIdempotency


class OfflineLeadCommandsTests(TestCase):
    setUp = tests_crm_light.LeadCrmLightTests.setUp

    def post(self, text="Saved once", key="stable-note"):
        return self.api.post(f"/api/leads/{self.assigned_lead.id}/add-note/", {"text": text}, format="json", HTTP_IDEMPOTENCY_KEY=key)

    def test_lost_response_replay_has_one_note_history_and_audit(self):
        self.api.force_authenticate(self.manager)
        first = self.post()
        second = self.post()
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.data["id"], first.data["id"])
        self.assertEqual(Note.objects.count(), 1)
        self.assertEqual(ActivityEvent.objects.filter(event_type="lead_note_added").count(), 1)
        self.assertEqual(AuditLog.objects.filter(entity_type="Note").count(), 1)

    def test_changed_payload_conflicts_without_effect(self):
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(self.post("Changed").status_code, 409)
        self.assertEqual(Note.objects.count(), 1)

    def test_audit_failure_rolls_back_then_retry_succeeds(self):
        self.api.force_authenticate(self.manager)
        with patch("apps.leads.views.write_audit_log", side_effect=RuntimeError("injected audit failure")):
            self.assertEqual(self.post().status_code, 500)
        self.assertEqual(Note.objects.count(), 0)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 0)
        self.assertEqual(self.post().status_code, 201)
        self.assertEqual(Note.objects.count(), 1)

    def test_replay_checks_current_lead_scope(self):
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.post().status_code, 201)
        self.assigned_lead.responsible_user = self.other_manager
        self.assigned_lead.save(update_fields=["responsible_user"])
        self.assertEqual(self.post().status_code, 404)
        self.assertEqual(Note.objects.count(), 1)

    def test_empty_note_rejected_without_receipt(self):
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.post(" ").status_code, 400)
        self.assertEqual(Note.objects.count(), 0)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 0)

    def test_expired_offline_key_never_creates_note_or_task(self):
        self.api.force_authenticate(self.manager)
        stamp = int((timezone.now().timestamp()-3601)*1000)
        key = f"lead-offline:{stamp}:12345678-1234-1234-1234-123456789abc"
        self.assertEqual(self.post(key=key).status_code, 409)
        response = self.api.post(f"/api/leads/{self.assigned_lead.id}/create-task/", {"title": "Late retry"}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(Note.objects.count(), 0)

    def test_valid_offline_note_key_replays(self):
        self.api.force_authenticate(self.manager)
        key = f"lead-offline:{int(timezone.now().timestamp()*1000)}:12345678-1234-1234-1234-123456789abc"
        self.assertEqual(self.post(key=key).status_code, 201)
        self.assertEqual(self.post(key=key).status_code, 201)
        self.assertEqual(Note.objects.count(), 1)

    def test_other_business_actor_cannot_replay_note(self):
        from apps.accounts.models import User
        from apps.businesses.models import Business
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.post().status_code, 201)
        outsider = User.objects.create_user(username="outsider-offline", email="outsider-offline@example.test")
        Business.objects.create(owner=outsider, name="Other", slug="offline-other")
        self.api.force_authenticate(outsider)
        self.assertEqual(self.post().status_code, 404)
        self.assertEqual(Note.objects.count(), 1)

    def test_role_update_denial_applies_to_replay(self):
        from apps.businesses.models import BusinessMember, RolePermission
        self.api.force_authenticate(self.manager)
        self.assertEqual(self.post().status_code, 201)
        role = BusinessMember.objects.get(business=self.business, user=self.manager).business_role
        RolePermission.objects.update_or_create(business_role=role, resource="leads", action="update", defaults={"is_allowed": False, "scope": "none"})
        self.assertEqual(self.post().status_code, 403)
        self.assertEqual(Note.objects.count(), 1)

    def test_offline_task_lost_response_and_conflict(self):
        from apps.tasks.models import Task
        self.api.force_authenticate(self.manager)
        key = f"lead-offline:{int(timezone.now().timestamp()*1000)}:12345678-1234-1234-1234-123456789abc"
        url = f"/api/leads/{self.assigned_lead.id}/create-task/"
        first = self.api.post(url, {"title": "Once", "assignee": self.manager.id}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        second = self.api.post(url, {"title": "Once", "assignee": self.manager.id}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(first.data["id"], second.data["id"])
        changed = self.api.post(url, {"title": "Changed", "assignee": self.manager.id}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(changed.status_code, 409)
        self.assertEqual(Task.objects.count(), 1)

    def test_offline_task_own_scope_cannot_assign_peer(self):
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        from apps.tasks.models import Task
        role = BusinessRole.objects.create(business=self.business, name="Offline own commands")
        BusinessMember.objects.filter(business=self.business, user=self.manager).update(business_role=role)
        for resource in ("leads", "clients", "tasks"):
            RolePermission.objects.create(business_role=role, resource=resource, action="view", scope="business")
        RolePermission.objects.create(business_role=role, resource="tasks", action="create", scope="own")
        self.api.force_authenticate(self.manager)
        key = f"lead-offline:{int(timezone.now().timestamp()*1000)}:12345678-1234-1234-1234-123456789abc"
        response = self.api.post(f"/api/leads/{self.assigned_lead.id}/create-task/", {"title": "Forbidden peer", "assignee": self.other_manager.id}, format="json", HTTP_IDEMPOTENCY_KEY=key)
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Task.objects.count(), 0)
        self.assertEqual(CRMCommandIdempotency.objects.count(), 0)
