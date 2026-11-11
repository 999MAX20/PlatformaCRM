import re


_MODEL_ID = re.compile(r"[a-z0-9][a-z0-9._-]{0,63}/[a-z0-9][a-z0-9._:-]{0,100}")
_REQUEST_ID = re.compile(r"(?:gen|req)[-_][A-Za-z0-9_-]{1,100}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}")


def safe_model_id(value):
    return value if isinstance(value, str) and _MODEL_ID.fullmatch(value) else "unrecognized"


def safe_provider_id(value):
    return value if isinstance(value, str) and _REQUEST_ID.fullmatch(value) else None


def speech_http_failure(status):
    if status == 402:
        return "speech_payment_required", False
    if status in (408, 504):
        return "speech_timeout", True
    if status == 429:
        return "rate_limited", True
    if status >= 500:
        return "provider_unavailable", True
    return "provider_rejected", False
