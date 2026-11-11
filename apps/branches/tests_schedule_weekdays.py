from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from django.db import close_old_connections
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.core.models import AuditLog
from apps.scheduling.models import Resource
from .models import Branch, BranchAccess, ScheduleDay, SpecialistBranch


class ScheduleWeekdaysTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="week-owner", email="week-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Network", slug="week-network")
        self.first = Branch.objects.create(business=self.business, name="First")
        self.second = Branch.objects.create(business=self.business, name="Second")
        self.resource = Resource.objects.create(business=self.business, name="Specialist", resource_type="staff")
        for branch in (self.first, self.second):
            SpecialistBranch.objects.create(business=self.business, branch=branch, resource=self.resource)
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def post(self, weekdays, **extra):
        return self.api.post(f"/api/branches/{self.first.pk}/schedule-weekdays/", {
            "resource": self.resource.pk, "weekdays": weekdays,
            "intervals": [{"start": "09:00", "end": "12:00"}], **extra,
        }, format="json")

    def test_multiple_days_and_repeat_have_one_row_per_day(self):
        for _ in range(2):
            response = self.post([0, 2, 4])
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(len(response.data), 3)
        self.assertEqual(ScheduleDay.objects.count(), 3)
        self.assertEqual(set(ScheduleDay.objects.values_list("weekday", flat=True)), {0, 2, 4})
        self.assertEqual(self.post([0, 2], intervals=[]).status_code, 200)
        self.assertEqual(ScheduleDay.objects.get(weekday=0).intervals, [])

    def test_later_day_conflict_rolls_back_all_days_and_audit(self):
        old = ScheduleDay.objects.create(business=self.business, branch=self.first, resource=self.resource,
            weekday=0, intervals=[{"start": "13:00", "end": "15:00"}])
        ScheduleDay.objects.create(business=self.business, branch=self.second, resource=self.resource,
            weekday=2, intervals=[{"start": "10:00", "end": "13:00"}])
        before = AuditLog.objects.count()
        response = self.post([0, 1, 2])
        self.assertEqual(response.status_code, 409, response.data)
        old.refresh_from_db()
        self.assertEqual(old.intervals, [{"start": "13:00", "end": "15:00"}])
        self.assertEqual(ScheduleDay.objects.count(), 2)
        self.assertEqual(AuditLog.objects.count(), before)

    def test_invalid_and_foreign_resource_have_no_effects(self):
        for days in ([], [0, 0], [7], [0, 1, 2, 3, 4, 5, 6, 0]):
            self.assertEqual(self.post(days).status_code, 400)
        other = Business.objects.create(owner=self.owner, name="Other", slug="week-other")
        resource = Resource.objects.create(business=other, name="Foreign", resource_type="staff")
        self.assertEqual(self.post([0], resource=resource.pk).status_code, 400)
        self.assertEqual(self.post([0], intervals=[{"start": "12:00", "end": "09:00"}]).status_code, 400)
        self.assertEqual(ScheduleDay.objects.count(), 0)

    def test_role_and_branch_scope_denied(self):
        user = User.objects.create_user(username="week-limited", email="week-limited@example.test")
        member = BusinessMember.objects.create(business=self.business, user=user, role="admin")
        BranchAccess.objects.create(member=member).branches.add(self.second)
        self.api.force_authenticate(user)
        self.assertEqual(self.post([0, 1]).status_code, 403)
        member.role = "specialist"
        member.save()
        self.assertIn(self.post([0, 1]).status_code, (403, 404))
        self.assertEqual(ScheduleDay.objects.count(), 0)

    def test_configuration_includes_only_global_and_selected_branch_absences(self):
        from .models import SpecialistAbsence
        for branch, date in ((None, "2030-01-07"), (self.first, "2030-01-08"), (self.second, "2030-01-09")):
            SpecialistAbsence.objects.create(business=self.business, resource=self.resource,
                branch=branch, starts_on=date, ends_on=date)
        response = self.api.get(f"/api/branches/{self.first.pk}/configuration/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual({str(row["starts_on"]) for row in response.data["absences"]}, {"2030-01-07", "2030-01-08"})


@skipUnlessDBFeature("has_select_for_update")
class ScheduleWeekdaysConcurrencyTests(TransactionTestCase):
    def test_competing_branch_templates_cannot_interleave_days(self):
        fixture = ScheduleWeekdaysTests()
        fixture.setUp()
        barrier = Barrier(2)

        def save(branch):
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(fixture.owner)
                barrier.wait(timeout=15)
                response = api.post(f"/api/branches/{branch.pk}/schedule-weekdays/", {
                    "resource": fixture.resource.pk, "weekdays": [0, 1],
                    "intervals": [{"start": "09:00", "end": "12:00"}],
                }, format="json")
                return response.status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(save, branch) for branch in (fixture.first, fixture.second)]
            results = [future.result(timeout=30) for future in futures]
        self.assertEqual(sorted(results), [200, 409])
        rows = list(ScheduleDay.objects.values_list("branch_id", "weekday"))
        self.assertEqual(len(rows), 2)
        self.assertEqual(len({branch for branch, _ in rows}), 1)
        self.assertEqual({day for _, day in rows}, {0, 1})
