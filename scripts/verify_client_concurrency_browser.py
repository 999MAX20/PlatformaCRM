"""QA-021 browser regressions using the existing disposable quality-gate runtime."""
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime


def main():
    output = ROOT / "output/qa-021"
    output.mkdir(parents=True, exist_ok=True)
    with isolated_runtime(python=sys.executable) as runtime:
        config = output / "playwright.config.ts"
        config.write_text(
            'import base from "../../frontend/playwright.config";\n'
            'export default {...base, webServer: base.webServer.map(server => ({...server, cwd: '
            + json.dumps(str(ROOT / "frontend"))
            + ', timeout:240000})), testDir:"../../frontend/e2e", '
            'testMatch:"client-concurrent-edit.spec.ts", timeout:120000, '
            'outputDir:"./results", reporter:[["list"]]};\n', encoding="utf-8",
        )
        with (output / "browser.log").open("w", encoding="utf-8") as log:
            result = subprocess.run(
                ["node", "node_modules/@playwright/test/cli.js", "test", "--config", str(config),
                 "--project=desktop-chromium", "--project=mobile-chromium", "--max-failures=1", *sys.argv[1:]],
                cwd=ROOT / "frontend", env=runtime.environment, stdout=log, stderr=subprocess.STDOUT,
            )
        print(f"QA-021 browser exit: {result.returncode}; log: {output / 'browser.log'}")
        return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
