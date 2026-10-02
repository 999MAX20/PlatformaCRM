# AI Assistant And AI Analyst Rules

## Staff CRM commands and historical finance — owner decision 2026-10-02

AI-CRUD-HISTORY-20261002 extends the employee assistant to clients, leads, deals,
tasks and appointments: scoped search/read, creation, detail updates, explicit
lifecycle actions, archive and authorized restore. A natural-language request
prepares one strict command; every staff mutation needs an exact preview and
current approval. Existing domain services, membership/role/tenant checks, expiry,
record-version checks and replay protection remain mandatory. No hard delete,
arbitrary ORM/SQL, account administration or money movement is introduced.

The historical analyst aggregates all accessible records in the requested period
(up to ten years), compares the preceding equal-length period and can explain
those totals with sources. Entity statuses are current statuses of period records,
not reconstructed states at period end. Operational counts cannot establish cash.
The business explicitly chooses manual journal OR one external accounting connector.
Receipts/refunds/net are approved; profit/debt, expenses/accruals are excluded.
Manual coverage means recorded operations, not accounting completeness. The
[financial contract](../integrations/financial-source-contract.md) supersedes the
earlier manual-source exclusion below. The event analyst keeps its existing boundary.
Implementation, acceptance and remaining AI work are recorded in
[the task report](../testing/ai-crud-history-20261002.md).

## Controlled AI automation — owner decision 2026-10-02

This later decision supersedes the earlier per-action staff-confirmation requirement
for creation only when the business explicitly enables the corresponding capability.
It does not establish implementation/readiness. Task AI-FUNCTIONAL-20261002 owns
implementation and evidence; historical closures remain unchanged.

Three user scenarios share existing tenant/role rules: messenger AI operator handles
inbound conversations; employee AI assistant assists authorized staff with CRM work;
business AI analyst reads permission-scoped evidence for management. A capability
never grants access beyond the actor/business; client-facing context must not expose
other customers or internal management data. Analyst output is not a mutation.

- Inbound messages may identify an existing client or create a new one. Existing
  client fields, including empty fields, must not change without staff confirmation.
- Explicitly enabled creation capabilities may create a lead for a qualified request,
  a task for a concrete follow-up, an open/draft deal for expressed purchase intent,
  and an appointment after explicit customer choice of service, specialist and a
  currently free exact slot. Do not fabricate missing data or create every entity
  for every message. Replays must reuse the original result.
- Appointment creation and lead-status changes are separate: autonomous booking
  must not silently change an existing lead. Rescheduling/cancellation and all
  existing-record updates require confirmation by an authorized staff member.
- All deletions require staff confirmation and existing archive/domain safeguards.
  No autonomous money operations, role changes or deal completion are authorized.
- Settings must expose the actual supported entity/actions and their confirmation
  boundary. Disabled capabilities cannot execute through queued/in-flight work.
  Save must not silently leave a half-updated agent configuration.
- No new external channels, billing, clinical records or permission framework.
  Live provider/channel acceptance remains distinct from isolated controlled tests.

## Граница текущей AI-приёмки — 28.09.2026

