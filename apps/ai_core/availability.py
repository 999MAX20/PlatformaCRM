"""Local configuration diagnostics; no provider request or live-health claim."""
from django.conf import settings
from rest_framework.exceptions import ValidationError

from apps.ai_core.runtime_policy import generation_policy
from apps.ai_core.ai_client import resolve_model
from apps.bots.ai_settings import validate_ai_settings


def generation_readiness(agent=None):
    provider = settings.AI_PROVIDER
    credentials = {
        "openai": (settings.OPENAI_API_KEY, settings.OPENAI_BASE_URL),
        "openrouter": (settings.OPENROUTER_API_KEY, settings.OPENROUTER_BASE_URL),
        "kimi": (settings.KIMI_API_KEY, settings.KIMI_BASE_URL),
    }
    configured = provider == "mock" or all(credentials.get(provider, (None, None)))
    try:
        model = generation_policy(prompt_type="crm_assistant", agent=agent).model if agent else resolve_model(prompt_type="crm_assistant")
    except ValidationError:
        model = None
    state = ("disabled" if not settings.AI_ENABLED else "not_configured" if not configured
             else "model_missing" if not model else "mock" if provider == "mock" else "configured")
    options = []
    for tier in ("smart", "fast", "cheap"):
        value = validate_ai_settings({"model": resolve_model(model_tier=tier)})["model"]
        if value and not any(item["value"] == value for item in options):
            options.append({"value": value, "tier": tier})
    return {"state": state, "configuration_ready": state in {"mock", "configured"},
            "provider": provider if provider in {*credentials, "mock"} else "unknown",
            "model": model or "", "model_options": options, "live_verified": False}
