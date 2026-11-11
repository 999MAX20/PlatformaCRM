# AI-AGENTS-FIXES-20261111

Owner request: fix the scoped `/ai-agents` audit findings and agent readiness,
preserving current design and verifying affected scenarios. No release/live gate.
Canonical root: `C:/Users/user/Desktop/PlatformaCRM`; branch `codex/ui-testing-toolkit`;
base `841e8bfaf28bb80741e77c00b7f83041b5d58a68`. Foreign starting WIP and later
unrelated voice/docs changes preserved. Detailed checkpoint/logs: `output/ai-agents-fixes-20261111`.

## Behavior

- Local AI configuration participates in lifecycle/runtime readiness. Structural
  readiness is separately available; mock is explicit, provider network health is
  never inferred. No external requests, secrets or provider base URLs in diagnostics.
- Automatic booking preflight reuses current responsible-member validation and
  checks current authorizing actor permissions. It is advisory; existing transactional
  actor/resource/slot/approval checks are retained and other features remain available.
- Effective model and selectable profiles come from server configuration/generation
  policy; custom saved models are retained. No claim of provider model-catalog validation.
- Allowed-but-inactive functions explain mode restrictions without discarding permissions.
- CRM operation status has loading/error/retry/empty states; disabled analytics does
  not mount the runtime and offers settings navigation only to a manager.
- Existing permission-scoped Inbox summary supplies selected-agent counts. Message
  links retain agent identity and explicit URL filters ignore unrelated stored filters.
- Existing visual system/components retained; new copy in RU/KK/EN.

## Verification

Focused initial24:23PASS/1 test-fixture URL error (wrong runtime-directory endpoint);
corrected diagnostics8PASS. The error was in the new test URL, not an application404.

Final backend: **123 PASS**, system check PASS, migration drift PASS. Command from root:

```powershell
.venv/Scripts/python.exe output/ai-agents-fixes-20261111/verify.py backend apps.bots.tests_readiness_diagnostics apps.bots.tests_readiness apps.bots.tests_scenarios apps.bots.tests_runtime_configuration apps.bots.tests_configuration apps.bots.tests_customer_knowledge apps.bots.tests_automatic_booking apps.bots.tests_booking_creation apps.bots.tests_preview apps.bots.tests_pause_inbound apps.ai_core.tests_agent_runtime apps.ai_core.tests_settings_certification apps.ai_core.tests_approval_binding apps.ai_core.tests_knowledge_isolation apps.ai_core.tests_workflows
```

The wrapper uses `scripts.codex_verify.isolated_runtime`, running `manage.py check`,
`makemigrations --check --dry-run`, then explicit test labels. Disposable SQLite;
mock AI/eager jobs, no external integrations. Includes activation/configuration errors,
role/tenant guards, safe knowledge, approval binding, booking rollback/replay and
agent-specific Inbox counts. Logs: `backend-1794405837472197700-{0,1,2}.log`.

Browser: **7 PASS** using an isolated real API and Vite, including new4 scenarios
and existing3 UX regressions. Command:

```powershell
.venv/Scripts/python.exe output/ai-agents-fixes-20261111/verify.py browser
```

Initial browser1PASS/6FAIL: new fixture used disabled generic conversation-create API,
an analytics assertion used the work-chat label, and accumulated bots hit the plan
limit. Fixed tests to use public website intake, actual analytics field and cleanup
only their created agents; no application permissions or entitlement were weakened.
Corrected run: `browser-1794406201830362100-1.log`,7PASS. It proves saved/effective
tool state, server model persistence, scoped real summary/empty/error/retry, explicit
URL filters, CRM status503/retry, analytics off/no runtime and on/recovery, draft
protection, knowledge validation/retry and manager configuration denial.

RU1440/KK320/EN390 screenshots inspected; no document horizontal overflow, scoped
axe2a/2aa PASS. Keyboard Enter follows the analytics settings link. Provider outage
presentation uses an intercepted response; provider configuration denial and booking
diagnostics are separately proven by backend tests, not by the injected screenshot.
Existing layout, tokens, shared form controls and mobile navigation are retained.

Review aligned unread/handoff links with the summary's **open** conversation scope.
After that final frontend delta only the affected activity flow was rerun:

```powershell
.venv/Scripts/python.exe output/ai-agents-fixes-20261111/verify.py browser --grep "agent activity"
```

Result1PASS (`browser-1794406473557377100-1.log`); other6 unchanged-input PASS retained.
Images from the7-scenario run remain in `browser-results`; the focused rerun uses
a separate `browser-results-<port>` directory. Test-owned servers are stopped by runner.

Frontend final: `npm.cmd run build` (i18n7134/TypeScript/app/widget PASS),
`npm.cmd run check:bundle` PASS. Logs `build-final.log`, `bundle-final.log`.
An earlier build also passed; the final build followed the link-scope correction.
RU/KK dictionary chunks remain >500kB advisory; app-shell400kB budget PASS.
React review: hooks remain unconditional, API calls stay in clients, permission
guards precede reads, query keys include agent/business, errors remain visible.

No full-project/live gate: no release candidate, no schema changes, no new locks or
concurrency semantics. PostgreSQL concurrency suites were not repeated; existing
transactional booking/approval paths are unchanged. Readiness tests prove local
configuration, not provider/network/model quality or production availability.

No working-database/provider/deployment actions, migrations, new permissions,
notification or BusinessEvent effects. No new roadmap phase is introduced.

Contracts/frontend/capabilities and both agent passports updated. README/setup/access/
CRM/integration/operations requirements are unchanged; no roadmap phase acceptance
was reopened or closed. Scoped implementation/local verification remainder: none.
Publication reviewed separately: foreign outgoing history blocks pushing this task
to origin/main without including unrelated work; no deployment or new CI claimed.
