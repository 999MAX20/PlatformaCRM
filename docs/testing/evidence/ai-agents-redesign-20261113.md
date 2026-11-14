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
- Customer overview contains existing Inbox activity and channel status. Test chat
  overlays the right side below the global header without reflow; it uses the saved
  configuration, with no client send or CRM write. The inner messages button is removed.
- CRM work, analytics and staff-only access retain the existing runtime.
- Header retains agent identity, scenario and status; truthful profile/dirty states.
  Readiness disclosure and activation switch were removed by the owner correction below.
- Effective permissions precede action settings; saved unavailable permissions stay.
- Knowledge has a complete read-only view, independent editor and explicit shared
  attachment. Client visibility and knowledge ownership remain separate.
- Existing create/delete, channel setup/OAuth and aliases remain reachable.

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

## Owner correction: compact header

Explicit follow-up scope: remove readiness and on/off switch from the inner header
on all sections and raise the existing content. This supersedes their original
presentation above; backend readiness and activation APIs were not changed.
The now-unused page mutation/props were removed. No replacement activation UI was
added. Agent name, scenario and status badge remain. Other requested changes
(field widths, branch selector, template button and duplicate section headings)
are completed in the compact-configuration follow-up below. Processing-limit
disclosure remains outside that follow-up. Message-button removal and
test-chat overlay were completed in the follow-up below.

Base `1247e507`; canonical checkout/current branch, foreign WIP preserved.
Follow-up checks: build/types/i18n/application/widget PASS; save/retry and keyboard
focus 4 PASS; customer/CRM/staff scenarios 3 PASS. The CRM fixture activates through
the existing API, then tests the same confirmation/runtime behavior; absence of the
removed switch is asserted. Browser matrix 21 section/locale/viewport combinations
PASS (RU1440/KK320/EN768), screenshots captured and visually inspected. Desktop
capture was repeated after the loading transition settled. Geometry, retained
identity and absence of readiness/switch passed; no horizontal overflow.

Follow-up delivery gate PASS: existing tokens/identity, fewer header controls,
responsive geometry, retained keyboard and save recovery. No copy/theme/media,
backend or new state behavior; their broader gates are not rerun for this removal.
Full release/live/deployment not run. No remainder in this first requested step.
Commands/results/failures: `output/ai-agents-header-20261113/`; publication receipt:
`output/ai-agents-redesign-20261113/CHECKPOINT.md`.

## Owner correction: test chat and picker layers

Base `ef316d6e`, same canonical checkout/branch. Removed inner messages button;
RU/KK/EN trigger and title now say Test chat. Fixed right-side portal uses the actual
global-header bottom, one-third viewport width on desktop (minimum360px) and full
phone width; opening does not resize or shift the editor. Escape/close restores
focus; moving focus outside dismisses the nonmodal panel. Local question/history
survive close/reopen for the same agent. Conversation scrolls to new responses;
large text retains readable history with additional panel scrolling.

The supplied picker defect was reproduced by restoring the former stacking classes
temporarily in the browser:99 sampled popup points hit editor content. With the fix,
zero points did. Navigation paints above the isolated editor layer; no menu redesign.

Final scoped regressions8PASS (desktop/mobile), followed by affected save/chat4PASS
after the large-text adjustment. Browser matrix26 assertions PASS, interaction16
PASS (pending/repeat suppression, multi-turn history, resize, keyboard, axe), final
large-text6PASS. RU1440/KK320/EN768 and200% screenshots captured and visually inspected.
Chat and picker axe WCAG A/AA scans reported zero violations. Final build/types/
i18n7299/app/widget and bundle PASS; unchanged locale chunk warnings remain.

Delivery gate PASS within scope: shared tokens and truthful test-only content,
functional controls/recovery, no header overlap/reflow, menu hit-testing, responsive
and keyboard access. No new assets/theme/provider/backend/permission policy.
Initial harness failures retained: mobile link name included unread count; direct
fixture profile lacked business; direct cookie-auth token request returned HTML.
Corrected selector and existing UI save flow passed; no assertion was weakened.
No scoped code/evidence remainder. Fullrelease/live/deployment not run.
Logs/scripts/hashes: `output/ai-agents-chat-panel-20261113/`; same checkpoint holds
publication and cleanup. The compact-configuration follow-up below supersedes the
earlier pending field/branch/template/title items.

## Owner correction: compact configuration and minimal test chat

