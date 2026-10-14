from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone

from apps.bots import tests_runtime_configuration as fixtures
from apps.bots.customer_safety import set_customer_ai_state, safety_handoff
from apps.bots.handoff_recovery import resume_due_conversations, schedule_after_staff_delivery
from apps.bots.inbox_service import handoff_conversation, register_bot_message, send_outbound_message, close_conversation
from apps.bots.models import BotMessage
from apps.core.models import AuditLog


class HandoffRecoveryTests(TestCase):
    def setUp(self):
        fixtures.RuntimeConfigurationTests.setUp(self)
        self.actor = self.business.owner
        self.start = timezone.now()
        with patch("django.utils.timezone.now", return_value=self.start):
            handoff_conversation(self.conversation, actor=self.actor)

    def reply(self, minutes=5, ok=True):
        at = self.start + timedelta(minutes=minutes)
        with patch("django.utils.timezone.now", return_value=at), patch(
            "apps.bots.outbound_delivery.send_message", return_value={"ok": ok, "retryable": False}
        ):
            return send_outbound_message(self.conversation, "Staff answer", self.actor)

    def incoming(self, minutes=10):
        with patch("django.utils.timezone.now", return_value=self.start + timedelta(minutes=minutes)):
            msg = BotMessage.objects.create(conversation=self.conversation, direction="inbound", sender_type="client", text="More help")
            register_bot_message(msg)
        return msg

    def due(self, minutes=65):
        return resume_due_conversations(now=self.start + timedelta(minutes=minutes))

    def test_hour_boundary_repeat_and_no_outbound(self):
        self.reply()
        before = self.conversation.messages.count()
        self.assertEqual(self.due(64), 0)
        with patch("apps.bots.outbound_delivery.send_message") as send:
            self.assertEqual(self.due(), 1)
            self.assertEqual(self.due(), 0)
        send.assert_not_called()
        self.conversation.refresh_from_db()
        self.assertTrue(self.conversation.bot_enabled)
        self.assertFalse(self.conversation.handoff_required)
        self.assertEqual(self.conversation.messages.count(), before)
        self.assertEqual(AuditLog.objects.filter(metadata__automatic_recovery=True).count(), 1)

    def test_unanswered_and_failed_reply_stay_with_human(self):
        self.assertEqual(self.due(), 0)
        self.reply(ok=False)
        self.assertEqual(self.due(120), 0)
        self.conversation.refresh_from_db()
        self.assertIsNone(self.conversation.ai_resume_at)

    def test_new_inbound_requires_new_successful_answer(self):
        self.reply()
        self.incoming()
        self.assertEqual(self.due(120), 0)
        self.reply(minutes=125)
        self.assertEqual(self.due(184), 0)
        self.assertEqual(self.due(185), 1)

    def test_new_staff_reply_moves_deadline_and_system_notice_does_not(self):
        self.reply()
        self.reply(minutes=30)
        BotMessage.objects.create(conversation=self.conversation, direction="outbound", sender_type="system", status="sent", text="Internal")
        self.assertEqual(self.due(65), 0)
        self.assertEqual(self.due(90), 1)

    def test_manual_pause_while_already_disabled_cancels_timer(self):
        self.reply()
        set_customer_ai_state(conversation=self.conversation, actor=self.actor, enabled=False)
        self.reply(minutes=20)
        self.assertEqual(self.due(120), 0)
        self.conversation.refresh_from_db()
        self.assertIsNone(self.conversation.handoff_resume_started_at)

    def test_safety_and_automatic_review_do_not_arm_timer(self):
        self.reply()
        safety_handoff(self.conversation, "uncertain")
        self.reply(minutes=20)
        self.assertEqual(self.due(120), 0)
        self.conversation.refresh_from_db()
        self.assertIsNone(self.conversation.ai_resume_at)

    def test_readiness_failure_cancels_without_later_surprise(self):
        self.reply()
        self.channel.status = "paused"
        self.channel.save()
        self.assertEqual(self.due(), 0)
        self.channel.status = "active"
        self.channel.save()
        self.assertEqual(self.due(120), 0)

    def test_actor_deactivated_cannot_resume(self):
        self.reply()
        self.actor.is_active = False
        self.actor.save()
        self.assertEqual(self.due(), 0)

    def test_close_and_reopen_cannot_revive_timer(self):
        self.reply()
        close_conversation(self.conversation, actor=self.actor)
        self.assertEqual(self.due(), 0)

    def test_resume_revokes_old_queued_reply_and_preserves_usage(self):
        self.reply()
        self.conversation.refresh_from_db()
        calls = [{"at": self.start.timestamp(), "stage": "reply"}]
        self.conversation.ai_safety_state = {"calls": calls}
        self.conversation.save(update_fields=["ai_safety_state"])
        old = BotMessage.objects.create(conversation=self.conversation, direction="outbound", sender_type="bot", status="queued", text="Stale")
        self.assertEqual(self.due(), 1)
        old.refresh_from_db()
        self.assertEqual(old.status, "failed")
        self.conversation.refresh_from_db()
        self.assertEqual(self.conversation.ai_safety_state["calls"], calls)

    def test_audit_failure_rolls_back_resume(self):
        self.reply()
        with patch("apps.core.audit.write_actor_audit_log", side_effect=RuntimeError("test rollback")):
            with self.assertRaises(RuntimeError):
                self.due()
        self.conversation.refresh_from_db()
        self.assertFalse(self.conversation.bot_enabled)
        self.assertIsNotNone(self.conversation.ai_resume_at)
        self.assertEqual(self.due(), 1)

    def test_stale_delivery_cannot_answer_newer_customer_message(self):
        reply = self.reply()
        self.incoming()
        schedule_after_staff_delivery(reply)
        self.assertEqual(self.due(120), 0)

    def test_pending_reply_blocks_timer_until_delivery(self):
        from apps.bots.outbound_delivery import _finish_delivery
        self.reply()
        with patch("django.utils.timezone.now", return_value=self.start + timedelta(minutes=20)):
            pending = BotMessage.objects.create(conversation=self.conversation, direction="outbound", sender_type="manager",
                text="Pending reply", status="queued", payload_json={"sent_by_user_id": self.actor.pk})
            register_bot_message(pending, actor=self.actor)
        self.assertEqual(self.due(100), 0)
        with patch("django.utils.timezone.now", return_value=self.start + timedelta(minutes=110)):
            _finish_delivery(pending, result={"ok": True})
        self.assertEqual(self.due(169), 0)
        self.assertEqual(self.due(170), 1)

    def test_old_episode_reply_and_legacy_handoff_remain_stopped(self):
        self.conversation.refresh_from_db()
        self.conversation.handoff_resume_started_at = None
        self.conversation.save(update_fields=["handoff_resume_started_at"])
        self.reply()
        self.assertEqual(self.due(120), 0)
        # A manual handoff must not convert an existing protected stop to ordinary.
        handoff_conversation(self.conversation, reason="Operator handling", actor=self.actor)
        self.reply(minutes=30)
        self.assertEqual(self.due(120), 0)

    def member(self):
        from apps.accounts.models import User
        from apps.businesses.models import BusinessMember, BusinessRole, RolePermission
        user = User.objects.create_user(username="recovery-member", email="recovery-member@example.test")
        role = BusinessRole.objects.create(business=self.business, name="Recovery operator")
        for resource, action in (("conversations", "view"), ("conversations", "update"), ("ai_assistant", "suggest")):
            RolePermission.objects.create(business_role=role, resource=resource, action=action, scope="business", is_allowed=True)
        member = BusinessMember.objects.create(business=self.business, user=user, role="operator", business_role=role)
        return user, member, role

    def test_revoked_membership_blocks_scheduled_recovery(self):
        self.actor, member, _ = self.member()
        self.reply()
        member.is_active = False
        member.save()
        self.assertEqual(self.due(), 0)
        self.conversation.refresh_from_db()
        self.assertFalse(self.conversation.bot_enabled)
        self.assertIsNone(self.conversation.handoff_resume_started_at)

    def test_revoked_ai_permission_blocks_scheduled_recovery(self):
        self.actor, _, role = self.member()
        self.reply()
        role.permissions.filter(resource="ai_assistant").update(is_allowed=False)
        self.assertEqual(self.due(), 0)

    def test_api_projection_and_stop_are_scoped_and_readonly(self):
        from apps.accounts.models import User
        from rest_framework.test import APIClient
        api = APIClient()
        self.reply()
        url = f"/api/inbox/conversations/{self.conversation.pk}/"
        foreign = User.objects.create_user(username="recovery-foreign", email="recovery-foreign@example.test")
        api.force_authenticate(foreign)
        self.assertEqual(api.get(url).status_code, 404)
        self.assertEqual(api.post(url + "ai-state/", {"bot_enabled": False}).status_code, 404)
        api.force_authenticate(self.actor)
        data = api.get(url).data
        self.assertIsNotNone(data["ai_resume_at"])
        self.assertNotIn("ai_resume_actor", data)
        self.assertEqual(api.patch(url, {"ai_resume_at": self.start.isoformat()}).status_code, 405)
        stopped = api.post(url + "ai-state/", {"bot_enabled": False})
        self.assertEqual(stopped.status_code, 200, stopped.data)
        self.assertIsNone(stopped.data["ai_resume_at"])
        self.assertEqual(self.due(120), 0)

    def test_staff_without_ai_permission_cannot_arm_or_cancel_timer(self):
        from rest_framework.test import APIClient
        user, _, role = self.member()
        role.permissions.filter(resource="ai_assistant").update(is_allowed=False)
        self.reply()
        api = APIClient()
        api.force_authenticate(user)
        self.assertEqual(api.post(f"/api/inbox/conversations/{self.conversation.pk}/ai-state/", {"bot_enabled": False}).status_code, 403)
        self.actor = user
        self.reply(minutes=20)
        self.assertEqual(self.due(120), 0)

    def test_hour_does_not_reset_call_budget_or_override_review(self):
        self.reply()
        self.conversation.refresh_from_db()
        self.conversation.ai_safety_state = {"calls": [{"at": timezone.now().timestamp(), "stage": "reply"}]}
        self.conversation.save(update_fields=["ai_safety_state"])
        self.bot.settings_json["customer_safety"] = {"calls_per_24h": 1}
        self.bot.save()
        self.assertEqual(self.due(), 0)
        self.conversation.refresh_from_db()
        self.assertEqual(len(self.conversation.ai_safety_state["calls"]), 1)

    def test_only_next_inbound_can_run_ai_and_old_inbound_is_not_replayed(self):
        from types import SimpleNamespace
        from apps.conversations.auto_pipeline import maybe_run_auto_pipeline
        from apps.conversations.ai_qualification import ConversationQualification
        # A received request handled while stopped retains its durable decision.
        with patch("apps.conversations.auto_pipeline.qualify_conversation") as qualify:
            maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)
        qualify.assert_not_called()
        self.reply()
        self.assertEqual(self.due(), 1)
        with patch("apps.conversations.auto_pipeline.qualify_conversation") as qualify:
            maybe_run_auto_pipeline(conversation=self.conversation, message=self.message)
        qualify.assert_not_called()
        new = self.incoming(minutes=70)
        qualification = ConversationQualification(intent="price_question", confidence=.95, summary="New question")
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=(qualification, None)) as qualify, \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", return_value=(SimpleNamespace(output_text="New answer"), None, [], [])), \
             patch("apps.bots.outbound_delivery.send_message", return_value={"ok": True}):
            result = maybe_run_auto_pipeline(conversation=self.conversation, message=new)
        qualify.assert_called_once()
        self.assertIsNotNone(result.reply_message)
        self.assertEqual(result.reply_message.status, "sent")


