# GOOGLE-SHEETS-20261119

## Production continuation — 23Nov2026

Resume after owner extension update: HEAD263f8793 unchanged, origin/main equal;
foreign auth/medical/YCloud WIP preserved. Prior live and local PASS -> missing
exact error screenshot -> rerun only isolated Calendar browser acceptance.
No product rewrite, real Google grant or working-DB mutation required.

Owner explicitly requests production-ready Google Sheets and Google Calendar.
Prior Sheets implementation and synthetic acceptance remain historical evidence;
At continuation start, Calendar synchronization and live Google acceptance were missing. Minimal delta:
verify/reuse Sheets and shared OAuth, implement Calendar behind existing integration
and scheduling services, then prove recovery, permissions and real provider flows.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
starting HEAD030b9b41d3ea3215eae6c31b4ed9eec48d5ab9a4. Starting foreign WIP retained
in ignored output/google-production-20261123/starting-status.txt. No foreign edits owned.
Mode implementation/verification; gaps code, evidence, environment and Calendar policy.
Owner decisions23Nov: CRM is authoritative; Google receives appointment copies;
external Google busy intervals block booking. Event content is time, client name
and service name only; no phone, messages or medical data. Google-side changes
must never move/cancel CRM appointments. Existing specialist calendars are reused.
Sheets scope remains client import/export and manual refresh, not whole-CRM sync.
Reuse encrypted actor/Business connections, import snapshots, export reservations,
existing permission/field scopes and audit. Preserve Google login and YCloud.
Risk: sensitive external transfers, duplicate writes, revoked access, cross-tenant
routing, appointment lifecycle/availability and provider outages. Focused isolated
tests after each backend slice; completion affected/dependent suites, PostgreSQL races,
system/drift and isolated migration checks, frontend build/types, localized reachable
browser actions and inspected screenshots, then controlled live Google acceptance.
Skills: zani-build-integration-reliability and zani-run-verification; UI skills must
be read and scoped before UI edits. Production Google project/configuration, OAuth
verification where required, live grants and deployment remain separate evidence
boundaries. No working DB migration, production deployment or client-data transfer
is implicitly authorized by this checkpoint. No new dependencies currently planned.
23Nov browser inventory: extension Chrome profile named Settings, one blank tab;
previous Platforma Digital session is not currently visible. Baseline Google suite
started in disposable isolated runtime; output/google-production-20261123/baseline.log.
Google Cloud opened successfully, but the currently signed-in account lacks project
access. Owner asked to open Platforma Digital profile/account; no IAM request sent.
Owner opened Platforma Digital; project credentials and OAuth overview readable.
Baseline18 PASS; Calendar OAuth7 PASS; provider adapter7 PASS; sync lifecycle10 PASS
in disposable SQLite, mocked Google. Logs in output/google-production-20261123.
Calendar models/migration0014 and sync are local WIP, not applied to working DB.
Availability4 PASS on first slice; expanded combined OAuth/provider/sync/API/booking
suite42 PASS after horizon, provider-date normalization and revoked-token fixes
(`calendar-combined.log`). On-demand Google checks cover booking beyond the90-day
snapshot; outbound copies include later appointments. Calendar feature flag gates
OAuth start/complete and writes. Pending/stale state is exposed to UI.
First frontend build found Select props mismatch; corrected to existing options/label
contract. Repeat build PASS (`frontend-build-fixed.log`), including i18n8139,
TypeScript, Vite and widget. Existing chunk warnings retained. Live results below
supersede the earlier pending-consent state. Affected backend completion201 PASS (`backend-completion.log`):
Google OAuth/Sheets/Calendar, import/export access, scheduling/resource booking,
management booking and branch scheduling; Django check and migration drift PASS.
PostgreSQL4 races PASS (`postgres.log`): existing Sheets OAuth/import/export plus
concurrent Calendar workers reserve/insert one copy. Dedicated UUID test DB dropped
by the runner finally block; exit0. Working DB remains unchanged.
Browser synthetic RU: bind existing specialist/calendar -> synchronized, pause ->
paused, resume during provider outage -> explicit failed status, automatic retry
after provider recovery -> synchronized. Mobile390x844 EN form and KK empty-calendar
state inspected, Escape returns focus to Connect. Screenshots in
output/google-calendar-browser/{bind-ru,synced-ru,error-ru,mobile-en,empty-kk}.png.
No clipping observed in the affected dialogs/cards. KK provider-list503 -> Retry
-> selectable calendar PASS (`retry-kk.png`); disconnect completed and new page
shows Connect (`disconnected-kk.png`). The original tab detached during disconnect;
same-profile fresh tab recovered the original target and confirmed its outcome.
No cross-channel fallback. Focus restoration after this detached disconnect is
unverified; Escape focus-return was verified separately. Owned fixture runner
session98940 uses ports60888/60889.
Live Google acceptance fixture session36861 uses isolated temporary DB, ports8000/
5173 and only configured Google credentials; other providers disabled. It has only
synthetic seeded data; no production/work DB mutation. Stop files: respective output
directories `stop` and `google-production-20261123/live-stop`.
Owner confirmed Sheets and separately Calendar consent. Both callback screens and
connection cards show the Platforma Digital account. Live Sheets PASS: exported2
synthetic clients, refreshed the same destination, actual Google Picker selected
that sheet, previewed3 rows, imported exactly1 new synthetic client; existing2
were deduplicated. Import close returned focus. Screenshots live-export.png and
live-import.png under output/google-production-20261123. Spreadsheet title
PlatformaCRM Clients; only synthetic fixtures transferred.
Live Calendar: created dedicated PlatformaCRM Integration Test 2026-11-23 calendar
in Asia/Almaty, bound E2E Specialist Schedule. Real API sync succeeded; Google UI
shows one private event with only client/service/time, no guests/description/location.
Created external busy event24Nov10:00-11:00 Asia/Almaty. Real pull persisted only
05:00-06:00 UTC interval; reschedule API returned409 schedule_conflict explicitly
naming Google Calendar, and available-slots excluded both overlapping30min slots.
A valid reschedule to11:00 Asia/Almaty returned200; Google readback showed the same
single copy at11:00, no duplicate. Editing its title in Google was repaired by
CRM sync. Cancellation through CRM API returned200/cancelled and Google showed
only the independent busy event. Removing that test event restored the previously
blocked10:00 slot. Thus live create/update/cancel, replay, external edit repair,
busy exclusion and release PASS. Google deletion/recreation is automated evidence,
not separately exercised against the live provider.
Logs live-api-acceptance.log; screenshots live-calendar-google.png and
calendar-consent-handoff.png. No credentials saved in evidence.
Final UI refinement keeps disconnect available when binding status fails, removes
queued notice after a newer sync and corrects pending copy. Final build PASS
(`frontend-build-final.log`, session96339). Disconnected state inspected after HMR;
live queued notice appeared and disappeared after a newer completed sync PASS.
Network-blocked bindings response produced the error and Retry in accessibility
state, with disconnect still available; removing the block recovered automatically.
The earlier screenshot caught a transition without error text. After the owner's
extension update, resumed on isolated runner73204 (frontend55512/backend55511).
Blocked only calendar/bindings requests after normal page load. Error banner,
legible copy, Retry, and available disconnect visually PASS in
output/google-production-20261123/calendar-bindings-error-verified.png.
Removed the browser network block, clicked Retry, and observed error disappear
with connection controls intact PASS. No application code changed for this check.
The final visual error-state criterion is closed; previous missing screenshot is
superseded by this focused evidence. Required local/live scoped acceptance passed.
Public home/privacy URLs and production Google configuration remain open.
Final review: prior lifecycle PASS -> GET410 was treated like never-created404 ->
preserve a cancelled tombstone for410 so sync reserves a fresh identity. Added
provider regressions for both responses; existing deleted-event lifecycle tests
cover reservation/retry. Focused provider/sync/availability/API recheck37 PASS in
isolated DB; system check and migration drift PASS, exit0. Log
calendar-gone-regression.log; no frontend/runtime contract change. Prior201 dependent
and PG4 evidence retained for unchanged boundaries; no CI run. Task diff hygiene
PASS. Task-only implementation committed as
fe23674e71d803bcf7832e2041f0f2cd775c8edb on codex/ui-testing-toolkit, canonical root.
Committed-range static gate against263f8793b37c374b8f89b7312c473bd8f52a1973 PASS
(system/drift, working/index/range hygiene), log committed-static.log. Normal push
to origin/main succeeded; ls-remote SHA matched fe23674e71d803bcf7832e2041f0f2cd775c8edb.
Foreign medical URL hunks and other WIP excluded. Runner73204 stopped through own
stop file, exit0. CI intentionally not triggered/polled under local acceptance;
no workflow changes, deployment or working-DB migration. Scoped implementation,
local checks and controlled live-provider acceptance complete. Remaining environment/
owner decision: approved public home/privacy URLs, separate production Google
configuration/verification, authorized target migration/activation/deployment.
Known limits remain in the current integration contract; full public launch is not closed.
Reference: https://developers.google.com/workspace/calendar/api/guides/errors.
Owned live session36861 and synthetic98940 stopped through their stop files; both
exit0, own processes/temp DB cleaned. Real Google grants were not revoked because
client-wide revocation can affect both connectors. Tokens lived only in the removed
temporary DB; continuing live acceptance requires a new local connection. The
named empty test calendar and synthetic spreadsheet remain in the owner account.
No real clients or normal working DB were used. Browser network block was cleared
before the extension stop. No production deployment or working migration0014.
Google Cloud readback23Nov: External/Testing, one test user Platforma Digital;
Publish disabled because Branding lacks home/privacy/terms URLs. Authorized domain
platformacrm.kz is already present. Existing legal-page component has an empty body
pending owner-approved copy. Requested approved public URLs; no policy invented or
Google publication attempted. Separate production project/config and scope/brand
verification remain open per Google's production policy.
UI skills read: antislop (during, owner rule), ui/layoutmobile/human/copywriting,
zani-review-frontend. Existing integration cards/tokens are design authority:
calm operational settings, ENERGY1/RHYTHM1/MOTION1. No new assets or shell changes.
Applied requirements: real connection/binding status only; explicit export confirmation;
labels, keyboard/focus and retained selection on failure; RU/KK/EN wrapping and
mobile layout with existing controls. Capture/inspect affected screenshots and
exercise loading/empty/error/retry/permissions before declaring UI acceptance.
React best-practices applied to the changed components: reuse query-cache ownership,
conditional provider requests and established controlled form/accessibility components.

