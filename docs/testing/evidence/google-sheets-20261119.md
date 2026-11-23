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

## Public production acceptance continuation — 23Nov2026

Owner requests completing both integrations and acceptance through production.
Prior local/provider acceptance and published02bc229b retained -> open deployment,
Google production configuration/verification and public-page gaps -> no rewrite.
Canonical root/branch unchanged; starting HEAD02bc229ba9a49173233261de16b5ed6079be9934.
Foreign dirty auth/medical/YCloud/docs changes remain excluded. Mode operation and
verification; prepare reviewed candidate before target activation. No real customer
transfer or unrelated release. Reuse published connector/provider/UI/tests.
Checks: exact target configuration/migration plan, candidate affected/dependent
checks, backup/rollback readiness, production OAuth/Picker plus synthetic Sheets
import/export and Calendar lifecycle/busy/recovery after authorized activation.
No CI. Credentials remain private; no new permissions/domain policy invented.
Current Cloud readback: only platformacrm-integrations-dev visible, Testing;
home/privacy/terms blank. Public legal article intentionally empty pending approved
copy. Owner asked for approved URLs or permission to draft for review.
SSH read-only succeeds at94.131.87.21; crm-web/worker/events/stand/beat all active,
WorkingDirectory /opt/platforma/releases/20261119-google-final-64d29158.
Do not confuse earlier guessed nonexistent platforma-* unit names with outage.
Production configuration and target activation are not yet performed.
Production Cloud project created and read back: platformacrm-integrations-prod,
PlatformaCRM Integrations Prod, no billing/trial activation. OAuth branding form
prepared with PlatformaCRM, External and existing business contact; stopped before
Google API Services User Data Policy acceptance. Awaiting owner action-time consent;
Chrome tab retained. Screenshot output/google-production-20261123/production-oauth-policy.png.
Server read-only: all six Google integration settings absent/empty; Calendar source
absent. SQL migration recorder confirms integrations0013 and scheduling0015 applied;
required new migration is integrations0014, not yet executed. First SQL invocation
failed due PowerShell quoting; corrected stdin query succeeded with no DB writes.
No target source/config/services changed. Next: owner policy consent and approved
public copy, then OAuth/API credentials and exact candidate/deployment acceptance.
Official production requirements checked23Nov:
https://developers.google.com/identity/protocols/oauth2/production-readiness/policy-compliance

### Owner supplied legal documents and Google policy consent

Owner explicitly accepted Google API Services User Data Policy and authorised review
and necessary edits of Desktop documents. Located Platforma CRM RU/KK/EN legal set
under Desktop/Platforma_—_юридические_документы_35_файлов. Sources are draft0.1 with
unfilled hosting/recipient/retention/effective-date fields, not approved public copy.
Created9 separate v0.2 copies (01 policy,07 browser notice,09 integration terms in
three languages) in Platforma CRM/Редакция Google 2026-11-23; original hashes match.
Added actual Sheets fields including notes, Calendar minimal payload/busy intervals,
OAuth scopes/tokens, Google destination and restrictions, recovery/pause and accurate
disconnect-versus-deletion behavior. Report documents remaining publication inputs.
Code unchanged; no deployment or migration. Structural/version checks PASS.
Chrome/document recovery23Nov: owner authorised installed LibreOffice. Chrome4
extension access recovered; original OAuth creation completed in a fresh tab.
Google policy accepted; overview confirms OAuth configuration created for
platformacrm-integrations-prod. No OAuth clients configured yet. Screenshot saved
and inspected: output/google-production-20261123/production-oauth-created.png.
Nine DOCX rendered with bundled render_docx.py and owner-authorised LibreOffice;
all23 final pages visually inspected PASS. Footer0.1 fixed to0.2 and rerendered.
Source/output hashes and footer text verified; originals unchanged. Empty optional
footer parts excluded from version assertion after initial overstrict check failed.
Final renders/manifest: output/google-production-20261123/legal. Desktop report updated.
No app edits, deployment, migration or CI. Public-policy recipient/hosting/retention
facts, public pages, OAuth clients/scopes and exact target acceptance remain open.

### Production activation preparation — owner continuation23Nov

