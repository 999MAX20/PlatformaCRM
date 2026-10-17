from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.core.models import AuditLog
from apps.leads.models import Lead
from apps.notifications.models import Notification
from apps.tasks.models import Task


class LeadAssignmentPatchTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="assignment-owner", email="assignment-owner@example.test")
        cls.actor = User.objects.create_user(username="assignment-actor", email="assignment-actor@example.test")
        cls.peer = User.objects.create_user(username="assignment-peer", email="assignment-peer@example.test")
        cls.outside = User.objects.create_user(username="assignment-outside", email="assignment-outside@example.test")
        cls.business = Business.objects.create(owner=cls.owner, name="Assignments", slug="assignment-patch")
        cls.role = BusinessRole.objects.create(business=cls.business, name="View all, update own")
        for resource in ("leads", "tasks", "notifications"):
            RolePermission.objects.create(business_role=cls.role, resource=resource, action="view", scope="business")
            RolePermission.objects.create(business_role=cls.role, resource=resource, action="update", scope="own")
        cls.members = {}
        for user in (cls.actor, cls.peer, cls.outside):
            cls.members[user.pk] = BusinessMember.objects.create(
                business=cls.business, user=user, role="operator", business_role=cls.role)
        cls.customer = Client.objects.create(business=cls.business, full_name="Customer")
        cls.lead = Lead.objects.create(business=cls.business, client=cls.customer, responsible_user=cls.peer, message="Original")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def test_view_business_update_own_cannot_take_foreign_lead_by_patch_or_put(self):
        for method in (self.api.patch, self.api.put):
            response = method(f"/api/leads/{self.lead.pk}/", {
                "business": self.business.pk, "client": self.customer.pk,
                "responsible_user": self.actor.pk, "message": "Hijacked",
            }, format="json")
            self.assertEqual(response.status_code, 403, response.data)
        response = self.api.post(f"/api/leads/{self.lead.pk}/assign/", {}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.responsible_user_id, self.peer.pk)
        self.assertEqual(self.lead.message, "Original")
        self.assertFalse(ActivityEvent.objects.exists())
        self.assertFalse(AuditLog.objects.exists())
        self.assertFalse(Notification.objects.exists())

    def test_shared_guard_rejects_notification_recipient_takeover(self):
        notification = Notification.objects.create(business=self.business, recipient=self.peer, text="Private", send_at=timezone.now())
        response = self.api.patch(f"/api/notifications/{notification.pk}/", {"recipient": self.actor.pk}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        notification.refresh_from_db()
        self.assertEqual(notification.recipient_id, self.peer.pk)

    def set_scope(self, scope):
        RolePermission.objects.filter(business_role=self.role, resource="leads", action="update").update(scope=scope)

    def update(self, payload):
        return self.api.patch(f"/api/leads/{self.lead.pk}/", payload, format="json")

    def test_business_scope_patch_uses_assignment_history_and_notifications_once(self):
        self.set_scope("business")
        response = self.update({"responsible_user": self.actor.pk, "message": "Edited"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["responsible_user"], self.actor.pk)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.message, "Edited")
        event = ActivityEvent.objects.get(event_type="lead_assigned")
        self.assertEqual(event.metadata["from"], self.peer.pk)
        self.assertEqual(event.metadata["to"], self.actor.pk)
        self.assertEqual(event.actor_id, self.actor.pk)
        self.assertEqual(AuditLog.objects.filter(metadata__kind="assignment").count(), 1)
        self.assertEqual(set(Notification.objects.values_list("recipient_id", flat=True)), {self.actor.pk, self.peer.pk})
        self.assertEqual(Notification.objects.count(), 2)
        response = self.update({"responsible_user": self.actor.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(ActivityEvent.objects.filter(event_type="lead_assigned").count(), 1)
        self.assertEqual(Notification.objects.count(), 2)

    def test_own_scope_can_edit_own_and_claim_unassigned_but_cannot_assign_peer(self):
        self.lead.responsible_user = self.actor
        self.lead.save()
        response = self.update({"message": "Own edit", "responsible_user": self.actor.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.update({"responsible_user": self.peer.pk}).status_code, 403)
        self.assertEqual(self.api.post(f"/api/leads/{self.lead.pk}/assign/", {"user_id": self.peer.pk}).status_code, 403)
        self.lead.responsible_user = None
        self.lead.save()
        self.assertEqual(self.update({"responsible_user": self.actor.pk}).status_code, 200)
        self.lead.responsible_user = None
        self.lead.save()
        self.assertEqual(self.api.post(f"/api/leads/{self.lead.pk}/assign/", {}).status_code, 200)

    def test_team_scope_checks_original_and_target_team(self):
        self.set_scope("team")
        team = Team.objects.create(business=self.business, name="Team")
        for user in (self.actor, self.peer):
            TeamMember.objects.create(team=team, member=self.members[user.pk])
        response = self.update({"responsible_user": self.actor.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.update({"responsible_user": self.outside.pk}).status_code, 403)
        self.lead.responsible_user = self.outside
        self.lead.save()
        self.assertEqual(self.update({"responsible_user": self.actor.pk}).status_code, 403)
        self.assertEqual(self.api.post(f"/api/leads/{self.lead.pk}/assign/", {"user_id": self.actor.pk}).status_code, 403)

    def test_null_cannot_remove_assignment_and_unchanged_null_is_safe(self):
        self.api.force_authenticate(self.owner)
        response = self.update({"responsible_user": None, "message": "Must roll back"})
        self.assertEqual(response.status_code, 400, response.data)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.responsible_user_id, self.peer.pk)
        self.assertEqual(self.lead.message, "Original")
        self.lead.responsible_user = None
        self.lead.save()
        self.assertEqual(self.update({"responsible_user": None, "message": "Unassigned edit"}).status_code, 200)
        self.assertFalse(ActivityEvent.objects.filter(event_type="lead_assigned").exists())

    def test_owner_reassignment_and_invalid_targets_match_assign_action(self):
        self.api.force_authenticate(self.owner)
        stranger = User.objects.create_user(username="stranger", email="stranger@example.test")
        for target, update in ((stranger, {}), (self.outside, {"is_active": False}),
                               (self.outside, {"is_active": True, "role": "accountant"}),
                               (self.outside, {"role": "operator", "availability_status": "unavailable"})):
            if update:
                BusinessMember.objects.filter(pk=self.members[self.outside.pk].pk).update(**update)
            with self.subTest(target=target.pk, update=update):
                response = self.update({"responsible_user": target.pk, "message": "Invalid"})
                self.assertIn(response.status_code, (400, 409), response.data)
                self.assertIn(self.api.post(f"/api/leads/{self.lead.pk}/assign/", {"user_id": target.pk}).status_code, (400, 409))
                self.lead.refresh_from_db()
                self.assertEqual(self.lead.responsible_user_id, self.peer.pk)
                self.assertEqual(self.lead.message, "Original")
        self.assertEqual(self.update({"responsible_user": self.actor.pk}).status_code, 200)

    def test_inactive_account_and_foreign_tenant_are_denied(self):
        self.api.force_authenticate(self.owner)
        User.objects.filter(pk=self.outside.pk).update(is_active=False)
        self.assertEqual(self.update({"responsible_user": self.outside.pk}).status_code, 400)
        other = Business.objects.create(owner=self.outside, name="Other", slug="assignment-other")
        customer = Client.objects.create(business=other, full_name="Other")
        lead = Lead.objects.create(business=other, client=customer, responsible_user=self.outside)
        for url, payload in ((f"/api/leads/{lead.pk}/", {"responsible_user": self.owner.pk}),
                             (f"/api/leads/{self.lead.pk}/", {"business": other.pk, "client": customer.pk})):
            response = self.api.patch(url, payload, format="json")
            self.assertIn(response.status_code, (400, 403, 404), response.data)

    def test_failure_in_assignment_or_ordinary_audit_rolls_back_entire_edit(self):
        self.api.force_authenticate(self.owner)
        self.api.raise_request_exception = False
        for target in ("apps.leads.services.create_assignment_notifications", "apps.core.viewsets.write_audit_log"):
            with patch(target, side_effect=RuntimeError("Injected write failure")):
                response = self.update({"responsible_user": self.actor.pk, "message": "Must roll back"})
            self.assertEqual(response.status_code, 500)
            self.lead.refresh_from_db()
            self.assertEqual(self.lead.responsible_user_id, self.peer.pk)
            self.assertEqual(self.lead.message, "Original")
            self.assertFalse(ActivityEvent.objects.exists())
            self.assertFalse(AuditLog.objects.exists())
            self.assertFalse(Notification.objects.exists())

    def test_shared_task_update_cannot_claim_foreign_task_and_regular_edit_works(self):
        task = Task.objects.create(business=self.business, title="Peer task", assignee=self.peer, created_by=self.actor)
        response = self.api.patch(f"/api/tasks/{task.pk}/", {"assignee": self.actor.pk}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        task.assignee = self.actor
        task.save()
        response = self.api.patch(f"/api/tasks/{task.pk}/", {"title": "Own edit"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def test_owner_without_membership_and_unchanged_disabled_assignee_match_domain(self):
        self.api.force_authenticate(self.owner)
        response = self.update({"responsible_user": self.owner.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.lead.responsible_user = self.peer
        self.lead.save()
        BusinessMember.objects.filter(pk=self.members[self.peer.pk].pk).update(is_active=False)
        response = self.update({"responsible_user": self.peer.pk, "message": "Historical assignment retained"})
        self.assertEqual(response.status_code, 200, response.data)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.responsible_user_id, self.peer.pk)

    def test_update_rechecks_original_after_lock_reload(self):
        from apps.leads.views import LeadViewSet

        self.lead.responsible_user = self.actor
        self.lead.save()
        original = LeadViewSet.get_object
        calls = []

        def reassign_after_first_read(view):
            instance = original(view)
            calls.append(instance.pk)
            if len(calls) == 1:
                Lead.objects.filter(pk=instance.pk).update(responsible_user=self.peer)
            return instance

        with patch.object(LeadViewSet, "get_object", reassign_after_first_read):
            response = self.update({"responsible_user": self.actor.pk, "message": "Stale edit"})
        self.assertEqual(response.status_code, 403, response.data)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.responsible_user_id, self.peer.pk)
        self.assertEqual(self.lead.message, "Original")

    def test_unassigned_claim_action_remains_available_with_view_own(self):
        RolePermission.objects.filter(business_role=self.role, resource="leads", action="view").update(scope="own")
        self.lead.responsible_user = None
        self.lead.save()
        self.assertEqual(self.update({"responsible_user": self.actor.pk}).status_code, 404)
        response = self.api.post(f"/api/leads/{self.lead.pk}/assign/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
