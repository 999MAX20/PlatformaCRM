# AI-AGENT-SCENARIOS-20261005

Owner-authorized restructuring, locally implemented and verified on 2026-10-05.
Canonical source: `C:/Users/user/Desktop/PlatformaCRM`, branch
`codex/ui-testing-toolkit`, base/HEAD `9ff366207e73472cda71ca3b9113ca4f9f305af9`.
Uncommitted snapshot; prior UI work is preserved and the index remains empty.
This supersedes the preceding three-workspace UX decision, not its historical evidence.

## Result and boundaries

- Creation requires a name and one of two large scenario cards, with icons and
  hover/focus/tap help: customer conversations (`inbox`) or CRM/analytics (`crm`).
- Scenario is stored in `Bot.settings_json`, validated server-side and immutable.
  Existing agents default to inbox. One CRM agent per business is enforced under
  a business lock. No schema migration or new permission framework.
- Stable URLs remain `/app/ai-agents/:id/:section`: renaming does not break links.
  The persisted scenario selects the interface. Inbox retains profile, knowledge,
  actions, channels and test; CRM has profile, knowledge, actions, work and analytics.
- The old AI Assistant page is removed; old URLs redirect into AI Agents.
  Its CRM work, exact approvals and historical/event analytics are retained.
- Each CRM agent supplies its own instructions, sources, tools and model settings.
  Jobs and prepared commands carry its identity/fingerprint; pause or changed
  settings revoke stale work. Existing confirmation, replay, role and tenant checks
  remain. Customer agents cannot use the internal CRM runtime or CRM channels.
- Staff use a minimal permitted agent directory without configuration access.
  Legacy business-level APIs remain compatible. Knowledge items remain shared
  business knowledge; the agent's own source/action selection is persisted separately.
- No new external delivery, paid provider calls, BusinessEvent policy, financial
  calculation or notification policy. Existing activity/audit behavior is preserved.

## Verification

All application checks used the existing `.venv` and
`scripts.codex_verify.isolated_runtime`; disposable DBs, ports and mock AI.
No dependency install, working-DB seed or full-project/E2E certification.
Local runners and logs are in `output/ai-agent-scenarios-20261005`.

| Check | Result |
| --- | --- |
| Focused creation/configuration, runtime/jobs/CRM, status and customer boundary | PASS: 9, 70, 12 and 10 tests at successive coherent backend steps |
| `manage.py test apps.ai_core apps.bots apps.conversations.tests_ai_confirmation -v 1` | PASS: 250 tests; `backend-final.log` |
| `manage.py check`; `manage.py makemigrations --check --dry-run` | PASS, no drift |
| `node --test scripts/tests/sidebar-navigation-policy.test.mjs scripts/tests/action-color-policy.test.mjs` | PASS: 13 checks |
| `e2e/ai-agent-scenarios.spec.ts`, desktop/mobile | PASS: 3 + 3; final desktop and mobile-4 logs |
| `e2e/ai-agents-ux.spec.ts`, desktop/mobile | PASS: 3 + 3; browser-ux logs |
| `e2e/ai-functional-settings.spec.ts`, desktop/mobile | PASS: 2 + 2; functional-desktop-2 and functional-mobile logs |
| `npm run build`; `npm run check:bundle` | PASS: i18n, TypeScript, app/widget build, bundle; `build-2.log` |
| Working/index diff hygiene, changed documentation links, new-file review | PASS; no new committed range |

Browser command, separately per file/project to isolate fixture quotas:

```powershell
.\.venv\Scripts\python.exe output/ai-agent-scenarios-20261005/verify-ui.py <project> <filename>
```

The runner invokes `npx playwright test e2e/<filename> --project=<project>
--reporter=line` in the isolated environment. Evidence covers required scenario,
duplicate CRM prevention, saved settings/reload, customer settings, staff denial,
source filtering, paused runtime, errors/retry, dirty navigation, template review,
keyboard help, RU/KK/EN, mobile overflow and axe checks. CRM approval uses a real
server-prepared tool payload; only the planner response is substituted with that
payload. Cancel leaves no task; exact confirmation creates one task through the
real API. Screenshots of creation and analytics were visually inspected.

Initial failures are retained: test fixture/selector corrections; creation blocked
by an untouched absent profile; click racing canonical navigation; CRM knowledge
save footer disappearing; mobile table keyboard scrolling; translation fallback
ordering. These were corrected and affected checks passed. One runner invocation
used bundled Python without Django and failed before tests; reruns use `.venv`.
An invalid title filter selected no tests and is not counted as verification.

## Authorized local cleanup

Owner explicitly requested removing the two existing local agents to start fresh.
Canonical `db.sqlite3` contained agents 1/2, four channels, two profiles and no
conversations. SQLite backup was verified before mutation. Audited bot/profile
DELETE endpoints were invoked with each business owner in one guarded transaction.
The first attempt rolled back because profiles use SET_NULL, not cascading delete;
the corrected operation explicitly removed only their associated profiles.

Final result: zero agents/channels/profiles, 109 unrelated tables unchanged by
row fingerprint, four audit and four activity events added, integrity and foreign
keys PASS. No CRM history or AI request logs removed. Local backup:
`output/ai-agent-scenarios-20261005/before-agent-cleanup-2.sqlite3`;
receipt: `cleanup-receipt.json`. Backups remain ignored and must not be published.

## Publication and limits

No commit/push/deployment: prior CI run 37312854122 for `9ff3662` failed dependency
audit (braces/DOMPurify); frontend build/backend passed on the last recorded readback.
See [prior CI evidence](ui-feedback-20261005.md). Dependency repair is outside this
scope. Scoped local PASS does not change that failure or prove live AI/delivery.
The next step is owner review from the now-empty local AI Agents page; this task
does not authorize another product phase.
