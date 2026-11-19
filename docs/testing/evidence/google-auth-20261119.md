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

## Authorized Cloud setup / rollout preparation (2026-11-19)

Owner reopened Chrome Platforma Digital; live Cloud account/project verified:
platforma.digitalkz@gmail.com, platformacrm-integrations-dev (844826644933).
After explicit action-time confirmation, created Web application client
PlatformaCRM Server Sign-In:
`844826644933-l70iv9kalh1eausb7ujo9sj9dsljid40.apps.googleusercontent.com`.
Readback confirms the only JavaScript origin is `https://platformacrm.kz`, no
redirect URIs, agent option off. Existing Local Dev client preserved. Secret is
not needed by GIS ID-token login and was not copied into config or artifacts.
Screenshot: output/google-signin-client-created.jpg. Audience remains External /
Testing, one existing test user (owner). Branding name/support contact exist;
home/privacy/terms fields are blank. Public publication/verified legal text is not
claimed. No billing/trial or Google API scope expansion.

Server source-only stage ac9a8d71:3480/3480 hashes match. Preparatory snapshot
restored into disposable DB:167 tables; accounts0012 only pending, applied to copy;
166 pre-existing non-metadata tables/10923 rows have identical full row digests.
System check PASS, pending0, new flow table empty; disposable DB removed and absence
verified. Live service/config identities unchanged. Old release extras: RELEASE.json,
1118 built frontend files, .env symlink; no extra source overlays found. Evidence:
output/digital-deploy-20261109/rehearsal-receipt-ac9a8d71.json. This does not replace
the fresh paused-writer backup required before live mutation. Actual deployment
and real Google login still pending at this checkpoint; full CI not awaited.

## Server rollout and real Google boundary

Exact ac9a8d71 deployed and public CRM reopened 2026-11-19T13:05:32Z. Final
receipt: output/digital-deploy-20261109/final-receipt-ac9a8d71.json. Frozen-lock
build/i18n/types/app/widget PASS;3480 source/580 frontend hashes verified.
Fresh paused dump restored167 tables;164 nonmetadata tables/10134 rows unchanged
through accounts0012 and transactional access/auth smoke. These counts exclude
metadata and are not the same boundary as the earlier preparatory snapshot.
Backups: pgBackRest20261115-200004F_20261119-125648I, restic dadba5b7/b9a3039e;
server-local dump/recovery DB retained. After reopening, no stale DB restore is safe.

Five services use new root. First beat startup failed because umask made operations
directory0700; fixed that directory0755 and verified crm access.6 failed wrapper
starts/5 historical systemd restarts preserved; final70s stable window had0 additional
restarts and at least2 consumed restricted polls. Beat remains ycloud-events only.
Bounded Google-flow expiry service succeeded; hourly timer enabled. AI/Scribe/YCloud
and inline automation remain false. Env changed only Google audience; permissions,
stand gate and non-CRM Caddy blocks preserved. HTTPS gated login/ready/asset200,
asset hash matches; ungated401, anonymous clients401, missing-CSRF Google start403.

Real Chrome Platforma Digital: new Google button visible on server. Actual Google
popup requested only name/profile photo/email. Owner explicitly approved Continue;
real Google credential accepted and /google/complete displayed verified owner email
and new-business form. Existing user count0/Google identity0 before this test;
no silent account/business creation. Form prepared with test business and unselected
legal acknowledgements; awaiting explicit registration approval. Terms route shows
only heading; legal text readiness not claimed. Screenshot captured and inspected:
output/google-signin-signup-review.jpg. Popup screenshots failed (CDP timeout),
while AX reading and keyboard action succeeded; no browser protocol/native bypass.
Full authenticated CRM session and repeat-login/no-duplicate proof still pending.

## Signup entry closure (2026-11-19)

User authorized Google registration button on /signup, scenario checks and server
rollout. Source f43f2ba271149e69e2c98d4cc10eca9ffd7805af, exact tree
868a3c8cb9efc01cf20ae17ac58f4270387181b7, normal-pushed/read back from origin/main.
Eight scoped files; partial SignupPage staging preserves/excludes foreign password,
form simplification and CSS work. No backend/schema/config change. Reused official
GoogleSignInButton with signup_with text; login default unchanged; signup handles
new identity, explicit link, existing session and MFA with error/retry/submit guard.
Label option verified against https://developers.google.com/identity/gsi/web/reference/js-reference#text.

Command `.venv/Scripts/python.exe scripts/verify_google_oauth_browser.py
google-signup-entry-final-20261119`:36/36 PASS4.3m, desktop/mobile RU/KK/EN. Real
isolated CRM backend and signed RS256 fixture tokens; Google SDK/JWKS synthetic.
New owner/docs required/success, both entry paths, matching-email explicit link,
known identity/MFA, failed verification retry and script retry with retained inputs,
expiry/recovery, keyboard activation and no horizontal overflow covered. Runtime
stopped and fixture removed. Earlier preparation cancelled to separate signup MFA
fixtures before final run. Working-tree browser run coexisted with foreign form
WIP; not represented as an exact release visual snapshot. Changed Google handlers
unchanged through verification. Exact immutable tree independently passed frozen
install/i18n/types/app/widget build on server; source3480/frontend580 hashes verified.
No full CI awaited; automated push CI is not claimed green.

