"""Internal CRM completeness: atomic commands and fresh persisted state."""
from decimal import Decimal
from unittest.mock import patch
from types import SimpleNamespace

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.businesses.access import ensure_default_roles
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import InvalidTransition
from apps.core.archive import archive_instance
from apps.core.models import AuditLog
from apps.crm.models import Deal, DealStageHistory, DealValueHistory, Pipeline, PipelineStage
from apps.crm.services import move_deal_stage
from apps.leads.models import Lead
from apps.leads.services import mark_lead_contacted, mark_lead_lost


class CRMServerScenarioFixture(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="server-owner", email="server-owner@example.com", role=User.Roles.BUSINESS_OWNER)
        self.manager = User.objects.create_user(username="server-manager", email="server-manager@example.com", role=User.Roles.BUSINESS_MANAGER)
        self.business = Business.objects.create(owner=self.owner, name="Scenario business", slug="server-scenarios")
        ensure_default_roles(self.business)
        for user, role in ((self.owner, "owner"), (self.manager, "manager")):
            BusinessMember.objects.create(
                business=self.business, user=user, role=role,
                business_role=BusinessRole.objects.get(business=self.business, preset_key=role),
            )
        self.customer = Client.objects.create(business=self.business, full_name="Scenario client")
        self.lead = Lead.objects.create(business=self.business, client=self.customer, responsible_user=self.owner)
        self.pipeline = Pipeline.objects.create(business=self.business, name="Sales", slug="sales", is_default=True)
        self.first = PipelineStage.objects.create(business=self.business, pipeline=self.pipeline, name="New", order=1)
        self.next_stage = PipelineStage.objects.create(business=self.business, pipeline=self.pipeline, name="Offer", order=2)
        self.won = PipelineStage.objects.create(business=self.business, pipeline=self.pipeline, name="Won", order=3, is_won=True)
        self.lost = PipelineStage.objects.create(business=self.business, pipeline=self.pipeline, name="Lost", order=4, is_lost=True)
        self.deal = Deal.objects.create(
            business=self.business, client=self.customer, pipeline=self.pipeline, stage=self.first,
            title="Scenario deal", amount=Decimal("100"), owner=self.owner,
        )
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.api.raise_request_exception = False

    def effect_counts(self):
        return ActivityEvent.objects.count(), AuditLog.objects.count(), DealStageHistory.objects.count()


class LeadServerScenarios(CRMServerScenarioFixture):
    def test_create_deal_rejects_invalid_money_without_partial_records(self):
        before = self.effect_counts()
        for amount in ("not-money", "NaN", "99999999999999999.00", "12.345"):
            with self.subTest(amount=amount):
                response = self.api.post(f"/api/leads/{self.lead.pk}/create-deal/", {"amount": amount}, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.assertFalse(Deal.objects.filter(lead=self.lead).exists())
                self.lead.refresh_from_db()
                self.assertEqual(self.lead.status, Lead.Statuses.NEW)
                self.assertEqual(self.effect_counts(), before)

    def test_status_audit_failure_rolls_back_command(self):
        before = self.effect_counts()
        with patch("apps.leads.services.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.post(f"/api/leads/{self.lead.pk}/mark-lost/", {"lost_reason": "No longer needed"})
        self.assertEqual(response.status_code, 500)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Statuses.NEW)
        self.assertEqual(self.lead.lost_reason, "")
        self.assertEqual(self.effect_counts(), before)

    def test_assignment_audit_failure_rolls_back_command(self):
        before = self.effect_counts()
        with patch("apps.leads.services.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.post(f"/api/leads/{self.lead.pk}/assign/", {"user_id": self.manager.pk})
        self.assertEqual(response.status_code, 500)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.responsible_user_id, self.owner.pk)
        self.assertEqual(self.effect_counts(), before)

    def test_stale_instance_cannot_bypass_lost_lead_reopen(self):
        stale = Lead.objects.get(pk=self.lead.pk)
        mark_lead_lost(lead=self.lead, actor=self.owner, lost_reason="No longer needed")
        before = self.effect_counts()
        with self.assertRaises(InvalidTransition):
            mark_lead_contacted(lead=stale, actor=self.owner)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Statuses.LOST)
        self.assertEqual(self.effect_counts(), before)

    def test_repeated_lost_preserves_reopen_state_and_single_effect(self):
        url = f"/api/leads/{self.lead.pk}/mark-lost/"
        data = {"lost_reason": "No longer needed"}
        self.assertEqual(self.api.post(url, data).status_code, 200)
        self.lead.refresh_from_db()
        previous = self.lead.previous_status
        before = self.effect_counts()
        response = self.api.post(url, data)
        self.assertIn(response.status_code, (200, 409))
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.previous_status, previous)
        self.assertEqual(self.effect_counts(), before)


