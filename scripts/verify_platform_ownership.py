"""ADMIN-02 real browser flows with disposable data, providers and dedicated ports."""
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
from apps.businesses.models import Business, BusinessMember, BusinessRole
from apps.support.models import SupportCase
for project in ('desktop-chromium', 'mobile-chromium'):
    for scenario in ('flow', 'states'):
        people = {}
        for kind, role in (('admin', 'platform_admin'), ('manager', 'platform_manager'), ('owner', 'business_owner'), ('recipient', 'staff')):
            email = f'ownership-{scenario}-{kind}-{project}@example.com'
            people[kind] = User.objects.create_user(username=email, email=email, full_name=f'{kind} {scenario} {project}', role=role, password=os.environ['E2E_PASSWORD'])
        business = Business.objects.create(owner=people['owner'], name=f'Ownership {scenario} {project}', slug=f'ownership-{scenario}-{project}', timezone='Asia/Almaty')
        owner_role = BusinessRole.objects.create(business=business, name='Owner', preset_key='owner')
        role = BusinessRole.objects.create(business=business, name='Specialist', preset_key='specialist')
        BusinessMember.objects.create(business=business, user=people['owner'], role='owner', business_role=owner_role)
        BusinessMember.objects.create(business=business, user=people['recipient'], role='specialist', business_role=role)
        SupportCase.objects.create(business=business, created_by=people['owner'], requester=people['owner'], subject='Ownership transfer', source='clinic')
"""
folder = ROOT / "output" / "platform-ownership"
folder.mkdir(parents=True, exist_ok=True)
path = folder / f"browser-{time.time_ns()}.log"
with isolated_runtime(python=sys.executable) as runtime, path.open("w", encoding="utf-8") as log:
    runtime.environment["E2E_PLATFORM_OWNERSHIP"] = "1"
    runtime.environment["DEBUG"] = "pw:webserver"
    browser = [shutil.which("node"), "node_modules/@playwright/test/cli.js", "test", "e2e/platform-ownership.spec.ts",
               "--project=desktop-chromium", "--project=mobile-chromium"]
    if args.grep:
        browser += ["--grep", args.grep]
    for command, cwd in [
        ([shutil.which("node"), "e2e/django-e2e.mjs", "prepare"], ROOT / "frontend"),
        ([sys.executable, "manage.py", "shell", "-c", fixture], ROOT), (browser, ROOT / "frontend"),
    ]:
        log.write(f"Starting {command[1]} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
        log.flush()
        result = subprocess.run(command, cwd=cwd, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            break
print(path)
print(path.read_text(encoding="utf-8", errors="replace")[-7000 if result.returncode else -2000:].encode("ascii", "replace").decode())
raise SystemExit(result.returncode)
