from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.bots.models import BotConversation, BotMessage
from apps.integrations import tests_ycloud_coexistence as coexistence_tests
from apps.integrations.ycloud import client, onboarding, webhooks
from apps.integrations.ycloud.models import YCloudEvent, YCloudDispatch


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-webhook-secret")
class YCloudHistoryTests(TestCase):
    def setUp(self):
        coexistence_tests.CoexistenceMessageTests.setUp(self)
        self.channel.external_id = self.binding.phone_id
        self.channel.save(update_fields=["external_id"])

    signed = coexistence_tests.CoexistenceMessageTests.signed
    accept = coexistence_tests.CoexistenceMessageTests.accept
    process = coexistence_tests.CoexistenceMessageTests.process
    echo = coexistence_tests.CoexistenceMessageTests.echo

    def history(self, outbound=False, **changes):
        payload = self.echo(**changes)
        data = payload.pop("whatsappMessage")
        if not outbound:
            data["from"], data["to"] = data["to"], data["from"]
        data["sendTime"] = (timezone.now() - timezone.timedelta(days=90)).isoformat()
        payload.update(type="whatsapp.smb.history")
        payload["whatsappMessage" if outbound else "whatsappInboundMessage"] = data
        return payload

    def test_history_is_visible_without_new_message_side_effects(self):
        with patch("apps.integrations.whatsapp.maybe_run_auto_pipeline") as ai, patch.object(client, "call") as network:
            first = self.process(self.history())
            second = self.process({**self.history(True, wamid="wamid.out"), "id": "history-out"})
        self.assertEqual((first.status, second.status), ("processed", "processed"))
        self.assertEqual(BotMessage.objects.count(), 2)
        conversation = BotConversation.objects.get()
        self.assertEqual(conversation.external_user_id, "+77012223344")
        self.assertEqual(conversation.unread_count, 0)
        self.assertIsNone(conversation.last_inbound_at)
        self.assertFalse(conversation.bot_enabled)
        self.assertFalse(conversation.handoff_required)
        self.assertFalse(YCloudDispatch.objects.exists())
        self.assertTrue(all(m.created_at < timezone.now() - timezone.timedelta(days=89) for m in conversation.messages.all()))
        ai.assert_not_called()
        network.assert_not_called()
        self.api.force_authenticate(self.owner)
        result = self.api.get(f"/api/integrations/ycloud/channels/{self.channel.pk}/")
        self.assertEqual(result.data["history"], {"messages": 2, "pending_events": 0, "failed_events": 0})
        self.api.force_authenticate(self.other_owner)
        self.assertEqual(self.api.get(f"/api/integrations/ycloud/channels/{self.channel.pk}/").status_code, 404)

    def test_replay_and_different_event_ids_import_once(self):
        payload = self.history()
        self.process(payload)
        self.process(payload)
        self.process({**payload, "id": "duplicate-history"})
        self.assertEqual(BotMessage.objects.count(), 1)
        self.assertEqual(YCloudEvent.objects.count(), 2)

    def test_live_inbound_reuses_history_thread_and_only_new_message_opens_window(self):
        payload = self.history()
        self.process(payload)
        live = {**payload, "id": "live-duplicate", "type": "whatsapp.inbound_message.received"}
        with patch("apps.integrations.whatsapp.maybe_run_auto_pipeline"):
            self.assertEqual(self.process(live).status, "processed")
            self.assertIsNone(BotConversation.objects.get().last_inbound_at)
            live["whatsappInboundMessage"].update(id="new-live", wamid="wamid.new-live", sendTime=timezone.now().isoformat())
            self.assertEqual(self.process({**live, "id": "live-new"}).status, "processed")
        self.assertEqual(BotConversation.objects.count(), 1)
        self.assertEqual(BotMessage.objects.count(), 2)
        conversation = BotConversation.objects.get()
        self.assertEqual(conversation.unread_count, 1)
        self.assertIsNotNone(conversation.last_inbound_at)

    def test_history_and_live_app_echo_deduplicate_in_both_orders(self):
        self.process(self.history(True))
        self.process({**self.echo(), "id": "live-echo"})
        message = BotMessage.objects.get()
        self.assertFalse(message.payload_json["historical"])
        self.assertTrue(message.conversation.handoff_required)
        self.process({**self.history(True), "id": "later-history"})
        self.assertEqual(BotMessage.objects.count(), 1)
        self.process({**self.echo(id="app-2", wamid="wamid.app-2"), "id": "live-first"})
        self.process({**self.history(True, id="app-2", wamid="wamid.app-2"), "id": "history-last"})
        self.assertEqual(BotMessage.objects.count(), 2)

    def test_duplicate_message_cannot_change_participants_or_direction(self):
        self.process(self.history(True))
        event = self.process({**self.history(True, to="+77019999999"), "id": "conflict"})
        self.assertEqual(event.error_code, "message_identity_conflict")
        event = self.process({**self.history(), "id": "direction-conflict"})
        self.assertEqual(event.error_code, "message_identity_conflict")
        self.assertEqual(BotMessage.objects.count(), 1)

    def test_unsigned_or_foreign_history_never_writes(self):
        with self.assertRaises(PermissionDenied):
            webhooks.accept(b'{}', "bad")
        with self.assertRaises(webhooks.MessageRouteNotReady):
            self.accept(self.history(wabaId="foreign"))
        with self.assertRaises(webhooks.MessageRouteNotReady):
            self.accept(self.history(True, **{"from": "+77019999999"}))
        self.assertFalse(YCloudEvent.objects.exists())
        self.assertFalse(BotMessage.objects.exists())

    def test_progress_only_is_not_assigned_to_any_tenant(self):
        self.assertIsNone(self.accept({"id": "progress", "type": "whatsapp.smb.history", "phase": 2, "progress": 100}))
        self.assertFalse(YCloudEvent.objects.exists())

    def test_ambiguous_history_direction_rejected(self):
        payload = self.history()
        payload["whatsappMessage"] = self.echo()["whatsappMessage"]
        with self.assertRaises(ValidationError):
            self.accept(payload)
        self.assertFalse(YCloudEvent.objects.exists())

    def test_failed_event_can_be_recovered_after_channel_revision_restored(self):
        self.channel.config_json["setup_revision"] = "stale"
        self.channel.save()
        event = self.process(self.history())
        self.assertEqual(event.status, "failed")
        self.assertFalse(BotMessage.objects.exists())
        self.channel.config_json["setup_revision"] = "coexist"
        self.channel.save()
        onboarding.recover(self.channel, self.owner, "retry_events")
        from apps.integrations.ycloud.events import process
        process(event.pk)
        event.refresh_from_db()
        self.assertEqual(event.status, "processed")
        self.assertEqual(BotMessage.objects.count(), 1)

    def test_paused_channel_imports_but_platform_mode_rejects_history(self):
        self.channel.status = "paused"
        self.channel.save()
        self.assertEqual(self.process(self.history()).status, "processed")
        self.binding.onboarding_type = "WHATSAPP_BUSINESS_PLATFORM"
        self.binding.save()
        event = self.process({**self.history(wamid="other"), "id": "api-only"})
        self.assertEqual(event.error_code, "coexistence_not_enabled")
        self.assertEqual(BotMessage.objects.count(), 1)

    def test_invalid_history_rolls_back_and_media_is_explicitly_unavailable(self):
        for index, changes in enumerate([{"wamid": ""}, {"text": {}}, {"type": []}]):
            event = self.process({**self.history(**changes), "id": f"invalid-{index}"})
            self.assertEqual(event.status, "failed")
        self.assertFalse(BotConversation.objects.exists())
        self.process({**self.history(type="image"), "id": "media"})
        self.assertTrue(BotMessage.objects.get().payload_json["content_unavailable"])

    def test_invalid_time_or_receipt_fails_without_retry(self):
        for index, changes in enumerate([{"sendTime": "2026-99-01T00:00:00Z"}, {"sendTime": "2000-01-01"},
                                        {"status": {}}, {"sendTime": (timezone.now() + timezone.timedelta(days=1)).isoformat()}]):
            payload = self.history(True)
            payload["whatsappMessage"].update(changes)
            event = self.process({**payload, "id": f"invalid-time-{index}"})
            self.assertEqual(event.status, "failed")
        self.assertFalse(BotMessage.objects.exists())

    def test_late_history_preserves_existing_conversation_window_and_order(self):
        now = timezone.now()
        conversation = BotConversation.objects.create(business=self.business, bot=self.channel.bot,
            channel="whatsapp", external_user_id="+77012223344", last_inbound_at=now,
            last_message_at=now, unread_count=3, bot_enabled=True)
        self.process(self.history())
        conversation.refresh_from_db()
        self.assertEqual((conversation.last_inbound_at, conversation.last_message_at, conversation.unread_count), (now, now, 3))
        self.assertTrue(conversation.bot_enabled)

    def test_paused_connected_channel_cannot_be_replaced_by_signup(self):
        self.channel.status = "paused"
        self.channel.external_id = "existing-phone"
        self.channel.save()
        with patch.object(client, "create_link") as network, self.assertRaises(ValidationError):
            onboarding.start(self.channel, self.owner)
        network.assert_not_called()
