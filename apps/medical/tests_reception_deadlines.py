from datetime import date, datetime, time, timezone
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.exceptions import ValidationError

from apps.accounts.models import User
from apps.branches.models import Branch, ScheduleDay
from apps.businesses.models import Business
from apps.scheduling.models import WorkingHours
from .reception_deadlines import reception_acceptance_deadline


class ReceptionDeadlineTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="reception-deadline", email="deadline@example.test")
        self.business = Business.objects.create(owner=owner, name="Synthetic reception", slug="deadline", timezone="Asia/Qyzylorda")
        self.branch = Branch.objects.create(business=self.business, name="First")
        self.other = Branch.objects.create(business=self.business, name="Second")
        for weekday in range(5):
            ScheduleDay.objects.create(business=self.business, branch=self.branch, weekday=weekday,
                intervals=[{"start": "09:00", "end": "12:00"}, {"start": "13:00", "end": "18:00"}])

    def local(self, value):
        return datetime.fromisoformat(value).replace(tzinfo=ZoneInfo("Asia/Qyzylorda"))

    def due(self, value, **changes):
        return reception_acceptance_deadline(**({"business": self.business, "branch_id": self.branch.pk,
            "requested_at": self.local(value), "patient_in_clinic": False} | changes))

    def test_onsite_five_elapsed_minutes_even_outside_opening_hours(self):
        self.assertEqual(self.due("2026-11-22T23:58:00", patient_in_clinic=True), self.local("2026-11-23T00:03:00"))

    def test_thirty_minutes_cross_break_without_rounding_away_seconds(self):
        self.assertEqual(self.due("2026-11-23T11:45:30"), self.local("2026-11-23T13:15:30"))
        self.assertEqual(self.due("2026-11-23T08:00:00"), self.local("2026-11-23T09:30:00"))
        self.assertEqual(self.due("2026-11-23T17:30:00"), self.local("2026-11-23T18:00:00"))

    def test_weekend_and_explicit_holiday_are_skipped(self):
        ScheduleDay.objects.create(business=self.business, branch=self.branch, date=date(2026, 11, 23), intervals=[])
        self.assertEqual(self.due("2026-11-20T17:45:00"), self.local("2026-11-24T09:15:00"))

    def test_future_schedule_and_date_override_use_selected_branch_only(self):
        ScheduleDay.objects.create(business=self.business, branch=self.branch, weekday=0,
            effective_from=date(2026, 11, 23), intervals=[{"start": "10:00", "end": "14:00"}])
        self.assertEqual(self.due("2026-11-23T09:00:00"), self.local("2026-11-23T10:30:00"))
        ScheduleDay.objects.create(business=self.business, branch=self.branch, date=date(2026, 11, 23),
            intervals=[{"start": "15:00", "end": "16:00"}])
        self.assertEqual(self.due("2026-11-23T09:00:00"), self.local("2026-11-23T15:30:00"))
        self.assertIsNone(self.due("2026-11-23T09:00:00", branch_id=self.other.pk))

    def test_explicit_business_defaults_reuse_existing_working_hours(self):
        WorkingHours.objects.create(business=self.business, weekday=0, start_time=time(8), end_time=time(16))
        self.assertIsNone(self.due("2026-11-23T09:00:00", branch_id=self.other.pk))
        self.other.uses_business_defaults = True
        self.other.save(update_fields=["uses_business_defaults"])
        self.assertEqual(self.due("2026-11-23T07:00:00", branch_id=self.other.pk), self.local("2026-11-23T08:30:00"))

    def test_foreign_archived_branch_and_invalid_inputs_rejected(self):
        foreign = Business.objects.create(owner=self.business.owner, name="Foreign", slug="deadline-foreign")
        foreign_branch = Branch.objects.create(business=foreign, name="Foreign")
        for changes in ({"branch_id": foreign_branch.pk}, {"branch_id": True}, {"patient_in_clinic": 1},
                        {"requested_at": datetime(2026, 11, 23)}):
            with self.assertRaises(ValidationError):
                self.due("2026-11-23T09:00:00", **changes)
        self.branch.archived_at = datetime.now(timezone.utc)
        self.branch.save(update_fields=["archived_at"])
        with self.assertRaises(ValidationError):
            self.due("2026-11-23T09:00:00")
