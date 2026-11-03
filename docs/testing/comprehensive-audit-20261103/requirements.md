# CRM requirements and cross-contract audit — 2026-11-04

Scope: source/contract mapping joined to the completed isolated runtime audit. CRM HEAD `0b3348e1ab31121a106badbde830b496ec477aac` plus preserved WIP. No application changes, working migrations or provider sends. [Runtime matrix](tests.md) and [backend results](backend.md) identify actual tests/results and limits; named historical evidence alone does not assert a fresh PASS. The full backend run remains failed (4 assertions), with separate PG50 PASS and scoped recovery/UI results.

External source: `C:/Users/user/Desktop/PLATFORMA_CRM_MARKET_UNIFIED_TECHNICAL_SPEC.md`, `UNIFIED-SPEC-20261028`, edition29.10, SHA256 `a4e1449d1aadfde70346a56033fd28affa3e7edaa54183e1558e45e7bce39659`, matches roadmap44–55. Its header explicitly declines whole-document approval. Latest owner decisions take precedence. Yandex Cloud is selected; region/services/resources remain open. Native implementation assigned elsewhere does not exclude this requested mobile audit. Exchange/campaigns remain after the pilot, not pilot gates. Scope does not include the whole Market audit.

Statuses: **implemented/scoped** = code/reachable path found and named checks mapped below/in tests.md; this is not full AC acceptance; **partial** = material accepted behavior missing; **external** = target/person/provider receipt absent; **future** = retained later requirement. No row marked production PASS.

