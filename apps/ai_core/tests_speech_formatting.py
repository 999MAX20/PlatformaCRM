import json
import io
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from apps.ai_core.ai_client import AIClientError, AIClientResult
from apps.ai_core.speech_formatting import format_transcript


class SpeechFormattingTests(SimpleTestCase):
    @override_settings(AI_ENABLED=True, AI_PROVIDER="openrouter", OPENROUTER_API_KEY="synthetic",
                       OPENROUTER_BASE_URL="https://openrouter.ai/api/v1")
    def test_formatting_uses_private_openrouter_route_without_audio_or_tools(self):
        body = {"choices": [{"message": {"content": json.dumps({"text": "Салам, бро!"})}, "finish_reason": "stop"}]}
        with patch("apps.ai_core.providers.compatible.request.urlopen", return_value=io.BytesIO(json.dumps(body).encode())) as send:
            self.assertEqual(format_transcript("салам бро"), "Салам, бро!")
        payload = json.loads(send.call_args.args[0].data)
        self.assertEqual(payload["provider"], {"zdr": True, "data_collection": "deny"})
        self.assertEqual(payload["model"], "openai/gpt-4o-mini")
        self.assertNotIn("input_audio", payload)
        self.assertNotIn("tools", payload)

    def test_adds_punctuation_without_dropping_spoken_words(self):
        source = "создай задачу с названием позвонить поставщику"
        expected = "Создай задачу с названием «Позвонить поставщику»."
        with patch("apps.ai_core.speech_formatting.generate_text", return_value=AIClientResult(
                json.dumps({"text": expected}), "test", provider="test")) as generate:
            self.assertEqual(format_transcript(source), expected)
        self.assertFalse(generate.call_args.kwargs["allow_mock"])
        self.assertEqual(generate.call_args.kwargs["model"], "openai/gpt-4o-mini")

    def test_shortening_translation_changed_numbers_and_extra_keys_keep_original(self):
        original = "Позвони Ивану завтра в 10 часов"
        for value in ({"text": "Позвони Ивану"}, {"text": "Call Ivan tomorrow at 10"},
                      {"text": "Позвони Ивану завтра в 11 часов"},
                      {"text": original, "tool": "crm_create"}, []):
            with self.subTest(value=value), patch("apps.ai_core.speech_formatting.generate_text",
                    return_value=AIClientResult(json.dumps(value), "test", provider="test")):
                self.assertEqual(format_transcript(original), original)

    def test_formatting_failure_does_not_lose_transcription(self):
        with patch("apps.ai_core.speech_formatting.generate_text", side_effect=AIClientError()):
            self.assertEqual(format_transcript("Салам бро"), "Салам бро")
