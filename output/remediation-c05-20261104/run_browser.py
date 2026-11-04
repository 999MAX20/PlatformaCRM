import sys,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.codex_verify import isolated_runtime
out=ROOT/'output/remediation-c05-20261104'
specs = sys.argv[1:] or ['e2e/logout-recovery.spec.ts','e2e/logout-callers.spec.ts','e2e/session-cache-isolation.spec.ts','e2e/session-persistence.spec.ts']
log_name = 'browser-cross-tab.log' if sys.argv[1:] else 'browser.log'
with isolated_runtime(python=sys.executable) as runtime:
 with (out/log_name).open('w',encoding='utf-8') as log:
  for cmd in [[shutil.which('node'),'e2e/django-e2e.mjs','prepare'],[shutil.which('node'),'node_modules/@playwright/test/cli.js','test',*specs,'--project=desktop-chromium','--project=mobile-chromium','--reporter=list','--config=playwright.logout.config.ts']]:
   result=subprocess.run(cmd,cwd=ROOT/'frontend',env=runtime.environment,stdout=log,stderr=subprocess.STDOUT)
   if result.returncode: break
print('browser exit',result.returncode)
raise SystemExit(result.returncode)