Base `ebe8f2ab`; canonical checkout/current branch, unrelated WIP preserved.
Owner requested narrower/shorter fields, branch choice, removal of the instruction
template and duplicate headings, and a minimal test composer from the supplied
screenshot. Existing design tokens, saved configuration and preview API retained.

Profile/advanced forms are bounded to576px and instruction/action forms to672px;
desktop inputs/selectors use36px, phone targets44px. Textareas are shorter and
remain editable/resizable. Section navigation supplies context without repeating
the heading above the form. The manual instruction-template button/modal is gone;
existing saved instructions and default agent creation are unchanged.

Branch choice uses existing branch_ids: null means current/future branches;
explicit selection shows named checkboxes. Re-selecting the current mode does not
change the subset. Atomic save/reload retains the subset or null. Loading, failure
with retry and an honest empty list are shown. Backend scope checks are unchanged.

The empty test panel now shows three short message suggestions directly above a
single-row message field and icon send action. No introductory copy or large
warning/result cards. Suggestions fill and focus the editable field. Messages
appear after testing; reset appears only with history. If reply is absent, the
server summary becomes the compact response. Dirty/permission reasons and errors
remain short inline text; pending disables duplicates; failed input survives retry.

Focused browser regressions cover instruction preservation/navigation guards,
atomic-save recovery, keyboard focus, chat error/retry/history/close and actual
branch subset/all save/reload on desktop and phone. Localized visual checks cover
RU/KK/EN320/768/1440, long branch values, 200% text, empty/pending/history/dirty chat,
branch loading/error/retry/empty and no-reply handoff. Representative captures were
visually inspected. Final coverage:16 distinct desktop/mobile UX cases and3 desktop
customer/CRM/staff scenarios PASS across retained runs; browser118 checks, state16
and final7 PASS. Final build/types/i18n7301/app/widget and bundle PASS; unchanged
RU/KK chunk warnings remain. Four editor sections and chat have zero scoped axe
violations. Final results/commands/hashes are in the existing checkpoint.

Preserved attempts: one dependent fixture POST hit SQLite database-locked during
simultaneous browser/test work. Its traceback is retained; final serial retry PASS.
Repeated branch fixtures initially collided on unique names; run-specific names
fixed the harness, and subset/re-select/save/reload/all checks passed twice. The
customer-creation scenario still expected the deliberately removed template;
its assertion now checks absence while retaining default-instruction assertions.
The corrected scenario PASS; no product assertion or threshold was weakened.
Visual inspection caught branch fieldset intrinsic-width clipping and a200% chat
composer overflow. Explicit min-width containment and fixed44px icon targets fix
those cases; final geometry and screenshots verify the controls and labels fit.
The preliminary build preceded these adjustments; final build is the completion gate.

Delivery gate: existing neutral/emerald brand and fonts; no assets/theme/dependencies;
all new controls use real data/actions and localized labels. Small suggestion rows
follow the owner's explicit compact-height request (minimum28px); primary touch
controls remain44px. Keyboard, focus, recovery, geometry and scoped axe checks are
recorded and PASS. React/frontend review retains API-layer calls, functional draft updates,
query reuse, bounded state and existing permission guards; no backend, notification,
BusinessEvent or provider policy changes. Handoff summaries stay outside the sent
conversation history. No scoped code/local-evidence remainder. Fullrelease/live/
deployment are out of scope.

Scripts/logs: `output/ai-agents-compact-20261113/`; screenshots:
`output/playwright/ai-agents-compact-20261113/`. Publication and cleanup receipt:
`output/ai-agents-redesign-20261113/CHECKPOINT.md`. No new roadmap phase is closed;
README/AI/access/operations/CRM contracts need no change for this UI-only follow-up.

## Owner correction: overview cards

Base `c87939f5`, canonical checkout/current branch. Approved scope: centered overview
bounded to 880 px, three clickable preparation cards without counter, compact
channel cards with existing logos, truthful statuses and a selected-channel setup
link. Conversation metrics and their Inbox filters stay unchanged.

Preparation cards retain their links when complete and change the action label to
an explicit completed state. Channel draft/active/paused/error have separate labels;
action text distinguishes finish setup, open settings and check connection.
The overview passes the channel name in the existing editor route. The setup panel
opens only for an existing permitted channel; closing consumes the parameter and
returns focus. Invalid/missing channel and read-only roles never create/open setup.
The shared channel list uses the same status labels. Visual inspection reproduced
an overlap of longer labels at 200% text; its narrow rows now place status below
identity and allow actions to wrap. No provider connection or domain rule changed.

