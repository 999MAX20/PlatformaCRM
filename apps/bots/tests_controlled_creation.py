from unittest.mock import patch

from django.test import TestCase
from rest_framework.exceptions import PermissionDenied

from apps.bots import tests_runtime_configuration as fixtures
from apps.conversations.ai_qualification import ConversationQualification
from apps.conversations.auto_pipeline import maybe_run_auto_pipeline
from apps.conversations.pipeline import run_conversation_pipeline
from apps.ai_core.models import AgentProfile
from apps.bots.models import Bot
from apps.clients.models import Client
from apps.leads.models import Lead
from apps.tasks.models import Task
from apps.crm.models import Deal


class ControlledCreationTests(TestCase):
    def setUp(self):
        fixtures.RuntimeConfigurationTests.setUp(self)
        self.bot.settings_json = {"_automatic_actor_id": self.business.owner_id, "auto_crm_pipeline": {
            "mode": "draft_deal", "enabled": True, "creation_policy": "automatic", "auto_send_reply": False}}
        self.bot.save()
        self.profile.allowed_tools_json = {"tools": ["create_client", "create_lead", "create_task", "create_deal"]}
        self.profile.save()
        self.qualification = ConversationQualification(intent="purchase_interest", confidence=0.95, summary="Customer requests cleaning",
            client_name="Test customer", should_create_lead=True, should_create_task=True, should_create_deal=True, next_action="Call customer")

    def run_pipeline(self):
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(self.qualification, None)):
            return maybe_run_auto_pipeline(conversation=self.conversation, message=self.message, channel=self.channel)

    def test_enabled_creation_produces_linked_entities_and_replay_is_idempotent(self):
        result = self.run_pipeline()
        self.assertTrue(all(result.result.created.values()))
        again = self.run_pipeline()
        self.assertFalse(any(again.result.created.values()))
        for model in (Client, Lead, Task, Deal):
            self.assertEqual(model.objects.filter(business=self.business).count(), 1)
        self.assertEqual(result.result.deal.client_id, result.result.client.id)
        self.assertEqual(result.result.lead.status, "new")
        self.assertEqual(result.confirmation_policy["requires_explicit_confirmation"], [])

    def test_disabled_tools_do_not_create_work(self):
        self.profile.allowed_tools_json = {"tools": ["create_client"]}; self.profile.save()
        self.run_pipeline()
        self.assertEqual(Client.objects.count(), 1)
        self.assertFalse(Lead.objects.exists() or Task.objects.exists() or Deal.objects.exists())

    def test_direct_service_cannot_bypass_revoked_consent(self):
        Bot.objects.filter(pk=self.bot.pk).update(settings_json={"auto_crm_pipeline": {"mode": "off"}})
        with self.assertRaises(PermissionDenied):
            run_conversation_pipeline(conversation=self.conversation, automatic_creation=True, qualification_override=self.qualification)
        self.assertFalse(Client.objects.exists() or Lead.objects.exists())

    def test_revoked_authorizing_user_blocks_creation(self):
        self.business.owner.is_active = False; self.business.owner.save(update_fields=["is_active"])
        with self.assertRaises(PermissionDenied):
            run_conversation_pipeline(conversation=self.conversation, automatic_creation=True, qualification_override=self.qualification)
        self.assertFalse(Client.objects.exists())

    def test_legacy_settings_do_not_gain_autonomous_creation(self):
        self.bot.settings_json["auto_crm_pipeline"].pop("creation_policy"); self.bot.save()
        self.run_pipeline()
        self.assertFalse(Lead.objects.exists() or Task.objects.exists() or Deal.objects.exists())

    def test_existing_client_is_reused_without_editing_fields(self):
        client = Client.objects.create(business=self.business, full_name="Existing", phone="123")
        self.conversation.client = client; self.conversation.save()
        self.qualification.client_name = "Changed name"; self.qualification.phone = "456"
        self.run_pipeline()
        client.refresh_from_db()
        self.assertEqual((client.full_name, client.phone), ("Existing", "123"))

    def test_client_switch_applies_in_staff_confirmation_mode(self):
        self.bot.settings_json["auto_crm_pipeline"]["creation_policy"] = "staff_confirmation"
        self.bot.save()
        self.profile.allowed_tools_json = {"tools": ["create_lead"]}
        self.profile.save()
        result = self.run_pipeline()
        self.assertEqual(result.status, "needs_review")
        self.assertFalse(Client.objects.exists() or Lead.objects.exists())

    def test_public_intake_cannot_bypass_disabled_client_creation(self):
        from rest_framework.test import APIClient
        self.profile.allowed_tools_json = {"tools": ["create_lead"]}; self.profile.save()
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(self.qualification, None)):
            response = APIClient().post(f"/api/public/website-chat/{self.channel.public_token}/conversations/",
                {"message": "Book cleaning", "phone": "+77015550001", "full_name": "Visitor", "whatsapp_consent": True}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNone(response.data["client_id"])
        self.assertFalse(Client.objects.exists())

    def test_public_intake_returns_guarded_creation_result(self):
        from rest_framework.test import APIClient
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(self.qualification, None)):
            response = APIClient().post(f"/api/public/website-chat/{self.channel.public_token}/conversations/",
                {"message": "Book cleaning", "phone": "+77015550002", "full_name": "Visitor", "whatsapp_consent": True}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        self.assertIsNotNone(response.data["client_id"])
        self.assertIsNotNone(response.data["lead_id"])
        self.assertEqual(Client.objects.count(), 1)
        from apps.outreach.models import OutreachConsent
        self.assertTrue(OutreachConsent.objects.filter(client_id=response.data["client_id"]).exists())
