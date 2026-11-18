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
