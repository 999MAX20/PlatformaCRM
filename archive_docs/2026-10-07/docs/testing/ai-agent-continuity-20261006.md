# AI-AGENT-CONTINUITY-20261006

## Contract before implementation

Owner approved the complete proposal after PUBLICATION-20261006: fix confirmed
AI behavior defects; durable, scoped memory for Inbox and employee CRM/analytics;
coherent model settings; useful role/tone controls; recoverable action orchestration;
reachable, intuitive UI and scenario/risk acceptance. These are implementation
slices of one authorized result, not additional owner approval gates.

Mode: implementation and verification. Gaps: code and end-to-end evidence.
Owner: registered generation3 primary, canonical C:/Users/user/Desktop/PlatformaCRM.
Branch: codex/ui-testing-toolkit. Starting HEAD/origin main:
ada5874971fbfb5a5992bf43e1ba4043dd802c0a; clean working tree/index, no untracked files.
Prior delivery CI37493625059 SUCCESS; prior real-model acceptance remains failed.

Reuse BotConversation/BotMessage, AgentProfile, knowledge isolation, current AI
provider boundary, CRM tools/domain services, exact approvals, AI jobs, Inbox
pipeline/booking/outbox, permission selectors and existing UI/API components.
No new permission framework, money actions, clinical records, channel integration
or implicit cross-agent/customer/staff memory sharing. No deployment or live
customer messages. Working-DB migrations require their own explicit target scope.

## Behavior and risk

- Model output must become either a validated proposal, a useful clarification or
  a controlled failure; no invalid model payload passed through as a user-input400.
- Both scenarios retain conversation history, bounded retrievable context and
  pending action state. Sources and current permissions override stale memory.
- One agent runtime policy governs generation/classification/planning/analytics;
  settings never imply authority beyond existing actor/capability rules.
- Orchestration records clarification, proposal/approval, execution, completion,
  recovery and cancellation; retries/replays do not duplicate effects. Partial
  completion is explicit. Slots and command versions revalidate at execution.
- UI exposes real threads, progress, questions, proposals and recovery controls;
  supported locales, keyboard/mobile states and saved settings remain coherent.

High-risk boundaries: tenant/actor memory isolation, source revocation, concurrency,
idempotency, stale approvals, untrusted retrieved text and failed delivery. Schema
changes, if needed, are additive and verified on isolated databases. Existing domain
actions retain their activity, audit, BusinessEvent and notification behavior;
memory itself must not trigger business mutations or notifications.

## Verification plan

1. Each coherent backend slice: focused isolated regression tests before building
   dependent behavior. Include malformed/missing input and no-data; tenant/actor
   denial; source/config/permission changes; duplicate/concurrent attempts;
   confirmation, cancellation, stale state and recovery where applicable.
2. Completion: affected/dependent AI, bots, conversations, automation/integration
   suites; system/schema/migration checks via isolated_runtime. Reuse unaffected
   evidence only with unchanged relevant inputs. No ordinary db.sqlite3 writes.
3. UI: focused reachable interactions, loading/error/empty/forbidden/recovery,
   desktop/mobile and RU/KK/EN, keyboard; frontend types/build/i18n/bundle once at
   completion unless a relevant later change invalidates it.
4. Synthetic real-model evaluation: reuse the existing budget ledger and prior
   USD3 cumulative ceiling (USD0.16127360 spent), never reset spending or allow
   unbounded retries. The owner's approved prior discussions include real-response
   retests. No merchant data or external message delivery. Record exact remaining
   coverage and quality limits; no claim of all possible natural-language inputs.
5. Review full task-owned diff/new files, committed-range checks, normal push
   HEAD:main and actual CI readback under standing authorization. No CD.

## Progress

- Initial source inspection: planner trusts provider-shaped arguments until domain
  validation; qualification still contains an obsolete blanket staff-only booking
  instruction, conflicting with the approved controlled-creation contract.
- Implementation and acceptance are in progress; no new checks marked PASS yet.

### Backend checkpoint

- Known planner envelope errors now become validated proposals or localized
  clarification without creating a command. Empty source catalog returns no-data
  without a provider call. Removed obsolete blanket staff-only booking instruction.
