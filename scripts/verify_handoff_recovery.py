"""Reachable Inbox idle-recovery flow against a disposable local database."""
from pathlib import Path
import argparse
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--grep", help="Run only matching scenarios after a scoped test/UI change.")
args = parser.parse_args()
directory = ROOT / "output" / "ai-return-20261014"
directory.mkdir(parents=True, exist_ok=True)
log = directory / f"browser-{time.time_ns()}.log"
with isolated_runtime(python=sys.executable) as runtime, log.open("w", encoding="utf-8") as output:
    runtime.environment["E2E_HANDOFF_RECOVERY"] = "1"
    commands = [
        [shutil.which("node"), "e2e/django-e2e.mjs", "prepare"],
        [shutil.which("npx.cmd") or shutil.which("npx"), "playwright", "test", "e2e/handoff-recovery.spec.ts",
         "--project=desktop-chromium", "--project=mobile-chromium"],
    ]
    if args.grep:
        commands[-1].extend(["--grep", args.grep])
    for command in commands:
        result = subprocess.run(command, cwd=ROOT / "frontend", env=runtime.environment,
                                stdout=output, stderr=subprocess.STDOUT)
        if result.returncode:
            break
print(log)
print(log.read_text(encoding="utf-8")[-6500:] if result.returncode else log.read_text(encoding="utf-8")[-1200:])
raise SystemExit(result.returncode)
