# AGENTS.md

Execution rules for Codex/AI agents in PlatformaCRM (PlatformaCRM).
These rules govern work; live status and test counts belong in task evidence.

## 1. Start and restore context

1. Read [STATUS.md](STATUS.md), the selected checkpoint in
   [PRIMARY-SESSION](docs/testing/task-state/PRIMARY-SESSION.md), and the continuity
   section of [task template](docs/testing/CODEX_TASK_TEMPLATE.md).
2. Check [project handoff](actual_docs/PROJECT_HANDOFF.md),
   `.codex/project-session.json` and [rollover protocol](docs/testing/SESSION_ROLLOVER.md).
   Establish the registered owner, authorized scope, remaining result and one next step.
3. Verify actual repository root, branch, HEAD, staged/unstaged changes and untracked
   files. Separate task-owned work from user/other work; retain a starting snapshot.
4. Read the relevant contracts below and compare existing code/tests/closure evidence
   before creating models, endpoints, services or components. An old plan is not a new task.

Only `C:\Users\user\Desktop\PlatformaCRM` is a writable source checkout (owner decision
2026-09-21; canonical folder renamed with explicit owner approval 2026-09-28).
The old `Desktop\Zani` junction resolves to this same checkout for an already-open
Codex project; it is not another source copy. Use the new canonical path for new work.
Do not create/use another worktree, clone or source copy for edits.
Alternate trees are read-only recovery sources until separately accepted/retired.
One repository-wide writer includes code, migrations, contracts and shared docs.
Parallel audits may only read an identified snapshot. Keep the current branch;
never switch a dirty/shared checkout or overwrite it to match a remembered revision.
Unexpected writer, branch/HEAD drift or affected-path changes pause writes until reconciled.
See [consolidation evidence](archive_docs/2026-10-07/docs/testing/task-state/CONSOLIDATION-2026-09-21.md).

Run servers from the canonical folder. Before trusting localhost, verify backend,
frontend and worker source roots and build/profile. Do not stop others' processes.
Disposable test databases/build outputs are allowed, not alternate source trees.
Working-DB migrations and removal of old trees need their own agreed scope/checks.

## 2. One bounded work cycle

- Use the existing task ID/source and record a compact contract before implementation:
  mode, observable result, gap type (code/evidence/environment/policy/roadmap), reused
  layers, scope/non-goals, owner/root/base, acceptance and required checks. Use the
  [task template](docs/testing/CODEX_TASK_TEMPLATE.md); scale detail to the change.
  Clear user authorization suffices; routine steps need no repeated approval.
- Identify permission, notification, BusinessEvent, AI, migration/env impacts.
  An environment/evidence gap does not automatically authorize a code rewrite.
- Inspect, make the smallest sufficient change, verify the affected behavior, record
  evidence and publish under section 6. Prefer small services/selectors/components.
  Do not mix unrelated backend/UI/integration/docs changes without explicit scope.
- Preserve unrelated changes; never revert another person's work without authorization.
  Refactor only for acceptance or a demonstrated risk in the changed path. File size
  prompts review, not a rewrite. Record optional cleanup separately; no endless polish.
- Reopen closed work only for a reproduced regression, proven missing acceptance
  criterion or approved requirement change. Record prior closure, new evidence,
  minimal delta and regression check. Do not restart audits merely after compaction.
- After two equivalent failed attempts with unchanged inputs, change the hypothesis
  and run the smallest diagnostic. Explicit order/flakiness experiments remain valid.
  Fix in-scope failures; preserve evidence for external/unrelated blockers without
  silently expanding scope. Request direction only when needed.
- Code shows actual behavior; approved contracts define required behavior. Neither a
  newer timestamp nor an index resolves policy conflict. For unresolved permission,
  lifecycle, data-loss or external-effect policy, obtain an owner decision before
  dependent changes; continue independent authorized work.
- Owner clarification 2026-09-25: first check already-approved decisions, then
  classify only the unresolved question. A: foundational money/architecture/security
  decisions precede dependent implementation. B: ambiguous business policy blocks
  only the affected scenario; request a short decision with options and consequences.
  C: safely apply established rules without inventing policy or adding approval
  loops for routine/cosmetic work. Fix proven bugs within the authorized phase;
  categories do not authorize a new phase or let the agent choose major policy.
- Keep established staff rules: disabling login does not disable the specialist;
  history/appointments remain and a manager reassigns work manually. Overlap and
  AI staff-action rules remain. The annotation's automatic transfer of tasks to
  an administrator is a hypothetical example, not an approved override.

