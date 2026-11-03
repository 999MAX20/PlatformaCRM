# CALENDAR-SHARED-20261103

The accepted Records date picker is reused across seven consumer areas and all
26 `Input` date/datetime-local declarations in 19 files. Owner explicitly included
these fields, retained CalendarBoard, chose antislop After, then approved its one
cursor finding. No backend/API/domain/schema, permission, notification,
BusinessEvent, AI, working-data or deployment change.

Canonical checkout: `C:/Users/user/Desktop/PlatformaCRM`, branch
`codex/ui-testing-toolkit`, base `98d83de05eab1f9d311ab8592655922d2c3077b1`.
Starting dirty snapshot and compact contract: `output/calendar-shared-20261103`.
Unrelated existing WIP is preserved. Gates below cover the named working snapshot,
not certification or publication of unrelated WIP.

## Behavior

- CalendarPopover extracts the approved positioning, portal and outside dismissal.
  Inside a dialog its DOM stays in that dialog's focus boundary. Escape dismisses
  the nested select before the calendar; Tab continues from the opener to the next
  form control. Opening causes no page reflow.
- DatePickerPanel owns a range draft, Cancel and atomic Apply. Incomplete ranges
  cannot apply. CRM filters may clear the range. Single-day scheduling applies on
  selection. Analytics and operations no longer wrap the picker in another modal.
- Operations retains its existing UTC dates, future-date prohibition and maximum
  365-day difference. Existing route/filter/API consumers retain their formats.
- CalendarInput replaces the browser picker button for every date/datetime Input.
  Native value editing, required/min/max/step, disabled/readOnly, names, refs,
  change/blur handlers and RHF registration remain. Date-time selection preserves
  hours/minutes; empty time is not silently replaced with midnight. Apply checks
  native date-time validity; optional fields can clear. Error association and
  error-border hover/focus styling remain.
- Explicit month dictionaries avoid Chromium's `M11` fallback for Kazakh. Existing
  translated weekdays are reused. The compact header accommodates long months and
  a full year at 320px. Dates with times still use their caller's timezone conversion.
- Cursor correction is scoped to calendar controls, following explicit owner
  approval. Other shared buttons and styles are unchanged.

Current consumer map: [frontend contract](../../current/frontend.md#подключения-общего-календаря).
Scheduling passport: [scheduling](../../pre-production/scheduling.md).
Separate post-implementation review: [antislop audit](../../../anti-slop/audit-001-20261103.md).

## Verification

Existing dependencies reused. Builds use `safe_environment`; component browser
tests use dedicated Vite57433 and an unreachable backend9. Application browser
tests use `isolated_runtime`, fresh temporary SQLite, synthetic fixture users/data,
separate loopback ports, mock AI/eager providers and no ordinary database writes.
The standard isolated runner prepares/migrates only its disposable database.

| Command / evidence | Result and boundary |
| --- | --- |
| `.venv/Scripts/python.exe output/calendar-shared-20261103/verify.py browser` plus focused rechecks listed below | 15 unique shared-control scenarios passed across applicable final-input runs: date/range/date-time, bounds, required validation, RHF reset/submit, error styling, disabled/readOnly, nested dialog/select Escape, Tab, outside focus, translated months, 320/390/desktop and cursor behavior |
| `.venv/Scripts/python.exe output/calendar-shared-20261103/consumers.py` | Task deadline save and platform-history range passed on desktop and mobile; task date/time round-trip2026-12-15 14:35 Asia/Almaty =09:35Z |
| Same consumer command with `--grep 'analytics applies\|Records, schedule'` | Remaining four cases passed after test selector corrections: actual analytics request/503/recovery/period preservation and schedule/Records/client-filter URL flows, desktop/mobile |
| `.venv/Scripts/python.exe output/calendar-shared-20261103/verify.py build` | Final safe build, TypeScript, i18n6680, application and widget PASS |
| `.venv/Scripts/python.exe output/calendar-shared-20261103/verify.py bundle` | App shell342.1kB under400kB; existing RU/KK chunks over500kB remain warnings |
| Source inventory and diff/link/new-file review | All26 date fields still route through shared Input; no CalendarBoard/SimpleCalendar migration; owned paths reviewed separately from foreign WIP |

Eight unique application browser scenarios passed. This is representative consumer
coverage, not runtime certification of each of the19 source files or every permission
role. Backend suites, full E2E, dependency reinstalls, live providers, working-DB
migrations and deployment were not run: UI controls and representations only.
Keyboard/console and measured selected-text contrast checks passed in the focused
fixture. Token contrasts on white: primary16.64, secondary6.83, muted5.17,
selected white/brand.hover6.99. Disabled controls are exempt from text contrast.

Initial failures remain in ignored output, not rewritten as PASS:

1. `browser-first.log`: eight PASS, one incorrect test button name, and reproduced
   Kazakh Intl month fallback. Fixed accessible opener copy and explicit month names.
2. `consumers-first.log`: four PASS; analytics refresh selector matched both toolbar
   and recovery button, Records selector omitted its date suffix. Source/API behavior
   was intact. Corrected selectors and proved actual503 recovery in the recheck.
3. `browser-320-failure.log`: Russian long month clipped at320. First width adjustment
   exposed clipped years in EN/KK (`browser-year-failure.log`, twelve PASS).
   Reduced narrow-header gaps and reserved72px for year; all three320 cases then PASS.
4. Error-border hover retained the original Input rule after source review.
   The owner-approved cursor fix passed its focused test without enabling disabled dates.

Applicable evidence logs: `browser-ten-pass.log`, `browser-supplement-pass.log`,
`browser-year-failure.log` (its twelve passed unaffected cases),
`browser-320-pass.log`, final `browser.log` (cursor/date-time/RHF),
`consumers-first.log` (four unchanged PASS), final `consumers.log` (four rechecks),
`build.log`, `bundle.log`. Product source hashes and consumer inventory are in
[manifest](calendar-shared-20261103-manifest.json). Old logs retain their earlier
source boundary; only unaffected assertions are reused after the narrow CSS fixes.

## Visual evidence and closure

[RU320](calendar-shared-20261103-assets/calendar-320.png),
[EN320](calendar-shared-20261103-assets/en-320.png),
[KK320](calendar-shared-20261103-assets/kk-320.png),
[nested form](calendar-shared-20261103-assets/registered-dialog.png),
[date-time draft](calendar-shared-20261103-assets/datetime-desktop.png).
Screenshots are explicit isolated component fixtures, not merchant production data.

No code or scoped verification remainder. Publication/remote SHA and actual CI are
recorded in the task checkpoint. This change does not close a roadmap release stage.
Frontend contract and scheduling passport updated. Other business contracts,
passports, roadmap and README need no change: their data, permission, setup and
business workflows are unchanged; the frontend contract owns the shared control map.
