# QA critical access follow-up — 21.11.2026

User scope: continue remaining QA specification defects by severity; no working DB.
Base 493fd243bfc06a3c68418cf607fcdd42abf32b84, branch codex/ui-testing-toolkit,
canonical C:/Users/user/Desktop/PlatformaCRM. Existing auth/WhatsApp/module docs WIP
is foreign. QA-021 remains closed locally; no rewrite.

Phase: access/data integrity. QA-025/026/027 are evidence-first, not proven causes.
QA-023 code hypothesis: general ActivityEvent analytics permission removes own task
history for operator/specialist before existing entity scope. Reproduce first.
Reuse ActivityEvent endpoint, timeline serializer/redaction, task VIEW selector;
permit only exact task history reads, not general analytics, writes or actors list.
No new role framework, migrations, provider calls, notifications, events or AI changes.
Task event records already exist; never duplicate them to repair visibility.

Acceptance: QA-023 own task create/comment/status events visible, inaccessible task
returns explicit denial/not-found, genuine empty history is empty; no tenant or
metadata leaks. General analytics and mutations retain permissions. Isolated
focused regression, affected activities/projection/task suites, system/drift and
reachable role browser scenario. QA-025 existing session races/recovery/identity
browser tests; keep environment-origin uncertainty separate from local PASS.
QA-026/027 inspect existing acceptance and reproduce before changing selectors.
Skills: zani-change-crm-domain, zani-run-verification, zani-review-access. No UI
composition change planned; preserve existing error/empty/retry presentation.
Build/server: only disposable runtime and isolated output; no shared/live server.

Status: QA-023 and QA-024 locally verified; remaining IDs retain their evidence boundaries below.

QA-024 next slice: existing branch-grant service already enforces team.manage,
current branch scope and explicit future/network grant. UI lacks that capability
information. Add read-only capabilities to existing member-access endpoint and
consume them in TeamBranchAccess. No permission relaxation, write-policy change,
new schema or working DB. Test capabilities against actual write outcomes for
owner, limited admin, network admin, foreign tenant and owner-target protection.
UI reuses form/Button/ErrorState, retains choices on denial, explains disabled
network option, has retry, keyboard labels and RU/KK/EN; 44px controls. Anti Slop
during (standing owner preference), human/copy modules and frontend skill apply.
Completion: branch API/service regressions, focused role desktop/mobile browser,
separate-output build, screenshots, types/i18n, system/drift.

User supplied QA origin: platformacrm.kz. Historical release/time/config unknown.
QA-025 local session-persistence suite: 11 PASS; original deployed incident not
closed by local checks. Working DB remains untouched.

## Results and evidence

QA-023: reproduced count=0 for an existing event of the operator's own task
(before-task-history.log). Exact Task history now delegates to task VIEW before
pagination and keeps existing timeline serializers/redaction. General analytics,
actor lookup, event detail/write and unknown entity routes retain their old access.
TaskInspector already distinguishes empty/error and supports retry; no UI rewrite.
8 focused cases PASS (task-history-focused-final.log). First extended fixture had
only a tasks allow override, so the operator inherited clients.view; corrected the
fixture with an explicit clients.view deny, then verified metadata/text redaction.

QA-024: added read-only capabilities to the existing grant endpoint; UI filters
available choices, disables future/network grants without authority, explains
existing outside-scope grants, retains failed selection and reloads capabilities.
No POST policy relaxation. Focused branch-access 11 PASS (branch-capabilities.log).
Dependent branch suites 42 PASS (branch-dependent.log). Final focused/check/drift
result is recorded below after completion; final tests include oversized target ID
and archived outside-scope grants.

Commands (canonical .venv Python, scripts.codex_verify.isolated_runtime, disposable
SQLite/ports, no ordinary db.sqlite3):

- `manage.py test apps.activities apps.core.tests_crm_projection_access apps.tasks.tests_workspace apps.businesses.tests_access.CanonicalBusinessRoleTests apps.scheduling.tests_specialist_schedule apps.scheduling.tests_record_workspace apps.scheduling.tests_calendar_summary apps.branches.tests_scheduling --noinput -v 1`:
  174 PASS, affected-and-scheduling.log. Includes QA-023 cases and diagnostic
  specialist/list/calendar/branch availability controls; counts overlap focused runs.