class DealServerScenarios(CRMServerScenarioFixture):
    def test_quick_terminal_actions_obey_the_same_stage_requirements(self):
        before = self.effect_counts()
        for stage, action, payload in ((self.won, "mark-won", {}), (self.lost, "mark-lost", {"lost_reason": "No longer needed"})):
            with self.subTest(action=action):
                stage.required_fields_json = {"fields": ["expected_close_at"]}
                stage.save(update_fields=["required_fields_json"])
                response = self.api.post(f"/api/deals/{self.deal.pk}/{action}/", payload, format="json")
                self.assertEqual(response.status_code, 400, response.data)
                self.deal.refresh_from_db()
                self.assertEqual(self.deal.status, Deal.Statuses.OPEN)
                self.assertEqual(self.effect_counts(), before)
        self.assertEqual(self.api.patch(f"/api/deals/{self.deal.pk}/", {"expected_close_at": "2030-01-01"}, format="json").status_code, 200)
        self.assertEqual(self.api.post(f"/api/deals/{self.deal.pk}/mark-won/", {}, format="json").status_code, 200)

    def test_amount_update_audit_failure_rolls_back_value_and_history(self):
        before = self.effect_counts()
        with patch("apps.crm.services.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.patch(f"/api/deals/{self.deal.pk}/", {"amount": "250.00"}, format="json")
        self.assertEqual(response.status_code, 500)
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.amount, Decimal("100.00"))
        self.assertEqual(self.effect_counts(), before)
        self.assertFalse(DealValueHistory.objects.filter(deal=self.deal).exists())

    def test_stage_audit_failure_rolls_back_command_and_history(self):
        before = self.effect_counts()
        with patch("apps.crm.services.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.post(f"/api/deals/{self.deal.pk}/move-stage/", {"stage": self.next_stage.pk})
        self.assertEqual(response.status_code, 500)
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.stage_id, self.first.pk)
        self.assertEqual(self.effect_counts(), before)

    def test_stale_stage_change_does_not_overwrite_new_amount(self):
        stale = Deal.objects.get(pk=self.deal.pk)
        response = self.api.patch(f"/api/deals/{self.deal.pk}/", {"amount": "250.00"}, format="json")
        self.assertEqual(response.status_code, 200)
        move_deal_stage(deal=stale, stage=self.next_stage, actor=self.owner)
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.amount, Decimal("250.00"))
        history = DealStageHistory.objects.get(deal=self.deal)
        self.assertEqual(history.amount_before, Decimal("250.00"))
        self.assertEqual(history.amount_after, Decimal("250.00"))

    def test_repeated_lost_preserves_previous_stage_and_single_effect(self):
        url = f"/api/deals/{self.deal.pk}/mark-lost/"
        data = {"lost_reason": "No longer needed"}
        self.assertEqual(self.api.post(url, data).status_code, 200)
        self.deal.refresh_from_db()
        previous = self.deal.previous_stage_id
        before = self.effect_counts()
        response = self.api.post(url, data)
        self.assertIn(response.status_code, (200, 409))
        self.deal.refresh_from_db()
        self.assertEqual(self.deal.previous_stage_id, previous)
        self.assertEqual(self.effect_counts(), before)

    def test_repeated_won_amount_has_single_effect_and_validates_input(self):
        url = f"/api/deals/{self.deal.pk}/mark-won/"
        for amount in ("not-money", "NaN", "99999999999999999.00", "12.345"):
            with self.subTest(amount=amount):
                self.assertEqual(self.api.post(url, {"amount": amount}).status_code, 400)
                self.deal.refresh_from_db()
                self.assertEqual(self.deal.status, Deal.Statuses.OPEN)
                self.assertEqual(self.deal.amount, Decimal("100"))
        self.assertEqual(self.api.post(url, {"amount": "250.00"}).status_code, 200)
        before = self.effect_counts()
        self.assertEqual(self.api.post(url, {"amount": "250.00"}).status_code, 200)
        self.assertEqual(self.effect_counts(), before)
        self.assertEqual(DealValueHistory.objects.filter(deal=self.deal).count(), 1)


class ArchiveServerScenarios(CRMServerScenarioFixture):
    def test_archive_audit_failure_leaves_record_and_effects_unchanged(self):
        before = self.effect_counts()
        with patch("apps.core.archive.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.post(f"/api/leads/{self.lead.pk}/archive/", {"reason": "No longer needed"})
        self.assertEqual(response.status_code, 500)
        self.lead.refresh_from_db()
        self.assertFalse(self.lead.is_archived)
        self.assertEqual(self.effect_counts(), before)

    def test_stale_archive_does_not_repeat_effects_or_replace_reason(self):
        stale = Lead.objects.get(pk=self.lead.pk)
        self.assertEqual(self.api.post(f"/api/leads/{self.lead.pk}/archive/", {"reason": "First reason"}).status_code, 200)
        before = self.effect_counts()
        request = SimpleNamespace(user=self.owner, META={}, headers={})
        archive_instance(request, stale, reason="Stale reason")
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.archive_reason, "First reason")
        self.assertEqual(self.effect_counts(), before)

    def test_restore_audit_failure_leaves_record_archived(self):
        self.assertEqual(self.api.post(f"/api/leads/{self.lead.pk}/archive/", {"reason": "Archived"}).status_code, 200)
        before = self.effect_counts()
        with patch("apps.core.archive.write_audit_log", side_effect=RuntimeError("audit unavailable")):
            response = self.api.post(f"/api/leads/{self.lead.pk}/restore/")
        self.assertEqual(response.status_code, 500)
        self.lead.refresh_from_db()
        self.assertTrue(self.lead.is_archived)
        self.assertEqual(self.effect_counts(), before)


