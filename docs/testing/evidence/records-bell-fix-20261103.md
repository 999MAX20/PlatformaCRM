# RECORDS-BELL-FIX-20261103

Owner approved one cycle for Records loading/read-error feedback and concrete
service-event text in the personal bell. Canonical `C:/Users/user/Desktop/PlatformaCRM`,
branch `codex/ui-testing-toolkit`, HEAD `e02a28f550e94a543c3d88acac7c1b19ee48f90b`
plus preserved WIP. Plan, starting status, owned before-files and delta are in
`output/records-bell-fix-20261103`; [source hashes](records-bell-fix-20261103-manifest.json).

## Result

- Ordinary dev Records404 was caused by the old `runserver --noreload` process:
  its loaded router lacked the workspace action present in current sources.
  Owner-authorized restart now serves the list. Final Chrome request to
  `/api/appointments/workspace/` with selected business/date/workflow returned200,
  count0/results0 and the correct empty state. Final dev uses StatReloader to load
  later Python changes, backend8000/frontend5173 from the canonical root. No working
  DB migration, seed/reset or data write was performed.
- `RecordsLoadError` distinguishes read failure from empty success and form save.
  HTTP404/503 show a list-loading explanation; invalid400 filters get guidance;
  permission errors retain their permission message. Retry restores the real list.
- Personal SYSTEM service events expose only an allowlisted localized message key
  for component + started/recovered. The existing server-owned reference must match
  an existing same-Business state and a valid episode. Missing/malformed/foreign
  references remain generic. Historical text, provider reference and errors stay
  redacted. Recipient/access/revocation filtering is unchanged. Announcements keep
  their authorized content, other work events keep existing source-based redaction.
  One state lookup per business per serialization context avoids per-event queries.
- No header service indicator returns. No new model, migration, permission grant,
  delivery behavior, BusinessEvent or AI action. Existing service observations and
  personal recipients are reused.

## Verification

All backend verification used `scripts.codex_verify.isolated_runtime`, installed
`.venv/Scripts/python.exe`, disposable DBs and isolated settings. Browser fixtures
used `safe_environment`, a new SQLite DB, loopback54555/54556, separate refresh cookie,
and outbound socket blocking in `runtime.py`; no ordinary DB or external provider.

| Check | Exact command / result |
|---|---|
| Focused backend, before dependent UI | `manage.py test apps.notifications.tests_service_messages -v 2`: 6 PASS |
| Completion backend | `manage.py test apps.notifications.tests_service_messages apps.notifications.tests_personal_api apps.notifications.tests_personal_services apps.notifications.tests_bell apps.notifications.tests_personal_recipients apps.core.tests_service_status apps.scheduling.tests_record_workspace -v 1`: 82 tests,81 PASS/1 skipped |
| System/schema | `manage.py check`; `manage.py makemigrations --check --dry-run`: PASS/no changes |
| Frontend focused | `node --test scripts/tests/record-filters.test.mjs scripts/tests/app-error-normalization.test.mjs scripts/tests/notification-header-model.test.mjs`:14 PASS |
| Build | `npm run build` under safe environment: types/i18n6666/app/widget PASS |
| Bundle | `npm run check:bundle`: PASS; app-shell342.1kB, below400kB; existing RU/KK chunks remain above500kB warning threshold |
| Browser initial | `npx playwright test --config=playwright.records-bell.config.ts` at the initial testMatch:6 PASS, RU/KK/EN list/filter/empty/404/503/400/retry and real service start/recovery in bell + Notifications page |
| Updated former S03 scenario | Same config with `--grep "service events show"`, `E2E_SERVICE_S03=1`:1 PASS, real producer event and localized RU/KK/EN text, absence of removed header indicator |
| Final Records/permission extension | Same config with `--grep "records real list" --output=../output/records-bell-fix-20261103/browser-records-recheck-results`:3 PASS including403 reason and keyboard Enter retry |

Browser commands require `RECORDS_BELL_ISOLATED=1` and `RECORDS_BELL_URL` set to the
isolated runtime frontend. Logs: `backend-focused.log`, `backend-completion.log`,
`system.log`, `drift.log`, `frontend-focused.log`, `build.log`, `browser-first.log`,
`browser-s03.log`, `browser-records-recheck.log` in the task output directory.
Source snapshot was unchanged after production build; later edits were tests/docs only.

The skipped test is the unchanged service-observer row-lock concurrency test on
SQLite (`has_select_for_update` unavailable). No collector/write/concurrency code
changed. PostgreSQL/full-project/release/live delivery suites were not run; these
scoped results do not certify full S03 or release readiness.

Retained failure: the first additional403 injection used `request_failed` with a
permission category. The frontend correctly follows the code registry, so the
permission assertion failed in all3 locales. The fixture now matches
`apps/core/exceptions.py` (`permission_denied` for403); all3 checks pass. No product
assertion or permission behavior was weakened. Logs/traces remain in
`browser-records-final.log` and `browser-records-results`.
The earlier S03 exact-text failure remains historical evidence in
[alert remediation](alert-remediation-20261103.md); this new slice fixes its cause.
The obsolete indicator steps were replaced following the explicit HEADER-CLEANUP
decision, while the concrete service-message assertion was retained and localized.

[Service start/recovery](records-bell-fix-20261103-assets/service-events-ru.png),
[Records RU](records-bell-fix-20261103-assets/records-read-error-ru.png),
[KK](records-bell-fix-20261103-assets/records-read-error-kk.png),
[EN/mobile](records-bell-fix-20261103-assets/records-read-error-en.png).
Screenshots and DOM checks cover real isolated fixture data; injected read errors
are clearly separated from actual API200/producer checks. Desktop1440/mobile390,
no horizontal overflow, keyboard retry and readable message text checked.

## Closure boundary

Both requested fixes are implemented and locally verified, including ordinary dev
Records recovery. No code/evidence or business-policy decision remains in this cycle.
Frontend/access/operations contracts, notification passport and S03 roadmap note are
aligned. README/CRM/AI/integrations/scheduling schema contracts need no change because
setup requirements, lifecycle, business data/API shapes and delivery rules did not change.

Publication remains blocked by pre-existing `.git/index.lock` and mixed prerequisites.
No staging, own commit/push, new CI or deployment. Other work remains intact.
Task-only isolated backend6864 (wrapper7944) and frontend9644 were stopped after
root/port checks. Ordinary dev remains running with autoreload; current runtime
is recorded in `output/records-bell-fix-20261103/dev-runtime.json`.
