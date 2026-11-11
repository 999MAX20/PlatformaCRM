# TEST-SESSION-ISOLATION-20261112

Owner request: reproduce cookie conflict and isolate test sessions without increasing
session lifetimes. Canonical source C:/Users/user/Desktop/PlatformaCRM;
branch codex/ui-testing-toolkit, starting7b26b548, tested shared checkout98967c60
plus task diff. Foreign product and documentation work preserved.

## Result and boundary

`safe_environment` assigns refresh, CSRF and Django session cookie names using a
stable hash of the disposable database path. Rebuilding one runtime preserves names;
new runtimes differ even if ports repeat. Browser bootstrap reuses the same function.
Django reads CSRF_COOKIE_NAME and SESSION_COOKIE_NAME with unchanged ordinary defaults.
Affected Python/browser tests now read configured names. No JWT/session timeout,
CSRF/origin/rotation/revocation policy, working DB, environment file or provider changes.
No permission, notification, BusinessEvent or AI behavior changes; no migration.

## Evidence

All commands use existing dependencies, canonical sources and disposable runtimes.
Detailed scripts/logs: `output/test-session-isolation-20261112/`.

- Before-fix namespace regression FAIL retained in baseline-regression.log.
- `.venv/Scripts/python.exe -m unittest scripts.tests.test_codex_verify.SafeEnvironmentTests scripts.tests.test_browser_test_runtime`:9PASS.
- `.venv/Scripts/python.exe -m unittest scripts.tests.test_codex_verify scripts.tests.test_browser_test_runtime scripts.tests.test_cookie_namespace scripts.tests.test_auth_cache`:25run,24PASS/1Redis-config skip. Parser-invalid-input stderr is expected.
- `.venv/Scripts/python.exe output/test-session-isolation-20261112/verify.py`:
  accounts tests, device sessions, session policy, login CSRF, admin MFA and MFA84PASS;
  isolated `manage.py check` and `makemigrations --check --dry-run` PASS.
- `node --test frontend/scripts/tests/audit-runtime.test.mjs`:7PASS.
- `.venv/Scripts/python.exe output/test-session-isolation-20261112/http_proof.py`:
  real HTTP, one shared cookie jar, same127.0.0.1/different ports, three disposable DBs.
  Before: default-name test login overwrites stand-in refresh; refresh on stand-in401.
  After: three logins coexist, six rotations200; test logout preserves default and
  other test; default logout preserves both tests. Tokens/cookie values not recorded.
  First harness run expected403 for an old masked CSRF token but got401 because
  the shared CSRF secret remained valid; actual conflict is overwritten refresh.
  Corrected diagnostic expectation; retained baseline server logs and final JSON.

## Browser acceptance attempts

`browser.py` runs only session-persistence, logout-recovery and account-session-
continuations on desktop Chromium with real isolated API. Initial25:19PASS/6FAIL.
Five continuation tests required navigation to Login while an earlier cookie response
was deliberately held. This contradicts approved C05 (`13862c6d`, identity-access
passport): logout waits for server confirmation. Updated those tests to assert
pending status/current account screen, release the response, then verify mutation →
logout → new login and reloaded new-account identity. No application change.
Initial sixth failure was login429, before invalid-refresh acceptance began.

Recheck `browser-recheck.py`:6PASS/1FAIL. All five corrected continuations passed;
unchanged expired-mutation case hit login429 after ten recent successful logins.
The other unchanged account scenario passed. Initial run already passed the
expired-mutation case; its rate-limit failure is retained and targeted separately.
Login rate10/min remains unchanged. Targeted invalid-refresh startup first exceeded
webServer120s while another runtime was running; no behavior assertion executed.
Final focused runs prepare disposable fixtures before the server startup deadline.

## Limits and operation

This reproduces a possible cause of the reported logout, not historical attribution
of every prior logout. Tests never touched the user's browser profile or working DB.
Existing test servers must restart through the updated runtime to adopt names;
no foreign processes stopped. Browser local storage is already origin/port scoped.
Manual/custom servers that bypass the safe runtime are outside this guarantee.
Full-project/release/provider/live certification and app build omitted: no product
frontend/source UI change, only test configuration/readers and Django cookie config.
No roadmap product milestone changed; access/session contract preserved. Operations
and testing guidance updated; README/product/AI passports do not need changes.

## Final scoped result

`invalid-refresh.py`:1PASS after pre-prepare; `expired-mutation.py`:1PASS in fresh
runtime. All25distinct selected browser scenarios have PASS evidence across scoped
batches; initial/recheck failures above remain visible, not a clean single-suite PASS.
No in-scope code/evidence remainder. Full release/live acceptance was not requested.
All owned wrappers exited; disposable contexts cleaned their databases and browser
servers. Working processes/browser profile were not restarted or modified.
Diff hygiene and owned-file review PASS; task files were clean at start. Source
manifest and exact executable harnesses retained locally with checkpoint.
Own local commit only. After fetch54pre-existing outgoing commits include foreign
work; publishing only this change by normal push is impossible without also sending
that work. No push/newCI/deploy; no remote or integration PASS claimed.
