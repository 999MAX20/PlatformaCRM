# VISIT-PLAN-PAYMENTS-20261118

## Contract and starting snapshot

Authorized implementation: finish plan payments and accepted UI references; owner
confirmed rejection of positive package price when all base prices are zero.
Canonical root C:/Users/user/Desktop/PlatformaCRM; starting HEAD b5dde74b,
current branch retained. Pre-existing changes: STATUS.md and PRIMARY-SESSION.md;
their existing content belongs to other work and must be preserved.

Prior result: nonfinancial plans and manual receipts/refunds verified independently
→ current models/API have no plan terms or allocations → extend those layers only.

Outcome: accepted terms, package/per-visit prices, advances, immutable allocations,
versioned future changes, explicit retain/refund and reuse for the same client.
No acquiring, SaaS billing, terminal appointment reopening or legacy auto-backfill.

Risk: high (money, tenant permissions, completion, concurrency, migrations).
Reuse Payment/record_payment, VisitPlan commands, Business lock, existing API/UI.
Preserve payment scopes and all-step appointment access; no new permission grants.
Activity remains amount-free; financial history/audit require financial access.
No new notification/provider/AI command or BusinessEvent type. Existing appointment
effects remain once-only. Additive isolated migrations; working DB/deploy separately.

Checks: focused isolated service/API tests per slice; affected payment/scheduling/
client-merge/export suites; PostgreSQL races, migration forward/reverse and drift,
system check; frontend build/i18n/types and real isolated browser flows RU/KK/EN,
desktop/mobile, keyboard, stale/unknown-response recovery. Review full task diff,
commit/publish only after required checks and authorized outgoing range review.

Skills: zani-change-crm-domain, zani-run-verification, zani-review-frontend;
Anti Slop during with UI/layout/human/copy modules. Apply existing components and
tokens, distinguish receipt/allocation/remaining balance, preserve entered values
on errors, maintain keyboard focus and readable mobile money rows.

## Iteration record (superseded by final verification below)

At this checkpoint implementation was in progress; no working-DB migration or publication.
- Backend terms, exact integer-cent largest-remainder distribution, plan receipts,
  completion allocation, bounded refunds, retain/transfer and protected projections added.
- Owner zero-base decision implemented. New terms freeze completed visit prices.
- Payment/plan replays check current rights; financial fields use existing access policy.
- Existing form extended; price preview/consent, balance summary, per-step amounts,
  remainder/credit dialogs, version history and RU/KK/EN added.
- Focused SQLite: 14 tests PASS; disposable PostgreSQL17: 17 tests PASS including
  complete/complete, refund/complete and duplicate payment identity races.
- Dependent isolated SQLite: 122 tests PASS, system/drift PASS (before final
  preview-empty-reason fix and payment provenance serializer change).
- Browser found preview rejected empty draft reason and duplicate sibling React keys;
  both fixed. Fresh-page price preview now displays 90000 -> 30000/60000 correctly.
  Zero-base rejection observed; draft input retained through validation/network failure.
- First frontend app/widget build+i18n/types PASS; final build pending after fixes.
Logs/helpers: output/visit-plan-payments-20261118. Canonical source and disposable DB
verified in runtime.json. Foreign integration changes and commits appeared during work;
not task-owned, do not stage/publish without outgoing-range authorization.
Remaining: final focused/migration and UI workflow/locales/recovery checks, diff/docs,
publication review. Terminal correction/reopen policy remains outside authorized
implementation; no invented reversal API or legacy receipt conversion.

## Checkpoint 12:36 UTC

Implementation scope retained. All money/UI work is task-owned; unrelated integrations,
WhatsApp fixtures/hooks and earlier STATUS/PRIMARY entries remain foreign WIP. HEAD
advanced independently from b5dde74b to f7fe7029; fetch showed no outgoing foreign
commits (origin/main..HEAD empty). Publication not yet attempted.

Additional verification: final-focused.log 39 PASS (includes forward/reverse additive
migration with old receipt preserved and no backfill), system/drift PASS;
final-regressions.log 18 PASS after legacy-reconciliation and VIEW guards;
finance-dependent.log 21 PASS. frontend-accepted-build.log app/widget/types/i18n PASS.
Current PostgreSQL rerun pending to pin final backend input. No working DB touched.

