"""Focused connection/session browser checks using the standard isolated runtime."""
from pathlib import Path
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

folder = ROOT / "output" / "connection-recovery"
folder.mkdir(parents=True, exist_ok=True)
path = folder / f"browser-{time.time_ns()}.log"
specs = sys.argv[1:] or ["e2e/connection-recovery.spec.ts", "e2e/connection-probe.spec.ts"]
with isolated_runtime(python=sys.executable) as runtime, path.open("w", encoding="utf-8") as log:
    command = [shutil.which("npx.cmd") or shutil.which("npx"), "playwright", "test", *specs,
               "--project=desktop-chromium", "--project=mobile-chromium"]
    result = subprocess.run(command, cwd=ROOT / "frontend", env=runtime.environment,
                            stdout=log, stderr=subprocess.STDOUT)
print(path)
print(path.read_text(encoding="utf-8", errors="replace")[-6500 if result.returncode else -2200:].encode("ascii", "replace").decode())
raise SystemExit(result.returncode)
