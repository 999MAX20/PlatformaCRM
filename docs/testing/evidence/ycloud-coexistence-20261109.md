# YCloud Coexistence: local preparation, 2026-11-09

Owner request: prepare CRM for Zani Delivery Coexistence and draft a request to
YCloud to enable TP Lite. Local implementation and checks completed. No support
message sent, provider configuration changed, working DB migrated or deployment made.

## Behavior

- Setup chooses API-only or `WHATSAPP_BUSINESS_APP`; the latter requires an expected
  E.164 number, persisted with the attempt and matched against the provider result.
- Signed app echoes/created events become already-sent staff messages. Both streams
  deduplicate by wamid; recipient/tenant/number/revision conflicts are rejected.
- App replies pause conversation AI until manual resume and cancel queued automatic
  replies. Dispatch rechecks takeover. HTTP already in flight cannot be recalled.
- App replies do not create inbound unread counts or open the 24-hour service window.
  They are recorded even while the CRM channel is paused. Media is an unavailable
  content notice; no download, historical import, templates or reminders were added.
- integrations0010 adds mode and expected number, preserving API mode for existing
  bindings. Migration tested in disposable databases only.
- Setup retains existing components and tokens; RU/KK/EN copy, validation, disabled,
  pending, loading, retry and cancellation states. Channel changes reset local form
  state and temporary signup links. No new dependency or asset.

## Verification

Canonical root: `C:/Users/user/Desktop/PlatformaCRM`.
Branch: `codex/ui-testing-toolkit`; starting HEAD:
`6a8af190b0701158b2a7b187547bf6ba1a2f5567`. Evidence applies to the local dirty source
snapshot, not the entire branch or a production release.

Commands run from the canonical root unless prefixed with `frontend/`:

| Check | Result |
| --- | --- |
| `.venv/Scripts/python.exe scripts/verify_ycloud.py apps.integrations.tests_ycloud_coexistence.CoexistenceOnboardingTests apps.integrations.tests_ycloud.YCloudOnboardingTests` | 11 PASS; early iteration, superseded by completion suite |
| Focused `CoexistenceMessageTests` via the same runner | 12 PASS; early iteration, superseded below |
| `.venv/Scripts/python.exe scripts/verify_ycloud.py --postgres-bin "C:/Program Files/PostgreSQL/17/bin" apps.integrations.tests_ycloud apps.integrations.tests_ycloud_dispatch apps.integrations.tests_ycloud_coexistence apps.bots.tests_handoff_recovery` | 82 PASS, 134.320s, no skips; system and migration drift PASS |
| Same PostgreSQL runner, `apps.integrations.tests_ycloud_coexistence_concurrency` | 4 PASS, 23.109s, no skips; two concurrent app streams yield one message/conversation; inherited confirmation/inbound/delivery concurrency checks also PASS |
| `frontend/`: `node node_modules/@playwright/test/cli.js test --config playwright.ycloud.config.ts` | 10 PASS, 52.9s; 1440 desktop / 390 mobile, RU/KK/EN, keyboard, invalid number, 503/retry, pending reload, no stored URL, read-only/unavailable, loading/default API/cancel |
| `frontend/`: `npm run build` with existing `safe_environment` and `VITE_API_URL=''` | PASS: i18n 6933 keys, TypeScript, application and widget builds |
| `frontend/`: `node node_modules/typescript/bin/tsc -p e2e-ycloud/tsconfig.json` | PASS |
| `frontend/`: `node scripts/check-bundle.mjs` | PASS app-shell budget; existing RU/KK chunks above 500 kB remain warnings |
| Scoped `git diff --check` and review of added files | PASS |

Tests use disposable databases, synthetic contacts and mocked provider calls. Browser
fixture mounts the real setup component with intercepted local HTTP; it is not a live
provider signup or an authenticated whole-CRM flow. API authorization and tenant
checks are covered separately by the backend suite. No dependency reinstall.

Initial browser attempts failed because the fixture intercepted source module URLs,
an exact input-name locator changed when validation text appeared, and a loading
button changes its accessible name. Fixtures/assertions corrected; product assertions
retained. Final complete run passes. Logs of failed attempts remain available.

Artifacts: `output/ycloud-coexistence-20261109/` contains before copies, PLAN,
backend/concurrency/build/browser logs, screenshot evidence and own-source manifest.
Visually inspected Russian desktop and Kazakh mobile screenshots: no page overflow,
readable form/help, visible keyboard focus and existing CRM layout preserved.

## Scoped design review

