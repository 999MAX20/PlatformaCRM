import sys,shutil,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT))
from scripts.codex_verify import isolated_runtime
out=ROOT/'output/remediation-c06-20261104'
with isolated_runtime(python=sys.executable) as runtime:
 with (out/'browser.log').open('w',encoding='utf-8') as log:
  for cmd in [[shutil.which('node'),'e2e/django-e2e.mjs','prepare'],[shutil.which('node'),'node_modules/@playwright/test/cli.js','test','e2e/inbox-draft-provenance.spec.ts','e2e/inbox-inspector.spec.ts','--grep','draft provenance|switching conversations','--project=desktop-chromium','--project=mobile-chromium','--reporter=list']]:
   result=subprocess.run(cmd,cwd=ROOT/'frontend',env=runtime.environment,stdout=log,stderr=subprocess.STDOUT)
   if result.returncode:break
print('browser exit',result.returncode)
raise SystemExit(result.returncode)
