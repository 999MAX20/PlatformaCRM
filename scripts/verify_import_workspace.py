"""Targeted import browser flow in a disposable database and dedicated loopback ports."""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import time

root = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(root))
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
out = root / "output/import-workspace-20261104/implementation"
out.mkdir(parents=True, exist_ok=True)

def seed_fixture():
    from datetime import time
    from scripts.browser_test_runtime import configure_browser_runtime
    configure_browser_runtime()
    import django
    django.setup()
    from apps.businesses.models import Business, BusinessRole, BusinessMember, RolePermission
    from apps.scheduling.models import WorkingHours
    from apps.accounts.models import User
    business = Business.objects.get(slug=os.environ["E2E_BUSINESS_SLUG"])
    WorkingHours.objects.filter(business=business, resource__isnull=True).delete()
    for day in range(7):
        WorkingHours.objects.create(business=business, weekday=day, start_time=time(8), end_time=time(20))
    viewer = User.objects.create_user(username="import-viewer", email="import-viewer@example.test", password=os.environ["E2E_PASSWORD"], role="staff")
    role = BusinessRole.objects.create(business=business, name="Import viewer")
    for resource in ["clients", "appointments", "settings", "integrations"]:
        RolePermission.objects.create(business_role=role, resource=resource, action="view", scope="business")
    BusinessMember.objects.create(business=business, user=viewer, role="specialist", business_role=role)
    (out/"ui-fixture.json").write_text(json.dumps({"business": business.pk, "timezone": business.timezone}))

def main():
    if "--fixture" in sys.argv:
        seed_fixture()
        return
    from scripts.codex_verify import isolated_runtime
    with isolated_runtime(python=sys.executable) as runtime:
        env = runtime.environment
        env["IMPORT_RUN"] = str(time.time_ns())
        env["IMPORT_WORKSPACE_OUTPUT"] = str(out)
        (out / "ui-ports.json").write_text(json.dumps({"frontend": runtime.frontend_port, "backend": runtime.django_port}))
        commands = [
            ("prepare", [sys.executable, "scripts/browser_test_runtime.py", "prepare"], root),
            ("fixture", [sys.executable, str(Path(__file__).resolve()), "--fixture"], root),
            ("browser", [shutil.which("node"), "frontend/node_modules/@playwright/test/cli.js", "test", "--config", "frontend/playwright.import-workspace.config.cjs"], root),
        ]
        for name, command, cwd in commands:
            if name == "browser" and "--grep" in sys.argv:
                command.extend(["--grep", sys.argv[sys.argv.index("--grep") + 1]])
            log_path = out / ("ui-" + name + "-" + env["IMPORT_RUN"] + ".log")
            with log_path.open("w", encoding="utf-8") as log:
                result = subprocess.run(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT)
            print(name, result.returncode, flush=True)
            if result.returncode:
                print(log_path.read_text(encoding="utf-8")[-6000:])
                raise SystemExit(result.returncode)

if __name__ == "__main__":
    main()
