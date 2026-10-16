"""Run ADMIN-03 UI against disposable SQLite and a synthetic local outbox."""
import argparse
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

fixture = """
import os
from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember, BusinessRole
from apps.support.models import SupportCase
for project in ('desktop-chromium', 'mobile-chromium'):
    for scenario in ('flow', 'states'):
        people = {}
        for kind, role in (('operator','platform_manager'),('owner','business_owner'),('employee','staff')):
            email = f'recovery-{scenario}-{kind}-{project}@example.com'
            people[kind] = User.objects.create_user(username=email,email=email,full_name=f'{kind} {scenario} {project}',role=role,password=os.environ['E2E_PASSWORD'])
        business = Business.objects.create(owner=people['owner'],name=f'Recovery {scenario} {project}',slug=f'recovery-{scenario}-{project}')
        role = BusinessRole.objects.create(business=business,name='Specialist',preset_key='specialist')
        BusinessMember.objects.create(business=business,user=people['owner'],role='owner')
        BusinessMember.objects.create(business=business,user=people['employee'],role='specialist',business_role=role)
        for kind in ('owner','employee'):
            SupportCase.objects.create(business=business,created_by=people['operator'],requester=people[kind],source='platform',subject=f'Recover {kind}')
"""

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grep")
    args = parser.parse_args()
    folder = ROOT / "output" / "platform-recovery"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"browser-{time.time_ns()}.log"
    with isolated_runtime(python=sys.executable) as runtime, path.open("w", encoding="utf-8") as log:
        runtime.environment.update(E2E_PLATFORM_RECOVERY="1", EMAIL_BACKEND="scripts.recovery_test_mail.EmailBackend",
            FRONTEND_URL=f"http://127.0.0.1:{runtime.frontend_port}", ACCOUNT_RECOVERY_SUPPORT_EMAIL="support@example.com",
            E2E_RECOVERY_MAIL_DIR=str(runtime.database_path.parent / "recovery-mail"), DEBUG="pw:webserver")
        command = [shutil.which("node"), "node_modules/@playwright/test/cli.js", "test", "e2e/platform-recovery.spec.ts",
                   "--project=desktop-chromium", "--project=mobile-chromium"]
        if args.grep:
            command += ["--grep", args.grep]
        for cmd, cwd in [([shutil.which("node"), "e2e/django-e2e.mjs", "prepare"], ROOT / "frontend"),
                         ([sys.executable, "manage.py", "shell", "-c", fixture], ROOT), (command, ROOT / "frontend")]:
            log.write(f"Starting {cmd[1]} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"); log.flush()
            result = subprocess.run(cmd, cwd=cwd, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                break
    print(path)
    print(path.read_text(encoding="utf-8", errors="replace")[-6500 if result.returncode else -1800:].encode("ascii", "replace").decode())
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
