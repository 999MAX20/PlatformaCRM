import logging
import re


_SYMBOL = re.compile(r"[A-Za-z_][A-Za-z0-9_.<>-]{0,199}\Z")
_EVENT_ID = re.compile(r"[a-f0-9]{32}\Z")


def _symbol(value, fallback):
    return value if isinstance(value, str) and _SYMBOL.fullmatch(value) else fallback


def _stacktrace(stacktrace):
    frames = []
    for frame in (stacktrace or {}).get("frames", [])[-100:]:
        if not isinstance(frame, dict):
            continue
        filename = str(frame.get("filename", "")).replace("\\", "/").rsplit("/", 1)[-1]
        safe = {
            "filename": _symbol(filename, "unknown.py"),
            "function": _symbol(frame.get("function"), "unknown"),
        }
        if type(frame.get("lineno")) is int and frame["lineno"] > 0:
            safe["lineno"] = frame["lineno"]
        if type(frame.get("in_app")) is bool:
            safe["in_app"] = frame["in_app"]
        frames.append(safe)
    return {"frames": frames}


def sanitize_sentry_event(event, hint):
    # Attachments bypass the event payload and must also be removed from the envelope.
    hint.pop("attachments", None)
    event_id = event.get("event_id", "")
    if not isinstance(event_id, str) or not _EVENT_ID.fullmatch(event_id):
        return None
    safe = {"event_id": event_id, "platform": "python"}
    if event.get("level") in {"fatal", "error", "warning", "info", "debug"}:
        safe["level"] = event["level"]
    for key in ("release", "environment"):
        safe[key] = _symbol(event.get(key), "unknown")
    exceptions = []
    for exception in (event.get("exception") or {}).get("values", [])[-10:]:
        if not isinstance(exception, dict):
            continue
        item = {
            "type": _symbol(exception.get("type"), "Error"),
            "value": "Exception details withheld by privacy policy",
            "stacktrace": _stacktrace(exception.get("stacktrace")),
        }
        mechanism = exception.get("mechanism") or {}
        if type(mechanism.get("handled")) is bool:
            item["mechanism"] = {"type": "generic", "handled": mechanism["handled"]}
        exceptions.append(item)
    if exceptions:
        safe["exception"] = {"values": exceptions}
    else:
        safe["message"] = "Application error; diagnostic content withheld by privacy policy"
        if event.get("stacktrace"):
            safe["stacktrace"] = _stacktrace(event["stacktrace"])
    return safe


def discard_sentry_payload(payload, hint):
    return None


def sentry_privacy_options():
    from sentry_sdk.integrations.atexit import AtexitIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration
    from sentry_sdk.integrations.dedupe import DedupeIntegration
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.excepthook import ExcepthookIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration

    return {
        "send_default_pii": False,
        "include_local_variables": False,
        "include_source_context": False,
        "max_request_body_size": "never",
        "max_breadcrumbs": 0,
        "before_send": sanitize_sentry_event,
        "before_send_transaction": discard_sentry_payload,
        "before_breadcrumb": discard_sentry_payload,
        "enable_logs": False,
        "auto_session_tracking": False,
        "profiles_sample_rate": 0,
        "profile_session_sample_rate": 0,
        "default_integrations": False,
        "auto_enabling_integrations": False,
        "integrations": [
            AtexitIntegration(),
            CeleryIntegration(propagate_traces=False, monitor_beat_tasks=False),
            DedupeIntegration(),
            DjangoIntegration(),
            ExcepthookIntegration(),
            LoggingIntegration(level=None, event_level=logging.ERROR),
        ],
    }
