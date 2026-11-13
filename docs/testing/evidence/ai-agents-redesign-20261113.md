# AI-AGENTS-REDESIGN-20261113

Owner-authorized redesign of `/app/ai-agents` using the agreed structure and
references. Scope is the existing agent editor; no backend, schema, provider,
working database, permission policy or unrelated feature changes.

Canonical root: `C:/Users/user/Desktop/PlatformaCRM`; current branch
`codex/ui-testing-toolkit`; starting HEAD `1421a11184a035e83313d03a66cc81290be7be66`.
All pre-existing WIP is foreign and preserved. Publication is recorded separately
after required acceptance. Current state: scoped implementation and local acceptance passed.

## Implemented behavior

- Named agent picker, direct local section navigation, responsive section menu.
- Separate profile, instructions and advanced settings; existing atomic save,
  field values and JSON retained; draft guards remain.
- Customer overview contains existing Inbox activity and channel status. Context
  testing uses the saved configuration, with no client send or CRM write.
- CRM work, analytics and staff-only access retain the existing runtime.
- Compact readiness with full diagnostic disclosure; truthful profile/dirty states.
- Effective permissions precede action settings; saved unavailable permissions stay.
- Knowledge has a complete read-only view, independent editor and explicit shared
  attachment. Client visibility and knowledge ownership remain separate.
- Existing create/delete, channel setup/OAuth, activation and aliases remain reachable.

## Verification boundary

Disposable SQLite/mock runtime only, source rooted in the canonical checkout.
No live model/provider calls, working database writes, real messages or deployment.
Browser fixture accounts/data are synthetic. Runtime and exact commands/results,
failure history, source hashes and owned process cleanup are retained in
`output/ai-agents-redesign-20261113/CHECKPOINT.md` and adjacent logs.
Screenshots and interaction scripts:
`output/playwright/ai-agents-redesign-20261113/`.

Initial scoped 12 browser cases: 10 passed; 2 failed on the new helper's incorrect
exact Select name. The corrected atomic-save scenario passed desktop and mobile,
including a synthetic 503, retry and persisted fields/JSON. Dependent CRM dialogue
history and explicit confirmation/retry scenarios passed. Fixture collisions and
agent-limit failures in the first combined dependent run are retained; sequential
scoped runs isolate their inputs. These are not product acceptance failures erased
by weaker assertions.

Final checks: UX suite 12 PASS plus keyboard regression 2 PASS; dependent dialogue
continuity/confirmation 2 PASS, isolated knowledge 2 PASS, scenarios 3 desktop and
3 mobile PASS. Browser matrix 26 localized views, preview 22 assertions, picker
15 assertions and 8 channel-dialog checks PASS. Seven customer sections and CRM
analytics in RU/KK/EN reported zero scoped axe WCAG A/AA violations. Screenshots
were captured and visually inspected, including 320/390/768/1440 widths, 200% text,
long names, preview, knowledge, channel dialogs and CRM work/analytics.

Final `python output/ai-agents-redesign-20261113/check.py build` PASS (i18n 7299 keys,
TypeScript, application and widget); `check.py bundle` PASS. Existing locale chunks
over 500 kB remain warnings; app-shell budget is met. Backend suites, full release,
live providers, working database and deployment are not required by this UI scope.
No scoped code/local-evidence remainder. Publication and actual CI receipt are in
the checkpoint; CI is separate from the local acceptance reported here.

## Delivery gate (affected scope)

- Hard gate PASS: real API data/actions, no fabricated statistics/assets, 26 layout
  checks, seven-section axe result, keyboard/Enter/Escape and recovery evidence.
- Purpose PASS: existing emerald selection and primary actions identify the active
  context; icons identify settings, knowledge, channels and test; borders separate
  forms; no decorative blocks or unsolicited imagery were added.
- Direction PASS: approved reference composition within PlatformaCRM tokens;
  restrained energy, section-based rhythm and minimal motion. Agent identity and
  current section form the focal point; spacing separates navigation/editing/testing.
- Craft PASS: atomic-save retry preserves fields/JSON, independent knowledge save,
  draft guards, permissions, disabled states and responsive focus were exercised.
  Existing data stays in its original language; RU/KK/EN interface keys align.
  Theme/media/marketing-specific checks are N/A: no new theme, media or marketing.

React/frontend checklist: shared controls and API hooks reused; effect handlers
clean up; no new provider calls, dependencies or raw component requests; queries
remain conditional. No new permission, notification, BusinessEvent or AI policy.

Full release certification, live providers, production and wider roadmap acceptance
are outside this UI change. AI/access/operations contracts and README need no
behavior/setup edits; frontend contract and module passport describe the new UI.
