from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from scripts.codex_verify import isolated_runtime

parser = argparse.ArgumentParser()
parser.add_argument("--rebuild", action="store_true", help="Include the platform rebuild read-model/UI checks")
parser.add_argument("--grep", help="Narrow the existing browser checks after a relevant fix")
args = parser.parse_args()

fixture = """
import os
from django.utils import timezone
from apps.accounts.models import User
from apps.businesses.models import Business
from apps.core.models import SupportAccessGrant, AuditLog
from apps.automations.models import AutomationRun
owner = User.objects.get(email='business_owner@example.com')
for index in range(23):
    Business.objects.get_or_create(slug=f's02-clinic-{index:02}', defaults={'owner': owner, 'name': f'S02 Clinic {index:02}'})
business, _ = Business.objects.get_or_create(slug='s02-support', defaults={'owner': owner, 'name': 'S02 Support'})
for project in ('desktop-chromium', 'mobile-chromium'):
    email = f's02-support-{project}@example.com'
    user = User.objects.create_user(username=email, email=email, password=os.environ['E2E_PASSWORD'], role=User.Roles.PLATFORM_ADMIN)
    SupportAccessGrant.objects.create(business=business, user=user, created_by=owner, reason='Isolated S02 verification', expires_at=timezone.now()+timezone.timedelta(hours=2))
for index in range(12):
    AuditLog.objects.create(business=business, actor=owner, action='update', entity_type='platform_support_action', entity_id=str(business.pk), metadata={'note': f'S02 historical note {index}', 'action_type':'support_note','status':'logged'})
AutomationRun.objects.create(business=business, trigger_type='lead_created', status=AutomationRun.Statuses.FAILED, run_after=timezone.now())
"""
if args.rebuild:
    fixture += """
from apps.billing.models import Subscription, SubscriptionPlan
plan = SubscriptionPlan.objects.create(code='rebuild-paid', name='Rebuild paid plan', monthly_price=4200)
paid = Business.objects.create(slug='rebuild-paid', name='Rebuild Paid Clinic', owner=owner, status=Business.Statuses.ACTIVE)
Subscription.objects.create(business=paid, plan=plan, status=Subscription.Statuses.ACTIVE)
"""
log_dir = root / 'output' / ('platform-rebuild-01' if args.rebuild else 'crm-s02-20261014')
log_dir.mkdir(parents=True, exist_ok=True)
log = log_dir / f'browser-{time.time_ns()}.log'
with isolated_runtime(python=sys.executable) as runtime, log.open('w', encoding='utf-8') as output:
    runtime.environment["E2E_PLATFORM_S02"] = "1"
    runtime.environment["E2E_PLATFORM_REBUILD"] = "1" if args.rebuild else "0"
    grep = 'platform search|support note uses|platform load recovery|platform routes render|support note form'
    if args.rebuild:
        grep += '|platform rebuild'
    if args.grep:
        grep = args.grep
    commands = [
        ([shutil.which('node'), 'e2e/django-e2e.mjs', 'prepare'], root/'frontend', None),
        ([sys.executable, 'manage.py', 'shell', '-c', fixture], root, None),
        ([(shutil.which('npx.cmd') or shutil.which('npx')), 'playwright', 'test', 'e2e/platform-s02.spec.ts', 'e2e/smoke.spec.ts', '--grep', grep, '--project=desktop-chromium', '--project=mobile-chromium'], root/'frontend', None),
    ]
    for args, cwd, input_text in commands:
        result = subprocess.run(args, cwd=cwd, env=runtime.environment, input=input_text, text=True, encoding='utf-8', stdout=output, stderr=subprocess.STDOUT)
        if result.returncode:
            break
print(log)
print(log.read_text(encoding='utf-8')[-6500:] if result.returncode else log.read_text(encoding='utf-8')[-1200:])
raise SystemExit(result.returncode)