- `manage.py test apps.branches.tests_access apps.branches.tests_management apps.branches.tests_compatibility apps.branches.tests_single_location --noinput -v 1`:
  42 PASS, branch-dependent.log. The final small validation/archived-case delta is
  covered again by the final focused gate.
- Browser, existing frontend/playwright.config.ts with testMatch overrides,
  webServer cwd set to canonical frontend, disposable runtime and 120s test timeout:
  session-persistence.spec.ts desktop: 11 PASS, browser.log.
  session-cache-isolation desktop: first five PASS; sixth login hit HTTP429 in a
  rapid shared-fixture sequence (history-browser/browser.log and error-context).
  Re-ran only the cross-tab case in a fresh disposable runtime: desktop/mobile PASS.
  No production throttle was weakened or auth code changed.
- task-history-access.spec.ts + cross-tab session case: 6 PASS (4 history + 2 session),
  history-browser-focused/browser.log. Task create/comment/start/complete/reload,
  retained comment, 503 history retry, operator/specialist, desktop/mobile.
- branch-grant-access.spec.ts: 6 PASS, branch-browser/browser.log. Each RU/KK/EN
  desktop/mobile case exercises owner, limited admin, existing outside-scope target,
  network admin, failed-save retention/retry and persisted grants after reload.
- `node scripts/check-i18n.mjs`, `node node_modules/typescript/bin/tsc -b --pretty false`,
  Vite app/widget builds to output/qa-critical-20261121/app-dist and widget-dist:
  PASS, build.log. Existing node_modules reused. No shared build output changed.

Local browser launch recipes are retained as run_sessions.py, run_history_focused.py
and run_branch_browser.py in output/qa-critical-20261121; each uses isolated_runtime
and invokes the existing Playwright CLI. Tests themselves are tracked in frontend/e2e.
No mock merchant DB or real provider call was used. Network failure responses are
injected only into the targeted browser requests; successful flows use real local API.

UI acceptance: task history screenshots (operator desktop, specialist mobile) inspected;
branch limited-admin RU desktop/KK mobile and outside-scope EN desktop/RU mobile
screenshots inspected. Affected history and grant controls/labels fit, 44px labels
and buttons reused; branch form overflow assertion passed. Keyboard Space toggles
an allowed grant; forbidden options and saves are disabled; input survives failure.
Existing drawer close/focus mechanism unchanged; no new dialog. Shared application
header/notification overlay outside the changed region is not recertified by this fix.

## Remaining boundary

QA-023 and QA-024 local code/acceptance are addressed; publication/check completion
is recorded below. QA-021 remains locally closed and its prior CI44924980685 is now
confirmed success. Other 26 report IDs remain open; no blanket QA release sign-off.
QA-025: local persistence/identity controls pass, but no historical origin trace,
release SHA or MFA incident sequence from platformacrm.kz was supplied. Do not
attribute the original incident to the fixture's HTTP429 or claim it fixed.
QA-026: linked-user and OWN/list/calendar controls pass in synthetic fixtures;
original Resource.linked_user/branch configuration is unverified. No scope widening.
QA-027: branch availability controls pass; original date/configuration, room and
reservation snapshot missing. No scheduling restriction removed to fabricate slots.
Working DB and live server were not queried or changed; no deployment performed.
Shared build/server coordination from the earlier instruction remains outstanding;
this work used only separate outputs and disposable servers, not the shared run.

Contract and frontend behavior docs updated; no setup change or new roadmap stage,
so README/roadmap/passport release claims require no change. Foreign auth/WhatsApp
and module-plan changes preserved. No notifications, BusinessEvent, AI, migration
or provider effects added. The next implementation priority in the source ТЗ is
remaining P2 functional flows; QA-025/026/027 additionally need their original
runtime evidence before closure.

## Final gate and publication

`manage.py test apps.activities.tests_task_history_access apps.branches.tests_access
--noinput -v 1`: 19 PASS on final backend inputs; `manage.py check`: PASS;
`manage.py makemigrations --check --dry-run`: PASS, no changes detected.
All three commands ran in one disposable runtime; final-backend.log retained.
No required local check remains for QA-023/024. Live acceptance/deployment is not
claimed. Code was tested in the identified dirty checkout with foreign WIP preserved.
Only task-owned paths/hunks are eligible for publication; normal push/CI pending.
Whole-tree whitespace debt in foreign google-button-design-20261119.md is excluded;
no foreign file is repaired or staged for this phase.
