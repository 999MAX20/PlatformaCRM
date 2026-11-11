import contextvars
import json
import logging
from datetime import datetime, timezone

from django.conf import settings
from apps.core.sanitization import sanitize_error_payload


request_id_context = contextvars.ContextVar("request_id", default="")


class RequestContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_context.get("")
        record.release = getattr(settings, "RELEASE", "unknown")
        record.environment = getattr(settings, "ENVIRONMENT", "unknown")
        return True


class JsonLogFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "request_id": getattr(record, "request_id", ""),
            "release": getattr(record, "release", "unknown"),
            "environment": getattr(record, "environment", "unknown"),
        }
        for key in ("method", "path", "status_code", "duration_ms", "user_id", "business_id", "job_id", "task_name"):
            value = getattr(record, key, None)
            if value not in (None, ""):
                payload[key] = value
        if record.name == "apps.ai_core.speech" and record.msg in {"ai.speech_request_completed", "ai.speech_provider_failed"}:
            for key in ("speech_stage", "speech_model", "speech_error_code", "speech_exception_type",
                        "speech_provider_request_id", "speech_generation_id", "speech_headers_ms"):
                value = getattr(record, key, None)
                if isinstance(value, (str, int, float)) and not isinstance(value, bool):
                    payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        # Normalize custom context values before redaction; retain complete tracebacks.
        serialized = json.dumps(payload, ensure_ascii=True, default=str)
        safe_payload = sanitize_error_payload(json.loads(serialized), max_string_length=len(serialized))
        return json.dumps(safe_payload, ensure_ascii=True)
