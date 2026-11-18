import io
import json
from email import policy
from email.parser import BytesParser
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, TestCase, override_settings

from apps.ai_core import tests_speech as speech_fixtures
from apps.ai_core.models import AgentTurn
from apps.ai_core.providers import elevenlabs_speech
from apps.ai_core.providers.base import AIProviderError
from apps.ai_core.speech import transcribe_audio
from apps.ai_core.speech_configuration import speech_ready


DIRECT_SETTINGS = dict(
    AI_ENABLED=True, VOICE_INPUT_ENABLED=True, VOICE_TRANSCRIPTION_PROVIDER="elevenlabs",
    ELEVENLABS_API_KEY="synthetic-elevenlabs-key", ELEVENLABS_SCRIBE_ENABLED=True,
    ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED=True, VOICE_HTTP_TIMEOUT_SECONDS=60,
    OPENROUTER_API_KEY="", OPENROUTER_BASE_URL="",
    VOICE_TRANSCRIPTION_MODEL="google/gemini-4-carbon",
)


@override_settings(**DIRECT_SETTINGS)
class ElevenLabsSpeechTests(SimpleTestCase):
    def test_disabled_or_unconfirmed_configuration_never_sends_audio(self):
        for config in (
            {"ELEVENLABS_SCRIBE_ENABLED": False}, {"ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED": False},
            {"ELEVENLABS_API_KEY": ""}, {"VOICE_TRANSCRIPTION_PROVIDER": "unknown"},
            {"AI_ENABLED": False}, {"VOICE_INPUT_ENABLED": False},
        ):
            with self.subTest(config=config), override_settings(**config), \
                 patch("apps.ai_core.providers.elevenlabs_speech.open_request") as direct, \
                 patch("apps.ai_core.speech.request.urlopen") as router:
                self.assertFalse(speech_ready())
                with self.assertRaises(AIProviderError) as caught:
                    transcribe_audio(speech_fixtures.audio_bytes())
                self.assertEqual(caught.exception.code, "not_configured")
                direct.assert_not_called()
                router.assert_not_called()

    def test_v3_multipart_preserves_wav_and_uses_only_explicit_fields(self):
        audio = speech_fixtures.audio_bytes()
        for language in ("auto", "ru", "kk"):
            with self.subTest(language=language):
                call = elevenlabs_speech.build_request(audio, language)
                self.assertEqual(call.full_url, elevenlabs_speech.TRANSCRIPTION_URL)
                self.assertEqual(call.get_header("Xi-api-key"), "synthetic-elevenlabs-key")
                self.assertIsNone(call.get_header("Authorization"))
                mime = BytesParser(policy=policy.default).parsebytes(
                    f"Content-Type: {call.get_header('Content-type')}\r\n\r\n".encode() + call.data)
                fields = {part.get_param("name", header="content-disposition"): part.get_payload(decode=True)
                          for part in mime.iter_parts()}
                expected = {"model_id": b"scribe_v3", "numbers_format": b"words",
                    "tag_audio_events": b"false", "diarize": b"false", "timestamps_granularity": b"none",
                    "webhook": b"false", "use_multi_channel": b"false", "no_verbatim": b"false",
                    "temperature": b"0", "file": audio}
                if language != "auto":
                    expected.update(language_code=language.encode(),
                                    secondary_language_codes=b"kk" if language == "ru" else b"ru")
                self.assertEqual(fields, expected)

    def test_original_text_used_without_editing_or_openrouter_fallback(self):
        result = {"text": "Телефон плюс семь семь ноль один два три четыре пять шесть семь восемь",
                  "edited_transcript": "PRIVATE_SENTINEL", "words": []}
        with patch("apps.ai_core.providers.elevenlabs_speech.open_request",
                   return_value=io.BytesIO(json.dumps(result).encode())) as direct, \
             patch("apps.ai_core.speech.request.urlopen") as router, \
             self.assertLogs("apps.ai_core.speech", level="INFO") as logs:
            self.assertEqual(transcribe_audio(speech_fixtures.audio_bytes(), "ru")["text"],
                             "Телефон +77012345678")
        direct.assert_called_once()
        self.assertEqual(direct.call_args.kwargs["timeout"], 60)
        router.assert_not_called()
        self.assertEqual(logs.records[0].speech_model, "elevenlabs/scribe-v3")
        self.assertNotIn("PRIVATE_SENTINEL", str(logs.records[0].__dict__))

    def test_errors_are_safe_with_no_retry_or_fallback(self):
        cases = [(HTTPError("PRIVATE_SENTINEL", 403, "PRIVATE_SENTINEL", {}, None), "provider_rejected", False),
                 (HTTPError("PRIVATE_SENTINEL", 402, "PRIVATE_SENTINEL", {}, None), "speech_payment_required", False),
                 (HTTPError("PRIVATE_SENTINEL", 429, "PRIVATE_SENTINEL", {}, None), "rate_limited", True),
                 (TimeoutError("PRIVATE_SENTINEL"), "speech_timeout", True)]
        for failure, code, retryable in cases:
            with self.subTest(code=code), \
                 patch("apps.ai_core.providers.elevenlabs_speech.open_request", side_effect=failure) as direct, \
                 patch("apps.ai_core.speech.request.urlopen") as router, \
                 self.assertLogs("apps.ai_core.speech") as logs:
                with self.assertRaises(AIProviderError) as caught:
                    transcribe_audio(speech_fixtures.audio_bytes())
                self.assertEqual((caught.exception.code, caught.exception.retryable), (code, retryable))
                self.assertNotIn("PRIVATE_SENTINEL", str(logs.records[0].__dict__))
                direct.assert_called_once()
                router.assert_not_called()

    def test_invalid_response_never_becomes_a_command(self):
        for body in (b"invalid", b'{"text":42}', b'{"edited_transcript":"not original"}', b"x" * 65537):
            with self.subTest(size=len(body)), \
                 patch("apps.ai_core.providers.elevenlabs_speech.open_request", return_value=io.BytesIO(body)):
                with self.assertRaises(AIProviderError) as caught:
                    transcribe_audio(speech_fixtures.audio_bytes())
                self.assertEqual(caught.exception.code, "invalid_response")

    def test_redirect_cannot_forward_audio_or_key(self):
        call = elevenlabs_speech.build_request(speech_fixtures.audio_bytes(), "auto")
        with self.assertRaises(AIProviderError) as caught:
            elevenlabs_speech._NoRedirect().redirect_request(call, None, 302, "Found", {}, "https://other.invalid")
        self.assertEqual(caught.exception.code, "provider_rejected")
        self.assertFalse(caught.exception.retryable)


