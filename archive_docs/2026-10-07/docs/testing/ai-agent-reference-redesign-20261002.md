# AI-agent reference redesign — 2026-10-02

## Owner-approved navigation correction

After centered-width publication `028898d`, the owner requested the ordinary
global-search position and a small internal navigation panel in the free left
margin. This supersedes the prior header-picker/no-inner-list decision; the
960px centered editor and content-following actions remain unchanged.

The agent-only global-header grid, context slot and 105px header-height exception
are removed. Agents now use the existing common header grid and 57px height.
Create and selection move into page navigation: a 208px list panel from 1536px,
a two-button rail from 1280px, and a compact row above the editor below that.
The panel reuses actual bot/profile data, search by name/role, keyboard selection,
loading/error/retry/empty states, the create modal and existing dirty-draft guard.
All text comes from existing i18n keys and API fields.

Verification is scoped to navigation and shared-header geometry, using isolated
fixtures under `output/ai-agent-navigation-20261002`. The layout case compares
global search with Clients and Tasks at each tested size, checks sidebar/editor
separation, and retains five-tab/locale/centered-form evidence. Updated existing
picker cases cover expanded and collapsed navigation, create-dialog focus,
cancel/save/discard, long lists, loading/error/retry/empty and denied access.
Unchanged knowledge/channel/preview business contracts reuse prior evidence.
Final results and exact publication receipt are at the top of PRIMARY-SESSION.

Navigation correction browser receipt (helper prefix:
`.venv/Scripts/python.exe output/ai-agent-navigation-20261002/verify.py`):

| Arguments | Result |
| --- | --- |
| `desktop e2e/agent-reference-layout.spec.ts e2e/agent-header-picker.spec.ts --project=desktop-chromium --grep 'centered agent\|agent navigation searches\|picker presents\|manager cannot'` | Layout and denied access PASS, retained; create-close focus failed and was corrected. Long-list case superseded by the focused repeat below. |
| `desktop-navigation-final e2e/agent-header-picker.spec.ts --project=desktop-chromium --grep 'agent navigation searches'` | PASS: expanded panel, creation-dialog focus, search, long label, dirty cancel/save/discard. |
| `desktop-states-final e2e/agent-header-picker.spec.ts --project=desktop-chromium --grep 'picker presents'` | PASS: collapsed rail, scrollable list, keyboard selection, loading/error/retry/empty. |
| `mobile-tablet e2e/agent-reference-layout.spec.ts e2e/agent-header-picker.spec.ts --project=mobile-chromium --project=tablet-chromium --grep 'centered agent\|agent navigation searches\|picker presents\|manager cannot'` | Five PASS; three tablet interaction cases intentionally skipped because that interaction matrix covers desktop/mobile. Tablet layout is included. |
| `create-preview-mobile e2e/agent-setup.spec.ts --project=mobile-chromium --grep 'saved agent setup'` | PASS: actual creation through page navigation, saved setup, preview/recovery/readiness. |

Ten applicable browser cases passed. Desktop layout/denial evidence has unchanged
inputs after the local focus correction; panel keyboard behavior was repeated.
The create-modal correction uses the existing explicit focus-return mechanism,
without changing shared overlays. Search x/y/width/height match Clients and Tasks;
the global header is 57px throughout. All five sections remain centered and clear
of the navigation panel. RU/KK/EN, keyboard, contrast, no horizontal overflow and
long-form action reachability passed at 1280/1600/1848, tablet1024 and mobile393.
Screenshots and JSON are in the helper's `browser-*` output directories; the final
wide panel is in `browser-desktop-navigation-final/.../navigation-profile.png`.

An initial preflight failed before browser launch because the tracked picker had
been renamed but the rename was not yet staged. Reviewing/staging those two paths
allowed the unchanged Vite-environment policy to inspect tracked source. Failed
attempts are not counted as successful gates. No dependency reinstall, full local
backend/CRM suite, working database, live provider or real activation was used.

Final isolated `verify.py build` passed i18n (5080 keys), TypeScript and app/widget
builds. `npm run check:bundle` passed: app shell297.5kB (92.0kB gzip), agents71.7kB
(17.8kB gzip). The common search position was also visually reviewed on wide and
compact screens; the running local Vite server serves the updated canonical source.
No backend, permission, notification, BusinessEvent, AI/provider or migration
contract changed. The source branch remains `codex/ui-testing-toolkit`, target main.

## Owner-approved centered-width correction

The owner subsequently rejected viewport-wide forms and approved replacement
profile/channel/action references. This amendment supersedes the full-width
layout statements below; their original verification remains historical evidence
for6a3f39f. That commit was normal-pushed to main and CI36983828025 completed
successfully. Correction base: `6a3f39f5dbeba8d1340208208ceb207e7175c040`.

All five tabs now share one centered max960px container with responsive outer
padding, measured relative to the area right of the global sidebar. Heading,
tabs, sections and bottom actions have aligned edges. The container has no outer
card or border. Page content sets its height; the document scrolls, and bottom
actions immediately follow the form. The preview log has bounded scrolling;
it no longer grows to consume unused viewport height. The role textarea starts
at80px and remains resizable. Desktop controls stay36–40px; touch controls keep
their existing accessible sizing. The compact action rows expose their existing
explanations through native disclosures; no safeguard or setting was removed.

The generated references' dark sidebar, replacement logos/search/avatar, status
values and switch positions do not alter the approved global shell or business
rules. No internal sidebar was restored. Backend, API, permissions, readiness,
save/dirty guard and AI-execution contracts are unchanged.

