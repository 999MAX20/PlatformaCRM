"""OFFICIAL-15: current nested Task read context, synthetic regression controls."""
from datetime import timedelta
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bots.models import Bot, BotConversation
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.core.crm_cards import client_crm_card, lead_crm_card, deal_crm_card, appointment_crm_card
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.leads.models import Lead
from apps.scheduling.models import Appointment, Resource
from apps.services.models import Service
from apps.tasks.models import Task
from apps.tasks.serializers import TaskSerializer


class TaskPreviewContextTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="preview-owner", email="preview-owner@example.test")
        self.actor = User.objects.create_user(username="preview-reader", email="preview-reader@example.test")
        self.peer = User.objects.create_user(username="preview-peer", email="preview-peer@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Synthetic previews", slug="preview-context")
        self.role = BusinessRole.objects.create(business=self.business, name="Preview reader")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="operator")
        for resource in ("clients", "leads", "deals", "appointments", "tasks", "conversations"):
            RolePermission.objects.create(business_role=self.role, resource=resource, action="view", scope="business")
        RolePermission.objects.create(business_role=self.role, resource="tasks", action="update", scope="own")
        self.customer = Client.objects.create(business=self.business, full_name="Synthetic private client")
        self.lead = Lead.objects.create(business=self.business, client=self.customer, responsible_user=self.peer)
        pipeline = Pipeline.objects.create(business=self.business, name="Preview pipeline", slug="preview")
        stage = PipelineStage.objects.create(business=self.business, pipeline=pipeline, name="Preview stage")
        self.deal = Deal.objects.create(business=self.business, client=self.customer, lead=self.lead,
            pipeline=pipeline, stage=stage, title="Synthetic private deal", owner=self.peer)
        service = Service.objects.create(business=self.business, name="Synthetic private service")
        resource = Resource.objects.create(business=self.business, name="Synthetic specialist", linked_user=self.peer)
        self.appointment = Appointment.objects.create(business=self.business, client=self.customer, lead=self.lead,
            service=service, resource=resource, start_at=timezone.now()+timedelta(days=3),
            end_at=timezone.now()+timedelta(days=3, minutes=30))
        bot = Bot.objects.create(business=self.business, name="Synthetic bot")
        self.conversation = BotConversation.objects.create(business=self.business, bot=bot, client=self.customer,
            lead=self.lead, channel="website", external_user_id="synthetic-private-contact", assigned_to=self.peer)
        self.task = Task.objects.create(business=self.business, client=self.customer, lead=self.lead, deal=self.deal,
            appointment=self.appointment, conversation=self.conversation, title="Readable task", assignee=self.actor,
            created_by=self.actor)
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def permission(self, resource, allowed=True, scope="business", action="view"):
        RolePermission.objects.filter(business_role=self.role, resource=resource, action=action).update(is_allowed=allowed, scope=scope)

    def cards(self):
        return [("clients", self.customer, client_crm_card), ("leads", self.lead, lead_crm_card),
                ("deals", self.deal, deal_crm_card), ("appointments", self.appointment, appointment_crm_card)]

    def row(self, route="clients", obj=None):
        obj = obj or self.customer
        response = self.api.get(f"/api/{route}/{obj.pk}/crm-card/")
        self.assertEqual(response.status_code, 200, response.data)
        return next(row for row in response.data["tasks"] if row["id"] == self.task.pk)

    def assert_masked(self, row, fields):
        self.assertEqual(row["id"], self.task.pk)
        self.assertEqual(row["title"], self.task.title)
        for field in fields:
            self.assertIsNone(row[field], field)
            for key in row:
                if key.startswith(field+"_"):
                    self.assertIn(row[key], (None, ""), key)
            self.assertNotIn(field, [link["type"] for link in row["relations"]])

    def test_four_http_cards_preserve_actor_for_forbidden_linked_fields(self):
        mapping = {"clients": "client", "leads": "lead", "deals": "deal", "appointments": "appointment", "conversations": "conversation"}
        for route, obj, _ in self.cards():
            with self.subTest(route=route):
                for resource in mapping:
                    self.permission(resource, resource == route)
                self.assert_masked(self.row(route, obj), [field for res, field in mapping.items() if res != route])

    def test_four_direct_card_wrappers_keep_legitimate_fields_and_actions(self):
        for _, obj, builder in self.cards():
            with self.subTest(builder=builder.__name__):
                row = next(r for r in builder(obj, actor=self.actor)["tasks"] if r["id"] == self.task.pk)
                self.assertEqual(row["client_name"], self.customer.full_name)
                self.assertEqual(row["deal_title"], self.deal.title)
                self.assertEqual(row["appointment_service_name"], self.appointment.service.name)
                self.assertEqual(row["conversation_external_user_id"], self.conversation.external_user_id)
                self.assertIn("edit", row["available_actions"])
                self.assertTrue({"client", "lead", "deal", "appointment", "conversation"}.issubset({r["type"] for r in row["relations"]}))

    def test_scalar_list_and_request_context_are_equivalent(self):
        self.permission("deals", False)
        for context in ({"actor": self.actor}, {"request": SimpleNamespace(user=self.actor)}):
            scalar = TaskSerializer(self.task, context=context).data
            nested = TaskSerializer([self.task], many=True, context=context).data[0]
            self.assertEqual(scalar, nested)
            self.assert_masked(scalar, ["deal"])
            self.assertEqual(scalar["client"], self.customer.pk)

    def test_no_actor_masks_scalar_and_list_and_rejects_cards(self):
        for data in (TaskSerializer(self.task).data, TaskSerializer([self.task], many=True).data[0]):
            self.assert_masked(data, ["client", "lead", "deal", "appointment", "conversation"])
            self.assertEqual(data["available_actions"], [])
        for _, obj, builder in self.cards():
            with self.assertRaises(PermissionDenied):
                builder(obj)

    def test_hidden_client_aliases_mask_even_when_lead_and_conversation_readable(self):
        self.permission("clients", False)
        row = self.row("leads", self.lead)
        self.assert_masked(row, ["client"])
        self.assertEqual(row["lead"], self.lead.pk)
        self.assertEqual(row["lead_title"], f"Lead #{self.lead.pk}")
        self.assertEqual(row["conversation"], self.conversation.pk)
        self.assertEqual(row["conversation_label"], f"Conversation #{self.conversation.pk}")
        self.assertEqual(row["conversation_external_user_id"], "")

    def test_linked_own_scope_and_current_reassignment(self):
        self.permission("deals", scope="own")
        self.assert_masked(self.row(), ["deal"])
        Deal.objects.filter(pk=self.deal.pk).update(owner=self.actor)
        self.assertEqual(self.row()["deal"], self.deal.pk)
        Deal.objects.filter(pk=self.deal.pk).update(owner=self.peer)
        self.assert_masked(self.row(), ["deal"])

    def test_linked_team_scope_and_membership_removal(self):
        self.permission("deals", scope="team")
        team = Team.objects.create(business=self.business, name="Synthetic preview team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        peer = TeamMember.objects.create(team=team, member=self.peer_member)
        self.assertEqual(self.row()["deal"], self.deal.pk)
        peer.delete()
        self.assert_masked(self.row(), ["deal"])

    def test_task_scope_is_applied_before_count_and_preview(self):
        self.permission("tasks", scope="own")
        Task.objects.create(business=self.business, client=self.customer, title="Other task", assignee=self.peer, created_by=self.peer)
        response = self.api.get(f"/api/clients/{self.customer.pk}/crm-card/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual([r["id"] for r in response.data["tasks"]], [self.task.pk])
        self.assertEqual(response.data["meta"]["related_counts"]["tasks"], 1)
        self.permission("tasks", False)
        response = self.api.get(f"/api/clients/{self.customer.pk}/crm-card/")
        self.assertEqual(response.data["tasks"], [])
        self.assertEqual(response.data["meta"]["related_counts"]["tasks"], 0)

    def test_readable_task_does_not_gain_update_actions(self):
        self.permission("tasks", False, action="update")
        row = self.row()
        self.assertEqual(row["available_actions"], [])
        self.assertEqual(row["deal_title"], self.deal.title)

    def test_task_capability_and_foreign_business_controls(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign synthetic", slug="foreign-preview")
        BusinessMember.objects.create(business=foreign, user=self.actor, role="admin")
        Task.objects.create(business=foreign, client=self.customer, title="Foreign backref", assignee=self.actor)
        self.assertEqual(len(self.api.get(f"/api/clients/{self.customer.pk}/crm-card/").data["tasks"]), 1)
        BusinessCapability.objects.update_or_create(business=self.business, module_key="tasks", defaults={"is_enabled": False})
        self.assertEqual(self.api.get(f"/api/clients/{self.customer.pk}/crm-card/").data["tasks"], [])
        self.api.force_authenticate(self.peer)
        self.assertEqual(self.api.get(f"/api/clients/{Client.objects.create(business=foreign, full_name='Foreign').pk}/crm-card/").status_code, 404)

    def test_current_link_view_revocation_matches_direct_task_response(self):
        self.assertEqual(self.row()["deal"], self.deal.pk)
        self.permission("deals", False)
        direct = self.api.get(f"/api/tasks/{self.task.pk}/")
        self.assertEqual(direct.status_code, 200)
        self.assert_masked(direct.data, ["deal"])
        self.assert_masked(self.row(), ["deal"])

    def test_parent_task_and_specialist_aliases_use_current_context(self):
        parent = Task.objects.create(business=self.business, client=self.customer,
            title="Synthetic hidden parent", assignee=self.peer, created_by=self.peer)
        self.task.parent_task = parent
        self.task.specialist = self.appointment.resource
        self.task.save(update_fields=["parent_task", "specialist"])
        self.permission("tasks", scope="own")
        self.assert_masked(self.row(), ["parent_task", "specialist"])
        Task.objects.filter(pk=parent.pk).update(assignee=self.actor)
        row = self.row()
        self.assertEqual(row["parent_task"], parent.pk)
        self.assertIn("parent_task", [r["type"] for r in row["relations"]])
