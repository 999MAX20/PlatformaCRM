from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource, WorkingHours
from apps.services.models import Service
from .models import ScheduleDay, SpecialistAbsence
from .services import create_branch


class StaffLifecycleTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="absence-owner", email="absence-owner@example.test")
        self.user = User.objects.create_user(username="absence-doctor", email="absence-doctor@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Clinic", slug="absence-clinic", timezone="Asia/Almaty")
        self.member = BusinessMember.objects.create(business=self.business, user=self.user, role="specialist")
        self.resource = Resource.objects.create(business=self.business, name="Doctor", linked_user=self.user)
        self.service = Service.objects.create(business=self.business, name="Visit", duration_minutes=30)
        self.client_record = Client.objects.create(business=self.business, full_name="Patient")
        self.branch = create_branch(business=self.business, actor=self.owner, name="Main")
        for resource in [None, self.resource]:
            for weekday in range(7):
                ScheduleDay.objects.update_or_create(business=self.business, branch=self.branch, resource=resource, weekday=weekday,
                    defaults={"intervals": [{"start": "09:00", "end": "18:00"}]})
        self.start = datetime(2030, 1, 7, 10, tzinfo=ZoneInfo(self.business.timezone))
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def book(self, start=None):
        return self.api.post("/api/appointments/", {"business": self.business.pk, "branch": self.branch.pk,
            "client": self.client_record.pk, "service": self.service.pk, "resource": self.resource.pk,
            "start_at": (start or self.start).isoformat()}, format="json")

    def absence(self, **extra):
        return self.api.post(f"/api/resources/{self.resource.pk}/absences/", {
            "starts_on": "2030-01-07", "ends_on": "2030-01-09", "reason": "sick", **extra}, format="json")

    def test_absence_blocks_new_slots_keeps_visits_and_expires_by_date(self):
        visit = self.book()
        self.assertEqual(visit.status_code, 201, visit.data)
        response = self.absence()
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Appointment.objects.get(pk=visit.data["id"]).status, "created")
        self.assertEqual(self.book(self.start + timedelta(hours=1)).status_code, 409)
        self.assertEqual(self.book(self.start + timedelta(days=2)).status_code, 409)
        self.assertEqual(self.book(self.start + timedelta(days=3)).status_code, 201)
        self.resource.refresh_from_db()
        self.assertTrue(self.resource.is_active)
        self.assertEqual(self.api.post(f"/api/resources/{self.resource.pk}/remove-absence/", {"absence": response.data["id"]}).status_code, 200)
        self.assertEqual(self.book(self.start + timedelta(hours=1)).status_code, 201)

    def test_retirement_requires_review_preserves_history_and_only_disables_business_membership(self):
        future = self.book()
        self.assertEqual(future.status_code, 201, future.data)
        endpoint = f"/api/resources/{self.resource.pk}/retire/"
        self.assertEqual(self.api.post(endpoint, {"disable_access": True}).status_code, 409)
        historical = Appointment.objects.create(business=self.business, branch=self.branch, service=self.service,
            resource=self.resource, client=self.client_record, status="completed", start_at=self.start-timedelta(days=5000), end_at=self.start-timedelta(days=5000)+timedelta(minutes=30))
        response = self.api.post(f'/api/appointments/{future.data["id"]}/cancel/', {"reason": "Patient chose another specialist"})
        self.assertEqual(response.status_code, 200, response.data)
        from apps.tasks.models import Task
        followups = Task.objects.filter(business=self.business, assignee=self.user, status__in=["open", "in_progress"])
        self.assertTrue(followups.exists())
        self.assertEqual(self.api.post(endpoint, {"disable_access": True}).status_code, 409)
        for task in followups:
            completed = self.api.post(f"/api/tasks/{task.pk}/complete/")
            self.assertEqual(completed.status_code, 200, completed.data)
        result = self.api.post(endpoint, {"disable_access": True})
        self.assertEqual(result.status_code, 200, result.data)
        self.resource.refresh_from_db()
        self.member.refresh_from_db()
        self.user.refresh_from_db()
        self.assertFalse(self.member.is_active)
        self.assertTrue(self.user.is_active)
        self.assertIsNotNone(self.resource.retired_at)
        self.assertFalse(self.resource.branch_assignments.filter(is_active=True).exists())
        historical.refresh_from_db()
        self.assertEqual(historical.resource_id, self.resource.pk)
        self.assertEqual(self.api.patch(f"/api/resources/{self.resource.pk}/", {"is_active": True}).status_code, 400)
        self.assertEqual(self.api.post(endpoint, {"disable_access": True}).status_code, 200)

    def test_absence_and_retirement_permissions_and_audit_rollback(self):
        self.api.force_authenticate(self.user)
        self.assertIn(self.absence().status_code, [403, 404])
        self.assertFalse(SpecialistAbsence.objects.exists())
        self.api.force_authenticate(self.owner)
        self.assertEqual(self.absence(ends_on="2030-01-06").status_code, 400)
        with patch("apps.branches.staff_lifecycle.write_actor_audit_log", side_effect=RuntimeError("audit failed")):
            self.assertEqual(self.absence().status_code, 500)
        self.assertFalse(SpecialistAbsence.objects.exists())

    def test_branch_pause_and_archive_keep_future_appointments(self):
        visit = self.book()
        self.assertEqual(visit.status_code, 201)
        self.assertEqual(self.api.post(f"/api/branches/{self.branch.pk}/state/", {"state": "paused"}).status_code, 200)
        self.assertEqual(self.book(self.start + timedelta(hours=1)).status_code, 400)
        self.assertEqual(self.api.post(f"/api/branches/{self.branch.pk}/state/", {"state": "archived"}).status_code, 409)
        self.assertEqual(Appointment.objects.get(pk=visit.data["id"]).status, "created")