Taste app-screen route and Anti Slop during mode: existing product design retained.
ENERGY 1 / RHYTHM 1 / MOTION 1. Existing green primary action provides the focal point;
field spacing and typography follow Input/Select/Button. No decorative assets or new
animation. Hard gate, purpose and craftsmanship review: PASS within the changed
form; mobile, keyboard and error/loading states verified. Shared components outside
this change are not certified as a whole-design audit.

## External and publication boundaries

Draft only: `output/ycloud-coexistence-20261109/ycloud-tp-lite-request.txt`. It asks
YCloud to enable TP Lite, confirm Business App eligibility, signing/event semantics,
Meta requirements and billing. It contains no API key or webhook secret.

Live activation still requires YCloud permission, eligible number and primary-phone
authorization; approved deployment/migration; server credentials; the exact signed
POST webhook exception from stand login; worker `bots` queue and beat; end-to-end
inbound/app reply/API reply/delivery acceptance. History is intentionally excluded.

No commit/push/CI: a pre-existing `.git/index.lock` is present. Current local history
also contains 20 commits absent from the recorded origin/main and 3 remote-only
commits. Unrelated work was not staged, merged or published. This is a concrete
publication blocker under AGENTS section 6, not a local test failure.
No comprehensive release certification: prior unrelated card payload/SQL performance
budget failures remain outside this bounded preparation.

Provider references:
- https://docs.ycloud.com/en/partner-center/technical-development-partners/partner-direct-link-tp-lite
- https://docs.ycloud.com/en/api-reference/guides/examples/webhook-examples/whatsapp-business-app-sent-message-sync-webhook-examples.md

## 2026-11-19: history import preparation

Prior result: onboarding and app echoes implemented, history explicitly excluded.
New owner requirement: prepare customer onboarding, Coexistence and history while
YCloud partner approval is pending. Minimal delta: signed history ingestion into
the existing Inbox importer, deduplication against live/app streams, safe status
and existing recovery controls. No provider activation or working DB migration.

Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD d8ec748aa46782051198b13c8a547d2f49d13850. Existing unrelated Google,
accounts, WhatsApp signup and shared documentation WIP must be preserved.
Risk: tenant routing, replay/order, false unread/service windows or AI responses.
Reuse YCloud durable events, channel locks and direct Meta history storage.
Focused checks: history validation, auth/tenant, duplicates, no automation, paused
and stale binding, recovery. Completion: affected YCloud/direct history/Inbox suites
on disposable PostgreSQL, system/drift; frontend build and targeted setup browser
flow if changed. Live handshake, history completeness and delivery remain unproven
until partner approval and handset consent. No purchases or deployment in scope.

UI delta: expose existing YCloud setup from a new unbound WhatsApp channel only;
preserve direct Meta and already connected/paused channels. Anti Slop during (owner
preference), human/copywriting and project frontend skills: reuse Button/Input,
existing typography/spacing, visible keyboard focus and RU/KK/EN; show observed
history counts rather than a fabricated completion percentage. No layout redesign,
new assets or dependency. Verify setup/retry/read-only/history states and mobile.

Implementation: added `ycloud/history.py`; durable intake recognizes both history
directions and verifies the same WABA/number route as live messages. It reuses
`whatsapp.coexistence_messages.import_message` with YCloud's existing E.164 thread
identity. History does not change unread, last_inbound_at, consent or AI state.
App/history races use existing Business/channel/connection locks. Live app echoes
promote a historical outbound record and perform staff handoff without another
message. Connected/paused numbers cannot be overwritten through new onboarding.
The existing permission-scoped setup response includes observed history counts.

No new migrations, dependency, env key, provider call or working-data mutation.
Imported non-text records are explicit unavailable-content placeholders; media
download, contact-book sync and templates are not implemented by this extension.
Unattributable progress-only callbacks have no tenant effect and cannot establish
completion. Archive completeness must be checked against the actual phone.

### Activation after partner approval

1. Enable Partner Direct Link in the approved YCloud Tech Partner account; configure
   branding and HTTPS return URL for PlatformaCRM. CRM ignores redirect success as
   proof: signed account binding plus server lookup are still authoritative.
2. Configure `YCLOUD_API_KEY`, `YCLOUD_WEBHOOK_SECRET`, `YCLOUD_ENABLED=True` in the
   server secret environment for web and workers. Never put these in frontend or
   customer config. This turn does not create or rotate credentials.
