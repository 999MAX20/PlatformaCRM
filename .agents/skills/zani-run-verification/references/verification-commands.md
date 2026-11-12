# Verification Commands

Use [the maintained testing guide](../../../../docs/testing/testing.md), not a
second copied command list. Run from the canonical `C:\Users\user\Desktop\PlatformaCRM`
checkout with a compatible installed interpreter. AGENTS.md prohibits another
worktree, clone or source copy for edits; isolate test databases, ports and queues.

## Select The Relevant Section

- [Verification matrix and evidence](../../../../docs/testing/testing.md#verification-selection-and-evidence): choose required checks before implementation and distinguish docs, local iteration, phase close, release and live acceptance.
- [Deterministic runner](../../../../docs/testing/testing.md#deterministic-local-quality-gate): modes, explicit task base, repeated backend targets and full candidate gate.
- [Before the first task commit](../../../../docs/testing/testing.md#isolated-focused-checks-before-a-committed-range): safe focused checks when base equals HEAD; never substitute an arbitrary older commit.
- [CRM business flows](../../../../docs/testing/testing.md#crm-e2e-business-flow-gates): affected cross-entity and browser evidence without a frozen app list.
- [Controlled pilot QA](../../../../docs/testing/testing.md#controlled-pilot-qa): isolated fixtures and explicit authorization for any working-database mutation.
- [Network policy](../../../../docs/testing/testing.md#external-network-policy) and [hang diagnosis](../../../../docs/testing/testing.md#if-tests-hang): no live provider calls in ordinary automated checks and hypothesis-driven reproduction. Separately authorized live acceptance follows the guide’s explicit target and effect boundaries.

Do not mutate a working database, install dependencies, apply migrations or run
seed/reset merely to validate Markdown. Frontend browser fixtures also need an
isolated database and ports while using the canonical source checkout.

Report exact commands/results, state identity, coverage, environment, skipped
checks and reasons. A preview (`--list-stages`), a rendered UI or a scoped PASS
is not proof that a required full or live gate passed.