Browser (canonical disposable runtime, CUA Chrome extension): created two plans via
Client -> Plans; package90000 bases10000/20000 ->30000/60000; zero bases rejected;
accepted explicit consent; receipt50000; scheduled and early-completed first visit
with reason -> allocation30000/unallocated20000/remaining40000; refunded10000,
retained10000, transferred retained10000 into second per-visit plan with no new receipt.
Lost-response fault after committed receipt1000 ->503, same-form retry ->200,
received51000 (not52000). Empty credit selector disables confirmation. Escape returns
focus. RU desktop and RU/KK mobile screenshots captured and visually inspected.
Full-page screenshot timed out once; ordinary screenshot recovered on same app after
page state changed. HMR i18n context reset recovered by reload after saved operation.
Earlier duplicate React sibling keys corrected; fresh page has exactly one money panel.

Remaining independent work: EN/localized form review, stale-payment review recovery,
final documentation consistency/diff and commit/push/actual CI. Browser runtime PID
and disposable DB: output/visit-plan-payments-20261118/runtime.json; stop only owned
runtime via stop-runtime marker after UI acceptance. No other agent/process ownership.

## Final local acceptance — 18 November 2026

Authorized money/UI slice: implemented and verified on f7fe7029 + task-owned dirty
patch. No remaining code/evidence gap in this slice. This is not full AC01–14 or
pilot/deployment certification. No dependencies, env keys, provider calls, new
notification/BusinessEvent/AI commands or role grants added. Working DB unchanged.
Additive payments0002 migration is tested only on disposable databases.

| Acceptance | Result / evidence |
| --- | --- |
| Package/per-visit terms, exact allocation, zero-base decision | PASS: 18 focused tests; UI 90000 -> 30000/60000 and rejected positive price with zero bases |
| Versioned future prices / fixed completed price | PASS: backend frozen-price regression; EN readonly completed base visually inspected; terms history shows both versions, actor and reason |
| Advance, partial/late payment, completion once | PASS: receipt and allocation separate; UI 50000 -> allocated30000/free20000; automated late payment and replay |
| Refund/retain/credit | PASS: bounded refund, explicit consent/reason, same-client transfer, cancellation no auto-money effect, archive guard, merge preservation |
| Rights / tenants / rollback | PASS: foreign actor, manager denial, revoked VIEW, cross-client rejection, audit rollback, legacy standalone receipt guard |
| Concurrency | PASS: final PostgreSQL17 21 tests, including completion/completion, refund/completion and duplicate payment identity |
| Recovery | PASS: synthetic committed response lost ->503 -> same identity retry, no duplicate receipt; stale revision409 retains input, refresh shows11000/remaining1000, records1000 once -> remaining0 |
| UI delivery | PASS in scoped CUA Chrome extension: RU desktop/mobile, KK mobile form, EN desktop/history; labels, focus/close/return, loading, empty credit/disabled action, errors/recovery; no horizontal mobile overflow |

Screenshots captured and visually inspected under output/visit-plan-payments-20261118:
zero-bases-ru.jpg, plan-completed-ru.jpg, plan-credit-mobile-ru.jpg,
terms-mobile-kk.jpg, payment-stale-en.jpg, plan-paid-history-en.jpg,
terms-frozen-en.jpg. Synthetic client/service names remain user data in each locale.
Temporary viewport override reset. Owned browser runtime stopped successfully through
stop-runtime; owned disposable PostgreSQL stopped. Other processes untouched.

### Executed checks and input boundaries

All Django runs use `.venv/Scripts/python.exe`, `scripts.codex_verify.isolated_runtime`
and `output/visit-plan-payments-20261118/django_safe.py` as manage.py wrapper:
it suppresses ordinary dotenv loading and blocks external sockets. Commands below
are wrapper arguments (same documented focused isolated check path, not full gate).
Logs are retained in that output directory. No unrelated dependency install.

