"""Signed Google fixture boundary, restricted to the disposable browser database."""
import json
import os
from pathlib import Path
import sys
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.browser_test_runtime import configure_browser_runtime

configure_browser_runtime()
import django
django.setup()
from cryptography.hazmat.primitives import serialization
from django.conf import settings
from django.core.management import call_command

fixture = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))
key = serialization.load_pem_public_key(fixture["public_key"].encode())
settings.GOOGLE_OAUTH_CLIENT_IDS = ["synthetic-client"]
# Multiple independent browser locales share this disposable process/IP.
settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth_signup"] = "100/hour"
settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth_social"] = "200/min"
settings.REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"]["auth_login"] = "200/min"
with patch("apps.accounts.social_auth.PyJWKClient") as jwks:
    jwks.return_value.get_signing_key_from_jwt.return_value = SimpleNamespace(key=key)
    call_command("runserver", f"127.0.0.1:{os.environ['E2E_DJANGO_PORT']}", use_reloader=False)
