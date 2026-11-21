# QA-021: concurrent client edits

Mode: implementation; gap: code. User authorized QA fixes, QA-021 first.
Source: QA register19–20Nov, QA-021 and generated35-page correction specification
in output/qa-register-analysis-20261121. This phase protects client edits only;
other28 IDs remain open. Prior static analysis → full ClientForm payload and
unguarded client update confirmed → conditional backend write and recoverable UI.

Root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD035c5a9ed5c3b8318a23f4bdbb0538504bef54fd. Existing auth, WhatsApp and
module-plan WIP is foreign. Client implementation paths were clean at start.

Contract: API PUT/PATCH requires expected_updated_at from the read snapshot.
Atomic conditional update prevents stale writes, including direct API calls.
No migration: reuse updated_at, strictly advance it on success. Preserve identity
normalization and existing permissions/field masking. Conflict returns409 with
client_edit_conflict and no write/audit success. Missing precondition is rejected.
UI sends changed fields only, retains draft on conflict, offers explicit review
of latest values before retry; never refreshes the token silently.

Impact: client metadata only, no lifecycle change; permissions unchanged;
existing audit/activity on successful update remain transactional. No new
notifications, BusinessEvent, AI or provider effects. No working DB access.

Checks: isolated regression/API tests for stale and missing versions, same/different
fields, normalization, tenant/role denial and rollback; affected clients suites,
Django check/drift. Frontend targeted two-editor browser flow, error/review/retry,
keyboard and RU/KK/EN; build/types once coordinated. Shared build/server coordination
requested from «Интеграции + Deploy»; no foreign processes stopped.

UI requirements: reuse existing ClientForm/StatusNotice/Button and tokens;
retained draft, explicit conflict/recovery, keyboard focus and localized copy.
Skills: zani-change-crm-domain, zani-run-verification, zani-review-frontend;
Anti Slop during (standing user instruction), human/copy modules for changed form.

## Implementation and verification

Implemented: dedicated ClientUpdateSerializer and atomic conditional service;
transactional existing audit/activity; changed-field ClientForm submissions,
retained draft, explicit latest-value review, recoverable GET failure and focus
return. Both form consumers reuse this behavior. No schema or permission change.

Verified in disposable SQLite environments from the canonical dirty checkout:

- `manage.py test apps.clients --noinput -v 1`: 92 PASS before the final
  future-date hardening and two additional regression cases; `output/qa-021/backend.log`.
- `manage.py test apps.clients.tests_concurrent_updates apps.core.tests_client_import_permissions --noinput -v 1`:
  35 PASS on final backend code, including eight concurrency cases;
  `output/qa-021/backend-final.log`. Counts overlap the preceding suite.
- `manage.py test apps.core.tests_tenant_isolation --noinput -v 1`: 11 PASS;
  `output/qa-021/tenant.log`. Same-business edit and forbidden business reassignment
  still exercise the API with a valid precondition.
- `manage.py check` and `manage.py makemigrations --check --dry-run`: PASS
  in the isolated runtime, no changes detected. All manage.py commands above ran
  through `scripts.codex_verify.isolated_runtime`, never ordinary db.sqlite3.
- Frontend `node --test scripts/tests/app-error-normalization.test.mjs`: 8 PASS.
- Build equivalents: `node scripts/check-i18n.mjs`,
  `node node_modules/typescript/bin/tsc -b --pretty false`, Vite app and widget builds
  with explicit output/qa-021/app-dist and widget-dist destinations: PASS.
  Full log: `output/qa-021/build.log`; reproducible local invocation:
  `.venv/Scripts/python.exe output/qa-021/build.py`.
- Browser: `.venv/Scripts/python.exe scripts/verify_client_concurrency_browser.py`
  uses the existing disposable quality-gate runtime, isolated ports and fixtures.
  Tests cover two real editor tabs, rejected stale PATCH, changed-only payload,
  draft retention, failed review GET/retry, explicit continuation, keyboard focus,
  final persistence of both edits and horizontal overflow. RU/KK/EN × desktop/mobile.
  Initial six-case PASS retained in `output/qa-021/browser-six-pass.log`;
  final rerun after 44px recovery buttons: 6 PASS (3.2m),
  output/qa-021/browser.log. Final RU desktop/mobile, EN desktop and KK mobile
  action screenshots visually inspected: labels/actions fit, no horizontal clipping.

Attempts: initial regression fixtures needed unique synthetic emails and an HTTP500
assertion for the project's exception handler; fixed without weakening behavior.
Initial browser config used output-directory cwd; fixed to canonical frontend.
Immediate focus after form.reset failed a browser assertion; requestAnimationFrame
restores focus after the reset renders. Failure log retained at
`output/qa-021/browser-focus-failure.log`. The final backend race test injects a
write between read and save in one transaction; this is deterministic CAS evidence,
not an independent multi-connection PostgreSQL stress test.

UI delivery: existing form, notice, buttons and tokens preserved. Localized warning,
latest-value labels, loading/disabled states, failed-read recovery, retained input,
keyboard activation and focus return verified. Empty latest values show the existing
em-dash convention. Form scrolls without horizontal overflow. Review is inline;
no new dialog lifecycle. Affected screenshots captured under output/qa-021/results.

Boundary: scoped QA-021 acceptance only; no whole-project certification, PostgreSQL
load test, live/deployed acceptance or working-DB migration. Shared build/server
coordination was requested twice from «Интеграции + Deploy»; no confirmation received.
Only disposable servers and separate build destinations were used; shared build
and live-server checks remain outside this local result. Foreign processes untouched.

Docs: CRM API contract and registered evidence updated. No README setup change,
new roadmap stage or permission/passport claim is needed for this defect correction;
existing roadmap and parallel capability work remain untouched. Other 28 QA IDs
remain open. No notifications, AI, BusinessEvent or provider changes.

Publication: code commit `dad129e6604a04e9894b6b78da4e58526624e5ec` normal-pushed
to origin/main; remote SHA read back and matched. Branch remains
`codex/ui-testing-toolkit`. Outgoing range contained only the reviewed QA-021 commit.
Task index and committed-range diff hygiene PASS. CI run 44924920096 was
`in_progress` at publication check, not a claimed PASS; no deployment performed.

Final scoped status: QA-021 implemented and locally verified. No remaining code
or local evidence gap in this phase. Deployment/live-server acceptance is separate.
Documentation registry parses and referenced evidence exists; browser runner compiles.
Whole-tree diff hygiene detects a pre-existing blank EOF line in foreign
`docs/testing/evidence/google-button-design-20261119.md:41`; excluded from this change.
Task-owned diff/index hygiene and outgoing-range checks are the publication boundary.
