from django.test import TestCase, override_settings
from rest_framework.exceptions import NotFound, PermissionDenied

from apps.ai_core import tests as fixtures
from apps.ai_core.conversation_access import create_staff_conversation, memory_access_fingerprint, staff_conversation
from apps.ai_core.conversation_memory import inbox_memory, staff_memory
from apps.ai_core.models import AgentConversation, AgentProfile, AgentTurn, BusinessKnowledgeItem
from apps.bots.lifecycle import activate_bot, create_bot
from apps.bots.models import Bot, BotConversation, BotMessage


@override_settings(AI_PROVIDER="mock", AI_ENABLED=True)
class ConversationMemoryTests(TestCase):
    def setUp(self):
        fixtures.AICoreFoundationTests.setUp(self)
        self.agent = create_bot(validated_data={"business": self.business, "name": "CRM", "scenario": "crm"})
        activate_bot(bot=self.agent)
        self.thread = create_staff_conversation(business=self.business, agent_id=self.agent.pk, user=self.owner)

    def turn(self, sequence, text, **values):
        return AgentTurn.objects.create(conversation=self.thread, sequence=sequence, idempotency_key=str(sequence),
            request_hash="synthetic", message=text, response="Old generated claims must not become facts", status="completed",
            access_fingerprint=memory_access_fingerprint(business=self.business, agent=self.agent, user=self.owner),
            runtime_fingerprint="synthetic", **values)

    def test_old_topic_is_recalled_beyond_recent_window_with_provenance(self):
        first = self.turn(1, "Подготовь встречу по проекту Альтаир", context_json={"question": "Когда провести встречу?"})
        for index in range(2, 35):
            self.turn(index, f"Другой вопрос {index}")
        memory = staff_memory(thread=self.thread, user=self.owner, query="Вернёмся к проекту Альтаир")
        recalled = next(item for item in memory["messages"] if item["source_id"] == f"TURN-{first.pk}")
        self.assertIn("Альтаир", recalled["text"])
        self.assertNotIn("Old generated claims", str(memory))
        self.assertLessEqual(len(memory["messages"]), 16)
        self.thread.refresh_from_db()
        self.assertTrue(self.thread.memory_json["summary"])

    def test_recalled_user_statement_is_citable_without_becoming_a_crm_fact(self):
        from apps.ai_core.grounding import source_catalog, validate_answer
        from apps.ai_core.ai_client import AIClientResult
        import json
        turn = self.turn(1, "Проект Альтаир обсуждаем во вторник")
        memory = staff_memory(thread=self.thread, user=self.owner, query="Альтаир")
        sources = source_catalog({}, [], memory)
        self.assertEqual(sources[0]["id"], f"TURN-{turn.pk}")
        self.assertEqual(sources[0]["authority"], "historical_user_statement_not_current_crm_fact")
        result = AIClientResult(output_text=json.dumps({"answer": "Вы упомянули вторник", "source_ids": [f"TURN-{turn.pk}"], "no_data": False}), model="test", tokens_used=1, provider="test", is_mock=False)
        self.assertEqual(validate_answer(result, sources).sources[0]["id"], f"TURN-{turn.pk}")

    def test_analytics_period_remains_available_for_followup(self):
        period = {"start": "2026-10-01", "end": "2026-10-07"}
        self.turn(1, "Проанализируй выбранный период", plan_json={"intent": "analytics", "steps": [], "period": period})
        memory = staff_memory(thread=self.thread, user=self.owner, query="А прибыль за тот же период?")
        self.assertEqual(memory["pending"]["plan"]["period"], period)

    def test_threads_never_share_memory_even_for_same_employee_agent(self):
        self.turn(1, "PRIVATE_TOPIC")
        separate = create_staff_conversation(business=self.business, agent_id=self.agent.pk, user=self.owner)
        self.assertNotIn("PRIVATE_TOPIC", str(staff_memory(thread=separate, user=self.owner, query="PRIVATE_TOPIC")))
        with self.assertRaises(PermissionDenied):
            staff_memory(thread=self.thread, user=self.other_owner, query="PRIVATE_TOPIC")
        with self.assertRaises(NotFound):
            staff_conversation(conversation_id=self.thread.pk, user=self.other_owner)

    def test_source_disconnect_invalidates_old_extracts_and_cache(self):
        item = BusinessKnowledgeItem.objects.create(business=self.business, bot=self.agent, title="Private", content="OLD_KNOWLEDGE")
        self.turn(1, "OLD_KNOWLEDGE")
        self.assertIn("OLD_KNOWLEDGE", str(staff_memory(thread=self.thread, user=self.owner, query="Old")))
        item.is_active = False
        item.save()
        self.assertNotIn("OLD_KNOWLEDGE", str(staff_memory(thread=self.thread, user=self.owner, query="Old")))
        self.thread.refresh_from_db()
        self.assertNotIn("OLD_KNOWLEDGE", str(self.thread.memory_json))

    def test_tone_change_preserves_memory_but_source_switch_does_not(self):
        self.turn(1, "Keep the conversation")
        profile = AgentProfile.objects.get(bot=self.agent)
        profile.tone = "formal"
        profile.save()
        self.assertTrue(staff_memory(thread=self.thread, user=self.owner, query="conversation")["messages"])
        profile.rules_json["sources"] = ["tasks"]
        profile.save()
        self.assertFalse(staff_memory(thread=self.thread, user=self.owner, query="conversation")["messages"])

    def test_memory_epoch_and_disable_remove_recall_without_deleting_history(self):
        self.turn(1, "Remember")
        self.thread.memory_epoch = 1
        self.thread.save()
        self.assertFalse(staff_memory(thread=self.thread, user=self.owner, query="Remember")["messages"])
        self.assertEqual(self.thread.turns.count(), 1)
        self.turn(2, "New context", memory_epoch=1)
        self.agent.settings_json["memory_enabled"] = False
        self.agent.save()
        self.thread.agent = self.agent
        self.assertFalse(staff_memory(thread=self.thread, user=self.owner, query="context")["messages"])

    def test_inbox_recall_is_per_conversation_and_excludes_undelivered_or_stale_answers(self):
        bot = Bot.objects.create(business=self.business, name="Inbox")
        AgentProfile.objects.create(business=self.business, bot=bot, name="Inbox")
        conversation = BotConversation.objects.create(business=self.business, bot=bot, channel="website")
        other = BotConversation.objects.create(business=self.business, bot=bot, channel="website")
        BotMessage.objects.create(conversation=other, direction="inbound", text="OTHER_CUSTOMER")
        old = BotMessage.objects.create(conversation=conversation, direction="inbound", text="Мой вопрос: Альтаир")
        signature = memory_access_fingerprint(business=self.business, agent=bot)
        for status in ("queued", "failed", "sent"):
            BotMessage.objects.create(conversation=conversation, direction="outbound", status=status,
                text=f"REPLY_{status}", payload_json={"memory_access_fingerprint": signature})
        BotMessage.objects.create(conversation=conversation, direction="outbound", status="sent", text="STALE_REPLY", payload_json={"memory_access_fingerprint": "old"})
        for index in range(20):
            BotMessage.objects.create(conversation=conversation, direction="inbound", text=f"Other topic {index}")
        memory = inbox_memory(conversation=conversation, query="Альтаир")
        self.assertIn(old.pk, [item["id"] for item in memory["messages"]])
        for hidden in ("OTHER_CUSTOMER", "REPLY_queued", "REPLY_failed", "STALE_REPLY"):
            self.assertNotIn(hidden, str(memory))
        preview = BotConversation(business=self.business, bot=bot, channel="website")
        before = AgentConversation.objects.count()
        self.assertEqual(inbox_memory(conversation=preview)["messages"], [])
        self.assertEqual(AgentConversation.objects.count(), before)