Local acceptance PASS:

- New persistent overview regression: 2 desktop/mobile cases; three card targets,
  selected setup, Escape/focus, query cleanup/reload and invalid query.
- Existing affected atomic-save, draft-navigation and keyboard cases: 6 PASS.
- Browser CLI: 40 interaction checks, 55 localized/layout/completion checks,
  14 loading/error/retry/empty/read-only/denied checks and 6 affected channel-action
  checks PASS. Four additional channel layouts inspected. Repeated runs are not
  additional independent coverage.
- RU/KK/EN at 320/768/1440, 390 px at 200% text, incomplete/complete cards,
  all four channel states, empty and error screenshots captured and representative
  affected areas visually inspected. Nine overview axe scans and the channel
  consumer scan have zero WCAG A/AA findings. Keyboard/Enter/Escape/focus and
  bottom-action reachability checked independently.
- Final build: i18n 7308 keys, TypeScript, app and widget PASS; bundle budget PASS.
  Existing RU/KK chunk-size warnings remain. No full-release certification.

Evidence uses the project's disposable SQLite runtime with dedicated ports and
synthetic data. Actual API creates/listing, UI navigation and saves were exercised;
channel status combinations, readiness completion, permission presentation and
failure responses were injected for deterministic UI checks. No live provider
call, ordinary working DB or new server authorization change is certified here.

Retained failed attempts: fixture login omitted CSRF (replaced by the app's normal
API client); browser cleanup initially used an ambiguous Cancel selector and left
a beforeunload guard (scoped to save bar, guard handled, full run then passed).
The initial persistent test used WhatsApp already owned by the visual fixture;
its ownership-conflict response is retained. The reusable test now uses a per-agent
website channel, keeping all navigation assertions; all four messenger setup
flows were separately exercised. Initial 200% overview overflow and visual channel
overlap were fixed and rechecked; no acceptance threshold was reduced.

Anti Slop during delivery gate, within this change:

- Geometry/mobile PASS: bounded centered overview, three columns to phone stack,
  compact one/two-column channel grid, long localized statuses and 200% reflow.
- Purpose/content PASS: cards navigate to real settings and report API readiness;
  metrics still use the existing Inbox API. No decorative, demo or marketing blocks.
- Interaction/state PASS: real links, explicit action labels, loading/error/retry,
  empty state, safe read-only behavior, preserved drafts and setup focus return.
- Accessibility PASS: native links/buttons, labels, visible keyboard focus,
  44 px phone actions, text reflow and scoped contrast/axe checks above.
- Visual/copy PASS: existing neutral/emerald tokens and Manrope/Noto typography;
  existing provider assets, no new theme/dependency. Icons reuse section meanings,
  arrows identify navigation, check marks convey completion. Equal preparation
  cards follow the explicit owner composition; status color accompanies text.
- Dials and craftsmanship PASS: ENERGY/RHYTHM/MOTION 1/1/1, next setup actions are
  the focal point, whitespace separates preparation/metrics/channels. No invented
  claims or fields. Theme switching, hero media, marketing and field-performance
  claims are N/A to this scoped authenticated screen.
- React/frontend review PASS: existing API/query layers, typed props, derived URL
  selection without an opening effect, functional query cleanup and no new fetch
  or external effect. Only the affected status consumer needed responsive changes.

Current frontend contract and CRM-agent passport match this result. No roadmap
phase or D01 acceptance advanced; README/AI/access/operations/CRM contracts need
no change because their behavior is unchanged. No scoped code/local-evidence or
owner-decision remainder. Live provider/deployment remains outside this task.
Commands, hashes, attempts and publication receipt:
`output/ai-agents-redesign-20261113/CHECKPOINT.md`; scripts/logs:
`output/ai-agents-overview-20261113/`; screenshots:
`output/playwright/ai-agents-overview-20261113/`.

## Owner refinement: preparation CTA, centered metrics and full-size logos

Base `3baf814f`, canonical checkout/current branch; unrelated WIP preserved.
Owner explicitly requested stronger completed/required states, an explanation
above preparation, centered conversation metrics kept on the overview, and logos
filling their icon area across channels and connections. This supersedes only the
previous preparation presentation; navigation/readiness/metrics behavior is retained.

