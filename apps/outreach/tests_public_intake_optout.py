from django.db import connection
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import User
from apps.ai_core.models import AgentProfile, BusinessKnowledgeItem
from apps.bots.models import Bot, BotChannel, BotConversation
from apps.businesses.models import Business, BusinessMember
from apps.clients.models import Client
from apps.leads.models import Lead, LeadForm, LeadFormSubmission
from apps.outreach.consent import record_inbound_consent
from apps.outreach.models import OutreachConsent
from apps.outreach.services import record_explicit_consent


class PublicIntakeOptOutTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="public-consent-owner", email="public-consent-owner@example.test", role="business_owner")
        self.operator = User.objects.create_user(username="public-consent-op", email="public-consent-op@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Consent boundary", slug="public-consent-boundary")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        BusinessMember.objects.create(business=self.business, user=self.operator, role="operator")
        self.customer = Client.objects.create(business=self.business, full_name="Synthetic existing", phone="+77010002222",
            email="synthetic-contact@example.test", telegram_id="synthetic-tg-contact", whatsapp_id="+77010002222")
        self.form = LeadForm.objects.create(business=self.business, name="Consent form", title="Synthetic intake", default_responsible_user=self.owner)
        bot = Bot.objects.create(business=self.business, name="Synthetic intake bot", status="active")
        self.channel = BotChannel.objects.create(bot=bot, channel="website", status="active")
        AgentProfile.objects.create(business=self.business, bot=bot, name="Synthetic profile")
        BusinessKnowledgeItem.objects.create(business=self.business, bot=bot, title="Synthetic knowledge", content="Ask the manager.", customer_visible=True)
        address = 1 + sum(map(ord, self._testMethodName)) % 200
        self.public = APIClient(REMOTE_ADDR=f"192.0.2.{address}")

    def opt_out(self, channel="whatsapp", client=None):
        client = client or self.customer
        return OutreachConsent.objects.create(business=client.business, client=client, channel=channel, status="opted_out",
            source="inbound_keyword", note="Synthetic STOP evidence", evidence_json={"text": "STOP", "synthetic": True},
            opted_in_at=timezone.now(), opted_out_at=timezone.now())

    def snapshot(self, consent):
        return OutreachConsent.objects.values().get(pk=consent.pk)

    def form_post(self, **fields):
        return self.public.post(f"/api/public/forms/{self.form.public_id}/submit/", {
            "full_name": "Synthetic visitor", "phone": self.customer.phone, "message": "Synthetic intake", **fields,
        }, format="json")

    def chat_post(self, **fields):
        return self.public.post(f"/api/public/website-chat/{self.channel.public_token}/conversations/", {
            "full_name": "Synthetic visitor", "phone": self.customer.phone, "message": "Synthetic intake", **fields,
        }, format="json")

    def public_consent(self, client=None, channel="whatsapp", **kwargs):
        return record_explicit_consent(client=client or self.customer, channel=channel, source="lead_form", note="Public flag",
            evidence={"marketing_consent": True}, **kwargs)

    def test_helper_preserves_full_whatsapp_refusal(self):
        consent = self.opt_out()
        before = self.snapshot(consent)
        result = self.public_consent()
        self.assertEqual(result.pk, consent.pk)
        self.assertEqual(result.status, "opted_out")
        self.assertEqual(self.snapshot(consent), before)

    def test_helper_preserves_full_telegram_refusal(self):
        consent = self.opt_out("telegram")
        before = self.snapshot(consent)
        self.public_consent(channel="telegram")
        self.assertEqual(self.snapshot(consent), before)

    def test_new_unknown_and_existing_optin_controls(self):
        consent = self.public_consent()
        self.assertEqual(consent.status, "opted_in")
        self.assertIsNotNone(consent.opted_in_at)
        self.assertIsNone(consent.opted_out_at)
        self.assertEqual(consent.evidence_json, {"marketing_consent": True})
        for state in ("unknown", "opted_in"):
            OutreachConsent.objects.filter(pk=consent.pk).update(status=state, source="old")
            again = self.public_consent()
            self.assertEqual((again.pk, again.status, again.source), (consent.pk, "opted_in", "lead_form"))
        self.assertEqual(OutreachConsent.objects.count(), 1)

    def test_stop_becoming_visible_before_update_cannot_be_overwritten(self):
        consent = OutreachConsent.objects.create(business=self.business, client=self.customer, channel="whatsapp", status="unknown")
        for initial in ("unknown", "opted_in"):
            OutreachConsent.objects.filter(pk=consent.pk).update(status=initial)
            injected = []
            stamp = timezone.now()

            def stop_before_update(execute, sql, params, many, context):
                if not injected and sql.lstrip().upper().startswith("UPDATE") and OutreachConsent._meta.db_table in sql:
                    injected.append(True)
                    OutreachConsent.objects.filter(pk=consent.pk).update(status="opted_out", source="synthetic_stop",
                        note="STOP before public write", evidence_json={"stop": True}, opted_out_at=stamp, updated_at=stamp)
                return execute(sql, params, many, context)

            with self.subTest(initial=initial), connection.execute_wrapper(stop_before_update):
                self.public_consent()
                self.assertTrue(injected)
                consent.refresh_from_db()
                self.assertEqual((consent.status, consent.source, consent.opted_out_at), ("opted_out", "synthetic_stop", stamp))
                self.assertEqual(consent.evidence_json, {"stop": True})

    def test_public_form_flags_and_replays_keep_refusal_and_accept_intake(self):
        consent = self.opt_out()
        before = self.snapshot(consent)
        for flag in ("marketing_consent", "outreach_consent", "newsletter_consent", "whatsapp_consent"):
            with self.subTest(flag=flag):
                response = self.form_post(**{flag: True})
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(self.snapshot(consent), before)
        self.assertEqual(LeadFormSubmission.objects.count(), 4)
        self.assertEqual(Lead.objects.count(), 4)
        self.assertEqual(Client.objects.count(), 1)

    def test_public_chat_flags_and_replays_keep_refusal_and_accept_intake(self):
        consent = self.opt_out()
        before = self.snapshot(consent)
        for flag in ("marketing_consent", "outreach_consent", "newsletter_consent", "whatsapp_consent"):
            with self.subTest(flag=flag):
                response = self.chat_post(**{flag: True})
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(self.snapshot(consent), before)
        self.assertEqual(BotConversation.objects.count(), 4)
        self.assertFalse(Lead.objects.exists())

    def test_email_match_with_unverified_supplied_phone_cannot_reset_consent(self):
        consent = self.opt_out()
        before = self.snapshot(consent)
        for submit in (self.form_post, self.chat_post):
            with self.subTest(submit=submit.__name__):
                response = submit(phone="+77010009999", email=self.customer.email, marketing_consent=True)
                self.assertEqual(response.status_code, 201, response.data)
                self.assertEqual(self.snapshot(consent), before)
        self.assertEqual(Client.objects.count(), 1)

    def test_new_form_client_can_still_record_explicit_consent(self):
        response = self.form_post(phone="+77010003333", marketing_consent="on")
        self.assertEqual(response.status_code, 201, response.data)
        client = Client.objects.get(phone="+77010003333")
        consent = OutreachConsent.objects.get(client=client, channel="whatsapp")
        self.assertEqual((consent.status, consent.source), ("opted_in", "lead_form"))
        self.assertEqual(consent.evidence_json["fields"]["marketing_consent"], "on")

    def test_new_chat_client_can_still_record_explicit_consent(self):
        response = self.chat_post(phone="+77010004444", whatsapp_consent=True)
        self.assertEqual(response.status_code, 201, response.data)
        client = Client.objects.get(phone="+77010004444")
        consent = OutreachConsent.objects.get(client=client, channel="whatsapp")
        self.assertEqual((consent.status, consent.source), ("opted_in", "website_chat"))
        self.assertFalse(Lead.objects.exists())

    def test_false_or_missing_public_flag_does_not_create_consent(self):
        for submit, phone in ((self.form_post, "+77010005555"), (self.chat_post, "+77010006666")):
            with self.subTest(submit=submit.__name__):
                response = submit(phone=phone, marketing_consent=False)
                self.assertEqual(response.status_code, 201, response.data)
        self.assertFalse(OutreachConsent.objects.exists())

    def test_existing_unknown_is_allowed_to_record_first_explicit_optin(self):
        consent = OutreachConsent.objects.create(business=self.business, client=self.customer, channel="whatsapp", status="unknown")
        response = self.form_post(marketing_consent=True)
        self.assertEqual(response.status_code, 201, response.data)
        consent.refresh_from_db()
        self.assertEqual(consent.status, "opted_in")
        self.assertEqual(OutreachConsent.objects.count(), 1)

    def test_channel_specific_refusal_does_not_block_other_channel_first_consent(self):
        telegram = self.opt_out("telegram")
        before = self.snapshot(telegram)
        self.assertEqual(self.form_post(whatsapp_consent=True).status_code, 201)
        self.assertEqual(self.snapshot(telegram), before)
        self.assertEqual(OutreachConsent.objects.get(client=self.customer, channel="whatsapp").status, "opted_in")

    def test_other_business_contact_and_consent_are_unchanged(self):
        other = Business.objects.create(owner=self.owner, name="Other consent boundary", slug="other-public-consent")
        client = Client.objects.create(business=other, full_name="Other synthetic", phone=self.customer.phone)
        refusal = self.opt_out(client=client)
        before = self.snapshot(refusal)
        self.assertEqual(self.form_post(marketing_consent=True).status_code, 201)
        self.assertEqual(self.snapshot(refusal), before)
        self.assertEqual(OutreachConsent.objects.get(client=self.customer).status, "opted_in")

    def test_existing_inbound_start_reconsent_flow_is_preserved(self):
        for channel, external_id in (("telegram", self.customer.telegram_id), ("whatsapp", self.customer.whatsapp_id)):
            with self.subTest(channel=channel):
                consent = self.opt_out(channel)
                result = record_inbound_consent(business=self.business, channel=channel, external_user_id=external_id, text="START")
                self.assertEqual(result["status"], "opted_in")
                consent.refresh_from_db()
                self.assertEqual(consent.status, "opted_in")
                self.assertIsNone(consent.opted_out_at)

    def test_authorized_management_reconsent_and_role_denial_are_preserved(self):
        consent = self.opt_out()
        api = APIClient()
        api.force_authenticate(self.operator)
        response = api.patch(f"/api/outreach/consents/{consent.pk}/", {"status": "opted_in"}, format="json")
        self.assertEqual(response.status_code, 404)  # Existing OWN notification scope hides this row.
        consent.refresh_from_db()
        self.assertEqual(consent.status, "opted_out")
        api.force_authenticate(self.owner)
        response = api.patch(f"/api/outreach/consents/{consent.pk}/", {"status": "opted_in", "source": "synthetic_confirmed"}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        consent.refresh_from_db()
        self.assertEqual(consent.status, "opted_in")
        self.assertIsNone(consent.opted_out_at)

    def test_stop_after_new_consent_wins_over_public_replay(self):
        consent = self.public_consent()
        result = record_inbound_consent(business=self.business, channel="whatsapp", external_user_id=self.customer.whatsapp_id, text="STOP")
        self.assertEqual(result["status"], "opted_out")
        before = self.snapshot(consent)
        self.public_consent()
        self.assertEqual(self.snapshot(consent), before)
