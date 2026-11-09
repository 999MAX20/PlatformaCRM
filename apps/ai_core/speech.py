import base64
import io
import json
import logging
import wave
from urllib import error, request

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.ai_core.providers.base import AIProviderError
from apps.ai_core.providers.openrouter import OpenRouterProvider


logger = logging.getLogger(__name__)


MAX_AUDIO_BYTES = 2_000_000
MAX_AUDIO_SECONDS = 60


def validate_audio(content):
    if not content or len(content) > MAX_AUDIO_BYTES:
        raise ValidationError({"audio": "audio_size"})
    try:
        with wave.open(io.BytesIO(content), "rb") as audio:
            frames = audio.getnframes()
            if audio.getnchannels() != 1 or audio.getsampwidth() != 2 or audio.getframerate() != 16000 or audio.getcomptype() != "NONE":
                raise ValueError
            if not 1600 <= frames <= 16000 * MAX_AUDIO_SECONDS:
                raise ValueError
            pcm = audio.readframes(frames)
            if len(pcm) != frames * 2:
                raise ValueError
            if not any(pcm):
                raise ValidationError({"audio": "audio_empty"})
            return frames / 16000
    except (wave.Error, EOFError, ValueError):
        raise ValidationError({"audio": "audio_format"}) from None


def transcribe_audio(content, language="auto"):
    duration = validate_audio(content)
    if language not in {"auto", "ru", "kk"}:
        raise ValidationError({"language": "invalid_language"})
    if not settings.AI_ENABLED or not settings.VOICE_INPUT_ENABLED or not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_BASE_URL:
        raise AIProviderError(code="not_configured", retryable=False)
    provider = OpenRouterProvider()
    payload = {"model": settings.VOICE_TRANSCRIPTION_MODEL,
        "input_audio": {"data": base64.b64encode(content).decode("ascii"), "format": "wav"},
        "provider": {"zdr": True, "data_collection": "deny"}}
    if language != "auto":
        payload["language"] = language
    try:
        call = request.Request(provider.base_url.rstrip("/") + "/audio/transcriptions",
            data=json.dumps(payload).encode(), headers=provider._headers(), method="POST")
        with request.urlopen(call, timeout=settings.VOICE_HTTP_TIMEOUT_SECONDS) as response:
            raw = response.read(65537)
            if len(raw) > 65536:
                raise ValueError
            result = json.loads(raw)
    except error.HTTPError as exc:
        retryable = exc.code in {408, 429} or exc.code >= 500
        code = "rate_limited" if exc.code == 429 else "provider_unavailable" if retryable else "provider_rejected"
        logger.warning("ai.speech_provider_failed", extra={"status_code": exc.code, "error_code": code})
        raise AIProviderError(code=code, retryable=retryable) from None
    except (OSError, ValueError, UnicodeDecodeError):
        raise AIProviderError(code="provider_unavailable") from None
    if not isinstance(result, dict) or not isinstance(result.get("text"), str) or len(result["text"]) > 4000:
        raise AIProviderError(code="invalid_response", retryable=False)
    text = result["text"].strip()
    if not text:
        raise AIProviderError(code="no_speech", retryable=False)
    return {"text": text, "duration_seconds": duration}
