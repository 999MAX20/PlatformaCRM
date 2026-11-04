from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from threading import Barrier
from unittest.mock import patch

from django.db import connections
from django.test import TransactionTestCase, override_settings, skipUnlessDBFeature

from apps.bots import tests_booking_creation as fixtures
from apps.bots.models import BotConversation, BotMessage
from apps.conversations.booking import maybe_create_appointment_from_reply
from apps.integrations.models import BusinessEvent
from apps.scheduling.models import Appointment
from apps.scheduling.services import handle_appointment_created
from apps.automations.models import AutomationRun
from apps.tasks.models import Task


@skipUnlessDBFeature("has_select_for_update")
@override_settings(AUTOMATIONS_RUN_INLINE=True)
class BookingCreationConcurrencyTests(TransactionTestCase):
    def setUp(self):
        fixtures.BookingCreationTests.setUp(self)

    def parallel(self, operation):
        barrier = Barrier(2)
        def execute():
            connections.close_all()
            try:
                barrier.wait(timeout=20)
                return operation()
            finally:
                connections.close_all()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(execute) for _ in range(2)]
            return [future.result(timeout=45) for future in futures]

    def assert_once(self):
        self.assertEqual(BusinessEvent.objects.filter(event_type="appointment.created").count(), 1)
        self.assertEqual(AutomationRun.objects.filter(rule=self.rule).count(), 1)
        self.assertEqual(Task.objects.filter(title="Prepare this appointment").count(), 1)

    def test_concurrent_customer_selection_creates_one_record_and_effect(self):
        def book():
            result = maybe_create_appointment_from_reply(
                conversation=BotConversation.objects.get(pk=self.conversation.pk),
                message=BotMessage.objects.get(pk=self.reply.pk))
            self.assertEqual(result.status, "booked", result.reason)
            return result.appointment.pk
        with patch("apps.bots.inbox_service.send_outbound_message", return_value=None):
            ids = self.parallel(book)
        self.assertEqual(ids[0], ids[1])
        self.assertEqual(Appointment.objects.count(), 1)
        self.assert_once()

    def test_concurrent_creation_callbacks_execute_once(self):
        record = Appointment.objects.create(business=self.business, client=self.client,
            responsible_user=self.business.owner, service=self.service, resource=self.resource,
            start_at=self.start, end_at=self.start + timedelta(minutes=30))
        self.parallel(lambda: handle_appointment_created(Appointment.objects.get(pk=record.pk)).pk)
        self.assert_once()