3. Register `https://platformacrm.kz/api/integrations/ycloud/webhook/`; allow this
   exact signed POST through stand access, retaining HMAC and timestamp validation.
   Subscribe to `whatsapp.business_account.updated`,
   `whatsapp.inbound_message.received`, `whatsapp.message.updated`,
   `whatsapp.smb.message.echoes`, `whatsapp.smb.message.created`,
   `whatsapp.smb.history` before authorizing the phone's history share.
4. Verify beat schedules `integrations.process_ycloud_events` every 30 seconds and
   a worker consumes its configured default queue. Pending events must drain;
   the API receipt alone does not mean that a message reached Inbox.
5. Use a new unbound CRM channel, choose YCloud then Business App, enter the exact
   expected E.164 number and authorize through Meta/YCloud. Permit history sharing
   on the primary phone; do not delete the Business App account.
6. Verify old text in the correct tenant, no AI/unread/window effects, one new
   inbound, CRM reply/delivery, app reply/handoff, replay deduplication and recovery.
   Check media separately: this implementation does not download its content.
7. If API sending must stop, pause the CRM channel while retaining signed event
   intake and the phone app. No disconnection/migration is an automatic rollback.

Current external blocker: Tech Partner application submitted, approval not yet
observed. No promise that provider admission removes number-level Meta restrictions.

19Nov2026 live read-only recheck: authenticated Platforma Digital console at
`https://www.ycloud.com/console/#/app/partner` still shows disabled Become a Tech
Partner and no Partner menu/Direct Link configuration. Screenshot captured and
visually inspected. This confirms no observed approval, not a rejection; contact
email was not inspected. No application resubmission, credential exposure, number
activation, settings mutation or purchase. GitHub connector latest-attempt jobs for
run44392825855 both completed/success (backend checks/tests and frontend build,
including dependency audits). This verifies source9c86bc76 CI, not a later release.

Later19Nov read-only ticket observation:
https://www.ycloud.com/resource/t/2532 is In Progress. It already contains today's
account-specific follow-up requesting Free-plan TP Lite/Coexistence review status,
missing documents/ETA and applicable DPA/subprocessor/processing-location details.
No response after that follow-up was visible. Earlier10Nov human support referred
the account to Victor Zhang for Free Tech Partner/TP Lite assistance; earlier
automated replies did not grant approval. This coordinator only read the existing
ticket, did not send/reopen/subscribe or claim authorship of the follow-up. No
activation, billing commitment or guaranteed Free-plan eligibility inferred.

### Local verification, 19.11.2026

- Disposable PostgreSQL17 via `scripts/verify_ycloud.py --postgres-bin "C:/Program Files/PostgreSQL/17/bin"`: 116 tests PASS across YCloud foundation/dispatch/Coexistence/history, PostgreSQL concurrency, direct Meta Coexistence and handoff recovery. Log: `output/ycloud-history-backend.log`. No concurrency skips. System and migration drift PASS. Two final history validation cases were added afterwards and are covered by the final focused run below.
- `node node_modules/@playwright/test/cli.js test --config playwright.ycloud.config.ts` from frontend: 18 PASS desktop/mobile RU/KK/EN, API fixtures. Log `output/ycloud-history-browser.log`. Covers keyboard/focus, invalid number, retained input/retry, pending/reload, cancellation, unavailable/read-only, new-channel entry/back, paused-channel protection, counts and import error recovery.
- Isolated safe-environment `npm run build`: PASS i18n/types/app/widget; `tsc -p e2e-ycloud/tsconfig.json`: PASS; `node scripts/check-bundle.mjs`: PASS (shell355.1KB within400KB). Existing locale-size warnings remain. Build log `output/ycloud-history-build.log`.
- Screenshots captured in `output/ycloud-coexistence-20261109/browser` by this run (directory name retained from runner). Visually inspected RU desktop history, KK mobile history, RU mobile form: wrapping/spacing/control sizes/focus/overflow PASS. Uses existing tokens and components; new dialog, motion, imagery and theme checks are not applicable. Mock UI does not prove live provider authorization.
- Initial history-exclusion test updated to the new authorized behavior. Extra live-inbound test initially rejected a fixture without its connected phone ID; corrected the fixture to match real onboarding. Production routing was not weakened.
- Rerun trigger: changed YCloud/history/Inbox contracts or relevant dependencies/configuration. No working DB/provider credentials, media downloads, deployment or real messages used. Full-project/release suite not run: scoped preparation, not release certification.

Final focused run: 14/14 PASS on final history code and corrected connected-channel fixture; system/migration drift PASS. Log `output/ycloud-history-final-focused.log`. This supplements the 116-test dependent run, not an additional 14 distinct scenarios. Task-owned staged diff hygiene PASS; no dependency/schema changes.
