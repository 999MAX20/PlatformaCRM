# QA-006 client custom-field filters, 21.11.2026

Scope: next locally reproducible P2 from the QA specification; working DB untouched.
Base 08b81d5000123671b5a2fbbcc565cbb5f28f2cea, codex/ui-testing-toolkit,
C:/Users/user/Desktop/PlatformaCRM. Foreign auth/WhatsApp/docs WIP preserved.
QA-017 and prior closures remain unchanged. No deployment or shared server/build.

Gap: existing server filter and shared controls exist, but ClientsFilters supplies
no definitions, CrmFilterControls excludes clients, and useCrmFilters strips custom
parameters. Minimal delta: connect existing definitions/controls and URL keys.
Reuse listFiltered, server summary/pagination, validation and shared error recovery.
No new endpoints, permissions, migration, notification, BusinessEvent or AI behavior.

Acceptance: text/number/select/date and empty-value filters use server results;
URL/reload, standard conditions, reset/pagination and errors retain consistent state.
Direct API rejects inactive/disabled/role-denied/foreign fields. Existing server
semantics and quick-filter summary boundary preserved. No client-side list filtering.

Skills: zani-review-frontend, zani-run-verification, antislop during (saved preference)
and antislop-human. Apply existing labelled Select/Input, localized copy, keyboard
and Escape/focus return, responsive popover and retained draft. Existing CRM design
is direction: calm working form, ENERGY/RHYTHM/MOTION 1/1/1; no restyling/assets.

Checks planned: browser reproducer before fix; isolated custom-field/client API
regressions including permissions and summary; existing filter unit tests; targeted
RU/KK/EN desktop/mobile flow with screenshots; types/i18n and separate app/widget
build outputs. Full-project certification and live platformacrm.kz are out of scope.
Status: locally verified and code published to main.

Prior clients-records-20261105 evidence reported client custom-filter support and
12 node tests PASS. Subsequent CLIENTS-FILTERS-20261117 owner decision deliberately
removed these controls and URL keys. Current QA-006 specification explicitly asks
to restore custom-field filtering; this task restores only that requested behavior,
not removed segments/handoff/saved views. Current base reproduces the gap: clients-toolbar
tests fail 2/6 (custom key stripped and absent from client key list); a focused
URL-read check likewise reads undefined instead of field7. Minimal delta restores
that accepted contract; existing source/quick/card-context semantics stay intact.

Browser before fix: missing custom-filter combobox, timeout150s; captured under
output/qa-006-20261121/before. Final node suites after fix:15 PASS (clients-toolbar,
custom-field-filter, client-search). Reused existing tests instead of retaining a
duplicate new URL test. Frontend delta adds no fetch/effect/dependency: definitions
come from the existing context query; URL remains the source of applied state.
React best-practices review applies to the two changed TSX components: existing
query cache, shared controlled inputs and component contracts preserved.

Backend verification (unchanged production code):
`output/qa-006-20261121/backend.py` with isolated_runtime, disposable SQLite:
`manage.py test apps.clients.tests_custom_field_filters apps.core.tests_custom_fields
apps.core.tests_import_custom_fields --noinput -v 1`: 28 PASS.
`manage.py check` PASS; `makemigrations --check --dry-run` PASS, no changes.
New client-specific tests cover typed filters, count/summary before pagination,
standard source intersections, is_empty, invalid operators/values and rejected
inactive/disabled/role-denied/foreign definition IDs. No backend rewrite required.

Frontend commands from frontend:
`node --test scripts/tests/clients-toolbar.test.mjs scripts/tests/custom-field-filter.test.mjs scripts/tests/client-search.test.mjs`.
Build: `output/qa-006-20261121/build.py`, check-i18n, TypeScript -b, app/widget Vite
builds PASS; outputs isolated under this task folder, shared dist untouched.
`output/qa-006-20261121/browser.py`: 6 PASS (3.4 minutes), RU/KK/EN desktop Chromium
and Pixel7; text/number/select/date with API count/summary, standard source/search,
page reset, reload, empty operator/empty result, validation draft, clear and browser
Back/Forward. Escape closes and restores trigger focus. Product inputs unchanged
after this run; separate recovery test added afterward, no build inputs changed.

Screenshots inspected: RU/KK number, EN date desktop; RU number and KK/EN date mobile.
Existing scrollable popover accommodates added fields and localized footer buttons,
with readable labels/value/actions; no clipping of affected controls or horizontal
overflow. A screenshot of the scrolled panel naturally omits its upper content.
Anti Slop scoped gate: geometry/meaning PASS, existing shared form tokens retained;
behavior PASS for main scenarios above; labels and Escape/focus PASS. No new assets,
copy, typography, colors, motion or themes. Full theme/physical-keyboard/device
certification not claimed. Request-error recovery evidence follows below.

Updated frontend contract and clients passport to replace the deliberate17.11
removal only for QA-006. Domain/access/README/roadmap need no change: server policy,
API behavior, setup and roadmap scope are unchanged. No working DB or deployment.
QA-006 AC1-4 have local evidence;22 source QA IDs
remain open. Original production behavior/version remains outside local acceptance.

Recovery: `output/qa-006-20261121/recovery.py --grep 'request error'`,2 PASS
(desktop/mobile,1.6m). Injected list503 keeps source/search/custom value in URL,
existing Retry returns matching client, reopened panel retains Alpha. Keyboard
Enter opens panel and field selector; first Escape closes selector, second closes
panel and restores trigger focus. Mobile error screenshot and RU empty-result
screenshot inspected: visible error/retry and empty/reset, retained search and
usable toolbar. Total8 browser cases PASS across two scoped runs, not a full suite.
No code/evidence gap remains for the bounded QA-006 phase. Full-project gate,
production-origin smoke and live deployment not run; no authorization for working
DB operations was inferred. JSON registry/new-link and scoped diff hygiene PASS.

Code `c9570fa55adc940d6a8c8ce080f8d93558b0d77e` committed on codex/ui-testing-toolkit and normal-pushed to
origin main, remote SHA verified. Task-only12 paths/hunks reviewed; foreign WIP
preserved. Index and real committed-range diff hygiene PASS. CI44934913440 in_progress (conclusion=None).
No CI success or deployment is claimed. Publication record is a docs-only follow-up.
