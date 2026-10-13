from datetime import datetime, timedelta, timezone as dt_timezone

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.crm.models import Deal, Pipeline, PipelineStage
from apps.tasks.models import Task


class DealWorkspaceFilterTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="deal-filters", email="deal-filters@example.test", password="test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Deal filters", slug="deal-filters", timezone="Asia/Almaty")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.client = Client.objects.create(business=self.business, full_name="Patient")
        self.pipeline = Pipeline.objects.create(business=self.business, name="Sales")
        self.stage = PipelineStage.objects.create(business=self.business, pipeline=self.pipeline, name="New", order=1, sla_minutes=60)
        self.deal = Deal.objects.create(business=self.business, pipeline=self.pipeline, stage=self.stage, client=self.client, title="Own", owner=self.owner, amount=100, source="website")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def get(self, endpoint="", **params):
        return self.api.get(f"/api/deals/{endpoint}", {"workspace": "true", "pipeline": self.pipeline.pk, **params})

    def test_combined_filters_summary_and_board_share_scope(self):
        Deal.objects.create(business=self.business, pipeline=self.pipeline, stage=self.stage, client=self.client, title="Other", amount=900, status="won", source="manual")
        self.assertEqual(self.get().data["count"], 1)
        result = self.get(scope="mine", statuses="open,won", source="manual,website", amount_min=50, amount_max=150, stage=str(self.stage.pk))
        self.assertEqual(result.data["count"], 1)
        summary = self.get("summary/", scope="mine", search="Own", quick="no_tasks").data
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["no_tasks"], 1)
        board = self.get("board/", scope="mine", search="Own").data
        self.assertEqual(board["stages"][0]["count"], 1)
        self.assertEqual(self.get("summary/", search="missing").data["total"], 0)

    def test_next_action_and_sla_reasons_use_existing_domain_rules(self):
        self.assertEqual(self.get(quick="no_tasks").data["count"], 1)
        task = Task.objects.create(business=self.business, deal=self.deal, client=self.client, title="Call", assignee=self.owner)
        self.assertEqual(self.get(quick="no_tasks").data["count"], 0)
        task.is_archived = True
        task.save()
        self.assertEqual(self.get(quick="no_tasks").data["count"], 1)
        Deal.objects.filter(pk=self.deal.pk).update(next_action_at=timezone.now() + timedelta(days=1), stage_entered_at=timezone.now() - timedelta(hours=2))
        self.assertEqual(self.get(quick="no_tasks").data["count"], 0)
        self.assertEqual(self.get(attention_reason="sla").data["count"], 1)
        self.assertEqual(self.get(quick="hot").data["count"], 1)

    def test_date_boundaries_archive_and_invalid_ranges(self):
        Deal.objects.filter(pk=self.deal.pk).update(created_at=datetime(2026, 10, 12, 19, 30, tzinfo=dt_timezone.utc), expected_close_at="2026-10-15")
        self.assertEqual(self.get(created_from="2026-10-13", created_to="2026-10-13", expected_close_from="2026-10-15", expected_close_to="2026-10-15").data["count"], 1)
        self.assertEqual(self.get(created_to="2026-10-12").data["count"], 0)
        for params in [{"amount_min": "NaN"}, {"amount_min": -1}, {"amount_min": 100, "amount_max": 10}, {"stage": "bad"}, {"expected_close_from": "2026-11-01", "expected_close_to": "2026-10-01"}]:
            self.assertEqual(self.get(**params).status_code, 400)
        Deal.objects.filter(pk=self.deal.pk).update(is_archived=True)
        self.assertEqual(self.get().data["count"], 0)
        self.assertEqual(self.get(archive="archived", include_archived="true").data["count"], 1)

    def test_summary_and_board_counts_cover_full_matching_scope(self):
        Deal.objects.create(business=self.business, pipeline=self.pipeline, stage=self.stage, client=self.client, title="Scheduled", owner=self.owner, source="website", next_action_at=timezone.now() + timedelta(days=1))
        Deal.objects.create(business=self.business, pipeline=self.pipeline, stage=self.stage, client=self.client, title="Excluded", owner=self.owner, source="manual")
        response = self.get(scope="mine", source="website", page_size=1)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        summary = self.get("summary/", scope="mine", source="website", quick="no_tasks", page_size=1)
        self.assertEqual(summary.data["total"], 2)
        self.assertEqual(summary.data["no_tasks"], 1)
        board = self.get("board/", scope="mine", source="website", limit_per_stage=1)
        self.assertEqual(board.data["stages"][0]["count"], 2)
        self.assertEqual(len(board.data["stages"][0]["deals"]), 1)
