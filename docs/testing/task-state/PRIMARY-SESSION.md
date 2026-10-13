# PRIMARY-SESSION — PlatformaCRM

## CRM-TOOLBARS-20261013 — approved unified filters and date controls

Owner approved all12 recommendations and explicitly requested implementation.
Phase1: clients/leads/deals compact shared toolbar, precise server-side filters,
shared date/range picker in project design system. Calendar week/month/hover/day
inspector redesign is phase2 and is not started by phase1 completion.
Mode implementation; gap behavior/UX. Executor current primary via direct owner
request; canonical C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit,
base33795e273f0c782a143269ced190e49022472921. Starting unrelated ONEC pilot notes in
STATUS/this checkpoint preserved; snapshot output/crm-toolbars-20261013. No peer
approval loop/registry change. One actual writer, affected-path drift checked.

Approved behavior: clients All/WaitingReply, no Mine/New shortcuts or new ownership;
waiting=open scoped conversation with unanswered last inbound, successful human/AI
outbound only clears it, reading/draft/failure does not; handoff separate. Leads
All/Mine orthogonal to All/New/InProgress/Attention; no Hot, unassigned named honestly;
attention=open with missing owner, missing next action or overdue action, reason in
row. Deals All/Mine orthogonal to All/Attention/NoNextAction, existing lifecycle.
Defaults nonarchived clients, unfinished leads, open deals with visible restriction.
Advanced filters: clients source/tags(any/all)/segment/created/handoff/archive;
leads status/owner-or-unassigned/source/created/attention reason/archive; deals
status/stage/owner-or-unassigned/source/amount/created/expected-close/attention reason/
archive. Multi values OR within field, AND across fields; reject invalid ranges/IDs.
Search/quick apply immediately; advanced draft Apply/Cancel/Reset. URL restoration,
personal per-user/business saved views. Counts on same search/scope/advanced boundary,
not loaded page; failed counts not0. Active chips only when needed, no search duplicate.
Search240–280, wide one row, overflowMore preserving selection, two-row phone.
Date control opens on whole field, month/year navigation, range highlight and business
local day boundaries. Existing tokens/UI/API/selectors reused; no new permissions,
clinical data, lifecycle writes, notification/BusinessEvent/AI provider effects,
external calls or working DB migrations. No model migration anticipated.

Verification plan: focused isolated backend after each coherent selector/API slice,
valid/invalid combinations, own/team/tenant visibility, reply delivery semantics,
archive, date/timezone boundaries, multi filters and counts across pagination.
Completion: affected/dependent clients/leads/deals/read-scope suites + system/drift;
focused reachable RU/KK/EN desktop/mobile tests for URL/back, draft apply/reset,
presets, multiselect, keyboard/date/overflow/error/empty; one isolated frontend
build/types/i18n/bundle. No full-project gate absent demonstrated shared risk.
Review explicit task-owned diff, preserve other WIP, docs links/hygiene, conventional
commit and normal push origin main with remote SHA and actual CI readback.

Result: server selectors/API and shared React controls are wired for all three
workspaces. URL/draft/reset/personal browser views/date grid/contextual counts are
implemented; lead rows show grounded attention reasons. Phase1 scoped checks PASS.

Verification (canonical source; disposable DB/ports, existing locked dependencies):
- `.venv/Scripts/python.exe output/crm-toolbars-20261013/backend.py apps.clients apps.leads apps.crm apps.core.tests_b2_roles_queues apps.core.tests_mixed_membership_scope apps.core.tests_workspace_related_filters apps.core.tests_work_queues`: 126 PASS, `backend-1791911852879416700.log`.
- Same isolated helper with `apps.core.tests_crm_workspace_filters`: 3 PASS,
  `backend-1791912264773398700.log`; team/own/denied/disabled/anonymous boundaries.
- `.venv/Scripts/python.exe output/crm-toolbars-20261013/backend-final.py`: focused
  clients/leads/deals workspace + read-scope modules, 13 PASS; `manage.py check`
  and `manage.py makemigrations --check --dry-run` PASS, no drift;
  `backend-final-1791912600380125200.log`.
- Additional count/pagination methods: `apps.clients.tests_workspace_filters.ClientWorkspaceFilterTests.test_counts_ignore_quick_and_pagination_but_keep_search_and_source`, `apps.leads.tests_workspace_filters.LeadWorkspaceFilterTests.test_counts_cover_all_pages_and_ignore_only_quick_filter`, `apps.crm.tests_workspace_filters.DealWorkspaceFilterTests.test_summary_and_board_counts_cover_full_matching_scope` via `backend.py`.
  Leads/deals PASS in `backend-1791913761673988000.log`; clients fixture initially
  assumed configurable page_size=1, but actual default pagination is fixed50.
  Corrected test uses51 matching records and both pages; focused rerun PASS in
  `backend-1791913904685275400.log`. No pagination implementation change.
  Combined affected coverage:132 distinct tests, including16 new regressions.
- `.venv/Scripts/python.exe output/crm-toolbars-20261013/browser.py <project> crm-unified-filters.spec.ts --config=../output/crm-toolbars-20261013/playwright.config.ts`:
  `mobile-chromium` 4 PASS (`browser-1791913196031539000.log`),
  `desktop-chromium` 4 PASS (`browser-1791913470264043600.log`). RU/KK/EN across
  all three pages, URL/back/reload, draft cancel/apply/reset, saved views,
  multiselect, own+quick, status conflict, invalid date/amount, error recovery,
  zero/unknown counts, month/year/keyboard, highlighted five-day range; screenshots
  inspected at both viewports. Initial mobile overflow fixed by clipping the
  hidden width probe; subsequent startup timeout was before assertions. With
  host memory pressure (~64MB free of8GB), ignored isolated config allows240s
  startup; assertions retained, other processes untouched. Final reruns PASS.
- `.venv/Scripts/python.exe output/multibranch/frontend.py build`: i18n, TypeScript,
  Vite app/widget and bundle budgets PASS; `output/multibranch/build-1791913851855203100.log`.

Evidence logs/screenshots and starting unrelated-WIP snapshot remain under ignored
`output/crm-toolbars-20261013`. Relevant application inputs unchanged after PASS.
No working DB migrations, installs, external provider calls or deployment acceptance.
Full-project/local full-E2E omitted per proportional scope; push CI read separately.
Next: task-owned diff/index/range hygiene and normal publication receipt.

## DIRECT-TASK-AUTHORIZATION-20261013 — owner-directed peer tasks

Owner approved removing routine peer permission/reporting between CRM and CRM UI.
Policy-only scope: AGENTS, continuity instructions/hook and focused hook tests;
no product code, ownership transfer, phase, DB, dependency or process changes.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
clean starting HEAD 7d4fc192a0302ac4515eaf9598783a882f9a8866.
Behavior: direct owner implementation request permits the receiving non-retired
chat's bounded work, without primary polling/grant/release/completion messages.
Analysis remains read-only; preserve one actual writer and reconcile concrete
conflicting writes with the owner. Explicit task transfer retains context exchange;
managed primary rollover/retired/freeze protections remain, registry unchanged.
Risk: stale non-primary restriction or accidental bypass of transition guards.
Checks planned: focused node hook/CLI tests, syntax, docs links/consistency and
working/index/actual committed-range diff hygiene. No app builds or database/E2E
suites for this policy adapter. Hook trust remains REQUIRES_REVIEW_AND_TRUST;
unit tests do not prove app runtime activation. No peer tasks launched for receipts.

Verification: `node --test .codex/continuity-hook.test.cjs` — 31 PASS;
`node --check .codex/continuity-hook.cjs` and `git diff --check` — PASS.
Reviewed policy scenarios: both chats' direct requests, read-only limits, compact,
retired sources, pending transitions, validated finalization and unchanged metadata.
Publication limited to the eight reviewed policy/evidence/test files; no product WIP.

## INTEGRATIONS-SIMPLIFY-20261013 — two provider cards

Owner follow-up13.10: previous30b8f55 cards are too large. Approved delta: compact
centered pair, logo/name/status/action only; detailed descriptions/history/errors
inside the existing setup dialog. Primary confirmed sole UI writer again from clean
base5787fe76491ff7107c85ff92b349dc4835afc820, same root/branch, registry unchanged.
Risk: responsive centering, relocated details and keyboard focus. Reuse existing
tokens/setup/API; no backend changes. Verify desktop/mobile RU/KK/EN via existing
focused settings-workflow case, visual inspection and one isolated build; docs/diff
hygiene and normal publication. No new CSS tests, provider calls or full suites.

Compact follow-up verification:
- `.venv/Scripts/python.exe output/multibranch/frontend.py build` PASS, log
  `output/multibranch/build-1791905713712056300.log` (types/i18n/app/widget/budgets).
- Same focused `verify_ui.py desktop-chromium settings-workflow.spec.ts --grep
  "Integrations retains" --project=mobile-chromium` command: first attempt timed out
  starting webServer at120s while build ran, before any tests. Preserved log
  `browser-1791905724331161200.log`. Sequential retry after build: 2 PASS, each with
  RU/KK/EN, log/screens `output/inbox-density-20261008/browser-1791905906477230900`.
  No test assertions/timeouts weakened. Existing dialogs/focus/preferences proved.
- Live desktop and isolated desktop EN/mobile KK screenshots inspected: pair672px,
  compact approximately138px-tall cards, centered; mobile stacked, text uncut.
  Live МойСклад opening/Escape/focus return checked without setup submission.
- Six task-owned files. Backend/data/provider calls unchanged; full/backend/migration
  suites skipped for visual delta. Publication/actual CI receipt follows.

Compact publication: `aaa2d976a9e74a04eae632d172a22b3bc86f2915` normal-pushed
main; remote exact SHA verified. Base5787fe7 matched fetched main. Six reviewed paths,
63 local links, encoding and working/index/actual committed-range diff hygiene PASS.
[CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/38424218319) in_progress
on readback. Scoped writer released; primary/registry unchanged. No next phase.

Owner explicitly approved removing the duplicate page title, subtitle, metrics,
search/filters, financial-source form and all providers except МойСклад and 1C.
Mode frontend implementation; gap visual hierarchy/catalog scope. Reuse existing
ProviderCard setup flows, APIs, shared Button/Badge/Modal and semantic tokens.
Generation5 primary confirmed no competing writers and granted temporary sole
scoped writer to PlatformaCRM UI `01a0f32f-7d02-7263-a53d-496c8f9787f5`;
primary/registry unchanged. Canonical C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, clean starting base `8fda4ccd2550f99edd4fe9f36f767f5dbb7f2cc8`.
Result: exactly two redesigned cards, existing setup actions and real status/error
states, responsive desktop/mobile. Remove only the financial form's page entry;
stored settings and backend remain. No provider launch, external calls, backend,
permission, schema, notification, BusinessEvent or AI behavior changes. Prior audit
findings remain separate; this scope does not certify external integrations.
Risk: lost entry points, wrapping/locales, keyboard/modal focus and error visibility.
Checks: affected page and setup opening/closing in desktop/mobile RU/KK/EN, keyboard,
loading/error/read-only states; one isolated frontend build/types/i18n/bundle.
No new CSS-mirroring E2E, backend/full-project/live-provider suites or migrations.
Review docs/links and working/index/actual committed-range hygiene; explicit reviewed
commit, normal push main, remote readback and actual CI. Release scoped writer at close.

Implementation and evidence, 13.10.2026:
- Page now contains only МойСклад/1C in responsive cards. Existing setup flows,
  loading/no-business/error rendering and manage guards retained. Provider catalog
  outside this page, stored financial settings, imports/backend unchanged.
- User requested an image reference during implementation: built-in imagegen
  generated a preview from the current screenshot. This is an illustrative reference,
  not a runtime screenshot or a new token source. Final code uses exact shared tokens.
- Existing settings-workflow test updated because its financial form was explicitly
  removed. `.venv/Scripts/python.exe output/inbox-density-20261008/verify_ui.py
  desktop-chromium settings-workflow.spec.ts --grep "Integrations retains"
  --project=mobile-chromium` — 2 PASS (each runs RU/KK/EN), log/screenshots
  `output/inbox-density-20261008/browser-1791883568915205400` (log has `.log` suffix).
  Proves two provider entries, removal of financial/search controls, both dialogs,
  Enter/Escape/focus return and unchanged financial/profile API values. Disposable
  DB/ports, disabled providers; no setup submission or ordinary working DB writes.
- Screenshots inspected: desktop RU, mobile KK/EN; live desktop at1536px also
  inspected. Other locale snapshots captured. Existing loading/error/permission
  branches reviewed statically; fault injection/role matrix not rerun for layout.
- `.venv/Scripts/python.exe output/multibranch/frontend.py build` — PASS types,
  i18n, Vite app/widget and bundle budget, final log
  `output/multibranch/build-1791883640443561700.log`. Earlier build also passed;
  final rerun followed a fix aligning the request button's accessible/visible label.
- No backend/migration/full-project/live-provider gate: no corresponding behavior
  changed. Prior integration audit issues (business scoping, generic 1C credentials,
  request/health semantics and live readiness) are not claimed fixed by this layout.
- Eight intentional changed paths, no new tracked artifact. Publication receipt below.

Publication: `30b8f55f1798ed334765a17da88fd2d3974eb007` normal-pushed to main,
remote SHA read back exact. Fetched target matched starting8fda4cc; no merge/rebase.
Working/index/actual8fda4cc..30b8f55 diff hygiene, changed-file encoding,
63 local link paths and docs registration PASS. Existing anchor targets unchanged.
[Implementation CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/38376829919)
observed in_progress (no full-green claim). `gh` unavailable; read-only GitHub API
helper used with the canonical repository URL and exact SHA. Local build/browser
processes finished; normal dev retained. Scoped writer released at closure;
primary generation5/registry unchanged. Next step is owner review, no new phase.

## INBOX-COMPACT-20261013 — approved full-height conversation workspace

Owner approved the generated compact reference and detailed implementation analysis.
Mode frontend implementation; gap layout/interaction. Same registered primary generation5,
canonical C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit, clean
base 7df422d4ccdbc3683186ed7d233aeecb2def45a2. Prior Tasks scoped writer released.
Observable result: edge-to-edge Inbox, 288px list / flexible chat / 320px inspector;
72px normal thread header, 80px normal composer, message typography14/22; inline
AI/templates tools, preserved explicit AI preview/insertion and existing actions.
Inspector docks at1440px; narrower widths use drawer, phones retain list/thread flow.
Reuse AppLayout/WorkQueueLayout, shared Button/Tooltip/ActionMenu/Drawer, API hooks,
i18n and draft/retry permissions. No backend, schema, permission, notification,
BusinessEvent or AI provider-policy changes; no external sends/working-data changes.
Risk: responsive overflow, focus restoration, relocated actions and AI preview,
composer growth, scroll anchoring and retained drafts. Plan: layout then header,
composer/messages; targeted isolated Inbox interaction/locale desktop/mobile tests,
visual geometry on laptop/desktop/mobile and keyboard/zoom, one isolated build/types/
i18n/bundle. Preserve errors/forbidden/safety/retry/attachments; no CSS-mirroring E2E.
Docs/link and working/index/actual range hygiene; explicit reviewed commit and normal
push main with remote/actual-CI readback. R01 remains deferred; no full-project gate.

