# CALENDAR-OVERVIEW-20261104 (verification in progress)

Owner approved implementation after screenshot-based reference, then explicitly
extended scope to year overview. Canonical PlatformaCRM, codex/ui-testing-toolkit,
base66101d50 plus preserved foreign WIP. No task transfer or other-chat operations.
Plan, starting status/diff, original IAB screenshot: output/calendar-overview-20261104.

Implemented compact navigation/period/today/week-month-year/filter row; anchored
draft filters without modal; adjacent month dates with matching fetch range;
two appointment previews/overflow, separate task count; responsive year overview,
month/day drilldown and day-only detailed reads. URL is the state source; old hidden
search removed. Existing picker/popover/Select/day inspector/APIs reused.
New read-only calendar-summary groups scoped appointment starts in Business timezone
and returns at most366 day totals, no PII. Same history VIEW policy as ordinary list.
No migration, workingDB writes, notification/BusinessEvent/AI changes or deployment.

## Verification so far

- `.venv/Scripts/python.exe output/calendar-overview-20261104/backend.py`:11 PASS
  (test-1793808333749597400.log). Earlier enum typo and incorrect branch test retained
  as failures; branch expectation corrected against access.md CRM-MB01, not new policy.
- `.../backend.py --completion apps.scheduling.tests_calendar_summary apps.scheduling.tests_record_workspace apps.branches.tests_access`:
  system/drift and46 tests PASS (1793808750994082500), isolated SQLite.
- `node --test frontend/scripts/tests/calendar-period.test.mjs`:5 PASS.
- `.../run.py --browser`:7 PASS/1 FAIL (1793808740820351100), real isolated API.
  Failure is exact accessible-name test selector for shared Select; corrected test
  and targeted filter run pending. Passed year/day/month/week/history, neighbors,
  no hover popup, keyboard, readonly,503 recovery, RU/KK/EN mobile/picker flows.
- `.../run.py --build`:FAILED in existing i18n root dictionaries (1793809022633607500).
  Foreign importWorkspace spread precedes ru in en.ts/kk.ts. These were already dirty
  at task start and are outside calendar scope; not changed. Required build is not
  claimed green. Initial types found is_staff vs resource_type typo, corrected;
  final types/build stages pending.

## Remaining

Finish filter verification, type/application build stages, screenshot/contrast/source
review, docs consistency and own publication preflight. No overall delivery PASS yet.
Roadmap requirements unchanged (explicit UI continuation, no roadmap phase closure).
README/setup/access/AI/integrations/operations need no behavior change; CRM/API,
frontend contract and scheduling passport updated. No full release or live certification.
