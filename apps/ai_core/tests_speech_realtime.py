import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import TestCase, override_settings
from rest_framework.throttling import ScopedRateThrottle

from apps.ai_core import tests_conversation_memory as fixtures
from apps.ai_core.models import AgentTurn, AIRequestLog
from apps.ai_core.providers.elevenlabs_realtime import TOKEN_URL


@override_settings(AI_ENABLED=True, VOICE_INPUT_ENABLED=True, ELEVENLABS_SCRIBE_ENABLED=True,
                   ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED=True, ELEVENLABS_SCRIBE_REALTIME_ENABLED=True,
                   ELEVENLABS_API_KEY="server-only-synthetic-key")
class RealtimeSpeechTests(TestCase):
    def setUp(self):
        fixtures.ConversationMemoryTests.setUp(self)
        keys = [ScopedRateThrottle.cache_format % {"scope": "ai_assistant", "ident": u.pk}
                for u in (self.owner, self.other_owner)]
        ScopedRateThrottle.cache.delete_many(keys)
        self.addCleanup(ScopedRateThrottle.cache.delete_many, keys)
        self.api.force_authenticate(self.owner)

    def post(self, business=None):
        return self.api.post("/api/ai/speech/session/", {"business": business or self.business.pk}, format="json")

    def test_token_is_bounded_uncached_and_does_not_create_a_command(self):
        with patch("apps.ai_core.providers.elevenlabs_realtime.open_request",
                   return_value=io.BytesIO(b'{"token":"single-use-synthetic-token"}')) as send:
            response = self.post()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data, {"token": "single-use-synthetic-token", "max_seconds": 60})
        self.assertIn("no-store", response["Cache-Control"])
        self.assertNotIn("server-only", str(response.data))
        self.assertEqual(send.call_args.args[0].full_url, TOKEN_URL)
        self.assertEqual(send.call_args.args[0].method, "POST")
        self.assertEqual(send.call_args.kwargs["timeout"], 10)
        self.assertFalse(AgentTurn.objects.exists())
        self.assertFalse(AIRequestLog.objects.exists())

    def test_each_activation_gate_denies_before_provider(self):
        for flag in ("AI_ENABLED", "VOICE_INPUT_ENABLED", "ELEVENLABS_SCRIBE_ENABLED",
                     "ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED", "ELEVENLABS_SCRIBE_REALTIME_ENABLED"):
            with self.subTest(flag=flag), override_settings(**{flag: False}), patch(
                    "apps.ai_core.providers.elevenlabs_realtime.open_request") as send:
                self.assertEqual(self.post().data["code"], "not_configured")
                send.assert_not_called()

    def test_foreign_business_and_anonymous_denied_before_provider(self):
        with patch("apps.ai_core.providers.elevenlabs_realtime.open_request") as send:
            self.api.force_authenticate(self.other_owner)
            self.assertEqual(self.post().status_code, 404)
            self.api.force_authenticate(None)
            self.assertIn(self.post().status_code, (401, 403))
            send.assert_not_called()

    def test_role_denial_and_post_provider_recheck(self):
        from rest_framework.exceptions import PermissionDenied
        for outcomes, calls in (([PermissionDenied()], 0), ([self.business, PermissionDenied()], 1)):
            with patch("apps.ai_core.speech_views.speech_scope", side_effect=outcomes), patch(
                    "apps.ai_core.providers.elevenlabs_realtime.open_request",
                    return_value=io.BytesIO(b'{"token":"single-use-synthetic-token"}')) as send:
                response = self.post()
                self.assertEqual(response.status_code, 403)
                self.assertNotIn("single-use", str(response.data))
                self.assertEqual(send.call_count, calls)

    def test_rate_limit_precedes_provider(self):
        throttle = ScopedRateThrottle()
        key = throttle.cache_format % {"scope": "ai_assistant", "ident": self.owner.pk}
        count, duration = throttle.parse_rate(throttle.THROTTLE_RATES["ai_assistant"])
        throttle.cache.set(key, [throttle.timer()] * count, duration)
        with patch("apps.ai_core.providers.elevenlabs_realtime.open_request") as send:
            self.assertEqual(self.post().status_code, 429)
            send.assert_not_called()

    def test_provider_errors_are_sanitized_without_retry(self):
        for failure, code in ((HTTPError("secret", 401, "secret", {}, None), "provider_rejected"),
                              (HTTPError("secret", 429, "secret", {}, None), "rate_limited"),
                              (TimeoutError("secret"), "speech_timeout")):
            with patch("apps.ai_core.providers.elevenlabs_realtime.open_request", side_effect=failure) as send:
                response = self.post()
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.data["code"], code)
            self.assertNotIn("secret", str(response.data))
            send.assert_called_once()

    def test_invalid_or_oversized_token_response(self):
        for body in ([], {"token": ""}, {"token": "contains spaces"}, {"token": "x" * 9000}):
            with patch("apps.ai_core.providers.elevenlabs_realtime.open_request",
                       return_value=io.BytesIO(json.dumps(body).encode())):
                self.assertEqual(self.post().data["code"], "invalid_response")