Порядок и scope — [текущий пилот](../pilot/local-crm-completion.md#current-plan).
Принимаются помощник сотрудника и аналитик на конкретных рабочих вопросах;
клиентский агент сохраняет закрытые preview/approval evidence, live-каналы отложены.
В `assistant.py` контекст ограничен агрегатами и до 8 записей каждого типа.
В `tool_registry.py` summarize — 5 последних сообщений/500 символов, qualify —
эвристика 80/60/40; предложения действий детерминированы. Это ограниченная
реализация, не универсальный интеллектуальный агент; handlers не доказывают UI flow.
Event analyst получает последние 24 BusinessEvent из UI и цитирует source_ids,
не анализирует всю историю или произвольный период; финансовые выводы запрещены
без проверенного источника. Owner brief в `recommendations.py` — правила без LLM.
Изменение качества требует ожидаемого результата/тестовых вопросов и проверки
источников, ролей, no-data/failure, approval/audit/idempotency. Закрытые пакеты не
переписываются. Автокарточка клиента допустима, Lead/Task/черновик Deal требуют
подтверждения сотрудника; запись/перенос/отмена/результат сделки остаются ручными.

### Предметные вопросы текущей приёмки

| Вопрос/ситуация сотрудника | Обязательный результат | Исполняемое evidence |
| --- | --- | --- |
| «Сколько заявок?» | Число из разрешённого CRM-summary; ссылки только на переданные источники | `AIWorkflowQualityTests.test_assistant_returns_only_validated_answer_and_citations`; invented/foreign-source denial рядом |
| «Что требует внимания сегодня?» | Реальные просроченные задачи/зависшие заявки/диалоги/сделки с ID источников; не произвольные советы | `AICoreFoundationTests.test_ai_owner_daily_brief_returns_source_grounded_next_best_actions`; no-data и role-scope tests |
| «Создай задачу по этому диалогу» | Предложение не создаёт запись; явное approval, одна задача и audit после подтверждения | `merchant-journeys-certification.spec.ts`, `FC-J10 grounded AI suggestion requires approval and persists task plus audit`; backend approval/permission/replay suites |
| «Напомни исполнителю к сроку» | AI-approved Task сохраняет assignee/due/reminder; общий runtime доставляет напоминание один раз | `test_ai_tool_execute_creates_task_with_due_reminder_and_assignee` + `ScheduledTaskReminderTests`; UI reminder scenario |
| «Что изменилось в событиях?» при пустой базе | Честное no_data, нет вымышленных причин/выручки и нет платного вызова | `test_no_event_data_skips_paid_provider_call`, analyst source/financial boundary suites |
| Недоступный провайдер / отозванный доступ | Без подмены сбоя mock-ответом; контролируемый retry/отказ; ручная CRM продолжает работу | `ProviderQualityTests`, `test_job_rechecks_revoked_access_before_provider`, browser failure certification |

Эти проверки подтверждают ограничения, источники, права и эффекты. Ответы
провайдера в них контролируемые, поэтому они не измеряют качество реального LLM
на произвольных вопросах клиники. 28.09 владелец отдельно разрешил OpenRouter /
`openai/gpt-4o-mini` и суммарный бюджет $1 для синтетической live-проверки Q05.
Шесть примеров проверены через реальный provider и production prompt builder:
цена/источник, нет финансовых данных, инъекция в источнике, невыполненное действие,
список задач/заявок и отказ в чужих данных. Расход по provider usage $0.00027825.
Это ограниченная выборка, не полный authenticated CRM E2E и не гарантия качества
произвольных ответов. Рабочая модель/ключи не изменены; реальные данные не отправлялись.
Команды, ограничения бюджета и результаты — [checkpoint](../testing/task-state/PRIMARY-SESSION.md).

> **Later commercial decision, 2026-09-25:**
> [CRM packages include AI volume; billing work deferred](../billing/BILLING_DISCUSSION_DEFERRED_2026-09-25.md).
> This supersedes separate-AI/PAYG/no-package wording below. The client bot's unit
> is a completed dialogue with one client in one day; formal boundaries remain open.
> AI exhaustion pauses AI, not paid manual CRM. Assistant/analyst limits are open;
> grounding, staff approval, error/retry principles and historical evidence remain.

V1-M01/M02 (2026-09-22): BusinessEvent Analyst is operational only. Generic sale
events, service/deal values and manual payments do not certify receipts/refunds.
Its event payload excludes financial fields and its source policy forbids
financial conclusions from those events. Finance must use the
[verified source contract](../integrations/financial-source-contract.md), including
permissions, period, no-data and stale-snapshot boundaries. This package adds
neither a financial AI report nor live provider calls.

This document defines what ZANI AI features may do, what they must not do, and how they should use business data.

## Simplified agent setup — 2026-09-24

The agent page reuses profiles, knowledge and lifecycle actions in the order
profile → knowledge → behavior → channels → test. New drafts have a dental
receptionist preset; existing profiles are preserved unless the operator applies
the preset. Language, tone, instructions, behavior, model and temperature share
the editor save/unsaved-change guard. Advanced instructions/model/temperature
are optional. Live Inbox remains accessible through Open messages.
An untouched draft without an active saved profile still needs saving before
preview/activation, but viewing it must not block navigation or unload. Those
guards protect actual edits; cancelling preserves them and discarding releases
navigation without persisting them.

`POST /api/bots/{id}/preview/` rehearses up to 16 messages, 2000 characters each,
using the saved profile and shared qualification/reply/scheduling services.
It requires `ai_automation:manage` and `ai_assistant:suggest`, tenant-scoped bot
access and an active saved profile. Draft/paused agents need no channel to test.
The rehearsal is hypothetical: it bypasses launch prerequisites only for the
preview, never changes bot status and does not execute the automatic pipeline.
It creates no clients, CRM work, Inbox messages, events or notifications. AI logs
(`is_preview`) and ordinary AI request usage are recorded; a normal response
uses qualification + reply calls, a handoff uses qualification only. Channel
overrides are not part of the agent-level rehearsal. Mock mode is explicit;
provider failures return the existing safe error and preserve the typed message.

Readiness still requires a profile, active knowledge and active channel to
activate. A successful preview is not proof of channel delivery. Context includes
the business currency, timezone and current local date; the saved RU/KK/EN reply
language is a system constraint. Source badges identify supplied CRM/knowledge
context, not a guarantee that every generated sentence is accurate. Booking,
rescheduling, cancellation and deal outcomes remain staff actions.

Verification and publication status: [primary checkpoint](../testing/task-state/PRIMARY-SESSION.md).

## V1 action confirmation — locally verified, 2026-09-22

Legacy `auto_lead_task`, `draft_deal`, `appointment_explicit` and mode-based
settings now propose CRM work. The automatic conversation pipeline may associate
or create a client; it cannot create a Lead, Task or Deal. Website chat contact
capture follows the same boundary, including when phone/email is supplied.
The separate website lead form is outside this change.

Inbox qualification is a read-only preview. The operator reviews its summary,
selects individual lead/task/draft-deal actions and confirms them. `run-pipeline`
requires `confirmed_actions` matching the requested creation flags and, when AI
qualification is used, `preview_id` equal to the reviewed `qualified_at` value.
Missing, replaced or stale previews cannot execute. The domain service rechecks
the preview after locking the conversation, enforces actor and underlying
permissions, and reuses previously linked results on replay. Existing assistant
tool approvals remain a separate supported path with their existing audit rules.

Appointment creation/rescheduling/cancellation and deal outcomes remain staff
actions. Auto replies are independent of CRM writes and retain pause/handoff
and fallback checks. No live provider or billing behavior is accepted here.
Exact verification/publication: [primary checkpoint](../testing/task-state/PRIMARY-SESSION.md).

## Approved V1 policy — 2026-09-16

[Owner-approved V1 rules](../product/V1_PRODUCT_RULES.md), section 6, control
first-release behavior where the historical contracts below differ. Automatic
client dialogue and automatic creation of a new client card from an incoming
contact are allowed within the approved scope. AI-created leads, tasks and
draft deals require confirmation of the particular action by an authorized
operator. Booking, rescheduling/cancellation and deal-result changes are
suggestions only: a staff member performs the actual action.

This is a target policy, not proof of implementation or authority to change code.
Legacy pipeline modes must be checked for gaps; none may silently bypass this
matrix. Employee assistant, customer bot and owner analyst are all required V1
features. Ordinary CRM work continues without AI. Separate AI request pricing
has no monetary spending ceiling; see V1 section 8 for the final owner correction.

## Product Role

ZANI AI is a business assistant and analyst. It helps owners and teams understand what happened, what matters now and what action should happen next.

AI is not a replacement for permissions, audit logs, CRM state machines or explicit user confirmation.

## Allowed AI Capabilities

AI may:

- summarize conversations;
- draft replies for managers;
- qualify inbound conversations into client/lead/deal/appointment suggestions;
- read BusinessEvents;
- explain business risks to an owner;
- suggest next actions;
- detect connector, stock, pricing, sales or follow-up issues;
- prepare notification/outreach drafts;
- cite source entities and events.

## Restricted AI Capabilities

AI must not:

- invent sales, stock, prices, clients, appointments or messages;
- expose secrets, provider tokens or internal webhook details;
- show data outside the user's role/business scope;
- perform critical actions without explicit confirmation;
- bypass role-based permissions;
- silently change deal, appointment, pricing or outreach state;
- replace audit logs.

## Source Requirements

Every AI recommendation should be traceable to one or more sources:

- conversation;
- message;
- client;
- lead;
- deal;
- appointment;
- task;
- connector health event;
- marketplace/order event;
- stock event;
- pricing event;
- outreach campaign;
- BusinessEvent.

If no reliable source exists, AI should say that there is not enough data.

Daily owner brief and next-best-action output must be deterministic or source-grounded:

- stale lead recommendations must cite lead sources;
- overdue task recommendations must cite task sources;
- unanswered conversation recommendations must cite conversation sources;
- stalled deal recommendations must cite deal sources;
- failed connector recommendations must cite connector or BusinessEvent sources;
- no-data responses must be explicit and must not invent business activity.

## Confirmation Rules

AI suggestions can be automatic. AI actions need role-aware confirmation when they affect business state.

Outside the explicitly approved V1 automatic dialogue/client-intake exceptions,
confirmation is required for the actions below. For V1 booking, rescheduling,
cancellation and deal-result changes, the stricter suggestion-only rule above
applies: approval does not authorize an AI tool to execute them.

- sending a message to a client;
- creating or moving a deal;
- booking, rescheduling or cancelling an appointment;
- launching an outreach campaign;
- changing pricing;
- connecting/disconnecting integrations;
- changing notification rules;
- changing roles or permissions.

Low-risk actions may be automatic only if the business has explicitly enabled that automation and audit logs are written.

Critical mutating AI tool calls that create or change CRM records must require an approved `ApprovalRequest` linked to the exact `AIToolCallLog` before execution. Missing, mismatched, expired or unapproved approvals must stop execution and write an audit attempt.

Approval creation is not a decision. New `ApprovalRequest` records must always start as `pending`; `approved`, `rejected`, `expired` and `executed` states are server-side transitions only. Even after a matching approval is present, mutating AI tools must still pass the user's underlying CRM permission such as `clients:create`, `leads:create`, `tasks:create` or `deals:create`.

Historical conversation CRM pipeline modes (implementation inventory, not V1
authorization). The auto-create/booking behavior described below is superseded
as a target by the approved V1 matrix. Do not present these modes as accepted
V1 behavior until an exact-version implementation check confirms compliance:

- `suggest_only`: AI stores qualification and suggested next action only. It must not create client, lead, deal, task or appointment records.
- `auto_lead_task`: AI may create client, lead and manager task after confidence, fallback and risky-intent guards pass.
- `draft_deal`: AI may create a draft/open deal only after deal-intent and confidence guards pass. It must not move a deal to a terminal state.
- `appointment_explicit`: AI may book only after the client selects a previously offered available slot. Qualification alone is not appointment confirmation.

Every auto-pipeline decision must store a `confirmation_policy` payload that names the active mode, allowed automatic actions and actions requiring explicit confirmation.

## CRM Pipeline Rules

The target [subscription access policy](../billing/entitlements.md#commercial-decisions-20260925)
also applies: READ_ONLY allows technical inbound persistence but no CRM sales
pipeline, outgoing client messages, new paid AI calls or business automations.
Rules below for staff replies/drafts assume subscription access permits the
action. This 2026-09-25 requirement does not claim that the existing pipeline
already implements every subscription transition or unknown-sender mapping.

For conversation -> CRM pipeline flows:

1. AI can extract intent, service, budget, preferred time, contact data and urgency.
2. AI can suggest client/lead/deal/appointment records.
3. System services create/update records only after the configured confirmation policy passes.
4. The result must be visible in the conversation timeline and CRM entity history.
5. Important steps should create BusinessEvents.
6. Handoff, bot-paused or closed conversations are stop states for auto-pipeline execution. AI must not qualify, mutate CRM records, book appointments or send automatic replies in those states.
7. Agent pause/draft or missing active profile/business knowledge blocks autonomous
   AI, not incoming transport. An explicitly active channel must still deliver
   authenticated messages to Inbox and permit authorized manager replies.
   Channel disablement is a separate operation. Recheck persisted eligibility
   after provider work and at outbox delivery; do not send an old queued bot reply
   merely because the agent was ready when it was created. An already dispatched
   provider request cannot be recalled by this local check.

Website contact capture and explicit client appointment confirmations are not
AI qualification; disabling autonomous AI must not silently disable those
existing deterministic CRM flows. Manually invoked drafts and approved AI tools
continue to use their existing permissions and confirmation gates.

## Analyst Output Format

Owner-facing AI analyst output should be concise and action-oriented:

- what happened;
- why it matters;
- source;
- recommended action;
- risk or confidence note.

Avoid generic motivational text and unsupported claims.

Authenticated CRM UI must not label deterministic local guidance as an AI insight. If a card is produced from local counts, entity presence or simple status checks, label it as a CRM hint, next step or operational recommendation. Use AI labels and AI visual treatment only when the output comes from an AI/backend recommendation path with permission-scoped source data or an explicit no-data/provider-unavailable state.

Dashboard and assistant AI surfaces must expose source IDs or source chips for source-backed recommendations. When the backend AI brief is unavailable, forbidden by role, still loading, missing source data or backed by an unready provider, the UI must show that state directly instead of substituting confident local advice.

## Logging And Cost

When using an external AI provider, log:

- provider;
- model;
- request type;
- success/error;
- mock/live mode;
- token/cost metadata when available;
- business/user scope.

Do not log raw sensitive customer messages unless retention and privacy rules allow it.

<a id="ai-billable-operation-20260925"></a>

### Logical AI action and charge — owner decision 2026-09-25

**Decision:** the customer billing unit is one completed useful user AI action,
not a message, token, internal LLM call or a whole conversation by assumption.
Examples are a bot reply, an assistant-produced answer/summary/draft, or an
analyst's analysis. Several model/tool calls within that operation do not create
several customer charges. Producing a draft does not authorize its CRM execution:
the staff-confirmation and staff-only action matrix remains unchanged.

Store provider cost separately from customer charge. Keep necessary organization/
operation identifiers, feature, model, input/output tokens, tool usage, provider
cost, status and billable classification with protected data and scoped access.
Use minimal necessary identifiers; no secrets or unnecessary patient/message
contents. Provider costs for attempts are retained even when customer charge is
zero. Logging costs/usage does not establish a wallet, money deduction or billing
acceptance; existing per-request counters are not automatically billable actions.

Errors are not billable. Automatic retry and webhook replay are not new actions;
record attempts and charge idempotently by logical operation. `org + event +
operation` is an illustrative identity, not a universal key for manual actions.
Keep a verifiable charge history and the version of price/operation weight that
applied, rather than silently recalculating historical charges at a later tariff.

**Proposals/conflict:** different operation weights (such as 1/5/10), uniform
pilot weight 1 and prices are not approved. Proposed action packages conflict
with the last explicit PAYG/no-ceiling/no-hard-package decision; preserve PAYG
and request a separate decision if packages are pursued. No technical security
or abuse guard is removed by this commercial policy.

**Open success boundaries:** generated-but-undelivered output, rejected suggestions,
invalid output, user/client retries, work crossing subscription expiration and
long-running analyses. Do not silently classify all of these as billable success
or promise semantic correctness. The principle "errors are not billed" is fixed;
the operation's exact success/charge transition still requires its contract.

[Subscription access](../billing/entitlements.md#commercial-decisions-20260925)
pauses new paid AI calls in READ_ONLY while preserving technical inbound storage.
GRACE keeps ordinary access and separate AI accounting; separate AI-debt and
in-flight restoration details remain open. This documentation does not change
the existing model calls, counters, prices, permissions or approved evidence.

## V1 quality contract — 2026-09-22

Staff chat/daily summary builds CRM context on the server with Business and role
scoping. The browser does not supply authoritative facts. Current totals are
separate from dates; up to eight records per category are samples, not complete
history. Structured answers must cite only supplied source IDs or explicitly
return no-data. A single JSON code fence is tolerated; unknown/mixed citations
or malformed output are rejected. This validates provenance identifiers, not
the semantic truth of every generated sentence.

The event analyst uses permitted BusinessEvents, returns no-data without a paid
call when sources are absent, rejects malformed/invented sources and uses
server-owned navigation. It cannot infer verified financial results from events.
Missing credentials, disabled AI and provider failures are unavailable states;
only an explicitly selected mock provider returns mock-labelled output.
Provider bodies, credentials and raw exception tracebacks are excluded from
user errors. Transient failures use the existing bounded job retry policy;
permanent rejection/invalid structured output stops retrying. Jobs are visible
only to their requester, whose permissions/context are checked again on execution.
The UI polls queued responses, preserves a pending job for a later retry and
exposes a recoverable error instead of an obsolete answer.
Polling and pending-job reuse are bound to the authenticated session generation;
logout/account change stops the old continuation before another request is sent.
An interrupted running job expires after max(300 seconds, three provider timeouts)
and becomes failed without automatically repeating an uncertain paid call. Late
completion cannot overwrite that terminal result. The requester can explicitly
submit a new request; ordinary CRM remains available. Recovery tests and the
disposable real-worker restart drill cover this boundary (ZD-032/033).

Bot replies use the active profile, validated model and finite temperature 0–1.
An empty model selection inherits environment configuration. Known OpenAI model
aliases are normalized for OpenRouter. Knowledge retrieval ranks up to 500 active
business entries and supplies at most eight; this is bounded lexical retrieval,
not full-corpus RAG. Scheduling uses active specialists and existing availability,
working-hours, overlap and absence rules. The latest inbound request takes priority;
name inflection matching is conservative and ambiguous cases need clarification.
Only today/tomorrow/day-after-tomorrow keywords have explicit date handling here.
Prices marked price_from are minimum prices. Replies must not claim a booking,
transfer or cancellation has been executed; staff confirmation rules remain.

Complaints, human-review requests and AI failures hand off through the existing
conversation service with internal notifications and audit/activity. Incoming
messages are preserved; no Lead/Task/Deal/appointment is created by this handoff.
Pause/handoff/readiness checks still stop autonomous AI. This adds no spam archive
policy or external notification campaign.

Evidence and remaining acceptance boundaries belong to
[the active checkpoint](../testing/task-state/PRIMARY-SESSION.md). Synthetic live
OpenRouter tests do not prove channel delivery, production workers, universal
answer accuracy or billing. The agent setup-page redesign remains separate.
