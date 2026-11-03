from datetime import time, timedelta

from django.test import TestCase
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.ai_core.tests_crm_tools import CRMCommandTests
from apps.ai_core.assistant import build_crm_context
from apps.ai_core.tool_registry import suggest_tool_calls
from apps.activities.taxonomy import ActivityEvents
from apps.scheduling.models import Appointment, Resource, WorkingHours
from apps.services.models import Service


class RecordAIWorkflowTests(TestCase):
    proposal = CRMCommandTests.proposal
    approval = CRMCommandTests.approval
    execute = CRMCommandTests.execute

    def setUp(self):
        CRMCommandTests.setUp(self)
        self.business.timezone = "UTC"
        self.business.save(update_fields=["timezone"])
        self.service = Service.objects.create(business=self.business, name="Visit", duration_minutes=30)
        self.resource = Resource.objects.create(business=self.business, name="Specialist")
        for day in range(7):
            WorkingHours.objects.create(business=self.business, weekday=day, start_time=time(8), end_time=time(18))
        self.start = (timezone.now() + timedelta(days=2)).replace(hour=10, minute=0, second=0, microsecond=0)
        self.values = {"client": self.person.pk, "service": self.service.pk, "resource": self.resource.pk, "start_at": self.start.isoformat()}

    def test_confirmed_creation_replays_one_record_without_lead_or_deal(self):
        from apps.leads.models import Lead
        from apps.crm.models import Deal
        from apps.activities.models import ActivityEvent
        proposal = self.proposal("crm_create", entity="appointments", values=self.values)
        self.assertEqual(Appointment.objects.count(), 0)
        approval = self.approval(proposal)
        for _ in range(2):
            response = self.api.post(f"/api/ai/tools/{proposal.pk}/execute/", {"approval_id": approval.pk})
            self.assertEqual(response.status_code, 200, response.data)
        record = Appointment.objects.get()
        self.assertEqual(record.responsible_user_id, self.owner.pk)
        self.assertIsNone(record.lead_id)
        self.assertEqual(Lead.objects.count(), 0)
        self.assertEqual(Deal.objects.count(), 0)
        self.assertEqual(ActivityEvent.objects.filter(entity_id=str(record.pk), event_type=ActivityEvents.APPOINTMENT_CREATED).count(), 1)

    def test_specialist_required_and_inactive_specialist_rechecked_after_approval(self):
        with self.assertRaises(ValidationError):
            self.proposal("crm_create", entity="appointments", values={key: value for key, value in self.values.items() if key != "resource"})
        proposal = self.proposal("crm_create", entity="appointments", values=self.values)
        self.resource.is_active = False
        self.resource.save(update_fields=["is_active"])
        self.assertEqual(self.execute(proposal).status_code, 400)
        self.assertEqual(Appointment.objects.count(), 0)

    def test_early_completion_uses_reviewed_reason(self):
        from apps.activities.models import ActivityEvent
        record = Appointment.objects.create(business=self.business, client=self.person, service=self.service,
            resource=self.resource, start_at=self.start, end_at=self.start + timedelta(minutes=30))
        denied = self.proposal("crm_transition", entity="appointments", entity_id=record.pk, action="complete")
        self.assertEqual(self.execute(denied).status_code, 400)
        record.refresh_from_db()
        self.assertEqual(record.status, "created")
        approved = self.proposal("crm_transition", entity="appointments", entity_id=record.pk, action="complete", reason="Finished earlier")
        response = self.execute(approved)
        self.assertEqual(response.status_code, 200, response.data)
        event = ActivityEvent.objects.get(entity_id=str(record.pk), event_type=ActivityEvents.APPOINTMENT_COMPLETED)
        self.assertEqual(event.metadata["reason"], "Finished earlier")
        self.assertEqual(event.actor_id, self.owner.pk)

    def test_context_includes_rescheduled_and_pending_but_not_archived(self):
        record = Appointment.objects.create(business=self.business, client=self.person, service=self.service,
            resource=self.resource, start_at=self.start, end_at=self.start + timedelta(minutes=30), status="rescheduled")
        context = build_crm_context(self.business, user=self.owner)
        self.assertEqual(context["upcoming_appointments"][0]["id"], record.pk)
        self.assertEqual(context["summary"]["open_appointments_count"], 1)
        Appointment.objects.filter(pk=record.pk).update(start_at=timezone.now()-timedelta(hours=2), end_at=timezone.now()-timedelta(hours=1))
        self.assertEqual(build_crm_context(self.business, user=self.owner)["summary"]["pending_results_count"], 1)
        Appointment.objects.filter(pk=record.pk).update(is_archived=True)
        self.assertEqual(build_crm_context(self.business, user=self.owner)["summary"]["pending_results_count"], 0)
        self.assertNotIn("create_lead", [log.tool_name for log in suggest_tool_calls(business=self.business, user=self.owner)])

    def test_record_owner_brief_counts_all_pending_and_links_only_visible_records(self):
        from apps.ai_core.recommendations import build_owner_daily_brief
        for _ in range(4):
            Appointment.objects.create(business=self.business, client=self.person, service=self.service,
                resource=self.resource, start_at=timezone.now()-timedelta(hours=2),
                end_at=timezone.now()-timedelta(hours=1), status="rescheduled")
        result = build_owner_daily_brief(business=self.business, user=self.owner, limit=2, workflow="appointments")
        self.assertEqual(result["summary"]["categories"]["pending_records"], 4)
        self.assertNotIn("stale_leads", result["summary"]["categories"])
        self.assertNotIn("stalled_deals", result["summary"]["categories"])
        self.assertEqual(len(result["recommendations"]), 2)
        self.assertTrue(all(item["href"].startswith("/app/appointments/") for item in result["recommendations"]))
        denied = build_owner_daily_brief(business=self.business, user=self.other_owner, workflow="appointments")
        self.assertEqual(denied["summary"]["categories"]["pending_records"], 0)
        self.assertFalse(any(item["entity_type"] == "appointment" for item in denied["sources"]))
        response = self.api.get("/api/ai/owner-brief/daily/", {"business": self.business.pk, "workflow": "appointments"})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["summary"]["categories"]["pending_records"], 4)
