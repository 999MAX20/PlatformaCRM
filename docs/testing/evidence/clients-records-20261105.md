# Clients workspace: Records layout and functional cleanup, 05.11.2026

Owner approved implementation of the reference with Records spacing and requested
an explanation/removal of redundant controls. Canonical PlatformaCRM checkout,
branch codex/ui-testing-toolkit, HEAD66101d509cb7642b2928275e48c4b64354abf07b plus
preserved shared WIP. Starting snapshot, plan, own delta, source SHA256 manifest,
fixtures, scripts, screenshots and exact logs: `output/clients-records-20261105`.

## Result and control audit

- Search keeps the real server-backed name/phone/email query. Waiting replies is
  the existing unanswered inbound predicate in an open conversation, not an editable
  client lifecycle. The count comes from the scoped API summary.
- Removed checkbox selection: it had no bulk operation and only opened the first
  selected client. Row/name/Enter/Space now opens the existing client drawer directly.
- The reference's all-status dropdown was not a supported client-status filter.
  Archive/source/tags/segment/handoff/creation date remain in one filter panel.
  Additional-field conditions share its draft, Apply/Cancel/reset and saved views.
- One columns control contains Source/Manager visibility and additional columns
  with their existing ordering. Core client/status/activity/next-step fields remain.
- The three-dot list menu holds export of ALL readable clients (explicit label;
  not a filtered/page-only export) and permitted manual accounting. Keeping the
  menu subtree mounted preserves an export job while the menu is closed.
- Create remains the primary header action, hidden with its shortcut for denied
  roles. Existing client edit/tag/archive/merge and segment forms are reused.
- Last contact renamed Last activity in RU/KK/EN because it includes CRM activity.
  No new status policy, API, backend, schema, business event, notification or AI action.

Records wrapper, shared table/pagination, semantic colors/type and radius reused.
Measured1440px: both workspaces x88/right1416,24px side inset from the sidebar/content
edge, toolbar y65/h40, global-header gap16px, table gap16px, footer gap16px.
Horizontal control gaps8px. Mobile390px uses the existing horizontal toolbar pattern
and client cards, with no document horizontal overflow. No unrelated page redesign.

## Verification

Commands from canonical root:

- Runtime Node `--test frontend/scripts/tests/clients-toolbar.test.mjs frontend/scripts/tests/client-search.test.mjs`:12PASS (`node.log`).
- `.venv/Scripts/python.exe output/clients-records-20261105/run.py`:
  initial browser5PASS/3 harness failures; narrow corrected reruns below.
- Same runner `--grep 'desktop rows|single columns|failed refresh'`:3PASS,
  run1793821288186936900 (31.8seconds).
- Same runner `--grep 'desktop rows|locale|one draft'`:4PASS plus one new harness
  source-selector failure; desktop and RU/KK/EN evidence on final layout retained.
- Same runner `--grep 'one draft'`:1PASS, run1793821549789291600. This includes combined
  source+additional field, saved view, cancel/reset/empty recovery, nested Escape,
  and the moved segment-create trigger. Eight distinct browser scenarios passed
  across focused runs; this is not one all-green full-project suite.
- Same runner `--build`:i18n6883, TypeScript, app/widget Vite build and bundle budget
  PASS. Repeated once after the final2px spacing correction; final build logs retained.
  RU/KK dictionary chunks above500kB remain advisory; app-shell budget passes.

Browser evidence: real HTTP/isolated DB, waiting-reply toggle, row/name/Enter drawer,
server sorting/paging/search/reset; one Apply for ordinary/custom filters, saved
views, nested Escape and focus; column toggles; real CSV download; financial drawer;
create dialog; viewer denial of create/shortcut/payments; injected403 conceals old
rows and retry recovers; RU/KK/EN desktop/mobile; Records filters and layout comparison.
No pageerrors in the desktop flow. Screenshots and spacing.json were inspected.

Failures were test setup/expectation issues: nonexistent Client.is_active fixture
field; wrong relative Playwright path; seeded third unanswered client; obsolete
expectation that /app/leads exposes the old toolbar; error surface uses status rather
than alert; Source is checkbox multiselect rather than combobox. Receipts retained.
Leads/Deals now route to LegacyRecordsPage; old shared-filter consumers are not
reachable there. Their pure filter-state behavior is covered by the Node regression,
not claimed as a reachable old-toolbar browser PASS.

