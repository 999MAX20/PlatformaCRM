"""Customer-agent configuration. No option can grant access or remove hard limits."""
from rest_framework.exceptions import ValidationError


DEFAULTS = {
    "allow_first_off_topic": True,
    "off_topic_handoff_after": 3,
    "calls_per_24h": 30,
    "messages_per_minute": 12,
    "max_message_chars": 4000,
    "repeat_handoff_after": 3,
}
RANGES = {
    "off_topic_handoff_after": (1, 3),
    "calls_per_24h": (1, 30),
    "messages_per_minute": (3, 30),
    "max_message_chars": (256, 8000),
    "repeat_handoff_after": (2, 10),
}


def validate_safety_policy(value):
    if not isinstance(value, dict) or set(value) - set(DEFAULTS):
        raise ValidationError({"customer_safety": "Unsupported safety configuration."})
    if "allow_first_off_topic" in value and type(value["allow_first_off_topic"]) is not bool:
        raise ValidationError({"customer_safety": "Use a boolean for the first off-topic reply."})
    for key, (lower, upper) in RANGES.items():
        if key in value and (type(value[key]) is not int or not lower <= value[key] <= upper):
            raise ValidationError({"customer_safety": f"{key} must be between {lower} and {upper}."})
    return {**DEFAULTS, **value}


def safety_policy(bot):
    return validate_safety_policy((bot.settings_json or {}).get("customer_safety", {}))
