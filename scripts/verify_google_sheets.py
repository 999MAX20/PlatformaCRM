"""Serve real CRM flows with synthetic Google responses in a disposable database."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUTPUT = ROOT / ("output/google-calendar-browser" if "--calendar" in sys.argv else "output/google-sheets-browser")


def serve():
    from scripts.browser_test_runtime import configure_browser_runtime
    configure_browser_runtime()
    import django
    django.setup()
    from datetime import timedelta
    from types import SimpleNamespace
    from django.conf import settings
    from django.core.management import call_command
    from django.utils import timezone
    from apps.accounts.models import User
    from apps.businesses.models import Business
    from apps.integrations import google_oauth, google_sheets, google_sheets_export
    from apps.integrations.credential_encryption import encrypt_credential_value
    from apps.integrations.google_models import GoogleConnection
    from apps.core import antivirus

    business = Business.objects.get(slug=os.environ["E2E_BUSINESS_SLUG"])
    owner = User.objects.get(email="business_owner@example.com")
    GoogleConnection.objects.get_or_create(business=business, actor=owner, defaults={
        "status": "connected", "email": "sheets-fixture@example.test", "subject": "isolated-account",
        "encrypted_access": encrypt_credential_value("isolated-access"),
        "encrypted_refresh": encrypt_credential_value("isolated-refresh"),
        "access_expires_at": timezone.now()+timedelta(hours=2)})
    settings.GOOGLE_INTEGRATION_CLIENT_ID = "isolated-client"
    settings.GOOGLE_INTEGRATION_CLIENT_SECRET = "isolated-secret"
    settings.GOOGLE_INTEGRATION_REDIRECT_URI = os.environ["E2E_BASE_URL"] + "/app/integrations/google/callback"
    antivirus.scan_stream = lambda stream: SimpleNamespace(clean=True)

    def remote(url, **kwargs):
        if "revoke" in url:
            return {}
        if "userinfo" in url:
            return {"sub": "isolated-account", "email": "sheets-fixture@example.test", "email_verified": True}
        if url.endswith("/token"):
            return {"access_token": "isolated-access", "refresh_token": "isolated-refresh",
                    "scope": google_oauth.SHEETS_SCOPE, "expires_in": 3600}
        if "/values/" in url:
            return {"values": [["full_name", "phone"], ["Google Browser Client", "+77015553388"]]}
        if "drive/v3/files" in url:
            return {"id": "isolated_export_sheet", "files": [{"id": "isolated_export_sheet"}]}
        if ":batchUpdate" in url:
            return {}
        return {"properties": {"title": "Google synthetic clients"}, "sheets": [{"properties": {
            "sheetId": 0, "sheetType": "GRID", "title": "Clients", "gridProperties": {"rowCount": 1000, "columnCount": 26}}}]}

    google_oauth.google_request = google_sheets.google_request = google_sheets_export.google_request = remote
    if "--calendar" in sys.argv:
        from scripts.google_calendar_browser_fixture import configure
        configure(business, owner, OUTPUT)
    call_command("runserver", f"127.0.0.1:{os.environ['E2E_DJANGO_PORT']}", use_reloader=False)


def main():
    if "--serve" in sys.argv:
        serve()
        return
    from scripts.codex_verify import isolated_runtime
    OUTPUT.mkdir(parents=True, exist_ok=True)
    (OUTPUT / "stop").unlink(missing_ok=True)
    with isolated_runtime(python=sys.executable) as runtime:
        env = runtime.environment
        with (OUTPUT / "prepare.log").open("w", encoding="utf-8") as log:
            subprocess.run([sys.executable, "scripts/browser_test_runtime.py", "prepare"], cwd=ROOT,
                           env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        (OUTPUT / "runtime.json").write_text(json.dumps({"frontend": runtime.frontend_port, "backend": runtime.django_port}))
        logs = [(OUTPUT / name).open("w", encoding="utf-8") for name in ("backend.log", "frontend.log")]
        processes = []
        try:
            processes.append(subprocess.Popen([sys.executable, __file__, "--serve", *(["--calendar"] if "--calendar" in sys.argv else [])], cwd=ROOT, env=env, stdout=logs[0], stderr=subprocess.STDOUT))
            processes.append(subprocess.Popen([shutil.which("node"), "node_modules/vite/bin/vite.js", "--config", "vite.google-sheets.config.ts",
                "--host", "127.0.0.1", "--port", str(runtime.frontend_port), "--strictPort"], cwd=ROOT / "frontend", env=env, stdout=logs[1], stderr=subprocess.STDOUT))
            print(f"Isolated UI: {env['E2E_BASE_URL']}", flush=True)
            while not (OUTPUT / "stop").exists() and all(process.poll() is None for process in processes):
                time.sleep(1)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.terminate()
                    process.wait(timeout=20)
            for log in logs:
                log.close()


if __name__ == "__main__":
    main()
