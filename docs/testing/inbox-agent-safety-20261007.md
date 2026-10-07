# INBOX-AGENT-SAFETY-20261007

## Contract before implementation

Owner authorized client-agent safety and configurable risk behavior on 7 October.
CRM/Analytics development is paused; preserve existing implementation and settings.
Canonical root C:/Users/user/Desktop/PlatformaCRM; registered generation3 owner;
branch codex/ui-testing-toolkit; clean starting HEAD
9fabae07e96c14ff52ae9deb11bfb76d781b5626. Prior application and receipt CI completed
SUCCESS (37511802600/37511999334); this does not certify the new changes.

Mode: implementation + verification. Gap: safety policy, enforcement and evidence.
Result: customer AI stays within business purpose, protects private information,
limits abuse and provider attempts, and hands off visibly with safe recovery.
Reuse Inbox lifecycle, existing handoff/notifications/audit, durable inbound turns,
provider boundary, agent configuration and knowledge ownership. No new channel,
deployment, billing rules, working database migration or analytics expansion.

## Approved policy and bounded implementation

- One short safe off-topic answer, then a boundary answer, then AI pause/handoff
  on the third off-topic question. Greetings/thanks do not count. Security and
  personal-record requests do not receive a free disclosure attempt.
- Owner selected 30 provider calls per conversation per24 hours, no new business
  cap. This is a technical attempt limit, not commercial billing. Reservations
  occur before provider calls; uncertain/failed calls retain their reservation.
- Personal-record lookup by a supplied name is not identity proof. Hand off
  ambiguous/existing private-record requests without confirming record existence.
- Mandatory tenant/secret/privacy/action restrictions cannot be disabled through
  settings. Optional behavior may be stricter; recovery requires authorized staff
  and cannot erase the rolling usage ledger. Incoming transport remains available.
- Numerical burst/length controls are engineering protections, configurable in
  bounded ranges; record exact defaults and behavior with completion evidence.

High-risk boundaries: confidentiality, concurrent admission, superseded answers,
configuration changes, duplicate delivery, recovery and existing booking behavior.
Any additive schema is tested in isolation; working migration needs separate scope.

## Verification plan

1. Focused isolated service tests after each coherent backend slice: invalid
   configuration, permissions/tenant isolation, zero-call refusal, exact thresholds,
   retries/concurrency, no stale action/reply and recovery without budget reset.
2. Privacy/attack fixtures with synthetic sentinels: inspect actual model inputs,
   outbound text and domain changes; secrets or other-client records must not leak.
3. Affected/dependent bots, conversations and ai_core tests; isolated system/schema
   checks and migration tests. Do not call external models or messaging providers.
4. Reachable settings save/reload/denial and Inbox handoff/recovery on desktop/mobile,
   RU/KK/EN where affected; frontend build/i18n/types and bundle at completion.
5. Review all changes, static committed range, normal push HEAD:main and actual CI.
   No full local E2E or dependency reinstall without demonstrated need.

## Progress

### Pause requested by owner — 7 October 2026, 00:51 local

Owner asked to stop and save a checkpoint because usage limits are running out.
Do not continue implementation until the owner resumes. This is the same task and
registered primary, not a handoff or a completed phase. No commit/push was made.
HEAD remains 9fabae07e96c14ff52ae9deb11bfb76d781b5626 on codex/ui-testing-toolkit.
All current modified/untracked paths belong to this task; starting tree was clean.
The exact stopped path inventory is output/inbox-agent-safety-20261007/paused-paths.txt.

Implemented locally, still awaiting completion acceptance:
- Durable safety state and rolling provider-attempt reservations; admission before
  calls, off-topic progression, burst/repeat/length controls and privacy handoff.
- Reduced customer model context, input/output guards and explicit customer-visible
  knowledge. Private CRM knowledge remains separate; existing shared knowledge requires
  explicit customer-use review. Materials owned by Inbox agents retain their audience. Shared connection permission is explicit.
- Authorized Inbox recovery preserves usage; draft settings and recovery UI with
  RU/KK/EN strings. Browser/save/reload acceptance has NOT been performed.
- Additive migrations ai_core.0008_customer_knowledge_visibility and
  bots.0011_botconversation_ai_safety_state exist and ran in isolated test DBs only.
  Working db.sqlite3 has NOT been migrated; do not use normal localhost as proof
  of the new feature until migration scope is explicitly approved.

Current configurable defaults: allow first off-topic answer; handoff after 3;
30 calls per rolling 24h; 12 messages/minute; 4000 message characters; repeat
handoff threshold 3. Config bounds: off-topic 1–3, calls 1–30, burst 3–30,
length 256–8000, repeats 2–10. These require final UI/behavior verification.

Focused isolated evidence (overlapping suites; do not sum as unique tests):
The command prefix for each row was
`.venv/Scripts/python.exe output/inbox-agent-safety-20261007/verify.py test`;
append the listed modules and `-v 1`. The wrapper uses codex_verify.isolated_runtime,
not the working database. Logs are under output/inbox-agent-safety-20261007/.