- Runtime model policy now covers classification and replies; structured stages
  cap temperature at0.2. Supported existing model presets request JSON output for
  structured stages. Settings changes reject late responses.
- Additive ai_core.0007 introduces scoped AgentConversation/AgentTurn, durable
  state, request idempotency and one running turn per conversation. Extractive
  cited recall never treats previous generated answers as current CRM facts.
- Staff orchestration prepares exact domain proposals, requires confirmation,
  preserves completed steps on partial failure and prepares dependent actions
  only after actual parent results. Cancellation and reset revoke pending work.
- Focused isolated results: planner9 PASS; runtime policy53 PASS; memory/state12
  PASS; execution/state/job-recovery18 PASS. Runs overlap and are not summed.
  First planner fixture selected a nonexistent task and correctly returned403;
  corrected fixture passed. First memory run reproduced SQLite Cyrillic LIKE
  case handling; implementation fixed and rerun passed.
- Commands use `.venv/Scripts/python.exe output/ai-agent-continuity-20261006/verify.py
  test <labels> -v 1` with scripts.codex_verify.isolated_runtime. Exact labels and
  first failures remain in the corresponding local ignored logs. API integration
  checks are running in conversation-api.log. No working-DB migration or live
  model request has occurred in this phase yet.
- Remaining: finish API permission/recovery checks, integrate Inbox recall and
  replay/stale-message protections, implement thread/settings UI and i18n, run
  affected/dependent and browser gates, synthetic real-model acceptance, update
  contracts and normal publication with actual CI. Full authorized scope continues.

### Continuation checkpoint — first hour

- API/execution/memory integration: 16 PASS (`conversation-api.log`). Inbox
  integration: 22 PASS (`inbox-continuity.log`), covering inbound dedupe,
  out-of-order input, new input during qualification/reply, queued stale reply
  suppression and existing booking. First run exposed a booking fixture that
  inserted the selection before the offer; corrected chronological setup passed.
- Inbox recall now feeds qualification/reply/scheduling. Delivered outbound
  messages carry source fingerprints. Each inbound has one durable attempt;
  no repeated model calls or delivery on replay. Existing outbox retry remains.
- CRM/analytics conversation UI is implemented and types PASS; visual/browser,
  localization and recovery verification remain. Settings expose memory control.
- Working-DB migration authorization requested with exact additive0007 scope and
  backup; pending answer. Continue isolated checks independently. No working DB
  change, external message delivery, live-model spend or publication in this phase.
- Remaining authorized work includes Inbox memory reset controls, dependent gates,
  real-model retests, UI acceptance, contracts and normal push/actual CI.

### Runtime and reachable-flow checkpoint

- Owner explicitly approved working local migration with backup. Applied exactly
  ai_core.0007 to canonical db.sqlite3; backup:
  `output/ai-agent-continuity-20261006/working-before-20261006T174330Z.sqlite3`.
  Existing data in114 tables preserved. First strict comparison flagged Django's
  expected new content types/permissions; follow-up proved existing rows unchanged,
  exactly2 content types and8 permissions added, new memory tables empty, SQLite
  quick_check and foreign_key_check PASS. No seed/reset was performed.
- New controls: Inbox memory clear preserves messages and revokes late reply;
  reset API rejects a foreign user. Controls run28 actual tests PASS but invocation
  exited1 for an incorrect deletion test label; corrected `apps.bots.tests_deletion`
  plus new turn-cancellation test:5 PASS. Memory/grounding31 PASS; subsequent
  route/no-data/period regressions40 PASS. Logs preserve the initial failures.
- Frontend build/types/i18n/widget PASS before browser recovery-button fix.
  Desktop browser first run: action-review contract PASS; real persistence flow
  exposed retry button also submitting its form (three requests instead of two)
  and SQLite concurrent write failure. Fixed button type, serialized SQLite
  conversation writes, removed unconditional writes during ordinary history polls;
  affected browser/backend checks are running again.
