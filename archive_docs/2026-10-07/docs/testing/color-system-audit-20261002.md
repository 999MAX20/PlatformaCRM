# Whole-CRM color audit — 2026-10-02

Status: implementation and scoped local acceptance are complete. This report
distinguishes inventory, observed defects, repairs and verified coverage.
Execution ownership and publication receipt belong to the
[primary checkpoint](task-state/PRIMARY-SESSION.md).

## Contract and snapshot

- Canonical source: `C:/Users/user/Desktop/PlatformaCRM`, existing branch
  `codex/ui-testing-toolkit`, starting commit
  `10abfbe3a670ecc2e2f875193fffe7545ded483d`. All changes in this package are
  task-owned; no alternate source checkout or parallel writer was used.
- The 35 values in [semantic-tokens.json](../../frontend/src/theme/semantic-tokens.json)
  exactly match the owner-approved CRM/Market JSON. The JSON takes precedence
  over generated reference images. Tailwind and the embedded widget read that
  versioned source; legacy CSS variables adapt to it.
- Scope is colors and visual interaction states across existing CRM surfaces.
  Geometry, workflows, logo assets, RU/EN Manrope and KK Noto typography remain.
  A new tag's default color follows the palette; existing user tag/stage colors
  are preserved. There are no backend, API, permission, lifecycle, notification,
  BusinessEvent, AI execution, migration or production environment changes.
- Source inventory: 84 explicit router path declarations and 413 TS/TSX/CSS/SVG
  files in `src`, `widget/src` and `public`. The token JSON and Tailwind adapter
  were also reviewed. The inventory is derived from the real router, not a
  remembered navigation list.
- Local evidence is under `output/emerald-palette-20261002`. Browser runs use
  `scripts.codex_verify.isolated_runtime`: disposable SQLite/uploads, separate
  loopback ports, local mail, disabled external providers and eager workers.
  Ordinary working data and another person's servers were not used.

## Findings and repairs

| Finding | Evidence | Repair |
| --- | --- | --- |
| CSS/Tailwind and local utility drift | Duplicated warm palette, local neutral/status shades, old auth/widget colors | One versioned semantic source, alpha-aware adapters, shared controls and local color roles |
| Warning pressed text contrast | Initial component run measured 4.09:1 | Derived warning hover/pressed mixing reduced to 4%/8%; canonical values unchanged |
| Faded integration metrics/cards | Metric labels/details 2.83–3.92:1; unavailable card text as low as 2.57:1 | Full-opacity semantic text; only actual disabled controls use disabled colors |
| Platform sidebar descriptions | 35%/45% white produced 3.2–4.38:1 | Existing dark sidebar retained; secondary inverse text uses 70% white |
| Muted text on row/card hover | Approved muted/hover pair measured 4.47:1 | Affected lead metadata and dashboard hints use `text.secondary` |
| Transparent fixed mobile navigation | `bg-surface-card/96` did not generate CSS; content behind labels produced 1.03:1 | Explicit `[0.96]` alpha; equivalent unsupported 92% surfaces and 16% ring fixed |
| Missing soft-background alpha utilities | Hex-valued `bg-[var(...)]/60` and `/45` selectors were absent | RGB-aware `dangerSoft`/`warningSoft` aliases; exact browser RGBA assertions |
| Remaining local disabled opacity | Action/file menus, composer, knowledge templates, preference switches, calendar slots and audience selection | Explicit approved disabled colors, retaining each control's geometry and behavior |
| Faded readable content | Archived service rows and small analytics/audience text used container/text opacity | Muted surface or full-opacity semantic text; archived data stays readable |

The broad collector completed 444 page visits in 16 scenarios (desktop/mobile,
including two static alias-registry checks). It found no old palette colors or
outer horizontal overflow, but recorded **165 contrast-node findings**, including
repeated instances of shared defects. Its process PASS was **not** a contrast
acceptance PASS. The findings above were repaired and the affected surfaces are
subject to strict follow-up assertions. Future runs of the broad test also fail
on recorded contrast violations.

Two fixture-discovery mistakes were corrected: conversation IDs come from
`/api/inbox/conversations/`, and AI-agent routes use bot IDs from `/api/bots/`.
The follow-up explicitly visits actual conversations and all five AI sections
(`profile`, `knowledge`, `actions`, `channels`, `test`) for each business role.

