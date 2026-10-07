from types import SimpleNamespace
from unittest.mock import patch

from django.test import TestCase, override_settings
from rest_framework.test import APIClient

from apps.bots import tests_runtime_configuration as fixtures
from apps.bots.customer_safety import safety_handoff, set_customer_ai_state
from apps.bots.models import BotMessage
from apps.bots.safety_state import reserve_call
from apps.conversations.ai_qualification import ConversationQualification
from apps.conversations.auto_pipeline import maybe_run_auto_pipeline


class CustomerRecoveryTests(TestCase):
    def setUp(self):
        fixtures.RuntimeConfigurationTests.setUp(self)
        self.api = APIClient()
        self.url = f"/api/inbox/conversations/{self.conversation.pk}/ai-state/"

    def test_resume_is_authorized_and_preserves_usage_and_history(self):
        from apps.accounts.models import User
        reserve_call(conversation=self.conversation, stage="reply")
        safety_handoff(self.conversation, "off_topic")
        foreign = User.objects.create_user(username="foreign-safety", email="foreign-safety@example.test")
        self.api.force_authenticate(foreign)
        self.assertIn(self.api.post(self.url, {"bot_enabled": True}).status_code, (403, 404))
        self.api.force_authenticate(self.business.owner)
        response = self.api.post(self.url, {"bot_enabled": True})
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["ai_safety"]["calls_used"], 1)
        self.assertFalse(response.data["handoff_required"])
        self.assertTrue(response.data["bot_enabled"])
        self.assertTrue(self.conversation.messages.filter(pk=self.message.pk).exists())

    def test_member_without_ai_permission_cannot_resume(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        user = User.objects.create_user(username="safety-member", email="safety-member@example.test")
        role = BusinessRole.objects.create(business=self.business, name="Inbox only")
        for action in ("view", "update"):
            RolePermission.objects.create(business_role=role, resource="conversations", action=action, scope="business", is_allowed=True)
        BusinessMember.objects.create(business=self.business, user=user, role="operator", business_role=role)
        safety_handoff(self.conversation, "off_topic")
        self.api.force_authenticate(user)
        response = self.api.post(self.url, {"bot_enabled": True})
        self.assertEqual(response.status_code, 403)
        self.conversation.refresh_from_db()
        self.assertTrue(self.conversation.handoff_required)

    def test_budget_limit_cannot_be_cleared_by_state_endpoint(self):
        self.bot.settings_json["customer_safety"] = {"calls_per_24h": 1}
        self.bot.save()
        reserve_call(conversation=self.conversation, stage="reply")
        safety_handoff(self.conversation, "call_limit")
        self.api.force_authenticate(self.business.owner)
        response = self.api.post(self.url, {"bot_enabled": True, "ai_safety_state": {}}, format="json")
        self.assertEqual(response.status_code, 400)
        self.conversation.refresh_from_db()
        self.assertEqual(len(self.conversation.ai_safety_state["calls"]), 1)
        self.assertFalse(self.conversation.bot_enabled)

    def test_pause_then_resume_during_generation_cannot_send_old_response(self):
        def generate(**kwargs):
            set_customer_ai_state(conversation=self.conversation, actor=self.business.owner, enabled=False)
            set_customer_ai_state(conversation=self.conversation, actor=self.business.owner, enabled=True)
            return SimpleNamespace(output_text="Obsolete"), None, [], []
        qualification = ConversationQualification(intent="price_question", confidence=.9, summary="Price")
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(qualification, None)), \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", side_effect=generate), \
             patch("apps.bots.outbound_delivery.send_message") as send:
            maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)
        send.assert_not_called()

    @override_settings(OUTBOUND_MESSAGES_RUN_INLINE=False)
    def test_queued_reply_stays_revoked_after_pause_resume(self):
        from apps.bots.outbound_delivery import deliver_outbound_message
        qualification = ConversationQualification(intent="price_question", confidence=.9, summary="Price")
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(qualification, None)), \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", return_value=(SimpleNamespace(output_text="Old reply"), None, [], [])):
            result = maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)
        self.assertIsNotNone(result.reply_message)
        set_customer_ai_state(conversation=self.conversation, actor=self.business.owner, enabled=False)
        set_customer_ai_state(conversation=self.conversation, actor=self.business.owner, enabled=True)
        with patch("apps.bots.outbound_delivery.send_message") as send:
            delivered = deliver_outbound_message(result.reply_message.pk)
        send.assert_not_called()
        self.assertEqual(delivered.status, "failed")
