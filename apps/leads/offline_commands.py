"""Bound browser retries to less than the minimum CRM receipt retention (one day)."""
import re

from django.utils import timezone

from apps.core.domain_errors import IdempotencyConflict


def validate_offline_command_key(key):
    if not key.startswith("lead-offline:"):
        return
    match = re.fullmatch(r"lead-offline:(\d{13}):[0-9a-f-]{36}", key)
    age = timezone.now().timestamp() * 1000 - int(match[1]) if match else None
    # A suspended tab/request must not recreate an effect after its receipt expires.
    if age is None or age < -60_000 or age > 3_600_000:
        raise IdempotencyConflict("Offline retry window expired. Check the existing result before creating another command.")
