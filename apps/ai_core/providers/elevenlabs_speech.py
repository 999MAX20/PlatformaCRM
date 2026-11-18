from urllib import request
from uuid import uuid4

from django.conf import settings

from apps.ai_core.providers.base import AIProviderError


MODEL_ID = "scribe_v3"
DIAGNOSTIC_MODEL_ID = "elevenlabs/scribe-v3"
TRANSCRIPTION_URL = "https://api.elevenlabs.io/v1/speech-to-text?enable_logging=false"


def is_configured():
    return bool(settings.ELEVENLABS_SCRIBE_ENABLED and settings.ELEVENLABS_API_KEY
                and settings.ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED)


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward audio or the API key, even to another ElevenLabs URL.
        raise AIProviderError(code="provider_rejected", retryable=False)


def build_request(content, language):
    if not is_configured():
        raise AIProviderError(code="not_configured", retryable=False)
    if language not in {"auto", "ru", "kk"}:
        raise AIProviderError(code="provider_rejected", retryable=False)
    fields = [
        ("model_id", MODEL_ID), ("numbers_format", "words"),
        ("tag_audio_events", "false"), ("diarize", "false"),
        ("timestamps_granularity", "none"), ("webhook", "false"),
        ("use_multi_channel", "false"), ("no_verbatim", "false"),
        ("temperature", "0"),
    ]
    if language != "auto":
        fields.extend([("language_code", language),
                       ("secondary_language_codes", "kk" if language == "ru" else "ru")])
    boundary = "platforma-" + uuid4().hex
    while boundary.encode("ascii") in content:
        boundary = "platforma-" + uuid4().hex
    parts = []
    for name, value in fields:
        parts.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"'
                      f'\r\n\r\n{value}\r\n').encode("utf-8"))
    parts.extend([
        (f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="recording.wav"'
         '\r\nContent-Type: audio/wav\r\n\r\n').encode("ascii"),
        content, f"\r\n--{boundary}--\r\n".encode("ascii"),
    ])
    return request.Request(TRANSCRIPTION_URL, data=b"".join(parts), method="POST", headers={
        "xi-api-key": settings.ELEVENLABS_API_KEY,
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Accept": "application/json",
    })


def open_request(call, *, timeout):
    return request.build_opener(_NoRedirect()).open(call, timeout=timeout)
