"""Combined ADMIN01-04 and ADMIN05 foundation browser gate; no live payments/mail."""
import argparse
import ast
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

SCENARIOS = (
    ("platform_details", "E2E_PLATFORM_DETAILS", "platform-details"),
    ("platform_ownership", "E2E_PLATFORM_OWNERSHIP", "platform-ownership"),
    ("platform_recovery", "E2E_PLATFORM_RECOVERY", "platform-recovery"),
    ("platform_employee_access", "E2E_PLATFORM_EMPLOYEE_ACCESS", "platform-employee-access"),
    ("billing_commerce", "E2E_BILLING_COMMERCE", "billing-commerce"),
)


def fixture(name):
    # Older standalone runners execute at import time. Read their literal fixtures
    # without importing/executing the runner or duplicating mutable test data.
    path = ROOT / "scripts" / f"verify_{name}.py"
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    values = [ast.literal_eval(node.value) for node in tree.body
              if isinstance(node, ast.Assign) and any(isinstance(target, ast.Name)
              and target.id in {"fixture", "FIXTURE"} for target in node.targets)]
    if len(values) != 1 or not isinstance(values[0], str):
        raise ValueError(f"Expected one literal fixture in {path.name}")
    return values[0]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--grep", help="Optional focused rerun with fresh isolated data.")
    args = parser.parse_args()
    folder = ROOT / "output" / "platform-admin-acceptance"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"browser-{time.time_ns()}.log"
    with isolated_runtime(python=sys.executable) as runtime, path.open("w", encoding="utf-8") as log:
        runtime.environment.update({flag: "1" for _, flag, _ in SCENARIOS})
        runtime.environment.update(EMAIL_BACKEND="scripts.recovery_test_mail.EmailBackend",
            FRONTEND_URL=f"http://127.0.0.1:{runtime.frontend_port}",
            ACCOUNT_RECOVERY_SUPPORT_EMAIL="support@example.com",
            E2E_RECOVERY_MAIL_DIR=str(runtime.database_path.parent / "recovery-mail"), DEBUG="pw:webserver")
        command = [shutil.which("node"), "node_modules/@playwright/test/cli.js", "test",
                   *[f"e2e/{spec}.spec.ts" for _, _, spec in SCENARIOS],
                   "--project=desktop-chromium", "--project=mobile-chromium"]
        if args.grep:
            command += ["--grep", args.grep]
        steps = [([shutil.which("node"), "e2e/django-e2e.mjs", "prepare"], ROOT / "frontend")]
        steps += [([sys.executable, "manage.py", "shell", "-c", fixture(name)], ROOT) for name, _, _ in SCENARIOS]
        steps += [(command, ROOT / "frontend")]
        for cmd, cwd in steps:
            log.write(f"Starting {cmd[1]} at {time.strftime('%Y-%m-%d %H:%M:%S')}\n"); log.flush()
            result = subprocess.run(cmd, cwd=cwd, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
            if result.returncode:
                break
    print(path)
    print(path.read_text(encoding="utf-8", errors="replace")[-6500 if result.returncode else -1800:].encode("ascii", "replace").decode())
    raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
