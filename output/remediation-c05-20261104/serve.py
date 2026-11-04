import sys,runpy
from pathlib import Path
root=Path(__file__).resolve().parents[2];sys.path.insert(0,str(root))
from scripts import codex_verify
# Dedicated synthetic login pack; production throttle configuration is unchanged.
codex_verify.SAFE_ENV['AUTH_LOGIN_RATE']='1000/min'
runpy.run_path(str(root/'frontend/e2e/serve-isolated.py'),run_name='__main__')
