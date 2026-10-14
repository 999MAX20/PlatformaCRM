> Решение владельца 14.10.2026: межчатовая координация, роли primary/UI,
> назначения writer, ожидание других чатов, автоматическая передача и связанные
> ограничения отменены. Применять актуальный AGENTS.md. Ниже сохранены сведения
> о задачах и evidence; прежние межчатовые назначения являются историей, а не
> действующими инструкциями. Продуктовый scope, результаты и блокеры сохраняются.

# PRIMARY-SESSION — PlatformaCRM

## CRM-S02-20261014 — operational platform administration

Owner authorized S02 and the sequence inspect/reuse → server rules with focused
checks → integrated UI aligned to shared design → affected-flow verification.
Mode implementation; gaps code/evidence/UI. Canonical root
C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
base821719d00fafef26e8a09a57cc4152900da81b82; clean starting index/worktree.
No delegation/interchat coordination. Existing platform layout, four implemented
pages, API, support grants/MFA/audit and operations diagnostics are reused.

Observable result: bounded server search/pagination, useful business detail/support
history, truthful overview/diagnostics and reachable support action with preserved
draft/errors, shared tokens/components across the affected platform shell/pages.
Keep existing platform/merchant access separation. No billing product, commercial
analytics, implementation of five placeholder sections, AI/provider integration,
S03 incident notification system or S04 infrastructure/backup work. No schema or
working-DB changes intended. No new business suspension/identity/billing rights.

Owner answered: keep diagnostics and support journal; recovery belongs to the
authorized clinic employee. No platform retry/cancel rights added. Platform
support suggestions no longer navigate to an unrelated active merchant context.

Backend first slice: list API now returns count/next/previous/results with server
search/status and bounded page_size1..100 (default20), stable created_at/pk order.
Updated existing internal client/tests for this explicit response contract.
Operational aggregation moved to selectors and batch queries; no500-business cap.
Overview errors now count persisted failed automation/notification/integration/
export records (not live outage status). Support notes receive typed validation.
First attempted baseline aborted during URL import while helper extraction was
in progress (domain-1791971477454376800.log); this is not a product regression
reproduction. The original unbounded/constant/capped behavior is evidenced by code.
After coherent implementation, isolated check/drift plus24 tests PASS:
`.venv/Scripts/python.exe output/crm-s01-20261014/check.py
apps.core.tests_platform_s02 apps.core.tests_platform_operations
apps.core.tests.PlatformDashboardTests apps.core.tests.PlatformAccessFoundationTests`
(domain-1791971540135176400.log).

Support journal slice: GET existing support-actions route returns paginated,
business-scoped, sanitized audit; POST retains admin + exact grant + fresh MFA.
No operator write/recovery expansion. Full history supersedes the5-item preview.
Focused/affected `check.py apps.core.tests_platform_s02
apps.core.tests_platform_operations` =21 PASS plus check/drift
(domain-1791971707365150100.log), including506-business accurate summary under50
queries, invalid filters/notes, cross-business history and permission denials.

Frontend reuses PageHeader/Card/Input/Select/Button/CrmPagination/LanguageSelector
and existing draft guard; light shared shell, four operational pages, no new
placeholder functionality. Search/page are URL-backed, detail returns to list
context; form preserves error draft and has one labelled note field; full journal
has page controls. Build/i18n/types/widget/bundle PASS via
`.venv/Scripts/python.exe output/crm-s02-20261014/frontend.py` (isolated env,
no dependency install). Browser verification is underway. First fixture attempt
used interactive Django shell, causing syntax errors before browser acceptance;
stopped owned session17387 and verified no matching child processes. Corrected
fixture execution to shell -c; new disposable run, no working DB changes.

Initial evidence: merchant list loads every business and filters client-side;
overview examines at most500 while claiming total_monitored of all; errors count
is hard-coded0. Platform shell has a nonfunctional search-looking block and
different hero/sidebar styling from the current CRM workspace. Existing support
write already requires platform_admin + exact grant + recent MFA; retain it.

Risk: data scope, privileged support audit, pagination correctness, misleading
operational summaries and inaccessible/error UI. Backend focused reproductions
after each coherent slice, then affected platform/security/operations tests and
check/drift. Frontend build once at completion; targeted isolated browser flows
for list/search/pagination/detail/support note and deny/error/recovery, desktop and
mobile, RU/KK/EN representative copy/keyboard states. No full-project local suite,
dependency reinstall or reuse of another task's dev servers. Publish only own
reviewed changes to origin/main, remote SHA and actual CI readback separately.

Final S02 verification (14.10):
- Final affected backend command: `.venv/Scripts/python.exe
  output/crm-s01-20261014/check.py apps.core.tests_platform_s02
  apps.core.tests_platform_operations apps.core.tests.PlatformDashboardTests
  apps.core.tests.PlatformAccessFoundationTests`:28 PASS, system/drift PASS;
  log output/crm-s01-20261014/domain-1791972669070503900.log.
- Build/i18n/types/widget/bundle PASS, unchanged frontend product inputs since
  output/crm-s02-20261014/frontend-isolated-final.log.
- `.venv/Scripts/python.exe scripts/verify_platform_s02.py`:9 PASS/1 intentional
  mobile skip (existing desktop-only route audit). Six new checks pass across
  desktop/mobile; other smoke checks prove route and server-capability rendering.
  Log output/crm-s02-20261014/browser-1791972639638775200.log. The tracked runner
  provisions disposable DB/ports and opts in E2E_PLATFORM_S02 fixtures; no working DB.
- Real grant + MFA enrollment/recovery-code step-up +201 support write verified;
  bad factor preserves draft, paginated journal includes write, no-grant read-only,
  server search/page/return/empty,503 recovery and RU/KK/EN operations keyboard
  checks pass. Screenshots under frontend/test-results/platform-s02-*/platform-*.png
  visually inspected for list/detail/overview/operations, desktop/mobile; horizontal
  table scrolling stays inside its container.
- Attempt2 stopped for test session mismatch after enrollment; fixture now reloads
  the rotated session. Attempt3:4 PASS/2 support failures exposed missing CORS
  allow-header, not backend denial. Added x-zani-mfa-step-up to existing headers,
  with allowed/untrusted-origin preflight regression. Final browser run above PASS.
  No permission bypass. Restored original latest_activity fallback semantics while
  batching selectors; final backend run includes this delta.
- No schema/env additions, migrations to working DB, external sends, BusinessEvents,
  AI actions, new recovery rights or provider work. Audit write remains existing
  support action. Full local suite/live queues/provider/deployed acceptance skipped
  as outside S02; local SQLite/eager/locmem is not production readiness. Existing
  environment warnings remain visible in diagnostics. Owned test servers stopped.
- Reviewed all25 intended paths including new selectors/serializers/tests/runner;
  synthetic fixture identities only. Actual remote main readback821719d at prepublish;
  stored origin/main ref was stale, use explicit remote readback/FETCH_HEAD.
  Final commit-range static and normal push pending below. S03/S04 not started.

S02 delivery receipt: code fc322a67007abacc27349f6fe03626eda6203f45 committed
on codex/ui-testing-toolkit in canonical root. Exact command
`.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
821719d00fafef26e8a09a57cc4152900da81b82` PASS (working/index/committed diff,
migration drift/system check). Fetch/FETCH_HEAD ancestry proved normal fast-forward;
`git push origin HEAD:main` succeeded and `git ls-remote origin refs/heads/main`
matched fc322a6. GitHub run38548233244 in_progress at readback, not CI PASS.
Prior S01 runs38535866997/38535831639 completed success. No deployment workflow
in repository, only CI; no deployment claimed. Final docs receipt checks:
diff hygiene, changed links/commands/consistency; unchanged app checks reused.
S02 closed in authorized scoped boundary; S03 next, not started.

## CRM-S01-20261014 — server scenario completeness

D-04 continuation, owner approval 14.10: reuse one built-in appointment follow-up
without overwriting it; explicit create_task remains separate. Base4152976,
canonical root/branch unchanged, clean tree. Scope scheduling follow-up service,
automation action and targeted tests/docs only. Risk duplicate tasks/effects and
overwriting staff work. Reuse existing task creation activity as origin evidence;
serialize lookup/create with Business/Appointment locks. No schema, permissions,
AI or external-delivery change. Focused checks: inline/delayed rules, replay,
preserved fields/status, explicit task, tenant denial and PostgreSQL concurrency.
Completion: affected scheduling/automation suites, check/drift/static; reuse
unchanged earlier S01 checks. No frontend changes/build or working DB operation.

D-04 result: implemented in scheduling service and automation engine. Built-in
task is created before inline rules; task creation activity identifies it without
matching editable titles. Business/Appointment locks serialize lookup/create.
Reuse preserves staff changes, completed/archived status and original effects;
explicit create_task and nonterminal follow-up configuration remain independent.
No cleanup of historical duplicates or backfill performed.

Baseline focused policy tests: 2 FAIL / 1 ERROR / 1 PASS
(domain-1791966486639622000.log): duplicate cancellation task, wrong delayed task
identity, three completion tasks instead of built-in plus explicit task.
After fix, `.venv/Scripts/python.exe output/crm-s01-20261014/check.py
apps.automations.tests_follow_up_policy apps.automations.tests apps.scheduling.tests`
= 81 PASS, check/drift PASS (domain-1791966538894569000.log).
Additional rollback/archive/nonterminal tests and dependent checks:
`.venv/Scripts/python.exe output/crm-s01-20261014/check.py
apps.automations.tests_follow_up_policy apps.automations.tests_dispatch_commit
apps.automations.tests_claim_ownership apps.scheduling.tests_settings_delivery`
= 23 PASS, check/drift PASS (domain-1791966624780128100.log).
`.venv/Scripts/python.exe output/multibranch/postgres.py
apps.automations.tests_follow_up_concurrency` = 1 PASS
(postgres-1791966579872981300.log): competing rule/built-in creators return the same
task. Disposable PostgreSQL17 stopped, no owned processes remain. Tenant denial,
API completion/cancellation, delayed execution, replay and transactional rollback
are covered. Existing permission/other S01 checks below reused unchanged.
Prior implementation/receipt CI runs38531639534/38531700474 now confirmed SUCCESS.

