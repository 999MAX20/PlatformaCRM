# Records table, drawer and filters, 04.11.2026

Owner annotation1 approved the previously described interaction changes.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD66101d509cb7642b2928275e48c4b64354abf07b plus preserved foreign WIP.
Plan, starting status/diff, disposable fixture and logs: output/records-drawer-20261104.

Implemented: client-first columns; client link vs row/Enter drawer; existing pagination;
colored calendar navigation; removed toolbar plans/reset; anchored draft filters,
apply/cancel/Escape/outside, full reset on apply. Existing16px grid reused.
Drawer reuses CRM card/API commands, backend update capability, comment editing,
reschedule form, linked plan with unscheduled steps, timeline/tasks and attachments.
Client workspace retains access to all plans, including a plan without appointments.
Legacy table caller retains full-card opening when no drawer callback is supplied.

Scoped verification complete on the local dirty snapshot. Command:
`.venv/Scripts/python.exe output/records-drawer-20261104/run.py`.
Uses scripts.codex_verify.isolated_runtime, guarded browser fixture setup,
temporary SQLite/media/ports, disabled external providers, existing dependencies.
No ordinary database writes or working migrations; migration/seed only disposable.
Initial build failures: missing JSX closure in plan panel, then required onOpen
prop in LegacyRecordsPage consumer; both corrected. No failed attempt is a PASS.

Final run1793804779924363300: Node8 PASS; TypeScript/i18n6685/app/widget build PASS;
Playwright7 PASS (1.4m). Logs are timestamped under the output directory. The7 cases:

- RU1440px, KK390px and EN390px: column ordering, independent client link, row/Enter
  drawer, real PATCH note save, nested reschedule Escape, plan/undated step rendering,
  client access to a plan with no appointments, page-size selection, filter draft/apply,
  reset/cancel/outside/Escape/focus, no table shift and no document horizontal overflow.
- Real read-only role:503 card recovery, readonly comment, disabled save and absent
  lifecycle/reschedule controls. Injected503 is an explicit browser failure fixture.
- Real confirmation/early completion, required reason, terminal action removal;
  injected first503 followed by refresh and successful real command.
- Real reschedule with a deliberately delayed request: Escape preserves the pending
  form; after success immediate cancellation succeeds with the new version/reason.
- Calendar full card retains the five applicable actions; existing client drawer
  still opens in place and closes with Escape.

Two product defects found by this cycle were fixed and rechecked: nested Escape
closed the parent after its child; the shared handler now respects defaultPrevented.
Immediate cancellation after reschedule captured the old version and returned409;
the reschedule dialog now waits for card invalidation/refetch before closing, and
lifecycle controls wait for refresh. Initial harness errors (dictionary modules and
Select accessible names including values) remain in earlier logs, not counted as PASS.
KK common.reset was Russian; corrected to «Қалпына келтіру», checked in the final KK flow.

`node scripts/check-bundle.mjs` from the frontend directory PASS:
app-shell343.0kB <400kB. Advisory warnings remain
for the existing large RU/KK dictionaries (>500kB); no blanket bundle-size improvement.
Working/index diff hygiene and new-file/registry/link checks PASS. No new own committed
range exists; no invented base or unrelated full backend/E2E/release gate was run.
Final screenshots: ru-1440.png, kk-390.png, en-390.png, drawer-{ru,kk,en}.png,
drawer-plan.png and filters-{ru,kk,en}.png. Visual review confirms full client heading,
two-column desktop metadata,16px separation, neutral terminology and mobile wrapping.
Final hashes: output/records-drawer-20261104/final-source-manifest.json.
Own test servers stopped automatically; final dedicated ports have no listeners.

No backend/domain/API/AI/notification/BusinessEvent change. No full suite or live
certification in this frontend scope. Roadmap requirements, CRM/access/AI/integrations,
operations/README need no change: no new domain behavior, setup or release claim.
Frontend contract and scheduling passport updated; historical evidence preserved.

