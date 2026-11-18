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
    def test_keyterms_are_bounded_names_in_repeated_multipart_fields(self):
        terms = ["Әсел Қасымова", "Әсел Қасымова", "Әсем", "x\r\ninjected", "123", "a" * 51]
        call = elevenlabs_speech.build_request(b"synthetic", "kk", keyterms=terms)
        mime = BytesParser(policy=policy.default).parsebytes(
            f"Content-Type: {call.get_header('Content-type')}\r\n\r\n".encode() + call.data)
        actual = [part.get_payload(decode=True).decode() for part in mime.iter_parts()
                  if part.get_param("name", header="content-disposition") == "keyterms"]
        self.assertEqual(actual, ["Әсел Қасымова", "Әсем"])
        self.assertEqual(len(elevenlabs_speech.bounded_name_terms(["Name " + chr(65 + i) for i in range(20)])), 10)
        with override_settings(ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED=False):
            with self.assertRaises(AIProviderError):
                elevenlabs_speech.build_request(b"synthetic", "kk", keyterms=terms)

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

    def test_malformed_context_is_rejected_before_provider(self):
        self.api.force_authenticate(self.owner)
        with patch("apps.ai_core.speech_views.transcribe_audio") as transcribe:
            for value in ([1], {"entity": [], "id": 1}, {"entity": "clients", "id": True},
                          {"entity": "clients", "id": 1, "name": "Untrusted"}):
                with self.subTest(value=value):
                    response = self.post(format_text="false", current_entity=json.dumps(value))
                    self.assertEqual(response.status_code, 400)
            transcribe.assert_not_called()

    def test_opted_in_card_names_are_scoped_and_not_stored(self):
        from apps.clients.models import Client
        from apps.ai_core.models import AIRequestLog, AgentProfile
        from apps.bots.models import Bot
        Bot.objects.filter(business=self.business).update(status="paused")
        AgentProfile.objects.filter(business=self.business).update(is_active=False)
        own = Client.objects.create(business=self.business, full_name="Әсел Қасымова")
        other = Client.objects.create(business=self.other_business, full_name="Foreign Sentinel")
        self.api.force_authenticate(self.owner)
        with patch("apps.ai_core.speech_views.transcribe_audio", return_value={"text": "synthetic"}) as transcribe:
            self.assertEqual(self.post(format_text="false").status_code, 200)
            self.assertEqual(transcribe.call_args.kwargs["keyterms"], [])
            response = self.post(format_text="false", current_entity=json.dumps({"entity": "clients", "id": own.pk}))
            self.assertEqual(response.status_code, 200, response.data)
            self.assertEqual(transcribe.call_args.kwargs["keyterms"], ["Әсел Қасымова", "Әсел", "Қасымова"])
            transcribe.reset_mock()
            response = self.post(format_text="false", current_entity=json.dumps({"entity": "clients", "id": other.pk}))
            self.assertEqual(response.status_code, 403)
            transcribe.assert_not_called()
        self.assertFalse(AIRequestLog.objects.exists())
        self.assertFalse(AgentTurn.objects.exists())

    def test_linked_client_scope_and_archived_names(self):
        from apps.clients.models import Client
        from apps.tasks.models import Task
        own = Client.objects.create(business=self.business, full_name="Әсем")
        foreign = Client.objects.create(business=self.other_business, full_name="Foreign Sentinel")
        task = Task.objects.create(business=self.business, title="Synthetic", client=own)
        self.api.force_authenticate(self.owner)
        context = json.dumps({"entity": "tasks", "id": task.pk})
        with patch("apps.ai_core.speech_views.transcribe_audio", return_value={"text": "synthetic"}) as transcribe:
            self.assertEqual(self.post(format_text="false", current_entity=context).status_code, 200)
            self.assertEqual(transcribe.call_args.kwargs["keyterms"], ["Әсем"])
            Client.objects.filter(pk=own.pk).update(is_archived=True)
            self.assertEqual(self.post(format_text="false", current_entity=context).status_code, 200)
            self.assertEqual(transcribe.call_args.kwargs["keyterms"], [])
            Task.objects.filter(pk=task.pk).update(client=foreign)
            transcribe.reset_mock()
            self.assertEqual(self.post(format_text="false", current_entity=context).status_code, 403)
            transcribe.assert_not_called()

    def test_context_revoked_during_transcription_does_not_return_text(self):
        from apps.clients.models import Client
        own = Client.objects.create(business=self.business, full_name="Әсем")
        self.api.force_authenticate(self.owner)
        def transcribe(*args, **kwargs):
            Client.objects.filter(pk=own.pk).update(business=self.other_business)
            return {"text": "PRIVATE_SENTINEL"}
        with patch("apps.ai_core.speech_views.transcribe_audio", side_effect=transcribe):
            response = self.post(format_text="false", current_entity=json.dumps({"entity": "clients", "id": own.pk}))
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("PRIVATE_SENTINEL", str(response.data))

    def test_disabled_privacy_does_not_read_context_names(self):
        self.api.force_authenticate(self.owner)
        with override_settings(ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED=False), \
             patch("apps.ai_core.speech_context.target_for_command") as read, \
             patch("apps.ai_core.providers.elevenlabs_speech.open_request") as send:
            response = self.post(format_text="false", current_entity=json.dumps({"entity": "clients", "id": 1}))
        self.assertEqual(response.status_code, 503)
        read.assert_not_called()
        send.assert_not_called()

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
