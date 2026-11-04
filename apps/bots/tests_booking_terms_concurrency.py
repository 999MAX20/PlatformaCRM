from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from django.db import OperationalError, connection, connections, transaction
from django.test import TransactionTestCase, skipUnlessDBFeature

from apps.bots import tests_booking_terms as fixtures
from apps.scheduling.services import validate_appointment_availability
from apps.services.models import Service


@skipUnlessDBFeature("has_select_for_update")
class BookingTermsLockTests(TransactionTestCase):
    def setUp(self):
        fixtures.AutomaticBookingTermsTests.setUp(self)

    store_offer = fixtures.AutomaticBookingTermsTests.store_offer
    book = fixtures.AutomaticBookingTermsTests.book

    def test_catalog_update_cannot_interleave_validation_and_creation(self):
        service_id = self.service.pk

        def update_price():
            try:
                with transaction.atomic():
                    with connection.cursor() as cursor:
                        cursor.execute("SET LOCAL lock_timeout = '150ms'")
                    Service.objects.filter(pk=service_id).update(price_from=200)
                return "updated"
            except OperationalError as exc:
                return str(exc)
            finally:
                connections.close_all()

        def check_locked(*args, **kwargs):
            with ThreadPoolExecutor(max_workers=1) as pool:
                outcome = pool.submit(update_price).result(timeout=5)
            self.assertIn("lock timeout", outcome)
            return validate_appointment_availability(*args, **kwargs)

        with patch("apps.conversations.booking.validate_appointment_availability", side_effect=check_locked), \
             patch("apps.bots.inbox_service.send_outbound_message", return_value=None):
            result = self.book()
        self.assertEqual(result.status, "booked", result.reason)
        self.assertEqual(str(result.appointment.booked_price), "100.00")
        with ThreadPoolExecutor(max_workers=1) as pool:
            self.assertEqual(pool.submit(update_price).result(timeout=5), "updated")
