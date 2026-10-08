# PRIMARY-SESSION — PlatformaCRM

## DOCS-ROADMAP-20261009 — production route and domain passports

Owner requested one production roadmap and substantive passports in the existing
pre-production directory, with all preserved acceptance IDs mapped to that route.
Docs-only implementation; gap type documentation/roadmap. Reuse current contracts,
two AI passports, source code and published scoped evidence; no new business policy,
product phase, runtime changes, migrations, provider calls or deployment.
Generation 4 primary remains unchanged. Primary explicitly released sequential
docs-writing to PlatformaCRM UI after Settings completion. Canonical root
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`, clean base
`768b2675f38f1f00a5273f627c3f184b91e6a015`; Settings CI 37832658462 success.
Acceptance: one route with dependencies/results/DoD/status/evidence, substantive
passports, complete acceptance mapping, registered navigation and no false readiness.
Risk: converting deferred policy into work or scoped PASS into production readiness.
Checks: source/contract consistency, links, JSON registry, acceptance ID coverage,
working/index/committed-range diff hygiene and complete intended-file review.
No application checks: code/config/dependency inputs unchanged. Finish with reviewed
docs commit, normal push to main, remote SHA and actual CI; return the writing lease.

Implementation: one `docs/current/roadmap.md` with seven result stages, dependencies,
DoD, scoped foundations and six deferred directions; all 36 preserved acceptance
IDs explicitly mapped, including historical closures and V1 policy boundaries.
Thirteen new domain passports plus the two retained AI passports cover fifteen
directions. Navigation, template, source map, project state and JSON registry updated.
Current contracts retain their meaning; no archive bodies or primary registry changed.
Legal placeholder bodies and commercial processing remain production boundaries.

Verification 09.10 on base `768b2675` + docs patch: standard-library Python check
via `.venv/Scripts/python.exe -` parsed the JSON registry (unique/existing paths),
checked every local Markdown target/heading anchor in changed/new documents and
compared the explicit 36-ID acceptance set with roadmap: PASS. Static review traced
passport claims to current contracts, services/routes and existing evidence; checked
all new files for unrelated/private material. `git diff --check` PASS. Index and
real committed-range checks run at publication. No app install/build/backend/browser
or live checks: docs-only; previous application evidence retains its original scope.
Published commit/remote readback and actual push-triggered CI are reported in the
task's final receipt and writing-lease return, without a self-referential commit SHA.
Final staged checker also proved both original AI bodies preserved. Its first
invocation incorrectly required the JSON index to register itself as a Markdown
document; that checker-only assertion was corrected and the full check passed
(26 docs/JSON files, 343 local links/anchors, 36 acceptance IDs).

## SETTINGS-FUNCTIONAL-20261008 — functional settings completion

Owner-authorized scope transferred by the read-only settings audit task after Inbox
completion: all ten existing settings sections, no cosmetic redesign/new navigation.
Generation 4 primary; canonical root and branch unchanged. Clean starting snapshot
`33b316d9cfdb44aab2601ddedbb9830f5fb6b4d4`. Mode: domain/API/frontend corrections and
source-backed evidence. Reuse existing settings, role permissions, tenant scoping,
notification scheduling/delivery, billing metadata, API clients and shared controls.
Trace each setting/action through UI, API, storage, runtime consumer, permission and
verification. Retain working controls; fix broken behavior; make reference-only
metadata honest; remove inert editing without deleting saved data. Cover business,
team, roles, security, appointment messages, personal notifications, quick replies,
billing, usage and custom fields. Preserve approved specialist/history semantics,
role presets, financial-source choices and provider/AI development boundaries.
No new billing provider, quotas, commercial policy, lifecycle/permission framework,
clinical behavior, schema or paid/external calls; no working-DB migration/seed/reset.
Risks: wrong-tenant reads/writes, partial permission changes, stale notification jobs,
misleading saved settings, hidden permission denial and stale form/cache state.
Checks: focused isolated backend tests after each coherent service/API correction,
before dependent UI; then affected/dependent suites, system/migration checks,
targeted reachable desktop/mobile and RU/KK/EN UI flows, final frontend build/types.
Use mocks for external delivery and disposable databases. No full local release
suite without demonstrated need. Record registry/evidence, review explicit paths,
normal-push verified change to main and inspect actual CI. Initial next step:
selected-business billing resolution and atomic role visibility changes.

Local completion 09.10: all ten sections are mapped in the registered
[settings evidence](../settings-functional-20261008.md). Selected-business queries,
atomic role scopes preserving grants, actual membership checks, security counters,
notification preferences and delivery readiness/reconciliation are corrected.
Reference-only settings preserve stored metadata without promising runtime behavior.
Custom definitions/values enforce tenant, entity access, role, types and retention;
card controls preserve typed arrays/booleans and untouched values. Forms retain drafts
and show real loading/error/recovery states. Appointment input overflow found during
visual inspection was corrected and verified at desktop/mobile widths.

Verification uses the existing dependencies and `scripts.codex_verify.isolated_runtime`
through the ignored helpers in `output/settings-functional-20261008/`. Commands:
`.venv/Scripts/python.exe output/settings-functional-20261008/verify_backend.py <labels>`;
logs below are relative to that directory. Evidence is reused only for unchanged inputs.
- `apps.billing.tests_settings_scope apps.billing.tests.BillingFoundationTests`:
  20 PASS, `backend-1791483108063750200.log` (selected business, denial, invalid
  metadata, audit rollback, current/monthly usage); unchanged since that run.
- `apps.businesses.tests_access.TeamAccessTests apps.businesses.tests_role_visibility
  apps.businesses.tests_settings_team`: 40 PASS,
  `backend-1791483005594091600.log`; `apps.businesses.tests_settings_team`: 4 PASS,
  `backend-1791483180228940500.log`.
- `apps.core.tests_security`: 13 PASS, `backend-1791483348303765700.log`.
- `apps.scheduling.tests_settings_delivery apps.notifications.tests`: 26 PASS,
  `backend-1791484223189422400.log`; `apps.notifications.tests_settings_preferences`: 4 PASS,
  `backend-1791484923598116500.log`.
- Broad affected run `apps.scheduling apps.notifications apps.billing
  apps.businesses.tests_access apps.businesses.tests_member_deactivation
  apps.businesses.tests_role_visibility apps.businesses.tests_settings_team
  apps.core.tests_security apps.core.tests_custom_fields
  apps.conversations.tests_quick_replies`: 200/202 passed,
  `backend-1791485572718350100.log`. Two legacy Telegram fixtures had client IDs
  but no ready channel; fixtures were completed with enabled/active synthetic
  transport, without weakening channel expectations. `apps.scheduling.tests`:
  49 PASS, `backend-1791485937050184400.log`.
- Later queue-lock + extended-field run `apps.scheduling.tests_settings_delivery
  apps.scheduling.tests apps.notifications apps.core.tests_custom_fields`:
  99/100 passed, `backend-1791486206843899800.log`; the new reschedule test needed
  a staff Resource under the existing booking contract. Fixture corrected.
- Final `apps.scheduling.tests_settings_delivery apps.businesses.tests_role_visibility
  apps.businesses.tests_settings_team apps.core.tests_api_contracts`: 25 PASS,
  `backend-1791486447962966600.log`, covering final lock changes and corrected
  reschedule/cancel fixture. Earlier failed runs are not labelled whole-suite PASS.
- Final `apps.core.tests_custom_fields apps.core.tests_crm_projection_access`:
  41 PASS, `backend-1791487029812351200.log`, including invalid calendar dates,
  explicit business selectors, scope/role denial, typed data and audit rollback.

Browser command:
`.venv/Scripts/python.exe output/settings-functional-20261008/verify_ui.py <project> settings-functional.spec.ts [--grep ...]`.
Eleven distinct scenarios are verified on desktop and mobile, using real local APIs,
disposable fixtures and injected 503 only for recovery. RU/KK/EN all ten sections,
profile persistence/invalid timezone, appointment drafts, preference load recovery,
custom definition/card/deactivate, billing metadata/plan preference, atomic visibility,
quick reply to Inbox draft, and manual invitation/revoke/department/login toggle.
- Desktop profile passed in `browser-1791486217224581800.log`; preferences passed
  in `browser-1791486508651367200.log`. Those runs subsequently stopped on unrelated
  test-selector errors, retained in the logs. Corrected appointment/card tests passed
  later; the failures are not product acceptance exceptions.
- Desktop billing/role/quick-reply/team: 4 PASS, `browser-1791486967464559000.log`.
- Final desktop locales/appointment/custom fields: 5 PASS,
  `browser-1791487275581052600.log`, including edit-role picker, required metadata
  read-only state and label edit retaining object-based choice labels.
- Mobile complete run: 11 PASS, `browser-1791487071203693200.log`; final extended
  custom-field flow: 1 PASS, `browser-1791487365894026900.log`.
- Custom-card checkbox selector was scoped to its field group so retained fields
  from a previous run do not collide. Desktop `--grep 'custom definition'
  --repeat-each=2`: 2 PASS, `browser-1791487662533786100.log` on the same disposable DB.
- Harness fixes used the actual client drawer route, localized MiB label and the
  Select's accessible name including its selected value. Initial raw-key assertion
  matched concatenated English prose; narrowed to actual leaf text. No required
  behavior/assertion was removed. Reviewed screenshots include desktop business,
  appointment cards and mobile RU appointment/KK custom fields; final desktop
  RU/KK/EN screenshots are in the last desktop run.

`.venv/Scripts/python.exe output/settings-functional-20261008/verify_frontend.py`:
`npm run build` (i18n, TypeScript, app, widget) and `npm run check:bundle` PASS,
`frontend-isolated-final.log`. Isolated `manage.py check` and
`manage.py makemigrations --check --dry-run` passed 08.10 19:12 UTC; later field
value validation did not change models/configuration. No schema changes detected.
Full local release/E2E gate skipped under proportional affected-scope verification.
SQLite and mocks do not certify PostgreSQL lock contention or live provider delivery.
No working-DB writes/migrations, dependency installs, external messages, payments,
paid AI calls, notification categories, BusinessEvents or new permission framework.
An already-started provider request cannot be recalled; a revoked claim stays revoked.

Working diff, 57 intended changed/new paths, Markdown links, registry JSON and
credential-shaped-content review PASS. Publication uses a conventional Settings
commit and normal push to main; exact commit/remote readback and actual CI receipt
are reported in the task completion message. Base Inbox commit `33b316d9` CI
completed successfully (run `37819153554`). Fetch/readback
confirmed actual remote main still equals that base; the limited local fetch refspec
required explicitly refreshing `refs/remotes/origin/main`. No conflicting writer.
The separate docs architecture task `01a0f32f-7d02-7263-a53d-496c8f9787f5` remains
read-only while Settings verification/publication completes; no write lease yet.

## INBOX-RELINK-20261008 — confirmed client replacement

Owner approved and requested implementation of the described confirmation dialog.
Mode mixed domain/UI implementation; closes the client-replacement policy gap only.
Generation 4 primary, canonical root/branch unchanged; clean base
`101f0df8e172ac2484f17dc96d683a0a0636092e`. Reuse link-client endpoint, scoped access,
activity/audit helpers, existing dialog, API client and locale dictionaries.
Result: selecting a different client previews incompatible lead/deal links; explicit
confirmation atomically changes client and detaches only those links. Entities,
their ownership/history, messages, appointments and tasks remain intact. Same client
is a no-op; no conflicts means immediate linking. Hidden entities have no exposed
identity. Signed confirmation binds actor/target/current relation snapshot; changed
relations require refreshed confirmation. Server repeats tenant/role checks.
No lifecycle/permission framework, provider/AI policy, notification, BusinessEvent,
schema/dependency/environment changes; no working-DB mutations or paid/external calls.
Activity/audit record the replacement. Risk: stale confirmation, partial writes,
privacy leaks and unintended deletion. Focused isolated backend regressions first:
preview/no-op/compatible/confirmed, tenant/role denial, stale/forged token, rollback,
preserved history and retry. Then affected Inbox suites, system/migration checks,
desktop/mobile reachable confirmation/cancel/recovery, RU/KK/EN and final build.
No full local release suite. Update current contracts/evidence and publish verified
explicit paths via normal push; read remote SHA and actual CI.

Implementation: `client_linking.py` reuses link-client with a typed 200 preview or
the existing conversation result. Signed opaque digest expires after 10 minutes;
hidden child identities are absent from both preview and decoded token. Same-client
retries write no duplicate activity/audit. Transaction locks cover replacement and
the existing link-lead/link-deal/create-client actions so stale loaded objects cannot
restore a previous client. The old CRM qualification preview is invalidated while
other metadata/history remains. No provider/model behavior was developed.

Backend receipts (`output/inbox-relink-20261008/`, `.venv/Scripts/python.exe`):
- `verify_backend.py apps.conversations.tests_client_linking.ClientLinkingTests`
  — 11 PASS, `backend-1791480529448373200.log`, before dependent UI work.
- Initial dependent set — 47 PASS, `backend-1791480763213079200.log`.
- Approval invalidation/actor/client access regressions + AI confirmation — 25 PASS,
  `backend-1791480880137201100.log` (intermediate; final below supersedes it).
- Final `verify_backend.py apps.conversations.tests_client_linking.ClientLinkingTests apps.conversations.tests_ai_confirmation apps.conversations.tests_inbox_context apps.conversations.tests_inbox_tasks apps.bots.tests.InboxBackendTests`
  — 88 PASS, `backend-1791480964102981000.log`, including 15 replacement regressions.
  Mocks, disposable SQLite, no working DB/provider calls. Stale-write/approval,
  replay and rollback tested; live PostgreSQL lock contention is not certified.

Browser: desktop RU/KK/EN confirmed replacement, cancel, refreshed concurrent-link
preview, injected 503 recovery, retained records/messages/draft and keyboard focus
PASS (`browser-1791481158604242100.log`, 3 cases); RU screenshot visually inspected.
Earlier failures retained: initial fixture did not confirm its own setup replacement
(`browser-1791480734868264000.log`); repeated locale fixture names caused ambiguous
locator (`browser-1791480945620263900.log`, RU flow passed); after unique names, one
expected-text assertion still used the old names (`browser-1791481040864274900.log`).
Fixture/assertion corrections did not weaken the runtime requirements.
Mobile same spec — 3 PASS (`browser-1791481229203134600.log`); RU screenshot
visually inspected, no overflow. Isolated `manage.py check` and
`makemigrations --check --dry-run` PASS (`system-migration.log`).
`verify_ui.py desktop-chromium inbox-inspector.spec.ts` — 11 PASS
(`browser-1791481329224830600.log`); two existing setup steps now explicitly confirm
their fixture relinking. Combined 17 browser cases for this change. New flow commands:
`verify_ui.py desktop-chromium inbox-client-relink.spec.ts` and
`verify_ui.py mobile-chromium inbox-client-relink.spec.ts`.
`verify_frontend.py` — i18n, TypeScript, app/widget build and bundle budgets PASS
(`frontend-isolated-final.log`). Existing dependencies reused. No full-project local
suite, live provider, production DB/migration or real PostgreSQL contention test:
scoped local change with disposable fixtures. Owner's running servers/data untouched.
Changed-source/new-file/secret review, docs links and working/index diff hygiene
reviewed for publication. Normal commit/push HEAD:main, actual range hygiene,
remote SHA and CI receipt recorded in `output/inbox-relink-20261008/publication.json`
and final response; CI pending is not green. No next phase is authorized.
Prior manual-task commit 101f0df CI 37815619846 is now confirmed SUCCESS.

## INBOX-MANUAL-20261008 — operator workflow acceptance

Owner explicitly requests manual Inbox review including inspector context/actions,
correct entity links, client/lead/deal/task/appointment creation and management,
and an efficient operator workflow. Mode manual verification + repair of reproduced
in-scope defects; not a new workflow engine or permission policy. Same registered
primary/root/branch; clean base ccee758e4f015a97b3cce43e38ac4db823d7d3a2.
Reuse current Inbox/API/domain services and existing acceptance evidence. Verify
live local owner session Business 2, with a backed-up, separate identifiable QA
conversation batch; preserve user's active demo conversations/drafts. No resets,
working migrations, real external recipients or paid model calls. AI/transport
behavior can use isolated provider fixtures and must be reported as such.
Manual matrix: empty/partial/full inspector, create/link/change client/lead/deal,
appointment prefill/save/navigation, task creation, exact links/Back/draft, queue
filters/unread/assignment/priority/bulk, close/reopen, bot readiness, templates,
delivery failure/retry and CRM preview/confirmation. Existing lifecycle/tenant/role
contracts are acceptance; UI alone cannot prove backend security or concurrency.
Risk/check plan: confirm local source roots/DB/business, backup before QA writes,
trace each mutation through normal services. For backend fixes run focused isolated
regressions before dependent work, then affected/system/drift; frontend fixes need
targeted interactions/responsive/manual evidence and one final build. No full-project
suite absent demonstrated impact. Record exact PASS/FAIL/blocked boundaries; persist
results and publish any verified code/docs under standing authorization.

08.10 manual result (publication pending): real local Chrome owner session,
canonical backend :8000 and frontend :5173; dedicated conversations 5/6 in Business 2.
Backup `output/inbox-manual-20261008/before.sqlite3` passed integrity_check;
bootstrap/manifest in the same ignored evidence directory. Existing conversations
1–4 and the owner's active browser tab were not edited by the test sequence.
Created through UI: client152, lead89, deal71, task62, appointment86. Both QA
conversations link to the same QA client/lead/deal. Appointment confirmed, lead/task
taken into work; source website preserved while saving synthetic email/notes.
No external delivery, paid model call, reset or working-DB migration was performed.

Manual PASS: empty → client → lead/deal → appointment/task; existing relation
pickers; exact entity routes and reverse links; appointment confirmation and task/
lead lifecycle action; client edit reflected in inspector; draft across navigation,
reload, filtering and close/reopen; assignment/priority; bot resume correctly
rejected without channel; empty quick-reply state; filtered empty/reset; selected
two-QA-only bulk mark-read. AI draft/delivery retry/CRM preview confirmation and
permission/error recovery are separately verified with isolated provider fixtures,
not asserted as real-channel manual delivery.

Reproduced/repaired frontend defects: direct entry did not mark the opened thread
read (now once per visible selection, preserving explicit unread through polling);
booking shortcut disappeared when appointments existed; task/lead prefill used
the last system/outbound event instead of latest loaded inbound customer text;
all historical messages were labelled today (now date groups and times use business
timezone); task metrics/CRM quick actions/won status/priority summary leaked raw
translation keys or IDs; shared ClientForm source selector displayed manual for
website clients (controlled by existing form state); no-match filter looked like
an entirely empty Inbox. No new API, lifecycle, permission or model contract.

Open policy found by code review: link-client changes only conversation.client;
existing lead/deal links may belong to another client in the same Business.
Owner asked for explanation and recommendation, not yet selected a rule. Current
recommendation: explicit confirmation to detach incompatible links while preserving
the original entities/history, then link the new client's work. This is a proposal,
not approved behavior; no backend relinking changes made. Other limits observed:
resume denial gives generic validation copy; system activity text still comes from
existing English backend events; no dedicated history search/outgoing attachment
composer. These are not represented as fixed or as live-provider readiness.

Verification receipts under `output/inbox-manual-20261008/` using isolated_runtime,
existing dependencies, disposable DB/ports and mocked external providers:
- `verify_ui.py desktop-chromium inbox-inspector.spec.ts` — 11 PASS,
  `browser-1791478911166096000.log`, including AI/delivery/approval/error/permission
  cases, real CRM routes, booking with existing visits, source edit, dates and tasks.
- `verify_ui.py mobile-chromium inbox-inspector.spec.ts --grep 'real client|message date|direct entry|reopened conversation|context errors'`
  — first three PASS in `browser-1791479073627894200.log`; task check failed because
  its locator selected the hidden list preview rather than thread event. Corrected
  selector; `--grep 'reopened conversation|context errors'` — 2 PASS,
  `browser-1791479255733373000.log`. Mobile RU screenshot visually inspected.
- Initial desktop focused run: 2 PASS, task check selected datetime instead of
  description. Label selector corrected; focused task rerun PASS
  `browser-1791478530961526400.log`, then full 11-case scoped run above passed.
- Final direct-entry regression rerun PASS `browser-1791479413216119100.log`.
- Build first caught optional unread_count TS error; null-safe guard added.
  `verify_frontend.py` (npm build: i18n/types/app/widget + check:bundle) then PASS;
  final repeat after one read-selection deduplication line PASS, exit 0,
  `frontend-isolated-final.log`; no new dependency installation.
Backend/system/migration/full-project/live-provider gates not run: frontend-only
change, no migration/infra/AI policy change; scoped checks do not certify them.
Next: diff/docs/secret review, normal commit/push/main readback
and actual CI. Keep relinking decision open unless owner explicitly selects it.

## INBOX-DENSITY-20261008 — active Inbox layout and operator review

Owner requests equal container gutters and analysis/improvement of bulky rows,
crowded thread controls/composer and undifferentiated inspector information.
Mode frontend implementation + bounded UX review, same canonical owner/root/branch;
clean base b3959e99e9cc75223bbf14362fafb61490740c9c. Read current frontend and
verification contracts; reuse shared layout/buttons/menu and existing actions/i18n.
Live Chrome 1536x639 CSS viewport: container x88/y64/w1424/h535.2, app header
height56.8/sidebar64: top7.2, sides24, bottom39.8. Root causes: max-width/negative
margins, unrelated fixed104px height offset, ungrouped controls. Change only Inbox
route layout, list density, thread action grouping, composer and inspector sections.
Keep permissions/API/drafts/confirmations/retry identities and all existing actions.
No backend/AI policy changes, new messages/provider calls or working-data mutations.
Risk: shared AppLayout route branch, relocated memory action and responsive overflow.
Checks: affected existing isolated inspector desktop/mobile critical flows, memory
confirmation cancel/permission visibility, keyboard/long RU/KK/EN and live geometry;
empty Inbox and one non-Inbox layout representative. One final isolated build/types/
i18n/bundle and diff/docs review. No full-project or backend gate for unchanged APIs.
Review findings must distinguish reproduced UI issues from unproven product gaps.

Implemented: route-scoped 16px gutters with dvh and mobile nav/safe-area clearance;
removed negative margins and fixed104px offset. Rows now 68.8px in owner's browser
(about88px in supplied original screenshot); smaller avatar, quiet status metadata,
unread badge separated from avatar. Priority links remain reachable as compact rows.
Thread identity/context and working actions are grouped separately; memory reset and
AI usage moved into the existing menu. Confirmation, role checks, pending/error/success
feedback retained; exhaustion/handoff warnings remain inline. Composer tools grouped,
RU/KK/EN quick-reply label clarified, editor gets an accessible name. Message retry
remains at the same message with compact status/attempt/action placement. Inspector
uses separate flat sections/icons/dividers and clear link arrows. Removed floating
today marker overlap, but did not change its pre-existing date semantics.
Row keyboard activation prevents Space scrolling and nested bulk-selection events
from also opening the conversation. No shared ActionMenu behavior changed.

Verification on canonical dirty snapshot, helpers under ignored
`output/inbox-density-20261008/`, isolated DB/ports and existing dependencies:

- `.venv/Scripts/python.exe output/inbox-density-20261008/verify_ui.py desktop-chromium inbox-inspector.spec.ts --grep 'real client|AI inserts|CRM menu'`
  — 3 PASS, `browser-1791476572189000600.log`: actual four-entity links/Back/draft,
  RU/KK/EN, editable AI insertion without send, retry identity, granular CRM approval.
- Same helper `mobile-chromium inbox-inspector.spec.ts --grep 'thread menu|real client|AI inserts|CRM menu|switching conversations'`
  — 5 PASS, `browser-1791476734384221300.log`: mobile equivalents plus switching/
  late-send drafts and new memory-menu regression (cancel sends no request, confirm
  sends once, persisted message history and unsent draft retained).
- Same helper `desktop-chromium ui-operations.spec.ts --grep 'Inbox channel|deals show'`
  — 3 PASS, `browser-1791476882861581600.log`: empty Inbox/filter/CTA/restricted user
  and non-Inbox Deal layout representative for shared AppLayout's route branch.
- Same helper `desktop-chromium inbox-inspector.spec.ts --grep 'thread menu|context handles'`
  — 1 PASS, `browser-1791477001940939000.log`. Only the memory-menu test matched;
  the `context handles` alternative matches no test and is not claimed as coverage.
- `node --test frontend/scripts/tests/inbox-delivery-policy.test.mjs` — 2 PASS.
- `.venv/Scripts/python.exe output/inbox-density-20261008/verify_frontend.py` — one
  final isolated build/types/i18n/app/widget + bundle PASS, `frontend-isolated-final.log`.
  No dependency reinstall, API/schema changes, backend/full E2E or live-provider run.
- Live Chrome, actual current test data: desktop 1536x639 CSS viewport, gutters
  left/right16, top16.2, bottom15.8, no horizontal overflow; row68.8, typical thread
  header109.3. Mobile viewport394x851: left16/right16.4, top16.2, gap to bottom nav16.4;
  editor bottom739.6 before nav top777.6, no overlap/overflow. Temporary viewport
  reset, user's current conversation/filter preserved. Desktop and mobile screenshots
  reviewed, including KK. HMR briefly invalidated I18nProvider during dictionary edit;
  normal reload recovered, isolated fresh loads passed, no app failure persisted.

Bounded review findings, not authorization for another phase:

- Supplied/live Alina reply says no appointment information while inspector displays
  an appointment. `apps/bots/ai.py` intentionally builds customer-safe reply context
  rather than passing the inspector projection. Investigate controlled appointment
  grounding separately with client identity/permissions; do not expose private CRM
  fields to a public agent merely to improve the reply.
- Composer supports text, templates and editable AI draft; MessageBubble displays
  incoming attachments, but there is no outgoing upload control in this flow.
- Conversation filters accept `search`, but this page currently installs only a title
  in setPageHeader; there is no dedicated history-search control. Global CRM search
  is not a search within this thread. Useful follow-up for longer conversations.
- Static date marker still says today regardless of historical messages. Also
  markRead is called by selectConversation; direct URL entry does not use that path.
  Owner's direct-entry conversation remained unread. These are existing correctness
  follow-ups, not fixed by density changes or claimed covered by the above checks.
- Demo delivery failures are expected: the dedicated synthetic bot has no channel;
  no delivery-readiness conclusion can be drawn from these test conversations.

Final reviewed diff, commit/push/readback and actual CI in local publication receipt
and final response. No working-DB edits or paid model/provider calls by this task.

## INBOX-DEMO-20261008 — owner-requested local inspector examples

Mode operation, environment gap: owner explicitly requests test conversations in
the currently signed-in local Inbox. Browser confirms business_owner@example.com;
Business 2 (Zani E2E Demo), user 2, empty Inbox. Canonical backend/frontend roots
verified for ports 8000/5173; local SQLite, branch codex/ui-testing-toolkit,
clean starting HEAD 951c8e806125fe28feb7b174b744d362533a4e2a, same primary writer.
Create one identifiable additive demo batch, with backup and atomic rollback:
linked client/deal/lead/task/appointment, multiple appointments, and unlinked visitor.
Reuse existing CRM API/services; fixture conversations/messages have no external
channel or delivery queue. No resets, migrations, permissions or paid AI calls.
Risk/checks: assert exact local DB/business/owner and no active automation; verify
entity relations and context projection, then visible live-browser inspector.
Completion: persist manifest/evidence, docs diff hygiene and normal publication.
No app build/test suite needed for a data-only operation with unchanged product code.

Completed: additive batch `inbox-demo-20261008`, conversations 1–4, three new
clients, three leads, one deal, one task and appointments 83–85. Dedicated paused
demo bot 13 has no channels; all conversations have bot_enabled=False, synthetic
messages have no queued/retrying outbox. Existing data/settings preserved.
`manage.py shell -c "exec(open('output/inbox-demo-20261008/seed.py', encoding='utf-8').read())"`
PASS: existing authorized APIs/services create CRM links and validate available
appointment slots. Context reads for all four scenarios PASS: full context with
conversation appointment provenance, two client appointments, lead-only client,
and unlinked visitor. Backup SQLite integrity_check PASS before writes; batch
created atomically. Ignored local `output/inbox-demo-20261008/` contains seed script,
`before.sqlite3` backup and `manifest.json`; no DB or messages committed to Git.
Chrome at `http://127.0.0.1:5173/app/conversations/1` verified actual four-item list,
client/note/email, tomorrow's appointment/service/specialist, 15000 KZT deal,
lead and next task with exact links; left open for owner. No server restart needed.
Data-only operation: no product-code changes, migrations, builds or provider tests.
Final docs/index/committed diff and publication recorded in local receipt.