Completed cards use the existing success surface, check mark and explicit Completed
label. Required cards have an explicit Required step label and a solid action area;
the whole card remains one native link. The requested intro explains that all three
steps precede launch. Completion copy acknowledges preparation, not activation or
live-provider readiness. RU/KK/EN use the same meaning and server readiness inputs.
Metrics use three centered columns and a centered phone stack; API counts, empty/
loading/error handling, retry and exact Inbox URL filters remain unchanged.

Shared LogoMark now renders the original image at the full 36/44 px icon size,
without an extra frame, shadow or padding. Object-contain preserves asset proportions;
explicit dimensions reserve space. Existing initials are retained for providers
without an image. Callers reviewed: overview, channel list, messenger setup header
and integrations ProviderCard. No new assets, dependencies or provider operations.

Local acceptance PASS: 4 affected desktop/mobile overview-navigation and atomic-save
regressions; 64 browser visual/state/keyboard checks; 31 shared-consumer/metrics
checks. Overview RU/KK/EN320/768/1440 and390px at200% text captured; mixed and complete
states visually inspected. Nine scoped axe scans report zero violations. Full-size
WhatsApp/Telegram/Instagram logos were checked in list and setup at320/1440;
1C in the reachable integrations catalog at both sizes. Representative captures
visually inspected. All three setup windows close with Escape and return focus.
Metric loading/failure never display invented zeros, retry restores real data,
and all three nonempty metric links retain their filters. No failed acceptance run.

Final build/types/i18n7313/app/widget and bundle PASS. Existing RU/KK chunk warnings
remain. The disposable project runtime and synthetic fixtures were used; mixed
readiness is real fixture data, all-complete readiness and metric503 are response
injections. No working DB, live provider, deployment or full-release gate in scope.

Anti Slop during delivery: purpose/copy PASS (owner-requested explanation, explicit
real states/actions, no activation promise); geometry/responsive PASS (centered
metrics, reflow, full icon bounds); accessibility PASS (native links, visible focus,
text+icon states,44px metric/CTA targets, scoped contrast/axe and200%); craftsmanship
PASS (existing tokens/fonts,1/1/1 dials, required actions are the focal point,
unchanged brand assets and source proportions). Theme/marketing/media/performance
field measurements N/A. React/frontend review PASS: simple derived state, no new
requests/effects/dependencies; existing API/permissions and save/navigation retained.

Frontend contract and CRM-agent passport updated. README, roadmap/D01 and AI/access/
CRM/integrations/operations contracts need no change: no domain, policy, endpoint,
provider setup behavior or environment changed. No scoped code/evidence/environment/
owner-decision remainder. Logs/scripts: `output/ai-agents-cta-20261114/`; screenshots:
`output/playwright/ai-agents-cta-20261114/`. Exact commands, hashes, publication/CI
and cleanup: `output/ai-agents-redesign-20261113/CHECKPOINT.md`.


## Instruction editor — 14.11.2026

Owner selected only the first instruction-audit phase: explain role/main instruction/
reply-rule purposes, link to Actions and expand the main instruction while preserving
current design. Existing user text/default prompts and backend behavior are unchanged.
Inline expansion shares the original field/value; collapse and Escape retain edits,
Escape returns focus, including view-only use. The Actions link stays within the
selected agent and retains all editor drafts. Hints are programmatically associated
with fields. Customer and CRM action explanations reflect their different scopes.
RU/KK/EN use existing typography/tokens/components; no assets or dependencies added.

10 distinct desktop/mobile browser cases verified across final and serial runs:
customer/CRM expansion, keyboard/Escape, long/empty input, Actions/back, real atomic
save/readback/reload/cancel, exit guard, failed-save recovery and focused field visibility.
The initial batch retained two stale language-selector failures; existing foreign
profile WIP renamed Language to Fallback language. The selector now accepts either
exact label prefix; assertions are unchanged. The second batch had one SQLite-lock
failure during CRM fixture creation; the four affected expansion cases passed serially
after closing the visual browser. Logs and traces retained, not relabelled as PASS.

CLI visual-final:84 checks PASS, including nine scoped axe scans with zero violations,
RU/KK/EN320/768/1440, expanded/compact states and200% text. States:13 checks PASS for
no extra saves/AI calls, pending disable, retained failed-save input/expansion, actual
retry/readback and view-only controls/navigation. Screenshots captured and representative
compact/expanded desktop/mobile/tablet,200%, failure and view-only images inspected.
Initial fixed13px expand-button text did not scale at200%; changed to shared text-sm
and rechecked. Keyboard handler covers the field and its toggle.