class AccessServerScenarios(CRMServerScenarioFixture):
    def test_created_deal_replay_denied_after_object_scope_changes(self):
        Lead.objects.filter(pk=self.lead.pk).update(responsible_user=self.manager)
        self.api.force_authenticate(self.manager)
        url = f"/api/leads/{self.lead.pk}/create-deal/"
        data = {"amount": "1250.50", "title": "Linked deal"}
        first = self.api.post(url, data, format="json", HTTP_IDEMPOTENCY_KEY="reassigned-deal")
        self.assertEqual(first.status_code, 201, first.data)
        Deal.objects.filter(pk=first.data["id"]).update(owner=self.owner)
        before = self.effect_counts()
        for key in ("reassigned-deal", "new-command-reassigned-deal"):
            with self.subTest(key=key):
                response = self.api.post(url, data, format="json", HTTP_IDEMPOTENCY_KEY=key)
                self.assertEqual(response.status_code, 403, response.data)
        self.assertEqual(self.effect_counts(), before)
        self.assertEqual(Deal.objects.filter(lead=self.lead).count(), 1)

    def test_lead_create_deal_replay_uses_current_field_permissions(self):
        Lead.objects.filter(pk=self.lead.pk).update(responsible_user=self.manager)
        self.api.force_authenticate(self.manager)
        url = f"/api/leads/{self.lead.pk}/create-deal/"
        data = {"amount": "1250.50", "title": "Linked deal"}
        response = self.api.post(url, data, format="json", HTTP_IDEMPOTENCY_KEY="role-change")
        self.assertEqual(response.status_code, 201, response.data)
        linked_id = response.data["id"]
        operator = BusinessRole.objects.get(business=self.business, preset_key="operator")
        BusinessMember.objects.filter(business=self.business, user=self.manager).update(role="operator", business_role=operator)
        for resource, action in (("leads", "view"), ("deals", "view"), ("deals", "create")):
            RolePermission.objects.update_or_create(business_role=operator, resource=resource, action=action,
                defaults={"is_allowed": True, "scope": RolePermission.Scopes.BUSINESS})
        RolePermission.objects.update_or_create(business_role=operator, resource="billing", action="view",
            defaults={"is_allowed": False, "scope": RolePermission.Scopes.NONE})
        before = self.effect_counts()
        for key in ("role-change", "new-command-existing-deal"):
            with self.subTest(key=key):
                response = self.api.post(url, data, format="json", HTTP_IDEMPOTENCY_KEY=key)
                self.assertIn(response.status_code, (200, 201), response.data)
                self.assertEqual(response.data["id"], linked_id)
                self.assertIsNone(response.data["amount"])
                self.assertEqual(response.data["notes"], "")
        self.assertEqual(self.effect_counts(), before)
        self.assertEqual(Deal.objects.filter(lead=self.lead).count(), 1)

    def test_reassignment_after_view_check_denies_stale_lead_action(self):
        from apps.leads.services import mark_lead_lost as execute
        Lead.objects.filter(pk=self.lead.pk).update(responsible_user=self.manager)
        self.api.force_authenticate(self.manager)

        def reassign_then_execute(**kwargs):
            Lead.objects.filter(pk=self.lead.pk).update(responsible_user=self.owner)
            return execute(**kwargs)

        before = self.effect_counts()
        with patch("apps.leads.views.mark_lead_lost", side_effect=reassign_then_execute):
            response = self.api.post(f"/api/leads/{self.lead.pk}/mark-lost/", {"lost_reason": "Stale action"})
        self.assertEqual(response.status_code, 403, response.data)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, Lead.Statuses.NEW)
        self.assertEqual(self.effect_counts(), before)

    def test_archived_lead_and_deal_cannot_change_lifecycle(self):
        for entity, route in ((self.lead, "leads"), (self.deal, "deals")):
            with self.subTest(route=route):
                entity.__class__.objects.filter(pk=entity.pk).update(is_archived=True)
                before = self.effect_counts()
                response = self.api.post(f"/api/{route}/{entity.pk}/mark-lost/?include_archived=true", {"lost_reason": "Not allowed"})
                self.assertEqual(response.status_code, 409, response.data)
                entity.refresh_from_db()
                self.assertNotEqual(entity.status, "lost")
                self.assertEqual(self.effect_counts(), before)
