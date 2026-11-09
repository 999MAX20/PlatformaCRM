# IMPORT-WORKSPACE-20261104 — implementation evidence

Status: first-phase implementation and targeted local verification complete.
Publication not performed. This evidence does not certify live providers or rollout.

## Scope and implementation

Owner authorized the full first phase in [contract](../../current/import-workspace.md)
on04.11, then explicitly accepted no import-triggered notifications/reminders/
automations; activation of future appointments is a separate reviewed action.
Canonical `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
starting/current HEAD66101d509cb7642b2928275e48c4b64354abf07b plus shared dirty tree.
Other executors' Records/Calendar/UI/remediation work was retained. No worktree,
working-DB migration, shared runtime restart or cross-chat coordination was performed.

Implemented: versioned owner/Business staging, multi-source/sheet parsing and scan,
corrections preserving original cells, additional fields, explicit links/duplicate
choices, mapping profiles and stable source bindings, real-component previews,
transactional background validation/import/recovery, selective future activation.
Native clients/services/specialists/appointments consume fields in cards/tables,
server filters and protected CSV exports; calendar tiles show up to two selected
fields. Existing imports remain available. AI is excluded.

## Verification boundary

Commands/logs: `output/import-workspace-20261104/implementation/`.
Use only isolated_runtime, synthetic data, temporary SQLite/PG17 and dedicated ports.

- `run-backend.py`: 137 discovered tests,135PASS/2SKIP; system check PASS,
  makemigrations --check --dry-run PASS. Skips require PostgreSQL, covered separately.
  Labels: core import workspace drafts/sources/API/engine/operations/activation,
  imported custom fields, scheduling import commands, core custom fields,
  import_export, import_job_boundaries, xlsx_reader, export_access, export_attempts.
- `run-focused.py`: actor disabled after enqueue and denied role/branch2PASS.
- PG before filter fix:27 tests,26PASS/1FAIL. Numeric JSON string cast failed only
  on PostgreSQL; KeyTextTransform fixed it. Custom-field6PASS after fix.
- PG locking pass: engine/concurrent-confirm/import command suites PASS;
  log in postgres-locks-pass.log. Calendar/source/race28PASS in
  postgres-calendar-pass.log. Same-source simultaneous confirmation and duplicate
  worker delivery create one result; preview is transient, rollback/replay tested.
- Later display schema/dependent PG38:37PASS/1fixture ERROR (cleanup line inserted
  into the next test). Cleanup restored; two affected tests then PASS. Failure log
  retained as postgres-display-fixture-failure.log; corrected run postgres-concurrency.log.
- Frontend Node15PASS: import-workspace-errors, legacy import-review/import-history.
  New tests prove localized actionable error categories without raw technical keys.
- Browser first full tracked runner:5PASS/1FAIL; new cached-row test initially did
  not force stale refresh. Source rows now revalidate on mount, conceal data after
  failed reads, and cache keys include user. Targeted cache+explicit-overwrite2PASS.
  Final7PASS (run1793811044160054000,2.0minutes). `scripts/verify_import_workspace.py` is the maintained runner;
  frontend/e2e/import-workspace.spec.cjs and playwright.import-workspace.config.cjs.
- Final build/types/i18n6850/app+widget PASS after staleTime change
  (frontend-final.log, bundle-final.log). Bundle main-shell343.1kB within400kB; RU/KK dictionary advisory >500kB.

Browser coverage: four CSV entities and real links, row correction, new fields,
profile save/apply, before→after explicit update, safe repeated profile, preview
calendar and final calendar custom labels, client filter/export/hide, service field
editing, explicit activation, errors/retry, unsaved navigation, RU/KK mobile keyboard,
read-only denial and stale-row concealment/recovery. It uses local scanner/eager
workers; PostgreSQL tests separately prove locking. Live broker/provider not certified.

Reproduced and fixed during verification: EN/KK dictionary override by RU fallback;
PostgreSQL numeric cast; corrected source row reopening its modal after save.
Harness-only failures (Select/Close/status/gridcell locators, live-edit interruption,
encoding of log output and fixture cleanup) remain in earlier logs; no failed run
is relabelled PASS. No dependencies were reinstalled.

## Boundaries, documentation and publication

core0014–0017 applied only to disposable DBs. Existing active/schedule/overlap/branch
rules also apply to historical records. Multi-branch records without an unambiguous
branch are rejected; the importer does not guess or bypass guards. A changed source
without a stable profile is not guaranteed to be the same source. Completed staging
is retained with history; there is no automatic retention sweep or rollback after
users edit confirmed objects. Direct external sync/AI/live rollout are outside scope.

Updated current import/integration/frontend/operations contracts, clients/scheduling/
settings/integration/capability passports, README and testing command. Roadmap and
open acceptance IDs unchanged: this is the owner's bounded standalone first-phase
request, not closure of another roadmap/release. Product/access/CRM/AI policy remains
unchanged; new paths enforce it. Detailed task delta remains in PRIMARY/checkpoint.

Publication preflight confirmed: existing empty index.lock (04.11 19:04 local),
empty staging,17 outgoing commits belonging to earlier work. Remote main read-back
0b3348e1ab31121a106badbde830b496ec477aac; local66101d50 unchanged. No task
staging/commit/push/deploy/newCI. Own isolated58908/58909 stopped, no listeners.
Do not publish mixed foreign work under standing permission.

## UI delivery gate

Final screenshots ui-calendar, ui-live-calendar, ui-service, ui-mobile-ru/kk inspected. Uses the existing mint/neutral CRM
identity, compact Manrope typography and shared spacing/components; no generated
assets, marketing blocks, invented business metrics or industry defaults were added.


Scoped antislop delivery review (existing shell/other writers are not recertified):

- R-02 PASS: em dash appears only as a missing-value marker in data cells.
- R-03 PASS: RU/KK390px browser checks and screenshots; data grids scroll inside containers.
- R-17 PASS: preview counts derive from server report, no invented metrics.
- R-18 PASS: no testimonials.
- R-23 PASS: approved three references; no new visual assets.
- R-24 PASS: transfer entry/return and result routes use existing application routes.
- R-25 PASS: existing CRM text/button tokens retained; inspected screen text remains readable, no new color pairs.
- R-26 PASS: source review connects controls to handlers; critical commands exercised in seven browser scenarios.
- R-27 PASS: empty/loading/error/retry components; failed refresh concealment tested.
- R-28 PASS: no FAQ.
- R-32 PASS: mobile Tab/Enter/Escape and visible focus checked.
- R-33 PASS: behavior lives in tracked TSX/Python sources, no runtime source-rewriting patch.
- R-34 PASS: no theme toggle added; existing CRM light scheme retained.
- R-35 PASS: final build and seven recorded browser scenarios; source wiring reviewed for secondary controls.
- R-36 PASS: no unsupported customer/security/performance claims.
- R-37 PASS: accepted CRM references, ENERGY1/RHYTHM2/MOTION1 recorded before UI implementation.
- R-38 PASS: runtime content comes from API; synthetic data only in disposable tests.
- R-39 PASS: shared labeled controls/focus/disabled states; no new animation or media; keyboard scenarios pass.
- R-40 PASS: no new media, hero or third-party script; bundle budget measured.
- R-01 PASS: no new gradients/glows.
- R-04 PASS: Plus creates transfer, Upload adds file, up/down controls reorder columns.
- R-06 PASS: shared Manrope for continuity and dense CRM readability.
- R-07 PASS: calendar grid encodes actual dates, no decorative grid.
- R-08 PASS: directional controls encode back/reorder, not decoration.
- R-09 PASS: statuses/counts come from the report; no marketing badges.
- R-10 PASS: no new glass panels.
- R-12 PASS: existing cards separate editor/history; modal elevation indicates blocking review.
- R-13 PASS: no new glow.
- R-14 PASS: no feature-card grid; editor, history and calendar have distinct structures.
- R-19 PASS: no ornamental animations.
- R-22 PASS: no illustrations.
- Dials PASS: ENERGY1/RHYTHM2/MOTION1; restrained mint, data-dependent layouts, no ornamental motion.
- Consistency PASS: screenshots match those dials.
- Focal point PASS: selected source/editor and confirm action organize the working screen.
- Whitespace PASS: separates source configuration, preview and commit actions.
- Accent PASS: mint identifies selected source and primary command.
- Identity PASS: shared compact CRM forms and mint calendar tiles repeat across preview/native view.
- Design Read PASS: existing Records screenshot and approved three references informed implementation.
- C-1 PASS: hierarchy follows source/edit/preview/confirm workflow.
- C-2 PASS: handlers inspected; primary flows exercised.
- C-3 PASS: blocks serve history, source configuration, data, errors or actions.
- C-4 PASS: tested desktop/mobile, RU/KK/EN, denied/loading/error/recovery/keyboard boundary.
- C-5 PASS: no fabricated claims.
- R-05 PASS: operational editor/table/calendar composition, no landing-page template.
- R-11 PASS: existing control/card/modal radii retained.
- R-15 PASS: actions name save/check/confirm/cancel/activate operations.
- R-16 PASS: no marketing buzzwords; AI excluded.
- R-20 PASS: shared CRM identity persists through native forms and calendar preview.
- R-21 PASS: existing light scheme preserved, no forced dark default.
- R-29 PASS: shared neutral/mint palette with semantic error color.
- R-30 PASS: existing product components reused, no third-party product clone.
- R-31 PASS: source tabs select data; dense tables compare rows; modal confirms effects.

No code/local-evidence remainder in the accepted first phase. Publication remains
blocked; real workers/scanner/providers, working migrations and rollout were not
accepted by these local tests. Full-project/release E2E skipped per proportional
verification; local eager/scanner fixtures are not live integration certification.

## IMPORT-DEMO-20261104 — real CSV/XLSX upload demonstration

Owner requested generated test files and local import through CRM UI. No product
source changes. Canonical root/branch/HEAD66101d50 + retained shared dirty tree.
Plan/status/source hashes/logs under output/import-demo-20261104.
Command: `.venv/Scripts/python.exe output/import-demo-20261104/run.py`.
CSV1PASS and XLSX1PASS in independent disposable SQLite databases; each journey
imports one client/service/specialist/appointment through real upload/mapping/preview/
confirm UI. Four CSV and four XLSX files generated with synthetic data. Optional
Loyalty/Rating/Room fields, explicit row correction, profile save, native client
filter/export/column visibility, service field edit, calendar rendering and explicit
future activation checked; no browser pageerrors. This is a small happy-path demo,
not large-volume, all-format/locale or release certification.

Inputs: outputs/import-demo-20261104/import-test-files.zip (8 source files + README).
Screenshots: output/import-demo-20261104/{csv,xlsx}/ui-mapping.png,ui-calendar.png,
ui-clients.png,ui-service.png,ui-live-calendar.png. Both result receipts persist.
Inputs visually reviewed; openpyxl read-only verification confirmed raw phone and
ISO timestamp. Artifact CSV inference initially converted timestamp; fixture builder
corrected before XLSX run to preserve explicit timezone text. No product defect or
failed browser run in this demo. Generated XLSX numeric amount/duration/rating retain
numeric types. Workbook renderer omits phone plus sign, but exported file and actual
CRM retain it; raw export/readback checked.

Reuses isolated_runtime/guarded seed, local fake scanner and eager worker; no real
provider sends, workingDB migration/write or shared runtime restart. Owned servers
automatically stopped. Existing build/PG/security evidence not rerun for this
verification-only request. Current source hashes unchanged over final demo interval.
Documentation-only hygiene applies. No own commit/push/CI/deploy; existing lock and
foreign outgoing publication blocker unchanged. No remaining demonstration work.
