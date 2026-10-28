from concurrent.futures import ThreadPoolExecutor
from threading import Barrier
from unittest.mock import patch
import unittest

from django.db import close_old_connections, connection
from django.test import TransactionTestCase, override_settings
from django.utils import timezone

from apps.integrations import tests as foundation
from apps.integrations.ycloud import client, onboarding
from apps.integrations.ycloud.models import YCloudConnection, YCloudEvent, YCloudDispatch
from apps.bots.models import BotMessage, BotConversation


@unittest.skipUnless(connection.vendor == "postgresql", "Requires isolated PostgreSQL")
@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-secret")
class YCloudConcurrencyTests(TransactionTestCase):
    def setUp(self):
        foundation.WhatsAppIntegrationFoundationTests.setUp(self)
        self.channel.config_json = {"provider_mode": "ycloud", "setup_revision": "revision"}
        self.channel.status = "draft"
        self.channel.save()
        self.binding = YCloudConnection.objects.create(channel=self.channel, initiated_by=self.owner,
            setup_revision="revision", expires_at=timezone.now()+timezone.timedelta(hours=2))

    def concurrent(self, function):
        barrier = Barrier(2)
        def run():
            close_old_connections()
            try:
                barrier.wait(timeout=10)
                return function()
            finally:
                close_old_connections()
        with ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run) for _ in range(2)]
            return [future.result(timeout=30) for future in futures]

    def test_confirmation_lock_rechecks_current_binding(self):
        with patch.object(client, "connected_number", return_value={"id": "phone-1", "phoneNumber": "+77010000000"}) as lookup:
            self.concurrent(lambda: onboarding.confirm(YCloudConnection.objects.get(pk=self.binding.pk), {"id": "waba-1", "paymentMethodAttached": True}))
        self.assertEqual(lookup.call_count, 1)
        self.binding.refresh_from_db()
        self.assertEqual(self.binding.status, "connected")

    def test_event_processing_duplicate_workers_have_one_inbox_effect(self):
        from apps.integrations.ycloud.events import process
        self.channel.status = "active"
        self.channel.save()
        self.binding.status, self.binding.waba_id, self.binding.phone_id, self.binding.phone_number = "connected", "waba-1", "phone-1", "+77010000000"
        self.binding.save()
        self.channel.external_id = "phone-1"
        self.channel.save()
        event = YCloudEvent.objects.create(connection=self.binding, external_id="event-1", kind="whatsapp.inbound_message.received", next_attempt_at=timezone.now(),
            payload={"whatsappInboundMessage": {"id": "msg-1", "wabaId": "waba-1", "from": "+77012223344", "to": "+77010000000", "type": "text", "text": {"body": "Hello"}, "sendTime": timezone.now().isoformat()}})
        with patch("apps.integrations.whatsapp.maybe_run_auto_pipeline"):
            self.concurrent(lambda: process(event.pk))
        self.assertEqual(BotMessage.objects.filter(direction="inbound").count(), 1)
        self.assertEqual(BotConversation.objects.get().unread_count, 1)
        event.refresh_from_db()
        self.assertEqual(event.attempts, 1)
        self.assertEqual(event.status, "processed")

    def test_two_delivery_workers_cannot_repeat_http_attempt(self):
        from apps.bots.outbound_delivery import deliver_outbound_message
        self.channel.status = "active"
        self.channel.save()
        self.binding.status, self.binding.waba_id, self.binding.phone_id, self.binding.phone_number = "connected", "waba-1", "phone-1", "+77010000000"
        self.binding.save()
        conversation = BotConversation.objects.create(business=self.business, bot=self.bot, channel="whatsapp",
            external_user_id="+77012223344", last_inbound_at=timezone.now())
        message = BotMessage.objects.create(conversation=conversation, direction="outbound", sender_type="manager",
            text="Hello", status="queued", payload_json={"sent_by_user_id": self.owner.pk})
        with patch.object(client, "call", return_value={"id": "yc-1", "status": "accepted"}) as network:
            self.concurrent(lambda: deliver_outbound_message(message.pk))
        self.assertEqual(network.call_count, 1)
        self.assertEqual(YCloudDispatch.objects.count(), 1)
        message.refresh_from_db()
        self.assertEqual(message.status, "accepted")
