# MANAGEMENT-IMPLEMENTATION-20261111

## Browser review — 12.11.2026

Owner separately requested ordinary-user browser verification of all five pages,
forms, relations and schedules, including mobile, with fixes. Review base372ec4f8,
canonical checkout/current branch unchanged. Only five frontend files changed;
existing foreign WIP preserved. Detailed artifacts and commands:
`output/playwright/management-review-20261112/CHECKPOINT.md`.

Three reproduced issues fixed:

1. Changing only room branch/schedule mode or absence reason did not mark the form
   dirty: Cancel discarded the selection without warning. Explicit custom-Select
   dirtiness now reaches the form and navigation guard. The confirmation uses the
   existing general RU/KK/EN wording instead of referring to a schedule in every form.
2. The schedule's Absences link opened the specialist editor. It now opens that
   specialist's absence form directly, retaining branch context and existing rights.
3. Saving a direct-linked editor could reopen it when query invalidation reprocessed
   the same URL. Each requested form is opened once; successful saves bypass the
   dirty/pending navigation guard when clearing the form parameters.

Chrome interactive checks: specialist create, bidirectional service/room/branch
   relations, zero price and reload, branch address edit, date-specific schedule,
   absence create/edit, dropdown-only draft warning and successful form close.
Playwright against the same real disposable API: existing seven Management scenarios
PASS (CRUD/relations/reload,503 recovery/drafts/effective schedule, RU320/KK390/EN768,
manager denial403, lifecycle). Added diagnostic scripts prove direct-link save,
absence link/reason/calendar, room-branch-only discard, branch creation with links,
empty search/reset, all five pages at320/390/768/1440 and four forms at320 with
required-name/long-text/keyboard/discard behavior. Screenshot review performed;
no horizontal overflow in this coverage. Desktop/mobile browser, not a physical phone.

`npm run build` (types + i18n7237 keys + app/widget), `npm run check:bundle` and diff
hygiene PASS. Existing two locale chunk warnings remain; app shell is within400kB.
No backend/schema changes; isolated backend regression suites were not repeated for
these frontend-only fixes. No dependency installation, working-DB writes/migrations,
external-provider action or deployment. Existing design/tokens and API rights retained.

Retained failed attempts: initial CLI login500 from disposable SQLite lock contention
while another browser run wrote; serialized retry passed. First direct-link retry
exposed the query-reopen cause above, then passed after the fix. One diagnostic expected
an absence reason in a calendar cell; the approved cell uses generic Absences, corrected
against the implementation and independently checked saved reason. A dev-HMR provider
error interrupted the viewport sweep during build; fresh navigation after build passed
the remaining768/1440 screens and all forms. CUA time-field fill changed DOM but did not
commit React state; native keyboard input and independent Playwright schedule checks
confirmed persistence. Earlier failures are not presented as PASS.

No remaining code or local-browser evidence item in this review scope. Local commit
only; foreign outgoing commits prevent own-only push/new CI. Production remains outside
this review. Runtime/fixture cleanup and exact Git receipt are in the checkpoint.

Owner request: implement the accepted Management prototype in CRM, all five pages,
inner navigation, forms and responsive layouts with real data. Owner additionally
approved preserving existing automatic service eligibility as explicit links.
Canonical root: `C:/Users/user/Desktop/PlatformaCRM`; branch `codex/ui-testing-toolkit`.
Initial HEAD `f01d2d8b`; later shared-checkout commits/WIP from other tasks are excluded
from this task's authorship and publication. Detailed commands, failures and running
processes: `output/management-implementation-20261111/CHECKPOINT.md`.

## Delivered behavior

- Services, Specialists, Rooms, Branches, Working hours use existing domain entities
  and real tenant-scoped APIs. Desktop inner menu has five entries; mobile Select and
  responsive cards preserve access to the same forms. Company/account/equipment
  management is outside this menu; existing data and compatible direct routes remain.
- Atomic entity-plus-relation forms; nullable price differs from zero; explicit
  specialist services per branch; no implicit login creation or qualification by job
  title. Draft/error retention, retry, read-only roles, lifecycle confirmations.
- New specialists have no implicit service eligibility/hours. Ordinary first branch;
  conversion copies legacy automatic offers/assignments/hours/exceptions/access and
  booking snapshots without reseeding data. Existing configured branches stay explicit.
- A service can require one available room from its branch pool. Existing mandatory
  equipment remains mandatory. Legacy mandatory rooms survive metadata edits; explicit
  pool configuration changes future requirements, never historical reservation snapshots.
- Versioned weekly schedules use effective_from; dated exceptions take precedence.
  Staff/room absences support create/edit/remove. Future appointments block conflicting
  schedule/absence/deactivation/archive/removal changes. Accounts/tasks remain unchanged.
- Room-related appointment filtering includes reserved resources, within the existing
  tenant/role queryset. Calendar links for services/staff/rooms/branches retain context.
- Writes use existing permissions/branch access, Business locks, audit/activity and
  transaction rollback. No new permission framework, provider action, notification or
  BusinessEvent type. AI/bot/manual booking share the same availability constraints.

## Verification and retained failures

Product verification used disposable databases and canonical source. The separately
authorized local activation is recorded below. No reset, external provider call,
dependency installation or deployment was performed.