## Browser and component boundaries

Browser coverage uses desktop and Pixel 7 mobile Chromium. The existing workspace
and typography suites also cover tablet. Each broad observation records the
requested and actual route, permission/error state, computed colors, screenshot,
overflow and axe contrast findings. A rendered error/empty state is not evidence
of a populated successful workflow. A denied page is not evidence of its hidden
authorized content.

| Component family | Examined states and evidence |
| --- | --- |
| Buttons and semantic actions | Exact default/hover/pressed colors, normal text contrast, keyboard focus, disabled and loading; brand/neutral/warning/danger/AI |
| Input, textarea, select | Default/hover/focus, invalid, read-only, disabled, open and keyboard-selected option; actual create/edit forms |
| Checkbox, radio, switch | Keyboard selection/accent/focus; shared disabled switch; local preference pending/recovery scenario |
| Tabs, filters, pagination, lists | Selected/focus states; real leads/clients search/filter/columns and failed-list recovery; deal board/table pagination |
| Cards, metrics and tables | Shared metric tones, integration unavailable cards, dashboard/lead hover, expanded analytics, archived services |
| Menus and tooltip | Actual shared action menu disabled colors, keyboard close; existing conversation tooltip hover colors |
| Dialogs and drawers | Real create-lead/edit-client/archive dialogs, disabled/ready archive confirmation; shared overlay and CRM detail components reviewed |
| Header/sidebar/mobile navigation | Actual role-specific surfaces, exact mobile background alpha, selected links and existing platform dark sidebar |
| Auth and public surfaces | Login/signup/recovery/invitation/MFA/documents/not-found; successful auth/reset/invitation/MFA regression flows use isolated fixtures |
| AI, integrations, settings | All reachable top-level routes; settings anchors; actual AI sections; local forms and conditional statuses reviewed in source |
| Embedded widget | Open, input focus, busy/disabled and 503 recovery; request intercepted before external delivery |
| Typography and geometry | Existing RU/KK/EN switching and actual font-family tests; preserved CRM workspace coordinates and responsive controls |

There is no claim that every possible data-dependent overlay, custom role,
provider wizard or arbitrary user color was exercised in a browser. Source-only
coverage and exclusions are listed below. Automatic contrast results are scoped
to the rendered states; they are not a complete WCAG certification.
`OutreachPage` currently has no router entry: its local controls were reviewed
in source, and visiting `/app/outreach` only checks the existing not-found page.

## Justified local color exceptions

The final source scan reports ten files containing literal colors or SVG color
attributes. These were reviewed rather than blindly recolored:

| Location | Reason |
| --- | --- |
| `BusinessSettingsForm.tsx` | Example value in the user's business color field, not a fixed UI theme |
| `AvatarCropper.tsx` | Black crop mask; content manipulation, not brand color |
| `authExperience.css`, `authExperienceMobileFix.css` | Dormant, not imported into the current route graph; historical styles retained |
| `authLoginSerenity.css` | White inverse surfaces/text and black decorative mask; actual themed colors use aliases |
| `calendarUtils.ts` | Categorical specialist/resource colors, not success or selection semantics |
| `ClientInspector.tsx` | WhatsApp identity marker |
| `ConversationItem.tsx` | Channel identity markers |
| `TaskList.tsx` | SVG `currentColor`, inheriting the semantic text role |
| `styles.css` | Existing discovery/AI-border extensions and neutral shadow/backdrop values |

The Tailwind adapter retains the same discovery and AI-border extensions.
White/inverse utility colors, provider/logo raster assets, QR codes, uploaded
media and user-selected stage/tag colors remain intentional. Calendar picker
`disabled:opacity-0` represents empty grid placeholders, not faded readable
controls. Animated/decorative opacity remains intentional.

## Checks and limitations

`verify.py` below is the task-local helper at
`output/emerald-palette-20261002/verify.py`, invoked from the canonical root
with `.venv/Scripts/python.exe`. It wraps the documented isolated runtime.
The `node --test` and `npm run check:bundle` commands run from `frontend`.

- `verify.py controls-complete e2e/action-color-roles.spec.ts
  e2e/emerald-palette.spec.ts e2e/widget-colors.spec.ts
  --config=playwright.action-colors.config.ts`: **8 PASS**, desktop/mobile.
