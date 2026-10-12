from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase
from apps.bots.tests_automatic_booking import AutomaticBookingTests
from apps.bots.models import BotMessage
from apps.bots.scheduling_context import build_bot_scheduling_context
from apps.bots.runtime_configuration import agent_runtime_fingerprint
from apps.conversations.booking import maybe_create_appointment_from_reply, store_offered_slots, format_booking_offer
from apps.scheduling.models import Appointment
from .models import BranchService, SpecialistAbsence
from .services import create_branch
from .bot_context import remember_branch_reply


class BranchBotTests(TestCase):
    def setUp(self):
        AutomaticBookingTests.setUp(self)
        self.branches = [create_branch(business=self.business, actor=self.business.owner,
            name=name, address=f"Address {name}") for name in ["North", "South", "East", "West", "Center"]]
        self.resource.contact_phone = "+private"
        self.resource.save()
        BranchService.objects.filter(branch=self.branches[0]).update(price_from=10000)

    def inbound(self, text):
        message = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text=text)
        remember_branch_reply(self.conversation, message)
        return message

    def test_five_branches_require_selection_then_grounded_terms(self):
        self.inbound("Book Cleaning")
        context = build_bot_scheduling_context(self.conversation)
        self.assertEqual(len(context["branches"]), 5)
        self.assertFalse(context["next_available_slots"])
        self.inbound("North")
        context = build_bot_scheduling_context(self.conversation)
        self.assertEqual(context["branch_selection"], self.branches[0].pk)
        self.assertTrue(context["next_available_slots"])
        self.assertNotIn("+private", str(context))
        slot = context["next_available_slots"][0]
        self.assertEqual(slot["price_from"], "10000.00")
        self.assertIn("Address North", format_booking_offer(self.conversation, [slot]))
        self.inbound("Thanks")
        self.assertEqual(build_bot_scheduling_context(self.conversation)["branch_selection"], self.branches[0].pk)

    def prepare_offer(self):
        self.inbound("Book Cleaning at North")
        context = build_bot_scheduling_context(self.conversation)
        self.assertTrue(context["next_available_slots"])
        store_offered_slots(conversation=self.conversation, scheduling_context=context,
            runtime_fingerprint=agent_runtime_fingerprint(self.conversation), offer_message_id=self.offer.pk)
        return context

    def test_changed_branch_or_empty_context_clears_old_offers(self):
        self.prepare_offer()
        self.inbound("South")
        context = build_bot_scheduling_context(self.conversation)
        self.assertFalse(context["next_available_slots"])
        result = maybe_create_appointment_from_reply(conversation=self.conversation, message=self.inbound("1"))
        self.assertEqual(result.status, "skipped")
        self.assertFalse(Appointment.objects.exists())
        self.prepare_offer()
        store_offered_slots(conversation=self.conversation, scheduling_context={"next_available_slots": []})
        self.assertFalse(self.conversation.metadata_json["auto_booking"]["offered_slots"])

    def test_confirmed_branch_booking_is_idempotent_and_price_change_rejected(self):
        self.prepare_offer()
        reply = self.inbound("1")
        with patch("apps.bots.inbox_service.send_outbound_message", return_value=None):
            result = maybe_create_appointment_from_reply(conversation=self.conversation, message=reply)
            self.assertEqual(result.status, "booked", result.reason)
            self.assertEqual(result.appointment.branch_id, self.branches[0].pk)
            self.assertEqual(str(result.appointment.booked_price), "10000.00")
            self.conversation.refresh_from_db()
            again = maybe_create_appointment_from_reply(conversation=self.conversation, message=reply)
            self.assertEqual(again.appointment.pk, result.appointment.pk)
        self.prepare_offer()
        BranchService.objects.filter(branch=self.branches[0]).update(price_from=15000)
        result = maybe_create_appointment_from_reply(conversation=self.conversation, message=self.inbound("1"))
        self.assertEqual(result.status, "requires_staff")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_config_scope_any_branch_and_absence(self):
        self.bot.settings_json["branch_ids"] = [self.branches[0].pk]
        self.bot.save()
        self.inbound("Book Cleaning at any branch")
        context = build_bot_scheduling_context(self.conversation)
        self.assertEqual(len(context["branches"]), 1)
        self.assertTrue(context["next_available_slots"])
        SpecialistAbsence.objects.create(business=self.business, resource=self.resource,
            starts_on=self.start.date()-timedelta(days=1), ends_on=self.start.date()+timedelta(days=10), reason="Private illness")
        context = build_bot_scheduling_context(self.conversation)
        self.assertFalse(context["next_available_slots"])
        self.assertNotIn("Private illness", str(context))
