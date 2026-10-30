"""Anonymous intake receipts must not reveal prior CRM contact membership."""
from uuid import UUID

from django.test import TestCase
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.bots.models import Bot, BotChannel, BotConversation, BotMessage
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.leads.models import Lead, LeadForm, LeadFormSubmission


class PublicIntakePrivacyTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="privacy-owner", email="privacy-owner@example.test", role="business_owner")
        self.business = Business.objects.create(owner=self.owner, name="Synthetic intake", slug="public-privacy")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.client_record = Client.objects.create(business=self.business, full_name="Private existing name", phone="+77010001122", email="private-contact@example.test")
        self.form = LeadForm.objects.create(business=self.business, name="Public form", title="Contact", default_responsible_user=self.owner)
        self.bot = Bot.objects.create(business=self.business, name="Public bot", status="active")
        self.channel = BotChannel.objects.create(bot=self.bot, channel="website", status="active")
        self.api = APIClient(REMOTE_ADDR="192.0.2.200")

    def submit(self, **fields):
        return self.api.post(f"/api/public/forms/{self.form.public_id}/submit/", {"full_name": "Visitor", "message": "Hello", **fields}, format="json")

    def chat(self, **fields):
        return self.api.post(f"/api/public/website-chat/{self.channel.public_token}/conversations/", {"full_name": "Visitor", "message": "Hello", **fields}, format="json")

    def form_receipt(self, response):
        self.assertEqual(response.status_code, 201, response.data)
        return {k: v for k, v in response.data.items() if k not in {"submission_id", "lead_id"}}

    def chat_receipt(self, response):
        self.assertEqual(response.status_code, 201, response.data)
        UUID(response.data["conversation_id"])
        return {k: v for k, v in response.data.items() if k not in {"conversation_id", "message_id"}}

    def test_form_phone_membership_not_disclosed_but_staff_evidence_retained(self):
        known = self.submit(phone=self.client_record.phone)
        unknown = self.submit(phone="+77010003344")
        self.assertEqual(self.form_receipt(known), self.form_receipt(unknown))
        self.assertFalse(known.data["duplicate_warning"])
        submission = LeadFormSubmission.objects.get(pk=known.data["submission_id"])
        self.assertEqual(submission.client_id, self.client_record.pk)
        self.assertTrue(submission.duplicate_json["duplicates"])
        self.assertNotIn("Private existing name", str(known.data))

    def test_form_normalized_phone_alias_and_replay_do_not_disclose_membership(self):
        first = self.submit(whatsapp="+7 701 000 11 22")
        second = self.submit(whatsapp="+7 701 000 11 22")
        self.assertFalse(first.data["duplicate_warning"])
        self.assertEqual(self.form_receipt(first), self.form_receipt(second))
        self.assertEqual(Lead.objects.filter(client=self.client_record).count(), 2)

    def test_form_email_membership_not_disclosed(self):
        known = self.submit(email=self.client_record.email)
        unknown = self.submit(email="new-contact@example.test")
        self.assertEqual(self.form_receipt(known), self.form_receipt(unknown))

    def test_widget_phone_membership_and_stable_client_id_not_disclosed(self):
        known = self.chat(phone=self.client_record.phone)
        unknown = self.chat(phone="+77010003344")
        self.assertEqual(self.chat_receipt(known), self.chat_receipt(unknown))
        self.assertIsNone(known.data["client_id"])
        self.assertIsNone(known.data["lead_id"])
        conversation = BotConversation.objects.get(public_id=known.data["conversation_id"])
        self.assertEqual(conversation.client_id, self.client_record.pk)
        self.client_record.refresh_from_db()
        self.assertEqual(self.client_record.full_name, "Private existing name")

    def test_widget_email_and_replay_keep_fresh_conversation_capability(self):
        first = self.chat(email=self.client_record.email)
        second = self.chat(email=self.client_record.email)
        self.assertIsNone(first.data["client_id"])
        self.assertEqual(self.chat_receipt(first), self.chat_receipt(second))
        self.assertNotEqual(first.data["conversation_id"], second.data["conversation_id"])
        response = self.api.post(f"/api/public/website-chat/{self.channel.public_token}/conversations/{first.data['conversation_id']}/messages/", {"message": "Follow up"}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertNotIn("client_id", response.data)
        self.assertEqual(BotMessage.objects.count(), 3)

    def test_widget_controlled_mode_does_not_reveal_existing_vs_uncreated_client(self):
        self.bot.settings_json = {"auto_crm_pipeline": {"creation_policy": "suggest_only", "enabled": False}}
        self.bot.save(update_fields=["settings_json"])
        known = self.chat(phone=self.client_record.phone)
        unknown = self.chat(phone="+77010003344")
        self.assertEqual(self.chat_receipt(known), self.chat_receipt(unknown))
        self.assertIsNone(known.data["client_id"])
        self.assertEqual(Client.objects.count(), 1)

    def test_no_contact_widget_still_accepts_and_can_receive_followup(self):
        response = self.chat()
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["client_id"])
        self.assertEqual(BotConversation.objects.count(), 1)

    def test_invalid_widget_input_has_no_intake_effects(self):
        response = self.chat(message="", phone=self.client_record.phone)
        self.assertEqual(response.status_code, 400)
        self.assertFalse(BotConversation.objects.exists())
        self.assertEqual(Client.objects.count(), 1)

    def test_other_channel_cannot_use_fresh_conversation_capability(self):
        created = self.chat()
        other_bot = Bot.objects.create(business=self.business, name="Separate public bot", status="active")
        other_channel = BotChannel.objects.create(bot=other_bot, channel="website", status="active")
        response = self.api.post(f"/api/public/website-chat/{other_channel.public_token}/conversations/{created.data['conversation_id']}/messages/", {"message": "Wrong channel"}, format="json")
        self.assertEqual(response.status_code, 404)
        self.assertEqual(BotMessage.objects.count(), 1)

    def test_archived_match_is_private_and_not_reactivated(self):
        self.client_record.is_archived = True
        self.client_record.save(update_fields=["is_archived"])
        response = self.chat(email=self.client_record.email)
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["client_id"])
        self.assertEqual(BotConversation.objects.get().client_id, self.client_record.pk)
        self.client_record.refresh_from_db()
        self.assertTrue(self.client_record.is_archived)

    def test_email_precedence_stays_internal_when_phone_matches_another_client(self):
        other = Client.objects.create(business=self.business, full_name="Other private", phone="+77010003344")
        response = self.chat(phone=other.phone, email=self.client_record.email)
        self.assertEqual(response.status_code, 201)
        self.assertIsNone(response.data["client_id"])
        self.assertEqual(BotConversation.objects.get().client_id, self.client_record.pk)

    def test_foreign_business_contact_is_not_reused_or_disclosed(self):
        foreign = Business.objects.create(owner=self.owner, name="Other business", slug="public-privacy-other")
        foreign_client = Client.objects.create(business=foreign, full_name="Foreign private", phone="+77010003344")
        form = self.submit(phone=foreign_client.phone)
        chat = self.chat(phone=foreign_client.phone)
        self.assertFalse(form.data["duplicate_warning"])
        self.assertIsNone(chat.data["client_id"])
        self.assertNotEqual(LeadFormSubmission.objects.get().client_id, foreign_client.pk)
        self.assertNotEqual(BotConversation.objects.get().client_id, foreign_client.pk)
        self.assertEqual(Client.objects.filter(business=foreign).count(), 1)
