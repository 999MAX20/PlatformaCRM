# ANALYTICS-DETAIL-COMPARE-20261111

Owner request: add metric drilldown and previous-period comparison to `/app/analytics`,
preserve the existing design and access rules, verify with backend tests and Playwright,
and preserve unrelated work. This is a new bounded addition after the nine-fix audit
closure, not a reopened audit or full R01 release. Work started11.11 and finished locally12.11.

## Result and boundaries

- Appointment KPI, rate numerator, status, source, service and responsible-user counts
  open the same period's paginated records, including archive. Previous values open
  the previous period's records. Rows link to the existing appointment workspace.
- `GET /api/analytics/reports/records/` requires analytics and appointments capability/view,
  intersects existing appointment scope, and independently masks inaccessible clients.
  Filters combine metric/source/service/responsible_user; team IDs must be visible in
  the report. Stable start_at/id pagination defaults to25, accepts up to100; UI uses20.
- Workspace `compare=previous` is opt-in. It uses the immediately preceding period of
  equal inclusive calendar length in the business timezone. Earliest supported dates
  return an unavailable comparison instead of overflowing. Prior-only service/source
  groups remain visible with current zero. Zero and missing values remain distinct.
- Rate changes use percentage points; relative count changes require a positive base.
  Financial changes use Decimal and require two available reports of the same source
  and currency. Stale, unavailable or incompatible reports have no financial delta.
- Existing Dialog/table/pagination, loading/error/empty states and API client are reused.
  Context changes close detail and abort the request;403 hides data without retry.
  RU/KK/EN and keyboard focus/Escape are supported. Current queues and selected-period
  CSV are unchanged; the definitions explain the comparison and export boundary.

No new KPI, financial transaction drilldown, schema/migration, permission model,
notification, BusinessEvent, AI, provider configuration, working database or deployment
change. Source is the canonical `C:/Users/user/Desktop/PlatformaCRM`, current branch
`codex/ui-testing-toolkit`. Start HEAD286c9cf6; final local verification used2537e8b6 plus
this task's owned diff. Own source hashes: [manifest](../../../output/analytics-detail-20261111/verified-source.json).

## Verification

Backend uses the existing `scripts.codex_verify.isolated_runtime`, disposable SQLite,
eager/mock test profile and the canonical source. The wrapper runs `check`,
`makemigrations --check --dry-run`, then the specified test labels; no working DB migration.

- `.venv/Scripts/python.exe output/analytics-detail-20261111/check.py apps.analytics apps.core.tests_import_export apps.core.tests_export_access apps.core.tests_export_history apps.core.tests_export_attempts apps.core.tests_client_pii_projections`:
  **147 tests:145PASS,2 existing PostgreSQL-only skips**; system/schema drift PASS.
  Covers analytics, exports and independent linked-client PII projection.
- `.venv/Scripts/python.exe output/analytics-detail-20261111/check.py apps.analytics.tests_workspace_comparison apps.analytics.tests_workspace_records`:
  final **11PASS**, system/drift PASS after adding incompatible/stale financial comparison cases.
  Calendar/leap/boundary/archive, standalone-report parity, scoped roles/tenant denial,
  read-only method, invalid filters, pagination/no duplicates and client masking are covered.
- In `frontend`: `node --test scripts/tests/analytics-comparison.test.mjs`:3PASS;
  `npm run check:i18n`:7236 keys PASS; `node node_modules/typescript/bin/tsc -b --force`:PASS.
- `node node_modules/vite/bin/vite.js build --outDir ../output/analytics-detail-20261111/dist-final`
  and `node node_modules/vite/bin/vite.js build --config widget/vite.config.ts --outDir ../output/analytics-detail-20261111/widget-final`:
  app and widget PASS. `node scripts/check-bundle.mjs` with
  `BUNDLE_ASSETS_DIR=../output/analytics-detail-20261111/dist-final/assets`:PASS,
  app shell349.5kB under400kB. RU/KK locale chunks retain >500kB warnings; no threshold changed.
- Playwright CLI Chromium with real isolated API, synthetic31current+6previous appointments,
  archive and a prior-only service/source. Five final scripts,56 assertions PASS:
  core13, recovery8, locales21, roles5, metrics9. These include exact detail cohorts,
  numerator counts, paging/page-size50, existing card/back, pending-request context change,
  earliest-date unavailable comparison,503/retry/403, manager own-team boundary,
  operator forbidden UI, empty/zero/missing, and RU1440/KK320/EN390 with keyboard/no overflow.
  The report still has31 current records after the flows. Desktop/mobile screenshots
  were inspected, including finance and horizontally scrollable detail tables.

Final logs: [backend](../../../output/analytics-detail-20261111/backend-completion.log),
[focused](../../../output/analytics-detail-20261111/final-focused.log),
[types](../../../output/analytics-detail-20261111/types-completion.log),
[i18n](../../../output/analytics-detail-20261111/i18n-completion.log),
[core](../../../output/analytics-detail-20261111/browser-core-final.log),
[recovery](../../../output/analytics-detail-20261111/browser-recovery-final.log),
[locales](../../../output/analytics-detail-20261111/browser-locales.log),
[roles](../../../output/analytics-detail-20261111/browser-roles-verified.log),
[metrics](../../../output/analytics-detail-20261111/browser-metrics.log).

## Retained failures and recovery

Initial comparison fixture assumed a manager had own appointment scope; the existing
policy grants business appointments but own team reporting. The fixture now explicitly
creates a custom own-scoped role and linked specialist; no product permission changed.
Imported fixture tests were initially discovered twice; module import removes duplication.
The first disposable browser seed used nonexistent Service.price; corrected to price_from.

Foreign staff_lifecycle syntax temporarily prevented configured URLs from importing.
A temporary analytics-only test URL configuration proved the focused boundary; after the
foreign fix, full configured focused/dependent checks passed. Initial full frontend build
failed on foreign management translations, and a later type check failed on foreign
ManagementCatalog.can_manage. Their subsequent source updates passed the recorded final
checks. No foreign code was repaired or staged by this task, and failures remain in logs.

Foreign i18n HMR invalidated the running provider context. Restarting only this task's
frontend with watch disabled and a full browser navigation recovered it. The environment
configuration and repository infrastructure were not edited. CLI multiline quoting and
version mismatch attempts are retained; final execution uses the current CLI's --filename.
Browser harness corrections used the actual localized status/pagination/scope labels,
waited for team rendering, and asserted the existing forbidden page rather than a redirect.
No access or cohort assertion was weakened.

## Closure

Owned browser/backend/frontend processes are stopped; the isolated runtime exited0 and
its TemporaryDirectory cleanup completed. Source hashes and Git/cleanup receipt are in
[RESULT](../../../output/analytics-detail-20261111/RESULT.json); detailed continuity and
commands are in [checkpoint](../../../output/analytics-detail-20261111/CHECKPOINT.md).

CRM/frontend contracts, money/analytics passport, capabilities and evidence registry agree.
No roadmap phase was authorized or closed; R01 and full release/live acceptance remain
open. Access/AI/integration/operations/README need no task change because setup, policy,
external effects and lifecycle behavior are unchanged. No scoped code/local evidence remains.
PostgreSQL concurrency, full-project E2E, screen-reader and production certification were
not requested and are not claimed for this bounded read/UI addition.

Fetch confirmed origin/main is an ancestor with44 pre-existing foreign outgoing commits.
Normal-pushing this branch to main would publish that unrelated work, so only this task's
reviewed paths/hunks are eligible for a local commit. No push, new CI or deployment is claimed.
