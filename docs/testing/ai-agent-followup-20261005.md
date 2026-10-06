# AI-AGENT-FOLLOWUP-20261005

Owner follow-up to [typed agents](ai-agent-scenarios-20261005.md): fix the local
CRM creation failure and intrusive help; add profile-footer deletion. Owner chose
to retain conversations and history when deleting an agent.

Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch
`codex/ui-testing-toolkit`, HEAD `9ff366207e73472cda71ca3b9113ca4f9f305af9`.
Prior WIP retained, index empty. Starting patch/status and final source hashes are
under ignored `output/ai-agent-followup-20261005`.

## Diagnosis and result

The live local backend was still the earlier `runserver --noreload` process.
`GET /api/ai/agents/` returned 404; the source and isolated test servers had the new
route. Four owner-created agents (3–6) had no scenario in persisted settings.
The earlier local delivery missed restarting that process. Only the owned canonical
backend was restarted, with autoreload; the same route now returns authentication
401, and authenticated `OPTIONS /api/bots/` returns 200 with inbox/CRM choices.
The existing four records were not converted, deleted or seeded. Frontend remains
on port 5173 and backend on 8000; source root and commands were checked.

The scenario tooltip opens only from the help icon, keyboard focus or touch.
It appears to the right of the modal in available space; narrow viewports expand
the hint inside its card without covering other choices. Escape dismisses help
before dismissing the modal. Focused touch help stays open until focus leaves.

Deletion is available at the bottom of both profile types, subject to existing
`ai_automation.delete` permission. A shared confirmation dialog describes history
retention and lost unsaved settings. Cancel, pending state, API error/retry and
post-delete navigation are supported. Unsaved changes cannot trap the user on a
successfully deleted agent's route.

`DELETE /api/bots/:id/` now calls an audited transaction that retains historical
foreign keys and marks the agent deleted in protected settings. It pauses channels,
disables profiles/conversation AI, rejects unexecuted tool calls and approvals,
stops queued AI jobs/automatic replies and cancels active runs for its conversations.
Retries cannot revive it. Default Bot lookups/quotas exclude retired agents;
explicit historical lookups remain available. A CRM replacement can be created.
Shared automation rules, other agents and existing CRM records remain unchanged.
Existing fingerprints and business/command locks protect late work; a message
already sent to an external provider cannot be recalled. No remote deprovisioning
or live-provider acceptance is claimed.

## Verification

Used existing `.venv` and `scripts.codex_verify.isolated_runtime`; disposable
databases/ports and mock AI, no install or working-DB migration/seed. Exact inner
commands (run from the canonical root, frontend commands from `frontend`):

```text
manage.py test apps.bots.tests_deletion apps.bots.tests_scenarios apps.ai_core.tests_agent_runtime -v 1
manage.py test apps.bots.tests_deletion -v 1
manage.py test apps.ai_core apps.bots apps.conversations.tests_ai_confirmation apps.automations -v 1
manage.py check
manage.py makemigrations --check --dry-run
node --test scripts/tests/sidebar-navigation-policy.test.mjs scripts/tests/action-color-policy.test.mjs
npm run build
npm run check:bundle
```

- Focused gate exposed a lifecycle helper replacing the caller's Bot instance;
  fixed by refreshing the locked existing instance, preserving activation behavior.
  Test fixture emails were made unique; manager denial correctly accepts the
  existing scoped 404 as well as 403. Deletion follow-up: 4 PASS before dependent UI.
- Final affected/dependent backend: **287 PASS**, system check and migration drift
  PASS (`backend-final.log`). No migration is needed. Tests prove history retention,
  scoped/role denial, stopped jobs/commands/runs, replacement, protected marker,
  stale-instance reactivation denial, idempotent service and audit-failure rollback.
- Frontend policy: **13 PASS**. Build/type/i18n (5256 keys)/app/widget/bundle PASS
  (`build-2.log`). Initial build caught a missing explicit React ref initializer.
- Browser core workflow: desktop/mobile PASS (`browser-desktop-2.log`,
  `browser-mobile-2.log`): icon-only help, right-side/inline placement, mouse-selected
  CRM, server response and DB-backed API readback, reload retaining CRM tabs, delete
  cancel, injected 503 preserving draft, retry/204/navigation and new CRM creation.
  Initial mobile run exposed a synthetic mouse-leave closing focused touch help;
  fixed. The first desktop run was stopped after identifying a wrong textbox label
  in the test; the corrected exact existing label passed.