| Boundary | Evidence/result |
| --- | --- |
| Backend slices | rooms/legacy booking, migration executor conversion, API/lifecycle and schedule versions verified incrementally; prior failures retained in checkpoint |
| API/staff/schedule/conversion | 20 PASS; test-1794423734981617900.log; system/drift PASS |
| Native PostgreSQL17 | 14 PASS, including two concurrent alternative-room bookings, last-room oversell, reservation/deactivation/reschedule races and schedule versions; postgres-concurrency.json/log; disposable cluster stopped |
| Affected/dependent suites | 102: 100 PASS, 1 PG-only skip, 1 ERROR; test-1794424093563295600.log. Error was changed voice batch-conflict exception type; corrected in product adapter |
| Voice dependent recheck | 40 PASS; test-1794424296879573300.log; system/drift PASS |
| Legacy room metadata guard | 13 PASS; test-1794424401466481200.log; system/drift PASS |
| Final Management API + resource booking | 31 PASS; test-1794424533744624900.log; includes physical-resource list filter and tenant boundary; system/drift PASS |
| Final branch-state/API check | 18 PASS; test-1794424749236086300.log; direct pause guard and unchanged visits, system/drift PASS |
| Node schedule/navigation | 14 PASS; effective-date boundary/override/history plus shared navigation |
| Browser initial | 4 PASS / 2 FAIL; browser-1794423914143787800.log. KK/EN test setup left localStorage language at RU; corrected fixture usage, not application translations |
| Browser KK/EN recheck | 2 PASS; browser-1794424216032753600.log |
| Browser lifecycle/draft | 1 PASS; browser-1794424599288892700.log; includes inactive unassigned draft visibility, activation/archive/restore/delete |
| Frontend completion | build-completion.log and bundle-completion.log PASS: app/widget, types, RU/KK/EN i18n, app-shell budget. Two locale chunk-size warnings retained; no budget failure |

Browser evidence: real isolated API and Chromium; CRUD, linked catalogs and reload,
503/save recovery, unsaved cancellation, schedule effective date, absence, manager
UI/API denial, all five pages at RU320/1440, KK390 and EN768; keyboard form focus.
Screenshots under each browser run were visually inspected. Browser evidence does
not replace database/concurrency checks. No real device, native mobile or live AI
certification is claimed for this scoped implementation.

Test-harness failures are retained: initial missing MANAGEMENT_FIXTURE was caused
by safe environment sanitation and fixed by retaining the output path before setup;
a wrong loader label was corrected; an old absence test expected conflicting future
visits to be accepted and now asserts refusal, unchanged visit and explicit cancellation
before adding absence. Earlier migration test state/loaded-model errors remain in logs.
No assertion was weakened to accept the unsafe behavior.

## Activation and rollback boundary

Intentional migrations: services0003 (requires_room), scheduling0014 (Resource archive),
branches0005 (alternative requirements), branches0006 (city + explicit catalog backfill),
branches0007 (effective schedule versions). Owner explicitly approved working local
activation with backup and checks in this chat on 12.11.2026.

Target verified: development PostgreSQL `127.0.0.1:55432/platformacrm`, application role
`crm_app`, canonical local profile. Snapshot-consistent custom pg_dump:
`output/management-implementation-20261111/pre-management-1794425168597813900.dump`;
1034706 bytes; SHA256 `2c5c8458db01f60f025f998bda027a6ce1d6321cffadd6a4467378beee2786ae`.
The backup contains working data, stays local/ignored and is not included in Git.

Restore verification: all154 tables/10212 rows matched. Exact-five migration rehearsal
on the restored DB passed; disposable restore DB removed. First rehearsal failed with
PostgreSQL pending trigger events while wrapping data+schema migration in one outer
transaction; working DB was untouched. Rehearsal retry set constraints IMMEDIATE before
migration, preserving FK enforcement and enabling one atomic checked working operation.

Working apply committed exactly those five migrations. Protected original columns/rows
of153 data tables preserved;10016→10161 rows reflects only reviewed explicit schedule/access
configuration.15 automatic branches converted; existing service eligibility checked;
appointment records/reservation snapshots unchanged. No pending migrations; system/drift PASS.
Receipts: backup-receipt.json, migration-result.json, activation-backup*.log,
activation-apply.log in the task output folder.

Six read-only real API views200 (Management, branches, services, resources, appointments,
branch configuration); health/frontend200 and unauthenticated API401. Canonical identity
of backend/frontend/import worker verified. Existing backend autoreloaded current source;
no unrelated process was stopped. Import worker was not restarted or newly certified.
Current authenticated Chrome session opened all five Management pages with real local data;
pre-migration cached error recovered through Retry. No working business entities were edited
by the browser check. Existing branch configuration gaps were displayed, not filled with demos.

Backfill reverse is intentionally non-destructive (retains explicit data). Do not
blindly reverse branches0007 after multiple effective versions exist: the former unique
constraints cannot represent them. Prefer restored verified backup or a reviewed forward
repair; code rollback must be assessed against the migrated schema and data.

## Scope remainder and publication

No scoped code/local-evidence/local-activation remainder. Push/deployment/production
remain distinct. 45 foreign outgoing commits prevent own-only
publication; no push or new CI is claimed. Own reviewed changes are committed locally. Contracts/frontend/scheduling passport/README
and roadmap are reconciled in this task; access/AI/product decisions outside this scope
remain unchanged. No unrelated roadmap or acceptance item is closed.