## Historical implementation contract — 19Nov2026
User authorizes implementation of shared Google OAuth and Sheets connector plus Google Cloud setup in Chrome profile Platforma Digital. Calendar must support existing specialist calendars; Calendar event synchronization is outside this implementation slice.
Root: C:/Users/user/Desktop/PlatformaCRM. Base d8ec748aa46782051198b13c8a547d2f49d13850; retain current branch. Starting foreign WIP listed below; no ownership claimed.
Gap: code and environment. Existing catalog placeholders + import/credential foundations → current code inspection → add Google adapter, reuse import preview/confirm and scoped export.
Scope: OAuth start/complete, encrypted refresh, revoke/disconnect, Sheets Picker/metadata, immutable client-import snapshot with mapping/confirm, client export and repeat update in dedicated spreadsheet. No working DB migration, production deployment, Calendar writes or unrelated changes.
Risk: OAuth/account binding, tenant and current permissions, external data disclosure, duplicate import/export, partial external failure. Generic connector/credential APIs must not bypass Google ownership/state.
Checks: isolated focused OAuth/API tests first; Sheets import/export permission/retry tests next; affected import/connector regressions, Django system/drift, isolated migration, frontend build/types, targeted desktop/mobile RU/KK/EN actions and screenshot inspection. Real Google acceptance separate from mocks.
Skills: zani-build-integration-reliability, zani-review-frontend, zani-run-verification; UI antislop during + ui/layoutmobile/human/copywriting. Preserve existing cards/tokens; use current import review; keyboard/focus and error recovery; RU/KK/EN neutral copy.
Permission: integrations MANAGE plus current Clients CREATE/VIEW and field policy. Audit connection/import/export; reuse import BusinessEvents; no AI or messages. Environment: dedicated Google OAuth client/secret/redirect and Picker key/project number; encrypted credentials use existing keyring.

