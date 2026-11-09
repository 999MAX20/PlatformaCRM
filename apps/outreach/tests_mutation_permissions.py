"""OFFICIAL-19: effective action permissions constrain existing outreach roles."""
from types import SimpleNamespace
from unittest.mock import patch

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.businesses.access import Resources
from apps.businesses.capabilities import module_for_resource
from apps.core.domain_errors import ModuleDisabled
from apps.clients.models import Client
from apps.notifications.models import Notification
from apps.outreach.models import OutreachCampaign, OutreachConsent, OutreachRecipient, OutreachTemplate


class OutreachMutationPermissionTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="outreach-policy-owner", email="outreach-policy-owner@example.test")
        self.actor = User.objects.create_user(username="outreach-policy-reader", email="outreach-policy-reader@example.test")
        self.peer = User.objects.create_user(username="outreach-policy-peer", email="outreach-policy-peer@example.test")
        self.outside = User.objects.create_user(username="outreach-policy-outside", email="outreach-policy-outside@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Synthetic outreach", slug="outreach-mutation-policy")
        self.role = BusinessRole.objects.create(business=self.business, name="Restricted marketer")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="marketer", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="marketer")
        BusinessMember.objects.create(business=self.business, user=self.outside, role="marketer")
        RolePermission.objects.create(business_role=self.role, resource="notifications", action="view", scope="business")
        RolePermission.objects.create(business_role=self.role, resource="notifications", action="manage", is_allowed=False, scope="none")
        self.customer = Client.objects.create(business=self.business, full_name="Synthetic customer", telegram_id="synthetic-recipient")
        self.campaign = OutreachCampaign.objects.create(business=self.business, created_by=self.actor,
            name="Synthetic campaign", channel="telegram", message_text="Hello", audience_type="manual")
        self.template = OutreachTemplate.objects.create(business=self.business, created_by=self.actor,
            name="Synthetic template", channel="telegram", body="Hello")
        self.consent = OutreachConsent.objects.create(business=self.business, client=self.customer, channel="telegram", status="unknown")
        self.api = APIClient()
        self.api.force_authenticate(self.actor)
        scanner = patch("apps.core.antivirus.scan_stream", return_value=SimpleNamespace(clean=True))
        scanner.start()
        self.addCleanup(scanner.stop)

    def grant(self, action="manage", allowed=True, scope="business"):
        RolePermission.objects.update_or_create(business_role=self.role, resource="notifications", action=action,
            defaults={"is_allowed": allowed, "scope": scope})

    def effects(self):
        return tuple(model.objects.count() for model in (OutreachCampaign, OutreachTemplate, OutreachConsent, OutreachRecipient, Notification))

    def campaign_payload(self, **extra):
        return {"business": self.business.pk, "name": "Created synthetic", "channel": "telegram", "message_text": "Hello", **extra}

    def template_payload(self, **extra):
        return {"business": self.business.pk, "name": "Created synthetic", "channel": "telegram", "body": "Hello", **extra}

    def test_campaign_create_respects_manage_fallback_deny(self):
        before = self.effects()
        response = self.api.post("/api/outreach/campaigns/", self.campaign_payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(self.effects(), before)

    def test_template_create_respects_manage_fallback_deny(self):
        before = self.effects()
        response = self.api.post("/api/outreach/templates/", self.template_payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(self.effects(), before)

    def test_consent_create_respects_manage_fallback_deny(self):
        before = self.effects()
        response = self.api.post("/api/outreach/consents/", {"business": self.business.pk, "client": self.customer.pk,
            "channel": "whatsapp", "status": "opted_out"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(self.effects(), before)

    def test_all_campaign_manage_actions_deny_before_domain_call(self):
        for action, function in (("prepare", "prepare_campaign_recipients"), ("launch", "launch_campaign"),
                                 ("retry-failed", "retry_failed_recipients"), ("cancel", "cancel_campaign")):
            with self.subTest(action=action), patch("apps.outreach.views."+function, return_value={"synthetic": True}) as call:
                before = self.effects()
                response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/{action}/", {}, format="json")
                self.assertEqual(response.status_code, 403, response.data)
                call.assert_not_called()
                self.assertEqual(self.effects(), before)

    def test_bulk_json_respects_manage_deny(self):
        before = self.effects()
        response = self.api.post("/api/outreach/consents/bulk-import/", {"business": self.business.pk,
            "channel": "telegram", "status": "opted_out", "rows": [{"client": self.customer.pk}]}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.consent.refresh_from_db()
        self.assertEqual(self.consent.status, "unknown")
        self.assertEqual(self.effects(), before)

    def test_bulk_file_respects_manage_deny(self):
        response = self.api.post("/api/outreach/consents/bulk-import-file/", {"business": self.business.pk,
            "file": SimpleUploadedFile("synthetic.csv", f"client,channel,status\n{self.customer.pk},telegram,opted_out\n".encode(), content_type="text/csv")}, format="multipart")
        self.assertEqual(response.status_code, 403, response.data)
        self.consent.refresh_from_db()
        self.assertEqual(self.consent.status, "unknown")

    def test_manage_revocation_between_requests_is_current(self):
        self.grant()
        with patch("apps.outreach.views.prepare_campaign_recipients", return_value={"synthetic": True}) as call:
            self.assertEqual(self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/prepare/").status_code, 200)
            self.grant(allowed=False)
            response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/prepare/")
            self.assertEqual(response.status_code, 403, response.data)
            self.assertEqual(call.call_count, 1)

    def test_own_manage_denies_another_creator(self):
        self.grant(scope="own")
        OutreachCampaign.objects.filter(pk=self.campaign.pk).update(created_by=self.peer)
        with patch("apps.outreach.views.cancel_campaign", return_value={"synthetic": True}) as call:
            response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/cancel/")
            self.assertEqual(response.status_code, 403, response.data)
            call.assert_not_called()

    def test_team_manage_denies_outside_creator(self):
        self.grant(scope="team")
        team = Team.objects.create(business=self.business, name="Synthetic outreach team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        TeamMember.objects.create(team=team, member=self.peer_member)
        OutreachCampaign.objects.filter(pk=self.campaign.pk).update(created_by=self.outside)
        with patch("apps.outreach.views.prepare_campaign_recipients", return_value={"synthetic": True}) as call:
            response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/prepare/")
            self.assertEqual(response.status_code, 403, response.data)
            call.assert_not_called()

    def test_team_membership_removal_narrows_manage(self):
        self.grant(scope="team")
        team = Team.objects.create(business=self.business, name="Synthetic outreach team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        peer = TeamMember.objects.create(team=team, member=self.peer_member)
        OutreachCampaign.objects.filter(pk=self.campaign.pk).update(created_by=self.peer)
        with patch("apps.outreach.views.prepare_campaign_recipients", return_value={"synthetic": True}) as call:
            self.assertEqual(self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/prepare/").status_code, 200)
            peer.delete()
            response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/prepare/")
            self.assertEqual(response.status_code, 403, response.data)
            self.assertEqual(call.call_count, 1)

    def test_owner_preset_create_control(self):
        self.api.force_authenticate(self.owner)
        response = self.api.post("/api/outreach/templates/", self.template_payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)

    def test_admin_preset_create_control(self):
        self.member.role = "admin"
        self.member.business_role = None
        self.member.save(update_fields=["role", "business_role"])
        response = self.api.post("/api/outreach/campaigns/", self.campaign_payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)

    def test_marketer_preset_create_control(self):
        self.member.business_role = None
        self.member.save(update_fields=["business_role"])
        response = self.api.post("/api/outreach/templates/", self.template_payload(), format="json")
        self.assertEqual(response.status_code, 201, response.data)

    def test_existing_role_eligibility_fence_is_not_expanded(self):
        self.grant()
        self.member.role = "manager"
        self.member.save(update_fields=["role"])
        response = self.api.post("/api/outreach/campaigns/", self.campaign_payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)

    def test_foreign_business_does_not_inherit_own_grant(self):
        self.grant()
        foreign = Business.objects.create(owner=self.outside, name="Foreign outreach", slug="foreign-outreach-policy")
        campaign = OutreachCampaign.objects.create(business=foreign, created_by=self.outside, name="Foreign", channel="telegram", message_text="Hello")
        self.assertEqual(self.api.post(f"/api/outreach/campaigns/{campaign.pk}/cancel/").status_code, 404)
        response = self.api.post("/api/outreach/campaigns/", self.campaign_payload(business=foreign.pk), format="json")
        self.assertEqual(response.status_code, 403, response.data)

    def test_action_specific_create_deny_overrides_manage(self):
        self.grant()
        self.grant(action="create", allowed=False)
        response = self.api.post("/api/outreach/templates/", self.template_payload(), format="json")
        self.assertEqual(response.status_code, 403, response.data)

    def test_action_specific_update_deny_is_preserved(self):
        self.grant()
        self.grant(action="update", allowed=False)
        response = self.api.patch(f"/api/outreach/campaigns/{self.campaign.pk}/", {"name": "Denied"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)

    def test_specific_update_allow_is_not_replaced_with_manage_requirement(self):
        self.grant(action="update")
        response = self.api.patch(f"/api/outreach/campaigns/{self.campaign.pk}/", {"name": "Allowed update"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.name, "Allowed update")

    def test_create_own_uses_server_creator_candidate(self):
        self.grant(scope="own")
        response = self.api.post("/api/outreach/templates/", self.template_payload(created_by=self.peer.pk), format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(OutreachTemplate.objects.get(pk=response.data["id"]).created_by_id, self.actor.pk)

    def test_consent_create_own_has_no_invented_client_ownership(self):
        self.grant(scope="own")
        response = self.api.post("/api/outreach/consents/", {"business": self.business.pk, "client": self.customer.pk,
            "channel": "whatsapp", "status": "opted_out"}, format="json")
        self.assertEqual(response.status_code, 403, response.data)

    def test_bulk_own_cannot_mutate_unowned_consent(self):
        self.grant(scope="own")
        response = self.api.post("/api/outreach/consents/bulk-import/", {"business": self.business.pk,
            "channel": "telegram", "status": "opted_out", "rows": [{"client": self.customer.pk}]}, format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.consent.refresh_from_db()
        self.assertEqual(self.consent.status, "unknown")

    def test_own_manage_denies_legacy_unowned_campaign(self):
        self.grant(scope="own")
        OutreachCampaign.objects.filter(pk=self.campaign.pk).update(created_by=None)
        with patch("apps.outreach.views.prepare_campaign_recipients", return_value={"synthetic": True}) as call:
            response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/prepare/")
            self.assertEqual(response.status_code, 403, response.data)
            call.assert_not_called()

    def test_admin_role_does_not_override_current_manage_deny(self):
        self.member.role = "admin"
        self.member.save(update_fields=["role"])
        with patch("apps.outreach.views.prepare_campaign_recipients", return_value={"synthetic": True}) as call:
            response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/prepare/")
            self.assertEqual(response.status_code, 403, response.data)
            call.assert_not_called()

    def test_multibusiness_action_grants_are_not_reused(self):
        self.grant()
        foreign = Business.objects.create(owner=self.outside, name="Second outreach", slug="second-outreach-policy")
        role = BusinessRole.objects.create(business=foreign, name="Second restricted marketer")
        BusinessMember.objects.create(business=foreign, user=self.actor, role="marketer", business_role=role)
        RolePermission.objects.create(business_role=role, resource="notifications", action="view", scope="business")
        RolePermission.objects.create(business_role=role, resource="notifications", action="manage", is_allowed=False, scope="none")
        self.assertEqual(self.api.post("/api/outreach/campaigns/", self.campaign_payload(), format="json").status_code, 201)
        response = self.api.post("/api/outreach/campaigns/", self.campaign_payload(business=foreign.pk), format="json")
        self.assertEqual(response.status_code, 403, response.data)
        self.assertFalse(OutreachCampaign.objects.filter(business=foreign).exists())

    def test_capability_boundary_is_used_without_inventing_module_mapping(self):
        # Current registry deliberately has no notifications module/toggle.
        self.assertIsNone(module_for_resource(Resources.NOTIFICATIONS))
        self.grant()
        before = self.effects()
        with patch("apps.outreach.views.assert_resource_enabled", side_effect=ModuleDisabled()) as capability:
            response = self.api.post("/api/outreach/campaigns/", self.campaign_payload(), format="json")
            self.assertEqual(response.status_code, 403, response.data)
            capability.assert_called_once()
        with patch("apps.outreach.views.assert_resource_enabled", side_effect=ModuleDisabled()), \
             patch("apps.outreach.views.prepare_campaign_recipients", return_value={"synthetic": True}) as call:
            response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/prepare/")
            self.assertEqual(response.status_code, 403, response.data)
            call.assert_not_called()
        self.assertEqual(self.effects(), before)

    def test_unowned_consent_update_retains_existing_update_policy(self):
        # Existing can(UPDATE) permits unowned records; MANAGE differs.
        self.grant(action="update", scope="own")
        response = self.api.patch(f"/api/outreach/consents/{self.consent.pk}/", {"status": "opted_out"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.consent.refresh_from_db()
        self.assertEqual(self.consent.status, "opted_out")

    def test_own_manage_real_prepare_cancel_control_has_no_delivery(self):
        self.grant(scope="own")
        response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/prepare/", {"client_ids": [self.customer.pk]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertTrue(OutreachRecipient.objects.filter(campaign=self.campaign, client=self.customer).exists())
        response = self.api.post(f"/api/outreach/campaigns/{self.campaign.pk}/cancel/", {"reason": "Synthetic control"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.campaign.refresh_from_db()
        self.assertEqual(self.campaign.status, "cancelled")
        self.assertFalse(Notification.objects.filter(channel__in=["telegram", "whatsapp"], status="sent").exists())
