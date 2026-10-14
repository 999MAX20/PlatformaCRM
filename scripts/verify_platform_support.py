"""Support UI acceptance on disposable databases and dedicated loopback ports."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

parser = argparse.ArgumentParser()
parser.add_argument("--grep", help="Run only a named affected support flow after a fix")
args = parser.parse_args()
fixture = """
import os
from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.businesses.access import ensure_default_roles
from apps.support.services import create_case
from apps.core.models import ServiceComponentState
from django.utils import timezone
for project in ('desktop-chromium', 'mobile-chromium'):
    owner = User.objects.create_user(username=f'support-owner-{project}', email=f'support-owner-{project}@example.com', password=os.environ['E2E_PASSWORD'], role='business_owner', full_name='Clinic owner')
    business = Business.objects.create(owner=owner, name=f'Support Clinic {project}', slug=f'support-{project}')
    ensure_default_roles(business)
    ServiceComponentState.objects.create(business=business, component='exports', episode=1, state='degraded', started_at=timezone.now()-timezone.timedelta(minutes=10), observed_at=timezone.now(), affected_count=2)
    BusinessMember.objects.create(business=business,user=owner,role='owner',business_role=business.roles.get(preset_key='owner'))
    for name, role in [('employee', 'operator'), ('colleague', 'operator'), ('admin', 'admin')]:
        user = User.objects.create_user(username=f'support-{name}-{project}', email=f'support-{name}-{project}@example.com', password=os.environ['E2E_PASSWORD'], role='business_operator', full_name=f'Clinic {name}')
        BusinessMember.objects.create(business=business,user=user,role=role,business_role=business.roles.get(preset_key=role))
    User.objects.create_user(username=f'support-team-{project}', email=f'support-team-{project}@example.com', password=os.environ['E2E_PASSWORD'], role='platform_manager', full_name=f'Support team {project}')
    for index in range(21):
        create_case(actor=owner,business_id=business.pk,subject=f'Queue fixture {project} {index:02}',text='Fixture question',idempotency_key=f'queue-{index}')
"""
folder = ROOT / "output" / "platform-support"
folder.mkdir(parents=True, exist_ok=True)
path = folder / f"browser-{time.time_ns()}.log"
with isolated_runtime(python=sys.executable) as runtime, path.open("w", encoding="utf-8") as log:
    runtime.environment["E2E_PLATFORM_SUPPORT"] = "1"
    browser_command = [shutil.which("npx.cmd") or shutil.which("npx"), "playwright", "test", "e2e/platform-support.spec.ts", "e2e/platform-support-incidents.spec.ts", "--project=desktop-chromium", "--project=mobile-chromium"]
    if args.grep:
        browser_command += ["--grep", args.grep]
    commands = [
        ([shutil.which("node"), "e2e/django-e2e.mjs", "prepare"], ROOT / "frontend"),
        ([sys.executable, "manage.py", "shell", "-c", fixture], ROOT),
        (browser_command, ROOT / "frontend"),
    ]
    for command, cwd in commands:
        result = subprocess.run(command, cwd=cwd, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            break
print(path)
print(path.read_text(encoding="utf-8", errors="replace")[-9000 if result.returncode else -2500:])
raise SystemExit(result.returncode)
