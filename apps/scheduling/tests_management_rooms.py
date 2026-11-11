from datetime import timedelta

from django.test import TestCase

from apps.branches.models import ServiceResourceRequirement
from apps.core.domain_errors import ScheduleConflict
from .models import Appointment
from .resource_booking import validate_resource_availability
from .resource_services import create_resource
from .services import reschedule_appointment
from . import tests_resource_booking as fixtures


class ManagementRoomTests(TestCase):
    setUp = fixtures.ResourceBookingTests.setUp
    set_requirements = fixtures.ResourceBookingTests.set_requirements
    book = fixtures.ResourceBookingTests.book
    slots = fixtures.ResourceBookingTests.slots

    def configure_rooms(self):
        self.set_requirements([])
        self.service.requires_room = True
        self.service.save(update_fields=["requires_room"])
        self.second_room = create_resource(business=self.business, name="Another room", resource_type="room")
        for room in [self.room, self.second_room]:
            ServiceResourceRequirement.objects.create(branch=self.branch, service=self.service, resource=room, is_alternative=True)

    def test_one_free_room_is_reserved_and_other_specialist_can_use_another(self):
        self.configure_rooms()
        first = self.book()
        self.assertEqual(list(first.reserved_resources.values_list("resource_id", flat=True)), [self.room.pk])
        self.assertIn(self.start, self.slots())
        second = self.book(resource=self.other_staff)
        self.assertEqual(list(second.reserved_resources.values_list("resource_id", flat=True)), [self.second_room.pk])
        with self.assertRaises(ScheduleConflict):
            validate_resource_availability(self.business, self.service, self.branch, self.start, self.start + timedelta(minutes=30))
        self.assertEqual(Appointment.objects.count(), 2)

    def test_required_room_without_options_fails_closed(self):
        self.configure_rooms()
        ServiceResourceRequirement.objects.all().delete()
        self.assertEqual(self.slots(), [])
        with self.assertRaises(ScheduleConflict):
            self.book()
        self.assertFalse(Appointment.objects.exists())

    def test_inactive_option_does_not_hide_another_free_room(self):
        self.configure_rooms()
        self.room.is_active = False
        self.room.save(update_fields=["is_active"])
        visit = self.book()
        self.assertEqual(list(visit.reserved_resources.values_list("resource_id", flat=True)), [self.second_room.pk])

    def test_existing_booking_keeps_exact_room_after_options_change(self):
        self.configure_rooms()
        visit = self.book()
        ServiceResourceRequirement.objects.filter(resource=self.room).delete()
        moved = reschedule_appointment(appointment=visit, actor=self.owner, resource=self.staff,
            start_at=self.start + timedelta(hours=1))
        self.assertEqual(list(moved.reserved_resources.values_list("resource_id", flat=True)), [self.room.pk])

    def test_legacy_required_equipment_is_still_reserved(self):
        self.configure_rooms()
        ServiceResourceRequirement.objects.create(branch=self.branch, service=self.service, resource=self.device)
        visit = self.book()
        self.assertEqual(set(visit.reserved_resources.values_list("resource_id", flat=True)), {self.room.pk, self.device.pk})
        self.assertNotIn(self.start, self.slots())

    def test_batch_preflight_can_exclude_already_selected_room(self):
        self.configure_rooms()
        chosen = validate_resource_availability(self.business, self.service, self.branch, self.start,
            self.start + timedelta(minutes=30), unavailable_ids={self.room.pk})
        self.assertEqual([room.pk for room in chosen], [self.second_room.pk])


from django.test import TransactionTestCase, skipUnlessDBFeature
from . import tests_resource_booking_concurrency as races


@skipUnlessDBFeature("has_select_for_update")
class ManagementRoomConcurrencyTests(TransactionTestCase):
    setUp = fixtures.ResourceBookingTests.setUp
    set_requirements = fixtures.ResourceBookingTests.set_requirements
    book = fixtures.ResourceBookingTests.book
    configure_rooms = ManagementRoomTests.configure_rooms
    parallel = races.ResourceBookingConcurrencyTests.parallel

    def test_parallel_bookings_choose_distinct_alternative_rooms(self):
        self.configure_rooms()
        results = self.parallel(lambda: self.book().pk, lambda: self.book(resource=self.other_staff).pk)
        self.assertNotIn("blocked", results)
        self.assertEqual(Appointment.objects.count(), 2)
        from .models import AppointmentResource
        self.assertEqual(set(AppointmentResource.objects.values_list("resource_id", flat=True)), {self.room.pk, self.second_room.pk})
        self.assertEqual(AppointmentResource.objects.count(), 2)

    def test_one_remaining_room_is_not_oversold(self):
        self.configure_rooms()
        self.second_room.is_active = False
        self.second_room.save(update_fields=["is_active"])
        results = self.parallel(lambda: self.book().pk, lambda: self.book(resource=self.other_staff).pk)
        self.assertEqual(results.count("blocked"), 1)
        self.assertEqual(Appointment.objects.count(), 1)
