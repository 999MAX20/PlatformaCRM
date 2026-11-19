"""Focused invitation acceptance using disposable data and a captured mailbox."""
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
from django.utils import timezone
from apps.businesses.models import Business, BusinessInvitation
from apps.accounts.models import User, MfaDevice
from apps.billing.models import SubscriptionPlan
from apps.integrations.credential_encryption import encrypt_credential_value
b = Business.objects.get(slug='e2e-business')
subscription = b.subscription
base_plan = subscription.plan
# Both browser projects retain accepted recipients in this disposable business.
# Keep entitlement checks enabled, with capacity for the complete flow suite.
subscription.plan = SubscriptionPlan.objects.create(
    name='Invitation flow fixture', code='invitation-flow-fixture',
    limits_json={**base_plan.limits_json, 'users': 50},
    features_json=base_plan.features_json,
)
subscription.save(update_fields=['plan'])
for project in ('desktop-chromium','mobile-chromium'):
    user = User.objects.create_user(username=f'invite-mfa-{project}', email=f'invite-mfa-{project}@example.com', password='InviteMfa123!', role=User.Roles.BUSINESS_OPERATOR)
    MfaDevice.objects.create(user=user, encrypted_secret=encrypt_credential_value('JBSWY3DPEHPK3PXP'), confirmed_at=timezone.now())
    BusinessInvitation.objects.create(business=b, email=user.email, role='operator', expires_at=timezone.now()+timezone.timedelta(hours=24), delivery_channel='manual')
    BusinessInvitation.objects.create(business=b, email=f'expired-{project}@example.com', role='operator',
        expires_at=timezone.now()-timezone.timedelta(hours=1), delivery_channel='email')
    BusinessInvitation.objects.create(business=b, email=f'states-{project}@example.com', role='operator',
        expires_at=timezone.now()+timezone.timedelta(hours=24), delivery_channel='manual')
    BusinessInvitation.objects.create(business=b, email=f'recovery-{project}@example.com', role='operator',
        expires_at=timezone.now()+timezone.timedelta(hours=24), delivery_channel='manual')
"""

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--grep")
    args = parser.parse_args()
    folder = ROOT / "output" / "invitations-24h-20261112"
    folder.mkdir(parents=True, exist_ok=True)
    log_path = folder / f"browser-{time.time_ns()}.log"
    with isolated_runtime(python=sys.executable) as runtime, log_path.open("w", encoding="utf-8") as log:
        runtime.environment["E2E_INVITATION_MAIL_DIR"] = str(runtime.database_path.parent / "invitations-mail")
        command = [shutil.which("node"), "node_modules/@playwright/test/cli.js", "test", "--config=playwright.invitations.config.ts",
            "--project=desktop-chromium", "--project=mobile-chromium"]
        if args.grep:
            command += ["--grep", args.grep]
        fixture = FIXTURE.replace("e2e-business", runtime.environment["E2E_BUSINESS_SLUG"])
        for cmd, cwd in [([shutil.which("node"), "e2e/django-e2e.mjs", "prepare"], ROOT / "frontend"),
                         ([sys.executable, "-c", "from scripts.browser_test_runtime import configure_browser_runtime; configure_browser_runtime(); import django; django.setup(); exec(" + repr(fixture) + ")"], ROOT),
                         (command, ROOT / "frontend")]:
            result = subprocess.run(cmd, cwd=cwd, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                break
    print(log_path)
    print(log_path.read_text(encoding="utf-8", errors="replace")[-4500:].encode("ascii", "replace").decode())
    sys.exit(result.returncode)
