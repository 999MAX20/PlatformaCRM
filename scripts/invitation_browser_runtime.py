"""Serve real invitation APIs with local-only captured mail and a disposable DB."""
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

if __name__ == "__main__":
    from scripts.browser_test_runtime import configure_browser_runtime
    configure_browser_runtime()
    import django
    from django.conf import settings
    settings.EMAIL_BACKEND = "scripts.invitation_test_mail.EmailBackend"
    settings.FRONTEND_URL = os.environ["E2E_BASE_URL"]
    django.setup()
    from django.core.management import call_command
    call_command("runserver", f"127.0.0.1:{os.environ['E2E_DJANGO_PORT']}", use_reloader=False)
