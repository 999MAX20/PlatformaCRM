import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from scripts.codex_verify import isolated_runtime

phase = sys.argv[1]
labels = sys.argv[2:] or ["apps.bots.tests_booking_terms"]
commands = [["test", *labels, "--noinput", "-v", "2"]]
if phase == "completion":
    commands += [["check"], ["makemigrations", "--check", "--dry-run"]]
codes = []
with isolated_runtime(python=sys.executable) as runtime:
    with (Path(__file__).parent / (phase + ".log")).open("w", encoding="utf-8") as log:
        for command in commands:
            code = "from scripts.browser_test_runtime import configure_browser_runtime; configure_browser_runtime(); import django; django.setup(); from django.core.management import execute_from_command_line; execute_from_command_line(['manage.py', *" + repr(command) + "])"
            result = subprocess.run([sys.executable, "-c", code], cwd=ROOT, env=runtime.environment, stdout=log, stderr=subprocess.STDOUT)
            codes.append(result.returncode)
print(json.dumps({"phase": phase, "exit_codes": codes}))
sys.exit(max(codes))
