# Calendar year correction and Records/Calendar review — 04.11.2026

User requested correction of the 1900 year list and wrapped fourth digit, a data-aware
year range, and an audit of implemented Records/Calendar changes. This is a new
explicit local task, not continuation/publication of another chat's work.
Canonical `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
HEAD `66101d509cb7642b2928275e48c4b64354abf07b` plus preserved mixed WIP.
Starting status/affected diff, plan, scripts, logs and screenshots:
`output/calendar-review-20261104/`. Final source hashes are in its `manifest.json`.

## Corrected behavior

- CalendarPicker and RecordsPeriodPanel use the earliest/latest **readable,
  nonarchived appointment starts**, including imported records. Existing workspace
  API is reused with business, ascending/descending start_at and page_size=1.
  No whole-history download or new backend contract. Dates use Business timezone;
  cache keys include business, user and timezone.
- Quick range begins at the earlier of current year and first record year, and ends
  at the later of current year +5 and last record year. Empty/error fallback is
  current year through +5. Explicit selected years and month navigation can extend
  this range: it is not a restriction on importing or selecting older/future dates.
  Generic date controls without business bounds use current year ±5 and retain
  selected/visible years and explicit min/max validation.
- Year menu is at least112px wide with single-line labels. Select scrolls to the
  active value; asynchronous insertion of earlier years preserves selected focus.
  Tokens, date validation, draft/cancel/apply and keyboard behavior are retained.

## Confirmed audit findings remaining open

1. **P2 — a retained responsible-user filter is displayed as All.** A role can read
   appointments without TEAM VIEW. Open Records with `responsible_user` pointing
   to another responsible user: the API returns the matching records, but the
   filter panel displays All. Apply retains the same ID. `RecordsToolbar.tsx:77`
   constructs options without the retained value; `RecordsPage.tsx:66` loads members
   only with TEAM VIEW and passes the current user as fallback. The generic Select
   displays its first option for an unknown value. Preserve an explicit unavailable
   selection (without revealing a hidden user's name), as CalendarToolbar already
   does. Reproduced against real isolated API, read-only fixture role.
2. **P2 — zero results remove the custom-field filter and its selective reset.**
   Apply a valid custom field with a nonmatching value. `RecordsPage.tsx:120-123`
   unmounts RecordsTable, which owns the custom-field toolbar. The applied URL
   condition remains, but editing/removing only this condition is impossible from
   the displayed UI. General reset also replaces the chosen period with today.
   Keep filter controls outside the nonempty-results branch. Reproduced with an
   actual synthetic field and real API; no response mocks. This belongs to the
   existing import/custom-field consumer WIP, not the year correction.

These are review findings, not fixes performed by this task. Source paths above
are relative to `frontend/src/features/calendar/`. Screenshots:
`audit-responsible-filter.png`, `audit-empty-custom-filter.png` in task output.
No additional confirmed Calendar defect was found in the reviewed boundary after
the requested picker correction; this is not exhaustive production certification.

## Verification

All commands below run from the canonical root; output runners use
`scripts.codex_verify.isolated_runtime`, disposable SQLite/media, synthetic users,
dedicated ports, mock/eager provider settings and disabled outbound delivery.
No ordinary database migration, seed, reset or live-provider call was performed.

| Command | Result / boundary |
| --- | --- |
| `node --test frontend/scripts/tests/calendar-years.test.mjs frontend/scripts/tests/calendar-period.test.mjs frontend/scripts/tests/record-filters.test.mjs` |17 PASS: quick years, historical/future selection, validation bounds, period arithmetic, URL filters |
| `.venv/Scripts/python.exe output/calendar-review-20261104/run.py --browser` |12 PASS, run1793810905747610800: month/week/year, summary/day drilldown, filters, keyboard, readonly,503 recovery; both pickers at320px RU/KK/EN,2014–2040 bounds, historical fallback |
| `.venv/Scripts/python.exe output/calendar-review-20261104/records-run.py --browser` |7 PASS, run1793811053109135200: table/client/drawer/plan links, real note save, permission denial UI,503 recovery, confirmation/early completion/reschedule/cancel and keyboard |
| `.venv/Scripts/python.exe output/calendar-review-20261104/audit-run.py --browser` |3 PASS, run1793811331665962600: two assertions reproducing the open defects above, plus delayed year-bounds focus regression. A passing reproducer does NOT close the defect |
| `.venv/Scripts/python.exe output/calendar-review-20261104/backend.py apps.scheduling.tests_calendar_summary apps.scheduling.tests_record_workspace` |40 PASS, run1793811089428597200: scoped API counts/filter/ordering, historical/future/timezone boundaries, tenant/OWN/role checks; system check included |
| `.venv/Scripts/python.exe output/calendar-review-20261104/run.py --build` |Final run1793811412380154500 PASS: safe frontend build, TypeScript, i18n, application/widget. Earlier successful build preceded final Select focus adjustment and is not substituted for this final run |

Screenshots `year-fixed-{ru,kk,en}-320.png` show synthetic isolated data, not
production. RU inspected visually; browser assertions check unwrapped digits,
selected-option visibility, focus and historical navigation in all three locales.
No dependency reinstall, full-project/E2E release gate, migration drift or production
deployment: no backend/model changes and no release authorization. Existing large
dictionary bundle warnings remain advisory.

## Documentation and delivery

Frontend picker contract and scheduling passport updated; registry/evidence and
task checkpoint recorded. CRM/API/access/AI/integration/operations/product/roadmap
and README require no change: existing API, permissions and business workflows are
reused, and no roadmap stage is closed. Historical reports remain unchanged.
Requested picker correction and bounded audit completed locally. Two audited
defects remain open for implementation. Existing `.git/index.lock` and unrelated
outgoing commits/mixed WIP prevent own-only publication; lock not removed, no stage,
commit/push, new CI or deployment performed by this task.
