# GOOGLE-SHEETS-20261119

## Contract
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
- Browser: scripts/verify_google_sheets.py uses canonical source, isolated DB and dedicated ports53523/53522, synthetic Google adapter/Picker and test scanner; real API/import/export permissions and DB transitions. RU import preview/mapping/confirm imported1 client; export3 clients and refresh retained one destination. EN390x844 import dialog inspected. KK metadata-error400 -> Retry -> selector PASS; cancel selection leaves card unchanged; disconnect -> disconnected + Connect button focus PASS; cancelled OAuth -> localized message and return link PASS. Loading state observed. No-data: disconnected card; empty-grid input rejected in backend. No live Google access/Picker SDK proof.
- Focus defect found and fixed: Overlay uses data-focus-return-id. Escape returns focus to Import. Sheet select accessible label added. Retry now retries failed choose/connect instead of only refetching status. Browser confirmed retry and focus after fix.
- Screenshots saved and visually inspected: output/google-sheets-browser/connected-ru.jpg, import-preview-ru.jpg, import-mobile-en.jpg, import-kk-recovery.jpg, oauth-cancelled-kk.jpg; Google Cloud key restriction screenshot output/google-picker-restricted.jpg. Geometry, wrapping, labels, keyboard close/focus and translated copy inspected. No adjacent UI redesign. Picker's actual Google iframe remains live acceptance.
- Diff hygiene PASS. Task-owned files reviewed including new files; .env ignored. README setup and integration contract updated; registry links this evidence. No separate Google roadmap/passport was changed: this authorized implementation slice is recorded in the current integration contract, with Calendar still open.

## Remaining acceptance and publication
Code: implementation and scoped local verification complete. Environment/evidence: working DB migration0013 and real OAuth grant/Picker/import/export need explicit selected-environment approval and user grant. Working DB unchanged; no deployment. Calendar synchronization is later scope, not claimed complete. Production OAuth verification and production origins/secrets are not configured.
Starting HEAD d8ec748aa46782051198b13c8a547d2f49d13850 advanced by unrelated YCloud commit9c86bc769d11fb563e9cc32f43d9e933e7f96fec, already on origin/main. This task did not create that commit. Initial foreign invitation/WhatsApp WIP below is preserved. No foreign work is staged. Publication pending; origin/main equals the current HEAD before this task commit. CI workflow is checks/tests/build only; no push-triggered deployment found in the applicable workflow.
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
