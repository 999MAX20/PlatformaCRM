# QA-017 custom field keys, 21.11.2026

User scope: continue locally reproducible QA issues by severity, no working DB.
P2 QA-017 code gap: frontend removes non-Latin letters from label-derived keys,
so distinct Russian QA names collide. Existing DB unique constraint and saved-value
identity protection remain; no existing key/value rewrite or schema migration.
Base 61a0105b51289ed134f57c94fc1084b96b8dbebe, codex/ui-testing-toolkit,
C:/Users/user/Desktop/PlatformaCRM. Prior QA-021/023/024/013/004 closure preserved.
Foreign auth/WhatsApp/docs WIP is outside this task; STATUS uses own hunk only.

Plan: server generates an ASCII UUID key when create omits key; explicit keys
remain supported and scoped to Business/entity type. Existing serializer validates
definition identity/options; a small creation service translates a unique-constraint
race into a key validation error. Frontend sends no label-derived key on create,
retains returned key on edit and keeps draft/error/retry behavior.
Risk: duplicate identity or lost saved values; tenant/permission regression.
No new permission, BusinessEvent, AI, provider or notification behavior. Keep current
audit/activity behavior. Skills reused: zani-change-crm-domain, zani-review-access,
zani-review-frontend, zani-run-verification; Anti Slop during/human. Preserve drawer,
tokens, labels, focus/error placement; no redesign or new merchant technical controls.

Checks: isolated API missing-key reproducer; multilingual/length/explicit-key and
stale-validation race tests, saved values and access controls, dependent custom-field
suites, check/migration drift. Real create/edit/retry browser flows RU/KK/EN desktop
and mobile with inspected screenshots; types/i18n and separate-output builds.
Use disposable DB/ports only. Shared server/build and production remain untouched.
Status: locally verified and code published. QA-017 scoped acceptance passed.

Before: API missing-key reproducer FAIL400 (before.log); UI slug expression maps
both Russian QA labels to qa. After: 22 focused custom-field/key tests PASS
(focused-final.log). Initial expanded fixture had two empty unique User emails
and omitted display.in_filters in the filter-retention scenario; fixed fixture
inputs without weakening permission/filter validation. Earlier failure kept in
focused.log. Stale validation is tested by validating both serializers before the
first insert, then asserting the second save returns a field error and one row.
Browser tests additionally issue simultaneous automatic and explicit-key POSTs.

Final backend: `output/qa-017-20261121/backend.py` uses isolated_runtime and runs
`manage.py test apps.core.tests_custom_field_keys apps.core.tests_custom_fields
apps.core.tests_import_custom_fields --noinput -v 1`: 31 PASS (includes the 22
focused cases). `manage.py check` PASS; `makemigrations --check --dry-run` PASS,
no changes. Real concurrent HTTP requests in the browser scenario additionally
verify two automatic creates return201 with distinct keys; duplicate explicit key
returns one201/one400 with key error. This is local SQLite evidence, not a separate
PostgreSQL load/concurrency certification.

Frontend build command: `output/qa-017-20261121/build.py`; final TypeScript,
check-i18n and app/widget Vite builds PASS. Outputs stay under this task's output
folder. Rebuilt after adding RU/KK/EN duplicate-key text. Anti Slop copy requirements
also apply: specific correction at the key field, no new unrelated copy/components.
New field creation omits key; edit keeps saved key; existing cache invalidation and
draft persistence reused. No state/effect or API layer duplication.

First browser run reached expected PATCH400 but its exact accessible-name locator
no longer matched after the shared Input included error text in its label. Corrected
the test to match the stable label prefix, retaining the aria-invalid assertion;
scroll inline error into view before screenshot. Failure kept in browser/browser.log.
Final run under browser-final uses the unchanged final product inputs.

Final browser: `output/qa-017-20261121/browser.py`, 6 PASS (3.2 minutes),
RU/KK/EN on desktop Chromium and Pixel 7. Final log and screenshots are under
`output/qa-017-20261121/browser-final/`. Visually inspected duplicate-key screenshots
for all six cases, RU mobile retained-input/retry and EN desktop saved-list screenshots:
labels/errors/actions readable, controls aligned, no horizontal overflow; mobile
inline error reachable by scrolling. Existing drawer, buttons and tokens retained.
Assertions cover localized error, aria-invalid, retained draft, recovery, persisted
rename/value and reload. Keyboard-only navigation/focus-return was not separately
recertified; shared dialog mechanics were not changed. No new loading/empty UI.

AC1-3 are locally verified. No schema/environment/permission/notification/AI changes;
no working DB access, migrations, production checks or deployment. Existing import
and custom-field suites passed. Full project gate and PostgreSQL stress testing were
not run for this bounded change. CRM/frontend contracts and registry updated;
roadmap/README need no change because this fixes existing behavior without changing
roadmap scope or setup. Of 29 source QA IDs, six have local closure evidence and
23 remain open; next work is the highest-severity remaining locally reproducible
issue. No remaining code gap in this QA-017 phase; live acceptance remains external.

Publication: code `e7c6ee2620d393a65887b8e22c17a71bd83b4e88` on `codex/ui-testing-toolkit`, normal-pushed to
origin main; remote SHA read back matches. Only 13 task-owned paths/hunks committed;
foreign WIP preserved. Working/index/committed-range diff hygiene PASS, registry JSON
and new evidence target PASS. No CI run listed yet for this SHA. CI is not claimed green.