Runtime completion: all14 AC,22 CRM-C and8 CG have a source/result/remainder. Fresh executed coverage is joined per requirement family in [tests.md](tests.md#связь-runtime-покрытия-с-требованиями). New CRM-TERMS01/CRM-EVENT01/PERF01–03 findings qualify prior implemented statements; none of the rows grants production acceptance. External/absent behavior remains explicitly unverified or unimplemented.

## All 14 new pilot acceptance criteria

Requirement text comes from `docs/current/roadmap.md:350–364`, detailed semantics from `docs/current/crm.md:106–338` and `docs/current/ai.md`.

| ID | Implementation / reachable API and UI | Inspected coverage | Result / exact remainder |
| --- | --- | --- | --- |
| AC01 | `record_commands.create_record`, `RecordCreateSerializer`; POST appointments/create-record; Records/Client/Inbox create forms share Appointment | `tests_record_commands`: default/shared ID, closed provenance, required specialist, past time, source permissions; `tests_record_workflow` no Lead/Deal creation | implemented/scoped for manual/confirmed staff commands; automatic path has REQ03, CRM-TERMS01 and CRM-EVENT01 gaps |
| AC02 | Appointment is common scheduled model; `record_workspace`, `AppointmentWorkspacePage`, `CalendarPage`, `AppointmentRescheduleForm`; expected_updated_at checked | record commands stale/conflict/replay; workspace counts/filter; record concurrency last slot/two actions | implemented/scoped; fresh calendar actions/recovery/view-only and Records read/period tests verified; stale existing assertions retained in UI report |
| AC03 | `merchantRoutes.tsx:24–51` sends legacy routes to LegacyRecordsPage; `legacy_record_links.py:18–26` follows actual lead link, never equal IDs/shared client; legacy APIs retained | workspace source hidden/archived/multiple links/no child-read grant | implemented/scoped; representative older external links need browser receipt, no conversion/deletion inferred |
| AC04 | `record_commands.py:20–102` current member/assignment/tenant/branch/service/Resource checks; plan_access/readable_plans | commands role/tenant/current read/revocation; plans OWN/TEAM/partial branch/read restriction; broader access suite | implemented/scoped, security high findings and all mutation entry points remain separate audit rows; UI hiding is no proof |
| AC05 | `services.py` status commands + version and atomic effects; early completion actor/reason/history; `plan_lifecycle` updates revision | completion five negatives/rollback cases; record concurrency early-complete/cancel race | partial: lifecycle implemented; required monetary allocation after completion absent (REQ01) |
| AC06 | Manual create_record sets source_conversation/responsible; plan default/override exists; employee AI crm_writes calls same service; customer auto `_commit_selected_slot` calls legacy booking | manual closed-source/replay/disabled responsible; plan override retained; employee AI record tests | partial: automatic customer booking does not write new responsible/provenance; Business AI default setting absent (REQ03). Old draft exact review/browser context needs current receipt |
| AC07 | Appointment effects in scheduling/services; automations engine/validator and task follow-up policy; preserved legacy rule semantics | automations tests/action_validation/follow_up_policy + scheduling effects | partial: existing triggers plus real local worker/retry/WAIT/cancel verified; CRM-EVENT01 automatic creation omits configured trigger, new money effects remain absent |
| AC08 | `apps/analytics/workspace.py`, record metrics/exports, work_queues; workflow=appointments used by dashboard/owner brief; money source selected separately | tests_record_metrics/tests_workspace/tests_work_queues/tests_financial_sources | implemented/scoped for record metrics/source separation; no plan monetary metrics possible before REQ01 |
| AC09 | `Payment` only receipt/refund with optional Appointment OR Deal; manual_finance separates ledger; VisitPlan has no payment mode/terms/allocation | existing payments tests cover journal; no plan allocation model/API/UI/tests found | **partial, REQ01 P1:** package/pay-per-visit, advance, allocations, mode changes, retained/refunded remainder absent; journal is not completion of this criterion |
| AC10 | Legacy read resolver, Client merge/archive services and plan lifecycle integration; existing import/export survives through legacy context | plans merge moves scheduled identity, archive rejects undated; source read no child-grant; import/export current access tests | implemented/scoped within existing data lifecycle; plan money/history after new schema remains pending; no arbitrary historical re-open |
| AC11 | Sidebar appointments; router and legacy routes; timeline/task/search/dashboard notification links; Records plans as view=plans | route-prefetch/timeline/task workspace/record filters and browser historical evidence | partial: web mapped; native separate branch lacks current Record acceptance; full routes/role/mobile audit remains separate |
| AC12 | Two independent Businesses are distinct from MB01 five branches. Synthetic tests can check isolated roles; working day includes R01/D01/channels/support | no same-candidate real staff/provider day receipt established in this subaudit | **external + code gaps:** REQ01–03, real channels, target/support/staff named acceptance. Old scoped PASSs cannot close this |
| AC13 | Shared UI primitives/token/i18n sources; actual Records/Plan/Calendar components | historical records-full/remediation/shared-calendar reports distinguish320/390/desktop, RU/KK/EN, keyboard/recovery | partial: fresh UI/locale/viewport/action evidence and confirmed UI01–12; user/staff usability, physical device and reader acceptance remain distinct |
| AC14 | `VisitPlan`/`VisitPlanStep` models139–170; nullable one-to-one Appointment, undated steps no slot; `/api/visit-plans/`, schedule/revise/archive/restore/responsible; VisitPlansPage |22 plan tests incl history/replay/branch/merge/override +3 PostgreSQL plan races | partial: nonmonetary plan exists; immutable prices/payment versions/allocations/financial termination absent (REQ01); native not certified |

## Significant CRM-C requirements (all22)

| ID / source mapping | Code / reachable boundary | Test/evidence mapping and result |
| --- | --- | --- |
| C01 Access — access.md, AC04, PK0 | accounts/businesses/core permissions, session/MFA/field selectors, APIs and protected routes | access/permission/session tests plus security audit; implemented/scoped, fresh full-suite denial/revoke plus real private-file/worker and PG proofs mapped in tests.md; no universal endpoint/security-clean claim |
| C02 Client/history — crm378+, AUD03/11 | clients services/merge/archive, activities/core cards, Clients page | duplicate visibility/client PII/merge/history suites; fresh backend plus client create/edit/archive/undo/linked-task UI scoped; dependent AC10 remains bounded |
| C03 Lead/Deal — crm/AC03 | retained apps/leads+crm; legacy read UI, normal Appointment new-work entry | record_workspace legacy tests + domain lifecycle suites; implemented/scoped, not removed or converted |
| C04 Full search — AUD08/09 | clients q/business/page selectors, ClientPicker, async chosen-ID hydration | focused picker/search helpers and server query tests; fresh58-task global-search probe FAIL (UI02); Clients latency PERF02, picker semantics UI04; server search/roles covered separately |
| C05 Branches — MB01/crm554+ | apps/branches + Resource assignments/schedules/travel + booking snapshots | specialist_schedule/branches and record tests; implemented/scoped; five branches is not five independent tenants or capacity proof |
| C06 Calendar — R01/AC01/02/05/14 | Appointment domain + Record workspace + plan schedule | commands/completion/record and plan races; partial new financial effects |
| C07 Task/follow-up — crm632+, D04 | apps/tasks, appointment followups, task editor links | tasks + follow_up_policy; implemented/scoped, worker receipt distinct |
| C08 Automations — AUD04–07 | apps/automations domain engine/atomic actions/editor/history | action_validation/follow_up_policy/automations suites; retained real history; real local worker/crash/retry/WAIT/cancel receipt PASS in adapted drill; shipped helper remains VERIFY02 |
| C09 Inbox — crm/integrations | conversations/inbox_views, read_results, create-record route; ConversationsPage | inbox current-read/create-write tests, record provenance; customer automatic REQ03 prevents broad closure |
| C10 Customer AI — ai.md | bots runtime fingerprints/automation_policy, conversations auto_pipeline/booking | existing safety/knowledge/automatic booking definitions; historical real-model results are old; new AI default/provenance gap REQ03 |
| C11 Handoff — R02-AI-RETURN | bots handoff tasks and successful-delivery timer; manual Inbox | tests_handoff_recovery and `scripts/verify_handoff_recovery.py` referenced; isolated eager/mock != real channel/beat |
| C12 Import — AUD12/16/20/21/22 | core import jobs/permissions, preview/history existing legacy UI | rollback/concurrency/XLSX bounds/mapping tests; full-suite/PG and real AV API+UI preview/confirm/retry/denial verified; no working DB import |
| C13 Export — AUD12c/18/FU | core export_access and job fingerprint/projections/history/download | export current-role/PII/async tests; real local export worker/replay/revoked access verified; target storage/worker acceptance remains external |
| C14 Offline — AUD01/10 | scoped frontend storage/queue, stable command keys and expiry | storage/queue tests and historical lost-response41st-item fixtures; partial offline, no claim of whole offline CRM or money replay |
| C15 Money — AC09/14 | apps/payments immutable journal + financial_metrics source selection | journal/financial_sources tests; confirmed REQ01 gap, external readers empty |
| C16 Settings/notifications | notification personal recipients/read state/SSE plus settings UI | existing WIP personal_api/concurrency/migration/realtime definitions; fresh full-suite/PG recipient/migration/realtime checks mapped; working migration/deployment remains separate |
| C17 Account/support — ADMIN01–05 | support/identity business scope and owner consent; billing adapter foundation | administrative permission/recovery suites; live card processor/offer/commercial enforcement not proven, no SaaS acceptance |
| C18 Files — S04/BE-GAP011 | private attachment upload/quarantine/ClamAV/current permission checks | existing file/AV/recovery coverage; cloud storage/retention/keys/target recovery external |
| C19 Operations — R02/R04/CG04 | production_rules/audit/config, container/runbooks, queues/health | real local recovery and failed HTTP load receipts recorded; Yandex target not deployed/accepted; RPO15m/RTO4h objectives |
| C20 Legal/commercial — CG03/07 | product/legal signup/config vs external legal texts and deferred billing | no technical test can approve legal basis/retention/terms; remain owner/legal inputs, not code assertions |
| C21 Campaigns — D02/AC-CAMPAIGN | existing outreach model/services and consent guards; Market event transport absent | consent/template/mutation tests are partial foundations; future after pilot; shared recipient/1advertisement7days/continuation/live not closed |
| C22 Native — AC-MOBILE-REUSE | historical mobile-release branch, current main web/API; separate mobile audit | native current install/build/device/push/store API compatibility pending; prior implementation ownership not audit exclusion |

## Mandatory D01 and crosscut CG gates

| Boundary | Located evidence / result | Closure requirement |
| --- | --- | --- |
| D01 factual text analytics | ai_core conversation/planner/grounding/history/analyst; AgentConversationPanel and CRMAgentRuntime | current permission/source/no-data tests + real selected flow; no old blanket pause, no automatic production PASS |
| D01 confirmed text commands | crm_approval/crm_tools/crm_writes, approval binding and actor/target fingerprint; tests_record_workflow includes create/replay/early reason | fresh allowed/denied/stale/revoked/replay/injection/record UI result |
| D01 voice | no audio input/transcription/speech flow in ai_core or assistant UI/API; LeadDetailPanel voice note is unrelated | **REQ02 P1:** chosen speech/audio contract + editable transcript + same approval/current rights + RU/KK/mixed/noise/permission/offline/recovery proof |
| CG01 two pilot Businesses | approved quantity/selection preserved in product/roadmap, no need to ask names again | role/data/channel manifest and accepting staff on same candidate |
| CG02 BSP | YCloud TP Lite source and webhook/dispatch tests exist; historical local scope | eligibility/ownership/capabilities/number/WABA/price/onboarding/target webhook + real receipts; do not replace with QR provider |
| CG03 legal/data | contract requires actual texts/purposes/retention/roles/AI/BSP/audio | qualified decisions/approved artifacts; code cannot infer legal basis |
| CG04 target/recovery | local guards/runbooks; latest owner Yandex selection replaces old doc statements | measured load/restore/rollback/DB-files-keys-queues and named serious-incident coverage; no chosen tariff/region claim |
| CG05 send/STOP boundary | outreach final consent checks and limited retries; integration dispatch identity | unknown external attempt reconciliation, versioned consent/revoke/in-flight policy + sandbox receipts; no promise to recall started HTTP |
| CG06 remaining domain decisions | technical allocation/storage/command project in crm.md; existing Record/Plan code | zero positive package/zero bases and exact new terminal corrections still owner edge decisions; existing choices1–23 not re-asked |
| CG07 SaaS | ADMIN05 foundation and deferred R06; visit-money separate | approved commercial policy/provider/enforcement/refund receipts upon resumed SaaS scope, not current pilot plan money |
| CG08 native | known RN/Expo historical source and second developer ownership | current builds/install/device/push/deeplink/store accounts/review and compatibility; main mobile audit owns measurements |

## Confirmed gaps and priorities

**REQ01 / high readiness gap / P1 / AC09,AC14:** package/pay-per-visit terms, advance allocation, mode change and residual funds decisions are accepted requirements but absent from models/API/UI. `VisitPlan` has only client/responsible/revision/archive; `Payment` has receipt/refund with single appointment/deal link; plan commands exclude monetary operations. Reproduce statically by inspecting model fields and registered plan actions. Expected: versioned package shares exactly total, completion consumes available advance once without second receipt; actual journal has no allocation layer. Impact: cannot complete full paid plan pilot, partial payments cannot be treated as completed scope. Acceptance: immutable terms/price versions; exact rounding; concurrent allocation/refund rollback/no double spend; consent retained/returned balance; reachable UI and history. Root independently re-read both model definitions and confirmed the gap. Implementation plan only, no fix in audit.

**REQ02 / high readiness gap / P1 / D01:** text interface and commands exist, voice does not. `AgentConversationPanel.tsx:67–75` sends `{message,idempotency_key,mode,period}`; backend conversation inputs/planner contain text flow, no audio transport/transcription. Search assistant frontend, AI API files and ai_core for audio/speech/MediaRecorder/transcription yields no voice path. A separate Lead note recording is not D01. Root independently re-read the send path and confirmed text-only input. Acceptance described in CG table. No claim that text D01 is absent.

**REQ03 / P1 confirmed requirement defect / AC06:** customer automatic slot path `conversations/booking.py:219–224` calls `create_appointment_from_conversation`; helper105–118 constructs Appointment without responsible_user or source_conversation. New manual/staff-confirmed path `record_commands.py` populates both and tests prove them. Business model has no chosen AI default-responsible setting. Expected accepted AI default setting/current membership validation + provenance; actual auto booking retains legacy null columns. Impact: unassigned automated visits/incomplete provenance versus manual flow. Independent backend-agent reproduction confirmed this on04.11: nine existing automatic-booking controls PASS; the new tenth test fails both subtests because responsible_user_id and source_conversation_id are null. Receipt: ../../../output/comprehensive-audit-20261103/backend/booking-contract-results.json; exact assertions and AUDIT_BOOKING output: ../../../output/comprehensive-audit-20261103/backend/booking-contract.log; harness: ../../../output/comprehensive-audit-20261103/backend/audit_booking.py. Temporary SQLite, isolated_runtime, no working DB, outbound sockets blocked except loopback; exit1. This proves this automatic path, not all AI behavior. Existing authorizing `_automatic_actor_id` is permission context, not selected responsible policy.

**REQ04 / future integration gap / P2 / AC-CRM,C21:** no concrete interproduct tenant binding/versioned event/download authorization transport found in either inspected integration schema. Generic event/ERP infrastructure is not proof of exchange. Not pilot blocker under02.11; do not implement while auditing. Minimal agreed capability/direction/authority matrix precedes code, paired test must replay version/revoke/outage and prove no duplicate accounting.

## Cross-project contract review (read-only)

Market read at HEAD `36081f0427bf8a6d52917536e5c02109a659843b`, current tree may contain independent WIP. Only `AGENTS`, §23/selected contract paragraphs, schema and integration boundary inspected; no full Market audit or edits.

Agreement: CRM `docs/current/integrations.md:302–338` and Market `actual_docs/UNIFIED_SPEC_MARKET_REQUIREMENTS_2026-10-29.md:853–883` both require optional verified legal-entity Organization↔Business binding, no email/BIN matching grant; field/direction/source/purpose/version/actor/idempotency/correlation, revocation, history and reconciliation; Market signed originals authoritative, protected CRM recipient access, no finance-panel export and no imported signature/refund authority. Market `BUSINESS_RULES_AND_IMPLEMENTATION.md:522–528` correctly says exchange/campaign vertical not complete. CRM latest pilot exclusion02.11 does not remove future Market requirements.

Schema fact: CRM Business uses integer Django PK, BusinessEvent source/event/external_id/deduplication_key with unique business/source/key; `connectors.py:362–397` dedups by source:event:external_id (or payload hash). It is generic ingestion, not version conflict/revoked-binding logic. Market Organization ID is UUID; IntegrationProvider enum includes MOYSKLAD/ONE_C/CUSTOM_API/MOCK (schema665–670), data types describe ERP catalog/order/reservation/return, no CRM-specific binding. Search apps/api integration modules, Prisma and packages/schemas found no CRM binding/version transport. CUSTOM_API extensibility is not absence-proof for all arbitrary integrations, but none supplies accepted CRM AC evidence.

Financial no-double-count protection presently visible in CRM: `financial_metrics.py:30–46` selects manual OR one configured external source; never sums systems. `providers/registry.py:19` FINANCIAL_SOURCE_READERS is empty; external FinancialSnapshot contract explicitly future. Thus no observed live Market payment import or double accounting is asserted. Future adapter must preserve source payment/refund IDs and versions and must not create a second manual receipt; tests should intentionally replay receipt/refund and direction changes. Generic event dedup alone cannot certify this.

Additional concrete adapter mismatches to cover before connecting: Market integration-contracts represents prices as `valueMinor` integer strings and three-letter currency; CRM Payment stores Decimal(14,2) amounts and Business currency. An explicit minor-unit/currency conversion is necessary, not raw copying. Market IntegrationConnection3510 is supplier/source-scoped, not an Organization↔CRM Business grant; IntegrationMapping3570 uses connection/entity/externalId uniqueness and UUID internal IDs. IntegrationSyncJob3588 has connection/idempotencyKey uniqueness and correlationId; webhook3617 dedups connection/externalEventId. These are useful existing primitives, but no accepted binding, document-recipient authority, source version ordering or reversal-to-ledger mapping is demonstrated. A cross-system test should use deliberately colliding local IDs, repeated event IDs with conflicting payload/version, revoked bindings and out-of-order refunds. This is a design/acceptance gap for future exchange, not an asserted exploit of absent code.

Cross-doc drift to report only: Market imported spec988 still repeats superseded CRM rejection of Yandex Cloud; update belongs to Market owner, no neighboring edits made.

## Documentation inventory and corrections

`documentation-inventory.json` records89 current technical/procedure/evidence Markdown files with hashes/headings/roles,114 registry entries and201 archive metadata entries. No media/customer content included. Archive bodies were not reread as current policy. Current43 key documents have956 local path links with0 missing; no registry missing path/duplicate. Heuristic anchor scan in preparation found0 candidates; no network URL certification.

| ID | Supported correction | Priority and boundary |
| --- | --- | --- |
| DOC01 | operations42–44 and passport operations7–8 explicitly exclude Yandex; product265–267/roadmap99,378,439 retain old target | P2; latest owner selects Yandex; retain unchosen region/resources/legal suitability and target proof |
| DOC02 | crm-ai-agent title/4–5/29, project-state39–44, capabilities363, passport README row, product27/260 blanket D01 pause | P2; limited text/voice D01 required30.10/02.11, expanded analytics deferred; preserve dated historical pause/evidence |
| DOC03 | product30/roadmap402 say Records UI not implemented/started; roadmap289 says new states/plan not done | P2; reconcile scoped published6349acdf/code with money/AI/default/full14AC remainder; not a global PASS |
| DOC04 | refactor-20261030.md linked roadmap22/PRIMARY11223 absent registry | P3; add evidence role, retain368a3fa4 historical scope, no re-certification |
| DOC05 | current entrypoint project-state top still lists AUD10/21 partial on dated21.10 baseline vs latest roadmap all scoped closed | P3; make historical baseline explicit and link current source; no rewrite of old test outcomes |

No entire current document is demonstrated obsolete: these require in-place corrections, not bulk archive. Existing archive manifest/README already explains original paths and provenance. A movement log for this audit should state zero moves unless coordinator identifies further verified obsolete documents. Runtime configs, dependencies, app code and working DB remain untouched.

## Ordered remediation plan (proposal)

1. Resolve reproduced security/data correctness findings from main audit; keep requirement gaps separate from exploit claims.
2. Close accepted monetary domain in coherent tested slices: immutable terms/rounding → advance allocation/reversal → residual disposition/refund → UI/history → dependent transitions/concurrency/full14AC. Obtain only genuinely unresolved zero-base/correction decisions.
3. Unify automatic booking with accepted responsible/provenance contract and validate current authorizing and assigned users independently, exact offered terms and replay.
4. Complete D01 text acceptance, then voice transport/transcription/edit/confirmation under same tools and rights; resource/privacy/retention decisions precede audio implementation.
5. Candidate-wide pilot acceptance on same hashes, role/data manifest, real sandbox/approved provider receipts, Yandex deployment-specific restore/load/alerts. Product fixes are not made by this audit.
6. Future exchange/campaigns: agree minimal capability matrix and source IDs/version/conflict/revoke semantics; build paired vertical with no double-account tests after explicit resumption. Native compatibility work remains separate owner/developer scope.


## Completed documentation body review and disposition — 04.11

See [document-review-coverage](document-review-coverage.md) and its JSON for every file in the original89-file
inventory, plus12 supporting skill references previously excluded by the inventory.
All active core contract, passport, navigation, procedure and skill bodies were
read; dated roadmap/status/spec evidence is explicitly scoped by section rather
than pretending all historical reports were reread or runtime-certified.

Additional supported documentation drift: AUD12-open in data-lifecycle/integrations;
AUD17/18-open in identity-access; next-AUD12-not-started in tasks-automations;
obsolete blanket AUD10/rest-open and28-vs43 model scenarios in capabilities;
customer-agent blanket CRM AI pause; product AUD07/10-open; roadmap AUD10-partial;
operations notifications0006/7/core0012/support0002 migration status (separately
authorized historical29Oct local application); README scheduling0010 application
(separate02Nov local operation); frontend refactor publication368a3fa4; CRM plan
API future-only wording and Records publication6349acdf. Proposals are in
`supplemental-doc-corrections.patch` and `final-doc-corrections.patch`, with source
hash manifests. Coordinator applies/reviews shared documentation; this subagent
did not edit any product/shared document or claim its own publication.

No whole-document archive is justified. Core docs retain current requirements,
passports retain implementation boundaries, platform spec retains accepted ADMIN
contracts interleaved with explicitly dated proposals, and evidence remains linked
to exact historical snapshots. Archive movement count: zero. No historical body
rewrites proposed. Historical OPEN or pending-CI statements remain dated facts;
new audit results do not retroactively change them.
