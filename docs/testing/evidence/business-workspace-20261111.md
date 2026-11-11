# BUSINESS-IMPLEMENTATION-20261111

Owner request: implement the approved business prototypes in CRM code. Canonical
`C:/Users/user/Desktop/PlatformaCRM`, current branch `codex/ui-testing-toolkit`,
starting HEAD `2e715377`. Other tasks changed HEAD during this work; foreign AI,
leads/task UI and documentation changes are preserved and excluded from this result.

## Result

Six real pages: Company, Branches, Staff, Services, Rooms/equipment, Schedule.
Company uses the business profile and protects drafts. The single-location view is
centered; a network has list/detail selection. Navigation retains branch context;
archive selection is independent. Creating a branch exits archive, preserving an
empty new catalog; restore returns it paused. Existing lifecycle/dependency guards
remain authoritative, including no restoration of a retired specialist.

Staff assignment to branches/services and CRM membership access are independent.
The staff page exposes actual team access controls; role/invitation administration
links to the established settings flow. Services retain one global identity with
branch offers and mandatory physical resources. Physical catalogs exclude staff;
account fields are absent there. Creation opens the actual new entity and clears
filters that would hide it; branch relationships are configured explicitly.
Search, paging, custom fields, permissions, archives and errors reuse existing layers.

The schedule has desktop week and mobile selected day, date override/reset,
multiple intervals where supported, absence projection and pair-specific travel.
Today uses the business time zone; month/day labels support RU/KK/EN. Automatic
locations use WorkingHours/ScheduleException; explicit branches use ScheduleDay.
The additive schedule-weekdays command validates 1–7 unique weekdays and uses the
existing service inside one Business lock/transaction. Later conflicts roll back
all days and audit; overlapping branches, missing travel and denied scope still fail.
No new models/migrations, permission framework, notifications, BusinessEvents or
AI execution. The UI does not interpret an active branch as guaranteed bookable.

## Verification and retained failures

Artifacts and exact commands: `output/business-implementation-20261111/`.
Backend runs use existing `.venv`, `scripts.codex_verify.isolated_runtime`, disposable
SQLite or native PostgreSQL17 and denied external network. Canonical source only.
No dependency installation, working DB/env change, provider operation or deployment.

- `run_checks.py catalog-fixed`: 4 PASS after correcting a fixture model import.
  Later expanded catalog tests initially expected a paginated result where the
  denied branch correctly returned an error; corrected to assert denial.
  `catalogs-corrected.log` retains 8 PASS and earlier logs remain.
- `run_checks.py weekdays-focused apps.branches.tests_schedule_weekdays`: focused
  4 PASS before dependent UI. Details in that log.
- `run_checks.py completion apps.scheduling.tests_resource_catalog
  apps.branches.tests_schedule_weekdays apps.branches.tests_scheduling
  apps.branches.tests_access apps.branches.tests_staff apps.branches.tests_physical_resources
  apps.branches.tests_single_location apps.services.tests apps.services.tests_metrics
  apps.scheduling.tests_working_hours_integrity apps.scheduling.tests_specialist_schedule
  apps.scheduling.tests.CorePlatformTests.test_resource_list_filters_paginates_and_returns_operational_summary
  apps.scheduling.tests.CorePlatformTests.test_resource_manager_can_view_but_cannot_update_settings
  apps.scheduling.tests.CorePlatformTests.test_bulk_upsert_week_creates_and_updates_without_duplicates
  apps.scheduling.tests.CorePlatformTests.test_bulk_upsert_week_rejects_invalid_week_without_partial_save`:
  98 tests, 97 PASS/1 PostgreSQL-only skip; system check and migration drift PASS.
- `run_pg.py apps.branches.tests_schedule_weekdays apps.branches.tests_concurrency
  apps.scheduling.tests_resource_catalog`: 15 PASS, including real concurrent writes;
  own PostgreSQL test cluster stopped and disposable database removed.
- After absence projection: `run_checks.py absence-projection
  apps.branches.tests_schedule_weekdays.ScheduleWeekdaysTests apps.branches.tests_staff`:
  9 PASS. Unchanged dependent results retained.
- `frontend_verify.py`: 6 schedule logic tests, i18n, forced `tsc -b`, app/widget
  builds and bundle budget PASS. Locale chunks retain size warnings; shell budget passes.
  Separate output directories preserve other builds. Final file snapshot below.
- `scripts/verify_business_workspace.py`: isolated real API and Chromium, synthetic
  accounts, own ports. Initial browser failures exposed test selector/locale/fixture
  errors: hidden desktop/mobile duplicate rows; combobox value in accessible name;
  hidden mobile shell heading; first-location shifts and required travel missing.
  They did not justify weakening domain constraints. Original logs are retained.
  Run `1794411935054281200`: 5 desktop flows PASS; 2 mobile recovery checks failed
  because a single injected 503 was automatically retried successfully. Corrected
  scenario keeps the outage until explicit Retry. Targeted mobile run
  `1794412181468444800`: 2 PASS, all six pages KK320/EN390, keyboard day selection,
  Today, sustained 503/retry and no document overflow. Screenshots inspected;
  Chromium's KK month placeholder was replaced by existing dictionary labels.

Covered: company save/draft guard/initial-point synchronization, physical creation,
branch price zero and duration, resource requirement save, failed save/retry with
retained input, staff assignment off/on, account disable without specialist disable,
weekly/day/reset/conflict recovery, archive/new branch/paused restore, manager denial,
mobile navigation/locales/keyboard/error recovery. Tests do not certify production,
provider delivery or the whole project. Full-project/E2E gates are not required for
this scoped implementation; no acceptance IDs or separate roadmap phases are closed.

## Closure

Automatic-location weekly/day/absence scenario: run `1794412302519482500`, 1 PASS.
Final affected company/mobile recheck after date-label correction:
`1794412509624447700`, 3 PASS. Eight distinct browser scenarios have passing evidence;
unchanged desktop results are reused. Final KK320 schedule image inspected: translated
month, selected day, horizontal navigation and no page overflow. Final forced types,
app build and bundle budget PASS; unchanged logic/i18n/widget checks retained.
Source hashes: `output/business-implementation-20261111/source-snapshot.json`.

Current frontend/CRM contracts and scheduling passport updated. Existing roadmap,
README, access, AI, integrations and operations contracts need no change: no new
release phase, setup, role, provider or operational behavior. No scoped code or local
verification remainder. Human production acceptance and deployment are outside scope.
Working DB, environment and ordinary development services untouched; owned test
runners exited. Full-project certification was not performed.

Fetch confirmed 0 remote-only / 35 pre-existing outgoing commits. Task-only local
commit is permitted; pushing that foreign range is not authorized. No push, new CI
or deployment is claimed. Publication is the remaining external blocker.
