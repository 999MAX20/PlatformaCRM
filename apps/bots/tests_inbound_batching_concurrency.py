from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from types import SimpleNamespace
from unittest import skipUnless
from unittest.mock import patch

from django.db import connection, connections, transaction
from django.test import TransactionTestCase, override_settings

from apps.ai_core.inbox_runtime import run_inbound_once
from apps.ai_core.models import AgentTurn
from apps.bots.inbound_batching import process_batch
from apps.bots.inbox_service import handoff_conversation
from apps.bots.models import BotMessage, InboundMessageBatch
from apps.bots import tests_inbound_batching as fixtures
from apps.conversations.ai_qualification import ConversationQualification


@skipUnless(connection.vendor == "postgresql", "Requires independent PostgreSQL transactions")
@override_settings(AI_ENABLED=True, AI_PROVIDER="mock", CELERY_TASK_ALWAYS_EAGER=True)
class InboundBatchConcurrencyTests(TransactionTestCase):
    message = fixtures.InboundBatchTests.message
    enqueue = fixtures.InboundBatchTests.enqueue
    due = fixtures.InboundBatchTests.due

    def setUp(self):
        fixtures.InboundBatchTests.setUp(self)
        self.conversation.external_user_id = "batch-concurrency-recipient"
        self.conversation.save(update_fields=["external_user_id"])

    def worker(self):
        connections.close_all()
        try:
            return process_batch(self.conversation.pk)
        finally:
            connections.close_all()

    def qualification(self):
        return ConversationQualification(intent="price_question", confidence=.99, summary="Price"), None

    def test_two_workers_admit_one_due_group_and_replay_without_effects(self):
        message = self.enqueue()
        self.due()
        ready = Barrier(2)

        def admit(**kwargs):
            # Both workers have read the pending batch and released its read transaction.
            ready.wait(timeout=30)
            return run_inbound_once(**kwargs)

        with patch("apps.bots.inbound_batching.run_inbound_once", side_effect=admit), \
             patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=self.qualification()) as classify, \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", return_value=(SimpleNamespace(output_text="5000 KZT"), None, [], [])) as reply, \
             patch("apps.bots.outbound_delivery.send_message", return_value={"ok": True, "provider_message_id": "synthetic"}) as send:
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(self.worker) for _ in range(2)]
                results = [future.result(timeout=60) for future in futures]
            self.assertEqual(len(results), 2)
            self.assertIsNone(process_batch(self.conversation.pk))
        self.assertEqual(AgentTurn.objects.count(), 1)
        self.assertEqual(AgentTurn.objects.get().idempotency_key, f"message:{message.pk}")
        self.assertFalse(InboundMessageBatch.objects.get().pending)
        self.assertEqual(self.conversation.messages.filter(direction="outbound").count(), 1)
        classify.assert_called_once()
        reply.assert_called_once()
        send.assert_called_once()

    def run_with_committed_intervention(self, intervene):
        self.enqueue()
        self.due()
        generating, release = Event(), Event()

        def classify(**kwargs):
            generating.set()
            if not release.wait(timeout=30):
                raise AssertionError("Intervention did not release generation")
            return self.qualification()

        with patch("apps.conversations.auto_pipeline.qualify_conversation", side_effect=classify), \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply") as reply, \
             patch("apps.conversations.auto_pipeline.run_conversation_pipeline") as actions, \
             patch("apps.bots.outbound_delivery.send_message") as send:
            with ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(self.worker)
                try:
                    self.assertTrue(generating.wait(timeout=30))
                    intervene()
                finally:
                    release.set()
                result = future.result(timeout=60)
            reply.assert_not_called()
            actions.assert_not_called()
            send.assert_not_called()
        self.assertFalse(self.conversation.messages.filter(direction="outbound").exclude(sender_type="manager").exists())
        return result

    def test_new_inbound_survives_old_group_completion_and_runs_once(self):
        self.run_with_committed_intervention(lambda: self.enqueue("Different request"))
        batch = InboundMessageBatch.objects.get()
        self.assertTrue(batch.pending)
        latest_id = self.conversation.messages.filter(direction="inbound").order_by("-pk").first().pk
        self.assertEqual(batch.last_message_id, latest_id)
        self.due()
        with patch("apps.conversations.auto_pipeline.qualify_conversation", return_value=self.qualification()) as classify, \
             patch("apps.conversations.auto_pipeline.suggest_bot_reply", return_value=(SimpleNamespace(output_text="5000 KZT"), None, [], [])), \
             patch("apps.bots.outbound_delivery.send_message", return_value={"ok": True}) as send:
            process_batch(self.conversation.pk)
            self.assertIsNone(process_batch(self.conversation.pk))
        classify.assert_called_once()
        send.assert_called_once()
        self.assertEqual(AgentTurn.objects.count(), 2)
        self.assertFalse(InboundMessageBatch.objects.get().pending)
        self.assertEqual(self.conversation.messages.filter(direction="outbound").count(), 1)

    def test_committed_staff_handoff_blocks_inflight_effects(self):
        def intervene():
            with transaction.atomic():
                handoff_conversation(self.conversation, actor=self.owner)
                BotMessage.objects.create(conversation=self.conversation, direction="outbound", sender_type="manager", text="I'll help")

        self.run_with_committed_intervention(intervene)
        self.conversation.refresh_from_db()
        self.assertTrue(self.conversation.handoff_required)
        self.assertFalse(self.conversation.bot_enabled)
        self.assertFalse(InboundMessageBatch.objects.get().pending)
        self.assertEqual(AgentTurn.objects.count(), 1)
        self.assertIsNone(process_batch(self.conversation.pk))