@override_settings(**DIRECT_SETTINGS)
class ElevenLabsSpeechAPITests(TestCase):
    setUp = speech_fixtures.SpeechTests.setUp
    post = speech_fixtures.SpeechTests.post

    def test_ready_uses_direct_provider_without_exposing_credentials(self):
        self.api.force_authenticate(self.owner)
        response = self.api.get("/api/ai/speech/", {"business": self.business.pk})
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.data["ready"])
        self.assertNotIn("synthetic-elevenlabs-key", str(response.data))
        with override_settings(ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED=False):
            self.assertFalse(self.api.get("/api/ai/speech/", {"business": self.business.pk}).data["ready"])
            with patch("apps.ai_core.providers.elevenlabs_speech.open_request") as direct:
                response = self.post(format_text="false")
            self.assertEqual(response.status_code, 503)
            self.assertEqual(response.data, {"code": "not_configured", "retryable": False})
            direct.assert_not_called()
        self.assertFalse(AgentTurn.objects.exists())

    def test_upload_uses_existing_permission_boundary(self):
        self.api.force_authenticate(user=None)
        with patch("apps.ai_core.providers.elevenlabs_speech.open_request") as direct:
            response = self.post(format_text="false")
        self.assertIn(response.status_code, (401, 403))
        direct.assert_not_called()
