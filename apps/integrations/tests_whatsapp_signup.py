import copy
from datetime import timedelta
from unittest.mock import patch
from urllib.error import URLError
from urllib.parse import parse_qs, urlparse

from django.contrib.auth import get_user_model
from django.test import TestCase, TransactionTestCase, override_settings, skipUnlessDBFeature
from django.utils import timezone
from rest_framework.test import APIClient

from apps.businesses.models import Business, BusinessMember
from apps.bots.models import Bot, BotChannel
from apps.integrations.credential_encryption import decrypt_credential_value
from apps.integrations.models import BusinessConnector, ConnectorCredential, WhatsAppSignupAttempt
from apps.integrations.whatsapp.embedded_signup import build_embedded_signup_state, build_embedded_signup_url, complete_embedded_signup, exchange_code_for_access_token
from apps.integrations.whatsapp.signup_graph import validate_signup_assets, graph_call


@override_settings(META_APP_ID="app", META_APP_SECRET="secret", WHATSAPP_GRAPH_BASE_URL="https://graph.facebook.com",
                   CORS_ALLOWED_ORIGINS=["https://app.zani.kz"], CSRF_TRUSTED_ORIGINS=["https://app.zani.kz"])
class WhatsAppSignupTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_user(username="signup", role=User.Roles.BUSINESS_OWNER)
        self.business = Business.objects.create(owner=self.user, name="Signup", slug="signup")
        BusinessMember.objects.create(business=self.business, user=self.user, role=BusinessMember.Roles.OWNER)
        self.channel = BotChannel.objects.create(bot=Bot.objects.create(business=self.business, name="Signup"), channel="whatsapp", status="draft")
        self.redirect = "https://app.zani.kz/app/integrations"
        self.api = APIClient()
        self.api.force_authenticate(self.user)
        self.debug = {"is_valid": True, "app_id": "app", "scopes": ["whatsapp_business_management", "whatsapp_business_messaging"],
                      "expires_at": int((timezone.now() + timedelta(hours=1)).timestamp())}
        self.calls = []
        self.graph = patch("apps.integrations.whatsapp.signup_graph.graph_call", side_effect=self.respond).start()
        self.exchange = patch("apps.integrations.whatsapp.embedded_signup.exchange_code_for_access_token", return_value={"access_token": "private-token"}).start()
        self.addCleanup(patch.stopall)

    def respond(self, edge, token, **kwargs):
        self.calls.append((edge, kwargs))
        if edge == "debug_token":
            return {"data": copy.deepcopy(self.debug)}
        if edge.endswith("/phone_numbers"):
            return {"data": [{"id": "123", "display_phone_number": "+77010000000", "platform_type": "CLOUD_API"}]}
        return {"success": True}

    def payload(self):
        return dict(business=self.business, user=self.user, code="code", state=build_embedded_signup_state(
            business=self.business, user=self.user, redirect_uri=self.redirect, bot_channel=self.channel),
            redirect_uri=self.redirect, phone_number_id="123", waba_id="456", display_phone_number="untrusted", registration_pin="123456")

    def test_login_url_requests_only_cloud_api_permissions(self):
        url, _ = build_embedded_signup_url(business=self.business, user=self.user,
                                         redirect_uri=self.redirect, bot_channel=self.channel)
        self.assertEqual(parse_qs(urlparse(url).query)["scope"],
                         ["whatsapp_business_management,whatsapp_business_messaging"])

    def test_full_flow_verifies_assets_before_activation_and_stores_secrets_encrypted(self):
        channel, connector = complete_embedded_signup(**self.payload())
        self.assertEqual([x[0] for x in self.calls], ["debug_token", "456/phone_numbers", "456/subscribed_apps", "123/register"])
        self.assertEqual(channel.status, "active")
        self.assertEqual(channel.config_json["display_phone_number"], "+77010000000")
        self.assertNotIn("private-token", str(channel.config_json) + str(connector.config_json))
        token = ConnectorCredential.objects.get(connector=connector, key="access_token")
        self.assertIsNotNone(token.expires_at)
        self.assertEqual(decrypt_credential_value(token.encrypted_value), "private-token")
        self.assertEqual(decrypt_credential_value(connector.credentials.get(key="registration_pin").encrypted_value), "123456")
        self.assertTrue(WhatsAppSignupAttempt.objects.get().succeeded)
        self.assertEqual(self.calls[-1][1]["body"], {"messaging_product": "whatsapp", "pin": "123456"})

    def test_replay_does_not_exchange_or_register_again(self):
        data = self.payload()
        complete_embedded_signup(**data)
        with self.assertRaises(ValueError):
            complete_embedded_signup(**data)
        self.assertEqual(self.exchange.call_count, 1)

    def test_new_start_invalidates_previous_pending_state(self):
        old = self.payload()
        self.payload()
        with self.assertRaises(ValueError):
            complete_embedded_signup(**old)
        self.exchange.assert_not_called()

    def test_concurrent_attempt_is_rejected_before_provider(self):
        data = self.payload()
        WhatsAppSignupAttempt.objects.create(channel=self.channel, user=self.user, channel_revision=self.channel.updated_at, consumed_at=timezone.now())
        with self.assertRaises(ValueError):
            complete_embedded_signup(**data)
        self.exchange.assert_not_called()

    def test_stale_worker_can_be_recovered_after_thirty_minutes(self):
        data = self.payload()
        WhatsAppSignupAttempt.objects.create(channel=self.channel, user=self.user, channel_revision=self.channel.updated_at, consumed_at=timezone.now()-timedelta(hours=1))
        complete_embedded_signup(**data)

    def test_invalid_token_variants_never_activate_or_reserve(self):
        for change in ({"is_valid": False}, {"app_id": "foreign"}, {"scopes": []}, {"expires_at": 1},
                       {"data_access_expires_at": 1}, {"granular_scopes": [{"scope": "whatsapp_business_management", "target_ids": ["other"]}]}):
            with self.subTest(change=change):
                original = copy.deepcopy(self.debug)
                self.debug.update(change)
                with self.assertRaises(ValueError):
                    complete_embedded_signup(**self.payload())
                self.debug = original
        self.assertFalse(WhatsAppSignupAttempt.objects.filter(phone_number_id__isnull=False).exists())
        self.assertFalse(BusinessConnector.objects.exists())
        self.assertFalse(any(edge.endswith("register") for edge, _ in self.calls))

    def test_foreign_phone_rejected_before_subscription(self):
        data = self.payload()
        data["phone_number_id"] = "999"
        with self.assertRaises(ValueError):
            complete_embedded_signup(**data)
        self.assertEqual([x[0] for x in self.calls], ["debug_token", "456/phone_numbers"])

    def test_failed_subscription_or_registration_preserves_connection_and_consumes_attempt(self):
        for failed_edge in ("456/subscribed_apps", "123/register"):
            with self.subTest(edge=failed_edge):
                data = self.payload()
                self.graph.side_effect = lambda edge, token, **kw: {"success": False} if edge == failed_edge else self.respond(edge, token, **kw)
                with self.assertRaises(ValueError):
                    complete_embedded_signup(**data)
                self.channel.refresh_from_db()
                self.assertEqual(self.channel.status, "draft")
                self.assertFalse(ConnectorCredential.objects.exists())
                before = self.exchange.call_count
                with self.assertRaises(ValueError):
                    complete_embedded_signup(**data)
                self.assertEqual(self.exchange.call_count, before)
        self.graph.side_effect = self.respond
        complete_embedded_signup(**self.payload())

    def test_exchange_failure_is_safe_and_retry_requires_new_state(self):
        data = self.payload()
        self.exchange.side_effect = URLError("secret provider detail")
        with self.assertRaisesRegex(ValueError, "Restart setup"):
            complete_embedded_signup(**data)
        self.assertIsNotNone(WhatsAppSignupAttempt.objects.get().finished_at)
        self.graph.assert_not_called()

    def test_malformed_token_response_is_rejected_without_activation(self):
        for response in ([], None, "token", {"access_token": []}):
            with self.subTest(response=response):
                self.exchange.return_value = response
                with self.assertRaises(ValueError):
                    complete_embedded_signup(**self.payload())
        self.graph.assert_not_called()
        self.assertFalse(ConnectorCredential.objects.exists())

    def test_changed_channel_does_not_get_overwritten(self):
        data = self.payload()
        # A rapid write can share the same clock timestamp as the signup start.
        BotChannel.objects.filter(pk=self.channel.pk).update(status="paused")
        with self.assertRaises(ValueError):
            complete_embedded_signup(**data)
        self.exchange.assert_not_called()

    def test_change_during_provider_call_blocks_local_activation(self):
        def activation(edge, token, **kwargs):
            if edge.endswith("register"):
                BotChannel.objects.filter(pk=self.channel.pk).update(status="paused")
            return self.respond(edge, token, **kwargs)
        self.graph.side_effect = activation
        with self.assertRaisesRegex(ValueError, "no longer current"):
            complete_embedded_signup(**self.payload())
        self.assertFalse(ConnectorCredential.objects.exists())
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.status, "paused")

    def test_phone_reserved_for_another_channel_is_rejected(self):
        other = BotChannel.objects.create(bot=Bot.objects.create(business=self.business, name="Other"), channel="whatsapp")
        WhatsAppSignupAttempt.objects.create(channel=other, user=self.user, channel_revision=other.updated_at, phone_number_id="123", consumed_at=timezone.now(), finished_at=timezone.now())
        with self.assertRaises(ValueError):
            complete_embedded_signup(**self.payload())
        self.assertFalse(any(edge.endswith("register") for edge, _ in self.calls))

    def test_api_rejects_invalid_state_pin_and_missing_account(self):
        data = self.payload()
        data.pop("user")
        data["business"] = self.business.pk
        for change in ({"state": "tampered"}, {"registration_pin": "１２３４５６"}, {"registration_pin": "12345"}, {"waba_id": ""}):
            response = self.api.post("/api/business-connectors/whatsapp-embedded-signup/complete/", {**data, **change}, format="json")
            self.assertEqual(response.status_code, 400)
        self.exchange.assert_not_called()

    def test_api_denies_foreign_business_and_mismatched_actor(self):
        other = get_user_model().objects.create_user(username="outsider", email="outsider@example.test", role=get_user_model().Roles.BUSINESS_OWNER)
        data = self.payload()
        data.pop("user")
        data["business"] = self.business.pk
        self.api.force_authenticate(other)
        response = self.api.post("/api/business-connectors/whatsapp-embedded-signup/complete/", data, format="json")
        self.assertIn(response.status_code, (403, 404))
        self.exchange.assert_not_called()
        data = self.payload()
        data["user"] = other
        with self.assertRaises(ValueError):
            complete_embedded_signup(**data)

    def test_pagination_uses_cursor_without_following_remote_url(self):
        self.graph.side_effect = [
            {"data": self.debug},
            {"data": [], "paging": {"next": "https://evil.invalid/?token=secret", "cursors": {"after": "next-page"}}},
            {"data": [{"id": "123", "display_phone_number": "+7"}]},
        ]
        validate_signup_assets("token", "123", "456")
        self.assertEqual(self.graph.call_args_list[-1].args[0], "456/phone_numbers")
        self.assertEqual(self.graph.call_args_list[-1].kwargs["params"]["after"], "next-page")

    def test_graph_transport_redacts_errors(self):
        with patch("apps.integrations.whatsapp.signup_graph.urllib_request.urlopen", side_effect=URLError("private-token")):
            with self.assertRaises(ValueError) as error:
                graph_call("123/register", "private-token", body={"pin": "123456"})
        self.assertNotIn("private-token", str(error.exception))

    def test_revoked_actor_during_registration_cannot_activate(self):
        def revoke(edge, token, **kwargs):
            if edge.endswith("register"):
                get_user_model().objects.filter(pk=self.user.pk).update(is_active=False)
            return self.respond(edge, token, **kwargs)
        self.graph.side_effect = revoke
        with self.assertRaisesRegex(ValueError, "no longer active"):
            complete_embedded_signup(**self.payload())
        self.assertFalse(ConnectorCredential.objects.exists())

    def test_failed_reconnect_retains_previous_working_credentials(self):
        complete_embedded_signup(**self.payload())
        self.channel.refresh_from_db()
        before = copy.deepcopy(self.channel.config_json)
        self.exchange.return_value = {"access_token": "replacement-token"}
        self.graph.side_effect = lambda edge, token, **kwargs: {"success": False} if edge.endswith("register") else self.respond(edge, token, **kwargs)
        with self.assertRaises(ValueError):
            complete_embedded_signup(**self.payload())
        self.channel.refresh_from_db()
        self.assertEqual(self.channel.status, "active")
        self.assertEqual(self.channel.config_json, before)
        self.assertEqual(decrypt_credential_value(ConnectorCredential.objects.get(key="access_token").encrypted_value), "private-token")

    def test_pin_is_redacted_from_config_and_error_payloads(self):
        from apps.integrations.sanitization import sanitize_config
        from apps.core.sanitization import sanitize_error_payload
        for sanitize in (sanitize_config, sanitize_error_payload):
            self.assertNotIn("123456", str(sanitize({"registration_pin": "123456"})))

    def test_sdk_token_exchange_does_not_send_redirect_uri(self):
        from io import BytesIO
        from urllib.parse import urlparse, parse_qs
        with patch("apps.integrations.whatsapp.embedded_signup.urllib_request.urlopen", return_value=BytesIO(b'{"access_token":"test"}')) as request:
            exchange_code_for_access_token(code="sdk-code", redirect_uri=self.redirect)
        query = parse_qs(urlparse(request.call_args.args[0]).query)
        self.assertNotIn("redirect_uri", query)
        self.assertEqual(query["code"], ["sdk-code"])

    def test_recovered_stale_worker_cannot_commit_late_result(self):
        def expire(edge, token, **kwargs):
            if edge.endswith("register"):
                WhatsAppSignupAttempt.objects.filter(channel=self.channel).update(finished_at=timezone.now())
            return self.respond(edge, token, **kwargs)
        self.graph.side_effect = expire
        with self.assertRaisesRegex(ValueError, "no longer current"):
            complete_embedded_signup(**self.payload())
        self.assertFalse(ConnectorCredential.objects.exists())


