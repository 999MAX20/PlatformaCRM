"""ADMIN-04 browser flows in a disposable database and dedicated local ports."""
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
import os
from django.utils import timezone
from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole, BusinessInvitation
from apps.scheduling.models import Resource
from apps.tasks.models import Task
from apps.support.models import SupportCase
for project in ('desktop-chromium', 'mobile-chromium'):
    for scenario in ('flow', 'invitations', 'states'):
        people = {}
        for kind, role in (('operator','platform_manager'),('owner','business_owner'),('employee','staff')):
            email = f'access-{scenario}-{kind}-{project}@example.com'
            people[kind] = User.objects.create_user(username=email,email=email,full_name=f'{kind} {scenario} {project}',role=role,password=os.environ['E2E_PASSWORD'])
        business = Business.objects.create(owner=people['owner'],name=f'Access {scenario} {project}',slug=f'access-{scenario}-{project}')
        role = BusinessRole.objects.create(business=business,name='Specialist',preset_key='specialist')
        BusinessRole.objects.create(business=business,name='Manager',preset_key='manager')
        BusinessMember.objects.create(business=business,user=people['owner'],role='owner')
        BusinessMember.objects.create(business=business,user=people['employee'],role='specialist',business_role=role)
        Resource.objects.create(business=business,name='Preserved specialist',linked_user=people['employee'])
        Task.objects.create(business=business,title='Preserved assignment',assignee=people['employee'])
        SupportCase.objects.create(business=business,created_by=people['operator'],requester=people['owner'],source='platform',subject='Employee access')
        for recipient in ('invite','revoke'):
            BusinessInvitation.objects.create(business=business,email=f'access-{recipient}-{scenario}-{project}@example.com',full_name=f'{recipient} {scenario}',business_role=role,expires_at=timezone.now()+timezone.timedelta(days=7))
        other = Business.objects.create(owner=people['owner'],name=f'Other {scenario} {project}',slug=f'other-access-{scenario}-{project}')
        BusinessMember.objects.create(business=other,user=people['employee'],role='manager')
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grep")
    args = parser.parse_args()
    folder = ROOT / "output" / "platform-employee-access"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"browser-{time.time_ns()}.log"
    with isolated_runtime(python=sys.executable) as runtime, path.open("w", encoding="utf-8") as log:
        runtime.environment.update(E2E_PLATFORM_EMPLOYEE_ACCESS="1", DEBUG="pw:webserver")
        command = [shutil.which("node"), "node_modules/@playwright/test/cli.js", "test", "e2e/platform-employee-access.spec.ts",
                   "--project=desktop-chromium", "--project=mobile-chromium"]
        if args.grep:
            command += ["--grep", args.grep]
        for cmd, cwd in [([shutil.which("node"), "e2e/django-e2e.mjs", "prepare"], ROOT / "frontend"),
                         ([sys.executable, "manage.py", "shell", "-c", FIXTURE], ROOT), (command, ROOT / "frontend")]:
            log.write(f"Starting {cmd[1]} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"); log.flush()
            result = subprocess.run(cmd, cwd=cwd, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                break
    print(path)
    print(path.read_text(encoding="utf-8", errors="replace")[-6500 if result.returncode else -1800:].encode("ascii", "replace").decode())
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