Implementation and scoped verification complete, 13.10.2026:
- Full-height shell, responsive header/menu, inline tools, bounded composer and
  compact bubbles implemented; AI draft copy now accurately describes preview.
- Existing isolated interactions: `.venv/Scripts/python.exe
  output/inbox-density-20261008/verify_ui.py desktop-chromium inbox-inspector.spec.ts
  --grep "thread menu|AI inserts|switching conversations|context errors"` — 4 PASS;
  same command with mobile-chromium — 4 PASS. Logs
  browser-1791880417218603900 and browser-1791880837673834900 in that output folder.
- New targeted flow: same helper with `desktop-chromium inbox-compact.spec.ts
  --project=mobile-chromium` — 6 PASS, RU/KK/EN desktop/mobile. Final log/screenshots
  browser-1791881055877515400. AI error/retry/explicit insertion/no send, keyboard
  focus, draft retention, inspector reflow and assignment/close/reopen covered.
- Initial runs found template focus restoration and breakpoint ordering defects;
  both fixed. Later EN resize assertion raced React media state; explicit waiting
  fixed the test. Earlier failures retained in output logs, final six cases green.
- `.venv/Scripts/python.exe output/multibranch/frontend.py build` — PASS types,
  i18n, Vite app/widget and bundle budgets; log build-1791881239095610700.log.
- Visual inspection: desktop/mobile plus laptop/tablet reflow, including long
  messages and warnings. Live read-only Inbox at1536x695: header72px, composer78.8px,
  history487.4px versus prior374px (~30% gain), no horizontal overflow. Browser
  zoom shortcut had no effect (DPR remained1.25); actual200% zoom is unverified.
  Responsive768px evidence is not claimed as browser-zoom certification.
- Disposable fixtures/DB/ports and disabled providers only; normal working DB
  not migrated/seeded, no external sends. Backend/full-suite/live-provider gates
  omitted: no backend contracts changed; R01 and deployment remain outside scope.
- All17 changed/new paths task-owned; explicit diff/new-file review, encoding,
  registered docs/links and working/index/committed-range hygiene required before
  normal publication. Publication and actual CI receipt follow below.

Publication receipt: implementation commit `0ca57fb3531ecc1eee12e2b9ca375bac2a3b4a8f`
normal-pushed to origin main; remote SHA read back exact. FETCH_HEAD was starting
base7df422d (origin/main tracking ref is stale because main is absent from fetch
refspec; ls-remote and FETCH_HEAD are authoritative for this publication).
Working/index and real7df422d..0ca57fb diff hygiene PASS;62 local docs links/anchors,
registration and changed/new encoding PASS. Git clean after implementation push.
[Implementation CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/38372395639)
observed in_progress, no green/full-project claim. No further product scope started;
next step is owner review of this UI; R01 still deferred.

## TASKS-REDESIGN-20261013 — approved task workspace and domain behavior

Owner approved both generated references and all task proposals, explicitly requested
implementation, and confirmed this chat as the scoped sole writer. Primary remains
01a130d8-8f15-7d23-bffc-5e61c21a98e2 / generation 5, idle verified natively.
Scoped writer 01a0f32f-7d02-7263-a53d-496c8f9787f5 only; no delegation/parallel writes.
Canonical C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
clean starting HEAD/base e30f990f401ff93a0baf7c59e7b78cb93ac186fc.

Mode implementation; gaps domain/API/UX. Result: usable task list with personal/all
scope, deadline groups, clear counts and optional team view; right inspector opened
only by selection, full-screen mobile and direct task route, links/comments/history,
editable details with draft recovery and explicit actions.
Reuse Task models/services, permission scopes, assignments, notification routing,
activity/audit, idempotency commands, shared UI tokens/primitives and API layer.
Approved delta: waiting state with reason/optional return date, resume; existing
open/in-progress/done/cancelled remain. Overdue is computed, snooze differs from due.
Operator/specialist can create for self; assignment/lifecycle enforce scope and active
available CRM account. Non-login specialists are context, never sole accountable
assignee. Task relations remain optional and individually permission-checked; task
completion never changes linked CRM lifecycle. My=assignee; created/watched separate.
Unified assignment validation, available actions, atomic effects, replay/conflict
handling, consistent business-timezone buckets and summary. Preserve historical
work and custom role overrides; no new permission framework.

Permission impact: scoped task creation and action checks. Notification/activity/audit:
retain routing/preferences and trace lifecycle/assignment; no external sends or new
channels. AI/automation callers must stay compatible with task transitions, no new AI
features. Intentional task schema migration, isolated tests only; working DB migration
requires separate target approval. No seed/reset or changes to other product pages.

Verification plan: focused isolated backend after each coherent slice, lifecycle,
invalid input, role/tenant/entity-access, assignment availability, atomic rollback,
idempotency and concurrent/stale updates; then affected tasks/core permissions,
notifications and relevant AI/automation consumers plus system/drift/migration checks.
Targeted reachable browser flows desktop/mobile RU/KK/EN, draft/error/empty/forbidden
and keyboard states; build/types/i18n/bundle once at completion using existing env.
No full-project gate absent demonstrated shared risk. Docs/index/actual range hygiene,
explicit task-owned commit and normal push main with remote SHA/actual CI readback.
No working DB activation, live provider, release or deployment acceptance implied.

In progress, 13.10 local / 12.10 UTC: domain/API and list/inspector/editor implemented
in the dirty task-owned tree; no publication or working-DB migration yet. Additive
tasks 0011 introduces waiting metadata and optional specialist context. Existing
idempotency receipts and transaction locks are reused; browser command headers are
explicitly allowed by CORS. Custom create permission is checked separately from update.

Focused evidence (canonical installed environment, disposable DB/ports):
- `output/multibranch/run.py test apps.tasks --verbosity 1`: 66 PASS, log
  `check-1791833286031169600.log`, before subsequent custom-create/snooze/CORS checks.
- Latest focused workspace tests: 17 PASS (`check-1791834210820842400.log`).
- `output/multibranch/postgres.py apps.tasks.tests_concurrency`: 15 PASS including
  14 accidentally discovered imported fixtures; concurrent edit itself proved one
  200/one 409 and winner persistence (`postgres-1791833461535984200.log`). Import now
  uses module qualification so the fixture class is no longer rediscovered.
- Frontend TypeScript PASS at initial integration; current final build pending.
  i18n references PASS, 5680 keys at that snapshot.
- Browser attempts preserved: first identified missing action/send translations;
  second textarea exact-label selector was inconsistent after draft rerender (DOM
  and screenshot proved draft intact); corrected to accessible textbox query.
  Third exposed a navigation request dropped while comment refresh was pending;
  guard now queues navigation until the mutation settles. Current desktop/mobile
  RU/KK/EN flow is running. No browser completion PASS claimed yet.
- Migration preservation test initially used historical account state against newer
  unrelated account columns; fixture corrected to current User/Business before
  migrating only tasks. Rerun pending, no migration defect inferred.
- Daily workspace policy checks PASS. Additional action-color suite has two unchanged
  baseline failures in CRMAgentRuntime and BillingSection. The original HEAD test
  against HEAD sources reproduces the same two failures (4 PASS/2 FAIL), recorded in
  `output/tasks-redesign/baseline-action-colors.log`; neither product file changed.
  Do not report this broader suite as green or silently alter those pages.

Next: finish dependent backend and migration checks, browser recovery/permissions/
links/filter coverage and mobile keyboard/visual review, then build/system/drift and
reviewed publication. References approved in owner conversation; fictional mockup
content must not enter working/production fixtures. Remaining primary roadmap paused.

19:56 UTC update: owner separately approved local `db.sqlite3` migration with backup.
`output/tasks-redesign/activate.py` backed up the canonical SQLite DB to ignored
`output/tasks-redesign/activation-20261012T195459Z/db-before.sqlite3`, asserted the
plan contained only tasks 0011, applied it successfully, and proved hashes of every
pre-existing table/column payload unchanged except one django_migrations receipt
(166 → 167). SQLite integrity/foreign keys and `manage.py check` PASS; no seeds.
Migration preservation regression PASS (`check-1791834577165714200.log`).

Dependent backend run found two task regressions among 224 tests: legacy staff/doctor
accidentally inherited new specialist CREATE; AI service request context has no HTTP
headers. Restored explicit legacy task preset and optional version-header lookup.
Both regressions plus workspace scenarios: 19 PASS (`check-1791834818160731500.log`).
Affected completion run is in progress on those fixes; its result is not yet PASS.

Browser lifecycle/draft recovery: desktop RU/KK/EN 3 PASS in
`browser-1791834516699603400.log`; mobile initially exposed shell-header overlap.
Inspector now uses the established drawer layer, mobile body scroll lock/keyboard
containment and drawer-level action menu. Mobile RU/KK/EN rerun 3 PASS (latest browser
log in output/tasks-redesign). Deadline conversion/grouping and daily workspace
policy: 8 Node tests PASS. Remaining: additional filter/link/conflict/permission UI
coverage, visual review, final build/types/i18n/bundle, isolated system/drift and
dependent backend result, docs/diff review and normal publication with CI readback.


20:08 UTC completion evidence, same task-owned snapshot based on e30f990:
- `.venv/Scripts/python.exe output/multibranch/run.py test apps.tasks apps.businesses.tests_access apps.businesses.tests_role_visibility apps.core.tests_b2_roles_queues apps.core.tests_crm_projection_access apps.conversations.tests_inbox_tasks apps.conversations.tests_inbox_context apps.ai_core.tests_crm_tools apps.automations.tests --verbosity 1`:
  225 discovered, 224 PASS/1 SQLite lock skip, log `check-1791834950572068900.log`.
  The skipped competing-writer case previously passed on isolated PostgreSQL.
- Same isolated wrapper with `test apps.branches.tests_staff apps.businesses.tests_member_deactivation --verbosity 1`:
  9 PASS, `check-1791835551922150800.log`; waiting remains pending staff work.
- Same wrapper `check` and `makemigrations --check --dry-run`: PASS/no drift,
  logs `check-1791835313421907900.log`, `check-1791835294344829200.log`.
- `.venv/Scripts/python.exe output/tasks-redesign/frontend.py browser --project=desktop-chromium --project=mobile-chromium`:
  lifecycle/draft RU/KK/EN plus list network recovery/view-only response 8 PASS;
  two new relation-flow tests failed on exact selector `Client` (actual accessible
  name includes selected value), `browser-1791835268323557000.log`. Corrected the
  selector and concurrent fixture to PATCH. No weakened behavior assertion.
- Same browser command with `--grep 'terminal actions|recovery en'`: 4 PASS,
  `browser-1791835491172234700.log`. Proves filtered empty state, created/watching,
  team-to-assignee list, client picker/link navigation, real 409 version conflict,
  retained draft and preserved concurrent description, complete/reopen/cancel/history.
  View-only UI used an explicit available_actions response stub; actual role denial
  and tenant/link masking are covered by backend, not attributed to that stub.
- Final desktop/mobile screenshots visually inspected, including KK mobile; task
  inspector uses drawer stacking/keyboard containment. Final English flow rerun
  includes later draft-guard corrections. No horizontal viewport overflow.
- `node --test frontend/scripts/tests/task-workspace.test.mjs frontend/scripts/tests/daily-workspaces-policy.test.mjs`: 8 PASS.
- `.venv/Scripts/python.exe output/tasks-redesign/frontend.py build`: PASS i18n,
  TypeScript, app/widget build and bundle budgets; `build-1791835502445554600.log`.
  Existing environment/lock reused, no local dependency reinstall.
- Scope contracts/passport/roadmap updated. Local full-project/E2E, target live
  worker/provider/deployment checks not run: no release/live acceptance authorized.
  Two unrelated baseline action-color failures above remain visible and unmodified.

Publication receipt: implementation `4abc60aab9e4b3b572ff93a64d22d3d54909abab`
normal-pushed to origin main from codex/ui-testing-toolkit; `ls-remote` equals HEAD.
Fetched target before publication was e30f990; outgoing range contained only this
reviewed task commit. Local origin/main tracking ref is stale because the configured
fetch refspec excludes main: use FETCH_HEAD/ls-remote, not that cached reference.
All 50 intended tracked/new files reviewed, UTF-8/local Markdown targets and diff
hygiene PASS; no credentials, local DB, backup, generated screenshots or logs staged.
`scripts/codex_verify.py --mode static --base-ref e30f990f401ff93a0baf7c59e7b78cb93ac186fc`
PASS on the committed implementation (range hygiene/system/drift included).

[Implementation CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/38302357789)
is push-triggered on this exact SHA: frontend success, full backend still running at
20:16 UTC readback. This is not an overall CI PASS. Workflow contains checks/tests/
audits, no deployment. Required scoped local gates passed; full local project gate
was not selected. Publication receipt/ownership metadata are a separate docs-only
follow-up, reusing unchanged application evidence; its own CI is reported separately.
Scoped writer released without changing primary/generation or assigning a next phase.
R01 remains deferred. Next operational check is the outstanding CI result; failed CI
must be classified and any task regression corrected before overall CI-green claims.

## R01-DEFER-20261013 — owner defers acceptance until UI completion

Owner explicitly postpones R01 while Tasks, Connections, Analytics and History UI
are unfinished. Settings completeness must be reconciled with existing scoped evidence
before overall acceptance; this is not a finding that previous implementations failed.
Resume acceptance after owner reports readiness. No product implementation or acceptance
suite authorized by this decision. Existing MB/settings evidence remains bounded.
Docs-only contract: record scope change in STATUS/roadmap/checkpoint; same primary,
canonical root and branch, clean starting HEAD `aff9d6f79fa64db6e6ca632d00f08c38dc9074f8`.
Risk: status consistency only. Checks: working/index/committed diff hygiene, local links,
registry/encoding and intended three-file review; no application build/database/browser
checks needed. Publish under standing authorization; no runtime/permission/AI changes.

## CRM-MB01-IMPLEMENT-20261012 — multi-branch implementation before R01

