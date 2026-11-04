import hashlib
from http.cookiejar import CookieJar
from contextlib import closing
import json
from pathlib import Path
import shutil
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.request import urlopen, Request, build_opener, HTTPCookieProcessor

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime
from scripts.recovery_runtime import stop_process, HIDDEN

OUT = Path(__file__).resolve().parent
working = ROOT / "db.sqlite3"
before = hashlib.sha256(working.read_bytes()).hexdigest()
results = {}
with isolated_runtime(python=sys.executable) as runtime:
    env = runtime.environment
    with (OUT / "dependent-checks.log").open("w", encoding="utf-8") as log:
        for label, command in [
            ("node", [shutil.which("node"), "--test", "frontend/scripts/tests/audit-runtime.test.mjs", "frontend/scripts/tests/gate-env.test.mjs"]),
            ("python", [sys.executable, "-m", "unittest", "scripts.tests.test_browser_test_runtime", "scripts.tests.test_recovery_faults", "scripts.tests.test_codex_verify"]),
        ]:
            result = subprocess.run(command, cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            results[label] = result.returncode
            assert result.returncode == 0, label
    with (OUT / "launcher-integration.log").open("w", encoding="utf-8") as log:
        server = subprocess.Popen([shutil.which("node"), "frontend/e2e/django-e2e.mjs", "serve"], cwd=ROOT,
                                  env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=HIDDEN)
        try:
            deadline = time.monotonic() + 180
            while True:
                assert server.poll() is None, "launcher exited before readiness"
                try:
                    with urlopen(env["E2E_API_BASE_URL"] + "/health/", timeout=2) as response:
                        assert response.status == 200
                    break
                except OSError:
                    if time.monotonic() >= deadline:
                        raise AssertionError("launcher readiness timed out")
                    time.sleep(.3)
            body = json.dumps({"email": env["E2E_OWNER_EMAIL"], "password": env["E2E_PASSWORD"]}).encode()
            client = build_opener(HTTPCookieProcessor(CookieJar()))
            with client.open(env["E2E_API_BASE_URL"] + "/api/auth/csrf/", timeout=10) as response:
                csrf = json.load(response)["csrf_token"]
            with client.open(Request(env["E2E_API_BASE_URL"] + "/api/auth/token/", data=body,
                                    headers={"Content-Type": "application/json", "Origin": env["E2E_API_BASE_URL"], "X-CSRFToken": csrf}), timeout=10) as response:
                assert response.status == 200
                assert json.load(response).get("access")
            with closing(sqlite3.connect(runtime.database_path)) as connection:
                assert connection.execute("select count(*) from businesses_business where slug=?", (env["E2E_BUSINESS_SLUG"],)).fetchone()[0] == 1
            results["isolated_launcher_health_login_fixture"] = "PASS"
        finally:
            stop_process(server)
        for arguments in (["check"], ["makemigrations", "--check", "--dry-run"]):
            code = "from scripts.browser_test_runtime import configure_browser_runtime; configure_browser_runtime(); import django; django.setup(); from django.core.management import execute_from_command_line; execute_from_command_line(['manage.py', *" + repr(arguments) + "])"
            result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT)
            assert result.returncode == 0, arguments
        results["system_migration_drift"] = "PASS"
    for port in (runtime.django_port, runtime.frontend_port):
        with socket.socket() as sock:
            assert sock.connect_ex(("127.0.0.1", port)) != 0
    directory = runtime.database_path.parent
assert not directory.exists()
assert hashlib.sha256(working.read_bytes()).hexdigest() == before
results.update(working_db_unchanged=True, owned_processes_stopped=True, disposable_directory_removed=True)
(OUT / "helper-results.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
print(json.dumps(results))
