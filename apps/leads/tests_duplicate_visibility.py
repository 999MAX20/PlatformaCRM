"""Synthetic OFFICIAL-16 read-boundary tests, no network or real accounts."""
import json
from datetime import timedelta
from types import SimpleNamespace

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessCapability, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.leads.serializers import LeadDuplicateCheckSerializer


class LeadDuplicateVisibilityTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="lead-dupe-owner", email="lead-dupe-owner@example.invalid")
        self.actor = User.objects.create_user(username="lead-dupe-reader", email="lead-dupe-reader@example.invalid", role="business_operator")
        self.peer = User.objects.create_user(username="lead-dupe-peer", email="lead-dupe-peer@example.invalid", role="business_operator")
        self.outsider = User.objects.create_user(username="lead-dupe-other", email="lead-dupe-other@example.invalid", role="business_operator")
        self.business = Business.objects.create(owner=self.owner, name="Lead duplicates A", slug="lead-duplicates-a")
        self.other = Business.objects.create(owner=self.owner, name="Lead duplicates B", slug="lead-duplicates-b")
        self.role = BusinessRole.objects.create(business=self.business, name="Lead read boundaries")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="operator")
        BusinessMember.objects.create(business=self.business, user=self.outsider, role="operator")
        self.read = RolePermission.objects.create(business_role=self.role, resource="leads", action="view", is_allowed=False, scope="none")
        RolePermission.objects.create(business_role=self.role, resource="leads", action="create", scope="business")
        self.client_read = RolePermission.objects.create(business_role=self.role, resource="clients", action="view", scope="business")
        self.client = Client.objects.create(business=self.business, full_name="PRIVATE_CONTACT_916", phone="+77015550916", email="private916@example.invalid")
        self.own = Lead.objects.create(business=self.business, client=self.client, responsible_user=self.actor, message="Own permitted message", status="new")
        self.team_lead = Lead.objects.create(business=self.business, client=self.client, responsible_user=self.peer, message="TEAM_PRIVATE_916", status="contacted")
        self.hidden = Lead.objects.create(business=self.business, client=self.client, responsible_user=self.outsider, message="HIDDEN_MESSAGE_916", status="in_progress")
        now = timezone.now()
        for lead, days in [(self.own, 3), (self.team_lead, 2), (self.hidden, 1)]:
            Lead.objects.filter(pk=lead.pk).update(created_at=now-timedelta(days=days))
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def grant(self, scope="business", allowed=True):
        self.read.scope = scope
        self.read.is_allowed = allowed
        self.read.save()

    def check(self, **data):
        return self.api.post("/api/leads/check-duplicates/", {"business": self.business.pk, "client": self.client.pk, **data}, format="json")

    def test_view_denial_removes_all_lead_fields_but_keeps_safe_warning(self):
        response = self.check()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["related_leads"], [])
        self.assertTrue(response.data["has_restricted_related_leads"])
        self.assertNotIn("HIDDEN_MESSAGE_916", json.dumps(response.data))

    def test_own_scope_returns_only_assigned_lead(self):
        self.grant("own")
        response = self.check()
        self.assertEqual([r["id"] for r in response.data["related_leads"]], [self.own.pk])
        self.assertTrue(response.data["has_restricted_related_leads"])
        self.assertNotIn(self.hidden.message, json.dumps(response.data))

    def test_team_scope_returns_only_existing_team_members(self):
        self.grant("team")
        team = Team.objects.create(business=self.business, name="Synthetic team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        TeamMember.objects.create(team=team, member=self.peer_member)
        response = self.check()
        self.assertEqual({r["id"] for r in response.data["related_leads"]}, {self.own.pk, self.team_lead.pk})
        self.assertTrue(response.data["has_restricted_related_leads"])

    def test_business_scope_preserves_allowed_fields_and_ordinary_order(self):
        self.grant()
        response = self.check()
        self.assertEqual([r["id"] for r in response.data["related_leads"]], [self.hidden.pk, self.team_lead.pk, self.own.pk])
        self.assertEqual(response.data["related_leads"][0]["message"], self.hidden.message)
        self.assertEqual(response.data["related_leads"][0]["status"], "in_progress")
        self.assertFalse(response.data.get("has_restricted_related_leads", False))

    def test_owner_retains_allowed_duplicate_reader(self):
        self.api.force_authenticate(self.owner)
        response = self.check()
        self.assertEqual(len(response.data["related_leads"]), 3)
        self.assertEqual(response.data["related_leads"][0]["message"], self.hidden.message)

    def test_scope_applies_before_limit_and_hidden_count_is_not_returned(self):
        self.grant("own")
        for i in range(8):
            Lead.objects.create(business=self.business, client=self.client, responsible_user=self.outsider, message=f"hidden newer {i}")
        response = self.check()
        self.assertEqual([r["id"] for r in response.data["related_leads"]], [self.own.pk])
        self.assertTrue(response.data["has_restricted_related_leads"])
        self.assertNotIn("restricted_count", response.data)

    def test_client_view_deny_does_not_grant_client_fk_or_remove_readable_lead(self):
        self.grant()
        self.client_read.is_allowed = False
        self.client_read.save()
        response = self.check()
        self.assertEqual(len(response.data["related_leads"]), 3)
        self.assertTrue(all(row["client"] is None for row in response.data["related_leads"]))
        self.assertEqual(response.data["related_leads"][0]["message"], self.hidden.message)

    def test_unreadable_client_id_cannot_derive_contacts_for_duplicate_search(self):
        self.client_read.is_allowed = False
        self.client_read.save()
        Client.objects.create(business=self.business, full_name="OTHER_PRIVATE_CONTACT_916", phone=self.client.phone, email="other-private916@example.invalid")
        response = self.check()
        self.assertEqual(response.data["duplicates"], [])

    def test_explicit_contact_keeps_restricted_client_warning_without_details(self):
        self.client_read.is_allowed = False
        self.client_read.save()
        response = self.check(phone=self.client.phone)
        self.assertTrue(response.data["duplicates"])
        self.assertTrue(all(row["id"] is None for row in response.data["duplicates"]))
        self.assertNotIn(self.client.email, json.dumps(response.data))

    def test_permission_revocation_is_applied_on_next_read(self):
        self.grant()
        self.assertEqual(len(self.check().data["related_leads"]), 3)
        self.grant("none", False)
        response = self.check()
        self.assertEqual(response.data["related_leads"], [])
        self.assertTrue(response.data["has_restricted_related_leads"])

    def test_foreign_business_and_foreign_client_do_not_expand_query(self):
        other_client = Client.objects.create(business=self.other, full_name="Foreign", phone=self.client.phone)
        Lead.objects.create(business=self.other, client=other_client, message="FOREIGN_PRIVATE_MESSAGE")
        response = self.check(client=other_client.pk)
        self.assertEqual(response.data["related_leads"], [])
        self.assertNotIn("FOREIGN_PRIVATE_MESSAGE", json.dumps(response.data))
        self.assertEqual(self.check(business=self.other.pk).status_code, 400)

    def test_missing_actor_in_direct_serialization_fails_closed(self):
        serializer = LeadDuplicateCheckSerializer(data={"business": self.business.pk, "client": self.client.pk}, context={"request": SimpleNamespace(user=self.actor)})
        serializer.is_valid(raise_exception=True)
        serializer.context.clear()
        data = serializer.duplicates()
        self.assertEqual(data["related_leads"], [])
        self.assertTrue(data["has_restricted_related_leads"])

    def test_disabled_lead_capability_hides_direct_reader_even_for_owner(self):
        BusinessCapability.objects.update_or_create(business=self.business, module_key="leads", defaults={"is_enabled": False})
        serializer = LeadDuplicateCheckSerializer(data={"business": self.business.pk, "client": self.client.pk}, context={"request": SimpleNamespace(user=self.owner)})
        serializer.is_valid(raise_exception=True)
        self.assertEqual(serializer.duplicates()["related_leads"], [])

    def test_no_match_and_legacy_archived_read_semantics_preserved(self):
        self.grant()
        self.hidden.is_archived = True
        self.hidden.save(update_fields=["is_archived"])
        self.assertIn(self.hidden.pk, [r["id"] for r in self.check().data["related_leads"]])
        empty = Client.objects.create(business=self.business, full_name="No related lead")
        data = self.check(client=empty.pk).data
        self.assertEqual(data["related_leads"], [])
        self.assertFalse(data.get("has_restricted_related_leads", False))

    def test_readable_self_only_has_no_restricted_warning(self):
        self.grant()
        Lead.objects.exclude(pk=self.own.pk).delete()
        data = self.check().data
        self.assertEqual([r["id"] for r in data["related_leads"]], [self.own.pk])
        self.assertFalse(data.get("has_restricted_related_leads", False))
