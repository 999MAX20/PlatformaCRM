# Records / Calendar fixes — 05.11.2026

Owner annotation1 authorized the two Records filter defects and nine failed Calendar
interaction cases. Implementation and scoped local verification complete. Publication
blocked; no claim of deployment or full-project certification.

## Result

- Retained responsible/resource/branch values missing from readable options display
  #ID rather than All. No hidden member name is fetched or exposed.
- Records custom columns/filter controls survive zero results and request errors.
  Selective reset keeps period/other filters. Browser Back/Forward updates the filter
  draft; the shared Services consumer was checked too.
- Calendar root horizontal clipping no longer creates a scroll container. Sticky
  toolbar and its picker/filter panels remain below the global header on scroll.
- Booking scenario failures were test ambiguity/prerequisite expectations: selectors
  now identify the intended controls, and existing branch requirements are preserved.
  No booking backend/domain policy was changed.

## Evidence and exact commands

Canonical `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
HEAD `66101d50`; shared dirty snapshot. Starting status, originals, owned source
patch, hashes, runners, fixtures, screenshots and logs are in
`output/records-calendar-fixes-20261105/`.

- `node --test frontend/scripts/tests/calendar-period.test.mjs frontend/scripts/tests/calendar-years.test.mjs frontend/scripts/tests/record-filters.test.mjs`: 17 PASS (`node.log`).
- `.venv/Scripts/python.exe output/records-calendar-fixes-20261105/run.py --browser --grep 'sticky panels|booking'`: final9 PASS, `browser-1793887005965788900.log`.
- `.venv/Scripts/python.exe output/records-calendar-fixes-20261105/run.py --browser --grep-invert 'sticky panels|booking'`: 14 PASS, `browser-1793887271899265600.log`.
- `.venv/Scripts/python.exe output/records-calendar-fixes-20261105/records-run.py --browser`: 7 PASS, `records-browser-1793887192704264100.log`.
- `.venv/Scripts/python.exe output/records-calendar-fixes-20261105/audit-run.py --browser`: initial two Records failures reproduced; after repair3 PASS. Expanded RU/KK/EN and recovery/history run7 PASS/1FAIL (`audit-browser-1793887182482363300.log`). The shared Services case attempted Back before pending filter navigation settled; bounded wait for completed query added. Focused `--grep 'shared service'`: 1 PASS (`audit-browser-1793887492857897800.log`). Eight distinct final audit cases passed across those runs, not a claim of one clean expanded run.
- `.venv/Scripts/python.exe output/records-calendar-fixes-20261105/run.py --build`: build/types/i18n/app/widget and bundle PASS initially (`build-1793887288969230000.log`). Final diff review found an accidentally recoded mobile separator, restored its original middle dot; final build and the three locale Records cases rerun (receipts below).

Initial failures retained: two filter defects, sticky picker closure, booking selector
ambiguity, and the Services harness navigation timing. Final scenarios verify real
isolated API creation/prerequisites, permissions, errors/recovery, URL state,
keyboard/focus, scrolling and RU/KK/EN desktop/mobile. Screenshots inspected in the
working session include sticky picker and retained responsible filter. No new
CSS-mirroring unit tests. Existing bounded runtime specs remain local evidence.

## Boundaries and documentation

Disposable SQLite/runtime ports only. No working DB mutation/migration, provider
call, deployment or dependency installation. Owned test servers managed by runners;
ordinary dev retained. Full-project/backend gates omitted: frontend behavior only,
unchanged backend contracts. Existing bundle locale size warnings remain.

Frontend contract, scheduling passport, STATUS/checkpoint and evidence registry
updated. Roadmap, business/access/AI contracts and README need no change: no new
capability, permission, setup, migration or roadmap acceptance is introduced.
Historical audit remains intact and is superseded only for these named defects.
No remaining code/scoped evidence item. Environment/publication remainder: existing
empty index.lock from04.11 and17 foreign outgoing commits prevent own-only normal
publication. No staging, lock removal, commit, push, new CI or deployment performed.

Final build/bundle receipt: build-1793887746387095000.log and bundle-1793887746387095000.log, both exit0.
Final locale recheck: `records-run.py --browser --grep "table drawer filters"`:3 PASS, `records-browser-1793887766087468200.log`.
Scoped working/index diff hygiene and affected links/registration/new-file review PASS. No committed range exists for this task; committed-range gate inapplicable.
