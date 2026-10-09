# SETTINGS-WORKFLOW-20261009

09.10.2026, owner-requested implementation after SETTINGS-REDESIGN review.
Canonical root C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
base 3026debb3b2b9078fc2764dc8f2042a55ee0e90b. Scope and publication receipt:
[PRIMARY-SESSION](task-state/PRIMARY-SESSION.md). Current contract: [frontend](../current/frontend.md).

## Result and boundaries

- Company is one form; timezone, currency, invoice email, legal name and optional
  tax ID remain. Slug/reference-only metadata are hidden and preserved by updates.
- Financial source/connector controls move to Integrations using the same Business
  API and permission. No provider connection or external synchronization is initiated.
- Roles leave the Settings sidebar and open from employee/invitation drawers with
  selected role, shared-role impact and return preserving the draft.
- Personal notification preferences live in Account, explicitly scoped to Business/User.
  Default-on and critical-event exceptions are unchanged. Legacy Settings hash redirects.
- Security retains audit/login/support records, adds failed-login filtering and removes
  unhelpful aggregate counters. Existing history is limited to the latest 100 events.
- Empty Inbox quick replies link to Settings for users with management permission.
- Custom-field headers/rows share column sizes and an action menu. Existing panel is
  reused on full client/lead/deal/appointment pages after a reproduced missing-input
  failure. Definition creation, value save and reload are verified through real APIs.
- Billing body is cleared; stored subscription and billing APIs are unchanged.
- Usage uses backend entitlements: active members, bots, automation rules, storage MiB
  and monthly UsageCounter values against plan limits. These are stored business data,
  not frontend mock numbers; local fixture data are not production metrics.
- Category headings shift left. RU/KK/EN and mobile navigation remain supported.
- Custom messaging scenarios are explicitly deferred by the owner.

No backend/domain change, migration, ordinary DB mutation, external send, new permission,
BusinessEvent or AI policy. Full production/release certification is outside this scope.

## Verification

Disposable SQLite runtime and isolated frontend/backend ports use the existing
`scripts.codex_verify.isolated_runtime`; installed dependencies and lock inputs unchanged.
Working UI inspected read-only through the browser: corrected custom-field columns,
compact action menu, category/navigation alignment and the single Company form.

Focused first pass: 5 tests PASS for profile preservation/invalid timezone recovery,
Account preference load/retry, cleared Billing/real Usage, invitation return and custom-field
editing. Log `output/settings-workflow/browser-1791556162594684500.log`.

Reproducer before full-page integration: client field input absent, 1 expected failure,
`browser-1791556438364011900.log`. After reuse of the existing panel: all four entity
creation/value/reload flows PASS, `browser-1791556639612488000.log`.

Desktop affected suite: 24 PASS, `browser-1791557093952829900.log`:
`.venv/Scripts/python.exe output/settings-workflow/verify_ui.py desktop-chromium "settings-(functional|redesign|workflow).spec.ts" --max-failures=2`.
The same three committed spec files cover scoped data/locales, profile preservation,
message-setting drafts/retry, typed fields, empty Billing/real Usage, independent role
permission writes, invitations/access controls, keyboard/focus, field permissions,
contextual existing-role editing, finance-source retry, per-user/business preferences,
Inbox empty-to-create-to-draft and all four full entity pages.

Initial added-test errors were test setup/selectors: accessible Select names include
the selected value; Business creation requires a slug; filtered role groups open
automatically. Tests were corrected against observed UI/API, without weakening their
data assertions. Four-entity regression and full desktop suite then passed.

Backend/services, dependencies and schema are unchanged: reuse the applicable
domain/tenant/rollback/system/drift proof in prior evidence. No backend suite or
full release gate is repeated merely for this frontend completion.
Mobile affected suite: 24 PASS, `browser-1791557309620003800.log`, same command with
`mobile-chromium`. Company and populated custom-field screenshots reviewed: no horizontal
overflow; compact action menu and stacked rows. Full-page screenshots include viewport
overlays from fixed navigation/save controls.

After the final failed-login empty-state copy change, desktop security recheck 1 PASS,
`browser-1791557565093593600.log`: `verify_ui.py desktop-chromium settings-redesign.spec.ts --grep "security tabs"`.
The initial concurrent attempt timed out during web-server setup before any test
(`browser-1791557376582185200.log`); the sequential retry passed without source changes.

Final `.venv/Scripts/python.exe output/settings-workflow/verify_frontend.py` PASS:
`npm run build` (5532 i18n keys, TypeScript, Vite application/widget) and
`npm run check:bundle`, `frontend-isolated-final.log`. App shell 325.7 kB, Settings
68.7 kB, largest locale 436.3 kB before gzip; all configured budgets passed.
Changed/new files reviewed for secrets/unrelated data; docs registration, links,
encoding and diff hygiene passed. Publication is recorded in the checkpoint.