Owner authorised completing public policy/publication, production OAuth and server
acceptance. Starting HEAD6347057f; newer unrelated dental commits and dirty auth,
medical, YCloud changes excluded. Existing Google implementation/provider checks
reused. Integration reliability skill applies: narrow credentials, tenant isolation,
recovery and disabled-until-ready rollout; no new domain behavior intended.
OAuth web client PlatformaCRM Production Integrations created after action-time
owner confirmation in platformacrm-integrations-prod; origin https://platformacrm.kz,
callback https://platformacrm.kz/app/integrations/google/callback. Creation and list
readback PASS; screenshot output/google-production-20261123/oauth-client-created.png.
Client secret saved outside repository under owner-only Windows ACL; not logged.
Project remains Testing; API enablement, Picker key, scopes and verification pending.
SSH read-only reconfirmed crm-web/worker/beat active in prior release; six Google
integration settings absent. Object-storage endpoint storage.yandexcloud.kz, region
kz1 confirmed from target configuration; this alone does not prove all processing,
backup locations or retention. Timer inventory shows no dedicated CRM backup timer;
cron/provider backup investigation still required before concluding backup absence.
Public legal pages and retention facts remain open. No production mutation or DB
migration performed. Required next checks: exact candidate versus deployed overlay,
backup/rollback, affected gates, then synthetic real-provider target acceptance.

Sheets/Drive/Calendar/Picker APIs enabled and dashboard readback PASS; screenshot
output/google-production-20261123/apis-enabled.png. No billing/trial activated.
Target RELEASE metadata identifies artifact tree64d29158, publicationcba360ca and
source basea0dfb128. A first unfiltered manifest read was oversized; bounded metadata
read corrected it. Candidate not assembled: scoped comparison includes unrelated
YCloud delta which must be excluded. Existing Google-auth checkpoint confirms backup
timers/archive disabled by prior owner decision; no re-enablement. Owner asked whether
approved retention regulation exists. Facts and explicitly unapproved proposal saved
in output/google-production-20261123/production-facts-and-retention-proposal.md.

Prepared immutable runtime candidate 9a1556f22245d719b59b1cd68ef8a8815af9cd05 over deployed
artifact64d29158 with30 Google task paths. Initial patch failed only on config/urls.py
medical context; regenerated exact two Google additions against deployed file.
Cached-index patch check PASS, no checkout/worktree/source overwrite. Candidate
not built/tested/deployed; canonical dirty files preserved. Manifest and patch under
output/google-production-20261123/. Picker credential action prepared; owner
action-time confirmation pending. Retention-regulation question remains pending.