@skipUnlessDBFeature("has_select_for_update")
class HandoffRecoveryConcurrencyTests(TransactionTestCase):
    setUp = HandoffRecoveryTests.setUp
    reply = HandoffRecoveryTests.reply

    def test_two_workers_resume_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import close_old_connections
        from apps.bots.handoff_recovery import resume_due_conversation
        from apps.bots.models import BotConversation
        self.reply()
        barrier = Barrier(2)
        def run():
            close_old_connections()
            try:
                candidate = BotConversation.objects.get(pk=self.conversation.pk)
                barrier.wait(timeout=10)
                return resume_due_conversation(candidate, now=self.start + timedelta(minutes=65))
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(lambda _: run(), range(2)))
        self.assertEqual(sum(results), 1)
        self.assertEqual(AuditLog.objects.filter(metadata__automatic_recovery=True).count(), 1)

    def test_inbound_committed_while_timer_waits_keeps_human_control(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Event
        from django.db import close_old_connections, transaction
        from apps.bots.handoff_recovery import resume_due_conversation
        from apps.bots.safety_state import _locked
        self.reply()
        started = Event()
        def run():
            close_old_connections()
            try:
                started.set()
                return resume_due_conversation(self.conversation, now=self.start + timedelta(minutes=65))
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=1) as pool:
            with transaction.atomic():
                current = _locked(self.conversation)
                future = pool.submit(run)
                self.assertTrue(started.wait(timeout=10))
                with patch("django.utils.timezone.now", return_value=self.start + timedelta(minutes=64)):
                    incoming = BotMessage.objects.create(conversation=current, direction="inbound", sender_type="client", text="Still waiting")
                    register_bot_message(incoming)
            self.assertFalse(future.result(timeout=15))
        self.conversation.refresh_from_db()
        self.assertFalse(self.conversation.bot_enabled)
