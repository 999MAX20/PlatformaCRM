from datetime import datetime, timedelta

from django.test import TestCase

from apps.businesses.models import Business, RolePermission
from apps.scheduling.models import Appointment
from apps.scheduling import tests_record_commands as fixtures


class CalendarSummaryTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        fixtures.RecordCommandTests.setUpTestData.__func__(cls)

    def setUp(self):
        fixtures.RecordCommandTests.setUp(self)

    def record(self, start="2026-11-04T09:00:00+00:00", **overrides):
        at = datetime.fromisoformat(start)
        return Appointment.objects.create(**{
            "business": self.business, "client": self.client_record,
            "service": self.service, "resource": self.resource,
            "start_at": at, "end_at": at + timedelta(minutes=30), **overrides,
        })

    def summary(self, **params):
        return self.api.get("/api/appointments/calendar-summary/", {
            "business": self.business.pk, "start_from": "2026-01-01", "start_to": "2027-01-01", **params,
        })

    def test_year_counts_are_complete_and_do_not_return_details(self):
        for _ in range(31):
            self.record()
        self.record("2026-12-31T23:30:00+00:00", status="completed")
        response = self.summary(page_size=1)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["days"], [
            {"date": "2026-11-04", "appointments": 31}, {"date": "2026-12-31", "appointments": 1},
        ])
        self.assertEqual(response.data["total"], 32)
        self.assertEqual(set(response.data), {"start_from", "start_to", "timezone", "days", "total"})

    def test_empty_year_and_historical_and_future_years(self):
        self.record("2020-06-15T10:00:00+00:00")
        self.record("2030-06-15T10:00:00+00:00")
        self.assertEqual(self.summary().data["days"], [])
        for year in (2020, 2030):
            with self.subTest(year=year):
                result = self.summary(start_from=f"{year}-01-01", start_to=f"{year + 1}-01-01")
                self.assertEqual(result.status_code, 200, result.data)
                self.assertEqual(result.data["total"], 1)

    def test_local_midnight_start_inclusive_end_exclusive(self):
        self.business.timezone = "Asia/Qyzylorda"
        self.business.save(update_fields=["timezone"])
        self.record("2025-12-31T18:59:00+00:00")
        self.record("2025-12-31T19:00:00+00:00")
        self.record("2026-12-31T18:59:00+00:00")
        self.record("2026-12-31T19:00:00+00:00")
        self.assertEqual(self.summary().data["days"], [
            {"date": "2026-01-01", "appointments": 1}, {"date": "2026-12-31", "appointments": 1},
        ])

    def test_leap_day_and_dst_zone(self):
        self.business.timezone = "America/New_York"
        self.business.save(update_fields=["timezone"])
        self.record("2024-03-01T04:30:00+00:00")
        self.record("2024-03-10T07:30:00+00:00")
        result = self.summary(start_from="2024-01-01", start_to="2025-01-01")
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["days"], [
            {"date": "2024-02-29", "appointments": 1}, {"date": "2024-03-10", "appointments": 1},
        ])

    def test_archives_never_count_even_if_requested(self):
        self.record(is_archived=True)
        self.record(status="cancelled")
        self.assertEqual(self.summary(include_archived="true").data["total"], 1)

    def test_filters_combine_and_nonmatching_ids_are_empty(self):
        from apps.branches.models import Branch
        branch = Branch.objects.create(business=self.business, name="First")
        selected = self.record(branch=branch, status="confirmed")
        self.record(status="created")
        response = self.summary(branch=branch.pk, service=selected.service_id,
                                resource=selected.resource_id, status="confirmed")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["total"], 1)
        for key in ("branch", "service", "resource"):
            self.assertEqual(self.summary(**{key: 999999}).data["total"], 0)

    def test_invalid_inputs_are_rejected_before_queryset(self):
        for params in ({"business": "bad"}, {"resource": "bad"}, {"service": -1},
                       {"branch": "bad"}, {"status": "unknown"}, {"start_from": "bad"},
                       {"start_to": "2026-01-01"}, {"start_to": "2025-01-01"},
                       {"start_to": "2028-01-01"}, {"start_from": "2026-02-30"}):
            with self.subTest(params=params):
                self.assertEqual(self.summary(**params).status_code, 400)
        self.assertEqual(self.api.get("/api/appointments/calendar-summary/").status_code, 400)

    def test_foreign_business_and_revoked_membership(self):
        foreign = Business.objects.create(owner=self.staff, name="Foreign", slug="calendar-foreign")
        self.record(business=foreign)
        self.assertEqual(self.summary(business=foreign.pk).status_code, 400)
        self.assertEqual(self.summary().data["total"], 0)
        self.api.force_authenticate(self.staff)
        self.staff.business_memberships.filter(business=self.business).update(is_active=False)
        self.assertEqual(self.summary().status_code, 400)

    def test_own_scope_matches_detail_visibility(self):
        self.record()
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.summary().data["total"], 0)
        self.resource.linked_user = self.staff
        self.resource.save(update_fields=["linked_user"])
        self.assertEqual(self.summary().data["total"], 1)

    def test_role_denial_and_unauthenticated(self):
        role = self.staff.business_memberships.get(business=self.business).business_role
        RolePermission.objects.update_or_create(business_role=role, resource="appointments", action="view",
            defaults={"scope": "business", "is_allowed": False})
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.summary().status_code, 403)
        self.api.force_authenticate(None)
        self.assertIn(self.summary().status_code, (401, 403))

    def test_branch_write_grant_does_not_narrow_business_history_view(self):
        from apps.branches.models import Branch, BranchAccess
        member = self.staff.business_memberships.get(business=self.business)
        RolePermission.objects.update_or_create(business_role=member.business_role, resource="appointments", action="view",
            defaults={"scope": "business", "is_allowed": True})
        allowed = Branch.objects.create(business=self.business, name="Allowed")
        denied = Branch.objects.create(business=self.business, name="Denied")
        grant = BranchAccess.objects.create(member=member)
        grant.branches.add(allowed)
        self.record(branch=allowed)
        self.record(branch=denied)
        self.api.force_authenticate(self.staff)
        # CRM-MB01 keeps history shared under the current record VIEW scope.
        self.assertEqual(self.summary().data["total"], 2)
        self.assertEqual(self.summary(branch=denied.pk).data["total"], 1)
        listed = self.api.get("/api/appointments/", {"business": self.business.pk})
        rows = listed.data["results"] if isinstance(listed.data, dict) else listed.data
        self.assertEqual(len(rows), self.summary().data["total"])
