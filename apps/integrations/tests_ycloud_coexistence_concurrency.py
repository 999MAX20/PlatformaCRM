from unittest.mock import patch

from django.utils import timezone

from apps.integrations import tests_ycloud_concurrency as foundation
from apps.integrations.ycloud.models import YCloudEvent
from apps.bots.models import BotMessage, BotConversation


class CoexistenceConcurrencyTests(foundation.YCloudConcurrencyTests):
    def test_two_app_streams_import_one_reply(self):
        from apps.integrations.ycloud.events import process
        self.channel.status = "active"
        self.channel.external_id = "phone-1"
        self.channel.save()
        self.binding.status = "connected"
        self.binding.onboarding_type = "WHATSAPP_BUSINESS_APP"
        self.binding.waba_id = "waba-1"
        self.binding.phone_id = "phone-1"
        self.binding.phone_number = "+77010000000"
        self.binding.save()
        payload = {"id": "app-1", "wamid": "wamid-app-1", "wabaId": "waba-1", "from": "+77010000000", "to": "+77012223344", "type": "text", "text": {"body": "Staff reply"}, "status": "sent", "sendTime": timezone.now().isoformat()}
        events = [YCloudEvent.objects.create(connection=self.binding, external_id=f"app-event-{i}", kind=kind, next_attempt_at=timezone.now(), payload={"whatsappMessage": payload}) for i, kind in enumerate(["whatsapp.smb.message.echoes", "whatsapp.smb.message.created"])]
        from threading import Lock
        remaining = [event.pk for event in events]
        lock = Lock()
        def run():
            with lock:
                event_id = remaining.pop()
            process(event_id)
        with patch("apps.integrations.whatsapp.maybe_run_auto_pipeline") as ai, patch.object(foundation.client, "call") as network:
            self.concurrent(run)
        self.assertEqual(BotMessage.objects.count(), 1)
        self.assertEqual(BotConversation.objects.count(), 1)
        self.assertFalse(BotConversation.objects.get().bot_enabled)
        self.assertEqual(YCloudEvent.objects.filter(status="processed").count(), 2)
        ai.assert_not_called()
        network.assert_not_called()
