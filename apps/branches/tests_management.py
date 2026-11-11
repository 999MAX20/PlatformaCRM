from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.scheduling.models import Appointment, Resource
from apps.scheduling.record_commands import create_record
from apps.services.models import Service
from .configuration import save_schedule_day
from .models import BranchAccess, ScheduleDay, ServiceResourceRequirement, SpecialistBranch
from .single_location import ensure_initial_location


class ManagementApiTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="management-owner", email="management-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Management", slug="management-api", timezone="Asia/Almaty")
        self.branch = ensure_initial_location(self.business)
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def post(self, route, **values):
        return self.api.post(f"/api/management/{route}/", {"business": self.business.pk, **values}, format="json")

    def specialist(self, **values):
        response = self.post("staff", name="Specialist", locations=[{"branch": self.branch.pk, "service_ids": []}], **values)
        self.assertEqual(response.status_code, 201, response.data)
        return Resource.objects.get(pk=response.data["id"])

    def service(self, staff=None, **values):
        response = self.post("services", name="Consultation", description="", duration_minutes=30, price_from=None,
            locations=[{"branch": self.branch.pk, "specialist_ids": [staff.pk] if staff else [], "room_ids": []}], **values)
        self.assertEqual(response.status_code, 201, response.data)
        return Service.objects.get(pk=response.data["id"])

    def appointment(self, staff, service):
        for target in [None, staff.pk]:
            save_schedule_day(branch=self.branch, actor=self.owner, resource_id=target, weekday=0,
                intervals=[{"start": "09:00", "end": "18:00"}])
        client = Client.objects.create(business=self.business, full_name="Test client")
        return create_record(business=self.business, actor=self.owner, client=client, resource=staff, service=service,
            branch=self.branch, start_at=datetime(2030, 1, 7, 10, tzinfo=ZoneInfo("Asia/Almaty")))

    def test_specialist_starts_unassigned_without_inherited_hours_and_service_assigns_explicitly(self):
        staff = self.specialist(profession="Assistant")
        link = SpecialistBranch.objects.get(resource=staff, branch=self.branch)
        self.assertFalse(link.services.exists())
        self.assertFalse(staff.working_hours.exists())
        self.assertFalse(staff.branch_schedule_days.exists())
        service = self.service(staff)
        self.assertEqual(list(link.services.values_list("pk", flat=True)), [service.pk])
        result = self.api.get("/api/management/", {"business": self.business.pk})
        self.assertEqual(result.status_code, 200, result.data)
        self.assertEqual(result.data["resources"][0]["profession"], "Assistant")
        self.assertEqual(result.data["assignments"][0]["service_ids"], [service.pk])

    def test_invalid_late_relation_rolls_back_new_service_and_offers(self):
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="management-foreign")
        room = Resource.objects.create(business=foreign, name="Foreign room", resource_type="room")
        response = self.post("services", name="Must roll back", duration_minutes=30, price_from="12.50", requires_room=True,
            locations=[{"branch": self.branch.pk, "specialist_ids": [], "room_ids": [room.pk]}])
        self.assertEqual(response.status_code, 400, response.data)
        self.assertFalse(Service.objects.filter(business=self.business).exists())
        self.assertFalse(self.branch.service_offers.exists())

    def test_room_form_creates_bidirectional_options_and_inherits_branch_hours(self):
        service = self.service()
        response = self.post("rooms", name="Room 1", branch=self.branch.pk, service_ids=[service.pk], inherit_schedule=True)
        self.assertEqual(response.status_code, 201, response.data)
        room = Resource.objects.get(pk=response.data["id"])
        self.assertTrue(ServiceResourceRequirement.objects.get(resource=room, service=service).is_alternative)
        service.refresh_from_db()
        self.assertTrue(service.requires_room)
        self.assertFalse(room.branch_schedule_days.exists())
        catalog = self.api.get("/api/management/", {"business": self.business.pk}).data
        self.assertTrue(next(row for row in catalog["resources"] if row["id"] == room.pk)["inherit_schedule"])

    def test_future_appointment_blocks_relation_removal_and_rolls_back_metadata(self):
        staff = self.specialist()
        service = self.service(staff)
        self.appointment(staff, service)
        response = self.post("staff", id=staff.pk, name="Must roll back", locations=[])
        self.assertEqual(response.status_code, 409, response.data)
        staff.refresh_from_db()
        self.assertEqual(staff.name, "Specialist")
        self.assertTrue(staff.branch_assignments.get(branch=self.branch).is_active)

    def test_future_hours_absence_and_lifecycle_guards_cannot_be_bypassed(self):
        staff = self.specialist()
        service = self.service(staff)
        visit = self.appointment(staff, service)
        response = self.api.post(f"/api/branches/{self.branch.pk}/schedule/", {"resource": staff.pk,
            "weekday": 0, "intervals": [{"start": "12:00", "end": "18:00"}]}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(ScheduleDay.objects.get(resource=staff, weekday=0).intervals[0]["start"], "09:00")
        response = self.api.post(f"/api/resources/{staff.pk}/absences/", {"starts_on": "2030-01-07", "ends_on": "2030-01-07"}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        for path, payload in [(f"/api/services/{service.pk}/deactivate/", {}), ("/api/management/lifecycle/", {
            "business": self.business.pk, "id": staff.pk, "kind": "staff", "operation": "archive"})]:
            response = self.api.post(path, payload, format="json")
            self.assertEqual(response.status_code, 409, response.data)
        visit.refresh_from_db()
        self.assertEqual(visit.status, "created")

    def test_archive_restore_and_delete_unused_preserve_accounts(self):
        staff = self.specialist()
        for operation in ["archive", "restore", "activate", "deactivate", "delete"]:
            response = self.post("lifecycle", kind="staff", id=staff.pk, operation=operation)
            self.assertEqual(response.status_code, 200, response.data)
            if operation == "restore":
                staff.refresh_from_db()
                self.assertFalse(staff.is_active)
                self.assertIsNone(staff.archived_at)
        self.assertFalse(Resource.objects.filter(pk=staff.pk).exists())
        self.owner.refresh_from_db()
        self.assertTrue(self.owner.is_active)

    def test_used_service_cannot_be_deleted_even_after_visit_is_completed(self):
        staff = self.specialist()
        service = self.service(staff)
        visit = self.appointment(staff, service)
        Appointment.objects.filter(pk=visit.pk).update(status="completed")
        response = self.post("lifecycle", kind="services", id=service.pk, operation="delete")
        self.assertEqual(response.status_code, 409, response.data)
        self.assertTrue(Service.objects.filter(pk=service.pk).exists())

    def test_foreign_business_and_denied_role_have_no_writes(self):
        other = User.objects.create_user(username="management-outsider", email="management-outsider@example.test")
        self.api.force_authenticate(other)
        self.assertEqual(self.api.get("/api/management/", {"business": self.business.pk}).status_code, 404)
        self.assertEqual(self.post("staff", name="Denied", locations=[]).status_code, 404)
        BusinessMember.objects.create(business=self.business, user=other, role="staff")
        self.assertEqual(self.post("staff", name="Denied", locations=[]).status_code, 403)
        self.assertFalse(Resource.objects.exists())

    def test_late_audit_failure_rolls_back_entity_and_links(self):
        with patch("apps.branches.management_commands.record_change", side_effect=RuntimeError("audit failure")):
            response = self.post("staff", name="Rollback", locations=[{"branch": self.branch.pk, "service_ids": []}])
        self.assertEqual(response.status_code, 500, response.data)
        self.assertFalse(Resource.objects.exists())
        self.assertFalse(SpecialistBranch.objects.exists())

    def test_price_zero_is_preserved_and_negative_or_invalid_duration_rejected(self):
        response = self.post("services", name="Free", duration_minutes=5, price_from="0", locations=[])
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(Service.objects.get(pk=response.data["id"]).price_from, 0)
        for extra in [{"duration_minutes": 0, "price_from": None}, {"duration_minutes": 30, "price_from": "-1"}]:
            self.assertEqual(self.post("services", name="Invalid", locations=[], **extra).status_code, 400)
        self.assertEqual(Service.objects.count(), 1)

    def test_room_schedule_mode_and_absence_edit_persist_without_duplicates(self):
        response = self.post("rooms", name="Room", branch=self.branch.pk, service_ids=[], inherit_schedule=True)
        self.assertEqual(response.status_code, 201, response.data)
        room_id = response.data["id"]
        response = self.post("rooms", id=room_id, name="Room", branch=self.branch.pk, service_ids=[], inherit_schedule=False)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(ScheduleDay.objects.filter(resource_id=room_id).count(), 7)
        url = f"/api/resources/{room_id}/absences/"
        response = self.api.post(url, {"starts_on": "2030-01-10", "ends_on": "2030-01-11"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        absence_id = response.data["id"]
        response = self.api.post(url, {"id": absence_id, "starts_on": "2030-01-12", "ends_on": "2030-01-13"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertEqual(response.data["id"], absence_id)
        self.assertEqual(response.data["starts_on"], "2030-01-12")
        self.assertEqual(len(self.api.get(url).data), 1)
        other = self.specialist()
        response = self.api.post(f"/api/resources/{other.pk}/absences/", {"id": absence_id, "starts_on": "2030-01-12", "ends_on": "2030-01-13"}, format="json")
        self.assertEqual(response.status_code, 400)

    def test_form_activity_updates_use_future_booking_guards_and_rollback(self):
        staff = self.specialist()
        service = self.service(staff)
        self.appointment(staff, service)
        payloads = [
            ("services", dict(id=service.pk, name="Changed", duration_minutes=30, price_from=None, locations=[{"branch": self.branch.pk, "specialist_ids": [staff.pk], "room_ids": []}])),
            ("staff", dict(id=staff.pk, name="Changed", locations=[{"branch": self.branch.pk, "service_ids": [service.pk]}])),
            ("branches", dict(id=self.branch.pk, name="Changed", service_ids=[service.pk], specialist_ids=[staff.pk])),
        ]
        for route, values in payloads:
            response = self.post(route, is_active=False, **values)
            self.assertEqual(response.status_code, 409, response.data)
        for entity in [staff, service, self.branch]:
            entity.refresh_from_db()
            self.assertTrue(entity.is_active)
            self.assertNotEqual(entity.name, "Changed")
        empty = self.post("branches", name="Paused", service_ids=[], specialist_ids=[], is_active=False)
        self.assertEqual(empty.status_code, 201, empty.data)
        from .models import Branch
        self.assertFalse(Branch.objects.get(pk=empty.data["id"]).is_active)

    def test_metadata_edit_preserves_legacy_mandatory_rooms(self):
        service = self.service()
        room = Resource.objects.create(business=self.business, branch=self.branch, resource_type="room", name="Required room")
        requirement = ServiceResourceRequirement.objects.create(branch=self.branch, service=service, resource=room)
        response = self.post("services", id=service.pk, name="Renamed", duration_minutes=30, price_from=None,
            requires_room=False, locations=[{"branch": self.branch.pk, "specialist_ids": [], "room_ids": [room.pk]}])
        self.assertEqual(response.status_code, 200, response.data)
        requirement.refresh_from_db()
        self.assertFalse(requirement.is_alternative)
        response = self.post("rooms", id=room.pk, name="Renamed room", branch=self.branch.pk, service_ids=[service.pk], inherit_schedule=True)
        self.assertEqual(response.status_code, 200, response.data)
        requirement.refresh_from_db()
        service.refresh_from_db()
        self.assertFalse(requirement.is_alternative)
        self.assertFalse(service.requires_room)

    def test_room_related_appointments_filter_uses_reservations_and_keeps_tenant_scope(self):
        staff = self.specialist()
        service = self.service(staff)
        room = Resource.objects.create(business=self.business, branch=self.branch, resource_type="room", name="Room")
        ServiceResourceRequirement.objects.create(branch=self.branch, service=service, resource=room)
        visit = self.appointment(staff, service)
        response = self.api.get("/api/appointments/", {"business": self.business.pk, "resource": room.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([row["id"] for row in response.data["results"]], [visit.pk])
        foreign = Business.objects.create(owner=self.owner, name="Foreign", slug="room-filter-foreign")
        other_room = Resource.objects.create(business=foreign, resource_type="room", name="Other")
        response = self.api.get("/api/appointments/", {"business": self.business.pk, "resource": other_room.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["results"], [])
