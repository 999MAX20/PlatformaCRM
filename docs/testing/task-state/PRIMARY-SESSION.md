> Решение владельца 14.10.2026: межчатовая координация, роли primary/UI,
> назначения writer, ожидание других чатов, автоматическая передача и связанные
> ограничения отменены. Применять актуальный AGENTS.md. Ниже сохранены сведения
> о задачах и evidence; прежние межчатовые назначения являются историей, а не
> действующими инструкциями. Продуктовый scope, результаты и блокеры сохраняются.

# PRIMARY-SESSION — PlatformaCRM



## AUD-19-20261029 — lead form field tenant resolution and editor (verified)

Publication29.10: cd7a2598a9ca62444341f6fb7a2f49f1ee62b566 normal-pushed to
origin/main, remote SHA matched. Canonical PlatformaCRM, codex/ui-testing-toolkit;
24-file commit contains17 reviewed source/test files and7 documentation files.
[CI40835060335](https://github.com/999MAX20/PlatformaCRM/actions/runs/40835060335)
in progress at final documentation snapshot; no green CI claim. CI-repair parent
acb8687e remains complete success. No deployment/working migration. Outgoing
range/index hygiene and scoped docs links/anchor PASS. Other WIP preserved.
First stage/commit attempt failed on stale empty .git/index.lock (no commit created,
no-op push); no git.exe process on repeat inspection, lock unchanged over5min.
Moved empty lock to task artifact for recovery, then staged reviewed patch and
committed/pushed normally. No other work was staged or reset.


Final publication candidate29.10 supersedes the earlier blocked-build boundary.
CI-repair acb8687ed99f6a1882b1b74f1708f340debd1559 was published separately;
[CI40832440547](https://github.com/999MAX20/PlatformaCRM/actions/runs/40832440547)
is complete success for backend/frontend and dependency audits. AUD19 is17 source/
test files on that exact base, plus scoped docs, excluding other security/notification
WIP. No working migrations, deployment/provider action or new phase.

Artifacts: Temp/aud19-publication-20261029/aud19. Isolated candidate imports Git blobs
at canonical paths. `.venv/Scripts/python.exe <artifact>/run_candidate.py affected
 test apps.leads.tests_form_field_access apps.leads.tests_forms
 apps.core.tests_tenant_isolation apps.automations.tests
 apps.bots.tests.BotsFoundationTests apps.clients.tests_merge_atomicity -v1 --noinput`:
80 PASS/no skips on DRF3.18.3. Same runner `system check` and
`drift makemigrations --check --dry-run` PASS. Backend unchanged after these runs.
Frontend with NODE_OPTIONS=--require=<artifact>/frontend-snapshot.cjs in frontend/:
`npm run build` PASS (6466 keys/types/app/widget); final log build-pattern-fixed.log.
`node --test scripts/tests/capture-field-options.test.mjs`:2 PASS. No reinstall.

Candidate browser uses runtime.py, isolated SQLite/fixtures, canonical backend59405/
frontend59406, reviewed Python/JS index overlays. Real mouse/keyboard CRUD, duplicate
key400 with retained input/recovery, persisted edit/reopen, confirmed delete, empty
form and role reader without create/edit/delete PASS. RU desktop1036x703, KK/EN and
reader mobile390x844, Escape/focus return to More PASS. Earlier unchanged detailed
field-select metadata evidence retained. Screenshots output/playwright/aud19-pub-*.png.
Publication review found1036px header search intercepting new entry: moved entry to
existing Leads More ActionMenu (same translated label/current VIEW policy), without
shared header changes. Modern browser pattern rejected an unescaped hyphen: fixed
HTML pattern, real browser proves bad-space key invalid and valid-key_1 accepted.
No new architectural/state/API policy. React hooks/types/shared-menu review PASS.

Retained failures: original overlap screenshot and invalid-pattern console evidence;
Windows temporary SQLite cleanup file lock after stopping runtime (no recursive
manual cleanup attempted); one refresh-token500 from SQLite database-is-locked,
subsequent requests recovered. No SQLite concurrency repair claimed; auth tests and
full CI-repair backend PASS. Task-owned browser closed; backend/frontend listeners
59405/59406 and first52227/52228 absent after shutdown; disposable folders retained.
Code/evidence/owner decision remainder: none in this scope. Published code/remote SHA
are recorded above; CI completion is pending. Environment deployment/live separate.
Roadmap/CRM/access/frontend/leads-deals passport aligned to More-menu flow and evidence.
README/AI/integrations/operations unchanged: no new setup/provider/config contract.
AUD-10 unstarted and needs a new instruction. Unrelated WIP preserved; real index
empty before explicit task-only staging. Historical attempts below are retained.


Owner authorizes repair, required checks and roadmap update. Root canonical
PlatformaCRM, branch codex/ui-testing-toolkit, base8ee55d756b79c391e3de4a2f93fb2bfbe211aaf2.
Mode implementation/code+reachable-UI gap. Starting status/copies in Temp/aud19-20261029.
Prior security/notification/CI WIP preserved; no other phase authorized. Use declared
business_lookup consistently for permission, stored/candidate writes, delete and
history tenant. Reuse TenantModelViewSet/IsTenantMember/tenant ownership guard,
LeadFormFieldSerializer, current LEADS action/scope policy and existing API client.
Current form fields API list works, owner detail/write cannot resolve form business.
No current editor consumer exists; add bounded reachable field editor in Leads using
shared modal/form components and RU/KK/EN. No public submission policy/AI/notification/
BusinessEvent changes, no migrations/working DB/provider/deployment. Audit/activity
must carry derived Business. No new role grants or parent-transfer policy.
Risk high shared tenant infrastructure. Focused before/after CRUD owner, role denial,
foreign form, multi-business reparent rejection, partial payload and audit tenant;
representative bot/message/automation child consumers and direct Business controls.
Backend slice gate before UI; completion affected/dependent tests, system/drift,
frontend interaction/browser flow including error/empty/denied and desktop/mobile,
build/types/i18n. Publication only task-owned candidate; explicit hunks preserve WIP.


Resume29.10, owner asks to continue: repair the remaining resolver type blocker only.
Plan: distinguish raw schema input from parsed output in four forms; preserve schema
and submission policy. Risk: numeric coercion/form watcher types. Focused checks: real
resolver valid string-number inputs, invalid input, optional values and output shape;
completion forced types/build and unchanged AUD19 evidence hash check. Preserve existing
LeadForm WIP and dependency updates; publication includes only reviewed task changes.
Starting4 form copies in Temp/aud19-20261029/resume-before; HEAD unchanged8ee55d75.



Owner decision29.10: keep CI-repair and AUD19 as separate reviewed publications.
CI-repair must complete its checks/publication first; then validate AUD19 on the
new main and publish independently. No authorization to stage another writer's
WIP or message/manage another chat is inferred. Readback `git ls-remote origin
refs/heads/main` still8ee55d756b79c391e3de4a2f93fb2bfbe211aaf2; local HEAD same,
dependency/four-form fixes remain uncommitted. No unresolved publication-choice
question remains; current prerequisite is completion of separate CI-repair.
Task-only AUD19 candidate retained. No process/monitor started, no commit/push.

Resume evidence: initial read still showed old form types, but the immediate before-
edit copies already contain another writer's four-form InputValues/output fixes and
Zod4 coerce<string|number> annotations. Comparing all four copies proves no own
change to those type fixes. The only own delta was Number(resourceId) in an existing
query; removed as redundant, restoring the captured external code exactly. This is
a concrete overlapping publication boundary; user was asked whether to preserve
CI-repair as a separate publication or authorize a jointly reviewed dependency/type
packet. Do not stage or publish that other writer's packet until resolved.

Forced tsc passed; build-fixed.log passed app/widget after the shared fixes (before
removing the redundant conversion). New form-resolver-coercion.test.mjs executes
production schema declarations with installed zodResolver:8 PASS for numeric string
coercion, optional omission, unchanged strings/booleans and invalid-input no-payload.
With capture-field-options:10 PASS. Test is task-owned; four form/type and dependency
changes remain external WIP. Follow-up build-shared-fixed.log PASS verifies the restored
shared snapshot (app/widget, types, i18n). These are working-snapshot checks, not a standalone AUD19 dependency
certification. Existing final-hashes match every recorded non-doc AUD19/dependency
input, allowing backend/browser/options evidence reuse.

Separate Temp candidate.index now composes16 AUD19 source/test files only; reviewed
candidate-code.patch excludes package/lock, four existing forms and all security/
notification WIP. Real index remains empty. No new phase or publication performed.

Implementation29.10: resolve_tenant_business follows declared business_lookup;
IsTenantMember and shared object/write/delete/history paths use it. Existing
ownership guard still rejects cross-Business reparent. Activity writer accepts the
explicit derived Business, same as audit. LeadForm list accepts validated optional
business filter. New leadFormsApi.listPage and reachable modal/editor use shared UI,
LEADS action controls, user/business query keys, pagination and RU/KK/EN. Option
editing preserves surviving option labels/custom metadata. No schema/env change.

Backend: initial fixture attempts failed on username/email setup and assumed missing
role denial (existing role fallback is intentional); corrected explicit deny fixture.
Before implementation7 regressions failed. After focused18 PASS; affected80 PASS.
Exact completion: `.venv/Scripts/python.exe <Temp/aud19-20261029>/run_checks.py
 affected test apps.leads.tests_form_field_access apps.leads.tests_forms
 apps.core.tests_tenant_isolation apps.automations.tests
 apps.bots.tests.BotsFoundationTests apps.clients.tests_merge_atomicity
 -v1 --noinput --keepdb`. Same wrapper `system check` and
 `drift makemigrations --check --dry-run` PASS. Includes8 new API tests, full CRUD,
partial payload, foreign parent/read, role denial/current permission revocation,
multi-business ownership guard, invalid input, selected-business list, audit/activity.

Task-only candidate uses separate Temp candidate.index based on HEAD8ee55d75 and
reviewed5-file backend delta plus new test; real index untouched. snapshot_loader.py
imports reviewed Git blobs while all source stays canonical. First patch preparation
failed on Windows CRLF; normalized patch applied cleanly. First candidate run reused
a disposable DB with unrelated notification schema, producing19 failures/1 error;
retained candidate-affected.log. Clean candidate rerun without --keepdb:80 PASS/no
skips. Exact command: same labels above via run_candidate.py candidate-clean,
`-v1 --noinput`. Candidate-system check and candidate-drift makemigrations
--check --dry-run also PASS. No .env load/external network/working DB; isolated_runtime.

Frontend `node --test scripts/tests/capture-field-options.test.mjs`:2 PASS,
unchanged metadata omission and surviving labels/custom metadata on choice changes.
`npm run build`: check:i18n PASS6504 keys, TypeScript FAIL in existing
AppointmentForm.tsx:120, LeadForm.tsx:56, ServiceForm.tsx:56, WorkingHoursForm.tsx:47
(Zod4/resolver input unknown versus number). build.log preserves all four errors;
Vite app/widget stages not reached. Initial syntax and editing-ID errors in own
components were fixed; final build has no AUD-19 component errors. package/lock
changes belong to pre-existing CI-repair WIP and were not modified. This is a real
required gate blocker, not a waived/baseline PASS. No dependency reinstall.

Targeted real browser uses runtime.py with isolated SQLite, canonical source roots,
backend64828/frontend64829 (fixture-only owner/reader; no real records). CRUD persisted,
duplicate key error then recovery, delete confirmation/removal, new/empty form,
select duplicate choices rejected then corrected/reopened, read-only role has no
create/edit/delete controls; API denial is proven separately above. RU/KK/EN checked,
mobile390x844 and desktop1366x900, Tab trap and Escape/focus return. Screenshots in
output/playwright/aud19/{kk-mobile,en-mobile,ru-reader-mobile,ru-desktop}.png.
No new full E2E suite: focused flow matches functional frontend/shared tenant scope.
No PostgreSQL concurrency run: no locking/transaction/money algorithm changed.

Docs aligned: roadmap remains open at required build/publication, CRM/access/frontend
contracts and leads-deals passport describe actual local behavior. README/capabilities/
AI/operations/integrations need no update: no existing lead-form detail contradicted,
setup/AI/provider/runtime contract unchanged. Historical audit evidence untouched.
Remainder: code AUD-19 none known; evidence required frontend build/types on corrected
dependency/type boundary; environment commit/push/CI and deployment not performed;
owner policy none unresolved. After correcting the existing type/dependency boundary,
rerun affected frontend gate and candidate review before publication. AUD-10 unstarted.

Final hygiene: working diff --check and selected AUD-19 links/anchor PASS; new
files reviewed. Task delta and SHA256 manifest in Temp/aud19-20261029. Real index
empty; branch/HEAD unchanged. Browser tab closed and viewport reset. Runtime
parents exited; no listeners on64828/64829 and no AUD19 Python process remain.
Initial automatic temp cleanup hit Windows file lock; explicit cleanup was rejected
by automatic policy review (no more specific reason supplied). Disposable runtime
folder retained; no retry/bypass. No task-owned processes left running.


## CI-REPAIR-20261029 — migration isolation and dependency advisories (verified)

Owner requests fixing backend failures/dependency vulnerabilities, preserving all
other local work, verifying, publishing to main and waiting for green CI.
Canonical root/branch unchanged, base HEAD/main692e46f0, real index empty. Starting
diff/status in Temp/ci-repair-20261029. No other security/notification/SSE WIP included.
Confirmed CI40768322341:2116 tests,11 errors from missing YCloudConnection table,
40 skips; frontend build/budget PASS, npm audit fails on DOMPurify/Storybook/Zod.
Gap: test isolation and dependency security. Reuse current migration test/runner,
package manager lockfile, React Hook Form and existing form/browser/catalog checks.
Risk: migration test rollback leaks into later tests; Zod major-version validation
and coercion compatibility. No CRM/permission/notification/AI policy or production
schema/env changes intended. Working DB/migrations/provider actions excluded.
Checks before changes: ordered safety-migration→YCloud dispatch reproducer in
isolated Git-index Python source; audit/official advisories and dependency callers.
After backend fix: same order and owning tests, system/drift. Dependencies: npm audit,
forced types/build/bundle, form validation happy/error/coercion flows and Storybook
build/representative browser. Review exact index/outgoing range, normal commit/push,
read remote SHA and wait for complete green GitHub backend/frontend CI. Full backend
in CI required for this reproduced test-order interaction; no unrelated broad E2E.

Completion29.10: reviewed11 code/test/lock files, excluding AUD19 and unrelated WIP.
Migration test restores all graph leaf nodes in finally, even after failed downgrade.
Frontend updates DOMPurify/Storybook/Zod/resolver, separates raw/parsed form types,
and repairs stale Storybook IDs. Additional Python audit found DRF3.17.2 advisories
CVE-2026-114136/114137/114138. Scoped update to3.18.3 includes security fixes and
3.18.2 regression correction (official DRF release notes). Only DRF lower bound,
pin and distribution hashes changed; unrelated uvicorn/SSE excluded from candidate.

Artifacts: Temp/aud19-publication-20261029. Candidate loader reads reviewed Git blobs
in memory at canonical paths, using isolated_runtime; no .env/working DB/provider.
`.venv/Scripts/python.exe <artifact>/run_candidate.py
 apps.bots.tests_safety_migration apps.integrations.tests_ycloud_dispatch
 apps.accounts.tests apps.core.tests_tenant_isolation apps.leads.tests_forms
 apps.clients.tests`:73 PASS/no skips, system check and migration drift PASS.
`python -m pip_audit -r <artifact>/requirements-candidate.txt --no-deps --disable-pip`:
no known vulnerabilities. DRF3.18.3 installed in existing .venv using
`pip install --require-hashes --no-deps -r <artifact>/drf-install.txt`; verified PyPI
hashes, no other reinstall. Initial piptools compile failed: installed pip removed
stdlib_pkgs; retained lock-compile.log. Updated scoped pin/hashes from official PyPI
metadata instead, preserving other pins. Old-DRF audit failure remains in ci-repair.

Frontend commands in frontend/ with NODE_OPTIONS=--require=<artifact>/frontend-snapshot.cjs:
`npm run build`, `npx tsc -b --force`, `npm run check:bundle`, `npm audit --json`
PASS (6456 translation keys, zero audit findings). Existing large KK chunk warning
remains; app-shell budget PASS. `node --test scripts/tests/form-resolver-compatibility.test.mjs`:
8 PASS. Unchanged frontend candidate retains preceding `npm run build-storybook`
and `npx playwright test --config playwright.storybook.config.ts --grep
'fresh Storybook index|service modal validates'`:8 PASS desktop/mobile RU/KK/EN,
valid/invalid fields/reset/error recovery. Failed stale-ID attempts retained.
No full browser/live provider tests; no schema/env/API policy change. README/domain
passports need no change because behavior/setup contracts remain the same. Full
backend CI40832440547 for acb8687e completed success, including both audits.
Candidate diff hygiene/new-file/dependency review PASS; no secrets. Main push runs
only ci.yml checks, no deployment job. Published acb8687e; remote SHA confirmed;
full CI40832440547 success. Other WIP preserved.


## AUD-11-20261029 — atomic client merge and request audit (verified)

Owner authorized merge rollback repair and roadmap update. Canonical root
C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
base692e46f01934a946233a01181f24f6589bccea43. Prior WIP preserved; starting status
and file copies in Temp/aud11-20261029. No concurrent affected source edits observed.
Mode implementation/code gap. Existing merge service committed before request audit.
Minimal fix: outer transaction.atomic around merge action, retaining nested domain
service, request audit metadata/IP/actor, permissions, response and error contracts.
Business lock now remains held until audit completes. No new lifecycle policy,
permissions, notification, BusinessEvent/AI/provider behavior, schema or env changes.

Plan/checks: reproduce HTTP failure and persisted rows; prove atomic rollback of
ledger/client/archive/history/relations and retry, then owning clients/payment and
archive-dependent suites plus isolated system/drift. Existing merge API/UI reused.
Before: fixture failed on missing Payment.submission_id (UUID added); second attempt
wrongly expected propagated exception, but established handler returns sanitized500.
After inspecting handler corrected tests to assert500 plus database snapshot; before-http
then reproduced two rollback failures, activity failure control PASS. Logs retained.
No acceptance weakened: required rollback assertions remained unchanged.
After patch focused3 PASS. Added self-merge/no-writes and single activity assertions.
Final candidate54 PASS/no skips: apps.clients.tests, apps.clients.tests_merge_atomicity,
apps.clients.tests_archive_dependencies, apps.payments.tests. Includes4 new true
TransactionTestCase tests (no outer TestCase transaction), audit before/after insert,
activity failure, full row snapshot equality including conflicting deleted tags/custom
fields, payment125KZT, successful retry with one merge log/audit/activity; existing
happy path, foreign duplicate, permission denial, preview and ledger/refund controls.

Exact command: `.venv/Scripts/python.exe <Temp/aud11-20261029>/run_candidate.py
 candidate-affected test apps.clients.tests apps.clients.tests_merge_atomicity
 apps.clients.tests_archive_dependencies apps.payments.tests -v1 --noinput --keepdb`.
Same runner `system check` and `drift makemigrations --check --dry-run`: PASS.
First3 focused tests ran via run_checks.py after test ...ClientMergeAtomicityTests.
Runner reuses scripts.codex_verify.isolated_runtime, disposable SQLite, synthetic
fixtures, no .env load/external network. Candidate imports reviewed Python blobs
from a separate Git index based on HEAD, not another source checkout; excludes
unrelated WIP. All source remains in canonical folder. Tested source hashes and
candidate logs/manifests retained in task temp. No dependency installation.

Frontend inspection: clientsApi.merge rejects failed request; ClientsPage clears
preview and invalidates cache only onSuccess, existing pageError surfaces failure.
No UI/API shape change: browser/build/i18n/full E2E skipped as disproportionate.
PostgreSQL concurrency not rerun: no lock-order/ledger algorithm change; only commit
boundary extended. Live readiness/working data/deployment excluded. Historical audit
report untouched; clients passport and CRM contract correct the old failure assertion.
README/access/AI/operations unchanged: no setup, rights or policy change.
Code/evidence/owner decision remainder: none in scope. Roadmap AUD-11 closed;
next local audit item AUD-19 remains unstarted. Normal task-only publication selected;
prior notification/security/CI WIP excluded. Actual publication/CI reported separately.

Publication29.10: db0a4d9c normal-pushed to origin/main; remote SHA readback matches.
CI40822054259 in_progress when checked, no green-CI claim. Real index empty after
source commit; unrelated WIP preserved. Committed-range diff hygiene PASS.

## YCLOUD-PUBLICATION-20261029 — combined publication verification (published)

Owner explicitly authorizes review and normal publication of OFFICIAL-03, YCloud
and the three outgoing commits e5bca576/f2c8e371/98925b67 to origin/main if required
checks pass. This supersedes the earlier publication exclusion for this packet only.
Canonical root/branch unchanged; starting HEAD98925b67 and index empty. Local
origin/main67014f57 was stale: fetch origin main updated FETCH_HEAD, not that ref.
Pre-push FETCH_HEAD was98925b67, so the three reviewed ancestors were already remote.
Explicit fetch refs/heads/main:refs/remotes/origin/main now synchronizes the ref.
Starting diff/status saved in Temp/ycloud-publication-20261029. Other security and
notification WIP stays outside publication, including concurrent receipt refresh.
Mode review/verification/publication; no live rollout or working DB migration.
Risk: authenticated tenant routing, outbound retries, stored export authorization,
shared focus accessibility, and accidental inclusion of unrelated WIP.
Plan: compose/review only authorized hunks against HEAD; check dependencies and
secrets; run focused/affected WhatsApp/YCloud/export tests in isolated runtime,
PostgreSQL concurrency, system/drift and shared focus browser/build checks as needed.
Reuse unchanged reachable YCloud UI evidence with source hash proof. Review exact
outgoing range and CI/deployment effects; commit only reviewed paths/hunks, fetch,
normal-push HEAD:main, read remote SHA and inspect actual CI. No force/merge/rebase.
This is scoped integration publication, not release or live-provider certification.

Combined review result: no confirmed actionable defect in the authorized changes.
OFFICIAL-03 and YCloud compose as38 code files against HEAD without unrelated WIP;
the three existing commits remain intact. No new implementation change was needed.
Ten documentation files include only the relevant YCloud/OFFICIAL-03/publication
sections. No notification/security-neighbor/dependency-lock/Vite-proxy edits included.
No secrets/private data found in the reviewed additions; provider examples are empty
or synthetic. Existing CI workflow runs backend/frontend checks only, no deployment.
Historical main67014f57 has successful push CI run39599481089; this is baseline
evidence only. No real target/account/send/working migration was authorized or used.

Exact verification evidence: output/ycloud-publication-20261029 (generated local
artifacts, not another source tree). Existing Python/Node dependencies reused.
Read-only Python import and Node fs adapters load reviewed Git-index source blobs
in memory under canonical file paths; unrelated untracked modules/migrations are
excluded. No worktree/clone/stash/source replacement and no shared server stopped.
Backend wrapper run_candidate.py reuses scripts/verify_ycloud.py and
scripts.codex_verify.isolated_runtime, disposable SQLite/media or PostgreSQL17.
Command prefix: `.venv/Scripts/python.exe <artifact-dir>/run_candidate.py`.
- `apps.integrations.tests_whatsapp_binding apps.integrations.tests_ycloud
  apps.integrations.tests_ycloud_dispatch
  apps.integrations.tests.WhatsAppIntegrationFoundationTests
  apps.integrations.tests_credential_encryption apps.integrations.tests_channel_ownership
  apps.integrations.tests_channel_setup_consistency apps.integrations.tests_provider_rollout
  apps.bots.tests.InboxBackendTests apps.bots.tests_handoff_recovery
  apps.core.tests_export_access`:216 tests OK,214 PASS/two PG-only skips;
  backend-candidate-2.log. System check and migration drift PASS.
- `--postgres-bin "C:/Program Files/PostgreSQL/17/bin"
  apps.integrations.tests_ycloud_dispatch apps.integrations.tests_ycloud_concurrency
  apps.bots.tests_handoff_recovery.HandoffRecoveryConcurrencyTests`:16 PASS/no skips,
  including both previously skipped tests; pg-candidate.log. Disposable cluster stopped.
- `apps.core.tests_import_export apps.core.tests_b5_performance
  apps.clients.tests_sensitive_notes apps.analytics.tests_workspace apps.analytics.tests`:
  59 PASS/no skips; export-dependent.log, system/drift PASS.
- Frontend with `NODE_OPTIONS=--require=<artifact-dir>/frontend-snapshot.cjs`:
  `npm.cmd run build` PASS (i18n6456, types, app/widget);
  `npx.cmd tsc -b --force` PASS independently of incremental cache;
  `npm.cmd run check:bundle` PASS. Advisory chunk/plugin timings retained.
- Same frontend source adapter, ACTION_COLOR_PORT5293:
  `npx.cmd playwright test e2e/focus-modality.spec.ts e2e/action-color-roles.spec.ts
  --config playwright.action-colors.config.ts`:12 PASS, desktop/mobile RU/KK/EN,
  login/shared controls/modal/search/widget; auth mocked401, no working DB.
- Existing YCloud setup/Inbox UI evidence retained for unchanged task UI/API source.
  Original35-file manifest differs only in .env.example/config/settings.py due to
  unrelated notification additions excluded from candidate; no YCloud delta drift.
  Shared focus was reverified above. No repeat full-project/live acceptance suite.
- Candidate Python compile, new-file review, seven added local link targets,
  candidate/index/outgoing diff hygiene PASS; exact blobs and patch in artifacts.

Retained tooling failures: initial git apply check rejected CRLF patch representation;
LF-normalized composition matches full context without inferred changes. Initial
snapshot harness omitted ModuleNotFoundError.name, causing migration-loader error;
corrected harness, complete repeated gate above PASS, original log retained.
GitHub CLI unavailable; connected GitHub GET used for CI. Unsupported workflows-list
GET rejected; supported actions/runs GET works. These did not change product code.
Publication completed29.10: code commit b6de2956ecd1be566f61247f9a8cec641bd72344,
branch codex/ui-testing-toolkit, normal `git push origin HEAD:main` successful.
Remote `git ls-remote origin refs/heads/main` matched the full commit SHA; all three
authorized ancestors remain in main. No force/reset/rebase or unrelated WIP staged.
Published code tree01697fdfbc00fa07fa732a96c335b8f0829764d4 matches reviewed index.
CI push run40767943683 is in progress: backend install/static/drift/system/readiness
steps passed; backend tests and frontend build still running at inspection. No green
CI or deployment claim. Link: https://github.com/999MAX20/PlatformaCRM/actions/runs/40767943683
Publication docs follow-up records this result; it changes no application code.
Code/review/local-check/publication remainder: none. CI outcome and live/environment
acceptance remain separate. Existing other-task WIP and working services preserved.


## YCLOUD-TPLITE-20261028 — TP Lite and Inbox text (local scope complete)

Explicit owner request in this chat: implement first stage, reuse existing WhatsApp/
Inbox, no real sends or account connections; list owner access requirements separately.
Mode implementation; provider/model/UI gap. Root canonical PlatformaCRM; branch
codex/ui-testing-toolkit, HEAD98925b6796d4995e80af9d9a040ec5bbcfcab348.
Prior security and personal-notification WIP is unrelated and preserved. Starting
status/patch: C:/Users/user/AppData/Local/Temp/ycloud-tplite-20261028.
Scope: server-owned TP Lite attempt, signed durable webhook intake, one API number,
text inbound/outbound through existing Inbox/AI pipeline, delivery states and recovery,
reachable setup UI. No templates/reminders/media/history/Coexistence or live rollout.
Reuse BotChannel/BusinessConnector/provider/Inbox/BusinessEvent/outbox permissions.
Risk high: tenant binding, stale callbacks, signatures, duplicate/ambiguous sends.
Checks: focused isolated tests after each backend slice; affected integration/outbox
suites, clean migration/system/drift, PostgreSQL races, targeted UI/API states and
RU/KK/EN, frontend types/build at completion. No working DB or provider calls.

Local implementation and verification completed 29.10. Original publication blocker
was the unpublished OFFICIAL-03 route dependency and three outgoing commits against
origin/main67014f57 (e5bca576, f2c8e371,98925b67). Owner29.10 explicitly authorized
checking and publishing this combined set if required checks pass. Current outcome
is recorded in YCLOUD-PUBLICATION-20261029 above; other WIP remains excluded.

Implementation: YCloudConnection/Event/Dispatch, integrations0007/0008 and bots0013;
disabled-by-default server client, setup start/status/cancel/retry, signed durable
ingress and beat worker, reuse WhatsApp Inbox/CRM/AI pipeline. One API number, text
only. Server-owned customer/setup revision, fresh actor rights and WABA/number
binding prevent foreign/stale setup; no browser callback activates the channel.
POST intent is committed before network, unknown outcome forbids blind resend,
429 gets bounded retry; signed receipts correlate to attempt and do not regress.
Current manager rights and source-time24h window checked at send. Existing Meta
auth cannot route into YCloud. Events redact unknown fields; no API key/signup URL
is persisted or logged. Signup URL remains in browser memory and expires.
Existing UI shell/API used for setup and statuses, RU/KK/EN. Error reset corrected
after browser test; send toast now distinguishes queue/accepted/unknown/failure.
Readiness includes separate YCloud secret and shared runtime gates, not live proof.

Verification from canonical root, existing .venv and frontend dependencies; no
working DB/env/migration or provider call. scripts/verify_ycloud.py uses
scripts.codex_verify.isolated_runtime, disposable SQLite or owned PostgreSQL17,
synthetic credentials and mocked client. Every invocation runs system check and
makemigrations --check --dry-run first; these pass. Commands/logs in
C:/Users/user/AppData/Local/Temp/ycloud-tplite-20261028, reviewed durable copies in
output/ycloud-tplite-20261028 (no ui-env/password file copied).

- First onboarding slice8 PASS; signed ingress23 PASS; dispatch55 and permission55
  PASS; backend-focused60 PASS. Earlier counts included an imported foundation
  TestCase, later replaced by module import to avoid duplicated collection.
- `.venv/Scripts/python.exe scripts/verify_ycloud.py apps.integrations.tests_ycloud
  apps.integrations.tests_ycloud_dispatch apps.integrations.tests_whatsapp_binding
  apps.integrations.tests_channel_setup_consistency apps.integrations.tests_channel_ownership
  apps.integrations.tests.WhatsAppIntegrationFoundationTests
  apps.bots.tests.InboxBackendTests apps.bots.tests_handoff_recovery`:
  completion-backend.log171 OK,169 PASS/two PG-only skips. Latest receipt-order
  regression added during that run; final PG dispatch run below covers it.
- `.venv/Scripts/python.exe scripts/verify_ycloud.py --postgres-bin
  "C:/Program Files/PostgreSQL/17/bin" apps.integrations.tests_ycloud_dispatch
  apps.integrations.tests_ycloud_concurrency`: postgres-final.log14 PASS/no skips,
  including duplicate ingress, dispatch race and competing WABA binding. Prior PG13
  PASS retained. Disposable cluster shut down by runner.
- Same PG runner with `apps.bots.tests_handoff_recovery.HandoffRecoveryConcurrencyTests`:
  handoff-pg.log2 PASS, resolves the two SQLite skips; no changed handoff policy.
- Same isolated runner with `apps.integrations.tests_provider_rollout`:
  readiness-final.log16 PASS, including two new YCloud readiness regressions.
- `npm.cmd run build` in frontend: frontend-final.log PASS (i18n6494 RU/KK/EN,
  tsc -b, app and widget). Chunk-size advisory retained; no dependency install.
  After final send-toast refinement, frontend-completion.log PASS again; no later
  frontend source changes. Final accepted toast confirmed in browser screenshot.
- Browser CUA, canonical Vite/Django, disposable fixture DB only: setup unavailable,
  provider error/reset, pending link, cancel and new attempt, signed bind, incoming
  text, manual accepted reply and signed read; pause/resume. RU desktop, KK/EN390px,
  keyboard Tab/Escape and focus restoration. Screenshots retained. No real signup
  link opened. Two test-session refresh401 interruptions retained; repeat login
  recovered and completed the flow; authentication product code not changed.
  Alternate localhost address was unreachable; canonical127.0.0.1 test ports used.
  Fixture first start failed on nonexistent User.email_verified; corrected fixture,
  no source/model change. Failed log ui-server-attempt1.log retained.

Final review found two additional in-scope regressions, now fixed:
- Cached/deactivated initiator could start/confirm. current-authority-before.log
  has one reproduced failure and one test-mock response error (link mock corrected);
  third role-denial control passed. Service now reloads active account at start,
  confirm and recovery; does not change shared access policy. Isolated
  `apps.integrations.tests_ycloud.YCloudCurrentAuthorityTests
  apps.integrations.tests_ycloud.YCloudOnboardingTests`: current-authority-after.log11
  PASS, including same-business specialist403 for every setup write action.
- Message preceding number binding was acknowledged204 and discarded.
  `apps.integrations.tests_ycloud.YCloudIngressOrderingTests.test_message_before_binding_is_retried_instead_of_acknowledged_and_lost`:
  ingress-order-before.log reproduced204 vs expected503. Unknown signed message
  route now raises retryable503; provider resend after binding persists/processes
  one inbound message. Foreign routes still create no effects. First integration
  run (`apps.integrations.tests_ycloud apps.integrations.tests_ycloud_dispatch`)
  final-authority-ingress.log41:40 PASS/one failure because global exception handler
  normalizes generic APIException503 to500. Reused existing TemporaryServiceFailure
  domain exception; no global-handler change. Smallest affected class rerun
  `apps.integrations.tests_ycloud.YCloudIngressOrderingTests`: ingress-order-after.log1
  PASS (503, then204 and one Inbox message), system/drift PASS. Other40 unchanged
  paths reused; initial failed41 run is retained, not relabelled as green.
- PG runner with `apps.integrations.tests_ycloud_concurrency` after current-account
  guard: concurrency-completion.log3 PASS/no skips. Dispatch14/handoff2/readiness16
  results remain applicable to unchanged paths. Counts are executed tests, not
  a deduplicated project total (webhook class also inherits onboarding controls).

Final source/doc delta and SHA256 manifests: output/ycloud-tplite-20261028.
Code patch is against recorded pre-existing WIP (routing baseline reconstructed
from preserved OFFICIAL-03 artifact), not an independently deployable HEAD patch.
Doc patch includes only this task's sections, preserving concurrent notification
documentation. Code syntax, new/untracked-file review, diff hygiene, reverse patch
checks and changed local links checked at completion. No full-project/E2E gate:
bounded provider/Inbox scope, not release certification; base remains HEAD so the
documented isolated focused path was used instead of inventing a committed range.
Owned UI backend/frontend processes stopped; temporary viewport override reset.
Final integrity:25 Python files compile,35 task-code files hashed,6 added local
links/anchors valid; ordinary `git diff --check`, cached check and both reverse
patch checks PASS. One diagnostic mistakenly overrode core.autocrlf=False and
reported CRLF as trailing whitespace across existing files; no source rewrite was
made. Repository-configured checks (core.autocrlf=True) pass. Artifact packaging
initially used an obsolete notification heading, then preserved its current section
with a corrected boundary. These tooling attempts did not change application code.

Docs: integrations/operations/frontend contracts, integration+Inbox passports,
capabilities, roadmap R02, README and STATUS updated. Access/CRM/AI contracts need no
policy rewrite: existing actions, lifecycle, optional AI and safety reused; technical
permission details recorded in integration contract. No new roadmap phase opened.
Remainder: code/evidence in authorized local text/setup scope none; publication
authorization granted29.10, combined verification recorded above; environment needs target/migration/
worker/beat/HTTPS, owner access needs enabled TP Lite and number/account permissions,
server secrets and authorization of a real test. Media/templates/reminders/history/
Coexistence outside this stage. R02/R03 live acceptance explicitly open.


## OFFICIAL-03-20261028 — WhatsApp authenticated tenant binding (fixed locally)

Owner explicitly proceeds with OFFICIAL03. Root/branch canonical unchanged, HEAD98925b67
plus previous security WIP. User also reported Daybreak unavailable
for Astra; answered that no restriction should be bypassed. Ordinary allowed static source
review continues; no blocked tool action retried and no real provider/credential access.

Confirmed: BaseWhatsAppAdapter.verify_webhook collapses per-channel credential lookup to
bool/string; resolve_whatsapp_channel prioritizes arbitrary payload phone_number_id. Both
inbound and status paths can cross tenant. Status batches flatten all changes under first
nonempty route. Independent read-only whatsapp_boundary confirms this and recommends explicit
verified auth context (Meta/global internal/channel binding), all-route preflight before
effects and per-change status association. Preserve invalid-signature precedence, live HMAC
requirements, configured global internal mode only non-live, generic channel-secret payloads,
dedup and existing status-first behavior for mixed payloads. No owner policy gap identified.

Implemented boundary: carry typed verified context without raw secret into services; require
current active bound channel and supplied IDs matching configured/external aliases; global
verified modes route by unambiguous metadata. Preflight every metadata route before any
business effects, including ignored message changes. Keep status batches tenant/channel
scoped and log only corresponding payload portions; preserve response summary. Do not turn
this into full multi-message ingestion. Existing legacy credential lookup lazily migrates
legacy synthetic config; do not change shared Telegram/Instagram credential rules. Rejection
proof concerns business effects, documenting existing credential migration separately.

Result: baseline and scoped patch saved through plugin-managed artifacts/whatsapp-binding.
BEFORE12:9 security/route failures and3 controls PASS. AFTER36: new12 PASS, one existing
compatibility error because selected payload dropped a masked top-level api_key field.
Preserved the non-entry envelope while isolating changes; no assertion weakened.
Added8 controls; after-compat44 PASS. Final completion102 PASS, no skips; system/drift/
syntax PASS. Independent fresh candidate reviewer reported no findings. Full failed logs
remain; no baseline claim or hidden failed gate. Source hashes match the tested candidate.

Files: integrations/providers/whatsapp.py returns immutable VerifiedWhatsAppWebhook;
new whatsapp_routing.py revalidates active channel/Bot/Business and aliases, resolves
global routes uniquely and preflights all changes; whatsapp/__init__.py retains per-change
status/log portions and adds conversation Bot filtering. views.py only forwards context.
New tests_whatsapp_binding.py covers HTTP paths and direct stale-context defensive checks.
Same-Bot channel uniqueness supplies the channel boundary for message status lookup.
No new model/permission/role, migration, AI behavior, notification send or UI contract.
Existing BusinessEvent/usage/consent/inbox side effects run only after route validation;
valid idempotency and status-first/first-message ingestion preserved, not full batch ingestion.

Commands (canonical root; Python .venv/Scripts/python.exe): temporary artifact directory
C:/Users/user/AppData/Local/Temp/codex-security-artifacts-1d95dca3a3a214defe40ef89cc9676be3b5622a5abafcb39d5da4e18155bd64b/artifacts/whatsapp-binding.
run_checks.py before apps.integrations.tests_whatsapp_binding => expected FAIL9/12.
run_checks.py after apps.integrations.tests_whatsapp_binding
apps.integrations.tests.WhatsAppIntegrationFoundationTests =>35 PASS/1 compatibility error.
Same labels with after-compat =>44 PASS after envelope repair and8 additional controls.
run_checks.py completion apps.integrations.tests_whatsapp_binding
apps.integrations.tests.WhatsAppIntegrationFoundationTests apps.integrations.tests_credential_encryption
apps.integrations.tests_channel_ownership apps.integrations.tests_channel_setup_consistency
apps.integrations.tests_provider_rollout =>102 PASS. Completion runs manage.py check and
makemigrations --check --dry-run first, both PASS. All use scripts.codex_verify.isolated_runtime,
disposable SQLite/media, synthetic credential keys, no .env loading and denied network.
candidate.py compiles five changed/new Python files and records patch/source hashes.
Diff/reverse/integrity results retained with final report; strict reverse is line-ending
sensitive, --ignore-space-change verifies the actual task delta. Index remains empty.

Persistent record: C:/Users/user/.codex/state/plugins/codex-security/scans/PlatformaCRM/
artifacts-5c104f7eb8ffeb335f0ca5772aabb0cf2c88c0a722d9ac17d6bb18e0f3934604/artifacts/whatsapp-binding.
Includes exact commands/logs/results, baseline hashes and three original source files,
task.patch, review, integrity and fix-report.md. Canonical scan findings unchanged.
Root/branch/HEAD unchanged; previous dirty work including provider_rollout.py retained.
At original closure no staged files/commit/push/deploy; publication was excluded.
Owner29.10 superseded that exclusion for this packet; publication result is recorded
in YCLOUD-PUBLICATION-20261029 above. Original102-test evidence remains unchanged.

No remaining bounded code/evidence/owner-policy blocker. Environment limitations: local
synthetic SQLite only, no real provider/credential/account changes, working DB, PostgreSQL
concurrency or live/R02 certification. Frontend/build/browser skipped: no changed merchant
flow/DTO, and reachable webhook happy/denial behavior proven by synthetic HTTP tests.
No full-project gate: provider-specific boundary only. STATUS/roadmap/integrations contract/
capabilities/integrations passport updated; README/frontend/access/AI/operations contracts
need no change to setup, UI, role policy or operational settings. Next finding not started.


## AUD-18-20261027 — current export download authorization

Owner continuation authorizes AUD-18 only. Canonical root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, clean base f2c8e371f60c96cc06b3c704f07abed41303137b.
Code/evidence gap: ready export download checks VIEW but serves an older broader file.
Reuse ExportJob parameters, existing can/scope/capability/branch access and notes redaction.
Store a versioned access fingerprint at generation; require matching current access at download.
Fail closed for legacy files without a fingerprint; request a new export. No schema migration.
Risk: sensitive cross-scope disclosure and invalidating formerly available downloads.
Focused API tests: allowed download, BUSINESS to OWN/TEAM, team/branch/role revocation,
related analytics permissions, legacy files, capabilities, tenant/actor isolation, generation race.
Completion: export/import, sensitive-note, analytics and existing performance suites;
isolated system/migration drift, docs links and diff hygiene. No UI change/build/browser,
working DB, provider calls, deployment, new permission framework or next AUD phase.
Preserve stored files and existing notes redaction; no notification/BusinessEvent/AI impact.
Review explicit paths, commit and normal push origin main, inspect actual CI.


Result: completed in local scope. export_access.py computes a versioned SHA256
fingerprint using fresh DB actor/Business, effective VIEW/capability, accessible
branches, team IDs and streamed visible-record IDs for OWN/TEAM. Analytics also
captures underlying resources and performance-team visibility. Worker compares
before/after generation, stores fingerprint with completed job; download rejects
missing/different fingerprint before file access and success audit. Legacy files
require regeneration. Original bytes retained, AUD-03 notes redaction preserved.
No new model/migration/dependency. Conservative equality may reject expanded
access or new/deleted visible records; fingerprint tied to original actor.
Branch changes invalidate files, not the CRM-MB01 shared-base read contract.
Already downloaded/streaming copies cannot be revoked; no global authorization
lock or full concurrent role-change/ABA certification. Restricted ID hashing is
streamed with chunk_size2000; large target load remains operational acceptance.

Verification uses existing .venv Python and scripts.codex_verify.isolated_runtime,
disposable SQLite/media/config, no provider/server/working DB or installs.
Runner: output/aud18-20261027/verify.py executes `manage.py test <labels> -v 1`,
then `manage.py check` and `manage.py makemigrations --check --dry-run`.
Initial apps.core.tests_export_access: 10 errors from duplicate blank fixture emails
before test behavior; fixed explicit unique synthetic emails. Repeat: 10 PASS1.127s,
system/drift PASS (focused-fixed.log). Final additional actor/team-lead cases and
fresh-identity handling included in affected gate, six labels:
apps.core.tests_export_access apps.core.tests_import_export
apps.core.tests_b5_performance apps.clients.tests_sensitive_notes
apps.analytics.tests_workspace apps.analytics.tests
71 PASS40.974s, no skips; system check no issues, migration drift no changes
(affected.log). Includes 12 new tests: unchanged/fresh allowed, BUSINESS→OWN/TEAM,
team/branch/VIEW/membership/capability revocation, reassignment, tenant/actor denial,
legacy fail-closed, analytics resource/team-lead narrowing, worker freshness and
change during generation. Existing queued notes redaction and private files PASS.
No frontend build/browser: no UI/API shape change, real endpoint flow exercised.
No PostgreSQL/full local suite: no new transaction/lock/schema; scoped test result,
not broad concurrency or live-worker certification. No owned processes remain.

Roadmap, access/integrations contracts, integration/data-lifecycle/capabilities
passports and STATUS reconciled. README/product/CRM/AI/frontend/operations need
no change: setup, domain policy, UI, config and deployment unchanged. No new docs
registry entry needed. Original historical evidence preserved. Current roadmap
header clarified as historical snapshot; AUD-12 dependencies no longer imply
AUD-21/22 untested. Next AUD-17 not started. Code/evidence/owner-decision remainder
none in local scope; target live storage/worker and rollout separate.
Publication: reviewed task paths only; normal push to origin main under standing
authorization. Final SHA, remote readback and actual CI reported to owner; CI
not assumed green. Documentation links/registry and work/index/range hygiene
verified at publication. No deployment/release or working-DB migration.

## UI-FOCUS-20261023 — pointer versus keyboard focus

Owner requests project-wide focus UX analysis and correction, including /login.
Implementation/code gap; canonical root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, clean starting HEAD67014f575a0b089f061a4c5065d08b003db4b084.
Reuse shared controls, Tailwind variants, auth styles and existing browser fixtures.
Observable result: mouse/touch interaction and subsequent text entry do not show
keyboard rings; keyboard navigation and programmatic keyboard flows retain them.
Preserve actual DOM focus, caret, validation, selection and focus traps.
Risk: shared accessibility behavior, portals, widget and non-main entry points.
Focused checks: real login plus shared controls, pointer/keyboard transitions,
typing, error borders, native controls and programmatic focus; desktop and mobile.
Completion: focused browser regression, existing action-color checks, frontend
build/bundle, diff hygiene and contract/evidence consistency. No backend, working
DB, external providers, permissions, notifications, BusinessEvent or AI changes.
No unrelated layout redesign or release certification. Review explicit files,
commit and normal push to origin main; inspect actual CI.

Result: shared document modality tracks pointerdown and keyboard navigation in
capture phase without moving focus/preventing input. Default native focus-visible
is retained; clicked text entry/caret movement stays pointer. Tab/Escape and
keyboard controls restore rings. Tailwind focus-visible, custom CSS, auth legacy/
serenity and widget use the same guard; language wrapper uses keyboard-focus-within.
Unconditional focus utilities in tables/client rows, deal/lead notes, Inbox search
and outreach converted. Contextual task-row backgrounds/tooltips and selected/error
styles remain intentional. Main, catalog and widget entry points install the policy.

Evidence on base67014f57 + task diff, Windows/Node24.18.0, existing dependencies:
- Baseline focused shared-input test reproduced pointer outline solid (expected
  none). Initial login mock accidentally intercepted source imports, then returned
  invalid session shape; fixed harness to intercept fetch/xhr only with401. No
  product auth logic changed. Exact invalid-field label included validation text;
  locator corrected. Ring4+offset2 computes6px; assertion corrected accordingly.
- `cd frontend; npx playwright test e2e/focus-modality.spec.ts e2e/action-color-roles.spec.ts --config playwright.action-colors.config.ts`
  final12 PASS (29.2s): real login RU/KK/EN on desktop Chromium/Pixel7, typing,
  click-after-keyboard, touch, shared input/textarea/error/checkbox/radio, modal
  return focus, search, language selector, widget and action-color/axe/overflow.
  Frontend-only owned Vite127.0.0.1:5193 from canonical checkout; no Django/DB;
  auth requests mocked401 and no form submitted. Servers exited after checks.
- Existing color test had obsolete255,245,232 expectation; unchanged HEAD palette
  warning.soft=#F0F4F2 and styles warning-bold references it. Test now reads the
  committed semantic palette. Tailwind hover is capability-gated, so hover assertion
  applies to desktop; mobile retains color, focus, disabled, overflow and axe checks.
  Initial failures preserved here rather than represented as baseline PASS.
- `npm run build` PASS (i18n6440 keys, tsc, app and widget); advisory chunk warning,
  `npm run check:bundle` PASS (largest kk495.8KiB, app-shell331.8KiB).
- `node --test scripts/tests/login-page-policy.test.mjs`15 PASS.
- Desktop/mobile RU screenshots visually inspected; locale screenshots in ignored
  frontend/test-results/focus-modality-login-* directories. Existing hover border
  remains; keyboard halo is absent after click. No layout/copy redesign.
- Source inventory covers frontend/src CSS/TSX and widget; no unguarded decorative
  focus ring remains in authored CSS or focus utilities. Browser evidence samples
  shared consumers, not every authenticated route or Firefox/WebKit/physical AT.

Docs: frontend contract, capability passport and STATUS updated. No roadmap phase
changed, no new backlog; product/API/access/AI/operations and README need no change
because domain/setup/public delivery unchanged. No remaining code/evidence work in
the agreed focus correction; external environment acceptance/deployment out of scope.
No dependency reinstall, backend/database/full release suites: frontend-only change,
existing locks unchanged, focused isolated browser config plus build used.
Publication: code/evidence commit e5bca576cfcb237d43ef3f73a648df417bed3ba2,
normal-pushed to origin/main; remote SHA read back identical. Canonical branch
codex/ui-testing-toolkit retained, working tree clean after commit. Reviewed all24
intended files/new fixtures, working/index/committed67014f57..e5bca576 diff hygiene
PASS; added relative links resolve to existing registered documents. No secret or
unrelated payload. Push workflow inspection: CI only, no deployment workflow.
Immediate GitHub API read had not yet registered this commit's run; prior commit's
success is not this commit's CI PASS. Final task response records latest observed CI.

## AUD-22-20261021 — bounded XLSX parsing

Owner «продолжай» authorizes next AUD-22 only. Canonical root
C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
clean base66b3f64a019135f0b78f1f6b907fa421a91cf72f. Evidence/code gap: XLSX
materialized before row limit; workbook lacks finally cleanup. Reuse import reader,
AV/bounded source bytes, preview/confirm and existing domain/permission services.
First reproduce dimensions/rows/columns/compression cases in an isolated subprocess
with hard memory/time limits; then smallest bounded reader fix if confirmed.
Risk: memory/CPU amplification, partial imports, malformed-file errors and leaked
workbooks. Technical resource bounds may reject oversized workbooks explicitly;
no silent truncation. Scope: parser/tests, relevant config and docs, no new UI,
provider calls, working DB, migrations, AUD-18 or other phase.
Focused checks after parser change: valid CSV/XLSX, bounds and malformed inputs,
stream early stop and cleanup, AV preserved. Completion: import boundaries,
lifecycle/import-export/samples/file-scanning suites plus system/migration drift,
controlled subprocess rerun and reachable upload/preview/confirm API tests.
No frontend build/browser/full local suite for backend parser-only changes.
Update contracts/passports/roadmap/status; review commit, normal push, actual CI.

Result: fully completed in agreed local scope. Controlled synthetic XLSX probe
uses Windows Job Object PROCESS_MEMORY hard limit256MiB before Django startup,
parent subprocess timeout12s with owned child kill/wait. Same isolated_runtime
environment, scanner mocked, no DB/server/provider. Base66b3f64a: valid4843bytes
accepted; forged A1:XFD1048576 dimensions4866bytes hit12s timeout; understated
dimensions silently hid6000 appended rows; out-of-range column and compressed
padding accepted. These are synthetic resource/data-loss evidence, not live attack.
Logs/results: output/aud22-20261021/{probe.py,baseline.json,fixed.json}; helpers and
synthetic files ignored, not distributed as user data. Fixed probe: normal file
accepted; dimensions/rows/columns/compression rejected as ValidationError in
0.312–0.500s parser time, full child2.5–3.266s, within same hard caps.

Implementation: apps/core/xlsx_reader.py does bounded ZIP metadata checks and
streaming Expat XML preflight without building a tree; denies DTD/encrypted or
duplicate entries, excessive expansion/ratio/entries and worksheet dimensions,
actual coordinates/counts before openpyxl allocation. Validate all XML/sheets,
read active sheet, reset inaccurate dimensions, iterate and normalize bounded
rows; generator and workbook close in finally even on conversion/error/early exit.
IMPORT_MAX_ROWS remains5000 data rows; XLSX includes physical blanks/coordinates
plus one header. New defaults: columns256, entries256, expanded20MiB, ratio200;
config and .env.example documented, working env unchanged. Existing source byte
limit and AV before parsing retained; no permission/tenant/domain/event change.
Malformed/over-limit files return400; confirm rolls back and allows retry when
valid again. No partial acceptance/truncation. No new dependency or schema.

Verification via `.venv/Scripts/python.exe`, isolated_runtime subprocess:
`manage.py test apps.core.tests_xlsx_reader -v 1`: 9 PASS0.737s.
After final unsupported-compression error handling, completion:
`manage.py test apps.core.tests_xlsx_reader apps.core.tests_import_job_boundaries
apps.core.tests_import_lifecycle apps.core.tests_import_export
apps.core.tests_import_samples apps.core.tests_file_scanning -v 1`:
67 PASS22.120s, no skips. Covers real upload/preview/confirm/replay, confirm-time
limit/recovery without entities/events, invalid upload, exact bounds, forged
dimensions and actual cells, XML/archive limits, malformed/empty files, cleanup,
AV, tenant/permission and domain import regressions. `check` PASS;
`makemigrations --check --dry-run` PASS. Logs focused.log/affected.log/system.log
under same ignored output directory. No failed test attempts; baseline timeout
is expected reproduced risk, not hidden PASS. No owned processes remain.
No frontend/build/browser/full local suite: backend parser only, actual API flow
covered. PG concurrency not rerun: locking/transaction code unchanged, CSV inputs
of AUD-21 unaffected; scoped SQLite and bounded process evidence only for AUD-22.

Final review tightened non-.xml relationship targets (XML is parsed regardless
of filename; opaque binary media remains allowed), implicit row/cell coordinates
and malformed row children. Focused tests_xlsx_reader10 PASS0.655s; affected same
six labels68 PASS19.974s (affected-final.log). Last coordinate/structure delta:
`test apps.core.tests_xlsx_reader.XlsxReaderTests -v 1` 7 PASS0.454s
(parser-final.log); prior unaffected API/domain tests reused. Final bounded probe
fixed-final.json: valid accepted0.375s, all four adversarial cases rejected
0.281–0.328s; total child2.5–2.687s under256MiB/12s. No remaining owned processes.
Final docs registry86/docs33/links744/anchors104 PASS.

Docs: roadmap, integrations/operations contracts, integrations/data-lifecycle/
capabilities passports, README/env, current risk-register summary and STATUS
reconciled; original historical AUD evidence retained. CRM/access/AI/frontend/
product contracts need no change: policy/domain/UI scope unchanged. Docs registry/
links and working/index/committed-range hygiene checked before publication.
No remaining code/evidence/environment/owner-decision gap in local scope.
Full service load, live/deployment and production capacity are outside scope.
Final commit/remote SHA/actual CI reported in final response; not assumed green.
Previous AUD-21 commit66b3f64a CI39596573384 completed success. Next AUD-18
not started; no automation, handoff or new task.

## AUD-21-20261021 — concurrent import rollback and recovery

Owner requested next roadmap item. Evidence gap after AUD-16 row-lock fix;
reuse confirm/preview services and PostgreSQL concurrency tests. Canonical root
C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
clean base3834922c26e90d8d5c09c6dca64e0c3cd3fe1943, no unrelated WIP.
Scope: prove waiting confirm recovers after the first transaction fails during
row processing or after final audit, with no partial entities/events/sync/audit,
one committed result and rejected replay. Change runtime only for a proven defect.
Risk: duplicate/partial writes and stale state after lock wait. Focused gate:
owned disposable PostgreSQL17 concurrency tests; completion: import boundaries,
lifecycle, import/export and sample suites plus system/migration drift in isolation.
No working DB, external sends, provider setup, UI, AI or schema changes intended;
existing permission/tenant checks retained. No frontend build or full local gate
for evidence-only changes. Update roadmap/contract/passport/status, reviewed commit,
normal push and actual CI. AUD-22 and other phases excluded.

Completion: full local criterion proven; no runtime defect on current AUD-16
implementation, no additional lock/idempotency code needed. Added two regression
tests to existing concurrency suite: fail after real client/event/sync writes,
or after final job state and audit write. Observe pg_blocking_pids for actual
waiting request (not timing alone), then release failing transaction. Waiting
request reads original preview with no entities/events/sync/confirmation audit,
commits once; replay400. Failed on_commit callback discarded, successful one runs.
Existing confirm/confirm and preview/confirm tests also pass.

Exact environment/commands: `.venv/Scripts/python.exe` with
`scripts.codex_verify.isolated_runtime`; owned temporary PostgreSQL17 via initdb
`-U support_gate -A trust --encoding=UTF8 --locale=C`, loopback random port,
DATABASE_URL overridden only to disposable cluster. No shared DB or server touched.
`python manage.py check` PASS; `makemigrations --check --dry-run` PASS.
`python manage.py test apps.core.tests_import_job_concurrency
apps.core.tests_import_job_boundaries apps.core.tests_import_lifecycle
apps.core.tests_import_export apps.core.tests_import_samples -v 2`:
48 PASS, no skips, 29.759s. After strengthening final-audit assertion, reran
`test apps.core.tests_import_job_concurrency.ImportJobConcurrencyTests.test_waiting_confirm_recovers_after_row_failure
apps.core.tests_import_job_concurrency.ImportJobConcurrencyTests.test_waiting_confirm_recovers_after_final_audit_failure
-v 2`: 2 PASS2.864s. System/drift also passed again in this harness.
Unchanged affected tests reused; no failed attempts. Logs/harnesses under ignored
output/aud21-20261021/{postgres,focused-final}.{py,log}; both clusters stopped
and removed in finally, no active owned processes. Scanner mocked, no provider calls.
No frontend/build/browser/full local suite: tests/docs only, reachable confirm API
exercised directly. CI uses SQLite and skips row-lock tests; PG proof is above.
Docs registry86, changed/current/passport docs31, links680/anchors95 PASS;
working/index/committed-range hygiene and full intended diff reviewed for publication.

Roadmap, integrations contract/passport, capabilities and STATUS synchronized.
CRM/access/AI/frontend/product contracts and README need no changes: behavior,
permissions, schema, setup, UI and scope unchanged. Historical audit retained.
No remaining code/evidence/environment/owner-decision gap in accepted local scope;
deployment/live excluded. Base3834922c plus task-owned diff; final commit, remote
readback and actual CI reported in final response, not assumed green. AUD-22 next,
not started. No handoff, automation or independent task created.

## AUD-20-20261021 — initial lead and deal lifecycle invariants

Owner authorized AUD-20 after the roadmap status review. Implementation/code gap;
one bounded phase, no AUD-21/22 or new security scan. Canonical root
C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit; starting
HEAD/base a9c8498d4be44c260154acbd0a91d436237c2341; tracked/untracked Git snapshot clean.
The standalone Word report remains an ignored output artifact, not source WIP.

Result: API creation and lead import cannot persist invalid terminal state;
lost reason, server timestamps/actor and initial history agree. Reuse Lead/Deal,
their state/requirement validators, tenant/access layer, activity/audit and import
preview/locked confirm. Inspect analogous deal API/import creation and fix the
same demonstrated initial-state gap. Preserve existing lifecycle commands and
historical data; no migration, working DB, provider configuration or deployment.

Acceptance/check plan: isolated API/domain regressions for normal creation,
LOST without/with reason, initial history/server metadata, import preview and
confirm revalidation, rollback/retry, denied role and cross-Business input;
deal stage/status agreement and required fields. Run focused tests after each
coherent backend slice; completion affected lead/CRM/import and dependent
permission/lifecycle/API suites plus system and migration-drift checks. Use
scripts.codex_verify.isolated_runtime, no external calls or ordinary db.sqlite3.
Frontend inspected for callers; no UI redesign/new terminal-create form intended.
No full-project gate without demonstrated cross-cutting impact.

Impacts: preserve create/import permissions and tenant scope; server owns initial
loss/win metadata. Initial history describes creation, not a fabricated transition
through NEW/OPEN, so no new status/stage-change notifications or automations.
Existing API lead-created automation and import BusinessEvent remain. AI/provider
actions unchanged. Update roadmap, relevant contracts/passports and evidence after
checks; verified commit and normal push to origin main, actual CI separately.
Next: final reviewed commit/normal push and actual CI readback; no next AUD authorized.

Progress: baseline 11 tests reproduced missing initial loss validation/metadata and
non-atomic API creation; 13 failed assertions and 1 metadata error included an
incorrect role fixture (no explicit denial) and exception-handler expectation,
corrected without relaxing acceptance. First API iteration also exposed a misplaced
serializer create override; corrected before dependent work. API8 then PASS.
Lead import + existing import/export22 PASS. Deal baseline6: 5 failures; API6 PASS
after domain initialization. Expanded focused25 PASS (2.509s); system/drift PASS.
Logs: output/aud20-20261021. Affected suite307 PASS (216.591s); later-added Inbox
rollback/retry test1 PASS (0.111s). No skipped tests in that affected run.

Source review found two analogous default-stage holes: deal import could fall back
to a terminal stage; Inbox selected the first stage regardless of terminal/active.
Both now require an active open stage, with atomic error/retry. Lead conversion and
AI tool creation already filter nonterminal stages; their other behavior stays scoped
to existing contracts. No synthetic transition events are emitted during creation.
Frontend caller review found the ordinary create form offered terminal stages but
omits loss/status inputs by design. Minimal necessary UI correction: list active
open stages only; retain existing actions for completion. Add focused real-browser
form checks and one frontend build/types/i18n/bundle check at completion. Use existing
copy/components, no new labels/redesign, no full-browser suite or app reinstall.


Completion evidence (21.10, base a9c8498d + reviewed task diff):
- `.venv/Scripts/python.exe output/aud20-20261021/check.py apps.leads.tests_creation`
  API8 PASS after the first coherent slice; baseline and correction logs retained.
- Same isolated helper with `apps.core.tests_import_lifecycle apps.core.tests_import_export`:
  lead import22 PASS at that slice. Expanded focused lead/deal/import25 PASS.
- Affected command: `.venv/Scripts/python.exe output/aud20-20261021/check.py apps.leads
  apps.crm apps.core.tests_import_lifecycle apps.core.tests_import_export
  apps.core.tests_import_job_boundaries apps.core.tests_import_samples
  apps.core.tests_crm_server_scenarios apps.core.tests_api_contracts
  apps.core.tests_tenant_isolation apps.core.tests_business_flows_e2e
  apps.core.tests_crm_projection_access apps.automations.tests_dispatch_commit
  apps.bots.tests apps.conversations.tests_ai_confirmation` — 307 PASS.
- Later Inbox test: same helper with
  `apps.crm.tests_creation.DealCreationTests.test_inbox_creation_without_open_stage_rolls_back_and_can_retry`
  — 1 PASS. It was added after the affected suite collected tests; runtime unchanged.
- `.venv/Scripts/python.exe output/aud20-20261021/system_check.py` runs `manage.py check`
  and `manage.py makemigrations --check --dry-run` inside isolated_runtime: PASS.
- `npm run build` (includes i18n, tsc, main/widget) and `npm run check:bundle` in frontend:
  PASS. Existing dependencies reused, no installation or lock changes.
- Playwright CLI session aud20 against canonical source, dedicated ports52657/52658,
  disposable DB, mock/eager profile: real login, create OPEN201, reload persistence,
  keyboard stage selection, terminal/inactive exclusion, RU desktop and EN/KK390x844,
  no-open-stage Save disabled PASS. Screenshots inspected. Initial empty-auth refresh400
  and favicon404 only; no flow error. Initial harness used Escape before boundingBox;
  Escape closed the modal as implemented, so corrected harness selected the option
  and repeated the viewport checks successfully. No application change for harness.
- Servers/browser owned by this task stopped; isolated DB disposed. No real providers,
  shared servers, working DB, migration application or deployment affected.

Docs: CRM/integrations/product contracts, roadmap, leads-deals/integrations/inbox/
data-lifecycle/capabilities passports, current risk status and STATUS reconciled.
Historical 17.10 audit and earlier closure bodies preserved. README/platform spec,
access/AI/frontend contracts need no update: setup, architecture, permission policy,
AI behavior and shared UI contract unchanged; affected behavior documented above.
Scope complete: no code/evidence/owner-decision remainder. Environment: only local
acceptance claimed; live/deployment requires its own scope. No PG concurrency claim;
AUD-21/22 and full security certification not performed. No full-project local suite
because behavior-selected affected tests suffice; CI runs its configured full suite.
Documentation validator PASS: 86 registry paths, 32 current/changed documents,
717 local links and 95 anchors. Working diff hygiene PASS. All 5 new source/test
files and complete outgoing diff reviewed for scope/private data/secrets; only
synthetic test identities. Origin main fetched at a9c8498d; normal fast-forward
publication possible. CI workflow contains tests/build/audits, no deployment step.
System/drift PASS reused for unchanged runtime; actual committed-range diff and
publication readback follow after commit.

Publication: runtime/docs commit 1d95d1dec0a50992319c86ab9c6dd7b7c0e981d9,
normal push origin HEAD:main succeeded; remote SHA readback matched. Branch remains
codex/ui-testing-toolkit, canonical root unchanged. `git diff --check
 a9c8498d4be44c260154acbd0a91d436237c2341..HEAD` and index hygiene PASS; clean after commit.
CI run39585017029 queued at first readback, not a green claim. This final documentation
receipt changes no runtime inputs; local verification reused. Final publication/CI
readback is reported to the owner without modifying earlier historical evidence.
No active owned servers/browser processes remain. Next only by owner instruction:
AUD-21 concurrent rollback/recovery criterion, then AUD-22 resource-bounds evidence.

Final readback: documentation commit9054fd07eef31727ac870f5c463cd54893e84f7f
normal-pushed to origin main, remote SHA matched, tree clean before this blocker receipt.
CI39585106684 (and runtime CI39585017029) frontend install/build/bundle PASS;
`npm audit --audit-level=moderate` FAIL. Local reproduction `npm audit
--audit-level=moderate --json` exit1, output/aud20-20261021/npm-audit.json:
2 high package findings: follow-redirects1.16.0 (GHSA-q3jh-wrc6-jgq8,
GHSA-8r9p-f939-6h3c), vite8.0.16 (GHSA-698v-4r3x-3vcv,
GHSA-r825-w8mm-5pxw, GHSA-587h-7wmj-h5pm). `npm ls vite follow-redirects --depth=2`
confirms versions. `git diff a9c8498d..HEAD -- frontend/package.json
frontend/package-lock.json` empty: dependency inputs predate this change.
Backend CI still running Backend tests at readback. No full CI PASS or release
acceptance claimed. Runtime AUD-20 local criteria remain verified; broader dependency
remediation is outside this phase. Under failed-gate rule further publication stopped;
this STATUS/checkpoint blocker receipt remains local/uncommitted, no code WIP.

### AUD-20 CI continuation — owner continue 21.10

Owner authorized continuing the reported CI blocker. Base9054fd07, same canonical
root/branch; starting WIP only this task's STATUS/checkpoint blocker receipt.
Result: repair approved AI create consumer regression and targeted dependency audit
failures; no AUD-21/22, new scan, provider call, working DB or deployment.
CI39585106684 backend2026 tests: 1 failure, 35 skips; crm_create deal receives
unexpected stage_entered_at from ai_core.crm_writes. Caller also duplicates the
new domain creation audit/activity. Reuse shared serializers/domain initialization;
retain exact ApprovalRequest/permission/tenant/replay guards and lead-created effects.
Verification plan: reproduce existing failing AI test in isolated_runtime; assert
single initial activity/audit + server stage time/history and replay; focused AI
command/approval/domain/dependent suites then system/drift. Dependency scope:
vite8.0.16 to patched8.1.6, follow-redirects1.16.0 to patched1.16.1; inspect lock delta,
no broad audit-fix. Risk is dev/build compatibility and shared AI serializer consumer.
Run npm ci once for changed lock, audit, build/types/i18n/widget/bundle, existing
Vite environment/bundle tests and isolated browser create flow. Keep full CI gate
visible and inspect the published candidate's actual results. Docs/checkpoint/status
reconcile prior failed receipt; commit/push only after required local checks pass.

Continuation progress: existing failing AI test reproduced unchanged (1 FAIL).
crm_writes no longer supplies domain-owned stage_entered_at or duplicates initial
Lead/Deal activity/audit. Extended existing regression proves one initial event,
CREATE audit, stage history, server date/probability and replay with one command audit.
All19 tests in apps.ai_core.tests_crm_tools PASS (17.715s). Broader AI/domain suite
running. Approval, role, Business and lead-created automation paths retained.
Dependencies: Vite minimum/lock8.1.6, follow-redirects lock1.16.1. Initial ranged
install selected8.3.5; discarded only that task-owned lock attempt and installed
explicit8.1.6. Reviewed lock delta limited to Vite/rolldown1.1.5 and required
bindings/oxc/wasm/picomatch deduplication, plus follow-redirects. No broad audit fix.
Maintainer advisories: https://github.com/advisories/GHSA-587h-7wmj-h5pm and
https://github.com/advisories/GHSA-q3jh-wrc6-jgq8 list patched versions; npm registry
metadata verified versions/engines. Node24.18.0 satisfies project minimum.
`npm ci`, `npm run build`, `npm run check:bundle`, `npm audit --audit-level=moderate`
PASS (zero vulnerabilities). npm's existing install-script policy blocked optional
postinstall scripts for core-js/esbuild; policy not relaxed, builds successful.
Initial `npm run test:gate-env` omitted required quality profile and failed assertion
ZANI_QUALITY_GATE=1; corrected `frontend_policy.py` uses isolated_runtime and runs
node --test scripts/tests/gate-environment-policy.test.mjs scripts/tests/bundle-budget.test.mjs:
6 PASS. This was a harness failure, no product/policy edit.
Browser CLI aud20ci, canonical source Vite8.1.6, disposable DB ports64901/64902:
real login, stage options exclude terminal, create201 OPEN and reload persistence
PASS; screenshot output/aud20-ci-20261021/created.png inspected. Initial no-session
refresh400/favicon404 only. Owned servers/browser stopped, DB disposed.

Continuation completion gate: `.venv/Scripts/python.exe
output/aud20-20261021/check.py apps.ai_core apps.leads.tests_creation
apps.crm.tests_creation apps.core.tests_import_lifecycle
apps.automations.tests_dispatch_commit` — 214 PASS (148.955s), zero skips.
Then isolated system_check.py: check PASS, makemigrations --check --dry-run PASS.
Logs ci-affected.log/ci-system.log; unchanged non-AI AUD-20 checks reused.
Documentation links/anchors/registry and diff hygiene PASS. Runtime diff limited
to AI consumer and regression assertions; package lock contains only reviewed
Vite dependency closure and follow-redirects. No secrets/private data in outgoing diff.
README/access/AI permission/operations contracts unchanged: no new configuration,
rights, provider behavior or working DB. CRM contract and paused CRM-agent passport
record compatibility fix without unpausing CRM-D01; roadmap notes CI correction.
Scope code/evidence complete locally. Exact base9054fd07; publication/CI still to
verify on the new candidate. Earlier CI failure and initial harness errors retained.

CI remediation publication: 893619fdfb3552cf21d9a7117f5b5312ad91f970, normal push
origin HEAD:main; remote SHA matched. `git diff --check 9054fd07..HEAD` PASS;
clean tree before this publication receipt. CI39588974006 was in_progress at first
readback; authoritative result: https://github.com/999MAX20/PlatformaCRM/actions/runs/39588974006.
This receipt is docs-only, no runtime/input change; working/index/committed-range
hygiene and links checked. Final response records actual latest CI after completion;
no full/live certification is inferred from local PASS or an initial queued CI state.
No owned server/browser/test process remains. Scope has no local code/evidence
remainder; CI is assessed separately at its exact commit. No AUD-21/22 scope added.

Additional CI-stage diagnostic before waiting for full backend: local
`python -m pip_audit -r requirements.txt` FAIL, 9 advisories in certifi2026.7.22
and Pillow12.3.0; old CI did not reach pip-audit after its failed test step.
Continuation scope remains restoring this CI, now also Python dependency audit.
Update only Pillow13.0.0 (required security major) and certifi2026.10.19 using
pip-tools hashes; inspect all transitive differences, retain other pins. Production
and dev locks both carry certifi. Pillow usage source search: accounts.avatars only;
existing JPG/PNG/WebP limits, normalization, AV and own-account access remain.
Checks: hashed install/pip check/audit, isolated accounts avatar/related API tests,
system/drift, certifi CA-load smoke; Python3.11 CI authoritative install/full test.
Local pip26.2.1 and pip-tools7.6.0 have stdlib_pkgs ImportError before compilation;
use disposable lock tooling venv with compatible pip25.3, not a product/tooling policy
rewrite. No app/source copy, no data migration, no provider calls or deployment.
Maintainer release https://pillow.readthedocs.io/en/stable/releasenotes/13.0.0.html
and https://github.com/certifi/python-certifi/security/advisories/GHSA-6q48-6c7w-9gw2
reviewed for patched versions/compatibility. Existing frontend PASS remains valid.

Python lock remediation progress: disposable lock-env pip25.3/pip-tools7.6.0
compiled both locks with --generate-hashes --strip-extras --allow-unsafe --resolver
backtracking and targeted --upgrade-package certifi==2026.10.19 / pillow==13.0.0.
Pillow input range13..<14. verify_python_lock.py proves only those two version
changes (dev lock only certifi). compile_locks.py supplies exact CUSTOM_COMPILE_COMMAND
for reproducible header; no manual hash edits. Local .venv hash install of both
locks changed only certifi/Pillow, pip check PASS, pip-audit production lock PASS.
Pillow13 drops Python3.10, compatible with repository Python3.11 CI and local3.12.
CA smoke initial default SSL context mixed system trust and failed G3-absence check;
revised test parses exact certifi bundle, then loads it:120 bundle certificates,
compromised emSign ECC Root CA - G3 absent, PASS. OS trust-store configuration was
not changed or certified. No live provider requests. Account/avatar/API suite running.

Python dependency completion: isolated check.py apps.accounts
apps.core.tests_api_contracts apps.core.tests_b0_security —128 tests OK (125 passed,
3 PostgreSQL row-lock skips in accounts.tests_recovery),125.714s. The eight avatar
tests cover normalization/replacement/metadata stripping, own-account access,
authentication, AV failure, invalid/oversized/disallowed images and crop bounds.
System/drift PASS after new installed lock. Logs output/aud20-ci-20261021.
No product code changed for Pillow/certifi; no migration or working DB. Profile
Python3.12.14, disposable SQLite/mock. PG account races unaffected, no repeat PG
certification claimed. Unchanged frontend results reused; final combined Python3.11
CI remains authoritative. Earlier CI39588974006/39589110991 used old Python lock,
so their eventual dependency audit does not certify this correction.
Reviewed generated hashes/version delta, working/index diff hygiene and docs links.
README/operations/avatar contract need no behavior/setup changes: existing Python3.11
supported, no format/permission/API/AV policy changed. Lock tooling work-around is
recorded above; no pip policy changed in the shared environment.

Combined remediation publication:4056a4717ec97a1196a5fa61c616bab59f1061b5,
normal push origin HEAD:main; remote SHA matched. Committed range2a168e4f..HEAD
hygiene PASS. CI39590140960 started on combined AI/frontend/Python correction:
https://github.com/999MAX20/PlatformaCRM/actions/runs/39590140960.
This final publication receipt changes documentation only; local checks retained,
links/registry/hygiene checked. Authoritative latest CI completion is read separately
and reported to the owner. No active owned app servers/browser/tests. Disposable
lock tooling remains ignored output, shared pip tooling version not altered.

## DOCS-PILOT-PRODUCTION-20261021 — status reconciliation and product description

Owner requested verification of stopped Deep Scan, current technical documentation
and roadmap, and two descriptions: closed pilot for several dental businesses and
production. Canonical root C:/Users/user/Desktop/PlatformaCRM; branch
codex/ui-testing-toolkit, base ce2c290d3d4be4874e55339bd6bde225098b8683. Starting WIP:
only this task's previous scan-start notes in STATUS and this checkpoint; no runtime diff.
Mode docs/evidence reconciliation. Reuse current contracts, module passports,
platform specification, AUD register, source maps and existing verification receipts.
No new product scope, runtime fixes, provider connection, database migration or scan.
Risk: confusing local implementation with live readiness or deferred ideas with V1.
Checks: reconcile statuses/source references, current document links/anchors/registry,
working/index/actual committed-range diff hygiene and outgoing secret/scope review.
No app build/install/test suite for documentation-only changes. Commit/normal push
under standing authorization; report actual CI separately.

Scan diagnostic: stored run 090dff1a-9b2c-456c-aa7b-f0c0487d0179 still reported running
after the chat waiter was stopped. Owner explicitly confirmed stopping the scan;
cancel_codex_security_scan completed 21.10 at 07:10:46 UTC. Readback: canceled,
active 0, completed independent reviews 0, retained findings 18, partial report present.
This is not a completed audit or 18 new deduplicated defects. Original artifacts remain
in C:/Users/user/.codex/state/plugins/codex-security/scans/PlatformaCRM/
ce2c290d3d4be4874e55339bd6bde225098b8683_20261019T201920Z_ozw4rs8k/.
No completion/restart/worker review performed. The earlier 19.10 report remains
preserved in Git with 36 raw records. Fresh Daybreak advisory 21.10: not_granted;
account approval via https://chatgpt.com/cyber is separate from local permissions.
No configuration changes or application submission performed.

Reconciliation result: product/CRM/access/AI/frontend/integrations/operations and
acceptance contracts, engineering/testing procedures, roadmap, module passports,
platform specification section15 and current AUD/risk evidence were compared by
workflow and readiness boundary. Registry/link validation covers 35 current/changed
documents, 86 registered paths, 812 local links and 93 anchors: PASS, no missing targets.
Commands: `.venv/Scripts/python.exe output/docs-pilot-production-20261021/verify.py`;
`git diff --check`. Local JSON receipt is in the same output directory.
Source spot checks: frontend router and IntegrationsPage/ProviderCard; provider
registry FINANCIAL_SOURCE_READERS remains empty; config/settings.py commerce false
and adapter None; referenced domain/API/tests/evidence remain the source map.
This is a documentation reconciliation, not a new source-wide security review or
runtime certification. Prior PASS is retained only at its named historical boundary.

Corrected current scan/publication state, stale AUD-15-open claim, data-lifecycle
audit boundaries, overall project snapshot and pre-foundation billing description.
Added two product descriptions in existing product.md; no new competing roadmap.
Owner's several-clinic pilot clarification preserves 3–5 users as the earlier
participant estimate, not a clinic count/per-clinic quota. Instagram/site-form V1
requirements remain beyond two-channel pilot R03; deferred D01–D06 are not promises
for the first paid release. Three money domains are explicitly separated.
Other contracts/passports need no behavioral edits: code, API, rights, notifications,
BusinessEvents, AI, configuration and migrations are unchanged. Historical reports
and original security artifacts were not rewritten. Root README needs no setup change.
Remaining: full security evidence/deduplication; open AUD and R02–R07; external
environment/provider acceptance and commercial/operational owner decisions.
These remain in existing registers and are not newly authorized implementation.
Documentation scope has no remaining product-code work; Daybreak approval requires
the account holder's application/approval, not a local config edit. No scan process
owned by this task remains active. Final publication/CI receipt is in task response.

## PROJECT-DEEP-AUDIT-20261020 — full scan explicitly resumed

Current outcome 21.10: canceled at the owner's request, partial coverage only;
see DOCS-PILOT-PRODUCTION above. The following records the original launch scope,
not an active instruction to continue scanning.

Owner: «Приступай к deep scan». Canonical root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, clean initial HEAD ce2c290d3d4be4874e55339bd6bde225098b8683.
Mode comprehensive security analysis/docs, not remediation. Previous canceled scan
220130aa-3d20-4bcf-9415-8d794f1087e3 remains closed; preserved artifacts under
docs/testing/security-audit-20261019-partial are prior evidence, not a fresh PASS.
Scope whole repository, especially SQL injection, HTTP/API/auth/CSRF/SSRF, file and
avatar upload/processing/resource limits/storage/delivery/permissions, plus all
relevant trust boundaries. Plugin coordinator owns independent read-only scans,
validation/aggregation and canonical draft; parent completes once after success.
No working DB changes, source fixes, live attacks, real provider calls or messages.
Multi-pass run may take hours; do not infer deadlock from unchanged parent counters,
restart duplicate scans, or spam uninformative waiting updates. Do not change scan
limits/model/permissions without cause. Managed filesystem profile is now active.
Completion checks: canonical report/coverage and source snapshot, reconcile new
root causes with AUD without rewriting historical artifacts; docs links/registry/
diff/secret review; commit/push/actual CI under standing rules. No app build/install
merely for docs; runtime probes only if separately justified and isolated.
No complete-coverage or production-safety claim before actual results.

## PROJECT-RISK-REVIEW-20261019 — consolidation and comprehensive audit

Follow-up owner scope: preserve current audit records; full Deep Scan explicitly
deferred until later. Saved exact generated report/findings/coverage/manifest/model
under docs/testing/security-audit-20261019-partial, with README and SHA-256 receipt.
All 36 raw records retained, including duplicates; no new AUD IDs or runtime fixes.
Source artifacts remain unchanged. Verification: JSON parse, 36 count, partial flag,
byte identity and credential-pattern review PASS. New-document local links/anchors,
registry uniqueness/existence and working/index diff hygiene PASS. Staged five blobs
match original SHA-256; scoped .gitattributes preserves bytes across checkout.
No app install/build/tests: documentation-only preservation, runtime unchanged.
Publication fetch found origin/main at68c6bf0b, an ancestor of starting HEADdf2b9708;
outgoing range includes five earlier task commits AUD15/06/04/05/16 already reviewed
and checked in their checkpoints. No foreign remote commits or merge/rebase needed.
Normal push will include that existing history; actual readback/CI in task response.
Scope completion is preservation/publication only; comprehensive audit stays partial.
Product contracts, specifications and passports need no behavioral changes: no code,
API, permissions, environment or verified product result changed in this follow-up.

Interruption checkpoint: owner explicitly canceled Deep Scan on 19.10 at 18:34 UTC
(23:34 Asia/Qyzylorda). Scan 220130aa-3d20-4bcf-9415-8d794f1087e3 is canceled;
active reviews 0, one succeeded, four canceled, no worker/coordinator error recorded.
Configured 4 workers, allowance 3 subagents, maximum 40 full scans, 4 consecutive
no-new stopping threshold, 96-hour cap. First full review ran 18:17:23–18:33:24;
another launched 18:33:25. Thus ongoing work, not established deadlock. Parent failed
to explain multi-pass duration and gave repetitive wait updates; do not repeat that.
Original pending call returned canceled; no completion/restart/further audit work.
Retained report: C:/Users/user/.codex/state/plugins/codex-security/scans/PlatformaCRM/
df2b9708401a3075e590b3e5e97bc5369383c34a_20261019T181719Z_op40ld9x/report.md.
Generated canceled report contains 36 findings (19 medium/17 low), partial coverage;
not yet reconciled/deduplicated against AUD and not a completed certification.
Remaining: reconcile saved results if requested, choose bounded continuation explicitly,
final documentation verification and publication. Own six docs remain uncommitted.
User authorized global config change to on-request/workspace-write; valid TOML,
only those two values changed; backup config.toml.before-security-sandbox-20261019-231443.bak.
Managed profile now works; initial missing-profile blocker is resolved. Diagnosis
read service DB in read-only mode with explicit sandbox escalation; no app data changed.

Owner explicitly requested one consolidated document from PROJECT-AUDIT and the
PlatformaCRM UI / PlatformaCRM 2 discussions, followed by a fresh repository-wide
audit, especially SQL injection, HTTP/API/outbound requests, attachments and avatars.
Mode docs + security analysis; no runtime fixes, deployment, working DB changes or
external attacks. Canonical root C:/Users/user/Desktop/PlatformaCRM, current branch
codex/ui-testing-toolkit, clean starting HEAD df2b9708401a3075e590b3e5e97bc5369383c34a.
Reuse AUD IDs, roadmap, existing evidence and approved contracts; preserve historical
reports and closed local scopes. New findings must have source/attack path and
counterevidence; distinguish confirmed defect, hypothesis, evidence gap and policy.
First consolidate, then use the Codex Security Deep workflow for the whole repository.
No other chat is assigned work. Plugin-managed audit workers follow its own workflow.
Checks: docs registry/local links/consistency and working/index/committed diff hygiene;
scan canonical report and honest coverage; no app build/install merely for docs.
Any runtime probes must be harmless and isolated, with synthetic files/data and no
real recipients/provider calls. Completion: reconcile findings/statuses, reviewed
docs commit and normal push, remote SHA and actual CI. Existing AUD-20 implementation
does not start here. Product contracts/passports change only if their factual claims
are affected; analysis alone does not create new behavior or policy.

## AUD-16-20261019 — import job write boundaries

Owner requested document reconciliation first, then AUT-16 interpreted as existing
AUD-16 (no AUT ID). Canonical root C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, clean starting HEAD4a13153c4c24c9b72f9b01bbf9e252606927ea5e.
No other WIP. Scope: current audit completed-task docs, then AUD-16 only; no agents,
other tasks, deployment/working DB changes. Three result statuses are fully done,
partially done with explicit remaining work, not done; live acceptance stays separate.
Scan found stale AUD-05 open claim in capabilities and stale roadmap summary/status
vocabulary; corrected roadmap, capabilities, tasks-automations, STATUS. Existing
CRM/access/frontend contracts already contain relevant completed changes. Historical
evidence is retained; no mass timestamp or whole-project re-certification.
AUD-05 published4a13153c, CI39284791120 still queued at readback, not success.
Docs checks: changed links/registry/AUD mapping and diff hygiene, no app retest.

Implementation plan: prevent client writes to ImportJob actor/status/counters/preview
and immutable context/source. Existing create + preview mapping + confirm API/service
reused; mapping changes rebuild server preview. Confirm locks/reloads job and checks
current lifecycle/permissions/rows again; preserve AV/original-byte limits and rollback.
No new models/schema, providers, AI, imported-entity lifecycle rewrite (AUD-20),
XLSX resource-risk work (AUD-22), full import UI (AUD-12), export scope (AUD-18).
AUD-21 remains separate risk; narrow changed-locking evidence does not implicitly
close the separate phase. Integration events, connector history and audit retained,
effects transactional, no new external sends.
Risks: forged mapping/preview, duplicate confirmation, preview reopening imported job,
foreign actor/tenant, revoked permission, changed source, half import on invalid rows.
Focused tests before dependent changes: forged inputs/immutable updates, allowed
create, mapping re-preview validation, terminal preview/confirm, stale model reload,
source revalidation/AV/limits, denied tenant/role, rollback. Completion affected import
and dependent security/API/tenant/access suites + system/migration drift; isolated PG
for changed locking path. Inspect existing frontend caller compatibility; no build if
frontend unchanged, API integration covers unchanged reachable calls. Docs contract,
passport/roadmap/evidence at closure; verified commit normal push, actual CI. Stop at
AUD-16; AUD-20 not authorized here. Final status below supersedes implementation progress.

AUD-16 progress: initial baseline8: 17 assertion failures (0.558s), confirming
forged fields, ordinary mutation, terminal reopen/stale confirm and mapping shape.
First focused29 had 28 PASS + rollback-fixture error: mock omitted saved phone
header; fixed fixture so rollback is reached with valid mapping. Next focused12
found unknown-column preview ready flag and existing scanner503 normalized to500;
fixed missing mapping error and used existing TemporaryServiceFailure (503 retryable).
Focused14 PASS (0.607s): boundaries13 + ImportAntivirusTests1. Added explicit malformed
request/state cases and PG races; final gates running. API/admin source/context are
immutable; admin bypass closed with read-only history. No frontend calls need changes:
importExportApi.upload sends only allowed3 fields, confirm sends no payload. Existing
ImportPanel remains limited; AUD-12 not implemented. README/setup unchanged.

AUD-16 completion: выполнено полностью в согласованном локальном scope.
Code/evidence/owner-decision remainder none. Environment: local disposable SQLite
and PostgreSQL17 only, scanner mocked, no working DB/migration/deployment/provider.
Version: base4a13153c + reviewed task-owned diff, final commit/remote/CI in response.

Exact checks via `.venv/Scripts/python.exe` and `scripts.codex_verify.isolated_runtime`
environment, subprocess `[sys.executable, 'manage.py', *command]`:
- focused: `test apps.core.tests_import_job_boundaries
  apps.core.tests_file_scanning.ImportAntivirusTests -v 1`: 14 PASS0.607s.
- affected `test apps.core.tests_import_job_boundaries apps.core.tests_import_job_concurrency
  apps.core.tests_import_export apps.core.tests_import_samples apps.core.tests_file_scanning
  apps.core.tests_tenant_isolation apps.core.tests_api_contracts apps.businesses.tests_access
  apps.core.tests_export_jobs -v 1`: 113 discovered, 110 PASS, 2 PG-only skip,
  one loader ERROR96.899s because last label DOES NOT EXIST. This command was not green.
  Corrected missing export coverage with actual tests (unchanged source inputs):
  `test apps.core.tests_b5_performance.BackendPerformanceRegressionTests.test_large_entity_export_uses_background_job_and_private_download
  apps.core.tests_b5_performance.BackendPerformanceRegressionTests.test_entity_export_rejects_absolute_row_limit
  -v 1`: 2 PASS1.090s. Valid affected labels comprise 112 passing tests +2 PG-only
  skips across these runs. No product assertion failed in affected run; unchanged
  passing suites not repeated merely for a corrected loader label.
- `check` PASS; `makemigrations --check --dry-run` PASS, no changes.
- Owned disposable PG17 cluster: initdb -A trust --encoding=UTF8 --locale=C,
  loopback random port, isolated_runtime environment with DATABASE_URL overridden
  only to owned temporary cluster, `test apps.core.tests_import_job_boundaries
  apps.core.tests_import_job_concurrency -v 1`: 17 PASS6.274s, no skips. Two
  simultaneous confirm =>200/400 with one Client/event/sync; preview/confirm cannot
  reopen committed job. Cluster stopped and removed in finally; no shared process
  stopped. No active owned sessions. Logs output/aud16-verification/{baseline,
  focused,focused-final,focused-pass,final-0,completion-0,completion-1,completion-2,
  postgres}.log; failed harness iterations retained, not overwritten as PASS.
- Frontend build/browser/full release skipped: no frontend/dependency changes,
  existing upload/confirm payloads unchanged, real API integration tests cover them.
  No claim of full mapping/history UI (AUD-12) or source resource limits (AUD-22).
- Docs synchronized: roadmap three statuses, capabilities including stale AUD-05
  correction, tasks-automations, integrations passport, integration/access contracts,
  STATUS. CRM/frontend/AI/product contracts and README/setup need no changes:
  imported CRM lifecycle/engine/AI/UX/setup remain unchanged. Clients/leads-deals/inbox
  passports checked against prior completed scope; no stale open claims found there.
  Historical evidence not rewritten. AUD-21 partial note reflects only overlapping
  locking evidence; residual original-risk/concurrent failure recovery criterion remains.
  AUD-10 partial remainder retained. No new backlog or acceptance IDs removed.
Working/index/actual committed-range diff hygiene, changed doc links/registry and
explicit new-file/secret review accompany publication. Standing normal origin
HEAD:main push, remote readback and actual CI required; receipt in final response.
Next authorized stopping point reached; AUD-20 not started.

## AUD-05-20261019 — reachable automation rule editor

Owner «продолжай» authorizes AUD-05 only. Root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, clean base46e25ee799d8bf74a7350a2941502bb5c1353f84.
Result: simple draft opens reachable existing-rule editor; load current composition,
edit typed fields/conditions/actions, validate, atomically save, enable and execute
an actual CRM action. Reuse AUD-06 builder/validation, AUD-04 configuration PUT,
existing permission helper/team API/form primitives. Existing-rule preview must
require UPDATE rather than CREATE/quota for new rules. Preserve existing condition
value types, action settings, active state and priority on untouched round trip.
Scope editor controls/loading/error/retry/forbidden and stale preview; no history
pagination/redesign (AUD-07), new engine semantics, action types, schema or provider.
Permission/tenant: backend UPDATE+original Business; role-aware UI, server authoritative.
No new notification/BusinessEvent/AI/env/migration behavior; actual create_task uses
existing domain engine, isolated synthetic DB only, no working/deployed changes.
Risks: editing wrong rule, failed GET overwrites, loss of config/typed condition values,
stale preview after switch, role denial, activation of empty draft, failed save loss.
Checks: focused detail-preview permission/tenant/no-write and full lifecycle backend
before frontend dependencies; completion all automations + API/tenant/access dependent
suites and check/migration drift. Browser real isolated backend simple draft→editor→
preview→save→enable→lead event→one task; edit reload/failed GET+save recovery, stale
preview, desktop/mobile and RU/KK/EN/keyboard. Build/types/i18n/bundle once at end.
Existing PG locking proof unchanged from AUD-04; rerun only if locking changes.
Docs/contract/passport/roadmap and diff gate; commit normal push and actual CI. Stop
at AUD-05, no other chats/agents/automation or subsequent phase.

Progress: baseline detail-preview tests4 failed (0.136s): missing route returned404;
three diagnostic messages accessed .data on HTML404, one asserted404 !=200. Added
POST /api/automation-rules/{id}/preview/, shared existing-configuration validation
with configuration PUT; UPDATE on original rule, Business immutable, no CREATE/quota.
Focused30 PASS (2.690s): tests_rule_editor4 + configuration12 + action_validation14.
Covers read-only preview, invalid/tenant/role denial, update-only/no-creation-quota,
simple draft→configure→preview→enable→one actual Task under duplicate event.
Frontend editor uses existing builder+API PUT, fresh rule GET with loading/error/retry,
session guard for stale load/preview/save, permission helper, preserves active/priority
and typed condition/action data. Empty draft opens editor after creation; empty rule
cannot enable. Helpers tested with `node --test scripts/tests/automation-editor.test.mjs`:
4 PASS (clone/typed values, edits, legacy assignment aliases, zoned deadline display).
`node node_modules/typescript/bin/tsc -b --pretty false` in frontend PASS. Earlier
root npx --no-install tsc resolved the wrong cached command; no dependencies installed.
Previous AUD-04 commit46e25ee7 CI run39269034161 verified completed/success.
Completion checks on base46e25ee7 + task-owned dirty snapshot, canonical root:
- `.venv/Scripts/python.exe` with `scripts.codex_verify.isolated_runtime` and
  subprocess environment: `manage.py check`, `manage.py makemigrations --check
  --dry-run` PASS; `manage.py test apps.automations apps.core.tests_tenant_isolation
  apps.core.tests_api_contracts apps.core.tests_crm_server_scenarios
  apps.businesses.tests_access -v 1`: 153 found, 150 PASS, 3 PG-only skip, 108.770s.
  Logs output/aud05-verification/final-{0,1,2}.log. No working DB touched.
  PG locking code unchanged; AUD-04 PG29 evidence retained, no redundant PG rerun.
- frontend: `node --test scripts/tests/automation-editor.test.mjs` 4 PASS;
  `npm run build` (i18n/types/app/widget) PASS; `npm run check:bundle` PASS.
  Logs output/aud05-verification/frontend-{build,bundle}.log; no install/lock delta.
- Playwright CLI `npx --no-install --package @playwright/cli playwright-cli -s=aud05`
  open/snapshot/click/run-code against isolated_runtime disposable SQLite + Vite,
  prepared by `node frontend/e2e/django-e2e.mjs prepare`; inline automation.
  Verified simple create auto-opens editor, empty draft disabled, detail preview200,
  PUT200, enable and POST real client/lead through authenticated API => Task count1
  (rule1, lead3, task2), run success visible after reload. Existing editor reloads.
  Injected GET503 hides form; retry loads; PUT503/403 retain draft, retry200.
  Modified form and held preview from closed session cannot authorize save.
  RU desktop1280x720, EN/KK mobile390x844; screenshots visually inspected, no modal
  horizontal overflow, Tab enters name field, Escape closes. Saved types array,
  active=true, priority42, delay9, timestamp seconds survive UI preview/save200.
  Server canonical UTC `2026-12-01T07:30:12+00:00` preserved exactly after reload.
  Initial browser assertion wrongly expected custom503 detail (normalizer shows
  safe generic error); corrected to alert/no-form/retry. Initial timestamp assertion
  wrongly expected incoming +05:00 string; source DateTimeField normalizes UTC.
  Fresh isolated roundtrip proved stored UTC/seconds and all fields unchanged;
  no production fix needed for either harness expectation. Artifacts:
  output/playwright/aud05/, output/aud05-browser/, output/aud05-roundtrip/.
  Both owned runtimes/CLI stopped, disposable DBs removed; no shared servers stopped.
- Docs synchronized: roadmap, CRM API/behavior contract, tasks-automations passport,
  capabilities and STATUS. Frontend/access/AI/engineering contracts and README need
  no change: existing shared patterns/permissions/AI and setup unchanged. Historical
  audit evidence retained; live worker/provider/deployment and AUD-07 stay open.
  Existing server template text is RU in EN/KK outside changed editor; no template
  localization work or whole-page certification claimed.
Required scope PASS; code/evidence/owner-decision remainder none. Docs links/registry,
diff/untracked review, explicit staging, conventional commit, static actual-base gate,
normal origin HEAD:main push, remote readback and actual CI complete publication;
publication receipt is the task response. No new migration/env/dependency/provider
changes. No full-project/release gate: bounded editor, tested dependent areas above.
Next unfinished AUD-16 not started. No active owned background work after cleanup.

## AUD-04-20261019 — atomic automation configuration

Owner «Приступай» authorizes AUD-04 only. Canonical root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, clean base046c83bf2bd1340aa482b76d40ac04b1a9d2a9b5.
Mode fix reproduced persistence gap; result: manual/template aggregate creation and
full composition replacement commit rule/conditions/actions/history together or
roll back together. Activation and direct child CRUD cannot commit invalid active
composition. Reuse AUD-06 validators, Business ownership/access, existing audit and
activity helpers and API response shapes. Add bounded aggregate update API for the
existing rule; reachable editor is AUD-05, not included here. Existing simple draft,
preview and create callers preserved. No schema/env/provider/AI/action execution
rewrite, no working DB, deployment or later phase. No notification/BusinessEvent
on configuration save; record aggregate create/update in existing audit/activity.
Risk: partial active configuration, history without writes, permission bypass,
concurrent activation/child deletion and stale aggregate. Serialize configuration
writes within Business using DB transaction/row lock; keep engine effect semantics.
Checks: isolated fault injection baseline then focused regression after each coherent
service/API slice; success, invalid data, permissions, tenant denial, create/template/
replace/audit rollback and active-last-action guard. Completion all automations plus
core tenant/API/CRM scenarios and access; check/migration drift; isolated PostgreSQL
concurrent config writes because new locking boundary. Existing unchanged UI callers
get API-path evidence; no build/browser solely for backend transaction change unless
frontend contract wiring needs edits. Docs/roadmap/passport consistency, diff hygiene,
commit/normal push/actual CI. Preserve any subsequent unrelated WIP; no agents/chats.

AUD-04 progress: baseline tests_configuration3 confirmed FAIL (0.095s): manual
second action fault500 left rule+condition+first action; template action fault500
left rule; deleting active last action returned204. Initial test expected exceptions,
but the API handler returns500; changed only harness expectation, then confirmed
persistence counts before implementation. First slice: configuration service owns
atomic Business lock + writes/history; generic rule/action/condition CRUD uses the
same lock and validates affected active aggregates before commit. Focused17 PASS (1.136s).
Previous AUD-06 commit046c83bf CI run39236951562 verified completed/success 19.10.

Second slice: PUT /api/automation-rules/{id}/configuration/ replaces the full
composition with original-Business UPDATE enforcement; same Manual serializer and
AUD-06 validation. Service deep-copies shared template data before normalization.
Focused26 PASS (0.960s): aggregate success/order/history; condition/action/activity
failures roll back creation/replacement; invalid replacement, UPDATE denial/foreign
404/Business immutability; active source reparent rollback; generic history failure;
allowed child deletion, draft emptying and activation guard. PostgreSQL races2 and
completion suites running. Frontend source consumers inspected: AutomationsPage
uses unchanged create/applyTemplate/createManual/update API; no frontend edits or
build inputs changed. API evidence proves changed persistence paths, existing-rule
editor remains AUD-05. No build/browser rerun solely for backend transactions.

PostgreSQL17 isolated gate: tests_configuration12 + tests_action_validation14 +
tests_configuration_concurrency2 + tests_follow_up_concurrency1 =29 PASS, 10.537s.
Owned pg initialized with trust only on dedicated loopback/temp data, started hidden,
then stopped via pg_ctl and temp directories removed. Post-test wrapper exited1 only
when printing a mixed-encoding server-log tail to cp1251; tests/cleanup had completed.
Read-back ASCII summary confirmed29/OK; no aud04-pg postgres process or temp directory
remained. Do not mislabel this postprocessing failure as an application test failure
or rerun unchanged tests merely to change wrapper exit. Full log retained.

Completion, 19.10: affected208 tests PASS (205 passed, 3 PostgreSQL-only skips),
157.064s; `manage.py check` and `manage.py makemigrations --check --dry-run` PASS.
Command `.venv/Scripts/python.exe -` with $aud04Final uses isolated_runtime then
subprocess `[sys.executable, 'manage.py', ...]` for check, migration drift and:
`test apps.automations apps.tasks.tests apps.notifications.tests apps.core.tests_tenant_isolation apps.core.tests_api_contracts apps.core.tests_crm_server_scenarios apps.businesses.tests_access -v 1`.
Skipped SQLite tests are the two new configuration races and existing follow-up
concurrency; all three passed on isolated PostgreSQL17. Focused commands same helper
with `test apps.automations.tests_configuration apps.automations.tests_action_validation -v 1`.
PG command: `test apps.automations.tests_configuration apps.automations.tests_action_validation apps.automations.tests_configuration_concurrency apps.automations.tests_follow_up_concurrency -v 2`.
Logs output/aud04-verification/{baseline-confirmed,slice1,slice2,postgres,final-0,
final-1,final-2}.log retained ignored. No running owned process or working DB mutation.
Docs gate: changed links/anchors, registry and AUD01..22 mapping PASS (6 docs),
working diff hygiene PASS; index/actual committed-range gate follows publication.
Only AUD-04-owned changes from clean046c83bf. Version is this commit's source tree;
commit/remote/actual CI receipt in final answer. CRM contract documents full PUT
replacement defaults/child ID recreation; passport, capabilities, roadmap and STATUS
agree. No new rule model, permissions, migration/env/provider/AI/notification or
BusinessEvent behavior. Access/frontend/setup README unchanged: existing rules and
callers reused; UI editor is AUD-05, current API paths covered above. No full/release
or live provider/deployment gate requested. Config version pinning for in-flight Run
not introduced. Code/evidence/owner-decision remainder in AUD-04: none. Deployment
outside scope. Stop here; next AUD-05 not started.

## AUD-06-20261019 — executable automation action configuration

Owner continuation authorizes next AUD-06 only. Root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, clean base 474f432df52d8bbb80f6e307525d25aaaaef425e.
Mode fix confirmed preview/config gap; reuse action models, manual serializers,
condition allowlist, assignment policy, owner runtime actor, domain services, shared
form inputs/i18n/API clients. Result: all six supported action types share config
validation across preview/manual save/action CRUD/activation/runtime; malformed types,
missing required assignment, invalid enums/dates/delays and unavailable/foreign users
fail before effects. Runtime rechecks current membership, entity tenant and applicable
permissions; preview is configuration validation, not proof of future event success.
Keep valid task/note/notification defaults and D-04 appointment follow-up behavior.
UI: typed fields for each action with translated errors and invalidated preview when
inputs change; no merchant JSON requirement. Existing simple draft flow/editor and
atomic aggregate persistence remain AUD-05/AUD-04; do not close those IDs here.
No provider activation, AI feature, strict event graph rewrite, new permission model,
migration/working DB/deployment. Existing runtime owner identity, queue claims, WAIT,
idempotency, retry/cancel and domain activity/notification/BusinessEvent kept.
Risk: permissive legacy config, stale references/permissions, preview/save disagreement,
partial edits, UI stale success, runtime failure/replay and follow-up regression.
Checks: focused baseline and backend validation after each coherent slice; then
all automation/dependent domain/tenant/access tests and system/migration drift in
isolated_runtime. Targeted reachable browser flow desktop/mobile/RU/KK/EN with mock
providers or isolated backend, error/recovery/keyboard; frontend build/types/i18n/bundle
once at completion. No full E2E/release gate. Docs/roadmap/passports + diff review,
normal push and actual CI. No agents/other chats, preserve unrelated work.

Progress and closure, 19.10:
- Baseline isolated focused3 FAILED (0.064s): missing assignment preview200,
  non-object action config POST201, malformed draft activation200. First fix3 PASS.
- Shared action_validation validates all six configs and active Business members,
  existing assignment permissions/capabilities; serializers/template/runtime reuse it.
  Effective PATCH and trigger changes revalidate. Pending-action preflight prevents
  an earlier new effect when a later config is already invalid. Existing retry and
  completed-action semantics preserved. Action/Condition object permission now derives
  Business from parent rule; ordinary owned CRUD was previously incorrectly403.
- Expanded18 initially failed2: inherited parent permission and retry test setup.
  Narrow permission fix and use of real retry endpoint: 18 PASS (5.560s), including
  unchanged D-04 policy6. Final focused14 PASS (1.112s): valid six-action matrix,
  malformed values, CRUD, activation, permissions, foreign/inactive users, trigger,
  tenant entity, revoked membership preflight and successful retry with one effect.
- Completion `.venv/Scripts/python.exe -c $aud06Final` uses isolated_runtime and
  subprocess commands: `manage.py check`; `manage.py makemigrations --check --dry-run`;
  `manage.py test apps.automations apps.tasks.tests apps.notifications.tests apps.core.tests_tenant_isolation apps.core.tests_api_contracts apps.core.tests_crm_server_scenarios apps.businesses.tests_access apps.leads.tests_assignment_patch -v 1`.
  PASS: 207 tests, 206 passed/1 skipped, 155.134s; system check and migration drift PASS.
  Skip: existing tests_follow_up_concurrency (requires has_select_for_update).
  No new locks/concurrency mechanism; D-04 policy passes, PG concurrency not rerun.
- Typed action fields replace merchant JSON; API helper maps indexed field errors,
  draft signature invalidates old/in-flight preview on any input change. Members
  use existing team API, loading/error/retry. New translations RU/KK/EN; no SMS offer.
- Browser Playwright CLI session aud06, canonical Vite65395/Django65394, disposable
  isolated_runtime SQLite and synthetic prepare_e2e_smoke_data; no working DB touched.
  RU desktop: missing assignee400 + inline error, valid member preview, edit invalidates,
  stale save stays in form, re-preview/save succeeds; reload confirms draft persisted.
  EN mobile390x844: simulated team503, retry to real API restores without losing input;
  keyboard Enter/ArrowDown selects notification; typed text/link preview200. KK mobile
  task fields revealed intrinsic-grid overflow; local grid-cols-1/min-w-0 fix verified
  with screenshot and each input/textarea bounds. Escape closes modal. Screenshots
  inspected: output/playwright/aud06/{ru-desktop,en-mobile,kk-mobile-fixed}.png.
  Browser route503 is only fault injection, not provider certification. Existing
  background-worker freshness banner and server template Russian copy outside scope.
  Two CLI quoting syntax failures fixed by single-line code argument; no product fault.
- Initial TypeScript caught nonexistent TeamMember.user.is_active; removed frontend
  assumption, backend retains authoritative account check. Final `npm run build`
  (types+i18n+production/widget) and `npm run check:bundle` PASS after grid/SMS changes;
  i18n6440 keys, chunks/app shell within budget. Full E2E/release gate not requested.
  Ignored logs output/aud06-verification/final-{0,1,2}.log and frontend-final.log.
- Docs: CRM action contract, tasks/automations passport, capabilities, roadmap and
  STATUS reconciled. Access/frontend contracts unchanged: existing parent tenant and
  shared UI rules applied, no new role model. AI/integrations/setup README unchanged:
  no AI/provider/config/schema change. Existing task/notification/activity semantics
  and D-04 follow-up preserved. No working migration, live provider or deployment.
  All WIP belongs to AUD-06 from clean474f432d. Version is this commit's source tree;
  publication SHA/remote/actual CI receipt in final response. No in-scope code,
  evidence or owner decision remaining; environment/live acceptance stays separate.
  Next AUD-04 not started; aggregate atomic save and existing-rule editor AUD-04/05
  remain open. Validation guard alone does not close either item.

## AUD-15-20261019 — pipeline configuration relationship boundaries

Owner request 19.10: reconcile recent completed tasks with roadmap and continue next
work, starting AUD-15. This bounded cycle implements AUD-15; later audit items retain
their existing order. Root C:/Users/user/Desktop/PlatformaCRM; branch
codex/ui-testing-toolkit; clean base 68c6bf0bf5e13139165bcdc9aa7cedc3d0240c74.
Remote main matches base. No unrelated WIP, no agents or other-chat coordination.
Reconciliation: AUD-01/02/03/13/14 code commits and scoped closure evidence present;
remote includes all five. GitHub Actions checked 19.10: all completed/success:
35543e4f run39009392123; 74d9b179 run39010350380; f2bd3be7 run39012177880;
7c10df88 run39021653299; 68c6bf0b run39025582912. Historical CI-pending messages
remain true for their time; current receipt supersedes them. Roadmap AUD-14 row was
closed correctly but introductory summary omitted it; corrected. AUD-10 remains
partial; deployment/live/provider acceptance and other open IDs are not closed.

Mode fix confirmed source gap; acceptance: PipelineStage.business matches pipeline;
StageTransition.business/pipeline/from_stage/to_stage all agree on POST/PUT/PATCH,
including fields omitted in partial updates. Denied mutations leave rows, nested
pipeline/board and audit unchanged. Existing same-Business valid configuration,
readers and deal moves remain usable; permissions and tenant denial retained.
Reuse current serializers, TenantModelViewSet and CRM validation/services; no new
permission system, state graph, pipeline migration workflow or UI editor.
Stage pipeline binding must not be changed through generic edit after creation:
it would invalidate existing deal/history/transition references. Same pipeline
round-trip and ordinary stage edits remain allowed; no automatic data migration.
Risk: partial update bypass, foreign board pollution and broken stage consumers.
Focused reproducer before fix, focused links/partial updates/roles/read projections
and normal configuration/deal-move checks after each slice; completion affected CRM,
core tenant/projection/lifecycle and access suites, isolated system/migration drift,
docs consistency/diff review, commit/normal push/actual CI. UI inspection determines
whether browser/build required; no UI edits expected (current consumers read stages).
No model/migration/env/provider changes; current audit/activity retained, no new
notifications, BusinessEvent or AI action/approval. Working DB untouched.

Progress: baseline isolated `manage.py test apps.crm.tests_pipeline_boundaries -v 1`
FAILED 4/4 (0.082s): foreign-pipeline stage POST 201; wrong-pipeline transition POST
201; pipeline-only transition PATCH 200; existing stage reparent PATCH 200.
Added shared validate_pipeline_links in CRM services and serializer validation of
complete effective values (including omitted PATCH fields). Existing stage pipeline
binding immutable; ordinary edits and same-ID round-trip preserved. No view/schema
or permission changes. First fixed slice: 4 PASS, 0.079s. Expanded focused gate:
12 PASS, 0.780s: endpoint matrix, malformed old row, PUT/PATCH, valid transition relink,
role denial, tenant isolation, board/nested projections, ordinary stage/deal flow.
Commands use `.venv/Scripts/python.exe -c $aud15Check`, isolated_runtime environment,
subprocess manage.py with bounded captured logs and synthetic disposable SQLite/media.

Completion gate PASS (`.venv/Scripts/python.exe -c $aud15CompleteCheck`,
same isolated_runtime/subprocess boundary):
`manage.py check`; `manage.py makemigrations --check --dry-run`;
`manage.py test apps.crm apps.core.tests_tenant_isolation apps.core.tests_crm_projection_access apps.core.tests_crm_server_scenarios apps.core.tests_api_contracts apps.core.tests_platform_crm apps.businesses.tests_access -v 1`.
Frontend inspection: frontend/src/api/deals.ts exposes pipelineStagesApi; actual
consumers use .list in useEntityData/prefetch and display stages in deal screens.
No reachable stage-reparent UI consumer, no UI code/build inputs changed; affected
API flow proves create/update/read/board and move-stage. No browser/build needed.
No new locks/transaction design: PostgreSQL concurrency rerun not required for
pure configuration validation; existing lifecycle locks untouched. No full/release
gate: scoped CRM validation, dependent suites selected above. No external providers.

Final result: 158 affected/dependent tests PASS, 120.935s, no skips; check PASS,
makemigrations --check --dry-run PASS (no changes). Focused12 evidence retained;
no relevant source changes after the passed gate. Initial four expected reproducer
failures are fixed; no failing required gates or unresolved task blocker.
Closure: AUD-15 implemented/verified on base 68c6bf0b plus this task-owned commit;
publication SHA/remote/actual CI recorded in the final task receipt. Canonical branch
unchanged. Roadmap, CRM/access contracts and leads-deals/capabilities passports
reconciled with evidence; historical audit source preserved. README, integrations,
AI, frontend and operations contracts unchanged: no setup, provider, AI, UI, schema
or deployment change. No new document/backlog. No code/evidence/owner-decision
remainder in accepted scope. Environment remainder: deployment and examination of
old working data separate; no automatic cleanup or working DB migration.
Diff hygiene and changed-doc link/anchor/registry/AUD-ID mapping checked. Entire
intended source/tests/docs reviewed, synthetic fixture data only, no secrets or
unrelated WIP. All owned test processes finished. Next AUD-06 not started.

## AUD-14-20261017 — immutable message history and parent scope

Owner continuation authorizes AUD-14 only. Mode fix confirmed message PATCH/delivery
bypass; gap code/evidence. Root C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, base 7c10df881f7d9efbf252985f52378085fe4957b9; clean start.
Reuse access scope, existing message serializers, Inbox send/retry, inbound registration
and provider services. Preserve supported authenticated inbound text creation, but
server delivery metadata/provider IDs/payload and sender provenance cannot be supplied.
Generic PATCH/PUT/DELETE must not rewrite or remove message history (BotMessage and
legacy Message). Read/create scope derives from conversation, not an ownerless child.
Send/retry remain on existing guarded services; no new delivery or permission model.
Non-goals: unrelated BotConversation lifecycle, AUD-15+, provider activation, migrations,
working DB or real sends. No new UI unless an actual consumer regression requires it.
Risk: own/team message lists become empty/leaky; counterfeit inbound side effects;
existing intake/send/retry regressions; history change or partial inbound registration.
Focused reproducer and checks after each slice: payload/sender/status/requeue rejection,
owner/operator own/team/business parent scopes, foreign tenant, normal inbound, valid
send/retry/dedupe and invalid retry. Completion affected/dependent message/Inbox/access/
provider-boundary suites, system/migration drift, docs/diff review, normal push/actual CI.
Provider calls mocked/isolated. Notifications/BusinessEvents retain existing services;
no new AI action or confirmation policy. No agents or other-chat coordination.

AUD-14 implementation: message endpoints retain GET/POST only. Shared inbound
serializer allowlist accepts conversation/text/client sender (+ inbound direction for
BotMessage); provider metadata/state/payload/IDs/timestamps are read-only and explicit
input is rejected. No-context intake fails closed. Existing message serialization
remains readable; validation rejects direct serializer edits too. Parent VIEW/UPDATE
is checked at validation and after Business-first/parent row lock. Message creation,
registration and generic audit/activity are atomic; existing intake notifications and
BOT_MESSAGE_RECEIVED automation are retained. Scope helpers derive child OWN/TEAM
from parent query/object. Main UI uses Inbox send/retry, generic bot messages only read.
Two old tenant tests expected legacy message edits/reparenting; their expected result
now is 405 with preserved original parent/text, matching immutable-history acceptance.

Focused wrapper `.venv/Scripts/python.exe -c $aud14Check` uses isolated_runtime,
subprocess manage.py with runtime.environment and bounded captured logs.
`manage.py test apps.conversations.tests_message_history -v 1`:
- Fixture setup initially failed (0 tests): Bot.scenario is a property; corrected to
  existing default inbox scenario before baseline reproduction.
- Baseline 3 FAIL, 0.123s: PATCH requeues/rewrites (200), wrong-parent intake (201),
  OWN history list missing allowed message. These are reproduced code defects.
- First boundary slice: 3 PASS, 0.157s.
- Extended parent/sender/metadata/intake/rollback/send/retry suite: 11 PASS, 0.599s.
Final focused: 15 PASS, 4.729s, including 13 new history tests and the two updated
`apps.core.tests_tenant_isolation.TenantObjectBoundaryTests.test_message_history_cannot_be_reparented_inside_same_business` and
`...test_message_history_cannot_be_reparented_to_another_business` labels (same wrapper).
System check PASS; makemigrations --check --dry-run PASS, no changes.
Affected/dependent: 288 tests, 216.450s, OK (286 PASS, 2 skipped), same isolated wrapper:
`manage.py test apps.conversations apps.bots.tests apps.bots.tests_pause_inbound apps.bots.tests_handoff_recovery apps.businesses.tests_access apps.core.tests_tenant_isolation apps.core.tests_crm_projection_access apps.core.tests_platform_crm apps.activities.tests_write_boundaries apps.ai_core.tests_conversation_memory apps.ai_core.tests_crm_tools -v 1`.
Additional focused PostgreSQL gate selected for the newly locked inbound-create
boundary: apps.conversations.tests_message_history_concurrency tests two concurrent
POSTs preserve both rows and unread_count. Uses isolated_runtime with a new native
PostgreSQL17 cluster under ignored output/aud14-pg-*, localhost free port, synthetic
trust-only test user/database, hidden child processes. initdb/pg_ctl/createdb and
manage.py test via inline $aud14Pg; finally stops only its own cluster.
Final PostgreSQL17 run PASS: 1 test, 2.979s, both POST 201, two distinct rows and
unread_count=2. Owned cluster stopped successfully; postmaster.pid absent.
SQLite skips: new MessageIntakeConcurrencyTests and existing
HandoffRecoveryConcurrencyTests.test_two_workers_resume_once. New intake checked
separately on PostgreSQL; unchanged handoff concurrency remains outside this gate.
Initial PostgreSQL harness hung on inherited stdout pipe from pg_ctl; no tests ran.
Stopped only owned cluster and changed subprocess output to files. First actual
concurrency run failed BrokenBarrierError: a barrier inside intake waited while the
other request waited on earlier database writes. Moved synchronization to request
start, retaining all success/count/history assertions; corrected run passed.
Synthetic logs retained in ignored output/aud14-pg-ij0o3kcf (test2/test3 and stop logs).
No working DB/server is reused or stopped. This is not a full provider/live drill.

Host command startup/migration preparation slowed temporarily; the focused run
completed without timeout/error. No other processes stopped, no test gates weakened.

Closure: AUD-14 implemented and verified locally on base 7c10df881f7d9efbf252985f52378085fe4957b9
plus this task-owned commit (publication SHA/remote/CI receipt in task final).
Roadmap, access/CRM/integration contracts and identity/Inbox/capabilities passports
updated consistently. No code/evidence/owner-decision remainder in accepted scope.
Environment remainder: deployment and live provider acceptance are separate; no real
sends, credentials, working DB migrations or external delivery claims.
Frontend/API consumer inspection found no message-edit consumer; unchanged UI/build
inputs mean no browser/build gate required. AI/frontend/operations/README need no
changes: no new AI action, UI, settings, schema, setup or deployment behavior.
Full-project/release suite not run: bounded backend/history/access change, affected
and dependent suites above. Historical audit evidence preserved, with current status
in roadmap/passports. No new documents/backlog or agents. No owned processes remain.
Documentation verification PASS: 9 changed docs, changed relative link/anchor,
registry uniqueness and AUD-01..22 mapping; git diff --check PASS. Intended source,
tests and untracked files reviewed; synthetic fixtures only, no secrets/unrelated WIP.
Fetched origin/main matches base 7c10df88; normal HEAD:main publication intended.
Next unfinished criterion AUD-15 is not started or authorized by this closure.

## AUD-13-20261017 — original-object update and lead assignment

Owner continuation authorizes AUD-13 only. Mode: fix confirmed generic PATCH scope
bypass; gap code/evidence. Root C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, base f2bd3be71a793aaaeadcf833b779eaf6726c9476, clean start.
Reuse TenantModelViewSet, LockedCRMUpdateMixin, assign_lead and assignment policy.
Result: VIEW business/UPDATE own cannot take another user's lead via PATCH/PUT;
original UPDATE checked before input changes ownership. Valid lead reassignment
uses the existing service and its audit/activity/notifications atomically with edits.
Retain candidate/tenant checks and existing assign action including unassigned claim.
No new permission model, assignment/unassignment policy, lifecycle expansion or AUD-14.
Risk: shared guard changes consumers, mixed edits partially commit, duplicate effects,
null/same-target round-trips and inactive target. Focused regressions after each slice;
then affected lead/shared access/CRM/task/message consumers, system/migration checks,
diff/docs and normal push/actual CI. API flows plus static UI consumer inspection;
frontend build/browser only if frontend code or demonstrated affected UI needs it.
No migrations/working DB/provider/deployment. Existing assignment notifications reused;
no new BusinessEvent or AI behavior. No subagents or other-chat coordination.

AUD-13 progress: generic get_object now checks original UPDATE for PATCH/PUT in
addition to VIEW; candidate checks and tenant immutability remain. Lead updates
route changed responsible_user through assign_lead under the existing Business/row
lock and outer transaction; ordinary audit failure rolls back assignment effects.
Changed assignment to null is rejected (no unassign domain action); unchanged null
and same-target round-trips remain ordinary edits. Updates reuse the service's owner
exception and inactive/role/availability checks rather than competing serializer rules.
Main lead UI already uses leadsApi.assign with recoverable feedback; no UI changes.

Focused command: `.venv/Scripts/python.exe -c $aud13Check`,
`isolated_runtime(python=sys.executable)` and subprocess with runtime.environment,
`manage.py test apps.leads.tests_assignment_patch -v 1`.
- Initial fixture setup failed on duplicate empty email (0 tests); synthetic unique
  emails and required notification send_at fixed before the reproducer.
- Baseline two regressions FAILED as expected: lead and notification PATCH returned
  200 for takeover (expected 403), 2 tests, 0.086s; no production code changed yet.
- Original-object guard: 2 PASS, 0.096s.
- Assignment service/roles/null/rollback/shared consumers: 10 PASS, 0.774s.
- Owner exception, inactive unchanged assignee and stale reload: 13 PASS, 1.053s.
System check PASS; makemigrations --check --dry-run PASS (no changes).
Affected/dependent run (same isolated command wrapper): 324 tests, 278.592s, OK; 323 passed, 1 skipped:
`manage.py test apps.leads apps.core.tests_tenant_isolation apps.core.tests_mixed_membership_scope apps.core.tests_crm_server_scenarios apps.businesses.tests_access apps.tasks apps.notifications apps.crm apps.activities.tests_write_boundaries apps.clients.tests_sensitive_notes apps.branches.tests_access apps.bots.tests.InboxBackendTests apps.scheduling.tests.CorePlatformTests.test_resource_manager_can_view_but_cannot_update_settings apps.scheduling.tests.CorePlatformTests.test_generic_patch_cannot_bypass_appointment_lifecycle_actions apps.scheduling.tests.CorePlatformTests.test_generic_patch_cannot_bypass_appointment_reschedule_action apps.scheduling.tests.CorePlatformTests.test_generic_patch_cannot_bypass_appointment_archive_action -v 1`.
This covers shared consumers because original UPDATE is a shared security change;
not a full-project certification. Existing SQLite isolation/media/venv, no installs.
Skipped: apps.tasks.tests_concurrency.TaskConcurrentCommandsTests.
test_same_version_allows_only_one_competing_change requires has_select_for_update;
SQLite cannot prove PostgreSQL concurrency. Existing locking was not changed; this
phase proves reauthorization after a stale read, not a new concurrency certification.
No new migrations or working DB/provider/live effects. No outstanding failed gates.

Result: AUD-13 closed in local scope. Source UPDATE is enforced before payload
validation and after CRM lock reload; scoped assignment through both PATCH/assign,
role/tenant/invalid target, null/no-op, history/notifications and rollback verified.
Post-patch review covered generic candidate checks, custom perform_update consumers,
LeadSerializer callers, existing main UI assignment/error flow and inherited locks.
No frontend code: build/browser skipped; reachable API tests provide the changed flow.
No full-project run: affected shared consumers selected explicitly above.

Docs: roadmap/access/CRM, leads-deals/identity passports, capabilities and STATUS
reconciled. README/frontend/AI/integration/operations docs need no change: setup,
UI, provider and deployment contracts unchanged; notifications reuse existing policy,
no new BusinessEvent. Historical audit is preserved; this evidence supersedes AUD-13.
Code/evidence/owner decision remainder in accepted scope: none. Environment remainder:
actual deployment/live acceptance separate; no claim of full PostgreSQL certification.
Diff/links/registry, new test file and outgoing source reviewed before publication.
Base f2bd3be7 plus this bounded commit identifies the verified snapshot; final SHA,
normal push read-back and actual CI are in the completion receipt. AUD-14 next,
not started; its message delivery/payload boundary is not closed by this shared guard.

## AUD-03-20261017 — client sensitive-note read parity

Owner authorizes next AUD-03 only. Mode: fix reproduced Client.notes disclosure;
gap: code/evidence. Canonical root C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, base 74d9b179f71d03f9f0303f656cfea375c373b3aa, clean start.
Reuse can_view_sensitive_field, ClientSerializer, CRM projections and CSV exports;
do not introduce field grants, change role policy or expand into other AUD items.
Scope: Client.notes in direct/list/write responses, nested cards, segment/Inbox
serializer consumers, API-token response without a session actor, sync/background
CSV and stored CSV download after role narrowing. Fail closed without actor;
owner/allowed roles retain notes. Masked empty round-trips must not erase secrets.
Separate history Note records are not Client.notes and retain their existing policy.

Risk: lost actor context hides owner data; cached exports bypass current rights;
masked fields overwrite stored data; per-row permissions cause avoidable N+1.
Focused checks after each backend slice: owner/operator/custom role, same user with
different Business roles, no-context fallback, create/update and masked edit safety;
then sync/queued/download exports and nearest existing suites. Completion: affected
dependent suites, system/migration drift, diff/docs/links, normal push and actual CI.
No planned model/migration/environment/provider/notification/BusinessEvent/AI changes.
No working DB or deployment. No frontend changes unless a demonstrated consumer
regression requires them. Pre/post patch reviews here; no other-chat delegation.

Implementation progress: ClientSerializer masks notes with the existing policy and
per-Business serializer cache; context-free output fails closed. CRM cards/segment/
Inbox consumers now pass actor/request explicitly. Hidden empty edit values are
ignored to preserve stored notes; nonempty restricted writes are denied, consistent
with the existing CRM AI field validation. Owner edits/clearing remain supported.
Sync/queued CSV producers retain columns but mask notes; stored-file download streams
CSV parsing/redaction under current rights, preserving quoted multiline rows and
the original private file. Existing Inbox context/AI read and duplicate/merge
snapshots were inspected; they already mask or omit this field.

Separate bypass review found a notes-segment predicate/count oracle. Segment/filter
reads and actions, client list filtering by segment, and filter writes now apply
the same field policy; ordinary segments and owner evaluation remain available.
This closes an alternate Client.notes projection, not a new permission framework.

Focused commands used `.venv/Scripts/python.exe -c $aud03Check`, Python
`isolated_runtime(python=sys.executable)`, subprocess with runtime.environment and
`manage.py test apps.clients.tests_sensitive_notes -v 1`:
- API/serializer slice: 5 PASS, 1.788s.
- Export/role-change/token slice: 8 PASS, 1.917s.
- Segment predicate slice: 9 PASS, 2.419s.
No failed checks so far. `manage.py check` PASS and `makemigrations --check --dry-run`
PASS (no changes). Affected/dependent run PASS: 199 tests, 130.584s:
`manage.py test apps.clients apps.activities apps.core.tests_import_export apps.core.tests_crm_projection_access apps.core.tests_b5_performance apps.conversations.tests_inbox_context apps.conversations.tests_client_linking apps.integrations.tests_public_api apps.ai_core.tests_crm_tools -v 1`.
Result: AUD-03 closed in local scope. No code/evidence/owner-decision remainder
within this boundary. Tests used disposable isolated SQLite/media and the existing
venv; background job service invoked directly, no live broker/provider/storage.
No working DB mutation or migration. Live rollout/deployment remains separate;
stored private export files are masked on download, not rewritten or deleted.

Post-patch review checked all ClientSerializer callers, CSV producer/worker/download,
segment predicate/count bypasses, existing Inbox/AI field guards and merge snapshots.
No frontend source changed: no frontend build/browser or full-project suite, because
this scoped backend change is covered through reachable API tests and dependent suites.
Contracts access/CRM, clients/identity/data-lifecycle passports, capabilities, roadmap
and STATUS updated together. Frontend/AI/provider/operations contracts and README need
no change: no UI/config/setup/grant or provider behavior introduced. Historical audit
evidence remains immutable; this checkpoint supersedes its AUD-03 finding only.
Docs links/registry/diff hygiene and reviewed source/untracked files checked before
publication. Snapshot: base 74d9b179 plus this bounded commit; final SHA, normal push
read-back and actual CI are recorded in the task completion receipt. Next AUD-13 is
not started and requires the next instruction.

## AUD-02-20261017 — activity and form write boundaries

Owner continuation authorizes AUD-02 only. Mode: fix confirmed security boundary;
gap: code/evidence. Root C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, base 35543e4f86ff6424de2b1d12a654ba788c760c6e;
clean starting index/worktree. Reuse tenant viewsets, access/assignment policy,
activity serializers and form capture services; no alternate tree or delegation.

Result: notes/events cannot link foreign or forbidden CRM records or spoof authors;
POST binds actor to session and PATCH preserves attribution. Form defaults require
an active eligible same-Business assignee; submissions/errors are server-managed.
Inspect polymorphic links and capture-time stale defaults as equivalent entry points.
AUD-03/13/19 and general CRUD redesign are non-goals. No UI redesign, migrations,
new permissions, provider calls, working DB writes or new AI behavior. Existing audit,
activity and capture BusinessEvents must remain; assignment notifications unchanged.

Risk: rejecting legitimate CRM notes/history or public capture, partial-update bypass,
stale assignment after configuration. Focused API regressions for create/update,
foreign/missing/null/aliased links, attribution, permission denial and ordinary flows;
run each coherent backend slice before dependent changes. Completion: affected and
dependent suites in isolated_runtime, system/migration drift, source/diff review,
roadmap/contracts/passports/evidence, normal push and actual CI. No frontend build
or full E2E absent frontend changes or demonstrated need. Separate pre-patch and
post-patch bypass/compatibility reviews here (owner prohibits other-chat delegation).

Initial trace: activities serializers expose client/author/actor without validation;
generic save trusts those values. LeadFormSerializer accepts unrestricted defaults;
submission/error viewsets permit generic writes, while public capture is the proper
writer. Generic form-field authorization is separately tracked as AUD-19.

Outcome: fixed in the authorized local write-boundary scope. Notes/events validate
direct client and supported polymorphic CRM links, tenant plus VIEW/UPDATE scope;
old links are checked before relinking. Canonical model/PK storage matches the
authorized lookup. Session actor is set on create and read-only on update. Missing
and foreign client/default-assignee errors are indistinguishable. Ordinary note
create/edit, public capture, source attribution, automation/BusinessEvent and
read projections remain covered by the existing tests.

Form configuration/template creation reuse assignment_policy; explicit null keeps
the established owner default and checks that assignment. Capture checks current
membership/availability/account state even if the caller holds a stale user object.
An invalid default gives the existing generic public error and retained sanitized
error log, without partial Client/Lead/submission. No automatic fallback/reassignment
was introduced. Submission/error logs allow GET/HEAD/OPTIONS only, including no
inherited archive/restore; Django admin permits inspection but no add/change/delete.

Separate review inspected serializer consumers (CRM cards, lead/appointment note
actions), tenant save/ownership enforcement, forms_service/public submit, assignment
helpers and admin. Confirmed and fixed stale user-state, textual ID normalization,
missing/foreign error-shape differences and the admin log-write entry point.
Other generic CRUD, sensitive client fields and form-field parent authorization
remain their existing AUD-03/13/19 items. This was sequential review, not an
independent security certification. Original audit evidence is not rewritten.

Verification: canonical source, installed .venv, disposable SQLite and safe provider
defaults from scripts.codex_verify.isolated_runtime; no ordinary DB writes/install.
Outer command `.venv/Scripts/python.exe -c $aud02Check` used Python
`with isolated_runtime(python=sys.executable) as runtime` and
`subprocess.run([sys.executable, 'manage.py', *args], env=runtime.environment)`.
Later runs captured output and printed bounded failure logs or the success summary.
Exact inner commands/results, in order:
- `manage.py test apps.activities.tests_write_boundaries -v 1`: initial 5 setup
  errors (duplicate blank User.email in new fixture, not application failure).
  Assigned unique synthetic emails and extended role tests; repeat 7 PASS.
- `.venv/Scripts/python.exe -m py_compile apps/activities/write_validation.py apps/leads/form_assignment.py apps/leads/serializers.py apps/leads/forms_service.py apps/leads/tests_form_write_boundaries.py`: PASS.
- `manage.py test apps.leads.tests_form_write_boundaries apps.leads.tests_forms -v 1`:
  13 PASS after the coherent form slice, before dependent completion work.
- `manage.py check`: PASS; `manage.py makemigrations --check --dry-run`: PASS,
  no changes. No migrations authored or applied to a working DB.
- `manage.py test apps.activities apps.leads apps.core.tests_tenant_isolation apps.core.tests_crm_projection_access apps.scheduling.tests.CorePlatformTests.test_doctor_can_execute_advertised_add_note_for_own_appointment apps.scheduling.tests.CorePlatformTests.test_appointment_add_note_rolls_back_when_audit_fails -v 1`:
  112 PASS, 69.517s. Covers changed domains, tenant ownership, projections and
  existing note actions/rollback. Includes canonical-ID and stale-account fixes.
- After safe error-shape and admin read-only changes:
  `manage.py test apps.activities.tests_write_boundaries apps.leads.tests_form_write_boundaries -v 1`:
  17 PASS, 1.491s, system check PASS. New API/admin assertions cover the changed
  entry points; unchanged dependent flow evidence above reused, not repeated.
- Working/index/actual committed-range hygiene, changed-document links/anchors and
  reviewed untracked files are required before publication; final receipt in chat.
- `.venv/Scripts/python.exe -c $aud02Docs`: PASS, 9 changed documentation files,
  2 changed links/anchors, registry and AUD-01..22 mapping. Reused the existing
  project-audit validator in memory, filtering to the documentation subset;
  no generated inventory or historical audit content changed.

No frontend build/browser suite: no frontend source/copy/layout changes; existing
reachable note and public-form API flows exercised with real isolated DB writes.
No full-project gate, live provider, deployment, PostgreSQL concurrency certification
or existing-data migration claimed. No new OpenAPI artifact/generator in this gate;
API behavior is documented in the current access/CRM contracts. Source schema is
unchanged. Documentation updated: roadmap, access/CRM, clients/leads/identity and
capabilities passports. README/setup, AI/integrations/operations contracts need no
change: no setup, provider mapping, AI action, event schema or environment delta.

Evidence version: base 35543e4f plus task diff; final commit/push/remote SHA/actual CI
returned in this task. All owned test runtimes completed and disposable DBs cleaned.
In-scope code/evidence/owner decision remainder: none. Deployment and any authorized
analysis/remediation of legacy working records remain separate; old authors are not
rewritten. Next AUD-03 not started. No background continuation or other task assigned.

## AUD-01-20261017 — offline lead data isolation

Owner continuation authorizes the next roadmap item AUD-01 only. Mode: implement
and verify the reproduced cross-account offline disclosure. Canonical checkout,
branch codex/ui-testing-toolkit, base de78a674262132227183d2bc7bd175719e533080,
clean starting index/worktree. Reuse lead offline hook, tokenStorage session-clear
boundary and existing isolated Playwright fixtures; no worktree or delegation.

Observable result: A logout → B → offline cannot show or replay A's stored leads;
user/Business/access-context switches never reuse another scope, legacy unscoped
data is discarded, successful empty responses remove stale rows, while offline
fallback/reconnect for the same authorized context still works. Scope includes
queue isolation because it shares the leaking storage boundary; queue capacity,
idempotency and recovery UX remain AUD-10. No backend/API policy, migrations,
notifications, BusinessEvents or AI behavior changes intended.

Risk: stale React/query state or late callbacks repopulate cache after logout;
storage failures or loading/empty confusion break legitimate offline use.
Pre-patch separate review: inspect storage copies, token/session-clear callers,
query placeholder/identity lifecycle and direct consumers. Independent delegation
is unavailable under owner's no-other-chat instruction; perform separate review
passes here, including one bypass/regression pass after focused checks.

Focused checks: behavioral storage tests; isolated browser original A/B trigger,
legacy data, empty/loading/error/recovery and same-user Business/access changes;
nearest session-cache-isolation checks. Completion: build/types/i18n, bundle check,
diff/index/actual committed-range hygiene, updated AUD-01 status/passports/evidence,
normal push and actual CI receipt. No reinstall/full E2E/backend suite needed unless
the implementation demonstrates shared impact requiring it; no live providers or
working DB writes. Earlier audit evidence remains historical, not overwritten.

Outcome: fixed in the authorized local scope. Original A → logout → B → offline
trigger no longer discloses A's data or replays its legacy queue. Same-context offline
fallback survives reload plus 503/connection loss and reconnect; empty success clears
stale rows, loading preserves them, 403 hides/purges them. All ordinary display
preferences remain. Queue isolation is a completed subcriterion of AUD-10; its
capacity/drop/idempotency/recovery work remains open. Next AUD-02 not started.

Implementation: frontend/src/lib/leadOfflineStorage.ts provides versioned owner/
Business keys and access-envelope checks, removes ownerless legacy records and
filters mixed-Business rows. tokenStorage.clear covers logout, expiry, new login,
cross-tab invalidation and MFA transition. Lead hook resets in-memory scope before
render; generation/identity guards stop old callbacks from restoring storage or
continuing replay. Query placeholder cannot cross user/Business; only a genuine
successful response refreshes cache, including empty. Temporary/offline failures
can display the authorized snapshot with the existing offline warning; permission
errors cannot. No new UI copy/layout or backend policy.

Verification, canonical source, disposable SQLite/dedicated localhost ports:
- `node --test frontend/scripts/tests/lead-offline-storage.test.mjs`: 9 PASS.
  Covers same-scope reload, different user/Business, copied envelope, narrowed rights,
  legacy removal, empty snapshot, mixed rows, cleanup/preferences and denied storage.
- Initial `npx --prefix frontend tsc -b frontend/tsconfig.json --pretty false`
  found optional query access TS18048; explicit query guard fixed it; repeat PASS.
- `.venv/Scripts/python.exe scripts/verify_connection_recovery.py e2e/leads-offline-isolation.spec.ts e2e/session-cache-isolation.spec.ts`
  first run: 19 PASS / 3 FAIL, log
  output/connection-recovery/browser-1792217041319146300.log.
  Two failures exposed error panel hiding a valid offline snapshot (desktop/mobile);
  fixed only this fallback. One was a hidden mobile-link test locator.
  All 12 nearest session-cache cases PASS: same-tab/cross-tab identity changes,
  late 200/401 mutation, refresh/retry and queued refresh/logout.
- `.venv/Scripts/python.exe scripts/verify_connection_recovery.py e2e/leads-offline-isolation.spec.ts`:
  11 PASS / 1 FAIL, log output/connection-recovery/browser-1792217363636187100.log.
  Loading/empty/403/expiry and temporary fallback PASS on both viewports. Remaining
  mobile locator selected bottom navigation under an opened drawer; inspected
  error-context, selected the visible bottom link without opening the drawer.
- Separate bypass/compatibility review inspected all tokenStorage.clear callers,
  direct hook/query consumers, legacy/state copies, permission narrowing and late
  responses. Found network source/category mismatch: normalized category is offline,
  not network. Corrected allowlist and added real connection-loss case; no other
  concrete surviving bypass found. This was sequential review, not independent audit.
- Final affected rerun:
  `.venv/Scripts/python.exe scripts/verify_connection_recovery.py e2e/leads-offline-isolation.spec.ts --grep 'A logout|same session'`:
  6 PASS, no skips, log output/connection-recovery/browser-1792217576811081000.log.
  Original exploit, 503 and actual aborted connection/reconnect pass desktop/mobile.
  Reuse unchanged loading/empty/403/expiry and session checks above; no claim that
  earlier whole failing runs passed. Final coverage is 14 distinct lead browser cases
  plus 12 nearest session cases across these runs.
- `npm --prefix frontend run build`: PASS, final output/aud01-build-final.log;
  types, 6420 i18n keys RU/KK/EN, app/widget builds. Informational chunk/plugin/npm
  warnings retained; `npm --prefix frontend run check:bundle`: PASS.
- Working/index/actual committed-range diff hygiene and changed docs links/anchors
  are checked before publication. No dependency reinstall, backend/full E2E suite,
  working migration, provider send or deployment: no relevant backend/config delta.

Evidence version: base de78a674 plus task diff; source blob IDs before publication:
leadOfflineStorage 12e084621809ce3d79d0af02f0c4c23700ecf987;
tokenStorage 8820e63a6a5c548ab7dd22a842bb66dc73e05cd2;
offline hook 10e5cd1d9e3e79848b5bf4fbf64873f61f920c79;
workspace hook ebe25b56daf3e710b0a5566ccd60b95250375126.
Final commit/push/actual CI receipt is returned in this task. Build/source inputs
did not change after final checks. Owned browser runtimes finished and disposable
DBs were cleaned by isolated_runtime; no background continuation.

Documentation: roadmap and frontend contract plus capabilities/access/leads/tasks
passports reflect the changed boundary. Historical audit report remains unchanged.
README, backend access/CRM/API specifications, migrations and existing acceptance IDs
need no change: their setup/runtime contracts are not modified. In-scope code,
evidence and owner decisions: no remainder. Target deployment/live rollout remains
separate; cache is limited to 50 previously loaded rows and AUD-10 remains partial.

## PROJECT-AUDIT-20261017 — additional review and remediation roadmap

Owner requested documentation of the twelve findings reported 16.10, an additional
review for missed problems, and one roadmap with explicit completion/remaining-work
statuses. Current phase: audit + documentation; application fixes follow individual
roadmap items, not this documentation phase. No guarantee of finding every possible
vulnerability; distinguish confirmed defects, policy questions and unreviewed scope.

Canonical C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD/base 56dd1243ef1ad5a4b15ddb94115aaaa6d2b0047a; clean index/worktree.
Gap types: code/evidence/roadmap, with existing environment and owner-decision gaps
retained. Reuse current services/contracts and earlier isolated audit evidence on
the unchanged SHA. No application changes, migrations, live provider calls or
working-data changes. Review is sequential in this task; no inter-task delegation.

Plan: inspect additional security/domain/UI boundaries; validate new source-backed
findings and counterevidence; record a registered audit report and add stable IDs,
dependencies, acceptance and status rules to docs/current/roadmap.md. Update the
relevant documentation's verification boundary without rewriting historical PASS.
Risk: overstating coverage, turning hypotheses into defects, or duplicating backlog.
Focused checks: evidence-to-source paths/lines and reachability, existing decisions,
roadmap/report consistency. Completion: docs-only diff/index/actual committed-range
hygiene, local links/anchors, JSON registry, complete intended diff review; verified
commit and normal push to origin/main under AGENTS.md, with actual CI reported.
App build/full test suite not required for documentation; any audit probe must use
the documented disposable environment. Product permissions, events and AI runtime
remain unchanged. Delivery and final findings are recorded below when complete.

Outcome 17.10: audit/documentation phase complete locally. Registered
[project evidence](../project-audit-20261017.md) and one
[AUD roadmap](../../current/roadmap.md#project-audit-20261017): AUD-01..20 confirmed
(12 prior + 8 additional), AUD-21/22 source risks, AUD-V01 coverage follow-up.
No fixes started. Each row records acceptance, dependencies, status and remainder;
AUD-12 has three explicit subcriteria. Next implementation item AUD-01, not started.

Codex Security scan 1997f7a8-3449-4add-98d8-4bc1d5adc571 finalized successfully:
six additional static findings, 3 high/3 medium, partial coverage. Generated report
exists in local workbench; no independent baseline reviewer. Working-tree warning
is caused by this docs checkpoint; apps/frontend/config/scripts diff from base empty.
Original twelve findings reuse unchanged-source isolated evidence described in report.
No product processes started this phase; earlier owned servers/browser already stopped.

Documentation reconciliation: updated capabilities and clients, leads/deals, access,
Inbox, integrations, tasks/automations and settings/notifications passports at their
affected evidence boundaries. Existing product/access/CRM/AI/frontend/integration
contracts remain required behavior, so no normative changes needed. Existing
specification ADMIN-01..05, acceptance IDs and repository README setup unchanged:
this audit changes neither their behavior nor their accepted scope. No archive edits.

Checks: `git diff --check` PASS; local
`.venv/Scripts/python.exe output/project-audit-20261017/verify_docs.py` PASS
(14 docs files, 45 changed local links/anchors at first completion, JSON/registry and
unique AUD-01..22 mapping). Intended docs diff/new report reviewed for scope and
secrets; no credentials or private production data included. App build/tests,
migrations and full runner skipped per docs-only matrix; this is not release PASS.
Stage/index and actual committed-range hygiene are publication gates, with final
commit/push/CI receipt in this task response. Initial `git fetch origin main` left
the configured tracking ref stale; explicit
`git fetch origin refs/heads/main:refs/remotes/origin/main` and `git ls-remote`
agree at starting 56dd124; outgoing range contains only this docs change.
CI workflow inspected: checks/tests, no deployment step found. `gh` is not on PATH;
query actual CI by GitHub API after push.

Remainder for this bounded audit/docs scope: no code work intended; publication
receipt still follows. Product fixes, extra proof, target environment and owner-policy
questions remain explicitly open in the roadmap; no claim of all vulnerabilities found.

## PLATFORM-ADMIN-ACCEPTANCE-20261016 — stage6 scoped acceptance

Owner authorized acceptance of ADMIN01–04 plus the implemented ADMIN05 foundation;
all deferred ADMIN05 policy/code/environment/live criteria remain open for later.
Mode verification with minimal fixes only for reproduced in-scope defects.
Observable result: reachable business/support → diagnosis → authorized action →
verified result → audit/history across the five existing scenarios.
Canonical C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
base3c6939ee9f014b0bba1d00a4e990180610f9adc4; clean initial index/worktree.
Reuse existing services, APIs, support links, scenario fixtures and browser specs.
Risk: shared navigation/auth/MFA/permissions and interoperation, no new money policy.
Plan: map criteria to existing tests; combined isolated PostgreSQL affected/dependent
suites with real locks; run the five existing browser suites together on one
disposable DB/dedicated servers, add coverage for support/card/history navigation.
Build/types/i18n/bundle from3c6939ee reused while product inputs stay unchanged;
rerun affected gates for fixes. Completion: docs links/registry/diff/index/committed
range and normal push/readback/actual CI. No app installs, working migrations,
full-project E2E, real mail/provider calls or deployment. Permissions, notifications,
BusinessEvent/AI and migration contracts remain unchanged unless a proven defect
requires a minimal documented correction. Stage6 full closure is excluded while
ADMIN05 deferred items remain open; report a scoped acceptance boundary explicitly.

### Criteria, evidence and reproduced defect

| Boundary | Existing proof reused in the combined run |
| --- | --- |
| ADMIN01 details | strict fields, revision/conflict, both platform roles, MFA, tenant scope, audit rollback; UI save/reload/history and case link |
| ADMIN02 ownership | both personal consents, admin-only execution, one owner, business-local previous role, credential revocation, concurrency/rollback; real operator/owner/recipient browser sessions |
| ADMIN03 recovery | matching requester/identity evidence, owner consent for employee, verified new mailbox, one completion, epoch/session/MFA revocation; locally captured email and public completion |
| ADMIN04 employee access | both platform roles, required owner consent, stale role/epoch/terms denial, specialist/task/history preservation, invitation rotation and concurrency; owner/account confirmation flows |
| ADMIN05 foundation | verified bank/adapter receipt, separate application, exact amount/currency/period, duplicate/concurrent apply, independent restrictions and rollback; checkout/check/recovery UI |
| Shared navigation/history | updated platform-details browser scenario follows actual history case link → same Business → all five tabs → readable history in RU/KK/EN; permissions/loading/error/drafts tested by existing scenario suites |

`.venv/Scripts/python.exe output/admin-acceptance-backend.py`:162 PASS on temporary
PostgreSQL17, `manage.py check` PASS and `makemigrations --check --dry-run` PASS.
Exact `manage.py test` labels: apps.billing.tests_commerce,
apps.billing.tests_commerce_concurrency, apps.billing.tests,
apps.billing.tests_settings_scope, apps.core.tests_platform_details,
apps.businesses.tests_ownership, apps.accounts.tests_recovery,
apps.businesses.tests_employee_access, apps.businesses.tests_employee_access_concurrency,
apps.businesses.tests_invitation_concurrency, apps.support.tests_api,
apps.support.tests_domain. Script uses isolated_runtime plus fresh initdb/createdb,
loopback random port and finally pg_ctl stop. Log output/admin-acceptance-backend.log.
No backend changes after this PASS; temporary cluster stopped.

Initial `.venv/Scripts/python.exe scripts/verify_platform_admin_acceptance.py`
reproduced technical labels `clinicCrm.kind.ownership/account_recovery/employee_access/
billing_orders` in access history after visiting all sections. Screenshot/error context
from platform-details desktop; log output/platform-admin-acceptance/browser-1792170464678134900.log.
Stopped the run after reproduction to apply a minimal fix: ClinicAccessHistory maps
these four existing resource identifiers to existing translated tab labels. Backend
identifiers, data, permissions and audit unchanged. Expanded regression asserts all
four labels/no raw keys, history→case→Business navigation and RU/KK/EN/mobile overflow.
Final combined browser:26 PASS, no skips, log
output/platform-admin-acceptance/browser-1792170686600166200.log. All five suites
together, desktop/mobile, RU/KK/EN, support→Business→five tabs→history. Inspected
history KK desktop/EN mobile screenshots, labels/wrapping/case links; automated
locale/overflow assertions PASS. No partial run called PASS.
`npm --prefix frontend run build` PASS types/i18n/app/widget, log
output/admin-acceptance-build.log; `npm --prefix frontend run check:bundle` PASS.
Vite informational timing/chunk warning remains within the bundle budget.
Dedicated browser servers and temporary PostgreSQL stopped; no owned processes.

SCOPED PASS for the agreed local stage6 slice. No remaining code/evidence gap
found in this accepted slice. Full ADMIN05 and full stage6 remain OPEN: deferred
policy/provider/expiry/documents/live/working-environment criteria unchanged.
No permission/notification/BusinessEvent/AI/model/migration changes. Product,
access/integrations/operations/README and acceptance IDs need no changes: their
policy/rollout boundaries are preserved. Roadmap/spec/passports/frontend/testing/
defect knowledge/STATUS/handoff updated. No dependency install, full-project E2E,
live mail/provider, working migration or deployment. Final docs/diff/index/real
committed-range checks and publication/CI in final receipt. Base3c6939ee plus
task-owned diff identifies the tested source; only docs followed application PASS.

## PLATFORM-ADMIN-05-20261016 — payment foundation; full stage incomplete

### Implementation evidence — 16.10.2026

Implemented bank/card order foundation, merchant flow, platform inspector and safe
recovery. Separate payment/application transactions; immutable order terms, unique
receipt/open attempt, row locks, role/MFA/case checks, audit rollback and independent
blocks. No real provider, prices, legal documents or commercial expiry rollout.
All task changes belong to this scope; starting worktree was clean at11179a6.

Commands/results (canonical checkout, existing deps, disposable DB/ports only):
- `.venv/Scripts/python.exe output/admin05-focused.py`:9 PASS bank slice,
  then20 PASS card/API before frontend. First bank run8 PASS plus wrong test import;
  corrected import without weakening assertions.
- `.venv/Scripts/python.exe output/admin05-backend.py`: initial PostgreSQL run failed
  because accessible_businesses DISTINCT cannot be locked with FOR UPDATE. Corrected
  to outer Business query with scoped PK subquery; SQLite alone missed this defect.
- `.venv/Scripts/python.exe output/admin05-backend-fixed.py`:59 PASS on temporary
  PostgreSQL17 cluster. Exact test labels: `apps.billing.tests_commerce`,
  `apps.billing.tests_commerce_concurrency`, `apps.billing.tests`,
  `apps.billing.tests_settings_scope`, `apps.core.tests_platform_details`.
  `manage.py check` and `manage.py makemigrations --check --dry-run` PASS under
  isolated_runtime; clean DB applies billing0006. Cluster stopped in finally.
- `npm --prefix frontend run build`: PASS types/i18n/app/widget; informational
  Vite timing/chunk warning. `npm --prefix frontend run check:bundle`: PASS budgets.
- `.venv/Scripts/python.exe scripts/verify_billing_commerce.py`: initial run stopped
  on Select accessible-name mismatch; next run4 PASS recovery/locales and4 failures
  from ambiguous tax_id selector. Test selectors fixed; no product assertion removed.
  Keyboard test initially sent two ArrowDown events and returned to placeholder;
  corrected to one using the shared Select keyboard contract.
  `--grep 'bank order|card checkout|billing empty'`:2 states PASS (including explicit
  403/503 fallback),4 keyboard-test failures as above. Final
  `--grep 'bank order|card checkout'`:4 PASS, log
  `output/billing-commerce/browser-1792169779896389800.log`.
  Combined8 scenarios PASS:2 recovery from earlier run,2 strengthened state cases,
  4 bank/card cases. Relevant product inputs unchanged across runs; no full-suite
  PASS claimed. Desktop/mobile screenshots inspected, RU/KK/EN and overflow checks,
  keyboard offer selection, actual API result and duplicate application verified.
  Dedicated browser servers terminated; no owned processes left.
- `.venv/Scripts/python.exe output/admin04-links.py`:77 registered docs,248 local
  links PASS at the intermediate snapshot; final docs/index/range results follow
  in the publication receipt. No new authority documents or registry entries.

Residual code: selected provider adapter, expiry/grace/read-only enforcement,
document/fiscal integration after policy. Evidence: live payment/webhook/recovery,
full5a/5b/6. Environment: working billing0006 and commercial configuration not applied.
Owner decisions: seller/bank/provider, prices/period/start, documents/fiscalization,
third-party payer, refunds/partial/overpayment/compensation consequences. No live
money/working migration/production access or complete ADMIN05 claim.
Current product/acceptance requirements preserved; no new policy or closed IDs.
Updated roadmap/spec/passport/access/frontend/integrations/operations/partner brief.
README/product/CRM/AI require no changes: setup/default permissions/legacy lifecycle
remain; commercial requirements and open acceptance IDs are not resolved by foundation.
Publication and CI recorded in final receipt; full E2E/dependency install/live checks
not run (proportional scoped implementation, no rollout authorization).

### Implementation authorization and boundary — 16.10.2026

Iteration evidence: `.venv/Scripts/python.exe output/admin05-focused.py` uses
isolated_runtime, generated billing0006 only (no working DB). First bank slice:
9 tests, 8 PASS + one test import error (MfaStepUpRequired module typo); corrected
import then 9 PASS before card service/API work. No assertions weakened. New
card/API focused run pending. No real provider selected/connected.


Owner approved main logic for bank transfer and card acquiring, 5a diagnostics and
5b recovery; explicitly deferred unresolved commercial decisions and asked to mark
ADMIN05 incomplete. Canonical root C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, base11179a6d390323e8e6a4eeafb6aec6b7276940c9, clean start.
Mode implementation; code/evidence plus explicit policy/environment remainder.
Approved: buyer distinct from payment method; platform_admin confirms bank receipt;
both platform roles inspect/recover with fresh MFA/open case/reason; exact full
payment, one application, immutable evidence/audit, independent blocks retained.

Deferred: seller/bank/provider; prices and period-start rules; documents/fiscalization;
third-party personal-card payment for company; refunds/overpayment disposition.
No live payments, working migration, money movement or policy approval implied.
Implementation accepts only explicit approved offer terms and has no seeded live
prices/period calculation. Commerce disabled by default. No provider is selected:
provider-neutral checkout/verified-result/reconciliation contract with isolated test
adapter; unconfigured card mode fails closed. Actual adapter/live certification is
remaining work, never advertised as working production acquiring.
Reuse Subscription/Plan, entitlement_summary, billing permissions, platform audited
reads, support cases, MFA, shared UI, API layer, isolated test/browser runners.
SaaS receipt belongs to platform billing, not merchant Connector/CRM Payment;
provider-specific integration remains behind an adapter. No merchant BusinessEvent
or AI automation event; durable billing history and audit own the effects.

Observable result: merchant offer/order/payment flow and operator order/receipt/
application inspector with bank-confirm and safe retry; no false Paid or double
period. Applied subscription fields/actual technical quotas are re-read; full
commercial expiry enforcement and live acceptance remain visibly unproven until
remaining rollout contract is implemented, not inferred from status=active.
Verification high risk: each coherent service slice isolated focused tests before
UI. Money/amount/currency/order/tenant, fresh role/MFA denial, audit rollback,
idempotency/stale input, missing adapter, uncertain create/reconcile, refund/late
notifications, cross-channel overpayment, preservation of security/manual blocks.
Completion real PostgreSQL concurrency + affected billing/platform suites,
system/migration drift, intentional isolated migration, targeted merchant/operator
browser desktop/mobile and RU/KK/EN; frontend build/types/i18n/bundle once.
No deps install, full E2E, working DB, real provider/send/deployment.



Owner follow-up: document comparative payment analysis and create a short plain-text
partner discussion brief. Mode docs-only; no adopted financial policy or runtime.
Base 4994e45f5cc078aa97fdb770d94b8120d9ab44c0, canonical PlatformaCRM,
branch codex/ui-testing-toolkit, clean start. Scope: existing spec15.4 analysis,
partner .txt brief registered as evidence, roadmap/passport/navigation and status.
Plan/risk: distinguish buyer from payment method, verified public competitor facts
from proposed architecture and unresolved tax/period/permissions decisions. Reuse
sources researched in this conversation; no claims of live provider acceptance.
Checks: diff working/index/committed range, registry and local links, concise brief
content review. No app tests/build/install/DB: documentation only.
Result: spec15.4 records competitor facts with primary sources and proposed common
transfer/card architecture; UTF-8 .txt partner brief covers buyer types and seven
decisions. Roadmap/passport/status/navigation updated; registry77 and local links193
PASS (0 issues), working diff hygiene PASS. Source facts reused from preceding
research, no provider contract/test/live acceptance claimed. Brief reviewed for
clarity, no secrets/private data; no unrelated changes. Product/access/acceptance
contracts unchanged: no new approved rules and open IDs retained. Index/range checks
at publication; commit/push/remote SHA/CI in delivery receipt.




Owner follow-up: save the bank-transfer proposal in technical documentation for
later discussion and explain the next stage. Current mode docs-only; implementation
paused pending money/source decisions, no recommendation treated as approval.
Scope: spec15.4 proposal, roadmap status/dependencies and corrected stale 3/5 count
to 4/5 from existing ADMIN04 evidence, subscription passport, STATUS/checkpoint.
Starting dirty STATUS/checkpoint belong to this same task; no unrelated WIP.
Plan: preserve proposal/requirement/runtime boundaries; diff hygiene and local-link/
registry consistency only. No app tests/build/DB needed for Markdown.
Product/access contracts and README unchanged: no adopted policy, API, permission,
setup or runtime change. Existing registered docs reused, no new backlog.
Result: proposal records evidence, immutable obligation/payment/application links,
proposed roles, minimum exact-payment scope and unresolved Q20-Q22, storage and
period/refund decisions. Next after 5a is 5b; after ADMIN05 is stage6 acceptance.
Checks: working diff hygiene PASS; registry76 and local links157, no issues.
No application tests/build: docs-only. Index/committed-range hygiene at publication.
Delivery: normal push
under standing authorization, remote SHA and actual CI reported in final receipt.



Owner requested continuation after ADMIN04 publication 243de5d. Next roadmap phase
is ADMIN05a: verified payment evidence and inspector; ADMIN05b recovery depends
on its approved contract. Mode preparation/implementation; gaps policy/code/evidence.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD/base 243de5d60eee90eb00f4c5b11aa9ecde38ff8179, clean index/tree.
Observable goal: inspect real subscription/payment evidence without inventing Paid;
reuse billing models, entitlement summary, platform audited reads and support/MFA.
No working DB changes, live payment collection, provider credentials, new prices,
CRM payment ledger reuse or full commercial billing rollout authorized implicitly.

Source review: billing has SubscriptionPlan/Subscription/UsageCounter only; no
verified platform-payment ledger/invoice obligation/provider reconciliation source.
Metadata pause/resume/cancel changes status but is not paid-access enforcement.
get_plan_limits reads the plan independently of subscription status/due date;
ACTIVE/GRACE/READ_ONLY is approved future policy, not current enforcement.
CRM Payment represents merchant receipts and cannot establish SaaS payment.
Existing seed prices/limits are not approved commercial terms.

Open owner decision requested: bank-transfer confirmation by platform_admin from
bank evidence, followed by support/admin recovery with MFA/case (proposal), versus
specified payment provider, versus diagnostic-only scope. No answer inferred.
Period/amount/currency/refund rules remain unresolved Q20-Q22; settle the selected
source first and present concrete dependent terms before financial writes.
Permission/notification/BusinessEvent/AI/migration impacts are pending that choice;
no runtime source edits or processes started during preparation.

Verification plan: money/access high risk. After each authorized backend slice,
focused isolated tests for exact amount/currency/Business/obligation, confirmation
origin, invalid/refunded/stale evidence, role/MFA denial, duplicate/concurrent
application and audit rollback; completion affected billing/platform/access suites,
system/migration drift, applicable isolated migration, targeted reachable browser
states and frontend build/types/i18n/bundle. No full-project gate just for continuation.
For this preparation note only: diff hygiene, document consistency and local links.
Next step: owner chooses payment evidence source; then finalize bounded ADMIN05a
contract. ADMIN04 closed evidence is retained; no new acceptance marked passed.

## BUSINESS-LOGIC-QUESTIONS-CATEGORIES-20261016 — documentation

Owner requested two categories: questions solvable together through analysis and
proposals, versus questions requiring owner/partner business decisions.
Mode documentation; gap policy framing. Canonical root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, start/base e73da43e9ecdd5d7175cb8b60aa950206b5af0a7.
Scope: existing questions document plus separate status/checkpoint entries only.
Pre-existing ADMIN04 source/untracked work and shared-file edits remain unrelated;
only additive task hunks staged. No new policy, permissions, roadmap or runtime change.
Plan/risk: avoid treating analysis as owner approval; keep all Q01-Q25 exactly once,
mark mixed dependencies, reconcile Q10 with already accepted ADMIN04 authority.
Result: 10 analytical questions, 15 owner/partner decisions; original scenarios kept.
Checks: PowerShell regex coverage/unique IDs/category counts 10+15 and local link
existence PASS; working/index diff checks and real committed-range check required.
No app installs/build/database/browser tests: docs-only matrix. Source review of
current ADMIN04 checkpoint prevents reopening already approved permissions.
Fetch main readback matched starting HEAD. Delivery: task-only docs commit, normal
push to main, remote SHA readback, inspect CI separately; no deployment requested.

## PLATFORM-ADMIN-04-20261016 — preparation and employee access repair

Owner said to continue after published documentation reconciliation e73da43;
next unfinished administrative scenario is ADMIN-04. Canonical root
C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
starting HEAD/base e73da43e9ecdd5d7175cb8b60aa950206b5af0a7, clean tree/index.
Mode implementation; gaps code/evidence. Observable goal:
operator diagnoses employee User/membership/invitation/dependencies and performs
specifically authorized repairs with audit, preserving history/specialist state.
Reuse BusinessMember/BusinessInvitation/BusinessRole, support cases, platform card,
MFA, current user/epoch checks, Account confirmations and existing invitation accept.
No ADMIN05, ownership transfer, credential bypass, live sends, deployment or working
migration implied. ADMIN03 remains the approved identity/email recovery procedure.

Source review: invitations have pending/accepted/revoked/expired states and seven-day
expiry; creation currently records delivery_channel but does not perform sending.
Existing recipient must authenticate as that exact account; new recipient chooses
own password. Token acceptance locks invitation and creates/updates membership.
BusinessMember and User each have independent is_active; disabling membership does
not disable specialist or automatically reassign work. Current membership writes
share a Business/member lock with ADMIN02 ownership; any new writes must preserve
this boundary and cannot downgrade/disable the owner. Existing platform card has
separate details/ownership/recovery/work/support/access sections and reusable draft
and permission/error handling. New diagnostics must not disclose credentials/tokens.

Owner approved both platform roles + recent MFA and support case for invitation
reissue/revoke, membership disable/restore and assigning an existing role, preserving
the owner and specialist. Owner then approved personal owner confirmation for
granting/restoring access or role change, and repairs limited to the selected
Business. No global User unblock. Disable/revoke need an open case and reason but
no owner wait; restore/role/reissue require owner confirmation of immutable terms.
Persist a 24-hour request with actor, owner/epoch, exact target/action/role and
state revision; reject stale consent and repeat effects. Owner confirms in Account;
platform executes with fresh MFA. Reissued link remains in existing merchant team
invitation flow (no automatic email/transport claim and no token in platform reads).
Intentional businesses0013 migration is tested only in isolation.

Diagnostic design from existing code: reuse audited_response/clinic_access for
Business-scoped, fail-closed audited reads and no-store responses. List inactive
members too; report User.is_active separately from BusinessMember.is_active and
role availability. Scope specialist Resources by business + linked_user, and show
their state independently; never infer specialist retirement from disabled login.
Show invitation status/expiry and recipient identity without token or acceptance URL.
An invitation recipient without a membership must not expose another Business's
account or dependencies. Dependency counts/links must use the selected Business.
Existing ADMIN03 candidates intentionally exclude inactive accounts/members;
its recovery list therefore cannot replace this inspector.

Verification plan: high-risk access changes; focused isolated service/API checks
before UI for role/MFA/tenant denial, owner protection, invalid/expired/stale inputs,
repeat/concurrency, audit rollback, preserved specialist/history/other memberships
and invitation acceptance. Completion: affected/dependent team/invitation/ownership/
recovery/support suites, PostgreSQL concurrency, system/schema and any intentional
isolated migration; targeted operator/account/invitation desktop/mobile flow, RU/KK/EN,
loading/error/empty/forbidden/conflict/draft states, frontend build/types/i18n/bundle.
No full E2E, dependency reinstall, working DB/SMTP/provider or production evidence.
Notification/BusinessEvent/AI impact: expected no new automatic reassignment or events;
invitation delivery/confirmation transport must be explicit in accepted contract.
Implemented: EmployeeAccessRepair + businesses0013, employee_access service,
selectors and dedicated platform/account APIs; token-free scoped diagnostics;
BusinessEmployeeAccessPanel, Account confirmations, RU/KK/EN; isolated browser runner.
Invitation accept/revoke now share Business lock with repair and protect current
owner/unavailable role/team. Immutable target summaries preserve request history
without preventing ordinary membership/role deletion. No automatic transport,
reassignment, global credential/account change, new BusinessEvent or AI effect.

Focused iteration: `output/admin04-focused.py` initially failed on test-fixture
resolved_at/requester constraints, wrong invitation URL, expected MFA403 versus
the existing MFA401/code contract. Fixed fixtures/expectations; next14 tests PASS
before dependent UI. `output/admin04-focused-final.py`14 PASS after summary fields.
`output/admin04-backend.py`: PostgreSQL122 real tests passed; overall gate FAILED
because nonexistent apps.businesses.tests label produced one loader error. This is
not reported as a green gate. Corrected/expanded `output/admin04-backend-completion.py`
73 PASS (employee access, concurrency, settings/team, invitation concurrency, access),
system check and migration drift PASS. Reuse unaffected ownership/member-deactivation/
recovery/platform-CRM results from the former run; source unchanged in those paths.
Stable cross-business participant lock order then checked through
`output/admin04-lock-order.py`: PostgreSQL23 PASS, including4 concurrency cases,
system/schema PASS. All temporary clusters stopped/removed; no working DB touched.
Frontend first build stopped at fallback ordering in en/kk; moved existing ru spread
before translations. `npm --prefix frontend run build` PASS (i18n/types/app/widget),
`npm --prefix frontend run check:bundle` PASS. Logs: output/admin04-build-fixed.log,
output/admin04-bundle.log. `output/admin04-support.py`:32 dependent support API/domain
tests PASS on isolated PostgreSQL; no support source changes required.

Browser: `.venv/Scripts/python.exe scripts/verify_platform_employee_access.py` first
run4 PASS (invitation reissue/accept/revoke and states/locales, desktop/mobile),2 failed
because test-only raw GET reused pre-MFA-enrollment credentials (401). Actual UI
disable succeeded. Changed helper to inspect the current UI-authenticated GET;
`--grep 'disable restore role'` then2 PASS. Combined6 scenarios cover all5 commands,
personal owner consent, support-case creation for inactive membership, preserved
specialist/assigned task, invalid MFA, conflict, draft guard, empty/503/retry/403,
RU/KK/EN and desktop/mobile. Logs in output/platform-employee-access/browser-*.log;
first-run screenshots/traces preserved in first-run/. Manually viewed RU desktop,
KK mobile and completed mobile invitation/member histories; no page overflow.
Source unchanged between the two browser runs; only the helper changed. Servers
were canonical local sources on dedicated ports with disposable fixtures; stopped
by runner. No live provider, working migration or full-project E2E claimed.

During implementation HEAD advanced to36f068a (separate docs questions task).
Reviewed3-file docs-only commit; its additive STATUS/checkpoint entries preserved.
ADMIN04 starting base remains e73da43; no source conflict or ownership transfer.
Current docs/spec/roadmap/passports record implementation and residual boundaries.
No remaining local implementation criterion identified; working businesses0013,
target acceptance, external invitation delivery and full history beyond50 requests
remain explicit boundaries. Global unlock excluded; ADMIN05 not started.
Final review: working diff hygiene PASS; output/admin04-links.py confirms76 unique
registered paths and383 local links/anchors in changed docs with no issues. Reviewed
all intended source/test/migration/UI/docs additions; no secrets, real customer data
or unrelated WIP included. No runtime/full-E2E rerun for subsequent docs-only edits.
Delivery receipt (commit, normal push, remote SHA, actual CI) follows in task reply
and output/admin04-publication.json. No owned processes remain.

## DOCS-RECONCILIATION-20261016 — current documentation and roadmap

Owner requested documenting ADMIN-03 delivery, reconciling all active technical
contracts/passports/specifications and roadmap with implementation, recording
remaining work for closed stages, and mandatory ongoing documentation rules.
Mode audit + documentation; gaps evidence/roadmap/documentation. No product changes,
new stages, migrations, live calls or deployment. Canonical root
C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD/base dc1eedf93a1532f538cd513a339130b3b4580835; working/index clean.
Reuse current registry, source/service/API/UI/tests, scoped checkpoint evidence and
Git/CI receipts. Historical test results retain their exact boundaries; this static
review is not a fresh functional/security/production certification.
Risk: stale planned status, conflating support-note with new platform permissions,
and local scoped completion with live readiness. Focus: reconcile these claims,
retain open acceptance and distinguish requirement/code/evidence/environment gaps.
Completion: active-document coverage record, corrected contradictions and stage
notes; rules in AGENTS/template/engineering/passport guidance; working/index/range
hygiene, local links/anchors, registry JSON and intended patch review. No builds,
installs, DB/browser suites for docs-only. No runtime permission/notification/event/
AI/env effects. Publish reviewed docs to origin main by normal fast-forward only;
inspect actual CI separately. No owned background processes started.

Completed static reconciliation16.10: coverage and code/evidence mapping in
`docs/testing/docs-reconciliation-20261016.md`; roadmap now records actual ADMIN01/02/03
and MB/S/R closures with explicit remaining code/evidence/environment/policy boundaries.
Corrected stale multi-branch activation, Kazakhstan hosting, manager permissions,
publication blockers and accepted analytics definitions. Existing integrations UI gaps
remain documented (selected Business/pagination and generic1C credential payload,
error/view/history handling); no source fixes or new product phase performed.
AGENTS, engineering, task/passport templates and documentation navigation now require
completed work + remaining criterion and updating focused docs outside roadmap.
Historical reports/archives retained; the active integration review gets only a dated
pointer to current evidence. Found/corrected obsolete writer coordination in testing,
README and handoff; no coordination actions were taken.
Verification: `git diff --check` PASS; `.venv/Scripts/python.exe
output/docs-reconciliation/verify_docs.py` PASS: unique76-entry registry, all registered
paths present, local targets/anchors valid, only Markdown/JSON changes. Full intended
patch/new report reviewed; no secrets/private user data or unrelated source changes.
App install/build/system/schema/DB/browser suites skipped by docs-only matrix, not
claimed as fresh PASS. Intermediate inspection corrections (duplicate capability rows
and misplaced handoff notice) fixed before staging; initial report patch syntax error
made no edit. GitHub CLI absent; read-only GitHub API used for CI instead.
`git fetch origin main`, `git rev-parse FETCH_HEAD` and direct `git ls-remote origin
refs/heads/main` confirm dc1eedf; local origin/main tracking ref is stale and unused.
GitHub API: f7d74d5/cafcea5 CI success; dc1eedf CI38873408099 in_progress at observation.
Workflow inspected: CI only, no deployment. Working/code inputs unchanged from base.
Next delivery: explicit reviewed-path stage, cached diff check, conventional docs
commit, real committed-range hygiene against dc1eedf, normal HEAD:main push and
remote SHA/actual CI receipt in task response and ignored output/docs-reconciliation.
No implementation residual within this docs scope; no owned servers/background jobs.

## BUSINESS-LOGIC-QUESTIONS-20261016 — documentation

Owner requested saving the preceding analysis questions inside the project.
Mode documentation; gap policy/evidence. Result: 25 numbered discussion questions,
scenario/options/proposal/dependency, approved boundaries and decision-record format.
No new product policy, roadmap phase, implementation, tests or live operations authorized.
Root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD cafcea5b2b2143077072fbefd3330b7b8839c1f2.
Starting dirty ADMIN03/support/account/runtime/docs work is unrelated and preserved;
STATUS and this checkpoint receive only separate additive task entries. Starting
tracked patch and shared-file copies retained in the task's temporary snapshot.
Scope: docs/testing/business-logic-questions-20261016.md, documentation registry,
docs README, acceptance cross-reference and these task/status entries.
Risk: proposals mistaken for approved policy or a competing backlog. Mitigation:
evidence role, explicit unapproved status, existing IDs and contract ownership.
Verification plan: docs-only working/index/real committed-range diff hygiene,
25 unique sequential IDs, local link targets, JSON registration and full intended
patch review. No app build/install/database/browser suite: runtime unchanged.
Permission/notification/BusinessEvent/AI/migration/environment effects: none.
Publication: explicit task-owned paths/hunks only; normal push to origin main
only after fetch proves the outgoing range is authorized and fast-forward.
Docs verification PASS: git diff --check -- <six task paths> and
 git diff --cached --check; PowerShell validation found exactly Q01-Q25,
24 existing local link targets and one evidence registration in parsed JSON.
Intended staged diff reviewed: six documentation files, additive task changes only;
concurrent ADMIN03 change in docs/README.md excluded from the index.
Application suites skipped by docs-only matrix. Fetch/direct remote readback
confirmed main=cafcea5; origin/main tracking ref is stale and is not used as base.
Workflow inspected: push triggers CI, no deployment job declared.
Next delivery steps: docs commit, git diff --check cafcea5...HEAD, normal
HEAD:main push, direct remote SHA readback and actual CI status inspection.

## PLATFORM-ADMIN-03-20261016 — implementation

Owner requested continuing ADMIN-03 after ADMIN-02. Explicit decision: loss of
all access requires contacting support and supplying information for identity
verification. This does not yet define sufficient evidence or operator authority.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD cafcea5b2b2143077072fbefd3330b7b8839c1f2, clean working tree.
Mode preparation, gaps policy/code/evidence. Scope: email/access diagnostics and
support-assisted recovery; no ownership transfer, ADMIN04, billing or deployment.

Read-only source review: accounts/email_changes.py already requires own password
and enabled MFA, confirms a ten-minute new-mailbox code, limits invalid attempts,
checks auth epoch and revokes sessions. SMTP failure rolls back the challenge;
successful send is transport acceptance, not proof of mailbox delivery. Existing
MFA recovery codes require possession; disable_mfa requires password and factor.
SupportCase can be created by platform staff, but ordinary support access requires
authentication. A channel accessible without login must be selected for total loss.
User identity/email are global: recovery must not be disguised as a membership edit.

Owner approved both platform_admin and platform_manager executing recovery in
response to the proposed recent-MFA/support-case flow. Admin-only restriction rejected.
Initial questions, resolved by the accepted procedure below: evidence for identifying an
owner versus employee and contact channel without login.
No dependent recovery mutation implemented before these decisions. Existing account,
MFA/session, support/audit and platform card layers will be reused.

Verification plan: high-risk identity/access behavior. After each coherent backend
slice, isolated happy/invalid/denied/cross-tenant, expiry/replay, stale auth, rollback
and concurrency checks; completion affected account/MFA/session/email/support suites,
system/schema and any intentional isolated migration, then targeted desktop/mobile
UI recovery flows and RU/KK/EN, build/types/i18n/bundle. No live mail, working migration
or full-project E2E implied. Preparation docs require diff/link/consistency checks;
runtime tests have not run and implementation acceptance is not claimed.
Owner accepted the proposed procedure: support email accessible without login,
manual comparison with previously verified records for owners; employee confirmation
by the current owner in their account, plus account-holder identity verification
where other businesses are linked. Public identifiers alone never suffice; absent
evidence or discrepancies block recovery. Both platform roles may execute with MFA.
Do not collect identity-document copies by default. Record verification outcome and
reference/basis, not document contents. Contact email remains environment-configured;
no address was supplied and no fictional address will be shown.

Implementation contract: immutable, expiring support-linked recovery request;
owner confirmation when applicable; explicit operator verification attestation;
one-time new-mailbox link, claimant-chosen password, atomic session/MFA credential
revocation, mandatory MFA re-enrollment on next login, audit and preserved User ID,
Business ownership and memberships. Existing social links are old login credentials:
clear them at completion, shown in the user-facing consequences. No API exposes
link/token/password/factor. Delivery acceptance is not mailbox delivery proof.
Real SMTP/contact configuration and working migrations remain outside this task.
First implementation: AccountRecovery/model migration accounts0011, scoped platform
and owner-confirmation APIs, public one-time completion, safe transport status and
retry, retained account identity/memberships, atomic credential revocation/audit.
Focused gate `.venv/Scripts/python.exe output/admin03-focused.py`:28 tests PASS
(recovery + existing email change), isolated SQLite migration/system check PASS.
Only after this pass added platform panel, personal confirmation and public page.
Initial frontend build failed i18n ordering (fallback must precede translated keys);
fixed dictionary placement. `npm --prefix frontend run build` retry PASS including
i18n/types/app/widget; `npm --prefix frontend run check:bundle` PASS. Logs:
output/admin03-focused.log, admin03-build.log, admin03-build-retry.log, admin03-bundle.log.
Expanded isolated PostgreSQL gate running via output/admin03-completion.py;
one selected label apps.support.tests is absent (actual labels tests_domain/tests_api),
so that missing boundary must be run separately; passing unchanged labels need not repeat.
Browser runner scripts/verify_platform_recovery.py uses only disposable data and
scripts.recovery_test_mail synthetic outbox, guarded to the isolated temp DB.
Next: finish PG/dependent checks, real desktop/mobile browser gate, review and publish.

PG result:156 labels reported,155 actual tests PASS and1 loader error for the absent
apps.support.tests module; no product failure. Correct support modules then31 PASS
via output/admin03-support.py. End-to-end review found platform case creation always
used business owner, making a locked-out employee's new case unreachable. Extended
existing service with optional platform-only active same-business requester_id,
bound it into idempotency payload, kept actual operator author and default behavior.
Focused/dependent support32 PASS via output/admin03-support-requester.py; system/schema
PASS. UI reuses SupportCreateDialog with the selected immutable requester from the
recovery panel. Browser test now creates this actual case before the recovery request.
Subsequent recovery lock refinement serializes both owner/target accounts and
platform authority; affected recovery suite will rerun in PostgreSQL via
output/admin03-locks.py, including a consent-vs-owner-epoch race. Broader unchanged
account tests retain their above evidence. Temporary PG clusters stopped cleanly.

Final scoped verification16.10: recovery27 PostgreSQL PASS (including3 concurrency
tests) via `.venv/Scripts/python.exe output/admin03-locks.py`; system/schema PASS.
Support32 final tests PASS; unchanged broader account/access/session suites retain
the155-test run evidence above (26 older recovery cases replaced by the27 final cases).
This gives188 distinct backend tests across final/reused evidence, not a full suite.
`scripts/verify_platform_recovery.py`:4 desktop/mobile flows PASS, log
output/platform-recovery/browser-1792138337908625600.log. The browser server loaded
the lock refinement before starting. Actual case creation -> owner confirmation ->
synthetic mailbox -> new password -> login and final readback, invalid MFA/draft,
503/403, empty, RU/KK/EN and keyboard/contact/overflow checks passed. Inspected
RU desktop completed panel and KK mobile request screenshots. Temporary servers
terminated; no browser/provider behavior is claimed for a working environment.
Final `npm --prefix frontend run build` PASS (6273 locale keys, types, app/widget),
`npm --prefix frontend run check:bundle` PASS; output/admin03-build-final.log and
admin03-bundle-final.log. No dependency installation or working migrations/seeds.
Manual identity verification remains an operator judgment requiring prior verified
evidence; code enforces required recorded basis/consent and cannot authenticate
document contents. No AI/BusinessEvent mutation; external mail only after separately
configured working activation. Existing requester-less support creation unchanged.

Reviewed owned files/new files and credential patterns with output/admin03-review.py;
diff/link checks PASS, final staged/committed checks follow. Branch/root unchanged.
`git fetch origin main` FETCH_HEAD and direct ls-remote both cafcea5b2b2143077072fbefd3330b7b8839c1f2;
local origin/main is stale because configured fetch refspecs omit main. Do not use
that stale tracking ref to infer outgoing foreign commits. CI workflow contains
checks/tests/audits, no deployment. Next: explicit-path commit, static gate against
cafcea5, normal HEAD:main push and remote SHA/actual CI. Receipt in task response;
no new phase and no follow-up documentation-commit loop required.

Pre-publication snapshot: unrelated concurrent documentation appeared in
docs/current/acceptance.md, docs/documentation-index.json,
docs/testing/business-logic-questions-20261016.md and a separate docs/README.md row.
Preserve those working changes; stage only this task's README specification row
and explicit ADMIN03 paths. No source/runtime overlap observed; no coordination
or additional product task is implied.

The index briefly held that other task's changes; staging guard stopped before
any mutation. It then cleared after docs-only1c8ffa544ab577bd935bdb1ad017bfc8ea99d522
was committed and published by that task (direct remote SHA matched). Compared
cafcea5..1c8ffa5: only those six documentation files; tested runtime inputs unchanged.
Current reviewed commit base is therefore1c8ffa5; use it for the ADMIN03 committed
static gate and fast-forward publication. Shared-file unrelated text is preserved.

## PLATFORM-ADMIN-02-20261016 — implementation

Owner approved the proposed ordinary ownership transfer and requested implementation.
Annotation excludes transfer without the previous owner's participation; assisted
support recovery is a separate future scope, not an override implemented here.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
clean starting HEAD7f7d0c931778180e2cf59ba996c6d3889d1827d3. Prior publication
and CI38795672431 confirmed success. No unrelated dirty files at start.
Mode implementation; gap code. Reuse Business.owner, BusinessMember/BusinessRole,
SupportCase, platform/merchant identity checks, MFA, session revocation, audit,
platform business card and personal account. Add a bounded persisted transfer
request with immutable terms and explicit consent by both authenticated parties.
Only platform_admin executes with recent MFA, same-Business case and reason;
platform_manager reads/prepares the support case but cannot execute the transfer.
One active request per business; cancellation/expiry, stale revision, replay,
disabled participant and changed membership must never silently transfer ownership.
Preserve historical authorship, specialist state, assignments and other memberships.
No new permission framework, provider calls, payment/ADMIN03/ADMIN04 or recovery.
API/UI must show old/new owner, prior access outcome, consent state and audit result.
Both parties' pre-transfer credentials will be revoked through existing auth epoch
mechanism; global user identity/role remains unchanged. New owner login then follows
existing privileged MFA rules. In-app consent is reachable from personal account;
no email/SMS/provider delivery introduced. No BusinessEvent/AI mutation introduced.
Migration: intentional request model only, generated/tested in isolated DB; no
working/demo/staging/production migrations or seeds authorized by this task.
Owner clarified: explicitly select an existing employee profile or disable only
this business access. The selected outcome is immutable and shown to both parties.
Risk: privilege retention, stale consent, cross-tenant transfer and concurrent writes.
Focused backend tests before dependent UI: admin/manager/foreign denial, consent,
MFA, invalid input, role/owner consistency, revoked sessions, audit rollback/retry,
PostgreSQL concurrent single-winner and concurrent owner membership repair.
Completion: affected account/team/platform/permissions suites, system/schema and
isolated migration; real desktop/mobile operator -> owner -> recipient -> operator
flow, denied/error/empty/stale/recovery states; RU/KK/EN and keyboard; frontend
build/types/i18n/bundle once. Full project E2E/live deployment not part of this scope.
Preserve checks as evidence, review exact owned range, normal push under standing
authorization and inspect CI. No new task/phase after ADMIN02 completion.

Implementation checkpoint16.10: request model/migration0012, strict platform and
personal-account APIs, two consents, scoped previous-owner role/disable choice,
MFA execution, revision/epoch checks, atomic audit and session revocation implemented.
Existing profile repair and both membership write APIs now share the Business lock;
owner deletion/deactivation and stale serializer overwrite are rejected.
First isolated PostgreSQL run15 failed (5 failures/3 errors): existing session
revocation FOR UPDATE included nullable blacklist JOIN, plus two new fixture errors.
Fixed token lock to of=("self",), corrected RefreshToken fixture/source field.
Retry15 PASS, then expanded30 PASS with team/deactivation dependencies; system and
migration drift PASS. Logs output/admin02-focused.log, admin02-focused-retry.log,
admin02-member-checks.log; commands are matching .py helpers through .venv Python.
Later role-lock refinement passed all3 PostgreSQL concurrency tests through
output/admin02-role-concurrency.py: role changes invalidate consent, one execution
wins, and profile repair cannot restore the former owner. System/schema PASS;
disposable PostgreSQL stopped successfully. Local Windows memory load reached98%
(8GB RAM, roughly0.5GB free), with unrelated shell reads also delayed. Browser run
output/platform-ownership/browser-1792096415078106000.log failed initial load/timeout
and stalled teardown; it was stopped using its verified owned process tree only.
This is NOT UI acceptance. Repeat browser sequentially after PostgreSQL completion.
Sequential rerun started via scripts/verify_platform_ownership.py; evidence is
output/platform-ownership/browser-1792098068984475800.log. Corrected combobox
locators to include the shared Select's selected-value accessible-name suffix.
Platform/account UI and RU/KK/EN copy are implemented; build, final dependent gates,
browser screenshots, documentation closure, commit/push/CI remain outstanding.
Working/demo databases have not been migrated; existing demo was not modified.

Owner resumed ADMIN02 after the completion audit16.10; scope remains unchanged.
Sequential browser rerun ended before scenarios with webServer startup timeout120s;
all isolated migrations had passed. It is not UI PASS. The earlier build stopped
without a completion result after i18n; no build process survived the interruption.
HEAD remains7f7d0c9 and all listed ADMIN02 changes remain uncommitted. Resumed
build log: output/admin02-build-resume.log. Continue serially: finish build, diagnose
isolated server startup, verify the four browser scenarios, run affected/dependent
backend labels via output/admin02-completion.py, then close docs and publish/CI.
Do not rerun unchanged passing concurrency checks or expand to other ADMIN phases.

Resume results: npm run build PASS (i18n6230 keys, TypeScript, app/widget Vite),
npm run check:bundle PASS; logs output/admin02-build-resume.log and
output/admin02-bundle.log. No dependency/config changes or installation.
Startup diagnostic: direct installed Playwright CLI --version completed in0.3s;
npx incurred delay. The task browser helper now uses the installed CLI directly
and logs server startup via pw:webserver, without increasing acceptance timeouts.
Run output/platform-ownership/browser-1792131850189933600.log reached all4 tests:
desktop/mobile recovery,503/403, manager read-only, decline, RU/KK/EN, keyboard and
overflow checks PASS2. Both completion tests failed only at exact getByLabel lookup
of the filled textarea; snapshots retain the correct value and accessible textbox.
Replaced that lookup with getByRole('textbox', name=reason), preserving assertion.
Only completion scenarios rerun via scripts/verify_platform_ownership.py --grep
"ownership complete"; log browser-1792132046834654100.log. Previous screenshots
preserved in output/admin02-browser-attempt3; representative RU mobile, KK desktop
and EN mobile inspected. No demonstrated product regression from these failures.

Completion browser rerun PASS2 (desktop36.2s/mobile38.9s), both consent accounts,
MFA error/retry and retained draft, explicit transfer, owner readback and both old
sessions redirected to login. Together with the unchanged state scenarios this
covers4 targeted flows; completed desktop and participant mobile screenshots also
inspected. Temporary servers terminated by the runner. Final isolated PostgreSQL
suite154 is running via output/admin02-completion.py (system/schema already PASS):
apps.businesses.tests_ownership.OwnershipTests, tests_access, tests_settings_team,
tests_member_deactivation; apps.accounts.tests, tests_mfa, tests_session_policy,
tests_device_sessions, tests_email_changes; apps.core.tests_platform_details and
tests_mixed_membership_scope. Unchanged concurrency3 PASS reused separately.

Final local acceptance16.10: PostgreSQL154 PASS in200.011s, system/schema PASS;
the temporary database/cluster stopped successfully. All runtime inputs remained
unchanged after the above build and browser passes. Commands: `.venv/Scripts/python.exe
output/admin02-completion.py`, `output/admin02-role-concurrency.py`,
`scripts/verify_platform_ownership.py` and its `--grep "ownership complete"` rerun;
from frontend, `npm run build` and `npm run check:bundle`. Logs are named above.
Scope is these affected/dependent suites and4 browser flows, not full-project E2E
or deployed acceptance. No dependencies installed, provider effects, working DB
migrations or seeds. Migration0012 was applied only to disposable PG/SQLite DBs.
Owned change set29 files reviewed, including12 new files; whitespace/diff hygiene
and8 added relative links PASS via output/admin02-review.py. No foreign WIP or
staged changes. Root/branch remain canonical; current remote main readback7f7d0c9
matches the task base. CI workflow has checks/tests/audits only, no deploy job.
Next: explicit-path commit, committed-range static gate against7f7d0c9, normal
HEAD:main push, remote SHA readback and actual CI. Final commit/push/CI receipt
will be reported in the task response; no follow-up documentation commit loop.
No next ADMIN phase is authorized by completion of this one.

## ALL-CHANGES-PUBLICATION-20261016

Owner explicitly requested "сделай пуш всех изменений и ci". Operation/evidence
scope: publish the accumulated reviewed history and inspect actual GitHub CI;
no additional product phase or working database changes. Canonical root
C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit, clean HEAD
f7d74d5b906dc9239c0486d53d4934f633a99d73. Authorization includes the previously
blocked6e1bd46/834656b commits. Reviewed outgoing paths and workflow; only CI,
no deployment step in .github/workflows/ci.yml. Reused prior scoped runtime
evidence; `.venv/Scripts/python.exe scripts/codex_verify.py --mode static
--base-ref origin/main` PASS against local tracking c7e26f6 (diff/system/schema).
Remote fetch configuration does not automatically update origin/main; therefore
publication readback uses `git ls-remote origin refs/heads/main` directly.
`git push origin HEAD:main` succeeded normally (remote6e1bd46 -> f7d74d5);
readback exactly f7d74d5b906dc9239c0486d53d4934f633a99d73. CI run
https://github.com/999MAX20/PlatformaCRM/actions/runs/38795538634 is in progress
at this record. This receipt is a docs-only follow-up; final CI outcome is
reported in the task response after checking the final published SHA.
No untracked WIP, source rewrite, force push, migration, seed or deployment.

## CONNECTION-RECOVERY-20261015 — implementation

Owner requested fixing persistent connection notices after read-only analysis.
Mode implementation; gap code/evidence; canonical root PlatformaCRM, branch
codex/ui-testing-toolkit, starting HEAD e24d52dc6a630a1f167cc78f812ff5b4d98fcafb.
Pre-existing ADMIN-01 WIP (backend/platform UI, i18n, contracts/status/checkpoint)
is unrelated and preserved. Only append task evidence to shared records.
Reuse ConnectivityStatus, public readiness API, AuthProvider and existing browser
fixtures. Scope: recovery after hidden/offline state, public probe independent
of auth, successful service retry resumes pending session recovery. Preserve
drafts, identity checks, Retry-After and explicit-only business mutations.
No backend/permission/tenant/BusinessEvent/AI/migration/provider changes.
Risk: shared authentication recovery; do not hide errors before actual success.
Checks: regression before fix, targeted connectivity/session browser suites in
isolated_runtime with disposable DB/ports, frontend build/types/i18n/bundle,
diff hygiene. No full-project gate or working DB writes. Commit only owned hunks;
publication requires review of existing outgoing history, never other writers' WIP.

Implementation: readiness uses a public axios client without auth interceptors;
successful recovery probe signals AuthProvider to attempt session recovery.
Auth recovery repeats its timer and listens to visibilitychange, respecting
Retry-After, visibility/online state and existing single-flight/identity guards.
Existing business mutations are never replayed. UI copy/layout unchanged.
Before-fix regression: `.venv/Scripts/python.exe scripts/verify_connection_recovery.py`
failed all4 desktop/mobile checks on expected notice dismissal (not setup).
Log output/connection-recovery/browser-1792090622310699100.log. Both missing
behaviors reproduced: hidden startup retry and successful upper retry leaving
session error. This does not establish the historical screenshot's exact cause.
`npm --prefix frontend run build` PASS (i18n6206, tsc, app/widget build);
`npm --prefix frontend run check:bundle` PASS. Logs output/connection-recovery/
build.log and bundle.log. Error/action-feedback Node tests9 PASS, policy.log.
Targeted browser completion: `.venv/Scripts/python.exe scripts/verify_connection_recovery.py
e2e/connection-recovery.spec.ts e2e/session-persistence.spec.ts e2e/state-behavior.spec.ts`
PASS27;11 mobile session-suite duplicates skipped by its existing desktop-only
guard. Log browser-1792090778383703400.log. New regressions4 PASS desktop/mobile;
session503/429/offline, expired token, logout, multiple tabs, draft preservation,
failed/retried probe and keyboard feedback expiration covered. No full-project/
release gate claimed; no backend code or working DB changed by this task.
Fetch origin/main confirms8 pre-existing outgoing commits6e1bd46..e24d52d;
normal push would include unrelated work. Preserve this publication blocker.
Public probe `.venv/Scripts/python.exe scripts/verify_connection_recovery.py
e2e/connection-probe.spec.ts`:2 PASS desktop/mobile, no Authorization header and
successful public response across a concurrent session-generation change.
Log browser-1792090946031338700.log. Total browser29 PASS;11 intentional skips.
Owned test servers exit with the runners; existing dev servers untouched.
Ready for owned-path local commit; committed-range static gate follows it against
e24d52dc6a630a1f167cc78f812ff5b4d98fcafb, with outcome in the task response.
Push/CI not run due to the pre-existing outgoing-history publication blocker.

## PLATFORM-ADMIN-01-20261015 — implementation

Continuation16.10 owner «продолжай»: resolve the reproduced invitation PostgreSQL
blocker and finish ADMIN-01 verification. Starting HEAD834656b on the same branch
and canonical root; intervening CONNECTION-RECOVERY commit and its records are
preserved. Existing23-path ADMIN-01 dirty snapshot is task-owned; no conflict.
Minimal fix: lock invitation row itself, excluding nullable role/team JOIN rows.
Preserve authentication, same-Business membership, single-use token and audit;
no policy, schema, delivery, AI or BusinessEvent changes. Risk: concurrent accept.
Focused gate: previous8 failures + explicit PostgreSQL single-winner/rollback
regressions. Completion: original expanded backend labels plus new regressions,
system/schema; rerun4 ADMIN-01 browser flows because shared auth recovery changed.
Reuse unchanged frontend build/type/i18n evidence from834656b working snapshot;
no install/full-E2E/working-DB changes. Review owned commit and outgoing history;
«продолжай» does not authorize publishing other writers' existing commits.

Continuation evidence: invitation SELECT now uses select_for_update(of=("self",));
optional joins stay available, token consumption remains serialized. PostgreSQL
focused10 PASS (previous8 failing acceptance cases + concurrent single-winner and
audit-failure rollback/retry), system/schema PASS. Command
`.venv/Scripts/python.exe output/admin01-invitations-focused.py`, log
output/admin01-invitations-focused-20261016.log. No application code changed after
this fix. Browser command `.venv/Scripts/python.exe scripts/verify_platform_details.py`
PASS4 desktop/mobile on current shared auth; log browser-1792092221625169700.log.
Completion82 backend suite is running through output/admin01-completion-20261016.py.
Fresh fetch still contains prior unrelated6e1bd46 and834656b; preserve push boundary.

Continuation completion16.10: `.venv/Scripts/python.exe output/admin01-completion-20261016.py`
PASS82 PostgreSQL tests, system check and migration drift PASS. Labels:
apps.core.tests_platform_details, apps.core.tests_platform_crm,
apps.core.tests_platform_s02, apps.businesses.tests_settings_team,
apps.businesses.tests_access, apps.businesses.tests_invitation_concurrency.
Log output/admin01-completion-20261016.log. This supersedes the previous failed
expanded gate for this fixed snapshot; original failure/baseline evidence below
is retained. PostgreSQL single-use/rollback and existing permission/identity/
foreign-business invitation scenarios passed without weakening expectations.
All4 browser flows PASS on current shared auth; unchanged frontend build/types/
i18n/bundle PASS reused from CONNECTION-RECOVERY834656b working snapshot (included
the same ADMIN-01 frontend WIP), logs output/connection-recovery/build.log/bundle.log.
No dependencies/config/frontend changed during this continuation. Full E2E,
working DB migrations and deployment skipped as out of scope. Owned test servers
and PostgreSQL clusters stopped; existing demo not changed this continuation.
25 intended paths reviewed,13 added relative links resolve; working/new-file diff
hygiene PASS. Local acceptance complete. Commit only this task's diff against
834656b; committed-range static gate follows. No push/new CI: outgoing range still
includes unrelated6e1bd46 and834656b. Their inclusion needs an explicit publication
scope decision; no rewrite/cherry-pick/new worktree to bypass it. ADMIN-02 not started.

Owner's next «приступай» authorizes ADMIN-01 implementation after stage0.
Mode implementation; gap code. Canonical root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, clean starting HEAD e24d52d. Reuse Business,
platform role checks, MFA, SupportCase, audit and existing business card/API.
Result: both platform roles correct only approved details with recent MFA,
case/reason, atomic audit and stale-revision rejection. Merchant self-service
remains available. No owner/subscription/status changes, migrations, working DB,
notifications, BusinessEvent, AI, providers or other ADMIN phases.
Risk: privileged write, stale role/token, cross-business case, lost updates.
Focused checks before UI: explicit fields/validation, both roles and denials,
MFA, business scope, merchant conflict, audit rollback/replay. Completion:
affected backend/dependent tests, isolated system/schema, frontend build/types,
i18n/bundle and targeted desktop/mobile locale/keyboard/error/recovery flow.
No full-project gate without demonstrated cross-cutting risk. Commit reviewed
task paths after checks; normal push only if prior outgoing6e1bd46 blocker is
resolved. No deployment claims. No agents or alternate source tree.

Implemented bounded platform_details service/serializers/view/route; explicit
allowlist, fresh DB identity/epoch, case Business, revision of fields+updated_at,
row lock, field-only save and atomic sanitized audit. Merchant perform_update
refreshes instance under same lock so a previously loaded serializer preserves
unrelated corrected fields. Existing history adds correction metadata/case link.
UI details tab uses shared form components, API layer, MFA, draft guard, explicit
reload after conflict; RU/KK/EN. No migration or ordinary DB writes.
Focused SQLite first failed on fixture duplicate blank emails; fixed emails.
Second run exposed test expectations (MFA401, expanded no-store header); fixed.
PostgreSQL focused10 PASS, system/migration drift PASS via
`.venv/Scripts/python.exe output/admin01-postgres.py`; log admin01-postgres.log.
Completion PostgreSQL79 executed:71 PASS,8 FAIL in invitation acceptance due to
FOR UPDATE nullable JOIN. Invocation: output/admin01-postgres-completion.py;
labels core.tests_platform_details/core.tests_platform_crm/core.tests_platform_s02,
businesses.tests_settings_team/businesses.tests_access. Real two-writer test PASS.
No invitation code was changed. Baseline rerun loads e24d52d business view methods
in memory (no source copy/reset); initial command duplicated test method names,
thus8 loader errors, not baseline proof. Corrected baseline run pending.
Browser `scripts/verify_platform_details.py`:2 locale/load/403 flows PASS;2 save
flows initially FAIL (MFA generic session error and enrollment polling race).
Added specific MFA feedback; fixture stops app polling before epoch rotation.
Replaced mocked409 with actual second correction; fixed conflict envelope to
DomainAPIException/category=conflict. Scoped rerun `--grep 'details save'`:2 PASS,
real MFA/save/clear/persistence/draft guard/conflict/reload/history on desktop/mobile.
Logs output/platform-details/browser-1792081627966120100.log and
browser-1792081958166392900.log. Build/types/i18n/bundle initial PASS; after history
and MFA changes final build and focused PostgreSQL details+CRM rerun pending.
Publication remains blocked until required checks/outgoing range are resolved.

Final local evidence:
- `.venv/Scripts/python.exe output/admin01-final-focused.py`:24 PostgreSQL tests
  PASS (core.tests_platform_details + core.tests_platform_crm, including actual
  concurrent writes and correction history), system check and migration drift PASS.
  Log output/admin01-final-focused.log. No app code changed after this snapshot.
- Corrected `.venv/Scripts/python.exe output/admin01-baseline.py`:same8 invitation
  FAIL with e24d52d BusinessViewSet.perform_update and BusinessInvitationViewSet.accept
  loaded from Git into memory, with current unchanged invitation tests. PostgreSQL
  rejects FOR UPDATE on nullable JOIN. Log admin01-baseline-invitations-retry.log.
  This proves that path's baseline failure, not a full checkout certification.
  Expanded79-test gate remains failed; do not mark it green or fix invitations
  implicitly within ADMIN-01. Owned temporary PG clusters were stopped/removed.
- `npm --prefix frontend run build` PASS after final UI/MFA/history changes
  (check:i18n, tsc, app/widget build); output/admin01-build-final.log.
  `npm --prefix frontend run check:bundle` PASS; largest locale478.1kB, shell329.9kB.
- `scripts/verify_platform_details.py --grep 'details save'`:2 PASS; followed by
  `--grep 'details load'`:2 PASS, log browser-1792082289134655100.log. Four final
  distinct desktop/mobile flows cover real save/MFA/409/history plus load503/403,
  recovery, RU/KK/EN, focus/keyboard and viewport overflow. Screenshots visually
  inspected (RU desktop/mobile, KK desktop, EN mobile). Disposable databases/ports;
  providers remain isolated. No full-project E2E or release/live certification.
- Existing owned demo supervisor2732/backend15548/frontend18424 restarted from
  canonical root via existing stand.py (no --seed, no migration). Same synthetic
  output/platform-admin-demo-20261015/db.sqlite3, loopback5185/API8015, safe profile.
  Both platform-role details GET and frontend HTTP200 PASS. Demo stays running;
  verification processes have ended. Main working db.sqlite3 untouched.
- Fresh fetch origin/main: previous outgoing6e1bd46 remains. HEAD e24d52d unchanged,
  branch codex/ui-testing-toolkit. Required expanded gate failed, so no staging,
  new commit, push, deployment or new CI. User-facing local implementation is
  present; complete acceptance/publication is blocked. Next step is a separately
  authorized resolution of invitation baseline/publication blockers, not ADMIN-02.
  Working diff/new-file hygiene and added local documentation links checked.

## PLATFORM-ADMIN-01-CONTRACT-20261015 — stage0

User said proceed with the proposed plan. Under AGENTS one-phase rule, active
scope is stage0: inspect existing layers and establish ADMIN-01 action contract.
Starting canonical root C:/Users/user/Desktop/PlatformaCRM, branch
codex/ui-testing-toolkit, clean HEAD49e46a273eb0dea2a2770e712f180a12175d6f36.
Applied zani-change-crm-domain and zani-run-verification; read references.
No agents, source copies, runtime mutation, migrations or external operations.
Checks for this contract phase: inspected source/field references, consistency,
links and working/index/committed-range diff hygiene; no app gates for docs only.
Future backend/UI acceptance is specified in spec15.8, not claimed as tested.
Pending owner question via async: ADMIN-01 roles and grant policy. Proposed both
platform roles + recent MFA + business support case, without owner grant; other
choices admin-only or grant required. Existing access contract leaves these
write rights unresolved, so dependent implementation has not begun. Phase0 map
and proposed bounded API can be completed independently; do not infer an answer.
Owner replied asking for a recommendation and whether primary company data
should become support-only. Recommendation sent: display name/contacts remain
self-service; legal_name/tax_id editable until explicit owner confirmation, then
support-only on an owner request, both platform roles + MFA/audit without grant.
Second async question pending to choose that policy vs lock after first fill vs
retain current self-service. No choice received yet; do not mark recommendation
approved. This would add merchant API/UI constraints and an explicit fixation
state; migration impact must be assessed after the decision. Current work is
three documentation files only, uncommitted; source/runtime/data unchanged.

Owner explicitly agreed only to the annotated support permission proposal:
both admin/operator may correct details with recent MFA and audit, no temporary
owner grant; preserve reason, actor and history. Recorded in spec15.8/access.
Do not treat this as acceptance of merchant legal-field locking/confirmation.
Stage0 source map and bounded proposed API complete; next result ADMIN-01
implementation. No backend/UI changes or application checks in this phase.
Final scope is four docs paths including access; links/diff reviewed before
commit. Publication still requires rechecking the outgoing other-writer commit.
Completion: 13 new local references resolve; four intended documentation paths,
working diff hygiene PASS. Fresh fetch still shows6e1bd46 in outgoing range;
push blocked under AGENTS, no CI/deployment. Index and committed-range hygiene
checked for the task commit; app tests skipped because runtime is unchanged.


## PLATFORM-ADMIN-CAPABILITIES-20261015 — technical specification

Follow-up: owner requested explicit documentation of the inspector discussion and
an implementation plan. Docs-only continuation from clean HEAD4bf0c30 on the same
canonical root/branch. Scope: spec15.7, ordered plan in the existing roadmap,
status and this checkpoint. No implementation or live actions. Risk/checks:
avoid duplicate backlog and invented permissions; inspect complete four-file diff,
links, working/index/committed-range hygiene; skip app/DB/browser gates as docs-only.
Completed plan and spec clarification in four intended files; added-link check
PASS, full patch reviewed, working diff hygiene PASS. Fresh fetch still includes
other-writer6e1bd46 in outgoing range: no push, CI or deployment. Documentation
commit uses index/range hygiene checks; runtime code and working data unchanged.

Owner requested persistence of the coverage analysis and direct administrative
remediation requirements, after checking for an existing technical document.
Mode documentation; gap product/policy specification. Reuse registered
`docs/testing/platform-rebuild-spec-20261014.md`, add section15 rather than a
competing document. Scope: coverage, business/personnel/owner recovery, email,
confirmed subscription payment reconciliation, permission decision boundaries;
update contract pointers, index, roadmap and status. No implementation, live data,
new permissions, provider actions, deployment or agents.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD f3601712642be357127f8f7905c68fc9a273c61d; clean index/tree.
Risk: proposed powers mistaken for implemented permissions or paid entitlement
restoration mistaken for a new charge. Clearly separate approved product intent,
proposed mechanisms and open policy. Focused/completion checks: complete intended
diff, relative links, registry consistency, working/index/committed-range hygiene.
Docs only: no app installs, builds, tests, DB or browser suites. Standing normal
push applies only if outgoing range contains no unapproved other-writer work;
previous blocker is outgoing 6e1bd46 and must be rechecked before publication.

Owner then requested analysis first; only this task record had been edited.
After analysis owner explicitly approved all five scenarios and requested the
documentation update plus an explanation of database inspection/update for Paid
without activation. Section15 now records approved scope, coverage, scenario
acceptance, proposed read + explicit actions inspector and payment recovery test.
Product/access/roadmap pointers and docs index entry are consistent; no new file
or runtime behavior. Exact role matrix and payment evidence/period policy remain
open; mere Paid metadata is not treated as verified funds.
Verification: git diff --check PASS; PowerShell added-link existence/registry
check PASS (all seven intended docs paths). Initial link-check attempt via python
could not run because PATH resolves to Windows Store alias; replaced with native
PowerShell, no install. Full intended patch reviewed, no secrets/new files.
Index and actual committed-range hygiene are completion checks for this patch.
No application suites/build/DB/browser needed for documentation-only scope.
Fresh git fetch origin main: outgoing range still includes other-writer 6e1bd46
before this task's prior commits. Normal push remains blocked by AGENTS section6;
no history rewrite or publication of that work. No task CI/deployment triggered.


## PLATFORM-REFERENCE-REDESIGN-20261015 — analysis and implementation

Owner explicitly requested detailed analysis of the six generated references,
then implementation of the page redesign based on it. One authorized result covers
all six screens; no new approval between analysis and implementation. Canonical root
C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit, clean starting
HEAD/index/tree 5d5586e00db5dc655c1e0c4093ccd0a9f32c41a2. No agents or other checkouts.
Mode implementation, frontend composition/interaction gap. Reference artifacts:
output/platform-page-references-20261015/{01-overview,02-businesses,03-business-crm,
04-support-queue,05-support-case,06-operations}.png; prompts.json records sources.

### Structural analysis before implementation

Shared hierarchy is shell → compact toolbar → worklist → selected-record context.
Keep existing Manrope, semantic neutral/emerald tokens, 64px rail/57px header,
12px cards/10px controls, thin borders and restrained status colors. No global
token/component redesign. Lists should occupy the first viewport; timestamps and
metadata are secondary, not separate tall cards. Preserve text/icon status meaning,
long localized strings, accessible names/focus, mobile reflow and keyboard operation.

1. Overview: five linked metrics in one strip, two compact attention/support queues,
   operational signal row, disclosure sections for usage/finance. Retain all actual
   metrics, MRR definition, unavailable-source and fresh/unknown distinctions;
   generation's arbitrary assignees/business associations are not data requirements.
2. Businesses: one toolbar, shorter rows and clear business-status vs service-state
   columns. Subscription/usage details remain discoverable within the row; do not
   silently remove fields to imitate the picture. Search/pagination/return context
   stay server-backed and URL-persistent; no new create-business/repair capability.
3. Business CRM: single compact identity summary, existing tabs, kind/search/filter
   toolbar, desktop list/detail split and mobile detail with return. All nine entity
   types, children, relations, archive and pagination remain. No invented related
   counts; no mutation buttons. Reject duplicate business title and generator text.
4. Support queue: creation with filters, explicit assignee quick selection, compact
   rows/unread indicator. Retain business picker, status/unread/unavailable filters,
   server pagination, no priority/SLA inventions or unsupported filtering.
5. Support case: main thread and side context/actions/history/incident links.
   Public reply/internal note selected explicitly with separate retained drafts;
   never mix private note content into public thread. Existing action dialogs keep
   validation, transition reasons, permissions and draft guard. Reference dropdowns
   do not authorize direct mutation or bypass confirmation. Internal conversation
   can use its own selected tab instead of duplicating note content in both columns.
6. Operations: compact existing tabs/filters and readable state/date/action table.
   Current episodes and historical failures remain distinct. API has no connector
   name/error explanation: render supplied provider/kind/ID, not invented diagnostic
   copy. Keep counts, freshness, linked cases and support/business transitions;
   no platform retry/reconnect or backend projection expansion in this redesign.

Risk: draft loss/leakage on tab changes; master/detail URL/focus or denial regressions;
hidden fields after compaction; overflow in locales/mobile. Reuse existing API clients,
queries, Tabs, Card, inputs, pagination and domain dialogs; no backend/schema/roles,
grant/MFA, AI, BusinessEvents, notification or provider behavior changes. Merchant
support is a shared consumer: scope new composition to platform where applicable.

Checks: focused existing platform overview/CRM/operations/support browser runners
on isolated DB/ports, adding only meaningful master-detail and draft-mode regression
assertions; desktop/mobile and RU/KK/EN/error/empty/403 flows. Inspect real screenshots
against references and keyboard interactions. Completion build/types/i18n + bundle,
working/index/real committed-range diff hygiene and changed docs/links. No dependency
install, full-project E2E, working DB migration or provider calls. Existing local demo
may be used for read-only visual inspection after verifying roots/ports.
Standing commit/push applies only to permitted history; previous unrelated outgoing
6e1bd46 remains a publication blocker until fresh Git evidence changes that boundary.

### Implementation and verification (15 October)

All six page compositions are implemented. Overview queues and business rows are
compact; usage/finance/secondary metadata use native disclosures. CRM retains the
list next to record details at wide desktop sizes and uses a return flow on mobile.
Public/internal support tabs retain separate mounted drafts; actions still use the
existing reason/version dialogs. Operations uses the existing scoped worklists.
No backend, schema, roles, notifications, BusinessEvents or AI changes.

A direct CRM URL on the local SQLite demo exposed concurrent audited list/detail
reads returning 503. The frontend now starts detail after the list request settles;
mandatory backend audit remains unchanged. Added direct reload regression coverage.

- Final `npm --prefix frontend run build`: PASS (types, i18n, app and widget);
  `output/platform-page-references-20261015/redesign-build-final.log`.
- `npm --prefix frontend run check:bundle`: PASS (largest 477.7 kB; shell 329.9 kB).
- `.venv/Scripts/python.exe scripts/verify_platform_overview.py --spec
  e2e/platform-overview.spec.ts --grep 'operator overview'`: 6 PASS;
  `output/platform-overview/browser-1792071183731646500.log`.
- `.venv/Scripts/python.exe scripts/verify_platform_overview.py --clinic-crm --spec
  e2e/platform-clinic-crm.spec.ts --grep 'clinic CRM'`: 10 PASS, desktop/mobile,
  all kinds, direct reload, related records, permission/recovery, RU/KK/EN;
  `output/platform-clinic-crm/browser-1792071724317698600.log`.
- Earlier combined overview+CRM run: 12 PASS / 4 FAIL. CRM fixture changes overview
  counts and long combined execution expires freshness. Separate runners with their
  own intended fixtures passed; assertions were not relaxed. Original evidence:
  `output/platform-clinic-crm/browser-1792070601454213300.log` and
  `output/platform-reference-redesign/attempt1/test-results`.
- Build attempt 1 caught i18n fallback key order; fixed before the final PASS.
- Screenshots retained under `output/platform-reference-redesign/{overview-pass,crm-pass}`.
  Local demo visual inspection: compact business/support tables, CRM desktop split
  and mobile record. Support screenshots also cover RU/KK/EN and keyboard tabs.
- `.venv/Scripts/python.exe scripts/verify_platform_support.py`: 8 PASS,
  `output/platform-support/browser-1792072093953461900.log`. Separate drafts survive
  switching and leave/cancel; private notes remain private; unseen public messages
  remain unread while the internal tab is selected. Merchant support, stale version,
  recovery/denial, incident links and locales passed. The final source/test changes
  were saved before the browser worker started; screenshots include the added
  incoming-message fixture. Artifacts: `output/platform-reference-redesign/support-pass`.
- Operations first run: 2 PASS / 4 FAIL;
  `output/platform-operations/browser-1792072359509893100.log` and
  `output/platform-reference-redesign/operations-attempt1/test-results`.
  The navigation test expected access history on the default state tab; `git show`
  of the starting HEAD proves that history was already hidden outside Access.
  Updated the test to open Access and follow the exact preserved return URL.
  Provider assertions now use the existing localized Telegram label (the first
  worker had loaded the old lowercase assertion before this test correction).
  Recovery, filters and permission-loss checks passed unchanged. Only the four
  affected navigation/provider scenarios reran with fresh isolated fixtures: 4 PASS,
  `output/platform-operations/browser-1792072552194344500.log`, command
  `.venv/Scripts/python.exe scripts/verify_platform_operations.py --grep
  'operator worklists paginate|operator worklists separate'`. Together with the
  unchanged recovery/permission scenarios this proves all six operations scenarios.
  Screenshots: `output/platform-reference-redesign/operations-pass`.
- Total final applicable browser boundary: 30 distinct scenarios PASS (6 overview,
  10 CRM, 8 support/incident, 6 operations), desktop/mobile and RU/KK/EN. Inspected
  final CRM, overview, support and operations screenshots and live business queue.
- No dependency installs, full E2E, backend test suites, working-DB migrations or
  external provider calls: this is a frontend change. Required committed-range
  static/system/migration-drift checks follow the local implementation commit.
- Fresh fetch still shows unrelated `6e1bd46` before this task's history; normal push
  remains blocked by ownership boundary. No history rewritten or unrelated work staged.

Implementation and required frontend checks complete. Entire intended diff reviewed:
20 explicit task-owned paths, no untracked source or unrelated WIP, no new secrets.
Implementation committed as `b4ee81a` on `codex/ui-testing-toolkit`.
`.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
5d5586e00db5dc655c1e0c4093ccd0a9f32c41a2`: PASS on that commit, including working,
index and actual committed-range diff hygiene, isolated migration drift (no changes)
and Django system check (no issues). No app changes after this evidence.

Local demo Vite exited with Windows EBUSY while watching a generated Playwright
report asset. After tests, verified both dedicated ports were free and restarted
only this stand via its existing `stand.py`, hidden, same canonical source and
persistent synthetic DB; no seed/reset/migrations. Restart logs and current process
IDs are under `output/platform-admin-demo-20261015`. Ordinary ports were untouched.

Push not attempted: fresh origin/main fetch still leaves `6e1bd46` (other writer)
before this task's commits. Existing owner rules prohibit publishing that work.
No CI was triggered for this local implementation; no deployment claimed.
Next is only owner resolution of that publication boundary; all requested six-screen
analysis/implementation and applicable local verification are complete.


## PLATFORM-DIAGNOSTICS-01-20261015 — consistent diagnostic reads

Owner said «приступай» after platform analysis and ordered recommendations.
Bounded first phase: consistent connector error/attention classification across
overview, merchant list/detail, operations queue and infrastructure preview;
complete local demo scenarios for history, stale observations and recovery.
Code/evidence gap, implementation mode. Canonical root, codex/ui-testing-toolkit,
base d8f825bc54d0fbe07d106121582020b8b4b6f9ca; starting tree/index clean.
Existing closed read model is reopened only for reproduced ERROR connector omission:
business3 connector status=error while operations connector queue and error count=0.
Preserve established needs_attention=setup (not failure) contract and disabled/
disconnected/draft non-failure behavior. Reuse existing model/selector/worklist,
safe_environment and persistent isolated demo. No provider calls, credentials,
retry writes, permissions, BusinessEvents, AI, notifications or schema changes.
No redesign in this phase; next recommended phase is compact page composition.
Risk: shared counts/queue inconsistency or changing normal setup into an outage.
Focused checks: regression for all connector statuses, same-business filtering,
cross-surface totals, recovery, secrets and platform roles. Completion: affected
read suites/dependents, isolated system/migration drift, demo API/browser evidence,
diff hygiene and publication only of permitted outgoing history. Rendering the
new ERROR row also requires its existing failed-status wording in RU/KK/EN; run
frontend build/types/i18n once at completion. No full E2E or working-DB migrations.

### Result and verification

Shared platform_connector_status constants now include ERROR in failures and
attention; needs_attention remains setup-only. Overview, business list/detail,
operations queue and infrastructure reuse that classification. ERROR uses existing
failed-status copy in all three locales. Regression covers every model status,
both platform roles, business filtering, hidden provider secrets and recovery.

Checks executed with .venv/Scripts/python.exe, scripts.codex_verify.isolated_runtime,
disposable SQLite and safe environment (ordinary working DB untouched by these tests):
- `manage.py test apps.core.tests_platform_worklists apps.core.tests_platform_rebuild -v 1`:
  27 PASS; output/platform-diagnostics-01/focused.log.
- `manage.py check` and `manage.py makemigrations --check --dry-run`: PASS.
- `manage.py test apps.core.tests_platform_operations apps.core.tests_platform_overview apps.core.tests_platform_s02 apps.core.tests_service_status apps.support.tests_incidents -v 1`:
  50 PASS, 1 existing has_select_for_update skip on SQLite (collector lock test);
  output/platform-diagnostics-01/dependent.log. No concurrency code changed.
- `npm.cmd --prefix frontend run build`: PASS (i18n, types, Vite and widget);
  output/platform-diagnostics-01/build.log. No reinstall or broad E2E gate required.

scripts/platform_diagnostics_fixture.py guards the exact isolated demo SQLite path
and prepared marker, creates no jobs/provider calls, and was executed twice with
stable IDs. Business3: ERROR/FAILED/EXPIRED_CREDENTIALS plus setup in the attention
queue, disabled excluded; failed and successful integration/webhook/automation
history records. Added business16 stale export observation/case20 and business17
recovered export/case21. Existing manual records retained. Supervisor now excludes
the intentional stale fixture from synthetic timestamp refresh. Only own demo
processes restarted: supervisor10924, backend launcher16524, frontend12304.

Live local API checks for admin and manager: queue4 = failures3 + setup1, consistent
overview/detail/infrastructure; each failed history source count1; stale status
unknown with current episode, recovered healthy with no current attention episode.
Evidence: output/platform-diagnostics-01/api.json. Browser checked translated ERROR
row, filtered history, stale and recovered episode pages with linked cases.
These are synthetic observations, not real provider or production readiness.
No schema migration, permission, notification, BusinessEvent or AI behavior changes.

Entire intended diff/new files reviewed; working/index/committed-range hygiene is
the completion gate. Fetch origin/main still leaves pre-existing unrelated 6e1bd46
before own demo docs d8f825b; normal push would also publish that other writer's work.
Keep local commit, do not push this range or rewrite history. No new CI run claimed.
Next recommended phase: compact page composition; not started in this phase.

## PLATFORM-ADMIN-DEMO-20261015 — local manual preview

Owner requested a running local test stand for the platform admin interface,
populated business data and admin/operator functionality. Environment/data task;
no product changes or deployment. Canonical root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, starting HEAD 6e1bd465a12a1d81e66631461105ca3999890ea9,
clean starting index/worktree. Reuse codex_verify.safe_environment and existing
smoke/overview/CRM fixtures in an ignored persistent output directory. Separate
SQLite, media, loopback ports 8015/5185; preserve ordinary DB and existing servers.
Synthetic data only; inert providers, mock AI, local email; no permission bypass.
Risk: wrong DB/environment or misleading fixture health. Check explicit DB path,
process source roots, login and reachable UI/API for both platform roles; label
synthetic service observations. Completion: live URLs/accounts and restart helper,
docs diff hygiene, normal publication of task evidence. No full application gate
for environment-only work; no dependency installation or production migration.

Local result: frontend http://127.0.0.1:5185, backend 127.0.0.1:8015,
both loopback-only. Persistent ignored output/platform-admin-demo-20261015 contains
stand.py, start.ps1, enrich.py, operations.py, verify.py, README.txt, db.sqlite3,
logs and process/verification JSON. Source roots are canonical; development Vite,
Django --noreload, isolated media and safe_environment, mock AI/local email,
disabled external providers. Supervisor PID16732; backend launcher11112/runtime15844,
frontend15956. Existing 8000/5173 processes were not stopped/reconfigured.
Synthetic component observations refreshed every60s only in demo DB; three businesses
intentionally lack observations. This is fixture health, not live-service readiness.

Seed15 businesses/30 clients/19 cases, all support statuses, three unassigned cases,
active/trial/inactive/blocked businesses. Main rich business id15, ДЕМО — Альфа Сервис:
24 active clients plus archive, linked lead/deal/task/appointment/payment/conversation,
23 messages, notes/custom field/tag/activity, connector/channel and audit trail.
Additional failed connector/sync/event/export fixtures in business3 for Operations.
All demo accounts use the existing smoke password documented only in local README.
Platform administrator and platform manager roles remain unchanged; no grants or MFA
bypass added. Persistent data survives server restart; start.ps1 does not reseed.

Validation: stand.py --seed migrated only the explicit demo DB; initial Windows
shell stdin execution was interactive and produced IndentationError despite exit0.
Preserved incomplete DB as partial-seed.sqlite3, reran clean explicit shell -c seed
with business/client/case/role assertions: PASS. operations.py execution PASS.
verify.py: HTTP login + nine populated CRM list kinds + support list for both roles
PASS (verification.json). Browser: admin overview,24-client list,scoped support,
internal-note save; operator login/overview and case19 transition to in_progress
with visible actor/reason history verified. Fixture observations visible
as9 degraded/3 healthy/3 unknown. Startup navigation timed out during Vite dependency
optimization; subsequent page loaded normally. No dependencies installed.
Ordinary db.sqlite3 is used by pre-existing servers and its hash changed during
this interval, so no claim of global byte stability: read-only comparison confirms
none of the three stand-specific business slugs there versus all3 in demo DB.
No commands in this task targeted ordinary DB for migration/seed/write.
Full regression/build skipped: no application source/config/lockfile changes.
Documentation diff hygiene PASS; no new tracked links/files. Publication boundary:
fetch origin/main returned c7e26f6 while the starting HEAD6e1bd46 is another task's
unpublished receipt commit. Do not publish that unrelated outgoing commit from this
task; keep this task's evidence committed locally. No new push/CI for this local stand.

## CRM-NEUTRAL-TERMS-20261015 — industry-neutral interface

Owner request in PlatformaCRM UI: after the PlatformaCRM admin-panel implementation
finishes, replace clinic/patient/doctor and analogous industry-specific system copy,
then establish a rule that the common CRM interface is industry-neutral.
Prerequisite confirmed: PLATFORM-CLINIC-CRM completed/published aed452f, receipt
ee653a3; source task idle. Canonical C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, base ee653a3b4abcf18c7a1b244caeebb4e4d419b685;
starting index/working tree clean. Implementation + policy gap.

Scope: RU/KK/EN system copy including new platform CRM tabs, support/errors,
resource presets and default customer-AI role/template; authoritative frontend,
product/AI rules and AGENTS wording consistent with multi-industry CRM.
Reuse existing i18n, components, API error handling, AI profile creation and test
runners. Preserve stored customer data, explicit industry choices/templates,
API identifiers/enums and permission/lifecycle/approval/safety rules. No schema,
working DB changes, external calls, notification or BusinessEvent changes.
Risks: translated grammar, label overflow, saved-profile compatibility, accidental
loss of AI safety/confirmation clauses. Focused checks: translation inventory,
new-profile/template behavior and unchanged stored-profile loading, affected backend
error tests in isolated runtime. Completion: build/types/i18n, representative
platform/support/resources/AI UI in RU/KK/EN desktop/mobile and keyboard states,
system/schema checks for backend text edits, diff hygiene, reviewed normal push
and actual CI status. No full E2E, provider or deployed acceptance claim.
Implementation completed: 153 translated values (RU52/KK50/EN51), including the
new Business work tab, platform/support labels and errors, equipment/work-area
presets and neutral AI default role. API keys/enums and stored profiles/data stay
unchanged. Four backend error messages and the default legacy specialist role
name are neutral; role creation does not rewrite an existing stored name.
AGENTS and active product/frontend/AI contracts now require industry-neutral UI.
The existing build's check:i18n rejects known industry entity names in generic
translated values, with explicit industry-choice exceptions and safety preserved.

Verification15.10 (canonical source; existing dependencies; disposable SQLite,
isolated loopback browser servers via scripts.codex_verify.isolated_runtime):
- Installed `.venv/Scripts/python.exe` using the documented isolated focused
  helper: `manage.py test apps.core.tests_platform_crm apps.support.tests_api
  apps.support.tests_domain -v 1`:43 PASS; `manage.py check` and
  `manage.py makemigrations --check --dry-run`:PASS; output/neutral-terms/backend.log.
- After the role-name edit, same isolated helper:
  `manage.py test apps.businesses.tests_access.CanonicalBusinessRoleTests
  apps.businesses.tests_role_visibility -v 1`:10 PASS, output/neutral-terms/roles.log.
  Includes explicit preservation of an owner-saved industry role name. No model
  or migration inputs changed after the recorded system/schema checks.
- `npm --prefix frontend run test:terminology`:4 PASS. Rejects RU/KK/EN inflections,
  preserves technical keys, explicit industry choices and medical/legal safety.
- `npm --prefix frontend run build`:PASS (i18n6197 keys, types, Vite/widget),
  output/neutral-terms/build.log. `npm --prefix frontend run check:bundle`:PASS,
  largest477.5kB and shell329.9kB. Placeholder parity of all153 changed values PASS.
- `.venv/Scripts/python.exe scripts/verify_platform_overview.py --clinic-crm
  --spec e2e/platform-clinic-crm.spec.ts e2e/neutral-terminology.spec.ts
  e2e/ai-agents-ux.spec.ts e2e/ai-agent-scenarios.spec.ts
  --grep "clinic CRM locales|neutral resource|visible profile|customer creation"`:
  8 PASS desktop/mobile. Log output/platform-clinic-crm/browser-1792057000584706000.log.
  New profile + resource defaults RU/KK/EN, explicit template apply/cancel,
  saved-profile preservation, keyboard modal focus and platform tabs/no overflow.
- `.venv/Scripts/python.exe scripts/verify_platform_overview.py
  --spec e2e/platform-overview.spec.ts --grep "operator overview bounded queues"`:
  2 PASS desktop/mobile, overview/business/incident/support navigation RU/KK/EN.
  Log output/platform-overview/browser-1792057250427938200.log.
- Visual review: RU desktop AI, KK mobile equipment dialog, EN mobile Business
  work and RU desktop overview. Changed labels fit; explicit fixture data named
  Clinic/Patient remain unchanged as required. First-run screenshots copied to
  output/neutral-terms before the second browser run replaced test-results.
- Working diff hygiene PASS; reviewed changed/new files contain only task work.
  Full E2E, live providers/deployment and working DB checks skipped as outside this
  copy/default-template scope. No installs, schema/data migrations or external sends.
  gh CLI unavailable; GitHub public Actions API is available for actual CI readback.
  Fetch uses an explicit main tracking ref because the configured remote fetch
  refspec omits main; origin/main confirmed equal to base before publication.
Publication15.10: code c7e26f612b7c7bb69754c03d813ecf64472d5faa committed on
codex/ui-testing-toolkit and normal-pushed to origin/main; remote SHA readback
matches. `.venv/Scripts/python.exe scripts/codex_verify.py --mode static
--base-ref ee653a3b4abcf18c7a1b244caeebb4e4d419b685`:PASS, including isolated
system/schema and committed-range hygiene. GitHub Actions38715135513 in_progress
at receipt time; not claimed green. Prior base CI38712007561 completed success.
Automation crm-2 paused after completion to prevent repeated implementation.

## PLATFORM-CLINIC-CRM-20261015 — unified clinic and permanent CRM read access

Owner: «приступай» after Overview; spec13.5 step3 and approved permanent read
decision15.10. Implementation/code+UX gap. Canonical C:/Users/user/Desktop/PlatformaCRM,
codex/ui-testing-toolkit; basefa8a041214ff2bb38edbc75c89f5f2880d71bc47, clean tree/index.
Newer shell commits495f429/5b476b7/fa8a041 inspected and preserved; same root/branch.
Result: clinic sections state, CRM work, connections, support, access/history;
real searchable bounded lists/details for clients/leads/deals/tasks/appointments/
Inbox and CRM payment records, related navigation within visible selected clinic.
Inbox message bodies read without marking read/sending; no impersonation/merchant
API expansion. Explicit allowlisted fields, no provider credentials/raw JSON.
Reuse platform auth, existing models/selectors, scoped support, shared tabs/list/
pagination/fields and new shell header. Recheck active platform role per read;
Business-bound lookup before relations/detail; metadata-only view audit, no content
or search text. Keep support-note grant/MFA and support lifecycle unchanged.
No new write/export/file-download permission, collector behavior, AI/event/
notification effects, schema or working DB migration. Existing detailed CRM
permission is already owner-approved; no new business-policy decision required.
Risks: cross-Business relation disclosure, stale role/cache, unaudited private reads,
unbounded bodies/queries, lost return/draft state and accidental mutation.
Backend slices: access+lists/details then child records/diagnostics; focused isolated
tests after each coherent slice. Prove allowed/denied/inactive/role-loss, foreign
Business/entity/relation, safe projections/audit failure, pagination/query budget,
read-only/no side effects and unavailable-source recovery. Completion affected and
dependent PostgreSQL suites, system/migration drift; reachable desktop/mobile
RU/KK/EN keyboard/navigation/error/empty/403 flows, build/types/i18n/bundle.
No full-project/live gate. Explicit owned diff review and verified normal push
origin/main, remote SHA and actual CI. Next spec step4 remains separate.

Implementation checkpoint: separate GET-only clinic list/detail/child/access-log APIs
are in place. Collections cover clients/leads/deals/tasks/appointments/Inbox/payment
journal and connector/channel configuration status. Child records include messages,
comments, custom fields, notes, tags and activity. Explicit projections omit provider
secrets, raw JSON and payloads; client/relation/member links are Business checked.
Audit failure returns503 without data. UI has five clinic tabs and bounded lists,
URL filters, details/relations, child paging, clinic-scoped support and read history.
Source is locally verified; publication receipt follows below.

Checks so far (canonical source, disposable isolated_runtime, unchanged dependencies):
- SQLite first service slice8 PASS; child slice12 PASS; timezone/detail dependent
  recheck26 PASS (tests_platform_crm + tests_platform_rebuild), logs under
  output/platform-clinic-crm/{focused,children,timezone-focused}.log.
- PostgreSQL17 isolated system/migration drift PASS. First command selected
  tests_platform_crm/overview/worklists/operations/s02/rebuild/service_status and
  support.tests_incidents:88 actual tests PASS, plus one loader ERROR caused by
  nonexistent apps.support.tests. This command remains FAILED; log postgres.log.
  Corrected missing selection only (no rerun of unchanged green cases):
  apps.support.tests_api/tests_domain/tests_concurrency35 PASS,
  postgres-support.log; disposable clusters shut down/removed.
- Frontend build/types/i18n PASS after correcting new kk/en entry placement after
  ...ru. Later UI changes still require completion build. New bool/status copy
  review and browser checks remain pending.
- Browser runner is existing scripts/verify_platform_overview.py --clinic-crm with
  isolated extra fixture scripts/platform_clinic_fixture.py. Initial fixture failed
  payment_single_link because it set both deal and appointment; corrected fixture
  uses deal only. No ordinary DB touched. First browser run now in progress;
  found test selector mismatch: shared labelled Select includes its selected value
  in accessible name; corrected test helper, no shared-component rewrite.

Completion15.10: 123 actual PostgreSQL test cases PASS across the88+35 selections
above; the initial loader failure is retained as failed-command evidence, not
relabelled green. Backend inputs have not changed since those checks. No schema
change, ordinary DB migration, seed/reset, provider calls or collector startup.

PostgreSQL test commands inside isolated_runtime with temporary PG17 cluster:
`manage.py test apps.core.tests_platform_crm apps.support.tests apps.core.tests_platform_overview apps.core.tests_platform_worklists apps.core.tests_platform_operations apps.core.tests_platform_s02 apps.core.tests_platform_rebuild apps.core.tests_service_status apps.support.tests_incidents -v 2`
(first command has the recorded loader error); then
`manage.py test apps.support.tests_api apps.support.tests_domain apps.support.tests_concurrency -v 2`
PASS. Both used `.venv/Scripts/python.exe output/platform-clinic-crm/verify_postgres.py`,
`manage.py check` and `manage.py makemigrations --check --dry-run` in disposable DB.

Frontend exact commands from canonical root:
- `npm --prefix frontend run build` PASS on final UI, build-final.log;
  types/Vite/widget and6197 i18n keys; `npm --prefix frontend run check:bundle`
  PASS, largest477.7kB / shell329.9kB. No dependency install or lock changes.
- `.venv/Scripts/python.exe scripts/verify_platform_overview.py --clinic-crm --spec e2e/platform-clinic-crm.spec.ts --grep "clinic CRM"`:
  first browser run5 PASS/5 failed (browser-1792054689786813800.log): four test
  Select-name mismatches, one test strict-locator collision after the desktop
  support case was created. Corrected selectors/seed-row lookup and90s flow timeout.
- Same runner/spec, `--grep "clinic CRM (search|manager|support|locales)"`:
  8 PASS desktop/mobile, browser-1792055047032690700.log.
- Review found 403 needed to hide clinic summary as well as requested CRM data.
  Added shared denial callback to clinic boundary; list/detail/children/access
  denial unmounts clinic title, metadata and bodies. `--grep "clinic CRM transient"`:
  2 PASS desktop/mobile after fix, browser-1792055299094615100.log. Covers503
  retained data/search+retry, child403 and list403 hiding whole clinic,404 recovery.
- `.venv/Scripts/python.exe scripts/verify_platform_overview.py --clinic-crm --spec e2e/platform-clinic-crm.spec.ts e2e/platform-overview.spec.ts --grep "clinic CRM manager|operator overview preserves"`:
  4 PASS, browser-1792055534435360000.log. Manager all9 record kinds, unread count
  unchanged, no credential text, connections/access, plus dependent Overview
  partial/empty/503/retry/403 regression. Total12 distinct browser cases verified
  (10 new clinic +2 dependent Overview); repeated manager checks not double counted.

Browser evidence: real isolated API data for paging24/10, archive/search/empty,
client→task→client, fields/notes/tags/activity/comments, message paging23/20,
payment/connection details, scoped support creation/back/draft cancellation,
manager read-only, RU/KK/EN keyboard tabs and no horizontal overflow. Screenshot
review covered RU desktop list/conversation and KK mobile list/RU mobile payment;
artifacts retained under output/platform-clinic-crm/. All task-owned runtimes exited.
No full-project E2E/release/live gate: this is scoped read/UI work. No new exports,
impersonation, AI/event/notification or CRM mutations. Existing support writes
continue through their unchanged services/permissions. Updated current access,
frontend/operations, roadmap, spec delta and capabilities; next spec13.5 step4
remains unstarted. Base fa8a041 CI38705753503 independently confirmed SUCCESS.
Review: all29 intended paths (10 new) task-owned; local links218 PASS, registered
doc roles unchanged, diff hygiene PASS. No private/customer data or secrets in
intended diff; fixtures contain synthetic example.com identities only.

Publication receipt: code commit aed452f12eb7991ac82a7211a403b77a60eb2635,
canonical root/branch unchanged. `.venv/Scripts/python.exe scripts/codex_verify.py
--mode static --base-ref fa8a041214ff2bb38edbc75c89f5f2880d71bc47` PASS on the
actual committed range: working/index/range hygiene, isolated migration drift
and Django system checks. Fetched main remained ancestor; normal `git push origin
HEAD:main` succeeded and remote SHA read back exactly aed452f12eb7991ac82a7211a403b77a60eb2635.
Actual push CI38711917194 is IN_PROGRESS (not green). Publication verified;
no task-owned running processes or unfinished implementation. Next phase is
spec13.5 step4 only on a new user instruction. This receipt is docs-only and
reuses unchanged application PASS; no deployment/working-DB acceptance claimed.

## PLATFORM-SHELL-20261015 — implementation

Owner: «приступай», approved section14 shell reference. Implementation/code gap.
Canonical root C:/Users/user/Desktop/PlatformaCRM; codex/ui-testing-toolkit;
base495f429ee81ee17910fabfb99f4979b84a19e1ee, clean index/tree at start.
Result: overlay64/224 sidebar, single route-aware57px header, consistent insets,
account menu and platform self-account without Business dependencies. Reuse menu,
account/security APIs and shared controls; preserve merchant support/account.
Scope excludes domain/API/permission changes, migrations, working DB and new pages
other than self-account. No notification/BusinessEvent/AI or provider effects.
Risks: stale entity titles, lost actions, keyboard/focus, accidental tenant reads.
Focused checks: isolated browser routes/back/forward, states/403, menu and hover,
RU/KK/EN desktop/mobile, self-account save/failure/draft/language/logout and
representative merchant account/support plus shared ActionMenu consumers.
Completion: isolated frontend build/types/i18n/bundle, diff/links/private-data
review, real committed-range static, normal origin/main push and CI readback.
No full E2E/backend suite unless a changed contract demonstrates the need.

Implemented: four-item platform navigation reserves64px and overlays224px on
hover/keyboard focus;57px header owns one route title. Entity metadata comes from
accessible loaded content, keyed by pathname and cleared on unmount/denial.
Root page titles removed, actions/back links retained. Profile menu uses shared
ActionMenu; account route reuses self profile/security/language with merchant
access/start-page/notifications excluded. RU/KK/EN labels, long-title truncation,
mobile navigation and hash section navigation retained. No API/schema changes.
Shared menu fixes: outside blank-space click restores trigger focus after native
pointer focus; Escape stops bubbling so it cannot close a parent task inspector.
Visual review found Account's width token previously supplied only by AppLayout;
PlatformLayout now supplies the equivalent width, keeping the section rail visible.

Verification uses existing dependencies and disposable isolated_runtime DB/ports,
locmem/eager/provider-safe environment, canonical source. Exact browser entrypoint:
`.venv/Scripts/python.exe scripts/verify_platform_overview.py` with these selections:
- `--spec e2e/platform-shell.spec.ts e2e/platform-overview.spec.ts e2e/account-user-settings.spec.ts e2e/account-interface.spec.ts --grep "platform shell|operator overview|personal language saves|start page persists"`:
  11 PASS/7 failed, log output/platform-overview/browser-1792051135764100200.log.
  Four merchant-account regressions and five overview cases PASS. Test defects:
  locale loop waited on the preceding route, manager fixture absent, attempted
  focus refetch despite disabled focus polling;180s fixture freshness expired.
- `--spec e2e/platform-shell.spec.ts e2e/platform-overview.spec.ts --grep "platform shell|operator overview bounded"`:
  4 PASS/6 failed, browser-1792051546225492100.log. Both bounded overview cases
  PASS, completing overview coverage. Corrected test hover target under overlay,
  normalized503 assertion and explicit task fixture; diagnosed menu focus loss.
- `--spec e2e/platform-shell.spec.ts --grep "platform shell"`:
  7 PASS/1 failed, browser-1792051929701485500.log. Both self-account cases and
  both metadata/denial cases PASS. Desktop task-inspector Escape bubbling reproduced
  and fixed in shared menu; inspected account screenshots and corrected width token.
- `--spec e2e/platform-shell.spec.ts --grep "platform shell route|platform shell bounds"`:
  4 PASS, browser-1792052269967603500.log, both viewports, including default task
  menu and merchant support/route denial. No assertions or product freshness weakened.

- `--spec e2e/platform-shell.spec.ts --grep "platform shell self account"`:
  2 PASS, browser-1792052521655195900.log, after width correction. Desktop/mobile
  screenshots reviewed: section navigation fully visible, no overlap/clipping.

Final scoped coverage:18 distinct browser cases PASS across the above runs:
8 shell/self-account,6 overview and4 merchant-account regression cases. Unchanged
coverage reused; affected menu/account checks rerun after fixes. Initial build
stopped at two misplaced locale keys, corrected before acceptance. Isolated
`npm run test:gate-env`:1 PASS; final `npm run build` and `npm run check:bundle`
PASS after all product fixes, output/platform-shell/build-accepted.log;
types/i18n6005/production/widget, app shell329.9KiB under400KiB, all chunks under500KiB.
Desktop operations, mobileKK overview and corrected account screenshots reviewed.
Working diff hygiene and three added local doc-link targets PASS; no unrelated
changes or real credentials in the reviewed diff. Prior docs CI38698958050 SUCCESS.
No dependency install, full E2E/backend suite, working DB migration, live provider,
screen-reader certification or changes to retained dev processes were performed.

Publication: implementation5b476b7544bcec0040a44a97219b9b27b5c4c0f2 normal-pushed
to origin/main; ls-remote SHA matched. `.venv/Scripts/python.exe scripts/codex_verify.py
--mode static --base-ref 495f429ee81ee17910fabfb99f4979b84a19e1ee` PASS on the real
committed range: working/index/range hygiene, isolated migration drift/system check.
All24 staged files reviewed, including both new sources; no unrelated WIP remained.
CI38705646141 in_progress at readback, not green. This receipt is docs only;
application evidence unchanged. All owned verification commands/runtimes exited;
retained user dev processes unchanged. Scope complete; no next product phase started.

## PLATFORM-SHELL-20261015 — reference and change contract

User requested current /platform screenshot, sidebar/header reference and a
contract for later implementation, not product edits. Canonical root and branch
codex/ui-testing-toolkit retained. Initial HEAD c713b86 plus unrelated Overview
WIP; read-only inspection preserved it. That work independently committed through
0c9666e/b41d8da before these documentation edits; owned diff is only this record,
STATUS and section14 of the existing registered platform-rebuild spec.
Mode design/docs; gap proposed shell behavior and consistent page geometry.
Reuse /app64/224 overlay rail, tokens/menu primitives, personal account APIs;
no merchant navigation/Business scope in platform self-account. Main risks:
duplicate/stale headers, moved controls, inaccessible profile route and unintended
Business reads. Current checks: docs diff/links/consistency and local mock behavior;
future implementation checks are specified in section14, not claimed here.

Captured actual Chrome /platform at1536x639 in RU; screenshot and inline reference
stored in the task visualization output outside Git. Page-heading tops measured
Overview/Support92.4px vs Clinics/Operations82.4px, shell header62.4px. No UI writes,
account changes, data mutations, migration, external call or app test performed.
Reference preview checks PASS: hover64->224->64 with constant main-left64.8px,
header57px, one changing h1 on navigation, profile menu and Escape focus return;
1024 desktop and390 narrow no horizontal overflow. Browser viewport restored.
Mock rows are a small copied dev sample, not live results or a body redesign.
Personal notifications excluded because existing preferences require Business;
/platform/account is a future route, existing /app/account redirects platform users.
Preview CLI first rejected destination+--serve; corrected invocation succeeded.
No app build/install/backend suites: only documentation and an external mock changed.
Own preview server/tab closed, port5186 no longer listening; user's dev servers
and original platform tab retained. Full intended diff/private-data and reference
review PASS; working diff hygiene and reference JavaScript syntax PASS.
Publish only the reviewed documentation delta; actual CI readback is separate.

## PLATFORM-OVERVIEW-20261015 — actionable operator overview

Owner: «отлично, продолжаем», next spec13.5 step2. Implementation/code+UX gap.
Canonical C:/Users/user/Desktop/PlatformaCRM; codex/ui-testing-toolkit;
base c713b86e886e30e02a829fab7baed42a25ba4cd4, clean starting index/tree.
Result: bounded clinic/support attention previews with responsible users, exact
distinct clinic service counts and matching server-side merchant service filter,
active/unassigned/waiting-clinic case counts with matching support links. Keep
finance and real activity; label period, snapshot and partial sources. Refresh,
transient failure recovery, no-data/empty/403, desktop/mobile/keyboard/RU-KK-EN.
Reuse overview API, service-state definitions, scoped support selectors and shared
UI/tokens; no new permissions, writes, events, notifications, AI or migrations.
No detailed CRM read-path or new observations in this phase. Working DB untouched.
Risks: count/list mismatch, duplicate clinics, stale observations treated as fresh,
source failure becoming zero, unsafe case content and role-loss stale data.
Focused backend slice first: shared clinic classification/filter + overview queue
summary; happy/invalid/denied, dedup, missing sources/recovery, query budget and
agreement with destination lists. Completion: dependent platform/service/support
tests, isolated system/migration checks; targeted browser navigation/state flows,
build/types/i18n/bundle. No full-project/live gate. Review explicit owned diff,
commit, static real range, normal origin/main push, remote SHA and actual CI.
Prior Operations CI38694788872 still in_progress at start; not claimed green.

Implemented shared distinct-clinic service classification for overview and new
merchant `service=degraded|unknown|healthy|attention` filter. Bounded preview6:
fresh degraded clinics first, then unknown; component observation/start timestamps,
exact-episode support link counts with separate missing-link fallback. Support:
active/unassigned/waiting-clinic counts and six latest active cases with assignee
availability; reuse existing permissions/status definitions, no message/note bodies.
First isolated SQLite slice8 PASS (output/platform-overview/focused.log). Added
component/link coverage then affected PostgreSQL suite76 PASS via temporary
output/platform-overview/verify_postgres.py, log postgres.log; includes overview,
worklists, operations, S02, rebuild, service status, support incidents. Isolated
system/migration drift PASS; temporary PG stopped/removed. No backend changes since.
UI includes matching KPI links, queue previews, exact return context from clinic/
incident/case, server service filter, 30s polling and transient error retention;
403 hides overview. Existing finance/activity and recorded signal data preserved.
Build/types/i18n6003/bundle PASS, output/platform-overview/build.log.
`.venv/Scripts/python.exe scripts/verify_platform_overview.py`: 8 PASS (1.4m),
log output/platform-overview/browser-1792048385089682700.log. Includes six overview
desktop/mobile cases and two unchanged operator service-S03 regression cases.
Metric-to-list agreement, combined filter/return, clinic/incident/case return,
RU/KK/EN keyboard/no-overflow, retained data on503/recovery, missing source vs
zero/empty, role-loss403 covered. DesktopRU/mobileKK full-page captures inspected;
no clipping or unrelated layout change. Own isolated runtime exited cleanly.
Prior CI38694788872 backend/frontend SUCCESS now confirmed. Reviewed26 explicit
task-owned paths, six new files, no unrelated work or real secrets. Document
links185 and working/index diff hygiene PASS. Commit
0c9666e38ec652c03ceab671324fd6c41ab42840 normal-pushed to origin/main; remote SHA
matched, clean tree. `.venv/Scripts/python.exe scripts/codex_verify.py --mode static
--base-ref c713b86e886e30e02a829fab7baed42a25ba4cd4` PASS: real committed range,
isolated migration/system and diff checks. CI38697901995 in_progress at receipt;
not claimed green. This receipt changes docs only, application evidence unchanged.
Next result is unified clinic + detailed CRM read-path, not started. Working DB,
collector and other processes unchanged; support0002 activation remains separate.

## PLATFORM-OPERATIONS-20261015 — operator worklists

Owner said proceed after incident linking and console analysis. Current bounded
phase: spec13.5 step1, working Operations; Overview and permanent detailed CRM
read-path remain subsequent results. Mode implementation; gap code/UX/read-model.
Canonical C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit,
base1c6291a1d5b8254845d894209a949762d483531e, clean index/tree. Prior CI38642701572
backend/frontend completed SUCCESS. Reuse observations/incident links, existing
failure/connector models, platform authorization, shared URL filters/pagination/
date picker/tokens and isolated runner. No alternate checkout or delegation.
Result: separate current background episodes, connector attention, dated recorded
failures (automation/integration/webhook), and infrastructure/readiness. Server
filters Business/name, component/freshness or UTC date period; full counts and
bounded stable pagination; clinic/episode/support navigation, refresh/timestamps,
partial/unavailable/error/empty/forbidden and mobile/keyboard/RU-KK-EN states.
Risks: historical failures mistaken for live outage, truncated counts, mixed
Business rows, sensitive payload leaks, missing sources masquerading as zero,
unbounded queries and lost navigation context. New reads only; no lifecycle,
mutation permission, notification, BusinessEvent, AI, migration or working DB
effects. Legacy health CLI readiness semantics preserved separately from live
service state. Existing snapshot coverage remains four background components.
Focused backend tests immediately after read-model/API: >page counts and ordering,
filter combinations/invalid inputs/period bounds, role denial, no sensitive
payload, missing-source recovery, query-budget. Then affected platform/support/
service-status tests and isolated check/migration drift. UI targeted Operations
flows desktop/mobile/locales plus build/types/i18n/bundle; no full local E2E or
deployment. Review explicit diff, static real range, normal origin/main push and
remote SHA/actual CI. Working support0002 activation remains separate.

Implemented read-only operations-worklist API with five safe source projections,
Business/name search, component/freshness and UTC date filters (default30/max366
days), full count and stable pagination. Query cost does not grow per Business.
Incidents include fresh degraded and unknown latest episodes, not fresh recovered
ones; missing support links preserve observations with null linked count. Full
connector count fixed in legacy health; readiness item truncation removed while
legacy health CLI failure semantics remain unchanged. UI now four tabs, shared
date picker, pagination, URL filters, timestamp/polling30s and context return links.

Focused isolated SQLite worklist tests: first FAIL due to duplicate empty emails
in test fixture; fixed unique fixture emails. Retry11 PASS, log
output/platform-operations/focused-retry.log. Affected PostgreSQL17 command:
`manage.py test apps.core.tests_platform_worklists apps.core.tests_platform_operations
apps.core.tests_platform_s02 apps.core.tests_platform_rebuild
apps.core.tests_service_status apps.support.tests_incidents -v2`: 67 PASS;
isolated check and makemigrations --check --dry-run PASS. Temporary PG runner
output/platform-operations/verify_postgres.py, log postgres.log; cluster removed.
Build first found nonexistent platform.nav.support key; reused supportCases.title.
Complete build/types/i18n5990/bundle PASS, including final UI-only build after
adding invalid-page recovery and visible Business filter context (build-final.log).
First browser run: 5PASS/3FAIL. Dated sources/infrastructure and service-state
separation PASS desktop/mobile; recovery/permission PASS mobile. Navigation test
matched two Operations links, corrected to exact context-return href. Desktop
recovery failed at initial page load during browser ERR_NETWORK_IO_SUSPENDED,
confirmed trace (Vite disconnected), not an API assertion failure. Focused retry:
`.venv/Scripts/python.exe scripts/verify_platform_operations.py --grep 'operator worklists paginate|operator worklists preserve'`
4 PASS; log output/platform-operations/browser-1792046511215175900.log.
Combined eight distinct desktop/mobile scenarios PASS, reusing unchanged history/
infrastructure and service-S03 cases from browser-1792046238705349500.log.
RU/KK/EN, keyboard, overflow, filters, return context, 503/recovery, source loss,
invalid-page recovery and 403 covered. Screenshots inspected. Own runtimes exited;
working DB/collector/processes unchanged. No full E2E/live acceptance required.
Next bounded result is Overview, not started. Reviewed 24 explicit task-owned paths
including seven new files; no unrelated changes or real credentials included.
Local document links183 PASS; working/index diff hygiene PASS. Code commit
e464fe81575fb41210df53c5bc222718b1d1a35c normal-pushed to origin/main; remote SHA
matched, clean tree. `scripts/codex_verify.py --mode static --base-ref
1c6291a1d5b8254845d894209a949762d483531e` PASS (real committed range, isolated
migration/system and diff checks). CI38694737037 in_progress at receipt time,
not claimed green. This receipt changes documentation only; application evidence
remains valid. No new migration; prior support0002 working activation still separate.

## PLATFORM-INCIDENT-LINK-20261015 — explicit incident links and console analysis

Owner requested implementation of explicit incident-to-support linking plus a
separate deeper analysis of platform UX/backend, especially overview/operations.
Mode implementation + scoped analysis; gap domain/link UI and product workflow.
Canonical C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
base330e0c11823b4cbef441c436a08634054429a3fa, clean starting tree/index.
Reuse ServiceComponentState episodes, support case domain/access/idempotency,
platform diagnostics, shared components/API/i18n. Current observation is mutable;
links must pin component+episode and a safe immutable snapshot. Never replace an
old incident with the component's latest incident or label stale state healthy.
Outcome: diagnostic -> incident -> existing/new case; case -> pinned incident.
Platform-only diagnostic association, same Business, current-role recheck; clinic
public messages/events unchanged. Metadata audit; no patient text/provider payload,
new CRM access, grant/MFA change, auto-ticket, notification, BusinessEvent or AI.
Migration adds support link storage; isolated only, no working DB operation in
this scope. No full redesign implementation or removal of unrelated code now.
Analysis will amend existing platform spec/roadmap with evidence, operator jobs,
page/content/action requirements, backend gaps, permissions and bounded phases.
Owner clarified internal-data depth: permanent detailed CRM read access to all
clinics for platform operators. Recorded in access/spec section13 for the next
console implementation; linking does not implement this read-path or expand
mutation/export authority. Risk: cross-tenant association, private diagnostic leak,
misleading recovery after recurrence, duplicate creation/linking or lost drafts.
Focused backend gates immediately after domain/API: allowed/denied/cross-tenant,
role loss, replay, invalid/changed episode, rollback, fresh/stale/recovered/newer
observation. Completion dependent support+service-status/platform tests in isolated
runtime, migration/system checks; affected desktop/mobile/browser flows, build,
i18n, bundle and diff/docs gates. Reuse unchanged prior checks; no full local E2E.
Publish task-owned reviewed changes via normal origin/main and inspect actual CI.

Implemented: immutable IncidentLink per case/component/episode with safe snapshot;
explicit platform-only GET/POST, same-Business validation and role recheck,
atomic create+link, idempotent repeated link and metadata audit. No clinic-public
event/text/state change. New page from clinic/operations, reverse case links,
business-bound selector, manual create, current/stale/historical distinction.
Analysis: spec section13 includes page/workflow matrix, exact count/truncation/
freshness gaps, monitoring coverage, query-cost risks and backend acceptance.
Proposed next scope: Operations -> Overview -> unified clinic + detailed CRM view
-> missing observations/authorized actions; full redesign not implemented now.

Checks: isolated SQLite `manage.py test apps.support.tests_incidents -v2`: 9 PASS.
Temporary PostgreSQL17 via `output/platform-incident/verify_postgres.py`:
`manage.py test apps.support apps.core.tests_service_status
apps.core.tests_platform_s02 apps.core.tests_platform_operations -v2`: 77 PASS,
including concurrent link uniqueness/audit and collector concurrency. Isolated
`manage.py check` and `makemigrations --check --dry-run` PASS. Logs in
output/platform-incident; temporary cluster stopped/removed by runner.
`npm --prefix frontend run build`: first type check exposed missing existing
episode/start/recovery fields in PlatformClinicService type; fixed, complete
build/types/RU-KK-EN key parity PASS. `npm --prefix frontend run check:bundle` PASS.
First browser incident run failed because exact combobox test selector excluded
the shared Select's selected-value suffix; selector corrected.
`.venv/Scripts/python.exe scripts/verify_platform_support.py --grep
'support incident|support team creates'`: 4 PASS, desktop/mobile, incident flow
RU/KK/EN with keyboard/no-overflow, 503 preserves selected case then retry, explicit
existing/new link and reverse navigation, ordinary create/stale-version regression.
Visual review of RU desktop/mobile, KK mobile and EN desktop screenshots PASS;
artifacts frontend/test-results/platform-support-incidents-*/incident*.png.
Log output/platform-support/browser-1792014089000010800.log. Disposable browser
runtime exited normally. Local Markdown links checked (204): no missing paths;
working diff hygiene PASS. Product code gates reused after docs/test-only updates.
No backend/product changes after these gates; test fixture/selector only.
Working DB/migrations/servers unchanged; support0002 remains unapplied locally.
Full local project/E2E and production/deployment not run: this is scoped delivery.
Publication: reviewed 32 explicit paths including six new files; no unrelated
work/private data. Commit6bb2e46433d789388510a2dfe9168b45423e38f2,
`codex_verify.py --mode static --base-ref 330e0c11823b4cbef441c436a08634054429a3fa`
PASS. Fetched main/FETCH_HEAD equalled starting base; configured origin/main
tracking ref is stale (main is outside remote fetch refspec), so actual main
verified with ls-remote. Normal `git push origin HEAD:main` PASS; remote exact
SHA readback matched. GitHub CI38642643864 queued at inspection, not green yet.
This docs receipt changes no verified application inputs; docs diff hygiene only.

## PLATFORM-SUPPORT-ACTIVATE-20261015 — local working activation

Owner said continue after the remaining action was explicitly identified as
applying support0001 to the current working DB. Mode operation; environment gap.
Canonical C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
base de02851145568887576173cb9527df07c3fd5c9f; clean starting tree/index.
Target canonical db.sqlite3, existing local backend8000/frontend5173; no staging,
production, onboarding or new feature scope. Reuse passed support backend/browser
checks; do not rerun full suites against working data. Plan: verify runtime roots,
SQLite online backup and integrity, exact single migration plan, apply support0001,
check existing table data/integrity and read-only support API/HTTP availability.
Risk is working schema/data integrity; new migration only creates five tables.
No seed, fake cases, credential/role changes, external sends or worker restart.
CI for implementation is still running at initial inspection; no failed gate.
Completion: runtime cwd verified read-only for backend PID1532 (8000), Vite
PID6888 (5173, frontend) and existing handoff supervisor/worker/beat; all canonical.
Environment local, SQLite canonical db.sqlite3; exact plan support0001 only.
`output/local-support/activate.py` used SQLite online backup, verified integrity
and restored to an in-memory DB with matching table digests before applying
`manage.py migrate support 0001_initial --noinput`. PASS; five new empty tables.
Backup: output/local-support/before-support0001-20261014T210057Z.sqlite3 (local
private working backup, never staged). Report: output/local-support/activation.json.
Working integrity PASS, foreign-key check 0 issues; hashes/counts of all existing
business tables unchanged. Only expected content types/permissions and migration
record added by Django. `manage.py check` PASS; target migration plan now empty.
Read-only APIClient smoke on working DB: platform and clinic lists 200/empty,
clinic-to-platform denial403. No new case/message/account or token persisted.
Actual HTTP: health200, anonymous support APIs401, frontend app/platform support
routes200. This is local API/route activation, not another authenticated browser
suite or production certification; six prior isolated browser passes reused.
Existing handoff runtime left running unchanged. No servers stopped/restarted.
One initial diagnostics attempt lacked optional psutil; used existing native
read-only process-root helper, no installation. CI38636405892 frontend SUCCESS,
backend IN_PROGRESS at completion inspection; no green overall CI claim.
Activation complete; repository receipt is docs-only with diff/link checks.

## PLATFORM-SUPPORT-20261015 — clinic and platform support infrastructure

Owner explicitly skipped manual-business onboarding and requested support implementation.
Canonical C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
base e52db325b961a89dcfcfddc57abdfac75c943eb4; clean worktree/index at start.
Prior CI-B301 correction is published; CI38628077604 backend/frontend SUCCESS,
1696 backend tests OK/10 skipped. No prior failure is carried as a current blocker.
Mode implementation; gap domain/API/reachable UI. Reuse accounts/platform roles,
Business membership, CRM idempotency, audit, shared UI/API/i18n and isolated runners.
Outcome: clinic creates a case; platform queues/assigns/responds/keeps private notes;
clinic reads replies, history and status. Platform can manually create clinic cases.
Owner decisions: employee sees own, owner/admin all cases in own Business; platform
resolves with outcome; author/owner/admin explicitly reopen with reason. Messages
never implicitly change status. First release has no editing/deleting history,
attachments, external notifications, SLA automation, AI, onboarding or new grants.
Permissions: dedicated narrow support domain; no extra access to CRM/patient data.
Platform_admin/platform_manager manage support; active membership scoped clinic
access. Private notes have separate storage/selectors/API and never enter clinic data.
Migrations: new support tables, isolated creation/upgrade only; working DB activation
requires its own target authorization. Notifications: read states/unread in support
UI; no external delivery or general notification fanout. Events/audit: immutable
case history plus sanitized metadata audit, no message/note bodies in global audit.
No BusinessEvent consumer or AI behavior added; no worker/process changes.
Risk: cross-tenant/cross-case access, private-note leakage, replay and lost updates.
Backend iteration gates after coherent domain/API slices: happy path, invalid input,
all roles/role loss, tenant isolation, private-note non-disclosure, idempotency,
rollback, version conflicts, actual PostgreSQL concurrency. Completion: affected
dependent suites, system/migration checks, frontend build/types/i18n, focused real
API browser flows desktop/mobile/keyboard/locales and failure/retry/draft/conflict.
Publish reviewed task-only diff by normal push, inspect actual CI. No full E2E
or dependency reinstall by default. No delegation, cross-task coordination or timers.
Progress: new apps.support models/services/selectors/API; explicit case, public
message, internal note, event and read-cursor tables; migration support0001 generated.
Domain iteration isolated SQLite: 17 PASS (output/platform-support/domain.log).
API+domain iteration isolated SQLite: 31 PASS (output/platform-support/api.log),
including scoped pagination/query bound and private-note non-disclosure.
Mutable case transitions/assignment use versions; immutable message/note appends
use idempotency and row locks, never overwrite or silently transition. Private
notes do not change public updated_at/version/unread. Manual platform cases retain
real author and use the clinic owner as contact; no impersonated owner message.
PostgreSQL isolated gate: `manage.py test apps.support apps.core.tests_platform_s02 -v 2`
41 PASS including three real concurrent assignment/message/read-cursor tests.
Owned temporary PostgreSQL cluster stopped and removed. Log postgres.log; wrapper
reported an output-decoding error after successful test completion, verified from log.
Frontend queue/detail/create/assign/status/public/private forms implemented;
shared DraftGuard extracted unchanged with old TaskDraftGuard compatibility export.
First browser run: both desktop/mobile public/private lifecycle scenarios PASS;
conflict/recovery assertions hit getByLabel ambiguity after textarea value render.
Fixed selectors to role=textbox; no assertion weakened. Added transient detail
refresh failure coverage and retention of loaded list/card and drafts on temporary
errors; permission/not-found/auth failures still hide data. Browser rerun pending.
`npm run build` and `npm run check:bundle` initially PASS after fixing TS unknown
conditional; final rerun after error recovery adjustment pending. 5936 i18n keys.
Isolated `manage.py check` PASS; `makemigrations --check --dry-run` PASS/no drift.
Logs output/platform-support. Working DB/processes untouched; support0001 activation
pending separately authorized target. No dependency installation or full local E2E.

Completion evidence (unchanged final app inputs):
- `npm run build` PASS (types, 5936 i18n keys, app/widget production builds);
  `npm run check:bundle` PASS. Log output/platform-support/build.log.
- `.venv/Scripts/python.exe scripts/verify_platform_support.py`: second run
  browser-1792011006191828400.log has 4 PASS (desktop/mobile lifecycle and conflict)
  and 2 failures from ambiguous global refresh selector, not application failure.
- `.venv/Scripts/python.exe scripts/verify_platform_support.py --grep "support handles recovery"`:
  browser-1792011229031686100.log 2 PASS. Selector scoped to support page; explicit
  503 responses and rendered error asserted before retry. Proves loaded detail and
  draft survive failed refresh/send, keep-editing navigation guard, successful retry,
  RU/KK/EN focus/no horizontal overflow and 403 content removal on both viewports.
- Six distinct browser scenarios now PASS; unchanged lifecycle/conflict passes
  reused after test-only selector adjustment. Desktop team and mobile clinic
  screenshots visually inspected: clear public/private separation, wrapped controls,
  readable forms/history, no horizontal overflow. Synthetic fixtures only.
- Documentation relative links and working/index diff hygiene PASS; no secrets or
  unrelated files in intended 45-path changeset. Shared DraftGuard implementation
  matches previous task guard; compatibility export and representative flow verified.
No required local failures remain. Full project/local E2E skipped per proportional
scope; existing push CI inspected separately. All owned verification processes
completed and disposable runtimes removed. No working migration, deployment,
external messages, new grants or provider calls. Publication pending below.

Publication: code dd1c6bba68739377f7fc5dcbe4deccab2500d2ec normal-pushed to
origin/main; remote SHA read-back matched. Branch remains codex/ui-testing-toolkit
in canonical C:/Users/user/Desktop/PlatformaCRM. Exact committed-range gate
`.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref e52db325b961a89dcfcfddc57abdfac75c943eb4`
PASS (output/platform-support/static.log), including migration/system checks.
Push workflow contains CI only; no deployment action. GitHub run 38636349215
queued at first inspection, not a green CI claim. Documentation receipt uses
working/index/committed-range hygiene; unchanged application checks reused.
Authorized implementation complete in local verified/published boundary;
working DB support0001 activation remains a separate explicit-target operation.

## CI-B301-PAYLOAD-20261015 — requested CI repair

Owner explicitly requested fixing the reported red CI. Canonical root
C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit; base
772bca11461e62e29865dc152dbc958ee6924f97. Starting dirty files: STATUS.md and
this checkpoint, both our final CI evidence from the previous phase; preserve them.
Mode diagnosis/fix; scope B301 client-card payload failure and affected verification.
Reuse existing API/serializers and isolated runner. Risk: hiding a real regression
with a weaker measurement or budget, changing response semantics or tenant scope.
First compare the actual rendered HTTP body with the existing json.dumps metric
on the unchanged representative fixture. Keep 150000-byte budget and row counts;
repair the measured cause only. Focused gate: entire B301 module, with an explicit
measurement regression if instrumentation is wrong. Completion: isolated system/
migration checks, static diff gate, normal push and actual CI. No working DB,
new platform phase, threshold increase, fixture shrink or frontend redesign.
Diagnosis on unchanged code: isolated representative test reproduces FAIL,
150011 synthetic bytes vs 135616 actual JSONRenderer body bytes (32 SQL queries).
CI's snapshot measured 150019; both exceed only the
synthetic metric. `json.dumps(default=str)` uses ASCII escapes and spaces unlike
the HTTP renderer. Fix measures `len(response.content)` for all B301 surfaces;
new Cyrillic/Kazakh fixture assertion checks UTF-8 bytes, not character count.
No application, fixture-volume, budget, permission or response-field change.
Baseline log: output/ci-b301-payload/baseline.log. Initial diagnostic invocation
missed DJANGO_SETTINGS_MODULE and failed before DB/tests; corrected to config.settings.
Verification: existing Python3.12.14 environment, disposable SQLite through
`scripts.codex_verify.isolated_runtime`; `manage.py check` PASS;
`manage.py makemigrations --check --dry-run` PASS/no changes;
`manage.py test apps.core.tests_b301_performance -v 2` 4 PASS, including all nine
read surfaces, 60-to-300 related-row scaling and cross-tenant denial.
Logs: output/ci-b301-payload/{system,schema,focused}.log. No dependencies installed.
Frontend/browser and separate application suites skipped: only test measurement
changed; full existing push CI will validate the integrated candidate separately.
Working diff hygiene PASS. Publication/remote CI pending at this checkpoint.

## PLATFORM-REBUILD-01-20261014 — truthful clinic workspace

User explicitly requested starting after delivery of the specification. Authorized
phase: roadmap result 1, overview/list/detail with truthful configuration, recorded
failures and unavailable data; remove placeholder navigation. New onboarding/cases,
permissions, /admin, working migrations, provider calls and runtime operations excluded.
Mode implementation; gap code/UX. Reuses platform selectors/APIs, grants/MFA/audit,
S02 pagination/search/support-note flow and shared UI. Approved requirement change
to S02 health heuristics; historical closure remains at its original snapshot.
Canonical C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
base b056c3d6795721c14a81f87707b9b189e92212f4; clean worktree/index at start.
Risk: false healthy/zero readings, lost list context, leaking data or broadening
support rights. No notification/BusinessEvent/AI-action/schema changes intended.
Focused checks after coherent backend slice: isolated platform read-model regression
tests incl unavailable/partial source, absence of optional setup, permissions and
cross-business aggregation. Completion: affected S02/operations tests, system and
migration drift checks; frontend build/types, targeted isolated browser flows for
search/filter/return, health/no-data, locales/mobile/keyboard and preserved support
journal permission/MFA/draft flow. No full E2E or dependency reinstall without cause.
Acceptance: no sales/landing/subscription absence classified as service failure;
unknown is not zero/healthy; list/detail/overview consistent; working navigation;
existing grant/MFA and journal behavior retained. Verified commit + normal push
to origin main under standing authorization; actual CI reported separately.
Status: implemented and scoped verification passed on 15.10; commit
772bca11461e62e29865dc152dbc958ee6924f97 normally pushed to origin main and
remote SHA verified. Next result is manual clinic creation, not started.
Post-publication CI38622945054: frontend build PASS; backend 1695 tests,
1 failure/10 skipped. B301MeasuredPerformanceTests payload bound for client_crm_card
failed at 150019 > 150000 bytes. Baseline CI38618663948 on b056c3d has the exact
same test/assertion/value (1681 tests, 1 failure/10 skipped), proving a pre-existing
failure outside this platform phase. Overall CI remains failed; no threshold
relaxation, unrelated client-card fix or full local-suite rerun performed.
At that phase's stop the CI evidence remained local/uncommitted; publication was
paused after the failure was observed. The owner subsequently requested the scoped
repair above, which includes this preserved evidence in its publication.
Owner clarification during implementation: pilot relevance alone never justifies
removing production-useful logic/components. Keep estimated MRR and subscription
logic, separate financial context from operational state and label estimate vs
actual revenue. Remove only unused placeholders, duplication or incorrect signals.
Implementation:
- Platform source reads use independent savepoints; missing sources return null
  with safe availability metadata. Missing service-state schema no longer erases
  queue data. Batched service observations reuse existing 180-second freshness.
- Optional sales/forms/landing/subscription absence is not a service failure;
  health.score=null, recorded_signals clear/attention/unknown; form errors=30 days.
  Latest activity has no fabricated Business.updated_at fallback. Billing failure
  does not hide the operational overview. Read roles and support writes unchanged.
- Overview keeps MRR/active subscriptions as an explicitly estimated financial
  block. Clinic list/detail separate configuration, service observations, activity
  and recorded errors. Status URL/filter/return, mobile layout, RU/KK/EN and explicit
  permission fallback. Historical support journal/MFA/draft behavior retained.
- Three working navigation destinations; old placeholder URLs redirect to overview
  (billing to #finance). Placeholder source remains unreachable, no blanket deletion.
  Vite /ready/ proxy fixed: same backend as /api, verified JSON200 through frontend.
Verification (Python3.12.14, Node24.18.0, existing dependencies unchanged):
- Initial isolated SQLite: `manage.py test apps.core.tests_platform_rebuild
  apps.core.tests_platform_s02 apps.core.tests_platform_operations
  apps.core.tests_service_status.ServiceObservationTests -v 1` via isolated_runtime:
  42 PASS; output/platform-rebuild-01/backend-1792004343804014200.log.
- Same targets on owned temporary PostgreSQL17 cluster: 45 PASS, including actual
  failed SQL then successful read in the same transaction; cluster stopped/removed.
  output/platform-rebuild-01/postgres-1792005183596053700.log. No working DB used.
- After final overview/billing decoupling: isolated `manage.py test
  apps.core.tests_platform_rebuild apps.core.tests_platform_s02.PlatformListTests
  apps.core.tests_platform_operations.PlatformOperationsDashboardTests.test_platform_overview_returns_operations_summary
  -v 1`: 19 PASS; backend-final-* log. Unchanged service/savepoint PG evidence reused.
- Isolated `manage.py check` and `makemigrations --check --dry-run`: PASS/no changes;
  output/platform-rebuild-01/system-checks.log. No migration authored/applied to work DB.
- `npm run build`: PASS (i18n5869 aligned keys, tsc, app/widget builds);
  `npm run check:bundle`: PASS. One initial JSX syntax failure fixed before PASS.
- `python scripts/verify_platform_s02.py --rebuild`: 11 PASS, 1 existing mobile-only
  skip, 2 failed assertions for explicit permission fallback (data was correctly
  hidden but generic error rendered). Added dedicated ForbiddenState, no retry403.
  `python scripts/verify_platform_s02.py --rebuild --grep "platform rebuild distinguishes|platform load recovery"`:
  4 PASS on final UI. Combined 13 distinct scenarios PASS; unchanged prior successes
  reused. Logs browser-1792004975761893500.log / browser-1792005275829312700.log.
- Visual inspection: synthetic desktop overview/list/clinic and mobile overview/
  clinic screenshots, no clipping; keyboard refresh/filter/search and no-overflow
  assertions, RU/KK/EN, unknown/partial/stale/403, real financial/status/MFA flows.
  Artifacts output/platform-rebuild-01/screenshots-first and frontend/test-results.
Full E2E, dependency reinstalls, live providers and working migration skipped as
outside this read-model/UI phase. Working handoff runtime untouched. Existing
source migration core0012 and monitor activation remain separate environment work;
the console honestly displays unknown without that source. No readiness claim.
Diff/link/index/committed-range gate and remote SHA/actual CI reported at publication.

## PLATFORM-REBUILD-SPEC-20261014 — operator console specification

Owner approved redesigning /platform from its workflows, retaining tested services
and removing obsolete code only after replacement. Current authorized phase:
detailed functional analysis/specification, not deletion or product implementation.
Owner additionally selected a simple internal support-case queue and manual clinic
creation by platform_admin only. Staff help with setup under existing access rules.
Support cases originate both from platform staff and the clinic CRM Support button.
Mode analysis/docs; gaps product specification, code and environment evidence.
Canonical C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
base293ac49f0d8b00731cc8b71d7848fb31de1d76f5, starting worktree/index clean.
Reuse S02/S03 evidence, platform APIs/selectors, role/grant/MFA/audit, Business and
onboarding services, shared UI. Preserve S02/S03/S04 closure boundaries.
Deliverable: registered repository specification with roles/actions, journeys,
screen map/states, data/API contracts, reuse/change/create/remove inventory,
acceptance, rollout/retirement sequence and explicit unresolved policy.
No /admin changes, source deletion, working migration, worker changes, provider
calls, messages, billing or new account privileges. Local handoff runtime stays running.
Risk: silently turning proposals into permissions or readiness claims. Checks:
source/evidence traceability, decision consistency, document links/registry,
working/index/real committed-range diff hygiene; no build/test install for docs.
Status: specification complete; implementation not started.
Deliverable: [registered specification](../platform-rebuild-spec-20261014.md).
Includes source-backed gap analysis, four-screen navigation, role/action matrix,
onboarding, support lifecycle/public-private separation, proposed API/data model,
observability semantics, reuse/retirement inventory and acceptance matrix.
Open policy: invitation delivery/acceptance, clinic case visibility, close/reopen,
retention and SLA. Only dependent behavior awaits those decisions.
Roadmap updated with proposed result order; existing S02/S03/S04 closure unchanged.
Verification: `git diff --check` PASS; Python pathlib/re/json check of all 18
specification links, unique evidence registry and UTF-8 PASS. Reviewed complete
six-file docs change including new 323-line specification: no secrets/unrelated work.
No executable examples added. No application tests/builds required for docs-only.
Publication uses standing authorization, explicit six paths, normal push HEAD:main;
index/committed-range checks and actual remote/CI result are reported in this task.
No working DB/process/provider changes. Existing workflow is CI only, no deploy job.

## CRM-R02-AI-RETURN-ACTIVATE-20261014 — local working activation

Owner explicitly requested activation/check in the current working environment.
Mode operation; gap environment. Canonical root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, base 605e5766e02bd7fd4b0ddd175a1762ff3a67d9fe;
starting tree/index clean. Target local db.sqlite3, not cloud/staging/production.
Plan: verify server roots, consistent SQLite backup/integrity, apply only bots0012,
preserve existing conversation states, start single supervised worker/beat scoped
to bots.resume_answered_handoffs, observe real scheduled executions and repeat safety.
Reuse tested service/migration and existing machine-local filesystem-broker pattern.
Risk: accidental old-dialog reactivation, duplicate scheduler, unrelated queued work.
Do not seed/reset merchant DB or accelerate real deadlines. No provider/model calls,
core0012 migration, full runtime activation, Meta/PS Cloud setup or automatic startup
at Windows login. Isolated transition/concurrency/UI evidence remains unchanged.
Completion: backup integrity/data preservation, schema/system check, running process
identity, beat-to-worker execution evidence, no outbound delta; docs diff/links.
Initial evidence: only bots0012 required for target; core0012 separately pending.
Redis localhost:6379 timed out; no existing Celery worker/beat. Existing antivirus
runtime is stopped. Local focused runtime will use its own broker/control directory.
Evidence/progress:
- Backend PID13456/14092 current directory canonical root; Vite PID6888 canonical
  frontend, proven by read-only process directory inspection. No server stopped.
- `output/local-handoff-recovery/migrate_working.py`: SQLite online backup to
  before-bots0012-20261014T181653Z.sqlite3; backup/working integrity PASS,
  foreign key check zero issues. Applied only bots0012. Six conversation records
  unchanged across all pre-existing columns; all table counts preserved (16 messages).
  All new eligibility/deadline fields NULL. Django system check PASS.
- Machine-local runtime.py uses one locked supervisor and dedicated filesystem
  broker; only handoff task scheduled at 60s, default queue, expiry120s. No env
  credentials changed. Existing output/local-file-antivirus/deps reused (pywin32);
  first startup failed because this dependency directory was absent from sys.path,
  stopped owned supervisor and corrected import path; no installation required.
  Duplicate-lock failure wording corrected; no second supervisor started.
- Runtime verification PASS: beat dispatch 18:20:07/18:21:07 UTC, worker successful
  execution 18:20:08/18:21:08, both resumed=0 (no eligible working candidates).
  Actual broker delivery and repeated scheduling proven; no real deadline accelerated,
  no synthetic merchant data created. Existing 6 conversations and16 messages unchanged.
  GET /health/ and /health/db/ on verified server127.0.0.1:8000 returned200.
  Duplicate `runtime.py run` exits1 with "Handoff supervisor already running";
  existing supervisor unchanged. Status heartbeat<3s, worker/beat exit_code null,
  one start each after corrected setup. Supervisor PID2356, worker launcher11796
  (actual17400), beat launcher20208 (actual6324), source/DB canonical.
- Local runtime intentionally left running. Start hidden from canonical root with
  `Start-Process -FilePath .venv/Scripts/python.exe -ArgumentList
  'output/local-handoff-recovery/runtime.py','run' -WindowStyle Hidden`;
  `.venv/Scripts/python.exe output/local-handoff-recovery/runtime.py status` reads
  health, `... runtime.py stop` stops only this supervisor's children.
  No Windows-login/reboot autostart configured. Backup/runtime files contain local
  operational data, remain ignored under output and must not be committed/deleted
  as test trash. Existing antivirus dependency folder is reused, not started/changed.
- Completed requested local activation. Prior isolated transition/concurrency/UI
  tests reused (application inputs unchanged); no redundant build/full suites or
  real provider calls. Working transition on a due real conversation not exercised:
  none exist; behavior remains covered by prior isolated tests. core0012 pending,
  other queues/cloud acceptance out of scope. CI38612654544 still in_progress
  when inspected during this operation, not claimed green. Docs hygiene/links checked.

## CRM-R02-AI-RETURN-20261014 — answered handoff idle recovery

Owner explicitly authorized implementation; Meta integration and PS Cloud setup deferred.
Owner confirmed: one hour after last customer/staff message, only after staff has
answered; unanswered human requests, safety/review stops and explicit manual pause
remain stopped. Timer sends nothing; only future inbound can trigger AI.
Mode implementation; gap code. Canonical C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, base 5babe5cc89d9e4ac5ba90f54198c48b847c2a040;
starting index/worktree clean. Reuse BotConversation, handoff/state services,
outbox delivery, Celery beat, Inbox API/header, existing permission and audit layers.
Scope: durable ordinary handoff eligibility/deadline, successful staff reply,
readiness/current permission guards, repeat/concurrency safety, visible deadline
and permanent-pause action. No provider/hosting setup, live calls or working DB migration.
Risk: accidental AI reactivation or stale queued reply. Focused backend checks
before UI; then affected safety/runtime/delivery suites, PostgreSQL concurrency,
check/migration drift and isolated migration; frontend build plus focused browser
flow (desktop/mobile/locales/error/recovery). Exact committed-range static at close.
Permission model unchanged; timer rechecks authorized staff rights. Activity/audit
record automatic transition, no new notification/BusinessEvent trigger or AI call.
Intentional additive nullable migration; legacy handoffs remain stopped. New fields
read-only in API; RU/KK/EN status copy. Scoped checks PASS; code published in main.

Progress/evidence (isolated local boundary):
- Nullable migration bots/0012 adds ordinary-handoff start, indexed deadline and
  authorizing staff FK; no legacy handoff is enabled. Business/conversation locks
  coordinate inbound, delivery and timer. Existing AI state service handles current
  permissions/readiness/budget, memory revision, audit/activity and stale reply revocation.
- Only explicit ordinary staff handoff from enabled AI is eligible. Automatic
  safety/review or previous paused/handoff state cannot be relabelled by repeating
  handoff. Latest successful manager reply arms the timer; latest inbound or pending/
  failed reply prevents it. Retrying delivery reuses the same message. System notices
  do not move the deadline. Timer invokes no model/provider and creates no message.
- Inbox exposes read-only start/deadline, existing handoff action, time in Business
  timezone and permanent-pause action through the existing permission-checked API.
- First coherent backend slice: 12 PASS, domain-1791999764478572500.log.
  Existing safety/runtime/notice regressions: 48 PASS, domain-1791999877458225300.log.
  Expanded first attempt domain-1792000001632381400.log had one test-fixture TypeError
  (AutoPipelineDecision omitted required reason), corrected; no acceptance waived.
- PostgreSQL: `.venv/Scripts/python.exe output/multibranch/postgres.py
  apps.bots.tests_handoff_recovery` — 22 PASS including two concurrent workers and
  incoming message committed while timer waits for lock. Disposable PostgreSQL17
  cluster/migration, removed after run; log postgres-1792000094757192000.log.
- Affected/dependent completion command: `.venv/Scripts/python.exe
  output/crm-s01-20261014/check.py apps.bots.tests_handoff_recovery
  apps.bots.tests_safety_recovery apps.bots.tests_customer_safety
  apps.bots.tests_handoff_notice apps.bots.tests_runtime_configuration apps.bots.tests
  apps.ai_core.tests_inbox_continuity apps.integrations.tests.TelegramIntegrationSkeletonTests
  apps.integrations.tests.WhatsAppIntegrationFoundationTests
  apps.integrations.tests.InstagramIntegrationFoundationTests` — system/drift PASS,
  186 PASS +2 PostgreSQL-only skips; domain-1792000231770901700.log. Channel tests use
  controlled provider boundaries, not live accounts. App code unchanged afterward.
- Strengthened the next-inbound regression to exercise actual eligibility and
  classification/reply path with mocked provider work rather than bypass evaluation.
  Same isolated helper, label apps.bots.tests_handoff_recovery.HandoffRecoveryTests.
  test_only_next_inbound_can_run_ai_and_old_inbound_is_not_replayed — 1 PASS;
  domain-1792000660141680500.log. Unaffected suites reused.
- Build/types/i18n/widget/bundle: `.venv/Scripts/python.exe
  output/ai-return-20261014/frontend.py` PASS; frontend-isolated-final.log. Existing
  dependencies reused, no install. UI inputs unchanged since this check.
- Browser first attempt browser-1792000192754094200.log failed fixture assertions:
  raw 503 detail was intentionally normalized by app; previous failed test left a
  scheduled fixture which affected next batch count. Corrected localized assertion,
  explicit POST/CORS failure injection and scoped synthetic-fixture cleanup.
  Second attempt browser-1792000488881878500.log timed out at webServer startup,
  before scenarios. Changed runner to logged explicit disposable preparation before
  Playwright (same pattern as existing S03 runner); did not extend app acceptance.
  Third browser run browser-1792000732035444000.log: 4 PASS desktop/mobile,
  actual API/handoff, failed and simulated successful provider delivery, localized
  status/menu/keyboard and stop error/retry, actual task with advanced fixture clock,
  repeated task no-op and no outbound. Visually inspected desktop RU/mobile KK.
  Removed an empty existing safety container exposed by ordinary handoff without a
  reason; rebuilt frontend PASS, then rerun only affected UI scenarios via --grep.
  Final UI recheck: `.venv/Scripts/python.exe scripts/verify_handoff_recovery.py
  --grep "answered handoff exposes"` — 2 PASS desktop/mobile;
  browser-1792001061108407300.log. Final desktop RU/mobile KK screenshots inspected:
  deadline readable, empty safety bar removed.
- Changed document file links/new Python AST/diff hygiene PASS. Full release gate,
  real AI/providers, working migration, cloud setup and production workers are out
  of scope; local evidence does not activate the feature in an existing environment.
- Publication: f6d6373937c2f99bd6d95f7a76ce0f87b683b20f, normal push to origin/main,
  remote SHA readback matches. Branch preserved codex/ui-testing-toolkit.
  `.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
  5babe5cc89d9e4ac5ba90f54198c48b847c2a040` PASS (diff/system/migration drift).
  CI38612574478 queued at receipt; not claimed green. Local test processes finished.
  Authorized implementation complete; runtime activation requires separately scoped
  working migration and updated beat/worker. Meta/PS Cloud and remaining R02 deferred.

## CRM-R02-20261014 — pilot decisions and provider research

Task contract: owner answered pilot questionnaire and requested Kazakhstan WhatsApp/
hosting research plus an explanation of current customer-agent controls. Mode analysis/
docs; gap policy/environment and named future implementation. Canonical root
C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
base 0175cd5884c4fc6b037eea18ccc92da0a46d3299; clean starting tree.
Reuse current AI/channel/notification/operations implementations; no product rewrite,
credentials, subscriptions, external messages, deployments or working migrations.
Checks: inspect relevant code/contracts, primary provider sources, docs consistency,
links, working/index/actual committed-range hygiene. No app tests/build for docs.

Owner decisions:
- Clinic name and branch count are not prerequisites for preparation; actual routing
  must use the connected clinic's real Business/branch setup. 3–5 users; clinic
  administrator collects feedback/accepts clinic workflow. Individual roles not assigned.
- Exercise all current CRM functionality/behavior; this does not resume deferred ERP,
  integrations, CRM analyst, billing or clinical-record development. Real client,
  lead and appointment data after access opens; preserve data after the pilot.
- Telegram AND WhatsApp are required; clinics connect their own accounts. YCloud
  is a tentative WhatsApp choice, alternatives requested. No live accounts yet.
- Only customer Inbox AI in pilot; CRM/analytics agent development remains paused.
  Auto replies when agent/business policy permit; explicit prepare-reply action
  yields a draft. Replies and appointment reminders are desired pilot scope.
- Owner proposes returning a human-handled dialog to AI after 1 hour since the
  last customer/operator message. No immediate outbound message on timer implied.
  Current code has explicit staff resume, no hour-based resume found. Mandatory
  safety/review stops remain current contract; timer applicability to these and
  unanswered human requests needs a decision before dependent implementation.
- Infrastructure should be physically in Kazakhstan; Yandex ecosystem is no longer
  the selected hosting direction. Domain purchased, hosting account unspecified.
- Owner is technical operator and sole pilot stop/resume decision maker. Platform
  administration page is requested incident surface; it cannot alert through a
  total application outage. Independent alert destination remains undecided.
- Keep current client Excel/CSV import; no wider migration scope selected. Whether
  CRM replaces an existing schedule or runs alongside it remains to be explained.
- Target start 30 October 2026, duration at least approximately two weeks; target,
  not a proven launch date. Free pilot, owner funds infrastructure/AI/messages;
  do not introduce pilot billing caps or automatic spend cutoff. Existing abuse/
  safety protections are not removed by this commercial decision.
- Success: correct CRM relationships/no duplicate effects, grounded customer AI
  availability/booking behavior, recovery/reliability. No invented uptime percentage
  or guarantee of zero bugs. User chooses stop; no new automatic global shutdown.
- Retain business data and accounts for continued use; billing/limits after pilot
  require their own implementation. Observe interface/system behavior without
  collecting raw message contents/secrets in diagnostic logs.

Code inspection (not new runtime certification): AIAgentActionsSection.tsx exposes
pipeline mode, auto_send_reply, creation_policy and per-tool controls; Inbox
ConversationsPage.tsx has prepareReply preview and explicit insertion/send. Existing
AI contract covers controlled client/lead/task/open deal/new appointment creation,
fresh slot validation and staff-only existing-record changes. Resources such as
chairs/equipment remain outside current scheduling scope. Telegram provider and
Meta Cloud WhatsApp adapter exist; no YCloud adapter found. Existing reminder
delivery uses Telegram/WhatsApp but live provider acceptance remains required.

Primary-source research, 14 October 2026 (not contractual/provider certification):
- YCloud is a WhatsApp provider headquartered in Singapore, distinct from Yandex:
  https://www.ycloud.com/about-us
- edna Kazakhstan states official Meta partnership; documented API and partner
  program: https://edna.kz/about-company/ and
  https://docs-pulse.edna.kz/docs/api/messages/sending . Candidate for API transport;
  tenant onboarding, data geography, credentials/portability and terms unconfirmed.
- IntellectDialog has Kazakhstan LLP details and WABA/API in its offer:
  https://intellectdialog.com/docs/ophert/kz/ooo . API-only SaaS suitability and
  location of processors/backups remain to verify, not inferred from local company.
- SMSC.KZ documents WhatsApp send API: https://smsc.kz/api/http/send/whatsapp/ .
  Full inbound/webhook/multi-clinic onboarding fit not established by this page.
- PS Cloud lists PostgreSQL/KeyDB managed DBs and Kazakhstan locations:
  https://www.ps.kz/ru/hosting/dbaas ; compute/S3 described at https://www.ps.kz/ru .
  Recommended first infrastructure candidate. KeyDB is not the exact Redis runtime
  tested in S04; compatibility/queue recovery or separate Redis must be verified.
- Hoster.kz offers Kazakhstan cloud VPS: https://hoster.kz/cloud/vps/ . Alternative
  with self-managed components; equivalent managed PostgreSQL/Redis not confirmed.
- WhatsApp templates outside the 24h window and opt-in:
  https://whatsappbusiness.com/policy/ . Hour-based AI timer does not reset this window.

R02 remains OPEN: provider/target choice, safe onboarding credentials, applicable
legal texts, RPO/RTO/backup retention and human-handoff timer policy are not finalized.
No outreach to vendors. No unverified news about Yandex attacks accepted as fact.
S04 receipt CI38562361806 completed success, checked before this analysis.
Verification: changed relative link targets and working diff hygiene PASS; five
intentional Markdown files reviewed. No app/environment inputs changed, so no
build, install, browser or database tests run. Publication uses the standing normal
push authorization; actual commit/remote SHA and CI are reported with the response.

## CRM-S04-20261014 — isolated operations and recovery

Owner authorized S04 on 14.10 after S03. Mode evidence/environment with minimal
fixes for reproduced in-scope defects. Canonical root C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit, base b0f58e87ff4c2f981956cc1a7db4e2a1b1293763;
clean starting index/worktree. No other writers/agents involved.
Observable result: reproducible isolated PostgreSQL/Redis/Celery processing and
recovery/retry/cancel with no duplicate effects; export/private files and actual
backup restore validated against independent restored data. Reuse isolated_runtime,
existing domain services/tasks, pilot_recovery_drill and native PostgreSQL tools.
Existing SQLite/filesystem drill is prior evidence only, not PostgreSQL/Redis proof.

Scope: synthetic local fixtures, dedicated loopback ports and queues, owned
worker/beat lifecycle, disposable original/restored databases and file directories.
No working DB migration/data/credentials, external delivery/AI/integrations, cloud
provisioning, OS service changes, production RPO/RTO claims or new UI redesign.
Retain owner/admin recipient and clinic-only recovery policies from S02/S03.

Plan/risk/checks before implementation: inspect real queue/retry/lease/cancel and
backup contracts; validate dependencies and isolation before starting processes.
Then run real broker/worker restart/replay/retry/cancel scenarios incrementally;
validate exports and fail-closed files through existing APIs with role/tenant denial.
Restore pg_dump plus private files to separate target and assert relationships,
checksums/permissions and credential decryptability using synthetic credentials.
Required completion: reproducible runtime drill and affected/dependent domain tests,
system/migration drift, docs/diff/committed-range gate. Build/browser only if product
frontend changes or a missing reachable-flow acceptance requires it. Do not repeat
unchanged S03 UI checks. Record failures and exact runtime boundary. Stop own
processes on exit. Normal publish under standing authorization after scoped gates.
Notification/BusinessEvent/AI/domain impacts: existing effects exercised only in
synthetic data; no new business policy or provider calls planned. Migration none
planned, all current schema applied only to disposable targets. Next: Redis runtime
availability and focused gap inventory, then the first real worker check.


S04 progress/evidence 14.10:
- Native PostgreSQL17 reused. No Docker runtime/distribution available. Downloaded
  Redis7.4.9 Windows MSYS2 portable archive from redis-windows release7.4.9 into
  ignored output/crm-s04-20261014/deps; SHA256
  98af6511ca35601cc8d8200a92318e00f9d2d5425a9f7f3e8f699d3bdd59dcf6 matched release.
  No OS installation/service. This is a Windows compatibility runtime, not Linux
  production/prefork certification. Celery uses a separate real Redis and solo pool.
- New scripts/verify_recovery_s04.py + recovery_runtime/recovery_scenarios/recovery_files
  reuse isolated_runtime, new native PG cluster and owned loopback Redis/worker;
  no input accepts a working DB URL. Child runtime identity checks allocated ports,
  database names/user and disposable media paths. Windows stop targets owned process
  tree (venv launcher can own child Python). Outputs captured under S04 ignored folder.
- First queue run1791978871224576200: worker restart/WAIT/replay PASS but runner
  exited1 while printing mixed-encoding PG log. Fixed UTF-8 reporting/LC_ALL.
- Expanded run1791979026175071000.log: transaction crash/rollback/recovery PASS, then assertion
  expected403 for operator but scoped lookup correctly returned404. Fixed exact
  expected denial, leaving owner-success and outsider-denial checks intact.
- Queue rerun1791979107030349500 PASS: real PostgreSQL/Redis workers, committed
  progress, kill inside action transaction, stale claim recovery, API retry/cancel,
  access denial and one reminder under repeated dispatch. No product code changed.
- Full run1791979270642852100.log stopped before scenarios because runner isolation marker
  was added while initial process had already started. Fresh immutable run required;
  owned Redis/PG stopped. Do not edit executable drill inputs while it is running.
- Full run1791979334167615600.log: export/private download/replay/revoked actor PASS; file
  outage/retry/clean PASS; disk EICAR did not produce expected infected status.
  Small independent real-ClamAV in-memory diagnostic returned clean=False,size68,
  engine1.5.4/28153. Avoid host-file AV interference: retain memory EICAR assertion,
  add harmless S04 custom signature to a disposable COPY of signature DB for real
  file/worker quarantine. Do not weaken freshness/scan/download assertions.
- Existing local AV signature copy was stale (daily01.10); copied only signature
  files into S04 deps and ran freshclam against that copy. Public signature update
  succeeded to daily28153; working scanner/config/signatures untouched. Final full
  drill uses real ClamAV1.5.4 and unchanged72h freshness check.
- Focused affected/dependent gate via existing isolated check helper:
  apps.core.tests_file_scanning, apps.automations.tests, apps.notifications.tests,
  apps.tasks.tests_reminders, B5 large entity/report export tests, B1 notification
  claim/transient retry tests:73 PASS; system/drift PASS.
  output/crm-s01-20261014/domain-1791979399385763900.log.
- S03 receipt CI38554277365 now completed success; historical S03 code remains closed.
- Full runtime1791979527175071700.log PASS: exports/files + broker queue loss/durable
  recovery through actual beat + pg_dump/pg_restore/private-file/key restore.
  Restored API uses DRF APIClient against restored PostgreSQL/media, not browser UI.
  FK constraints, tenant links, corrupted restored-file denial, missing encryption
  key denial and correct-key decryption PASS. Owned worker/beat/ClamD/Redis/PG stopped.
- Final guard refinement rejects internal modes before Django/settings import;
  --worker/--drill/--restored with no runtime all rejected (3 checks PASS). Runtime
  executable paths are validated before startup. Final full rerun PASS on
  these exact inputs: output/crm-s04-20261014/runtime-1791979744347639300.log. No product behavior rewrite or new schema required.
  No frontend/product changes, no full local release gate or dependency reinstall.
- Final runner syntax and changed relative links PASS; working/index hygiene PASS.
  Required runtime and dependent tests complete.
  No working DB migration or service installation, no production RPO/RTO claim.
- Closure: S04 complete in the agreed local isolated boundary. Commit e3dbd9711b7cf78e6092b35bac48b1d55be8f65e
  passed scripts/codex_verify.py --mode static --base-ref b0f58e87ff4c2f981956cc1a7db4e2a1b1293763.
  Normal push origin HEAD:main succeeded; remote SHA matched. CI38562250124 is
  in_progress at publication, not a CI PASS. Final receipt changes only docs;
  runtime/test evidence remains valid. All owned runtime processes stopped.
  Canonical root/branch unchanged; no unrelated WIP. R02–R07 not started.

## CRM-S03-20261014 — service state and incident notifications

Owner asked to start S03 after S02. Mode implementation; gaps code/evidence.
Canonical C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit,
base0a9b15f72621068a2f20d43bbf31a01679679f63; clean starting index/worktree.
Reuse operations_health, readiness, ConnectivityStatus/StatusNotice, notifications
routing/bell/preferences and current tenant access; no interchat work/delegation.

Observable result: employee-facing service impact separated from platform diagnostic
readiness/history; incident start/recovery/freshness explicit; repeated observations
cannot duplicate notices. Optional disconnected providers do not signal CRM outage.
No external alert delivery/provider calls, working migrations, real clinics, S04
worker provisioning/recovery/backup or broad redesign. Existing clinic-only recovery
policy retained. Complete outage cannot be independently alerted from inside CRM.

Initial evidence: platform status currently mixes production readiness, all-time
failed jobs and optional provider rollout; no persisted service incident lifecycle.
ConnectivityStatus listens only to browser network events and checks liveness
/health, which does not prove DB availability. Existing notifications have role
routing/preferences but no service-incident transition identity.

Plan/risk: persist bounded per-Business/component observations with serialized
transition state; read-only tenant-safe status projection; current-state impact
from overdue internal background work, historical terminal failures remain separate
operator diagnostics. Stale observations are unknown, never an inferred recovery.
No external provider/config readiness in merchant service status. Reuse existing
stale deadlines for jobs and explicit monitor freshness. UI uses a concise real
status alert, existing bell and platform diagnostics, RU/KK/EN. Recipient policy
decision approved by owner 14.10: staff banner + owner/admin bell. Active accounts
and admin memberships required; existing normal SYSTEM preferences apply.

Checks selected before implementation: focused isolated lifecycle tests after each
backend slice (start/repeat/recovery/recurrence/stale/out-of-order/rollback), source
classification and optional-provider exclusion, tenant/role denial and safe payloads;
concurrency verification for transition dedupe where applicable. At completion
changed/dependent notifications/core suites, system/drift and isolated migration;
frontend build/types/bundle, targeted desktop/mobile status/bell/error/recovery and
locale/keyboard flow. No full local suite or installs without demonstrated need.
New observation schema is expected; no working DB migration authorized. Notifications
SYSTEM only; no new permissions, CRM lifecycle changes, BusinessEvents or AI actions.
Publish own reviewed change set using standing normal-push authorization after gates.

S03 final notification slice: owner accepted the recommended recipient policy.
Start/recovery notices are written atomically with observations, immediately SENT
in-app (no external calls or worker dependency). Existing SYSTEM preferences apply.
Owner receives even without a redundant membership; active admin memberships and
active users only. Bell scopes service notices to their recipient, including for
business-wide managers/admins; general authorized diagnostics retain their scope.
Episode transitions provide dedupe; a failed notification write rolls back the
sample. No S04 work. Final verification/publication follows below.

Implementation: core ServiceComponentState + migration0012 stores one unique
Business/component observation and recurring episode identity. Business row lock
covers source sampling/transitions; old observations cannot overwrite newer ones.
Current overdue automations, SYSTEM notifications, exports and pending/error file
checks are signals; historical terminal failures, future scheduled work, unconfigured
optional providers are excluded. Defaults reuse existing automation/export900s and
file scan lease120s; sampling60s, batch100 oldest-first, freshness180s. Stale/missing
observations mean unknown and never manufacture recovery. Cleared delay does not
claim a failed action succeeded. API read-only, tenant-access checked, no payload,
filename, entity ID or raw error. Platform summary includes bounded10 current incident
rows and separates environment readiness from service impact. Existing independent
external outage monitoring remains future environment work.

UI: ServiceStatusNotice in AppLayout uses shared StatusNotice, real API, explicit
unknown/error/recovery and RU/KK/EN copy. ConnectivityStatus adds authenticated visible-
tab readiness polling30s and uses /ready (DB check), retaining event/manual recovery;
reads only refetched after recovery, never mutations. Core task/beat and management
command observe_service_status collect observations; not run on working database.

Evidence:
- First isolated core lifecycle slice5 PASS, log
  output/crm-s01-20261014/domain-1791974102387565400.log.
- Expanded run23 tests had1 test-assertion defect: checking substring42 also matched
  timestamp microseconds. Replaced with checking absence of entity_id, keeping private
  text assertion; rerun service suite8 PASS, domain-1791974335292258200.log.
- Final affected `.venv/Scripts/python.exe output/crm-s01-20261014/check.py
  apps.core.tests_service_status apps.core.tests_platform_operations
  apps.notifications.tests_bell`:24 PASS/1 PostgreSQL-only skip; system/drift PASS,
  domain-1791974664081098600.log. Dirty snapshot after bounded incident summary added.
- `.venv/Scripts/python.exe output/multibranch/postgres.py
  apps.core.tests_service_status`:9 PASS including two-collector concurrency;
  output/multibranch/postgres-1791974472892395700.log. New migration applied only in
  disposable DB. PG cluster stopped. Subsequent delta only platform read summary/test.
- `.venv/Scripts/python.exe output/crm-s03-20261014/frontend.py`:final build/i18n/types/
  widget/bundle PASS; output/crm-s03-20261014/frontend-isolated-final.log.
- `.venv/Scripts/python.exe scripts/verify_service_s03.py`:8 PASS desktop/mobile,
  log output/crm-s03-20261014/browser-1791974634359261200.log. Real isolated API/fixture
  proves overdue export/banner/operator summary; boundary injection proves unknown,
  recovered,503/retry; real authenticated flow with failed readiness detects API outage
  despite navigator online. Existing reconnect/draft test also PASS on both viewports.
  RU/KK/EN keyboard/no overflow checked. Screenshots frontend/test-results/service-s03-*/
  service-impact*.png inspected (desktop RU/mobile KK); banner fits shared workspace.
  First runner attempt failed before browsers due hard-coded seed slug; fixed to
  isolated E2E_BUSINESS_SLUG, final run above passes. All owned browser servers stopped.
- Git diff hygiene PASS. No committed-range gate yet (base==HEAD), no commit/push,
  full local suite/live environment/external delivery not in this slice. Current
  dirty files all task-owned; new scripts/verify_service_s03.py makes UI fixtures
  reproducible. Prior S02 CI38548316979 and38548233244 are completed success.


Final notification evidence (14.10, after owner decision):
- Focused isolated service slice:10 PASS/1 PG skip,
  output/crm-s01-20261014/domain-1791975503385609000.log.
- Same isolated check helper with apps.core.tests_service_status,
  apps.core.tests_platform_operations and apps.notifications.tests_bell:
  26 PASS/1 PG skip, system/drift PASS;
  output/crm-s01-20261014/domain-1791975534631519500.log.
- PostgreSQL helper output/multibranch/postgres.py apps.core.tests_service_status:
  11 PASS including one bell under concurrent collectors, rollback/retry,
  recipients/preferences/inactive accounts and cross-business separation;
  output/multibranch/postgres-1791975545105477900.log. Cluster stopped.
- Browser run browser-1791975593912569800.log:7 PASS/1 failure. A real defect:
  fixed desktop header intercepted the connectivity retry button. Screenshot
  confirmed the banner behind the header. ConnectivityBanner now sticky z60;
  regression waits for the real header before clicking, no forced clicks.
- Rebuilt frontend after this fix: build/types/i18n/widget/bundle PASS,
  output/crm-s03-20261014/frontend-isolated-final.log. Backend unchanged since PASS.
- Final browser rerun:8 PASS desktop/mobile including real owner bell and retry
  above the mounted header; output/crm-s03-20261014/browser-1791975767587824600.log.
  All owned test processes stopped. Code/affected-flow verification complete;
  committed-range static and publication receipt follow. No full local release gate,
  dependency install, working migration, external provider call or deployment.


Publication receipt: S03 complete in agreed scoped boundary, S04 NOT started.
Canonical root and branch unchanged. Code1efc0f8d45d246a9d191b2243d6d3b15573c8613
normal-pushed origin HEAD:main; remote main read back at exactly this SHA.
`.venv/Scripts/python.exe scripts/codex_verify.py --mode static --base-ref
0a9b15f72621068a2f20d43bbf31a01679679f63` PASS on the actual committed range
(diff working/index/range, migration drift, system check). New files and full
outgoing range reviewed; a trailing blank line in the new test was removed before
commit. No unrelated WIP. This receipt changes docs only; application PASS reused.
GitHub CI38554191822 queued on readback, not claimed green. Push triggers existing
CI only; no deployment requested/performed. All owned tests/servers/PG stopped.
Remaining environment boundary: working core0012 migration, worker/beat operation,
independent external monitoring and production acceptance. Next roadmap item S04
requires its own user instruction; no automatic continuation/coordination.

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