- `verify.py details-final e2e/color-system-details.spec.ts
  --project=desktop-chromium --project=mobile-chromium`: **16 PASS** after the
  first audit repairs, before the final local-disabled additions. Preserved as
  intermediate evidence, not the final candidate's complete gate.
- `verify.py build`: **PASS** after the final product edits (TypeScript, i18n,
  app and widget). `npm run check:bundle`: **PASS**, all chunks below 500 kB and
  app shell below 400 kB.
- `node --test scripts/tests/action-color-policy.test.mjs
  scripts/tests/action-feedback-policy.test.mjs
  scripts/tests/daily-workspaces-policy.test.mjs
  scripts/tests/ui-toolkit-policy.test.mjs scripts/tests/login-page-policy.test.mjs`:
  **34 PASS**, no skips. Unsupported numeric alpha scan: **0 remaining**.
- `verify.py acceptance-fixed e2e/color-system-details.spec.ts
  e2e/crm-workspaces-reference.spec.ts e2e/crm-workspaces-deals.spec.ts
  e2e/kazakh-typography.spec.ts e2e/pilot-auth.spec.ts
  e2e/pilot-password-reset.spec.ts e2e/pilot-invitations.spec.ts
  e2e/account-mfa-qr.spec.ts`: **56 PASS, 13 conditional skips, 3 FAIL,
  3 not run**. This combined invocation is not reported as PASS. The detailed
  color suite produced **233 strict snapshots with zero contrast violations**.
- `verify.py remaining-mobile e2e/color-system-details.spec.ts
  e2e/pilot-auth.spec.ts e2e/pilot-password-reset.spec.ts
  e2e/pilot-invitations.spec.ts --project=mobile-chromium
  --grep 'archived service|password reset|owner signup|new employee'`:
  **5 PASS**, including previously failed/not-run mobile scenarios.
- `verify.py remaining-desktop-tablet e2e/color-system-details.spec.ts
  e2e/pilot-password-reset.spec.ts --project=desktop-chromium
  --project=tablet-chromium --grep 'archived service|password reset link'`:
  **3 PASS, 1 conditional skip** (tablet color-details is intentionally excluded).
- Across the combined and focused completion runs, all **62 distinct applicable
  scenarios pass**, with **13 distinct conditional skips**: nine tablet color
  detail scenarios and four desktop-only workspace/deal geometry scenarios on
  tablet/mobile. The mobile archive and desktop reset reruns duplicate prior
  passes and are not counted twice. The component/widget8 are separate.
  The corrected desktop archive/recovery adds two zero-violation snapshots;
  the mobile repeat adds two more. The earlier233 snapshots remain valid for
  unchanged product inputs.
- Committed-range static gate and publication/CI: **PENDING**.

The initial component iteration failed on warning pressed contrast and an
inaccurate select locator; both were corrected, then rerun. An earlier partial
route collection was intentionally stopped before the consistent broad run;
it is not counted as final coverage.
The first combined acceptance attempt also stopped after a new test timed out:
its live `details:not([open])` locator lost the second item when the first opened.
The trace identified that selector; the test now uses stable `details` locators.
This required no application change. The stopped run is not counted as PASS.

The completed combined run found a second test-selector defect: the service
test selected a hidden mobile article before the visible desktop row. Its
locator now explicitly targets the visible responsive variant. Assertions and
application code are unchanged. The two other failures were password-reset
requests reaching the existing shared-IP `5/hour` limit (HTTP429); one prevented
the tablet replay assertion and the next prevented mobile reset initiation.
Fresh, smaller disposable runs retain the original400/401 assertions and the
production throttle; no backend/throttle change was made. An attempted parallel
`reset-fresh` run timed out during web-server startup before any test ran;
subsequent focused runs are sequential. All failed attempts remain in the logs.

Actual-ID follow-up: owner/administrator have a seeded bot and conversation;
manager/operator have a conversation but no accessible bot; specialist has
neither. The latter AI/detail observations prove the applicable denied or
missing-data surface, not a populated workflow. Each allowed bot is visited
in all five existing sections. These findings supersede the broad collector's
incorrect initial entity lookup, without relabeling unavailable content as tested.

No working database migration, live delivery, provider/AI action, deployment or
full local backend/security suite was run for this color-only scope. Successful
password-reset tests prove local token consumption, not SMTP delivery. Widget
and preference recovery intercepts prove UI recovery, not a production outage.

