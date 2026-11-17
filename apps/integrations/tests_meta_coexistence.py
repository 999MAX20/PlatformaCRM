from copy import deepcopy
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.businesses.models import Business
from apps.bots.models import Bot, BotChannel, BotConversation, BotMessage
from apps.integrations.models import BusinessEvent, WhatsAppCoexistenceEvent, WhatsAppCoexistenceSync
from apps.integrations.whatsapp.coexistence_events import enqueue_event, prepare_event, process_event
from apps.integrations.whatsapp_routing import VerifiedWhatsAppWebhook


class MetaCoexistenceImportTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(username="coexistence")
        self.business = Business.objects.create(owner=self.user, name="Coexistence", slug="coexistence")
        self.bot = Bot.objects.create(business=self.business, name="Coexistence")
        self.channel = BotChannel.objects.create(bot=self.bot, channel="whatsapp", status="active", external_id="phone",
            config_json={"phone_number_id": "phone", "business_account_id": "waba", "display_phone_number": "+77010000000",
                         "provider_mode": "meta_cloud", "onboarding_mode": "coexistence", "setup_revision": "revision"})
        self.sync = WhatsAppCoexistenceSync.objects.create(channel=self.channel, setup_revision="revision", phone_number_id="phone", waba_id="waba")
        self.timestamp = str(int((timezone.now() - timezone.timedelta(hours=1)).timestamp()))
        self.message = {"id": "wamid.test", "timestamp": self.timestamp, "from": "77012223344", "type": "text", "text": {"body": "Historical question"}}

    def history(self, *messages, progress=100):
        return {"history": [{"metadata": {"phase": 0, "chunk_order": 1, "progress": progress},
                             "threads": [{"id": "77012223344", "messages": list(messages or (self.message,))}]}]}

    def process(self, field, payload):
        event = enqueue_event(self.sync, field, payload)
        process_event(event.pk)
        event.refresh_from_db()
        return event

    def test_history_import_is_idempotent_and_does_not_open_window_or_notify(self):
        with patch("apps.bots.inbox_service.register_bot_message") as register:
            self.process("history", self.history())
            self.process("history", self.history())
        self.assertEqual(BotMessage.objects.count(), 1)
        self.assertEqual(WhatsAppCoexistenceEvent.objects.count(), 1)
        conversation = BotConversation.objects.get()
        self.assertIsNone(conversation.last_inbound_at)
        self.assertEqual(conversation.unread_count, 0)
        self.assertFalse(conversation.bot_enabled)
        self.assertFalse(BusinessEvent.objects.exists())
        register.assert_not_called()
        self.assertEqual(BotMessage.objects.get().text, "Historical question")

    def test_old_history_does_not_replace_live_last_message_or_window(self):
        now = timezone.now()
        conversation = BotConversation.objects.create(business=self.business, bot=self.bot, channel="whatsapp",
            external_user_id="77012223344", last_message_at=now, last_inbound_at=now, unread_count=2)
        self.process("history", self.history())
        conversation.refresh_from_db()
        self.assertEqual((conversation.last_message_at, conversation.last_inbound_at, conversation.unread_count), (now, now, 2))

    def test_history_outgoing_is_not_enqueued_and_media_update_is_not_new_inbound(self):
        outgoing = {**self.message, "from": "77010000000", "type": "media_placeholder", "history_context": {"status": "sent"}}
        self.process("history", self.history(outgoing))
        media = {**outgoing, "type": "image", "image": {"id": "asset", "caption": "An image"}}
        self.process("history", {"messages": [media]})
        message = BotMessage.objects.get()
        self.assertEqual((message.direction, message.status, message.delivery_attempts), ("outbound", "sent", 0))
        self.assertEqual(message.text, "An image")
        self.assertIsNone(message.conversation.last_inbound_at)

    def test_historical_pending_and_failed_messages_are_never_resent(self):
        from apps.bots.outbound_delivery import retry_outbound_message
        for receipt, status in (("pending", "delivery_unknown"), ("error", "failed"), ("read", "sent")):
            with self.subTest(receipt=receipt):
                outgoing = {**self.message, "id": "history-" + receipt, "from": "77010000000", "history_context": {"status": receipt}}
                self.process("history", self.history(outgoing))
                message = BotMessage.objects.get(external_message_id=outgoing["id"])
                self.assertEqual(message.status, status)
                with self.assertRaises(ValidationError):
                    retry_outbound_message(message, actor=self.user)
                message.refresh_from_db()
                self.assertEqual(message.delivery_attempts, 0)

    def test_history_declined_is_recorded_without_fabricated_completion(self):
        self.process("history", {"history": [{"errors": [{"code": 2593109}]}]})
        self.sync.refresh_from_db()
        self.assertEqual(self.sync.state, "declined")
        self.assertFalse(BotMessage.objects.exists())

    def test_live_echo_overlapping_history_still_hands_off_without_duplicate(self):
        outgoing = {**self.message, "from": "77010000000", "to": "77012223344"}
        self.process("history", self.history(outgoing))
        conversation = BotConversation.objects.get()
        queued = BotMessage.objects.create(conversation=conversation, direction="outbound", sender_type="ai", status="queued", text="Pending")
        self.process("smb_message_echoes", {"message_echoes": [outgoing]})
        queued.refresh_from_db()
        conversation.refresh_from_db()
        self.assertEqual(queued.status, "cancelled")
        self.assertTrue(conversation.handoff_required)
        self.assertEqual(BotMessage.objects.filter(external_message_id=outgoing["id"]).count(), 1)

    def test_media_before_history_waits_and_is_requeued_after_parent_arrives(self):
        media = {**self.message, "type": "image", "image": {"id": "asset", "caption": "Image caption"}}
        event = self.process("history", {"messages": [media]})
        self.assertEqual(event.status, "awaiting_history")
        with patch("apps.integrations.tasks.process_whatsapp_coexistence_event.delay") as queue, self.captureOnCommitCallbacks(execute=True):
            self.process("history", self.history({**self.message, "type": "media_placeholder"}))
        self.assertIn(event.pk, [call.args[0] for call in queue.call_args_list])
        process_event(event.pk)
        self.assertEqual(BotMessage.objects.get().text, "Image caption")

    def test_invalid_later_history_rolls_back_whole_event(self):
        invalid = {**self.message, "id": "invalid", "from": "77019999999"}
        with self.assertRaises(ValidationError):
            self.process("history", self.history(self.message, invalid))
        self.assertFalse(BotMessage.objects.exists())

    def test_old_revision_does_not_import_into_reconnected_channel(self):
        self.channel.config_json["setup_revision"] = "new"
        self.channel.save()
        event = self.process("history", self.history())
        self.assertEqual(event.status, "obsolete")
        self.assertFalse(BotMessage.objects.exists())

    def test_event_requires_meta_signature_and_matching_waba(self):
        portion = {"entry": [{"id": "waba", "changes": [{"field": "history", "value": self.history()}]}]}
        with self.assertRaises(PermissionDenied):
            prepare_event(self.channel, portion, VerifiedWhatsAppWebhook(mode="channel"))
        altered = deepcopy(portion)
        altered["entry"][0]["id"] = "other-waba"
        with self.assertRaises(PermissionDenied):
            prepare_event(self.channel, altered, VerifiedWhatsAppWebhook(mode="meta"))
        self.assertEqual(prepare_event(self.channel, portion, VerifiedWhatsAppWebhook(mode="meta"))[0], self.sync)

    def test_echo_is_staff_reply_and_cancels_pending_ai_without_opening_window(self):
        conversation = BotConversation.objects.create(business=self.business, bot=self.bot, channel="whatsapp", external_user_id="77012223344")
        queued = BotMessage.objects.create(conversation=conversation, direction="outbound", sender_type="ai", status="queued", text="Pending")
        echo = {**self.message, "from": "77010000000", "to": "77012223344"}
        with patch("apps.bots.inbox_service.register_bot_message"):
            self.process("smb_message_echoes", {"message_echoes": [echo]})
            self.process("smb_message_echoes", {"message_echoes": [echo]})
        conversation.refresh_from_db()
        queued.refresh_from_db()
        self.assertFalse(conversation.bot_enabled)
        self.assertTrue(conversation.handoff_required)
        self.assertIsNone(conversation.last_inbound_at)
        self.assertEqual(queued.status, "cancelled")
        self.assertEqual(conversation.messages.filter(external_message_id="wamid.test").count(), 1)

    def test_history_media_webhook_is_queued_instead_of_opening_inbound_window(self):
        from apps.integrations.whatsapp.batches import process_whatsapp_webhook
        value = {"metadata": {"phone_number_id": "phone"}, "messages": [self.message]}
        payload = {"entry": [{"id": "waba", "changes": [{"field": "history", "value": value}]}]}
        with patch("apps.integrations.tasks.process_whatsapp_coexistence_event.delay") as queue, self.captureOnCommitCallbacks(execute=True):
            result = process_whatsapp_webhook(payload, VerifiedWhatsAppWebhook(mode="meta"))
        self.assertEqual(result["business_app_events"], 1)
        self.assertEqual(queue.call_count, 1)
        self.assertFalse(BotMessage.objects.exists())

    def test_wrong_waba_in_later_change_prevents_first_history_queue(self):
        from apps.integrations.whatsapp.batches import process_whatsapp_webhook
        value = {"metadata": {"phone_number_id": "phone"}, **self.history()}
        payload = {"entry": [{"id": waba, "changes": [{"field": "history", "value": value}]} for waba in ("waba", "other")]}
        with self.assertRaises(PermissionDenied):
            process_whatsapp_webhook(payload, VerifiedWhatsAppWebhook(mode="meta"))
        self.assertFalse(WhatsAppCoexistenceEvent.objects.exists())

    @patch("apps.integrations.whatsapp.coexistence_sync.get_whatsapp_access_token", return_value="synthetic")
    @patch("apps.integrations.whatsapp.coexistence_sync.graph_call")
    def test_sync_requests_contacts_then_history_once(self, graph, token):
        from apps.integrations.whatsapp.coexistence_sync import start_sync
        graph.side_effect = [{"request_id": "contacts"}, {"request_id": "history"}]
        start_sync(self.sync.pk)
        start_sync(self.sync.pk)
        self.assertEqual([call.kwargs["body"]["sync_type"] for call in graph.call_args_list], ["smb_app_state_sync", "history"])
        self.sync.refresh_from_db()
        self.assertEqual((self.sync.contacts_request_id, self.sync.history_request_id), ("contacts", "history"))

    @patch("apps.integrations.whatsapp.coexistence_sync.get_whatsapp_access_token", return_value="synthetic")
    @patch("apps.integrations.whatsapp.coexistence_sync.graph_call", side_effect=ValueError("network failure"))
    def test_unknown_sync_result_is_not_blindly_replayed(self, graph, token):
        from apps.integrations.whatsapp.coexistence_sync import start_sync
        start_sync(self.sync.pk)
        start_sync(self.sync.pk)
        self.assertEqual(graph.call_count, 1)
        self.sync.refresh_from_db()
        self.assertEqual(self.sync.state, "request_unknown")

    @patch("apps.integrations.whatsapp.coexistence_sync.graph_call")
    def test_expired_sync_does_not_call_meta(self, graph):
        from apps.integrations.whatsapp.coexistence_sync import start_sync
        WhatsAppCoexistenceSync.objects.filter(pk=self.sync.pk).update(created_at=timezone.now()-timezone.timedelta(hours=25))
        start_sync(self.sync.pk)
        graph.assert_not_called()
        self.sync.refresh_from_db()
        self.assertEqual(self.sync.state, "expired")


class MetaCoexistenceConcurrencyTests(TransactionTestCase):
    setUp = MetaCoexistenceImportTests.setUp

    @skipUnlessDBFeature("has_select_for_update")
    def test_two_workers_import_one_event_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        event = WhatsAppCoexistenceEvent.objects.create(sync=self.sync, digest="parallel", field="history",
            payload=MetaCoexistenceImportTests.history(self))
        ready = Barrier(2)

        def run():
            try:
                ready.wait(timeout=10)
                process_event(event.pk)
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as pool:
            jobs = [pool.submit(run) for _ in range(2)]
            for job in jobs:
                job.result(timeout=20)
        self.assertEqual(BotMessage.objects.filter(external_message_id=self.message["id"]).count(), 1)
