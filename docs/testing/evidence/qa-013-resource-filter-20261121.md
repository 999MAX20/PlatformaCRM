# QA-013 and QA-004 local follow-up, 21.11.2026

Scope: continue locally reproducible QA defects by severity; no working DB.
Base edfb5ee0ff5a2219be0b7735be78e96b583a5ab5, branch codex/ui-testing-toolkit,
canonical C:/Users/user/Desktop/PlatformaCRM. Existing auth/WhatsApp/docs WIP is
foreign. QA-021/023/024 prior local closure remains unchanged.

Prior reservation lookup already supports primary OR reserved resources; new
evidence: management sends rooms to Calendar as staff and Calendar filters on the
primary specialist alone. Minimal delta: explicit physical_resource filter in the
existing Records workspace and a room/equipment link to that list. Preserve
reservation services, cancellation history and overlap enforcement.

QA-013 P2: validate the physical ID, match only physical reservations of the same
Business, retain existing appointment authorization and branch-filter semantics, compose with
date/specialist/status, label the resource separately and support independent reset.
QA-004 P3 is in the same advanced filter form: its Reset currently calls global
resetRecordFilters and clears dates. Reset only the panel draft; Cancel discards
the draft and Apply preserves period, search and workflow.

Skills: zani-change-crm-domain, zani-review-access, zani-review-frontend,
zani-run-verification; Anti Slop during with human/copy requirements. Reuse Select,
CalendarPopover and existing labels/tokens. Keep keyboard/focus return, labelled
fields, retained draft on cancel, and RU/KK/EN neutral resource terminology.

Risk: wrong records or tenant exposure through resource IDs; regression in shared
filter state. Required checks: isolated backend reproducer, resource booking and
Records/branch dependent suites, check/migration drift; URL unit tests; actual
room link/filter/reset/cancel/recovery browser flow desktop/mobile with inspected
screenshots; types/i18n and app/widget builds in separate output directories.
No permissions/write policy/schema, events, notifications, AI or provider changes.
Only disposable runtime/ports; no shared build, working DB or deployed server.

Status: QA-013 and QA-004 implemented and locally verified. Other report IDs retain their existing
open status; historical platformacrm.kz deployment is not certified by local tests.

Focused pre-fix reproducer failed: one appointment with room and equipment counted
as two in summary when specialist matched primary resource (before-physical-filter.log).
The physical query key was previously ignored. Count distinct appointment IDs to
keep summary consistent with the list; add validated physical-only reservation filter.
Focused resource-booking + record-workspace suites: 51 PASS (physical-filter-focused.log).
URL state unit tests: 9 PASS. Logs before/focused are under output/qa-critical-20261121;
final artifacts are under output/qa-013-20261121. React best-practices review:
reuse scoped catalog query, derive options without new effects/dependencies, keep
hooks unconditional and event-driven draft apply/reset with existing focus return.

Completion commands/results so far (canonical .venv Python):
- `output/qa-013-20261121/backend.py`: isolated_runtime, `manage.py test
  apps.scheduling.tests_resource_booking apps.scheduling.tests_record_workspace
  apps.scheduling.tests_record_commands apps.branches.tests_access --noinput -v 1`:
  62 PASS, including reschedule projection and prior booking conflicts/rollback.
  `manage.py check` PASS; `manage.py makemigrations --check --dry-run` PASS, no changes.
- `node --test frontend/scripts/tests/record-filters.test.mjs`: 9 PASS.
- `output/qa-013-20261121/build.py`: check-i18n, tsc -b, Vite app and widget builds
  PASS. Outputs app-dist/widget-dist are separate from shared frontend/dist.
- `output/qa-013-20261121/browser.py`: Playwright testMatch
  physical-resource-records.spec.ts, desktop-chromium/mobile-chromium, isolated
  runtime and own ports. First attempt failed in fixture preparation (specialist
  schedule before branch assignment); corrected ordering, without changing product
  scheduling validation. Each locale/project uses its own date to isolate the
  six-record period assertion. Original failure retained in browser/browser.log;
  rerun artifacts under browser-2. Browser acceptance remains pending.