- `test apps.payments.tests_plan_payments apps.payments.tests apps.scheduling.tests_visit_plans apps.scheduling.tests_record_completion apps.scheduling.tests_record_commands apps.scheduling.tests_import_commands apps.clients.tests apps.core.tests_import_export --noinput`: 122 PASS (dependent.log); earlier input before final preview/serializer/legacy/VIEW fixes. Affected final money regressions rerun below.
- `test apps.payments.tests_plan_payments apps.payments.tests apps.payments.tests_plan_migration --noinput`: 39 PASS (final-focused.log); included forward/back/forward payments0002 and unchanged old receipt/no backfill. `check` and `makemigrations --check --dry-run` PASS. Subsequent guards do not change schema or old standalone payments.
- `test apps.payments.tests_plan_payments --noinput`: final 18 PASS (final-regressions.log).
- `test apps.analytics.tests_manual_finance apps.analytics.tests_financial_sources --noinput`: 21 PASS (finance-dependent.log).
- `.venv/Scripts/python.exe output/visit-plan-payments-20261118/postgres.py`: final 21 PASS, no skips (postgres.log/json), final backend. Disposable loopback PostgreSQL17, tests_plan_concurrency + tests_plan_payments, `--noinput -v 2`.
- Frontend `npm run build`: final app/widget, TypeScript and i18n7501 keys PASS (frontend-final-build.log), after final stale-payment summary/button changes. `npm run check:bundle` PASS (frontend-final-bundle.log); app shell355kB/400kB, existing RU/KK dictionary >500kB warnings remain.
- CUA browser uses canonical Vite source and isolated Django/SQLite fixture, ports60521/60520. Lost-response marker injects503 after actual committed receipt only in ignored test harness; not product code.
- Focused gate selected for high-risk money slice; full-project release gate/live providers skipped because not release certification. Build includes unrelated integration WIP already present, which is not staged in this task.

Rerun triggers: changes to money services/schema, appointment completion or permissions
require affected backend checks; changed UI needs affected flow/screenshots and build.
Unchanged scope evidence is reused; no full CRM readiness inference.

### Decisions and delivery boundary

Owner decision applied: all base prices zero forbids positive package; free plan
is allowed and creates no zero-value receipt. No question remains for this rule.
Separate future owner scenarios: how an already-completed visit may be corrected/
reopened and how existing standalone visit receipts should be reconciled. Neither
has an automatic conversion/reversal command in this slice. Legacy ambiguity is
rejected explicitly instead of double counting. Future implementation depends on
those scenarios; it does not invalidate the new-plan payment acceptance above.

Environment remainder: working migration, release/deploy and pilot acceptance on
the selected target remain separate, not performed. Roadmap AC09/14 keeps the
terminal-correction remainder and full cross-consumer acceptance open.
Updated CRM/API, frontend, access, capability passport, acceptance and roadmap
consistently; README unchanged because setup/env/public release status did not change.
No new parallel backlog. React best-practices review applied to affected components;
existing UI/API layers retained, no redundant global state or raw component requests.

### Publication