- First real-model continuity evaluation:21 cases,38 calls,3 new failures;
  prior six recorded failures PASS. Client→task separate confirmations and pronoun
  follow-up, task create/replay/correction, Inbox deep recall PASS. New failures:
  generic task invented a title, period query routed to current CRM instead of
  history, contradictory no-data response cited a record. Added focused fixes;
  the three-case real-model rerun is active. Manual review also found unsolicited
  booking prompts and product/service price conflation in some tones: reduced
  scheduling context for non-booking questions and strengthened entity-price rules.
- Cumulative budget ledger is unchanged:522 paid calls,USD0.20137475 before rerun;
  bounded request guard raised to750 for the approved additional evaluation,
  monetary ceiling remainsUSD3. No live customer/provider channel messages.
- All authorized scope remains active. No commit/push yet. Pending: dependent
  backend result, live retests/semantic review, desktop/mobile controls/settings
  and analytics browser checks, final affected build/checks/contracts/publication.

### Acceptance checkpoint — 18:13 UTC

- Three real-model failures now PASS (11 additional calls): clarification,
  deep recall/reset and analytics-period continuation. Earlier six regressions
  remain PASS. No external channel delivery was attempted.
- Dependent backend363 ran with two failures: the prior stale-response fixture
  had no sources (provider correctly bypassed); replay returned original created
  flags despite doing no new writes. Fixture now uses actual scoped context and
  asserts provider invocation; replay returns false creation flags. Focused23
  workflow/controlled-creation/Inbox tests PASS. No assertion was weakened.
- API pagination5 PASS: older threads remain reachable and foreign-owner threads
  remain excluded. Scheduling continuity20 PASS includes retained specialist,
  explicit replacement and selecting any specialist. Current price/date selectors
  remain authoritative; no new date inference was introduced.
- Desktop continuity2, mobile continuity2 and analytical report1 PASS. Screenshots
  inspected; RU/KK/EN, keyboard focus and accessibility covered. Initial selector
  ambiguity was narrowed to message history. A run crossing the list API change
  is invalid evidence; fresh coordinated servers passed. Analytics failure test
  selects a new report period to trigger a request instead of reusing cached data.
- Existing scenarios2/3 PASS exposed invalid aria-label on empty generic div;
  assigned role=log and rerun remains. Settings run failed before test body at
  server startup120s while multiple isolated servers/builds competed; retry runs
  after those operations finished. No product assertion/time limit was relaxed.
- Build/types/i18n/widget and bundle PASS before final accessibility/status edits;
  isolated system check and migration drift PASS. New analyst-status regression
  checks independent permission and disabled-analyst readiness; running now.
- Remaining: final affected browser/settings/Inbox reset and readiness checks,
  final build, diff review/contracts/commit/static gate/push and actual CI.
  Working backend has not yet been restarted. Publication is still pending.

## Local completion evidence — 2026-10-06

All approved implementation slices are complete and locally accepted. Publication
and actual CI are recorded separately below; local PASS is not deployment.

| Boundary | Evidence |
| --- | --- |
| Backend dependency run | `verify.py test apps.ai_core apps.bots apps.conversations apps.automations -v 1`:363 tests,361 passed,2 failures preserved in `dependent-backend.log`; both fixed and regression gates below passed |
| Dependent corrections | `apps.ai_core.tests_workflows apps.bots.tests_controlled_creation apps.ai_core.tests_inbox_continuity`:23 PASS (`dependent-regressions.log`) |
| Source/title privacy and paging | `apps.ai_core.tests_conversation_api`:8 PASS after final title-redaction fix (`concurrency-drill-final.log`); title uses first-turn visibility, not later unrestricted messages |
| Analyst permission/configuration | API/workflows/agent-runtime22 PASS (`status-permissions.log`); API/execution14 PASS including read-only analytics (`analytics-readonly.log`) |
| Inbox/scheduling continuity | Inbox/automatic-booking/preview20 PASS; runtime-configuration/Inbox/automatic-booking19 PASS after final qualification instruction (`booking-review-regressions.log`) |
| Concurrent delivery | Disposable file-backed SQLite:3 simultaneous duplicate sends and1 simultaneous exact confirmation PASS, one turn/job/domain action each; no real model calls. Driver `output/ai-agent-continuity-20261006/concurrency-drill.py` |
| Desktop Chromium | Continuity2, analytics1, settings4, final existing scenarios3 +Inbox reset1 PASS; actual message IDs unchanged after reset |
| Mobile Chromium | Continuity2 and analytics1 PASS; RU/KK/EN, focus, horizontal overflow and axe checks in conversation/scenario flows |
| Frontend | `npm run build` (i18n5304 keys, types, application/widget builds) PASS in `frontend-build-completion.log`; `npm run check:bundle` PASS |
| System and schema | Isolated `manage.py check` and `makemigrations --check --dry-run` PASS, no drift; migration0007 exercised by every fresh isolated database |
| Real model | Latest full21-case run20 PASS/1 false escalation; corrected qualification distinguished ordinary slot consent from exceptional human handoff. Focused2 booking cases then PASS,7 calls. All21 scenarios have current passing evidence; no mandatory review flag is overridden |

