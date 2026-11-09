from datetime import time, timedelta

from django.test import TestCase
from django.utils.dateparse import parse_datetime

from apps.bots import tests_automatic_booking as fixtures
from apps.bots.models import BotMessage
from apps.bots.runtime_configuration import agent_runtime_fingerprint
from apps.bots.scheduling_context import build_bot_scheduling_context
from apps.branches.physical_resources import save_resource_requirements
from apps.branches.single_location import ensure_initial_location
from apps.conversations.booking import store_offered_slots
from apps.scheduling.models import Appointment, Resource, WorkingHours
from apps.scheduling.record_commands import create_record
from apps.scheduling.resource_services import create_resource


class BotResourceBookingTests(TestCase):
    book = fixtures.AutomaticBookingTests.book

    def setUp(self):
        fixtures.AutomaticBookingTests.setUp(self)
        self.branch = ensure_initial_location(self.business)
        self.room = create_resource(business=self.business, name="Room", resource_type="room")
        WorkingHours.objects.create(business=self.business, weekday=self.start.weekday(), start_time=time(9), end_time=time(18))
        save_resource_requirements(branch=self.branch, actor=self.business.owner, service_id=self.service.pk, resource_ids=[self.room.pk])
        self.slot.update(branch_id=self.branch.pk, branch_name=self.branch.name, branch_address=self.branch.address)
        store_offered_slots(conversation=self.conversation, scheduling_context={"next_available_slots": [self.slot]},
            runtime_fingerprint=agent_runtime_fingerprint(self.conversation), offer_message_id=self.offer.pk)

    def test_bot_booking_reserves_room_and_replay_keeps_one_reservation(self):
        result = self.book()
        self.assertEqual(result.status, "booked", result.reason)
        self.assertEqual(list(result.appointment.reserved_resources.values_list("resource_id", flat=True)), [self.room.pk])
        self.conversation.refresh_from_db()
        self.assertEqual(self.book().appointment.pk, result.appointment.pk)
        self.assertEqual(Appointment.objects.count(), 1)

    def test_stale_offer_cannot_book_room_taken_by_other_specialist(self):
        other = Resource.objects.create(business=self.business, name="Other specialist")
        create_record(business=self.business, actor=self.business.owner, client=self.client, service=self.service,
            resource=other, start_at=self.start, branch=self.branch)
        result = self.book()
        self.assertNotEqual(result.status, "booked")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_bot_context_excludes_busy_resources_and_inactive_requirement(self):
        BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Book Cleaning")
        context = build_bot_scheduling_context(self.conversation)
        self.assertTrue(context["next_available_slots"])
        slot = context["next_available_slots"][0]
        other = Resource.objects.create(business=self.business, name="Other specialist")
        start = parse_datetime(slot["start_at"])
        create_record(business=self.business, actor=self.business.owner, client=self.client, service=self.service,
            resource=other, start_at=start, branch=self.branch)
        context = build_bot_scheduling_context(self.conversation)
        self.assertFalse(any(parse_datetime(row["start_at"]) < start + timedelta(minutes=30)
            and parse_datetime(row["end_at"]) > start for row in context["next_available_slots"]))
        self.room.is_active = False
        self.room.save()
        self.assertFalse(build_bot_scheduling_context(self.conversation)["next_available_slots"])