- Keyboard and RU/KK/EN confirmation: desktop/mobile PASS, for **4 final browser
  cases total** including the core flow. Evidence: `browser-keyboard-desktop-3.log`,
  `browser-keyboard-mobile-2.log`; locale screenshots under `keyboard-desktop` and
  `keyboard-mobile`. Two parallel attempts hit webServer startup timeout with about 300 MB free
  RAM; continued sequentially. An extra immediate reload in the locale test
  interrupted refresh-token rotation and was removed: each locale now makes one
  normal navigation and waits for the actual UI. Shared backend behavior from the
  prior task was not reimplemented.

Browser runner:

```powershell
.\.venv\Scripts\python.exe output/ai-agent-followup-20261005/verify-ui.py <desktop-chromium|mobile-chromium> ai-agent-followup.spec.ts
```

It invokes `npx playwright test e2e/ai-agent-followup.spec.ts --project=<project>
--reporter=line` in its own isolated runtime. Keyboard follow-up uses `--grep keyboard`.
Desktop/mobile screenshots were visually inspected. Working/index diff hygiene,
new files and changed documentation references passed review at closure; there is
no committed range for this uncommitted task. Full E2E and live external providers
were not run: the scope is these regressions and agent retirement.

## Publication

### Deletion-result investigation, 05.10 18:04 UTC

**Resolved after recurrence, 18:26 UTC:** HTTP readback from the running Vite/5173
proved it returned a stale transformed `useAIAgentEditorDrafts.ts` without
`discardDeletedAgent`, while the served page already called that function in
`onDeleted`. This causes a runtime exception after successful DELETE 204, before
list cache update/navigation, matching the symptom. The disk source already had
the function, explaining why isolated servers passed and ordinary reload failed.
Saved exact before/after responses under `output/ai-agent-delete-result-20261005`
as `*-served.js` and `*-fresh.js` (ignored local evidence).

Verified the owned canonical Vite PID14568 command line and restarted only it,
same root/5173, new PID8224. Fresh HTTP readback proves the returned hook now has
both `discardDeletedAgent` and `deletedAgentId`; the page caller is consistent.
Reloaded the owner's already-empty agent page. No merchant records were changed.
No application code changed, so the direct/proxy tests below remain applicable.
No extra build/backend/full suite required for refreshing a stale dev process.
The earlier unresolved checkpoint below is retained as the diagnostic trail.

Owner observed a generic error after successful deletion, followed by disappearance
on reload. Canonical backend logs confirm DELETE 204. Application files match the
previous closure's SHA-256 manifest; no conflicting writer or source drift found.
Browser console contained no retained error when inspected. No merchant data was
created/deleted by this investigation and no application fix is claimed.

Added `deleting legacy inbox agents updates the list without a false error` to
`frontend/e2e/ai-agent-followup.spec.ts`: two agents without profiles, sequential
confirmed deletion, immediate list removal/navigation and absence of alerts.
Both isolated runs PASS:

```text
.venv/Scripts/python.exe output/ai-agent-followup-20261005/verify-ui.py desktop-chromium ai-agent-followup.spec.ts --grep "legacy inbox"
.venv/Scripts/python.exe output/ai-agent-delete-result-20261005/verify-proxy.py
```

The second runner uses the same isolated environment with `VITE_API_URL` empty,
so browser requests pass through Vite's same-origin proxy to the disposable backend.
Logs: `output/ai-agent-delete-result-20261005/reproduce.log` and `proxy.log`.
No install, backend code change, build or full E2E: only regression coverage/docs
changed. Working/index hygiene passed. Branch/HEAD remain codex/ui-testing-toolkit
at 9ff3662, no committed range. Previous dependency CI blocks publication.
The reported error remains open pending recurrence/exception evidence; asked owner
whether it repeats after full reload. A stale browser module is only a hypothesis.

Changes are local. No commit/push because the prior dependency CI failure for
`9ff3662` remains unresolved (run 37312854122; braces/DOMPurify). This task does not
authorize dependency updates or publication of other WIP. Local passing checks do
not turn that CI green. Owner can refresh the existing local page, create a CRM
agent, and remove the earlier trial agents using the new footer action.
