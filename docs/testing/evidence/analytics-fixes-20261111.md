# ANALYTICS-FIXES-20261111

Owner request: fix all nine findings from the read-only `/analytics` audit in this
chat, verify through Playwright and backend tests, preserve the design, add no new
analytics features and preserve unrelated work. All nine are locally verified.

Canonical root: `C:/Users/user/Desktop/PlatformaCRM`; branch
`codex/ui-testing-toolkit`; starting HEAD `f01d2d8beecf5271bf85c970ad1b8ad751cce219`.
The verified dirty source hashes, starting Git snapshot, scripts, screenshots and
logs are in [task artifacts](../../../output/analytics-fixes-20261111).
The preceding read-only audit remains in
[its original directory](../../../output/playwright/analytics-audit-20261111).

## Results against the nine findings

| Finding | Result and evidence |
| --- | --- |
| Invalid Business / extreme dates caused500 | Positive bounded integer validation; workspace years0002–9998 reject unrepresentable edges with400. Regression tests include alphabetic, fractional, negative and oversized IDs and both date extremes. Existing tenant/role tests pass. |
| Calendar accepted forbidden periods | API exposes configured `period.max_days`; calendar validates inclusive days, explains the limit and disables Apply. Invalid URL periods have a correction action. Browser proves long-range rejection, valid correction, empty period, Escape/focus and arrows. Configured31-day backend regression also passes. |
| Team totals lacked scope/coverage context | Business/team/own scope and exclusion of records without an active responsible membership are stated in RU/KK/EN. No new totals or broadened access. Owner and manager screens verified; manager has no owner row. |
| Unanswered link opened a different set | Existing Inbox pipeline accepts `unanswered=true`: not archived, open, unread>0 OR handoff_required. URL/preset/reset plumbing preserves it. Tests cover each OR branch, overlap, ordinary open, closed and archived records; API IDs and browser count match analytics. |
| Refresh failure removed cached report | Temporary/offline/rate-limit errors retain the same query's report with warning and timestamp; export is disabled while failed.503→retry is verified.403 hides cached report and disables export; initial errors use existing error state. |
| Finance ignored locale | Existing date formatter receives active language; optional money-formatter locale preserves existing callers' default. Real manual-ledger figures and timestamps match Intl RU/KK/EN in browser. |
| Half-empty desktop row | Existing record distribution and source table share the desktop row.1440px screenshot inspected; no new chart or KPI. |
| Mobile hierarchy and broken words | Visible mobile heading, single scrolling tab row with active-tab reveal, compact actions, full-width period control and labels above bars. RU/KK320 and EN390 inspected; no page overflow. Resize320/390/768/1024/1440 keeps active tab visible. |
| Period accessible name omitted dates | Accessible button name includes the period label and both dates. Calendar keyboard arrows, Escape and focus restoration verified. |

## Verification

All backend commands ran from the canonical root using the existing
`scripts.codex_verify.isolated_runtime` helper, disposable SQLite, mock providers
and eager workers. The wrapper executes `check`, `makemigrations --check --dry-run`
and `test <labels> -v 1`; source is
[check.py](../../../output/analytics-fixes-20261111/check.py).

- `.venv/Scripts/python.exe output/analytics-fixes-20261111/check.py apps.analytics.tests_workspace`:
  initial14PASS; final16PASS, system and migration-drift checks PASS.
- `.venv/Scripts/python.exe output/analytics-fixes-20261111/check.py apps.analytics apps.core.tests_import_export apps.core.tests_export_access apps.core.tests_export_history apps.core.tests_export_attempts apps.core.tests_b5_performance apps.conversations.tests_inbox_context`:
  **133 total,131PASS,2SKIP**, system/drift PASS. Skips are existing PostgreSQL-only
  concurrency checks; this read/validation change does not modify locking/writes.
- `npm.cmd run build` in `frontend`: i18n7163 keys, types, app and widget PASS.
  After the final resize observer change, `npx.cmd tsc -b` and
  `npx.cmd vite build --outDir ../output/analytics-fixes-20261111/dist-final` PASS;
  unchanged widget and dictionary checks reused.
- `npm.cmd run check:bundle` with `BUNDLE_ASSETS_DIR=../output/analytics-fixes-20261111/dist-final/assets`:
  PASS. Existing RU/KK dictionary chunks remain over500kB warnings; app shell is
  within its400kB limit. No budget was changed.
- Playwright CLI Chromium, session `analytics-fixes`, real local API and synthetic
  fixtures: `browser-core.js`, `browser-period.js`, `browser-locales.js`,
  `browser-roles.js`, `browser-resize.js`. Final logs respectively:
  `browser-core-pass.log`, `browser-period-final.log`, `browser-locales-final.log`,
  `browser-roles-final.log`, `browser-resize.log`. Scripts and screenshots are retained.
  Core includes successful real CSV download; history dialog is reachable from the
  compact mobile button. Backend export suites cover access/revocation and jobs.

## Retained failures and recovery

The first new queue test omitted required `bot_id` and failed before assertions.
The fixture was corrected; the final focused and dependent suites pass. The initial
failure remains in `backend-queue.log`.

Browser harness corrections: exact source heading, waiting for tab render, selecting
the outer of two Inbox main elements, avoiding a hidden native combobox, and expecting
the existing operator forbidden screen rather than a redirect. No product assertions
were weakened. Intermediate scripts/logs remain alongside final evidence.

Vite crashed with Windows `EBUSY` while watching a CSV downloaded into
`frontend/.playwright-cli`. Own frontend was restarted on the same isolated port
with that artifact folder ignored by its watcher. No repository Vite/environment
configuration changed. Connection-refused and pending-response failures are retained;
the final core, calendar, locale, role and resize checks succeeded after recovery.

## Boundaries and publication

Existing design/tokens, scope rules, historical calculations, financial provenance
and normal export behavior are preserved. No schema, domain mutations, working-DB
migration, environment, provider, notification, BusinessEvent, AI or deployment changes.
The owned browser/backend/frontend processes exited, and the isolated runtime cleanup
completed with exit0. Other processes and unrelated source/docs WIP were preserved.

No code or local-evidence remainder within the requested nine fixes. This is not a
full-project release gate, large-data load test, screenreader certification, PostgreSQL
concurrency or production/R01 acceptance. Roadmap remains unchanged. Current CRM and
frontend contracts, the money/analytics passport, registry, STATUS and selected
checkpoint are updated; access/AI/integrations/operations/README need no changes
because policy, setup, external operations and roadmap scope did not change.

After `git fetch origin main`,42 pre-existing outgoing commits belong to other work.
Only this task's paths/hunks are eligible for the local commit; a normal push would
also publish that unrelated range, so no push/new CI/deployment is performed.
The local commit receipt is recorded in the task artifacts and final response.
