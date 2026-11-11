import io
import json
import logging
from unittest.mock import patch
from urllib.error import HTTPError, URLError

from django.test import SimpleTestCase, override_settings

from apps.ai_core.providers.base import AIProviderError
from apps.ai_core.speech import transcribe_audio
from apps.ai_core.tests_speech import audio_bytes
from apps.core.logging import JsonLogFormatter, RequestContextFilter, request_id_context


class Response(io.BytesIO):
    status = 200
    headers = {"x-request-id": "req-safe-123", "Authorization": "Bearer PRIVATE_SENTINEL"}


@override_settings(AI_ENABLED=True, VOICE_INPUT_ENABLED=True, OPENROUTER_API_KEY="PRIVATE_SENTINEL",
                   OPENROUTER_BASE_URL="https://openrouter.ai/api/v1", VOICE_TRANSCRIPTION_MODEL="elevenlabs/scribe-v2")
class SpeechDiagnosticsTests(SimpleTestCase):
    def formatted(self, record):
        RequestContextFilter().filter(record)
        return json.loads(JsonLogFormatter().format(record))

    def test_status_codes_are_actionable_and_never_log_error_body_or_secret(self):
        for status, code, retryable in ((402, "speech_payment_required", False), (401, "provider_rejected", False),
                (403, "provider_rejected", False), (404, "provider_rejected", False), (429, "rate_limited", True),
                (408, "speech_timeout", True), (504, "speech_timeout", True), (503, "provider_unavailable", True)):
            with self.subTest(status=status):
                error = HTTPError("https://PRIVATE_SENTINEL", status, "PRIVATE_SENTINEL", Response.headers, io.BytesIO(b"PRIVATE_SENTINEL"))
                with patch("apps.ai_core.speech.request.urlopen", side_effect=error) as send, self.assertLogs("apps.ai_core.speech") as logs:
                    with self.assertRaises(AIProviderError) as caught:
                        transcribe_audio(audio_bytes())
                self.assertEqual((caught.exception.code, caught.exception.retryable), (code, retryable))
                send.assert_called_once()
                payload = self.formatted(logs.records[0])
                self.assertEqual(payload["speech_stage"], "request")
                self.assertEqual(payload["speech_error_code"], code)
                self.assertEqual(payload["status_code"], status)
                self.assertEqual(payload["speech_provider_request_id"], "req-safe-123")
                self.assertGreaterEqual(payload["duration_ms"], 0)
                self.assertNotIn("PRIVATE_SENTINEL", json.dumps(payload))

    def test_timeout_phase_distinguishes_headers_from_body_and_network_error(self):
        class BodyTimeout(Response):
            def read(self, *args):
                raise TimeoutError("PRIVATE_SENTINEL")
        cases = [(TimeoutError("PRIVATE_SENTINEL"), "request", "speech_timeout"),
                 (URLError(TimeoutError("PRIVATE_SENTINEL")), "request", "speech_timeout"),
                 (URLError("PRIVATE_SENTINEL"), "request", "provider_unavailable"),
                 (BodyTimeout(), "response_body", "speech_timeout")]
        for result, stage, code in cases:
            with self.subTest(stage=stage, code=code):
                options = {"side_effect": result} if isinstance(result, Exception) else {"return_value": result}
                with patch("apps.ai_core.speech.request.urlopen", **options) as send, self.assertLogs("apps.ai_core.speech") as logs:
                    with self.assertRaises(AIProviderError) as caught:
                        transcribe_audio(audio_bytes())
                self.assertEqual(caught.exception.code, code)
                send.assert_called_once()
                payload = self.formatted(logs.records[0])
                self.assertEqual(payload["speech_stage"], stage)
                self.assertNotIn("PRIVATE_SENTINEL", json.dumps(payload))

    def test_invalid_and_empty_responses_have_distinct_codes_without_content(self):
        for raw, stage, code in ((b"PRIVATE_SENTINEL", "decode", "invalid_response"),
                (b'{"text":""}', "transcript", "no_speech"), (b"x" * 65537, "response_body", "invalid_response")):
            with self.subTest(stage=stage), patch("apps.ai_core.speech.request.urlopen", return_value=Response(raw)), self.assertLogs("apps.ai_core.speech") as logs:
                with self.assertRaises(AIProviderError) as caught:
                    transcribe_audio(audio_bytes())
            self.assertEqual(caught.exception.code, code)
            self.assertFalse(caught.exception.retryable)
            payload = self.formatted(logs.records[0])
            self.assertEqual(payload["speech_stage"], stage)
            self.assertNotIn("PRIVATE_SENTINEL", json.dumps(payload))

    def test_success_keeps_correlation_but_not_transcript_audio_or_credentials(self):
        token = request_id_context.set("local-correlation")
        try:
            with patch("apps.ai_core.speech.request.urlopen", return_value=Response(b'{"id":"gen-safe-456","text":"PRIVATE_SENTINEL"}')), self.assertLogs("apps.ai_core.speech", level="INFO") as logs:
                self.assertEqual(transcribe_audio(audio_bytes())["text"], "PRIVATE_SENTINEL")
            payload = self.formatted(logs.records[0])
            self.assertEqual(payload["request_id"], "local-correlation")
            self.assertEqual(payload["speech_generation_id"], "gen-safe-456")
            self.assertEqual(payload["speech_model"], "elevenlabs/scribe-v2")
            self.assertEqual(payload["speech_stage"], "completed")
            self.assertNotIn("PRIVATE_SENTINEL", json.dumps(payload))
        finally:
            request_id_context.reset(token)

    def test_untrusted_metadata_is_not_logged_and_unrelated_logger_is_unchanged(self):
        response = Response(b'{"id":"https://PRIVATE_SENTINEL","text":"PRIVATE_SENTINEL"}')
        response.headers = {"x-request-id": "PRIVATE_SENTINEL\nAuthorization: secret"}
        with override_settings(VOICE_TRANSCRIPTION_MODEL="https://PRIVATE_SENTINEL"), patch("apps.ai_core.speech.request.urlopen", return_value=response), self.assertLogs("apps.ai_core.speech", level="INFO") as logs:
            transcribe_audio(audio_bytes())
        payload = self.formatted(logs.records[0])
        self.assertEqual(payload["speech_model"], "unrecognized")
        self.assertNotIn("speech_generation_id", payload)
        self.assertNotIn("speech_provider_request_id", payload)
        self.assertNotIn("PRIVATE_SENTINEL", json.dumps(payload))
        record = logging.LogRecord("unrelated", logging.INFO, "", 1, "ordinary event", (), None)
        record.speech_model = "PRIVATE_SENTINEL"
        self.assertNotIn("speech_model", self.formatted(record))
