"""Focused invitation acceptance using disposable data and a captured mailbox."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

FIXTURE = """
from django.utils import timezone
from apps.businesses.models import Business, BusinessInvitation
b = Business.objects.get(slug='e2e-business')
for project in ('desktop-chromium','mobile-chromium'):
    BusinessInvitation.objects.create(business=b, email=f'expired-{project}@example.com', role='operator',
        expires_at=timezone.now()-timezone.timedelta(hours=1), delivery_channel='email')
    BusinessInvitation.objects.create(business=b, email=f'states-{project}@example.com', role='operator',
        expires_at=timezone.now()+timezone.timedelta(hours=24), delivery_channel='manual')
    BusinessInvitation.objects.create(business=b, email=f'recovery-{project}@example.com', role='operator',
        expires_at=timezone.now()+timezone.timedelta(hours=24), delivery_channel='manual')
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--grep")
    args = parser.parse_args()
    folder = ROOT / "output" / "invitations-24h-20261112"
    folder.mkdir(parents=True, exist_ok=True)
    log_path = folder / f"browser-{time.time_ns()}.log"
    with isolated_runtime(python=sys.executable) as runtime, log_path.open("w", encoding="utf-8") as log:
        runtime.environment["E2E_INVITATION_MAIL_DIR"] = str(runtime.database_path.parent / "invitations-mail")
        command = [shutil.which("node"), "node_modules/@playwright/test/cli.js", "test", "--config=playwright.invitations.config.ts",
            "--project=desktop-chromium", "--project=mobile-chromium"]
        if args.grep:
            command += ["--grep", args.grep]
        fixture = FIXTURE.replace("e2e-business", runtime.environment["E2E_BUSINESS_SLUG"])
        for cmd, cwd in [([shutil.which("node"), "e2e/django-e2e.mjs", "prepare"], ROOT / "frontend"),
                         ([sys.executable, "manage.py", "shell", "-c", fixture], ROOT),
                         (command, ROOT / "frontend")]:
            result = subprocess.run(cmd, cwd=cwd, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                break
    print(log_path)
    print(log_path.read_text(encoding="utf-8", errors="replace")[-4500:].encode("ascii", "replace").decode())
    sys.exit(result.returncode)
