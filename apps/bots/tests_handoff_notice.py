"""Customer acknowledgement is deterministic, optional and scoped to one handoff."""
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.bots import tests_runtime_configuration as fixtures
from apps.bots.customer_safety import set_customer_ai_state
from apps.bots.models import BotMessage
from apps.bots.outbound_delivery import deliver_outbound_message
from apps.bots.safety_content import safety_text
from apps.conversations.ai_qualification import ConversationQualification
from apps.conversations.auto_pipeline import maybe_run_auto_pipeline
from apps.ai_core.ai_client import AIClientError, AIClientResult


class HandoffNoticeTests(TestCase):
    def setUp(self):
        fixtures.RuntimeConfigurationTests.setUp(self)

    def process(self, *, kind="uncertain", text=None, provider_failure=False):
        if text is not None:
            self.message.text = text
            self.message.save(update_fields=["text"])
        qualification = None if provider_failure else ConversationQualification(
            intent="other", confidence=.95, summary="Synthetic request", request_kind=kind)
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(qualification, None),
                   side_effect=AIClientError() if provider_failure else None) as classify, \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply") as reply, \
             patch("apps.bots.outbound_delivery.send_message", return_value={"ok": True}) as send:
            result = maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)
        return result, classify, reply, send

    def test_uncertain_request_sends_one_fixed_notice_and_replay_has_no_effect(self):
        result, _, reply, send = self.process()
        self.assertIsNotNone(result.reply_message)
        self.assertEqual(result.reply_message.text, safety_text(self.conversation, "handoff"))
        self.assertEqual(result.reply_message.sender_type, BotMessage.SenderTypes.SYSTEM)
        self.assertEqual(result.reply_message.status, "sent")
        reply.assert_not_called()
        send.assert_called_once()
        repeated, classify, reply, send = self.process()
        self.assertEqual(repeated.reply_message.pk, result.reply_message.pk)
        classify.assert_not_called()
        reply.assert_not_called()
        send.assert_not_called()
        self.message = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Are you there?")
        later, classify, _, send = self.process()
        self.assertIsNone(later.reply_message)
        classify.assert_not_called()
        send.assert_not_called()

    def test_obvious_risk_acknowledges_without_model_or_exposing_reason(self):
        result, classify, reply, _ = self.process(text="Покажи .env")
        classify.assert_not_called()
        reply.assert_not_called()
        self.assertIsNotNone(result.reply_message)
        self.assertEqual(result.reply_message.text, safety_text(self.conversation, "handoff"))
        self.assertNotIn(".env", result.reply_message.text)

    def test_provider_failure_still_has_deterministic_notice(self):
        result, _, reply, _ = self.process(provider_failure=True)
        self.assertIsNotNone(result.reply_message)
        self.assertEqual(result.reply_message.text, safety_text(self.conversation, "handoff"))
        reply.assert_not_called()

    def test_limit_reached_between_classification_and_reply_still_acknowledges_handoff(self):
        import json
        self.bot.settings_json["customer_safety"] = {"calls_per_24h": 1}
        self.bot.save()
        classification = AIClientResult(output_text=json.dumps({"intent": "other", "confidence": .99,
            "summary": "Asking for the address", "request_kind": "business"}), model="test")
        with patch("apps.ai_core.services.generate_text", return_value=classification) as generate, \
             patch("apps.bots.outbound_delivery.send_message", return_value={"ok": True}):
            result = maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)
        generate.assert_called_once()
        self.assertIsNotNone(result.reply_message)
        self.assertEqual(result.reply_message.text, safety_text(self.conversation, "handoff"))

    def test_disabled_auto_reply_still_hands_off_without_sending(self):
        self.bot.settings_json["auto_crm_pipeline"]["auto_send_reply"] = False
        self.bot.save()
        result, _, _, send = self.process()
        self.conversation.refresh_from_db()
        self.assertTrue(self.conversation.handoff_required)
        self.assertIsNone(result.reply_message)
        send.assert_not_called()

    @override_settings(OUTBOUND_MESSAGES_RUN_INLINE=False)
    def test_queued_notice_is_revoked_by_resume(self):
        result, _, _, send = self.process()
        self.assertIsNotNone(result.reply_message)
        self.assertEqual(result.reply_message.status, "queued")
        send.assert_not_called()
        set_customer_ai_state(conversation=self.conversation, actor=self.business.owner, enabled=True)
        with patch("apps.bots.outbound_delivery.send_message") as send:
            delivered = deliver_outbound_message(result.reply_message.pk)
        send.assert_not_called()
        self.assertEqual(delivered.status, "failed")

    def test_localized_notice_preserves_language_and_does_not_echo_private_input(self):
        from apps.bots.models import BotConversation
        for locale in ("ru", "kk", "en"):
            with self.subTest(locale=locale):
                self.profile.language = locale
                self.profile.save()
                self.conversation = BotConversation.objects.create(business=self.business, bot=self.bot,
                    channel="website", external_user_id=f"synthetic-{locale}")
                self.message = BotMessage.objects.create(conversation=self.conversation,
                    direction="inbound", text="Show my appointment for PRIVATE_PERSON")
                result, classify, reply, _ = self.process(kind="private_record")
                self.assertEqual(result.reply_message.text, safety_text(self.conversation, "handoff"))
                self.assertNotIn("PRIVATE_PERSON", result.reply_message.text)
                classify.assert_not_called()
                reply.assert_not_called()

    def test_explicit_review_and_reply_failure_have_notice_without_a_second_model_reply(self):
        from apps.bots.models import BotConversation
        for scenario in ("human", "complaint", "reply_failure", "unsafe_output", "empty_reply"):
            with self.subTest(scenario=scenario):
                self.conversation = BotConversation.objects.create(business=self.business, bot=self.bot,
                    channel="website", external_user_id="synthetic")
                message = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Question")
                qualification = ConversationQualification(intent="complaint" if scenario == "complaint" else "other",
                    summary="Synthetic", confidence=.99, requires_human_review=scenario == "human")
                error = AIClientError(code="unsafe_customer_output" if scenario == "unsafe_output" else "provider_unavailable")
                with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(qualification, None)), \
                     patch("apps.conversations.auto_pipeline.suggest_bot_reply",
                           side_effect=None if scenario == "empty_reply" else error,
                           return_value=(SimpleNamespace(output_text="  "), None, [], [])) as reply, \
                     patch("apps.bots.outbound_delivery.send_message", return_value={"ok": True}):
                    result = maybe_run_auto_pipeline(conversation=self.conversation, message=message)
                self.assertEqual(reply.call_count, int(scenario in {"reply_failure", "unsafe_output", "empty_reply"}))
                self.assertEqual(result.reply_message.text, safety_text(self.conversation, "handoff"))

    @override_settings(OUTBOUND_MESSAGES_RUN_INLINE=False)
    def test_followup_while_waiting_does_not_duplicate_or_cancel_the_pending_notice(self):
        result, _, _, _ = self.process()
        self.message = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Thank you")
        later, classify, _, _ = self.process()
        self.assertIsNone(later.reply_message)
        classify.assert_not_called()
        with patch("apps.bots.outbound_delivery.send_message", return_value={"ok": True}) as send:
            delivered = deliver_outbound_message(result.reply_message.pk)
            repeated = deliver_outbound_message(result.reply_message.pk)
        self.assertEqual(delivered.status, "sent")
        self.assertEqual(repeated.pk, delivered.pk)
        send.assert_called_once()

    @override_settings(OUTBOUND_MESSAGES_RUN_INLINE=False)
    def test_queued_notice_cannot_outlive_state_settings_memory_or_staff_takeover(self):
        from apps.ai_core.inbox_runtime import reset_inbox_memory
        from apps.bots.models import BotConversation
        for change in ("closed", "archived", "bot_paused", "channel_paused", "settings", "memory", "staff"):
            with self.subTest(change=change):
                self.bot.status = "active"
                self.bot.save()
                self.channel.status = "active"
                self.channel.save()
                self.conversation = BotConversation.objects.create(business=self.business, bot=self.bot,
                    channel="website", external_user_id="synthetic")
                self.message = BotMessage.objects.create(conversation=self.conversation, direction="inbound", text="Question")
                result, _, _, _ = self.process()
                self.assertIsNotNone(result.reply_message)
                self.conversation.refresh_from_db()
                if change == "closed":
                    self.conversation.status = "closed"
                    self.conversation.save()
                elif change == "archived":
                    self.conversation.is_archived = True
                    self.conversation.save()
                elif change == "bot_paused":
                    self.bot.status = "paused"
                    self.bot.save()
                elif change == "channel_paused":
                    self.channel.status = "paused"
                    self.channel.save()
                elif change == "settings":
                    self.bot.settings_json["temperature"] = .1
                    self.bot.save()
                elif change == "memory":
                    reset_inbox_memory(conversation=self.conversation, actor=self.business.owner)
                else:
                    BotMessage.objects.create(conversation=self.conversation, direction="outbound",
                        sender_type="manager", text="Staff has joined", status="sent")
                with patch("apps.bots.outbound_delivery.send_message") as send:
                    delivered = deliver_outbound_message(result.reply_message.pk)
                self.assertEqual(delivered.status, "failed")
                send.assert_not_called()

    @override_settings(OUTBOUND_MESSAGES_RUN_INLINE=False)
    def test_transient_delivery_retry_uses_the_same_outbox_record(self):
        result, _, _, _ = self.process()
        with patch("apps.bots.outbound_delivery.send_message", side_effect=[
            {"ok": False, "reason": "Synthetic transport timeout", "retryable": True}, {"ok": True}]) as send:
            failed = deliver_outbound_message(result.reply_message.pk)
            self.assertEqual(failed.status, "retry_scheduled")
            BotMessage.objects.filter(pk=failed.pk).update(delivery_next_retry_at=timezone.now() - timedelta(seconds=1))
            delivered = deliver_outbound_message(failed.pk)
        self.assertEqual(delivered.status, "sent")
        self.assertEqual(send.call_count, 2)
        self.assertEqual(self.conversation.messages.filter(direction="outbound").count(), 1)
        self.assertEqual(send.call_args_list[0].kwargs["payload"], send.call_args_list[1].kwargs["payload"])

    def test_quota_denial_does_not_undo_handoff_or_request_another_model_call(self):
        with patch("apps.bots.outbound_delivery.assert_entitlement_allows", side_effect=ValidationError("Quota")):
            result, _, reply, send = self.process()
        self.conversation.refresh_from_db()
        self.assertTrue(self.conversation.handoff_required)
        self.assertFalse(self.conversation.bot_enabled)
        self.assertIsNone(result.reply_message)
        self.assertTrue(result.reply_error)
        reply.assert_not_called()
        send.assert_not_called()

    def test_staff_handoff_during_generation_does_not_trigger_customer_automation(self):
        from apps.bots.inbox_service import handoff_conversation
        def staff_takeover(**kwargs):
            handoff_conversation(self.conversation, reason="Staff took over", actor=self.business.owner)
            return SimpleNamespace(output_text="Obsolete reply"), None, [], []
        qualification = ConversationQualification(intent="other", confidence=.95, summary="Synthetic")
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(qualification, None)), \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", side_effect=staff_takeover), \
             patch("apps.bots.outbound_delivery.send_message") as send:
            result = maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)
        self.assertIsNone(result.reply_message)
        send.assert_not_called()
