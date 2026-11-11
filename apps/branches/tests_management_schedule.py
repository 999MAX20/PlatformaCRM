from datetime import date

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.core.domain_errors import ScheduleConflict
from apps.scheduling.models import Resource
from apps.scheduling.resource_booking import ResourceCalendar
from .configuration import save_schedule_day
from .models import Branch, ScheduleDay, SpecialistBranch, BranchTravelTime
from .schedule import day_intervals


class EffectiveScheduleTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="schedule-version", email="schedule-version@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Versions", slug="versions")
        self.branch = Branch.objects.create(business=self.business, name="First")
        self.staff = Resource.objects.create(business=self.business, name="Staff")
        self.room = Resource.objects.create(business=self.business, name="Room", resource_type="room", branch=self.branch)
        SpecialistBranch.objects.create(business=self.business, branch=self.branch, resource=self.staff)
        self.api = APIClient()
        self.api.force_authenticate(self.owner)
        for target in [None, self.staff]:
            ScheduleDay.objects.create(business=self.business, branch=self.branch, resource=target, weekday=0,
                intervals=[{"start": "09:00", "end": "18:00"}])

    def test_api_effective_date_preserves_previous_hours_and_room_inheritance(self):
        response = self.api.post(f"/api/branches/{self.branch.pk}/schedule-weekdays/",
            {"weekdays": [0], "effective_from": "2030-01-14", "intervals": [{"start": "11:00", "end": "16:00"}]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        for day, start in [(date(2030, 1, 7), "09:00"), (date(2030, 1, 14), "11:00")]:
            self.assertEqual(day_intervals(self.branch, None, date=day)[0]["start"], start)
            calendar = ResourceCalendar(self.business, self.branch, [self.room], date=day)
            self.assertEqual(calendar.intervals(self.room, 0, day)[0]["start"], start)
        self.assertEqual(ScheduleDay.objects.filter(resource=None).count(), 2)
        save_schedule_day(branch=self.branch, actor=self.owner, date=date(2030, 1, 14), intervals=[])
        self.assertEqual(day_intervals(self.branch, None, date=date(2030, 1, 14)), [])

    def test_future_cross_branch_shift_collision_rolls_back(self):
        other = Branch.objects.create(business=self.business, name="Second")
        SpecialistBranch.objects.create(business=self.business, branch=other, resource=self.staff)
        BranchTravelTime.objects.create(business=self.business, from_branch=self.branch, to_branch=other, minutes=0)
        with self.assertRaises(ScheduleConflict):
            save_schedule_day(branch=other, actor=self.owner, resource_id=self.staff.pk, weekday=0,
                effective_from=date(2030, 1, 14), intervals=[{"start": "10:00", "end": "12:00"}])
        self.assertFalse(ScheduleDay.objects.filter(branch=other).exists())

    def test_date_override_rejects_effective_date(self):
        response = self.api.post(f"/api/branches/{self.branch.pk}/schedule/",
            {"date": "2030-01-14", "effective_from": "2030-01-14", "intervals": []}, format="json")
        self.assertEqual(response.status_code, 400)
        self.assertFalse(ScheduleDay.objects.filter(date__isnull=False).exists())
