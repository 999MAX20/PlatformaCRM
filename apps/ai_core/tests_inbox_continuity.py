from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings

from apps.bots import tests_runtime_configuration as fixtures
from apps.bots.models import BotMessage
from apps.conversations.ai_qualification import ConversationQualification
from apps.conversations.auto_pipeline import maybe_run_auto_pipeline
from apps.ai_core.models import AgentTurn


class InboxContinuityTests(TestCase):
    def setUp(self):
        fixtures.RuntimeConfigurationTests.setUp(self)
        self.qualification = ConversationQualification(intent="price_question", confidence=0.99, summary="Price")

    def run_pipeline(self):
        return maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)

    def test_scheduling_remembers_specialist_but_latest_choice_wins(self):
        from apps.bots.scheduling_context import build_bot_scheduling_context
        from apps.scheduling.models import Resource
        from apps.services.models import Service
        Service.objects.create(business=self.business, name="Consultation", duration_minutes=30)
        first = Resource.objects.create(business=self.business, name="Айгерим", resource_type="staff")
        second = Resource.objects.create(business=self.business, name="Алия", resource_type="staff")
        previous = {"direction": "inbound", "text": "Запишите к Айгерим"}
        for latest, expected in [("А завтра?", first.pk), ("Лучше к Алии", second.pk), ("Можно к любому врачу", None)]:
            with self.subTest(latest=latest), patch("apps.bots.scheduling_context.get_available_slots", return_value=[]):
                context = build_bot_scheduling_context(self.conversation,
                    message_context=[previous, {"direction": "inbound", "text": latest}])
            self.assertEqual((context["matched_resource"] or {}).get("id"), expected)

    def test_duplicate_delivery_does_not_repeat_models_or_send(self):
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(self.qualification, None)) as qualify, \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", return_value=(SimpleNamespace(output_text="Price is 100"), None, [], [])) as reply, \
             patch("apps.bots.outbound_delivery.send_message", return_value={"ok": True, "provider_message_id": "synthetic"}):
            first = self.run_pipeline()
            again = self.run_pipeline()
        self.assertEqual(first.reply_message.pk, again.reply_message.pk)
        self.assertEqual(qualify.call_count, 1)
        self.assertEqual(reply.call_count, 1)
        self.assertEqual(AgentTurn.objects.count(), 1)
        self.assertEqual(self.conversation.messages.filter(direction="outbound").count(), 1)

    def test_new_message_during_qualification_stops_old_reply_and_actions(self):
        def qualify(**kwargs):
            BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Wait, another question")
            return self.qualification, None
        with patch("apps.conversations.auto_pipeline.qualify_conversation", side_effect=qualify), \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply") as reply, \
             patch("apps.conversations.auto_pipeline.run_conversation_pipeline") as pipeline:
            result = self.run_pipeline()
        self.assertEqual(result.status, "skipped_superseded")
        reply.assert_not_called()
        pipeline.assert_not_called()
        self.conversation.refresh_from_db()
        self.assertNotIn("auto_crm_pipeline", self.conversation.metadata_json)

    def test_out_of_order_message_does_not_call_provider(self):
        BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Latest")
        with patch("apps.conversations.auto_pipeline.qualify_conversation") as qualify:
            self.assertEqual(self.run_pipeline().status, "skipped_superseded")
        qualify.assert_not_called()

    def test_reset_during_reply_preserves_history_and_discards_late_result(self):
        from apps.ai_core.inbox_runtime import reset_inbox_memory
        from apps.ai_core.conversation_memory import inbox_memory
        def generate(**kwargs):
            reset_inbox_memory(conversation=self.conversation, actor=self.business.owner)
            return SimpleNamespace(output_text="Obsolete"), None, [], []
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(self.qualification, None)), \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", side_effect=generate), \
             patch("apps.bots.outbound_delivery.send_message") as send:
            self.run_pipeline()
        send.assert_not_called()
        self.assertTrue(self.conversation.messages.filter(pk=self.message.pk).exists())
        self.assertEqual(inbox_memory(conversation=self.conversation)["messages"], [])
        self.assertEqual(AgentTurn.objects.get().status, "cancelled")

    def test_reset_api_rejects_foreign_user_and_preserves_messages(self):
        from rest_framework.test import APIClient
        from apps.accounts.models import User
        api = APIClient()
        url = f"/api/inbox/conversations/{self.conversation.pk}/reset-ai-memory/"
        foreign = User.objects.create_user(username="foreign-memory", email="foreign-memory@example.test")
        api.force_authenticate(foreign)
        self.assertIn(api.post(url).status_code, (403, 404))
        api.force_authenticate(self.business.owner)
        response = api.post(url)
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(self.conversation.messages.count(), 1)

    def test_new_message_during_reply_does_not_send_or_handoff(self):
        def generate(**kwargs):
            BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Actually, no")
            return SimpleNamespace(output_text="Obsolete"), None, [], []
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(self.qualification, None)), \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", side_effect=generate), \
             patch("apps.bots.outbound_delivery.send_message") as send:
            self.run_pipeline()
        send.assert_not_called()
        self.conversation.refresh_from_db()
        self.assertFalse(self.conversation.handoff_required)

    @override_settings(OUTBOUND_MESSAGES_RUN_INLINE=False)
    def test_queued_reply_is_rejected_after_new_inbound(self):
        from apps.bots.outbound_delivery import deliver_outbound_message
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(self.qualification, None)), \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", return_value=(SimpleNamespace(output_text="Old"), None, [], [])):
            result = self.run_pipeline()
        BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="New")
        with patch("apps.bots.outbound_delivery.send_message") as send:
            delivered = deliver_outbound_message(result.reply_message.pk)
        send.assert_not_called()
        self.assertEqual(delivered.status, "failed")
