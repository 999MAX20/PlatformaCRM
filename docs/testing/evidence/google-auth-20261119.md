# Google authentication — 2026-11-19

User scope: existing-user Google login, new owner registration with business data
and existing legal acknowledgements, explicit safe linking without duplicates.
Canonical checkout: `C:/Users/user/Desktop/PlatformaCRM`; branch
`codex/ui-testing-toolkit`; starting HEAD `b53da6e48fd3b81f535e1ce9dd56c6a48d0965aa`.
This is source implementation and local verification, not a production rollout.

## Delivered behavior

The GIS-rendered button on `/login` uses a server nonce and a CSRF-protected
browser-bound attempt. Existing Google subject signs in to the same active user
with existing MFA policy. A new verified identity either opens business/legal
onboarding or asks the matching existing user to sign in and explicitly confirm
their password and fresh MFA/recovery factor. User/business/identity/acknowledgement
creation is atomic. Legacy Google social login cannot bypass the new flow.

Attempts expire after 10 minutes, are consumed once, and have bounded proof failures.
Nonce/browser secret are hashed; ID tokens are not persisted. Link authorization
rechecks the user epoch and device session under lock. Consumed identity data is
redacted immediately; expired rows have bounded opportunistic and scheduled cleanup.
Apple, AI, channel connections and working database were not changed.

## Verification

- Disposable PostgreSQL affected gate: **65/65 PASS**, including Google signature,
  issuer/audience/expiry/nonce/email verification, CSRF, cross-browser/replay,
  inactive user, ordinary owner signup, MFA/enrollment and real concurrent signup
  and link races. `output/google-auth-postgres-20261119.log`.
- After cleanup and epoch/device recheck: **18/18 PASS**, no skips, including both
  PostgreSQL races; system check 0 and migration drift No changes.
  `output/google-auth-postgres-final-20261119.log`; backend manifest9/9 matched.
- Browser: **22/22 PASS** in desktop Chromium1280×720 and Pixel7 mobile412×839.
  Real backend + signed RS256 JWTs; only the Google script/JWKS network boundary is
  synthetic. Registration and explicit link in RU/KK/EN, missing acknowledgements,
  wrong password/recovery, retained input, independent reveal/focus, expired flow,
  failed script retry, existing subject login, MFA login, link return after MFA,
  reused factor denial and fresh factor success.
  Command: `.venv/Scripts/python.exe scripts/verify_google_oauth_browser.py google-oauth-acceptance-20261119 --keep`.
  `output/google-oauth-acceptance-20261119/browser.log` and `results/` screenshots.
  Preview/backend stopped after acceptance; disposable fixtures removed by runner.
- Focused frontend login/error policy tests: **23/23 PASS**.
  `output/google-oauth-frontend-tests.log`.
- Final `npm run build`: **PASS** (i18n parity, TypeScript, app and widget).
  `output/google-oauth-build-final.log`. Bundle budget PASS; existing large RU/KK dictionary warnings remain, app shell below400kB.

Observed and fixed: successful Google callback briefly remounted/reinitialized the
button before lazy-route navigation completed, replacing the pending flow. The
button now starts a replacement attempt only after a failed exchange and ignores
duplicate submissions. Final22 scenarios passed with that fix. Initial desktop
batch also reached production IP throttle; disposable harness explicitly raises
social/login/signup rates for repeated locales only. Production limits unchanged.
An initial backend test-helper nonce naming collision and initial frontend schema
type mismatch were corrected before passing gates.

Anti Slop during + Design Taste/app-screen review retained the approved auth
background/tokens/shared controls. Captured AND visually inspected RU/KK/EN
desktop/mobile form screenshots plus MFA/expiry errors: aligned controls, wrapped
long email/legal text, no horizontal overflow, readable actions/errors, visible
keyboard focus. Form submit/recovery and keyboard reveal exercised. New dialogs,
list empty states and live Google popup appearance are not applicable to the
locally rendered completion form; real GIS popup acceptance remains below.

Foreign password-policy work (passwords/serializers/signup/reset/tests) and prior
STATUS/PRIMARY/Google Sheets evidence changes were preserved and excluded from
this task's commit. Local checks used that shared working tree; clean CI separately
validates the published source without foreign WIP. No dependencies were added.

## Deployment prerequisites / limits

See [Google Cloud and rollout setup](../../current/google-sign-in.md). Requires
accounts migration0012, matching frontend/backend client ID, rebuilt frontend,
effective proxy GIS/popup policy, and enabled existing auth cleanup scheduling.
No client secret is required for this GIS ID-token flow.

Actual Google Cloud client/real-account popup login is **not verified** by the
synthetic boundary tests. No production deployment was performed. Legal document
bodies remain the previously owner-approved placeholders; this change records
acknowledgements but does not supply approved legal content. Fill those bodies
before publishing the public consent URLs.
