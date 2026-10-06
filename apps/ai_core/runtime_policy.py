"""One saved model policy for every stage of an agent's execution."""
from dataclasses import dataclass
import hashlib
import json

from django.conf import settings

from apps.ai_core.ai_client import resolve_model
from apps.bots.ai_settings import validate_ai_settings


STRUCTURED_STAGES = frozenset({
    "conversation_qualification", "crm_action_plan", "agent_turn_plan",
    "agent_memory_summary", "business_event_analyst",
})
JSON_STAGES = STRUCTURED_STAGES | {"crm_assistant", "daily_summary", "business_history_analyst"}
# These are the existing selectable profiles, not a promise about arbitrary
# providers. Unknown/custom models retain the compatible text contract.
JSON_MODELS = frozenset({"gpt-4o", "gpt-4o-mini", "gpt-4.1", "gpt-4.1-mini"})


@dataclass(frozen=True)
class GenerationPolicy:
    model: str | None
    model_tier: str | None
    temperature: float | None
    language: str | None
    structured: bool
    json_output: bool


def generation_policy(*, prompt_type, agent=None, profile=None, configuration=None,
                      model=None, model_tier=None, temperature=None, language=None):
    structured = prompt_type in STRUCTURED_STAGES
    if agent is not None:
        saved = validate_ai_settings(agent.settings_json or {})
        # An agent's default tier is also coherent across stages; the former
        # qualification-specific "smart" fallback must not override this choice.
        model_tier = saved.get("model_tier") or settings.AI_DEFAULT_MODEL_TIER
        model = resolve_model(model=saved.get("model") or None, model_tier=model_tier)
        temperature = saved.get("temperature", settings.AI_TEMPERATURE)
        temperature = settings.AI_TEMPERATURE if temperature is None else temperature
        language = (configuration or {}).get("language") or (profile.language if profile else agent.default_language)
        if structured:
            temperature = min(temperature, 0.2)
    short_model = (model or "").removeprefix("openai/")
    return GenerationPolicy(model, model_tier, temperature, language, structured,
                            prompt_type in JSON_STAGES and short_model in JSON_MODELS)


def policy_fingerprint(agent, profile):
    fields = ("name", "role_description", "tone", "language", "is_active", "system_prompt",
              "rules_json", "allowed_tools_json", "escalation_rules_json")
    payload = {"agent": agent.pk, "status": agent.status, "language": agent.default_language,
               "settings": agent.settings_json,
               "profile": {field: getattr(profile, field) for field in fields} if profile else None}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False).encode()).hexdigest()
