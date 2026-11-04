import json

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.access import Actions, Resources, ensure_default_roles
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.leads.models import Lead


class TeamLeadSourceVisibilityTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.owner = User.objects.create_user(username="c02-owner", email="c02-owner@example.invalid")
        cls.actor = User.objects.create_user(username="c02-actor", email="c02-actor@example.invalid")
        cls.peer = User.objects.create_user(username="c02-peer", email="c02-peer@example.invalid")
        cls.business = Business.objects.create(owner=cls.owner, name="C02", slug="c02")
        ensure_default_roles(cls.business)
        cls.role = BusinessRole.objects.get(business=cls.business, preset_key=BusinessMember.Roles.MANAGER)
        BusinessMember.objects.create(business=cls.business, user=cls.owner, role=BusinessMember.Roles.OWNER)
        cls.member = BusinessMember.objects.create(business=cls.business, user=cls.actor, role=BusinessMember.Roles.MANAGER, business_role=cls.role)
        cls.peer_member = BusinessMember.objects.create(business=cls.business, user=cls.peer, role=BusinessMember.Roles.MANAGER, business_role=cls.role)
        client = Client.objects.create(business=cls.business, full_name="Synthetic C02")
        for user, reason in ((cls.actor, "C02_ACTOR_REASON"), (cls.peer, "C02_PEER_REASON")):
            Lead.objects.create(business=cls.business, client=client, responsible_user=user, status=Lead.Statuses.LOST, lost_reason=reason, source="manual")
        cls.foreign = Business.objects.create(owner=cls.owner, name="Other", slug="c02-other")
        other_client = Client.objects.create(business=cls.foreign, full_name="Other synthetic")
        Lead.objects.create(business=cls.foreign, client=other_client, responsible_user=cls.actor, status=Lead.Statuses.LOST, lost_reason="C02_FOREIGN_REASON")

    def setUp(self):
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def permission(self, *, allowed=True, scope="business", resource=Resources.LEADS):
        RolePermission.objects.update_or_create(business_role=self.role, resource=resource, action=Actions.VIEW,
                                               defaults={"is_allowed": allowed, "scope": scope})

    def report(self, **query):
        response = self.api.get("/api/team/performance/", {"business": self.business.pk, **query})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertNotIn("C02_FOREIGN_REASON", json.dumps(response.data))
        return response.data

    def team(self):
        team = Team.objects.create(business=self.business, name="C02 team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        TeamMember.objects.create(team=team, member=self.peer_member)

    def assert_no_leads(self, payload):
        for field in ("assigned_leads", "contacted_leads", "closed_leads", "lost_leads", "lost_rate"):
            self.assertEqual(payload["totals"][field], 0, field)
            for row in payload["members"]:
                self.assertEqual(row[field], 0, field)
        for row in payload["members"]:
            self.assertEqual(row["lost_without_reason"], 0)
            self.assertEqual(row["lost_reason_breakdown"], [])
        for row in payload["teams"]:
            for field in ("assigned_leads", "lost_leads", "lost_rate"):
                self.assertEqual(row[field], 0)
        self.assertNotIn("C02_ACTOR_REASON", json.dumps(payload))
        self.assertNotIn("C02_PEER_REASON", json.dumps(payload))

    def test_allowed_business_scope_keeps_own_report_boundary(self):
        self.permission()
        payload = self.report()
        self.assertEqual(payload["totals"]["assigned_leads"], 1)
        self.assertEqual(payload["members"][0]["lost_reason_breakdown"], [{"lost_reason": "C02_ACTOR_REASON", "count": 1}])
        self.assertEqual([row["user"]["id"] for row in payload["members"]], [self.actor.pk])

    def test_denied_source_hides_counts_reasons_and_team_summary(self):
        self.team()
        self.permission(allowed=False)
        self.assert_no_leads(self.report())

    def test_disabled_module_hides_even_owner_source_and_can_recover(self):
        self.api.force_authenticate(self.owner)
        capability = BusinessCapability.objects.create(business=self.business, module_key="leads", is_enabled=False)
        self.assert_no_leads(self.report())
        capability.is_enabled = True
        capability.save(update_fields=["is_enabled"])
        self.assertEqual(self.report()["totals"]["assigned_leads"], 2)

    def test_own_scope_intersects_team_report(self):
        self.team()
        self.permission(scope="own")
        payload = self.report()
        self.assertEqual(payload["totals"]["assigned_leads"], 1)
        peer = next(row for row in payload["members"] if row["user"]["id"] == self.peer.pk)
        self.assertEqual(peer["assigned_leads"], 0)
        self.assertEqual(peer["lost_reason_breakdown"], [])

    def test_team_scope_preserves_permitted_peer_and_no_duplicate_counts(self):
        self.team()
        self.permission(scope="team")
        self.assertEqual(self.report()["totals"]["assigned_leads"], 2)

    def test_permission_revocation_and_restore_apply_on_next_request(self):
        self.permission()
        self.assertEqual(self.report()["totals"]["assigned_leads"], 1)
        self.permission(allowed=False, scope="none")
        self.assert_no_leads(self.report())
        self.permission()
        self.assertEqual(self.report()["totals"]["assigned_leads"], 1)

    def test_source_filter_still_applies(self):
        self.permission()
        self.assert_no_leads(self.report(source="not-a-source"))

    def test_foreign_business_denied(self):
        self.assertEqual(self.api.get("/api/team/performance/", {"business": self.foreign.pk}).status_code, 403)

    def test_analytics_permission_still_required(self):
        self.permission(allowed=False, resource=Resources.ANALYTICS)
        self.assertEqual(self.api.get("/api/team/performance/", {"business": self.business.pk}).status_code, 403)

    def test_inactive_member_denied(self):
        self.member.is_active = False
        self.member.save(update_fields=["is_active"])
        self.assertEqual(self.api.get("/api/team/performance/", {"business": self.business.pk}).status_code, 403)