## 3. Product and engineering invariants

PlatformaCRM is an AI-first CRM/business control layer for SMB. The first paid release
serves dental administrators under [V1 rules](docs/current/product.md).
Keep daily work simple, fast, role-aware and action-oriented. Do not introduce
clinical records, a new permission framework or vertical-mode rewrite implicitly.
Do not turn it into heavy ERP, a full-sync warehouse, an admin maze, a developer
console for merchants or a mock-only demo.

Implementation order: domain invariants → state machines → audit/activity → API
contracts → frontend integration → E2E. Do not polish a page while rules are bypassable.

- Tenant isolation: merchant entities belong to `Business` or safely derive access
  through related objects; all linked entities must belong to the same business.
- Backend authorization is mandatory; hidden buttons and frontend validation are
  insufficient. Account assignees/owners/watchers/responsible users must be active
  business members. Appointment specialists follow their own approved domain contract.
- Keep business logic in services/selectors/state-machine helpers. Views validate,
  authorize, call services and return responses. CRM lifecycle fields (status/stage,
  completion/win/loss/archive timestamps, ownership/assignment) change through domain
  services, not ad hoc view/frontend writes.
- Deal stage must belong to the business and pipeline; terminal transitions use
  deal services; lost leads/deals require a reason. Booking/rescheduling respects
  working hours and overlap rules. Important actions write activity; sensitive or
  destructive actions write audit logs. Archive/restore critical data by default;
  merge/delete flows remain traceable.
- React uses `frontend/src/api/*`; no raw API calls in components. Search/reuse existing
  layers first. Provider-specific behavior stays behind connectors/provider adapters.
- Never expose secrets/tokens. Use env/config, encrypted credentials and masked
  serializers. Merchant daily UI hides provider technical complexity in setup/help.
- AI stays optional: ordinary CRM continues when it is unavailable. Critical changes
  require explicit user confirmation. Ground output in real entities/events with
  sources, or clearly say data is missing. A backend-only foundation is not complete
  without its applicable reachable user flow, permissions and tests.

## 4. Select current authority, not historical plans

Always follow [engineering rules](docs/current/engineering.md).
[docs/README.md](docs/README.md) and its explicit
[registry](docs/documentation-index.json) define active document roles.
Read only the current contract relevant to the task, its passport and selected
checkpoint. No document date, old checkbox or archived "continue" authorizes work.

| Work/question | Authority |
| --- | --- |
| Product and scope | `docs/current/product.md` |
| Implemented capabilities / evidence boundary | `docs/pre-production/README.md`, `docs/pre-production/capabilities.md` |
| Open acceptance / unresolved decisions | `docs/current/acceptance.md` |
| CRM lifecycle / money / automation | `docs/current/crm.md` |
| Permissions / tenant / identity | `docs/current/access.md` |
| AI grounding / actions / safety | `docs/current/ai.md` |
| Frontend / shared UI | `docs/current/frontend.md` |
| Connectors / imports / exports | `docs/current/integrations.md` |
| Environment / files / operations | `docs/current/operations.md` |
| Verification | `docs/testing/testing.md`, `docs/testing/CODEX_TASK_TEMPLATE.md` |
| Defect prevention | `actual_docs/DEFECT_KNOWLEDGE_BASE.md` |
| Ownership / transfer | `actual_docs/PROJECT_HANDOFF.md`, `.codex/project-session.json`, `docs/testing/SESSION_ROLLOVER.md` |

`archive_docs/` contains historical evidence only. Never use its instructions,
proposals or readiness claims as current authority. `.rgignore` excludes it from
default searches. For a specific decision/closure, explicitly read the exact
archived source (or `rg --no-ignore` on that path), label it historical and reconcile
with current contracts/code. Do not scan the entire archive on startup/compaction.
Archived relative links retain their original Git-tree context; the manifest maps
original paths. Do not repair historical bodies or restore redirect stubs.

Unregistered new docs cannot silently become authority. Register an intentional
document with its role and update its owner; do not create a competing backlog.
Generated inventory and test reports prove only their named snapshot/boundary.
Code shows implementation, contracts define requirements; unresolved conflicts
still follow section 2. Archiving does not close open acceptance or approve proposals.

## 5. Verification proportional to the change

[Testing guide](docs/testing/testing.md) owns exact commands and the matrix.
Use cross-platform `scripts/codex_verify.py`; Bash is not required. Select gates
before implementation; do not lower acceptance after a failure.

