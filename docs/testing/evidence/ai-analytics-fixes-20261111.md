# AI-ANALYTICS-FIXES-20261111

Owner request: fix the two findings from real-provider `/ai-agents` verification,
then repeat API and Playwright with the real provider without changing working data.
Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
starting HEAD `cf66534b9c17f7c5a8b80809b954d226fa17cdb6`. Foreign WIP retained.

Previous scoped readiness fixes stay closed; only the observed analytics plan failure
and total-versus-search-count error are reopened. Prior live evidence remains unchanged:
`output/playwright/ai-agents-live/REPORT.md` and captured synthetic model outputs.

## Implementation

- Analytics uses its own read-only routing contract and strict provider JSON schema
  for supported JSON models (unknown models retain text): exact five keys, historical
  period separate from current-record lookup, no copied workspace fields or counts.
- One additional format-generation attempt is permitted only for an invalid analytics
  plan. The exact same strict parser validates it. Invalid twice stays failed; provider
  and access failures and Work/voice routing do not receive this automatic retry.
- Before retry, current turn, cancellation, permissions and configuration are checked.
  Each actual generation is logged/metered normally; the invalid first response is
  never executed or promoted into an answer. No raw invalid output is added as instructions.
- Lookup context carries distinct permitted non-archived `total_count`, filtered `count`,
  page `shown` and `has_more`. The answering contract explains the scopes and requires
  summary citations for counts; historical period totals still use the existing selector.
- No API response-schema, permissions, notifications, BusinessEvent, migration, frontend
  design or working-environment changes. All fixture/configuration changes are disposable.

## Verification results

Baseline: new8 tests reproduced3FAIL/1ERROR on unchanged product code; missing total
and invalid captured plans confirmed. After source correction8PASS.
Final snapshot: `e67116cd385041dd0d1c135b4958f51c9c0e5483` plus this task's reviewed diff.
Final isolated automated checks: **156 affected/dependent +26 quality =182 PASS**.
System check and migration drift PASS. The156 include13 new routing/count regressions,
conversation API/execution/state/memory, history/grounding, agent runtime, settings,
knowledge isolation, workflows/tools and dependent voice language/policy/direct/booking.
No frontend source changed; no new build/full-E2E/full-project/PG queue gate was needed.

Exact commands use `.venv/Scripts/python.exe output/ai-analytics-fixes-20261111/verify.py`
with the labels recorded in `output/ai-analytics-fixes-20261111/CHECKPOINT.md`.
Logs: `verify-1794411396747000700-0.log` (156),
`verify-1794411580609644700-0.log` (26),
`verify-1794411196948433600-{0,1}.log` (system/drift).

Earlier failures remain recorded, not recategorized as PASS:

- Initial181 aggregate:179PASS/2FAIL in customer-handoff tests. Their old fixture
  lacked configured provider credentials and never reached mocked qualification.
  The separate VOICE-PLANNER task corrected those fixtures in `e67116cd` and added
  assertions that qualification was reached. This task authored none of that fix;
  its subsequent26-test run verified the updated tests.
- An intermediate command named nonexistent `apps.ai_core.tests_runtime_policy`:
  13 actual tests passed, one loader ERROR. Corrected final labels above all passed.
- Text-contract-only live iteration: total/name passed; period plan failed twice.
  `initial-model-outputs.json` and `initial-api-results.json` preserve that evidence.
  This caused the stricter schema change, not a relaxed parser.

## Real-provider API and Playwright

Final disposable SQLite runtime, canonical source, OpenRouter `openai/gpt-4o-mini`.
Credentials read from existing configuration, passed to the isolated process in memory;
no environment files, working data, accounts or deployed services were changed.

| Scenario | API | Playwright |
| --- | --- | --- |
| Total tasks plus exact LIVE-QA-731 record and sources | PASS:2 total, correct name | PASS |
| All tasks created Nov1–11, no name search | PASS:2 | PASS:2 |
| Total plus missing NONEXISTENT-999 | PASS:2 total, no match | PASS:2 total, absent |
| Same idempotency key replay | PASS for all3, same turn/answer | Not needed separately |
| Temporary API503 and explicit Retry | — | PASS: alert, retry, real answer2 |

Seven successful user turns used **15 real calls /32341 provider-reported tokens**;
individual model calls1.44–3.72s. One browser follow-up initially returned an
incompatible intent/read combination and recovered through exactly one automatic
format retry. Strict JSON schema alone does not prove semantic compatibility;
server parsing remains authoritative. No invalid plan executed and no CRM tools ran.
The synthetic database retained exactly2 tasks and0 tool calls after all7 turns.
No external messaging was performed. Cost in currency was not queried.

Artifacts in `output/playwright/ai-analytics-fixed`:
`api-live-results.json`, `final-diagnostic.json`, `provider-calls.jsonl`,
`browser-results.log`, `final-snapshot.txt`, `browser-0.png`–`browser-2.png`,
`recovery-snapshot.txt`, `retry-result.log`, `recovery-success.png`.
Own Playwright session/backend/frontend stopped; disposable DB removed by runtime cleanup.
The initial4-call iteration is separate in `initial-provider-calls.jsonl`.

Both requested findings are closed for this synthetic local boundary. This is not
universal model accuracy, human speech/KK/noise, all-provider compatibility, full D01,
messenger/worker or production acceptance. No migration/API-schema/permission,
notification, BusinessEvent, AI action or frontend design change.

## Publication and documentation

Contracts, CRM-agent passport and D01 roadmap note agree with this scoped evidence.
Other domain/access/integration/operations contracts and README need no change:
no setup, lifecycle, tenant model or deployment behavior changed. Existing acceptance
IDs and broader D01 remain open. Registered evidence; historical reports unchanged.

Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`.
After fetch, origin/main is an ancestor with34 pre-existing outgoing commits.
Task-only local commit is permitted; own-only normal push is blocked by that foreign
range. No push, new CI or deployment was triggered by this task.