## INBOX-INSPECTOR-20261008 — approved customer context and action placement

Mode implementation, code/UX gap. Owner approved inspector reference and explicitly
requested implementation; scope relayed by PlatformaCRM UI task
`01a0f32f-7d02-7263-a53d-496c8f9787f5`. Same generation 4 primary, canonical root
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`; clean base
`d76b5101d2c183fcbb2b863332611d9c740c6a83`. No parallel writer or source copy.
Approved change from prior Inbox rollback: selected conversation's compact
customer inspector only, with scoped client/contact/note, honestly attributed
upcoming appointment(s), deal/lead links and compact link/book actions. Preserve
empty three-column Inbox, sidebar, conversation list/filter and thread design.
Move existing delivery retry to message, AI draft/quick replies to composer,
priority/unread/task/CRM preview actions to menus/dialogs; retain all existing
domain services, granular approvals, safety, permissions and draft behavior.
Reuse API layer, shared overlays/buttons/menus, semantic tokens and RU/KK/EN.
Mobile opens the same customer context from thread header with focus restoration.

Risk/check plan: linked entity permission is independent of conversation access;
if a backend projection is needed, prove same Business, resource/object scope,
masked/hidden children, appointment time/status/multiple results in isolated
focused tests before UI consumption. Validate deep links, booking prefill,
draft preservation, denied/error/loading recovery, AI insertion without send,
message retry identity, CRM confirmation and selected/unlinked/partial context
on desktop/mobile/keyboard/locales. Finish affected/dependent backend suites and
system/drift checks if backend changes; targeted frontend tests/browser flows and
one isolated build/types/i18n/bundle. No full E2E absent demonstrated broad risk.
No working DB reset/seed/migrations, external sends/sync, paid AI, new models or
permissions framework. No development of CRM AI. Update evidence/current docs,
review owned diff, conventional commit, normal push origin HEAD:main and actual
remote SHA/CI.

Implementation: scoped read-only context and link search implemented;
conversation list masks inaccessible related IDs/names through batched child
authorization. No schema/write-service changes. The 320px inspector and mobile
drawer reuse existing tokens/overlays; exact entity routes, future appointments,
client booking prefill, menus, composer AI insertion and per-message retry wired.
Draft storage is scoped by user/business/conversation and persists before navigation;
the prior business/conversation session key is consumed once for upgrade continuity.
Late send/AI responses cannot overwrite another conversation's draft. Delivery retry
retains its request key after an uncertain failure and targets the same message.
The shared ActionMenu has an opt-in drawer/modal layer; default callers retain their
layer. Mobile inspection reproduced a menu below the drawer; this was fixed and
pointer/keyboard/Escape/focus retested. The obsolete inert attachment button was
removed while moving quick replies into the composer toolbar; no upload flow changed.

Verification (canonical dirty snapshot on the base above; isolated_runtime, fresh
temporary DB/ports/uploads, no dependency installation):

- `.venv/Scripts/python.exe output/inbox-inspector-20261008/verify_backend.py apps.conversations`
  — 42 PASS, including 15 context/picker/batching tests; system/drift PASS.
  Log `backend-1791452097344056200.log`.
- Same helper with `apps.bots.tests.InboxBackendTests apps.bots.tests_customer_safety apps.bots.tests_safety_state apps.bots.tests_safety_recovery apps.core.tests_b5_performance.BackendPerformanceRegressionTests.test_inbox_list_query_count_does_not_scale_with_conversations_or_messages apps.core.tests_workspace_related_filters.WorkspaceRelatedFilterContractTests.test_workspace_inbox_filters_are_relation_and_tenant_scoped`
  — 67 PASS, system/drift PASS; log `backend-1791452432247817500.log`.
  Together 109 distinct backend tests, with resource denial, OWN/tenant boundaries,
  capability/field masking, time/status/provenance/multiple appointments, task scope,
  bounded list queries, existing writes, delivery and AI confirmation/safety.
- `verify_ui.py desktop-chromium inbox-inspector.spec.ts` first three scenarios:
  3 PASS (`browser-1791451971663822800.log`); mobile same first three: 3 PASS
  (`browser-1791452180227713300.log`, later booking selector failed separately).
  Existing entity pages were opened and browser Back retained the draft; RU/KK/EN,
  desktop/mobile screenshots, no overflow, panel error recovery/denial, AI insertion
  without send and retry identity checked. Synthetic AI/delivery/error boundaries
  were mocked; entity links/context/appointment data used actual isolated APIs.
- `verify_ui.py mobile-chromium inbox-inspector.spec.ts --grep 'booking shortcut|CRM menu|switching conversations'`:
  booking/menu 1 PASS after the layer fix (`browser-1791452823177317600.log`);
  CRM teardown route-fetch race then corrected by awaiting in-flight routes.
  `--grep 'CRM menu|switching conversations'` mobile 2 PASS
  (`browser-1791452948177369900.log`); the three-scenario desktop run 3 PASS
  (`browser-1791452958951576100.log`). Proves booking client prefill, failed picker
  recovery, exact granular confirmation, legacy draft upgrade, switching and late send.
- `verify_ui.py mobile-chromium inbox-inspector.spec.ts --grep 'unlinked inspector'`
  — 1 PASS (`browser-1791453575400692600.log`): single client CTA/create option,
  missing links and real scoped existing-client link. Initial unlinked projection
  is a controlled fixture; the resulting link/context are actual isolated APIs.
- `verify_ui.py desktop-chromium ui-operations.spec.ts --grep 'Inbox channel'`
  — 2 PASS (`browser-1791453162634715700.log`), preserving empty layout/filter/CTA
  behavior and restricted access. Overall 15 distinct browser project/scenarios.
- `node --test scripts/tests/inbox-delivery-policy.test.mjs` from frontend — 2 PASS.
- `.venv/Scripts/python.exe output/inbox-inspector-20261008/verify_frontend.py`
  — one final isolated `npm run build` (i18n/types/app/widget) and `npm run check:bundle`
  PASS, `frontend-isolated-final.log`; no JS chunk >500kB, shell <400kB.

All helper/log paths above are under ignored `output/inbox-inspector-20261008/`.
Earlier failed fixture setup (unique email/Django client shadowing), picker `q`
colliding with parent conversation search (changed to `term`), cold/warm capability
cache measurement, dropdown selector names and initial reload selector race remain
in evidence. Final applicable reruns passed; no failed gate is being counted green.
No migrations/schema changes, working-DB seed/reset, external messages, paid AI or
new permission/notification/BusinessEvent/write policy. Full project E2E/live provider
certification skipped: bounded inspector/action placement scope. No new phase.
Final diff/docs checks and publication SHA/remote readback/actual CI are recorded in
the final response and local publication receipt; this is not deployed acceptance.

## INTEGRATIONS-REVIEW-20261008 — functional audit and redesign reference

Owner request: full functional analysis of /integrations, redesign proposal based
on the existing application design system, and a generated reference. Mode audit/
design proposal, not implementation or activation of external integrations.
Same registered primary/canonical root/branch; clean base
`4ed44964f373a43ce195898c02d5f912edccf6ac`. Inspect the canonical /app/integrations
route, reachable five-provider catalog, setup/import flows, API/services/permissions,
states and tests. Distinguish static implementation, isolated reproduced behavior,
historical evidence and live provider readiness. Use neutral/emerald tokens,
Manrope typography and current flat sidebar. Reference uses explicitly labelled
example states; no invented production metrics or implied provider availability.
Checks: targeted isolated browser walkthrough/screenshots and representative
error/permission states with mocked external boundaries; source evidence and
proposal/reference visual+interaction QA; docs/diff hygiene. No code fixes,
new providers, live sends/sync, working-DB writes/migrations, app dependency installs
or broad certification/build for a proposal. Record findings and a bounded
implementation recommendation; do not start implementation automatically.

Result: [full report](../integrations-functional-review-20261008.md) records the
five-provider inventory, reproducible generic-config 400/hidden modal error,
needs_attention filter omission, partial-failure misleading metrics, ignored
deep-link and static business-scope/request-state/monitoring risks. No product
fixes or new provider scope. First isolated audit: 2 PASS; operator locator
failed (wrong test-id, correct product denial). Corrected audit locator then
owner/operator desktop/mobile 4 PASS. Commands/logs/boundaries in report.
Interactive reference uses existing semantic colors, type, flat rail, service
rows and contextual setup/import panel. Reference QA desktop/390/320px,
validation, mock import, search/reset and Escape PASS after replacing QA
textbox locator with native searchbox. No application rebuild/backend full
suite: application inputs unchanged; scoped audit only. No working DB or
external sends. Docs validator PASS: 56 active documents, 370 local links,
14 anchors, 38 plain paths, 198 archived bodies intact; working diff hygiene
PASS. Publication SHA/actual CI are recorded in final response/local receipt.

## SIDEBAR-FLAT-NAV-20261008 — owner-requested navigation simplification

Mode targeted UI implementation. Owner requests removing Channels/Control
group containers and showing their contents as independent sidebar entries.
Reuse existing Integration, Analytics and Timeline links, icons, active states,
permission filters and mobile drawer. Same primary/root/branch; clean base
`73582953ec50f20112b4caf5dbbe62095edf4948`. Scope Sidebar navigation configuration
and evidence; no routes, permissions, backend, notifications, BusinessEvent, AI,
migrations or environment changes. Risk navigation visibility/reachability.
Checks: affected desktop collapsed/expanded + mobile drawer, keyboard navigation,
representative allowed/restricted roles; one isolated frontend build/types/i18n/
bundle and diff/docs consistency. No full E2E/backend suite. Normal commit/push
and remote SHA/actual CI readback after scoped PASS.

Implementation: only the two sidebar configuration arrays were flattened. The
three original links/icons/permission resources and their order are preserved;
top-level active states, keyboard navigation and mobile close-on-navigation are
reused. Visible RU names remain «Подключения», «Аналитика», «История».
Checks: `node --test scripts/tests/sidebar-navigation-policy.test.mjs` in
frontend — 7 PASS. `.venv/Scripts/python.exe output/sidebar-flat-nav-20261008/verify_frontend.py`
— isolated build/types/i18n/widget/bundle PASS.
`.venv/Scripts/python.exe output/ui-operations-20261008/verify_ui.py desktop-chromium ui-operations.spec.ts --grep "sidebar standalone" --project=mobile-chromium`
— 4 PASS (owner/operator desktop/mobile), log `browser-1791443167223872900.log`.
Owner's three direct keyboard routes and mobile drawer closing verified;
operator cannot see the restricted links. Desktop collapsed/expanded and mobile
screenshots inspected. Original expanded screenshot caught a width transition;
capture now disables animations. Focused desktop owner recheck (`--grep
"sidebar standalone navigation respects owner"` without mobile project) 1 PASS,
`browser-1791443292272058700.log`; completed expansion visually checked.
Docs validator — 55 documents/363 links/14 anchors/38 paths, 198 archived
sources intact PASS. No backend/full E2E: navigation configuration only.
No dependency install, working-DB changes or external provider calls.
Task complete locally; reviewed working/index/committed diff, normal push and
remote SHA readback recorded with actual CI in final response/local receipt.

## INBOX-EMPTY-FILTERS-20261008 — targeted owner refinements

Follow-up during publication: owner requests channel-neutral empty-state copy:
«Новые обращения с подключённых каналов появятся здесь автоматически»; keep the
title. Base `aa323fae7231313efd3a05bda149467b02936553` already normal-pushed and
remote read back. Scope only RU/KK/EN emptyText translations and this evidence;
reuse passed interaction/permission checks. Risk copy/layout only. Check affected
desktop/mobile empty view, i18n/build and diff hygiene; no backend/full E2E.
Follow-up result: RU/KK/EN copy changed, title unchanged. Same isolated build
command rerun after translations: PASS. Browser command above with grep
`"Inbox channel shortcut and"` and both `--project=desktop-chromium` /
`--project=mobile-chromium`: 2 PASS; log `browser-1791440356262436900.log` in
UI-OPERATIONS output. New desktop/mobile empty screenshots inspected; text fits.
Original UI commit CI `37736805660` was in progress at readback. Follow-up
commit/normal push/remote SHA and current CI recorded in final response/receipt.

Owner requests after rollback: remove the list empty-state card border, align
three empty panels, move connect-channel CTA into the empty thread and open the
customer agent Channels section, widen the two quick-filter menus and hide their
scrollbar while retaining scrolling/keyboard access. Mode implementation; UI/code
gap. Same primary, canonical root and branch; clean base `3c2182ea7bd569c1f6afc7b53d50e9384b0fb1ed`.
Reuse Inbox panes, existing channel route, i18n, Select and no-scrollbar utility.
No redesign of populated Inbox, backend/AI/permissions/notifications/BusinessEvent,
migrations, environment changes or external calls. Risk: menu clipping, keyboard
access, mobile CTA reachability and wrong agent/permission routing.
Checks: affected empty/filtered/populated Inbox, direct channel navigation,
restricted-role absence, desktop/mobile + RU/KK/EN visual and keyboard inspection;
representative default Select consumer, one isolated build/types/i18n/bundle,
docs/link consistency and working/index/committed diff hygiene. No broad E2E or
backend suite for unchanged services. Explicit reviewed commit/normal-push and
remote SHA/actual CI readback complete this bounded task.

Result: implementation/local acceptance PASS. List empty headline, thread CTA
and CRM empty message share the pane centre; list card framing removed. Three
columns fit 1280px without clipping the inspector. Existing filled panels remain.
Channels shortcut targets the first customer (non-CRM) agent of the active
business; no-agent fallback is the existing agent workspace. Only authorized
roles see it; mobile empty list retains the reachable action. Expanded Select is
opt-in for two quick filters, with full option labels, hidden scrollbar and
keyboard active-option scrolling; default advanced-filter Select also checked.

Checks (isolated disposable fixtures, no paid/external calls):
- `.venv/Scripts/python.exe output/ui-operations-20261008/verify_ui.py desktop-chromium ui-operations.spec.ts --grep "Inbox channel"`
  — 1 PASS, `browser-1791439955650005400.log`.
- Same command with `mobile-chromium` — 2 PASS (flow + restricted operator),
  `browser-1791440036828560700.log`. Direct Channels navigation by keyboard,
  queue/owner selection, Escape/focus, default advanced Select, empty/filtered/
  populated Inbox and unsent draft verified. RU/KK/EN desktop/mobile screenshots
  inspected in the corresponding `output/ui-operations-20261008/browser-*` folders.
- `.venv/Scripts/python.exe output/inbox-empty-filters-20261008/verify_frontend.py`
  — build/types/i18n/app/widget/bundle PASS; `frontend-isolated-final.log` alongside.
- `.venv/Scripts/python.exe output/docs-reset-20261007/verify.py` — 55 active
  documents, 362 links, 14 anchors, 38 paths PASS; 198 archive sources intact.
No failed checks. Backend/full E2E skipped: no backend or cross-cutting behavior
change. No dependencies installed, working DB migrations or deployment performed.
Working/index/actual committed range reviewed before normal publication; final
SHA, remote readback and actual CI status are in the task response/local receipt.

## INBOX-UI-ROLLBACK-20261008 — owner-requested rollback

Owner request: restore the Inbox UI preceding `8bb54dd`; the previous version
was preferred. Approved requirement change reopens only the Inbox UI portion of
UI-OPERATIONS, not the other five screens. Base `8bb54ddc5c08d562ca985bbccbdfccd3de7de3bf`,
clean canonical checkout, same primary/branch. Restore the three conversation UI
files and their Inbox-only copy to `79ffca5`; keep AI/backend/domain behavior.
Risk: accidentally reverting other screens or safety/recovery. Checks: exact
source comparison, targeted empty/populated Inbox and existing manual AI-recovery
browser flows desktop/mobile in isolation, one frontend build/types/i18n/bundle,
documentation consistency and working/index/committed diff. No backend changes,
new paid calls, working-DB changes, dependency installs or broad E2E. Commit and
normal-push after checks under standing authorization.

Result: exact source comparison against `79ffca5` PASS for all three UI files
and every Inbox translation in RU/KK/EN. Restored original panels/filter row/copy;
AI settings, provider behavior and other five screens are untouched.
Isolated build/i18n/types/app/widget/bundle PASS via
`.venv/Scripts/python.exe output/inbox-ui-rollback-20261008/verify_frontend.py`;
log `output/inbox-ui-rollback-20261008/frontend-isolated-final.log`.
Browser command prefix `.venv/Scripts/python.exe output/ui-operations-20261008/verify_ui.py`:
desktop/mobile `ui-operations.spec.ts e2e/inbox-agent-safety.spec.ts --grep "Inbox restored|Inbox pause"`.
Mobile 2 PASS (`browser-1791439073961115800.log`); desktop AI recovery PASS
(`browser-1791439032766988200.log`), restored-layout test initially expected an
unused subtitle. Corrected to the actual existing heading, then desktop
`ui-operations.spec.ts --grep "Inbox restored"` 1 PASS
(`browser-1791439204900938200.log`). Logs/screenshots in the UI-OPERATIONS output
directory; original failure retained. Empty/filtered/filled views, draft and
manual controls after AI limit verified. No product changes to satisfy the test.
Docs validator: 55 documents, 361 links, 14 anchors, 38 plain paths PASS;
archive preserved. No backend suites/full E2E or paid calls: runtime backend and
AI code unchanged. Reviewed 11 task-owned paths; working/index/actual committed
range checked for publication. Final SHA and actual CI reported in task response.

## UI-OPERATIONS-20261008 — implementation and local acceptance complete

Source: owner-approved UI/UX audit relayed by task
`01a0f32f-7d02-7263-a53d-496c8f9787f5` with explicit instruction to implement the
whole package in this registered primary. This is new scope, not ownership
transfer. Same generation 4 primary, root `C:/Users/user/Desktop/PlatformaCRM`,
branch `codex/ui-testing-toolkit`, clean starting HEAD
`79ffca5c2b4437750bb7559ce34453ab6c247a29`; no pre-existing changes.
Mode targeted defect correction and approved UI implementation; gaps code/data/UX.

Observable result and complete authorized scope:
- Leads: one create CTA, correctly named import in additional actions, consistent
  terminology, one nearby filter entry, no empty pagination/selection; distinguish
  no data/filter-empty/error. Compact creation form without losing fields.
- Deals: risk is attention, not hot sales; next task/action/date and no-step filter
  agree; honest empty columns and readable entity hierarchy, existing kanban retained.
- Calendar: day/week/month arrows and period heading match view, month/year boundaries
  and selected-mode accessibility; compact controls, slot creation preserved.
- Inbox: coherent empty state; readable filters with separate owner/AI-agent labels,
  filter icon/count; populated conversations, CRM context, drafts and AI pilot preserved.
- Settings: group business profile/contacts, appointments, finance and appearance;
  keep fields/permissions/drafts/save behavior; remove redundant framing/headings;
  group expansion matches visible children and accessibility state.
- Dashboard: real scoped today appointments/confirmations, waiting conversations
  and overdue tasks; full distinct counts separate from previews. Ordered/deduplicated
  entity action queue plus upcoming appointments; owner finance uses actual net
  receipts/source/period/freshness, useful grounded AI summary stays compact.
  Correct deep links, unavailable/error states never mean zero or all clear.

Approved layout reference (conditional data only):
`C:/Users/user/.codex/visualizations/2026/09/30/01a0f32f-7d02-7263-a53d-496c8f9787f5/crm-dashboard-proposal.html`.
Use composition, existing neutral/emerald tokens and RU/KK/EN. No demo data or
role-switch UI. Reuse workQueues/analytics selectors, current API clients, controls,
forms, scopes and existing tests. Minimal read-contract extensions if needed;
no new lifecycle/booking/money policy, notification, audit/BusinessEvent types,
CRM AI development, paid AI calls, external messages/integrations or deployment.
No schema/environment change expected; no working-DB seed/migration, dependency
reinstall, alternate source tree or stopping other processes.

Verification plan: before dependent UI, isolated backend regression for each
coherent count/queue change: overlaps, totals beyond preview limit, stable order,
role/tenant/capability scope and invalid input. Calendar unit/interaction checks
include different views and month/year boundaries. Targeted reachable browser
flows desktop/mobile, keyboard, RU/KK/EN, empty/filter-empty/error/recovery and
populated Inbox. Preserve customer AI safety/recovery/permissions through affected
regressions. Final frontend build/types/i18n/bundle, affected/dependent backend
tests + system/migration drift; no blanket full E2E absent demonstrated need.
Record exact commands/snapshots/results and preserved failures. Finish all six
areas, reviewed docs/checkpoint/STATUS, conventional commit and normal HEAD:main
push with remote SHA and actual CI. No intermediate approval gates or new phases.

Implementation checkpoint: all six areas are implemented in the same dirty
snapshot above. Work queues now expose full distinct operational counts, business
day/timezone, availability/scope and ordered entity previews; disabled/denied
modules cannot reappear through unassigned rows. Backend regression was red
before the fix; the focused gate passed before dependent UI. Query-budget failure
(63 versus 58) was corrected by reusing already loaded category previews.
Final affected/dependent backend gate: 78 tests PASS, system check PASS, no migration
drift; `output/ui-operations-20261008/backend-1791411501420078900.log`.
Calendar/dashboard/policy unit checks: 9 PASS. Six desktop flows passed across
targeted runs; all six mobile flows PASS in `browser-1791411479584303500.log`.
Screenshots inspected for compact form, calendar, settings, Inbox and dashboard.
Earlier selector mismatches and build errors are retained in the same output
directory; they were corrected rather than waived. Additional role/recovery and
navigation-accessibility checks passed: 7 desktop, 4 mobile and 2 tablet scenarios.
Isolated build/types/i18n/widget/bundle PASS; the post-success helper stdout
encoding issue is documented, not a product failure.
[Final evidence and exact checks](../ui-operations-20261008.md) preserve earlier
failures and exclusions. Updated frontend/CRM contracts and capability map.
Documentation registry/link/archive checks PASS: 55 active documents, 359 local
links, 14 anchors, 38 plain paths; preserved archive unchanged. Working diff
hygiene PASS; entire intended source/tests/docs and new files reviewed. Final
publication SHA, committed-range/index checks and actual CI are recorded in the
task response and `output/ui-operations-20261008/publication.json`; no new phase.

## PREPROD-AI-EVIDENCE-20261008 — documentation update

Owner request: update pre-prod with completed customer-agent behavior checks.
Docs-only evidence gap; same generation 4 primary/root/branch, clean base
`de1867bd7ed3a2350fdfdb7dfc35c8ca8c365e69`. Reuse the two acceptance reports,
final case/semantic review and verified publication receipt. No product behavior,
permissions, notifications, BusinessEvent, schema, environment or paid AI changes.
Risk: overstating coverage, conflating real model with real delivery, summing
overlapping tests or leaving stale version/CI status. Update existing passport
and pre-prod navigation/status; preserve historical evidence and external gaps.
Checks: counts/source/CI consistency, local links/anchors, registry and reviewed
working/index/committed diff hygiene. No app tests/build/install/model calls for
Markdown. Completion: reviewed docs commit, normal push and actual CI status.

Result: current passport contains the six-group behavioral matrix, observed
outcomes, fixes, handoff/recovery semantics, supporting checks, costs and limits.
Version and successful application CI are current; pre-prod navigation updated.
Five registered Markdown files, 65 local links/anchors and final 43-case/CI receipt
consistency PASS; diff hygiene PASS. Initial verification helper expected six
files instead of the actual five; corrected to an explicit scope list, then PASS.
No application checks or paid calls rerun. Documentation publication and its
push-triggered CI status are reported in the final response; prior application
CI SUCCESS is evidence for de1867b, not for a future documentation commit.

## INBOX-LOCAL-PILOT-20261008 — complete

Publication readback: `de1867bd7ed3a2350fdfdb7dfc35c8ca8c365e69` normal-pushed
to main; [CI37684198877](https://github.com/999MAX20/PlatformaCRM/actions/runs/37684198877)
backend/frontend SUCCESS. Local receipt `output/inbox-local-pilot-20261008/publication.json`.
The pre-publication steps below were completed; no product work remains in this scope.

Owner authorized completing the existing customer-agent pilot locally: safe
customer scenarios, handoff communication and fast flexible staff configuration.
No new capabilities, CRM-agent development, messenger integrations, production
hosting/database/workers or real customer delivery. Explicit separate USD1 budget.
Same generation 4 registered primary, root `C:/Users/user/Desktop/PlatformaCRM`,
branch `codex/ui-testing-toolkit`, clean base `0112475850c631cd946424c86f49e363c6b80881`.
All changed/untracked source/docs belong to this task; no original WIP or owner drift.
Prior base CI37676924581 SUCCESS. No ownership or runtime-env changes.

Mode audit/targeted implementation/verification; gaps code, UX and local evidence.
Reused safety/pipeline/outbox/recovery, profiles/settings/readiness, API clients,
design system/i18n and existing targeted suites. Risks: duplicate/stale sends,
private-data leakage, automatic writes without permission, lost settings/drafts.
Plan executed: focused isolated backend regressions after coherent fixes, affected/
dependent suites + system/drift, targeted isolated UI/API desktop/mobile/locales/
keyboard, final build/bundle. No full-project local gate, working DB or new install.

Implemented deterministic handoff acknowledgement with outbox idempotency and
revocation guards; empty-reply and mid-turn call-limit handoff fixes. One booking
control saves both permissions/settings; safe mode guards; advanced disclosures;
actual dental template respects saved permissions. No schema, new role or new
BusinessEvent; existing activity/audit/notifications retained. Details and exact
commands/skips/errors: [report](../inbox-local-pilot-20261008.md).

Verification: 241 scoped backend PASS before final call-limit fix; 72 affected
tests PASS after fix, system/drift PASS. 16 selected browser scenarios PASS and
one localized mobile recheck after i18n ordering fix. Build/types/i18n/widget and
bundle PASS; representative screenshots reviewed. Live final 43/43 PASS plus
semantic output/record review; run customer_pilot-1791405340114934200. Cumulative
145 reservations, 143 received calls, USD0.1416664 including failure reserves
of USD1. Final Python/i18n manifest matches. No more paid calls needed.

Evidence `output/inbox-local-pilot-20261008/`: append-only live cases/transport/
manifests + cumulative ledger, semantic-review.json, backend/browser/build logs.
All failed attempts retained: initial missing notice/takeover RED, first live
38/39 with call-limit defect, fixture-quota browser failures, bad selectors/grep,
two nonexistent backend labels and i18n build error. Corrected runs cited in report.

Completed DoD: final source/docs/index/secret review and diff hygiene,
conventional commit, fetch/prove fast-forward normal push HEAD:main, remote SHA
readback and actual CI. Do not call CI green before readback. Publication receipt
goes in local publication.json and final response; candidate is report's commit.
Next product boundary is real channel/target environment/staff acceptance, excluded
here and not automatically authorized. No own server/job is intentionally retained.

## INBOX-LIVE-ACCEPTANCE-20261008 — behavioral PASS; publication below

Owner authorized real-model acceptance of ordinary inquiries, booking, protection
and recovery, including fixes for reproduced in-scope defects. Explicit new budget:
USD 1 maximum, stop before exceeding it; prior task budgets are not reused.
Mode verification/targeted fixes; gap evidence. Same generation 4 primary/root/
branch; clean base `00fe0e7c8743a4b84d136db9492e9228e88beecd`.

Reuse `scripts/ai_behavior`, isolated_runtime, current Inbox pipeline, domain
services and existing safety/booking/recovery tests. Synthetic disposable DB,
real configured AI provider only; controlled outbound receipts, never real
customers or messenger delivery. No working DB, migration, deployment, billing,
CRM-agent/analytics development or new integration rollout.

Changed behavior initially none; if a defect reproduces, minimal correction and
focused regression before dependent work. Risks: budget overflow, false booking,
privacy leak, false handoff, duplicate work and stale replies after recovery.
Acceptance checks facts vs fixture, actual records/relationships and timestamps,
no writes without valid consent, denial/tenant boundaries, sensitive context,
limits and replay, provider failure/manual takeover/resume. Review model output
semantically; HTTP success alone is not PASS. Test controls cannot masquerade as
live channel, infrastructure or clinic acceptance.

Focused checks: existing customer safety/state/recovery, automatic booking,
runtime configuration, Inbox continuity and AI job recovery in isolated runtime;
test budget harness before live use. Add explicit USD1 CLI budget and a targeted
Inbox suite if needed, retaining cumulative attempts/reservations across retries.
Completion: affected/dependent backend suites plus system/migration checks if
runtime changes; reachable API flow, relevant UI/build only if changed. No full
project/E2E gate by default. Docs links/registry/diff checks; reviewed commit,
normal HEAD:main push, remote SHA and actual CI. Keep all failed attempts visible.

Initial plan: prepare selected synthetic scenarios and run deterministic baseline, then
bounded live evaluation. Evidence under `output/inbox-live-acceptance-20261008/`.

First results: 53 focused tests/system/migration drift PASS; 6 budget-harness tests
PASS; 4 no-provider safety/API dry cases PASS. First live 27 cases: 25 machine
PASS, 2 harness failures (ambiguous request expectation contradicted permitted
uncertain handoff; held-worker simulation accidentally used eager result backend).
Retain both failures and fix test setup/criteria transparently, not runtime policy.
Semantic review found a real wrong off_topic classification for clinic address,
and busy/denied booking selection led to another model confirmation of an
unavailable/uncommittable time. Appointment writes remained protected.

Bounded fix plan: clarify business-information categories in qualification;
when existing booking service returns requires_staff, call existing handoff
service and, when auto replies enabled, send existing localized handoff copy.
No new booking permission/policy/endpoint/schema/UI. Existing handoff activity,
audit and manager notification apply; pipeline event retains actual decision.
Add failing pipeline regression for busy, staff-only and disabled-tool selection,
verify immediately; strengthen live assertions and retest affected scenarios.
Provider-failure injection reserves cost conservatively; cumulative ledger stays
under the separately approved USD1. No real messenger delivery claimed.

Final behavioral gate: 130 affected/dependent backend PASS, system/migration-drift
PASS (`backend-1791401726512442200.log`); final live run 28/28 machine and semantic
PASS, 57 real calls. Total 55 case attempts retained, 110 received provider calls,
2 injected-failure reservations. Provider-reported USD0.1104668, conservative
charged/reserved USD0.1228916 of USD1. Final source manifest matches current Python
files. No further paid calls needed. Detailed commands, deltas and limitations:
[acceptance report](../inbox-live-acceptance-20261008.md). Next: final docs/source
review and diff gate, commit/push and actual CI. No new phase. Prior docs CI
37667508038 is now confirmed SUCCESS. Working DB/servers/dependencies unchanged.

## DOCS-RESET-20261007 — консолидация документации

Mode docs; gap — устаревшие маршруты/смешение требований и истории. Владелец
разрешил сверку реализации, обновление README и активных источников, архивацию
старых документов. Один writer generation 4 `01a11776-e13a-76c2-9fc0-75d38228f649`.
Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
clean base `f01d22610118e3a24df86257943a8be91314f916`.

### Контракт и план проверок

Результат: компактный реестр current contracts + паспорта + процедуры; агенты
не берут старые технические планы как действующие. Reuse существующих решений,
паспортов, source/tests и evidence; не переписывать продукт. Риск — потеря правил,
открытых обязательств или ложный live PASS. Поэтому оригиналы сохраняются с SHA256,
последние решения сверяются, незакрытое переносится явно.

Нет изменений кода, схемы, runtime, dependencies, ownership, permissions,
notification, BusinessEvent или AI-поведения. Никаких provider calls, миграций,
deployment или новой продуктовой фазы. Формулировки контрактов сохраняют уже
утверждённые границы, не утверждают архивные предложения.

Checks: inventory/classification, source/decision traceability, archive byte
integrity, active links/anchors/plain paths, agent routing/frontmatter/scenarios,
registry invariants, working/index/actual committed-range diff hygiene. Проверка
новых/нетрекнутых файлов обязательна. App tests/build/install/DB/browser — skipped:
документационная задача, программные входы неизменны. CI запускается существующим
push workflow независимо; его результат проверяется отдельно и не выдумывается.

### Сделано

- 198 прежних проектных документов учтены; 137 перенесены из активного дерева,
  20 прежних entrypoint/procedure/passport тел сохранены перед обновлением,
  40 старых архивных тел и один generated inventory сохранены на месте.
- Созданы 9 current контрактов и source-backed карта возможностей. Сохранены
  актуальные паспорта и стабильные пути процедур/реестра владельца.
- Убраны старые competing планы/redirect stubs; обновлены AGENTS, README, маршруты
  skills; архив имеет отдельную инструкцию non-authority и исключение `.rgignore`.
- Открытые FC/BE/UX/FB и бизнес-решения не закрыты переносом. Последние controlled
  AI creation / manual financial source / support-note / deferred billing решения
  отделены от старых предложений. Предыдущая safety live boundary сохранена.

### Проверки и публикация

Состояние: содержательная проверка PASS. `verify.py` в локальном evidence: 198
исходных Git blobs/сохранённых тел, 52 active entries (30 проектных +22 skill),
328 local links, 12 active anchors, 38 plain paths — PASS. Проверены JSON registry
без изменений ownership, skill frontmatter и отсутствие архива в default rg.
Сценарии маршрутизации: новая CRM/AI/UI задача ведёт к current contract;
исторический PASS читается точечно без открытия scope; unresolved acceptance
остаётся открытым; compaction не меняет владельца. Runtime references к
DKB/generated inventory и ZR-001–010 сохранены. Рабочий/index diff hygiene PASS; 198 staged archive blobs совпали с исходными
SHA256, посторонних non-document paths и unstaged diff нет. Зависший пустой
index.lock снят после проверки возраста, отсутствия Git-процессов и exclusive-open;
индекс и HEAD не менялись другим writer. Реальный committed range и remote/CI
проверяются на этапе публикации.
Детальные безопасные результаты: `output/docs-reset-20261007/` (локальные artifacts).
Документальная часть завершена и проверена. Публикация: reviewed explicit paths,
conventional commit, normal HEAD:main push,
remote SHA readback и фактический CI. Итоговый SHA/CI — в ответе задачи и локальной
квитанции; commit не может содержать собственный hash. Следующий продуктовый этап
не назначен. Незакрытые требования — [acceptance](../../current/acceptance.md).

### Сохранённая история

[Исходный checkpoint](../../../archive_docs/2026-10-07/docs/testing/task-state/PRIMARY-SESSION.md)
содержит закрытые scope и evidence до этой консолидации; это не очередь задач.
Передача generation 3 → 4 завершена и опубликована `f01d226`; registry idle,
source archived native readback. Latest safety CI 37653976762 / 37654213713 и
паспортный CI 37657729094 SUCCESS. Latest safety проверен с mocks; предыдущие
21 real-model continuity cases не сертифицируют последующее изменение защиты.
CRM/Analytics development paused; существующий runtime не удалён/не выключен.
HookActivationStatus REQUIRES_REVIEW_AND_TRUST; новой проверки runtime hook нет.
