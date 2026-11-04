import sys, shutil, subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

with isolated_runtime(python=sys.executable) as runtime:
    with (ROOT / 'output/remediation-c09-20261104/build.log').open('w', encoding='utf-8') as log:
        result = subprocess.run(
            [shutil.which('npm.cmd') or shutil.which('npm'), 'run', 'build'],
            cwd=ROOT / 'frontend', env=runtime.environment, stdout=log, stderr=subprocess.STDOUT,
        )
print('build exit', result.returncode)
raise SystemExit(result.returncode)
