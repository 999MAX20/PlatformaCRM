import json
from urllib import error, request

from django.conf import settings

from apps.ai_core.providers.base import AIProviderError
from apps.ai_core.providers.elevenlabs_speech import is_configured, open_request
from apps.ai_core.speech_diagnostics import speech_http_failure


SESSION_SECONDS = 75
TOKEN_URL = f"https://api.elevenlabs.io/v1/single-use-token/realtime_scribe?max_session_duration_seconds={SESSION_SECONDS}"


def realtime_ready():
    return bool(settings.AI_ENABLED and settings.VOICE_INPUT_ENABLED
                and settings.ELEVENLABS_SCRIBE_REALTIME_ENABLED and is_configured())


def create_session_token():
    if not realtime_ready():
        raise AIProviderError(code="not_configured", retryable=False)
    call = request.Request(TOKEN_URL, data=b"", method="POST", headers={
        "xi-api-key": settings.ELEVENLABS_API_KEY, "Accept": "application/json",
    })
    try:
        with open_request(call, timeout=10) as response:
            raw = response.read(8193)
        if len(raw) > 8192:
            raise ValueError
        body = json.loads(raw)
        token = body.get("token") if isinstance(body, dict) else None
        if not isinstance(token, str) or not 10 <= len(token) <= 4096 or not token.isascii() or any(c.isspace() for c in token):
            raise ValueError
        return token
    except error.HTTPError as exc:
        code, retryable = speech_http_failure(exc.code)
        raise AIProviderError(code=code, retryable=retryable) from None
    except (TimeoutError, error.URLError):
        raise AIProviderError(code="speech_timeout", retryable=True) from None
    except (ValueError, UnicodeError):
        raise AIProviderError(code="invalid_response", retryable=False) from None