Implementation commit `2012fd2ce351e06718ac62807dd290bc20c4717a` on retained
`codex/ui-testing-toolkit`, canonical C:/Users/user/Desktop/PlatformaCRM.
Task-only36-file index reviewed; working/index/committed-range diff hygiene PASS,
registry JSON parsed; relative evidence/contract links checked. No secrets, ignored
runtime/logs, unrelated integrations or status entries staged. Fetch proved no
foreign outgoing commits. Normal `git push origin HEAD:main` succeeded; remote
refs/heads/main read back exactly2012fd2ce351e06718ac62807dd290bc20c4717a.
Push workflow is CI (no deployment job); no deployment performed.
Actual [CI run471](https://github.com/999MAX20/PlatformaCRM/actions/runs/44307635515)
was in_progress at publication inspection; not reported as green. This follow-up
receipt is documentation only; application checks retain their stated boundaries.
Foreign integration/WhatsApp changes and their STATUS/PRIMARY entries remain unstaged.

## Authorized correction and legacy-payment follow-up

Owner confirmed all five proposed pilot rules, then requested implementation and
UI references before interface edits. Base9016bc42, same canonical root/branch.
Foreign dirty integrations/WhatsApp files and STATUS/PRIMARY entries unchanged.
Prior result: corrections and legacy attachment intentionally excluded -> explicit
owner authorization -> add two bounded, previewed commands on existing plan services.

Mode implementation; gap code. Owner-only with existing financial MANAGE, plan
UPDATE and complete tenant/object access. Erroneous completion becomes cancelled,
original history stays; reversal releases allocations into retained balance; a new
terms version removes that visit's charge without repricing other lines. A linked
replacement is explicitly created/scheduled, never restores the old slot.
Legacy attachment retains the original Payment and prior refunds, links its entire
available amount once to one same-client/business/currency plan; manual unambiguous
receipts only, no completed-service receipts or split/mass conversion.

Risk high: money/status/analytics/concurrency. Reuse Business lock, idempotent plan
commands, Payment/refund, allocation reversal, plan terms and activity/audit.
No cancellation messages or ordinary automation replay; cancel pending post-service
followups for annulled completion. Preserve historical events; reports read corrected
current status and cash receipts remain unchanged. Additive isolated migration only.
No working-DB migration, external provider mutation, deploy or new AI command.

Acceptance: exact balances and unchanged cash totals; original records retained;
owner/tenant denial; preview staleness; replay/rollback; competing attach/refund and
correction/refund; report regression; reachable RU/KK/EN desktop/mobile dialogs,
loading/empty/error/recovery, keyboard/focus and visually inspected screenshots.
Focused isolated backend per slice before frontend; affected payment/scheduling/
analytics suites, PostgreSQL races, migration/drift/system; final build/types/i18n.
Full release gate outside this phase. Normal task-only commit/push and actual CI.

UI references generated and shown before edits: exec-d4d4430a (annul completion),
exec-34974fa1 (attach prior payment), generated_images session directory. References
are illustrative modal compositions; existing navigation/logo/tokens stay unchanged.
Skills: domain/verification/frontend and imagegen; Anti Slop during (saved choice),
UI/layout/human/copy modules. Applied requirements: real server preview amounts;
explicit consent/reason; retained inputs and stable retry identity; readable mobile
layout and focus return. Existing quiet green/amber UI direction, no new assets in app.

Iteration: payments0003 adds correction and legacy-link records (no backfill).
An earmarked erroneous-visit receipt retains both released allocations and its
unused earmarked balance. Explicit reuse in the same plan releases only the selected
retained amount, preserving separate consent before paying the linked replacement.
First SQLite run stopped during slow DB setup; diagnostic run with a faulthandler timer encountered
native Windows access violation while rendering historical migration models, before
tests. Retained logs corrections-focused/diagnostic. New verbose run without timer
shows migrations advancing; no failed business assertion yet. No acceptance claimed.
Design read: owner financial review in existing PlatformaCRM form style; dials1/1/1,
spacing separates balance/consent, existing green/amber marks safe/sensitive actions.

Iteration checkpoint: first focused SQLite9 had8PASS/one money-string formatting
assertion failure; PostgreSQL15 had14PASS/another equivalent formatting assertion.
Assertions now compare exact Decimal values; no monetary tolerance added. Expanded
PostgreSQL rerun16/16PASS, including attach-vs-refund and competing-plan attachment.
After this run, replacement consent/reason became mandatory at the backend too;
dependent126 test batch includes that delta and followup/audit/replay/rollback tests.
Initial batch and browser fixture setup were interrupted by tool/process reset:
no Python processes remained and sessions were unavailable. Logs stopped during
migrations, no final test result; restarted only those isolated processes. System
check/drift passed before interruption. First new UI app/widget build completed;
final localized timeline delta will receive another completion build.
UI references preceded edits; new modal uses shared controls and current money
preview, full legacy balance, explicit replacement, reuse selection, safe retry.
Browser acceptance and dependent-suite completion are still pending at this checkpoint.

### Follow-up completion evidence

Canonical root and branch unchanged; implementation starts at9016bc42 plus the
task-owned dirty files. Foreign integration/WhatsApp changes and foreign index
entries were not included. New schema payments0003 is additive, without backfill.
It was applied/reversed/reapplied only in disposable databases; working DB unchanged.

Backend checks (isolated_runtime, dotenv/external sockets blocked by ignored harness):
- `corrections_dependent.py`: `check`, `makemigrations --check --dry-run` PASS;
  `test apps.payments.tests_plan_corrections.PlanCorrectionTests apps.payments.tests_plan_payments.PlanPaymentTests apps.payments.tests apps.payments.tests_plan_migration apps.scheduling.tests_visit_plans apps.scheduling.tests_record_completion apps.scheduling.tests_record_commands apps.analytics.tests_manual_finance apps.analytics.tests_financial_sources apps.activities.tests --noinput -v 2`:126PASS.
  This batch preceded the additional archive guard and final completed-legacy predicate;
  those deltas are covered by the following focused reruns.
- `corrections_pg.py`: disposable PostgreSQL17, `test apps.payments.tests_plan_corrections.PlanCorrectionTests apps.payments.tests_plan_concurrency.PlanMoneyConcurrencyTests --noinput -v 2`:19PASS, zero skips.
  Includes archive-before-terms guard, replacement consent, rollback/audit, preserved
  sent/cancelled pending followups, competing attachment/refund/completion and replay.
- `pricing_final.py`:31PASS (correction and original plan-payment classes), after
  preserving the completed-legacy guard even when its old receipt is fully refunded.
  Positive package/all-zero bases and previous frozen-price/rounding checks preserved.
- `security_final.py`:13PASS final correction class, adding direct API403 checks
  for all three owner-only commands/preview despite manager financial MANAGE,
  and forged foreign-Business receipt rejection with no attachment. Product code
  unchanged after pricing run; test-only extension. Log corrections-security-final.log.
- Logs/results: corrections-dependent.log/json, corrections-pg.log/json,
  corrections-pricing-final.log under output/visit-plan-payments-20261118.

Frontend completion `npm run build`: PASS (types,7527 RU/KK/EN keys, app/widget),
corrections-completion-build.log; `npm run check:bundle`: PASS,
corrections-completion-bundle.log. Existing RU/KK >500kB dictionary warnings remain;
app shell within400kB. Build includes preserved foreign working-tree integration WIP;
this task neither claims nor stages it. No dependencies added.

CUA Chrome extension, canonical Vite/Django source, dedicated localhost58932/58931,
isolated SQLite fixture only. Synthetic client and test owner; no real client data,
provider calls or actual funds. New references were shown before UI changes.
Observed actions and resulting database assertions (correction-browser-data.json):
- RU annul preview90k→60k, allocation30k→0, retained0→30k. Lost-response503 injected
  after actual commit in ignored harness; unchanged-payload retry succeeds with one
  correction/reversal and no second receipt. Reason/consent remained locked and retained.
- Explicit linked replacement creates an undated step; old visit stays cancelled.
  Existing schedule form reachable with correct client/service, no old-slot reopening.
  Re-agreed90k composition keeps other30k lines; separate reuse30k clears retained
  balance only after explicit reason/consent. Backend also covers scheduling/completing
  the replacement and later allocation; browser did not submit that second booking.
- Legacy receipt50k with prior refund10k initially previews40k attachment. Concurrent
  synthetic refund5k makes confirmation409, no attachment. Refresh retains reason,
  resets consent and recalculates35k / remaining25k. Confirm attaches35k, original
  receipt/date/plan=NULL remain, no extra cash receipt. Reopening shows no eligible
  source, preventing a second attachment. Extra fixtures used solely for localization.
- Loading/disabled controls, empty-source state, save error/recovery, stale refresh,
  draft-close confirmation, Escape/Tab, visible focus and focus return exercised.
  Labels, inputs, checkbox and actions are semantic shared controls. No new permission
  framework, UI-only authority or raw component API transport.
- RU/EN desktop and RU/KK390×844 forms/screenshots visually inspected. Two reproduced
  geometry issues fixed: shorter modal headings and two-column mobile balance rows;
  min-w-0 fieldsets prevent long source/reuse values widening either form. Recheck:
  viewport390, fieldset318/333 with equal client/scroll widths, no horizontal overflow.
  Translations include correction history; neutral terminology preserved.

Inspected screenshots in the output directory: correction-preview-en.png,
correction-preview-kk-mobile.png, correction-retry-mobile.png,
legacy-preview-en.png, legacy-preview-mobile.png, legacy-preview-kk-mobile.png,
reuse-mobile.png, legacy-attached-result.png, correction-completed-result.png.
The initial RU preview image precedes the mobile title/layout fix; final RU mobile
and KK/EN captures reflect the final component. Full-page capture timed out once;
documented troubleshooting followed, normal screenshot on the same page succeeded.
Temporary viewport reset; CUA completion recorded. No browser access bypass.

Harness-only attempts: first command fault wrapper omitted DRF action metadata and
returned404 before mutation; preserved action metadata and verified actual503/replay.
Translation hot reload invalidated the development I18nProvider once; fresh separate
tab verified final source without reloading an unsaved form. Neither harness/HMR
attempt was presented as a passed production flow.

Anti Slop during delivery gate applied within scope: real financial data/actions,
existing tokens and shared controls, readable layout, explicit consent, keyboard,
retained input, error/empty/loading and responsive/localized verification above.
No new visual assets, navigation redesign, animation or external links (N/A).
React review: state stays in bounded dialogs; existing API/cache/draft-guard layers
reused. CRM/access/frontend/roadmap/acceptance/capability docs synchronized; README
unchanged because setup/environment/public release status did not change.

Accepted implementation/local-evidence scope has no remaining owner decision or
code requirement. Working migration, target rollout and deployed pilot acceptance
remain separate environment/release work. Full AC01–14, arbitrary terminal reopen,
repricing rendered services, bulk/ambiguous legacy conversion are not closed here.

### Follow-up publication

Implementation `c42c4711e861a44321b4d478f3feedc461c83085`, retained branch
codex/ui-testing-toolkit, canonical C:/Users/user/Desktop/PlatformaCRM.
35-file task-only index reviewed, including all four new files. Working/index diff
hygiene, registry JSON and seven added relative documentation links PASS. STATUS
and PRIMARY staged with only this task's hunks; foreign Meta/WhatsApp work remains
unstaged. No ignored fixture, credentials, screenshot or runtime artifact published.
After commit, `scripts/codex_verify.py --mode static --base-ref 9016bc4286db12427b0d641d77fb92360d8d9d51`
PASS (working/index/actual committed range, migration drift, system check and final
hygiene); log corrections-static.log. No arbitrary base or full-project claim.

Fetch and ancestry proved exactly one authorized outgoing implementation commit.
Normal `git push origin HEAD:main` succeeded; remote refs/heads/main read back
exactlyc42c4711e861a44321b4d478f3feedc461c83085. Push workflow is CI, no deployment.
[CI473](https://github.com/999MAX20/PlatformaCRM/actions/runs/44317269011) was
in_progress at inspection (18.11.2026); not claimed green. This publication receipt
is docs-only; application evidence remains valid for unchanged source. Own test
backend/frontend and PostgreSQL processes stopped; ordinary working DB untouched.

## PLAN-TERMINATION-REFUSAL-20261118

Mode implementation; code gap. Owner approved five rules in the side conversation:
time cancellation preserves service/price and replacement history; refusal subtracts
only its agreed line; no fees or debt writeoff; owner with money rights confirms
refusal/termination; refund/retention and future credit transfer remain explicit.
Prior payment/correction closure -> scheduled refusal and termination absent ->
extend existing locked plan commands, terms ledger and shared dialogs only.

Canonical root C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit,
base a3753708bf809921dffa86070410293b71b76ff4. Starting foreign WIP: integrations
services/tests/signup and frontend WhatsApp fixtures/hook, integrations contract,
STATUS and PRIMARY-SESSION. Preserve those hunks. Payment/scheduling paths clean.
No handoff or parallel writer requested. No working database changes/deployment.

Acceptance: owner-only preview+reason+consent; cancel future bookings and pending
reminders atomically; retain rendered services, frozen line prices, allocations,
receipts and debt; zero remaining services allowed; refund/retain separately;
terminated plan cannot reopen/add services or accept excess advance; debt settlement
remains reachable; archive blocked on debt/unresolved balance. Cancelled time can
be rebooked with linked history and unchanged agreed price. Replays, stale previews,
rollback, tenant isolation and concurrency must pass. No new fees, AI tools,
external messages or cancellation marketing automations from refusal/termination.
Audit/activity record effects; no financial amounts in broad-access timeline.
Migration adds lifecycle/rebooking history fields, tested only in disposable DB.

Reuse zani-change-crm-domain, zani-run-verification and zani-review-frontend;
Anti Slop during: preserve shared tokens/components; responsive dialogs; keyboard,
focus and retained input; real preview amounts and RU/KK/EN copy. Reference board
shown before UI changes (generated_images/01a1eede-e68a-7850-bbd7-eb45e72d8b16/
exec-c1085901-b09a-4afa-81cc-200a294eaa25.png).
Focused domain/API tests precede UI. Completion: affected payment/scheduling suites,
PostgreSQL race checks, system/schema/migration checks in isolated runtime;
build/types/i18n and reachable real browser desktop/mobile/error/retry flows.
Update CRM/access/frontend/roadmap/capability contracts and this evidence. Commit
and normal push only task-owned verified outgoing range; inspect CI separately.
No remaining owner policy decision; full pilot certification outside this phase.

### Local acceptance result

Implemented and locally verified 18.11.2026 on a3753708 + task patch (HEAD advanced
independently to61a7946f: unrelated voice evidence only, not owned by this task).
New services plan_termination/plan_rebooking reuse Business/plan locks, immutable
terms, receipt/allocation ledger, permission checks, idempotency and shared dialogs.
Scheduling0015 adds termination/refusal/rebooking history. No working DB migration.

Acceptance PASS: agreed line subtraction without repricing; booked slots released;
completed services/receipts/allocations/debt retained; zero-service closure; owner-only
preview/reason/consent; stale balance/revision rejected; atomic rollback/replay;
linked rebooking preserves price and earmarked advance; no reopen after archive
restore; debt payments capped also per selected visit; retained balance transfers
to a new plan without a new receipt. Refused earmarked funds cannot conceal debt.

Commands/artifacts (all under ignored output/plan-termination-20261118):
- Python closure_dependent.py: isolated check, makemigrations --check --dry-run,
  affected payment/correction/migration/scheduling/analytics/activity suites:127 PASS.
  Exact labels/commands and exit codes in closure-dependent.json/log.
- Python acceptance_pg.py: disposable PostgreSQL17, termination functional11,
  termination races3 and existing money races6:20 PASS, no skips;
  acceptance-pg.json/log. Completion/refund races and same-key replay covered.
- frontend npm run build: i18n/types/app/widget PASS (frontend-acceptance-build.log).
  npm run check:bundle PASS (bundle-acceptance.log); existing RU/KK chunks warn above
 500kB; app shell stays within400kB. No dependency or environment change.

Initial dependent run exposed archive checking future charges and the old remove
flow test. Guard corrected to rendered debt; test now exercises explicit owner
refusal, preserving original history/replay assertions. Both affected reruns PASS.
Later earmarked-refusal projection fix reran dependent127 and PostgreSQL18 PASS;
last two coverage additions produced PostgreSQL20 PASS without further backend edits.
Synthetic fixture date-price type error repaired in ignored seed only.

Real Chrome extension + canonical Vite/Django, disposable SQLite, synthetic owner:
RU refusal90k->60k, termination60k->30k, paid45k/applied30k/free15k;
separate refund15k gives free0/debt0. KK mobile termination preserved10k debt:
10001 rejected,10000 accepted. EN linked rebooking preserves30k; second-tab change
rejects stale preview, refresh retains reason and resets consent. Injected lost
response after commit retries same identity once. Draft guard, required fields,
keyboard Space/Escape, close/focus return, loading/recovery and final list status
verified. New linked step opens the existing schedule form with fixed client/service.
Screenshots captured AND inspected: refusal-preview-ru.png, refusal-mobile-ru.png,
termination-preview-ru.png, terminated-refunded.png, termination-kk-mobile.png,
termination-refreshed-en.png, termination-final-en.png. Mobile390x844 no horizontal
overflow; shared40px buttons retained with spacing, consent/close targets44px.
Contrast warning4.92:1, subtle6.16:1. Existing tokens/Modal/Button retained; no new
assets, navigation or themes, so those aesthetic gates N/A. Translation HMR briefly
invalidated I18nProvider in dev; clean reload recovered the original target and all
final flows. This is not a deployed-browser certification. Viewport override reset.

CRM/access/frontend, roadmap, acceptance and capability evidence synchronized.
README unchanged: no installation/configuration or public release claim changes.
No remaining code, local evidence or owner decision in approved scope. Environment:
working migration/deployment and target pilot acceptance remain separate. Full
AC01–14, external bank execution and arbitrary terminal reopen are not certified.

### Termination publication receipt

Implementation bb051dbda914c3a654369a5532aee6ba93efd485 on retained branch
codex/ui-testing-toolkit. Task-only31-file index reviewed; foreign integration hunks
in STATUS/PRIMARY preserved unstaged. Added local links9, registry JSON, credential
pattern scan and diff hygiene PASS. Static runner before commit and after commit
with explicit base61a7946fda20ab2dd8ebf6a8135073a697800ae7 PASS; logs
static-precommit.log/static-committed.log. This checks the actual committed range.
Fetch proved only the authorized implementation outgoing; normal HEAD:main push
succeeded and remote SHA read back exactlybb051dbda914c3a654369a5532aee6ba93efd485.
[CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/44327322575) was in_progress
at inspection, not claimed green. Push starts CI, not deployment. Own synthetic
browser/backend/frontend and PostgreSQL runtimes stopped. No working DB mutation.
This docs receipt does not change application evidence inputs.
