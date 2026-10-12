from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo
from unittest.mock import patch

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource, WorkingHours, ScheduleException
from apps.scheduling.availability import get_available_slots
from apps.services.models import Service
from .models import Branch, ScheduleDay
from .services import create_branch


class FirstBranchCompatibilityTests(TestCase):
    def test_new_specialist_requires_explicit_branch_service_assignment(self):
        from apps.scheduling.resource_services import create_resource
        owner = User.objects.create_user(username="new-specialist-owner")
        business = Business.objects.create(owner=owner, name="Clinic", slug="explicit-specialist")
        create_branch(business=business, actor=owner, name="Original")
        resource = create_resource(business=business, name="New specialist")
        self.assertFalse(resource.branch_assignments.exists())

    def test_adoption_preserves_legacy_fallback_overrides_history_and_all_slots(self):
        owner = User.objects.create_user(username="compat-owner", email="compat@example.test")
        business = Business.objects.create(owner=owner, name="Legacy", slug="legacy-branch", timezone="Asia/Almaty")
        service = Service.objects.create(business=business, name="Visit", duration_minutes=30, price_from=12000)
        staff = Resource.objects.create(business=business, name="Doctor")
        start = datetime(2030, 1, 7, 10, tzinfo=ZoneInfo(business.timezone))
        WorkingHours.objects.create(business=business, weekday=0, start_time=time(9), end_time=time(12))
        WorkingHours.objects.create(business=business, resource=staff, weekday=1, start_time=time(8), end_time=time(20))
        ScheduleException.objects.create(business=business, resource=staff, date=start.date()+timedelta(days=2), start_time=time(7), end_time=time(21))
        days = [start.date()+timedelta(days=i) for i in range(3)]
        before = [get_available_slots(business, service, day, resource=staff) for day in days]
        client = Client.objects.create(business=business, full_name="Patient")
        visit = Appointment.objects.create(business=business, service=service, resource=staff, client=client,
            start_at=start-timedelta(days=7), end_at=start-timedelta(days=7)+timedelta(minutes=45), status="completed")
        branch = create_branch(business=business, actor=owner, name="Original", address="Original address")
        after = [get_available_slots(business, service, day, resource=staff, branch=branch) for day in days]
        self.assertEqual(before, after)
        visit.refresh_from_db()
        self.assertEqual(visit.branch_id, branch.pk)
        self.assertEqual(visit.booked_duration_minutes, 45)
        self.assertEqual(visit.status, "completed")
        self.assertEqual(visit.resource_id, staff.pk)

    def test_first_branch_setup_is_atomic(self):
        owner = User.objects.create_user(username="compat-owner")
        business = Business.objects.create(owner=owner, name="Legacy", slug="legacy-rollback")
        Resource.objects.create(business=business, name="Doctor")
        with patch("apps.branches.services.write_actor_audit_log", side_effect=RuntimeError("audit failed")):
            with self.assertRaises(RuntimeError):
                create_branch(business=business, actor=owner, name="Original")
        self.assertFalse(Branch.objects.exists())
        self.assertFalse(ScheduleDay.objects.exists())