| Modules | Result | Log |
| --- | --- | --- |
| apps.bots.tests_safety_state | 16 PASS, 0.544s | safety-state.log |
| apps.bots.tests_customer_safety apps.bots.tests_safety_state apps.bots.tests_runtime_configuration apps.ai_core.tests_inbox_continuity | 36 PASS, 4.226s | customer-boundary.log |
| apps.bots.tests_safety_recovery apps.bots.tests_customer_safety | 17 PASS, 1.118s | recovery.log |
| apps.bots.tests_customer_knowledge apps.ai_core.tests_knowledge_isolation apps.bots.tests_readiness apps.bots.tests_safety_recovery | 28 PASS, 17.853s | knowledge.log |

Earlier PASS predates subsequent related slices; repeat affected tests at completion.
No full acceptance, frontend build, browser gate or new CI PASS is claimed.
No external model/provider calls or messaging delivery were used in these checks.
At pause no verification processes remain. Existing canonical local servers remain:
frontend PID15372; Django parent17796 / child13668. No processes stopped; server
health with the pending working schema is unverified. No automatic continuation.

### Resume from this point

1. Read this checkpoint, STATUS and primary registry; verify same root/branch/HEAD
   and stopped path inventory. Preserve the current uncommitted implementation.
2. First unfinished step: inspect customer preview (`apps/bots/ai.py`, preview API
   and AIAgentPreview) and qualification prompt against the new safety contract.
   Verify first permitted off-topic answer is consistent with the system prompt,
   private/security requests always hand off, and preview cannot bypass guards.
   These are unfinished review items, not yet established defects.
3. Finish adversarial and concurrency/retry coverage; add migration preservation
   coverage for pre-existing knowledge/conversations. Re-run affected/dependent
   bots/conversations/ai_core/automations suites and isolated system/schema checks.
4. Finish settings/recovery UX (including next-call availability), inspect reachable
   desktop/mobile RU/KK/EN flows, then run frontend build/types/i18n/bundle once.
   Review fixture changes for explicit public knowledge; do not weaken assertions.
5. Update AI/product/CRM contracts and final evidence. Any working migration needs
   its separately approved target and backup/data-preservation procedure. Analytics
   stays paused without deletion; no expansion, real-provider evaluation or CD.
6. Only after required acceptance: review explicit paths, commit, normal-push
   HEAD:main under standing authorization, verify remote SHA and actual CI.

At the owner's pause, only checkpoint documentation is being finalized. Product
implementation and further tests are stopped; this unfinished patch is not published.

Checkpoint hygiene: selected documentation diff is clean. Whole working-tree
`git diff --check` reports trailing spaces in apps/bots/tests.py:808 and
apps/bots/tests_readiness.py:70,250; retained for cleanup on resume. This is an
open hygiene failure, not an application-test failure or a passed final gate.

### Resumed by owner — 7 October 2026

Owner requested checkpoint analysis and continuation of this same task. Root,
branch, HEAD, registry and dirty path inventory match the paused state. Reuse
existing implementation. Next coherent slice: preview safety and trusted courtesy
prompt flag; focus on zero-call private/security rejection and fail-closed
classification. Then migration/concurrency and dependent gates, UI acceptance,
contracts/publication. No analytics expansion or working migration is inferred.

Resume evidence: preview-resumed32 included one assertion failure exposing a
saved-language mismatch in deterministic copy. Fixed safety copy to use the active
profile language; preview-final37 PASS. Migration-state12 had11 PASS and one fixture
error (historical model state omitted an unrelated accounts.auth_epoch migration).
Corrected the fixture to use all actually applied migrations; migration-final1 PASS.
Concurrency/system/schema driver verify-concurrency.py PASS: four simultaneous
reservations at29/30 admit exactly one, total30; next attempt denied. SQLite reserves
the writer before reading counters, matching the existing staff-conversation pattern.
These are mocked provider/isolated DB results, not production or model-obedience proof.

### Resume checkpoint — 7 October, 21:32 local

Backend acceptance: initial affected/dependent `test apps.bots apps.conversations
apps.ai_core apps.automations -v 1` ran404:394 PASS and10 failures. Nine were legacy
public-knowledge readiness fixtures (including the safe runtime check command);
one expected linked private CRM fields now intentionally excluded. Updated explicit
fixture audience and the privacy assertion; recheck-backend.py10/10 PASS,23.769s.
No assertion was weakened to bypass protection. Subsequent concurrent duplicate
inbound drill reproduced SQLite database-is-locked at admission. Reused the safety
Business writer reservation before reads in run_inbound_once. Focused Inbox/recovery
13 PASS; final dependent `test apps.bots apps.conversations
apps.ai_core.tests_inbox_continuity -v 1`194 PASS,231.053s. Other unchanged AI/automation
coverage from the404 run remains applicable. Updated lower-limit expiry test passes.

