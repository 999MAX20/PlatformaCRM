# AI-agent reference redesign — 2026-10-02

## Scope and candidate

Owner-approved replacement for the cancelled compact-layout attempt. Canonical
checkout: `C:/Users/user/Desktop/PlatformaCRM`; branch `codex/ui-testing-toolkit`;
base `0521f03788783540894388518692f168fe9c4323`. Same registered primary writer.
The owner's separate verification-policy edits in AGENTS.md, testing.md, the task
template and two skills were confirmed during execution and excluded from this
change set. No backend, permission, notification, BusinessEvent, migration,
environment or AI execution contract changes.

## Result and reference interpretation

- One full-width editor, with the persistent inner agent list removed. Profile,
  Knowledge, Actions, Channels and Test use compact underline tabs.
- A fixed 180px selector sits between the page title and global search on wide
  screens; a second header row accommodates it on narrower screens. Creation
  remains a separate action. Full names remain available in the menu and title.
- The menu searches real names and profile roles, scrolls long lists, distinguishes
  operational status from readiness, and supports keyboard selection, Escape,
  focus return, loading, retry, empty and no-results states. Switching agents
  uses the existing unsaved-change guard.
- Profile follows the supplied reference's compact first row and section dividers;
  the dental preset sits beside the instruction heading. Advanced fields remain
  available in the existing disclosure. No field or text limit was invented.
- Actions use the reference's authority summary and aligned setting rows.
  Channels use name/status/action columns with provider logos and existing setup
  dialogs. Knowledge uses a toolbar and flat list; Test keeps readiness, real
  preview controls, source output and AI-usage notice.
- Global navigation, logo, search functionality, fonts and semantic palette are
  preserved. Internal agent labels use RU/KK/EN dictionaries. Existing translations
  outside the changed keys were reused, including any pre-existing RU fallback.
- Reference screenshots are structural guidance: actual backend status/readiness,
  permissions and auto-reply safeguards take precedence over illustrative copy.
  Small screens retain internal scrolling and reachable controls; all desktop
  content is not forced into one mobile viewport.

Shared changes are limited to an optional header context slot, an optional
underline Tabs appearance (default unchanged), and focus restoration that prefers
an explicit return target over the captured element. The latter fixes async channel
dialogs whose originally captured element can no longer identify the trigger.

## Verification

The ignored helper `output/ai-agent-reference-20261002/verify.py` uses
`scripts.codex_verify.isolated_runtime` and `validate_vite_environment_policy`.
It runs installed dependencies without reinstalling, with a disposable SQLite DB,
dedicated ports, synthetic fixtures and mock AI. Ordinary `db.sqlite3`, existing
dev servers, real provider credentials and live AI were not used.

Commands below use `.venv/Scripts/python.exe` from the canonical root. Browser
arguments are forwarded to the Playwright CLI with `--max-failures=3 --reporter=list`
and per-run output folders under `output/ai-agent-reference-20261002`.

| Command arguments after the helper | Result and boundary |
| --- | --- |
| `picker-final-desktop e2e/agent-header-picker.spec.ts --project=desktop-chromium` | 4 PASS: search/name/role, long labels, keyboard/focus, dirty cancel/save/reset, loading/error/retry/empty, 36-row fixture, knowledge create/edit, four channel dialogs, failed save recovery, manager denial |
| `picker-final-mobile e2e/agent-header-picker.spec.ts --project=mobile-chromium` | Same 4 scenarios PASS on mobile |
| `setup-final e2e/agent-setup.spec.ts --project=desktop-chromium --project=mobile-chromium` | 4 PASS: untouched draft navigation, discard guard, real saved settings, disabled activation without readiness, mock preview, transport failure/retry and reload persistence |
| `layout-final e2e/agent-reference-layout.spec.ts e2e/inspector-interaction.spec.ts` | 7 PASS, 5 explicit viewport-specific skips: all five tabs, 1280×720/1600×900/1024×768/393×851, RU/KK/EN, active-tab visibility, overflow, contrast; CRM nested dialog/drawer focus regression |
| `shared-geometry e2e/crm-workspaces-reference.spec.ts --project=desktop-chromium --grep "three real CRM workspaces"` | 1 PASS: leads/deals/clients still fill the same workspace under the header |
| `mobile-search-final e2e/agent-reference-layout.spec.ts --project=mobile-chromium` | 1 PASS: final targeted verification of expanded search spacing after the small mobile offset correction |
| `build` | i18n/typecheck, app and widget production builds; see checkpoint for final result |

From `frontend`, the following passed:

```powershell
node --test scripts/tests/action-color-policy.test.mjs scripts/tests/action-feedback-policy.test.mjs scripts/tests/daily-workspaces-policy.test.mjs
npm run check:bundle
```

14 Node tests passed. Bundle budget passed (largest chunk below 500kB and app shell
below 400kB). Working-tree and index diff hygiene passed. Committed-range static
verification and exact remote/CI evidence are recorded at publication.

The initial picker run had 3 PASS / 1 FAIL: closing the website dialog failed to
return focus. After the explicit-target focus fix both final picker runs passed.
An earlier preflight hit an unstaged deleted legacy list component; staging that
reviewed deletion made the environment validator's tracked-file inventory accurate.
Neither failed attempt is treated as a successful gate.

## Visual evidence and limitations

Before: unchanged base screenshots in
`output/ai-agent-layout-20261002/browser-before` for all five tabs and target sizes.
After: `browser-layout-final`, `browser-mobile-search-final`,
`browser-picker-final-desktop` and `browser-picker-final-mobile` under
`output/ai-agent-reference-20261002`. The layout runs include per-tab images,
advanced profile, each locale and `layout-evidence.json`; picker runs include
long-name/long-list, state and dialog images. These are local ignored artifacts,
not production data or committed assets.

No full-project/backend/deployment certification was requested or inferred for
this frontend change. Browser tests exercise existing API contracts but do not
replace backend tenant-isolation certification. Real activation, messaging,
OAuth and paid AI were not exercised. Actual push-triggered CI is inspected
separately; pending CI is not reported as green.