| Change | Required boundary |
| --- | --- |
| Docs only | Working/index/real committed-range diff hygiene; links, commands, consistency and new/untracked-file review. No unnecessary app build/install. |
| Backend iteration | Smallest isolated reproducer/regression; at phase close, system/migration-drift checks and affected/dependent suites. |
| Frontend / mixed flow | Build plus affected reachable UI/API evidence; backend checks when contracts change. |
| CRM lifecycle / security / AI / integration | Applicable happy path, permission denial, tenant isolation, recovery/no-data/approval/idempotency and secret handling under the guide. |
| Release-candidate integration | Full gate on the exact candidate/base plus acceptance-specific checks; scoped PASS is not full PASS. |
| Live/deployed acceptance | Explicitly authorized target/environment; local mock/eager evidence is not live readiness. |

The runner needs an explicit ancestor base different from HEAD. With no committed
range, use the documented isolated focused path and state that boundary; never
invent a base. Reuse evidence only for unchanged relevant inputs. New changes,
failures or unresolved concerns justify rechecks; unchanged docs do not invalidate
application evidence. Do not weaken assertions to make a gate green.

Generate only intentional migrations, test them in an isolated DB, and distinguish
that from applying them to a working DB. Working/staging/production migrations,
seed/reset or destructive smoke need explicit target/scope authorization. Never
repopulate ordinary `db.sqlite3` during verification.

Checkboxes require their applicable passed gate. A baseline failure needs evidence,
not an assertion; it still blocks any acceptance it leaves unproven. Record exact
commands, results, skipped checks/reasons, environment, coverage and commit or dirty
snapshot. Distinguish implemented, verified, committed, integrated and deployed.
If `.git` is absent, say branch/publication operations cannot be proven locally.

### Proportional verification — owner decision 2026-10-02

Choose checks by behavior, blast radius and failure impact, not file count. Before
implementation record a short plan: changed behavior, risk, focused checks and
completion checks. These are verification levels, not extra approval phases.

- Docs/rules: diff hygiene, links, examples and consistency only; no app installs,
  builds, database or browser suites just for Markdown.
- Local visual/copy change: inspect existing tokens, typography, spacing, sizes
  and layout; verify the affected component/page at relevant viewport/locale and
  keyboard states. Do not audit/redesign unrelated pages or create E2E tests that
  merely mirror CSS. Run frontend build/types once at completion where required.
- Functional frontend: targeted component/interaction tests and the changed
  reachable flow, including applicable loading/error/empty/recovery states.
  Use targeted browser tests for critical flows, not the whole E2E suite.
- Backend: after each coherent service/API/state transition, run focused automated
  tests before building dependent behavior. Never defer backend validation until
  the entire backend or a large phase is written. At completion run affected and
  dependent suites plus required system/schema/migration checks in isolation.
  Prove happy path and invalid input; where applicable prove role denial, tenant
  isolation, lifecycle invariants, transaction rollback, money/stock correctness,
  concurrency, idempotency, retries and recovery. UI screenshots do not prove these.
- Shared tokens/components/contracts: inspect callers and test representative
  affected consumers. Broaden only for demonstrated shared impact; auth, permissions,
  payments, migrations and shared infrastructure are high risk even in a one-line diff.
- Full-project/E2E gates: release candidates, explicitly authorized comprehensive
  certification, or a documented cross-cutting risk needing that scope. A routine
  task completion, commit, push or context restoration alone is not that reason.

Reuse PASS only while relevant code, dependencies, configuration and fixtures are
unchanged. Run affected checks again after relevant fixes; do not repeat unaffected
suites. Do not reinstall dependencies locally if the validated environment and lock
inputs are unchanged; retain deterministic installation in clean CI. Prefer concise
success summaries and bounded failure logs. Read the selected checkpoint and relevant
contracts, not entire historical records. Keep required failures visible; these rules
do not waive existing release acceptance or retroactively turn a failed gate green.


## 6. Verified commit and normal push

Standing owner authorization (2026-09-21): after an approved implementation/docs
change passes its required gates, commit and promptly normal-push to `origin`
(`https://github.com/999MAX20/PlatformaCRM.git`), target `main`. Read-only/no-push requests
and unresolved target/safety questions override it. This is not an automatic hook.

1. Verify canonical root, single owner, branch/HEAD, task-owned diff, pre-existing
   WIP and agreed target. Missing/ambiguous upstream blocks publication, not permission
   to choose one. Keep the branch; use agreed PR/branch only when requested.
2. Review the entire intended commit and outgoing range, including untracked files,
   for secrets, private data and unrelated work. Stage explicit reviewed paths/hunks.