Uses scripts.codex_verify.isolated_runtime and guarded setup, disposable SQLite,
media/ports, fake scanner/eager worker and disabled external providers. No working-DB
write/migration, paid API call, dependency reinstall or shared server restart.
Owned test servers stop with runner. Full-project, backend and live-worker gates
not required for this frontend scope and not claimed. No production rollout proof.

## Scoped UI quality gate

- PASS function/purpose: each changed block maps to search/filter/columns/list action,
  entity opening or pagination; redundant selection and duplicate custom toolbar removed.
- PASS hierarchy/spacing: owner-selected Records direction; measured geometry above,
  existing neutral/emerald theme, restrained rhythm and unchanged motion (1/1/1).
- PASS content/source: real API summaries/entities, existing localized copy plus
  approved functional labels; synthetic names exist only in isolated test fixtures.
- PASS interaction/states: recorded browser click-through above; native named controls,
  keyboard/focus, empty/retry/denial, pending export preservation. No decorative assets.
- PASS craft: standard tokens/radii/type; semantic badges distinguish real computed
  states, icons identify search/filter/columns/actions; no new gradients/glow/media.
  This scoped gate is not a full-site accessibility or performance certification.

## Delivery boundary

Implementation and agreed local verification complete; no scoped code/evidence
remainder. Publication remains blocked by the pre-existing empty .git/index.lock
and17 foreign outgoing commits. No lock deletion, own stage/commit/push/newCI/deploy.
Standing authorization does not permit publication of other writers' work.
Frontend contract and clients passport updated; roadmap/acceptance IDs unchanged.
Other domain contracts and root README need no change: no domain/setup/public-status
change. Historical evidence is preserved; this report is the current scoped receipt.

## Owner follow-up05.11 — search width and Clients actions

Supersedes the earlier Clients export/menu placement in this report. Owner requested
page searches match global-header search, standalone Manual accounting in global
header, and removal of Clients export. Implemented shared opt-in Input pageSearch
and existing --global-search-width for specialized inputs; 480px on wide desktop,
constrained by available space. Applied to Clients, Records, tasks, services,
resources, timeline, support, pricing and platform lists. Dialog entity lookups
retain their own container layout. Clients export/list menu removed; Manual
accounting restored as a separate permission-aware header action. No backend change.

Before snapshot/plan/own patch/final hashes/logs: output/clients-records-20261105/followup.
Checks: node --test frontend/scripts/tests/clients-toolbar.test.mjs
frontend/scripts/tests/client-search.test.mjs —12PASS.
`.venv/Scripts/python.exe output/clients-records-20261105/followup/run.py`:
initial7PASS/2FAIL; the two width checks selected hidden global search then compared
inner input instead of full visible search frame. Corrected measurement; focused
`--grep 'desktop rows|list search widths'` final2PASS (1793822797416331800).
Nine distinct scenarios passed across scoped runs; this is not a clean full rerun.
Input width moved to inline token style before final focused run and final build.
Browser covers header payment open/denial, removed export/menu, search, rows/filter/
column/recovery, keyboard, RU/KK/EN Clients desktop/mobile and Records geometry;
five representative list pages at1440/768/390 without horizontal overflow. Desktop
measurements all480px against global480px. Pricing/platform use shared implementation
and build/static review; separate authenticated browser flows there were not run.
`run.py --build` final1793822720201197100: types/i18n6883/app/widget PASS,
bundle PASS; existing RU/KK >500kB dictionary warnings remain. No new install,
backend/fullproject tests or workingDB writes required for this UI-only change.
Owned isolated runtimes stopped. Screenshots inspected; same established tokens,
copy, functional controls and app-screen direction; no visual redesign.

Frontend contract and Clients passport updated in main text; roadmap/domain/setup
contracts unchanged. No scoped implementation/local-check remainder. Canonical root
C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit, HEAD66101d50.
Existing index.lock and mixed foreign outgoing still block own-only publication;
no own stage/commit/push/newCI/deployment and no lock/history modification.
