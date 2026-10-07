# AI-CRUD-HISTORY-20261002

Owner request: complete core CRM CRUD, historical/financial analytics and identify
remaining AI stages. Owner decisions: select manual CRM journal or one external
accounting source; receipts/refunds/net only; no profit/debt or expenses/accruals.
This revises the manual-source exclusion of 22 September, not ledger invariants.

Canonical source: `C:/Users/user/Desktop/PlatformaCRM`, branch
`codex/ui-testing-toolkit`, base `c48b4e1007dd6a2fbbd296d8a1c82650e48e4dd0`.
Primary owner and compact verification plan are in the selected
[checkpoint](task-state/PRIMARY-SESSION.md). No alternate source tree or other writer.

## Result and boundaries

| Area | Implemented behavior |
| --- | --- |
| Staff CRUD | Clients, leads, deals, tasks, appointments: paginated scoped search/read, create, validated detail update, archive and administrator restore |
| Lifecycle | Lead start/contact/close/lose/reopen/assign; deal stage/win/lose/reopen/assign; task start/complete/cancel/reopen/assign; appointment confirm/complete/cancel/no-show/reschedule |
| Confirmation | Natural-language request prepares one command, visible before/after, explicit confirmation, exact approval fingerprint and expiry, current actor/approver permissions, stale target rejection, atomic rollback and replay |
| Source and rights | Existing active membership, Business isolation, OWN/TEAM selectors and sensitive-field rules; saved assistant source/tool switches apply at read, proposal and execution |
| Finance | Business chooses manual journal or a particular finance connector; never auto-selects or adds sources together; receipts/refunds/net use exact Decimal amounts and business timezone |
| History | Entire selected period, including archive, up to ten years; equal-length previous period; manual daily/monthly series; counts use appointment start time or entity creation time |
| AI explanation | Grounded report sent to existing provider, source citations validated; unavailable/no-data remains explicit; source/access/data changes discard an in-flight answer |
| UI | Reachable assistant search/request/review/confirmation/history panels; financial source in business settings; RU/KK/EN; existing UI/API layers reused |

This is a registry for the five core CRM entities, not arbitrary database access or
all administrative entities. Destructive deletion means domain archive. Money
movement, permissions, payroll, bulk commands and autonomous unconfirmed staff
mutations are not added. Natural-language interpretation needs a real configured
provider; mock mode returns an explicit unavailable state for command planning.
Reference lists sent to the model are bounded (50 core related records; up to 100
services/resources/members/stages); the search endpoint itself is paginated over
the full permitted scope. It is not an unlimited context or RAG claim.

Manual finance covers recorded journal operations, including a valid zero when
there are none. It does not certify complete accounting. Profit/debt remain
unavailable as requested. Current status aggregates do not reconstruct historical
state at period end. External reader registry remains empty: a source selector,
connected badge or imported event does not create a verified financial integration.

Migration `businesses.0011_financial_analysis_source` adds two Business fields;
existing businesses default to external/no selection, an explicit no-source state.
No new environment variables. Isolated migrations are exercised by each test run.
Working database application requires the separately requested local approval.
No external messages, deployment or new paid-provider calls in this task.

## Verification evidence

All commands below run from the canonical folder with existing dependencies.
The local helper `output/ai-functional-20261002/verify.py` delegates environment
creation to `scripts.codex_verify.isolated_runtime`: disposable SQLite/media,
isolated loopback ports, locmem/eager services, no real provider calls. Logs are
under `output/ai-crud-history-20261002`; these ignored artifacts are local evidence.
No full-project/release-candidate certification is claimed.

Command prefix: `.venv/Scripts/python.exe output/ai-functional-20261002/verify.py`.