## Implementation and Cloud result
Implemented shared OAuth start/complete with PKCE and consumed state, encrypted refresh, account binding and local/remote disconnect; Sheets Picker, immutable client-import preview/confirm, scoped export and manual refresh. Durable export reservation, appProperties discovery and literal string cells protect retries and formula handling. No Calendar event implementation.
Google Cloud project `platformacrm-integrations-dev` (844826644933), External/Testing: Sheets, Drive, Picker and Calendar APIs enabled. Test user is the owner's account. Scopes openid/email/drive.file only. Web client PlatformaCRM Local Dev uses origin http://127.0.0.1:5173 and callback /app/integrations/google/callback. Picker Local Dev key restricted to Drive/Picker APIs and http://127.0.0.1:5173/* plus https://docs.google.com/*; saved restrictions read back. Owner accepted legal terms and separately confirmed credential creation. No billing/trial. All five Google settings saved only in ignored .env; no secrets in evidence or screenshots.

## Verification
- OAuth iteration6 PASS; combined import11 PASS; export16 PASS. Earlier fixture-email collision and 500-vs-503 provider error corrected; later runs supersede those failures.
- Completion: `isolated_runtime` then `manage.py check`, `makemigrations --check --dry-run`, `manage.py test apps.integrations.tests_google_oauth apps.integrations.tests_google_sheets apps.integrations.tests_google_sheets_export apps.core.tests_client_import_permissions apps.core.tests_import_job_boundaries apps.core.tests_export_access -v 1`: check/drift PASS,72 tests PASS, output/google-backend-completion.log. Disposable SQLite with all migrations; Google mocked.
- PostgreSQL: output/run_google_postgres.py creates a UUID-named test_google_* database owned by crm_app in the dedicated local cluster, overrides test NAME to that disposable DB, runs tests_google_concurrency, then drops only that generated DB in finally. Initial run13 PASS (11 imported fixture-class tests +2 race tests). Final module imports fixtures as modules to avoid duplicate discovery and adds concurrent import; final3 PASS (OAuth callback, export create/write, import snapshot races), exit0; disposable database removed.
- Frontend `npm run build` PASS after focus/retry fixes: i18n7598, TypeScript, Vite and widget; output/google-frontend-final-build.log. Existing chunk-size warning. No package changes/install.
- Browser: scripts/verify_google_sheets.py uses canonical source, isolated DB and dedicated ports53523/53522, synthetic Google adapter/Picker and test scanner; real API/import/export permissions and DB transitions. RU import preview/mapping/confirm imported1 client; export3 clients and refresh retained one destination. EN390x844 import dialog inspected. KK metadata-error400 -> Retry -> selector PASS; cancel selection leaves card unchanged; disconnect -> disconnected + Connect button focus PASS; cancelled OAuth -> localized message and return link PASS. Loading state observed. No-data: disconnected card; empty-sheet handling exists in backend; no separate browser empty-sheet case. No live Google access/Picker SDK proof.
- Focus defect found and fixed: Overlay uses data-focus-return-id. Escape returns focus to Import. Sheet select accessible label added. Retry now retries failed choose/connect instead of only refetching status. Browser confirmed retry and focus after fix.
- Screenshots saved and visually inspected: output/google-sheets-browser/connected-ru.jpg, import-preview-ru.jpg, import-mobile-en.jpg, import-kk-recovery.jpg, oauth-cancelled-kk.jpg; Google Cloud key restriction screenshot output/google-picker-restricted.jpg. Geometry, wrapping, labels, keyboard close/focus and translated copy inspected. No adjacent UI redesign. Picker's actual Google iframe remains live acceptance.
- Diff hygiene PASS. Task-owned files reviewed including new files; .env ignored. README setup and integration contract updated; registry links this evidence. No separate Google roadmap/passport was changed: this authorized implementation slice is recorded in the current integration contract, with Calendar still open.

