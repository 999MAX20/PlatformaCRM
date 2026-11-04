from decimal import Decimal
from unittest.mock import patch

from django.test import TestCase

from apps.bots import tests_automatic_booking as fixtures
from apps.bots.models import BotMessage
from apps.bots.runtime_configuration import agent_runtime_fingerprint
from apps.bots.scheduling_context import build_bot_scheduling_context
from apps.conversations.booking import format_booking_offer, store_offered_slots
from apps.scheduling.models import Appointment


class AutomaticBookingTermsTests(TestCase):
    def setUp(self):
        fixtures.AutomaticBookingTests.setUp(self)
        self.service.price_from = Decimal("100.00")
        self.service.save(update_fields=["price_from"])
        self.slot.update(price_from="100.00", duration_minutes=30)
        self.store_offer()

    def store_offer(self):
        self.offer.text = format_booking_offer(self.conversation, [self.slot])
        self.offer.save(update_fields=["text"])
        store_offered_slots(conversation=self.conversation, scheduling_context={"next_available_slots": [self.slot]},
                            runtime_fingerprint=agent_runtime_fingerprint(self.conversation), offer_message_id=self.offer.pk)

    def book(self):
        return fixtures.AutomaticBookingTests.book(self)

    def assert_rejected(self):
        with patch("apps.conversations.booking.schedule_appointment_followups") as followups, \
             patch("apps.conversations.booking.create_activity_event") as activity, \
             patch("apps.conversations.booking.write_actor_audit_log") as audit, \
             patch("apps.bots.inbox_service.send_outbound_message") as send:
            self.assertEqual(self.book().status, "requires_staff")
            self.assertFalse(Appointment.objects.exists())
            for effect in (followups, activity, audit, send):
                effect.assert_not_called()
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "new")

    def test_changed_price_rejected_before_creation_effects(self):
        self.service.price_from = Decimal("200.00")
        self.service.save(update_fields=["price_from"])
        self.assert_rejected()

    def test_changed_duration_rejected_before_creation_effects(self):
        self.service.duration_minutes = 60
        self.service.save(update_fields=["duration_minutes"])
        self.assert_rejected()

    def test_missing_offer_terms_require_fresh_offer(self):
        for field in ("price_from", "duration_minutes"):
            with self.subTest(field=field):
                value = self.slot.pop(field)
                self.store_offer()
                self.assert_rejected()
                self.slot[field] = value

    def test_unchanged_terms_book_and_replay_keeps_original_snapshot(self):
        result = self.book()
        self.assertEqual(result.status, "booked", result.reason)
        self.assertEqual(result.appointment.booked_price, Decimal("100.00"))
        self.assertEqual(result.appointment.booked_duration_minutes, 30)
        self.service.price_from = Decimal("200.00")
        self.service.save(update_fields=["price_from"])
        self.conversation.refresh_from_db()
        replay = self.book()
        self.assertEqual(replay.appointment.pk, result.appointment.pk)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(BotMessage.objects.filter(sender_type="system").count(), 1)

    def test_null_and_zero_are_different_confirmed_terms(self):
        self.slot["price_from"] = None
        self.store_offer()
        self.service.price_from = Decimal("0.00")
        self.service.save(update_fields=["price_from"])
        self.assert_rejected()

    def test_zero_price_books_when_confirmed(self):
        self.service.price_from = Decimal("0.00")
        self.service.save(update_fields=["price_from"])
        self.slot["price_from"] = "0.00"
        self.store_offer()
        self.assertIn("0.00", self.offer.text)
        result = self.book()
        self.assertEqual(result.status, "booked", result.reason)
        self.assertEqual(result.appointment.booked_price, Decimal("0.00"))

    def test_generated_no_branch_slots_contain_current_terms(self):
        context = build_bot_scheduling_context(self.conversation, message_context=[{"direction": "inbound", "text": "Book Cleaning tomorrow"}])
        self.assertTrue(context["next_available_slots"])
        for slot in context["next_available_slots"]:
            self.assertEqual(slot.get("duration_minutes"), 30)
            self.assertEqual(slot.get("price_from"), "100.00")

    def test_context_distinguishes_zero_missing_and_positive_price(self):
        for value, expected in ((Decimal("0.00"), "0.00"), (None, ""), (Decimal("10.00"), "10.00")):
            with self.subTest(price=value):
                self.service.price_from = value
                self.service.save(update_fields=["price_from"])
                context = build_bot_scheduling_context(self.conversation, booking_only=True,
                    message_context=[{"direction": "inbound", "text": "Cleaning price"}])
                self.assertEqual(context["services"][0]["price_from"], expected)
                self.assertEqual(context["matched_service"]["price_from"], expected)

    def test_changed_terms_use_existing_pipeline_handoff(self):
        self.service.duration_minutes = 60
        self.service.save(update_fields=["duration_minutes"])
        fixtures.AutomaticBookingTests._assert_pipeline_review_handoff(self)

    def test_revoked_actor_cannot_accept_unchanged_terms(self):
        actor = self.business.owner
        actor.is_active = False
        actor.save(update_fields=["is_active"])
        self.assert_rejected()

    def test_foreign_service_cannot_accept_offer(self):
        from apps.businesses.models import Business
        from apps.services.models import Service
        other = Business.objects.create(owner=self.business.owner, name="Other", slug="terms-other")
        foreign = Service.objects.create(business=other, name="Other service", duration_minutes=30, price_from=100)
        self.slot["service_id"] = foreign.pk
        self.store_offer()
        self.assert_rejected()

    def test_final_creation_rechecks_terms_after_offer_selection(self):
        from apps.conversations.booking import create_appointment_from_conversation

        def change_before_create(**kwargs):
            type(self.service).objects.filter(pk=self.service.pk).update(price_from=200)
            return create_appointment_from_conversation(**kwargs)

        with patch("apps.conversations.booking.create_appointment_from_conversation", side_effect=change_before_create):
            self.assert_rejected()

    def test_branch_duration_change_rejected(self):
        from apps.branches.models import BranchService
        from apps.branches.services import create_branch
        branch = create_branch(business=self.business, actor=self.business.owner, name="North", address="North address")
        self.slot.update(branch_id=branch.pk, branch_name=branch.name, branch_address=branch.address)
        from apps.branches.bot_context import remember_branch_reply
        selection = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="North")
        remember_branch_reply(self.conversation, selection)
        self.store_offer()
        BranchService.objects.filter(branch=branch, service=self.service).update(duration_minutes=60)
        self.assert_rejected()
