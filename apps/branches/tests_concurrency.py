from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch

from django.db import close_old_connections
from django.test import TransactionTestCase, skipUnlessDBFeature
from rest_framework.test import APIClient

from apps.scheduling.models import Appointment
from apps.scheduling.views import AppointmentViewSet
from . import tests_scheduling


@skipUnlessDBFeature("has_select_for_update")
class BranchConcurrentBookingTests(TransactionTestCase):
    def test_two_prevalidated_bookings_compete_for_one_specialist_slot(self):
        fixture = tests_scheduling.BranchSchedulingTests()
        fixture.setUp()
        barrier = Barrier(2)
        original = AppointmentViewSet.perform_create

        def synchronized_create(view, serializer):
            # Both requests passed serializer validation before either can save.
            barrier.wait(timeout=15)
            return original(view, serializer)

        def book():
            close_old_connections()
            try:
                api = APIClient()
                api.force_authenticate(fixture.owner)
                response = api.post("/api/appointments/", {
                    "business": fixture.business.pk, "client": fixture.client_record.pk,
                    "service": fixture.service.pk, "resource": fixture.staff.pk,
                    "branch": fixture.first.pk, "start_at": fixture.start.isoformat(),
                }, format="json")
                return response.status_code
            finally:
                close_old_connections()

        with patch.object(AppointmentViewSet, "perform_create", synchronized_create):
            with ThreadPoolExecutor(max_workers=2) as pool:
                pending = [pool.submit(book) for _ in range(2)]
                results = [future.result(timeout=30) for future in pending]
        self.assertEqual(sorted(results), [201, 409])
        self.assertEqual(Appointment.objects.filter(resource=fixture.staff).count(), 1)