Second browser preparation failure: replacing the specialist's first service
assignment while future visits exist correctly returned conflict. Fixture now
retains both service assignments. No scheduling constraint weakened.
Branch diagnostic originally expected read denial solely from a branch grant.
Current access contract CRM-MB01 (12.10) explicitly shares history within Business
and narrows writes by branch. Corrected the fixture to assert shared read + denied
outside-branch update, then explicit OWN VIEW denial through physical filters.
This is a test-assumption correction, not a new product permission policy.

Revised branch/OWN regression PASS in physical-branch-scope-final.log (one enhanced
case, overlapping the 62-test suite). Same-business shared history stays readable;
outside-branch UPDATE stays denied; explicit OWN VIEW cannot retrieve another
specialist's records by physical_resource with or without branch parameter.
Third browser run: RU desktop complete PASS; KK reached the empty-state check but
the test's broad button-name prefix matched both Filter and Reset in Kazakh.
Scoped that locator to the existing toolbar; no product change. Full final run is
under browser-final. RU/KK desktop filter screenshots and RU six-record period and
empty state inspected: labels/actions visible, focus ring visible, no overflow.
Existing records-empty and records-toolbar reset-label assertions updated for the
new explicit global-reset label. The older toolbar suite also references removed
record links/toolbar reset controls; it is not a claimed passed suite in this phase.
The affected records-empty RU recovery scenario and new real-data flows passed.

## Final local acceptance

`browser.py`: 6 PASS, RU/KK/EN desktop and Pixel 7. `empty_browser.py --grep
'actions and recovery ru'`: 1 PASS, existing desktop empty/create/period/global
reset/recovery flow. Product inputs unchanged since the successful build/backend
gate; later changes corrected and expanded test fixtures/locators and docs only.

QA-013 AC1/2: actual management room link opens three reserved visits across dates;
room/equipment switching, explicit date plus specialist, independent room removal,
reload and Back/Forward all PASS. Unknown ID gives a filtered empty state with
recovery controls. Backend excludes primary staff as a physical match, foreign
Business reservations and records outside OWN VIEW. AC3: cancel/reschedule history,
occupancy release, double-booking denial and conflict rollback PASS. AC4 follows
existing tenant/record policy; shared Business history remains shared by CRM-MB01.

QA-004 AC1/2/3: Reset + Cancel retains URL/draft source; Reset + Apply removes only
panel-owned conditions and restores six synthetic visits on the selected day;
the explicit date remains. Global empty-state reset names and performs return to
today. Reload, Back/Forward and focus return PASS. Search/workflow are not part of
the panel draft and remain untouched by its reset.

Anti Slop scoped delivery gate: functional filter fields only, existing tokens and
controls; RU/KK/EN labels and longer synthetic resource names readable; keyboard
Escape and focus return exercised, visible focus inspected; no page overflow in
the new browser cases. Desktop/mobile filter screenshots in all three locales,
RU six-record period, RU desktop empty and KK mobile empty visually inspected.
KK footer wraps to two rows with both actions visible. Popover overlays the page
and remains within viewport. Loading/error/retry, empty and successful lists
exercised. No new imagery/marketing blocks; unrelated design checks not applicable.

No remaining code/evidence gap for this bounded QA-013/004 phase. No working DB,
shared server/build output or deployed platformacrm.kz was modified. No migrations
or external sends. Full-project certification is not claimed. Twenty-four other
source report IDs remain open; continue with a reproducible P2 (for example
QA-015 visit-plan refresh or QA-017 custom-field keys), retaining original-runtime
gaps for QA-025/026/027. Existing WhatsApp work is not reclassified as delivered.
Publication is pending the task-only commit and remote verification below.

Registry/link checks PASS. CRM API and frontend behavior contracts updated in
their existing sections. No new roadmap phase, setup or release capability claim:
README/roadmap/passports require no unrelated rewrite. Existing foreign WIP remains
outside this change. Previous commit edfb5ee0 CI44928222032 completed successfully.
