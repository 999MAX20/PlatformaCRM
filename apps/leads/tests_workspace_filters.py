from datetime import timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.tasks.models import Task


class LeadWorkspaceFilterTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="lead-filters", email="lead-filters@example.test", password="test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Lead filters", slug="lead-filters")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.client = Client.objects.create(business=self.business, full_name="Patient")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        self.mine = Lead.objects.create(business=self.business, client=self.client, responsible_user=self.owner, source="website")
        self.unassigned = Lead.objects.create(business=self.business, client=self.client, status="in_progress", source="manual")
        self.closed = Lead.objects.create(business=self.business, client=self.client, status="closed", responsible_user=self.owner)

    def get(self, endpoint="", **params):
        response = self.api.get(f"/api/leads/{endpoint}", {"workspace": "true", **params})
        return response

    def test_scope_combines_with_quick_status_and_contextual_counts(self):
        result = self.get(scope="mine", quick="new")
        self.assertEqual(result.status_code, 200)
        self.assertEqual([item["id"] for item in result.data["results"]], [self.mine.pk])
        self.assertEqual(self.get().data["count"], 2)
        self.assertEqual(self.get(statuses="closed,lost").data["count"], 1)
        summary = self.get("summary/", source="website", search="Patient", page_size=1, quick="attention").data
        self.assertEqual(summary["total"], 1)
        self.assertEqual(summary["new"], 1)
        self.assertEqual(self.get("summary/", search="nothing").data["total"], 0)

    def test_attention_is_missing_owner_or_action_or_overdue_not_idle_age(self):
        tomorrow = timezone.now() + timedelta(days=1)
        task = Task.objects.create(business=self.business, lead=self.mine, client=self.client, title="Call", assignee=self.owner, due_at=tomorrow)
        Lead.objects.filter(pk=self.mine.pk).update(updated_at=timezone.now() - timedelta(days=20))
        self.assertEqual(self.get(scope="mine", quick="attention").data["count"], 0)
        task.due_at = timezone.now() - timedelta(minutes=1)
        task.save()
        item = self.get(scope="mine", quick="attention").data["results"][0]
        self.assertEqual(item["attention_reasons"], ["overdue_action"])
        task.status = "done"
        task.save()
        self.assertEqual(self.get(scope="mine", quick="attention").data["results"][0]["attention_reasons"], ["no_action"])
        result = self.get(attention_reason="unassigned")
        self.assertEqual(result.data["count"], 1)
        self.assertIn("unassigned", result.data["results"][0]["attention_reasons"])

    def test_invalid_filters_archive_and_tenant_do_not_expand_access(self):
        stranger = User.objects.create_user(username="stranger-filter", email="stranger-filter@example.test", password="test")
        foreign = Business.objects.create(owner=stranger, name="Foreign", slug="foreign-lead-filter")
        client = Client.objects.create(business=foreign, full_name="Foreign")
        Lead.objects.create(business=foreign, client=client, responsible_user=stranger)
        self.assertEqual(self.get(assignees=str(stranger.pk), statuses="all").data["count"], 0)
        self.assertEqual(self.get(assignees=f"{self.owner.pk},unassigned").data["count"], 2)
        for params in [{"statuses": "invalid"}, {"assignees": "invalid"}, {"created_to": "bad"}, {"attention_reason": "invalid"}]:
            self.assertEqual(self.get(**params).status_code, 400)
        Lead.objects.filter(pk=self.mine.pk).update(is_archived=True)
        self.assertEqual(self.get().data["count"], 1)
        self.assertEqual(self.get(archive="archived", include_archived="true").data["count"], 1)
        self.api.force_authenticate(stranger)
        result = self.get(statuses="all", include_archived="true", archive="all")
        self.assertEqual(result.data["count"], 1)
        self.assertEqual(result.data["results"][0]["business"], foreign.pk)

    def test_counts_cover_all_pages_and_ignore_only_quick_filter(self):
        Lead.objects.create(business=self.business, client=self.client, responsible_user=self.owner, source="website")
        Lead.objects.create(business=self.business, client=self.client, responsible_user=self.owner, source="website", status="in_progress")
        response = self.get(scope="mine", source="website", quick="new", page_size=1)
        self.assertEqual(response.data["count"], 2)
        self.assertEqual(len(response.data["results"]), 1)
        summary = self.get("summary/", scope="mine", source="website", quick="new", page_size=1)
        self.assertEqual(summary.data["total"], 3)
        self.assertEqual(summary.data["new"], 2)
        self.assertEqual(summary.data["in_progress"], 1)
