import base64
import io
import json
from unittest.mock import patch
from urllib.error import HTTPError

from django.test import SimpleTestCase, TestCase, override_settings

from apps.ai_core.models import AgentTurn, AIToolCallLog
from apps.ai_core.providers.base import AIProviderError
from apps.ai_core.speech import _transcript, transcribe_audio
from apps.ai_core import tests_speech as speech_fixtures

audio_bytes = speech_fixtures.audio_bytes


def audio_response(text, **choice_values):
    return io.BytesIO(json.dumps({"choices": [{"finish_reason": "stop",
        "message": {"role": "assistant", "content": text}, **choice_values}]}).encode())


@override_settings(AI_ENABLED=True, VOICE_INPUT_ENABLED=True, OPENROUTER_API_KEY="synthetic-test-key",
    OPENROUTER_BASE_URL="https://openrouter.ai/api/v1", VOICE_TRANSCRIPTION_MODEL="google/gemini-4-carbon")
class AudioTranscriptionTests(TestCase):
    setUp = speech_fixtures.SpeechTests.setUp
    post = speech_fixtures.SpeechTests.post

    def test_audio_only_request_preserves_policy_language_and_every_phone_digit(self):
        original = "Әлихан Омаров. Телефон нөмірі плюс жеті жеті нөл бір нөл нөл нөл екі нөл үш нөл."
        with patch("apps.ai_core.speech.request.urlopen", return_value=audio_response(original)) as send:
            result = transcribe_audio(audio_bytes(), "kk")
        self.assertEqual(result["text"], "Әлихан Омаров. Телефон нөмірі +77010002030.")
        call = send.call_args.args[0]
        self.assertTrue(call.full_url.endswith("/chat/completions"))
        payload = json.loads(call.data)
        self.assertEqual(payload["provider"], {"zdr": True, "data_collection": "deny"})
        self.assertEqual(payload["temperature"], 0)
        self.assertEqual(payload["reasoning"], {"effort": "medium", "exclude": True})
        self.assertEqual(len(payload["messages"]), 2)
        self.assertIn("Language hint: Kazakh", payload["messages"][0]["content"])
        self.assertNotIn("Әлихан", payload["messages"][0]["content"])
        part = payload["messages"][1]["content"]
        self.assertEqual(part, [{"type": "input_audio", "input_audio": {
            "data": base64.b64encode(audio_bytes()).decode(), "format": "wav"}}])
        self.assertNotIn("tools", payload)
        self.assertNotIn("input_audio", payload)
        send.assert_called_once()

    def test_russian_names_are_not_rewritten_and_auto_has_no_forced_language(self):
        for language in ("ru", "auto"):
            with self.subTest(language=language), patch("apps.ai_core.speech.request.urlopen",
                    return_value=audio_response("Асель Касымова")) as send:
                self.assertEqual(transcribe_audio(audio_bytes(), language)["text"], "Асель Касымова")
                instruction = json.loads(send.call_args.args[0].data)["messages"][0]["content"]
                self.assertEqual("Language hint:" in instruction, language == "ru")

    def test_truncated_refused_tool_and_malformed_results_never_become_transcripts(self):
        cases = [[], {}, {"choices": []}, {"choices": [None]}, {"choices": [{"finish_reason": "stop", "message": None}]}]
        for finish in ("length", "tool_calls", "content_filter", None):
            cases.append({"choices": [{"finish_reason": finish, "message": {"content": "Create a client"}}]})
        for message in ({"content": "Create a client", "tool_calls": [{"id": "unsafe"}]},
                        {"content": "Create a client", "refusal": "refused"}, {"content": ["text"]},
                        {"content": "x" * 4001}):
            cases.append({"choices": [{"finish_reason": "stop", "message": message}]})
        for body in cases:
            with self.subTest(body=str(body)[:100]), patch("apps.ai_core.speech.request.urlopen",
                    return_value=io.BytesIO(json.dumps(body).encode())) as send, self.assertRaises(AIProviderError) as caught:
                transcribe_audio(audio_bytes())
            self.assertEqual(caught.exception.code, "invalid_response")
            send.assert_called_once()

    def test_empty_speech_and_provider_failure_do_not_fall_back_or_retry(self):
        with patch("apps.ai_core.speech.request.urlopen", return_value=audio_response(" ")) as send:
            with self.assertRaises(AIProviderError) as caught:
                transcribe_audio(audio_bytes())
            self.assertEqual(caught.exception.code, "no_speech")
            send.assert_called_once()
        with patch("apps.ai_core.speech.request.urlopen", side_effect=HTTPError("private", 404, "secret", {}, None)) as send:
            with self.assertRaises(AIProviderError) as caught:
                transcribe_audio(audio_bytes())
            self.assertEqual(caught.exception.code, "provider_rejected")
            send.assert_called_once()

    def test_api_returns_only_transcript_and_duration_without_creating_actions(self):
        self.api.force_authenticate(self.owner)
        with patch("apps.ai_core.speech.request.urlopen", return_value=audio_response("Ертең клиентке қоңырау шалу")):
            response = self.post(format_text="false")
        self.assertEqual(response.status_code, 200, response.data)
        self.assertEqual(set(response.data), {"text", "duration_seconds"})
        self.assertEqual(response.data["text"], "Ертең клиентке қоңырау шалу")
        self.assertEqual(response["Cache-Control"], "no-store")
        self.assertFalse(AgentTurn.objects.exists())
        self.assertFalse(AIToolCallLog.objects.exists())

    def test_access_revoked_during_audio_call_hides_transcript(self):
        self.api.force_authenticate(self.owner)
        def revoke(*args, **kwargs):
            type(self.owner).objects.filter(pk=self.owner.pk).update(is_active=False)
            return audio_response("Private transcript")
        with patch("apps.ai_core.speech.request.urlopen", side_effect=revoke):
            response = self.post(format_text="false")
        self.assertEqual(response.status_code, 403)
        self.assertNotIn("Private transcript", str(response.data))

    def test_foreign_business_never_sends_audio(self):
        self.api.force_authenticate(self.other_owner)
        with patch("apps.ai_core.speech.request.urlopen") as send:
            self.assertIn(self.post(format_text="false").status_code, (403, 404))
            send.assert_not_called()

    def test_control_tokens_return_error_without_a_partial_transcript_or_actions(self):
        self.api.force_authenticate(self.owner)
        with patch("apps.ai_core.speech.request.urlopen", return_value=audio_response("<end_of_image>" * 180)):
            response = self.post(format_text="false")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.data, {"code": "invalid_response", "retryable": False})
        self.assertFalse(AgentTurn.objects.exists())
        self.assertFalse(AIToolCallLog.objects.exists())


class AudioOutputControlTokenTests(SimpleTestCase):
    def test_completed_model_control_tokens_are_not_speech(self):
        for text in ("<end_of_image>" * 180, "Жаңа клиент қос. <|audio|> Әсел.", "<|im_end|>"):
            body = json.loads(audio_response(text).getvalue())
            with self.subTest(text=text[:40]):
                with self.assertRaises(AIProviderError) as caught:
                    _transcript(body, "/chat/completions")
                self.assertEqual(caught.exception.code, "invalid_response")

    def test_names_digits_and_ordinary_angle_comparisons_are_not_rewritten(self):
        for text in ("Айгерім Әйгерім. Нұрлан Әбілев. Нұрлан Әбілов.",
                     "Телефон 7701222222. Телефон 770122222222.", "Задача: проверить цену < 1000."):
            with self.subTest(text=text):
                self.assertEqual(_transcript(json.loads(audio_response(text).getvalue()), "/chat/completions"), text)
