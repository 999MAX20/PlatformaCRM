"""Read-scope regression coverage for unified CRM list/summary filters."""
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bots.models import Bot, BotConversation, BotMessage
from apps.businesses.models import Business, BusinessMember, Team, TeamMember
from apps.clients.models import Client
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.leads.models import Lead


class CrmWorkspaceReadScopeTests(TestCase):
    def setUp(self):
        self.api = APIClient()
        self.owner = User.objects.create_user(username="scope-owner", email="scope-owner@example.test")
        self.manager = User.objects.create_user(username="scope-manager", email="scope-manager@example.test")
        self.specialist = User.objects.create_user(username="scope-specialist", email="scope-specialist@example.test")
        self.hidden = User.objects.create_user(username="scope-hidden", email="scope-hidden@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Scope", slug="workspace-scope")
        for user, role in [(self.owner, "owner"), (self.manager, "manager"), (self.specialist, "specialist"), (self.hidden, "specialist")]:
            BusinessMember.objects.create(business=self.business, user=user, role=role)
        team = Team.objects.create(business=self.business, name="Visible team")
        for user in [self.manager, self.specialist]:
            TeamMember.objects.create(team=team, member=BusinessMember.objects.get(user=user, business=self.business))
        self.patient = Client.objects.create(business=self.business, full_name="Scoped patient")
        self.pipeline = Pipeline.objects.create(business=self.business, name="Scope")
        self.stage = PipelineStage.objects.create(business=self.business, pipeline=self.pipeline, name="Open")
        self.leads = {}
        self.deals = {}
        for user in [self.manager, self.specialist, self.hidden]:
            self.leads[user.pk] = Lead.objects.create(business=self.business, client=self.patient, responsible_user=user)
            self.deals[user.pk] = Deal.objects.create(business=self.business, client=self.patient, owner=user, pipeline=self.pipeline, stage=self.stage, title="Scoped deal")
        self.bot = Bot.objects.create(business=self.business, name="Scope")
        conversation = BotConversation.objects.create(business=self.business, bot=self.bot, client=self.patient, status="open", channel="website", external_user_id="scope")
        BotMessage.objects.create(conversation=conversation, direction="inbound", sender_type="client", status="received", text="Synthetic question")

    def get(self, path, **params):
        return self.api.get(f"/api/{path}/", {"workspace": "true", **params})

    def test_manager_team_scope_cannot_be_widened_by_filter_or_summary(self):
        self.api.force_authenticate(self.manager)
        for resource, records in [("leads", self.leads), ("deals", self.deals)]:
            with self.subTest(resource=resource):
                response = self.get(resource, statuses="all", archive="all", include_archived="true")
                self.assertEqual(response.status_code, 200)
                self.assertCountEqual([row["id"] for row in response.data["results"]], [records[self.manager.pk].pk, records[self.specialist.pk].pk])
                self.assertEqual(self.get(f"{resource}/summary", scope="mine").data["total"], 1)
                self.assertEqual(self.get(resource, assignees=self.hidden.pk).data["count"], 0)
                self.assertEqual(self.get(f"{resource}/summary", assignees=self.hidden.pk).data["total"], 0)
        board = self.get("deals/board", pipeline=self.pipeline.pk, assignees=self.hidden.pk)
        self.assertEqual(board.data["stages"], [])

    def test_specialist_own_leads_and_denied_deals_conversations_do_not_leak(self):
        self.api.force_authenticate(self.specialist)
        self.assertEqual([row["id"] for row in self.get("leads").data["results"]], [self.leads[self.specialist.pk].pk])
        self.assertEqual(self.get("leads/summary", statuses="all").data["total"], 1)
        self.assertEqual(self.get("deals", statuses="all").data["count"], 0)
        self.assertEqual(self.get("deals/summary").data["total"], 0)
        clients = self.get("clients")
        self.assertEqual(clients.data["count"], 1)
        self.assertFalse(clients.data["results"][0]["has_no_reply"])
        self.assertEqual(clients.data["summary"]["no_reply"], 0)
        self.assertEqual(self.get("clients", quick_filter="no_reply").data["count"], 0)
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.get("clients", quick_filter="no_reply").data["count"], 1)

    def test_anonymous_and_disabled_membership_cannot_use_workspace_filters(self):
        for resource in ["clients", "leads", "leads/summary", "deals", "deals/summary", "deals/board"]:
            self.assertEqual(self.get(resource).status_code, 401)
        BusinessMember.objects.filter(business=self.business, user=self.manager).update(is_active=False)
        self.api.force_authenticate(self.manager)
        for resource in ["clients", "leads", "deals"]:
            self.assertEqual(self.get(resource, statuses="all", archive="all", include_archived="true").data["count"], 0)
