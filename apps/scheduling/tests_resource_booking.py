from datetime import datetime, time, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.branches.configuration import save_assignment, save_offer, save_schedule_day
from apps.branches.models import BranchAccess, ServiceResourceRequirement
from apps.branches.physical_resources import save_resource_requirements
from apps.branches.services import create_branch
from apps.branches.tests_legacy_fixtures import ensure_legacy_initial_location as ensure_initial_location
from apps.businesses.access import Actions, Resources, can
from apps.businesses.models import Business, BusinessMember, BusinessRole, RolePermission
from apps.clients.models import Client
from apps.core.domain_errors import ScheduleConflict
from apps.services.models import Service
from .availability import get_available_slots
from .models import Appointment, AppointmentResource, Resource, ScheduleException, WorkingHours
from .record_commands import create_record
from .resource_services import create_resource
from .services import cancel_appointment, handle_appointment_created, reschedule_appointment


class ResourceBookingTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="booking-resources", email="booking-resources@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Booking", slug="booking-resources", timezone="Asia/Almaty")
        self.branch = ensure_initial_location(self.business)
        self.service = Service.objects.create(business=self.business, name="Service", duration_minutes=30)
        self.client_record = Client.objects.create(business=self.business, full_name="Client")
        self.staff = Resource.objects.create(business=self.business, name="First")
        self.other_staff = Resource.objects.create(business=self.business, name="Second")
        self.room = create_resource(business=self.business, name="Room", resource_type="room")
        self.device = create_resource(business=self.business, name="Device", resource_type="equipment")
        self.start = datetime(2030, 1, 7, 10, tzinfo=ZoneInfo(self.business.timezone))
        WorkingHours.objects.create(business=self.business, weekday=0, start_time=time(9), end_time=time(18))
        self.set_requirements([self.room.pk, self.device.pk])
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def set_requirements(self, ids, branch=None):
        return save_resource_requirements(branch=branch or self.branch, actor=self.owner, service_id=self.service.pk, resource_ids=ids)

    def book(self, **overrides):
        return create_record(**{"business": self.business, "actor": self.owner, "client": self.client_record,
            "service": self.service, "resource": self.staff, "start_at": self.start, "branch": self.branch, **overrides})

    def slots(self, **overrides):
        return get_available_slots(**{"business": self.business, "service": self.service, "resource": self.other_staff,
            "date": self.start.date(), "branch": self.branch, **overrides})

    def test_booking_reserves_all_required_resources_and_blocks_other_specialists(self):
        visit = self.book()
        self.assertEqual(set(visit.reserved_resources.values_list("resource_id", flat=True)), {self.room.pk, self.device.pk})
        self.assertNotIn(self.start, self.slots())
        self.assertIn(self.start + timedelta(minutes=30), self.slots())
        with self.assertRaises(ScheduleConflict):
            self.book(resource=self.other_staff)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_api_exposes_reservation_snapshot_and_resource_usage(self):
        visit = self.book()
        self.room.name = "Renamed room"
        self.room.save()
        response = self.api.get(f"/api/appointments/{visit.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertIn({"resource": self.room.pk, "resource_name": "Room"}, response.data["reserved_resources"])
        response = self.api.get(f"/api/resources/{self.room.pk}/")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["appointment_count"], 1)

    def test_raw_api_cannot_bypass_physical_occupancy(self):
        self.book()
        response = self.api.post("/api/appointments/", {"business": self.business.pk, "client": self.client_record.pk,
            "service": self.service.pk, "resource": self.other_staff.pk, "branch": self.branch.pk,
            "start_at": self.start.isoformat()}, format="json")
        self.assertEqual(response.status_code, 409, response.data)
        self.assertEqual(Appointment.objects.count(), 1)

    def workspace(self, **filters):
        return self.api.get("/api/appointments/workspace/", {"business": self.business.pk, **filters})

    def test_workspace_physical_filter_matches_reservations_not_primary_staff(self):
        visit = self.book()
        unused = create_resource(business=self.business, name="Unused", resource_type="room")
        for resource in (self.room, self.device):
            response = self.workspace(physical_resource=resource.pk, resource=self.staff.pk,
                start_from="2030-01-07", start_to="2030-01-08", branch=self.branch.pk)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual([item["id"] for item in response.data["results"]], [visit.pk])
            self.assertEqual(response.data["summary"]["planned"], 1)
        for filters in ({"physical_resource": unused.pk}, {"physical_resource": self.staff.pk},
                        {"physical_resource": self.room.pk, "resource": self.other_staff.pk},
                        {"physical_resource": self.room.pk, "start_from": "2030-01-08", "start_to": "2030-01-09"}):
            response = self.workspace(**filters)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["count"], 0, filters)

    def test_workspace_physical_filter_rejects_invalid_ids(self):
        for value in ("abc", "0", "-1", str(2 ** 64)):
            response = self.workspace(physical_resource=value)
            self.assertEqual(response.status_code, 400, response.data)
            self.assertIn("physical_resource", response.data)

    def test_workspace_physical_filter_does_not_match_foreign_reservations(self):
        visit = self.book()
        foreign_owner = User.objects.create_user(username="other-room-owner")
        foreign_business = Business.objects.create(owner=foreign_owner, name="Other", slug="other-rooms")
        foreign_room = Resource.objects.create(business=foreign_business, name="Foreign", resource_type="room")
        AppointmentResource.objects.create(appointment=visit, resource=foreign_room, resource_name="Foreign")
        response = self.workspace(physical_resource=foreign_room.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)
        self.api.force_authenticate(foreign_owner)
        response = self.api.get("/api/appointments/workspace/", {"business": foreign_business.pk, "physical_resource": self.room.pk})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 0)

    def test_workspace_physical_filter_preserves_cancelled_history(self):
        visit = self.book()
        cancel_appointment(appointment=visit, actor=self.owner, reason="Client cancelled")
        response = self.workspace(physical_resource=self.room.pk, workflow="cancelled")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual([item["id"] for item in response.data["results"]], [visit.pk])
        self.assertEqual(self.workspace(physical_resource=self.room.pk, workflow="planned").data["count"], 0)

    def test_cancel_releases_time_but_preserves_resource_history(self):
        visit = self.book()
        cancel_appointment(appointment=visit, actor=self.owner, reason="Client cancelled")
        self.assertIn(self.start, self.slots())
        self.assertEqual(visit.reserved_resources.count(), 2)
        replacement = self.book(resource=self.other_staff)
        self.assertEqual(replacement.reserved_resources.count(), 2)

    def test_reschedule_moves_reservation_and_releases_old_interval(self):
        visit = self.book()
        moved = reschedule_appointment(appointment=visit, actor=self.owner, resource=self.staff,
            start_at=self.start + timedelta(hours=1))
        self.assertIn(self.start, self.slots())
        self.assertNotIn(moved.start_at, self.slots())
        self.assertEqual(moved.reserved_resources.count(), 2)
        response = self.workspace(physical_resource=self.room.pk, resource=self.staff.pk)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(datetime.fromisoformat(response.data["results"][0]["start_at"]), moved.start_at)

    def test_reschedule_conflict_rolls_back_time_and_resources(self):
        visit = self.book()
        self.book(resource=self.other_staff, start_at=self.start + timedelta(hours=1))
        with self.assertRaises(ScheduleConflict):
            reschedule_appointment(appointment=visit, actor=self.owner, resource=self.staff,
                start_at=self.start + timedelta(hours=1))
        visit.refresh_from_db()
        self.assertEqual(visit.start_at, self.start)
        self.assertEqual(visit.reserved_resources.count(), 2)

    def test_requirement_changes_do_not_rewrite_existing_booking(self):
        visit = self.book()
        self.set_requirements([])
        moved = reschedule_appointment(appointment=visit, actor=self.owner, resource=self.staff,
            start_at=self.start + timedelta(hours=1))
        self.assertEqual(moved.reserved_resources.count(), 2)
        new_visit = self.book(resource=self.other_staff)
        self.assertFalse(new_visit.reserved_resources.exists())

    def test_booking_without_resources_keeps_empty_snapshot_after_new_requirements(self):
        self.set_requirements([])
        visit = self.book()
        self.set_requirements([self.room.pk])
        moved = reschedule_appointment(appointment=visit, actor=self.owner, resource=self.staff,
            start_at=self.start + timedelta(hours=1))
        self.assertFalse(moved.reserved_resources.exists())

    def test_physical_hours_and_date_exceptions_filter_slots_and_writes(self):
        WorkingHours.objects.create(business=self.business, resource=self.room, weekday=0,
            start_time=time(11), end_time=time(14))
        self.assertNotIn(self.start, self.slots())
        with self.assertRaises(ScheduleConflict):
            self.book()
        self.assertIn(self.start + timedelta(hours=1), self.slots())
        ScheduleException.objects.create(business=self.business, resource=self.device, date=self.start.date(),
            start_time=time(9), end_time=time(18), is_day_off=True)
        self.assertEqual(self.slots(), [])

    def test_deactivated_required_resource_fails_closed(self):
        self.device.is_active = False
        self.device.save()
        self.assertEqual(self.slots(), [])
        with self.assertRaises(ScheduleConflict):
            self.book()

    def test_existing_reservation_blocks_movement_or_deactivation(self):
        self.book()
        self.set_requirements([])
        second = create_branch(business=self.business, actor=self.owner, name="Second")
        for payload in ({"branch": second.pk}, {"is_active": False}):
            response = self.api.patch(f"/api/resources/{self.room.pk}/", payload, format="json")
            self.assertEqual(response.status_code, 409, response.data)

    def test_other_branch_uses_its_own_resources(self):
        second = create_branch(business=self.business, actor=self.owner, name="Second location")
        self.branch.refresh_from_db()
        room = create_resource(business=self.business, name="Second room", resource_type="room", branch=second)
        second_staff = Resource.objects.create(business=self.business, name="Second location specialist")
        save_offer(branch=second, actor=self.owner, service_id=self.service.pk, duration_minutes=30, price_from=None)
        save_assignment(branch=second, actor=self.owner, resource_id=second_staff.pk, service_ids=[self.service.pk])
        for target in (None, second_staff.pk):
            save_schedule_day(branch=second, actor=self.owner, resource_id=target, weekday=0,
                intervals=[{"start": "09:00", "end": "18:00"}])
        self.set_requirements([room.pk], branch=second)
        self.book()
        other = self.book(resource=second_staff, branch=second)
        self.assertEqual(list(other.reserved_resources.values_list("resource_id", flat=True)), [room.pk])
        self.assertEqual(self.workspace(physical_resource=room.pk).data["count"], 1)
        admin = User.objects.create_user(username="first-location-admin")
        member = BusinessMember.objects.create(business=self.business, user=admin, role="admin")
        grant, _ = BranchAccess.objects.get_or_create(member=member)
        grant.branches.set([self.branch])
        self.api.force_authenticate(admin)
        self.assertEqual(self.workspace(physical_resource=self.room.pk).data["count"], 1)
        self.assertEqual(self.workspace(physical_resource=room.pk, branch=second.pk).data["count"], 1)
        self.assertFalse(can(admin, self.business, Resources.APPOINTMENTS, Actions.UPDATE, obj=other).allowed)
        role = BusinessRole.objects.create(business=self.business, name="Own visits")
        RolePermission.objects.create(business_role=role, resource="appointments", action="view", scope="own", is_allowed=True)
        member.business_role = role
        member.save(update_fields=["business_role"])
        self.staff.linked_user = admin
        self.staff.save(update_fields=["linked_user"])
        self.assertEqual(self.workspace(physical_resource=self.room.pk).data["count"], 1)
        for filters in ({"physical_resource": room.pk}, {"physical_resource": room.pk, "branch": second.pk}):
            response = self.workspace(**filters)
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(response.data["count"], 0)

    def test_configured_location_physical_schedule_is_enforced_and_projected(self):
        create_branch(business=self.business, actor=self.owner, name="Second")
        self.branch.refresh_from_db()
        save_schedule_day(branch=self.branch, actor=self.owner, resource_id=self.room.pk, weekday=0,
            intervals=[{"start": "11:00", "end": "14:00"}])
        self.assertNotIn(self.start, self.slots())
        self.assertIn(self.start + timedelta(hours=1), self.slots())
        configuration = self.api.get(f"/api/branches/{self.branch.pk}/configuration/")
        self.assertEqual(configuration.status_code, 200, configuration.data)
        inherited = [row for row in configuration.data["days"] if row["resource"] == self.device.pk and row["weekday"] == 0]
        self.assertEqual(inherited[0]["intervals"], [{"start": "09:00", "end": "18:00"}])
        save_schedule_day(branch=self.branch, actor=self.owner, resource_id=self.device.pk,
            date=self.start.date(), intervals=[])
        self.assertEqual(self.slots(), [])

    def test_availability_query_count_does_not_scale_with_required_resource_count(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        from .resource_booking import ResourceAvailability

        extras = [create_resource(business=self.business, name=f"Device {index}", resource_type="equipment") for index in range(10)]
        with CaptureQueriesContext(connection) as small:
            self.assertTrue(ResourceAvailability(self.business, self.branch, [self.room], self.start,
                self.start + timedelta(minutes=30)).permits(self.start, self.start + timedelta(minutes=30)))
        with CaptureQueriesContext(connection) as larger:
            self.assertTrue(ResourceAvailability(self.business, self.branch, [self.room, *extras], self.start,
                self.start + timedelta(minutes=30)).permits(self.start, self.start + timedelta(minutes=30)))
        self.assertEqual(len(larger), len(small))

    def test_repeated_creation_effects_do_not_rewrite_snapshot(self):
        visit = self.book()
        self.set_requirements([])
        handle_appointment_created(visit)
        self.assertEqual(visit.reserved_resources.count(), 2)

    def test_reservation_and_appointment_rollback_together(self):
        with patch("apps.scheduling.services.schedule_appointment_followups", side_effect=RuntimeError("failure")):
            with self.assertRaises(RuntimeError):
                self.book()
        self.assertFalse(Appointment.objects.exists())
        self.assertFalse(AppointmentResource.objects.exists())

    def test_corrupt_cross_tenant_requirement_fails_closed(self):
        other = Business.objects.create(owner=self.owner, name="Other", slug="booking-other")
        foreign = Resource.objects.create(business=other, name="Foreign", resource_type="equipment")
        ServiceResourceRequirement.objects.create(branch=self.branch, service=self.service, resource=foreign)
        self.assertEqual(self.slots(), [])
        with self.assertRaises(ScheduleConflict):
            self.book()
