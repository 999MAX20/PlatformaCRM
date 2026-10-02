import math

from django.conf import settings
from rest_framework.exceptions import ValidationError


def validate_ai_settings(value):
    if not isinstance(value, dict):
        raise ValidationError("Agent settings must be an object.")
    value = dict(value)
    temperature = value.get("temperature")
    if temperature is not None:
        if isinstance(temperature, bool) or not isinstance(temperature, (int, float)) or not math.isfinite(temperature) or not 0 <= temperature <= 1:
            raise ValidationError("Temperature must be a number between 0 and 1.")
    model = value.get("model")
    if model is not None and (not isinstance(model, str) or len(model) > 128):
        raise ValidationError("Invalid model selection.")
    if settings.AI_PROVIDER == "openrouter" and model in {"gpt-4.1", "gpt-4.1-mini", "gpt-4o", "gpt-4o-mini"}:
        value["model"] = f"openai/{model}"
    tier = value.get("model_tier")
    if tier is not None and (not isinstance(tier, str) or tier not in {"fast", "smart", "cheap"}):
        raise ValidationError("Invalid model tier.")
    pipeline = value.get("auto_crm_pipeline")
    if pipeline is not None:
        if not isinstance(pipeline, dict):
            raise ValidationError("Automation settings must be an object.")
        for key in ("enabled", "auto_send_reply", "create_appointment", "require_review_on_fallback"):
            if key in pipeline and not isinstance(pipeline[key], bool):
                raise ValidationError({key: "Use a boolean value."})
        for key in ("min_lead_confidence", "min_deal_confidence"):
            number = pipeline.get(key, 0.7)
            if isinstance(number, bool) or not isinstance(number, (int, float)) or not math.isfinite(number) or not 0.1 <= number <= 1:
                raise ValidationError({key: "Use a number between 0.1 and 1."})
        if "mode" in pipeline and pipeline["mode"] not in {"off", "triage", "lead_task", "draft_deal"}:
            raise ValidationError("Invalid automation mode.")
        if pipeline.get("creation_policy", "staff_confirmation") not in {"staff_confirmation", "automatic"}:
            raise ValidationError("Invalid creation policy.")
        length = pipeline.get("max_auto_reply_chars", 900)
        if isinstance(length, bool) or not isinstance(length, int) or not 120 <= length <= 2000:
            raise ValidationError("Reply length must be between 120 and 2000.")
    return value