3. Make a meaningful conventional commit; fetch the agreed target and prove normal
   fast-forward publication. Do not silently merge/rebase unrelated histories,
   reset, rewrite history or force-push. Conflict, unexpected writer or failed
   required gate stops publication; preserve work and report the blocker.
4. Push promptly and read back the remote SHA: it must match the intended commit.
   Inspect actual CI separately; queued/not run is not green. A failed push means
   committed locally, not synchronized. Inspect push-triggered deployment effects
   before first publication to a new target; resolve unexpected effects.
5. Report canonical root, branch/commit, exact checks/skips, push and actual CI.
   Do not claim full delivery while a required gate/publication is blocked.

One task is one bounded change set in the canonical folder, not another worktree.
PR summaries include business areas, checks, migration/env, permission, notification,
BusinessEvent/AI impact, manual evidence and risks. Standing publication permission
never authorizes new tasks, releases/tags, PR creation, deployment or working-DB migration.

## 7. Checkpoints, interruption and stopping

The current owner updates STATUS.md at scope changes, meaningful results, blockers
and before ending/agreed handoff. Keep it compact: state, decisions, links and next
step. Detailed scope/DoD, Git/dirty ownership, checks, failures/attempt limits, processes
and closed work belong in the existing checkpoint, not another backlog. Update relevant
docs after meaningful changes; update the CRM plan when its scope/status changes and
README only for setup/behavior/public-status changes. Preserve closed evidence/archive
bodies and unresolved approved contracts; do not archive unfinished work as complete.
Never store secrets/full chats or duplicate changing counts across indexes.
Strict read-only work reports context without writing files.

Compaction restores the same task in the same chat after Git/evidence checks.
It does not authorize ownership transfer, new tasks, commits, worktrees, scope expansion
or archive. Do not disable compaction or split scope to manufacture completion.
No background autosave is promised; abrupt closure may leave unsaved progress.

An explicit user command «Передай работу новому чату» invokes the managed handoff
in [SESSION_ROLLOVER](docs/testing/SESSION_ROLLOVER.md). It authorizes one successor
named PlatformaCRM in the same saved project/local canonical folder, its prepared
read-only context prompt, verified ownership transfer and archival of this source.
Follow the protocol without asking again for already-authorized steps. A quotation,
discussion/setup of this command, compaction, window closure or archive-button click
does not invoke it. Reuse an existing transition; never create a duplicate successor.
The command does not waive completion/ownership checks or authorize a product phase.

For an unavailable old chat, perform read-only reconstruction under the
[recovery protocol](docs/testing/SESSION_ROLLOVER.md). Unknown/non-primary/retired
chats cannot appoint themselves owner. An exceptional recovery needs an explicit
owner decision and verified absence of conflicting writers; no registry/hooks are
changed merely by reading STATUS.md. Ordinary handoff retains full DoD, required
checks/publication/actual CI, finished operations and verified successor comprehension.
Only the registered primary initiates it. A recorded pre-validated successor or
registered orchestrator may idempotently finalize only the same confirmed transition
following native archive readback. Unknown evidence keeps it frozen. Hooks are
read-only and separately reviewed/trusted; unit tests do not prove runtime activation.
A governance task cannot close another unfinished task or authorize the next phase.

For checklist work, one authorized phase is the stopping point. "Continue" covers
only current/next phase unless multi-phase work was explicit. A phase is an observable
result with acceptance, not a file count. Do not invent internal approval gates or
extra phases; a blocker never expands scope. Finish all authorized work in the phase,
then report completed items, changes, exact checks/skips, risks and next unfinished
item. After 60 minutes save/report a checkpoint and continue the same phase. Before
ending unfinished work preserve its checkpoint. On resume, inspect relevant delta;
old "continue" messages do not authorize multiple new phases.

## 8. Authenticated UI content

Every visible block must serve navigation, a metric, real business data, an action,
form, list/entity card, chart, integration status, meaningful empty-state action or
system alert. Do not invent decorative/marketing/demo/motivational/explanatory blocks
unless explicitly requested. Dashboard pages show business state, not explain PlatformaCRM.

Copy comes from the prompt, existing page structure, approved content map,
i18n/constants or real API/model fields; do not invent static Russian page text.
Check each new block's purpose, allowed copy source and real backing (data/action/
navigation/form/setting/empty state/status). Fix failing new blocks within scope.
Do not remove an existing functional block merely because a negatively worded review
question got "no". Explicit explanatory requests still require truthful approved content.