A separate non-color defect was observed: `/invite/invalid` causes the existing
invitation-preview API to return 500 for a malformed UUID, and the UI shows its
generic error state. This backend path is unchanged; it was recorded without
expanding the authorized color task. Valid invitation acceptance is checked
separately. Missing/unassigned entity fixtures and existing platform placeholder
pages are explicitly not presented as completed business workflows.

## Route matrix

Generated from the real router and broad observations. `B` means a rendered
surface, `D` permission denial, `E` visible error/missing entity, `R` redirect or
canonicalized URL, and `S` source/alias-registry inspection only. Codes describe
coverage, not business certification. Follow-up observations supersede the
incorrect initial conversation/AI fixture lookup where those routes are allowed.

<!-- ROUTE_MATRIX -->

O owner; A administrator; M manager; Op operator; Sp specialist. Unless noted,
the observations exist at both desktop and mobile sizes. P is platform admin.

| Path | Source component / redirect | Coverage |
| --- | --- | --- |
| `/app/dashboard` | `DashboardPage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/account` | `AccountPage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/leads` | `LeadsPage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/leads/:id` | `LeadWorkspacePage` | O: B; A: B; M: E; Op: B; Sp: E |
| `/app/deals` | `DealsPage` | O: B; A: B; M: B; Op: D; Sp: D |
| `/app/deals/:id` | `DealWorkspacePage` | O: B; A: B; M: E; Op: D; Sp: D |
| `/app/clients` | `ClientsPage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/clients/:id` | `ClientWorkspacePage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/tasks` | `TasksPage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/tasks/:id` | `TaskWorkspacePage` | O: B; A: B; M: E; Op: E; Sp: E |
| `/app/calendar` | `CalendarPage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/calendar/:id` | `AppointmentWorkspacePage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/conversations` | `ConversationsPage` | O: R; A: R; M: R; Op: R; Sp: D |
| `/app/conversations/:id` | `ConversationsPage` | O: E; A: E; M: E; Op: E; Sp: D; actual-ID follow-up |
| `/app/timeline` | `TimelinePage` | O: B; A: B; M: B; Op: D; Sp: D |
| `/app/bots` | `BotsPage` | O: B; A: B; M: D; Op: D; Sp: D |
| `/app/bots/:id` | `BotDetailPage` | O: B; A: B; M: D; Op: D; Sp: D |
| `/app/integrations` | `IntegrationsPage` | O: B; A: B; M: D; Op: D; Sp: D |
| `/app/pricing` | `PricingPage` | O: B; A: B; M: D; Op: D; Sp: D |
| `/app/ai-assistant` | `AIAssistantPage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/ai` | `/app/ai-assistant` | O: R; A: R; M: R; Op: R; Sp: R |
| `/app/assistant` | `AIAssistantPage` | O: B; A: B; M: B; Op: B; Sp: B |
| `/app/inbox` | `ConversationsPage` | O: R; A: R; M: R; Op: R; Sp: D |
| `/app/ai-agents` | `AIAgentsPage` | O: R; A: R; M: D; Op: D; Sp: D; actual-ID follow-up |
| `/app/ai-agents/:id` | `AIAgentsPage` | O: E; A: E; M: D; Op: D; Sp: D; actual-ID follow-up |
| `/app/ai-agents/:id/:section` | `AIAgentsPage` | O: E; A: E; M: D; Op: D; Sp: D; actual-ID follow-up |
| `/app/automations` | `AutomationsPage` | O: B; A: B; M: D; Op: D; Sp: D |
| `/app/business` | `/app/business/services` | O: R; A: R; M: R; Op: D; Sp: D |
| `/app/business/services` | `ServicesPage` | O: B; A: B; M: B; Op: D; Sp: D |
| `/app/business/resources` | `ResourcesPage` | O: B; A: B; M: B; Op: D; Sp: D |
| `/app/business/working-hours` | `WorkingHoursPage` | O: B; A: B; M: B; Op: D; Sp: D |
| `/app/services` | `business route alias` | O: R; A: R; M: R; Op: D; Sp: D |
| `/app/resources` | `business route alias` | O: R; A: R; M: R; Op: D; Sp: D |
| `/app/working-hours` | `business route alias` | O: R; A: R; M: R; Op: D; Sp: D |
| `/app/analytics` | `AnalyticsPage` | O: B; A: B; M: B; Op: D; Sp: D |
| `/app/settings` | `SettingsPage` | O: B; A: B; M: D; Op: D; Sp: D |
| `/app/billing` | `/app/settings#billing` | O: R; A: R; M: D; Op: D; Sp: D |
| `/leads` | `LeadsPage` | S — existing alias/redirect; canonical component inspected |
| `/account` | `AccountPage` | S — existing alias/redirect; canonical component inspected |
| `/deals` | `DealsPage` | S — existing alias/redirect; canonical component inspected |
| `/clients` | `ClientsPage` | S — existing alias/redirect; canonical component inspected |
| `/tasks` | `TasksPage` | S — existing alias/redirect; canonical component inspected |
| `/calendar` | `CalendarPage` | S — existing alias/redirect; canonical component inspected |
| `/conversations` | `ConversationsPage` | S — existing alias/redirect; canonical component inspected |
| `/timeline` | `TimelinePage` | S — existing alias/redirect; canonical component inspected |
| `/crm-bots` | `BotsPage` | S — existing alias/redirect; canonical component inspected |
| `/integrations` | `IntegrationsPage` | S — existing alias/redirect; canonical component inspected |
| `/ai-assistant` | `AIAssistantPage` | S — existing alias/redirect; canonical component inspected |
| `/ai` | `/app/ai-assistant` | S — existing alias/redirect; canonical component inspected |
| `/assistant` | `AIAssistantPage` | S — existing alias/redirect; canonical component inspected |
| `/inbox` | `ConversationsPage` | S — existing alias/redirect; canonical component inspected |
| `/ai-agents` | `AIAgentsPage` | S — existing alias/redirect; canonical component inspected |
| `/automations` | `AutomationsPage` | S — existing alias/redirect; canonical component inspected |
| `/services` | `business route alias` | S — existing alias/redirect; canonical component inspected |
| `/resources` | `business route alias` | S — existing alias/redirect; canonical component inspected |
| `/working-hours` | `business route alias` | S — existing alias/redirect; canonical component inspected |
| `/analytics` | `AnalyticsPage` | S — existing alias/redirect; canonical component inspected |
| `/settings` | `SettingsPage` | S — existing alias/redirect; canonical component inspected |
| `/billing` | `/app/settings#billing` | S — existing alias/redirect; canonical component inspected |
| `/documents` | `DocumentsPage` | Public: B |
| `/documents/:documentId` | `DocumentsPage` | Public: B; four documents + unknown ID |
| `/` | `LoginPage` | Public: B |
| `/pricing` | `/login` | Public: R |
| `/bots` | `/login` | Public: R |
| `/crm` | `/login` | Public: R |
| `/contacts` | `/login` | Public: R |
| `/login` | `LoginPage` | Public: B |
| `/signup` | `SignupPage` | Public: B |
| `/mfa` | `MfaPage` | Public: B |
| `/forgot-password` | `ForgotPasswordPage` | Public: B |
| `/reset-password/:uid/:token` | `ResetPasswordPage` | Public: B |
| `/invite/:token` | `InviteAcceptPage` | Public: E |
| `/platform` | `PlatformOverviewPage` | P: B; manager in strict follow-up |
| `/platform/operations` | `PlatformOperationsPage` | P: B; manager in strict follow-up |
| `/platform/merchants` | `PlatformMerchantsPage` | P: B; manager in strict follow-up |
| `/platform/merchants/:id` | `PlatformMerchantDetailPage` | P: B; manager in strict follow-up |
| `/platform/prospects` | `PlatformPlaceholderPage` | P: B; manager in strict follow-up |
| `/platform/landings` | `PlatformPlaceholderPage` | P: B; manager in strict follow-up |
| `/platform/billing` | `PlatformPlaceholderPage` | P: B; manager in strict follow-up |
| `/platform/analytics` | `PlatformPlaceholderPage` | P: B; manager in strict follow-up |
| `/platform/settings` | `PlatformPlaceholderPage` | P: B; manager in strict follow-up |
| `/app` | `AppLayout/index` | B/R — all five roles in strict index follow-up |
| `/dashboard/*` | `route wrapper` | S — existing alias/redirect; canonical component inspected |
| `*` | `NotFoundPage` | Public: B |
