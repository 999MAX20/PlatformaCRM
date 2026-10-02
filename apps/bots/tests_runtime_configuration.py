from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase

from apps.accounts.models import User
from apps.ai_core.models import AgentProfile, BusinessKnowledgeItem
from apps.bots.models import Bot, BotChannel, BotConversation, BotMessage
from apps.bots.outbound_delivery import deliver_outbound_message
from apps.bots.runtime_configuration import agent_runtime_fingerprint
from apps.businesses.models import Business
from apps.conversations.auto_pipeline import AutoPipelineConfig, AutoPipelineDecision, _send_auto_reply, maybe_run_auto_pipeline


class RuntimeConfigurationTests(TestCase):
    def setUp(self):
        user = User.objects.create_user(username="runtime-config", email="runtime@example.test")
        self.business = Business.objects.create(owner=user, name="Runtime", slug="runtime-config")
        self.bot = Bot.objects.create(business=self.business, name="Runtime", status="active", settings_json={
            "temperature": 0.4, "auto_crm_pipeline": {"mode": "triage", "enabled": True, "auto_send_reply": True}})
        self.channel = BotChannel.objects.create(bot=self.bot, channel="website", status="active")
        self.profile = AgentProfile.objects.create(business=self.business, bot=self.bot, name="Runtime")
        self.knowledge = BusinessKnowledgeItem.objects.create(business=self.business, title="Price", content="100")
        self.conversation = BotConversation.objects.create(business=self.business, bot=self.bot, channel="website", external_user_id="test")
        self.message = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Price?")

    def test_disabled_settings_are_read_even_with_cached_bot(self):
        Bot.objects.filter(pk=self.bot.pk).update(settings_json={"auto_crm_pipeline": {"mode": "off", "enabled": False}})
        with patch("apps.conversations.auto_pipeline.qualify_conversation") as qualify:
            result = maybe_run_auto_pipeline(conversation=self.conversation, message=self.message, channel=self.channel)
        self.assertEqual(result.status, "skipped_disabled")
        qualify.assert_not_called()

    def test_settings_changed_during_qualification_cannot_create_or_reply(self):
        def change(**kwargs):
            Bot.objects.filter(pk=self.bot.pk).update(settings_json={"auto_crm_pipeline": {"mode": "off"}})
            return None, None
        with patch("apps.conversations.auto_pipeline.qualify_conversation", side_effect=change), patch("apps.conversations.auto_pipeline.run_conversation_pipeline") as run:
            result = maybe_run_auto_pipeline(conversation=self.conversation, message=self.message, channel=self.channel)
        self.assertEqual(result.status, "skipped_configuration_changed")
        run.assert_not_called()

    def test_inflight_reply_discarded_for_each_changed_runtime_input(self):
        changes = [
            lambda: Bot.objects.filter(pk=self.bot.pk).update(settings_json={"temperature": 0.1}),
            lambda: AgentProfile.objects.filter(pk=self.profile.pk).update(tone="formal"),
            lambda: AgentProfile.objects.filter(pk=self.profile.pk).update(allowed_tools_json={"tools": []}),
            lambda: BusinessKnowledgeItem.objects.filter(pk=self.knowledge.pk).update(content="200"),
        ]
        for change in changes:
            with self.subTest(change=change):
                decision = AutoPipelineDecision(status="qualified_only", reason="Test")
                def generate(**kwargs):
                    change()
                    return SimpleNamespace(output_text="Old reply"), None, [], []
                with patch("apps.conversations.auto_pipeline.suggest_bot_reply", side_effect=generate), patch("apps.conversations.auto_pipeline.send_outbound_message") as send:
                    _send_auto_reply(conversation=self.conversation, config=AutoPipelineConfig(), decision=decision)
                send.assert_not_called()
                self.assertIn("configuration changed", decision.reply_error)

    def test_queued_old_reply_is_not_sent_after_knowledge_edit(self):
        fingerprint = agent_runtime_fingerprint(self.conversation)
        message = BotMessage.objects.create(conversation=self.conversation, direction="outbound", sender_type="bot", text="Old price", status="queued",
                                            payload_json={"agent_runtime_fingerprint": fingerprint})
        BusinessKnowledgeItem.objects.filter(pk=self.knowledge.pk).update(content="New price")
        with patch("apps.bots.outbound_delivery.send_message") as provider:
            result = deliver_outbound_message(message.id)
        self.assertEqual(result.status, "failed")
        self.assertIsNone(result.delivery_next_retry_at)
        provider.assert_not_called()

    def test_customer_reply_does_not_receive_internal_client_notes(self):
        from apps.clients.models import Client
        from apps.bots.ai import suggest_bot_reply
        client = Client.objects.create(business=self.business, full_name="Customer", notes="PRIVATE_STAFF_NOTE_SENTINEL")
        self.conversation.client = client; self.conversation.save()
        with patch("apps.bots.ai.run_ai_request", return_value=(SimpleNamespace(output_text="Hello"), SimpleNamespace(input_json={}))) as run:
            suggest_bot_reply(conversation=self.conversation)
        self.assertNotIn("PRIVATE_STAFF_NOTE_SENTINEL", str(run.call_args))
        self.assertEqual(run.call_args.kwargs["input_json"]["crm_context"]["client"]["full_name"], "Customer")
