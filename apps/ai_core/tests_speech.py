import io
import json
import wave
from unittest.mock import patch
from urllib.error import HTTPError

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import ScopedRateThrottle

from apps.ai_core import tests_conversation_memory as fixtures
from apps.ai_core.models import AgentTurn, AIRequestLog
from apps.ai_core.speech import transcribe_audio, validate_audio
from apps.ai_core.providers.base import AIProviderError


def audio_bytes(seconds=1):
    stream = io.BytesIO()
    with wave.open(stream, "wb") as audio:
        audio.setparams((1, 2, 16000, 0, "NONE", "not compressed"))
        audio.writeframes(b"\x10\x00" * int(seconds * 16000))
    return stream.getvalue()


@override_settings(AI_ENABLED=True, VOICE_INPUT_ENABLED=True, VOICE_TRANSCRIPTION_PROVIDER="openrouter", OPENROUTER_API_KEY="synthetic-test-key",
    OPENROUTER_BASE_URL="https://openrouter.ai/api/v1",
    VOICE_TRANSCRIPTION_MODEL="elevenlabs/scribe-v2", VOICE_HTTP_TIMEOUT_SECONDS=60)
class SpeechTests(TestCase):
    def setUp(self):
        fixtures.ConversationMemoryTests.setUp(self)
        # Database rollback reuses user IDs; throttle cache outlives each test.
        keys = [ScopedRateThrottle.cache_format % {"scope": "ai_assistant", "ident": user.pk}
                for user in (self.owner, self.other_owner)]
        ScopedRateThrottle.cache.delete_many(keys)
        self.addCleanup(ScopedRateThrottle.cache.delete_many, keys)

    def test_speech_requests_still_enforce_rate_limit(self):
        self.api.force_authenticate(self.owner)
        throttle = ScopedRateThrottle()
        key = throttle.cache_format % {"scope": "ai_assistant", "ident": self.owner.pk}
        count, duration = throttle.parse_rate(throttle.THROTTLE_RATES["ai_assistant"])
        throttle.cache.set(key, [throttle.timer()] * count, duration)
        with patch("apps.ai_core.speech_views.transcribe_audio") as transcribe:
            response = self.post(format_text="false")
        self.assertEqual(response.status_code, 429, response.data)
        transcribe.assert_not_called()

    def post(self, content=None, **values):
        return self.api.post("/api/ai/speech/", {"business": self.business.pk,
            "audio": SimpleUploadedFile("recording.wav", content if content is not None else audio_bytes(), content_type="audio/wav"),
            **values}, format="multipart")

    def test_direct_capture_skips_punctuation_provider(self):
        self.api.force_authenticate(self.owner)
        with patch("apps.ai_core.speech_views.transcribe_audio", return_value={"text": "Create Call task"}), \
             patch("apps.ai_core.speech_views.format_transcript") as formatting:
            response = self.post(format_text="false")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["text"], "Create Call task")
        formatting.assert_not_called()

    def test_direct_capture_preserves_dictated_phone_before_command_planning(self):
        self.api.force_authenticate(self.owner)
        text = "Запиши Ивана Иванова телефон плюс семь семь ноль два два два два два два два два к Анне"
        with patch("apps.ai_core.speech.request.urlopen", return_value=io.BytesIO(json.dumps({"text": text}).encode())) as send, \
             patch("apps.ai_core.speech_views.format_transcript") as formatting:
            response = self.post(format_text="false")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["text"], "Запиши Ивана Иванова телефон +77022222222 к Анне")
        send.assert_called_once()
        formatting.assert_not_called()
        self.assertFalse(AgentTurn.objects.exists())

    def test_adapter_sends_audio_only_and_policy_without_chat_tools(self):
        response = io.BytesIO(json.dumps({"text": "Ертең клиентке хабарлас", "usage": {"cost": 0.001}}).encode())
        with patch("apps.ai_core.speech.request.urlopen", return_value=response) as send:
            result = transcribe_audio(audio_bytes(), "kk")
        call = send.call_args.args[0]
        self.assertTrue(call.full_url.endswith("/audio/transcriptions"))
        payload = json.loads(call.data)
        self.assertEqual(payload["model"], "elevenlabs/scribe-v2")
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["language"], "kk")
        self.assertEqual(payload["provider"], {"zdr": True, "data_collection": "deny"})
        self.assertNotIn("tools", payload)
        self.assertNotIn("messages", payload)
        self.assertEqual(result["text"], "Ертең клиентке хабарлас")

    def test_bad_truncated_silent_and_long_audio_rejected_before_provider(self):
        for content in (b"not audio", audio_bytes()[:-100], audio_bytes(61), b"", audio_bytes().replace(b"\x10\x00", b"\x00\x00")):
            with self.subTest(size=len(content)), patch("apps.ai_core.speech.request.urlopen") as send:
                with self.assertRaises(ValidationError):
                    transcribe_audio(content)
                send.assert_not_called()

    def test_provider_errors_do_not_expose_private_body(self):
        with patch("apps.ai_core.speech.request.urlopen", side_effect=HTTPError("private-url", 429, "secret-token", {}, None)):
            with self.assertRaises(AIProviderError) as caught:
                transcribe_audio(audio_bytes())
        self.assertEqual(caught.exception.code, "rate_limited")
        self.assertNotIn("secret", str(caught.exception))
        for body, code in (({"text": ""}, "no_speech"), ({"text": "x" * 4001}, "invalid_response"), ([], "invalid_response")):
            with patch("apps.ai_core.speech.request.urlopen", return_value=io.BytesIO(json.dumps(body).encode())):
                with self.assertRaises(AIProviderError) as caught:
                    transcribe_audio(audio_bytes())
                self.assertEqual(caught.exception.code, code)

    def test_api_returns_transcript_without_creating_turn_or_crm_mutation(self):
        self.api.force_authenticate(self.owner)
        before = AIRequestLog.objects.count()
        with patch("apps.ai_core.speech.request.urlopen", return_value=io.BytesIO(b'{"text":"Create a task"}')):
            response = self.post()
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(response.data["text"], "Create a task")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertEqual(AgentTurn.objects.count(), 0)
        self.assertEqual(AIRequestLog.objects.count(), before)

    def test_foreign_business_and_disabled_account_never_reach_provider(self):
        self.api.force_authenticate(self.other_owner)
        with patch("apps.ai_core.speech.request.urlopen") as send:
            self.assertIn(self.post().status_code, (403, 404))
            send.assert_not_called()
        self.api.force_authenticate(self.owner)
        self.owner.is_active = False
        self.owner.save(update_fields=["is_active"])
        with patch("apps.ai_core.speech.request.urlopen") as send:
            self.assertEqual(self.post().status_code, 403)
            send.assert_not_called()

    def test_revocation_during_transcription_hides_text(self):
        self.api.force_authenticate(self.owner)
        def revoke(*args, **kwargs):
            type(self.owner).objects.filter(pk=self.owner.pk).update(is_active=False)
            return io.BytesIO(b'{"text":"Private transcript"}')
        with patch("apps.ai_core.speech.request.urlopen", side_effect=revoke):
            response = self.post()
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Private transcript", str(response.data))

    def test_missing_provider_and_oversize_upload_have_safe_recovery(self):
        self.api.force_authenticate(self.owner)
        with override_settings(OPENROUTER_API_KEY=""):
            self.assertFalse(self.api.get("/api/ai/speech/", {"business": self.business.pk}).data["ready"])
            self.assertEqual(self.post().data["code"], "not_configured")
        with patch("apps.ai_core.speech.request.urlopen") as send:
            self.assertEqual(self.post(b"x" * 2_000_001).status_code, 400)
            send.assert_not_called()

    def test_provider_rejection_logs_only_status_and_never_retries(self):
        for status in (400, 401, 402, 403, 404):
            with self.subTest(status=status), patch("apps.ai_core.speech.request.urlopen",
                    side_effect=HTTPError("https://private.invalid/token", status, "private-secret", {}, io.BytesIO(b"private audio"))):
                with self.assertLogs("apps.ai_core.speech", level="WARNING") as logs, self.assertRaises(AIProviderError) as caught:
                    transcribe_audio(audio_bytes())
                self.assertEqual(caught.exception.code, "speech_payment_required" if status == 402 else "provider_rejected")
                self.assertFalse(caught.exception.retryable)
                self.assertEqual(logs.records[0].status_code, status)
                self.assertNotIn("private", str(logs.records[0].__dict__))

    def test_temporary_provider_failure_remains_retryable(self):
        with patch("apps.ai_core.speech.request.urlopen", side_effect=HTTPError("private", 503, "private", {}, None)):
            with self.assertRaises(AIProviderError) as caught:
                transcribe_audio(audio_bytes())
        self.assertEqual(caught.exception.code, "provider_unavailable")
        self.assertTrue(caught.exception.retryable)

    def test_api_error_codes_are_safe_and_never_create_commands(self):
        self.api.force_authenticate(self.owner)
        before = (AgentTurn.objects.count(), AIRequestLog.objects.count())
        for failure, code, retryable in (
            (HTTPError("PRIVATE_SENTINEL", 402, "PRIVATE_SENTINEL", {}, None), "speech_payment_required", False),
            (TimeoutError("PRIVATE_SENTINEL"), "speech_timeout", True),
            (HTTPError("PRIVATE_SENTINEL", 503, "PRIVATE_SENTINEL", {}, None), "provider_unavailable", True),
        ):
            with self.subTest(code=code), patch("apps.ai_core.speech.request.urlopen", side_effect=failure) as send:
                response = self.post(format_text="false")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.data, {"code": code, "retryable": retryable})
            self.assertNotIn("PRIVATE_SENTINEL", str(response.data))
            send.assert_called_once()
            self.assertEqual((AgentTurn.objects.count(), AIRequestLog.objects.count()), before)
