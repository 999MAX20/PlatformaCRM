# CRM-LANDING-INTEGRATION-20261106

## Result and boundary

Owner-authorized local integration of the supplied CRM landing is complete in
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`, dirty snapshot
based on `d6cf5829`. The landing is served at `/`; sign-in remains `/login`.
The normal frontend build contains all pages, assets and draft legal downloads.
Digital and Market source, DNS and working databases were not changed.
The owner subsequently authorized scoped deployment; the deployment result below
supersedes the initial local-only boundary. Overall production readiness is not claimed.

Reused the supplied HTML/CSS/JS and existing React authentication. Adjusted local
asset/page URLs, sign-in locale handoff, actual browser-storage disclosure and
Digital URL. At 320px a small logo-width adjustment prevents header overlap.
Public dentistry copy is the owner's supplied marketing scope; shared CRM copy is unchanged.

## Verification

- Existing login policy15 + Vite cache isolation3 PASS. New dev route check1 PASS.
  Initial combined run failed only because a test requesting port0 selected occupied5173;
  fixed ephemeral-port reservation and reran the affected route test.
- `npm run build` in `scripts.codex_verify.safe_environment`: i18n6921 keys,
  TypeScript, production frontend and widget build PASS.
- `npm run check:bundle`: PASS; two locale chunks still warn above500kB.
- Chromium production preview: RU/KK/EN at1440/390/320, locale persistence,
  scenario arrow keys, mobile menu/Escape/focus, sign-in and browser back,
  legal directory, no horizontal overflow and no page exceptions PASS (9 combinations).
  Direct login/MFA/calendar/password-reset SPA route responses PASS.
  Invalid login localized error, recovery navigation and protected-route redirect PASS.
  An initial error assertion expected raw API text; corrected it to the established
  localized login message and reran successfully. Canonical dev5173 root/login PASS.
  Initial login timeout was caused by the test blocking its isolated API origin;
  corrected mocks before external-origin blocking and reran successfully.
- Real Caddy with disposable credentials/upstream: preauth landing/assets denied,
  authenticated root/index landing, nested page, login/calendar SPA, API body,
  missing landing404/media404, webhook restrictions and gate-outage fail-closed PASS.
- Static artifact byte comparison PASS;640 local HTML page/asset/download references
  resolve to files. Legal downloads byte-identical to supplied source.
- Final narrow CSS change copied into disposable dist; all9 browser combinations
  and complete static artifact identity rechecked. TypeScript inputs unchanged.

Commands/scripts/logs/screenshots and starting ownership snapshot are in
`output/crm-landing-integration-20261106/`. No installs, full-project suite,
working-DB writes or migrations: routing/static frontend scope only. Auth uses
synthetic API responses; this does not recertify backend authentication or live services.

## One VM, three products — proposed arrangement

One ingress Caddy binds80/443 and selects independent virtual hosts by domain.
Digital stays in its own folder and serves its own static build at platformadigital.kz.
The CRM domain serves this combined landing/SPA build and proxies its own API.
Market keeps its own domain, build and backend. Exact CRM/Market domain names and
production rollout remain owner decisions; no DNS or cloud changes were performed.
Use separate service identities, secrets, database roles/databases, storage prefixes
and backups. Do not share cookies or database access just because the VM is shared.
Bind internal services to private Docker networks/loopback, expose only ingress,
and retain per-product health checks, logs, restart policies and rollback artifacts.
A shared VM is one failure/resource boundary; size it from measured combined load,
RAM, disk, worker/concurrency requirements rather than promising capacity here.

## Remaining work

No local implementation remainder in this scope. The owner subsequently authorized publication of the landing alone. The candidate
is based directly on origin/main, excluding all18 unrelated local commits and
preserving the remote security commit. Local branch/index/files remain intact.
Existing local checks describe the working snapshot; exact candidate CI is tracked
separately after push and is not predeclared green. Main and stand CI subsequently
completed successfully. The scoped deployment is recorded below; public access,
other-product domains and full-release acceptance remain separate work. Legal drafts require their own
approval before use as final documents. No roadmap phase was opened or closed;
CRM/API/access/AI contracts need no behavior changes.

## Publication follow-up verification

Owner authorized publishing only this landing, without deployment. The candidate
has parent b96a69514b47a7211899e745b94b1109a36bb4e6;18 unrelated local commits
are excluded. The ordinary index and current branch are not used for publication.
Temporary index/Git objects hold the candidate; no second source checkout is created.

Exact candidate TypeScript app690 roots/node2 roots PASS using an in-memory Git
filesystem and the unchanged installed dependency lock. Exact candidate production
frontend build and bundle check PASS; browser9 locale/viewport flows plus invalid
login/recovery/protected-route redirect repeated against that artifact PASS.
Candidate static assets171 matched repository data; existing widget/dependency
inputs unchanged. Standard clean CI remains a separate post-push observation.
Caddy/gate sources match the previously verified routing boundary exactly.

Imported HTML/CSS line endings and licence trailing whitespace normalized for
committed diff hygiene, with no visible content change; legal DOCX/TXT/ZIP unchanged.
Candidate diff reviewed for unrelated work; no workflow, backend, dependency,
credential or production configuration values included. Existing main workflows
run CI/stand-boundary tests and contain no deployment job. Deployment was excluded
from publication and later authorized separately as recorded below.

Preparation failures were tooling-only and corrected before commit: Windows path
separators in Git index input; text-encoding mismatch in the helper; overbroad
capability-prefix extraction caught by diff review; raw CRLF/trailing whitespace;
virtual TypeScript node_modules-directory recognition and binary-asset passthrough.

## Owner-authorized deployment follow-up

2026-11-06:112 published landing files and exact Caddy root/static handlers deployed
to protected platformacrm.kz. All1342 existing release files, CRM SPA bundle,
password/env and SSE handler retained; Caddy validated and gracefully reloaded.
Live HTTPS checks and Chromium RU/KK/EN/mobile home-to-login flows PASS;
encrypted files backup and backup health PASS. Existing CRM form renders normally.
Successful account authentication/MFA was not exercised; no credentials were changed.
The deployed runtime is a composed release: existing CRM bundle retained, source-only
LandingHome helper not rebuilt into it. Direct landing/login routing is supplied
by Caddy. No full-release acceptance or unrelated deployment is claimed.
Full manifests, rollback and evidence: `output/crm-landing-deploy-20261106/RESULT.md`.
