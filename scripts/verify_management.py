"""Verify Management against a disposable migrated database and real local APIs."""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

OUTPUT = ROOT / "output/management-implementation-20261111"
OUTPUT.mkdir(parents=True, exist_ok=True)
run = str(time.time_ns())
config = OUTPUT / "playwright.config.cjs"
config.write_text("""const { defineConfig } = require('../../frontend/node_modules/@playwright/test');
const root = require('path').resolve(__dirname, '../..');
module.exports = defineConfig({ testDir: root + '/frontend/e2e', testMatch: 'management.spec.ts',
 workers: 1, retries: 0, timeout: 150000, expect: { timeout: 15000 }, reporter: 'list',
 outputDir: __dirname + '/browser-' + process.env.MANAGEMENT_RUN,
 use: { baseURL: process.env.E2E_BASE_URL, actionTimeout: 15000, screenshot: 'only-on-failure', trace: 'retain-on-failure' },
 webServer: [
  { command: `"${process.env.E2E_PYTHON}" frontend/e2e/serve-isolated.py`, cwd: root,
    url: process.env.E2E_API_BASE_URL + '/health/', reuseExistingServer: false, timeout: 120000 },
  { command: `node node_modules/vite/bin/vite.js --host 127.0.0.1 --port ${process.env.E2E_FRONTEND_PORT} --strictPort`, cwd: root + '/frontend',
    url: process.env.E2E_BASE_URL, reuseExistingServer: false, timeout: 120000 }
 ] });
""", encoding="utf-8")
results = []
with isolated_runtime(python=sys.executable) as runtime:
    environment = runtime.environment
    environment["MANAGEMENT_RUN"] = run
    environment["MANAGEMENT_FIXTURE"] = str(OUTPUT / "browser-fixture.json")
    for label, command in [
        ("prepare", [sys.executable, "scripts/browser_test_runtime.py", "prepare"]),
        ("fixture", [sys.executable, "scripts/management_fixture.py"]),
        ("browser", [shutil.which("node"), "frontend/node_modules/@playwright/test/cli.js", "test", "--config", str(config), *sys.argv[1:]]),
    ]:
        log = OUTPUT / f"{label}-{run}.log"
        started = time.monotonic()
        with log.open("w", encoding="utf-8") as stream:
            result = subprocess.run(command, cwd=ROOT, env=environment, stdout=stream, stderr=subprocess.STDOUT)
        results.append({"label": label, "exit_code": result.returncode, "seconds": round(time.monotonic() - started, 2), "log": str(log)})
        print(json.dumps(results[-1]), flush=True)
        if result.returncode:
            break
(OUTPUT / f"browser-result-{run}.json").write_text(json.dumps(results, indent=2), encoding="utf-8")
raise SystemExit(results[-1]["exit_code"])
