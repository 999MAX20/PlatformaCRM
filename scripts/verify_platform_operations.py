"""Operator worklists acceptance on disposable DBs and dedicated loopback ports."""
import shutil
import argparse
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

parser = argparse.ArgumentParser()
parser.add_argument('--grep', default='operator worklists|service status keeps operator')
args = parser.parse_args()

fixture = """
from django.utils import timezone
from apps.accounts.models import User
from apps.businesses.models import Business
from apps.core.models import ServiceComponentState
from apps.automations.models import AutomationRun
from apps.integrations.models import BusinessConnector, IntegrationEventLog, WebhookEndpoint, WebhookDeliveryLog
from apps.support.services import create_case
from apps.support.incidents import link_incident
owner=User.objects.get(email='business_owner@example.com')
staff=User.objects.get(email='platform_admin@example.com')
now=timezone.now()
for project in ('desktop-chromium','mobile-chromium'):
    for index in range(23):
        business=Business.objects.create(owner=owner,name=f'Operations {project} {index:02}',slug=f'operations-{project}-{index}')
        ServiceComponentState.objects.create(business=business,component='exports',episode=1,state='degraded',started_at=now-timezone.timedelta(minutes=10),observed_at=now,affected_count=2)
        if index==0:
            first=business
    ServiceComponentState.objects.create(business=first,component='files',episode=1,state='degraded',started_at=now-timezone.timedelta(minutes=20),observed_at=now-timezone.timedelta(minutes=5),affected_count=1)
    case=create_case(actor=staff,business_id=first.pk,subject='Delayed export',text='Please investigate',idempotency_key=f'ops-{project}',platform=True).data['case_id']
    link_incident(actor=staff,case_id=case,business_id=first.pk,component='exports',episode=1)
    for index in range(13):
        BusinessConnector.objects.create(business=first,provider='telegram',name=f'Channel {index}',status='failed')
        AutomationRun.objects.create(business=first,trigger_type='lead_created',status='failed')
    old=AutomationRun.objects.create(business=first,trigger_type='lead_created',status='failed')
    AutomationRun.objects.filter(pk=old.pk).update(created_at=now-timezone.timedelta(days=31))
    IntegrationEventLog.objects.create(business=first,provider='telegram',direction='outbound',status='failed')
    endpoint=WebhookEndpoint.objects.create(business=first,name='Callback',url='https://example.com/hook',secret='isolated-only')
    WebhookDeliveryLog.objects.create(business=first,endpoint=endpoint,event_type='lead.created',status='failed',idempotency_key=f'hook-{project}')
"""
folder = ROOT / 'output' / 'platform-operations'
folder.mkdir(parents=True, exist_ok=True)
path = folder / f'browser-{time.time_ns()}.log'
with isolated_runtime(python=sys.executable) as runtime, path.open('w', encoding='utf-8') as log:
    runtime.environment['E2E_PLATFORM_OPERATIONS'] = '1'
    runtime.environment['E2E_SERVICE_S03'] = '1'
    commands = [
        ([shutil.which('node'), 'e2e/django-e2e.mjs', 'prepare'], ROOT/'frontend'),
        ([sys.executable, 'manage.py', 'shell', '-c', fixture], ROOT),
        ([shutil.which('npx.cmd') or shutil.which('npx'), 'playwright', 'test', 'e2e/platform-operations.spec.ts', 'e2e/service-s03.spec.ts', '--grep', args.grep, '--project=desktop-chromium', '--project=mobile-chromium'], ROOT/'frontend'),
    ]
    for command, cwd in commands:
        result = subprocess.run(command, cwd=cwd, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
        if result.returncode:
            break
print(path)
print(path.read_text(encoding='utf-8', errors='replace')[-6500 if result.returncode else -1500:])
raise SystemExit(result.returncode)
