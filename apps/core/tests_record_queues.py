from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from apps.businesses.models import RolePermission
from apps.core.work_queues import build_work_queues
from apps.scheduling.models import Appointment
from apps.scheduling.tests_record_commands import RecordCommandTests


class RecordQueueTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        RecordCommandTests.setUpTestData.__func__(cls)

    def setUp(self):
        RecordCommandTests.setUp(self)
        self.now = timezone.now().replace(hour=10, minute=0, second=0, microsecond=0)

    def record(self, *, status="created", hours=1):
        start = self.now + timedelta(hours=hours)
        return Appointment.objects.create(business=self.business, client=self.client_record, service=self.service,
            resource=self.resource, start_at=start, end_at=start + timedelta(minutes=30), status=status)

    def test_record_queues_count_before_limit_and_keep_rescheduled_appointments(self):
        self.lead.status = "new"
        self.lead.save(update_fields=["status"])
        for _ in range(12):
            self.record(hours=-2)
        self.record(status="rescheduled")
        self.record(status="confirmed")
        self.record(status="cancelled")
        result = build_work_queues(business=self.business, user=self.owner, workflow="appointments", limit=3, now=self.now)
        self.assertEqual(result["summary"]["today_appointments"], 14)
        self.assertEqual(result["summary"]["upcoming_appointments"], 2)
        self.assertEqual(result["summary"]["appointment_confirmations"], 1)
        self.assertEqual(result["summary"]["pending_results"], 12)
        self.assertEqual(result["summary"]["total_attention"], 13)
        self.assertEqual(len(result["attention"]), 3)
        self.assertTrue(all(item["attention_reason"] == "pending_result" for item in result["attention"]))
        self.assertTrue(all(item["href"] == f"/app/appointments/{item['id']}" for item in result["attention"]))
        self.assertFalse(result["available"]["leads"])
        self.assertEqual(result["queues"]["stale_leads"], [])
        historical = build_work_queues(business=self.business, user=self.owner, now=self.now)
        self.assertEqual(historical["summary"]["stale_leads"], 1)

    def test_denied_records_do_not_enter_counts_or_preview(self):
        self.record(hours=-1)
        role = self.staff.business_memberships.get(business=self.business).business_role
        RolePermission.objects.update_or_create(business_role=role, resource="appointments", action="view",
            defaults={"scope": "business", "is_allowed": False})
        result = build_work_queues(business=self.business, user=self.staff, workflow="appointments", now=self.now)
        self.assertEqual(result["summary"]["pending_results"], 0)
        self.assertEqual(result["summary"]["today_appointments"], 0)
        self.assertFalse(result["available"]["appointments"])
        self.assertFalse(any(item["type"] == "appointment" for item in result["attention"]))

    def test_endpoint_validates_workflow_and_current_membership(self):
        self.assertEqual(self.api.get("/api/work-queues/", {"business": self.business.pk, "workflow": "appointments"}).status_code, 200)
        self.assertEqual(self.api.get("/api/work-queues/", {"business": self.business.pk, "workflow": "unknown"}).status_code, 400)
        self.api.force_authenticate(self.staff)
        self.staff.business_memberships.filter(business=self.business).update(is_active=False)
        self.assertEqual(self.api.get("/api/work-queues/", {"business": self.business.pk, "workflow": "appointments"}).status_code, 403)