Owner23Nov confirms no retention regulation and requests a proposal; separately
approves restricted Picker key creation. Key PlatformaCRM Production Picker created
with Websites restrictions exactly platformacrm.kz/* and docs.google.com/* (HTTPS),
only Drive/Picker APIs. Saved outside repo in existing owner-only ACL directory;
edit-page readback confirms both API and website restrictions. Screenshot:
output/google-production-20261123/picker-key-restrictions.png. One post-close AX
observation still contained restricted browser key; secret not repeated in evidence,
OAuth client secret unaffected. Subsequent observations redact keys; transient detached
close node resolved by fresh state (dialog already closed). No extra key created.
Detailed unapproved retention proposal saved beside Desktop legal v0.2 documents:
Регламент хранения Google — проект 2026-11-23.md. It separates Google technical
retention from backup and tenant closure; requirements not yet implemented/approved.
No source changes or target activation; exact candidate checks/public pages/scopes
and provider verification remain unfinished. Existing local implementation PASS is
not evidence for new retention promises or deployed readiness.

### Sheets identity safety — owner request23Nov
Prior real-provider PASS -> confirmed exact-phone/first-match defect in shared
import confirmation -> minimal normalized identity matching and fail-closed ambiguity.
Base6347057f, canonical branch unchanged; foreign WIP excluded. Reuse clients.identity,
normalized indexed fields, existing preview/errors and transaction rollback. No new
schema or automatic merge. Preserve fill-only behavior and archived matching;
localize the existing error component without changing layout or controls.
Risk: shared client lookup callers (clients/leads/deals), permissions, atomicity.
Checks: normalized phone/email, split and multiple matches, archived/tenant boundaries,
preview plus confirm revalidation, full-job rollback, repeat and concurrent imports;
affected import/Google suites, Django check/drift. Production and retention remain
open; update immutable release candidate after this fix passes.

Implementation/acceptance23Nov: normalized indexed phone/email matching, ambiguous
candidate rejection at preview and confirmation, per-Business client-import lock.
No permission, notification, BusinessEvent or AI policy change; rollback preserves
existing audit/event atomicity. No migrations or working-DB writes.
Anti Slop during (owner preference), copywriting and existing component direction:
explain conflicting contacts and next action, neutral RU/KK/EN wording, preserve
tokens/layout, verify keyboard and error recovery. No new product screen or assets.
Focused36 tests PASS; completion112 tests OK/1 SQLite concurrency skip, Django
check0 and makemigrations --check --dry-run no changes. A separate isolated local
PostgreSQL concurrency test PASS, two jobs return200 and create one client; its
temporary database removed in runner finally. No CI run (owner local acceptance).
Commands: isolated_runtime, Django test apps.core.tests_import_identity,
tests_client_import_permissions, tests_import_export, tests_import_lifecycle,
tests_import_job_boundaries, tests_import_mapping_ui; apps.integrations.tests_google_sheets,
tests_google_sheets_export; apps.clients.tests. Full module paths use their stated
package. Logs: output/google-import-identity-{tests,completion,postgres}.log;
PostgreSQL runner output/run_import_identity_postgres.py.
Frontend check-i18n (8201 keys), tsc -b and vite build with isolated output PASS;
existing large-chunk warning only. Log output/google-import-identity-build.log.
Browser: actual ImportJobReview/ImportErrors with explicitly synthetic API fixture
at /e2e/fixtures/import-identity.html; real backend behavior covered by API tests.
Conflict disables confirm; mapping edit retains block, repreview clears corrected
conflict, Tab/Enter confirms and freezes imported mapping. RU/KK desktop and RU/EN
390px mobile screenshots saved and visually inspected; no clipping, visible focus.
UI gate scoped PASS: truthful actionable error, preserved appearance, localized
copy, recovery/keyboard and mobile checks. New themes/dialogs/navigation/assets not
applicable. Screenshots output/google-production-20261123/import-identity-*.png.
Browser4 unavailable; current inventory Chrome3 served local fixture successfully.
Limits: no name-only dedup or inferred country; no automatic merge or existing
duplicate cleanup. Intra-file conflicts discovered during insertion are atomically
rejected, not all predicted in preview. Manual concurrent creation does not share
the import lock. No deployment yet; publication and production continuation next.

Publication receipt: code/docs a03dc0e24dff4c876b76057e5ce1085bd850cb6a normal-pushed
from codex/ui-testing-toolkit to origin/main, remote SHA read back equal. Starting
origin/main equalled6347057f, so no foreign outgoing commits. Shared STATUS and
integration contract staged by task-only content; foreign WIP preserved. Intended
diff/new fixtures reviewed; working/index diff checks PASS. Owned UI fixture server
18743 stopped after verification; other services unchanged. Fixture edit triggered
a transient Vite createRoot/HMR warning before the explicit full reload; subsequent
screen/action checks used that fresh page, not HMR as acceptance evidence.

Production continuation: immutable candidate updated with the verified identity
patch; tree a2f47ce3b108b8955d10aeb628ee05f5993a7dc0,33 selected paths over deployed
64d29158. Cached-index patch check PASS; candidate itself is not built/tested/deployed.
Manifest output/google-production-20261123/candidate.json and runtime patch updated.
Owner approved technical retention requirements and then explicitly chose retaining
minimal mirror identifiers to prevent reconnect duplicates; their retention term
is to be decided separately. The Desktop regulation now reflects this exception
and approved-requirements status; no automatic deletion or backup enabled.
Owner reopened Platforma Digital; Chrome5 read the intended production Cloud project.
Configured and saved exactly openid, userinfo.email, drive.file,
calendar.calendarlist.readonly and calendar.events in OAuth Data Access, matching
application scope requests. This declares requested scopes, not a user data grant.
Save success read back; screenshot production-scopes.png saved/visually inspected.
AX clicks twice timed out with partial state; fresh DOM inspection and supported
Playwright controls completed the intended action without duplicate toggles.
Verification Center says no verification required while Testing, not production
approval. No audience publication, consent grants, server config or migrations.

Remaining production acceptance: implement/verify technical retention and scheduler
without deleting retained mirror IDs; finalize factual policy/public pages and
domain/brand/sensitive-scope verification; build/test exact server candidate, one-off
backup/rollback and target0014 migration/configuration; real-provider production
Sheets and Calendar lifecycle/recovery checks with synthetic data. Existing local
and dev-provider PASS cannot close these target-specific criteria. Import identity
scope is closed locally and published; full production integration remains open.

### Technical retention implementation23Nov
Owner explicitly requests cleanup, then policy/Google verification/server acceptance.
Base867981fa, canonical root/current branch; existing foreign WIP preserved. Gap is
code/operations evidence, not a rewrite of verified import/sync. Reuse connection,
import job locking, storage and Celery. Keep Calendar mirror/binding IDs and an
account identity digest; clear disconnected email/raw subject after30d. Preserve
transfer request-key tombstones against replay. No clients/appointments/Google-side
deletion, backup re-enablement or working migration. Add dry-run/bounded cleanup,
durable file retries and health evidence; scheduler disabled until reviewed activation.
Checks: age boundaries, dry-run, isolation, replay, shared-file/storage failure,
reconnect identity, pause/disconnect busy cleanup, PG import/sync races, migration
and affected Google/import suites. No new permission/notification/AI/BusinessEvent
policy; Google technical audit retention90d only. Public wording must match actual
deployment, not command existence. First operational apply requires reviewed dry-run.

Implementation iteration: focused10 then14 tests PASS. PostgreSQL16 tests PASS
(14 retention plus2 locking races), disposable DB removed by runner finally.
Completion118:116 PASS,1 SQLite concurrency skip,1 migration-fixture error
(historical accounts model omitted current auth_epoch). Fixed the fixture to create
user/business with current models before integration-only migration; focused rerun
16 PASS. Added10min cleanup headroom and age-boundary test. Final delta below
supersedes this intermediate result. Build/types/i18n8218 PASS;
isolated frontend output, existing chunk-size warning only. No CI.
UI uses existing StatusNotice/Modal and tokens, neutral RU/KK/EN copy, conditional
retention notices only when enabled; expired import hides unusable controls. Applied
Anti Slop during/copywriting and React Best Practices (hooks remain unconditional,
no new fetch/effect/dependency). Browser5 gone; inventory Chrome6 available but local
fixture attach twice reports debugger unattached. Requested extension recovery;
visual acceptance pending, not PASS. Owned Vite18743 remains running for that check.
Server read-only cloud-init metadata confirms availability_zone kz1-a and platform
ec2; cloud_name unknown. This verifies the reported zone, not every data processor.

Final retention delta23Nov: review found sanitized import summaries had no90d
deadline. Added bounded deletion after90d (imported_at, otherwise created_at),
preserving an expired request-key tombstone with SET_NULL job reference. No domain
record deletion. Added regression for this lifecycle and corrupt cross-tenant
transfer references. Snapshot selection now requires matching Business IDs.

Final verification: isolated_runtime with `.venv/Scripts/python.exe` ran Django
`check`, `makemigrations --check --dry-run`, and `test
apps.integrations.tests_google_retention apps.integrations.tests_google_retention_migration -v 1`:
18 PASS, exit0; output/google-retention-final-focused.log. The earlier migration
fixture error is resolved, not waived. Final PostgreSQL run
`.venv/Scripts/python.exe output/run_google_retention_postgres.py`:19 PASS, exit0,
including both locking races; output/google-retention-postgres.log. Runner's finally
dropped its uniquely generated test DB. Provider calls mocked, no working DB changed.
Earlier affected/dependent116 PASS remains evidence for unchanged provider/import
paths; the final focused run covers subsequent retention changes. Build/types/i18n
inputs unchanged since PASS. Working diff hygiene PASS; no CI requested/run.

Browser inventory still exposes Chrome6 and target fixture1634131116, but the
target attach remains unavailable. No screenshot/interaction acceptance claimed.
Pending owner recovery request covers opening the fixture and enabling extension
access; Platforma Digital profile is also needed for Google Console. No bypass via
native/CDP/another browser. Owned Vite18743 session43553 remains for resumption.

Canonical source only. Starting867981fa advanced externally to31530acd via
b4a911b2/31530acd medical/reception work; this task did not create those commits.
Retention files and exact Google hunks in STATUS/integrations/evidence remain
uncommitted, unstaged; foreign auth/medical/YCloud WIP preserved. Publication is
blocked by required visual acceptance, not missing owner permission. No retention
deployment or first apply. Desktop retention draft now describes local implementation
and explicitly leaves target activation/publication unfulfilled.

Next: restore target Chrome access, inspect expired-import and enabled disconnect
notices in RU/KK/EN/representative widths with screenshots/actions; finish scoped
publication, then update exact production candidate with retention. Policy factual
publication, Google branding/scope verification, target backup/migrations0014+0015,
configuration, reviewed dry-run/activation/monitoring and real-provider production
acceptance remain open. Do not mark production ready from these local checks.

### Retention UI acceptance —24Nov2026
Prior backend18/PG19/build PASS and blocked UI → owner restored Platforma Digital
Chrome7 → no product rewrite. Starting HEAD31530acd, same canonical root/branch,
foreign WIP preserved. Actual target fixture opened/read/screenshotted, so recovery
is verified beyond an empty/new tab. Existing Vite18743 serves canonical frontend.
Added synthetic `google-retention` fixture using real Cards/AuthProvider/Modal with
mocked adapters; no real grants/disconnects or remote writes. Existing import fixture
checks expired preview. Anti Slop during/copywriting requirements retained: accurate
retention copy, existing visual components, readable RU/KK/EN, keyboard/focus and
conditional promises; no design changes. Backend gates reused for unchanged inputs.

Visual PASS: expired source hides mapping/confirm and gives recovery instruction,
RU/KK desktop and RU/KK/EN390x844; disconnect dialogs both providers RU desktop,
KK/EN390x844, complete text/no horizontal overflow, clear actions; Escape closes and
returns focus; Tab reaches confirmation with visible focus; synthetic disconnect
changes each card to Connect. Empty Calendar name falls back to translated label.
Disabled retention hides30d promise in both dialogs. Existing loading seen; no
changed async/error path, prior provider recovery evidence retained. Screenshots
captured and visually inspected under output/google-retention-ui-20261124; viewport
reset. This is scoped UI evidence, not a new real-provider production PASS.
Build/types/i18n8254 PASS (foreign dictionary additions included),
output/google-retention-ui-final-build.log; existing chunk warning only.

Google Console read-only24Nov: correct Platforma Digital account/project selected;
verification center still says Testing, not production approval. Branding app name
PlatformaCRM/domain platformacrm.kz present; home/privacy/terms URLs empty. No Google
settings changed. Public policy and target acceptance still required before launch.

Publication24Nov: code e2c7f8f0ed3a15a0246f426ea02ba32ae6feeb5b normal-pushed
from codex/ui-testing-toolkit to origin/main; ls-remote matched. Static gate
`scripts/codex_verify.py --mode static --base-ref 31530acd52cea009f602847845d562c893c75d97`
PASS, output/google-retention-static.log. No CI (local-only). Exact29 task paths
and Google-only shared-doc hunks reviewed/staged; unrelated dirty work retained.
After final build the fixture additionally assigns its fail-closed Axios adapter
to apiClient (test-only hardening; no product build inputs changed).

Updated immutable candidate with exact e2c7f8f0 runtime patch applied to prior
a2f47ce3: new tree717a798022bd4938bf4cba71eca74f1b038f806a,44 paths over deployed
64d29158. Cached patch check PASS. Manifest/patch in output/google-production-20261123;
no source checkout/worktree created. Not full-gate tested or deployed. Owner asked
for one-off isolated immutable candidate-test directory exception to AGENTS.md,
because canonical checkout contains unrelated WIP; no dependent creation yet.

Server read-only24Nov reconfirmed same WorkingDirectory/services; DB/Redis localhost,
S3 endpoint storage.yandexcloud.kz/region kz1, SMTP smtp.resend.com; Google integration
settings still absent, retention disabled. No secrets emitted. Resend official
privacy/GDPR docs identify Plus Five Five, Inc. and US storage; add this factual
recipient before public policy. Sources https://resend.com/legal/privacy-policy and
https://resend.com/security/gdpr/. Updated existing production-facts-and-retention-proposal.md.
Owner decision pending: minimum Calendar IDs retained until Business account closure
or explicit deletion request with duplicate warning; no policy change assumed before
reply. These two pending decisions block dependent policy/candidate release work,
not completed scoped retention implementation/verification/publication.
