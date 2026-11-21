# QA-016 localized automatic task search, 21.11.2026

User scope: next locally reproducible P2 QA issue; no working DB operations.
Canonical C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit,
base c83bdd26c653cccf28735944e79639d2affc2664. Foreign auth/WhatsApp/docs WIP preserved.
Prior QA-006/017 and other closures remain unchanged.

Gap: taskTitle renders provenance-backed automatic titles in RU/KK/EN, while
server search sees only stored English title/description and TaskEditor uses raw
title. Reuse system_copy provenance, existing task selectors/API/formatter/editor.
Implement SQL filtering on displayed generated title for requested locale before
pagination, retaining original-text search and tenant/role scope. Recognize only
matching creation metadata plus unchanged canonical title; no prefix-only guessing.
Editor displays formatter output but sends only actual edits, preserving stored
canonical copy when another field changes. No migration/backfill or working DB.

Risk: hidden tasks leaking through search, false positives for user text, changing
stored title merely by opening/saving editor. No permission, lifecycle, activity,
BusinessEvent, notification or AI behavior change. No deployment/shared build/server.
Skills reused: zani-change-crm-domain, zani-review-frontend, zani-run-verification,
antislop during/human. Preserve existing form tokens/labels/focus/draft behavior,
existing localized copy and API layer; no new visual design or components.

Checks: isolated failing search regression; RU/KK/EN/generated/custom/edited/
missing-provenance/tenant/pagination/summary tests and dependent task suites,
system/migration drift. Frontend query/formatter tests, targeted desktop/mobile
browser search-clear/open/edit/retention with screenshots, types/i18n and separate
build outputs. AC1-3 locally verified is phase boundary, not live certification.
Status: QA-016 AC1-3 locally verified; code published to main. Eight of29 report
items have scoped local closures,21 remain open. No remaining code/evidence gap
within QA-016; live deployment and PostgreSQL execution are outside this boundary.

Before.log: RU search returned0 for three automatic tasks; provenance test likewise
returned no matching task. Test correction: a foreign task list returns200 with
zero results under the existing scope contract (not403); assert empty results/count.
First focused run confirmed multilingual count/provenance/tenant behavior but the
pagination test assumed page_size query support that this endpoint does not have.
Use a test-only PageNumberPagination.page_size=1 to exercise actual pagination;
do not change production pagination for this task. Preserve both failed logs.

Focused-final:3 PASS plus check/drift. Before UI integration the multilingual
filter, source metadata and foreign-list boundary passed. Expanded final backend
then passed66 cases. Review found PostgreSQL JSON/integer comparison risk; changed
the RHS to KeyTransform over JSONObject so both sides stay JSON typed. Repeated
the full affected suite on that final code:66 PASS in portable-backend.log,
including OWN role, malformed string appointment metadata, dictionary/template
parity, and all existing task workspace/system-copy/task tests.
Command: `output/qa-016-20261121/backend.py` via isolated_runtime runs
`manage.py test apps.tasks.tests_localized_search apps.tasks.tests_system_copy
apps.tasks.tests_workspace apps.tasks.tests --noinput -v 1`, then `check` and
`makemigrations --check --dry-run`: both PASS, no migrations. SQLite disposable DB.

Frontend: `node --test scripts/tests/task-localized-copy.test.mjs
scripts/tests/route-prefetch.test.mjs` from frontend:9 PASS. Locale separates
list/summary cache identity; parent task options use the common formatter and
preserve original user titles. `output/qa-016-20261121/build.py`: i18n, TypeScript,
app and widget builds PASS. Backend-only JSON comparison change does not alter
these build inputs. Existing TanStack query API and editor changed-fields payload
reused; no new effect, fetch layer, component or dependency (React review).

First browser run: search and translated editor title passed, description lookup
by getByLabel(exact) did not resolve the existing textarea. Snapshot confirms the
translated description was present. Changed test to labelled textbox role; original
failure retained in browser-final. Final query expression is exercised by the
browser-portable run. Synthetic creation helper calls configure_browser_runtime
before ORM access, rejecting a working DB and disabling external connections.

Final browser-portable/browser.log:6 PASS (2.6m), RU/KK/EN on desktop/mobile.
Search, empty/clear recovery, keyboard Enter, localized editor, unchanged original
copy after priority save, failed-save draft retention/retry and custom-title reload
are verified. Visually inspected all six editor screenshots and RU desktop/KK mobile
search screenshots: description wrapping, control alignment, visible actions and
search focus fit existing layout; no changed-area clipping. Editor screenshots are
scrolled to description/priority; title values are covered by browser assertions.
No layout/copy redesign, new loading mechanism or theme change: existing components
remain; no full accessibility or whole-product certification claimed. Screenshots
and logs reside in output/qa-016-20261121/browser-portable.

PostgreSQL portability: `output/qa-016-20261121/compile_postgres.py` compiled the
final ORM predicate with Django PostgreSQL15/16 dialects, never opening a database
connection. Reviewed JSONB-to-JSONB comparison in postgres-compile-final.log.
This is compilation evidence, not PostgreSQL runtime/load certification. Initial
compile-only helper lacked DJANGO_SETTINGS_MODULE; fixed helper environment only,
retained postgres-compile.log failure. No production connection or DB access.

Contracts: crm/frontend and tasks-automations passport updated. Roadmap, README,
access and AI contracts unchanged: this repairs existing search/editor semantics,
with no permission/setup/automation/lifecycle change. QA-003 broader event/error
localization remains open; this phase only addresses QA-016 AC1-3.

Publication: code 8a240ad39348a62bcebd714a7699c3f6b0eec653 on branch
`codex/ui-testing-toolkit`, normal-pushed to origin/main; remote SHA readback matched.
Only reviewed task paths and the own STATUS entry staged; foreign WIP preserved.
Working/index/committed-range diff hygiene passed; registry JSON parses and new
relative evidence links resolve. CI44937543011 queued, conclusion null at readback
(https://github.com/999MAX20/PlatformaCRM/actions/runs/44937543011); not a CI PASS.
Working DB, shared servers, deployment untouched. Next scope: highest-priority
remaining locally reproducible QA issue; QA-003 and live QA-025/027 remain open.
