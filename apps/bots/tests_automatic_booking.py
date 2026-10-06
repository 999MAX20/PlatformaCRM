from datetime import datetime, time, timedelta

from django.test import TestCase
from django.utils import timezone

from apps.bots import tests_runtime_configuration as fixtures
from apps.bots.models import BotMessage
from apps.bots.runtime_configuration import agent_runtime_fingerprint
from apps.clients.models import Client
from apps.conversations.booking import maybe_create_appointment_from_reply, store_offered_slots
from apps.leads.models import Lead
from apps.scheduling.availability import business_zone
from apps.scheduling.models import Appointment, Resource, WorkingHours
from apps.services.models import Service


class AutomaticBookingTests(TestCase):
    def setUp(self):
        fixtures.RuntimeConfigurationTests.setUp(self)
        self.bot.settings_json = {"_automatic_actor_id": self.business.owner_id, "auto_crm_pipeline": {
            "mode": "lead_task", "enabled": True, "creation_policy": "automatic", "create_appointment": True}}
        self.bot.save()
        self.profile.allowed_tools_json = {"tools": ["create_client", "create_lead", "create_appointment"]}; self.profile.save()
        self.client = Client.objects.create(business=self.business, full_name="Existing customer")
        self.lead = Lead.objects.create(business=self.business, client=self.client, status="new")
        self.conversation.client = self.client; self.conversation.lead = self.lead; self.conversation.save()
        self.service = Service.objects.create(business=self.business, name="Cleaning", duration_minutes=30)
        self.resource = Resource.objects.create(business=self.business, name="Doctor", resource_type="staff")
        tomorrow = timezone.localtime(timezone.now(), business_zone(self.business)).date() + timedelta(days=1)
        WorkingHours.objects.create(business=self.business, resource=self.resource, weekday=tomorrow.weekday(), start_time=time(9), end_time=time(18))
        self.start = timezone.make_aware(datetime.combine(tomorrow, time(10)), business_zone(self.business))
        self.slot = {"service_id": self.service.id, "service_name": "Cleaning", "resource_id": self.resource.id,
                     "resource_name": "Doctor", "start_at": self.start.isoformat(), "end_at": (self.start + timedelta(minutes=30)).isoformat()}
        self.offer = BotMessage.objects.create(conversation=self.conversation, direction="outbound", sender_type="bot", text="1. Cleaning Doctor tomorrow 10:00", status="sent")
        store_offered_slots(conversation=self.conversation, scheduling_context={"next_available_slots": [self.slot]},
                            runtime_fingerprint=agent_runtime_fingerprint(self.conversation), offer_message_id=self.offer.id)
        self.reply = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="1 вариант подходит")

    def book(self):
        return maybe_create_appointment_from_reply(conversation=self.conversation, message=self.reply)

    def test_explicit_selection_creates_once_without_changing_lead(self):
        result = self.book()
        self.assertEqual(result.status, "booked", result.reason)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "new")
        self.conversation.refresh_from_db()
        again = self.book()
        self.assertEqual(again.appointment.id, result.appointment.id)
        self.assertEqual(Appointment.objects.count(), 1)
        self.assertEqual(BotMessage.objects.filter(sender_type="system").count(), 1)
        self.assertEqual(result.appointment.client_id, self.client.id)

    def test_questions_negation_and_incidental_numbers_are_not_consent(self):
        for text in ["не подходит 1 вариант", "цена 1 услуги?", "1 октября", "10:00", "да", "какое время?"]:
            with self.subTest(text=text):
                self.reply.text = text
                self.assertEqual(self.book().status, "skipped")
        self.assertFalse(Appointment.objects.exists())

    def test_busy_slot_does_not_double_book(self):
        Appointment.objects.create(business=self.business, client=self.client, service=self.service, resource=self.resource,
                                   start_at=self.start, end_at=self.start + timedelta(minutes=30))
        self.assertEqual(self.book().status, "requires_staff")
        self.assertEqual(Appointment.objects.count(), 1)

    def test_reconfigured_or_undelivered_offer_cannot_book(self):
        self.offer.status = "queued"; self.offer.save()
        self.assertEqual(self.book().status, "requires_staff")
        self.offer.status = "sent"; self.offer.save()
        self.profile.allowed_tools_json = {"tools": []}; self.profile.save()
        self.assertEqual(self.book().status, "requires_staff")
        self.assertFalse(Appointment.objects.exists())

    def test_complete_pipeline_sends_exact_offer_then_books_customer_choice(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        from apps.conversations.ai_qualification import ConversationQualification
        from apps.conversations.auto_pipeline import maybe_run_auto_pipeline
        self.bot.settings_json["auto_crm_pipeline"]["auto_send_reply"] = True
        self.bot.save()
        qualification = ConversationQualification(intent="appointment_request", confidence=0.99,
            summary="Customer requests cleaning", should_create_lead=False, should_create_task=False)
        self.message.text = "I would like to book cleaning"; self.message.save()
        # The customer chooses only after receiving the newly generated offer.
        self.reply.delete()
        log = SimpleNamespace(id=None, input_json={"scheduling_context": {"next_available_slots": [self.slot]}})
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(qualification, None)), patch("apps.conversations.auto_pipeline.suggest_bot_reply", return_value=(SimpleNamespace(output_text="Choose a time"), log, [], [])), patch("apps.bots.outbound_delivery.send_message", side_effect=lambda *args, **kwargs: {"ok": True, "provider_message_id": str(kwargs["payload"]["zani_message_id"])}):
            offer = maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)
            self.assertIsNotNone(offer.reply_message, offer.reply_error)
            self.assertIn("Cleaning", offer.reply_message.text)
            self.assertIn("Doctor", offer.reply_message.text)
            from apps.bots.outbound_delivery import deliver_outbound_message
            delivered = deliver_outbound_message(offer.reply_message.id)
            self.assertEqual(delivered.status, "sent", delivered.error_text)
            self.conversation.refresh_from_db()
            self.reply = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="1 вариант подходит")
            booked = maybe_run_auto_pipeline(conversation=self.conversation, message=self.reply)
        self.assertEqual(booked.booking.status, "booked", booked.booking.reason)
        self.assertEqual(Appointment.objects.count(), 1)
        self.lead.refresh_from_db()
        self.assertEqual(self.lead.status, "new")