D-04 publication: 80273a4bc95b3bdcb36433daaaf80cbf2e5237f5 normal-pushed
to origin/main; remote SHA matched. Reviewed all intended files/new tests and
outgoing diff for secrets/unrelated changes; 3 added local links PASS.
`.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
4152976f58c7dfdef217a4a7a755748343b1b341` = PASS, including committed-range
hygiene, system check and no migration drift. GitHub
[run38535831639](https://github.com/999MAX20/PlatformaCRM/actions/runs/38535831639)
observed queued, not PASS; full CI acceptance is separate from scoped local closure.

S01 is closed within its six-boundary contract; the D-04 pending entries below
describe the earlier publication and are superseded by this owner-approved result.
Next unfinished stage is S02; not started. Full production/pilot and external
queues/delivery remain outside this result. Frontend unchanged, no build/browser
rerun; no dependency installation, schema migration, AI/provider call or working DB.

Owner request 14.10: persist the proposed four-step internal readiness plan and
start step 1, complete CRM server scenarios. Mode implementation/verification;
gap types code/evidence/policy. Current executor is this user task; no writer registry.
Canonical root C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
starting base/HEAD 973fef737b6276eac6f54bca112ca6daa31be851. Starting index/worktree
clean, no untracked files. Preserve any subsequent unrelated changes.

Observable result: bounded scenario matrix for concurrent/stale changes, command
replay, changed membership/permissions, archive dependencies, appointment reminder
reconciliation and overlapping built-in/user follow-up. Reuse domain services,
state machines, command wrappers, permission scopes and current tests/closures.
R01 and its unchanged 47-domain/15-browser evidence remain closed; this is the
owner-requested additional completeness boundary, not a repeat of full R01.

Acceptance: each named scenario has its existing rule, actual API/service path,
test/evidence and disposition; proven in-scope defects receive minimal fixes and
regression evidence. Policy D-04 and any genuinely undefined new rule require a
specific owner decision before dependent behavior; continue independent scenarios.
Do not turn an old open heading into a defect without current code evidence.

Risk: lifecycle/data loss, duplicate effects, role/tenant bypass and stale reminders.
Focused verification after each coherent backend change in the existing isolated
runner environment; prove happy/invalid/denial/tenant, rollback and replay as
applicable. Completion: affected/dependent suites, Django check/migration drift,
diff hygiene and actual committed-range static gate. Use PostgreSQL only where
row-lock/concurrency proof is required; no SQLite concurrency claim. Existing
reachable API paths must be exercised; frontend build/browser only if UI changes
or a concrete affected UI regression requires it. No full-project/E2E rerun by
default, no installs for unchanged dependencies, no working DB/servers.

Permissions unchanged except enforcing established rules; preserve single
notification/BusinessEvent/activity/audit effects. AI/provider behavior, new
permissions, lifecycle policy, billing, admin-panel implementation, incident UI,
local operations S04 and external pilot R02+ are non-goals. No migration intended.
Delivery: task-owned reviewed commit and normal push origin/main per AGENTS,
remote SHA readback and actual CI reported separately; no deployment authorized.
Inspection/reproduction: initial fixture failed before scenarios because two users
had the same empty unique email; corrected fixture emails only. Then
`output/crm-s01-20261014/check.py apps.core.tests_crm_server_scenarios` reproduced
7 failures on unchanged product behavior (domain-1791963044595760300.log): lead
status/assignment and deal stage survive failed audit; stale lead bypasses lost
reopen; stale deal stage change overwrites a newer amount; repeated lost commands
destroy lead previous_status/deal previous_stage. This is new evidence, not an
inference from an old open acceptance heading.

Lead slice: reuse Business-first locking (existing scheduling/payment convention),
reload before service validation, atomic mutation/effects and permission recheck
for the existing API permission. Exact repeated status is a no-op, preserving
reopen metadata. No new permission/lifecycle policy or database migration.
`.venv/Scripts/python.exe output/crm-s01-20261014/check.py
apps.core.tests_crm_server_scenarios.LeadServerScenarios apps.leads.tests_crm_light`:
Django check/drift and 30 tests PASS (domain-1791963172767257500.log), isolated
SQLite/eager/locmem. PostgreSQL concurrency remains a separate required check.
Owner was asked the precise D-04 choice (one built-in follow-up reused by the
follow-up rule action, rule priority, or leave pending); no response assumed.
Deal slice: stale state is reloaded before commands; ordinary updates use the
same Business/record locks. Exact repeated terminal commands preserve reopen
history; amount input uses the existing DecimalField limits. Stage requirements
apply to quick terminal actions as well as move-stage (no new stage graph).
Initial extra amount/update regressions failed on the old code; after the first
fix, deal scenario + apps.crm.tests = 33 PASS (domain-1791963431530773800.log).
The final stage-requirement addition has its own focused check below.

Archive slice: all three new regressions reproduced on the old helper
(domain-1791963516951665500.log): failed audit left archive/restore committed,
stale repeated archive replaced the original reason. Shared archive/restore now
reload under a row lock and commit effects atomically. New regressions plus
apps.core.tests_archive, apps.clients.tests_archive_dependencies,
apps.services.tests: 30 PASS (domain-1791963588236210300.log).

Access slice: lead create-deal serialized without actor context and replayed
stored fields after the actor lost sensitive-field access (two failing cases,
domain-1791963653876327200.log). Existing/replayed deals now require current
object view access and current field masking. No new role or permission model.
Access scenarios + member deactivation + lead API + task workspace: 52 PASS
(domain-1791963784882760200.log). Separate invalid create-deal amount regression
PASS (domain-1791963896943227000.log); uses the same DecimalField validation.

PostgreSQL: `.venv/Scripts/python.exe output/multibranch/postgres.py
apps.core.tests_crm_server_concurrency apps.tasks.tests_concurrency
apps.branches.tests_concurrency` = 6 PASS (postgres-1791963716070724300.log).
Proved concurrent create-deal yields one linked deal, repeated lost one transition,
detail/stage changes preserve both results, refund cap, task version conflict and
single specialist slot. Disposable PostgreSQL17 initialized and stopped by the
helper; no working DB, existing service or credentials used. Later relevant
lead/deal changes require rerunning that subset; unchanged other proofs remain valid.
Final stage-requirement regression + deal suite: 34 PASS
(domain-1791963991920535800.log). Relevant PostgreSQL lead/deal subset rerun:
3 PASS (postgres-1791964133807594600.log); unchanged refund/task/slot evidence reused.

Automation dispatch slice: outer CRM transactions exposed premature broker dispatch.
New baseline: 2 FAIL / 1 ERROR (domain-1791964279758754800.log). Non-inline enqueue
now runs on_commit(robust=True): rollback discards dispatch; transport failure keeps
the durable pending run available to existing recovery. No external messages sent.
`.venv/Scripts/python.exe output/crm-s01-20261014/check.py
apps.automations.tests_dispatch_commit apps.automations.tests
apps.automations.tests_claim_ownership apps.automations.tests_queue_runtime`:
36 PASS, check/drift PASS (domain-1791964360858427800.log).

Completion affected/dependent run: 238 PASS, check/drift PASS
(domain-1791964110612609600.log). Exact test labels, passed to the same isolated
helper: apps.core.tests_crm_server_scenarios apps.leads.tests_crm_light apps.crm.tests
apps.core.tests_archive apps.clients.tests_archive_dependencies apps.services.tests
apps.businesses.tests_member_deactivation apps.scheduling.tests_settings_delivery
apps.scheduling.tests apps.automations.tests apps.automations.tests_claim_ownership
apps.payments.tests apps.branches.tests_scheduling apps.branches.tests_staff;
plus apps.core.tests_business_flows_e2e.CrmBusinessFlowE2ETests methods
test_command_claim_rejects_concurrent_processing_and_reclaims_stale_lock,
test_command_keys_are_isolated_by_business_and_actor,
test_failed_command_can_retry_and_expired_results_are_pruned,
test_lead_client_appointment_task_flow, test_lead_to_deal_won_and_lost_flow,
test_appointment_reschedule_cancel_and_no_show_flow; plus
apps.ai_core.tests_crm_tools.CRMCommandTests methods
test_archive_preserves_data_and_restore_is_confirmed,
test_client_archive_respects_unfinished_work. The last two are shared archive
consumer compatibility, without AI/provider calls. Automation tests were repeated
after the later on_commit fix; unaffected suites were not repeated.

| Boundary | Disposition / evidence |
| --- | --- |
| Concurrent/stale commands | Fixed fresh-state locking and atomic effects; API regressions and disposable PostgreSQL races PASS. Existing task version/booking/refund invariants PASS. |
| Replay | Exact status replay preserves history; command claim/retry/expiry/tenant+actor isolation and create-deal concurrency PASS. |
| Changed access | Existing member-deactivation checks PASS; current object/field access rechecked on create-deal replay, stale assignment mutation denied. |
| Archive dependencies | Shared atomic archive/restore regressions PASS; client unfinished-work, service, branch/staff and representative archive consumers PASS. |
| Visit reminders | Existing reschedule/cancel retry/inflight invalidation in tests_settings_delivery and scheduling lifecycle PASS; no reminder code change needed. |
| Built-in/user follow-up | D-04 approved and verified in continuation above: one built-in task reused without overwriting, explicit create_task separate; policy/API/rollback/tenant/concurrency PASS. |

No frontend/build/browser rerun: no frontend/contract shape change or demonstrated
UI regression; reachable API flows tested. No full certification, installs, working
DB migration or external delivery. All owned disposable test processes stopped.
Publication contains independently verified fixes and the four-stage plan, not a
claim of full S01 closure or production readiness. Next: owner D-04 decision, then
its bounded implementation/regression; do not start S02 automatically.

Publication receipt: implementation c4e03cade82b82a0ceb48efff0df207be26f93b0,
normal push HEAD:main succeeded and remote SHA matched. Entire intended diff,
new files and outgoing range reviewed for unrelated changes/private data; added
local links and working/index/range hygiene PASS. Exact completion command:
`.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
973fef737b6276eac6f54bca112ca6daa31be851` — PASS (check/drift/hygiene).
GitHub run38531639534 observed queued after publication, not green; inspect
[actual CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/38531639534)
before relying on full CI acceptance. No deployment workflow was triggered.

## CRM-R01-FB009-20261014 — user-assisted screen-reader verification

Final owner decision 14.10: defer screen-reader work and close R01 if this was
its last remaining criterion. The selected R01 checkpoint and primary handoff
identify audible FB009 as that sole remainder; therefore R01 is closed against
the owner's revised scope. FB009 is DEFERRED / NOT EXECUTED, never PASS. Existing
accessibility support, broader FC003/FC008/clinical/live acceptance and unresolved
external policies remain unchanged. R02 is next but not started by this decision.
This supersedes the pending preparation state recorded below.

Closure is docs-only: reconcile roadmap/acceptance/STATUS and this checkpoint;
review all changes/links and working/index/actual committed-range hygiene, normal
push and actual CI readback. Reuse unchanged product checks and successful CI
38514642210 for base148dd9e; no rebuild, reinstall, app suite or working-DB change.
Stopped helper session72135 with `stop` (exit0), verified neither51017 nor51018
has a listener, and closed only owned Chrome tab1634112199. No audible test was
performed; no screen-reader version or output is claimed. No product code changed.

Preparation before deferral: primary transferred sole writer/checks/servers to
PlatformaCRM UI; canonical root and branch unchanged, base148dd9e, clean tree.
The reviewed isolated helper prepared a disposable administrator fixture;
Chrome opened the RU Inbox and menu/focus setup was inspected. User-assisted
listening never started. No real records, external messages, working-DB migrations
or product edits occurred. Complete diff/private-data review and local-reference
review PASS; no untracked source files. Docs hygiene gates are recorded with the
publication SHA in the task receipt. Writer returns to primary after publication.

## CI-PUBLISH-20261014 — remaining documentation and actual CI receipt

Owner explicitly requested all necessary CI checks and publication of all remaining
changes before continuing. Primary explicitly transferred the sole writer to
PlatformaCRM UI for this bounded operation and stopped writes/checks/servers.
Canonical root C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
starting HEAD/base 0b4d7da9c136686a3b0ddbcfb4dd458875e9dd9e; index empty;
starting dirty only ONEC STATUS +7 and this checkpoint +68, fully reviewed.
Mode operation/docs; gap unpublished evidence and stale CI status, no code delta.
Scope: publish the existing ONEC journal, record actual CI and verify normal push
to origin/main. Reuse unchanged product checks; no app installs/builds/DB/browser
reruns for Markdown. Focused/completion gates: whole intended diff and untracked
review, secret/private-data review, local links, working/index/actual-range diff
hygiene, remote SHA and GitHub job/step readback. No permissions, notifications,
BusinessEvents, AI, migration, working data or external integration changes.
ONEC access expansion and R01 audible screen-reader FB009 remain unresolved;
publication does not authorize either external action or a new product phase.

GitHub REST confirms success for Calendar runs 38464742290/38464828917,
Settings 38467033037/38467146320 and R01 38471830909/38471973914.
For exact starting HEAD, run38471973914 has both jobs and all steps successful:
committed-range static, migration drift, Django check, readiness-audit JSON smoke,
backend suite, Python dependency audit, frontend/widget build, bundle budget and
frontend dependency audit. Older queued/in_progress entries are historical.
Historical toolbar failures are not relabelled; the current descendant's full
CI is independently successful. This docs commit triggers the existing workflow;
its final SHA/run outcome is read back and reported in the task, without creating
an endless chain of receipt-only commits. No deployment job exists in ci.yml.
Whole diff and untracked review PASS (no untracked source files or sensitive
payloads); `git diff --check` PASS and the checkpoint link resolves. Explicit
fetch refreshed stale origin/main from 198e6a4 to the verified remote 0b4d7da;
fetch configuration and working branch unchanged. Index and committed-range
`git diff --check` are required before the normal publication/readback.

## CRM-R01-20261014 — bounded daily-cycle acceptance

Mode verification with minimal proven regression fixes; gap evidence/code.
Owner-authorized Phase3 follows Calendar and Settings scoped completion.
UI explicitly returned sole writer; primary verified canonical root, branch
codex/ui-testing-toolkit, base3d291720b091f77f147bc78d2a908a4a1626972e and remote.
Starting dirty is only unrelated ONEC STATUS7/checkpoint68, preserved under
output/r01-20261014; index empty. UI prepares current controls strictly read-only.
Result: administrator follows client/Inbox/lead/deal/task/visit and applicable
manual-payment/history cycle with persisted semantic receipts and independent
lifecycles. Reuse existing module, access and archive-dependency coverage.
First reproduce Inbox task Business-timezone and lost-response retry risks;
reuse taskDateISO, API idempotencyConfig and existing backend command wrapper.
No new lifecycle/permission/AI policy, backend rewrite, migration, live send,
working-DB operation, History redesign, R02+ or release-candidate certification.
Risk: wrong deadline/duplicate next step; focused isolated real-API browser
reproduction then regression (stored UTC, one task after retry, deliberate next
creation distinct, validation/draft recovery); existing inbox task domain suite.
Completion: selected linked daily cycle with independent API/activity receipts,
roles/tenant/dependencies/archive/restore and conflict/recovery from applicable
focused checks; RU/KK/EN, mobile and keyboard affected flow; one final isolated
build/types/i18n, current control registry/outcomes, diff/static actual range.
Reconcile baseline registry AI redirect/branches and Calendar view metadata.
FB009 real screen-reader remains open pending user-assisted evidence; automated
semantics are not equivalent. D04 overlapping built-in/user automation is excluded
pending policy, not silently accepted. Report named controls and gaps without a
global FC003/FC008 or production claim. Notification/BusinessEvent effects must
remain single for replayed commands; no new effects intended.
Delivery: reviewed owned commit and normal push origin/main with actual CI;
retain unrelated ONEC blocks and record failed attempts/skips explicitly.

R01 initial reproduction: isolated browser1791925280350159600 (UTC browser,
Business Asia/Almaty) failed both intended assertions: 10:30 stored/displayed15:30
Business time; successful create with lost response followed by retry returned
task4 instead of committed task3. No working database or external provider used.
Minimal frontend fix reuses taskDateISO in mutationFn (validation errors enter
existing recovery), adds existing Idempotency-Key config to inboxApi.createTask,
keeps key for the same actor/Business/conversation/payload and resets for a new
creation or context. Backend command implementation unchanged. Initial regression
browser1791925388427971600:2 PASS including intentional next create being distinct.
Broadened changed-flow locale/mobile/keyboard and single-activity checks pending.
Registry baseline metadata reconciled: AI legacy redirect outcome, existing branch
configuration route, month/week day inspector, actual History activity endpoints
and current journey test pointers. check:certification and two registry Node tests
PASS; pointers/historical PASS fields are not new execution receipts.
Daily-chain first fixture attempt browser1791925646573668100 failed before any
operational action: preset named administrator instead of actual enum admin.
Corrected fixture only; rerun pending. Preserve failures, no product role changes.
Second daily fixture attempt1791925737224260100 used obsolete /automations URL;
corrected to existing /automation-rules, before operational actions. Third attempt
1791925815672395300 reproduced a real shared Header issue for administrator:
reading the only unread conversation changed count1→0, effect cleanup cancelled
the toast's auto-dismiss timer but left it open indefinitely above About client.
Minimal fix separates unread activation/zero dismissal from timer lifecycle;
no notification data/delivery changes. Same real-role chain now explicitly checks
zero count and hidden notice before using the formerly covered button. Owner
changed-flow locale tests and administrator navigation are representative callers.
Focused isolated domain check/migration drift +47 tests PASS (domain.log):
apps.conversations.tests_inbox_tasks, apps.clients.tests_archive_dependencies,
apps.payments.tests. Includes task replay/single audit/activity/notification,
permissions/tenant, archive dependencies/rollback/restore and payment/refund limits.
No backend product edits; this is selected R01 domain evidence, not a full gate.
GitHub readback: Calendar2f9035b/receipt17fb7c1 and Settings receipt3d29172 CI success;
Settings implementationc40aff4 run38467033037 still in progress at this readback.

R01 daily-cycle evidence: desktop browser1791926492812083000 and mobile
browser1791926613690940100 PASS, each one real administrator linked journey.
Controls: take Inbox, client edit and retained unsent reply, contacted lead,
linked deal/task/branch visit, win without cascading task/visit/lead closure,
task completion, visit confirmation/completion, reject zero payment then persist
1250.50 manual receipt, reject archive409 with unfinished dependencies, History
search/detail/visit link and single completion event with actor/time; separate
UI-created client archive and Undo. Synthetic fixtures only, no external reply.
Additional fixture corrections: branch choice includes its address; payment
readback requires Business and nested link; History search waits for actual
debounced response before opening row. These failed attempts did not justify
product changes. Logs and semantic receipt attachments are in ignored
output/crm-toolbars-20261013/browser-<stamp>.

RU/KK/EN Inbox six cases per viewport passed before final focus fix:
desktop1791926765240490500/mobile1791926800705361100. Screenshot review replaced
incorrect page-title/page-subheading field labels with existing task name and
description translations; final creation checks use those labels. Manual Chrome
CU on isolated57528/57529 reproduced Escape losing focus; add an optional stable
ActionMenu focus-return marker, used only by Inbox, and task Dialog return ID.
Manual retest PASS: keyboard menu/open, fields, priority, Escape focus return,
reopen and keyboard create; saved task visible with client/lead/conversation
links. Owned tab closed and isolated runtime stopped, ports no longer listening.
No audible screen-reader result; pending user-assisted FB009 remains explicit.

Final selected commands (canonical root, disposable SQLite/eager/locmem;
no working DB, live provider, install or full-project E2E):
- `.venv/Scripts/python.exe output/r01-20261014/domain.py`: check, migration drift
  and 47 focused domain tests PASS, unchanged backend inputs reused.
- `.venv/Scripts/python.exe output/crm-toolbars-20261013/browser.py
  desktop-chromium r01-daily-cycle.spec.ts` and `mobile-chromium` equivalent:
  one PASS each at the stamps above, unchanged operational behavior reused.
- `node --test scripts/tests/functional-certification-registry.test.mjs
  scripts/tests/merchant-journey-certification.test.mjs
  scripts/tests/failure-certification-registry.test.mjs`: 3 PASS.
- `npm run check:certification`: PASS, 45 entries/85 router declarations.
  Source-backed pointer repairs are not a fresh full-matrix certification.
Final focus regression: desktop1791927015353280300 and mobile1791927087285237900,
6 PASS each (RU/KK/EN deadline, retry and Escape focus return).
Final isolated build/types/i18n + bundle/env policy PASS via
`.venv/Scripts/python.exe output/r01-20261014/build.py` after the focus fix.
The existing reopened-conversation consumer test1791927130843745800 reached the
new task inspector but failed its obsolete pre-redesign `/tasks/:id` URL check.
Fixture now asserts `/tasks?task=<actual response ID>` and retains description
and readable-status assertions; no Task product change. Rerun recorded below.
Rerun1791927246365375800 PASS (1): `browser.py desktop-chromium
inbox-inspector.spec.ts --grep "task from a reopened"`.
Committed-range gate and publication readbacks are recorded below when complete.
One mistyped browser project
chromium-desktop was rejected before tests; corrected to desktop-chromium.
R01 remains open solely within the named outstanding acceptance boundary;
global FC003/FC008, clinical day, live delivery, D04 policy and R02+ are not closed.
GitHub readback now confirms Settingsc40aff4 CI38467033037 success, together with
the already successful Calendar and Settings receipt runs.

R01 implementation f11fb05f2bc86056c1678a69624de53d23f18029 committed on
codex/ui-testing-toolkit in the canonical folder, normal-pushed origin HEAD:main;
remote main readback exactly matches. Reviewed outgoing range contains only
15 owned files, no private/live data. Unrelated ONEC STATUS7/checkpoint68 remains
unstaged byte-content preserved. Local origin/main tracking ref is stale because
the configured fetch refspec excludes main; fetched FETCH_HEAD and ls-remote
were used to prove ancestry and publication, without changing Git configuration.
Actual-range `.venv/Scripts/python.exe scripts/codex_verify.py --mode static
--base-ref 3d291720b091f77f147bc78d2a908a4a1626972e` PASS after commit (diff
hygiene working/index/range, isolated migration drift/system check).
CI38471830909 is in_progress at publication readback, not PASS. Existing heartbeat
continues only actual CI/receipt monitoring and the pending user-assisted FB009;
unchanged wait stays quiet, no repeated suites/new scope or repeated question.
No own servers or browser sessions remain; all focused check processes completed.
Next: actual CI receipt, then user-assisted audible screen-reader evidence.
Technical scoped publication does not close the outstanding R01 acceptance.

## SETTINGS-ASSIGNMENT-20261014 — Phase2 execution

Primary explicitly transferred the sole writer to PlatformaCRM UI after Calendar
receipt17fb7c1; primary prepares R01 read-only. Mode implementation, gap code/evidence.
Canonical root C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
base17fb7c10f4d9d3935a97050cb128f370a11e2e9d. Starting unrelated ONEC changes
in STATUS/this checkpoint preserved in output/settings-assignment-20261014.
Result: explicit Save assigns the selected role even when the legacy role string
is unchanged; unapplied permissions cannot appear effective or be edited here.
Reuse TeamSection, updateMemberMutation, existing team API and role editor.
Preserve custom assignments; no silent assignment, backend fallback or migration.
Risk: authorization presentation and query refresh. Focused checks: isolated
real-API browser legacy/null assignment, effective permissions and denial, sibling
unchanged, failure/retry, custom-role preservation and editor return. Check RU/KK/EN
desktop/mobile keyboard; one completion build and diff/static checks. Reuse unchanged
Settings/MB evidence; reconcile passport and SETUP-SETTINGS current controls only.
No new notification, BusinessEvent, AI, env or external-delivery behavior.
Delivery: scoped evidence, explicit owned staging, normal push to origin/main,
actual CI readback and bounded writer handback to primary. R01 remains open.

Implementation: compare persisted role FK as well as canonical role; preserve
assigned custom-role identity, keep owner immutable, disable employee role editing
and hide unapplied preview until explicit Save. Await member/auth invalidation.
The neutral RU/KK/EN pending status also works for team viewers without Save rights.
Evidence correction accepted by primary: planned clients list403 was not the
existing API contract. TenantModelViewSet returns200 with an empty denied-business
queryset and detail404; actual-access regression proves visible client/detail200
before, effective permission absent + empty list/detail404 after, and unchanged
legacy sibling access. No server change to manufacture403.
Browser iterations (ignored output/crm-toolbars-20261013):
- browser-1791924318847378800: fixture login shared browser refresh cookie; fixed
  by a separate APIRequestContext for each tested actor.
- browser-1791924561608255800: expected raw503 detail instead of existing normalized
  alert; corrected assertion to the visible error state plus unchanged FK/retry.
- browser-1791924674456775400: exactFK/effective deny passed; list403 assumption
  failed and was corrected to the source-backed list/detail contract above.
- browser-1791924789171465100: RU/KK/EN desktop3 PASS; custom-role editor locator
  was ambiguous across four comboboxes; scope it by the existing role label.
No product permission changes arose from these fixture/assertion corrections.
Isolated build helper output/settings-assignment-20261014/build.py uses
codex_verify.isolated_runtime and Vite policy validation: test:gate-env,
npm run build (types/i18n/production/widget) and check:bundle PASS. An earlier
ordinary build also passed but is not used as isolated environment evidence;
final isolated build repeated after owner-state/copy correction.
SETUP-SETTINGS actions/endpoints/tests and expected outcomes now reflect reachable
controls, not removed developer/billing writes. Scoped outcome/test-path check
PASS and status remains NOT_RUN (contract metadata, never a receipt).
Broader npm run check:certification and its registry test remain FAIL on two
proven baseline gaps: AI-ASSISTANT/redirect_to_agents outcome and business/branches
route. Read-only in-memory import of git show17fb7c1 registry gives the same errors;
router/outside contracts unchanged. Primary accepted these for R01 reconciliation.
This does not block the Settings-specific contract proof or imply full FC003 PASS.
Existing Settings08–09/MB scope retained; no rerun of unrelated pages/backend
suites, no dependency install, live send or working-database migration.

Settings coverage reconciliation (reuse is limited to unchanged inputs):
- Company save/timezone/requisites: existing settings-functional/workflow evidence;
  stored finance controls removed13.10, passport corrected without restoring them.
- Team invitation/revoke/department/login: existing settings-functional evidence;
  branch grants: closed MB evidence. Employee role assignment/editor is this delta.
- Roles matrix/owner read-only/invitation preview: settings-redesign and workflow;
  this regression adds real access, legacy sibling and custom-assignment proof.
- Security audit/login/support filters: settings-workflow; records remain bounded
  by existing history, no wider security or support policy acceptance inferred.
- Three appointment-message scenarios: settings-functional; custom scenarios still
  deferred. Local settings checks do not prove external client delivery.
- Quick reply editor and insertion as draft: settings-workflow; no send.
- Custom fields: settings-workflow full client/lead/deal/appointment consumers;
  Calendar phase rechecked the changed appointment consumer, unchanged others reused.
- Billing deliberately empty and usage from backend: settings-workflow; commercial
  payment controls not restored. Personal notification preferences live in Account.
Sources: [functional](../settings-functional-20261008.md),
[redesign](../settings-redesign-20261009.md), [workflow](../settings-workflow-20261009.md).
SETUP-SETTINGS is a contract inventory, not a replacement for these scoped receipts.

Final focused browser evidence uses `.venv/Scripts/python.exe
output/crm-toolbars-20261013/browser.py <project> <spec> [args]`, whose isolated_runtime
allocates disposable DB/ports and starts canonical-root servers only:
- desktop-chromium settings-assignment.spec.ts: RU/KK/EN3 PASS in the run above;
  those unchanged successful tests reused after the custom locator-only correction.
- desktop-chromium 'settings-(assignment|workflow).spec.ts' --grep
  'assigned custom role|employee opens': 2 PASS, browser-1791924906320098700.log.
- mobile-chromium settings-assignment.spec.ts: 4 PASS,
  browser-1791924906303558200.log. Includes custom-role preservation, owner immutable,
  keyboard Enter/save/retry/editor return and actual member/sibling access.
Desktop RU and mobile KK/EN screenshots inspected: pending status, role control and
Save remain readable/reachable, no horizontal overflow. Other localized screenshots
and automated overflow assertions retained in the same run folders.
`.venv/Scripts/python.exe output/settings-assignment-20261014/static.py` PASS:
isolated manage.py check + makemigrations --check --dry-run, working/index hygiene.
No listener remained on any of this task's six isolated backend/frontend port pairs.
Calendar2f9035b CI38464742290 separately verified SUCCESS; receipt CI still running
at this observation. Settings scoped implementation checks complete; publication below.

Publication: implementation c40aff47c5a3255e216657fbb0b65ab71e064657, normal
origin HEAD:main push and remote SHA readback match. Required committed-range
`.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
17fb7c10f4d9d3935a97050cb128f370a11e2e9d` PASS before push. Reviewed entire owned
index/range and new test; only unrelated ONEC STATUS7/checkpoint68 remain unstaged.
Remote-tracking origin/main is stale because the configured fetch refspec excludes
main; fetched FETCH_HEAD and ls-remote both proved current main17fb7c1 and the
normal ancestor path. No refspec/branch changes or force push.
Actual GitHub CI38467033037 for c40aff4 queued at receipt, not PASS. Calendar
implementation CI38464742290 SUCCESS; Calendar receipt38464828917 in progress.
Local checks are scoped; release/full FC003/FB009, live delivery and deployment
are not claimed. Existing CI only is push-triggered; no deployment workflow.
After publishing this docs-only receipt, UI stops all repository writes and
explicitly hands writer back to primary01a130d8-8f15-7d23-bffc-5e61c21a98e2 for
authorized Phase3 R01. Remaining: selected daily cycle, baseline route/outcome
metadata, actual screen-reader FB009 and primary's bounded Inbox candidates.
Primary must inspect actual CI separately and investigate any subsequent failure;
no pending run is treated as green. No servers/listeners remain from this package.

## TWO-CHAT-COORDINATION-20261014 — owner-authorized CRM workflow

Owner instruction relayed by PlatformaMarket UI: adopt coordinated work by the two
existing CRM chats, keep one repository-wide writer and one strictly read-only
preparer. Mode policy/docs; no Market product requirements or commands imported.
Canonical root/branch/base match CALENDAR-SETTINGS-R01 below. No code, environment,
permission, migration, notification, BusinessEvent or AI contract changes.
Plan/check boundary: reconcile AGENTS, rollover, handoff and existing roadmap;
review links/consistency and working/index/actual-range diff hygiene, no app tests.
Primary remains coordinator/writer and continues Calendar. Existing UI chat
01a1369b-a07d-7701-8832-cbabe7824db5 confirmed read-only Settings preparation on
a8cc789e, no unfinished own writes/servers/index. Its deliverable is existing
coverage, concrete gap/minimal plan, risk-based checks, journal draft and decisions.
It must await explicit writer transfer; preparation cannot close Settings.
The 13.10 no-peer-report procedure is superseded; direct owner scope and
proportional checks retained. Registry/generation unchanged, no chats created
or archived. Single roadmap updated to actual Analytics closure and authorized
Calendar → Settings → R01 order; no automatic R02–R07 or History redesign.
Preserve unrelated ONEC WIP in STATUS/this checkpoint unstaged and unpublished.
Docs published c2e25ff6e3fb2c1159ab7a1518eca24f12432091 to main with normal push;
remote SHA matched. Working/index/actual a8cc789e...c2e25ff diff hygiene and added
relative links PASS. No build/DB/browser for policy-only change. Analytics2474024
and receipta8cc789 actual CI success; governance CI38459212114 separately observed.
Calendar writer remains primary; UI read-only preparation of Settings and R01
received. No execution/ownership was transferred by those reports.

## CALENDAR-SETTINGS-R01-20261014 — owner-authorized sequential work

Owner14.10 explicitly authorized three phases after Analytics: calendar redesign,
Settings coverage reconciliation, then resume CRM-R01 without another routine
approval. Owner now confirmed Analytics completion and requested execution.
PlatformaCRM UI thread01a1369b-a07d-7701-8832-cbabe7824db5 readback: idle/completed;
Analytics implementation2474024 + receipta8cc789 published. Scoped evidence retained,
CI status separate. Current primary unchanged, canonical C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, task basea8cc789e61d3e2d7ceca7cec66c016b8516ad397.
Starting WIP: unrelated ONEC STATUS7/checkpoint68 lines only; snapshot in ignored
output/calendar-settings-r01-20261014. Preserve unstaged and never publish it.
No other active writer identified. Heartbeat settings-r01 retains this same scope.

Phase1 CALENDAR-REDESIGN: implementation, gap UX/functional completeness. Approved
13.10 scenario: month/week toggle, no separate Day screen, compact summaries visible
without opening, delayed hover/keyboard day preview, click opens full side inspector
with all visits/tasks ordered by time; appointment details return to same day.
Mobile click opens full-screen panel; important data never depends on hover.
Reuse CalendarPage/CalendarPicker, API CRUD listAll, shared Drawer/PopoverSurface,
appointment forms/domain actions, permissions, branch catalogue and existing i18n.
Inspect calendar pagination/role/date handling; fix proven omissions in this flow.
No booking policy/permission framework change, no AI/notification/BusinessEvent
expansion, no working-DB migration or external calls. History redesign not included.
Verification plan: focused date/view/grouping tests and critical real-API calendar
flows: month/week boundary, complete paginated data, hover edge/keyboard, day/detail
back/focus, tasks links, branch/service/staff/status filters, booking/reschedule and
permission denial, loading/error/empty. RU/KK/EN desktop/mobile; one final build,
static on actual committed range. Backend tests before dependent code only if
server contract changes. No full-project gate for calendar presentation.
Phase2: reconcile existing Settings contracts/control matrix/evidence with code;
reuse unchanged PASS, test unresolved/changed controls, fix in-scope regressions.
Phase3: R01 bounded daily-cycle acceptance under current contracts/remaining IDs;
record exact unresolved dependencies, including History only if actually necessary.
Do not automatically launch R02–R07, live channels, deployment or paid AI calls.
Each phase gets its own evidence/publication; continue all three as authorized.
Implementation: compact month/week Board, full shared Drawer day/detail flow,
real task links and complete pagination; actor/Business-scoped catalog queries,
permission-gated optional clients/leads/tasks, actual availability count only.
Date picker reuses shared range component in opt-in inline single-date mode;
filters use a compact dialog and shared select. Booking/domain APIs unchanged.
Appointments actions refresh tasks as well for persisted follow-up visibility.
Read-only UI review identified keyboard boundary focus loss while Board unmounted;
fixed by keeping Board mounted with busy state. Local iteration also fixed the
one-frame focus delay between days and ambiguous KK dismiss/action labels.
Focused node command: node --test scripts/tests/calendar-period.test.mjs
scripts/tests/daily-workspaces-policy.test.mjs, 9 PASS. Initial scoped browser
calendar arrows RU/KK/EN desktop PASS (browser-1791922026333799200.log).
New browser test first incorrectly assumed page_size=2 support; server uses50.
Replaced with real51 appointments/51 tasks; second page/full inspector proven.
Next attempt exposed keyboard timing, fixed above; next used the hidden select
test id, corrected to reachable combobox. RU full flow PASS in
browser-1791922761921722900.log; KK then found equal dismiss/action label and
was fixed using existing common.back. Final KK/EN/recovery/role and mobile results
are recorded below. Logs retained in ignored
output/crm-toolbars-20261013; no failure converted to a PASS or ordinary DB mutated.
Settings initial preparation found the passport's obsolete financial-source
location. Follow-up from Calendar role fixture found a concrete uncovered legacy
case: member.business_role=null keeps built-in permissions while TeamSection opens
the fallback preset editor/preview; changing RolePermission alone does not apply
to this member. Read-only UI review confirmed the path and missing actual-access
assertion in settings-workflow. Phase2 now includes its smallest explicit-assignment
fix: enable existing Save for a missing/different assignment even at the same
canonical role string; do not present draft RolePermission as applied or enable
role editing until saved. Preserve assigned custom roles; no silent assignment,
global backend fallback change or migration. Prove exact FK/effective_permissions,
403 after explicit deny, failed save/retry and unaffected sibling legacy member.
Historical Settings08–09 and MB grants evidence otherwise retained. Calendar's
negative fixture now explicitly assigns the tested role before checking denial;
desktop recovery/view-only2 PASS in browser-1791923178596923300.log. Mobile and
full appointment custom-field consumer verification are recorded below.
R01 preparation (read-only): select one daily chain with FC-003 per-control receipts,
reuse unchanged module evidence; FB-009 requires actual assisted screen-reader
evidence (native CUA disabled, Narrator binary exists but not executed). D-04
built-in/user-rule follow-up overlap remains policy-dependent, not automatically
included as an approved duplicate/override behavior. Other R02+ scopes unchanged.
Calendar completion evidence: desktop KK/EN/recovery3 PASS in
browser-1791922899655464000.log; mobile RU/KK/EN/recovery4 PASS in
browser-1791922922734535500.log. Role fixture initially lacked explicit FK,
corrected as above; final mobile recovery/view-only and real branch booking3 PASS
in browser-1791923221482962500.log. Its full-card custom-field case failed because
the legacy fixture omitted a branch; fixed only that fixture to use a branch offer,
assignment and schedule, then enter the full card through the calendar inspector.
Desktop branch booking + custom-field2 PASS browser-1791923470944480400.log;
mobile custom-field1 PASS browser-1791923481677130400.log. Invalid project name
in browser-1791923456710611200.log ran no tests; corrected to desktop-chromium.
Isolated build/types/i18n/widget/bundle PASS build-1791923649658378000.log under
output/multibranch; unchanged dependencies retained. No backend code/API changes,
so no additional backend suite; real API writes above used disposable databases.
Reviewed desktop/mobile week and detail screenshots; layouts and actions fit.
Shared range-mode representative check hit webServer startup120s timeout under
parallel load (browser-1791923582211479500.log), separate rerun recorded below.
Manual helper initially failed on staged-file inventory of removed MonthInspector;
reviewed/staged that deletion, validation then passed. Non-PTY helper stdin closed
after setup and cleaned its own processes; restarted with PTY for CU inspection.
Shared range-mode final PASS browser-1791923720073963200.log: advanced combinations,
invalid/empty recovery, two-date selection, five-day highlight and applied URL.
CU Chrome on own disposable57004/57005: month layout, full day inspector2visits/1task,
service selection, nested Escape (list then dialog), filter and day focus return,
bottom-edge delayed preview and scroll dismissal PASS. Ctrl+plus had no visible
scale change through browser control: 200% zoom is unproven; responsive viewport
checks above stand separately. Test tab closed and helper received stop.
Commands: .venv/Scripts/python.exe output/crm-toolbars-20261013/browser.py
<desktop-chromium|mobile-chromium> <spec> --grep <named scenario>; exact invocations
and bounded logs retained in output. No production/working database or live provider.
Calendar published2f9035bc7ffd6d279c7f7a5193868f01f4ecc85f to origin/main;
normal fast-forward from c2e25ff and ls-remote SHA match. Exact completion gate:
.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
c2e25ff6e3fb2c1159ab7a1518eca24f12432091 PASS (all three diff boundaries,
migration drift none, Django check0). Governance CI38459212114 success;
Calendar CI38464742290 queued at readback, not claimed green. Only CI workflow
exists; no deployment initiated. Own PTY92230 exited0; backend3148/frontend18924
absent; other writers' processes untouched. Remaining dirty blocks are exactly
unrelated ONEC STATUS7/checkpoint68, retained byte-for-byte and unpublished.
Explicit scoped writer transfer after this receipt publication: PlatformaCRM UI
01a1369b-a07d-7701-8832-cbabe7824db5 executes Phase2 Settings coverage and minimal
explicit-role-assignment repair above, passport/control-matrix reconciliation,
focused real-access/denial/recovery checks and one build, evidence/commit/push/CI.
UI must preserve Calendar changes and unrelated ONEC blocks. No backend permission
fallback rewrite, migration, automatic assignment, removed financial UI restoration,
live integrations or R02+ work. UI tracks Calendar CI; a failure is assessed against
its exact snapshot before any in-scope repair or coordinated return of writer.
Primary stops repository writes after receipt and prepares bounded R01 read-only.
UI returns writer explicitly with Git/dirty ownership, checks, processes, publication
and actual CI after Settings; no registry/generation/new task/archive changes.
Next: execute authorized Settings packet, then primary resumes bounded R01.

## ANALYTICS-REDESIGN-20261014 — period-based compact analytics

Owner directly requested Computer Use audit, generated reference first, then full
Analytics UI/UX and necessary backend redesign. Executor: UI continuation
01a1369b-a07d-7701-8832-cbabe7824db5; registered primary/generation unchanged.
Mode implementation; gap UX/calculation/API. Canonical root PlatformaCRM,
branch codex/ui-testing-toolkit, base903405d638f1931dfe93aac44ae30e91354dfffb.
Starting WIP only ONEC pilot STATUS+7/checkpoint+68; snapshots retained in ignored
output/analytics-redesign-20261014. Preserve those blocks unstaged/unpublished.
Browser audit: duplicate heading/subtitle, large KPI/AI banners, disconnected
attention rows, repeated team headings, technical scheduled-report placeholders.
Code: all-time dashboard mixed with default90-day summary; services counted from
one paginated appointment page; CSV client treats queued JSON as a CSV file.
Reference generated before implementation (illustrative data, neutral/emerald).
Owner explicitly accepted event dates: leads created_at; visits start_at;
won deals won_at; money payment/refund time; archived records retained in history.
Operational attention/open queues remain current and are labelled separately.
Reuse existing summary/export routes, permission scoping, financial_report,
work-queue predicates, date picker, UI primitives and i18n. Preserve unrelated
dashboard/AI consumers; no provider calls, money mutations, working DB migrations,
new AI functionality, notification/BusinessEvent changes or overall R01 closure.
Scope: Analytics selectors/API contract, matching exports, compact page with
overview/sources/team/finance views, full server aggregates and unavailable states.
Risk/check plan: focused isolated backend after each coherent selector/API slice;
date/timezone boundaries, distinct conversion, archive, invalid period, role denial,
tenant/resource scope and financial availability; matching export/queue regression.
Completion: affected/dependent analytics/export tests, Django check/migration drift,
RU/KK/EN desktop/mobile and keyboard flows, empty/error recovery, one isolated build,
review owned diff, commit/normal push and actual CI. No full-project local gate.
Implementation: workspace selector via existing summary route view=workspace;
event-time/archived aggregates, distinct cohort conversion, services and scoped
team tables, current queues separate. Existing dashboard/legacy report contracts
preserved. Workspace CSV uses the same selector and existing export-job flow.
Frontend overview/sources/services/team/finance, period/help dialogs, queued
download status, RU/KK/EN copy and shared primitives implemented.
Focused backend: first9 tests had two incorrect fixture expectations (existing
cross-tenant resolver returns400, manager has BUSINESS analytics permission).
Compared current contracts/tests; corrected expectations without weakening scope
assertions. Second10 PASS; export iteration13 PASS. Logs in output/analytics-redesign-20261014.
Completion backend: Django check0 issues, no migration changes, all71 tests across
apps.analytics, apps.core.tests_b5_performance, apps.core.tests_import_export PASS
(backend-completion.log). Isolated runtime, no ordinary database writes.
Build initial dictionary check failed due to new translations before ...ru fallback;
order fixed. Build/types/i18n/widget/bundle PASS (output/multibranch/build-1791919700456122500.log).
Final UI repairs: removed duplicate date presets and silent source truncation;
localized update timestamps and numeric KK dates. Final build/types/i18n/widget/
bundle PASS: output/multibranch/build-1791920362094947200.log.
CU: desktop1440 and mobile390 RU/KK/EN, five tabs, fixture totals and manual55000,
empty2020 period, invalid-date400 -> picker30days recovery, today apply, help Escape
and focus restoration, synchronous CSV PASS. Scoped tables scroll within cards.
One initial locale save was interrupted by navigation; awaited saved state on retry.
Queued CU export initially500: isolated_runtime REDIS_URL=memory:// inherited as
Celery result backend for runserver (tests override it correctly). Disposable
harness restarted with cache+memory://; no application/environment-file change.
Owner reconciled unrelated HEAD a7c8e76 roadmap commit and explicitly authorized
continuing on it. Real fetched main is a7c8e76 (origin/main tracking ref is stale
because configured fetch refspec omits main); use FETCH_HEAD/ls-remote receipts.
Commands: isolated_runtime + manage.py check; makemigrations --check --dry-run;
manage.py test apps.analytics apps.core.tests_b5_performance apps.core.tests_import_export
--noinput; .venv/Scripts/python.exe output/multibranch/frontend.py build.
No full-project local gate, live provider, deployment, working-DB migration or R01
certification; existing backend PASS reused after frontend/docs-only deltas.
Queued CU after harness repair: 202 -> ready/download action reached. Download
then reproduced400 because separate download resource mapping omitted workspace
keys. Added mapping and regression proving200 streamed CSV + foreign Business404.
Post-fix40 tests PASS (apps.analytics.tests_workspace, apps.core.tests_b5_performance,
apps.core.tests_import_export); check0 and no migration drift, backend-download.log.
Browser final download was not repeated after backend fix; API regression verifies
that exact route. No real worker/broker certification; eager boundary only.
Temporary CU servers stopped, no own listeners remain; live5173 tab retained.
Final build inputs unchanged by this backend-only repair; prior build PASS reused.
Diff/links reviewed; unrelated ONEC blocks preserved exactly and unstaged.
Implemented/verified/committed/integrated: 24740241da2f419365c1e9a824caf4e5cd324ccd,
normal push origin HEAD:main succeeded, remote SHA readback matched.
Static runner PASS --base-ref a7c8e76f2de2305d214e1d01ce10b57babd6c71e
(working/index/committed diff, isolated check and migration drift).
Actual GitHub CI run38457642369 in_progress at receipt, not green:
https://github.com/999MAX20/PlatformaCRM/actions/runs/38457642369
Only workflow is CI, no deployment workflow. No deployment claimed.
Scope complete; next product work requires owner direction, R01 stays deferred.

## CRM-TOOLBARS refinement — owner feedback 2026-10-13

Reopens only reproduced UX defects and approved requirement changes after b98381e:
owner screenshot shows lead row action menu outside viewport; checkbox/header and
entity alignment differ, actions drift to far edge, manager picker is native.
Owner rejects duplicated All controls/status-as-filter-button, narrow search and
tall/unclear pagination; explicitly requires identical shared controls across pages.
Mode implementation; gap UX/behavior. Current primary, canonical root,
codex/ui-testing-toolkit, base129f1a30e41b0d57c05f48d9e11afed15b0d223e.
Starting unrelated ONEC notes (STATUS7/checkpoint68 lines) preserved in ignored
output/crm-toolbar-refinement-20261013; no other writer/source delta.
Reuse CrmFilterControls, design-system Select/PopoverSurface, shared pagination;
scope: clients/leads/deals toolbar, lead table/menu/assignment and compact pagination.
Search comparable to global header; one filter entry, status informational only;
scope explicit by entity, quick conditions toggle without a second All control.
Compact footer: total, per-page selection, navigation/range only when multiple pages.
Inspect actual client page-size contract, fix a proven mismatch if necessary.
No calendar redesign, lifecycle/permission change, notification, BusinessEvent,
AI provider call, working DB migration or external effect. Registry unchanged.
Risk/check plan: focused menu viewport/keyboard/focus, manager selection, row/header
alignment, first/last/single page and page-size flows; shared Select change opt-in
for clipped table popovers, existing date picker representative regression retained.
Isolated backend pagination regression before dependent frontend if API fix needed.
Completion: affected RU/KK/EN desktop/mobile real-API browser flows, one build/types/
i18n/bundle, changed contracts/links/diff review, owned commit/normal push/actual CI.

Iteration: client API used default fixed50 despite UI sending page_size. Added
standard bounded ClientPagination (default50/max100) and page-size/last-page/count
regression. Isolated helper `output/crm-toolbars-20261013/backend.py` with
`apps.clients.tests_workspace_filters apps.clients.tests apps.core.tests_workspace_related_filters apps.core.tests_crm_workspace_filters`:
24 PASS, log `backend-1791914734498129900.log`. No lifecycle/auth changes.
Frontend source: unified full-width search, explicit entity scope, toggled quick
conditions, informational status and one filter button; compact footer opt-in on
three pages; bounded portal lead context menu; shared Select opt-in portal/density
for row/bulk assignment/scope/pagination. Header/row checkbox and text alignment
matched, column widths bounded to keep actions near data. First new test
incorrectly counted Columns as a filter dialog;
locator corrected to filter label, product assertions retained.
The next desktop attempt reproduced a product defect: moving to page2 caused the
realtime hook to announce newly visible existing rows as new leads. Its hovered
toast intercepted the page-size control. Baseline now keys by actor/business/list
query and skips placeholder data, so page/filter changes do not announce arrivals.
Keyboard handlers now respect handled events and interactive controls. Assignment
API omits user_id to mean current actor, not unassign: the picker no longer offers
a false unassign choice for assigned leads; unassigned state remains displayable
and selecting an actual member follows the existing assignment API.

Desktop RU refinement PASS (browser-1791915854308086400.log): shared toolbar,
480px search, actual client/lead page10/20 and last page, single-page footer,
manager assignment API readback, keyboard focus/Escape, right-edge menu clamp.
Screenshots inspected at1280/1920. One earlier assignment test assumed unassigned
creation; existing API assigns creator, so fixture now assigns another active
member before testing reassignment. No policy change. Multi-spec helper initially
hit Windows cmd pipe parsing; ignored runner now invokes node CLI directly.
Desktop remaining6 PASS (`browser-1791916046469429000.log`): KK/EN refinement,
RU/KK/EN existing filters/date keyboard/saved views, combinations/empty/error recovery.
Total desktop7 PASS; mobile7 PASS (`browser-1791916527879495800.log`, 5.8m).
All14 browser scenarios PASS against the same source snapshot.
Exact browser command prefix: `.venv/Scripts/python.exe output/crm-toolbars-20261013/browser.py`;
RU desktop args `desktop-chromium crm-toolbar-refinement.spec.ts --config=../output/crm-toolbars-20261013/playwright.config.ts --grep=\(ru\)`;
remaining desktop args `desktop-chromium 'crm-(unified-filters|toolbar-refinement).spec.ts' --config=../output/crm-toolbars-20261013/playwright.config.ts '--grep-invert=consistent.*\(ru\)'`;
mobile args `mobile-chromium 'crm-(unified-filters|toolbar-refinement).spec.ts' --config=../output/crm-toolbars-20261013/playwright.config.ts`.
Config retains prior isolated canonical-source environment, 240s startup allowance
for this host; fixtures/DB/ports disposable, real API, providers and emails disabled.
Mobile RU screenshots inspected: full-width search, consistent filter controls,
compact accessible footer above bottom navigation, no clipped toolbar.

Completion build `.venv/Scripts/python.exe output/multibranch/frontend.py build`
PASS: production app/widget, TypeScript, i18n, bundle budgets. Log
`output/multibranch/build-1791916899790325000.log`. Source hash manifest confirms
all24 owned source/test/contract paths unchanged across final browser/build runs.
Working/index diff hygiene PASS; all intended source and untracked test reviewed.
No dependency reinstall, migration, real provider call or ordinary DB writes.
Full-project E2E/backend intentionally not run: bounded frontend/API pagination
change; affected24 backend tests and14 real-API UI scenarios cover this delta.
Static `.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref 129f1a30e41b0d57c05f48d9e11afed15b0d223e`
PASS on candidate45f4899: working/index/real-range hygiene, isolated migration drift
(no changes) and Django check (0 issues). No full-project certification claimed.
Committed45f48998eb1aef15a7a0cd30505172e388f2191b and normal-pushed HEAD:main;
fetched target was ancestor, remote SHA readback matched. GitHub CI38449140800
observed in_progress (not green) after push. Workflow inspection found CI only,
no deployment workflow. Existing ONEC pilot blocks compared byte-for-text with
starting snapshot and preserved unstaged/unpublished. Registry unchanged.
Authorized refinement complete; calendar remains a separate unstarted phase.
This receipt changes documentation only; app checks remain valid for unchanged
source. Receipt publication uses normal push with exact remote readback.

## CRM-TOOLBARS-20261013 — approved unified filters and date controls

Owner approved all12 recommendations and explicitly requested implementation.
Phase1: clients/leads/deals compact shared toolbar, precise server-side filters,
shared date/range picker in project design system. Calendar week/month/hover/day
inspector redesign is phase2 and is not started by phase1 completion.
Mode implementation; gap behavior/UX. Executor current primary via direct owner
request; canonical C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit,
base33795e273f0c782a143269ced190e49022472921. Starting unrelated ONEC pilot notes in
STATUS/this checkpoint preserved; snapshot output/crm-toolbars-20261013. No peer
approval loop/registry change. One actual writer, affected-path drift checked.

Approved behavior: clients All/WaitingReply, no Mine/New shortcuts or new ownership;
waiting=open scoped conversation with unanswered last inbound, successful human/AI
outbound only clears it, reading/draft/failure does not; handoff separate. Leads
All/Mine orthogonal to All/New/InProgress/Attention; no Hot, unassigned named honestly;
attention=open with missing owner, missing next action or overdue action, reason in
row. Deals All/Mine orthogonal to All/Attention/NoNextAction, existing lifecycle.
Defaults nonarchived clients, unfinished leads, open deals with visible restriction.
Advanced filters: clients source/tags(any/all)/segment/created/handoff/archive;
leads status/owner-or-unassigned/source/created/attention reason/archive; deals
status/stage/owner-or-unassigned/source/amount/created/expected-close/attention reason/
archive. Multi values OR within field, AND across fields; reject invalid ranges/IDs.
Search/quick apply immediately; advanced draft Apply/Cancel/Reset. URL restoration,
personal per-user/business saved views. Counts on same search/scope/advanced boundary,
not loaded page; failed counts not0. Active chips only when needed, no search duplicate.
Search240–280, wide one row, overflowMore preserving selection, two-row phone.
Date control opens on whole field, month/year navigation, range highlight and business
local day boundaries. Existing tokens/UI/API/selectors reused; no new permissions,
clinical data, lifecycle writes, notification/BusinessEvent/AI provider effects,
external calls or working DB migrations. No model migration anticipated.

Verification plan: focused isolated backend after each coherent selector/API slice,
valid/invalid combinations, own/team/tenant visibility, reply delivery semantics,
archive, date/timezone boundaries, multi filters and counts across pagination.
Completion: affected/dependent clients/leads/deals/read-scope suites + system/drift;
focused reachable RU/KK/EN desktop/mobile tests for URL/back, draft apply/reset,
presets, multiselect, keyboard/date/overflow/error/empty; one isolated frontend
build/types/i18n/bundle. No full-project gate absent demonstrated shared risk.
Review explicit task-owned diff, preserve other WIP, docs links/hygiene, conventional
commit and normal push origin main with remote SHA and actual CI readback.

Result: server selectors/API and shared React controls are wired for all three
workspaces. URL/draft/reset/personal browser views/date grid/contextual counts are
implemented; lead rows show grounded attention reasons. Phase1 scoped checks PASS.

Verification (canonical source; disposable DB/ports, existing locked dependencies):
- `.venv/Scripts/python.exe output/crm-toolbars-20261013/backend.py apps.clients apps.leads apps.crm apps.core.tests_b2_roles_queues apps.core.tests_mixed_membership_scope apps.core.tests_workspace_related_filters apps.core.tests_work_queues`: 126 PASS, `backend-1791911852879416700.log`.
- Same isolated helper with `apps.core.tests_crm_workspace_filters`: 3 PASS,
  `backend-1791912264773398700.log`; team/own/denied/disabled/anonymous boundaries.
- `.venv/Scripts/python.exe output/crm-toolbars-20261013/backend-final.py`: focused
  clients/leads/deals workspace + read-scope modules, 13 PASS; `manage.py check`
  and `manage.py makemigrations --check --dry-run` PASS, no drift;
  `backend-final-1791912600380125200.log`.
- Additional count/pagination methods: `apps.clients.tests_workspace_filters.ClientWorkspaceFilterTests.test_counts_ignore_quick_and_pagination_but_keep_search_and_source`, `apps.leads.tests_workspace_filters.LeadWorkspaceFilterTests.test_counts_cover_all_pages_and_ignore_only_quick_filter`, `apps.crm.tests_workspace_filters.DealWorkspaceFilterTests.test_summary_and_board_counts_cover_full_matching_scope` via `backend.py`.
  Leads/deals PASS in `backend-1791913761673988000.log`; clients fixture initially
  assumed configurable page_size=1, but actual default pagination is fixed50.
  Corrected test uses51 matching records and both pages; focused rerun PASS in
  `backend-1791913904685275400.log`. No pagination implementation change.
  Combined affected coverage:132 distinct tests, including16 new regressions.
- `.venv/Scripts/python.exe output/crm-toolbars-20261013/browser.py <project> crm-unified-filters.spec.ts --config=../output/crm-toolbars-20261013/playwright.config.ts`:
  `mobile-chromium` 4 PASS (`browser-1791913196031539000.log`),
  `desktop-chromium` 4 PASS (`browser-1791913470264043600.log`). RU/KK/EN across
  all three pages, URL/back/reload, draft cancel/apply/reset, saved views,
  multiselect, own+quick, status conflict, invalid date/amount, error recovery,
  zero/unknown counts, month/year/keyboard, highlighted five-day range; screenshots
  inspected at both viewports. Initial mobile overflow fixed by clipping the
  hidden width probe; subsequent startup timeout was before assertions. With
  host memory pressure (~64MB free of8GB), ignored isolated config allows240s
  startup; assertions retained, other processes untouched. Final reruns PASS.
- `.venv/Scripts/python.exe output/multibranch/frontend.py build`: i18n, TypeScript,
  Vite app/widget and bundle budgets PASS; `output/multibranch/build-1791913851855203100.log`.

Evidence logs/screenshots and starting unrelated-WIP snapshot remain under ignored
`output/crm-toolbars-20261013`. Relevant application inputs unchanged after PASS.
No working DB migrations, installs, external provider calls or deployment acceptance.
Full-project/local full-E2E omitted per proportional scope; push CI read separately.
Publication: `b98381e525cf02f20e20b0ebde4de193689a38c6` on retained branch
`codex/ui-testing-toolkit`, normal push `HEAD:main`, remote SHA matches. Outgoing
range from33795e2 reviewed,44 explicit owned paths; unrelated ONEC blocks remain
unstaged. `.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
33795e273f0c782a143269ced190e49022472921` PASS (working/index/committed diff hygiene,
isolated system/drift); changed local links/anchors3 PASS, new files/secret review
PASS (synthetic example.test fixtures only). GitHub REST confirms
[CI38442456642](https://github.com/999MAX20/PlatformaCRM/actions/runs/38442456642)
in_progress at receipt; not a green/full-release claim. Connector initially returned
an empty workflow list, so the actual status was read directly from GitHub REST.
Phase1 complete and published; next unfinished scope is separate calendar redesign.

## ONEC-ODATA-PILOT-20261013 — bounded owner-authorized live discovery

Owner approved proceeding with the proposed next step: prepare separate service
access to the already identified company application in 1C Fresh Kazakhstan and
read metadata plus a small clients/catalog sample. Operation/evidence scope;
not implementation of the production connector or financial calculations.
Executor: current non-retired PlatformaCRM UI task under direct authorization.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
clean starting HEAD 33795e273f0c782a143269ced190e49022472921. Registry unchanged.
Target: the owner's authenticated Accounting for Kazakhstan 3.0 application;
private application identifier and credentials stay out of committed evidence.
Allowed external changes: dedicated service access and the minimum published
object set needed for the sample. No business-document writes, CRM imports,
working-DB mutations, notifications, BusinessEvents or AI actions.
Risk/check plan: inspect existing OData settings before mutation; preserve any
existing publication/access; protect the generated credential with Windows
user-bound encryption; HTTP GET only, exact target, no redirects, bounded time,
response size and at most 12 diagnostic API requests (no automatic retries).
Prove authentication, returned schema and bounded sample shape without retaining
customer payloads in Git. A successful read does not prove server-side read-only
permissions, financial completeness or general availability for other 1C editions.
Completion: report verified objects/fields, remaining mapping/access gaps and
retained/revoked pilot configuration. Docs hygiene and secret review; no app build
or database suite for this operational discovery. Production adapter remains deferred.

Discovery so far: exact OData service answered HTTP 401 with Basic authentication
challenge (one unauthenticated GET, no response payload retained). The in-app
browser could not open the endpoint (ERR_BLOCKED_BY_CLIENT); direct bounded HTTP
diagnostic confirmed reachability. A random pilot password was prepared without
plaintext tool output and saved only as a Windows user-bound DPAPI blob in ignored
local operational output. RSA-OAEP transfer key was removed after verified storage;
DPAPI roundtrip and helper syntax passed. No application credential record or
working database was changed. The service account form has not been saved.

Access boundary discovered before save: selecting Counterparties in this
configuration's OData form opens a mandatory dependency confirmation. Dependencies
include employees, individuals, users, attachments, payroll and financial documents,
not merely clients/catalog. Choosing No removes the selected object's checkbox
(`.checkbox.select` disappears); thus this form did not provide the proposed
three-object publication. No dependency expansion was accepted. The same dependency
prompt appeared for Nomenclature and Organizations. Earlier DOM `check=true` is
the checkbox control marker, not checked state; screenshot plus selected class
established the actual state. Do not infer a narrow publication from that marker.

Owner decision requested: restricted access prepared with a 1C specialist,
separate test application, or explicit expanded access to the working application
while our probe remains GET-only. This is an actual permission-scope change under
AGENTS section 2, not a routine peer approval. Authenticated sample and mapping
acceptance remain pending; no production-readiness or read-only-role claim.
Suggested specialist request: for Accounting for Kazakhstan 3.0 in 1cfresh.kz,
provide server-enforced read-only access limited to Counterparties, Nomenclature
and Organizations (plus individually justified dependencies), explain whether the
standard form can avoid its transitive dependency expansion, and confirm the
required Fresh role or audited extension. No request has been sent externally.

Owner follow-up confirmed the integration runtime must be strictly GET/read-only:
no creation, changes, deletion or document posting in 1C. This does not establish
server-side least privilege or resolve the previously requested publication-scope
decision. Additional read-only inspection found the built-in Only viewing profile;
its selected roles do not include OData, whereas the unfiltered role list exposes
Remote access (OData). No role was enabled and no profile was saved. This is not
proof that combining these roles would prevent writes. Specialist consultation
is optional for the permissions question, not a prerequisite to coding a connector.
All unsaved OData setup changes were explicitly discarded; no service account or
object publication was created. Prepared DPAPI credential remains inactive in
ignored local output for possible continuation. In-app session kept open. Only
STATUS and this checkpoint are modified; no production source or DB changes.

## DIRECT-TASK-AUTHORIZATION-20261013 — owner-directed peer tasks

Owner approved removing routine peer permission/reporting between CRM and CRM UI.
Policy-only scope: AGENTS, continuity instructions/hook and focused hook tests;
no product code, ownership transfer, phase, DB, dependency or process changes.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
clean starting HEAD 7d4fc192a0302ac4515eaf9598783a882f9a8866.
Behavior: direct owner implementation request permits the receiving non-retired
chat's bounded work, without primary polling/grant/release/completion messages.
Analysis remains read-only; preserve one actual writer and reconcile concrete
conflicting writes with the owner. Explicit task transfer retains context exchange;
managed primary rollover/retired/freeze protections remain, registry unchanged.
Risk: stale non-primary restriction or accidental bypass of transition guards.
Checks planned: focused node hook/CLI tests, syntax, docs links/consistency and
working/index/actual committed-range diff hygiene. No app builds or database/E2E
suites for this policy adapter. Hook trust remains REQUIRES_REVIEW_AND_TRUST;
unit tests do not prove app runtime activation. No peer tasks launched for receipts.

Verification: `node --test .codex/continuity-hook.test.cjs` — 31 PASS;
`node --check .codex/continuity-hook.cjs` and `git diff --check` — PASS.
Reviewed policy scenarios: both chats' direct requests, read-only limits, compact,
retired sources, pending transitions, validated finalization and unchanged metadata.
Publication limited to the eight reviewed policy/evidence/test files; no product WIP.

## INTEGRATIONS-SIMPLIFY-20261013 — two provider cards

Owner follow-up13.10: previous30b8f55 cards are too large. Approved delta: compact
centered pair, logo/name/status/action only; detailed descriptions/history/errors
inside the existing setup dialog. Primary confirmed sole UI writer again from clean
base5787fe76491ff7107c85ff92b349dc4835afc820, same root/branch, registry unchanged.
Risk: responsive centering, relocated details and keyboard focus. Reuse existing
tokens/setup/API; no backend changes. Verify desktop/mobile RU/KK/EN via existing
focused settings-workflow case, visual inspection and one isolated build; docs/diff
hygiene and normal publication. No new CSS tests, provider calls or full suites.

Compact follow-up verification:
- `.venv/Scripts/python.exe output/multibranch/frontend.py build` PASS, log
  `output/multibranch/build-1791905713712056300.log` (types/i18n/app/widget/budgets).
- Same focused `verify_ui.py desktop-chromium settings-workflow.spec.ts --grep
  "Integrations retains" --project=mobile-chromium` command: first attempt timed out
  starting webServer at120s while build ran, before any tests. Preserved log
  `browser-1791905724331161200.log`. Sequential retry after build: 2 PASS, each with
  RU/KK/EN, log/screens `output/inbox-density-20261008/browser-1791905906477230900`.
  No test assertions/timeouts weakened. Existing dialogs/focus/preferences proved.
- Live desktop and isolated desktop EN/mobile KK screenshots inspected: pair672px,
  compact approximately138px-tall cards, centered; mobile stacked, text uncut.
  Live МойСклад opening/Escape/focus return checked without setup submission.
- Six task-owned files. Backend/data/provider calls unchanged; full/backend/migration
  suites skipped for visual delta. Publication/actual CI receipt follows.

Compact publication: `aaa2d976a9e74a04eae632d172a22b3bc86f2915` normal-pushed
main; remote exact SHA verified. Base5787fe7 matched fetched main. Six reviewed paths,
63 local links, encoding and working/index/actual committed-range diff hygiene PASS.
[CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/38424218319) in_progress
on readback. Scoped writer released; primary/registry unchanged. No next phase.

Owner explicitly approved removing the duplicate page title, subtitle, metrics,
search/filters, financial-source form and all providers except МойСклад and 1C.
Mode frontend implementation; gap visual hierarchy/catalog scope. Reuse existing
ProviderCard setup flows, APIs, shared Button/Badge/Modal and semantic tokens.
Generation5 primary confirmed no competing writers and granted temporary sole
scoped writer to PlatformaCRM UI `01a0f32f-7d02-7263-a53d-496c8f9787f5`;
primary/registry unchanged. Canonical C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, clean starting base `8fda4ccd2550f99edd4fe9f36f767f5dbb7f2cc8`.
Result: exactly two redesigned cards, existing setup actions and real status/error
states, responsive desktop/mobile. Remove only the financial form's page entry;
stored settings and backend remain. No provider launch, external calls, backend,
permission, schema, notification, BusinessEvent or AI behavior changes. Prior audit
findings remain separate; this scope does not certify external integrations.
Risk: lost entry points, wrapping/locales, keyboard/modal focus and error visibility.
Checks: affected page and setup opening/closing in desktop/mobile RU/KK/EN, keyboard,
loading/error/read-only states; one isolated frontend build/types/i18n/bundle.
No new CSS-mirroring E2E, backend/full-project/live-provider suites or migrations.
Review docs/links and working/index/actual committed-range hygiene; explicit reviewed
commit, normal push main, remote readback and actual CI. Release scoped writer at close.

Implementation and evidence, 13.10.2026:
- Page now contains only МойСклад/1C in responsive cards. Existing setup flows,
  loading/no-business/error rendering and manage guards retained. Provider catalog
  outside this page, stored financial settings, imports/backend unchanged.
- User requested an image reference during implementation: built-in imagegen
  generated a preview from the current screenshot. This is an illustrative reference,
  not a runtime screenshot or a new token source. Final code uses exact shared tokens.
- Existing settings-workflow test updated because its financial form was explicitly
  removed. `.venv/Scripts/python.exe output/inbox-density-20261008/verify_ui.py
  desktop-chromium settings-workflow.spec.ts --grep "Integrations retains"
  --project=mobile-chromium` — 2 PASS (each runs RU/KK/EN), log/screenshots
  `output/inbox-density-20261008/browser-1791883568915205400` (log has `.log` suffix).
  Proves two provider entries, removal of financial/search controls, both dialogs,
  Enter/Escape/focus return and unchanged financial/profile API values. Disposable
  DB/ports, disabled providers; no setup submission or ordinary working DB writes.
- Screenshots inspected: desktop RU, mobile KK/EN; live desktop at1536px also
  inspected. Other locale snapshots captured. Existing loading/error/permission
  branches reviewed statically; fault injection/role matrix not rerun for layout.
- `.venv/Scripts/python.exe output/multibranch/frontend.py build` — PASS types,
  i18n, Vite app/widget and bundle budget, final log
  `output/multibranch/build-1791883640443561700.log`. Earlier build also passed;
  final rerun followed a fix aligning the request button's accessible/visible label.
- No backend/migration/full-project/live-provider gate: no corresponding behavior
  changed. Prior integration audit issues (business scoping, generic 1C credentials,
  request/health semantics and live readiness) are not claimed fixed by this layout.
- Eight intentional changed paths, no new tracked artifact. Publication receipt below.

Publication: `30b8f55f1798ed334765a17da88fd2d3974eb007` normal-pushed to main,
remote SHA read back exact. Fetched target matched starting8fda4cc; no merge/rebase.
Working/index/actual8fda4cc..30b8f55 diff hygiene, changed-file encoding,
63 local link paths and docs registration PASS. Existing anchor targets unchanged.
[Implementation CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/38376829919)
observed in_progress (no full-green claim). `gh` unavailable; read-only GitHub API
helper used with the canonical repository URL and exact SHA. Local build/browser
processes finished; normal dev retained. Scoped writer released at closure;
primary generation5/registry unchanged. Next step is owner review, no new phase.

## INBOX-COMPACT-20261013 — approved full-height conversation workspace

Owner approved the generated compact reference and detailed implementation analysis.
Mode frontend implementation; gap layout/interaction. Same registered primary generation5,
canonical C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit, clean
base 7df422d4ccdbc3683186ed7d233aeecb2def45a2. Prior Tasks scoped writer released.
Observable result: edge-to-edge Inbox, 288px list / flexible chat / 320px inspector;
72px normal thread header, 80px normal composer, message typography14/22; inline
AI/templates tools, preserved explicit AI preview/insertion and existing actions.
Inspector docks at1440px; narrower widths use drawer, phones retain list/thread flow.
Reuse AppLayout/WorkQueueLayout, shared Button/Tooltip/ActionMenu/Drawer, API hooks,
i18n and draft/retry permissions. No backend, schema, permission, notification,
BusinessEvent or AI provider-policy changes; no external sends/working-data changes.
Risk: responsive overflow, focus restoration, relocated actions and AI preview,
composer growth, scroll anchoring and retained drafts. Plan: layout then header,
composer/messages; targeted isolated Inbox interaction/locale desktop/mobile tests,
visual geometry on laptop/desktop/mobile and keyboard/zoom, one isolated build/types/
i18n/bundle. Preserve errors/forbidden/safety/retry/attachments; no CSS-mirroring E2E.
Docs/link and working/index/actual range hygiene; explicit reviewed commit and normal
push main with remote/actual-CI readback. R01 remains deferred; no full-project gate.

Implementation and scoped verification complete, 13.10.2026:
- Full-height shell, responsive header/menu, inline tools, bounded composer and
  compact bubbles implemented; AI draft copy now accurately describes preview.
- Existing isolated interactions: `.venv/Scripts/python.exe
  output/inbox-density-20261008/verify_ui.py desktop-chromium inbox-inspector.spec.ts
  --grep "thread menu|AI inserts|switching conversations|context errors"` — 4 PASS;
  same command with mobile-chromium — 4 PASS. Logs
  browser-1791880417218603900 and browser-1791880837673834900 in that output folder.
- New targeted flow: same helper with `desktop-chromium inbox-compact.spec.ts
  --project=mobile-chromium` — 6 PASS, RU/KK/EN desktop/mobile. Final log/screenshots
  browser-1791881055877515400. AI error/retry/explicit insertion/no send, keyboard
  focus, draft retention, inspector reflow and assignment/close/reopen covered.
- Initial runs found template focus restoration and breakpoint ordering defects;
  both fixed. Later EN resize assertion raced React media state; explicit waiting
  fixed the test. Earlier failures retained in output logs, final six cases green.
- `.venv/Scripts/python.exe output/multibranch/frontend.py build` — PASS types,
  i18n, Vite app/widget and bundle budgets; log build-1791881239095610700.log.
- Visual inspection: desktop/mobile plus laptop/tablet reflow, including long
  messages and warnings. Live read-only Inbox at1536x695: header72px, composer78.8px,
  history487.4px versus prior374px (~30% gain), no horizontal overflow. Browser
  zoom shortcut had no effect (DPR remained1.25); actual200% zoom is unverified.
  Responsive768px evidence is not claimed as browser-zoom certification.
- Disposable fixtures/DB/ports and disabled providers only; normal working DB
  not migrated/seeded, no external sends. Backend/full-suite/live-provider gates
  omitted: no backend contracts changed; R01 and deployment remain outside scope.
- All17 changed/new paths task-owned; explicit diff/new-file review, encoding,
  registered docs/links and working/index/committed-range hygiene required before
  normal publication. Publication and actual CI receipt follow below.

Publication receipt: implementation commit `0ca57fb3531ecc1eee12e2b9ca375bac2a3b4a8f`
normal-pushed to origin main; remote SHA read back exact. FETCH_HEAD was starting
base7df422d (origin/main tracking ref is stale because main is absent from fetch
refspec; ls-remote and FETCH_HEAD are authoritative for this publication).
Working/index and real7df422d..0ca57fb diff hygiene PASS;62 local docs links/anchors,
registration and changed/new encoding PASS. Git clean after implementation push.
[Implementation CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/38372395639)
observed in_progress, no green/full-project claim. No further product scope started;
next step is owner review of this UI; R01 still deferred.

## TASKS-REDESIGN-20261013 — approved task workspace and domain behavior

Owner approved both generated references and all task proposals, explicitly requested
implementation, and confirmed this chat as the scoped sole writer. Primary remains
01a130d8-8f15-7d23-bffc-5e61c21a98e2 / generation 5, idle verified natively.
Scoped writer 01a0f32f-7d02-7263-a53d-496c8f9787f5 only; no delegation/parallel writes.
Canonical C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
clean starting HEAD/base e30f990f401ff93a0baf7c59e7b78cb93ac186fc.

Mode implementation; gaps domain/API/UX. Result: usable task list with personal/all
scope, deadline groups, clear counts and optional team view; right inspector opened
only by selection, full-screen mobile and direct task route, links/comments/history,
editable details with draft recovery and explicit actions.
Reuse Task models/services, permission scopes, assignments, notification routing,
activity/audit, idempotency commands, shared UI tokens/primitives and API layer.
Approved delta: waiting state with reason/optional return date, resume; existing
open/in-progress/done/cancelled remain. Overdue is computed, snooze differs from due.
Operator/specialist can create for self; assignment/lifecycle enforce scope and active
available CRM account. Non-login specialists are context, never sole accountable
assignee. Task relations remain optional and individually permission-checked; task
completion never changes linked CRM lifecycle. My=assignee; created/watched separate.
Unified assignment validation, available actions, atomic effects, replay/conflict
handling, consistent business-timezone buckets and summary. Preserve historical
work and custom role overrides; no new permission framework.

Permission impact: scoped task creation and action checks. Notification/activity/audit:
retain routing/preferences and trace lifecycle/assignment; no external sends or new
channels. AI/automation callers must stay compatible with task transitions, no new AI
features. Intentional task schema migration, isolated tests only; working DB migration
requires separate target approval. No seed/reset or changes to other product pages.

Verification plan: focused isolated backend after each coherent slice, lifecycle,
invalid input, role/tenant/entity-access, assignment availability, atomic rollback,
idempotency and concurrent/stale updates; then affected tasks/core permissions,
notifications and relevant AI/automation consumers plus system/drift/migration checks.
Targeted reachable browser flows desktop/mobile RU/KK/EN, draft/error/empty/forbidden
and keyboard states; build/types/i18n/bundle once at completion using existing env.
No full-project gate absent demonstrated shared risk. Docs/index/actual range hygiene,
explicit task-owned commit and normal push main with remote SHA/actual CI readback.
No working DB activation, live provider, release or deployment acceptance implied.

In progress, 13.10 local / 12.10 UTC: domain/API and list/inspector/editor implemented
in the dirty task-owned tree; no publication or working-DB migration yet. Additive
tasks 0011 introduces waiting metadata and optional specialist context. Existing
idempotency receipts and transaction locks are reused; browser command headers are
explicitly allowed by CORS. Custom create permission is checked separately from update.

Focused evidence (canonical installed environment, disposable DB/ports):
- `output/multibranch/run.py test apps.tasks --verbosity 1`: 66 PASS, log
  `check-1791833286031169600.log`, before subsequent custom-create/snooze/CORS checks.
- Latest focused workspace tests: 17 PASS (`check-1791834210820842400.log`).
- `output/multibranch/postgres.py apps.tasks.tests_concurrency`: 15 PASS including
  14 accidentally discovered imported fixtures; concurrent edit itself proved one
  200/one 409 and winner persistence (`postgres-1791833461535984200.log`). Import now
  uses module qualification so the fixture class is no longer rediscovered.
- Frontend TypeScript PASS at initial integration; current final build pending.
  i18n references PASS, 5680 keys at that snapshot.
- Browser attempts preserved: first identified missing action/send translations;
  second textarea exact-label selector was inconsistent after draft rerender (DOM
  and screenshot proved draft intact); corrected to accessible textbox query.
  Third exposed a navigation request dropped while comment refresh was pending;
  guard now queues navigation until the mutation settles. Current desktop/mobile
  RU/KK/EN flow is running. No browser completion PASS claimed yet.
- Migration preservation test initially used historical account state against newer
  unrelated account columns; fixture corrected to current User/Business before
  migrating only tasks. Rerun pending, no migration defect inferred.
- Daily workspace policy checks PASS. Additional action-color suite has two unchanged
  baseline failures in CRMAgentRuntime and BillingSection. The original HEAD test
  against HEAD sources reproduces the same two failures (4 PASS/2 FAIL), recorded in
  `output/tasks-redesign/baseline-action-colors.log`; neither product file changed.
  Do not report this broader suite as green or silently alter those pages.

Next: finish dependent backend and migration checks, browser recovery/permissions/
links/filter coverage and mobile keyboard/visual review, then build/system/drift and
reviewed publication. References approved in owner conversation; fictional mockup
content must not enter working/production fixtures. Remaining primary roadmap paused.

19:56 UTC update: owner separately approved local `db.sqlite3` migration with backup.
`output/tasks-redesign/activate.py` backed up the canonical SQLite DB to ignored
`output/tasks-redesign/activation-20261012T195459Z/db-before.sqlite3`, asserted the
plan contained only tasks 0011, applied it successfully, and proved hashes of every
pre-existing table/column payload unchanged except one django_migrations receipt
(166 → 167). SQLite integrity/foreign keys and `manage.py check` PASS; no seeds.
Migration preservation regression PASS (`check-1791834577165714200.log`).

Dependent backend run found two task regressions among 224 tests: legacy staff/doctor
accidentally inherited new specialist CREATE; AI service request context has no HTTP
headers. Restored explicit legacy task preset and optional version-header lookup.
Both regressions plus workspace scenarios: 19 PASS (`check-1791834818160731500.log`).
Affected completion run is in progress on those fixes; its result is not yet PASS.

Browser lifecycle/draft recovery: desktop RU/KK/EN 3 PASS in
`browser-1791834516699603400.log`; mobile initially exposed shell-header overlap.
Inspector now uses the established drawer layer, mobile body scroll lock/keyboard
containment and drawer-level action menu. Mobile RU/KK/EN rerun 3 PASS (latest browser
log in output/tasks-redesign). Deadline conversion/grouping and daily workspace
policy: 8 Node tests PASS. Remaining: additional filter/link/conflict/permission UI
coverage, visual review, final build/types/i18n/bundle, isolated system/drift and
dependent backend result, docs/diff review and normal publication with CI readback.


20:08 UTC completion evidence, same task-owned snapshot based on e30f990:
- `.venv/Scripts/python.exe output/multibranch/run.py test apps.tasks apps.businesses.tests_access apps.businesses.tests_role_visibility apps.core.tests_b2_roles_queues apps.core.tests_crm_projection_access apps.conversations.tests_inbox_tasks apps.conversations.tests_inbox_context apps.ai_core.tests_crm_tools apps.automations.tests --verbosity 1`:
  225 discovered, 224 PASS/1 SQLite lock skip, log `check-1791834950572068900.log`.
  The skipped competing-writer case previously passed on isolated PostgreSQL.
- Same isolated wrapper with `test apps.branches.tests_staff apps.businesses.tests_member_deactivation --verbosity 1`:
  9 PASS, `check-1791835551922150800.log`; waiting remains pending staff work.
- Same wrapper `check` and `makemigrations --check --dry-run`: PASS/no drift,
  logs `check-1791835313421907900.log`, `check-1791835294344829200.log`.
- `.venv/Scripts/python.exe output/tasks-redesign/frontend.py browser --project=desktop-chromium --project=mobile-chromium`:
  lifecycle/draft RU/KK/EN plus list network recovery/view-only response 8 PASS;
  two new relation-flow tests failed on exact selector `Client` (actual accessible
  name includes selected value), `browser-1791835268323557000.log`. Corrected the
  selector and concurrent fixture to PATCH. No weakened behavior assertion.
- Same browser command with `--grep 'terminal actions|recovery en'`: 4 PASS,
  `browser-1791835491172234700.log`. Proves filtered empty state, created/watching,
  team-to-assignee list, client picker/link navigation, real 409 version conflict,
  retained draft and preserved concurrent description, complete/reopen/cancel/history.
  View-only UI used an explicit available_actions response stub; actual role denial
  and tenant/link masking are covered by backend, not attributed to that stub.
- Final desktop/mobile screenshots visually inspected, including KK mobile; task
  inspector uses drawer stacking/keyboard containment. Final English flow rerun
  includes later draft-guard corrections. No horizontal viewport overflow.
- `node --test frontend/scripts/tests/task-workspace.test.mjs frontend/scripts/tests/daily-workspaces-policy.test.mjs`: 8 PASS.
- `.venv/Scripts/python.exe output/tasks-redesign/frontend.py build`: PASS i18n,
  TypeScript, app/widget build and bundle budgets; `build-1791835502445554600.log`.
  Existing environment/lock reused, no local dependency reinstall.
- Scope contracts/passport/roadmap updated. Local full-project/E2E, target live
  worker/provider/deployment checks not run: no release/live acceptance authorized.
  Two unrelated baseline action-color failures above remain visible and unmodified.

Publication receipt: implementation `4abc60aab9e4b3b572ff93a64d22d3d54909abab`
normal-pushed to origin main from codex/ui-testing-toolkit; `ls-remote` equals HEAD.
Fetched target before publication was e30f990; outgoing range contained only this
reviewed task commit. Local origin/main tracking ref is stale because the configured
fetch refspec excludes main: use FETCH_HEAD/ls-remote, not that cached reference.
All 50 intended tracked/new files reviewed, UTF-8/local Markdown targets and diff
hygiene PASS; no credentials, local DB, backup, generated screenshots or logs staged.
`scripts/codex_verify.py --mode static --base-ref e30f990f401ff93a0baf7c59e7b78cb93ac186fc`
PASS on the committed implementation (range hygiene/system/drift included).

[Implementation CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/38302357789)
is push-triggered on this exact SHA: frontend success, full backend still running at
20:16 UTC readback. This is not an overall CI PASS. Workflow contains checks/tests/
audits, no deployment. Required scoped local gates passed; full local project gate
was not selected. Publication receipt/ownership metadata are a separate docs-only
follow-up, reusing unchanged application evidence; its own CI is reported separately.
Scoped writer released without changing primary/generation or assigning a next phase.
R01 remains deferred. Next operational check is the outstanding CI result; failed CI
must be classified and any task regression corrected before overall CI-green claims.

## R01-DEFER-20261013 — owner defers acceptance until UI completion

Owner explicitly postpones R01 while Tasks, Connections, Analytics and History UI
are unfinished. Settings completeness must be reconciled with existing scoped evidence
before overall acceptance; this is not a finding that previous implementations failed.
Resume acceptance after owner reports readiness. No product implementation or acceptance
suite authorized by this decision. Existing MB/settings evidence remains bounded.
Docs-only contract: record scope change in STATUS/roadmap/checkpoint; same primary,
canonical root and branch, clean starting HEAD `aff9d6f79fa64db6e6ca632d00f08c38dc9074f8`.
Risk: status consistency only. Checks: working/index/committed diff hygiene, local links,
registry/encoding and intended three-file review; no application build/database/browser
checks needed. Publish under standing authorization; no runtime/permission/AI changes.

## CRM-MB01-IMPLEMENT-20261012 — multi-branch implementation before R01

Publication/activation receipt 12.10 18:54 UTC: implementation `b48a82255d7d43b5ae48e340dc38373914835a51`
normal-pushed to origin/main; remote SHA readback matches. Branch retained as
`codex/ui-testing-toolkit`. CI run [38293650008](https://github.com/999MAX20/PlatformaCRM/actions/runs/38293650008)
currently has frontend success and backend running; no final CI PASS claimed yet.
Owner explicitly authorized backup and the three local schema migrations. Verified
online SQLite backup: `output/multibranch/activation-20261012T185321Z/db-before.sqlite3`.
`manage.py migrate scheduling 0009 --plan` showed only branches 0001/0002 and scheduling
0009; `manage.py migrate scheduling 0009 --noinput` applied all three successfully.
Database integrity and existing business-table row counts PASS; no Branch rows seeded.
Initial all-table-count assertion detected expected Django metadata additions, not
business-data changes: 3 migration receipts, 7 content types and 28 permissions.
Read-only follow-up proved every prior content-type/permission row preserved, exact
metadata deltas and zero other count changes (`result.json` in the same ignored folder).
`manage.py check` PASS. Backup remains local/ignored and is not published.


Local acceptance 12.10 18:48 UTC: MB1–MB5 implemented and verified; same owner,
canonical root and branch. Source freeze after branch snapshots revalidated under
Business lock (including approved staff-AI writes), branch lifecycle UI grants and
repeat-booking branch preservation. Publication and working-DB activation are separate.

Completion checks (installed .venv/Node, no reinstall, disposable DB and ports):
- `.venv/Scripts/python.exe output/multibranch/run.py test apps.branches apps.scheduling --verbosity 1`:
  110 discovered, 109 PASS + one PostgreSQL-only skip (`check-1791830469466096300.log`).
- `.venv/Scripts/python.exe output/multibranch/postgres.py apps.branches.tests_concurrency apps.branches.tests_scheduling`:
  11 PASS (`postgres-1791830438569383300.log`), isolated PostgreSQL 17 cluster initialized
  in a temporary directory, stopped and removed. Two prevalidated concurrent creates:
  exactly one 201, one 409, one visit. Fresh price/duration/address and migration schema
  exercised; existing PostgreSQL service/database untouched.
- `.venv/Scripts/python.exe output/multibranch/run.py test apps.ai_core.tests_crm_tools --verbosity 1`:
  19 PASS (`check-1791830659016412000.log`) after final staff-AI write revalidation.
- Earlier affected/dependent 280 run: 264 PASS, 16 FAIL (`check-1791828932304108100.log`).
  Unsaved Resource reverse relation caused 15 failures; one branch test targeted a
  protected serializer field. Fixed, 108-test retry PASS (`check-1791829442055927800.log`),
  superseded in affected branches/scheduling by final 110 above. Unchanged dependent
  lead/Inbox/membership/customer-AI/analytics results retained, not reported as a new
  all-project PASS. No known unresolved required failure.
- `.venv/Scripts/python.exe output/multibranch/frontend.py browser --project=desktop-chromium --project=mobile-chromium`:
  initial completed 10 PASS (`browser-1791830162025730300.log`). Final repeat-booking
  addition: 8 PASS, 2 keyboard-test expectation failures (`browser-1791830532848057600.log`).
  Native time-input segments retain Tab focus; corrected test exercises real button
  Tab/Enter/add/remove. Targeted same command with `-g configure`: 2 PASS
  (`browser-1791830818405450300.log`). Coverage: branch setup, failed-save recovery,
  grants and agent scope persistence, RU/KK/EN booking/reschedule/absence/retirement,
  historical links and repeat branch. Desktop/mobile screenshots inspected.
- `.venv/Scripts/python.exe output/multibranch/frontend.py build`: i18n/TypeScript/app+
  widget/bundle PASS (`build-1791830670238995800.log`). Initial compile errors corrected;
  no frontend runtime changes after this passing build.
- `run.py makemigrations --check --dry-run`: PASS, no drift
  (`check-1791830080962754900.log`); Django system checks passed in final backend runs.
- `.venv/Scripts/python.exe output/settings-workflow/check_docs.py`: changed/new-file
  encoding, existing registry and 168 links/anchors PASS before final receipt update.
  Task manifest reviews 94 source/docs/test paths; credential-pattern scan zero findings.
  Full release/E2E certification, real model calls, external sends and deployment not run.

Migration boundary: branches 0001/0002 and scheduling 0009 are additive schema changes;
first branch adoption is explicit application behavior, not automatic migration seeding.
Working target read-only verified as canonical `db.sqlite3`. At source freeze no working migration had been performed; the separately authorized
activation and backup are recorded above. No seed/reset or branch creation performed.
Outgoing baseline includes prior approved recovery receipt `383bf9a` above origin/main
`198e6a4`; no other writer WIP or unexpected HEAD change. Only CI is configured on push,
no repository push-deployment workflow. Review/stage explicit manifest paths; normal
push to main and remote readback completed in the receipt above; actual CI is tracked separately. R01 remains the next roadmap
phase after this bounded implementation/activation result.

Owner authorizes documentation followed by gradual implementation of CRM-MB01,
then R01. Analysis of models/API/UI/AI/tests on clean `383bf9aea8ca2de04efdf7b33440c5448cfd332a`
completed in this primary. Canonical C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, generation 5 primary 01a130d8-8f15-7d23-bffc-5e61c21a98e2.
No starting WIP; one writer, no worktrees/delegation. Existing dev 8000/5173 is
not a test fixture; no working DB migration, seed, external send or paid AI call.

Mode implementation; gap domain/UI/AI. Reuse Business membership/permissions,
Resource, Service, scheduling services/availability/exceptions, calendar/forms,
Business workspace, contextual team settings, Inbox scheduling/booking pipeline.
Approved: common clients/history, branch-scoped work; multi-interval cross-branch
specialist day with configured travel; branch-specific service price/duration;
single Business timezone; staff retirement/archive preserving historical links.
No new billing, clinical records, equipment capacity or autonomous existing-record
AI mutations. Five branches is acceptance example, not a cap.

Plan: MB1 branch/access/compatibility; MB2 service offers/assignments/intervals/travel;
MB3 absence/retirement/manual review; MB4 reachable Business/calendar/team UI;
MB5 branch-aware AI and integrated five-branch acceptance. Detailed checklist in
current roadmap; contracts in CRM/access/AI are authoritative, this is evidence.

Risks: shared permissions/availability and all booking callers, lifecycle/history,
stale AI offers, migration compatibility, monetary price snapshots, race conditions.
Permission impact: intersect existing permissions with allowed branches for writes;
common history must retain existing sensitive-field/record restrictions. Audit/activity
for changes; branch/address in existing appointment events/messages, no new sends.
AI: scoped public branch/service/staff sources, explicit customer selection, exact
slot revalidation/replay. Intentional schema/data migrations tested only in isolation.

Verification plan: focused isolated backend tests after each coherent domain/API
slice (happy/invalid, permission/tenant, rollback, interval/travel/absence, concurrency,
archived history and migration compatibility); then affected/dependent scheduling,
membership, Inbox booking/AI/message tests plus system/drift. Targeted reachable
browser/API scenarios desktop/mobile and RU/KK/EN, build/types/i18n/bundle once at
completion. No full release gate unless demonstrated shared risk requires it;
no installs with unchanged dependency inputs. Docs links/registry/diff/secret review;
explicit task-only commit, normal push origin main, remote SHA and actual CI.

Current: owner decisions documented; MB1 branch/access API focused 4 tests PASS
(`output/multibranch/check-1791826938767291800.log`). Initial run exposed test expectations around the
project's normalized 500 handler and concealed settings target (404 for specialist);
rollback/state assertions retained, branch read scope explicitly shared. Second run
left only the 403-vs-404 expectation; test now independently proves public branch
GET, denied PATCH and unchanged data. MB2 models/configuration/multi-interval
availability and appointment snapshots implemented; initial combined run 23/24
PASS, remaining test failed in fixture creation (duplicate blank email), fixed
unique fixture email and isolated targeted retry underway. No completed MB checkbox
or full user-facing PASS claimed; UI/AI/compatibility closure remains.

Progress 12.10: MB2 targeted fixture retry PASS (`check-1791827398300436800.log`).
First-branch compatibility 2 PASS (`check-1791827688159136700.log`). MB3 initial
17/18 passed (`check-1791827624367968700.log`): retirement correctly blocked on
the follow-up task created by visit cancellation. Test now proves that blocker,
completes the task through its API and then retires; staff/access 9 PASS
(`check-1791827929839444700.log`). Added explicit future-network grant protection.
Lead/Inbox booking and service-value snapshot paths: 8 PASS
(`check-1791828033488779700.log`). Branch-aware customer AI and existing automatic
booking: 13 PASS (`check-1791828215967667900.log`), including five locations,
remembered choice, address/terms, absence, stale offers and replay. No provider calls.
Frontend implemented WIP: branches workspace, offers/qualifications, multi-interval
week/date schedules, travel, branch booking/reschedule/calendar, staff absence and
retirement review, team grants and agent branch settings. First type check exposed
one number/string slot-counter type mismatch, fixed; final build/browser still pending.
New specialists require explicit branch/service assignment; first-location adoption
alone preserves existing legacy service eligibility. Shared catalog writes now
respect branch scope. Broader affected/dependent isolated regression running.
All changes task-owned, no staging/commit/push yet; same root/branch/HEAD.

## RECOVERY-20261012 — owner-authorized replacement of an unresponsive primary

Owner explicitly asked PlatformaCRM UI (`01a0f32f-7d02-7263-a53d-496c8f9787f5`)
to reconstruct context, archive unresponsive PlatformaCRM
`01a11776-e13a-76c2-9fc0-75d38228f649`, create one local successor named
«Платформа CRM продолжение», verify comprehension and transfer primary ownership.
This is the exceptional recovery in SESSION_ROLLOVER, not an ordinary source-led
handoff and not a new product phase. The coordinator owns only recovery metadata.
Source's attempts remained inProgress with no available response/tool activity;
cause unknown. Native archive returned archived=true; subsequent readback found
source in archived tasks, notLoaded, last turn interrupted. Source was archived
before metadata writes to remove the competing-writer risk; history was retained.

Canonical root C:/Users/user/Desktop/PlatformaCRM; saved project
local-3368c3df041be97f9549005fc6749ad2 still names Desktop/Zani, verified Junction
to the same canonical root. Branch codex/ui-testing-toolkit. Clean starting HEAD
`198e6a44ff092ad9644e3c7a53d3421e3d6872ea` matches remote main. Generation 4 -> 5
initially awaited one successor's comprehension. No existing transition/successor found.
Created exactly one local successor `01a130d8-8f15-7d23-bffc-5e61c21a98e2`
(«Платформа CRM продолжение»); read-only comprehension verified below.
No product, DB, server, hook-definition, dependency or archived-document changes.

Recovered completed scope: docs consolidation/roadmap/passports; Inbox local AI,
manual operator/inspector/relink work; Settings functional, redesign and workflow
changes. Latest Settings workflow: Company single form, financial source in
Integrations, role editor from employee/invitation, personal preferences in Account,
custom fields in full CRM cards, empty quick replies CTA and cleared Billing body.
CRM-MB01 only records the requirement for one Business with several branches
(five is an acceptance example, not a limit); no branch implementation was started.
Access, shifts, timezone, travel and migration policies remain unresolved.
Custom messaging scenarios, external integrations/billing and CRM AI development
retain their recorded deferrals. Local evidence is not production/live-channel admission.

Readback 12.10: CI 38236200299 success on 198e6a4; Settings implementation
CI 37947826093 success on 38be3be and receipt CI 37948418402 success on 16670de.
These supersede earlier pending observations, without rewriting historical receipts.
Source docs evidence records 129 links/anchors, registry/encoding and diff PASS;
actual committed-range `git diff --check 16670de...198e6a4` passed during recovery.
No pending source code edits or observed verification/write subprocesses.
User-requested dev is already running from the canonical checkout: Django 8000,
Vite 5173 (managed sessions of PlatformaCRM UI); do not duplicate or stop them.

Plan/DoD: create exactly one local successor; verify product, latest task, Git,
ownership, evidence and open decisions; register one generation change and retired
source; verify native archive; publish reviewed recovery metadata and notify successor.
Checks are docs/JSON/links/diff and native task/readback consistency. No application
test/install/build is required for this recovery. Old unresolved acceptance remains
unresolved. Next product action requires the owner's separate request in successor.

Release 12.10: successor `01a130d8-8f15-7d23-bffc-5e61c21a98e2` completed
read-only turn `01a130d8-9248-7481-92d2-17357cfa4ddf`. Coordinator checked the full
answer: correct V1/invariants, latest Settings workflow, docs-only CRM-MB01 and
unresolved branch policies, exact root/branch/HEAD and four coordinator-owned
metadata paths, no writes, no new phase, next step wait for release/owner request.
Native source archive readback and interrupted last turn were verified before writes;
no product-writing process was observed and Git remained unchanged except metadata.
Transition key `recovery-20261012-generation4-to5`: incremented once to generation 5,
new primary registered, source retired, transition idle, pending successor/handoff cleared.
This coordinator is not appointed primary; exceptional authority ends with publication.

Checks: `.venv/Scripts/python.exe output/settings-workflow/check_docs.py` PASS
(44 local links/anchors in the final recovery metadata),
JSON identity/generation/source-retirement assertions PASS, `git diff --check` PASS.
Stage only registry/STATUS/project handoff/this checkpoint; index and actual committed
range hygiene required before normal push. No app checks: metadata-only, source CI
already read back success. New push-triggered CI is inspected separately; pending
is not PASS and does not replace the verified source evidence. Publication SHA,
remote readback and actual new CI status are reported in the coordinator's final
receipt. After release notification successor waits for the owner's new task.

## DOCS-MULTIBRANCH-20261012 — один бизнес, несколько филиалов

Запрос владельца: зафиксировать реализацию сотрудников и графиков для одного бизнеса
с несколькими филиалами; пример — одна CRM на пять филиалов. Mode docs-only,
gap requirement/roadmap: записать целевой функционал, не реализовывать его в этом цикле.
Generation 4 primary, canonical root C:/Users/user/Desktop/PlatformaCRM, текущая ветка
codex/ui-testing-toolkit, чистая основа 16670de7c542401cf8ca0b333ab3dd8624fbba65.
Переиспользуем текущие product/CRM/roadmap/acceptance и паспорт scheduling; новый backlog
не создаётся. BusinessMember, Resource, WorkingHours сейчас привязаны к Business;
в просмотренных моделях businesses/scheduling отдельного филиала нет.
Риск документации: выдать план за runtime или неявно утвердить новую матрицу доступа.
DoD: единый ID CRM-MB01, сценарий пяти филиалов, сотрудники/графики/календарь,
критерии будущей приёмки и явные нерешённые политики. Проверки: согласованность,
локальные ссылки/anchors, working/index/реальный committed-range diff hygiene.
Без изменений кода, БД, миграций, разрешений, уведомлений, BusinessEvent или AI;
app build/backend/browser suites не нужны. После проверки — commit и normal push main.

Результат: CRM-MB01 добавлен в product/CRM/acceptance/roadmap; паспорт scheduling
отличает существующее поведение от будущего режима. Пять филиалов — проверочный
сценарий, не лимит. Решения по доступу, сменам, timezone, переездам и миграции данных
не выдуманы; они перечислены перед зависимой разработкой. Код/dev-процессы не менялись.
Проверка `output/settings-workflow/check_docs.py`: PASS, 129 локальных ссылок/anchors,
encoding/registry; ручная проверка согласованности и всего diff — PASS.
`git diff --check` PASS; index/committed-range hygiene проверяются при публикации.
Приложение/БД/браузерные suites пропущены как неприменимые к docs-only scope.
Следующий продуктовый шаг — отдельное назначение CRM-MB01 с решениями из acceptance;
это поручение закрывает только фиксацию требования.

## SETTINGS-WORKFLOW-20261009 — owner review and reachable flows

Owner follow-up explicitly requests a simpler Settings UI plus end-to-end verification.
Reopens prior redesign presentation on owner feedback, not its closed backend policy.
Mode implementation + verification; gap UI/workflow/evidence. Same generation 4 primary,
canonical root C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
clean base 3026debb3b2b9078fc2764dc8f2042a55ee0e90b; no other writer/worktree/delegation.
Observed in browser: custom-field headers misalign because independently sized grids
reserve different widths for action buttons. Live Vite PID 11600 cwd canonical frontend,
backend PID 16584 cwd canonical root; development profile, no Celery worker found.
Read-only inspection of working data; mutation tests use disposable isolated fixtures.

Acceptance: one Company profile/contact form; remove slug/read-only metadata and
appointments/finance/appearance tabs; retain functional timezone, currency, invoice
email, legal name and optional tax ID. Move finance source/connector controls into
Integrations using existing API and existing permission. Hide roles from Settings
navigation, retain contextual role editing from employee/invitation with selected role,
shared-role impact and return path. Personal notifications belong to Account only;
retain default-on delivery and per-user/per-business overrides. Inbox empty quick
replies links to permitted template creation. Custom fields align actions/columns,
explain their actual entity-card placement and prove creation/value persistence.
Security review should make existing events useful, not delete security infrastructure.
Clear Billing UI for future redesign (preserve stored data/API), verify real Usage source.
Category titles shift left relative to section links, desktop/mobile RU/KK/EN maintained.
Owner answer: custom message scenarios DEFERRED; no new trigger/delivery policy.

Reused layers: settings sections/model, business API/form, team catalog/permission API,
Account preferences, Inbox quick replies, CRM custom-field panels, connector API.
No new permission framework, messaging scenario, AI/BusinessEvent change, migration,
working-DB mutation, reset, external send/provider call or deployment. Risk: hidden
fields accidentally cleared, shared-role changes misrepresented as individual rights,
preferences leaking across businesses, lost drafts/return route, CRM field permissions.
Checks: targeted browser/API flows for profile preservation, contextual roles and
return, account preference isolation/defaults, Inbox empty-to-template-to-draft,
custom fields across client/deal/appointment cards, security states, empty Billing,
real Usage API mapping and responsive columns/navigation. Build/types/i18n/bundle at
completion; focused backend checks only if backend changes become necessary; reuse
unchanged domain proof. Diff/links/secret review, explicit commit + normal push main,
remote SHA and actual CI. No full release suite for this bounded follow-up.

Implemented the full authorized UI/workflow scope. Existing custom-field panel was
missing from full entity pages; client reproducer failed before the minimal reuse
fix, then client/lead/deal/appointment create/value/reload flows passed. Working UI
read-only inspection confirms aligned columns/action menu and simplified Company.
Desktop affected suite 24 PASS (`browser-1791557093952829900.log`), including
contextual existing-role edit/return, finance-source retry, per-user/business
notification isolation and Inbox empty-to-create-to-draft without sending.
Final build/types/i18n/app+widget/bundle PASS (`frontend-isolated-final.log`): 5532
locale keys; app shell 325.7 kB, Settings 68.7 kB, largest locale 436.3 kB before gzip.
Changed-doc encoding/registration/local links/anchors PASS. Source/backend,
schema and dependency inputs for earlier domain/system/drift proof unchanged.
Mobile affected suite 24 PASS (`browser-1791557309620003800.log`). One concurrent
desktop security-copy recheck timed out in web-server setup before any test
(`browser-1791557376582185200.log`); sequential retry 1 PASS
(`browser-1791557565093593600.log`), no source workaround or skipped gate.
The failed setup remains evidence; no product failure was reproduced by that attempt.
Mobile Company/custom-field screenshots visually reviewed; viewport overlays on full-page
screenshots are fixed navigation/save controls, not duplicate page blocks.
Pre-publication origin/main readback matched the starting base; preceding implementation/receipt CI
37936423372 and 37936544059 are now confirmed success via GitHub API.
All local acceptance passed; reviewed task-owned source/tests/docs and new files.
No unrelated WIP, credential/config changes, migrations or deployment.
Implementation `38be3be604a545ef486b0b2bf2af0c912f0918ee` committed and normal-pushed
to origin/main; remote SHA matches. Static gate on exact base `3026debb3b2b9078fc2764dc8f2042a55ee0e90b`
PASS, including committed-range hygiene, isolated migration drift and Django system check.
[CI 37947826093](https://github.com/999MAX20/PlatformaCRM/actions/runs/37947826093):
frontend success; backend checks/tests still in progress at final inspection around
15:00 UTC. This is not a CI PASS. All required local scoped checks and implementation
publication are complete; external CI result remains pending. This receipt records
that boundary without claiming release/deployment readiness. No additional product
scope is authorized; custom messaging scenarios remain deferred by owner.
Details: [evidence](../settings-workflow-20261009.md).

## SETTINGS-REDESIGN-20261009 — full Settings interface

Owner explicitly approved implementation across `/settings` using the five generated
desktop references after reviewing the project design system. Implementation/code gap;
reopens presentation and interactions after SETTINGS-FUNCTIONAL closure, not its backend
policies. Generation 4 primary; DOCS-ROADMAP writer explicitly returned the lease after
published `5434296a7826933617b8a8fde940588b58079490`, CI 37835398541 success.
Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
same clean starting HEAD; no pre-existing WIP. Single writer, no worktree/delegation.

Result: coherent Settings navigation and all ten existing sections, clear forms and
lists, contextual role/action/scope matrix and invitation access preview, local errors,
stable save actions, desktop/mobile RU/KK/EN. Reuse semantic tokens v2, shared controls,
drawers, existing API/hooks and real permission catalog. Preserve all four business
groups and saved reference values. Image sample content/validation is not product policy.
Scope: Settings, BusinessSettingsForm and necessary local components/i18n/tests/docs.
No global-shell redesign, permission framework, new policy, migrations, working-DB
seed/reset, provider calls or deployment. Existing tenant/permissions, notification,
BusinessEvent and AI behavior remain; test changed permission editing UI against actual
API. Risks: lost drafts, hidden feedback, misleading permission summaries, mobile overflow.

Verification plan: focused interaction/browser regressions for navigation, drafts,
role permissions, invitation preview and local error/retry; reachable affected sections
and keyboard/desktop/mobile/locales. Reuse unchanged backend evidence; backend changes,
if proven necessary, require focused tests immediately. Completion: build/types/i18n,
bundle, affected browser suite, visual comparison to references, diff/secret review,
explicit-path commit and normal push to main; verify remote SHA and actual CI.
Completed locally 09.10: all ten sections use the Settings layout and local editors,
configured-role action/scope matrix, invitation preview and stable save controls.
Existing permission/preset/custom-role policy remains. Missing permission POST is
now atomic with its audit: reproduced 7-test RED, immediate 11 PASS, then 52 affected
and dependent tests PASS. No schema, notification, BusinessEvent or AI-policy change.
Browser: full affected desktop 16 PASS + mobile 16 PASS; after final mobile width and
role disclosure fixes, affected desktop 6 + mobile 6 PASS; tablet all-sections RU 1 PASS.
RU/KK/EN, API/data assertions, draft persistence, local errors/retry, invitation preview,
POST/PATCH/readonly owner and keyboard/drawer behavior covered. Visual review includes
all ten desktop/mobile sections; final appointment controls fit mobile width.
Build/types/i18n/widgets/bundle PASS; isolated Django check/migration drift PASS.
Exact commands, logs, boundaries and prior failed attempts are in
[consolidated evidence](../settings-redesign-20261009.md).
No full release suite/live provider/PostgreSQL contention/deployment checks; scoped
SQLite/browser evidence does not imply production readiness. Ordinary DB untouched.
All helpers and screenshots remain ignored under output/settings-redesign.
Publication 09.10: implementation `9ea28fe6ff2d8060ea7c09ce7d1d3754fb06f798`
normal-pushed `5434296a..9ea28fe` to origin main; ls-remote matched exactly.
Canonical root/branch/registered writer unchanged. Reviewed all 39 intended files,
including new files; no unrelated work or secret-pattern findings. Working/index/range
hygiene PASS. `.venv/Scripts/python.exe scripts/codex_verify.py --mode static
--base-ref 5434296a7826933617b8a8fde940588b58079490` PASS on committed implementation.
Docs registry/local-link check PASS: 592 links, 15 anchors, no errors; archives and
owner registry unchanged. Git status clean after refreshing identical file metadata.
Only push CI is configured in repository workflows; no deployment performed.
[Implementation CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/37936423372)
was in_progress at publication readback; this is not a CI PASS claim.
Scope implemented, locally verified, committed and synchronized. No next product
phase is authorized; CI outcome remains separate from this local acceptance.


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