| Command suffix / log | Result and scope |
| --- | --- |
| `backend apps.ai_core.tests_crm_tools apps.ai_core.tests_crm_planner` / crm-permissions-final | 20 PASS before later approval atomicity/read-redaction refinement |
| `backend apps.analytics.tests_manual_finance apps.analytics.tests_financial_sources apps.ai_core.tests_history` / finance-history-selected | 33 PASS: exact totals, period boundaries, currencies, source selection, role/tenant, full-history aggregation |
| `backend apps.ai_core.tests_history_answers` / history-answers | 4 PASS: report grounding, unknown source rejection, in-flight source change, no-data/provider failure |
| `backend apps.ai_core apps.analytics apps.clients.tests apps.leads.tests apps.crm.tests apps.tasks.tests apps.scheduling.tests apps.businesses.tests` / backend-dependent | 268 run: 266 PASS, one nonexistent leads module label and one superseded auto-source expectation; original log remains FAILED |
| `backend apps.analytics.tests.OwnerDashboardAnalyticsTests.test_owner_dashboard_uses_sales_events_for_business_pulse apps.leads.tests_crm_light apps.clients.tests_archive_dependencies apps.tasks.tests_reminders apps.businesses.tests_access apps.businesses.tests_member_deactivation apps.scheduling.tests_specialist_schedule` / backend-dependent-corrected | 113 PASS; fixes the label, checks explicit no-source expectation and affected dependent domain/access services |
| `backend apps.ai_core.tests_crm_tools` / crm-scope-final | 18 PASS on final command code: all five entities, approval/replay/rollback, busy appointment recheck, stale target, OWN scope and sensitive notes |
| `backend apps.ai_core.tests_crm_tools apps.ai_core.tests_crm_planner` / crm-final | 23 PASS after final preview minimization/requester guard: errors do not disclose another employee's command; unchanged domain/dependent evidence reused |
| `browser ai-crm-history.spec.ts --project=desktop-chromium --project=mobile-chromium` / browser-corrected | Four PASS: persisted financial selection/totals and stale-target refusal; two failures were exact-label locator after textarea rerender |
| Same browser command plus `--grep 'AI CRM search'` / browser-command-final | Two PASS: provider error preserves draft, recovery, exact preview, no write before confirmation, one real API mutation |
| Same browser command plus `--grep keyboard` / browser-locale-labels-final | Two PASS covering RU/KK/EN and keyboard focus, including translated entity and financial labels after fixing fallback override |
| Same browser selection `--grep 'financial source'` / browser-finance-artifacts, browser-finance-layout | Two desktop/mobile PASS plus focused mobile viewport-width PASS; screenshots visually inspected, no horizontal document overflow |
| `build`, `bundle`, `checks` / build-final, bundle-final, checks-completion | PASS: 5209 i18n keys, types/app/widget build, bundle budget, Django system check and migration drift |

Earlier failed iterations retained: invalid RolePermission fixture field, then
missing explicit deny allowed preset fallback; corrected by a real deny fixture.
Browser fixtures initially used a broad search locator and incorrect payments
route; corrected to scoped panel and `client-payments`. No business assertion was
weakened. Provider planning in browser tests is controlled output; writes, approvals,
permissions, source settings, ledger and report queries use the isolated real API.
No new live LLM semantic-quality or PostgreSQL concurrency certification is implied.

Locale iteration exposed a real dictionary-order issue: RU fallback overwrote new
EN/KK entries and reused financial/entity labels. Relevant translated overrides
were moved after fallback; final runtime locale/keyboard tests and build passed.
The failed locale log remains failed; final evidence is explicitly separate.

## Remaining AI work

1. **Clinical semantic acceptance:** real employee questions across all three AI
   directions, ambiguous names/dates, multilingual requests, correction/escalation
   thresholds and individual bot knowledge (V1-O05/Q04/Q05). This task's deterministic
   tests prove validation/effects; the earlier small live samples do not certify the
   new planner's accuracy across arbitrary instructions.
2. **Knowledge retrieval at scale:** bounded knowledge/reference context exists;
   indexed retrieval/RAG completeness and quality are not proven by these changes.
3. **Live external channels and recovery:** actual provider delivery, revoked tokens,
   queue/worker restart and target PostgreSQL races need their own target acceptance.
   Website/email mocks and local eager checks cannot certify live exchange.
4. **Real external financial reader:** choose and implement an accounting connector,
   prove full-period reconciliation, pagination/retries, stale snapshot recovery and
   multi-currency contract. The production verified-reader registry is still empty.
5. **Commercial AI accounting:** package with included AI, dialogue unit, assistant/
   analyst limits and error/retry charging remain under the owner's deferred billing
   decision. Do not revive older separate-AI/PAYG rules or invent prices.
6. **Target operational and clinic acceptance:** authorized deployment/migrations,
   environment/worker recovery, screen-reader/manual clinical workday acceptance.
   Local scoped PASS and normal Git publication do not close those gates.

Sources of these remaining boundaries: [pilot plan](../pilot/local-crm-completion.md),
[V1 rules](../product/V1_PRODUCT_RULES.md),
[financial source contract](../integrations/financial-source-contract.md),
[billing decision](../billing/BILLING_DISCUSSION_DEFERRED_2026-09-25.md).
This inventory does not authorize new phases or reopen historical closures.

## Publication receipt

Code commit `708d0cc9fe2cb325052e14b9401ed7282f081952` on
`codex/ui-testing-toolkit`: 46 reviewed task-owned files, no working DB/secrets/
ignored test artifacts. Working/index/new-file review and committed-range static
gate passed against base c48b4e1. Normal push `HEAD:main` succeeded; remote SHA
matched exactly. [Push CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/37012604357)
was IN_PROGRESS at receipt time. This is not CI success or deployment acceptance.
The documentation receipt's own SHA/CI is reported in Git history/final response.
