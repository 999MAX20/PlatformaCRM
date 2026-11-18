from django.conf import settings

from apps.ai_core.providers import elevenlabs_speech


def speech_ready():
    if not settings.AI_ENABLED or not settings.VOICE_INPUT_ENABLED:
        return False
    if settings.VOICE_TRANSCRIPTION_PROVIDER == "elevenlabs":
        return elevenlabs_speech.is_configured()
    if settings.VOICE_TRANSCRIPTION_PROVIDER == "openrouter":
        return bool(settings.OPENROUTER_API_KEY and settings.OPENROUTER_BASE_URL)
    return False


def speech_model():
    if settings.VOICE_TRANSCRIPTION_PROVIDER == "elevenlabs":
        return elevenlabs_speech.DIAGNOSTIC_MODEL_ID
    return settings.VOICE_TRANSCRIPTION_MODEL
