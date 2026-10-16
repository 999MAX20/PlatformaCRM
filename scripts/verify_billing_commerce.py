"""ADMIN-05 browser flows in a disposable database and dedicated local ports."""
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
import os, uuid
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch
from django.test import override_settings
from django.db import DatabaseError
from django.utils import timezone
from apps.accounts.models import User
from apps.businesses.models import Business, BusinessMember
from apps.billing.models import BillingOffer, Subscription, SubscriptionPlan, BillingReceipt
from apps.billing.commerce import create_order
from apps.billing.application import attempt_application
from apps.support.models import SupportCase
for project in ('desktop-chromium', 'mobile-chromium'):
    for scenario in ('bank','card','recovery','states'):
        people={}
        for kind, role in (('operator','platform_admin'),('owner','business_owner')):
            email=f'billing-{scenario}-{kind}-{project}@example.com'
            people[kind]=User.objects.create_user(username=email,email=email,full_name=f'{kind} {scenario}',role=role,password=os.environ['E2E_PASSWORD'])
        business=Business.objects.create(owner=people['owner'],name=f'Billing {scenario} {project}',slug=f'billing-{scenario}-{project}',status='active')
        BusinessMember.objects.create(business=business,user=people['owner'],role='owner')
        plan=SubscriptionPlan.objects.get(code='growth')
        Subscription.objects.create(business=business,plan=plan,status='overdue')
        case=SupportCase.objects.create(business=business,created_by=people['operator'],requester=people['owner'],source='platform',subject='Subscription payment')
        now=timezone.now()
        offer=BillingOffer.objects.create(business=business,plan=plan,amount=Decimal('12000.00'),currency='KZT',period_start=now-timezone.timedelta(hours=1),period_end=now+timezone.timedelta(days=30),expires_at=now+timezone.timedelta(days=1),is_active=True,approval_reference='ISOLATED TEST ONLY',seller={'name':'TEST seller','tax_id':'000000000000','account_key':'test-account','bank':'TEST bank','iban':'TEST-NOT-AN-ACCOUNT','bic':'TEST'})
        if scenario == 'recovery':
            with override_settings(BILLING_COMMERCE_ENABLED=True):
                order=create_order(SimpleNamespace(user=people['owner'],headers={}),business.pk,request_id=uuid.uuid4(),offer_id=offer.pk,buyer={'kind':'company','name':'TEST buyer','tax_id':'000000000001','email':people['owner'].email})
                BillingReceipt.objects.create(order=order,source='bank',merchant='test-account',reference=f'recovery-{project}',amount=order.amount,currency='KZT',received_at=now,confirmed_by=people['operator'],support_case=case)
                with patch('apps.billing.application.apply_order',side_effect=DatabaseError):
                    attempt_application(business.pk,order.pk)
"""


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--grep")
    args = parser.parse_args()
    folder = ROOT / "output" / "billing-commerce"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"browser-{time.time_ns()}.log"
    with isolated_runtime(python=sys.executable) as runtime, path.open("w", encoding="utf-8") as log:
        runtime.environment.update(E2E_BILLING_COMMERCE="1", DEBUG="pw:webserver")
        command = [shutil.which("node"), "node_modules/@playwright/test/cli.js", "test", "e2e/billing-commerce.spec.ts",
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
