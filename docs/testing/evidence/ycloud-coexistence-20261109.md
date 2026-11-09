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
