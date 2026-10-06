from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.utils import timezone
from rest_framework.test import APIClient

from apps.ai_core.models import AgentProfile, AIJob, AIToolCallLog, ApprovalRequest
from apps.ai_core.services import process_ai_job
from apps.automations.models import AutomationRule, AutomationRun
from apps.automations.engine import process_automation_run
from apps.bots.deletion import delete_agent
from apps.bots.lifecycle import activate_bot, ensure_bot_channel
from apps.bots.models import Bot, BotChannel, BotConversation, BotMessage
from apps.businesses.models import Business, BusinessMember
from apps.core.domain_errors import InvalidTransition
from apps.core.models import AuditLog


class AgentDeletionTests(TestCase):
    def setUp(self):
        self.owner = get_user_model().objects.create_user(username="delete-owner", email="delete-owner@example.test")
        self.business = Business.objects.create(owner=self.owner, name="Delete", slug="delete")
        BusinessMember.objects.create(business=self.business, user=self.owner, role="owner")
        self.api = APIClient()
        self.api.force_authenticate(self.owner)

    def create(self, scenario="inbox"):
        response = self.api.post("/api/bots/", {"business": self.business.pk, "name": "Delete me", "scenario": scenario}, format="json")
        self.assertEqual(response.status_code, 201, response.data)
        return Bot.objects.get(pk=response.data["id"])

    def test_delete_stops_conversation_turn_and_preserves_its_history(self):
        from apps.ai_core.conversation_access import create_staff_conversation
        from apps.ai_core.conversation_state import start_turn
        from apps.ai_core.models import AgentTurn
        bot = self.create("crm")
        activate_bot(bot=bot)
        thread = create_staff_conversation(business=self.business, agent_id=bot.pk, user=self.owner)
        turn, job = start_turn(conversation_id=thread.pk, user=self.owner, message="Create a task", idempotency_key="delete-test")
        delete_agent(bot=bot, actor=self.owner)
        turn.refresh_from_db(); job.refresh_from_db()
        self.assertEqual(turn.status, AgentTurn.Statuses.CANCELLED)
        self.assertEqual(job.status, AIJob.Statuses.FAILED)
        self.assertEqual(turn.message, "Create a task")

    def test_inbox_delete_preserves_history_stops_work_and_hides_configuration(self):
        bot = self.create()
        other = self.create()
        profile = AgentProfile.objects.create(bot=bot, business=self.business, name="Settings")
        channel = BotChannel.objects.create(bot=bot, channel="website", status="active")
        conversation = BotConversation.objects.create(bot=bot, business=self.business, channel="website")
        incoming = BotMessage.objects.create(conversation=conversation, direction="inbound", text="Keep history")
        outgoing = BotMessage.objects.create(conversation=conversation, direction="outbound", sender_type="bot", status="queued")
        rule = AutomationRule.objects.create(business=self.business, name="Agent follow-up", trigger_type="bot_message_received", is_active=True)
        run = AutomationRun.objects.create(business=self.business, rule=rule, trigger_type=rule.trigger_type,
            entity_type="BotConversation", entity_id=str(conversation.pk), status="waiting", run_after=timezone.now())
        unrelated = AutomationRun.objects.create(business=self.business, rule=rule, trigger_type=rule.trigger_type, status="pending")
        self.assertEqual(self.api.delete(f"/api/bots/{bot.pk}/").status_code, 204)
        self.assertFalse(Bot.objects.filter(pk=bot.pk).exists())
        self.assertTrue(Bot.all_objects.get(pk=bot.pk).is_deleted)
        self.assertTrue(Bot.objects.filter(pk=other.pk).exists())
        for obj in (profile, channel, conversation, outgoing, run, unrelated):
            obj.refresh_from_db()
        self.assertFalse(profile.is_active)
        self.assertEqual(channel.status, "paused")
        self.assertFalse(conversation.bot_enabled)
        self.assertEqual(outgoing.status, "failed")
        self.assertTrue(BotMessage.objects.filter(pk=incoming.pk, text="Keep history").exists())
        self.assertEqual(run.status, "cancelled")
        self.assertEqual(process_automation_run(run.pk).status, "cancelled")
        AutomationRun.objects.filter(pk=run.pk).update(status="pending", run_after=timezone.now())
        self.assertEqual(process_automation_run(run.pk).status, "cancelled")
        self.assertEqual(unrelated.status, "pending")
        for url in (f"/api/bots/{bot.pk}/", f"/api/bot-channels/{channel.pk}/", f"/api/ai/agent-profiles/{profile.pk}/"):
            self.assertEqual(self.api.get(url).status_code, 404)
        self.assertEqual(self.api.get(f"/api/bot-conversations/{conversation.pk}/").status_code, 200)
        self.assertEqual(self.api.post(f"/api/bots/{bot.pk}/activate/").status_code, 404)
        self.assertEqual(self.api.get(f"/api/public/website-chat/{channel.public_token}/").status_code, 403)
        with self.assertRaises(InvalidTransition):
            activate_bot(bot=bot)  # stale object cannot resurrect the agent
        with self.assertRaises(InvalidTransition):
            ensure_bot_channel(bot=bot, channel_type="telegram")
        count = AuditLog.objects.filter(action="delete", entity_id=str(bot.pk)).count()
        delete_agent(bot=bot, actor=self.owner)
        self.assertEqual(AuditLog.objects.filter(action="delete", entity_id=str(bot.pk)).count(), count)

    def test_crm_delete_cancels_jobs_and_commands_and_allows_replacement(self):
        bot = self.create("crm")
        job = AIJob.objects.create(business=self.business, user=self.owner, prompt_type="crm_assistant", idempotency_key="delete-job",
            input_json={"runtime_context": {"_agent": {"agent_id": bot.pk}}})
        log = AIToolCallLog.objects.create(business=self.business, user=self.owner, tool_name="crm_create", input_json={"_agent": {"agent_id": bot.pk}})
        approval = ApprovalRequest.objects.create(business=self.business, requested_by=self.owner, action_type="crm_create", ai_tool_call_log=log)
        delete_agent(bot=bot, actor=self.owner)
        for obj in (job, log, approval):
            obj.refresh_from_db()
        self.assertEqual(job.status, "failed")
        self.assertEqual(log.status, "rejected")
        self.assertEqual(approval.status, "rejected")
        with patch("apps.ai_core.services.generate_text") as provider:
            self.assertEqual(process_ai_job(job.pk).status, "failed")
            provider.assert_not_called()
        for extra in ({"agent": bot.pk}, {}):
            self.assertEqual(self.api.get("/api/ai/crm/read/", {"business": self.business.pk, "entity": "tasks", **extra}).status_code, 403)
        self.assertEqual(self.api.get("/api/ai/agents/", {"business": self.business.pk}).data, [])
        replacement = self.create("crm")
        self.assertNotEqual(replacement.pk, bot.pk)
        self.assertEqual(self.api.get("/api/ai/crm/read/", {"business": self.business.pk, "entity": "tasks", "agent": bot.pk}).status_code, 403)

    def test_delete_is_tenant_scoped_and_manager_denied(self):
        bot = self.create()
        member = get_user_model().objects.create_user(username="delete-manager", email="delete-manager@example.test")
        BusinessMember.objects.create(business=self.business, user=member, role="manager")
        self.api.force_authenticate(member)
        self.assertIn(self.api.delete(f"/api/bots/{bot.pk}/").status_code, (403, 404))
        foreign = get_user_model().objects.create_user(username="delete-foreign", email="delete-foreign@example.test")
        self.api.force_authenticate(foreign)
        self.assertIn(self.api.delete(f"/api/bots/{bot.pk}/").status_code, (403, 404))
        self.assertTrue(Bot.objects.filter(pk=bot.pk).exists())

    def test_failure_rolls_back_all_changes_and_marker_cannot_be_forged(self):
        bot = self.create()
        with patch("apps.bots.deletion.write_actor_audit_log", side_effect=RuntimeError("audit unavailable")):
            with self.assertRaises(RuntimeError):
                delete_agent(bot=bot, actor=self.owner)
        self.assertTrue(Bot.objects.filter(pk=bot.pk).exists())
        response = self.api.patch(f"/api/bots/{bot.pk}/", {"settings_json": {"_deleted_at": "fake"}}, format="json")
        self.assertEqual(response.status_code, 400)
