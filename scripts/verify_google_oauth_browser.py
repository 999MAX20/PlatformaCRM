import json, os, subprocess, sys, time, urllib.request
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime
OUT = ROOT / ('output/' + (sys.argv[1] if len(sys.argv) > 1 else 'google-oauth-20261119'))
OUT.mkdir(exist_ok=True)
with isolated_runtime(python=sys.executable) as runtime:
    env = runtime.environment.copy()
    fixture = OUT / 'fixtures.json'
    env['E2E_GOOGLE_FIXTURES'] = str(fixture)
    with (OUT / 'prepare.log').open('w', encoding='utf-8') as log:
        subprocess.run([sys.executable, 'scripts/browser_test_runtime.py', 'prepare'], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
        source = """
import sys, json
from scripts.browser_test_runtime import configure_browser_runtime
configure_browser_runtime()
import django
django.setup()
from apps.accounts.models import User, SocialIdentity, MfaDevice
from apps.integrations.credential_encryption import encrypt_credential_value
from django.utils import timezone
import base64, secrets
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives import serialization
key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
fixtures = {'private_key': key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption()).decode(), 'public_key': key.public_key().public_bytes(serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo).decode()}
fixtures['mfa_hex'] = secrets.token_bytes(20).hex()
fixtures['recovery'] = {}
from apps.accounts.mfa import _replace_recovery_codes
for project in ('desktop-chromium', 'mobile-chromium'):
    for mode in ('known', 'mfa', 'known-signup', 'mfa-signup', 'mfa-link'):
        email = mode + '-' + project + '@google.example.test'
        user = User.objects.create_user(username=email, email=email, password='ExistingSynthetic123', role='business_operator')
        if mode != 'mfa-link':
            SocialIdentity.objects.create(user=user, provider='google', subject=email, email=email, email_verified=True)
        if mode.startswith('mfa'):
            MfaDevice.objects.create(user=user, confirmed_at=timezone.now(), encrypted_secret=encrypt_credential_value(base64.b32encode(bytes.fromhex(fixtures['mfa_hex'])).decode()))
        if mode == 'mfa-link': fixtures['recovery'][project] = _replace_recovery_codes(user)
    for lang in ('ru', 'kk', 'en'):
        email = lang + '-' + project + '@google-existing.example.test'
        User.objects.create_user(username=email, email=email, password='ExistingSynthetic123', role='business_operator')
with open(sys.argv[1], 'w') as stream: json.dump(fixtures, stream)
"""
        subprocess.run([sys.executable, '-c', source, str(fixture)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, check=True)
    env['VITE_GOOGLE_CLIENT_ID'] = 'synthetic-client'
    config = OUT / 'playwright.config.ts'
    config.write_text('import base from "../../frontend/playwright.config";\nexport default {...base, testDir: "../../frontend/e2e", webServer: undefined, outputDir: "./results", reporter: [["list"]]};\n', encoding='utf-8')
    handles = [(OUT / name).open('w', encoding='utf-8') for name in ('backend.log', 'frontend.log')]
    processes = []
    try:
        processes.append(subprocess.Popen([sys.executable, 'frontend/e2e/google-oauth-runtime.py', str(fixture)], cwd=ROOT, env=env, stdout=handles[0], stderr=subprocess.STDOUT))
        processes.append(subprocess.Popen(['node', 'node_modules/vite/bin/vite.js', '--host', '127.0.0.1', '--port', str(runtime.frontend_port), '--strictPort'], cwd=ROOT / 'frontend', env=env, stdout=handles[1], stderr=subprocess.STDOUT))
        for url in (f'http://127.0.0.1:{runtime.django_port}/health/', f'http://127.0.0.1:{runtime.frontend_port}/'):
            for attempt in range(120):
                try:
                    urllib.request.urlopen(url, timeout=2).close()
                    break
                except Exception: time.sleep(1)
            else: raise RuntimeError('Isolated server did not start')
        (OUT / 'runtime.json').write_text(json.dumps({'frontend': runtime.frontend_port, 'backend': runtime.django_port, 'pids': [p.pid for p in processes]}))
        with (OUT / 'browser.log').open('w', encoding='utf-8') as log:
            projects = ['--project=' + sys.argv[2]] if len(sys.argv) > 2 and not sys.argv[2].startswith('--') else ['--project=desktop-chromium', '--project=mobile-chromium']
            result = subprocess.run(['node', 'node_modules/@playwright/test/cli.js', 'test', '--config', str(config), 'google-oauth.spec.ts', '--max-failures=1', *projects], cwd=ROOT / 'frontend', env=env, stdout=log, stderr=subprocess.STDOUT)
        print('BROWSER_EXIT', result.returncode, flush=True)
        print('PREVIEW', runtime.frontend_port, flush=True)
        if '--keep' in sys.argv:
            while not (OUT / 'stop').exists(): time.sleep(1)
        if result.returncode: raise SystemExit(result.returncode)
    finally:
        for process in processes: process.terminate()
        for process in processes: process.wait(timeout=20)
        for handle in handles: handle.close()
        fixture.unlink(missing_ok=True)