Frontend-only published2026-11-19T13:26:53Z (18:26:53 Asia/Qyzylorda). Backend remains
ac9a8d71. Caddy changed only CRM static root; env/service identities/restart counters,
DB and other sites unchanged. Previous static artifact and Caddy retained for
static-only rollback. Receipt: output/digital-deploy-20261109/static-receipt-f43f2ba2.json.
Postflight signup/login/ready/entryasset200 and exact hashes PASS. One deployment
postflight helper shadowed http module; fixed helper only, repeated postflight PASS.

Live Chrome Platforma Digital: official Google button present with signup_with;
Google personalized its displayed label for the signed-in owner. Actual keyboard
activation -> account selection -> verified /google/complete business/documents
form PASS. Existing approved Google access reused, no broader scope requested.
Production business/documents submission NOT performed. Screenshot gate: inspected
output/google-signup-server-desktop.jpg, google-signup-server-mobile.jpg and
google-signup-server-callback.jpg. Mobile390x844, scrollWidth375 <= innerWidth390;
button fits, clear labels, desktop/mobile geometry and reachable flow PASS. Viewport
reset. Local locale screenshots/keyboard/error-retention evidence supplement live
RU GIS evidence. New decoration/colors/assets N/A; reused official SDK and existing
tokens. Legal text readiness and earlier full production signup/repeat-login scope
remain separate; this verifies the new entry point and isolated end-to-end creation.

## Static Google entry correction (2026-11-19)

Owner requested generic buttons without remembered name/email/avatar and no passive
expiry alert on login/signup. Reused shared GoogleSignInButton and existing protected
nonce/API flow; backend, cookies/TTL policy, identity linking and MFA unchanged.
Official GIS medium setting disables personalized presentation per Google's linked
personalized-button guide. Expired idle preparation renews without replacing the
button with an alert/loading paragraph; input stays intact. Hidden-tab return checks
expiry. Renewal stops before credential verification; generation rejects stale
callbacks. Actual verified onboarding retains its expiry and retry behavior.

Source commits 4063c2125e5a662802fd8c0823288719a8854c69 and
2e423f3b8ec54faab3818396c136071d853b18f7, normal-pushed/read back from origin/main.
First focused run 44/44 PASS. Live inspection found fixed-width overflow when the
window narrowed; added ResizeObserver redraw without a new auth attempt and reran
affected suite: `.venv/Scripts/python.exe scripts/verify_google_oauth_browser.py
google-static-button-final-20261119`, 48/48 PASS in 3.1m, desktop/mobile RU/KK/EN.
New cases cover idle renewal retaining input, slow credential verification without
rotation, and resize preserving the attempt then successful callback. Existing new
owner, explicit link, known identity/MFA, expiry and script/verification retry pass.
Google SDK/JWKS and accelerated expiry are synthetic; backend is real and isolated.
Both owned test runtimes stopped and fixtures deleted. Local screenshots inspected;
local working-tree form/CSS WIP is not presented as exact deployed visual evidence.

Deployed frontend is intentionally f43f2ba2 plus ONLY the two Google runtime/type
paths from the task commits. Other published form/CSS changes and dirty password
work are excluded. Exact artifact tree f7613883a30bbd0739fb15674aba524eb5b0212c;
source binding differs from committed blobs only in CRLF/LF, verified after newline
normalization. Immutable tree/source hashes remain recorded. Frozen npm install,
i18n/types/app/widget build PASS;3480 source files and580 build files verified.
Bundle budget PASS on manifest-listed new assets: shell356.6kB <400kB. Existing
RU/KK dictionaries603.1/604.8kB warnings retained. Initial post-retention bundle check
included legacy cached assets and failed the single-shell assertion; rerun against
the complete current manifest assets passed, no gate or production asset deletion.

Final frontend switch 2026-11-19T14:19:40Z. Receipt:
output/google-static-release-final-20261119/static-receipt.json. Backend ac9a8d71,
service identities/restart counters, env, DB/migrations and other Caddy sites unchanged.
Previous static artifacts/Caddy retained for static-only rollback. HTTPS login,
signup, ready and exact entry asset hashes PASS. CI44542486686 in_progress at readback;
full CI not awaited by owner instruction. Earlier4063 run44541061154 also in_progress
when inspected, not claimed green.

Actual Chrome server acceptance: generic Google labels on login/signup despite
remembered Google accounts; login keyboard Enter opens account chooser, closing it
leaves generic button. Final signup after desktop-to390px resize opens chooser too.
No account chosen, real registration, new consent grant or account mutation performed.
Signup button267px and login332px fit mobile forms; resized back to desktop and
inspected. Temporary viewport reset; owned popups/signup tab closed, login retained.
Screenshots saved AND visually inspected under output/google-static-release-final-20261119:
login-desktop.jpg, login-mobile.jpg, signup-desktop.jpg, signup-mobile.jpg.

Scoped UI delivery gate: PASS geometry/no overflow, real actions, keyboard, retained
input, loading/error/retry and responsive/localized checks. Official Google branding
and its intrinsic medium control retained to meet the no-personalization request;
no custom colors/assets/motion or adjacent layout introduced. Provider-internal
contrast/target dimensions not restyled. Purpose/liveliness: existing green form
identity and hierarchy preserved; no new decorative technique. Full production
registration/repeat-login remains outside this correction's live acceptance; isolated
end-to-end coverage is explicitly distinguished above.