Anti Slop during delivery: purpose/copy PASS (requested field guidance/navigation,
no fabricated business facts); geometry/responsive PASS (bounded form, wrapped controls,
long text and200%); accessibility PASS (labels/descriptions, keyboard/focus, scoped axe);
craftsmanship PASS (one draft/save path, recovery and view-only behavior). Existing
neutral/emerald direction, fonts and1/1/1 dials retained. New media/theme/motion N/A.
React/frontend review: local expansion state and refs, stable IDs, no new effects,
network layer or runtime permissions. Build/types/i18n/widget/bundle receipt and
source hashes are recorded in the checkpoint after final completion.

Evidence boundary: canonical checkout, base d2e3518d plus reviewed task delta and
preserved foreign WIP; disposable SQLite, dedicated ports, mocked providers. The
view-only UI case uses permission-response injection. No backend/full-release/live
provider/working-DB/deployment certification. No code/UI-evidence remainder in this
selected phase; draft-before-apply, version history and other audit proposals are
not implemented or implicitly authorized. Current frontend contract/passport/status
updated; roadmap/D01, README, AI/access/operations/CRM contracts unchanged in this
scope because domain/API/policy/setup behavior did not change.

Commands and publication/CI: output/ai-agents-redesign-20261113/CHECKPOINT.md.
Logs/scripts: output/ai-agents-instructions-20261114/.
Screenshots: output/playwright/ai-agents-instructions-20261114/.


## Side hints, 14.11.2026

Owner approved moving the instruction guidance beside the fields, preserving the
existing design. Container threshold60rem keeps the form stacked until a field up to42rem
and a16–18rem hint fit. Each row aligns its own field/hint; examples are separate
paragraphs, existing text retained in RU/KK/EN. Main instruction now owns the Actions
explanation/link and its accessible description; short reply rules retain their own
hint. This grouping reduced the first side-layout prototype from688 to588px in the
observed RU desktop form; this is not a measured comparison with the previous commit.
No backend, prompt default, permission or save behavior changed.

Final10 existing desktop/mobile regressions PASS: inbox/CRM expansion, Escape/focus,
Actions/back and draft retention, real save/readback/reload/cancel, failed-save retry,
exit guard and field visibility. Initial10PASS overlapped the grouping edits and is
not final evidence; final rerun after all source edits also10PASS. Build/types/i18n7324,
app/widget and bundle gate PASS; existing RU/KK chunk warnings remain within policy.

Chrome extension CUA inspected actual page and isolated fixtures. Measured RU/KK/EN
wide hints stay beside672px fields;1280/768/390/320 layouts stack with no horizontal
overflow. English/KK/RU desktop and narrow screenshots captured and visually inspected,
including expanded KK editor and lower English/Russian fields.200% root font verified
as28px hints at1440/390 with reflow, visible focus and reachable lower content.
Text color #4f5e58 on #f6f8f7 measured6.40:1. Browser geometry/details/images:
output/ai-agents-side-hints-20261114/browser-layout.json and sibling JPGs.

A full-page CDP screenshot timed out; documented diagnostics and changed capture
mode restored normal target-page screenshots. OS text-scale emulation did not change
actual desktop font size, so it is NOT200% evidence; a temporary root-font override
provided verified200% evidence and was removed. One early1280 screenshot captured a
stale paint after resizing;1280 geometry and later tablet/mobile images are separate
proof. No screenshot error was represented as loss of page access. Test-only account
locale was restored to RU; viewport reset; only own extra tabs closed. Working data
and user's original browser tab preserved. No new dependencies, assets or theme.

Anti Slop delivery: purpose/readability, per-field grouping, responsive geometry,
keyboard/descriptions/contrast and functional regression PASS within this boundary.
No new fetching/error/permission state was introduced. Existing10-scenario recovery
coverage rerun; screen-reader, fullrelease, liveAI and backend certification not claimed.
No scoped code/local-evidence remainder. Frontend contract/passport/status updated;
roadmap/D01 and README/API/AI/access/operations/CRM policy unchanged by this layout.
Publication, exact commands, source hashes and cleanup: existing redesign checkpoint.
