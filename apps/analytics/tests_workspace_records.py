from django.test import TestCase

from apps.analytics import tests_workspace as fixtures
from apps.accounts.models import User
from apps.businesses.models import BusinessMember, BusinessCapability, BusinessRole, RolePermission
from apps.scheduling.models import Resource


class WorkspaceRecordTests(TestCase):
    setUp = fixtures.AnalyticsWorkspaceTests.setUp
    appointment = fixtures.AnalyticsWorkspaceTests.appointment
    report = fixtures.AnalyticsWorkspaceTests.report

    def detail(self, **params):
        return self.api.get("/api/analytics/reports/records/", {"business": self.business.pk,
            "start": "2026-10-01", "end": "2026-10-14", **params})

    def test_exact_start_cohort_archive_and_status_group_match_summary(self):
        expected = []
        for index, status in enumerate(("created", "confirmed", "rescheduled", "completed", "cancelled", "no_show")):
            expected.append(self.appointment(status=status, is_archived=index % 2 == 0).pk)
        self.appointment(at="2026-09-30T23:30:00+05:00")  # Overlaps, but start is outside the cohort.
        self.appointment(at="2026-10-15T00:00:00+05:00")
        response = self.detail()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], self.report().data["appointments"]["total"])
        self.assertCountEqual([row["id"] for row in response.data["results"]], expected)
        self.assertEqual(self.detail(metric="planned").data["count"], 3)
        for status in ("completed", "cancelled", "no_show"):
            self.assertEqual(self.detail(metric=status).data["count"], 1)

    def test_filters_combine_and_pagination_has_no_duplicates(self):
        for _ in range(28):
            self.appointment(status="completed", source="website", responsible_user=self.owner)
        self.appointment(status="cancelled", source="manual")
        first = self.detail(metric="completed", source="website", service=self.service.pk, responsible_user=self.owner.pk)
        second = self.detail(metric="completed", source="website", service=self.service.pk, responsible_user=self.owner.pk, page=2)
        self.assertEqual(first.data["count"], 28)
        self.assertEqual(len(first.data["results"]), 25)
        self.assertEqual(len(second.data["results"]), 3)
        ids = [row["id"] for page in (first, second) for row in page.data["results"]]
        self.assertEqual(len(set(ids)), 28)
        self.assertEqual(self.detail(service=999999).data["count"], 0)

    def test_invalid_filters_and_read_only_method(self):
        for params in ({"metric": "unknown"}, {"source": "wrong"}, {"page_size": 101},
                       {"responsible_user": "abc"}, {"service": -1}, {"page": 0},
                       {"start": "9999-12-31", "end": "9999-12-31"}, {"business": "abc"}):
            with self.subTest(params=params):
                self.assertEqual(self.detail(**params).status_code, 400)
        self.assertEqual(self.api.post("/api/analytics/reports/records/", {}).status_code, 405)

    def test_tenant_role_own_scope_and_member_boundary(self):
        manager = User.objects.create_user(username="detail-manager", email="detail-manager@example.test")
        role = BusinessRole.objects.create(business=self.business, name="Own detail")
        for resource in ("analytics", "appointments"):
            RolePermission.objects.create(business_role=role, resource=resource, action="view", scope="own")
        BusinessMember.objects.create(business=self.business, user=manager, role="manager", business_role=role)
        resource = Resource.objects.create(business=self.business, name="Own specialist", linked_user=manager)
        mine = self.appointment(responsible_user=manager, resource=resource)
        hidden = self.appointment(responsible_user=self.owner)
        self.api.force_authenticate(manager)
        self.assertEqual([row["id"] for row in self.detail().data["results"]], [mine.pk])
        self.assertEqual(self.detail(responsible_user=self.owner.pk).status_code, 400)
        self.assertEqual(self.detail(business=self.other_business.pk).status_code, 400)
        self.assertNotIn(str(hidden.pk), [str(row["id"]) for row in self.detail().data["results"]])
        operator = User.objects.create_user(username="detail-operator", email="detail-operator@example.test")
        BusinessMember.objects.create(business=self.business, user=operator, role="operator")
        self.api.force_authenticate(operator)
        self.assertEqual(self.detail().status_code, 403)
        self.api.force_authenticate(self.owner)
        BusinessCapability.objects.update_or_create(business=self.business, module_key="appointments", defaults={"is_enabled": False})
        self.assertEqual(self.detail().status_code, 403)

    def test_client_permission_redacts_identity_but_preserves_cohort(self):
        self.appointment()
        BusinessCapability.objects.update_or_create(business=self.business, module_key="clients", defaults={"is_enabled": False})
        response = self.detail()
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data["count"], 1)
        row = response.data["results"][0]
        self.assertIsNone(row["client"])
        self.assertEqual(row["client_name"], "")
        self.assertNotIn("client_phone", row)
        self.assertNotIn("notes", row)
