from unittest.mock import patch

from django.test import TestCase, TransactionTestCase, override_settings
from rest_framework.exceptions import ValidationError

from apps.integrations import tests_ycloud as foundation
from apps.integrations.ycloud import client, onboarding
from apps.integrations.ycloud.models import YCloudConnection


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-webhook-secret")
class CoexistenceOnboardingTests(TestCase):
    setUp = foundation.YCloudOnboardingTests.setUp

    def test_app_mode_and_number_are_bound_to_attempt_and_returned_without_link(self):
        self.api.force_authenticate(self.owner)
        path = f"/api/integrations/ycloud/channels/{self.channel.pk}/"
        with patch.object(client, "call", return_value=self.link) as network:
            response = self.api.post(path, {"onboarding_type": "WHATSAPP_BUSINESS_APP",
                                          "expected_phone_number": self.number["phoneNumber"]}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(network.call_args.args[2]["onboardingType"], "WHATSAPP_BUSINESS_APP")
        binding = YCloudConnection.objects.get()
        self.assertEqual(binding.onboarding_type, "WHATSAPP_BUSINESS_APP")
        response = self.api.get(path)
        self.assertEqual(response.data["expected_phone_number"], self.number["phoneNumber"])
        self.assertEqual(response.data["onboarding_type"], "WHATSAPP_BUSINESS_APP")
        self.assertNotIn("onboarding_url", response.data)
        with patch.object(client, "connected_number", return_value={**self.number, "phoneNumber": "+77019999999"}):
            with self.assertRaisesMessage(client.YCloudError, "phone_number_mismatch"):
                onboarding.confirm(binding, {"id": "waba-1", "paymentMethodAttached": True})
        binding.refresh_from_db()
        self.assertEqual(binding.status, "pending")
        self.assertEqual(binding.waba_id, "")
        with patch.object(client, "connected_number", return_value=self.number):
            onboarding.confirm(binding, {"id": "waba-1", "paymentMethodAttached": True})
        binding.refresh_from_db()
        self.assertEqual(binding.status, "connected")

    def test_invalid_mode_or_number_never_calls_provider(self):
        for mode, number in [("unknown", ""), (None, ""), ([], ""),
                             ("WHATSAPP_BUSINESS_APP", ""), ("WHATSAPP_BUSINESS_APP", "87010000000"),
                             ("WHATSAPP_BUSINESS_APP", {"phone": "x"})]:
            with self.subTest(mode=mode, number=number), patch.object(client, "call") as network:
                with self.assertRaises(ValidationError):
                    onboarding.start(self.channel, self.owner, onboarding_type=mode, expected_phone_number=number)
                network.assert_not_called()
        self.assertFalse(YCloudConnection.objects.exists())

    def test_cancel_and_restart_can_change_mode_without_reviving_old_attempt(self):
        with patch.object(client, "create_link", return_value=self.link):
            onboarding.start(self.channel, self.owner, onboarding_type="WHATSAPP_BUSINESS_APP",
                             expected_phone_number=self.number["phoneNumber"])
            old = YCloudConnection.objects.get()
            onboarding.recover(self.channel, self.owner, "cancel")
            onboarding.start(self.channel, self.owner)
        current = YCloudConnection.objects.get()
        self.assertEqual(current.onboarding_type, "WHATSAPP_BUSINESS_PLATFORM")
        self.assertEqual(current.expected_phone_number, "")
        self.assertNotEqual(current.customer_id, old.customer_id)


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-webhook-secret")
class CoexistenceMessageTests(TestCase):
    signed = foundation.YCloudWebhookTests.signed
    accept = foundation.YCloudWebhookTests.accept

    def setUp(self):
        from django.utils import timezone
        foundation.YCloudOnboardingTests.setUp(self)
        self.channel.config_json = {"provider_mode": "ycloud", "setup_revision": "coexist", "connection_verified": True}
        self.channel.status = "active"
        self.channel.save()
        self.binding = YCloudConnection.objects.create(channel=self.channel, initiated_by=self.owner,
            setup_revision="coexist", status="connected", expires_at=timezone.now(),
            onboarding_type="WHATSAPP_BUSINESS_APP", waba_id="waba-1", phone_id="phone-1",
            phone_number="+77010000000")

    def echo(self, **changes):
        from django.utils import timezone
        return {"id": "event-app-1", "type": "whatsapp.smb.message.echoes", "whatsappMessage": {
            "id": "app-1", "wamid": "wamid.app-1", "wabaId": "waba-1", "from": "+77010000000",
            "to": "+77012223344", "type": "text", "text": {"body": "Staff answer"},
            "status": "sent", "sendTime": timezone.now().isoformat(), **changes}}

    def process(self, payload):
        from apps.integrations.ycloud.events import process
        event = self.accept(payload)
        process(event.pk)
        event.refresh_from_db()
        return event

    def test_both_app_streams_import_once_without_pipeline_dispatch_or_customer_window(self):
        from apps.bots.models import BotConversation, BotMessage
        from apps.integrations.ycloud.models import YCloudDispatch
        with patch("apps.integrations.whatsapp.maybe_run_auto_pipeline") as pipeline, patch.object(client, "call") as network:
            event = self.process(self.echo())
            duplicate = self.process({**self.echo(), "id": "event-app-2", "type": "whatsapp.smb.message.created"})
        self.assertEqual((event.status, duplicate.status), ("processed", "processed"))
        self.assertEqual(BotMessage.objects.count(), 1)
        message = BotMessage.objects.get()
        self.assertEqual((message.direction, message.sender_type, message.status), ("outbound", "manager", "sent"))
        self.assertNotIn("sent_by_user_id", message.payload_json)
        conversation = BotConversation.objects.get()
        self.assertEqual(conversation.business_id, self.business.pk)
        self.assertIsNone(conversation.last_inbound_at)
        self.assertEqual(conversation.unread_count, 0)
        self.assertFalse(conversation.bot_enabled)
        self.assertTrue(conversation.handoff_required)
        self.assertIsNone(conversation.ai_resume_at)
        self.assertFalse(YCloudDispatch.objects.exists())
        pipeline.assert_not_called()
        network.assert_not_called()

    def test_wrong_business_or_number_does_not_create_an_event(self):
        from apps.integrations.ycloud.webhooks import MessageRouteNotReady
        from apps.integrations.ycloud.models import YCloudEvent
        for changes in [{"wabaId": "other"}, {"from": "+77019999999"}]:
            with self.subTest(changes=changes), self.assertRaises(MessageRouteNotReady):
                self.accept(self.echo(**changes))
        self.assertFalse(YCloudEvent.objects.exists())

    def test_api_only_channel_rejects_app_events(self):
        from apps.bots.models import BotMessage
        self.binding.onboarding_type = "WHATSAPP_BUSINESS_PLATFORM"
        self.binding.save()
        event = self.process(self.echo())
        self.assertEqual((event.status, event.error_code), ("failed", "coexistence_not_enabled"))
        self.assertFalse(BotMessage.objects.exists())

    def test_invalid_echo_has_no_message_or_handoff_effect(self):
        from apps.bots.models import BotConversation
        for i, changes in enumerate([{"to": "invalid"}, {"wamid": ""}, {"text": {}},
                                     {"status": "accepted"}, {"sendTime": "2000-01-01"}]):
            with self.subTest(changes=changes):
                event = self.process({**self.echo(**changes), "id": f"bad-{i}"})
                self.assertEqual(event.status, "failed")
        self.assertFalse(BotConversation.objects.exists())

    def test_paused_channel_still_records_staff_reply(self):
        self.channel.status = "paused"
        self.channel.save()
        self.assertEqual(self.process(self.echo()).status, "processed")

    def test_stale_revision_cannot_import(self):
        from apps.bots.models import BotMessage
        self.channel.config_json["setup_revision"] = "replacement"
        self.channel.save()
        event = self.process(self.echo())
        self.assertEqual(event.error_code, "channel_unavailable")
        self.assertFalse(BotMessage.objects.exists())

    def test_media_echo_is_a_notice_without_fetching_media(self):
        from apps.bots.models import BotMessage
        with patch.object(client, "call") as network:
            event = self.process(self.echo(type="image", image={"link": "https://example.invalid/private"}))
        self.assertEqual(event.status, "processed")
        message = BotMessage.objects.get()
        self.assertTrue(message.payload_json["content_unavailable"])
        self.assertEqual(message.text, "[WhatsApp Business App: image]")
        self.assertNotIn("private", str(event.payload))
        network.assert_not_called()

    def test_late_echo_preserves_inbound_window_and_cancels_queued_ai(self):
        from django.utils import timezone
        from apps.bots.models import BotConversation, BotMessage
        now = timezone.now()
        conversation = BotConversation.objects.create(bot=self.bot, business=self.business, channel="whatsapp",
            external_user_id="+77012223344", last_message_at=now, last_inbound_at=now, last_outbound_at=now,
            ai_resume_at=now, ai_resume_actor=self.owner, handoff_resume_started_at=now)
        queued = BotMessage.objects.create(conversation=conversation, direction="outbound", sender_type="ai", status="queued")
        event = self.process(self.echo(sendTime=(now-timezone.timedelta(hours=2)).isoformat()))
        self.assertEqual(event.status, "processed")
        conversation.refresh_from_db()
        queued.refresh_from_db()
        self.assertEqual((conversation.last_inbound_at, conversation.last_message_at, conversation.last_outbound_at), (now, now, now))
        self.assertEqual(queued.status, "cancelled")
        self.assertIsNone(conversation.ai_resume_at)
        self.assertIsNone(conversation.handoff_resume_started_at)

    def test_failure_rolls_back_message_and_retry_records_it_once(self):
        from django.utils import timezone
        from apps.bots.models import BotMessage, BotConversation
        from apps.integrations.ycloud.events import process
        event = self.accept(self.echo())
        with patch("apps.bots.inbox_service.handoff_conversation", side_effect=RuntimeError("synthetic")):
            process(event.pk)
        self.assertFalse(BotMessage.objects.exists())
        self.assertFalse(BotConversation.objects.exists())
        event.refresh_from_db()
        self.assertEqual(event.status, "pending")
        event.next_attempt_at = timezone.now()
        event.save()
        process(event.pk)
        self.assertEqual(BotMessage.objects.count(), 1)

    def test_history_is_ignored_and_cannot_open_window(self):
        from apps.bots.models import BotMessage
        self.assertIsNone(self.accept({"id": "history-1", "type": "whatsapp.smb.history", "whatsappMessage": self.echo()["whatsappMessage"]}))
        self.assertFalse(BotMessage.objects.exists())

    def test_status_updates_for_app_message_do_not_create_dispatch_or_regress(self):
        from apps.bots.models import BotMessage
        self.process(self.echo())
        for i, status in enumerate(["read", "sent", "failed"]):
            event = self.process({**self.echo(status=status), "id": f"status-{i}", "type": "whatsapp.message.updated"})
            self.assertEqual(event.status, "processed")
        message = BotMessage.objects.get()
        self.assertEqual(message.status, "sent")
        self.assertEqual(message.payload_json["ycloud_status"], "read")
        self.assertIsNotNone(message.read_at)

    def test_status_before_echo_retries_then_recovers(self):
        from django.utils import timezone
        from apps.integrations.ycloud.events import process
        event = self.process({**self.echo(status="read"), "id": "early-status", "type": "whatsapp.message.updated"})
        self.assertEqual(event.status, "pending")
        self.process(self.echo())
        event.next_attempt_at = timezone.now()
        event.save()
        process(event.pk)
        event.refresh_from_db()
        self.assertEqual(event.status, "processed")

    def test_same_wamid_across_stream_ids_is_not_a_second_message(self):
        from apps.bots.models import BotMessage
        self.process(self.echo())
        event = self.process({**self.echo(id="other-stream-id"), "id": "event-app-2", "type": "whatsapp.smb.message.created"})
        self.assertEqual(event.status, "processed")
        self.assertEqual(BotMessage.objects.count(), 1)
        conflict = self.process({**self.echo(to="+77015555555"), "id": "conflict"})
        self.assertEqual(conflict.error_code, "message_identity_conflict")
        self.assertEqual(BotMessage.objects.count(), 1)


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-secret",
                   OUTBOUND_MESSAGES_RUN_INLINE=True)