Publication blocked by existing .git/index.lock and unrelated outgoing commits/WIP.
No foreign work staged, no push/deployment; actual new CI unavailable until publication.
Remote read-back04.11: origin/main0b3348e1ab31121a106badbde830b496ec477aac;
local HEAD remains66101d509cb7642b2928275e48c4b64354abf07b. No own commit.
There is no remaining implementation/local verification item in the approved scope;
publication remains blocked separately. No production, live worker or release acceptance.

## Scoped design gate

This reviews the changed Records surfaces and reused components in the named flows;
it does not certify every pre-existing screen, theme, browser or screen reader.

- R02 PASS: new visible copy uses existing i18n; date-range punctuation retained.
- R03 PASS: RU1440/KK390/EN390 screenshots and document-width assertions.
- R17 PASS: table counts come from workspace API; no invented metrics.
- R18 PASS: no testimonials.
- R23 PASS: existing CRM navigation/icons/tokens; synthetic fixture only in isolated tests.
- R24 PASS: client/calendar/plan links lead to existing reachable routes.
- R25 PASS: existing semantic text/surface/brand pairs retained; verify-docs.py checks
  seven used normal-text pairs against4.5:1. No full application contrast audit claimed.
- R26 PASS: real note/status/reschedule APIs and filter/navigation handlers exercised.
- R27 PASS: existing loading/empty views retained; card503 retry and read-only checked.
- R28 PASS: no FAQ.
- R32 PASS: row Enter, Escape layering, focus return and native labelled controls checked.
- R33 PASS: source changes through explicit patches; no runtime DOM/CSS patching.
- R34 PASS: no theme switch or theme-specific changes introduced.
- R35 PASS: final build and the7 named browser scenarios.
- R36 PASS: no security/commercial claims in UI.
- R37 PASS: owner-approved operational table/drawer/popover direction.
- R38 PASS: runtime data from scoped APIs, fixtures explicitly synthetic.
- R39 PASS: focusable row with pointer/hover, native buttons/links, localized names,
  existing label/disabled conventions; no new image or continuous animation.
- R40 PASS: no media, third-party scripts or performance claims added.
- R01 PASS: no new gradient/glow.
- R04 PASS: calendar/filter/branch/service/specialist icons identify their controls/data.
- R06 PASS: existing CRM typography; metadata labels use existing SummaryItem.
- R07 PASS: no background pattern.
- R08 PASS: no decorative arrows.
- R09 PASS: statuses and active filter count reflect actual state.
- R10 PASS: existing drawer backdrop only; no additional glass surfaces.
- R12 PASS: shared popover elevation separates temporary controls from the table.
- R13 PASS: no new glow.
- R14 PASS: metadata cards represent actual fields, not generic feature claims.
- R19 PASS: existing drawer transition only; no new motion introduced.
- R22 PASS: no illustrations.
- Dials PASS: ENERGY1/RHYTHM1/MOTION1, declared in PLAN before implementation.
- Dials consistency PASS: calm existing CRM grid; hover/focus and reused drawer motion.
- Focal point PASS: table and selected appointment remain the working objects.
- Whitespace PASS:16px groups toolbar/table; metadata/notes/plan sections separate actions.
- Accent PASS: existing emerald primary actions; user explicitly requested calendar color.
- Identity PASS: existing CRM tokens, controls, typography and shared drawer.
- Design read PASS: operational CRM for staff, table overview/detail drawer, existing tokens.
- C1 PASS: layout, spacing, color and icons have task-specific reasons above.
- C2 PASS: reachable real actions and recovery exercised.
- C3 PASS: each new block is a control or entity/plan state.
- C4 PASS: desktop/mobile/keyboard/readonly/error boundary checked in named flows.
- C5 PASS: no fabricated claims; test data confined to temporary runtime.
- R05 PASS: operational table/detail structure, no marketing template.
- R11 PASS: existing control/card radii.
- R15 PASS: explicit create/calendar/apply/reset/reschedule actions.
- R16 PASS: no marketing buzzwords.
- R20 PASS: established product design language retained.
- R21 PASS: established product theme retained; no new theme policy.
- R29 PASS: existing emerald/neutral palette and semantic statuses.
- R30 PASS: no product clone or unrelated redesign.
- R31 PASS: major decisions tied to the approved interaction and existing design tokens.
