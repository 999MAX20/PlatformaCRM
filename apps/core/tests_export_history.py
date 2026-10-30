from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.core.models import ExportJob


class ExportHistoryTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="history-owner", email="export-history@example.test")
        self.actor = User.objects.create_user(username="history-reader", email="reader@example.test")
        self.other = User.objects.create_user(username="history-other", email="other@example.test")
        self.business = Business.objects.create(owner=self.owner, name="History", slug="export-history")
        self.foreign = Business.objects.create(owner=self.other, name="Foreign", slug="export-foreign")
        self.role = BusinessRole.objects.create(business=self.business, name="History reader")
        self.member = BusinessMember.objects.create(business=self.business, user=self.actor, role="operator", business_role=self.role)
        self.permission = RolePermission.objects.create(business_role=self.role, resource="leads", action="view", scope="business")
        self.analytics = RolePermission.objects.create(business_role=self.role, resource="analytics", action="view", scope="business")
        RolePermission.objects.create(business_role=self.role, resource="clients", action="view", scope="none", is_allowed=False)
        self.api = APIClient()
        self.api.force_authenticate(self.actor)

    def job(self, **kwargs):
        return ExportJob.objects.create(**{"business": self.business, "actor": self.actor,
            "kind": "entity", "export_key": "leads", "status": "succeeded", "row_count": 3, **kwargs})

    def test_full_history_filters_before_pages_with_stable_ties(self):
        ids = [self.job().pk for _ in range(43)]
        for _ in range(24):
            self.job(kind="analytics_report", export_key="workspace_overview", status="pending")
        ExportJob.objects.all().update(created_at=timezone.now())
        seen = []
        for page, size in [(1, 20), (2, 20), (3, 3)]:
            result = self.api.get("/api/export-jobs/", {"business": self.business.pk, "kind": "entity", "status": "succeeded", "page": page})
            self.assertEqual(result.status_code, 200, result.data)
            self.assertEqual(result.data["count"], 43)
            self.assertEqual(len(result.data["results"]), size)
            seen.extend(row["id"] for row in result.data["results"])
        self.assertEqual(seen, list(reversed(ids)))
        self.assertEqual(self.api.get(f"/api/export-jobs/{ids[0]}/").status_code, 200)

    def test_actor_tenant_resource_and_membership_filter_history(self):
        own = self.job()
        self.job(actor=self.owner)
        self.job(business=self.foreign)
        self.job(export_key="clients")  # Explicit denial overrides the operator default.
        self.assertEqual([row["id"] for row in self.api.get("/api/export-jobs/").data["results"]], [own.pk])
        self.permission.is_allowed = False
        self.permission.save()
        self.assertEqual(self.api.get("/api/export-jobs/").data["count"], 0)
        self.assertEqual(self.api.get(f"/api/export-jobs/{own.pk}/").status_code, 404)
        self.permission.is_allowed = True
        self.permission.save()
        self.member.is_active = False
        self.member.save()
        self.assertEqual(self.api.get("/api/export-jobs/").data["count"], 0)

    def test_internal_fingerprint_is_not_history_data(self):
        job = self.job(parameters_json={"start": "2026-10-01", "end": "2026-10-31", "expected_rows": 3,
                                       "access_fingerprint_v1": "internal-proof", "arbitrary_internal": "hidden"})
        row = self.api.get(f"/api/export-jobs/{job.pk}/").data
        self.assertEqual(row["parameters_json"], {"start": "2026-10-01", "end": "2026-10-31", "expected_rows": 3})

    def test_invalid_query_is_400_and_wrong_context_is_404(self):
        job = self.job()
        for query in [{"business": "invalid"}, {"business": -1}, {"kind": "invalid"}, {"kind": ""}, {"status": "invalid"}]:
            with self.subTest(query=query):
                self.assertEqual(self.api.get("/api/export-jobs/", query).status_code, 400)
        self.assertEqual(self.api.get(f"/api/export-jobs/{job.pk}/", {"business": self.foreign.pk}).status_code, 404)
        self.assertEqual(self.api.get(f"/api/export-jobs/{job.pk}/", {"kind": "analytics_report"}).status_code, 404)

    def test_page_cap_empty_and_out_of_range(self):
        ExportJob.objects.bulk_create([ExportJob(business=self.business, actor=self.actor, kind="entity", export_key="leads") for _ in range(105)])
        result = self.api.get("/api/export-jobs/", {"page_size": 1000})
        self.assertEqual(result.data["count"], 105)
        self.assertEqual(len(result.data["results"]), 100)
        self.assertEqual(self.api.get("/api/export-jobs/", {"status": "failed"}).data["count"], 0)
        self.assertEqual(self.api.get("/api/export-jobs/", {"page": 99}).status_code, 404)
