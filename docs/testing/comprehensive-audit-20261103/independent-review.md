# Independent verification — UI01, OPS-Q01 and domain boundaries

04.11.2026; canonical checkout, HEAD0b3348e1 plus preserved WIP. Read-only product review.
Only audit output artifacts were written. No product source/config/dependency edits,
broker/server, working DB access, provider traffic or deployment. Findings were retraced through
actual source independently; prior reports were used only to identify requested IDs.

## UI01 — confirmed, P1 recovery defect

`frontend/src/main.tsx:17–21` places AppErrorBoundary ABOVE AppProviders.
`app/providers.tsx:79–86` places I18nProvider inside AppProviders. After a descendant
throws, boundary render replaces that subtree with its own fallback, so the fallback
has no I18nProvider ancestor. AppErrorBoundary49/52 renders actual Button; Button19
unconditionally calls useI18n even when isLoading is false. i18n.tsx116–118 throws
when context is null. PageFallbackLayout itself is provider-independent; the Button
dependency breaks the emergency tree. Boundary cannot catch its own failed render.

Independent executable reproduction: Node stdin in canonical frontend; installed
esbuild bundles actual AppErrorBoundary/i18n imports in memory (write:false,
platform:node, format:cjs, packages:external, jsx:automatic, import.meta.env={}).
Instantiate actual boundary, set state.hasError=true, call actual render(), and pass
the resulting tree to ReactDOMServer.renderToStaticMarkup without a provider.
Result: `useI18n must be used inside I18nProvider`. Control calls prepareLanguage('en')
then renders the same tree under actual I18nProvider:2 buttons and
data-testid=app-error-boundary, visible localized text, PASS. Final probe exit0.
This independently proves the fallback's missing-context dependency, not a complete
browser recovery journey. No monitoring initialization or network was called.

First control assertion expected fallback English wording rather than loaded-dictionary
wording and failed; corrected structural control verifies the real2 buttons/marker.
The missing-provider error reproduced in both attempts unchanged. That assertion
mistake was a probe error, not another product defect.

Minimal remediation boundary: emergency fallback must remain renderable without
the providers it replaces. Do not merely move boundary below all providers, losing
coverage for provider crashes. Acceptance: real descendant/provider crash renders
localized recovery once, no secondary exception; keyboard reload/home usable;
unavailable localStorage and dictionary loading should have safe fallback. Current
getLanguage reads localStorage without catch; that is an additional untested edge,
not a separately reproduced finding here.

## OPS-Q01 — confirmed shipped topology defect, P1 target blocker

docker-compose.yml defines generic celery without --queues, plus workers explicitly
consuming integrations,webhooks_outbound; ai; file_scans. compose.stand.yaml changes
edge/ports only. Neither defines consumers for notifications, automations or
reports_exports, including when workers+beat profiles are enabled.

config/settings.py26/324 sets default queue=default; no CELERY_TASK_QUEUES override
was found. Actual task decorators explicitly select notifications
(apps/notifications/tasks.py7), automations (apps/automations/tasks.py6/12/18), and
reports_exports (apps/core/tasks.py19/25). Beat schedules the due tasks in settings
442–462. Prefix-only router inspection is insufficient: registered names use
notifications.* / automations.*, so decorator execution options must be included.

Independent installed-Celery introspection used scripts.codex_verify.isolated_runtime
and a child Python process: import config.celery.app, django.setup(),
app.loader.import_default_modules(); capture app.amqp.queues.consume_from before
route resolution; resolve each task with router.route(task._get_exec_options(),name).
No worker, broker connection, migration or DB query was needed. Exit0 output:

```json
{"default_consumer_before_dynamic_route_resolution":["default"],"effective_task_queues":{"automations.process_automation_run":"automations","automations.process_due_automation_runs":"automations","exports.process_due_jobs":"reports_exports","exports.process_job":"reports_exports","notifications.process_due_notifications":"notifications"}}
```

Initial harness called django.setup before config.celery and failed unconfigured
settings; corrected import order above. Intermediate router.route({},name) ignored
decorator options and was diagnostic only, not evidence of effective routing.

