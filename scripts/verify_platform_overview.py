"""Overview acceptance with disposable storage and loopback servers."""
import argparse
import shutil
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

parser = argparse.ArgumentParser()
parser.add_argument("--grep", default="operator overview|service status keeps operator")
args = parser.parse_args()
fixture = """
from django.utils import timezone
from apps.accounts.models import User
from apps.businesses.models import Business
from apps.core.models import ServiceComponentState
from apps.core.service_status import COMPONENTS
from apps.support.models import SupportCase
from apps.support.services import create_case
from apps.support.incidents import link_incident
owner=User.objects.get(email='business_owner@example.com')
staff=User.objects.get(email='platform_admin@example.com')
now=timezone.now()
for business in Business.objects.all():
    for component in COMPONENTS:
        ServiceComponentState.objects.update_or_create(business=business,component=component,defaults={'state':'healthy','observed_at':now})
for index in range(9):
    business=Business.objects.create(owner=owner,name=f'Overview Clinic {index:02}',slug=f'overview-browser-{index}')
    for component in COMPONENTS:
        ServiceComponentState.objects.create(business=business,component=component,state='degraded' if component=='exports' else 'healthy',observed_at=now,episode=1,started_at=now-timezone.timedelta(minutes=12),affected_count=2 if component=='exports' else 0)
    for number in range(2):
        result=create_case(actor=staff,business_id=business.pk,subject=f'Overview case {index:02}-{number}',text='Please check the export',idempotency_key=f'overview-{index}-{number}',platform=True)
        link_incident(actor=staff,case_id=result.data['case_id'],business_id=business.pk,component='exports',episode=1)
        if number==1:
            SupportCase.objects.filter(pk=result.data['case_id']).update(assigned_to=staff,status='waiting_clinic')
for index in range(3):
    Business.objects.create(owner=owner,name=f'Overview Unverified {index}',slug=f'overview-unknown-{index}')
"""
folder=ROOT/'output'/'platform-overview'
folder.mkdir(parents=True,exist_ok=True)
path=folder/f'browser-{time.time_ns()}.log'
with isolated_runtime(python=sys.executable) as runtime, path.open('w',encoding='utf-8') as log:
    runtime.environment.update(E2E_PLATFORM_OVERVIEW='1',E2E_SERVICE_S03='1')
    commands=[
        ([shutil.which('node'),'e2e/django-e2e.mjs','prepare'],ROOT/'frontend'),
        ([sys.executable,'manage.py','shell','-c',fixture],ROOT),
        ([shutil.which('npx.cmd') or shutil.which('npx'),'playwright','test','e2e/platform-overview.spec.ts','e2e/service-s03.spec.ts','--grep',args.grep,'--project=desktop-chromium','--project=mobile-chromium'],ROOT/'frontend'),
    ]
    for command,cwd in commands:
        result=subprocess.run(command,cwd=cwd,env=runtime.environment,stdout=log,stderr=subprocess.STDOUT)
        if result.returncode:break
print(path)
print(path.read_text(encoding='utf-8',errors='replace')[-6000 if result.returncode else -1500:])
raise SystemExit(result.returncode)
