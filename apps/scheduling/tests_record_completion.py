from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from django.utils import timezone

from apps.activities.models import ActivityEvent
from apps.activities.taxonomy import ActivityEvents
from apps.core.models import AuditLog
from apps.scheduling.models import Appointment
from apps.scheduling.services import complete_appointment
from apps.scheduling.tests_record_commands import RecordCommandTests
from apps.tasks.models import Task


class RecordCompletionTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        RecordCommandTests.setUpTestData.__func__(cls)

    def setUp(self):
        RecordCommandTests.setUp(self)
        self.record = Appointment.objects.create(business=self.business, client=self.client_record,
            service=self.service, resource=self.resource, start_at=self.start,
            end_at=self.start + timedelta(minutes=30), responsible_user=self.owner)
        self.url = f"/api/appointments/{self.record.pk}/complete/"

    def test_early_completion_requires_reason_before_any_effect(self):
        before = (ActivityEvent.objects.count(), AuditLog.objects.count(), Task.objects.count())
        for reason in (None, "", "   ", "x" * 501):
            response = self.api.post(self.url, {} if reason is None else {"reason": reason}, format="json")
            self.assertEqual(response.status_code, 400, response.data)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, "created")
        self.assertEqual(before, (ActivityEvent.objects.count(), AuditLog.objects.count(), Task.objects.count()))

    def test_early_completion_records_actor_reason_time_and_is_not_replayed(self):
        response = self.api.post(self.url, {"reason": " Visit finished early ", "expected_updated_at": self.record.updated_at.isoformat()}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        event = ActivityEvent.objects.get(event_type=ActivityEvents.APPOINTMENT_COMPLETED, entity_id=str(self.record.pk))
        self.assertEqual(event.actor_id, self.owner.pk)
        self.assertEqual(event.metadata["reason"], "Visit finished early")
        self.assertTrue(event.metadata["early_completion"])
        self.assertTrue(event.metadata["completed_at"])
        audit = AuditLog.objects.get(entity_type="Appointment", entity_id=str(self.record.pk), metadata__event_type=ActivityEvents.APPOINTMENT_COMPLETED)
        self.assertEqual(audit.actor_id, self.owner.pk)
        self.assertEqual(audit.metadata["completed_at"], event.metadata["completed_at"])
        counts = (ActivityEvent.objects.count(), Task.objects.count())
        self.assertEqual(self.api.post(self.url, {"reason": "Visit finished early"}, format="json").status_code, 409)
        self.assertEqual(counts, (ActivityEvent.objects.count(), Task.objects.count()))

    def test_elapsed_unconfirmed_visit_can_complete_without_reason(self):
        self.record.start_at = timezone.now() - timedelta(hours=2)
        self.record.end_at = timezone.now() - timedelta(hours=1)
        self.record.save(update_fields=["start_at", "end_at"])
        response = self.api.post(self.url, {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        event = ActivityEvent.objects.get(event_type=ActivityEvents.APPOINTMENT_COMPLETED, entity_id=str(self.record.pk))
        self.assertFalse(event.metadata["early_completion"])

    def test_role_denial_and_stale_version_precede_completion(self):
        self.api.force_authenticate(self.staff)
        self.assertEqual(self.api.post(self.url, {"reason": "Finished"}, format="json").status_code, 404)
        self.api.force_authenticate(self.owner)
        response = self.api.post(self.url, {"reason": "Finished", "expected_updated_at": (self.record.updated_at - timedelta(seconds=1)).isoformat()}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, "created")

    def test_downstream_failure_rolls_back_status_audit_and_followups(self):
        before = (ActivityEvent.objects.count(), AuditLog.objects.count(), Task.objects.count())
        with patch("apps.scheduling.services.run_appointment_completed_automations", side_effect=RuntimeError("fixture failure")):
            with self.assertRaises(RuntimeError):
                complete_appointment(appointment=self.record, actor=self.owner, reason="Finished")
        self.record.refresh_from_db()
        self.assertEqual(self.record.status, "created")
        self.assertEqual(before, (ActivityEvent.objects.count(), AuditLog.objects.count(), Task.objects.count()))
