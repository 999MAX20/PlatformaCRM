"""ADMIN-01 browser acceptance with disposable data and dedicated ports."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

parser = argparse.ArgumentParser()
parser.add_argument("--grep")
args = parser.parse_args()
fixture = """
import os
from apps.accounts.models import User
from apps.businesses.models import Business
from apps.support.models import SupportCase
owner = User.objects.get(email='business_owner@example.com')
for project in ('desktop-chromium', 'mobile-chromium'):
    for role in ('platform_admin', 'platform_manager'):
        email = f'details-{role}-{project}@example.com'
        User.objects.create_user(username=email, email=email, role=role, password=os.environ['E2E_PASSWORD'])
        business = Business.objects.create(owner=owner, name=f'Details {role} {project}', slug=f'details-{role}-{project}', phone='+77000000000')
        SupportCase.objects.create(business=business, created_by=owner, requester=owner, subject='Correct business details', source='clinic')
"""
folder = ROOT / "output" / "platform-details"
folder.mkdir(parents=True, exist_ok=True)
path = folder / f"browser-{time.time_ns()}.log"
with isolated_runtime(python=sys.executable) as runtime, path.open("w", encoding="utf-8") as log:
    runtime.environment["E2E_PLATFORM_DETAILS"] = "1"
    browser = [shutil.which("npx.cmd") or shutil.which("npx"), "playwright", "test", "e2e/platform-details.spec.ts", "--project=desktop-chromium", "--project=mobile-chromium"]
    if args.grep:
        browser += ["--grep", args.grep]
    for command, cwd in [
        ([shutil.which("node"), "e2e/django-e2e.mjs", "prepare"], ROOT / "frontend"),
        ([sys.executable, "manage.py", "shell", "-c", fixture], ROOT),
        (browser, ROOT / "frontend"),
    ]:
        result = subprocess.run(command, cwd=cwd, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            break
print(path)
print(path.read_text(encoding="utf-8", errors="replace")[-6000 if result.returncode else -1800:].encode("ascii", "replace").decode())
raise SystemExit(result.returncode)
