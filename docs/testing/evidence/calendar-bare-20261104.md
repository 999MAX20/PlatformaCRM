# Calendar: internal toolbar removal and deliberate day opening

Owner04.11 explicitly requested the internal header/search/filters removed, leaving
only the calendar board, plus a proposal for a replacement single-row header.
The replacement is NOT implemented by this cycle.

Canonical C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
HEAD66101d509cb7642b2928275e48c4b64354abf07b + preserved foreign WIP.
Before snapshots, plan and starting status: output/calendar-bare-20261104.
CalendarPage and calendar-workspace.spec.ts already contained unrelated changes;
those changes are retained. CalendarBoard was clean before this cycle.

Removed toolbar/chips and their unused page wiring. CalendarBoard no longer creates
a portal/timer/hover/focus preview; native buttons retain inline counts/entries,
hover/focus highlight, keyboard movement and click/Enter/Space day activation.
Existing inspector handles empty days, appointment lists and appointment details.
Global header/create, backend/API/permissions, URL date/view/filter semantics and
ordinary DB remain unchanged. Context URLs may still filter; the removed controls
will return only through an agreed replacement. No hidden new header implemented.

Proposed row: previous / clickable month or period / next / Today / Week–Month /
Filters(count). Specialist, branch (when applicable), service and status inside the
filter popover. Existing global create action suffices. Proposed height40px desktop,
44px touch controls on narrow screens, one scrollable row; no added title/card row.

Verification pending: `.venv/Scripts/python.exe output/calendar-bare-20261104/run.py`.
Guarded isolated_runtime, temporary DB/media/ports and synthetic appointments only;
real local API, outbound disabled. Build/types/i18n plus3 targeted locale browser
cases covering sustained hover, empty/occupied click, focus/Enter, detail opening,
month/week URLs, no internal controls and mobile width. Broader existing calendar
test expectations updated for removed UI; its full business-flow suite is not rerun.
No backend/full-project/release suite required for this UI-only scope.

Frontend contract and scheduling passport updated; no domain/roadmap/README/setup
change. Existing Git index.lock and unrelated outgoing/WIP prevent own-only commit/
push; no own commit, new CI or deployment. Previous Records work is a separate cycle.