Correction verification uses the same isolated helper mechanism under
`output/ai-agent-centered-20261002`. The updated existing layout spec checks all
five tabs at1280×720,1600×900,1848×1000,1024×768 and393×851, plus RU/KK/EN. It
measures left/right margins, maximum width, aligned heading/tabs/fields/actions,
content-following footer, desktop control and textarea heights, resizability,
long-form save reachability, action descriptions and mobile search separation.
Relevant existing picker/dialog/save tests and build/budget complete the boundary;
results and exact commands are in the current checkpoint. No unrelated CRM audit
or full local suite is triggered by this correction.

Before screenshots for all five tabs reuse unchanged6a3f39f evidence under
`output/ai-agent-reference-20261002/browser-layout-final` and its final mobile
offset run. After screenshots and measured JSON are under
`output/ai-agent-centered-20261002/browser-desktop-layout-final` and
`browser-mobile-final`; unchanged tablet evidence remains in `browser-layout-final`.
Images include entire long forms and separate expanded-help/advanced-field states.
The local `comparison.html` presents all five tabs before/after at 1280, 1600 and
393 px. Additional 1848 px after-images verify the wider-screen layout; no archived
1848 px before-image existed, and the old source was not restored to fabricate one.

The initial correction layout run passed tablet/mobile but failed desktop on
the role textarea (96px instead of80px). The shared class joiner preserves both
minimum-height utilities; a local explicit override fixes it without changing
shared Textarea behavior. A concurrent interaction-run environment startup timed
out before tests. Subsequent browser runs are serialized; neither attempt is
counted as a passed final gate.
The next layout attempt exposed two harness assumptions: CSS reports vertical
resize as `vertical`, and nearest scrolling can leave a button behind the fixed
mobile navigation after collapsing content. The harness now checks the actual
CSS value and scrolls the action into the central visible area before measuring
reachability. The no-overlap assertion remains in place. Only failed desktop/mobile
targets are repeated; the unchanged tablet PASS is reused.
The desktop interaction run passed both existing picker/dialog tests. Its layout
case then attempted to save the same fixture value at a second viewport; the
correctly disabled save button timed out. The fixture now uses a unique value per
viewport. Only that layout case is repeated, without rerunning the passed tests.
The existing mobile setup test also needed to scroll back to the page top after
saving the long initial form: its subsequent Create-agent click targeted a header
hidden by scroll. The trace confirmed the target was outside the viewport. The
harness now returns to the top before that click; no product assertion was removed.

### Correction verification receipt

Canonical checkout and branch are unchanged. Commands below use
`.venv/Scripts/python.exe output/ai-agent-centered-20261002/verify.py` as their
prefix. That helper delegates to `scripts.codex_verify.isolated_runtime`, validates
Vite environment policy, uses disposable SQLite/ports and the existing installed
dependencies. Real provider calls and working-DB changes are excluded.

| Arguments after helper | Result and boundary |
| --- | --- |
| `layout-final e2e/agent-reference-layout.spec.ts` | Tablet PASS, reused for unchanged inputs; failed desktop/mobile cases superseded below. |
| `desktop-final e2e/agent-reference-layout.spec.ts e2e/agent-header-picker.spec.ts --project=desktop-chromium --grep 'centered agent\|header picker searches\|knowledge and channel'` | Two picker/dialog tests PASS; fixture-related layout timeout superseded below. |
| `desktop-layout-final e2e/agent-reference-layout.spec.ts --project=desktop-chromium` | PASS: 1280×720, 1600×900, 1848×1000; five tabs and RU/KK/EN. |
| `mobile-final e2e/agent-reference-layout.spec.ts e2e/agent-header-picker.spec.ts --project=mobile-chromium --grep 'centered agent\|header picker searches\|knowledge and channel'` | Three PASS: layout/locales, picker/dirty guard, knowledge/channel dialogs and failed-save recovery. |
| `preview-mobile-final e2e/agent-setup.spec.ts --project=mobile-chromium --grep 'saved agent setup'` | PASS: persisted settings, preview, injected provider-error recovery, reset and readiness. |

Eight applicable browser cases passed across these runs. Earlier failed attempts
are retained in the logs and explained above, not counted as green runs. Browser
evidence covers both empty and populated knowledge states, long forms, all seven
action descriptions, menu/dialog focus and zero measured horizontal overflow.
Contrast checks pass for the five sections at each tested viewport.

Measured desktop width is 960 px throughout. Equal margins inside the workspace
are 128/288/412 px at viewport widths 1280/1600/1848, respectively. Profile footer
ends at y=663 in all three cases, independent of viewport height. Tablet and mobile
retain responsive padding; long forms scroll naturally with reachable actions.
The author visually reviewed all five tabs at 1600 px and mobile, wide profile,
expanded settings/help, and representative picker/channel/knowledge dialogs.

Full local backend/E2E, dependency reinstall, working-DB migrations and live
activation were not run: this correction changes only agent layout/disclosures
and associated browser fixtures. Existing API/domain/authorization contracts and
global shared primitives remain unchanged. This is local scoped evidence, not
live-provider or deployment certification.

Final `verify.py build` passed i18n validation, TypeScript and app/widget production
builds. `npm run check:bundle` passed: agent chunk 70.4 kB (17.5 kB gzip), app shell
298.4 kB; all JS chunks remain below 500 kB and shell below 400 kB. Working diff
hygiene passed. Publication and actual CI receipt are maintained at the top of
PRIMARY-SESSION; the five unrelated policy files remain excluded.

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
