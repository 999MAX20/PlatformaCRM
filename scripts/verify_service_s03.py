from pathlib import Path
import shutil
import subprocess
import sys
import time

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
from scripts.codex_verify import isolated_runtime

fixture = """
import os
from django.utils import timezone
from apps.businesses.models import Business
from apps.core.models import ExportJob
from apps.core.service_status import observe_business_service
business = Business.objects.get(slug=os.environ['E2E_BUSINESS_SLUG'])
job = ExportJob.objects.create(business=business, actor=business.owner, kind='entity', export_key='clients')
ExportJob.objects.filter(pk=job.pk).update(created_at=timezone.now()-timezone.timedelta(hours=1))
observe_business_service(business.pk)
"""
log_dir = root / 'output' / 'crm-s03-20261014'
log_dir.mkdir(parents=True, exist_ok=True)
log = log_dir / f'browser-{time.time_ns()}.log'
with isolated_runtime(python=sys.executable) as runtime, log.open('w', encoding='utf-8') as output:
    runtime.environment["E2E_SERVICE_S03"] = "1"
    commands = [
        ([shutil.which('node'), 'e2e/django-e2e.mjs', 'prepare'], root/'frontend', None),
        ([sys.executable, 'manage.py', 'shell', '-c', fixture], root, None),
        ([(shutil.which('npx.cmd') or shutil.which('npx')), 'playwright', 'test', 'e2e/service-s03.spec.ts', 'e2e/state-behavior.spec.ts', '--grep', 'service status|service connectivity|reconnect waits', '--project=desktop-chromium', '--project=mobile-chromium'], root/'frontend', None),
    ]
    for args, cwd, input_text in commands:
        result = subprocess.run(args, cwd=cwd, env=runtime.environment, input=input_text, text=True, encoding='utf-8', stdout=output, stderr=subprocess.STDOUT)
        if result.returncode:
            break
print(log)
print(log.read_text(encoding='utf-8')[-6500:] if result.returncode else log.read_text(encoding='utf-8')[-1200:])
raise SystemExit(result.returncode)
