from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.core.domain_errors import InvalidTransition, ScheduleConflict
from . import tests_resource_booking as fixtures
from .models import Appointment, AppointmentResource
from .resource_services import update_resource
from .services import reschedule_appointment


@skipUnlessDBFeature("has_select_for_update")
class ResourceBookingConcurrencyTests(TransactionTestCase):
    setUp = fixtures.ResourceBookingTests.setUp
    set_requirements = fixtures.ResourceBookingTests.set_requirements
    book = fixtures.ResourceBookingTests.book

    def parallel(self, *actions):
        barrier = Barrier(len(actions))

        def run(action):
            close_old_connections()
            try:
                barrier.wait(timeout=15)
                return action()
            except (ScheduleConflict, InvalidTransition):
                return "blocked"
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=len(actions)) as pool:
            pending = [pool.submit(run, action) for action in actions]
            return [item.result(timeout=40) for item in pending]

    def test_two_specialists_cannot_reserve_same_room_and_device(self):
        result = self.parallel(lambda: self.book().pk, lambda: self.book(resource=self.other_staff).pk)
        self.assertEqual(result.count("blocked"), 1)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(AppointmentResource.objects.count(), 2)

    def test_deactivation_and_booking_serialize(self):
        result = self.parallel(lambda: self.book().pk,
            lambda: update_resource(resource=self.room, actor=self.owner, attributes={"is_active": False}).pk)
        self.assertEqual(result.count("blocked"), 1)
        self.room.refresh_from_db()
        self.assertEqual(Appointment.objects.exists(), self.room.is_active)
        self.assertEqual(AppointmentResource.objects.count(), 2 if self.room.is_active else 0)

    def test_competing_reschedules_keep_one_reservation_at_target(self):
        first = self.book()
        second = self.book(resource=self.other_staff, start_at=self.start + timedelta(hours=1))
        target = self.start + timedelta(hours=2)
        result = self.parallel(
            lambda: reschedule_appointment(appointment=first, actor=self.owner, resource=self.staff, start_at=target).pk,
            lambda: reschedule_appointment(appointment=second, actor=self.owner, resource=self.other_staff, start_at=target).pk,
        )
        self.assertEqual(result.count("blocked"), 1)
        self.assertEqual(Appointment.objects.filter(start_at=target).count(), 1)
        self.assertEqual(AppointmentResource.objects.count(), 4)