Final verify-concurrency.py: Django check and migration drift PASS; isolated clean
migration PASS; four simultaneous admissions at29/30 allow exactly one; simultaneous
duplicate inbound creates one durable turn without request failure. No model calls.
Migration preservation1 PASS on historical models (migration-final.log).

Browser initial desktop had a test wait aimed at PATCH instead of the actual atomic
PUT configuration endpoint, and a seeded agent lacked a bound profile for resume.
Corrected test setup/wait; desktop2 all3 PASS. Build initially caught new translated
keys placed before the Russian fallback spread; corrected dictionary order. Build,
types/i18n5324 keys, widget and bundle PASS (build-final.log/bundle.log). Mobile's
first server startup timed out120s while build/backend competed; no test body ran.
Retry after those jobs ended: mobile2 all3 PASS,1.9m. No installs/assertion weakening.

Visual inspection found clipped Inbox mobile controls despite functional PASS.
Added min-w-0 only to the affected thread-pane caller and a viewport-bounds assertion.
This requires final targeted desktop/mobile and a completion build after this CSS
fix; these are PENDING. Updated existing shared-knowledge isolation browser test to
exercise the new consent checkbox. Desktop-final selected settings/locales, Inbox
and shared-isolation checks currently running. No broad new audit.

Owner explicitly approved working db.sqlite3 migration with backup on7 October.
Prepared read-only plan matched exactly bots.0011 + ai_core.0008. Applied successfully
with output/inbox-agent-safety-20261007/migrate-working.py --apply. Backup:
output/inbox-agent-safety-20261007/working-before-20261007T162730Z.sqlite3 (ignored).
All original data in117 tables matched the backup; empty initial safety state and
expected knowledge audience, quick_check and foreign_key_check PASS. No reset/seed.
Earlier server PIDs were absent and8000/5173 free. Started canonical backend6316
(local AI_QUEUE_LIVE_REQUESTS=False, previous local inline policy), frontend16012.
Need HTTP health readback; do not stop other processes. Working migration log retained.

Fetched origin/main explicitly:9fabae07 equals current HEAD; only ci.yml exists,
no push-triggered CD. No commit/push yet. Finish visual correction checks, source/
secret/diff review and task manifest, update current status, normal publication and
actual CI. No paid provider calls, real messenger delivery or production acceptance.

### Completion acceptance — 7 October 2026

The pending mobile width correction passed desktop-final4/4 (2.5m) and
mobile-final1/1 (1.0m). Reuse unchanged mobile2 settings/publication/preview3/3.
Final desktop includes RU/KK/EN settings, keyboard focus/axe, failure/retry,
shared knowledge consent/isolation and manual Inbox recovery. Screenshot review
confirms translated settings and Inbox controls within mobile viewport after
min-w-0. Existing fixed navigation/tooltip behavior was not redesigned.

Exact final browser commands (canonical root; isolated SQLite and mock providers):

```powershell
.venv/Scripts/python.exe output/ai-agent-isolation-20261005/verify-ui.py desktop-chromium inbox-agent-safety.spec.ts e2e/ai-agent-isolation.spec.ts --grep='localized|new agents isolate|Inbox pause' --output=../output/inbox-agent-safety-20261007/browser-desktop-final
.venv/Scripts/python.exe output/ai-agent-isolation-20261005/verify-ui.py mobile-chromium inbox-agent-safety.spec.ts --grep='Inbox pause' --output=../output/inbox-agent-safety-20261007/browser-mobile-final
```

Final frontend `npm.cmd run build` and `npm.cmd run check:bundle` PASS after the
last source change; logs build-completion.log/bundle-completion.log. Types,
i18n5324 keys, app/widget builds and chunk budgets pass. No dependencies reinstalled.
Working HTTP health8000 and frontend5173 returned200 after authorized migration.

All60 intended paths reviewed, including new migrations, source and synthetic
adversarial tests. Private backup/logs remain ignored. Existing source/checkpoints
preserved; only current status sections updated. Diff hygiene and Python syntax
checked. Credential marker scan must distinguish deliberate synthetic canaries
from credentials; tests_customer_safety contains only the former.

Permissions: existing conversations.update + ai_assistant.suggest required for
state changes; Business scope and agent ownership enforced. Notifications reuse
existing handoff; audit/activity records recovery, existing BusinessEvent behavior
is reused. No new billing, environment variables or external provider permissions.

Coverage limits: provider calls mocked, no new paid-model evaluation, live messenger
or production certification. Pattern filtering is not comprehensive DLP; private
CRM exclusion and explicit publication are the primary data boundary. Business-wide
abuse budgets were explicitly excluded. Full local E2E was not warranted; existing
push CI is inspected separately. Earlier failures and their resolutions remain above.

Next: commit the reviewed task paths, static gate against the real starting base,
normal push HEAD:main and read back remote SHA/actual CI. No new phase or CD.