Impact: with ordinary default configuration, queued work/recovery/async exports
can accumulate while web/other workers remain healthy. Inline automation may hide
the gap for some immediate calls but does not supply a consumer for delayed work.
This is not proof any current server is deployed incorrectly; extra externally
configured consumers could compensate. One overridden default queue cannot cover
all three missing destinations. Acceptance: executable queue-to-consumer manifest
for deployed profiles; real isolated Redis/worker due notification, WAIT/retry,
async export and restart checks; one effect per replay, permission recheck, shared
private files and AV configuration where required. No blind queue replay proposed.

## Architecture: concrete sources of divergence and bounded acceptance

1. **Confirmed responsibility/provenance split (REQ03).** record_commands.create_record
   reloads references under Business lock, validates responsible/current membership,
   stores responsible_user/source_conversation and calls handle_appointment_created.
   conversations.booking.create_appointment_from_conversation74–158 directly creates
   another Appointment path without those columns. _commit_selected_slot219 calls it.
   automatic_creation_actor is the authorizing identity, not the agreed Business
   default coordinator. Independent backend receipt booking-contract.log corroborates
   null/null with9 existing controls passing and two failing subtests in the new test.
   This is domain divergence, not a file-size concern.

   Refactoring acceptance: preserve client exact-slot consent/fingerprint/offer-sent
   check, Business→conversation locks and booked_slots replay identity; share validated
   creation invariants/effects across manual, confirmed staff, automatic and plan
   scheduling. Resolve current default separately from authorizing actor; no arbitrary
   owner fallback. Prove provenance/coordinator/revocation/branch/object access,
   stale terms, last-slot race, rollback, replay and one follow-up/event/notification.

2. **Confirmed stale-terms consent bypass (P1), no-branch automatic booking.**
   Automatic _commit_selected_slot199–218 compares offered duration/price only inside
   Branch.exists branch. For a no-branch business, appointment_snapshot uses current
   Service duration/price (branches/schedule.py29–49), while runtime fingerprint
   (bots/runtime_configuration.py) covers bot/profile/knowledge/channel, not Service.
   create_record84–89 compares expected terms regardless of branch. Current authority
   docs/current/ai.md95–96 disallows confirming obsolete service terms.

   Independent isolated reproduction used actual maybe_create_appointment_from_reply,
   automatic_creation_actor, service snapshot and DB creation. The offer is generated
   by actual format_booking_offer, stored with current fingerprint and a SENT outbound
   message; customer replies exact option. Only outbound confirmation is mocked.
   No ordinary DB, live provider or production configuration was accessed.

   | Case | Observed | Expected |
   | --- | --- | --- |
   | No branch, unchanged100/30 | booked100.00/30, one Appointment | booked (PASS) |
   | No branch, price100→200 after offer | booked200.00/30, one Appointment | requires_staff (FAIL) |
   | No branch, duration30→60 after offer | booked100.00/60, one Appointment | requires_staff (FAIL) |
   | Branch-enabled existing control | initial booking/replay work; changed price rejected | PASS |

   Fingerprint remains unchanged in both failing cases. Run: `.venv/Scripts/python.exe
   output/comprehensive-audit-20261103/backend/run_backend.py stale-terms test
   output.comprehensive-audit-20261103.requirements.audit_stale_terms --noinput -v 2`.
   Child test exit1:4 tests,2 expected-contract failures; migration/setup/system
   check succeeded, temporary SQLite destroyed. Runner itself exits0, so the child
   returncode in backend/stale-terms.json and log is authoritative. Reproducer:
   requirements/audit_stale_terms.py; full receipt: backend/stale-terms.log. Snapshot
   HEAD0b3348e1 + preserved WIP,04.11.2026. This proves actual domain acceptance of
   changed catalogue terms, not live messenger delivery or concurrency behavior.

   Minimal fix boundary: compare current offered terms for both branch and no-branch
   businesses before creation under the shared lock, with explicit review/new offer
   on mismatch. Retain unchanged, branch, replay, availability and access controls;
   prove zero Appointment/effects on stale price and duration. No fix made in audit.