Publication/activation receipt 12.10 18:54 UTC: implementation `b48a82255d7d43b5ae48e340dc38373914835a51`
normal-pushed to origin/main; remote SHA readback matches. Branch retained as
`codex/ui-testing-toolkit`. CI run [38293650008](https://github.com/999MAX20/PlatformaCRM/actions/runs/38293650008)
currently has frontend success and backend running; no final CI PASS claimed yet.
Owner explicitly authorized backup and the three local schema migrations. Verified
online SQLite backup: `output/multibranch/activation-20261012T185321Z/db-before.sqlite3`.
`manage.py migrate scheduling 0009 --plan` showed only branches 0001/0002 and scheduling
0009; `manage.py migrate scheduling 0009 --noinput` applied all three successfully.
Database integrity and existing business-table row counts PASS; no Branch rows seeded.
Initial all-table-count assertion detected expected Django metadata additions, not
business-data changes: 3 migration receipts, 7 content types and 28 permissions.
Read-only follow-up proved every prior content-type/permission row preserved, exact
metadata deltas and zero other count changes (`result.json` in the same ignored folder).
`manage.py check` PASS. Backup remains local/ignored and is not published.


Local acceptance 12.10 18:48 UTC: MB1–MB5 implemented and verified; same owner,
canonical root and branch. Source freeze after branch snapshots revalidated under
Business lock (including approved staff-AI writes), branch lifecycle UI grants and
repeat-booking branch preservation. Publication and working-DB activation are separate.

Completion checks (installed .venv/Node, no reinstall, disposable DB and ports):
- `.venv/Scripts/python.exe output/multibranch/run.py test apps.branches apps.scheduling --verbosity 1`:
  110 discovered, 109 PASS + one PostgreSQL-only skip (`check-1791830469466096300.log`).
- `.venv/Scripts/python.exe output/multibranch/postgres.py apps.branches.tests_concurrency apps.branches.tests_scheduling`:
  11 PASS (`postgres-1791830438569383300.log`), isolated PostgreSQL 17 cluster initialized
  in a temporary directory, stopped and removed. Two prevalidated concurrent creates:
  exactly one 201, one 409, one visit. Fresh price/duration/address and migration schema
  exercised; existing PostgreSQL service/database untouched.
- `.venv/Scripts/python.exe output/multibranch/run.py test apps.ai_core.tests_crm_tools --verbosity 1`:
  19 PASS (`check-1791830659016412000.log`) after final staff-AI write revalidation.
- Earlier affected/dependent 280 run: 264 PASS, 16 FAIL (`check-1791828932304108100.log`).
  Unsaved Resource reverse relation caused 15 failures; one branch test targeted a
  protected serializer field. Fixed, 108-test retry PASS (`check-1791829442055927800.log`),
  superseded in affected branches/scheduling by final 110 above. Unchanged dependent
  lead/Inbox/membership/customer-AI/analytics results retained, not reported as a new
  all-project PASS. No known unresolved required failure.
- `.venv/Scripts/python.exe output/multibranch/frontend.py browser --project=desktop-chromium --project=mobile-chromium`:
  initial completed 10 PASS (`browser-1791830162025730300.log`). Final repeat-booking
  addition: 8 PASS, 2 keyboard-test expectation failures (`browser-1791830532848057600.log`).
  Native time-input segments retain Tab focus; corrected test exercises real button
  Tab/Enter/add/remove. Targeted same command with `-g configure`: 2 PASS
  (`browser-1791830818405450300.log`). Coverage: branch setup, failed-save recovery,
  grants and agent scope persistence, RU/KK/EN booking/reschedule/absence/retirement,
  historical links and repeat branch. Desktop/mobile screenshots inspected.
- `.venv/Scripts/python.exe output/multibranch/frontend.py build`: i18n/TypeScript/app+
  widget/bundle PASS (`build-1791830670238995800.log`). Initial compile errors corrected;
  no frontend runtime changes after this passing build.
- `run.py makemigrations --check --dry-run`: PASS, no drift
  (`check-1791830080962754900.log`); Django system checks passed in final backend runs.
- `.venv/Scripts/python.exe output/settings-workflow/check_docs.py`: changed/new-file
  encoding, existing registry and 168 links/anchors PASS before final receipt update.
  Task manifest reviews 94 source/docs/test paths; credential-pattern scan zero findings.
  Full release/E2E certification, real model calls, external sends and deployment not run.

Migration boundary: branches 0001/0002 and scheduling 0009 are additive schema changes;
first branch adoption is explicit application behavior, not automatic migration seeding.
Working target read-only verified as canonical `db.sqlite3`. At source freeze no working migration had been performed; the separately authorized
activation and backup are recorded above. No seed/reset or branch creation performed.
Outgoing baseline includes prior approved recovery receipt `383bf9a` above origin/main
`198e6a4`; no other writer WIP or unexpected HEAD change. Only CI is configured on push,
no repository push-deployment workflow. Review/stage explicit manifest paths; normal
push to main and remote readback completed in the receipt above; actual CI is tracked separately. R01 remains the next roadmap
phase after this bounded implementation/activation result.

Owner authorizes documentation followed by gradual implementation of CRM-MB01,
then R01. Analysis of models/API/UI/AI/tests on clean `383bf9aea8ca2de04efdf7b33440c5448cfd332a`
completed in this primary. Canonical C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, generation 5 primary 01a130d8-8f15-7d23-bffc-5e61c21a98e2.
No starting WIP; one writer, no worktrees/delegation. Existing dev 8000/5173 is
not a test fixture; no working DB migration, seed, external send or paid AI call.

Mode implementation; gap domain/UI/AI. Reuse Business membership/permissions,
Resource, Service, scheduling services/availability/exceptions, calendar/forms,
Business workspace, contextual team settings, Inbox scheduling/booking pipeline.
Approved: common clients/history, branch-scoped work; multi-interval cross-branch
specialist day with configured travel; branch-specific service price/duration;
single Business timezone; staff retirement/archive preserving historical links.
No new billing, clinical records, equipment capacity or autonomous existing-record
AI mutations. Five branches is acceptance example, not a cap.

Plan: MB1 branch/access/compatibility; MB2 service offers/assignments/intervals/travel;
MB3 absence/retirement/manual review; MB4 reachable Business/calendar/team UI;
MB5 branch-aware AI and integrated five-branch acceptance. Detailed checklist in
current roadmap; contracts in CRM/access/AI are authoritative, this is evidence.

Risks: shared permissions/availability and all booking callers, lifecycle/history,
stale AI offers, migration compatibility, monetary price snapshots, race conditions.
Permission impact: intersect existing permissions with allowed branches for writes;
common history must retain existing sensitive-field/record restrictions. Audit/activity
for changes; branch/address in existing appointment events/messages, no new sends.
AI: scoped public branch/service/staff sources, explicit customer selection, exact
slot revalidation/replay. Intentional schema/data migrations tested only in isolation.

Verification plan: focused isolated backend tests after each coherent domain/API
slice (happy/invalid, permission/tenant, rollback, interval/travel/absence, concurrency,
archived history and migration compatibility); then affected/dependent scheduling,
membership, Inbox booking/AI/message tests plus system/drift. Targeted reachable
browser/API scenarios desktop/mobile and RU/KK/EN, build/types/i18n/bundle once at
completion. No full release gate unless demonstrated shared risk requires it;
no installs with unchanged dependency inputs. Docs links/registry/diff/secret review;
explicit task-only commit, normal push origin main, remote SHA and actual CI.

Current: owner decisions documented; MB1 branch/access API focused 4 tests PASS
(`output/multibranch/check-1791826938767291800.log`). Initial run exposed test expectations around the
project's normalized 500 handler and concealed settings target (404 for specialist);
rollback/state assertions retained, branch read scope explicitly shared. Second run
left only the 403-vs-404 expectation; test now independently proves public branch
GET, denied PATCH and unchanged data. MB2 models/configuration/multi-interval
availability and appointment snapshots implemented; initial combined run 23/24
PASS, remaining test failed in fixture creation (duplicate blank email), fixed
unique fixture email and isolated targeted retry underway. No completed MB checkbox
or full user-facing PASS claimed; UI/AI/compatibility closure remains.

Progress 12.10: MB2 targeted fixture retry PASS (`check-1791827398300436800.log`).
First-branch compatibility 2 PASS (`check-1791827688159136700.log`). MB3 initial
17/18 passed (`check-1791827624367968700.log`): retirement correctly blocked on
the follow-up task created by visit cancellation. Test now proves that blocker,
completes the task through its API and then retires; staff/access 9 PASS
(`check-1791827929839444700.log`). Added explicit future-network grant protection.
Lead/Inbox booking and service-value snapshot paths: 8 PASS
(`check-1791828033488779700.log`). Branch-aware customer AI and existing automatic
booking: 13 PASS (`check-1791828215967667900.log`), including five locations,
remembered choice, address/terms, absence, stale offers and replay. No provider calls.
Frontend implemented WIP: branches workspace, offers/qualifications, multi-interval
week/date schedules, travel, branch booking/reschedule/calendar, staff absence and
retirement review, team grants and agent branch settings. First type check exposed
one number/string slot-counter type mismatch, fixed; final build/browser still pending.
New specialists require explicit branch/service assignment; first-location adoption
alone preserves existing legacy service eligibility. Shared catalog writes now
respect branch scope. Broader affected/dependent isolated regression running.
All changes task-owned, no staging/commit/push yet; same root/branch/HEAD.

## RECOVERY-20261012 — owner-authorized replacement of an unresponsive primary

Owner explicitly asked PlatformaCRM UI (`01a0f32f-7d02-7263-a53d-496c8f9787f5`)
to reconstruct context, archive unresponsive PlatformaCRM
`01a11776-e13a-76c2-9fc0-75d38228f649`, create one local successor named
«Платформа CRM продолжение», verify comprehension and transfer primary ownership.
This is the exceptional recovery in SESSION_ROLLOVER, not an ordinary source-led
handoff and not a new product phase. The coordinator owns only recovery metadata.
Source's attempts remained inProgress with no available response/tool activity;
cause unknown. Native archive returned archived=true; subsequent readback found
source in archived tasks, notLoaded, last turn interrupted. Source was archived
before metadata writes to remove the competing-writer risk; history was retained.

Canonical root C:/Users/user/Desktop/PlatformaCRM; saved project
local-3368c3df041be97f9549005fc6749ad2 still names Desktop/Zani, verified Junction
to the same canonical root. Branch codex/ui-testing-toolkit. Clean starting HEAD
`198e6a44ff092ad9644e3c7a53d3421e3d6872ea` matches remote main. Generation 4 -> 5
initially awaited one successor's comprehension. No existing transition/successor found.
Created exactly one local successor `01a130d8-8f15-7d23-bffc-5e61c21a98e2`
(«Платформа CRM продолжение»); read-only comprehension verified below.
No product, DB, server, hook-definition, dependency or archived-document changes.

Recovered completed scope: docs consolidation/roadmap/passports; Inbox local AI,
manual operator/inspector/relink work; Settings functional, redesign and workflow
changes. Latest Settings workflow: Company single form, financial source in
Integrations, role editor from employee/invitation, personal preferences in Account,
custom fields in full CRM cards, empty quick replies CTA and cleared Billing body.
CRM-MB01 only records the requirement for one Business with several branches
(five is an acceptance example, not a limit); no branch implementation was started.
Access, shifts, timezone, travel and migration policies remain unresolved.
Custom messaging scenarios, external integrations/billing and CRM AI development
retain their recorded deferrals. Local evidence is not production/live-channel admission.

Readback 12.10: CI 38236200299 success on 198e6a4; Settings implementation
CI 37947826093 success on 38be3be and receipt CI 37948418402 success on 16670de.
These supersede earlier pending observations, without rewriting historical receipts.
Source docs evidence records 129 links/anchors, registry/encoding and diff PASS;
actual committed-range `git diff --check 16670de...198e6a4` passed during recovery.
No pending source code edits or observed verification/write subprocesses.
User-requested dev is already running from the canonical checkout: Django 8000,
Vite 5173 (managed sessions of PlatformaCRM UI); do not duplicate or stop them.

Plan/DoD: create exactly one local successor; verify product, latest task, Git,
ownership, evidence and open decisions; register one generation change and retired
source; verify native archive; publish reviewed recovery metadata and notify successor.
Checks are docs/JSON/links/diff and native task/readback consistency. No application
test/install/build is required for this recovery. Old unresolved acceptance remains
unresolved. Next product action requires the owner's separate request in successor.

Release 12.10: successor `01a130d8-8f15-7d23-bffc-5e61c21a98e2` completed
read-only turn `01a130d8-9248-7481-92d2-17357cfa4ddf`. Coordinator checked the full
answer: correct V1/invariants, latest Settings workflow, docs-only CRM-MB01 and
unresolved branch policies, exact root/branch/HEAD and four coordinator-owned
metadata paths, no writes, no new phase, next step wait for release/owner request.
Native source archive readback and interrupted last turn were verified before writes;
no product-writing process was observed and Git remained unchanged except metadata.
Transition key `recovery-20261012-generation4-to5`: incremented once to generation 5,
new primary registered, source retired, transition idle, pending successor/handoff cleared.
This coordinator is not appointed primary; exceptional authority ends with publication.

Checks: `.venv/Scripts/python.exe output/settings-workflow/check_docs.py` PASS
(44 local links/anchors in the final recovery metadata),
JSON identity/generation/source-retirement assertions PASS, `git diff --check` PASS.
Stage only registry/STATUS/project handoff/this checkpoint; index and actual committed
range hygiene required before normal push. No app checks: metadata-only, source CI
already read back success. New push-triggered CI is inspected separately; pending
is not PASS and does not replace the verified source evidence. Publication SHA,
remote readback and actual new CI status are reported in the coordinator's final
receipt. After release notification successor waits for the owner's new task.

## DOCS-MULTIBRANCH-20261012 — один бизнес, несколько филиалов

Запрос владельца: зафиксировать реализацию сотрудников и графиков для одного бизнеса
с несколькими филиалами; пример — одна CRM на пять филиалов. Mode docs-only,
gap requirement/roadmap: записать целевой функционал, не реализовывать его в этом цикле.
Generation 4 primary, canonical root C:/Users/user/Desktop/PlatformaCRM, текущая ветка
codex/ui-testing-toolkit, чистая основа 16670de7c542401cf8ca0b333ab3dd8624fbba65.
Переиспользуем текущие product/CRM/roadmap/acceptance и паспорт scheduling; новый backlog
не создаётся. BusinessMember, Resource, WorkingHours сейчас привязаны к Business;
в просмотренных моделях businesses/scheduling отдельного филиала нет.
Риск документации: выдать план за runtime или неявно утвердить новую матрицу доступа.
DoD: единый ID CRM-MB01, сценарий пяти филиалов, сотрудники/графики/календарь,
критерии будущей приёмки и явные нерешённые политики. Проверки: согласованность,
локальные ссылки/anchors, working/index/реальный committed-range diff hygiene.
Без изменений кода, БД, миграций, разрешений, уведомлений, BusinessEvent или AI;
app build/backend/browser suites не нужны. После проверки — commit и normal push main.

Результат: CRM-MB01 добавлен в product/CRM/acceptance/roadmap; паспорт scheduling
отличает существующее поведение от будущего режима. Пять филиалов — проверочный
сценарий, не лимит. Решения по доступу, сменам, timezone, переездам и миграции данных
не выдуманы; они перечислены перед зависимой разработкой. Код/dev-процессы не менялись.
Проверка `output/settings-workflow/check_docs.py`: PASS, 129 локальных ссылок/anchors,
encoding/registry; ручная проверка согласованности и всего diff — PASS.
`git diff --check` PASS; index/committed-range hygiene проверяются при публикации.
Приложение/БД/браузерные suites пропущены как неприменимые к docs-only scope.
Следующий продуктовый шаг — отдельное назначение CRM-MB01 с решениями из acceptance;
это поручение закрывает только фиксацию требования.

## SETTINGS-WORKFLOW-20261009 — owner review and reachable flows

Owner follow-up explicitly requests a simpler Settings UI plus end-to-end verification.
Reopens prior redesign presentation on owner feedback, not its closed backend policy.
Mode implementation + verification; gap UI/workflow/evidence. Same generation 4 primary,
canonical root C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
clean base 3026debb3b2b9078fc2764dc8f2042a55ee0e90b; no other writer/worktree/delegation.
Observed in browser: custom-field headers misalign because independently sized grids
reserve different widths for action buttons. Live Vite PID 11600 cwd canonical frontend,
backend PID 16584 cwd canonical root; development profile, no Celery worker found.
Read-only inspection of working data; mutation tests use disposable isolated fixtures.

Acceptance: one Company profile/contact form; remove slug/read-only metadata and
appointments/finance/appearance tabs; retain functional timezone, currency, invoice
email, legal name and optional tax ID. Move finance source/connector controls into
Integrations using existing API and existing permission. Hide roles from Settings
navigation, retain contextual role editing from employee/invitation with selected role,
shared-role impact and return path. Personal notifications belong to Account only;
retain default-on delivery and per-user/per-business overrides. Inbox empty quick
replies links to permitted template creation. Custom fields align actions/columns,
explain their actual entity-card placement and prove creation/value persistence.
Security review should make existing events useful, not delete security infrastructure.
Clear Billing UI for future redesign (preserve stored data/API), verify real Usage source.
Category titles shift left relative to section links, desktop/mobile RU/KK/EN maintained.
Owner answer: custom message scenarios DEFERRED; no new trigger/delivery policy.

Reused layers: settings sections/model, business API/form, team catalog/permission API,
Account preferences, Inbox quick replies, CRM custom-field panels, connector API.
No new permission framework, messaging scenario, AI/BusinessEvent change, migration,
working-DB mutation, reset, external send/provider call or deployment. Risk: hidden
fields accidentally cleared, shared-role changes misrepresented as individual rights,
preferences leaking across businesses, lost drafts/return route, CRM field permissions.
Checks: targeted browser/API flows for profile preservation, contextual roles and
return, account preference isolation/defaults, Inbox empty-to-template-to-draft,
custom fields across client/deal/appointment cards, security states, empty Billing,
real Usage API mapping and responsive columns/navigation. Build/types/i18n/bundle at
completion; focused backend checks only if backend changes become necessary; reuse
unchanged domain proof. Diff/links/secret review, explicit commit + normal push main,
remote SHA and actual CI. No full release suite for this bounded follow-up.

Implemented the full authorized UI/workflow scope. Existing custom-field panel was
missing from full entity pages; client reproducer failed before the minimal reuse
fix, then client/lead/deal/appointment create/value/reload flows passed. Working UI
read-only inspection confirms aligned columns/action menu and simplified Company.
Desktop affected suite 24 PASS (`browser-1791557093952829900.log`), including
contextual existing-role edit/return, finance-source retry, per-user/business
notification isolation and Inbox empty-to-create-to-draft without sending.
Final build/types/i18n/app+widget/bundle PASS (`frontend-isolated-final.log`): 5532
locale keys; app shell 325.7 kB, Settings 68.7 kB, largest locale 436.3 kB before gzip.
Changed-doc encoding/registration/local links/anchors PASS. Source/backend,
schema and dependency inputs for earlier domain/system/drift proof unchanged.
Mobile affected suite 24 PASS (`browser-1791557309620003800.log`). One concurrent
desktop security-copy recheck timed out in web-server setup before any test
(`browser-1791557376582185200.log`); sequential retry 1 PASS
(`browser-1791557565093593600.log`), no source workaround or skipped gate.
The failed setup remains evidence; no product failure was reproduced by that attempt.
Mobile Company/custom-field screenshots visually reviewed; viewport overlays on full-page
screenshots are fixed navigation/save controls, not duplicate page blocks.
Pre-publication origin/main readback matched the starting base; preceding implementation/receipt CI
37936423372 and 37936544059 are now confirmed success via GitHub API.
All local acceptance passed; reviewed task-owned source/tests/docs and new files.
No unrelated WIP, credential/config changes, migrations or deployment.
Implementation `38be3be604a545ef486b0b2bf2af0c912f0918ee` committed and normal-pushed
to origin/main; remote SHA matches. Static gate on exact base `3026debb3b2b9078fc2764dc8f2042a55ee0e90b`
PASS, including committed-range hygiene, isolated migration drift and Django system check.
[CI 37947826093](https://github.com/999MAX20/PlatformaCRM/actions/runs/37947826093):
frontend success; backend checks/tests still in progress at final inspection around
15:00 UTC. This is not a CI PASS. All required local scoped checks and implementation
publication are complete; external CI result remains pending. This receipt records
that boundary without claiming release/deployment readiness. No additional product
scope is authorized; custom messaging scenarios remain deferred by owner.
Details: [evidence](../settings-workflow-20261009.md).

## SETTINGS-REDESIGN-20261009 — full Settings interface

Owner explicitly approved implementation across `/settings` using the five generated
desktop references after reviewing the project design system. Implementation/code gap;
reopens presentation and interactions after SETTINGS-FUNCTIONAL closure, not its backend
policies. Generation 4 primary; DOCS-ROADMAP writer explicitly returned the lease after
published `5434296a7826933617b8a8fde940588b58079490`, CI 37835398541 success.
Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
same clean starting HEAD; no pre-existing WIP. Single writer, no worktree/delegation.

Result: coherent Settings navigation and all ten existing sections, clear forms and
lists, contextual role/action/scope matrix and invitation access preview, local errors,
stable save actions, desktop/mobile RU/KK/EN. Reuse semantic tokens v2, shared controls,
drawers, existing API/hooks and real permission catalog. Preserve all four business
groups and saved reference values. Image sample content/validation is not product policy.
Scope: Settings, BusinessSettingsForm and necessary local components/i18n/tests/docs.
No global-shell redesign, permission framework, new policy, migrations, working-DB
seed/reset, provider calls or deployment. Existing tenant/permissions, notification,
BusinessEvent and AI behavior remain; test changed permission editing UI against actual
API. Risks: lost drafts, hidden feedback, misleading permission summaries, mobile overflow.

Verification plan: focused interaction/browser regressions for navigation, drafts,
role permissions, invitation preview and local error/retry; reachable affected sections
and keyboard/desktop/mobile/locales. Reuse unchanged backend evidence; backend changes,
if proven necessary, require focused tests immediately. Completion: build/types/i18n,
bundle, affected browser suite, visual comparison to references, diff/secret review,
explicit-path commit and normal push to main; verify remote SHA and actual CI.
Completed locally 09.10: all ten sections use the Settings layout and local editors,
configured-role action/scope matrix, invitation preview and stable save controls.
Existing permission/preset/custom-role policy remains. Missing permission POST is
now atomic with its audit: reproduced 7-test RED, immediate 11 PASS, then 52 affected
and dependent tests PASS. No schema, notification, BusinessEvent or AI-policy change.
Browser: full affected desktop 16 PASS + mobile 16 PASS; after final mobile width and
role disclosure fixes, affected desktop 6 + mobile 6 PASS; tablet all-sections RU 1 PASS.
RU/KK/EN, API/data assertions, draft persistence, local errors/retry, invitation preview,
POST/PATCH/readonly owner and keyboard/drawer behavior covered. Visual review includes
all ten desktop/mobile sections; final appointment controls fit mobile width.
Build/types/i18n/widgets/bundle PASS; isolated Django check/migration drift PASS.
Exact commands, logs, boundaries and prior failed attempts are in
[consolidated evidence](../settings-redesign-20261009.md).
No full release suite/live provider/PostgreSQL contention/deployment checks; scoped
SQLite/browser evidence does not imply production readiness. Ordinary DB untouched.
All helpers and screenshots remain ignored under output/settings-redesign.
Publication 09.10: implementation `9ea28fe6ff2d8060ea7c09ce7d1d3754fb06f798`
normal-pushed `5434296a..9ea28fe` to origin main; ls-remote matched exactly.
Canonical root/branch/registered writer unchanged. Reviewed all 39 intended files,
including new files; no unrelated work or secret-pattern findings. Working/index/range
hygiene PASS. `.venv/Scripts/python.exe scripts/codex_verify.py --mode static
--base-ref 5434296a7826933617b8a8fde940588b58079490` PASS on committed implementation.
Docs registry/local-link check PASS: 592 links, 15 anchors, no errors; archives and
owner registry unchanged. Git status clean after refreshing identical file metadata.
Only push CI is configured in repository workflows; no deployment performed.
[Implementation CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/37936423372)
was in_progress at publication readback; this is not a CI PASS claim.
Scope implemented, locally verified, committed and synchronized. No next product
phase is authorized; CI outcome remains separate from this local acceptance.


## DOCS-ROADMAP-20261009 — production route and domain passports

Owner requested one production roadmap and substantive passports in the existing
pre-production directory, with all preserved acceptance IDs mapped to that route.
Docs-only implementation; gap type documentation/roadmap. Reuse current contracts,
two AI passports, source code and published scoped evidence; no new business policy,
product phase, runtime changes, migrations, provider calls or deployment.
Generation 4 primary remains unchanged. Primary explicitly released sequential
docs-writing to PlatformaCRM UI after Settings completion. Canonical root
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`, clean base
`768b2675f38f1f00a5273f627c3f184b91e6a015`; Settings CI 37832658462 success.
Acceptance: one route with dependencies/results/DoD/status/evidence, substantive
passports, complete acceptance mapping, registered navigation and no false readiness.
Risk: converting deferred policy into work or scoped PASS into production readiness.
Checks: source/contract consistency, links, JSON registry, acceptance ID coverage,
working/index/committed-range diff hygiene and complete intended-file review.
No application checks: code/config/dependency inputs unchanged. Finish with reviewed
docs commit, normal push to main, remote SHA and actual CI; return the writing lease.

Implementation: one `docs/current/roadmap.md` with seven result stages, dependencies,
DoD, scoped foundations and six deferred directions; all 36 preserved acceptance
IDs explicitly mapped, including historical closures and V1 policy boundaries.
Thirteen new domain passports plus the two retained AI passports cover fifteen
directions. Navigation, template, source map, project state and JSON registry updated.
Current contracts retain their meaning; no archive bodies or primary registry changed.
Legal placeholder bodies and commercial processing remain production boundaries.

Verification 09.10 on base `768b2675` + docs patch: standard-library Python check
via `.venv/Scripts/python.exe -` parsed the JSON registry (unique/existing paths),
checked every local Markdown target/heading anchor in changed/new documents and
compared the explicit 36-ID acceptance set with roadmap: PASS. Static review traced
passport claims to current contracts, services/routes and existing evidence; checked
all new files for unrelated/private material. `git diff --check` PASS. Index and
real committed-range checks run at publication. No app install/build/backend/browser
or live checks: docs-only; previous application evidence retains its original scope.
Published commit/remote readback and actual push-triggered CI are reported in the
task's final receipt and writing-lease return, without a self-referential commit SHA.
Final staged checker also proved both original AI bodies preserved. Its first
invocation incorrectly required the JSON index to register itself as a Markdown
document; that checker-only assertion was corrected and the full check passed
(26 docs/JSON files, 343 local links/anchors, 36 acceptance IDs).

## SETTINGS-FUNCTIONAL-20261008 — functional settings completion

Owner-authorized scope transferred by the read-only settings audit task after Inbox
completion: all ten existing settings sections, no cosmetic redesign/new navigation.
Generation 4 primary; canonical root and branch unchanged. Clean starting snapshot
`33b316d9cfdb44aab2601ddedbb9830f5fb6b4d4`. Mode: domain/API/frontend corrections and
source-backed evidence. Reuse existing settings, role permissions, tenant scoping,
notification scheduling/delivery, billing metadata, API clients and shared controls.
Trace each setting/action through UI, API, storage, runtime consumer, permission and
verification. Retain working controls; fix broken behavior; make reference-only
metadata honest; remove inert editing without deleting saved data. Cover business,
team, roles, security, appointment messages, personal notifications, quick replies,
billing, usage and custom fields. Preserve approved specialist/history semantics,
role presets, financial-source choices and provider/AI development boundaries.
No new billing provider, quotas, commercial policy, lifecycle/permission framework,
clinical behavior, schema or paid/external calls; no working-DB migration/seed/reset.
Risks: wrong-tenant reads/writes, partial permission changes, stale notification jobs,
misleading saved settings, hidden permission denial and stale form/cache state.
Checks: focused isolated backend tests after each coherent service/API correction,
before dependent UI; then affected/dependent suites, system/migration checks,
targeted reachable desktop/mobile and RU/KK/EN UI flows, final frontend build/types.
Use mocks for external delivery and disposable databases. No full local release
suite without demonstrated need. Record registry/evidence, review explicit paths,
normal-push verified change to main and inspect actual CI. Initial next step:
selected-business billing resolution and atomic role visibility changes.

Local completion 09.10: all ten sections are mapped in the registered
[settings evidence](../settings-functional-20261008.md). Selected-business queries,
atomic role scopes preserving grants, actual membership checks, security counters,
notification preferences and delivery readiness/reconciliation are corrected.
Reference-only settings preserve stored metadata without promising runtime behavior.
Custom definitions/values enforce tenant, entity access, role, types and retention;
card controls preserve typed arrays/booleans and untouched values. Forms retain drafts
and show real loading/error/recovery states. Appointment input overflow found during
visual inspection was corrected and verified at desktop/mobile widths.

Verification uses the existing dependencies and `scripts.codex_verify.isolated_runtime`
through the ignored helpers in `output/settings-functional-20261008/`. Commands:
`.venv/Scripts/python.exe output/settings-functional-20261008/verify_backend.py <labels>`;
logs below are relative to that directory. Evidence is reused only for unchanged inputs.
- `apps.billing.tests_settings_scope apps.billing.tests.BillingFoundationTests`:
  20 PASS, `backend-1791483108063750200.log` (selected business, denial, invalid
  metadata, audit rollback, current/monthly usage); unchanged since that run.
- `apps.businesses.tests_access.TeamAccessTests apps.businesses.tests_role_visibility
  apps.businesses.tests_settings_team`: 40 PASS,
  `backend-1791483005594091600.log`; `apps.businesses.tests_settings_team`: 4 PASS,
  `backend-1791483180228940500.log`.
- `apps.core.tests_security`: 13 PASS, `backend-1791483348303765700.log`.
- `apps.scheduling.tests_settings_delivery apps.notifications.tests`: 26 PASS,
  `backend-1791484223189422400.log`; `apps.notifications.tests_settings_preferences`: 4 PASS,
  `backend-1791484923598116500.log`.
- Broad affected run `apps.scheduling apps.notifications apps.billing
  apps.businesses.tests_access apps.businesses.tests_member_deactivation
  apps.businesses.tests_role_visibility apps.businesses.tests_settings_team
  apps.core.tests_security apps.core.tests_custom_fields
  apps.conversations.tests_quick_replies`: 200/202 passed,
  `backend-1791485572718350100.log`. Two legacy Telegram fixtures had client IDs
  but no ready channel; fixtures were completed with enabled/active synthetic
  transport, without weakening channel expectations. `apps.scheduling.tests`:
  49 PASS, `backend-1791485937050184400.log`.
- Later queue-lock + extended-field run `apps.scheduling.tests_settings_delivery
  apps.scheduling.tests apps.notifications apps.core.tests_custom_fields`:
  99/100 passed, `backend-1791486206843899800.log`; the new reschedule test needed
  a staff Resource under the existing booking contract. Fixture corrected.
- Final `apps.scheduling.tests_settings_delivery apps.businesses.tests_role_visibility
  apps.businesses.tests_settings_team apps.core.tests_api_contracts`: 25 PASS,
  `backend-1791486447962966600.log`, covering final lock changes and corrected
  reschedule/cancel fixture. Earlier failed runs are not labelled whole-suite PASS.
- Final `apps.core.tests_custom_fields apps.core.tests_crm_projection_access`:
  41 PASS, `backend-1791487029812351200.log`, including invalid calendar dates,
  explicit business selectors, scope/role denial, typed data and audit rollback.

Browser command:
`.venv/Scripts/python.exe output/settings-functional-20261008/verify_ui.py <project> settings-functional.spec.ts [--grep ...]`.
Eleven distinct scenarios are verified on desktop and mobile, using real local APIs,
disposable fixtures and injected 503 only for recovery. RU/KK/EN all ten sections,
profile persistence/invalid timezone, appointment drafts, preference load recovery,
custom definition/card/deactivate, billing metadata/plan preference, atomic visibility,
quick reply to Inbox draft, and manual invitation/revoke/department/login toggle.
- Desktop profile passed in `browser-1791486217224581800.log`; preferences passed
  in `browser-1791486508651367200.log`. Those runs subsequently stopped on unrelated
  test-selector errors, retained in the logs. Corrected appointment/card tests passed
  later; the failures are not product acceptance exceptions.
- Desktop billing/role/quick-reply/team: 4 PASS, `browser-1791486967464559000.log`.
- Final desktop locales/appointment/custom fields: 5 PASS,
  `browser-1791487275581052600.log`, including edit-role picker, required metadata
  read-only state and label edit retaining object-based choice labels.
- Mobile complete run: 11 PASS, `browser-1791487071203693200.log`; final extended
  custom-field flow: 1 PASS, `browser-1791487365894026900.log`.
- Custom-card checkbox selector was scoped to its field group so retained fields
  from a previous run do not collide. Desktop `--grep 'custom definition'
  --repeat-each=2`: 2 PASS, `browser-1791487662533786100.log` on the same disposable DB.
- Harness fixes used the actual client drawer route, localized MiB label and the
  Select's accessible name including its selected value. Initial raw-key assertion
  matched concatenated English prose; narrowed to actual leaf text. No required
  behavior/assertion was removed. Reviewed screenshots include desktop business,
  appointment cards and mobile RU appointment/KK custom fields; final desktop
  RU/KK/EN screenshots are in the last desktop run.

`.venv/Scripts/python.exe output/settings-functional-20261008/verify_frontend.py`:
`npm run build` (i18n, TypeScript, app, widget) and `npm run check:bundle` PASS,
`frontend-isolated-final.log`. Isolated `manage.py check` and
`manage.py makemigrations --check --dry-run` passed 08.10 19:12 UTC; later field
value validation did not change models/configuration. No schema changes detected.
Full local release/E2E gate skipped under proportional affected-scope verification.
SQLite and mocks do not certify PostgreSQL lock contention or live provider delivery.
No working-DB writes/migrations, dependency installs, external messages, payments,
paid AI calls, notification categories, BusinessEvents or new permission framework.
An already-started provider request cannot be recalled; a revoked claim stays revoked.

Working diff, 57 intended changed/new paths, Markdown links, registry JSON and
credential-shaped-content review PASS. Publication uses a conventional Settings
commit and normal push to main; exact commit/remote readback and actual CI receipt
are reported in the task completion message. Base Inbox commit `33b316d9` CI
completed successfully (run `37819153554`). Fetch/readback
confirmed actual remote main still equals that base; the limited local fetch refspec
required explicitly refreshing `refs/remotes/origin/main`. No conflicting writer.
The separate docs architecture task `01a0f32f-7d02-7263-a53d-496c8f9787f5` remains
read-only while Settings verification/publication completes; no write lease yet.

## INBOX-RELINK-20261008 — confirmed client replacement

Owner approved and requested implementation of the described confirmation dialog.
Mode mixed domain/UI implementation; closes the client-replacement policy gap only.
Generation 4 primary, canonical root/branch unchanged; clean base
`101f0df8e172ac2484f17dc96d683a0a0636092e`. Reuse link-client endpoint, scoped access,
activity/audit helpers, existing dialog, API client and locale dictionaries.
Result: selecting a different client previews incompatible lead/deal links; explicit
confirmation atomically changes client and detaches only those links. Entities,
their ownership/history, messages, appointments and tasks remain intact. Same client
is a no-op; no conflicts means immediate linking. Hidden entities have no exposed
identity. Signed confirmation binds actor/target/current relation snapshot; changed
relations require refreshed confirmation. Server repeats tenant/role checks.
No lifecycle/permission framework, provider/AI policy, notification, BusinessEvent,
schema/dependency/environment changes; no working-DB mutations or paid/external calls.
Activity/audit record the replacement. Risk: stale confirmation, partial writes,
privacy leaks and unintended deletion. Focused isolated backend regressions first:
preview/no-op/compatible/confirmed, tenant/role denial, stale/forged token, rollback,
preserved history and retry. Then affected Inbox suites, system/migration checks,
desktop/mobile reachable confirmation/cancel/recovery, RU/KK/EN and final build.
No full local release suite. Update current contracts/evidence and publish verified
explicit paths via normal push; read remote SHA and actual CI.

Implementation: `client_linking.py` reuses link-client with a typed 200 preview or
the existing conversation result. Signed opaque digest expires after 10 minutes;
hidden child identities are absent from both preview and decoded token. Same-client
retries write no duplicate activity/audit. Transaction locks cover replacement and
the existing link-lead/link-deal/create-client actions so stale loaded objects cannot
restore a previous client. The old CRM qualification preview is invalidated while
other metadata/history remains. No provider/model behavior was developed.

Backend receipts (`output/inbox-relink-20261008/`, `.venv/Scripts/python.exe`):
- `verify_backend.py apps.conversations.tests_client_linking.ClientLinkingTests`
  — 11 PASS, `backend-1791480529448373200.log`, before dependent UI work.
- Initial dependent set — 47 PASS, `backend-1791480763213079200.log`.
- Approval invalidation/actor/client access regressions + AI confirmation — 25 PASS,
  `backend-1791480880137201100.log` (intermediate; final below supersedes it).
- Final `verify_backend.py apps.conversations.tests_client_linking.ClientLinkingTests apps.conversations.tests_ai_confirmation apps.conversations.tests_inbox_context apps.conversations.tests_inbox_tasks apps.bots.tests.InboxBackendTests`
  — 88 PASS, `backend-1791480964102981000.log`, including 15 replacement regressions.
  Mocks, disposable SQLite, no working DB/provider calls. Stale-write/approval,
  replay and rollback tested; live PostgreSQL lock contention is not certified.

Browser: desktop RU/KK/EN confirmed replacement, cancel, refreshed concurrent-link
preview, injected 503 recovery, retained records/messages/draft and keyboard focus
PASS (`browser-1791481158604242100.log`, 3 cases); RU screenshot visually inspected.
Earlier failures retained: initial fixture did not confirm its own setup replacement
(`browser-1791480734868264000.log`); repeated locale fixture names caused ambiguous
locator (`browser-1791480945620263900.log`, RU flow passed); after unique names, one
expected-text assertion still used the old names (`browser-1791481040864274900.log`).
Fixture/assertion corrections did not weaken the runtime requirements.
Mobile same spec — 3 PASS (`browser-1791481229203134600.log`); RU screenshot
visually inspected, no overflow. Isolated `manage.py check` and
`makemigrations --check --dry-run` PASS (`system-migration.log`).
`verify_ui.py desktop-chromium inbox-inspector.spec.ts` — 11 PASS
(`browser-1791481329224830600.log`); two existing setup steps now explicitly confirm
their fixture relinking. Combined 17 browser cases for this change. New flow commands:
`verify_ui.py desktop-chromium inbox-client-relink.spec.ts` and
`verify_ui.py mobile-chromium inbox-client-relink.spec.ts`.
`verify_frontend.py` — i18n, TypeScript, app/widget build and bundle budgets PASS
(`frontend-isolated-final.log`). Existing dependencies reused. No full-project local
suite, live provider, production DB/migration or real PostgreSQL contention test:
scoped local change with disposable fixtures. Owner's running servers/data untouched.
Changed-source/new-file/secret review, docs links and working/index diff hygiene
reviewed for publication. Normal commit/push HEAD:main, actual range hygiene,
remote SHA and CI receipt recorded in `output/inbox-relink-20261008/publication.json`
and final response; CI pending is not green. No next phase is authorized.
Prior manual-task commit 101f0df CI 37815619846 is now confirmed SUCCESS.

## INBOX-MANUAL-20261008 — operator workflow acceptance

Owner explicitly requests manual Inbox review including inspector context/actions,
correct entity links, client/lead/deal/task/appointment creation and management,
and an efficient operator workflow. Mode manual verification + repair of reproduced
in-scope defects; not a new workflow engine or permission policy. Same registered
primary/root/branch; clean base ccee758e4f015a97b3cce43e38ac4db823d7d3a2.
Reuse current Inbox/API/domain services and existing acceptance evidence. Verify
live local owner session Business 2, with a backed-up, separate identifiable QA
conversation batch; preserve user's active demo conversations/drafts. No resets,
working migrations, real external recipients or paid model calls. AI/transport
behavior can use isolated provider fixtures and must be reported as such.
Manual matrix: empty/partial/full inspector, create/link/change client/lead/deal,
appointment prefill/save/navigation, task creation, exact links/Back/draft, queue
filters/unread/assignment/priority/bulk, close/reopen, bot readiness, templates,
delivery failure/retry and CRM preview/confirmation. Existing lifecycle/tenant/role
contracts are acceptance; UI alone cannot prove backend security or concurrency.
Risk/check plan: confirm local source roots/DB/business, backup before QA writes,
trace each mutation through normal services. For backend fixes run focused isolated
regressions before dependent work, then affected/system/drift; frontend fixes need
targeted interactions/responsive/manual evidence and one final build. No full-project
suite absent demonstrated impact. Record exact PASS/FAIL/blocked boundaries; persist
results and publish any verified code/docs under standing authorization.

08.10 manual result (publication pending): real local Chrome owner session,
canonical backend :8000 and frontend :5173; dedicated conversations 5/6 in Business 2.
Backup `output/inbox-manual-20261008/before.sqlite3` passed integrity_check;
bootstrap/manifest in the same ignored evidence directory. Existing conversations
1–4 and the owner's active browser tab were not edited by the test sequence.
Created through UI: client152, lead89, deal71, task62, appointment86. Both QA
conversations link to the same QA client/lead/deal. Appointment confirmed, lead/task
taken into work; source website preserved while saving synthetic email/notes.
No external delivery, paid model call, reset or working-DB migration was performed.

Manual PASS: empty → client → lead/deal → appointment/task; existing relation
pickers; exact entity routes and reverse links; appointment confirmation and task/
lead lifecycle action; client edit reflected in inspector; draft across navigation,
reload, filtering and close/reopen; assignment/priority; bot resume correctly
rejected without channel; empty quick-reply state; filtered empty/reset; selected
two-QA-only bulk mark-read. AI draft/delivery retry/CRM preview confirmation and
permission/error recovery are separately verified with isolated provider fixtures,
not asserted as real-channel manual delivery.

Reproduced/repaired frontend defects: direct entry did not mark the opened thread
read (now once per visible selection, preserving explicit unread through polling);
booking shortcut disappeared when appointments existed; task/lead prefill used
the last system/outbound event instead of latest loaded inbound customer text;
all historical messages were labelled today (now date groups and times use business
timezone); task metrics/CRM quick actions/won status/priority summary leaked raw
translation keys or IDs; shared ClientForm source selector displayed manual for
website clients (controlled by existing form state); no-match filter looked like
an entirely empty Inbox. No new API, lifecycle, permission or model contract.

Open policy found by code review: link-client changes only conversation.client;
existing lead/deal links may belong to another client in the same Business.
Owner asked for explanation and recommendation, not yet selected a rule. Current
recommendation: explicit confirmation to detach incompatible links while preserving
the original entities/history, then link the new client's work. This is a proposal,
not approved behavior; no backend relinking changes made. Other limits observed:
resume denial gives generic validation copy; system activity text still comes from
existing English backend events; no dedicated history search/outgoing attachment
composer. These are not represented as fixed or as live-provider readiness.

Verification receipts under `output/inbox-manual-20261008/` using isolated_runtime,
existing dependencies, disposable DB/ports and mocked external providers:
- `verify_ui.py desktop-chromium inbox-inspector.spec.ts` — 11 PASS,
  `browser-1791478911166096000.log`, including AI/delivery/approval/error/permission
  cases, real CRM routes, booking with existing visits, source edit, dates and tasks.
- `verify_ui.py mobile-chromium inbox-inspector.spec.ts --grep 'real client|message date|direct entry|reopened conversation|context errors'`
  — first three PASS in `browser-1791479073627894200.log`; task check failed because
  its locator selected the hidden list preview rather than thread event. Corrected
  selector; `--grep 'reopened conversation|context errors'` — 2 PASS,
  `browser-1791479255733373000.log`. Mobile RU screenshot visually inspected.
- Initial desktop focused run: 2 PASS, task check selected datetime instead of
  description. Label selector corrected; focused task rerun PASS
  `browser-1791478530961526400.log`, then full 11-case scoped run above passed.
- Final direct-entry regression rerun PASS `browser-1791479413216119100.log`.
- Build first caught optional unread_count TS error; null-safe guard added.
  `verify_frontend.py` (npm build: i18n/types/app/widget + check:bundle) then PASS;
  final repeat after one read-selection deduplication line PASS, exit 0,
  `frontend-isolated-final.log`; no new dependency installation.
Backend/system/migration/full-project/live-provider gates not run: frontend-only
change, no migration/infra/AI policy change; scoped checks do not certify them.
Next: diff/docs/secret review, normal commit/push/main readback
and actual CI. Keep relinking decision open unless owner explicitly selects it.

## INBOX-DENSITY-20261008 — active Inbox layout and operator review

Owner requests equal container gutters and analysis/improvement of bulky rows,
crowded thread controls/composer and undifferentiated inspector information.
Mode frontend implementation + bounded UX review, same canonical owner/root/branch;
clean base b3959e99e9cc75223bbf14362fafb61490740c9c. Read current frontend and
verification contracts; reuse shared layout/buttons/menu and existing actions/i18n.
Live Chrome 1536x639 CSS viewport: container x88/y64/w1424/h535.2, app header
height56.8/sidebar64: top7.2, sides24, bottom39.8. Root causes: max-width/negative
margins, unrelated fixed104px height offset, ungrouped controls. Change only Inbox
route layout, list density, thread action grouping, composer and inspector sections.
Keep permissions/API/drafts/confirmations/retry identities and all existing actions.
No backend/AI policy changes, new messages/provider calls or working-data mutations.
Risk: shared AppLayout route branch, relocated memory action and responsive overflow.
Checks: affected existing isolated inspector desktop/mobile critical flows, memory
confirmation cancel/permission visibility, keyboard/long RU/KK/EN and live geometry;
empty Inbox and one non-Inbox layout representative. One final isolated build/types/
i18n/bundle and diff/docs review. No full-project or backend gate for unchanged APIs.
Review findings must distinguish reproduced UI issues from unproven product gaps.

Implemented: route-scoped 16px gutters with dvh and mobile nav/safe-area clearance;
removed negative margins and fixed104px offset. Rows now 68.8px in owner's browser
(about88px in supplied original screenshot); smaller avatar, quiet status metadata,
unread badge separated from avatar. Priority links remain reachable as compact rows.
Thread identity/context and working actions are grouped separately; memory reset and
AI usage moved into the existing menu. Confirmation, role checks, pending/error/success
feedback retained; exhaustion/handoff warnings remain inline. Composer tools grouped,
RU/KK/EN quick-reply label clarified, editor gets an accessible name. Message retry
remains at the same message with compact status/attempt/action placement. Inspector
uses separate flat sections/icons/dividers and clear link arrows. Removed floating
today marker overlap, but did not change its pre-existing date semantics.
Row keyboard activation prevents Space scrolling and nested bulk-selection events
from also opening the conversation. No shared ActionMenu behavior changed.

Verification on canonical dirty snapshot, helpers under ignored
`output/inbox-density-20261008/`, isolated DB/ports and existing dependencies:

- `.venv/Scripts/python.exe output/inbox-density-20261008/verify_ui.py desktop-chromium inbox-inspector.spec.ts --grep 'real client|AI inserts|CRM menu'`
  — 3 PASS, `browser-1791476572189000600.log`: actual four-entity links/Back/draft,
  RU/KK/EN, editable AI insertion without send, retry identity, granular CRM approval.
- Same helper `mobile-chromium inbox-inspector.spec.ts --grep 'thread menu|real client|AI inserts|CRM menu|switching conversations'`
  — 5 PASS, `browser-1791476734384221300.log`: mobile equivalents plus switching/
  late-send drafts and new memory-menu regression (cancel sends no request, confirm
  sends once, persisted message history and unsent draft retained).
- Same helper `desktop-chromium ui-operations.spec.ts --grep 'Inbox channel|deals show'`
  — 3 PASS, `browser-1791476882861581600.log`: empty Inbox/filter/CTA/restricted user
  and non-Inbox Deal layout representative for shared AppLayout's route branch.
- Same helper `desktop-chromium inbox-inspector.spec.ts --grep 'thread menu|context handles'`
  — 1 PASS, `browser-1791477001940939000.log`. Only the memory-menu test matched;
  the `context handles` alternative matches no test and is not claimed as coverage.
- `node --test frontend/scripts/tests/inbox-delivery-policy.test.mjs` — 2 PASS.
- `.venv/Scripts/python.exe output/inbox-density-20261008/verify_frontend.py` — one
  final isolated build/types/i18n/app/widget + bundle PASS, `frontend-isolated-final.log`.
  No dependency reinstall, API/schema changes, backend/full E2E or live-provider run.
- Live Chrome, actual current test data: desktop 1536x639 CSS viewport, gutters
  left/right16, top16.2, bottom15.8, no horizontal overflow; row68.8, typical thread
  header109.3. Mobile viewport394x851: left16/right16.4, top16.2, gap to bottom nav16.4;
  editor bottom739.6 before nav top777.6, no overlap/overflow. Temporary viewport
  reset, user's current conversation/filter preserved. Desktop and mobile screenshots
  reviewed, including KK. HMR briefly invalidated I18nProvider during dictionary edit;
  normal reload recovered, isolated fresh loads passed, no app failure persisted.

Bounded review findings, not authorization for another phase:

- Supplied/live Alina reply says no appointment information while inspector displays
  an appointment. `apps/bots/ai.py` intentionally builds customer-safe reply context
  rather than passing the inspector projection. Investigate controlled appointment
  grounding separately with client identity/permissions; do not expose private CRM
  fields to a public agent merely to improve the reply.
- Composer supports text, templates and editable AI draft; MessageBubble displays
  incoming attachments, but there is no outgoing upload control in this flow.
- Conversation filters accept `search`, but this page currently installs only a title
  in setPageHeader; there is no dedicated history-search control. Global CRM search
  is not a search within this thread. Useful follow-up for longer conversations.
- Static date marker still says today regardless of historical messages. Also
  markRead is called by selectConversation; direct URL entry does not use that path.
  Owner's direct-entry conversation remained unread. These are existing correctness
  follow-ups, not fixed by density changes or claimed covered by the above checks.
- Demo delivery failures are expected: the dedicated synthetic bot has no channel;
  no delivery-readiness conclusion can be drawn from these test conversations.

Final reviewed diff, commit/push/readback and actual CI in local publication receipt
and final response. No working-DB edits or paid model/provider calls by this task.

## INBOX-DEMO-20261008 — owner-requested local inspector examples

Mode operation, environment gap: owner explicitly requests test conversations in
the currently signed-in local Inbox. Browser confirms business_owner@example.com;
Business 2 (Zani E2E Demo), user 2, empty Inbox. Canonical backend/frontend roots
verified for ports 8000/5173; local SQLite, branch codex/ui-testing-toolkit,
clean starting HEAD 951c8e806125fe28feb7b174b744d362533a4e2a, same primary writer.
Create one identifiable additive demo batch, with backup and atomic rollback:
linked client/deal/lead/task/appointment, multiple appointments, and unlinked visitor.
Reuse existing CRM API/services; fixture conversations/messages have no external
channel or delivery queue. No resets, migrations, permissions or paid AI calls.
Risk/checks: assert exact local DB/business/owner and no active automation; verify
entity relations and context projection, then visible live-browser inspector.
Completion: persist manifest/evidence, docs diff hygiene and normal publication.
No app build/test suite needed for a data-only operation with unchanged product code.

Completed: additive batch `inbox-demo-20261008`, conversations 1–4, three new
clients, three leads, one deal, one task and appointments 83–85. Dedicated paused
demo bot 13 has no channels; all conversations have bot_enabled=False, synthetic
messages have no queued/retrying outbox. Existing data/settings preserved.
`manage.py shell -c "exec(open('output/inbox-demo-20261008/seed.py', encoding='utf-8').read())"`
PASS: existing authorized APIs/services create CRM links and validate available
appointment slots. Context reads for all four scenarios PASS: full context with
conversation appointment provenance, two client appointments, lead-only client,
and unlinked visitor. Backup SQLite integrity_check PASS before writes; batch
created atomically. Ignored local `output/inbox-demo-20261008/` contains seed script,
`before.sqlite3` backup and `manifest.json`; no DB or messages committed to Git.
Chrome at `http://127.0.0.1:5173/app/conversations/1` verified actual four-item list,
client/note/email, tomorrow's appointment/service/specialist, 15000 KZT deal,
lead and next task with exact links; left open for owner. No server restart needed.
Data-only operation: no product-code changes, migrations, builds or provider tests.
Final docs/index/committed diff and publication recorded in local receipt.

## INBOX-INSPECTOR-20261008 — approved customer context and action placement

Mode implementation, code/UX gap. Owner approved inspector reference and explicitly
requested implementation; scope relayed by PlatformaCRM UI task
`01a0f32f-7d02-7263-a53d-496c8f9787f5`. Same generation 4 primary, canonical root
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`; clean base
`d76b5101d2c183fcbb2b863332611d9c740c6a83`. No parallel writer or source copy.
Approved change from prior Inbox rollback: selected conversation's compact
customer inspector only, with scoped client/contact/note, honestly attributed
upcoming appointment(s), deal/lead links and compact link/book actions. Preserve
empty three-column Inbox, sidebar, conversation list/filter and thread design.
Move existing delivery retry to message, AI draft/quick replies to composer,
priority/unread/task/CRM preview actions to menus/dialogs; retain all existing
domain services, granular approvals, safety, permissions and draft behavior.
Reuse API layer, shared overlays/buttons/menus, semantic tokens and RU/KK/EN.
Mobile opens the same customer context from thread header with focus restoration.

Risk/check plan: linked entity permission is independent of conversation access;
if a backend projection is needed, prove same Business, resource/object scope,
masked/hidden children, appointment time/status/multiple results in isolated
focused tests before UI consumption. Validate deep links, booking prefill,
draft preservation, denied/error/loading recovery, AI insertion without send,
message retry identity, CRM confirmation and selected/unlinked/partial context
on desktop/mobile/keyboard/locales. Finish affected/dependent backend suites and
system/drift checks if backend changes; targeted frontend tests/browser flows and
one isolated build/types/i18n/bundle. No full E2E absent demonstrated broad risk.
No working DB reset/seed/migrations, external sends/sync, paid AI, new models or
permissions framework. No development of CRM AI. Update evidence/current docs,
review owned diff, conventional commit, normal push origin HEAD:main and actual
remote SHA/CI.

Implementation: scoped read-only context and link search implemented;
conversation list masks inaccessible related IDs/names through batched child
authorization. No schema/write-service changes. The 320px inspector and mobile
drawer reuse existing tokens/overlays; exact entity routes, future appointments,
client booking prefill, menus, composer AI insertion and per-message retry wired.
Draft storage is scoped by user/business/conversation and persists before navigation;
the prior business/conversation session key is consumed once for upgrade continuity.
Late send/AI responses cannot overwrite another conversation's draft. Delivery retry
retains its request key after an uncertain failure and targets the same message.
The shared ActionMenu has an opt-in drawer/modal layer; default callers retain their
layer. Mobile inspection reproduced a menu below the drawer; this was fixed and
pointer/keyboard/Escape/focus retested. The obsolete inert attachment button was
removed while moving quick replies into the composer toolbar; no upload flow changed.

Verification (canonical dirty snapshot on the base above; isolated_runtime, fresh
temporary DB/ports/uploads, no dependency installation):

- `.venv/Scripts/python.exe output/inbox-inspector-20261008/verify_backend.py apps.conversations`
  — 42 PASS, including 15 context/picker/batching tests; system/drift PASS.
  Log `backend-1791452097344056200.log`.
- Same helper with `apps.bots.tests.InboxBackendTests apps.bots.tests_customer_safety apps.bots.tests_safety_state apps.bots.tests_safety_recovery apps.core.tests_b5_performance.BackendPerformanceRegressionTests.test_inbox_list_query_count_does_not_scale_with_conversations_or_messages apps.core.tests_workspace_related_filters.WorkspaceRelatedFilterContractTests.test_workspace_inbox_filters_are_relation_and_tenant_scoped`
  — 67 PASS, system/drift PASS; log `backend-1791452432247817500.log`.
  Together 109 distinct backend tests, with resource denial, OWN/tenant boundaries,
  capability/field masking, time/status/provenance/multiple appointments, task scope,
  bounded list queries, existing writes, delivery and AI confirmation/safety.
- `verify_ui.py desktop-chromium inbox-inspector.spec.ts` first three scenarios:
  3 PASS (`browser-1791451971663822800.log`); mobile same first three: 3 PASS
  (`browser-1791452180227713300.log`, later booking selector failed separately).
  Existing entity pages were opened and browser Back retained the draft; RU/KK/EN,
  desktop/mobile screenshots, no overflow, panel error recovery/denial, AI insertion
  without send and retry identity checked. Synthetic AI/delivery/error boundaries
  were mocked; entity links/context/appointment data used actual isolated APIs.
- `verify_ui.py mobile-chromium inbox-inspector.spec.ts --grep 'booking shortcut|CRM menu|switching conversations'`:
  booking/menu 1 PASS after the layer fix (`browser-1791452823177317600.log`);
  CRM teardown route-fetch race then corrected by awaiting in-flight routes.
  `--grep 'CRM menu|switching conversations'` mobile 2 PASS
  (`browser-1791452948177369900.log`); the three-scenario desktop run 3 PASS
  (`browser-1791452958951576100.log`). Proves booking client prefill, failed picker
  recovery, exact granular confirmation, legacy draft upgrade, switching and late send.
- `verify_ui.py mobile-chromium inbox-inspector.spec.ts --grep 'unlinked inspector'`
  — 1 PASS (`browser-1791453575400692600.log`): single client CTA/create option,
  missing links and real scoped existing-client link. Initial unlinked projection
  is a controlled fixture; the resulting link/context are actual isolated APIs.
- `verify_ui.py desktop-chromium ui-operations.spec.ts --grep 'Inbox channel'`
  — 2 PASS (`browser-1791453162634715700.log`), preserving empty layout/filter/CTA
  behavior and restricted access. Overall 15 distinct browser project/scenarios.
- `node --test scripts/tests/inbox-delivery-policy.test.mjs` from frontend — 2 PASS.
- `.venv/Scripts/python.exe output/inbox-inspector-20261008/verify_frontend.py`
  — one final isolated `npm run build` (i18n/types/app/widget) and `npm run check:bundle`
  PASS, `frontend-isolated-final.log`; no JS chunk >500kB, shell <400kB.

All helper/log paths above are under ignored `output/inbox-inspector-20261008/`.
Earlier failed fixture setup (unique email/Django client shadowing), picker `q`
colliding with parent conversation search (changed to `term`), cold/warm capability
cache measurement, dropdown selector names and initial reload selector race remain
in evidence. Final applicable reruns passed; no failed gate is being counted green.
No migrations/schema changes, working-DB seed/reset, external messages, paid AI or
new permission/notification/BusinessEvent/write policy. Full project E2E/live provider
certification skipped: bounded inspector/action placement scope. No new phase.
Final diff/docs checks and publication SHA/remote readback/actual CI are recorded in
the final response and local publication receipt; this is not deployed acceptance.

## INTEGRATIONS-REVIEW-20261008 — functional audit and redesign reference

Owner request: full functional analysis of /integrations, redesign proposal based
on the existing application design system, and a generated reference. Mode audit/
design proposal, not implementation or activation of external integrations.
Same registered primary/canonical root/branch; clean base
`4ed44964f373a43ce195898c02d5f912edccf6ac`. Inspect the canonical /app/integrations
route, reachable five-provider catalog, setup/import flows, API/services/permissions,
states and tests. Distinguish static implementation, isolated reproduced behavior,
historical evidence and live provider readiness. Use neutral/emerald tokens,
Manrope typography and current flat sidebar. Reference uses explicitly labelled
example states; no invented production metrics or implied provider availability.
Checks: targeted isolated browser walkthrough/screenshots and representative
error/permission states with mocked external boundaries; source evidence and
proposal/reference visual+interaction QA; docs/diff hygiene. No code fixes,
new providers, live sends/sync, working-DB writes/migrations, app dependency installs
or broad certification/build for a proposal. Record findings and a bounded
implementation recommendation; do not start implementation automatically.

Result: [full report](../integrations-functional-review-20261008.md) records the
five-provider inventory, reproducible generic-config 400/hidden modal error,
needs_attention filter omission, partial-failure misleading metrics, ignored
deep-link and static business-scope/request-state/monitoring risks. No product
fixes or new provider scope. First isolated audit: 2 PASS; operator locator
failed (wrong test-id, correct product denial). Corrected audit locator then
owner/operator desktop/mobile 4 PASS. Commands/logs/boundaries in report.
Interactive reference uses existing semantic colors, type, flat rail, service
rows and contextual setup/import panel. Reference QA desktop/390/320px,
validation, mock import, search/reset and Escape PASS after replacing QA
textbox locator with native searchbox. No application rebuild/backend full
suite: application inputs unchanged; scoped audit only. No working DB or
external sends. Docs validator PASS: 56 active documents, 370 local links,
14 anchors, 38 plain paths, 198 archived bodies intact; working diff hygiene
PASS. Publication SHA/actual CI are recorded in final response/local receipt.

## SIDEBAR-FLAT-NAV-20261008 — owner-requested navigation simplification

Mode targeted UI implementation. Owner requests removing Channels/Control
group containers and showing their contents as independent sidebar entries.
Reuse existing Integration, Analytics and Timeline links, icons, active states,
permission filters and mobile drawer. Same primary/root/branch; clean base
`73582953ec50f20112b4caf5dbbe62095edf4948`. Scope Sidebar navigation configuration
and evidence; no routes, permissions, backend, notifications, BusinessEvent, AI,
migrations or environment changes. Risk navigation visibility/reachability.
Checks: affected desktop collapsed/expanded + mobile drawer, keyboard navigation,
representative allowed/restricted roles; one isolated frontend build/types/i18n/
bundle and diff/docs consistency. No full E2E/backend suite. Normal commit/push
and remote SHA/actual CI readback after scoped PASS.

Implementation: only the two sidebar configuration arrays were flattened. The
three original links/icons/permission resources and their order are preserved;
top-level active states, keyboard navigation and mobile close-on-navigation are
reused. Visible RU names remain «Подключения», «Аналитика», «История».
Checks: `node --test scripts/tests/sidebar-navigation-policy.test.mjs` in
frontend — 7 PASS. `.venv/Scripts/python.exe output/sidebar-flat-nav-20261008/verify_frontend.py`
— isolated build/types/i18n/widget/bundle PASS.
`.venv/Scripts/python.exe output/ui-operations-20261008/verify_ui.py desktop-chromium ui-operations.spec.ts --grep "sidebar standalone" --project=mobile-chromium`
— 4 PASS (owner/operator desktop/mobile), log `browser-1791443167223872900.log`.
Owner's three direct keyboard routes and mobile drawer closing verified;
operator cannot see the restricted links. Desktop collapsed/expanded and mobile
screenshots inspected. Original expanded screenshot caught a width transition;
capture now disables animations. Focused desktop owner recheck (`--grep
"sidebar standalone navigation respects owner"` without mobile project) 1 PASS,
`browser-1791443292272058700.log`; completed expansion visually checked.
Docs validator — 55 documents/363 links/14 anchors/38 paths, 198 archived
sources intact PASS. No backend/full E2E: navigation configuration only.
No dependency install, working-DB changes or external provider calls.
Task complete locally; reviewed working/index/committed diff, normal push and
remote SHA readback recorded with actual CI in final response/local receipt.

## INBOX-EMPTY-FILTERS-20261008 — targeted owner refinements

Follow-up during publication: owner requests channel-neutral empty-state copy:
«Новые обращения с подключённых каналов появятся здесь автоматически»; keep the
title. Base `aa323fae7231313efd3a05bda149467b02936553` already normal-pushed and
remote read back. Scope only RU/KK/EN emptyText translations and this evidence;
reuse passed interaction/permission checks. Risk copy/layout only. Check affected
desktop/mobile empty view, i18n/build and diff hygiene; no backend/full E2E.
Follow-up result: RU/KK/EN copy changed, title unchanged. Same isolated build
command rerun after translations: PASS. Browser command above with grep
`"Inbox channel shortcut and"` and both `--project=desktop-chromium` /
`--project=mobile-chromium`: 2 PASS; log `browser-1791440356262436900.log` in
UI-OPERATIONS output. New desktop/mobile empty screenshots inspected; text fits.
Original UI commit CI `37736805660` was in progress at readback. Follow-up
commit/normal push/remote SHA and current CI recorded in final response/receipt.

Owner requests after rollback: remove the list empty-state card border, align
three empty panels, move connect-channel CTA into the empty thread and open the
customer agent Channels section, widen the two quick-filter menus and hide their
scrollbar while retaining scrolling/keyboard access. Mode implementation; UI/code
gap. Same primary, canonical root and branch; clean base `3c2182ea7bd569c1f6afc7b53d50e9384b0fb1ed`.
Reuse Inbox panes, existing channel route, i18n, Select and no-scrollbar utility.
No redesign of populated Inbox, backend/AI/permissions/notifications/BusinessEvent,
migrations, environment changes or external calls. Risk: menu clipping, keyboard
access, mobile CTA reachability and wrong agent/permission routing.
Checks: affected empty/filtered/populated Inbox, direct channel navigation,
restricted-role absence, desktop/mobile + RU/KK/EN visual and keyboard inspection;
representative default Select consumer, one isolated build/types/i18n/bundle,
docs/link consistency and working/index/committed diff hygiene. No broad E2E or
backend suite for unchanged services. Explicit reviewed commit/normal-push and
remote SHA/actual CI readback complete this bounded task.

Result: implementation/local acceptance PASS. List empty headline, thread CTA
and CRM empty message share the pane centre; list card framing removed. Three
columns fit 1280px without clipping the inspector. Existing filled panels remain.
Channels shortcut targets the first customer (non-CRM) agent of the active
business; no-agent fallback is the existing agent workspace. Only authorized
roles see it; mobile empty list retains the reachable action. Expanded Select is
opt-in for two quick filters, with full option labels, hidden scrollbar and
keyboard active-option scrolling; default advanced-filter Select also checked.

Checks (isolated disposable fixtures, no paid/external calls):
- `.venv/Scripts/python.exe output/ui-operations-20261008/verify_ui.py desktop-chromium ui-operations.spec.ts --grep "Inbox channel"`
  — 1 PASS, `browser-1791439955650005400.log`.
- Same command with `mobile-chromium` — 2 PASS (flow + restricted operator),
  `browser-1791440036828560700.log`. Direct Channels navigation by keyboard,
  queue/owner selection, Escape/focus, default advanced Select, empty/filtered/
  populated Inbox and unsent draft verified. RU/KK/EN desktop/mobile screenshots
  inspected in the corresponding `output/ui-operations-20261008/browser-*` folders.
- `.venv/Scripts/python.exe output/inbox-empty-filters-20261008/verify_frontend.py`
  — build/types/i18n/app/widget/bundle PASS; `frontend-isolated-final.log` alongside.
- `.venv/Scripts/python.exe output/docs-reset-20261007/verify.py` — 55 active
  documents, 362 links, 14 anchors, 38 paths PASS; 198 archive sources intact.
No failed checks. Backend/full E2E skipped: no backend or cross-cutting behavior
change. No dependencies installed, working DB migrations or deployment performed.
Working/index/actual committed range reviewed before normal publication; final
SHA, remote readback and actual CI status are in the task response/local receipt.

## INBOX-UI-ROLLBACK-20261008 — owner-requested rollback

Owner request: restore the Inbox UI preceding `8bb54dd`; the previous version
was preferred. Approved requirement change reopens only the Inbox UI portion of
UI-OPERATIONS, not the other five screens. Base `8bb54ddc5c08d562ca985bbccbdfccd3de7de3bf`,
clean canonical checkout, same primary/branch. Restore the three conversation UI
files and their Inbox-only copy to `79ffca5`; keep AI/backend/domain behavior.
Risk: accidentally reverting other screens or safety/recovery. Checks: exact
source comparison, targeted empty/populated Inbox and existing manual AI-recovery
browser flows desktop/mobile in isolation, one frontend build/types/i18n/bundle,
documentation consistency and working/index/committed diff. No backend changes,
new paid calls, working-DB changes, dependency installs or broad E2E. Commit and
normal-push after checks under standing authorization.

Result: exact source comparison against `79ffca5` PASS for all three UI files
and every Inbox translation in RU/KK/EN. Restored original panels/filter row/copy;
AI settings, provider behavior and other five screens are untouched.
Isolated build/i18n/types/app/widget/bundle PASS via
`.venv/Scripts/python.exe output/inbox-ui-rollback-20261008/verify_frontend.py`;
log `output/inbox-ui-rollback-20261008/frontend-isolated-final.log`.
Browser command prefix `.venv/Scripts/python.exe output/ui-operations-20261008/verify_ui.py`:
desktop/mobile `ui-operations.spec.ts e2e/inbox-agent-safety.spec.ts --grep "Inbox restored|Inbox pause"`.
Mobile 2 PASS (`browser-1791439073961115800.log`); desktop AI recovery PASS
(`browser-1791439032766988200.log`), restored-layout test initially expected an
unused subtitle. Corrected to the actual existing heading, then desktop
`ui-operations.spec.ts --grep "Inbox restored"` 1 PASS
(`browser-1791439204900938200.log`). Logs/screenshots in the UI-OPERATIONS output
directory; original failure retained. Empty/filtered/filled views, draft and
manual controls after AI limit verified. No product changes to satisfy the test.
Docs validator: 55 documents, 361 links, 14 anchors, 38 plain paths PASS;
archive preserved. No backend suites/full E2E or paid calls: runtime backend and
AI code unchanged. Reviewed 11 task-owned paths; working/index/actual committed
range checked for publication. Final SHA and actual CI reported in task response.

## UI-OPERATIONS-20261008 — implementation and local acceptance complete

Source: owner-approved UI/UX audit relayed by task
`01a0f32f-7d02-7263-a53d-496c8f9787f5` with explicit instruction to implement the
whole package in this registered primary. This is new scope, not ownership
transfer. Same generation 4 primary, root `C:/Users/user/Desktop/PlatformaCRM`,
branch `codex/ui-testing-toolkit`, clean starting HEAD
`79ffca5c2b4437750bb7559ce34453ab6c247a29`; no pre-existing changes.
Mode targeted defect correction and approved UI implementation; gaps code/data/UX.

Observable result and complete authorized scope:
- Leads: one create CTA, correctly named import in additional actions, consistent
  terminology, one nearby filter entry, no empty pagination/selection; distinguish
  no data/filter-empty/error. Compact creation form without losing fields.
- Deals: risk is attention, not hot sales; next task/action/date and no-step filter
  agree; honest empty columns and readable entity hierarchy, existing kanban retained.
- Calendar: day/week/month arrows and period heading match view, month/year boundaries
  and selected-mode accessibility; compact controls, slot creation preserved.
- Inbox: coherent empty state; readable filters with separate owner/AI-agent labels,
  filter icon/count; populated conversations, CRM context, drafts and AI pilot preserved.
- Settings: group business profile/contacts, appointments, finance and appearance;
  keep fields/permissions/drafts/save behavior; remove redundant framing/headings;
  group expansion matches visible children and accessibility state.
- Dashboard: real scoped today appointments/confirmations, waiting conversations
  and overdue tasks; full distinct counts separate from previews. Ordered/deduplicated
  entity action queue plus upcoming appointments; owner finance uses actual net
  receipts/source/period/freshness, useful grounded AI summary stays compact.
  Correct deep links, unavailable/error states never mean zero or all clear.

Approved layout reference (conditional data only):
`C:/Users/user/.codex/visualizations/2026/09/30/01a0f32f-7d02-7263-a53d-496c8f9787f5/crm-dashboard-proposal.html`.
Use composition, existing neutral/emerald tokens and RU/KK/EN. No demo data or
role-switch UI. Reuse workQueues/analytics selectors, current API clients, controls,
forms, scopes and existing tests. Minimal read-contract extensions if needed;
no new lifecycle/booking/money policy, notification, audit/BusinessEvent types,
CRM AI development, paid AI calls, external messages/integrations or deployment.
No schema/environment change expected; no working-DB seed/migration, dependency
reinstall, alternate source tree or stopping other processes.

Verification plan: before dependent UI, isolated backend regression for each
coherent count/queue change: overlaps, totals beyond preview limit, stable order,
role/tenant/capability scope and invalid input. Calendar unit/interaction checks
include different views and month/year boundaries. Targeted reachable browser
flows desktop/mobile, keyboard, RU/KK/EN, empty/filter-empty/error/recovery and
populated Inbox. Preserve customer AI safety/recovery/permissions through affected
regressions. Final frontend build/types/i18n/bundle, affected/dependent backend
tests + system/migration drift; no blanket full E2E absent demonstrated need.
Record exact commands/snapshots/results and preserved failures. Finish all six
areas, reviewed docs/checkpoint/STATUS, conventional commit and normal HEAD:main
push with remote SHA and actual CI. No intermediate approval gates or new phases.

Implementation checkpoint: all six areas are implemented in the same dirty
snapshot above. Work queues now expose full distinct operational counts, business
day/timezone, availability/scope and ordered entity previews; disabled/denied
modules cannot reappear through unassigned rows. Backend regression was red
before the fix; the focused gate passed before dependent UI. Query-budget failure
(63 versus 58) was corrected by reusing already loaded category previews.
Final affected/dependent backend gate: 78 tests PASS, system check PASS, no migration
drift; `output/ui-operations-20261008/backend-1791411501420078900.log`.
Calendar/dashboard/policy unit checks: 9 PASS. Six desktop flows passed across
targeted runs; all six mobile flows PASS in `browser-1791411479584303500.log`.
Screenshots inspected for compact form, calendar, settings, Inbox and dashboard.
Earlier selector mismatches and build errors are retained in the same output
directory; they were corrected rather than waived. Additional role/recovery and
navigation-accessibility checks passed: 7 desktop, 4 mobile and 2 tablet scenarios.
Isolated build/types/i18n/widget/bundle PASS; the post-success helper stdout
encoding issue is documented, not a product failure.
[Final evidence and exact checks](../ui-operations-20261008.md) preserve earlier
failures and exclusions. Updated frontend/CRM contracts and capability map.
Documentation registry/link/archive checks PASS: 55 active documents, 359 local
links, 14 anchors, 38 plain paths; preserved archive unchanged. Working diff
hygiene PASS; entire intended source/tests/docs and new files reviewed. Final
publication SHA, committed-range/index checks and actual CI are recorded in the
task response and `output/ui-operations-20261008/publication.json`; no new phase.

## PREPROD-AI-EVIDENCE-20261008 — documentation update

Owner request: update pre-prod with completed customer-agent behavior checks.
Docs-only evidence gap; same generation 4 primary/root/branch, clean base
`de1867bd7ed3a2350fdfdb7dfc35c8ca8c365e69`. Reuse the two acceptance reports,
final case/semantic review and verified publication receipt. No product behavior,
permissions, notifications, BusinessEvent, schema, environment or paid AI changes.
Risk: overstating coverage, conflating real model with real delivery, summing
overlapping tests or leaving stale version/CI status. Update existing passport
and pre-prod navigation/status; preserve historical evidence and external gaps.
Checks: counts/source/CI consistency, local links/anchors, registry and reviewed
working/index/committed diff hygiene. No app tests/build/install/model calls for
Markdown. Completion: reviewed docs commit, normal push and actual CI status.

Result: current passport contains the six-group behavioral matrix, observed
outcomes, fixes, handoff/recovery semantics, supporting checks, costs and limits.
Version and successful application CI are current; pre-prod navigation updated.
Five registered Markdown files, 65 local links/anchors and final 43-case/CI receipt
consistency PASS; diff hygiene PASS. Initial verification helper expected six
files instead of the actual five; corrected to an explicit scope list, then PASS.
No application checks or paid calls rerun. Documentation publication and its
push-triggered CI status are reported in the final response; prior application
CI SUCCESS is evidence for de1867b, not for a future documentation commit.

## INBOX-LOCAL-PILOT-20261008 — complete

Publication readback: `de1867bd7ed3a2350fdfdb7dfc35c8ca8c365e69` normal-pushed
to main; [CI37684198877](https://github.com/999MAX20/PlatformaCRM/actions/runs/37684198877)
backend/frontend SUCCESS. Local receipt `output/inbox-local-pilot-20261008/publication.json`.
The pre-publication steps below were completed; no product work remains in this scope.

Owner authorized completing the existing customer-agent pilot locally: safe
customer scenarios, handoff communication and fast flexible staff configuration.
No new capabilities, CRM-agent development, messenger integrations, production
hosting/database/workers or real customer delivery. Explicit separate USD1 budget.
Same generation 4 registered primary, root `C:/Users/user/Desktop/PlatformaCRM`,
branch `codex/ui-testing-toolkit`, clean base `0112475850c631cd946424c86f49e363c6b80881`.
All changed/untracked source/docs belong to this task; no original WIP or owner drift.
Prior base CI37676924581 SUCCESS. No ownership or runtime-env changes.

Mode audit/targeted implementation/verification; gaps code, UX and local evidence.
Reused safety/pipeline/outbox/recovery, profiles/settings/readiness, API clients,
design system/i18n and existing targeted suites. Risks: duplicate/stale sends,
private-data leakage, automatic writes without permission, lost settings/drafts.
Plan executed: focused isolated backend regressions after coherent fixes, affected/
dependent suites + system/drift, targeted isolated UI/API desktop/mobile/locales/
keyboard, final build/bundle. No full-project local gate, working DB or new install.

Implemented deterministic handoff acknowledgement with outbox idempotency and
revocation guards; empty-reply and mid-turn call-limit handoff fixes. One booking
control saves both permissions/settings; safe mode guards; advanced disclosures;
actual dental template respects saved permissions. No schema, new role or new
BusinessEvent; existing activity/audit/notifications retained. Details and exact
commands/skips/errors: [report](../inbox-local-pilot-20261008.md).

Verification: 241 scoped backend PASS before final call-limit fix; 72 affected
tests PASS after fix, system/drift PASS. 16 selected browser scenarios PASS and
one localized mobile recheck after i18n ordering fix. Build/types/i18n/widget and
bundle PASS; representative screenshots reviewed. Live final 43/43 PASS plus
semantic output/record review; run customer_pilot-1791405340114934200. Cumulative
145 reservations, 143 received calls, USD0.1416664 including failure reserves
of USD1. Final Python/i18n manifest matches. No more paid calls needed.

Evidence `output/inbox-local-pilot-20261008/`: append-only live cases/transport/
manifests + cumulative ledger, semantic-review.json, backend/browser/build logs.
All failed attempts retained: initial missing notice/takeover RED, first live
38/39 with call-limit defect, fixture-quota browser failures, bad selectors/grep,
two nonexistent backend labels and i18n build error. Corrected runs cited in report.

Completed DoD: final source/docs/index/secret review and diff hygiene,
conventional commit, fetch/prove fast-forward normal push HEAD:main, remote SHA
readback and actual CI. Do not call CI green before readback. Publication receipt
goes in local publication.json and final response; candidate is report's commit.
Next product boundary is real channel/target environment/staff acceptance, excluded
here and not automatically authorized. No own server/job is intentionally retained.

## INBOX-LIVE-ACCEPTANCE-20261008 — behavioral PASS; publication below

Owner authorized real-model acceptance of ordinary inquiries, booking, protection
and recovery, including fixes for reproduced in-scope defects. Explicit new budget:
USD 1 maximum, stop before exceeding it; prior task budgets are not reused.
Mode verification/targeted fixes; gap evidence. Same generation 4 primary/root/
branch; clean base `00fe0e7c8743a4b84d136db9492e9228e88beecd`.

Reuse `scripts/ai_behavior`, isolated_runtime, current Inbox pipeline, domain
services and existing safety/booking/recovery tests. Synthetic disposable DB,
real configured AI provider only; controlled outbound receipts, never real
customers or messenger delivery. No working DB, migration, deployment, billing,
CRM-agent/analytics development or new integration rollout.

Changed behavior initially none; if a defect reproduces, minimal correction and
focused regression before dependent work. Risks: budget overflow, false booking,
privacy leak, false handoff, duplicate work and stale replies after recovery.
Acceptance checks facts vs fixture, actual records/relationships and timestamps,
no writes without valid consent, denial/tenant boundaries, sensitive context,
limits and replay, provider failure/manual takeover/resume. Review model output
semantically; HTTP success alone is not PASS. Test controls cannot masquerade as
live channel, infrastructure or clinic acceptance.

Focused checks: existing customer safety/state/recovery, automatic booking,
runtime configuration, Inbox continuity and AI job recovery in isolated runtime;
test budget harness before live use. Add explicit USD1 CLI budget and a targeted
Inbox suite if needed, retaining cumulative attempts/reservations across retries.
Completion: affected/dependent backend suites plus system/migration checks if
runtime changes; reachable API flow, relevant UI/build only if changed. No full
project/E2E gate by default. Docs links/registry/diff checks; reviewed commit,
normal HEAD:main push, remote SHA and actual CI. Keep all failed attempts visible.

Initial plan: prepare selected synthetic scenarios and run deterministic baseline, then
bounded live evaluation. Evidence under `output/inbox-live-acceptance-20261008/`.

First results: 53 focused tests/system/migration drift PASS; 6 budget-harness tests
PASS; 4 no-provider safety/API dry cases PASS. First live 27 cases: 25 machine
PASS, 2 harness failures (ambiguous request expectation contradicted permitted
uncertain handoff; held-worker simulation accidentally used eager result backend).
Retain both failures and fix test setup/criteria transparently, not runtime policy.
Semantic review found a real wrong off_topic classification for clinic address,
and busy/denied booking selection led to another model confirmation of an
unavailable/uncommittable time. Appointment writes remained protected.

Bounded fix plan: clarify business-information categories in qualification;
when existing booking service returns requires_staff, call existing handoff
service and, when auto replies enabled, send existing localized handoff copy.
No new booking permission/policy/endpoint/schema/UI. Existing handoff activity,
audit and manager notification apply; pipeline event retains actual decision.
Add failing pipeline regression for busy, staff-only and disabled-tool selection,
verify immediately; strengthen live assertions and retest affected scenarios.
Provider-failure injection reserves cost conservatively; cumulative ledger stays
under the separately approved USD1. No real messenger delivery claimed.

Final behavioral gate: 130 affected/dependent backend PASS, system/migration-drift
PASS (`backend-1791401726512442200.log`); final live run 28/28 machine and semantic
PASS, 57 real calls. Total 55 case attempts retained, 110 received provider calls,
2 injected-failure reservations. Provider-reported USD0.1104668, conservative
charged/reserved USD0.1228916 of USD1. Final source manifest matches current Python
files. No further paid calls needed. Detailed commands, deltas and limitations:
[acceptance report](../inbox-live-acceptance-20261008.md). Next: final docs/source
review and diff gate, commit/push and actual CI. No new phase. Prior docs CI
37667508038 is now confirmed SUCCESS. Working DB/servers/dependencies unchanged.

## DOCS-RESET-20261007 — консолидация документации

Mode docs; gap — устаревшие маршруты/смешение требований и истории. Владелец
разрешил сверку реализации, обновление README и активных источников, архивацию
старых документов. Один writer generation 4 `01a11776-e13a-76c2-9fc0-75d38228f649`.
Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
clean base `f01d22610118e3a24df86257943a8be91314f916`.

### Контракт и план проверок

Результат: компактный реестр current contracts + паспорта + процедуры; агенты
не берут старые технические планы как действующие. Reuse существующих решений,
паспортов, source/tests и evidence; не переписывать продукт. Риск — потеря правил,
открытых обязательств или ложный live PASS. Поэтому оригиналы сохраняются с SHA256,
последние решения сверяются, незакрытое переносится явно.

Нет изменений кода, схемы, runtime, dependencies, ownership, permissions,
notification, BusinessEvent или AI-поведения. Никаких provider calls, миграций,
deployment или новой продуктовой фазы. Формулировки контрактов сохраняют уже
утверждённые границы, не утверждают архивные предложения.

Checks: inventory/classification, source/decision traceability, archive byte
integrity, active links/anchors/plain paths, agent routing/frontmatter/scenarios,
registry invariants, working/index/actual committed-range diff hygiene. Проверка
новых/нетрекнутых файлов обязательна. App tests/build/install/DB/browser — skipped:
документационная задача, программные входы неизменны. CI запускается существующим
push workflow независимо; его результат проверяется отдельно и не выдумывается.

### Сделано

- 198 прежних проектных документов учтены; 137 перенесены из активного дерева,
  20 прежних entrypoint/procedure/passport тел сохранены перед обновлением,
  40 старых архивных тел и один generated inventory сохранены на месте.
- Созданы 9 current контрактов и source-backed карта возможностей. Сохранены
  актуальные паспорта и стабильные пути процедур/реестра владельца.
- Убраны старые competing планы/redirect stubs; обновлены AGENTS, README, маршруты
  skills; архив имеет отдельную инструкцию non-authority и исключение `.rgignore`.
- Открытые FC/BE/UX/FB и бизнес-решения не закрыты переносом. Последние controlled
  AI creation / manual financial source / support-note / deferred billing решения
  отделены от старых предложений. Предыдущая safety live boundary сохранена.

### Проверки и публикация

Состояние: содержательная проверка PASS. `verify.py` в локальном evidence: 198
исходных Git blobs/сохранённых тел, 52 active entries (30 проектных +22 skill),
328 local links, 12 active anchors, 38 plain paths — PASS. Проверены JSON registry
без изменений ownership, skill frontmatter и отсутствие архива в default rg.
Сценарии маршрутизации: новая CRM/AI/UI задача ведёт к current contract;
исторический PASS читается точечно без открытия scope; unresolved acceptance
остаётся открытым; compaction не меняет владельца. Runtime references к
DKB/generated inventory и ZR-001–010 сохранены. Рабочий/index diff hygiene PASS; 198 staged archive blobs совпали с исходными
SHA256, посторонних non-document paths и unstaged diff нет. Зависший пустой
index.lock снят после проверки возраста, отсутствия Git-процессов и exclusive-open;
индекс и HEAD не менялись другим writer. Реальный committed range и remote/CI
проверяются на этапе публикации.
Детальные безопасные результаты: `output/docs-reset-20261007/` (локальные artifacts).
Документальная часть завершена и проверена. Публикация: reviewed explicit paths,
conventional commit, normal HEAD:main push,
remote SHA readback и фактический CI. Итоговый SHA/CI — в ответе задачи и локальной
квитанции; commit не может содержать собственный hash. Следующий продуктовый этап
не назначен. Незакрытые требования — [acceptance](../../current/acceptance.md).

### Сохранённая история

[Исходный checkpoint](../../../archive_docs/2026-10-07/docs/testing/task-state/PRIMARY-SESSION.md)
содержит закрытые scope и evidence до этой консолидации; это не очередь задач.
Передача generation 3 → 4 завершена и опубликована `f01d226`; registry idle,
source archived native readback. Latest safety CI 37653976762 / 37654213713 и
паспортный CI 37657729094 SUCCESS. Latest safety проверен с mocks; предыдущие
21 real-model continuity cases не сертифицируют последующее изменение защиты.
CRM/Analytics development paused; существующий runtime не удалён/не выключен.
HookActivationStatus REQUIRES_REVIEW_AND_TRUST; новой проверки runtime hook нет.