## Remaining acceptance and publication
Code: implementation and scoped local verification complete. Owner explicitly approved integrations.0012 and0013 on local PostgreSQL platformacrm,127.0.0.1:55432 (19Nov2026). Target configuration verified; migrate plan contained exactly these two migrations. Applied with `call_command('migrate', 'integrations', '0013', interactive=False)`; both OK. Django check PASS, MigrationRecorder confirms both applied, ORM reads confirm all three Google tables. Log: output/google-working-migration.log. No existing data removed, no seeds, no deployment or Google grant. Remaining environment/evidence: real OAuth grant/Picker/import/export. Calendar synchronization is later scope, not claimed complete. Production OAuth verification and production origins/secrets are not configured.
Starting HEAD d8ec748aa46782051198b13c8a547d2f49d13850 advanced by unrelated YCloud commit9c86bc769d11fb563e9cc32f43d9e933e7f96fec, already on origin/main. This task did not create that commit. Initial foreign invitation/WhatsApp WIP below is preserved. No foreign work is staged. Published code918096ce6e791f3afc7a9b4370f7f7ce80a549bb on branch codex/ui-testing-toolkit to origin/main; remote SHA read back. Static gate `scripts/codex_verify.py --mode static --base-ref 9c86bc769d11fb563e9cc32f43d9e933e7f96fec` PASS (output/google-static-gate.log). CI44397837621 running, not PASS. CI workflow is checks/tests/build only; no push-triggered deployment found in the applicable workflow.
Browser access was restored by owner; no bypass used. Test tab closed and runner stop file written; runner exited0; its own servers and temporary database cleaned up. Cloud key-details tab retained. Viewport override reset.

