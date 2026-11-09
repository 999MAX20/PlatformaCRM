# SESSION-NOTICES-20261105 вЂ” coordinated connection/session notices

Owner approved repair after screenshot diagnosis: session recovery appeared bottom-centre
outside NotificationHost while connection warning appeared bottom-right. This is frontend
presentation/recovery coordination, not remediation of the underlying intermittent server
outage. Canonical checkout, codex/ui-testing-toolkit, HEAD66101d50 + preserved foreign WIP.
Plan, original files, own patch, hashes, logs and screenshots: output/session-notices-20261105.

## Behavior

NotificationHost now surrounds AuthProvider; identity-scoped query/notification/action
providers remain keyed inside it, preserving account isolation. Session recovery and
logout notices use the host session group. Stable connection unavailability suppresses
only offline/temporary/provider session warnings, including while the connection card
is dismissed or reconnecting. Readiness success reveals any remaining session failure.
A specific recovery message exists in RU/KK/EN; other error categories retain their
specific text. Startup unauthenticated ErrorState, expiry, retry-after, restoration,
logout logic and mutation replay policy are unchanged. No backend/API/permission,
BusinessEvent/AI/provider, migration or working-database changes.

## Verification

- `node --test frontend/scripts/tests/notification-dedupe.test.mjs frontend/scripts/tests/auth-request.test.mjs frontend/scripts/tests/auth-return-path.test.mjs`:9PASS.
- `.venv/Scripts/python.exe output/session-notices-20261105/run.py`: initial20 tests,
  14PASS/6FAIL. Failures hit login429 from repeated shared-fixture logins; original logs,
  snapshots and traces preserved. No auth throttle/assertion weakened.
- Fresh isolated `run.py --grep 'connection and session|cross-tab cookie switch|refresh 429'`:
  5PASS, run1793861630201974500.
- Fresh isolated `run.py --grep 'logout reaches sibling|explicit logout clears|invalid refresh requires'`:
  3PASS, run1793861645050468900.
- Screenshot inspection found account preference overrode browser language in the first
  locale harness. Test now sets the isolated account preference and asserts html lang;
  screenshots disable animation and await opacity to avoid capturing a transition.
  Final `run.py --grep 'connection and session'`,1793861773785920400:3PASS;
  html lang verified RU/KK/EN; final screenshots inspected.
- Final `run.py --build`,1793861655701292900: build/types/i18n6895/app/widget and
  bundle PASS. Existing RU/KK dictionary chunks exceed advisory500kB; app-shell budget PASS.

Twenty distinct browser scenarios across scoped runs cover account switch, old-request
isolation, multi-tab refresh/logout, cookie restore, startup/current-user failure,
503/429/offline recovery with preserved drafts, expired refresh, successful logout and
coordinated notices. New flow proves one host, outage suppresses session, dismiss does
not reveal duplicate, readiness recovery reveals still-failing session, keyboard retry
restores it without losing draft; viewports1440/390/768. Faults injected at API routes;
real isolated authentication/server and app UI. Not a production outage root-cause test.

Runtime uses scripts.codex_verify.isolated_runtime, guarded synthetic seeds, disposable
DB/media/ports, fake scanner/eager mode. No dependency reinstall, workingDB use or shared
server restart. Backend/fullproject/live gates not needed for UI-only scope. No committed
range exists for this task; no artificial base/full-gate claim.

## Documentation and delivery

Frontend contract and settings/notifications passport updated; evidence registered.
Domain/access/AI/integration/operations contracts, root README, roadmap/acceptance need
no edits because requirements, configuration, permissions and domain behavior are unchanged.
Scoped design review preserves established warning tokens, type, width, motion and mobile
navigation clearance; each block is a real recovery status/action. No redesign/assets.
React review: existing context/portals reused; auth operations and identity-keyed providers
preserved, no new network request or dependency. Scoped accessibility/locale review is not
a complete product audit.

Publication remains blocked by pre-existing .git/index.lock and17 foreign outgoing commits.
Remote main readback0b3348e1; index empty. No own stage/commit/push/newCI/deploy, no lock or
history changes. No claim that the actual local server instability has been fixed.

No scoped code/local-verification remainder. Owned runtimes stopped; source continuity,
new-file review, docs links/registry and working/index diff hygiene PASS.
