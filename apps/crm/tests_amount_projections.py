import csv
from datetime import timedelta
from decimal import Decimal
import io
import json

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.activities.models import ActivityEvent
from apps.activities.serializers import ActivityEventSerializer
from apps.ai_core.recommendations import build_owner_daily_brief
from apps.analytics.crm_metrics import build_crm_operational_metrics
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission, Team, TeamMember
from apps.clients.models import Client
from apps.core.crm_cards import deal_crm_card
from apps.core.export_access import assert_export_download_access
from apps.core.export_jobs import process_export_job, request_entity_export
from apps.core.import_export import export_deals
from apps.core.work_queues import build_work_queues
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.crm.selectors import build_deal_summary
from apps.crm.serializers import DealSerializer


class DealAmountProjectionTests(TestCase):
    markers = ("9371.42", "2482.36", "6193.84")

    def setUp(self):
        self.now = timezone.now()
        self.owner = User.objects.create_user(username="amount-owner", email="amount-owner@example.test")
        self.actor = User.objects.create_user(username="amount-reader", email="amount-reader@example.test")
        self.peer = User.objects.create_user(username="amount-peer", email="amount-peer@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Amount policy", slug="amount-policy")
        self.role = BusinessRole.objects.create(business=self.business, name="Amounts hidden")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.peer_member = BusinessMember.objects.create(business=self.business, user=self.peer, role="operator")
        for resource in ("deals", "clients", "analytics", "ai_analyst"):
            RolePermission.objects.create(business_role=self.role, resource=resource, action="view", scope="business")
        RolePermission.objects.create(business_role=self.role, resource="billing", action="view", scope="none", is_allowed=False)
        self.client = Client.objects.create(business=self.business, full_name="Synthetic amount client")
        self.pipeline = Pipeline.objects.create(business=self.business, name="Amounts", slug="amounts")
        self.stage = PipelineStage.objects.create(business=self.business, pipeline=self.pipeline, name="Open", sla_minutes=30, probability=50)
        self.deals = [Deal.objects.create(business=self.business, client=self.client, pipeline=self.pipeline, stage=self.stage,
            title=f"Synthetic deal {index}", owner=self.peer if index == 2 else self.actor, amount=marker, currency="USD",
            probability=50, status="won" if index == 1 else "open", stage_entered_at=self.now-timedelta(days=2))
            for index, marker in enumerate(self.markers)]
        self.deal = self.deals[0]
        self.event = ActivityEvent.objects.create(business=self.business, client=self.client, actor=self.owner,
            entity_type="Deal", entity_id=str(self.deal.pk), event_type="deal.value_changed", text="Deal value changed",
            metadata={"amount_before": self.markers[1], "amount_after": self.markers[0], "currency_before": "EUR", "currency_after": "USD",
                "reason": "synthetic", "nested": [{"previous_amount": self.markers[2], "amount_delta": "3177.58", "reason": "retained"}]})
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def grant_amount(self, allowed=True):
        RolePermission.objects.filter(business_role=self.role, resource="billing", action="view").update(is_allowed=allowed, scope="business" if allowed else "none")

    def assert_no_markers(self, value):
        text = json.dumps(value, default=str)
        for marker in self.markers:
            self.assertNotIn(marker, text)

    def summary(self, **params):
        return self.api.get("/api/deals/summary/", {"business": self.business.pk, **params})

    def test_standard_serializer_hidden_and_owner_controls(self):
        hidden = DealSerializer(self.deal, context={"actor": self.actor}).data
        self.assertIsNone(hidden["amount"])
        self.assertEqual(hidden["currency"], "")
        allowed = DealSerializer(self.deal, context={"actor": self.owner}).data
        self.assertEqual(allowed["amount"], self.markers[0])

    def test_csv_masks_only_amount_and_keeps_rows(self):
        rows = list(csv.DictReader(io.StringIO(export_deals(self.business, user=self.actor).content.decode())))
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["amount"] == "" for row in rows))
        self.assertEqual({int(row["id"]) for row in rows}, {d.pk for d in self.deals})

    def test_all_queue_representations_mask_amount_and_currency(self):
        queues = build_work_queues(business=self.business, user=self.actor, now=self.now)
        self.assert_no_markers(queues)
        items = [item for rows in queues["queues"].values() for item in rows if item.get("type") == "deal"]
        self.assertTrue(items)
        self.assertTrue(all(item["amount"] is None and item["currency"] == "" for item in items))

    def test_summary_masks_direct_and_derived_money_preserving_counts(self):
        response = self.summary()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["total"], 3)
        for key in ("open_value", "won_value", "lost_value", "pipeline_value", "expected_revenue"):
            self.assertIsNone(response.data[key])
        self.assert_no_markers(response.data)

    def test_legacy_amount_range_aliases_do_not_form_count_oracles(self):
        for path in ("/api/deals/", "/api/deals/board/", "/api/deals/summary/"):
            for key in ("amount_min", "amount_max", "min", "max"):
                with self.subTest(path=path, key=key):
                    response = self.api.get(path, {"business": self.business.pk, key: "9000"})
                    self.assertEqual(response.status_code, 403, getattr(response, "data", None))

    def test_workspace_amount_filters_and_ordering_are_guarded(self):
        for params in ({"amount_min": "9000"}, {"amount_max": "9000"}, {"ordering": "amount"}, {"ordering": "-amount"}):
            with self.subTest(params=params):
                response = self.api.get("/api/deals/", {"business": self.business.pk, "workspace": "true", **params})
                self.assertEqual(response.status_code, 403, response.data)

    def test_legacy_amount_ordering_is_guarded(self):
        for ordering in ("amount", "-amount"):
            with self.subTest(ordering=ordering):
                self.assertEqual(self.api.get("/api/deals/", {"business": self.business.pk, "ordering": ordering}).status_code, 403)

    def test_activity_endpoint_and_nested_money_do_not_disclose_values(self):
        response = self.api.get(f"/api/activity-events/{self.event.pk}/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assert_no_markers(response.data)
        self.assertNotIn("3177.58", json.dumps(response.data))
        self.assertEqual(response.data["metadata"]["reason"], "synthetic")
        self.event.refresh_from_db()
        self.assertEqual(self.event.metadata["amount_after"], self.markers[0])

    def test_card_passes_actor_to_timeline_and_keeps_owner_history(self):
        hidden = deal_crm_card(self.deal, actor=self.actor)
        self.assertTrue(hidden["timeline"])
        self.assert_no_markers(hidden)
        allowed = deal_crm_card(self.deal, actor=self.owner)
        self.assertIn(self.markers[0], json.dumps(allowed, default=str))
        self.assertEqual(allowed["timeline"][0]["metadata"]["amount_after"], self.markers[0])

    def test_ai_rule_brief_sources_use_same_field_policy(self):
        brief = build_owner_daily_brief(business=self.business, user=self.actor)
        sources = [s for s in brief["sources"] if s["entity_type"] == "deal"]
        self.assertTrue(sources)
        self.assert_no_markers(brief)
        self.grant_amount()
        allowed = build_owner_daily_brief(business=self.business, user=self.actor)
        self.assertIn(self.markers[0], json.dumps(allowed, default=str))

    def test_analytics_aggregate_values_mask_with_counts_preserved(self):
        team = Team.objects.create(business=self.business, name="Hidden amount reporting team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        TeamMember.objects.create(team=team, member=self.peer_member)
        metrics = build_crm_operational_metrics(self.business, user=self.actor, now=self.now)
        self.assertEqual(metrics["crm_funnel"]["deal_outcomes"]["open_count"], 2)
        for key in ("open_value", "won_value", "lost_value"):
            self.assertIsNone(metrics["crm_funnel"]["deal_outcomes"][key])
        self.assertTrue(metrics["manager_performance"]["rows"])
        for row in metrics["manager_performance"]["rows"]:
            self.assertIsNone(row["won_value"])
            self.assertIsNone(row["lost_value"])
        self.assert_no_markers(metrics)

    def test_missing_actor_fails_closed_for_sensitive_representations(self):
        self.assertIsNone(DealSerializer(self.deal).data["amount"])
        self.assertIsNone(build_deal_summary(Deal.objects.filter(business=self.business))["open_value"])
        self.assert_no_markers(ActivityEventSerializer(self.event).data)
        self.assertTrue(all(row["amount"] == "" for row in csv.DictReader(io.StringIO(export_deals(self.business).content.decode()))))

    def test_existing_manager_policy_and_billing_grant_are_preserved(self):
        self.grant_amount()
        self.assertEqual(self.summary().data["open_value"], "15565.26")
        rows = list(csv.DictReader(io.StringIO(export_deals(self.business, user=self.actor).content.decode())))
        self.assertIn(self.markers[0], [r["amount"] for r in rows])
        self.grant_amount(False)
        self.member.role = "manager"
        self.member.save(update_fields=["role"])
        self.assertEqual(self.summary().data["open_value"], "15565.26")
        queues = build_work_queues(business=self.business, user=self.owner, now=self.now)
        self.assertIn(self.markers[0], json.dumps(queues, default=str))

    def test_own_and_team_scope_remain_independent_of_field_visibility(self):
        permission = self.role.permissions.get(resource="deals", action="view")
        permission.scope = "own"
        permission.save()
        rows = list(csv.DictReader(io.StringIO(export_deals(self.business, user=self.actor).content.decode())))
        self.assertEqual({int(row["id"]) for row in rows}, {d.pk for d in self.deals[:2]})
        self.assertTrue(all(row["amount"] == "" for row in rows))
        team = Team.objects.create(business=self.business, name="Amount team")
        TeamMember.objects.create(team=team, member=self.member, is_lead=True)
        TeamMember.objects.create(team=team, member=self.peer_member)
        permission.scope = "team"
        permission.save()
        rows = list(csv.DictReader(io.StringIO(export_deals(self.business, user=self.actor).content.decode())))
        self.assertEqual(len(rows), 3)
        self.assertTrue(all(row["amount"] == "" for row in rows))

    @override_settings(EXPORT_SYNC_MAX_ROWS=0)
    def test_queued_export_renders_redacted_content(self):
        response, job = request_entity_export(business=self.business, actor=self.actor, export_key="deals")
        self.assertIsNone(response)
        job = process_export_job(job.pk)
        self.assertEqual(job.status, "succeeded", job.error)
        with job.result_file.open("rb") as stream:
            rows = list(csv.DictReader(io.StringIO(stream.read().decode())))
        self.assertTrue(rows)
        self.assertTrue(all(row["amount"] == "" for row in rows))

    @override_settings(EXPORT_SYNC_MAX_ROWS=0)
    def test_allowed_stored_export_cannot_be_downloaded_after_field_revocation(self):
        self.grant_amount()
        _, job = request_entity_export(business=self.business, actor=self.actor, export_key="deals")
        job = process_export_job(job.pk)
        self.assertEqual(job.status, "succeeded", job.error)
        assert_export_download_access(job, self.actor)
        self.grant_amount(False)
        with self.assertRaises(PermissionDenied):
            assert_export_download_access(job, self.actor)

    def test_permitted_filters_ordering_and_weighted_revenue_controls(self):
        self.grant_amount()
        response = self.api.get("/api/deals/", {"business": self.business.pk, "amount_min": "9000", "ordering": "amount"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["amount"], self.markers[0])
        self.assertEqual(self.summary().data["expected_revenue"], "7782.63")

    def test_permission_change_is_reflected_on_next_read(self):
        self.grant_amount()
        self.assertEqual(self.summary().data["won_value"], self.markers[1])
        self.grant_amount(False)
        self.assertIsNone(self.summary().data["won_value"])

    def test_mixed_business_summary_never_combines_hidden_amounts(self):
        other = Business.objects.create(owner=self.actor, name="Owned metrics", slug="owned-amounts")
        client = Client.objects.create(business=other, full_name="Synthetic owned client")
        pipeline = Pipeline.objects.create(business=other, name="Owned", slug="owned")
        stage = PipelineStage.objects.create(business=other, pipeline=pipeline, name="Start")
        Deal.objects.create(business=other, client=client, pipeline=pipeline, stage=stage, title="Permitted amount", amount=2)
        mixed = build_deal_summary(Deal.objects.filter(business__in=[self.business, other]), user=self.actor)
        self.assertEqual(mixed["total"], 4)
        self.assertIsNone(mixed["open_value"])
        permitted = build_deal_summary(Deal.objects.filter(business=other), user=self.actor)
        self.assertEqual(permitted["open_value"], "2.00")