3. **Confirmed creation automation omission (C07, P2).** create_record104 calls
   handle_appointment_created (services141–149), including scheduling, responsible
   notification and appointment_created automation. Legacy conversation helper calls
   schedule_appointment_followups directly and its own activity/audit; neither it nor
   the automatic caller invokes the common creation handler. Activity event and
   AutomationRun are distinct facts.

   Independent isolated2-test probe uses real save_configuration with owner permission,
   entitlement and action validation intact: active appointment_created rule, no
   conditions, create_task with unique title. AUTOMATIONS_RUN_INLINE=True enables the
   actual engine; neither engine, action validation nor Task creation is mocked.
   Only outbound booking confirmation is mocked. Both tests use the same existing
   automatic-booking fixture in separate disposable TestCase transactions.

   - Manual create_record control: Appointment created; one SUCCESS AutomationRun
     for its Appointment identity; action_results create_task SUCCESS; one unique
     titled Task. PASS.
   - Actual maybe_create_appointment_from_reply automatic path: status booked,
     Appointment created; zero matching AutomationRun and zero uniquely titled Task.
     FAIL expected one creation effect. This is absent event dispatch, not a failed
     queued worker, skipped condition, invalid action or owner authority denial.

   Command: `.venv/Scripts/python.exe
   output/comprehensive-audit-20261103/backend/run_backend.py creation-effects test
   output.comprehensive-audit-20261103.requirements.audit_creation_effects --noinput -v 2`.
   Child exit1,2 tests/1 failure;47.53s including isolated schema setup; system check
   passed; temporary SQLite destroyed. Source requirements/audit_creation_effects.py;
   receipts backend/creation-effects.log and backend/creation-effects.json. Same
   HEAD0b3348e1 + preserved WIP. No product/working-DB edits or provider traffic.

   Policy cross-check: tasks-automations passport6–9 defines appointment_created as
   default new trigger, preserves existing owner-run rules and states follow-up/replay/
   lifecycle coverage. Current CRM automation contract retains runtime owner/action
   checks. No explicit exclusion for client automatic Appointment creation was found
   in current CRM/AI/task-automation contracts. The demonstrated behavior diverges
   from the ordinary appointment_created event semantics; code comment separating
   legacy booking commands is not a policy exception. Parent should include this
   concrete omitted user-configured effect in C07 acceptance.

   Remediation boundary: share the creation event/effect orchestration across valid
   booking paths, preserving consent/access/locks and exactly-once replay. Do not add
   another handler blindly: existing follow-up and audit calls could duplicate work.
   Verify automatic/manual/staff/plan creation triggers once, rollback produces none,
   replay none additional, and owner permissions recheck. Notification recipient
   omission is still a separate source finding, not runtime-proven by this Task test.

4. **Plan money is missing domain state, not a UI/refactor-only issue (REQ01).**
   VisitPlan139–153 has coordinator/revision/archive; Step155–167 links optional
   one-to-one Appointment. plan_services147 uses create_record with expected terms;
   plan_lifecycle only locks/touches revision. Payment has receipt/refund, no terms
   versions/allocation/reversal. record_payment55 caps refund at amount-refunded,
   which is correct for current ledger but insufficient once allocations exist.
   Do not infer an existing double-spend exploit in an absent allocation feature.

   Keep Payment as received/refunded fact, Appointment as scheduled/status fact,
   plan terms as immutable accepted price versions and allocations as distinct
   append-only consumption/reversal. Derive balances from those facts; never create
   another receipt on completion or silently change completed price. Share Business
   lock order across completion/refund/retain/reversal. Acceptance: exact total and
   rounding, no duplicate receipt/over-refund/double allocation, concurrent races,
   rollback, stale consent, current financial/branch access, merge/history/export,
   UI retained-vs-unresolved remainder. Fully-zero base with positive package and
   new completion corrections still need only their unresolved owner decisions.

No recommendation to rewrite modules wholesale, introduce an independent permission
framework, change queue settings now, or implement money during this audit.

Durable command receipts: [stale terms](assets/stale-terms.json),
[creation effects](assets/creation-effects.json). The diagnostic source and full
synthetic logs remain in [requirements output](../../../output/comprehensive-audit-20261103/requirements/)
and [backend output](../../../output/comprehensive-audit-20261103/backend/).
Only audit materials were written; the application implementation is unchanged.
