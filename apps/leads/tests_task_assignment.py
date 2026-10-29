"""OFFICIAL-18: Lead follow-up uses final Task creation/assignment policy."""
from datetime import timedelta
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.core.models import AuditLog, CRMCommandIdempotency
from apps.core.domain_errors import InvalidTransition
from apps.leads.models import Lead
from apps.leads.services import create_follow_up_task_from_lead
from apps.notifications.models import Notification
from apps.tasks.models import Task


class LeadTaskAssignmentTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="followup-owner", email="followup-owner@example.test")
        self.actor = User.objects.create_user(username="followup-actor", email="followup-actor@example.test")
        self.peer = User.objects.create_user(username="followup-peer", email="followup-peer@example.test")
        self.outside = User.objects.create_user(username="followup-outside", email="followup-outside@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Synthetic followup", slug="followup-assignment")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.role = BusinessRole.objects.create(business=self.business, name="Synthetic followup role")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="operator")
        self.outside_member = BusinessMember.objects.create(business=self.business, user=self.outside, role="operator")
        for resource in ("clients", "leads", "tasks"):
            RolePermission.objects.create(business_role=self.role, resource=resource, action="view", scope="business")
        RolePermission.objects.create(business_role=self.role, resource="tasks", action="create", scope="own")
        RolePermission.objects.create(business_role=self.role, resource="tasks", action="update", scope="none", is_allowed=False)
        self.team = Team.objects.create(business=self.business, name="Followup team")
        TeamMember.objects.create(team=self.team, member=self.member, is_lead=True)
        self.peer_team = TeamMember.objects.create(team=self.team, member=self.peer_member)
        self.customer = Client.objects.create(business=self.business, full_name="Synthetic client")
        self.lead = Lead.objects.create(business=self.business, client=self.customer, responsible_user=self.actor)
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def permission(self, scope="own", allowed=True):
        RolePermission.objects.filter(business_role=self.role, resource="tasks", action="create").update(scope=scope, is_allowed=allowed)

    def post(self, payload=None, **headers):
        return self.api.post(f"/api/leads/{self.lead.pk}/create-task/", payload or {"title": "Synthetic task"}, format="json", **headers)

    def effects(self):
        return tuple(model.objects.count() for model in (Task, ActivityEvent, AuditLog, Notification, CRMCommandIdempotency))

    def denied(self, payload, status=403):
        before = self.effects()
        response = self.post(payload, HTTP_IDEMPOTENCY_KEY="synthetic-denied-followup")
        self.assertEqual(response.status_code, status, response.data)
        self.assertEqual(self.effects(), before)

    def test_own_cannot_select_another_active_member(self):
        self.denied({"title": "Synthetic task", "assignee": self.peer.pk})

    def test_team_cannot_select_active_member_outside_team(self):
        self.permission("team")
        self.denied({"title": "Synthetic task", "assignee": self.outside.pk})

    def test_explicit_create_deny_has_no_side_effects(self):
        self.permission(allowed=False)
        self.denied({"title": "Synthetic task", "assignee": self.actor.pk})

    def test_unavailable_default_responsible_is_rejected(self):
        self.member.availability_status = "unavailable"
        self.member.unavailable_until = timezone.now()+timedelta(days=1)
        self.member.save(update_fields=["availability_status", "unavailable_until"])
        self.denied({"title": "Synthetic task"}, 409)

    def test_ineligible_active_member_role_is_rejected(self):
        self.permission("business")
        self.peer_member.role = "support"
        self.peer_member.save(update_fields=["role"])
        self.denied({"title": "Synthetic task", "assignee": self.peer.pk}, 400)

    def test_unavailable_explicit_member_is_rejected(self):
        self.permission("business")
        self.peer_member.availability_status = "unavailable"
        self.peer_member.save(update_fields=["availability_status"])
        self.denied({"title": "Synthetic task", "assignee": self.peer.pk}, 409)

    def test_inactive_user_rejected_even_with_active_membership(self):
        self.permission("business")
        self.peer.is_active = False
        self.peer.save(update_fields=["is_active"])
        self.denied({"title": "Synthetic task", "assignee": self.peer.pk}, 400)

    def test_foreign_business_assignee_is_rejected(self):
        foreign = Business.objects.create(owner=self.outside, name="Other synthetic", slug="followup-foreign")
        self.outside_member.delete()
        BusinessMember.objects.create(business=foreign, user=self.outside, role="owner")
        self.denied({"title": "Synthetic task", "assignee": self.outside.pk}, 400)

    def test_direct_service_cannot_bypass_own_scope_without_request(self):
        before = self.effects()
        with self.assertRaises(PermissionDenied):
            create_follow_up_task_from_lead(lead=self.lead, actor=self.actor, title="Direct synthetic", assignee_id=self.peer.pk)
        self.assertEqual(self.effects(), before)

    def test_direct_service_cannot_bypass_create_deny(self):
        self.permission(allowed=False)
        before = self.effects()
        with self.assertRaises(PermissionDenied):
            create_follow_up_task_from_lead(lead=self.lead, actor=self.actor, title="Direct synthetic")
        self.assertEqual(self.effects(), before)

    def test_source_lead_view_still_required(self):
        RolePermission.objects.filter(business_role=self.role, resource="leads", action="view").update(is_allowed=False)
        self.denied({"title": "Synthetic task", "assignee": self.actor.pk}, 404)

    def test_self_task_on_readable_peer_lead_uses_task_not_lead_ownership(self):
        Lead.objects.filter(pk=self.lead.pk).update(responsible_user=self.outside)
        response = self.post({"title": "Self task", "assignee": self.actor.pk})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Task.objects.get().assignee_id, self.actor.pk)

    def test_team_task_on_readable_outside_lead_is_allowed(self):
        self.permission("team")
        Lead.objects.filter(pk=self.lead.pk).update(responsible_user=self.outside)
        response = self.post({"title": "Team task", "assignee": self.peer.pk})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Task.objects.get().assignee_id, self.peer.pk)

    def test_own_self_control_preserves_fields_and_effects_without_update(self):
        due = timezone.now()+timedelta(days=2)
        response = self.post({"title": "  Own task  ", "description": "Synthetic details", "priority": "high",
                              "due_at": due.isoformat(), "assignee": self.actor.pk})
        self.assertEqual(response.status_code, 201, response.data)
        task = Task.objects.get()
        self.assertEqual((task.title, task.assignee_id, task.created_by_id, task.client_id, task.lead_id),
                         ("Own task", self.actor.pk, self.actor.pk, self.customer.pk, self.lead.pk))
        self.assertEqual(task.due_at, due)
        self.assertTrue(ActivityEvent.objects.filter(entity_type="Task", entity_id=str(task.pk)).exists())
        self.assertTrue(AuditLog.objects.filter(entity_type="Task", entity_id=str(task.pk)).exists())
        self.assertTrue(Notification.objects.filter(business=self.business, recipient=self.actor).exists())

    def test_business_scope_can_select_eligible_peer(self):
        self.permission("business")
        response = self.post({"title": "Business task", "assignee": self.peer.pk})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Task.objects.get().assignee_id, self.peer.pk)

    def test_omitted_assignee_preserves_default_responsible(self):
        response = self.post()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Task.objects.get().assignee_id, self.actor.pk)

    def test_explicit_null_preserves_default_responsible(self):
        response = self.post({"title": "Null default task", "assignee": None})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Task.objects.get().assignee_id, self.actor.pk)

    def test_no_request_foreign_actor_cannot_use_service(self):
        before = self.effects()
        with self.assertRaises(PermissionDenied):
            create_follow_up_task_from_lead(lead=self.lead, actor=User.objects.create_user(username="followup-foreign-actor"), title="Synthetic task")
        self.assertEqual(self.effects(), before)

    def test_invalid_input_preserves_no_side_effects(self):
        for payload in ({"title": ""}, {"title": "Synthetic", "priority": "invalid"}, {"title": "Synthetic", "assignee": "invalid"}):
            with self.subTest(payload=payload):
                self.denied(payload, 400)

    def test_same_key_same_rights_replay_does_not_create_again(self):
        payload = {"title": "Replay control", "assignee": self.actor.pk}
        first = self.post(payload, HTTP_IDEMPOTENCY_KEY="synthetic-followup-once")
        self.assertEqual(first.status_code, 201, first.data)
        before = self.effects()
        again = self.post(payload, HTTP_IDEMPOTENCY_KEY="synthetic-followup-once")
        self.assertEqual(again.status_code, 201, again.data)
        self.assertEqual(again.data["id"], first.data["id"])
        self.assertEqual(self.effects(), before)

    def test_string_id_cannot_bypass_assignment_scope(self):
        self.denied({"title": "Synthetic string ID", "assignee": str(self.peer.pk)})

    def test_locked_current_lead_controls_default_not_stale_instance(self):
        Lead.objects.filter(pk=self.lead.pk).update(responsible_user=self.peer)
        before = self.effects()
        with self.assertRaises(PermissionDenied):
            create_follow_up_task_from_lead(lead=self.lead, actor=self.actor, title="Stale default",
                                           request=SimpleNamespace(user=self.actor, META={}))
        self.assertEqual(self.effects(), before)

    def test_direct_service_checks_current_source_view_scope(self):
        RolePermission.objects.filter(business_role=self.role, resource="leads", action="view").update(scope="own")
        Lead.objects.filter(pk=self.lead.pk).update(responsible_user=self.peer)
        before = self.effects()
        with self.assertRaises(PermissionDenied):
            create_follow_up_task_from_lead(lead=self.lead, actor=self.actor, title="Source scope", assignee_id=self.actor.pk)
        self.assertEqual(self.effects(), before)

    def test_disabled_task_module_preserves_no_effects(self):
        BusinessCapability.objects.update_or_create(business=self.business, module_key="tasks", defaults={"is_enabled": False})
        self.denied({"title": "Disabled synthetic"})

    def test_archived_source_still_requires_restore(self):
        Lead.objects.filter(pk=self.lead.pk).update(is_archived=True)
        before = self.effects()
        with self.assertRaises(InvalidTransition):
            create_follow_up_task_from_lead(lead=self.lead, actor=self.actor, title="Archived synthetic")
        self.assertEqual(self.effects(), before)

    def test_expired_unavailability_preserves_eligible_member_control(self):
        self.permission("business")
        self.peer_member.availability_status = "unavailable"
        self.peer_member.unavailable_until = timezone.now()-timedelta(minutes=1)
        self.peer_member.save(update_fields=["availability_status", "unavailable_until"])
        response = self.post({"title": "Available again", "assignee": self.peer.pk})
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Task.objects.get().assignee_id, self.peer.pk)

    def test_existing_business_scope_unassigned_fallback_is_preserved(self):
        self.permission("business")
        Lead.objects.filter(pk=self.lead.pk).update(responsible_user=self.peer)
        self.peer_member.is_active = False
        self.peer_member.save(update_fields=["is_active"])
        response = self.post()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(Task.objects.get().assignee_id)

    def test_denials_match_regular_task_create_policy(self):
        for scope, target in (("own", self.peer), ("team", self.outside)):
            with self.subTest(scope=scope):
                self.permission(scope)
                before = self.effects()
                direct = self.api.post("/api/tasks/", {"business": self.business.pk, "title": "Ordinary control",
                                                      "assignee": target.pk}, format="json")
                self.assertEqual(direct.status_code, 403, direct.data)
                self.assertEqual(self.effects(), before)
                self.denied({"title": "Lead control", "assignee": target.pk})
