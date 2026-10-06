# AI-AGENTS-CERTIFICATION-20261006

## Scope and boundary

Owner requested user-flow certification of the existing AI Agents page, saved
settings and their effects in Inbox, CRM and analytics, plus an assessment of a
future internal business chat. Same registered primary, canonical
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`, base HEAD
`9ff366207e73472cda71ca3b9113ca4f9f305af9`, existing dirty work preserved.
This is local scoped certification, not release or live messenger certification.
No new analytical chat, uploads, exports, roles or business policy were implemented.

Risk/verification plan: reuse existing agent configuration, knowledge, runtime,
permissions and connector layers. Exercise saved values through real local API and
browser flows using isolated databases; check actual provider inputs and four
separately authorized synthetic live requests. Fix bounded reproduced defects;
run focused backend checks after the prompt fix, affected/dependent backend suites,
desktop/mobile flows and final frontend build. No dependency reinstall or full
project E2E gate. Ordinary owner data is excluded from certification fixtures.

## Reproduced defects and changes

1. Website snippet used a relative script path, resolving against a merchant's
   domain. It now uses the application origin and retains the configured API base.
2. New website channels were drafts, but their activation switch was hidden.
   The switch is now available for website channels. Backend permits website
   activation; messenger verification requirements are unchanged.
3. Price instructions unconditionally required Russian `от`, including English
   replies. The prompt now applies minimum-price wording only to `price_from`
   and asks for the selected reply language. Four live samples exposed this;
   post-fix provider-input assertions pass, but no fifth live call was authorized.
4. WhatsApp/Instagram forms marked saved credentials as connected before actual
   verification. Badges now reflect channel status; credentials alone show setup.
5. Telegram's key field lacked an accessible name; it now uses its existing
   translated label as an accessible name.

## Coverage map

| Surface | Evidence |
| --- | --- |
| Creation/navigation | Explicit scenario choice, keyboard/help, separate inbox/CRM tabs, duplicate CRM prevention, legacy redirects and staff route |
| Profiles | Name/blank validation, language, tone, model, temperature, role, main instruction, rules, save/readback/reload/cancel; provider inputs verify runtime effects |
| Knowledge | Own vs explicitly shared sources, empty defaults, search/connect/disconnect, CRUD, whitespace validation, failed save/retry and agent/tenant isolation |
| Inbox actions | Modes, automatic/confirmed creation, appointment/reply flags, confidence/length limits, tools and escalation rules; persistence plus backend pipeline/confirmation tests |
| CRM sources/actions | Source filtering, tool permissions, agent pause, analytical permission, confirmed execution and cancellation; ordinary role checks remain mandatory |
| Channels | Website snippet and activation, Telegram key validation/masking/link, WhatsApp/Instagram synthetic settings/masking/status/link; no external outbound action |
| Test preview | Manual price, booking, complaint and reset; automated preview prompt/context/readiness/error behavior |
| Work/analytics | Agent identity passed to runtime, question/response, source-restricted CRM browser, proposed action review/confirmation, history tables and locale/accessibility coverage |
| Lifecycle/recovery | Pause revokes runtime; deletion/cancel/retry, retained history, no late execution, failed load/save recovery and role denial |

Coverage combines browser execution, manual inspection and backend assertions.
It is not a claim that every provider response or every possible field combination
has been tested live. External OAuth, real Telegram/Meta credentials, webhook
delivery and production widget hosting remain outside this run.

## Results

- Focused prompt/configuration and preview checks: **9 PASS**.
- Completion backend: **393 PASS**, `check` and migration drift **PASS**.
  Includes `apps.ai_core`, `apps.bots`, confirmation, automations, Telegram,
  WhatsApp/Instagram foundation, channel consistency and ownership tests.
- Browser completion: **24 unique checks PASS** (18 desktop, 6 mobile), including
  RU/KK/EN, keyboard and scoped accessibility checks. Superseded/retried runs are
  not added to this total. Mobile profile, provider form and analytical report
  screenshots were visually inspected.
- Frontend `npm run build`: **PASS** (i18n, TypeScript, app and widget).
  `npm run check:bundle`: **PASS**. Built `dist/widget/platformacrm-widget.js`
  exists. Production hosting and merchant-domain execution were not exercised.
- Report links, current working/index diff hygiene and localhost readback: **PASS**.
  Current eight changed source/test files are identified in `source-sha256.json`.
- Four live OpenRouter requests: **4/4 instruction/fact checks PASS**, 3328 total
  tokens, `openai/gpt-4o-mini`, isolated synthetic business/knowledge only.
  ALPHA→BETA instruction changes appeared in both Inbox and CRM replies; CRM
  returned knowledge sources. Inbox English replies exposed the price-wording
  defect above. These samples do not certify general output quality.

Commands and local evidence (ignored `output/ai-agents-certification-20261006`):

```text
.venv/Scripts/python.exe output/ai-agents-certification-20261006/verify-backend.py
# isolated_runtime invokes check, makemigrations --check --dry-run, then:
python manage.py test apps.ai_core apps.bots apps.conversations.tests_ai_confirmation apps.automations apps.integrations.tests.TelegramIntegrationSkeletonTests apps.integrations.tests.WhatsAppIntegrationFoundationTests apps.integrations.tests.InstagramIntegrationFoundationTests apps.integrations.tests_channel_setup_consistency apps.integrations.tests_channel_ownership -v 1
# browser helper creates a fresh isolated environment/database for each invocation:
.venv/Scripts/python.exe output/ai-agent-isolation-20261005/verify-ui.py PROJECT SPEC [--grep FILTER] --output=../output/ai-agents-certification-20261006/RESULT
```

Browser invocations use the helper above; all filenames are under `frontend/e2e`.

| Project | Spec / filter | Result directory / log |
| --- | --- | --- |
| desktop-chromium | ai-agent-settings-certification.spec.ts, initial profile/actions subset | settings-desktop-2 |
| desktop-chromium | ai-agent-settings-certification.spec.ts, `channel forms` | channels-desktop-2 |
| desktop-chromium | ai-agent-settings-certification.spec.ts, `^crm:` extended controls | crm-settings-desktop-2 |
| desktop-chromium | ai-agent-isolation.spec.ts | isolation-desktop |
| desktop-chromium | ai-agent-scenarios.spec.ts; focused `customer creation` retry | ai-agent-scenarios-desktop / creation-retry-desktop |
| desktop-chromium | ai-agents-ux.spec.ts | ai-agents-ux-desktop |
| desktop-chromium | ai-agent-followup.spec.ts | ai-agent-followup-desktop |
| desktop-chromium | ai-functional-settings.spec.ts | ai-functional-settings-desktop |
| mobile-chromium | ai-agent-settings-certification.spec.ts | settings-mobile |
| mobile-chromium | ai-agent-scenarios.spec.ts, `creation requires purpose` | crm-mobile |
| desktop-chromium | ai-agent-analytics-certification.spec.ts | analytics-desktop-2 |
| mobile-chromium | ai-agent-analytics-certification.spec.ts | analytics-mobile |

Profile/settings checks run against real persisted local API values, not route
stubs. Controlled failures and planner responses are identified inside the specs.

The initial combined browser run accumulated agents above the five-agent fixture
plan limit; files were rerun against independent databases. One scenario failed
at `browserContext.newPage` before its body; its focused retry is recorded
separately. Initial blank-name test incorrectly clicked the intentionally disabled
Save button; corrected to assert disabled state and unchanged persistence.
Initial channel failure exposed the missing website activation control.
An added CRM test initially expected the Analytics tab to disappear when disabled;
the UI deliberately retains navigation and the backend denies analytical runtime.
The corrected test asserts persisted disabled state and HTTP403, then reenables it.
The initial analytical lookup test assumed Clients was the default CRM section;
the actual first section was Appointments. The test now explicitly selects Clients
and passes on both viewports. No application assertion or permission was weakened.
All failed logs are retained; none is presented as a passing run.

Final build/log commands (in `frontend`): `npm run build`, `npm run check:bundle`.
Logs: `build-final.log`, `check-bundle-final.log`. Final artifact/readback helper:
`.venv/Scripts/python.exe output/ai-agents-certification-20261006/verify-artifacts.py`.

## Working database operation

Owner explicitly accepted backup plus only `ai_core.0006`. Applied on 06.10 after
checking the migration plan. Backup:
`output/ai-agents-certification-20261006/working-before-20261006T121116Z.sqlite3`.
Original rows/columns in 113 tables are unchanged; zero implicit knowledge links,
SQLite integrity/foreign-key checks pass. Existing two knowledge records remain
shared. No reset/seed/deletion. Evidence: `working-migration.log`.
Owned canonical servers refreshed after fixes: backend parent9140/child8592 on8000,
frontend13772 on5173. Health and frontend HTTP200; served modules contain absolute
widget URL, website activation and Telegram accessible name. Readback is recorded
in `local-readback.json`. Disposable test servers completed and were stopped by
their isolated runners; no other project's processes were stopped.

## Assessment of internal business chat

The proposed separate internal chat matches the distinction between customer
messaging and business analysis. Today `CRMAgentRuntime` has one question and its
latest response; `AIHistoryPanel` provides a selected-period report and explanation.
There is no persistent conversational workspace, streaming, attachment analysis or
report export in this flow. The general CRM prompt uses bounded entity samples;
it cannot establish arbitrary employee/month analysis merely from a new prompt.
The history API already calculates period metrics independently of the model,
which is useful infrastructure to reuse.

Proposed first result, requiring a separate implementation scope: an AI analyst
workspace in Analytics with saved conversations, follow-up context and explicit
business/period/person scope. Answers should cite source records, show data
freshness/coverage and separate observed metrics from interpretations. Deterministic
server queries should calculate totals and comparisons; the model explains them.
Existing entity permissions, agent source/tool settings and explicit confirmation
for writes must apply to every turn. Employee names need disambiguation; incomplete
work records must not become unsupported performance judgments.

Do not remove all metrics/tables/period controls: they provide immediate visibility
and a way to verify an answer without composing prompts. A simple period selector
and optional employee scope can coexist with conversational requests. Empty-state
suggestions should be actionable business questions backed by supported data.
Uploads and Excel/PDF/Word exports can follow once the same report snapshot and
source traceability support both the on-screen answer and the exported document.

## Publication

Changes remain local/uncommitted. Existing failed dependency CI 37312854122 on
9ff3662 (braces/DOMPurify) blocks publication. No dependency work, push, deployment
or full-release acceptance is claimed here.
GitHub readback on 06.10 confirms backend job success and frontend job failure
specifically at `Audit moderate-severity frontend dependencies`; its build and
bundle steps passed. This is prior-commit CI, not CI for the current dirty snapshot.