class CoexistenceDispatchTests(TransactionTestCase):
    def setUp(self):
        from apps.integrations.tests_ycloud_dispatch import YCloudDispatchTests
        YCloudDispatchTests.setUp(self)
        self.binding.onboarding_type = "WHATSAPP_BUSINESS_APP"
        self.binding.save()

    def test_app_reply_does_not_open_service_window_or_get_resent(self):
        from django.utils import timezone
        from django.db import transaction
        from apps.bots.outbound_delivery import create_outbound_message, deliver_outbound_message
        from apps.integrations.ycloud.coexistence import record_app_message
        from apps.integrations.ycloud.models import YCloudDispatch
        self.conversation.last_inbound_at = timezone.now()-timezone.timedelta(days=2)
        self.conversation.save()
        with transaction.atomic():
            echo = record_app_message(self.binding, {"id": "app-1", "wamid": "wamid.app-1", "wabaId": "waba-1",
                "from": self.binding.phone_number, "to": self.conversation.external_user_id,
                "type": "text", "text": {"body": "Reply in app"}, "status": "sent", "sendTime": timezone.now().isoformat()})
        with patch.object(client, "call") as network:
            deliver_outbound_message(echo.pk)
            message = create_outbound_message(self.conversation, text="CRM reply", user=self.owner)
        network.assert_not_called()
        self.assertEqual(message.status, "failed")
        self.assertFalse(YCloudDispatch.objects.exists())

    def test_app_receipt_for_api_message_is_not_imported_again(self):
        from django.utils import timezone
        from django.db import transaction
        from apps.bots.outbound_delivery import create_outbound_message
        from apps.bots.models import BotMessage
        from apps.integrations.ycloud.coexistence import record_app_message
        with patch.object(client, "call", return_value={"id": "api-1", "wamid": "wamid.api-1", "status": "sent"}):
            message = create_outbound_message(self.conversation, text="CRM reply", user=self.owner)
        with transaction.atomic():
            record_app_message(self.binding, {"id": "api-1", "wamid": "wamid.api-1", "wabaId": "waba-1",
                "from": self.binding.phone_number, "to": self.conversation.external_user_id,
                "type": "text", "text": {"body": "CRM reply"}, "status": "sent", "sendTime": timezone.now().isoformat()})
        self.assertEqual(BotMessage.objects.count(), 1)
        message.refresh_from_db()
        self.assertEqual(message.status, "sent")

    def test_staff_handoff_is_rechecked_at_dispatch(self):
        from apps.bots.models import BotMessage
        from apps.integrations.ycloud.dispatch import send_text
        self.conversation.handoff_required = True
        self.conversation.bot_enabled = False
        self.conversation.save()
        message = BotMessage.objects.create(conversation=self.conversation, direction="outbound", sender_type="ai",
                                           text="Stale answer", status="delivering")
        with patch.object(client, "call") as network:
            result = send_text(self.channel, self.conversation.external_user_id, message.text, {"zani_message_id": message.pk})
        self.assertFalse(result["ok"])
        self.assertEqual(result["reason"], "staff_takeover")
        network.assert_not_called()
