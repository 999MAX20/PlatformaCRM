from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from apps.ai_core import tests_crm_tools as command_fixtures
from apps.branches.single_location import ensure_initial_location
from apps.services.models import Service
from .models import Appointment, Resource


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True, AI_QUEUE_LIVE_REQUESTS=False)
class ManagementBookingFlowTests(TestCase):
    proposal = command_fixtures.CRMCommandTests.proposal
    approval = command_fixtures.CRMCommandTests.approval
    execute = command_fixtures.CRMCommandTests.execute

    def setUp(self):
        command_fixtures.CRMCommandTests.setUp(self)
        self.business.timezone = "Asia/Almaty"
        self.business.save(update_fields=["timezone"])
        self.branch = ensure_initial_location(self.business)
        self.start = datetime(2030, 1, 7, 10, tzinfo=ZoneInfo("Asia/Almaty"))
        self.staff = self.create("staff", Resource, name="Primary specialist", locations=[{"branch": self.branch.pk, "service_ids": []}])
        self.other_staff = self.create("staff", Resource, name="Second specialist", locations=[{"branch": self.branch.pk, "service_ids": []}])
        self.service = self.create("services", Service, name="Configured service", duration_minutes=45, price_from="12345.67",
            locations=[{"branch": self.branch.pk, "specialist_ids": [self.staff.pk, self.other_staff.pk], "room_ids": []}])
        self.room = self.create("rooms", Resource, name="Configured room", branch=self.branch.pk,
            service_ids=[self.service.pk], inherit_schedule=True)
        for resource in (None, self.staff.pk, self.other_staff.pk):
            self.hours(resource, [{"start": "09:00", "end": "18:00"}])

    def create(self, route, model, **values):
        response = self.api.post(f"/api/management/{route}/", {"business": self.business.pk, **values}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return model.objects.get(pk=response.data["id"])

    def hours(self, resource, intervals, **values):
        response = self.api.post(f"/api/branches/{self.branch.pk}/schedule-weekdays/",
            {"resource": resource, "weekdays": [0], "intervals": intervals, **values}, format="json")
        self.assertEqual(response.status_code, 200, response.data)

    def values(self, **extra):
        return {"client": self.person.pk, "service": self.service.pk, "resource": self.staff.pk,
            "branch": self.branch.pk, "start_at": self.start.isoformat(), **extra}

    def manual(self, **values):
        return self.api.post("/api/appointments/", {"business": self.business.pk, **self.values(**values)}, format="json")

    def slots(self, **extra):
        response = self.api.get("/api/appointments/available-slots/", {"business_id": self.business.pk,
            "service_id": self.service.pk, "resource_id": self.staff.pk, "branch_id": self.branch.pk,
            "date": self.start.date().isoformat(), **extra})
        self.assertEqual(response.status_code, 200, response.data)
        return [datetime.fromisoformat(row["start_at"].replace("Z", "+00:00")) for row in response.data]

    def test_manual_creation_uses_management_terms_and_joint_reservation(self):
        self.assertIn(self.start, self.slots())
        response = self.manual()
        self.assertEqual(response.status_code, 201, response.data)
        visit = Appointment.objects.get()
        self.assertEqual(visit.end_at - visit.start_at, timedelta(minutes=45))
        self.assertEqual(str(visit.booked_price), "12345.67")
        self.assertEqual(list(visit.reserved_resources.values_list("resource_id", flat=True)), [self.room.pk])
        self.assertNotIn(self.start, self.slots(resource_id=self.other_staff.pk))
        self.assertEqual(self.manual(resource=self.other_staff.pk).status_code, 409)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_ai_creation_requires_confirmation_and_replays_one_reservation(self):
        log = self.proposal("crm_create", entity="appointments", values=self.values())
        self.assertFalse(Appointment.objects.exists())
        self.assertEqual(self.api.post(f"/api/ai/tools/{log.pk}/execute/", {}).status_code, 403)
        approval = self.approval(log)
        for _ in range(2):
            response = self.api.post(f"/api/ai/tools/{log.pk}/execute/", {"approval_id": approval.pk})
            self.assertEqual(response.status_code, 200, response.data)
        visit = Appointment.objects.get()
        self.assertEqual(visit.resource_id, self.staff.pk)
        self.assertEqual(visit.end_at - visit.start_at, timedelta(minutes=45))
        self.assertEqual(list(visit.reserved_resources.values_list("resource_id", flat=True)), [self.room.pk])

    def test_ai_confirmation_rechecks_room_taken_after_preview(self):
        log = self.proposal("crm_create", entity="appointments", values=self.values())
        self.assertEqual(self.manual(resource=self.other_staff.pk).status_code, 201)
        response = self.execute(log)
        self.assertIn(response.status_code, (400, 409), response.data)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_individual_room_hours_and_absence_filter_manual_and_ai(self):
        self.hours(self.room.pk, [{"start": "11:00", "end": "14:00"}])
        self.assertNotIn(self.start, self.slots())
        self.assertIn(self.start + timedelta(hours=1), self.slots())
        self.assertEqual(self.manual().status_code, 409)
        log = self.proposal("crm_create", entity="appointments", values=self.values(start_at=(self.start + timedelta(hours=1)).isoformat()))
        absent = self.api.post(f"/api/resources/{self.room.pk}/absences/",
            {"starts_on": "2030-01-07", "ends_on": "2030-01-07"}, format="json")
        self.assertEqual(absent.status_code, 201, absent.data)
        self.assertEqual(self.slots(), [])
        self.assertIn(self.execute(log).status_code, (400, 409))
        self.assertFalse(Appointment.objects.exists())

    def test_effective_schedule_and_date_override_apply_at_booking_date(self):
        self.hours(self.staff.pk, [{"start": "12:00", "end": "16:00"}], effective_from="2030-01-14")
        self.assertIn(self.start, self.slots())
        self.assertNotIn(self.start + timedelta(days=7), self.slots(date="2030-01-14"))
        self.assertIn(self.start + timedelta(days=7, hours=2), self.slots(date="2030-01-14"))
        response = self.api.post(f"/api/branches/{self.branch.pk}/schedule/",
            {"resource": self.staff.pk, "date": "2030-01-14", "intervals": []}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.slots(date="2030-01-14"), [])
        self.assertEqual(self.manual(start_at=(self.start + timedelta(days=7, hours=2)).isoformat()).status_code, 409)

    def test_manual_and_ai_reschedule_preserve_room_and_rollback_conflicts(self):
        self.assertEqual(self.manual().status_code, 201)
        visit = Appointment.objects.get()
        self.assertEqual(self.manual(resource=self.other_staff.pk, start_at=(self.start + timedelta(hours=2)).isoformat()).status_code, 201)
        url = f"/api/appointments/{visit.pk}/reschedule/"
        blocked = self.api.post(url, {"start_at": (self.start + timedelta(hours=2)).isoformat()}, format="json")
        self.assertEqual(blocked.status_code, 409, blocked.data)
        visit.refresh_from_db()
        self.assertEqual(visit.start_at, self.start)
        log = self.proposal("crm_transition", entity="appointments", entity_id=visit.pk, action="reschedule",
            values={"start_at": (self.start + timedelta(hours=1)).isoformat()})
        response = self.execute(log)
        self.assertEqual(response.status_code, 200, response.data)
        visit.refresh_from_db()
        self.assertEqual(visit.resource_id, self.staff.pk)
        self.assertEqual(visit.start_at, self.start + timedelta(hours=1))
        self.assertEqual(list(visit.reserved_resources.values_list("resource_id", flat=True)), [self.room.pk])
        self.assertIn(self.start, self.slots(resource_id=self.other_staff.pk))

    def test_ai_conflicting_reschedule_and_manual_success_keep_reservations(self):
        self.assertEqual(self.manual().status_code, 201)
        visit = Appointment.objects.get()
        log = self.proposal("crm_transition", entity="appointments", entity_id=visit.pk, action="reschedule",
            values={"start_at": (self.start + timedelta(hours=2)).isoformat()})
        self.assertEqual(self.manual(resource=self.other_staff.pk, start_at=(self.start + timedelta(hours=2)).isoformat()).status_code, 201)
        self.assertIn(self.execute(log).status_code, (400, 409))
        visit.refresh_from_db()
        self.assertEqual(visit.start_at, self.start)
        response = self.api.post(f"/api/appointments/{visit.pk}/reschedule/",
            {"start_at": (self.start + timedelta(hours=1)).isoformat()}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        visit.refresh_from_db()
        self.assertEqual(visit.start_at, self.start + timedelta(hours=1))
        self.assertEqual(list(visit.reserved_resources.values_list("resource_id", flat=True)), [self.room.pk])
        self.assertEqual(str(visit.booked_price), "12345.67")

    def test_unassigned_specialist_is_not_bookable(self):
        unassigned = self.create("staff", Resource, name="No service permission", locations=[{"branch": self.branch.pk, "service_ids": []}])
        self.hours(unassigned.pk, [{"start": "09:00", "end": "18:00"}])
        response = self.manual(resource=unassigned.pk)
        self.assertIn(response.status_code, (400, 409), response.data)
        log = self.proposal("crm_create", entity="appointments", values=self.values(resource=unassigned.pk))
        self.assertIn(self.execute(log).status_code, (400, 409))
        self.assertFalse(Appointment.objects.exists())

    def test_ai_specialist_references_exclude_rooms_equipment_and_archived_staff(self):
        from apps.ai_core.crm_planner import reference_choices
        equipment = Resource.objects.create(business=self.business, name="Equipment", resource_type="equipment")
        archived = Resource.objects.create(business=self.business, name="Archived staff", resource_type="staff", archived_at=self.start)
        retired = Resource.objects.create(business=self.business, name="Retired staff", resource_type="staff", retired_at=self.start)
        choices = reference_choices(self.business, self.owner, "appointments")
        ids = {row["id"] for row in choices["resource"]}
        self.assertIn(self.staff.pk, ids)
        self.assertTrue(ids.isdisjoint({self.room.pk, equipment.pk, archived.pk, retired.pk}), choices["resource"])

    def test_text_planner_rejects_model_selection_of_a_room_as_specialist(self):
        import json
        from unittest.mock import patch
        from apps.ai_core.ai_client import AIClientResult
        from apps.ai_core.models import AIToolCallLog
        output = {"tool": "crm_create", "arguments": {"entity": "appointments", "values": self.values(resource=self.room.pk)}, "question": ""}
        with patch("apps.ai_core.services.generate_text", return_value=AIClientResult(
            output_text=json.dumps(output), model="test", provider="test",
        )):
            response = self.api.post("/api/ai/crm/plan/", {"business": self.business.pk,
                "entity": "appointments", "message": "Create the requested appointment"}, format="json")
        self.assertIn(response.status_code, (400, 503), response.data)
        self.assertFalse(AIToolCallLog.objects.exists())
        self.assertFalse(Appointment.objects.exists())