## Starting foreign Git snapshot
```
 M STATUS.md
 M apps/accounts/serializers.py
 M apps/integrations/services.py
 M apps/integrations/tests.py
 M apps/integrations/tests_whatsapp_signup.py
 M docs/current/access.md
 M docs/current/frontend.md
 M docs/current/integrations.md
 M docs/testing/evidence/invitations-24h-20261112.md
 M docs/testing/task-state/PRIMARY-SESSION.md
 M frontend/e2e/fixtures/whatsapp-signup.tsx
 M frontend/e2e/pilot-invitations.spec.ts
 M frontend/e2e/whatsapp-signup.spec.ts
 M frontend/src/app/routeGuards.tsx
 M frontend/src/features/integrations/components/setup/useWhatsAppSignup.ts
 M frontend/src/features/settings/components/TeamAccessControl.tsx
 M frontend/src/features/settings/sections/TeamSection.tsx
 M frontend/src/lib/i18n/en/identity.ts
 M frontend/src/lib/i18n/kk/identity.ts
 M frontend/src/lib/i18n/ru/identity.ts
 M frontend/src/types/identity.ts
?? apps/accounts/tests_revoked_business_access.py
?? frontend/src/features/auth/BusinessAccessRevoked.tsx
```

## Live acceptance continuation — 19Nov2026
Owner requested real OAuth in Platforma Digital plus Picker/import/export. Prior synthetic checks and approved migrations remain valid; new gap is live environment/evidence, not a rewrite. Current HEAD fda242c4, same canonical root/branch; unrelated invitation and Overlay WIP preserved. Plan: verify canonical local services, authorize actual Google account at consent screen, select a test spreadsheet and named business, confirm preview before import and explicit data destination before export; check resulting client/sheet and retry without duplicates. No Calendar writes or production deployment. Initial ports8000/5173 absent; launched documented dev.ps1 (output/google-live-start.log), startup in progress.

Local startup: first dev.ps1 attempt hit a transient backend reloader process-registration NoneType error after starting Redis/scanner/updater/worker/backend. Changed condition verified: canonical backend listening8000. Second documented launch reused verified processes and started canonical Vite5173; health/proxy/scanner/worker checks completed, exit2 only for unrelated pending bots0015, payments0002/0003, scheduling0015. No unrelated migration applied. Logs output/google-live-start.log and output/google-live-start-recovery.log; process ownership receipt output/local-dev/processes.json. Live browser profile Platforma Digital opened127.0.0.1:5173/login; owner asked to sign in and identify test business. No Google grant or client data transfer yet; tab preserved for handoff.

Owner then explicitly authorized creating a separate test business and performing login/actions. Created only a new local fixture via activate_landing_business and apply_business_type_defaults: business17 (Google Sheets — тест 19.11.2026), owner22 (google-sheets-live-20261119@example.test). Random password stored only in ignored output/google-live-account.json; never printed. Existing accounts/businesses unchanged; local configured MFA policy unchanged. Browser replacement tab1634126914 in Platforma Digital can read AX login page, but Playwright fill times out at Runtime.evaluate; AX setValue times out at DOM.resolveNode; longer locator timeout still hits provider deadline. No successful login observed, no Google grant/transfer. Requested owner reload/re-enable extension only; agent will perform login after recovery. Test account creation is complete, browser evidence remains blocked on control.

Owner requested autonomous reload while away from computer. Attempted tab.reload:30s timeout reset CUA runtime. Fresh inventory found Platforma Digital now browser4 (profile matched by name/extension), existing login tab1634126914. Rebinding this tab in the fresh session also timed out and reset runtime. No confirmed reload/login, no grant/transfer. Recovery through permitted extension channel exhausted for current unchanged state; no native Chrome control, process kill or alternate protocol used. Test business17 and local services preserved.
