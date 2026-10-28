import json
import hashlib
import hmac
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone
from rest_framework.exceptions import PermissionDenied, ValidationError

from apps.integrations import tests as foundation
from apps.integrations.ycloud import client, onboarding
from apps.integrations.ycloud.models import YCloudConnection


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-webhook-secret")
class YCloudOnboardingTests(TestCase):
    def setUp(self):
        foundation.WhatsAppIntegrationFoundationTests.setUp(self)
        self.channel.status = "draft"
        self.channel.save()
        self.link = {"onboardingUrl": "https://connect.ycloud.com/open/whatsapp/onboard#token=synthetic",
                     "expiresAt": int((timezone.now() + timezone.timedelta(hours=2)).timestamp() * 1000)}
        self.number = {"id": "phone-1", "wabaId": "waba-1", "phoneNumber": "+77010000000", "status": "CONNECTED"}

    def begin(self):
        with patch.object(client, "create_link", return_value=self.link):
            return onboarding.start(self.channel, self.owner)

    def test_disabled_client_never_opens_network(self):
        with override_settings(YCLOUD_ENABLED=False), patch.object(client.request, "build_opener") as opener:
            with self.assertRaises(client.YCloudError):
                client.create_link("test")
            opener.assert_not_called()

    def test_link_is_not_persisted_and_start_is_not_duplicated(self):
        self.assertEqual(self.begin()["onboarding_url"], self.link["onboardingUrl"])
        self.channel.refresh_from_db()
        self.assertNotIn("synthetic", json.dumps(self.channel.config_json))
        with self.assertRaises(ValidationError):
            self.begin()
        self.assertEqual(YCloudConnection.objects.count(), 1)

    def test_failed_start_leaves_original_setup(self):
        original = self.channel.config_json.copy()
        with patch.object(client, "create_link", side_effect=client.YCloudError()):
            with self.assertRaises(client.YCloudError):
                onboarding.start(self.channel, self.owner)
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.config_json, original)
        self.assertFalse(YCloudConnection.objects.exists())

    def test_confirm_requires_payment_and_reuses_channel(self):
        self.begin()
        connection = YCloudConnection.objects.get()
        with self.assertRaises(client.YCloudError):
            onboarding.confirm(connection, {"id": "waba-1", "paymentMethodAttached": False})
        with patch.object(client, "connected_number", return_value=self.number):
            onboarding.confirm(connection, {"id": "waba-1", "paymentMethodAttached": True})
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.config_json["provider_mode"], "ycloud")
        self.assertEqual(self.channel.status, "active")
        connection.refresh_from_db()
        self.assertEqual(connection.phone_number, "+77010000000")

    def test_stale_configuration_cannot_be_reactivated(self):
        self.begin()
        connection = YCloudConnection.objects.get()
        self.channel.refresh_from_db()
        self.channel.config_json["setup_revision"] = "changed"
        self.channel.save()
        with self.assertRaises(client.YCloudError), patch.object(client, "connected_number") as lookup:
            onboarding.confirm(connection, {"id": "waba-1", "paymentMethodAttached": True})
        lookup.assert_not_called()

    def test_other_business_cannot_start(self):
        with self.assertRaises(PermissionDenied), patch.object(client, "create_link") as create:
            onboarding.start(self.channel, self.other_owner)
        create.assert_not_called()

    def test_provider_link_host_is_validated(self):
        with patch.object(client, "call", return_value={**self.link, "onboardingUrl": "https://evil.example/#token=x"}):
            with self.assertRaises(client.YCloudError):
                client.create_link("test")

    def test_setup_api_is_tenant_scoped(self):
        self.api.force_authenticate(self.other_owner)
        response = self.api.post(f"/api/integrations/ycloud/channels/{self.channel.pk}/", {}, format="json")
        self.assertEqual(response.status_code, 404)
        self.api.force_authenticate(self.owner)
        with patch.object(client, "create_link", return_value=self.link):
            response = self.api.post(f"/api/integrations/ycloud/channels/{self.channel.pk}/", {}, format="json")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response["Cache-Control"], "no-store")
        response = self.api.get(f"/api/integrations/ycloud/channels/{self.channel.pk}/")
        self.assertEqual(response.data["status"], "pending")
        self.assertNotIn("synthetic-key", str(response.data))


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-webhook-secret")
class YCloudCurrentAuthorityTests(TestCase):
    setUp = YCloudOnboardingTests.setUp
    begin = YCloudOnboardingTests.begin

    def test_disabled_cached_initiator_cannot_start(self):
        type(self.owner).objects.filter(pk=self.owner.pk).update(is_active=False)
        with patch.object(client, "create_link", return_value=self.link) as create, self.assertRaises(PermissionDenied):
            onboarding.start(self.channel, self.owner)
        create.assert_not_called()
        self.assertFalse(YCloudConnection.objects.exists())

    def test_disabled_initiator_cannot_confirm_pending_connection(self):
        self.begin()
        connection = YCloudConnection.objects.get()
        type(self.owner).objects.filter(pk=self.owner.pk).update(is_active=False)
        with patch.object(client, "connected_number", return_value=self.number) as lookup, self.assertRaises(PermissionDenied):
            onboarding.confirm(connection, {"id": "waba-1", "paymentMethodAttached": True})
        lookup.assert_not_called()
        connection.refresh_from_db()
        self.assertEqual(connection.status, "pending")

    def test_current_role_denial_blocks_all_setup_actions(self):
        from apps.businesses.models import BusinessMember
        BusinessMember.objects.create(business=self.business, user=self.other_owner, role="specialist")
        self.api.force_authenticate(self.other_owner)
        with patch.object(client, "create_link") as create:
            for action in ("start", "cancel", "retry_events"):
                response = self.api.post(f"/api/integrations/ycloud/channels/{self.channel.pk}/", {"action": action}, format="json")
                self.assertEqual(response.status_code, 403)
        create.assert_not_called()
        self.assertFalse(YCloudConnection.objects.exists())


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-webhook-secret")
class YCloudWebhookTests(YCloudOnboardingTests):
    # Inherits the onboarding controls as well as testing durable intake separately.
    def signed(self, payload, timestamp=None):
        body = json.dumps(payload).encode()
        timestamp = str(timestamp or int(timezone.now().timestamp()))
        signature = hmac.new(b"synthetic-webhook-secret", timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        return body, f"t={timestamp},s={signature}"

    def accept(self, payload):
        from apps.integrations.ycloud.webhooks import accept
        return accept(*self.signed(payload))

    def bind(self):
        self.begin()
        connection = YCloudConnection.objects.get()
        data = {"id": "waba-1", "partnerCustomerId": str(connection.customer_id), "updateEvent": "PARTNER_ADDED", "paymentMethodAttached": True}
        event = self.accept({"id": "binding-1", "type": "whatsapp.business_account.updated", "whatsappBusinessAccount": data})
        from apps.integrations.ycloud.events import process
        with patch.object(client, "connected_number", return_value=self.number):
            process(event.pk)
        connection.refresh_from_db()
        self.assertEqual(connection.status, "connected")
        return connection

    def incoming(self, **changes):
        return {"id": "event-1", "type": "whatsapp.inbound_message.received", "whatsappInboundMessage": {
            "id": "inbound-1", "wamid": "wamid.inbound-1", "wabaId": "waba-1", "from": "+77012223344",
            "to": "+77010000000", "type": "text", "text": {"body": "Hello"}, "sendTime": timezone.now().isoformat(), **changes}}

    def test_signature_modified_expired_missing_or_duplicated_time(self):
        from apps.integrations.ycloud.webhooks import accept
        body, signature = self.signed({"id": "event", "type": "unknown"})
        for raw, header in [(body+b" ", signature), (body, ""), (body, signature+",t=1"), self.signed({}, int(timezone.now().timestamp())-600)]:
            with self.subTest(header=header), self.assertRaises(PermissionDenied):
                accept(raw, header)

    def test_webhook_is_durable_before_processing_and_private_response(self):
        self.begin()
        data = {"id": "event", "type": "whatsapp.business_account.updated", "whatsappBusinessAccount": {
            "partnerCustomerId": str(YCloudConnection.objects.get().customer_id), "id": "waba-1", "updateEvent": "PARTNER_ADDED", "paymentMethodAttached": True}}
        body, signature = self.signed(data)
        response = self.api.generic("POST", "/api/integrations/ycloud/webhook/", body, content_type="application/json", HTTP_YCLOUD_SIGNATURE=signature)
        self.assertEqual(response.status_code, 204)
        from apps.integrations.ycloud.models import YCloudEvent
        self.assertEqual(YCloudEvent.objects.get().status, "pending")
        self.assertEqual(YCloudConnection.objects.get().status, "pending")

    def test_inbound_reuses_inbox_event_and_deduplicates_distinct_event_ids(self):
        self.bind()
        from apps.integrations.ycloud.events import process
        from apps.bots.models import BotMessage, BotConversation
        from apps.integrations.models import BusinessEvent
        event = self.accept(self.incoming())
        with patch("apps.integrations.whatsapp.maybe_run_auto_pipeline") as pipeline:
            process(event.pk)
            process(event.pk)
            another = self.accept({**self.incoming(), "id": "event-2"})
            process(another.pk)
        self.assertEqual(pipeline.call_count, 1)
        self.assertEqual(BotMessage.objects.filter(direction="inbound").count(), 1)
        conversation = BotConversation.objects.get()
        self.assertEqual(conversation.business_id, self.business.pk)
        self.assertEqual(conversation.unread_count, 1)
        self.assertTrue(BusinessEvent.objects.filter(event_type="message.received", business=self.business).exists())

    def test_foreign_or_mismatched_route_has_no_effect(self):
        self.bind()
        from apps.integrations.ycloud.webhooks import MessageRouteNotReady
        from apps.integrations.ycloud.models import YCloudEvent
        before = YCloudEvent.objects.count()
        for changes in [{"wabaId": "other"}, {"to": "+77019999999"}]:
            with self.assertRaises(MessageRouteNotReady):
                self.accept(self.incoming(**changes))
        self.assertEqual(YCloudEvent.objects.count(), before)

    def test_paused_channel_retries_without_inbound_effect(self):
        self.bind()
        self.channel.refresh_from_db()
        self.channel.status = "paused"
        self.channel.save()
        event = self.accept(self.incoming())
        from apps.integrations.ycloud.events import process
        from apps.bots.models import BotMessage
        process(event.pk)
        event.refresh_from_db()
        self.assertEqual(event.error_code, "channel_unavailable")
        self.assertEqual(event.status, "pending")
        self.assertFalse(BotMessage.objects.exists())


    def test_processing_failure_rolls_back_and_retries_are_bounded(self):
        self.bind()
        event = self.accept(self.incoming())
        from apps.integrations.ycloud.events import process
        from apps.bots.models import BotMessage
        for attempt in range(6):
            event.next_attempt_at = timezone.now()
            event.save(update_fields=["next_attempt_at"])
            with patch("apps.integrations.whatsapp.record_message_received_event", side_effect=RuntimeError("synthetic")):
                process(event.pk)
            self.assertFalse(BotMessage.objects.exists())
        event.refresh_from_db()
        self.assertEqual(event.attempts, 6)
        self.assertEqual(event.status, "failed")

    def test_expired_attempt_cannot_bind_replacement(self):
        self.begin()
        connection = YCloudConnection.objects.get()
        old_id = str(connection.customer_id)
        connection.expires_at = timezone.now()-timezone.timedelta(seconds=1)
        connection.save()
        self.begin()
        connection.refresh_from_db()
        self.assertNotEqual(str(connection.customer_id), old_id)
        self.assertIsNone(self.accept({"id": "late", "type": "whatsapp.business_account.updated", "whatsappBusinessAccount": {"partnerCustomerId": old_id}}))

    def test_meta_and_legacy_auth_cannot_route_to_ycloud(self):
        self.bind()
        from apps.integrations.whatsapp_routing import VerifiedWhatsAppWebhook, resolve_whatsapp_channel
        for mode in ["meta", "internal", "channel"]:
            with self.assertRaises((PermissionDenied, ValidationError)):
                resolve_whatsapp_channel(VerifiedWhatsAppWebhook(mode=mode, channel_id=self.channel.pk,
                    bot_id=self.bot.pk, business_id=self.business.pk), "phone-1")

    def test_cancel_invalidates_already_accepted_binding_and_can_restart(self):
        self.begin()
        connection = YCloudConnection.objects.get()
        event = self.accept({"id": "before-cancel", "type": "whatsapp.business_account.updated", "whatsappBusinessAccount": {
            "partnerCustomerId": str(connection.customer_id), "id": "waba-1", "paymentMethodAttached": True, "updateEvent": "PARTNER_ADDED"}})
        onboarding.recover(self.channel, self.owner, "cancel")
        from apps.integrations.ycloud.events import process
        with patch.object(client, "connected_number") as lookup:
            process(event.pk)
            lookup.assert_not_called()
        self.begin()
        self.assertEqual(YCloudConnection.objects.get().status, "pending")

    def test_malformed_and_non_text_messages_have_no_crm_effect(self):
        self.bind()
        from apps.integrations.ycloud.events import process
        from apps.bots.models import BotMessage
        for index, changes in enumerate([{"text": []}, {"type": "image"}, {"sendTime": "bad"}, {"from": ""}]):
            event = self.accept({**self.incoming(**changes), "id": f"invalid-{index}"})
            process(event.pk)
            event.refresh_from_db()
            self.assertEqual(event.status, "failed")
        self.assertFalse(BotMessage.objects.exists())


@override_settings(YCLOUD_ENABLED=True, YCLOUD_API_KEY="synthetic-key", YCLOUD_WEBHOOK_SECRET="synthetic-webhook-secret")
class YCloudIngressOrderingTests(TestCase):
    setUp = YCloudOnboardingTests.setUp
    begin = YCloudOnboardingTests.begin
    signed = YCloudWebhookTests.signed
    incoming = YCloudWebhookTests.incoming

    def test_message_before_binding_is_retried_instead_of_acknowledged_and_lost(self):
        self.begin()
        body, signature = self.signed(self.incoming())
        response = self.api.generic("POST", "/api/integrations/ycloud/webhook/", body,
            content_type="application/json", HTTP_YCLOUD_SIGNATURE=signature)
        self.assertEqual(response.status_code, 503)
        from apps.integrations.ycloud.models import YCloudEvent
        self.assertFalse(YCloudEvent.objects.exists())
        with patch.object(client, "connected_number", return_value=self.number):
            onboarding.confirm(YCloudConnection.objects.get(), {"id": "waba-1", "paymentMethodAttached": True})
        response = self.api.generic("POST", "/api/integrations/ycloud/webhook/", body,
            content_type="application/json", HTTP_YCLOUD_SIGNATURE=signature)
        self.assertEqual(response.status_code, 204)
        from apps.integrations.ycloud.events import process
        from apps.bots.models import BotMessage
        with patch("apps.integrations.whatsapp.maybe_run_auto_pipeline"):
            process(YCloudEvent.objects.get().pk)
        self.assertEqual(BotMessage.objects.filter(direction="inbound").count(), 1)
