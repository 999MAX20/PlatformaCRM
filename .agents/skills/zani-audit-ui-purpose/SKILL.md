---
name: zani-audit-ui-purpose
description: Audit PlatformaCRM interface purpose, information density, consistency and accessibility using source and browser evidence. Use for a requested interface quality or anti-slop review, not as an automatic redesign mandate for routine changes.
---

# Audit CRM interface purpose

Adapted from Miqdad Badjuber's anti-slop; read [provenance](references/provenance.md)
for the pinned source, license and deliberate changes. This supplementary skill does
not replace AGENTS.md, current frontend/product contracts or zani-review-frontend.

## Scope and evidence

Use the user's existing scope and authorization. An audit means inspection and
recommendations, not permission to fix product code. Do not ask a during/after
question, read global antislop settings, install upstream or introduce approval gates.
Read the relevant current contracts, semantic tokens, shared components and route
metadata. Preserve unrelated WIP and record HEAD plus dirty-source boundary.

Inventory route families and the work users perform: triage leads, progress deals,
find clients, manage tasks, schedule, respond, configure and inspect results. Select
representatives by interaction risk and shared impact, not a fixed screen quota.
Include role, viewport, locale and state in the coverage record. Use a safe isolated
fixture environment for mutations or fault injection. On an existing working stand,
inspect read-only surfaces and unsaved forms; avoid opening messages if that marks
read, sending, saving, acknowledging or altering account preferences. A missing
safe environment is a coverage limit, not permission to seed the working database.

## Purpose before appearance

For each material block, identify its job and backing: navigation, real data/metric,
action, form, entity/list/chart, integration status, useful empty state or alert.
Trace displayed values to the API/model/i18n or approved copy. Existing test/user
records are not fabricated UI. Distinguish examples explicitly labelled as examples.
An unknown backing source calls for investigation; it is not proof of decoration.

Judge hierarchy by whether users can find the next action, deciding field, status,
owner and recovery. Preserve established table/card patterns, semantic badges,
neutral palette, typography and density when they support scanning. Repetition,
sidebar, equal cards, rounded controls or a familiar font are not defects by themselves.
Do not add themes, assets, navigation, asymmetry or motion just to look distinctive.
Do not remove a functional block because a negatively phrased checklist got “no”.

## Review dimensions

- Tables/lists: useful columns, sorting/filter scope, selection, paging, truncation
  with reachable full content, status meaning, and narrow-screen alternatives.
- Forms/overlays: labels, required/optional meaning, error association, retained
  input, disabled/pending clarity, accessible names, keyboard order, nested Escape,
  initial focus, focus containment and return. Inspect shared callers before proposing
  a shared fix. UI checks never prove backend authorization or transaction safety.
- Calendar/Inbox: distinguish scheduled state and delivery state; retain selected
  context, actionable time/owner information and keyboard alternatives to dragging.
- Loading/empty/error/recovery: distinguish first-use, no filter results, forbidden
  and service failure. Preserve valid data during background refresh when appropriate;
  never mask failure as an empty success. Retry must describe the failed operation.
- Text/locales: source RU/KK/EN from established dictionaries; inspect visible values,
  plural/date/currency formatting and longer labels. Use neutral Business/Client/
  Specialist terminology; preserve user-entered industry text and explicit templates.
  Apply grammar and punctuation appropriate to each language, not English-only bans.
- Responsive/accessibility: representative desktop and narrow mobile; zoom/reflow,
  focus visibility, labels, reduced motion and existing themes where applicable.
  Compute contrast from actual foreground/background including opacity and weight.
  WCAG AA text needs 4.5:1; 3:1 applies only at >=24 CSS px regular or >=18.667 CSS px
  bold (18pt / 14pt). 18px regular is normal text. Do not round a failing ratio to PASS.
  Distinguish text contrast, essential non-text contrast and target-size requirements;
  use current W3C guidance when making compliance claims. Screenshots alone do not
  certify WCAG, screen-reader behavior or measured performance.
- Code comments: retain useful business/security invariants, workaround reasoning,
  issue references and version constraints. No line-count cap or unrelated cleanup.

## Report and completion

Record concrete findings with screen/file and line, reproduction/evidence type,
user impact, priority, minimal proposal and follow-up verification. Separate browser
observations, static conclusions, hypotheses and historical evidence. Prioritize
blocked tasks/data risk over friction, then cosmetic issues; do not invent a quota.
Record existing good solutions, coverage gaps and the proposed order of future work.
Report FAIL and untested states honestly; no mandatory all-green Delivery Gate or
numeric “slop score”. An audit does not authorize the recommended implementation.

For skill/report-only changes validate the skill, links, provenance, consistency,
new files and diff hygiene. Exercise realistic decisions (e.g. useful repeated table,
18px contrast failure, read-only failure-state gap) and record outcomes. No app build,
install, database or full E2E solely for Markdown. Product implementation, if separately
requested, follows the repository's proportional verification and publication rules.
