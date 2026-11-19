# Google sign-in

Google authentication uses the Google Identity Services button with a JavaScript
callback. It grants access to the CRM account, not Google Sheets/Calendar APIs.

Both `/login` and `/signup` start the same protected flow. Signup uses the official
GIS `signup_with` button text. Both entry points use the official `medium` button,
which does not display a remembered Google name, email or profile picture.
New identities continue to business/documents onboarding, existing identities sign
in (including MFA), and matching-email accounts require explicit linking.

## Account flow

- Existing `(provider=google, subject)` signs in to that same active user. Required
  MFA/enrollment runs before issuing the CRM session; email changes at Google do
  not choose a different CRM user.
- A new Google identity with an existing CRM email requires ordinary CRM login,
  then explicit confirmation of the current password and a fresh MFA/recovery
  code when enabled. The authenticated user/email must match, the session must be
  recent (10 minutes), and its epoch/device must still be active. Email matching
  alone never attaches Google. A second Google identity for that user is rejected.
- A new email opens `/google/complete`: owner name/phone, business name/type/city,
  and the existing four legal acknowledgements. User, business defaults, member,
  legal receipts and identity are created atomically only after submission.
  The account has no generated password. Existing policy can require MFA enrollment.
- Attempts use CSRF and a 10-minute single-use HttpOnly browser cookie with a
  hashed random nonce; signature/audience/issuer/expiry/email verification are
  checked on the server. Raw Google credentials never go in URLs or browser storage.
  Legacy Google `/api/auth/social/` calls are rejected. Apple behavior is unchanged.
- An idle entry page silently renews its expired preparation while keeping the
  Google button and entered email form values. Returning to a suspended tab also
  renews expired preparation. Renewal stops as soon as credential verification
  starts, and stale callbacks cannot use a newer attempt. Network failures retain
  the retry action; actual verified onboarding still has its normal expiry.

## Google Cloud configuration

1. In **Google Auth Platform → Branding**, use PlatformaCRM, a monitored support
   email and authorized domain `platformacrm.kz`. Set homepage to
   `https://platformacrm.kz/`, privacy to
   `https://platformacrm.kz/documents/privacy`, terms to
   `https://platformacrm.kz/documents/terms`. The document routes exist, but their
   approved legal bodies must be supplied before a public launch; acknowledgement
   tracking does not create legal text.
2. Configure **Audience** for the intended users. Add the pilot Google accounts
   to test users while using Testing, and follow the console's publishing/branding
   verification requirements before wider use.
3. Under **Clients**, create/select an OAuth client of type **Web application**.
   Authorized JavaScript origin: `https://platformacrm.kz` (no `/login` path).
   Add only actual development origins separately. This callback-based popup flow
   does not need an authorized redirect URI; `/google/complete` is an internal CRM
   continuation, not a Google redirect endpoint. No Sheets/Drive/Calendar scopes
   are requested by this feature.
4. Configure the same web client ID (ending `.apps.googleusercontent.com`) in
   frontend build variable `VITE_GOOGLE_CLIENT_ID` and backend allowlist
   `GOOGLE_OAUTH_CLIENT_IDS`. The frontend value requires rebuilding. No client
   secret is used by this ID-token flow or put into the frontend.
5. If the reverse proxy adds CSP, allow the Google GIS script, frames and connections
   per Google's setup guide. Check popup behavior with the effective
   Cross-Origin-Opener-Policy; Google documents `same-origin-allow-popups` when
   needed without FedCM. Keep HTTPS and secure auth cookies.

Sources: [Google GIS setup](https://developers.google.com/identity/gsi/web/guides/get-google-api-clientid),
[server ID-token verification](https://developers.google.com/identity/gsi/web/guides/verify-google-id-token),
[GIS button](https://developers.google.com/identity/gsi/web/guides/display-button),
[personalization conditions](https://developers.google.com/identity/gsi/web/guides/personalized-button).

## Rollout and verification

Apply accounts migration `0012_googleauthflow` before serving the new code. No
existing users/businesses are migrated or auto-linked. Deploy frontend and backend
together because the old Google endpoint deliberately rejects unbound sign-in.
Unset frontend client ID hides the Google button; unset backend allowlist denies
starting the flow. Rollback can leave the new table in place to preserve data.

Consumed/restarted flows immediately redact Google subject/email/name. Expired
rows are pruned in bounded batches during new starts and by the existing
`accounts.flush_expired_tokens` task. Confirm that task is actually scheduled and
allowed in the rollout's beat/worker profile; a restricted pilot beat allowlist may
exclude it. No beat configuration is changed merely by this source implementation.

Local verification uses real signed RS256 tokens with a synthetic JWKS/browser
provider boundary, an isolated database, and no external sends:

```powershell
.venv/Scripts/python.exe scripts/verify_google_oauth_browser.py
```

The runner runs desktop/mobile Chromium scenarios, writes results beneath
`output/google-oauth-20261119`, and stops its processes. Optional second argument
selects a Playwright project; `--keep` keeps the disposable preview until a `stop`
file is created in the output directory. Google Cloud configuration and a real
Google-account sign-in must still be verified on the configured deployment.