class WhatsAppSignupConcurrencyTests(TransactionTestCase):
    @skipUnlessDBFeature("has_select_for_update")
    def test_two_workers_claim_one_attempt_once(self):
        from concurrent.futures import ThreadPoolExecutor
        from threading import Barrier
        from django.db import connections
        from apps.integrations.whatsapp.embedded_signup import _claim_attempt, load_embedded_signup_state
        user = get_user_model().objects.create_user(username="parallel-signup", email="parallel@example.test")
        business = Business.objects.create(owner=user, name="Parallel", slug="parallel-signup")
        channel = BotChannel.objects.create(bot=Bot.objects.create(business=business, name="Parallel"), channel="whatsapp")
        state = build_embedded_signup_state(business=business, user=user, redirect_uri="https://example.com", bot_channel=channel)
        payload = load_embedded_signup_state(state)
        ready = Barrier(2)

        def claim():
            try:
                current = BotChannel.objects.select_related("bot").get(pk=channel.pk)
                actor = get_user_model().objects.get(pk=user.pk)
                ready.wait(timeout=10)
                try:
                    _claim_attempt(current, actor, payload)
                    return "claimed"
                except ValueError:
                    return "rejected"
            finally:
                connections.close_all()

        with ThreadPoolExecutor(max_workers=2) as workers:
            futures = [workers.submit(claim) for _ in range(2)]
            self.assertCountEqual([future.result(timeout=20) for future in futures], ["claimed", "rejected"])