Exact focused commands use `.venv/Scripts/python.exe
output/ai-agent-continuity-20261006/verify.py test <labels> -v 1`.
Browser commands use the existing isolated helper
`output/ai-agent-isolation-20261005/verify-ui.py <project> <spec> --output=<path>`;
each log records the exact arguments. The final desktop batch includes
`ai-agent-scenarios.spec.ts` and `ai-inbox-memory.spec.ts`. No dependencies were
reinstalled. Unchanged broad passing tests were reused; only affected regressions
were rerun after their fixes. CI provides the fresh integrated full test result.

The first concurrency helper incorrectly invoked an interactive Django shell;
its exception-filled log and printed PASS line are invalid evidence. Corrected
`shell -c` execution fails on assertions and produced the successful result above.
No failed attempt was discarded or reclassified as a passing run.

Real-model evaluation used the existing cumulative ledger:580 calls,
USD0.26152530 charged/reserved, unchanged USD3 ceiling. Command:
`.venv/Scripts/python.exe scripts/ai_behavior/run.py --suite continuity --live
--max-calls 750`; final affected rerun adds `--case-filter '^booking-'`.
Synthetic records only. Website transport receipt is controlled; real messenger
delivery, production workers, Firefox/WebKit and universal natural-language
correctness are outside this evidence. Model quality remains probabilistic.

Own canonical backend was refreshed; localhost8000 health and5173 frontend return
200. Local backend uses process-only `AI_QUEUE_LIVE_REQUESTS=False`: no local
worker was found and one existing pending daily_summary is deliberately untouched.
`.env`, production queue defaults and other writers' processes are unchanged.
No working data was seeded/reset; only the separately approved additive migration
was applied. Final backend refresh after the qualification correction is recorded
with the publication receipt. No CD or external channel messages.

## Publication receipt

- Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch
  `codex/ui-testing-toolkit`, same registered generation3 owner. Reviewed71
  task-owned paths,3566 insertions/141 deletions; no unrelated work included.
- Application commit `c750d16180fdb803f61261a9fb40c9ad838c8b30` passed
  `.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
  ada5874971fbfb5a5992bf43e1ba4043dd802c0a`. This includes the actual committed
  range, source checks, migration drift/system checks and final diff hygiene.
- Normal fast-forward `HEAD:main` push succeeded. Independent `git ls-remote`
  returned exactly the intended SHA. Working tree was clean after publication.
- [Application CI37511802600](https://github.com/999MAX20/PlatformaCRM/actions/runs/37511802600)
  was queued at receipt time, not yet PASS. The final documentation receipt also
  triggers CI; its exact SHA and final CI readback are reported in the task's
  completion response and `output/ai-agent-continuity-20261006/final-ci-receipt.json`.
  No full delivery claim is made while required CI remains pending.
- Final owned backend parent17796 runs the canonical checkout with local inline
  AI; HTTP health200. Existing pending daily_summary remains untouched. Frontend
  source is canonical Vite5173. Working migration/data preservation evidence above
  is unchanged. Only CI is configured for this push; no CD/deployment was started.
