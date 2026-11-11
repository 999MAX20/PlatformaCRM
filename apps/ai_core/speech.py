import base64
import io
import json
import logging
import time
import wave
from urllib import error, request

from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.ai_core.providers.base import AIProviderError
from apps.ai_core.providers.openrouter import OpenRouterProvider
from apps.ai_core.speech_numbers import normalize_spoken_phone
from apps.ai_core.speech_diagnostics import safe_model_id, safe_provider_id, speech_http_failure


logger = logging.getLogger(__name__)


MAX_AUDIO_BYTES = 2_000_000
MAX_AUDIO_SECONDS = 60

def _speech_request(content, language):
    payload = {"model": settings.VOICE_TRANSCRIPTION_MODEL, "temperature": 0,
        "input_audio": {"data": base64.b64encode(content).decode("ascii"), "format": "wav"},
        "provider": {"zdr": True, "data_collection": "deny"}}
    if language != "auto":
        payload["language"] = language
    return "/audio/transcriptions", payload


def _transcript(result, endpoint):
    if not isinstance(result, dict) or not isinstance(result.get("text"), str) or len(result["text"]) > 4000:
        raise AIProviderError(code="invalid_response", retryable=False)
    text = result["text"].strip()
    if not text:
        raise AIProviderError(code="no_speech", retryable=False)
    return text


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
    started = time.monotonic()
    diagnostic = {"speech_stage": "configuration", "speech_model": safe_model_id(settings.VOICE_TRANSCRIPTION_MODEL)}
    completed = False
    try:
        if not settings.AI_ENABLED or not settings.VOICE_INPUT_ENABLED or not settings.OPENROUTER_API_KEY or not settings.OPENROUTER_BASE_URL:
            raise AIProviderError(code="not_configured", retryable=False)
        provider = OpenRouterProvider()
        endpoint, payload = _speech_request(content, language)
        call = request.Request(provider.base_url.rstrip("/") + endpoint,
            data=json.dumps(payload).encode(), headers=provider._headers(), method="POST")
        diagnostic["speech_stage"] = "request"
        with request.urlopen(call, timeout=settings.VOICE_HTTP_TIMEOUT_SECONDS) as response:
            diagnostic["status_code"] = getattr(response, "status", 200)
            headers = getattr(response, "headers", {})
            diagnostic["speech_provider_request_id"] = safe_provider_id(headers.get("x-request-id"))
            diagnostic["speech_headers_ms"] = round((time.monotonic() - started) * 1000, 2)
            diagnostic["speech_stage"] = "response_body"
            raw = response.read(65537)
            if len(raw) > 65536:
                raise AIProviderError(code="invalid_response", retryable=False)
            diagnostic["speech_stage"] = "decode"
            result = json.loads(raw)
        diagnostic["speech_stage"] = "transcript"
        if isinstance(result, dict):
            diagnostic["speech_generation_id"] = safe_provider_id(result.get("id"))
        text = _transcript(result, endpoint)
        completed = True
        diagnostic["speech_stage"] = "completed"
        return {"text": normalize_spoken_phone(text), "duration_seconds": duration}
    except error.HTTPError as exc:
        code, retryable = speech_http_failure(exc.code)
        diagnostic.update(status_code=exc.code, speech_error_code=code, speech_exception_type="HTTPError")
        diagnostic["speech_provider_request_id"] = safe_provider_id((exc.headers or {}).get("x-request-id"))
        raise AIProviderError(code=code, retryable=retryable) from None
    except (TimeoutError, error.URLError, OSError) as exc:
        timeout = isinstance(exc, TimeoutError) or isinstance(getattr(exc, "reason", None), TimeoutError)
        code = "speech_timeout" if timeout else "provider_unavailable"
        diagnostic.update(speech_error_code=code, speech_exception_type="TimeoutError" if timeout else "NetworkError")
        raise AIProviderError(code=code, retryable=True) from None
    except (ValueError, UnicodeDecodeError):
        code = "invalid_response" if diagnostic["speech_stage"] == "decode" else "provider_rejected"
        diagnostic.update(speech_error_code=code, speech_exception_type="InvalidResponse" if code == "invalid_response" else "ConfigurationError")
        raise AIProviderError(code=code, retryable=False) from None
    except AIProviderError as exc:
        diagnostic["speech_error_code"] = exc.code
        raise
    finally:
        diagnostic["duration_ms"] = round((time.monotonic() - started) * 1000, 2)
        if completed:
            logger.info("ai.speech_request_completed", extra=diagnostic)
        else:
            diagnostic.setdefault("speech_error_code", "internal_error")
            logger.warning("ai.speech_provider_failed", extra=diagnostic)
