DENTAL-MCS ACTIVE K08. Assistant invite/accept/current draft/menu/notification/revoke flow locally accepted and published aad03096; remote SHA verified. Backend isolation/lifecycle/PG/check/drift, desktop/mobile recovery/keyboard/focus, doctor regression and build/types/i18n passed. Next DOCX visual QA; DOCX policy and L05/L06 remain open. No CI/working migrations/deployment;0041/0042 isolated only. Checkpoint: docs/testing/task-state/DENTAL-MCS-20261122.md.

QA-016-20261121 LOCAL VERIFIED: automatic tasks searchable by displayed RU/KK/EN title; editor preserves original copy on unrelated edits. 66 backend, 9 node, 6 desktop/mobile browser scenarios, build/types/i18n/check/drift PASS; Code 8a240ad3 pushed to main; CI44937543011 queued (not PASS). Working DB untouched. [Evidence](docs/testing/evidence/qa-016-task-search-20261121.md).

QA-006-20261121 LOCAL VERIFIED: client custom-field filtering restored under QA specification; 28 backend, 15 node and 8 browser scenarios (RU/KK/EN desktop/mobile plus API-error recovery) PASS; build/types/i18n/check/drift PASS. Code c9570fa5 pushed to main; CI44934913440 in_progress (conclusion=None); working DB untouched. [Evidence](docs/testing/evidence/qa-006-client-filters-20261121.md).

QA-017-20261121 LOCAL VERIFIED: multilingual custom-field keys fixed; 31 backend and 6 RU/KK/EN desktop/mobile browser tests PASS, types/i18n/build/check/drift PASS. Code e7c6ee26 pushed to main; No CI run listed yet for this SHA; working DB untouched. [Evidence](docs/testing/evidence/qa-017-custom-field-keys-20261121.md).

QA-013/004-20261121 LOCAL VERIFIED: room/equipment links use reserved-resource Records filter; advanced reset preserves period; summary counts unique visits. Backend 62 + enhanced OWN/branch check, URL tests 9, browser 6 RU/KK/EN desktop/mobile + empty recovery 1, builds/types/i18n/check/drift PASS. Code 0029b2c5 pushed to main; CI44931895566 in progress. No working DB/deployment; 24 other report IDs remain open. [Evidence](docs/testing/evidence/qa-013-resource-filter-20261121.md).

QA-CRITICAL-20261121 LOCAL VERIFIED: QA-023 task history restored under task VIEW; QA-024 branch grant UI follows server capabilities. Final focused 19, affected 174 and branch-dependent 42 PASS (overlap); 4 history, 6 grant UI and session controls PASS; isolated builds/check/drift PASS. Code 9d7d038c pushed to main; CI44928103156 in progress. No working DB/live server/deployment. QA-025/026/027 retain original-environment gaps; 26 report IDs remain open. [Evidence](docs/testing/evidence/qa-critical-access-20261121.md).

QA-021-20261121 LOCAL VERIFIED: stale client writes rejected atomically; draft retained with explicit latest-value review/retry. Backend clients 92, final focused 35 and tenant 11 PASS (overlapping suites); 6 RU/KK/EN desktop/mobile browser scenarios, types/i18n and isolated app/widget builds PASS. Working DB and shared servers untouched; deployment not performed. Code dad129e6 pushed to main; CI44924980685 success. Remaining QA IDs are tracked in QA-CRITICAL-20261121. [Evidence](docs/testing/evidence/qa-021-client-concurrency-20261121.md).

AUTH-ENTRY-FEEDBACK-20261121: implemented and deployed in20261121-auth-entry-feedback. Precise password feedback, dirty-form reload warning, login background and no access-list on public invitation. Candidate/live20 browser cases PASS each; build/types/i18n/bundle PASS. No accounts created. Evidence: docs/testing/task-state/PRIMARY-SESSION.md. Corrected code commit e1886fea normal-pushed to main, remote SHA verified; foreign work retained. CI44921188977 in progress.

CRM-D04-MAP-20261121:22.11 завершён docs-only анализ24 apps/UI/связей на4a3214a6 + WIP. Планы посещений, плановые деньги, UI/voice и dental-presets отнесены к стоматологическому модулю; Client/Appointment/Payment и AI runtime остаются общими. [Карта](docs/testing/evidence/crm-core-dentistry-map-20261122.md). Код/БД не менялись; следующий шаг — отдельно порученная реализация по существующему плану.

GOOGLE-ENTRY-LAYOUT21Nov: ordinary Google button without name/email/photo deployed in20261121-google-static; shared medium size supersedes large. Fixed44px slot and readiness/late expansion fixes retained. Build/types/bundle,24 mocked cases and real candidate/live desktop/mobile first-load/reload PASS; displacement0px. Signed-in Chrome profile confirms no personalization. No accounts created. Evidence: docs/testing/task-state/PRIMARY-SESSION.md.

MFA server deployment21Nov: verified mfa.py from b755c9e1 deployed, four CRM services active, health/ready/signup200, no migrations. Read-only policy/signup-branch checks PASS with mocked persistence/session, no real registration; DB remains0 accounts/0 businesses. Google readiness rollout is recorded separately above. Evidence: docs/testing/task-state/PRIMARY-SESSION.md.

TEST-ACCOUNT-PURGE-20261121: active local/server CRM DBs cleared, users/businesses0 in both; local22/17 and server37/19 removed with related records. Verified backups retained, reference tables/schema/sequences preserved, health/ready200; PlatformaMarket untouched. Evidence: docs/testing/task-state/PRIMARY-SESSION.md.

MFA-OPTIONAL-20261121: voluntary business-user MFA implemented and locally verified; signup/invites enter CRM, confirmed factors enforced. Backend 133 PASS/8 PostgreSQL skips, browser 3 PASS, build/check/drift PASS; local DB has no pending migrations. Server MFA module deployed21Nov; read-only target checks PASS, no accounts created. Evidence: docs/testing/task-state/PRIMARY-SESSION.md.

AUTH-HALVES-20261119: /login, /signup, /mfa centered in equal desktop halves;
mobile layout retained. Browser geometry/screenshots, navigation/validation/focus,
RU/KK/EN sampled; build/types/i18n/bundle PASS. Follow-up: login/signup decorative
top stripe removed, including MFA; expired MFA return centered with 24/32px spacing.
Desktop/mobile screenshots and fresh build PASS. Compact signup implemented:
five44px fields, unified background, internal card scrolling; phone/niche in settings.
RU/KK/EN browser checks PASS; test account/business cleaned with owner approval.
Email placeholder updated; approved name/email pair and submit consent notice implemented.
Backend consent/system/drift, build/types/bundle and focused browser PASS.
RU/KK/EN retry/link/retained input and desktop/mobile screenshots verified.
Signup follow-up1541933a pushed to main; CI44535029646 in_progress at observation.
Foreign WIP preserved. No deployment.
Auth button follow-up: shared280px centered desktop / full-width mobile rule;
login/signup/forgot/reset screenshots, RU/KK/EN, focus and build/types/bundle PASS.
Evidence: [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md#auth-halves-20261119).

AUTH-FORMS-AUDIT-20261119: lost-access public link/contact removed; password eyes
added across account/auth fields without hover, keyboard focus retained. Forgot
and reset backgrounds match login; localized acknowledgement and actionable reset
errors. Backend13, frontend26, fresh mobile12 and affected desktop8 PASS;
build/types/i18n PASS. Prior desktop API outcomes unchanged, initial shared-runtime
mobile429 failures resolved by separate isolated backend, throttle unchanged.
RU/KK/EN desktop/mobile screenshots inspected. Source-only; new deployment not
authorized. Checkpoint: docs/testing/task-state/PRIMARY-SESSION.md#auth-forms-audit-20261119.

PILOT-RELEASE-20261119: owner authorized coordinated readiness; startup channel
WhatsApp only, real names/assignments not a preparation blocker. YCloud source CI
44392825855 and main b9415d71 CI44404635483 backend/frontend success confirmed.
Tech Partner approval not observed in authenticated console; no number activation.
Initial server58a6427e+17 invite/access overlays retained for recovery;
the combined52-file candidate incorporates those fixes.
Combined candidate3e605431 published; CI44494144956 backend/frontend success.
Same-origin app/widget review artifact and static smoke PASS. Owner authorized
safe deployment, five migrations, beat and access checks19Nov. Exact3e605431 is
deployed; CRM reopened15:18:32 UTC+5 after verified fresh restore, migrations and
production JWT/tenant/role/revoked smoke. Source/frontend hashes match; original
business data preserved. Singleton beat runs only disabled-provider YCloud polls;
AI/Scribe/YCloud off, dormant notification/AI backlog remains excluded.
Live owner browser reached authenticator MFA; user completion pending.
Client number activation remains excluded.
Full gate PASS:3689 backend/98skips,build/types/i18n/bundle,2mobile smoke,audits0;
frozen app inputs unchanged; inert test-runner override removed with equivalent-env proof.
WSL restore/PITR/files/5migrations/data-preservation PASS; old-code INSERT23502
reproduced, pre-migration schema restore fixes tested inserts. Full businessRPO/RTO
and post-write reconciliation not certified. WhatsApp cross-flow twoBusiness PASS;
consumers6/6 and money2/2 browser PASS, inspected24+8screenshots, no source drift.
Fresh invite122 backend/14browser PASS and live owner form desktop/mobile/actions
verified; employee live auth still open. Inbox60 focused and3 PG batching races
PASS (23 distinct in PG run),isolated real Celery restart PASS; AC10 export fixed/
scoped verified. Voice local240PASS/4skips,4browser; final D01/D02 text2/2 PASS,
17scored turns/$0.00847635/STT0; audio/fullD01 open. Server deployed; owner UI pending.
Owner approved Direct Meta callback inclusion in combined pilot commit; unrelated
Google-live/older Meta App Review evidence WIP remains excluded.
Checkpoint: docs/testing/task-state/PRIMARY-SESSION.md#pilot-release-20261119--coordination-and-candidate-preparation.

INVITATIONS-FLOW-20261119: wide no-blur modal, readable grants, inline password/MFA
and direct CRM entry implemented and exact13-file patch deployed. Focused18 and
104 dependent backend PASS; all14 scoped browser scenarios have current PASS;
server build/types/i18n/readiness PASS. Live Chrome confirmed member removal and
modal opening; owner form desktop/mobile/actions verified after Chrome recovery;
employee live acceptance/MFA/revoked browser checks remain open.
Disabled membership29 removed from Business18; server account retained, local
account absent. No new invites sent. Own commit/push pending coordinated publication.
Evidence: docs/testing/evidence/invitations-24h-20261112.md.

## GOOGLE-SHEETS-20261119 — local verification / live acceptance pending

23Nov owner expanded scope to production-ready Sheets + Calendar. Calendar local
implementation: CRM-owned copies, external busy blocks, pause/retry and private
minimal event content. Backend201/PG4 PASS, build PASS; scoped RU/EN/KK browser
checks PASS. Live Sheets OAuth/Picker/export/refresh/import PASS; Calendar grant, first
copy/reschedule/cancel/repair and external-busy block-release PASS. Final error-state
screenshot and Retry recovery PASS after extension update; GET410 regression37 PASS. Public launch blocked on
approved home/privacy pages and production Google configuration/verification.
Code fe23674e normal-pushed to main; remote SHA and committed static PASS. Local-only
acceptance; no CI/deployment/working migration. Active checkpoint:
docs/testing/evidence/google-sheets-20261119.md#production-continuation--23nov2026.

OAuth + Sheets import/export implemented; Cloud test project, OAuth client and restricted Picker key configured. Backend72 PASS, final build PASS, RU/KK/EN desktop/mobile synthetic flows verified; PostgreSQL3 race tests PASS; published918096ce to origin/main (remote SHA verified); CI44397837621 running, not PASS. Local PostgreSQL platformacrm: approved migrations0012/0013 applied, Django check and Google tables verified. Live Google grant/transfer and Calendar sync not claimed. Evidence: docs/testing/evidence/google-sheets-20261119.md.

INVITATIONS-ACCESS-UX-20261118: terminal invite errors/expiry hidden; access toggle at top.
Revoked employee gets explicit auth-me state and separate empty screen; RU/KK/EN.
14 focused + 90 dependent backend PASS; build PASS; browser 4+2 PASS.
Exact 9-file patch deployed, live owner UI/readiness and read-only employee state PASS.
Live revoked-employee browser check awaits owner login. No mail/membership mutations.
Evidence: docs/testing/evidence/invitations-24h-20261112.md.

## SETTINGS-CLARITY-20261118 — локально проверено

Упрощены навигация, выбор часового пояса и времени сообщений; единое сохранение сценария и защита черновиков. Серверные фильтры/страницы истории безопасности; локальные голосовые настройки обозначены явно. PASS: 14 backend tests, check/schema, build/types/i18n/bundle, 12 выбранных desktop/mobile сценариев (с исправленными тестовыми данными), осмотр RU/KK/EN. Django8000 перезапущен по просьбе владельца, Chrome открыт на /app/settings. Код 986c3138 отправлен в origin/main, SHA подтверждён; CI44368616294 выполняется (не PASS). Граница и логи: [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md#settings-clarity-20261118).

INVITATIONS-SMTP-20261118: restored Resend SMTP + HTTPS FRONTEND_URL on live stand.
New invitations 3 Manager / 4 Operator: SMTP accepted and Resend Delivered confirmed.
Owner-approved old test emails 630/632/635 cancelled with audit; active queue 0.
SMTP TLS/auth, Django check/readiness, services and read-only DB checks PASS.
Inbox/Spam and employee acceptance not verified; existing-business send scope complete.
Evidence: docs/testing/evidence/invitations-24h-20261112.md.

INVITATIONS-LIVE-20261118: owner selected existing business; no new signup.
Two explicit recipient/role-approved invitations created: Manager and Operator.
Both email attempts FAIL, persisted after reload; only owner remains a member.
No resend/revoke/accept/config/deploy. SSH timeout prevents root-cause proof.
Evidence: docs/testing/evidence/invitations-24h-20261112.md#рабочий-прогон--18112026.

GLOBAL-SEARCH-20261118: селектор страницы/CRM удалён; поиск всегда общий, URL-фильтры страниц независимы.
Локально: 40 backend + 15 Node PASS, 32 browser assertions (30 проверок поведения/адаптива
и 2 воспроизведённых ограничения), build/types/i18n/bundle PASS. Аудит выявил неполноту
задач/диалогов, несовпадение полей диалогов и неполные error states; это не полная готовность поиска.
Evidence: docs/testing/evidence/global-search-20261118.md. c5fec11e normal-push origin/main подтверждён; CI464 in_progress, не green.

VOICE-SCRIBE-V3-20261117: broad synthetic benchmark18Nov complete; customer activation off.
64 utterances/298 conditions;295 HTTP200,2 provider429,1 local silence rejection.
Paired KK WER1.36% explicit KK/RU vs6.53% auto; mixed names/phone/negation failures remain.
Account usage delta833 within new2000 cap; exact attribution caveat in evidence.
Approved fixes implemented: KK fallback/phone guards, reviewed scheduling changes,
locale language defaults and authorized opt-in card-name hints. Isolated backend,
10 browser scenarios and build/types PASS. Follow-up short booking/visit-plan
corrections retain other fields and require new review; one-field clarification.
194 backend tests (190PASS/4SQLite skips), check/drift and new browser flow PASS.
Live human KK/planner acceptance remains open.
24-dialogue corpus prepared; approved4-dialogue live pilot attempted12 text/voice combinations,0 fully correct.
OpenRouter actual$0.00733485; STT9success/1timeout, creditreserve92/200 (exactbilling unavailable).
Follow-up: main-route negation guard, scheduling schema and unchanged-correction clarification verified locally.
Final235 tests:231PASS/4SQLite skips; system/drift,2 browser flows and build/types/bundle PASS.
Initial name preservation and live/human KK acceptance remain open; no further paid calls or activation.
Evidence: docs/testing/evidence/voice-scribe-v3-20261117.md.
Checkpoint: output/voice-scribe-v3-20261117/CHECKPOINT.md.

META-COEXISTENCE-20261117: local Business App onboarding/history preparation implemented.
18Nov evening: official Meta error reference maps3441107 to Advanced Access via
App Review for the two WhatsApp permissions. Diagnostic message sent to Meta's
business assistant; human handoff failed, no support case ID. Technical-report Next
disabled for both relevant categories. Review remains incomplete/unsubmitted;
video upload still fails after owner enabled extension file access. Processor countries
and contracting entities unconfirmed; owner has no DPA/country list available.
18Nov CI repair: speech cache interference reproduced; fixture-only cleanup plus
rate-limit control verified (28 affected tests, candidate without foreign WIP also28).
System/drift/static PASS; no production throttle change.
Owner-approved maintained picomatch patch prepared: bounded malicious-pattern
tests, consumer/source integrity, clean install, app/widget/Storybook builds and
npm audit PASS locally. Candidate58a6427e CI44291366686 backend/frontend/audits PASS;
full isolated release gate44291424890 PASS (3515 tests/82 skips,2 mobile smoke).
Package58a6427e prepared; owner approved the entire candidate including added UI scope.
SSH restored after approved /32
UFW rule and one VM restart; temporary bootcmd removed. Existing CRM active.
58a6427e deployed18Nov; integrations0012 applied, service/readiness/protection checks PASS.
Existing connections preserved. No new-number import yet; browser login pending.
Owner approved entire ebfeea67 release after green checks; published to main.
Prior CI44139255024 failed speech tests and npm audit; new CI verifies the repair.
Server runs58a6427e; no live import or final submission.
Signed expected number, no phone re-registration, durable authenticated import,
no historical AI/send/window effects; app replies hand off to staff. Migration0012.
130 PostgreSQL affected checks,17 final focused checks and23 browser cases/build PASS.
Three Coexistence subscriptions enabled v27.0 with owner approval. Live OAuth
launch validated v4/coexOn; Meta rejects Business App number with3441107 (partner
app not set up). App Review still Not submitted,2WhatsApp permissions; Tech Provider1/2.
Live Meta/number acceptance, history import and review videos
remain open. Phone-only identities and metadata-only attachments are current limits.
Evidence: PRIMARY-SESSION META-COEXISTENCE-20261117; output/meta-review-20261117.

NOTIFICATIONS-REDESIGN-20261114: approved compact bell and notification center implemented.
15.11 modal correction complete: no-blur dialog on all widths, source/metadata and
personal receipt actions retained; visible filter labels removed, accessible names kept.
13browser PASS +4final localized/320/200% reruns; build/types/i18n/bundle/axe PASS.
15.11 follow-up complete: period beside sort; read-all result line removed. Bell now
prioritizes personal unread rows before server pagination. Fresh74 backend/system/drift,
13browser cases +8affected post-wrap rerun, build/types/i18n/bundle PASS.
RU/KK/EN320–1440 screenshots inspected; realHTTP receipt/permission/retry checks PASS.
Personal filters, responsive details, read/unread/read-all and acknowledgement retained.
Backend 73 distinct scenarios, system/drift, build/types/i18n/bundle and browser 10/10 PASS.
RU/KK/EN screenshots inspected; 320px/200% text footer overlap corrected and rechecked.
No scoped code/local-evidence remainder. Publication/CI receipt and exact limits:
output/notifications-redesign-20261114/CHECKPOINT.md.

MFA-INBOX-20261114: six-cell MFA and automatic entry implemented and locally verified.
Return link centered with16px gap on desktop/mobile; recovery and profile retry retained.
Unlinked Inbox actions create/link client and create task use real existing server writes.
75distinct backend/11browser/15Node cases verified across retained runs; build/types/i18n/bundle PASS.
RU/KK/EN320–1440, keyboard, form200% and affected axe checks PASS; screenshots inspected.
No scoped code/local-evidence remainder; no backend policy/schema/workingDB/provider/deploy changes.
Publication/CI receipt: output/mfa-inbox-20261114/CHECKPOINT.md.
Evidence: docs/testing/task-state/PRIMARY-SESSION.md#mfa-inbox-20261114.

CHANNELS-FIXES-20261114: search/key autofill and channel setup UI implemented locally;
unified statuses, website copy/toggle and Telegram replacement. Owner correction:
WhatsApp now shows one Connect button, no provider choice/names or manual keys.
Fresh browser10/10 + signup5/5, build/types/i18n PASS; RU/KK/EN screenshots inspected.
No login needed for removed key field. Former signup dependency blocker resolved
by release04949366/4cc19068: published to main, CI success, deployed17Nov.
This reuses release evidence, not a new live channel-delivery test. Evidence:
docs/testing/task-state/PRIMARY-SESSION.md#channels-fixes-20261114.

AI-AGENTS-REDESIGN-20261113: approved editor redesign implemented; scoped local acceptance PASS.
19.11 authorized phase: preview explanations + opt-in inbound grouping, accepted design preserved.
Local scope PASS: final47 + dependent97 + unchanged56 =200 distinct backend scenarios;
browser8+4 PASS, strengthened mobile3 PASS, build/types/i18n/bundle/system/drift PASS.
Code85d086e6 published/read back on origin/main; CI44404460792 in_progress at inspection.
Migration0015 isolated only; target migration/beat-worker rollout not performed.
Evidence: docs/testing/evidence/ai-agents-redesign-20261113.md (Preview explanations and inbound batching).
17.11 create modal: CRM selection retained but disabled, localized development banner;
Create centered beneath cards. Local build/types/i18n/bundle and8distinct browser
cases PASS across final reruns;320/1440, RU/KK/EN, text200 screenshots inspected.
Existing CRM and customer creation preserved; no API/deployment change.
Evidence: docs/testing/evidence/ai-agents-redesign-20261113.md (Create modal availability).
Knowledge follow-up reconciled17Nov: truthful eligibility, guarded drafts, persistent
topic shortcuts and full shared-library reading shipped in04949366/4cc19068.
Eight final desktop/mobile knowledge cases PASS in release focus-results.json;
earlier failed harness runs retained. Channel/language dependencies integrated;
remote main and actual CI rechecked at4cc19068. Deployment receipt reused, no new
deployment or AI activation. Language live evidence exposed a stale-model override;
minimal fix verified by11focused/145dependent tests plus system/drift PASS.
Own publication receipt in the existing checkpoint; fix not deployed or live-model
retested. Real customer delivery remains separate. Evidence: existing redesign evidence,
knowledge closeout.
Named picker/local sections, split configuration, overview/context test and full knowledge view.
Atomic save, independent knowledge/channels, draft/permission/runtime guards preserved.
UX14 and dependent10 browser cases PASS; localized/responsive/keyboard/recovery/axe and build/bundle PASS.
No scoped local remainder; no backend/workingDB/provider/deployment changes. Publication/CI receipt:
output/ai-agents-redesign-20261113/CHECKPOINT.md; docs/testing/evidence/ai-agents-redesign-20261113.md.
Owner follow-up: readiness and activation switch removed from inner header; content raised.
Header acceptance: build +7 browser regressions +21 localized viewport checks PASS.
Other listed UI corrections deferred to next scoped step; receipt in same checkpoint.
Next owner correction complete: inner messages button removed; Test chat overlays right
side below global header without reflow. Picker/editor stacking defect reproduced/fixed.
Scoped8PASS plus affected4PASS; browser26+interaction16+large-text6PASS; build/bundlePASS.
Screenshots RU/KK/EN320–1440 and200% inspected. Logs output/ai-agents-chat-panel-20261113.
Next correction complete: compact fields/selectors, named branch choice, no instruction
template/duplicate titles; minimal chat with3short suggestion rows and compact input.
19distinct scoped/dependent browser cases PASS; localized/200%/recovery/axe/build/bundle PASS.
No scoped local remainder. Final logs output/ai-agents-compact-20261113; same checkpoint
holds publication/CI. Backend/workingDB/provider/deployment unchanged.
Next owner correction complete: centered overview, three preparation cards without
counter, compact channel cards/logos, distinct status and selected-channel setup.
Conversation metrics preserved; 8 scoped/dependent browser cases PASS. RU/KK/EN,
200% text, permissions/recovery/keyboard/axe/build/bundle PASS; screenshots inspected.
No scoped local remainder. Logs output/ai-agents-overview-20261113; publication/CI
in the same checkpoint. Backend/workingDB/provider/deployment unchanged.
Owner refinement14.11 complete: explicit completed/required preparation states,
requested launch-preparation intro, centered metrics, full-size shared provider logos.
4 affected regressions +64 visual/state +31 consumer/recovery checks PASS; build,
bundle, RU/KK/EN/mobile/200%/axe PASS, screenshots inspected. No scoped local remainder.
Logs output/ai-agents-cta-20261114; publication/CI in the same checkpoint.
Instruction phase14.11: clear field purposes, Actions link and inline expansion.
10distinct scoped browser cases verified; RU/KK/EN320–1440/200% and recovery/view-only
checks PASS, screenshots inspected. No next audit phase/backend/workingDB scope.
Final build/publication/CI: same checkpoint; logs output/ai-agents-instructions-20261114.
Side hints14.11: guidance beside fields on wide forms, below on narrow screens;
examples separated, Actions guidance next to main instruction. Final10browser
regressions/build/types/i18n/bundle PASS; localized320–1440/200% images inspected.
No scoped local remainder. Receipt: same checkpoint; logs ai-agents-side-hints-20261114.
Owner correction14.11: expand button/state/keys removed; native resize and side hints
retained.10UI regressions +build/types/i18n/bundle PASS; desktop/mobile inspected.
14server tests PASS confirm saved instruction reaches provider input (mocked model,
local dirty server snapshot, not deployed/live-model compliance). Receipt: checkpoint.
Actions audit14.11 complete, no product edits:116isolated server tests PASS,
including10audit reproductions; desktop Actions inspected, draft cancelled.
A-A01 P1: model reason can impersonate fallback and bypass required handoff when
fallback review is off. A-A02–07: live legacy Lead/Deal, misleading threshold/
policy copy, hidden channel overrides, unclear off-topic counts and redundant control.
Findings remain open; audit PASS is not product acceptance. Full map/explanations:
docs/testing/evidence/ai-agents-redesign-20261113.md#actions-audit--14112026.
No next implementation/live-provider/workingDB scope; publication in checkpoint.
Actions implementation14.11: A-A01–07 corrected in the approved local scope.
Trusted fallback marker; Client/Task/Appointment controls and separate consent;
explicit legacy adoption preserves history, new mode ignores channel overrides.
221server tests +20distinct scoped browser cases PASS; system/drift/build/types/
i18n/bundle PASS. RU/KK/EN390/1440,200%text, keyboard/axe inspected. No scoped code/
local-evidence remainder; no workingDB/liveprovider/deployment claim.
Publication/actualCI: output/ai-agents-actions-implementation-20261114/RESULT.json
and existing redesign checkpoint. Evidence: ai-agents-redesign-20261113.md#actions-implementation--14112026.


NOTIFICATIONS-SERVER-FIXES-20261113: all six server defects fixed and locally verified.
Personal access/internal history, atomic retry, stale delivery, failure alerts and monitor.
27 new regressions; affected212:205SQLitePASS + all7concurrencyPASS on disposablePG17.
System/drift PASS; no schema/UI/workingDB/live-send change; foreign WIP preserved.
CI stale SYSTEM delivery fixture corrected;55dependent tests/system/drift PASS.
No scoped code/local-evidence remainder. Follow-up publication/CI: checkpoint.
Evidence: docs/testing/task-state/PRIMARY-SESSION.md#notifications-server-fixes-20261113.

PAGE-LOADING-20261113: scoped implementation and local UI acceptance complete.
17.11 cold-entry correction: header/sidebar/mobile navigation remain usable while
one loader waits in page content; merchant/legacy/platform shells covered.
26distinct browser cases verified (24initialPASS +5focusedPASS including2recoveries),
17Node/build/types/i18n/bundle PASS; RU/KK/EN and320px/200% images inspected.
No scoped local remainder; publication/CI: output/loading-shell-20261117/CHECKPOINT.md.
One initial loader; visible queries only; local refresh preserves content/drafts.
Inbox list geometry, retry/403, hidden settings, cache, portal focus verified.
Loading23PASS; dependent19 scenarios verified across retained runs; Node/build/bundlePASS.
RU/KK/EN320–1536 and text200% inspected; no backend/workingDB/provider/deploy changes.
No scoped code/local-evidence remainder. Publication and actual CI: checkpoint.
Evidence: docs/testing/evidence/page-loading-20261113.md.
Checkpoint: output/page-loading-20261113/CHECKPOINT.md.

CRM-GLOBAL-REMAINING-20261112: T01–T07/O01–O03 resolved within scoped acceptance.
Provider/money fixtures, registries and SYSTEM reminder replay verified; prior T02/T03 already published.
Business-local activity time, task from/to history and truthful Inbox retry status fixed.
New requests route to Appointment; clarification/review/keyboard confirmation verified.
86domain/75routing/80task/3PG/9Node + realqueue/browser/build/system/drift PASS (overlapping sets).
Experimental speech excluded; foreign WIP preserved; no workingDB/env/real sends/deploy.
Full204matrix/load/fullS04/live acceptance remains open; publication/CI tracked in checkpoint.
Evidence: docs/testing/evidence/crm-global-remaining-20261112.md.
Checkpoint: output/crm-global-remaining-20261112/CHECKPOINT.md.

BACKEND-CI-FIXES-20261112: existing two test corrections verified for publication.
Voice client creation requires review/confirmation and replay creates exactly one client.
Branch migration checks0003 defaults then0006 explicit configuration, preserving history.
5focused+64dependent/system/drift PASS with committed dependencies, isolatedDB/no sends.
No product/schema/UI changes; all other local work preserved. Prior62commits published31fe3115.
Publication and exact remoteCI result: output/backend-ci-fixes-20261112/CHECKPOINT.md.
Evidence: docs/testing/evidence/crm-global-fixes-20261112.md#backend-ci-corrections--12112026.

CRM-GLOBAL-FIXES-20261112: all ten confirmed F01–F10 fixed and locally verified.
Archive/RO/search/conflicts/reschedule/widget/password/demo reset/system locales.
Backend focused/dependent, Node, browser RU/KK/EN, build/types/i18n/budget/system/drift PASS.
Held-response browser harness timeouts/429 retained; diagnostic recovery passed.
No full matrix/S04/live/deploy claim; seven other test failures and three observations remain.
Own runtimes stopped; workingDB/env/sends untouched. Own commit only; foreign outgoing blocks push/newCI.
Evidence: docs/testing/evidence/crm-global-fixes-20261112.md.
Checkpoint: output/crm-global-fixes-20261112/CHECKPOINT.md.

INVITATIONS-24H-20261112: /invite and email issue/resend locally verified.
24h bound token, own password/existing login, business selection, revoke/rotation.
84dependent/17PG/15redaction/browser/build/types/i18n/budget/system/drift PASS.
Historical Resend SMTP+Inbox06Nov confirmed; local console, current server SSH timeout.
No working migration/live invite/deploy. Evidence: docs/testing/evidence/invitations-24h-20261112.md.
Checkpoint: output/invitations-24h-20261112/CHECKPOINT.md.

CRM-GLOBAL-RUN-20261112: isolated functional/Computer audit report prepared; NOT full PASS.
SQLite3329:3249PASS/3FAIL/2ERROR/75SKIP; PG288:287PASS/1FAIL; all75SKIP coveredPG.
Node304PASS/2FAIL; build/types/i18n/budget/system/drift/dependency auditsPASS.
10confirmed findings;48browser/204case/100route coverage records retain unproven variants.
No product fixes/real sends/workingDB/env/deploy. Load limited by RAM; S04 incomplete.
Own runtimes stopped; temporary load folders retained after automatic cleanup rejection.
Own docs only;55foreign/mixed outgoing block push/newCI. Report:
docs/testing/evidence/crm-global-run-20261112.md.
Checkpoint: output/crm-global-run-20261112/CHECKPOINT.md.

TEST-SESSION-ISOLATION-20261112: reproduced and fixed cross-port test-cookie collision.
Per-disposableDB refresh/CSRF/session names; ordinary defaults/lifetimes unchanged.
RealHTTP before401/after3coexisting sessionsPASS;84backend/system/drift/runtime/NodePASS.
25distinct browser scenariosPASS across batches; stale-test/429/startup failures retained.
Own runtimes stopped; workingDB/browser/env untouched. Own local commit only;
54foreign/mixed outgoing block own-only push/newCI. Evidence:
docs/testing/evidence/test-session-isolation-20261112.md.
Checkpoint: output/test-session-isolation-20261112/CHECKPOINT.md.

MANAGEMENT-BOOKING-20261112: manual/AI booking integration locally verified.
Management terms, staff eligibility, rooms, schedules/absence, transfer/rollback PASS.
Fixed text-AI specialist references exposing physical/retired/archived resources.
64focused/dependent tests +realAPI browser create/transfer/AIapproval PASS; system/driftPASS.
Mock planner only; no live-model certification, workingDB/schema/env/deploy changes.
Own local commit;Foreign outgoing block own-only push/newCI. Evidence:
docs/testing/evidence/management-implementation-20261111.md#management-booking-integration--12112026.
Checkpoint: output/management-booking-20261112/CHECKPOINT.md.

VOICE-ERRORS-20261112: localized speech errors and safe diagnostics locally verified.
No paid calls; mocked API/provider,17browser RU/KK/EN, backend/system/drift and frontendPASS.
Explicit retry/countdown/text recovery; bounded metadata only, no audio/text/secrets.
Own runtimes stopped; workingDB/env/default unchanged. Prior accuracy/live timeout open.
Own-only publication blocked by foreign outgoing; no newCI/deploy.
Evidence: docs/testing/evidence/voice-errors-20261112.md.
Checkpoint: output/voice-errors-20261112/CHECKPOINT.md.

AI-WORK-CRM-COMPLEX-FIXES-20261112: C1–C3 fixed and verified on isolated realAI data.
Independent action values, scoped archive reads, named/localized Appointment review.
Router accepts both permitted samples; unknown IDs/ambiguity remain guarded.
API17initial15PASS2FAIL; targeted recovery/final PASS, failures retained; browser11PASS/1harnessFAIL.
90realcalls,SQL2clients12tasks2appointments; no extra writes/leaks. Newrequest→Appointment preserved.
Backend focused/dependent, system/drift, frontend build/types/i18n/budget/formatter checks recorded.
Own runtimes stopped; workingDB/env untouched. Own commit only; foreign outgoing blocks push/newCI.
Evidence: docs/testing/evidence/ai-work-crm-complex-fixes-20261112.md.

MANAGEMENT-BROWSER-REVIEW-20261112: all five pages checked through real browser/API.
Fixed Select-only draft guard, schedule-to-absence link and direct-form save/reopen.
Existing7browserPASS; targeted regression,20viewports/four320forms/branch+searchPASS.
RU/KK/EN, keyboard, relations/schedule/recovery/manager; build-types-i18n-bundlePASS.
Isolated synthetic DB only; no backend/schema/workingDB/provider/deploy changes.
Own local commit only; foreign outgoing range blocks push/newCI. Evidence:
docs/testing/evidence/management-implementation-20261111.md#browser-review--12112026.
Checkpoint: output/playwright/management-review-20261112/CHECKPOINT.md.

AI-WORK-CRM-COMPLEX-20261112: complex live CRM verification complete; open C1–C3.
Two independent creates duplicate first values; archive read invents access denial;
Appointment review shows raw IDs/untranslated branch. API/browser findings retained.
Dependent chains/corrections/partial recovery/archive restore/rights/replay verified.
79real calls; SQL2clients8tasks2appointments only; no leaks/unexpected writes found.
Prior report reviewed: new requests→Appointment; exact equipment reproducer1PASS now.
Own runtimes stopped/disposableDBremoved; workingDB/env/productcode/deploy untouched.
Own docs commit;46foreign outgoing block push/newCI. Evidence:
docs/testing/evidence/ai-work-crm-complex-20261112.md.

MANAGEMENT-IMPLEMENTATION-20261111: five approved pages implemented with real APIs.
Explicit service/staff/branch links, room pools, effective schedules and safe lifecycle.
7browser scenarios RU/KK/EN320–1440; API31+18/AI40/PG14/node14/build-types-i18n-bundlePASS.
Owner-approved localPG5 migrations applied; backup restore154tables/10212rowsPASS.
15automatic branches converted; protecteddata/6API/5Chrome pagesPASS.
No scoped remainder; owncommit only,45foreign outgoing block push/newCI; no deploy/provider.
Evidence: docs/testing/evidence/management-implementation-20261111.md.
Checkpoint: output/management-implementation-20261111/CHECKPOINT.md.

ANALYTICS-DETAIL-COMPARE-20261111: metric drilldown and previous-period comparison verified locally.
KPI/status/source/service/team lists match period/archive/scope; financial Decimal delta guarded.
145dependentPASS/2PGskips +11focusedPASS; system/drift,3logic/types/i18n/build/budgetPASS.
Playwright real isolatedAPI: current/prior/zero/paging/roles/503retry/403/RU-KK-EN320–1440PASS.
No new KPI/schema/workingDB/env/provider/deploy; own runtimes stopped. No scoped code/evidence remainder.
44foreign outgoing block own-only push/newCI. Evidence:
docs/testing/evidence/analytics-detail-compare-20261111.md.

AI-REQUEST-APPOINTMENTS-20261111: new applications route to appointments, not Lead.
Owner correction of priorW3; server guard and pending clarification, historical IDs preserved.
Focused5PASS; dependent63PASS/1equipmentERROR; system/driftPASS. Same equipmentERROR in baseline.
RealAI API8PASS+1proposal-boundaryFAIL; overlap confirmation safely fails without writes.
Playwright clarification/proposal/keyboard confirmation1440/390PASS;23real calls.
SQL only5newappointments; prior5entitytable rows unchanged. WorkingDB/env untouched.
Own runtimes stopped/disposableDBabsent. Local uncommitted; no stage/push/newCI/deploy.
Evidence: docs/testing/evidence/ai-request-appointments-20261111.md.

ANALYTICS-FIXES-20261111: nine audited /analytics defects fixed and locally verified.
API validation/period, team scope, exact Inbox link, cached recovery, locales and responsive/a11y.
Focused16 and dependent131PASS/2PGskips; system/drift, build/types/i18n/bundle PASS.
Playwright real isolatedAPI:503/recovery/403/CSV/calendar/roles/RU-KK-EN320–1440 PASS.
Existing design/rights preserved; no new KPI/schema/workingDB/env/provider/deploy.
No scoped code/local-evidence remainder;42foreign outgoing block own-only push/newCI.
Evidence: docs/testing/evidence/analytics-fixes-20261111.md.

AI-WORK-CRM-FIXES-20261111: W1–W4 implemented; isolated API/Chrome verification recorded.
Target identity/explicit selection, task transitions, Lead and localized access denial.
API22+7PASS;10browser scenarios incl recovery; title3API+browserPASS; backend scoped PASS.
Final shared-checkout compatibility 75PASS; system/driftPASS; earlier foreign SyntaxError retained.
No workingDB/env/deploy; own runtimes stopped. Own local commit;43foreign outgoing block push/newCI.
Evidence: docs/testing/evidence/ai-work-crm-fixes-20261111.md.

BUSINESS-CLEAR-20261111: /app/business content removed at owner request.
Empty workspace in existing shell; no company redirect/form/section tabs.
Direct subsection routes and data preserved; unfinished parity edits withdrawn.
13navigation/types/appbuild/budgetPASS; Chrome1440/390 blank main confirmed.
Own runtime stopped; no workingDB/env/provider/deploy. Own commit only;
40foreign outgoing block push/newCI. Evidence:
docs/testing/evidence/business-workspace-20261111.md#clear-business-entry-20261111.

AI-WORK-CRM-LIVE-20261111: verification completed with open W1–W4; no product fixes.
Real AI/API/Chrome: create/update, confirmation, rights and sequential replay tested.
Wrong/ambiguous target, completion routing, Lead interpretation and denied-action UX fail.
22initial API17PASS/5FAIL (incl harness403/dependent skip); extension7PASS;65real calls.
Protected records unchanged; no unauthorized writes/duplicates observed. Own runtimes stopped.
WorkingDB/env/deploy untouched. FullD01/PGconcurrency/production not certified.
Own docs commit only;40foreign outgoing block push/newCI. Evidence:
docs/testing/evidence/ai-work-crm-live-20261111.md.

VOICE-ACCURACY-20261111:12Nov targeted timeout investigation blocked by audio balance.
Only2failed scenarios repeated; both nowHTTP402,minimumaudio balance0.50USD.
Original60s wait likely; historical precise provider/network cause unproven without trace/ID.
No passed checks rerun; no product/env/workingDB changes; own runtimes stopped/no writes.
No owncommit/push/CI. Restore sufficient balance then repeat only these2cases.
Evidence: docs/testing/evidence/voice-accuracy-20261111.md.
Checkpoint: output/voice-accuracy-20261111/CHECKPOINT.md.

AI-ANALYTICS-COMPLEX-FIXES-20261111: A1–A4 fixed and locally reverified.
Dates/selected period, own/team status groups, compatible routing and denied-source response.
34API/8Playwright/2directhistory/replay PASS with real AI; final41calls,0toolcalls.
39synthetic tasks preserved; no hidden/foreign leaks found; backend scoped checksPASS.
Prior citation/fixture/cleanup failures retained; final runtimes stopped, disposableDBs removed.
WorkingDB/env/deploy untouched. No scoped code/evidence remainder; fullD01/production open.
Own local commit;39foreign outgoing block own-only push/newCI. Evidence:
docs/testing/evidence/ai-analytics-complex-fixes-20261111.md.

BUSINESS-BROWSER-REVIEW-20261111: six pages reviewed;7UI/data-context findings fixed.
Branch service terms, archive context, staff actions, mobile forms/search/nav/schedule.
Chrome owner+manager; real isolated CRUD/lifecycle/drafts/recovery, RU/KK/EN320–1440.
Logic6/i18n/types/app-widget/build-budgetPASS; stale-output bundleFAIL retained.
No backend/workingDB/env/provider/deploy changes. Own runtime stopped; foreignWIP kept.
Own local commit only; foreign outgoing range blocks push/newCI. Evidence:
docs/testing/evidence/business-workspace-20261111.md#browser-review-20261111.
Details: output/business-browser-review-20261111/REPORT.md.

VOICE-KAZAKH-20261111: approved review for new voice clients/tasks implemented and verified locally.
Ambiguous phones/spelling clarify; edits/cancel/replay/rollback and bypass guards verified.
145dependent +38task-review +25PostgreSQL PASS; system/drift,5browser,build/types/i18n/bundle PASS.
18real synthetic audio workflows PASS;9required simulated human corrections, not exact-STT PASS.
Human/noise/fullD01/production remain open. No workingDB/env/deploy; own runtimes stopped.
Own-only commit;37foreign outgoing block push/newCI. Evidence:
docs/testing/evidence/voice-kazakh-20261111.md.

AI-ANALYTICS-COMPLEX-20261111: verification complete; overallFAIL, openA1–A4.
Periods/archives/roles tested on35primary+4foreign synthetic tasks; real API/Playwright.
Confirmed lost date/selected period, wrong own status breakdown, invalid plans, denied-source UX.
33initialAPI:29PASS/4FAIL; browser confirms findings.52realcalls/127566tokens; no data leak found.
39tasks preserved/0toolcalls; workingDB/env/productcode unchanged by this task; runtimes stopped.
Report-only; fixes/reverification remain. Own docs commit;36foreignoutgoing block push/newCI.
Evidence: docs/testing/evidence/ai-analytics-complex-20261111.md.

BUSINESS-IMPLEMENTATION-20261111: approved six-section workspace implemented locally.
Company/branches/staff/services/physical resources/schedule use real APIs and existing rules.
Backend97PASS/1PGskip +PG15 +absence9; system/drift PASS. Eight browser scenarios PASS,
RU desktop/KK320/EN390; logic6/i18n/types/app-widget/bundle PASS. Prior failures retained.
No workingDB/env/migration/provider/deploy changes; no scoped implementation remainder.
Task-only local commit;35foreign outgoing block push/newCI. Evidence:
docs/testing/evidence/business-workspace-20261111.md.

AI-ANALYTICS-FIXES-20261111: both live analytics findings fixed and locally verified.
Strict routing schema + bounded retry; overall totals separated from search matches.
182backend/system/driftPASS;7real-provider API/Playwright turns incl503/retryPASS.
15model calls,one format retry recovered;2synthetic tasks retained,0CRMtoolcalls.
WorkingDB/env/deploy untouched; own runtimes stopped. No scoped code/evidence remainder.
Own commit only;34foreign outgoing prevent push/newCI. FullD01/production remain open.
Evidence: docs/testing/evidence/ai-analytics-fixes-20261111.md.

VOICE-PLANNER-20261111: reproduced malformed planner JSON; default model policy fixed.
Default/tier now resolves before JSON capability; strict parser/direct/replay retained.
Before1/12FAIL; after24/24real audio→CRM+replayPASS,48JSONmode requests.
146dependentPASS +2baseline fixture failures fixed; finalquality/regression30/system/driftPASS.
No scoped code/evidence remainder; human/fullD01/production open. Foreign WIP preserved.
Own commit only;33pre-existing outgoing block push/newCI. Evidence:
docs/testing/evidence/voice-planner-20261111.md.

VOICE-RECOGNITION-20261111: names/phones fixed locally, synthetic corpus verified.
Scribe v2 default, exact digit-word phone conversion; ZDR/access/direct flow preserved.
10real STT/model API→CRM+replay PASS;118backend/system/driftPASS. Initial transient
planner failure retained; not a general human/KK/noise/fullD01/production certification.
No workingDB/env/deploy changes. Own local commit;32foreignoutgoing block push/newCI.
Evidence: docs/testing/evidence/voice-recognition-20261111.md.

TIMELINE-FLAT-PAGINATION-20261111: approved flat prototype implemented in timeline only.
Rows select + persistent range + arrows; no panel/page badge; global search width retained.
Browser1440/390/320, RU/KK, boundaries/zero/size/keyboard PASS; Node9/build/types/i18n/bundle PASS.
No shared component/backend/workingDB/deploy changes; foreign WIP retained.
Own local commit only;29pre-existing outgoing commits block own-only push/newCI.
Evidence: docs/testing/evidence/timeline-fixes-20261111.md#flat-pagination.

CRM-GLOBAL-TEST-PLAN-20261111: detailed draft prepared for owner review.
Implemented-function matrix, Computer user scenarios and static route/test inventory.
No application tests/build/browser/server/DB/provider actions; no acceptance closure.
Execution target/candidate/external effects/defect policy require plan agreement.
Plan: docs/testing/crm-global-plan-20261111/README.md.
Checkpoint: output/crm-global-test-plan-20261111/CHECKPOINT.md.

AI-AGENTS-FIXES-20261111: readiness/UI fixes implemented and locally verified.
Provider/configuration and booking diagnostics; effective actions, recovery, scoped Inbox.
Backend123/system/drift/browser7+final1/build-types-i18n-bundle PASS; RU/KK/EN320–1440.
Design/permissions/foreign WIP retained; no workingDB/provider/deploy or new CI.
No scoped implementation/local-evidence remainder; foreign outgoing range blocks push.
Evidence: docs/testing/evidence/ai-agents-fixes-20261111.md; output/ai-agents-fixes-20261111.

TIMELINE-PAGINATION-20261111: search uses global-header width; pagination moved into toolbar.
Desktop1440 both search controls480px; single-row toolbar; table footer removed.
Browser320/390/1024/1440 paging/back/size/filter-reset/keyboard PASS; no page overflow.
Node9/build-types-i18n/bundle logs in output/timeline-pagination-20261111.
No backend/workingDB/deploy changes; own publication blocked by foreign outgoing range.
Evidence: docs/testing/evidence/timeline-fixes-20261111.md#toolbar-pagination.

TIMELINE-LAYOUT-20261111: requested layout refinement implemented and locally verified.
Table matches Clients width; balanced desktop gaps and expanded mobile list.
Single toolbar date button opens shared DatePickerPanel; atomic range/clear/cancel.
Node9/build/types/i18n/bundle PASS; browser RU/KK/EN320–1440/calendar/keyboard PASS.
No backend/workingDB/provider/deploy changes. Own commit only; foreign outgoing blocks push.
Evidence: docs/testing/evidence/timeline-fixes-20261111.md#layout-refinement.

TIMELINE-FIXES-20261111: all5 audit findings fixed and locally verified.
RU/KK/EN event catalog; safe historical details/current object names; author semantics;
compact mobile/filter disclosure/single scroll; prior design and access retained.
Backend113/presentation9/system-drift/build-types-i18n/bundle/browser PASS.
Browser320–1536: locales/keyboard/filter/paging/link/recovery/operator denial PASS.
No workingDB/migration/provider/deploy; publication blocked by25foreign outgoing commits.
Own local commit only; exact commands/limits: docs/testing/evidence/timeline-fixes-20261111.md.
Artifacts/checkpoint: output/timeline-fixes-20261111.

LOCAL-MIGRATIONS-20261111: exactly3 approved local migrations applied; no pending migrations.
Fresh pg_dump verified by restore:154tables/9855rows; SHA retained with backup.
RestoredDB rehearsal and workingDB old-column parityPASS;153data tables/9662rows unchanged.
Historical status choices +YCloud onboarding fields only; no provider actions/data reseeding.
IsolatedPG27/system/drift/5readonlyAPI/HTTP/browserloginPASS; dev.ps1 exit0,6services running.
No product source edits/push/deployment. Backup and checks:
docs/testing/evidence/local-migrations-20261111.md; output/local-migrations-20261111.

DIGITAL-DEPLOY-20261109: deployed and scoped live verification complete.
platformadigital.kz HTTPS; www validTLS redirects preserving path; DNS updated.
37public file hashes/404/securityheaders PASS; browserRU/KK/EN desktop/mobile/keyboard PASS.
CRM service and Market container identities/protected config hashes unchanged;
HTTPS stand pages200/protected APIs401 PASS. No DB/migration/app restart/source push.
Chrome timeout retained as client limitation; owner-approved in-app browser PASS.
Evidence and rollback: output/digital-deploy-20261109/RESULT.md. No scoped remainder.

META-LEGAL-20261109: owner-requested document proposals prepared, not published.
RU privacy/deletion/integration terms and owner options in output/meta-legal-20261109.
Meta terms and local data/event/disconnect behavior compared; text/link-target checks PASS.
Pending owner scope/retention/provider/operations decisions and proof of deletion/retention.
No public HTML/export edits, provider updates, code, deploy, commit or push.

BRANCH-WORKSPACE-20261109: implemented, scoped checks passed, activated locally.
Simple single-point overview/direct hours; physical resources linked to location;
service requirements jointly reserved for manual/bot/AI booking; snapshots retained.
API/migration42; bot/AI46; PG6+7; card/PII/budget40; browser6/build/types/i18n/bundlePASS.
Aggregate239PASS/14PGskips retains1bad-label loaderERROR, correctedconsumer runPASS.
Owner-approved two migrations applied; backup restore152tables/10287rowsPASS,
all existing data preserved incl14appointments. No scoped code/local-evidence remainder.
No push/deploy/CI;3foreign migrations and existing worker outside activation scope.
Evidence: docs/testing/evidence/branch-workspace-20261109.md.
Details: output/branch-workspace-20261109/CHECKPOINT.md.

PUSH-FIXES-20261109: fixes verified, owner-approved local integration complete; NO PUSH.
Candidate commit6648e297; mergeff312e69 preserves both histories and verified source tree.
All9conflicts resolved as approved; duplicate Vite import avoided; stale lock archived.
Backend3106:3038PASS/68PG-only skips/0FAIL; PG35actual+62dependentPASS.
Node288+focused6/build-types-i18n/bundle/filter12browser/cardbrowserPASS.
Card fixture148383/150000bytes,maxSQL12181/15000; relations/limits/foreign work retained.
origin/main is ancestor; no new CI, workingDB/migration/provider/deployment changes.
Evidence: docs/testing/evidence/push-fixes-20261109.md.
Details: output/push-fixes-20261109/integration-result.json and CHECKPOINT.md.

PUSH-PREPARATION-20261109: all-change review and verification completed with blockers.
1184-path reviewed snapshot; explicit829-path staging proposal; source unchanged.
Confirmed: numeric blank filter500, multiselect filter400, task-history encoding.
Backend3081:3003PASS/3FAIL/11ERROR/64PG-only skips;13mixed-versionYCloud failures
fresh-reproduced13PASS. PG45:43PASS/2card-budget FAIL; Node8failures confirmed.
Build/types/i18n/bundle/mobile2/dependency audits/tooling checks PASS; separate
YCloud82+4PG/10browser evidence reused after22source hashes verified.
Not push-ready: findings/tests/budgets plus Git20local/3remote and existing lock.
No product edits/stage/commit/push/newCI/workingDB/deploy. Report and exact scope:
output/push-preparation-20261109/REPORT.md; RESULT.json and CHECKPOINT.md.

YCLOUD-COEXISTENCE-20261109: local CRM preparation and TP Lite support draft complete.
Explicit Business App mode + expected-number binding; signed app replies deduplicated,
recorded as sent staff messages, pause AI, no resend/unread/24h-window extension.
82 PostgreSQL affected/dependent +4 concurrency PASS; schema/system PASS.
10 targeted browser tests RU/KK/EN desktop/mobile +build/i18n/types/bundle PASS.
Migration0010 isolated only; no live provider/account/server changes or message sent.
No commit/push/CI: existing index.lock and divergent foreign history remain blockers.
Evidence: docs/testing/evidence/ycloud-coexistence-20261109.md.
Draft/artifacts: output/ycloud-coexistence-20261109.

CRM-UI-FIXES-20261109: all15 audit findings fixed and locally verified.
Existing design retained; menus/plan confirmations/mobile controls/client tabs,
task date+footer/import results/priority actions/localized labels/public wrap.
Desktop1440/mobile390 plus320 public; real isolated API saves/import and503recovery PASS.
RU/KK/EN representative screens,13navigation tests/build-types-i18n/bundle PASS.
No scoped code/UI-evidence remainder; no backend/workingDB/migration/deploy changes.
Own publication blocked by existing index.lock and3remote-only/20foreignlocal commits.
No own stage/commit/push/newCI. Evidence: docs/testing/evidence/crm-ui-fixes-20261109.md.

LOCAL-RELEASE-20261108: owner-approved relations restoration and local candidate archive.
Task/card/access focused12 PASS; PostgreSQL combined76 =74PASS/2performance FAIL.
Card payload152195>150000; SQL15068>15000. Same-fixture before/restored36queries,
SQL15011unchanged; requiredrelations add11434bytes. Limits unchanged; not deploy-ready.
Earlier notification145PG, otherPG29+53, mobile2, builds/audits PASS reused.
Archive includes exact manifest+acceptance gaps; SHA/member verification recorded.
Foreign source/index preserved; no staging/commit/push/CI/workingDB/deploy changes.
Evidence: docs/testing/evidence/local-release-20261108.md;
artifacts: output/local-release-20261108.

PERFORMANCE-20261106: measured SQL/auth bottlenecks fixed locally; load repeated.
Request-local permissions; client counts/facets/page enrichment. No API/schema change.
Large clients median2053→336ms; auth281→11SQL, tasks623→13SQL.
PG75/51/72 +SQLite18/system-drift PASS. Small5users180s p95822ms PASS;
large1user180s p951196ms FAIL; later no-think1stream180s2.88rps/p95599ms PASS.
Real system paging observed; shared-host capacity not certified. All HTTP/writes PASS.
No workingDB/env/deploy changes; benchmark DBs removed. Gitlock/20foreignoutgoing/
3remote-only block own commit/push/newCI. Evidence:
docs/testing/evidence/performance-20261106.md; details output/performance-20261106.

CRM-SCREENSHOTS-20261106: browser catalog delivered locally.
656 unique PNGs (790 captures;134 exact duplicates);97 routes accounted incl aliases.
Desktop/mobile, merchant/platform/public, dialogs/shared components; synthetic isolated data.
PNG/ZIP/gallery search+filters PASS;434TSX source hashes unchanged during capture.
All task-owned runtimes stopped; no product/workingDB/deploy changes or full-state certification.
Gallery and scope: output/crm-screenshots-20261106/index.html and README.md.

INTERNAL-NOTIFICATION-ACCOUNTING-20261106: stand queue warning removed; healthy.
Internal feed excluded from transport counts and batch/claim/direct delivery; publication errors remain visible.
54 records retained,24 read/30 unread; full notification/state/activity/audit hashes unchanged.
21 isolated tests plus live repeat processing/HTTPS/services/protected hashes PASS.
External worker unchanged/off for notifications; password/foreign WIP preserved.
Own commit6a8af190; no push due unrelated outgoing history.
Evidence: output/internal-notification-accounting-20261106/RESULT.txt.

POSTGRES-LOAD-20261106: local CRM switched to PostgreSQL17.10; original SQLite retained.
Final backup +152tables/10117rows field parity +pg_dump restore PASS; real API→PG proof.
16focused/141isolatedPG tests PASS; local startup/token Windows tasks exit0.
Load measured small/100k-client datasets: no p95<=1s SLO pass on shared7.7GiB machine.
5users small1.98req/s p952.96s; large1.03req/s p9510.69s,0%errors (1worker).
Two later foreign choices-only migrations remain pending; no production changes.
Evidence: docs/testing/evidence/postgres-load-20261106.md; details/backup in output/postgres-load-20261106.

DELIVERY-SYNC-20261106: owner-approved stand resolution verified.
Messages29/30/36 cancelled;1C connector4/run9 deferred; history retained,5 audit records.
24 isolated tests,live history/replay/HTTPS/services/protected-config PASS.
Delivery/sync failures0; queue warning remains for54 system notifications.
Own commit377b6329; no push due18 pre-existing outgoing commits; foreign work preserved.
Evidence/backup/limits: output/delivery-sync-20261106/RESULT.txt.

VOICE-RELIABILITY-20261106: original audio failure reproduced and fixed locally.
Router had created only Client; explicit booking retains atomic client+visit workflow.
Persisted same-Business Appointment/count required before success; factual RU/KK/EN replies.
Focused11/final dependent102/system-drift + real ASR/model4 audio cases PASS; replay safe.
Working14visits/config unchanged. No scoped code/local-evidence remainder; human/fullD01/production open.
No commit/push/CI/deploy: origin2ahead/18foreignoutgoing. Evidence: docs/testing/evidence/single-location-20261106.md#voice-reliability-20261106.

EMAIL-READINESS-20261106: Resend Free SMTP deployed; mail blocker closed.
Verified notify.platformacrm.kz; sending-only domain key, enforced TLS, tracking off.
One synthetic mail Delivered and owner-confirmed Inbox;74 isolated checks and runtime SMTP/HTTPS PASS.
Only approved test Notification630/632/635 cancelled with audit;pending email0.
Stand password/protected hashes and foreign source preserved; encrypted backupPASS.
General gate remains7PASS/5FAIL; no full release certification/newCI/source push.
Evidence/rollback/limits: output/email-readiness-20261106/RESULT.txt.

CRM-LANDING-INTEGRATION-20261106: scoped landing deployed to protected platformacrm.kz.
Published1dc5a6c8 main/fullCI+standCI PASS;112 static files and exact Caddy routes activated.
Existing1342 release files/SPA, password/env and SSE preserved; HTTPS and live browser RU/KK/EN/mobile PASS.
Home opens landing; login opens existing CRM form. Real account authentication not exercised.
Encrypted backup/health PASS. No backend/DB changes or whole-release certification.
Deployment: output/crm-landing-deploy-20261106/RESULT.md.
Evidence: docs/testing/evidence/crm-landing-integration-20261106.md.

REACTIVATE-BRANCH-20261106: existing archived Branch1 activated through domain service/audit.
Catalog/staff/hours unchanged; existing slot available. Real audio+model booking PASS
on disposable exact-config copy; replay no duplicate; working14appointments unchanged.
First audio completed without Appointment remains an OPEN D01 reliability finding;
text replay and explicit Create booking audio PASS do not erase it. No product edits/deploy.
Evidence: docs/testing/evidence/single-location-20261106.md (explicit activation follow-up).

DEV-MIGRATION-CHECK-20261106: fresh local SQLite backup verified; dev exits0/no warnings.
branches0003 was already applied by DB-MAINTENANCE; independently confirmed,
no rollback/reapply. Original pre-migration backup hash/integrity verified too.
Fresh backup integrity/FK/restore153tables PASS; all six dev services ready/reused.
No product/schema/data mutation or deployment. Checkpoint/backups (Git-ignored):
output/dev-migration-check-20261106/CHECKPOINT.md. Prior dev exit2 warning superseded.

DB-MAINTENANCE-20261106: verified backup; local branches0003+scheduling0012 applied.
All16 businesses have a branch; general-hours duplicate constraint/API recovery.
Expired tokens3552+blacklist2987 removed; live tokens/revocations unchanged.
Daily Windows task12:00/current-user login; two runs exit0. SQLite101/PG12,
system/drift/integrity/FK PASS. No local remainder; production unchanged.
Publication blocked by divergent foreign range. Evidence:
docs/testing/evidence/db-maintenance-20261106.md.

PRIVATE-STORAGE-20261106: protected stand switched to existing private S3; W012 and W006 closed.
91 focused tests plus deployed-code S3/ClamAV/API tenant-denial/import/export/recovery PASS.
81 files copied with hashes; disk originals retained. Encrypted S3 backup/restore and HTTPS PASS.
Stand password preserved; approved key replacement saved and old key revoked.
Evidence/rollback/limits: output/observability-storage-20261106/STORAGE-RESULT.txt.

DEV-COMMAND-20261106: one Windows command ./dev.ps1 starts/reuses local stack.
Redis/ClamAV/updater/import worker/Django/Vite; serialized start, source/PID checks,
health/logs and explicit failures. No installs/env edits/migrations/Windows autostart.
Ten focused tests PASS; live frontend start and repeated six-service reuse/health PASS.
Current run exits2 honestly: branches0003 remains pending from another task.
Dev services retained; launcher scope complete, database migration requires separate approval.
Canonical branch codex/ui-testing-toolkit; publication blocked by foreign outgoing range.
Checkpoint: output/dev-command-20261106/CHECKPOINT.md.

SENTRY-20261106: protected stand receives sanitized errors; W006 closed.
67 focused/dependent tests, live synthetic receipt/email-rule trigger and HTTPS PASS.
Free trial with no payment method; automatic Developer fallback, no paid subscription.
W012 storage remains open after earlier browser interruption. Source publication blocked
by 15 unrelated outgoing commits; runtime deployed separately, no new CI claimed.
Evidence: output/observability-storage-20261106/RESULT.txt.

SINGLE-LOCATION-20261106: automatic single point/multi-branch and voice fixes locally verified.
Shared catalog/hours, explicit second-point setup, last-active archive guard and retained visit terms;
voice branch/date/mapping/slot reasons and calendar context including text fallback.
Affected205, final dependent102, reschedule77 across corrected runs; PG17+21 and browser5 distinct,
final shared-hours delta46/build/types/i18n/bundle PASS. Working branches0003 applied externally;
read-only schema/counts/quick_check verified15automatic+1archived, no own workingDB writes.
No scoped code/local-evidence remainder. Publication blocked by divergent remote/16foreign outgoing.
Evidence: docs/testing/evidence/single-location-20261106.md; detailed checkpoint in output/single-location-20261106/CHECKPOINT.md.

PILOT-BOUNDARIES-FIX-20261106: all three security findings fixed and verified locally.
Admin MFA/session proof, password-change throttle, shared Redis quotas; focused/dependent tests and real browser PASS.
Published security fixes as b96a69514b47a7211899e745b94b1109a36bb4e6 on origin/main; stale empty lock archived. Current branch/index and 592 local files preserved; 15 foreign commits remain local. CI 42198771978 success. Security runtime delta deployed to protected stand 2026-11-06; external HTTPS, admin MFA proof denial, shared Redis, password throttle, services/backups PASS. Stand password unchanged. Details: output/security-deploy-20261106/RESULT.md.
Evidence and exact limits: [C:/Users/user/.codex/state/plugins/codex-security/scans/PlatformaCRM/artifacts-5c104f7eb8ffeb335f0ca5772aabb0cf2c88c0a722d9ac17d6bb18e0f3934604/artifacts/security-fixes-20261106/report.md](C:/Users/user/.codex/state/plugins/codex-security/scans/PlatformaCRM/artifacts-5c104f7eb8ffeb335f0ca5772aabb0cf2c88c0a722d9ac17d6bb18e0f3934604/artifacts/security-fixes-20261106/report.md).

PILOT-BOUNDARIES-20261106: three original failures fixed locally; bounded access audit found admin MFA bypass and two throttle gaps. Gate retained, no deploy; existing Git lock/foreign outgoing block publication. Evidence: output/pilot-boundaries-20261106/CHECKPOINT.txt.

MFA-LOGIN-20261106: login-styled MFA and simple Sign in completion saved locally.
Recovery-code reveal removed from login enrollment; backend/account recovery unchanged.
New browser10 + existing recovery1/TOTP1 + Node15/build-types-i18n/bundle PASS.
Existing invitation notification400 and prior3 full-gate failures remain visible.
Owner paused deployment: Yandex balance exhausted, VM STOPPED; new artifact not uploaded.
Existing Gitlock/17foreign outgoing prevent commit/push. Resume checkpoint:
output/mfa-login-20261106/CHECKPOINT.md (patch/artifact/tests/deploy procedure).

IMPORT-FULL-EXCEL-20261106: original XLSX fully verified through CRM clients.
Real chooser/ClamAV/mapping/reload/preview/confirm + all20 persisted fields/list rows PASS.
Real Redis/Celery4 tasks; confirm replay and full reimport retain20/no duplicates.
Restored local scanner/updater/loopbackRedis/import worker; health/PONG PASS.
WorkingDB contains0 test-file emails; no product/.env/migration changes or deployment.
No scoped remainder; local services retained, Windows autostart outside scope.
Existing Gitlock/17foreign outgoing block commit/push/newCI. Evidence:
docs/testing/evidence/import-upload-alert-20261106.md (full Excel follow-up).

VOICE-WORKFLOWS-20261106: connected voice booking/visit plans and history locally verified.
Atomic client+visits; full scoped lookup, retained clarifications, server timezone;
linked results/history, matched 20px bell and labeled recording controls.
Affected165 + final64 + PostgreSQL58, real-model7, browser/build/types/i18n/bundle PASS.
No scoped code remainder; human/fullD01/production acceptance remains open.
Existing lock/17foreign outgoing block own commit/push/newCI; no workingDB/env/deploy.
Evidence: docs/testing/evidence/voice-workflows-20261106.md.


IMPORT-NEW-PICKER-20261106: New transfer opens file chooser before creating draft.
Cancel creates nothing; selected XLSX uploads immediately; append/retry reuse draft.
Browser4 RU/KK/EN+existing recovery1, Node3/build-types-i18n-bundle PASS.
No scoped code/evidence remainder; backend/workingDB/env unchanged.
Existing lock/17foreign outgoing block own commit/push/newCI; no deployment.
Evidence: docs/testing/evidence/import-upload-alert-20261106.md (file-picker follow-up).

IMPORT-UPLOAD-ALERT-20261106: local Excel upload and compact error notices fixed.
Existing ClamAV/updater restored; real Excel20 rows API200 PASS, user draft rolled back.
Import errors use bottom-right host/no layout shift, compact real request-code copy,
clear read-only refresh and localized scanner reason. No AV bypass/DB migration.
Backend25/system-drift/Node10/browser5+shared1/build-types-i18n-bundle PASS.
Scanner/updater intentionally retained; Windows autostart/production not asserted.
No scoped code/evidence remainder; existing lock/17foreign outgoing block publication.
Evidence: docs/testing/evidence/import-upload-alert-20261106.md.

VOICE-DIRECT-20261105: ordinary voice actions locally verified (completion06.11).
Record→Send→action/clarification→result; no transcript or second confirmation.
Original task wording retained; empty-title clarification, RU/EN/KK values checked.
Backend113/system-drift/concurrency, browser8+realRU audio, queued7, build/types/bundle PASS.
No scoped code/local-evidence remainder. Human/fullD01/production acceptance open.
Existing lock/17foreign outgoing block own commit/push/newCI; no DB/env/deploy change.
Evidence: docs/testing/evidence/voice-direct-20261105.md.

IMPORT-CREATE-20261106: local New transfer schema issue resolved.
Owner explicitly authorized working migration without backup; core0014-0017 applied.
Existing business table counts/integrity PASS; API create201/history200 PASS with
smoke draft rolled back. No backup created in application step, no source change.
Worker/scanner/full import acceptance unchanged; no deploy/commit/push/newCI.
Checkpoint: output/import-create-20261106/CHECKPOINT.md (includes prior temp blocker).

CONNECTIONS-SETTINGS-20261105: Connections moved to Settings tab locally complete.
Desktop/mobile sidebar entry removed; legacy routes/query redirect preserved.
Settings entry supports integrations.view; sections/manage retain own permissions.
Six distinct scoped browser cases across runs, RU/KK/EN, dialogs/keyboard/error,
final build/types/i18n/bundle PASS. No scoped code/evidence remainder.
Existing index.lock/17foreign outgoing block commit/push/newCI; no deploy/workingDB.
Evidence: docs/testing/evidence/connections-settings-20261105.md.

VOICE-REBUILD-20261105: capture/panel and task interpretation locally verified.
Real waveform, complete PCM checks, visible interruption; original request retained.
Final backend98/system-drift/Node7/browser10 distinct/build-types/bundle PASS.
Real task clarification3 + RU/EN/KK3 + long21s browser-to-Task PASS.
Human microphone/noise and production acceptance remain open; publication blocked.
Evidence: docs/testing/evidence/voice-rebuild-20261105.md.
Existing lock/17foreign outgoing preserved; no workingDB/env/deploy change.

ENTITY-FIXED-SIZE-20261105: Client and Appointment fixed viewport size complete locally.
Max width1080, height90dvh (mobile viewport−24px), stable across tabs/loading/error.
Desktop header/tabs fixed, sidebar/panel scroll independently; mobile one body scroll.
Six Client +five Appointment scoped cases across runs/build-types-i18n-bundle PASS.
No scoped remainder; existing lock/17foreign outgoing block own commit/push/newCI.
Evidence: docs/testing/evidence/entity-cards-20261105.md (fixed-size follow-up).

VOICE-NATURAL-20261105: full capture and natural GPT-4o mini replies locally verified.
Recorder preload/drain; punctuation preserves recognized words/numbers; natural chat.
Affected84/Node5/browser6/live syntheticRU browser-to-Task/build-types/bundle PASS.
Human RU/KK/mixed/noise and production acceptance remain open; no scoped code remainder.
Evidence: docs/testing/evidence/voice-natural-20261105.md.
Existing lock/17foreign outgoing block publication; no workingDB/env/deployment change.

CLIENT-LAYOUT-TABS-20261105: owner follow-up locally complete.
Client actions above/name left; Client+Appointment single scrollable tab strip,
no More selector/scrollbar, overflow arrows+keyboard. Client deals tab removed.
Tablet nearest-record wrapping and mobile action row corrected.11 distinct client
cases across scoped runs +4 appointment cases; final locale6/build/types PASS.
No scoped remainder; existing lock/17foreign outgoing block own commit/push/newCI.
Evidence: docs/testing/evidence/entity-cards-20261105.md (layout/tabs follow-up).

APPOINTMENT-LAYOUT-20261105: reference rearrangement locally complete.
Actions in fixed top header/mobile second row; name/date/status in sidebar;
tabs at body top, text-first activity markers. Contacts/source/plan/guards retained.
Eight scoped interaction cases + final locale3/build/types/i18n/bundle PASS.
No scoped remainder; existing lock/17foreign outgoing block commit/push/newCI.
Evidence: docs/testing/evidence/appointment-card-20261105.md (reference follow-up).

ENTITY-CARD-FOOTER-20261105: owner follow-up locally complete.
Removed redundant bottom Close/divider in Client and Appointment modals;
content reclaims height, top close/Escape and draft/pending guards retained.
Four scoped RU/KK/EN desktop/mobile browser cases and build/types/bundle PASS.
Initial stale footer-based test waits failed; corrected field/save wait rerun PASS.
No scoped remainder; existing lock/17foreign outgoing block commit/push/CI.
Evidence: docs/testing/evidence/appointment-card-20261105.md (footer follow-up).

VOICE-HARDENING-20261105: false text-command rejections fixed; Turbo synthetic RU API Task/replay PASS.
Live command checks exposed planner schema/cancel routing and time-only reschedule defects;
fixed prompt/shape and preserved specialist/reason in existing domain adapter.
Final affected98/system/drift PASS; live seven-command queue matrix PASS.
Human RU/KK/mixed/noise and production broker/worker acceptance remain open.
Existing lock/17foreign outgoing block publication; no workingDB/env/deploy change.
Evidence: docs/testing/evidence/voice-hardening-20261105.md.

APPOINTMENT-CARD-20261105: next entity-card stage locally complete.
Centered/no-blur Appointment, sections/actions/reasons/version recovery, draft guards;
Client↔Appointment back, Calendar inspector restoration, context voice preserved.
Node13/browser17 distinct scoped cases across runs/final build-types-i18n6895/bundle PASS.
Real related note/field/file, status actions, role/foreign denial and RU/KK/EN checked.
No scoped code/evidence remainder; workingDB/dev retained. Existing lock/17foreign
outgoing block publication; no own commit/push/newCI/deploy. Task/Plan not started.
Evidence: docs/testing/evidence/appointment-card-20261105.md.

RECORDS-CALENDAR-FIXES-20261105: two Records filters and Calendar interactions fixed locally.
Retained inaccessible values show #ID; custom filter survives empty/error and follows URL.
Sticky Calendar toolbar/panels remain below header; booking harness corrected.
Node17/Calendar9+14/Records7/audit8 distinct scoped cases PASS across final runs;
final build and mobile separator recheck recorded in evidence. WorkingDB/dev retained.
Existing lock/17foreign outgoing block publication; no own commit/push/newCI/deploy.
Evidence: docs/testing/evidence/records-calendar-fixes-20261105.md.

SESSION-NOTICES-20261105: coordinated connection/session recovery locally verified.
One shared host; related session warning suppressed during server outage, revealed
only if still needed after readiness recovery. Specific RU/KK/EN recovery copy.
Node9/20 distinct browser cases across scoped runs/final locale3/build-types-i18n6895/
bundle PASS. Login429 harness failures retained; fresh focused reruns PASS.
No workingDB/backend change. Existing lock/foreign outgoing block publication;
no own commit/push/newCI/deploy. Evidence: docs/testing/evidence/session-notices-20261105.md.

ENTITY-CARDS-20261105: discussion/specification registered; Client modal locally complete.
Centered/no blur, reference layout, permitted actions/related sections, correct next
appointment, draft/pending/error recovery and localized dates.14 distinct scoped
browser cases + Node12 + final build/types/i18n6894/bundle/docs PASS.
Evidence: docs/testing/evidence/entity-cards-20261105.md; spec docs/current/entity-cards.md.
No scoped code/evidence remainder. Existing lock/no upstream/foreign outgoing block
publication; no own commit/push/newCI/deploy. Appointment stage not started.

VOICE-LIVE-20261105: real OpenRouter audio→text→proposal→confirmed Task PASS.
Fixed STT404 data-policy route with Whisper Large V3, preserving ZDR/no-data-collection.
Local ai_core0009 applied with SQLite backup/quick_check; local no-worker inline mode.
Named-task optional deadline prompt corrected; focused19+35/system/drift PASS.
Real RU synthetic API/replay and Chromium mic→Task PASS; KK/noise/full D01/live-worker open.
Existing lock/17foreign outgoing: no own commit/push/newCI/deploy.
Evidence: docs/testing/evidence/voice-live-20261105.md.

VOICE-INTERFACE-20261105: voice is independent CRM interface, no created Bot.
Private user/Business voice threads + built-in runtime; permissions/approval/replay retained.
Backend92/Node4/browser6 RU KK EN/build-types-i18n6883/system-drift/migration PASS.
Code/local evidence complete; working ai_core0009 migration needs owner target approval.
Live STT/full D01 open; existing lock/17foreign outgoing block publication.
No own commit/push/CI/deploy/workingDB writes. Evidence:
docs/testing/evidence/voice-interface-20261105.md.

CLIENTS-RECORDS follow-up05.11: page searches use global-header width; Manual
accounting restored to standalone header action; Clients export/menu removed.
Node12, nine scoped browser scenarios across focused runs, build/types/i18n6883/
bundle PASS. Existing lock/foreign outgoing block publication; no own push/CI.
Evidence: docs/testing/evidence/clients-records-20261105.md (owner follow-up).

CLIENTS-RECORDS-20261105: Clients layout/control cleanup complete locally.
Records spacing, single toolbar/filters/columns/menu and direct client drawer;
nonfunctional checkboxes removed, create respects rights. Node12/eight scoped
browser scenarios/build-types-i18n6883/bundle PASS; isolated DB only.
Publication blocked by existing lock/foreign outgoing; no own commit/push/CI/deploy.
Evidence: docs/testing/evidence/clients-records-20261105.md.

VOICE-ASSISTANT-20261104: agreed voice workflow locally implemented/verified05.11.
Header capture→editable transcript→private turn→button approval→CRM result;
personal settings/account recovery, OpenRouter adapter, bounded voice policies.
Affected BE86+later22/language1, Node4, scoped browser/RU KK EN/build/types/i18n PASS.
Live STT quality/rollout open; existing lock/foreign outgoing block publication.
WorkingDB/foreignWIP preserved; no own commit/push/newCI/deploy. Evidence:
docs/testing/evidence/voice-assistant-20261104.md; detailed checkpoint in output.

IMPORT-DEMO-20261104: actual CSV and XLSX UI uploads each PASS in separate
isolated DBs, four linked entities per format. Correction/customfields/preview/
confirm and native consumers verified.8synthetic files+ZIP and screenshots saved.
No product/workingDB changes; own runtimes stopped; prior publication block retained.
Evidence: docs/testing/evidence/import-workspace-20261104.md (demo section).

ENTITY-PREREQUISITES-20261104: entity dependency/user setup analysis documented.
Matrix separates current creation requirements, activation conditions and proposed
guidance; static review only, no product fixes or full runtime certification.
Report: docs/testing/entity-prerequisites-20261104.md. Existing WIP preserved.
Publication blocked by existing index.lock and absent branch upstream; no push/CI.

IMPORT-WORKSPACE implementation04.11 locally verified: four-entity file wizard,
row corrections/profiles/native previews/custom-field consumers/background recovery.
Import effects suppressed; future activation explicit. Backend135+2 focused/PG races,
Node15/browser7/build/types/i18n6850/bundle PASS within evidence boundaries.
No code/local-evidence remainder; publication blocked by existing lock/mixed outgoing.
WorkingDB unchanged; no commit/push/newCI/deploy. Detailed evidence:
docs/testing/evidence/import-workspace-20261104.md.

RECORDS-DRAWER-20261104: approved table/drawer/filter implementation verified locally.
Client-first rows, independent client navigation, appointment drawer with plan/history/
tasks/reschedule, anchored draft filters and calendar button implemented locally.
Node8/browser7/build/types/i18n6685/bundle PASS. Nested Escape and stale-version
after reschedule reproduced, fixed and rechecked. WorkingDB/foreignWIP preserved;
existing Git lock/mixed outgoing block publication. Evidence: records-drawer-20261104.

IMPORT-WORKSPACE follow-up04.11: owner accepted scenario/references; current-code
comparison added to current/import-workspace. Existing import edits mapping only;
source sample is not an editable future CRM preview. New wizard remains unimplemented.
Node import review/history12 PASS; static UI/API/service/parser trace, docs checks.
No product/runtime/workingDB changes. Publication blocked by existing lock/mixed
outgoing; no own commit/push/newCI. Boundary/details in PRIMARY.

IMPORT-WORKSPACE-20261104: migration direction documented in current/import-workspace.
First phase files→clients/specialists/services/appointments + custom fields and
preview; AI explicitly excluded, optional future only. Three Image Gen references
in output/import-workspace-20261104. No product code/runtime/deploy changes.
Docs/publication boundary in PRIMARY; existing index.lock/foreign outgoing retained.

REMEDIATION-C11-20261104: stale export completion closed locally.
Per-attempt token fences success/failure; unique file names and losing-output cleanup.
BEFORE3:2FAIL/1PASS; focused20/expanded7/dependent32/PG9 + system/drift PASS.
Migration core0013 isolated only; workingDB unchanged, dev off, foreign WIP retained.
Evidence: docs/testing/evidence/remediation-c11-20261104.md. Own local commit only;
no push/newCI/deploy/live storage. C12 not started; C26 limits/rows unchanged.

REMEDIATION-C10-20261104: idempotency pruning race closed locally.
DELETE rechecks original expiry cutoff; renewed claim/result and replay survive.
BEFORE3:2FAIL/1PASS; focused3/dependent23/PG8 PASS; system/drift PASS.
WorkingDB unchanged, dev off, foreign WIP preserved. Evidence:
docs/testing/evidence/remediation-c10-20261104.md. Own local commit only;
no push/newCI/deploy/live. C11 not started; C05 retained-temp limitation unchanged.

REMEDIATION-C09-20261104: context and creation effects closed locally.
Explicit Business AI assignee setting/UI, current validation, source conversation;
one transactional BusinessEvent/followups/notification/automation, replay/rollback.
SQLite145 affected (144PASS + corrected legacy expectation recheck1PASS), settings12,
PG21, migration/OWN/branch checks, browser6 and build/types/i18n6685 PASS.
WorkingDB unchanged; migration0014 isolated only. Dev off, foreign WIP retained.
Evidence: docs/testing/evidence/remediation-c09-20261104.md. Own local commit only;
no push/newCI/deploy/live. C10 not started; C05 retained-temp limitation unchanged.

REMEDIATION-C08-20261104: stale automatic-booking terms closed locally.
Offers bind price/duration; final creation rechecks, legacy incomplete offers refuse;
zero price preserved. Catalog lock + PG nullable-join locks verified.
SQLite focused26/dependent48 + system/drift PASS; final PG36 PASS.
WorkingDB unchanged, dev off, foreign WIP preserved. Evidence:
docs/testing/evidence/remediation-c08-20261104.md. Own local commit only;
no push/newCI/deploy/live model/channel. C09 not started; C05 temp limitation unchanged.

REMEDIATION-C07-20261104: frontend telemetry bearer URL leak closed locally.
Sentry final hooks/PostHog enriched events/Plausible manual URLs sanitized;
PostHog flags/replay disabled; sensitive Plausible referrer suppresses tracking.
Node+actual SDK Chromium20 PASS; actual Plausible2 scenarios PASS;
safe build/types/i18n6682 PASS. WorkingDB unchanged, dev off, foreign WIP retained.
Evidence: docs/testing/evidence/remediation-c07-20261104.md. Own local commit only;
no push/newCI/deploy/live ingestion. C08 not started; C05 cleanup limitation unchanged.

REMEDIATION-C06-20261104: ownerless Inbox draft adoption closed locally.
Only user/business/conversation drafts restore; legacy values remain unread/unchanged.
BEFORE8:2FAIL/6PASS; AFTER14PASS; browser4PASS; safe build/types/i18n6682 PASS.
WorkingDB unchanged, dev off, foreignWIP preserved. Evidence:
docs/testing/evidence/remediation-c06-20261104.md. Own local commit only;
no push/newCI/deploy. C07 not started; earlier C05 temp cleanup limitation remains.

REMEDIATION-C05-20261104: logout failure/retry boundary closed locally.
UI waits for server revocation; persistent RU/KK/EN failure/retry, queued refresh
and stale logout guards, sibling-tab completion. Node31/browser43 PASS(11 planned
SKIP); safe build/types/i18n PASS. WorkingDB unchanged, dev off, foreign WIP retained.
Evidence: docs/testing/evidence/remediation-c05-20261104.md. Own local commit only,
no push/newCI/deploy. C06 not started.
Two interrupted test folders retained after policy-blocked cleanup.

REMEDIATION-C04-20261104: clean source archive boundary closed locally.
Nested runtime/env/DB/browser artifacts excluded; links/special files skipped;
real Python ZIP, guarded destination and LF entrypoint.7 synthetic tests PASS,
exact manifest/bytes/CRC + failure cleanup. WorkingDB unchanged, dev off.
Evidence: docs/testing/evidence/remediation-c04-20261104.md. No real checkout
archive/distribution; own local commit only, no push/newCI/deploy. C05 not started.

REMEDIATION-C03-20261104: broker/exception console leaks closed locally.
Readiness uses configured/TLS metadata; JSON console masks recognized credentials
in args/chains/context and preserves diagnostics. Focused11/completion105 PASS,
system/drift PASS. Evidence: docs/testing/evidence/remediation-c03-20261104.md.
Sentry/other sinks unverified; no blanket telemetry PASS. WorkingDB unchanged,
dev off; own local commit only, no push/newCI/deploy. Next C04 not started.

REMEDIATION-C02-20261104: TEAM-ANALYTICS Lead source boundary closed locally.
Team performance applies current LEADS VIEW scope/capability before aggregation.
BEFORE10:4 FAIL/6 PASS; AFTER10 PASS; completion54 PASS + system/drift.
Evidence: docs/testing/evidence/remediation-c02-20261104.md. WorkingDB unchanged,
dev off, foreign WIP preserved; own local commit only, no push/newCI/deploy.
Next C03 not started. Other source-resource metrics are outside this Lead-only cycle.

REMEDIATION-C01-20261104: UI31/VERIFY02 closed locally; dev stopped.
Guarded isolated helpers, missing-action/5xx failure predicates, valid recovery
fault fixtures implemented. Node7/Python23, isolated prepare/serve/CSRF/login,
system/drift, real PG/Redis crash/rollback/retry/exactly-once PASS; workingDB unchanged.
Evidence: docs/testing/evidence/remediation-c01-20261104.md. One old disposable
folder remains after cleanup policy rejection; final test runtime cleaned.
Own local commit only, no push/CI/deploy. Next C02 not started.

AUDIT-REMEDIATION-PLAN-20261104: owner-requested cycle list prepared.
87 findings mapped without omissions:50 current CRM cycles +13 conditional cycles.
Plan: docs/current/audit-remediation-cycles.md. First C01 protects isolated verification;
next C02 fixes analytics source permissions. No implementation started in this step.
Docs-only checks; own local save only, prior no-push/deploy boundary preserved.

FULL-AUDIT-20261104: file/static audit complete on d27044b1 + preserved WIP.
127843 paths;5734 own-text;941 backend modules/413 process modules;976 API operations,
17jobs;95routes/3014UI instances;1557 requirement traces. Registry checks PASS.
87findings=29prior+58additional; product defects/failed gates remain open.
Dynamic evidence is scoped:99 protected/external UI commands and6 environment
boundaries remain unaccepted; no release/native/live/production PASS.
Report: output/full-audit-20261104/report/README.md; final evidence/local-save
boundary in report/documentation.md. No product/workingDB/push/merge/deploy changes.

COMPREHENSIVE-AUDIT-20261103: executable audit complete on0b3348e1+preservedWIP.
Backend2752:2698PASS/4FAIL/50SKIP; PG50PASS on isolated repeat; original teardown
FAIL retained. Real recovery/AV PASS; HTTP2x50 each40success/10Clients timeouts.
Build/types PASS; Node215PASS/7FAIL; UI45+targeted flows. Findings include stale
auto-booking terms, missing creation effects/context, Clients latency, fallback,
Compose queues, money/D01 and historical native gaps. Report and ordered plan:
docs/testing/comprehensive-audit-20261103/README.md. No product fixes/workingDB writes.
Own docs/reports saved locally;4 active docs require foreignWIP context and are
preserved as own patch, not directly staged. No push/merge/deploy or production PASS.

CALENDAR-SHARED-20261103: approved picker reused across7 consumer areas and all26
Input date/datetime fields. Shared15/consumer8/browser/build/types/i18n6680/bundle PASS.
Antislop cursor finding fixed with owner approval. Published44a9c92e to origin/main;
remote SHA confirmed. CI41656489506: frontend PASS, backend FAIL (AI suggested-actions test:2<3). Evidence: docs/testing/evidence/calendar-shared-20261103.md.
No scoped code/evidence/publication remainder; foreign WIP retained, no deployment.

RECORDS-PERIOD-POPOVER-20261103: period calendar floats above content without
layout shift; visible guidance/presets removed for this picker. Desktop/mobile390,
range/apply/cancel/Escape/outside/nested Select PASS; safe build/types/i18n/bundle PASS.
No API/data change. Full evidence and publication boundary in PRIMARY.

VITE-CACHE-FIX-20261103: shared dev-page crash cause addressed by isolated
Vite caches/strict ports and noEmit for config. Node3, isolated build/types/i18n6667,
bundle and browser login/Dashboard/Clients/Calendar/Records PASS. Concurrent test
optimizer leaves working dev cache unchanged. Dev5173 restarted; working DB untouched.
Details and publication boundary in PRIMARY; unrelated WIP retained.

RECORDS-PUBLICATION-20261103: selected Records/VisitPlan/RF01–09 candidate verified.
Backend213/PG29/Node25/build/types/i18n6616/bundle and13 unique browser cases PASS
within evidence boundary. Report: docs/testing/evidence/records-publication-20261103.md.
Published6349acdf to origin/main; remote SHA confirmed. CI41620011747: frontend
success/backend in progress. Foreign WIP preserved; no working DB migration/deploy.

GIT-LOCK-20261103: stale empty index.lock removed after two process checks and
exclusive-open verification. Index SHA256 unchanged; staged diff empty. This supersedes
prior lock blockers below. Mixed task prerequisites still require scoped publication;
no commit/push performed. Current branch has no configured upstream.

RECORDS-REMEDIATION-20261103:9 audit findings fixed locally; styled inline period
calendar replaces modal. Quick reset persistence race also fixed. Node8/scoped
browser11+regression10/build/types/i18n6667 PASS in stated boundary. Evidence:
docs/testing/evidence/records-remediation-20261103.md. No workingDB writes/deploy.
Publication blocked by existing index.lock/mixed prerequisites; no commit/push.

RECORDS-FULL-AUDIT-20261103: component audit complete;9 findings(7P2/2P3), no fixes.
56 focused backend PASS;19 browser audit scenarios reproduce/inspect scoped behavior.
Report: docs/testing/evidence/records-full-audit-20261103.md.34 source hashes unchanged;
working DB untouched. Publication blocked by existing index.lock/mixed prerequisites.

RECORDS-SINGLE-ROW-20261103: one-row Records toolbar implemented; status dropdown,
filter count/dialog, icon sort/reset and navigation. Empty page was Today03.11 vs
10 demo appointments04.11; session-scoped selected period now survives menu return.
Real dev10 rows verified. Node7/browser7/build/types/i18n PASS. Evidence:
docs/testing/evidence/records-single-row-20261103.md. No DB writes this cycle.
Publication remains blocked by index.lock/mixed prerequisites; no commit/push/deploy.

RECORDS-COMPACT-DEMO-20261103: single-row header reference prepared (proposal only).
Owner explicitly chose current-business test data: Business2 Zani E2E Demo,
10 synthetic clients153–162 and appointments87–96 created for04.11.2026 09:00–14:00
Asia/Almaty via existing permission-checked API views/domain commands, atomic batch.
UI confirms10; prior4 preserved. Evidence/IDs/backup: output/records-compact-demo-20261103.
No product code/deployment; existing index.lock/mixed docs block publication.

RECORDS-TOOLBAR-20261103: approved Records references implemented locally. Compact
toolbar, draft/apply filters and dates, chips/reset, separate navigation/mobile statuses.
Node5 + browser6 RU/KK/EN + build/types/i18n PASS. Evidence:
docs/testing/evidence/records-toolbar-20261103.md. Publication blocked by existing
index.lock/mixed prerequisites; no own commit/push/CI/deploy.

APPOINTMENTS-UI-AUDIT-20261103: screenshot and scoped Records UI/UX audit complete.
Four findings: expanded-filter density/mobile result below fold, incomplete active
condition/reset overview, mixed navigation/status controls and oversized sorting.
Compared Clients/Calendar/Tasks; compact local toolbar + filter dialog proposed.
Report: docs/testing/evidence/appointments-ui-audit-20261103.md. No product changes.

RECORDS-BELL-FIX-20261103: both requested defects locally closed. Dev Records API200
and correct empty state after backend refresh; dev now autoreloads. Read-failure copy
and safe localized service-event keys implemented. Backend81 PASS/1 SQLite skip,
Node14, browser6+S03-1 and final Records3, build/types/i18n6666/bundle PASS.
Evidence: docs/testing/evidence/records-bell-fix-20261103.md. Publication remains
blocked by index.lock/mixed prerequisites; no own commit/push/CI/deploy.

HEADER-CLEANUP-20261103: service header indicator removed; Dashboard/Calendar
technical timezone/update captions removed. Header always fixed, desktop48/mobile56.
Build/types/i18n PASS; real-dev RU desktop/mobile/shared-layout checks recorded in PRIMARY.
Publication blocked by existing index.lock/mixed prerequisites; Records API404 remains separate.

ALERT-REMEDIATION-20261103: persistent service header indicator and contextual finance
reasons/links implemented; Client/Resource/Account/Bell fixes scoped-verified locally.
22 browser scenarios covered (20 completion PASS +2 login429 rechecks PASS), Node19,
final build/types/i18n6655/bundle PASS. Legacy S03 event-text remains FAIL due to
pre-existing personal projection; report: docs/testing/evidence/alert-remediation-20261103.md.
Publication blocked by index.lock/mixed prerequisites; no own commit/push/CI/deploy.

ALERT-AUDIT-20261103: source inventory and five isolated browser scenarios complete.
Five confirmed consumer defects; ServiceStatusNotice still shifts page content.
Evidence: docs/testing/evidence/alert-audit-20261103.md. Audit only, no product fixes.
Docs publication blocked by existing index.lock; no own commit/push/CI/deploy.

CRM-R01-PLANS-20261102: plans/undated steps and Appointment scheduling implemented
and scoped-verified locally. Backend128/PG23/cache1/build/types/i18n6650 and
RU/KK/EN browser PASS within evidence boundary; no money/D01/live closure.
Evidence: docs/testing/evidence/visit-plans-20261102.md. Publication blocked by
index.lock and dirty prerequisites; remote main now equals e02a28f5. No own
commit/push/CI/deploy or working DB migration. Next code: price versions/allocation.

RECORDS-WORKSPACE-20261102: first Records cycle implemented and scoped-verified locally.
Appointment list/card/pipeline and dependent consumers replaced; history retained.
Evidence: docs/testing/evidence/records-workspace-20261102.md. Backend/PG, final
build/types/i18n, Node21 and synthetic RU/KK/EN browser PASS within named boundaries.
Publication blocked by index.lock, foreign outgoing commit and dirty prerequisites.
No commit/push/deploy. Full R01 plans/money/D01/live acceptance remains open.

ALERT-COMPONENTS-20261102: solid four-tone notices/common bottom-right host implemented
and scoped-verified03.11. Toast/undo/network/Inbox, modal focus, timers/recovery,
RU/KK/EN and mobile checks PASS; real service form503/retry/save PASS.
Evidence: docs/testing/evidence/alert-components-20261102.md. Build/types/i18n PASS.
Publication blocked by pre-existing index.lock; actual remote main=HEAD e02a28f5.
No own commit/push/CI/deploy or working DB migration. Own isolated servers stopped.

ALERT-REFERENCES-20261102: Market alert specification analysed; three image references
prepared for desktop/mobile/form. Analysis and proposed CRM-specific clarifications:
output/crm-alert-references-20261102/ANALYSIS.md. Await owner visual approval before
implementation. Product code/Market/spec untouched; no app tests or deployment.

UIUX-FULL-20261102: original six anti-slop skills installed globally; hashes match
upstream941b1532. Comprehensive scoped UI/UX audit completed:14 findings (1P1/9P2/4P3),
coverage/limits, recommendations and evidence in docs/testing/uiux-full-20261102.md.
No product fixes/live writes. Own docs checks PASS; commit blocked by existing index
lock; push also includes foreign unpushed e02a28f5. No staging; audit servers stopped.

RECORDS-ROADMAP-20261102: first R01 delivery now explicitly Records page +
Appointment pipeline + full merchant Lead/Deal entrypoint/consumer replacement.
Plan/payment extensions follow. Existing data/history/API retained; no duplicate
Record entity or automatic conversion. Roadmap and CRM/frontend/acceptance aligned.
Docs checks PASS; no product implementation. Own publication still blocked by
prerequisite dirty docs; no foreign WIP staged. Supersedes prior plan-first next step.

PILOT-R01-CONTRACT-20261102: pilot scope corrected locally per owner annotations.
D02 exchange/C21 campaigns are future work; native belongs to second developer;
staff assistant D01 is mandatory. R01 technical draft added to current CRM contract;
no application implementation/runtime PASS yet. Positive package with zero base sum
awaits explicit policy choice; recommendation recorded. Docs/examples checks PASS.
Own publication blocked by prerequisite uncommitted docs; index empty, no push/deploy.

ROADMAP-STATUS-20261102: stale AUD/R01/dev-migration statuses reconciled locally.
Remaining work grouped by bounded existing-ID cycles in docs/current/roadmap.md;
implementation, evidence/publication, target/legal and deferred work separated.
Docs checks PASS. Publication blocked: own patch depends on pre-existing uncommitted
roadmap/acceptance sections absent from HEAD; no foreign WIP staged. Details in PRIMARY.

UI-ANTISLOP-20261102: project skill and bounded interface audit completed locally.
10 merchant screens inspected in RU; leads/calendar also390px, source review covers
shared states and selected localization paths.5 findings (4P2,1P3), coverage limits
and proposals in docs/testing/ui-purpose-audit-20261102.md. Skill/provenance/license,
manifest and docs checks recorded in PRIMARY. No product fixes, data writes or push.

UI-REFRESH-20261102: six owner-approved dev migrations applied with backups;
data/integrity checks PASS. Tariff500 resolved; leads idle/selection/draft stable
in representative browser checks. Original5–10s blink not definitively reproduced.
Dev5173/8000 remains running; no product-code changes or deployment. Evidence and
verification boundaries in PRIMARY checkpoint.

## REFACTOR-20261030 — итоговая проверка и публикация

Опубликовано в main до `368a3fa4`, включая Header/Calendar/Inbox.
P01–P18 завершены; дополнительный аудит и измерение запросов PASS.
[Roadmap](docs/current/roadmap.md), [evidence](docs/testing/evidence/refactor-20261030.md).
Эта запись заменяет прежние REFACTOR «not published»/bundle blockers ниже;
исторические проверки и статусы других задач сохраняются. P19 mapping завершён,
CRM-C21/live/release acceptance открыты. Чужой WIP сохранён.


> Решение владельца 14.10.2026: межчатовая координация, роли primary/UI,
> назначения writer, ожидание других чатов, автоматическая передача и связанные
> ограничения отменены. Применять актуальный AGENTS.md. Ниже сохранены сведения
> о задачах и evidence; прежние межчатовые назначения являются историей, а не
> действующими инструкциями. Продуктовый scope, результаты и блокеры сохраняются.

# PlatformaCRM — текущий статус

CRM-R01-RECORD-FIRST-20261031: single-Appointment Client/Inbox package published
bc46d7c9.02.11 continuation corrected notification preference fixture and dependency
audit blockers locally:31 backend/system/drift, app/widget/Storybook/types/XLSX and
npm audit0 PASS. Fix02e89c3b published, remote SHA confirmed; CI41437983420 success.
Full R01 plans/money/live remain open; foreign WIP preserved. Evidence in PRIMARY.

PILOT-ACCESS-20261031: two-Business onboarding/access verified and published43aab2fe.
Existing security fixes integrated; neutral signup and MFA error recovery corrected.
Focused/dependent suites, PostgreSQL12, build/types/i18n/Node12 and browser PASS.
Remote SHA confirmed; CI41134080952 success. Task servers stopped.
R02/R04/live/legal acceptance remains open; no working DB/deployment. Evidence in PRIMARY.

AUD-REMAINING-20261031: AUD12c history and bounded AUDV01 review verified locally.
Login-CSRF and automation authority fixed; owner-run policy retained. Build/types/
i18n, focused/dependent backend and RU/KK/EN browser PASS. Published0db46068;
remote SHA confirmed, CI41127057520 in progress.
Public-intake privacy fix is other local WIP, excluded from publication; live/release
acceptance remains open. No working DB/deployment. Evidence in PRIMARY.

AUD-12b-20261031: full server-filtered import history/page/size/current detail verified.
Backend27, Node12, system/drift/build/types/i18n and RU/KK/EN browser PASS.
Actor isolation/reload/503 retry/new import and modal page-size menu checked.
Published1b25694a, remote SHA confirmed; CI41118186023 in progress.
12c export history remains open.
No working DB/deployment; unrelated WIP preserved. Evidence in PRIMARY.

AUD-12a-20261030: mapping/re-preview/full row errors/correction and retry verified.
Backend50 union, Node5, system/drift/build/types/i18n and RU/KK/EN browser PASS.
Published f9a7a6c8, remote SHA confirmed; CI41112355081 in progress.12b/12c open.
No working DB/deployment; unrelated WIP preserved. Evidence in PRIMARY.

AUD-07-20261030: complete paginated automation history, status/trigger filters
and full server metrics verified. Backend40 union, Node10, system/drift,
build/types/i18n and RU/KK/EN browser503/retry/roles PASS. Published2a710d32,
origin/main SHA confirmed; CI41107592332 in progress.
Temporary servers stopped; cleanup of disposable DB directory blocked by policy.
No working DB/deployment; unrelated WIP preserved. Evidence in PRIMARY; AUD12 not started.

AUD-09-20261030: complete permitted service summary and appointment counts verified
locally on exact candidate. Owning16/dependent3, system/drift, build/types and
RU/KK/EN browser PASS; filters/error/retry/keyboard checked. Published1ac77023;
origin/main SHA confirmed, CI41103878148 queued (no green claim).
No working DB/deployment; unrelated WIP preserved. Scope/evidence in PRIMARY.
Next AUD07 not started.

REFACTOR-20261030: frontend extraction and routing/prefetch cleanup implemented
locally; final isolated frontend build and focused interaction checks PASS.
Existing notification/security WIP is preserved. Not committed or published;
the combined CRM/Market task still has Market bundle/verification blockers.
Exact scope and retained failures: REFACTOR entry in PRIMARY-SESSION.

AUD-08-20261030: paged server Client search and async Deal/Lead/Task selection
verified locally; optional business filter prevents mixing accessible businesses.
Exact candidate36 backend/14 Node/system/drift/build/forced types and targeted
browser RU/KK/EN PASS. Published d22cd337, origin/main SHA confirmed;
CI40962432948 in progress. No deployment/working DB changes.
Details and retained failures — AUD08 in PRIMARY. Next AUD09 not started.


OFFICIAL18-PUBLICATION-20261030: owner authorized minimal prerequisite and five existing
outgoing commits, then AUD10. Prerequisite-only28 and combined65 isolated tests PASS.
Only task-assignment service/API guard/tests included; unrelated WIP preserved.
No schema/env/working DB/deployment change. Receipt: OFFICIAL18-PUBLICATION in PRIMARY.


AUD-10-20261030: offline queue/replay/recovery locally verified and published
8d710f03; prerequisite OFFICIAL18 bae967bd. Both normal pushes/remote SHAs confirmed.
Combined65 backend, Node18, build/types/system/drift and targeted browser PASS.
CI40956811723/40957243699 completed success30.10. Canonical PlatformaCRM,
codex/ui-testing-toolkit; unrelated WIP preserved. No working DB/deployment.
Full boundary/commands/retained failures — AUD-10-20261030 in PRIMARY.


CI-REPAIR-20261029: candidate73/system/drift, frontend build/types/budget, resolver8
and npm/Python audits PASS. DRF3.18.3 closes three remaining advisories; unrelated
WIP excluded. Published acb8687e to origin/main; remote SHA confirmed.
CI40832440547 complete success; AUD19 follows separately.
Evidence: CI-REPAIR and AUD19-PUBLICATION in PRIMARY.


AUD-19-20261029: separate candidate on published CI-repair acb8687e verified.
Business resolution/field CRUD and More-menu editor: candidate80/system/drift,
build/types/i18n/options2 and RU/KK/EN desktop/mobile browser PASS. Reader role,
error recovery, keyboard/focus and key-pattern checks PASS; details in PRIMARY.
Published cd7a2598 to origin/main; remote SHA confirmed.
CI40835060335 complete success (backend/frontend); docs HEAD e9c1681b CI40835282538
also complete success. Verified29.10. No working migration/deployment.
AUD-10 proceeds separately below; other WIP preserved. CI-repair40832440547 complete success.

AUD-11-20261029: merge API now commits transfers, ledger/archive, history and request
audit together. Audit failure before/after insert rolls everything back; retry creates
one merge/audit/activity. Final isolated candidate54 tests/no skips, system/drift PASS.
Base692e46f0, canonical root, branch codex/ui-testing-toolkit; prior WIP preserved.
No schema/env/UI/deployment change. Scope complete; AUD-19 status is recorded above.
Exact commands, failed reproductions and candidate boundary in PRIMARY.
Published db0a4d9c to origin/main, remote SHA confirmed; CI40822054259 in progress.

YCLOUD-TPLITE-20261028,29.10: первый локальный этап реализован: серверное подключение
одного WhatsApp API-номера и текстовый обмен в существующем Inbox, подписанный durable
ingress, безопасные повторы и статусы accepted/unknown/sent/delivered/read. Проверки
backend, актуальных прав, порядка callbacks, PostgreSQL-гонок и readiness PASS;
RU/KK/EN desktop/mobile browser и frontend types/i18n/build PASS. Точные прогоны,
сохранённые падения и snapshot — в PRIMARY. Рабочих миграций, аккаунтов и отправок нет.
Проверенный код YCloud/OFFICIAL-03 опубликован в main: b6de2956; удалённый SHA
подтверждён, три согласованных предшествующих коммита включены. Прочий WIP сохранён.
CI40767943683 выполняется, зелёный CI не заявлен; детали — YCLOUD-PUBLICATION в PRIMARY.
R02/R03 live открыты; доступ TP Lite, target и реальная приёмка требуют владельца.

NOTIFICATIONS-SSE-20261029: local Redis + dedicated ASGI invalidation stream implemented
for owner/admin announcement monitoring. Two independent browser sessions update~1s;
restart resync/missed changes and subsequent events PASS (stalled proxy recovery~40s).
Backend105/PG3/Node10/system/drift/build PASS. Default off; no working config/DB or
deployment. Code/evidence scope complete; no commit/push/CI due to prior unpublished
foundation boundary. Canonical root, branch codex/ui-testing-toolkit HEAD98925b67+WIP.
Setup/limits in operations; commands/attempts/screenshot in PRIMARY checkpoint.

NOTIFICATIONS-REFRESH-20261029: receipt changes now invalidate feed/summary/detail
and announcement monitoring together. Node QueryClient2, build/types/i18n and isolated
browser page/bell read-all, single read, open/ack/unread PASS; updates observed within
0.9–2s including navigation, without60s wait. SQLite lock on one rapid fixture unread
retained; retry succeeds, no contention-fix claim. Local source only, no commit/push/CI
because prior unpublished WIP dependency remains. Details in PRIMARY checkpoint.

NOTIFICATIONS-PERSONAL working DB/UI,29.10: targeted migrations applied after backup;
legacy27 rows unchanged,21 exact recipients; integrity/system PASS. Owner-authorized
UI publication to6 participants, read/open/ack/unread and monitoring checked; test
announcement revoked, history retained, removed from personal feed. ORM proof agrees.
Observed read-all lag subsequently corrected by NOTIFICATIONS-REFRESH-20261029. Canonical
8000/5173, branch codex/ui-testing-toolkit HEAD98925b67 + WIP. No commit/push/CI;
worker heartbeat unavailable. Evidence and remaining boundaries in PRIMARY checkpoint.

NOTIFICATIONS-PERSONAL-20261028 — local scope verified 29.10.2026. Personal staff
feed and fixed-audience business announcements implemented; owner/admin-only publish,
revoke and named monitoring. Open/read/explicit acknowledgement are independent;
read-all never acknowledges. Backend affected255 initially had4 expectation/clock
failures; corrected4 PASS, unchanged251 reused; dependent49 PASS. Isolated migration1,
PostgreSQL concurrency3, system/drift, frontend types/i18n/app+widget builds and targeted
RU/KK/EN desktop/mobile browser flow PASS. Root PlatformaCRM, branch codex/ui-testing-toolkit,
HEAD98925b67 + preserved WIP + patch. No commit/push/working migration/deployment.
Code/evidence/owner-decision remainder: none in this scope. Environment/publication
remain separate; external staff channels/addressed groups are deferred. Exact commands,
failed attempts, hashes and screenshots: NOTIFICATIONS-PERSONAL-20261028 in PRIMARY.

OFFICIAL-21 / AUD-17, 28.10.2026: mark-all-read now checks current VIEW+UPDATE
per visible Notification and updates only the allowed subset, per owner decision.
Forbidden rows/timestamps, shared/TEAM policy and Inbox/bell filters are retained;
VIEW-only receives403 even on empty sets. Final62 isolated tests PASS, system/drift
PASS; independent review no findings. HEAD98925b67 + prior WIP + patch; local only,
no publication or PostgreSQL concurrency certification. Detailed checks and retained
failed attempts: OFFICIAL-21-20261028 in PRIMARY; plugin artifacts/mark-all-read.

FU-HIST-02, 28.10.2026: public intake no longer reports private contact membership
or CRM associations. Form duplicate_warning is a constant false compatibility field;
website client_id/lead_id are always null. Internal matching/evidence and fresh public
conversation UUID remain. Preview reports only conversation creation in RU/KK/EN.
Final106 isolated backend tests PASS (12 new); system/drift/syntax, actual frontend
consumer checks, i18n/types/app+widget builds PASS; independent review no findings.
HEAD98925b67 + prior WIP + patch; no publication/live certification. Details:
FU-HIST-02-20261028 in PRIMARY and plugin artifacts/public-intake-privacy.

OFFICIAL-03, 28.10.2026: WhatsApp webhook identity now survives authentication;
channel credentials cannot route events into another Business. All changes are
preflighted before business effects; signed status batches keep per-change routes,
Bot/Business targeting and separate payload copies. Final102 isolated tests PASS
(20 new), system/drift/syntax PASS; independent candidate review no findings.
Initial9/12 reproduction failures and one corrected compatibility regression retained.
HEAD98925b67 + prior WIP + patch; local scope closed, no publication/live certification.
Details: OFFICIAL-03-20261028 in PRIMARY-SESSION and plugin artifacts/whatsapp-binding.

OFFICIAL-22, 28.10.2026: ApprovalRequest decision evidence is immutable from creation;
generic PUT/PATCH cannot rebind commands/payload/expiry. Reason-only updates avoid stale
status overwrites. Exact approval, underlying rights and one-time execution retained.
Final17 regressions PASS;78 dependent tests PASS on unchanged source. Completion95 initially
had one wrong HTTP expectation; failed log retained, corrected focused check PASS.
System/drift/syntax/diff/integrity PASS; independent review no findings. Local scope closed
at HEAD98925b67 + WIP + patch, no publication/live certification. OFFICIAL-22 in PRIMARY.

OFFICIAL-13, 28.10.2026: appointment automation status now enforces NOTIFICATIONS VIEW
and current row scope before counts/top8; independent Client/Appointment visibility applies.
Calendar URL copies are rebuilt from a readable linked Appointment, closing detached/stale
link leakage. Final116 tests PASS (21 new), system/drift/syntax/diff/integrity PASS.
Independent reviewer issue reproduced and repaired; prior failed attempts retained.
Local scope closed at HEAD98925b67 + prior WIP + patch, no publication/live certification.
Details and retained artifacts: OFFICIAL-13-20261028 in PRIMARY-SESSION.

OFFICIAL-09, 28.10.2026: catalog Service writes now enforce current SETTINGS UPDATE
and shared-object branch access for import/manual paths. Existing inactive/archive
state retained; Service/event/audit rollback covered. Initial12 regression tests and
83 affected tests PASS; supplementary final19 PASS after correcting test expectations
to existing ownership/error contracts. System/drift/syntax/diff PASS; independent review
has no findings. Local scope closed at HEAD98925b67 + prior WIP + patch; no publication,
production or PG certification. Details/evidence: OFFICIAL-09-20261028 in PRIMARY-SESSION.


OFFICIAL-19, 28.10.2026: existing outreach role eligibility is now intersected
with current NOTIFICATIONS action/object decisions at all12 role-helper callsites.
CRUD uses CREATE/UPDATE and server-owned candidate; campaign actions and consent bulk
use existing MANAGE map/actual campaign or consent candidate. Explicit overrides and
OWN/TEAM/current membership apply before writes/domain calls. No new role eligibility
or Client-derived consent owner. Capability helper reused; notifications currently has
no module mapping/toggle, only injected disabled-boundary integration proof claimed.
BEFORE22:14 failing methods/17 security assertions,8 controls PASS. AFTER27 new tests
within98 affected and combined1095 PASS/no skips; syntax/system/drift/diff/reverse PASS.
HEAD98925b67 + WIP/18 prior closed packets + patch. Evidence OFFICIAL-19-20261028 and
output/security-remediation-20261028/outreach-mutation-permissions/fix-report.md.
No real delivery or production/PG/full browser certification.

OFFICIAL-18, 28.10.2026: Lead follow-up Task creation now validates the
resolved assignee with ordinary validate_assignment(creating=True) and checks TASKS
CREATE on the final unsaved Task, not on the source Lead. Current source Lead VIEW,
Business/module and archive/lock checks remain; direct service calls also enforce actor.
Wrong source-based TASKS guards removed for this action only. No TASKS UPDATE required,
default/null/unassigned behavior retained where normal creation policy permits.
BEFORE20:8 security gaps,2 false denials,10 controls. AFTER28 new tests within113
affected and combined1068 PASS, zero skips; syntax/system/drift/diff/reverse PASS.
HEAD98925b67 + WIP/17 prior closed findings + patch. Evidence OFFICIAL-18-20261028
checkpoint and output/security-remediation-20261028/lead-task-assignment/fix-report.md.
Local assignment-boundary proof only; generic replay/production/PG not certified.
This is OFFICIAL-18, unrelated to already-closed historical AUD18 export.

OFFICIAL-17, 28.10.2026: Client import writes now distinguish current UPDATE
for existing matches (including archived/no-op) from CREATE for new Clients, under
the existing object policy. Shared Client notes write rule is reused by API/import;
proposed fields are validated before mutation. Client/Lead/Deal sheets use the same
Client boundary/current request actor; legacy direct row calls use job.actor, no actor
fails closed. Fill-only matching, duplicate warning, archive state and atomic rollback
remain. Existing ImportJob CREATE admission remains, not an update-only upload feature.
27 new tests within103 affected and combined1040 PASS/no skips; syntax/system/drift/
diff/reverse PASS. HEAD98925b67 + previous WIP/16 closed findings + patch, local only.
Evidence OFFICIAL-17-20261028 checkpoint and output/security-remediation-20261028/
client-import-update-permission/fix-report.md. Current OWN/TEAM UPDATE semantics for
unowned Client retained exactly; no new ownership rule or production certification.

OFFICIAL-15, 28.10.2026: no_change to production code. Current FU-BE-02
already passes actor into CRM-card Task previews and uses it for linked-field masking,
relations/actions; missing actor fails closed. Dedicated12 new regressions cover all
four card routes, forbidden/allowed fields, scalar/list/request/actor, OWN/TEAM/current
rights, Client aliases, parent task/specialist and Business/capability controls.
Current-tree initial11 PASS; final owning131 and combined1004 PASS, zero skips;
syntax/system/migration drift/diff PASS. HEAD98925b67 +15 prior fixes/WIP + tests/docs.
Evidence OFFICIAL-15-20261028 checkpoint and output/security-remediation-20261028/
task-preview-context/fix-report.md. Local scoped closure of an already-remediated
finding; no new functional patch, generic replay or production certification.

OFFICIAL-10 Inbox scope, 28.10.2026: create-action responses now require current
child VIEW/scope/capability and same Business before returning CRM data. Without VIEW,
writes still succeed but direct responses acknowledge read_restricted without record
fields; pipeline child fields are null, created flags unchanged. Task/Appointment keyed
replies reserialize current resource under current actor, never replay old DTO blindly.
Stored receipts, creation/dedup/locking/status unchanged; known metadata ID copies also
guarded. Pending booking without saved Appointment keeps its offered slot.
BEFORE17:15 security failures,2 controls. AFTER20 new tests within75 affected and
combined992 PASS, zero skips; syntax/system/drift/actual frontend consumers/
i18n/types/build PASS. HEAD98925b67 + WIP/fourteen prior fixes + patch. Evidence:
OFFICIAL-10-INBOX-20261028 checkpoint; output/security-remediation-20261028/
inbox-create-read-visibility/fix-report.md. Local scoped proof, not production PASS.

OFFICIAL-16, 28.10.2026: Lead duplicate-check details now pass existing LEADS
VIEW/object scope/capability and Business filtering BEFORE LIMIT5. Hidden rows return
no IDs/messages/status/source; optional restricted-match boolean preserves generic
duplicate warning without private count. Client projection reuses BE02/BE03: no hidden
Client FK or contact lookup/exclusion derived from an unreadable Client ID.
LeadForm preserves allowed counts/self-only editing and generic create-anyway warning,
clearing restricted state on error/no selection. No new endpoint permission or writes.
BEFORE10 security failures +5 controls after timestamp-fixture correction. AFTER15
new tests within86 affected and combined957 PASS, zero skips; syntax/system/
drift/component/i18n/types/build PASS. HEAD98925b67 + WIP/thirteen prior fixes + patch.
Evidence OFFICIAL-16-20261028 checkpoint and output/security-remediation-20261028/
lead-duplicate-visibility/fix-report.md. Local synthetic only; OFFICIAL10 remains open.

FU-BE-03, 28.10.2026: Client duplicate details now require current Client VIEW,
object scope, capability and same Business. CREATE-only keeps one non-identifying
warning for hidden matches; exclude_client_id cannot suppress an unreadable match.
Shared read projection covers Client check/Inbox warning and stored import snapshots,
plus the same DTO copies in form submissions/activity. Current reader used on every
read; stored evidence, matching/import writes and public warning semantics unchanged.
UI keeps duplicate banner/confirmation/create-anyway, no hidden open/merge target.
BEFORE18 security assertions across11 methods +2 reproduced snapshot copies; five
baseline controls PASS after fixture corrections. AFTER20 new tests within136 affected
and combined942 PASS, zero skips. Syntax/system/drift/component/i18n/types/build
PASS. HEAD98925b67 + WIP/twelve prior fixes + patch. FU-BE-03-20261028 checkpoint;
output/security-remediation-20261028/client-duplicate-visibility/fix-report.md.
Local synthetic evidence only. OFFICIAL16/10 remain separate and unclosed.

FU-BE-02, 28.10.2026: linked Client projections now apply existing CLIENTS VIEW,
object scope, capability and same-Business policy. Readable parent records remain;
hidden Client IDs/contact labels and typed copies are masked in serializers, CRM-card,
history, queues, AI context/rules, outreach previews/evidence and CSV. Contact-search and exact Client-ID filter
branches respect Client visibility; stored Lead/Deal export fingerprints include it.
Actor context is explicit; no actor fails closed. Frontend accepts nullable links,
retains generic placeholders and avoids null-equality joins. No new ownership rule.
BEFORE22:61 failing assertions across18 methods,4 controls PASS after fixture correction.
Focused25 PASS; final27 plus affected history/card suites 105 PASS; combined
894 PASS without skips. Syntax/system/drift/component/i18n/types/build PASS.
HEAD98925b67 + prior WIP/eleven fixes + this patch. Evidence FU-BE-02-20261028 in
PRIMARY and output/security-remediation-20261028/client-pii-projections/fix-report.md.
Local synthetic evidence only; no production/provider/browser-E2E certification.

OFFICIAL-05, 28.10.2026: unverified public form/chat flags no longer replace
existing per-channel OPTED_OUT. Common record_explicit_consent creates absent rows
and conditionally updates only non-OUT rows at SQL write, then refreshes existing
result. Refusal evidence/timestamps retained; normal intake/new/UNKNOWN/IN unchanged.
Existing inbound START and authorized management re-consent remain separate and PASS.
BEFORE15 security failing assertions across7 methods; corrected existing404 denial
control PASS before source patch. AFTER106/combined654 PASS without skips;
syntax/system/drift PASS. HEAD98925b67 + WIP/ten prior fixes + patch. Evidence:
OFFICIAL-05-20261028 in PRIMARY; output/security-remediation-20261028/
public-intake-optout/fix-report.md. Only local synthetic consents, no actual sends.

OFFICIAL-11, 28.10.2026: consent XLSX now uses existing bounded core reader
after actual upload max+1 byte check. ZIP expansion/entries/ratio and XML/worksheet
bounds run before openpyxl; rows stream to unchanged consent normalizer, with explicit
file errors and iterator/workbook cleanup. No eager worksheet list or silent trim.
Existing aliases, values, active sheet/cached formulas, CSV and consent rules retained.
BEFORE18:14 failing assertions across10 methods, one old underreported-dimension
error,7 controls PASS. AFTER52/combined551 PASS without skips; syntax/system/drift
PASS. HEAD98925b67 + WIP/nine previous fixes + patch. OFFICIAL-11-20261028 in PRIMARY;
output/security-remediation-20261028/consent-xlsx-limits/fix-report.md.
Only synthetic tiny fixtures/mocks; no stress/production or publication claim.

OFFICIAL-12, 28.10.2026: alternate Deal readers now share existing sensitive
amount policy (owner/admin/manager/accountant or BILLING VIEW as already defined).
CSV/queues/summary/typed activity metadata/CRM timeline/AI rule sources/Deal-value
analytics mask denied monetary fields and derivatives; actor context explicit.
Amount filters/order denied before use; stored Deal export fingerprint includes
field access. Missing context fails closed. Nullable frontend types and two money
helpers show existing '-' for hidden values, preserving ordinary numeric formatting.
BEFORE30 failing assertions across15 methods,3 controls PASS (see fixture correction
in checkpoint); AFTER18+3 supplemental controls,19 unique methods PASS; combined
523 PASS without skips. Syntax/system/drift, i18n/types/main Vite build PASS.
HEAD98925b67 + WIP/eight prior fixes + patch. OFFICIAL-12-20261028 in PRIMARY-SESSION;
output/security-remediation-20261028/deal-amount-projections/fix-report.md.
Local synthetic evidence only; no provider/production/publication certification.

OFFICIAL-02, 28.10.2026: legacy analytics intersects source Lead/Deal/
Appointment/Task VIEW, object scope and capability before counts/grouping/sums.
Reuses existing analytics _scoped in manager metrics, dashboard and legacy summary/
CSV. Member boundary and permitted formulas retained; Lead-to-Deal conversion also
requires a readable Lead without changing the historical reporting-period formula.
BEFORE15:13 failing assertions across10 methods,5 controls PASS; AFTER38/combined
375 PASS without skips, syntax/system/migration-drift PASS. HEAD98925b67 + WIP/
seven prior fixes + patch. OFFICIAL-02-20261028 in PRIMARY-SESSION; evidence in
output/security-remediation-20261028/analytics-resource-visibility/fix-report.md.
Scoped local synthetic evidence only; no production acceptance or publication.

OFFICIAL-07, 28.10.2026: ensure_default_roles now initializes absent presets
only; onboarding never overwrites existing role metadata, activation, JSON, denies,
scope or permission rows. Initialization of a new role is atomic. Explicit audited
TEAM MANAGE permission editing remains separate; no reset API/permission added.
Corrected BEFORE12:11 failing assertions across10 methods,2 controls PASS;
AFTER23/combined316 PASS without skips, syntax/system/migration-drift PASS.
HEAD98925b67 + preserved WIP/six prior fixes + patch. OFFICIAL-07-20261028 in
PRIMARY-SESSION; output/security-remediation-20261028/onboarding-preset-preservation/
fix-report.md. Local isolated synthetic evidence only; no publication/live acceptance.

OFFICIAL-04, 28.10.2026: Notes reads now intersect inherited tenant/Clients
access with the linked record's current VIEW/object scope using existing
scope_entity_history before pagination and serialization. Hidden recognized links
return404 for detail and inherited object actions; ordinary CRUD, archived/unlinked
history and existing non-CRM/system policy remain. BEFORE13:21 failing assertions,
4 controls PASS; inherited archive baseline1 failed. AFTER23/combined270 PASS without
skips; system/migration-drift and syntax/diff PASS. HEAD98925b67 + preserved WIP/five
prior fixes + this patch. Evidence: OFFICIAL-04-20261028 in PRIMARY-SESSION;
output/security-remediation-20261028/notes-linked-object-access/fix-report.md.
Local synthetic SQLite only, no production/live acceptance or publication.

28.10.2026. OFFICIAL-06: outreach рендерит только flat named variables без Python
format expansion; input≤16384/output≤65536 символов, ошибка вместо обрезания.
Stored personalized text проверяется по размеру при записи/launch; braces остаются
данными. BEFORE13:20 FAIL,3 controls PASS; AFTER ordered13/совместно184 PASS без skip,
system/drift PASS. Версия 98925b67 + WIP/patch; OFFICIAL-06-20261028 в checkpoint.
Реальных отправок/публикации нет. Следующий независимый finding: OFFICIAL-04.

28.10.2026. OFFICIAL-08: pricing offer сверяет эффективный сохранённый/входящий
Business с rule при PATCH; recommendation/autopilot readers исключают legacy чужие
строки. Валидные create/PUT/PATCH/relink и audit сохранены. BEFORE13:7 FAIL,6 controls
PASS; AFTER focused13/совместно171 без skip, system/drift PASS. Версия 98925b67 +
WIP/patch, без публикации; команды — OFFICIAL-08-20261028 в checkpoint. Реальные
строки не исправлялись, auth/reset/AUD-17/Business.status не затронуты.

28.10.2026. OFFICIAL-20: readiness выводит признаки настроенности вместо raw
broker/origin/provider URL; malformed broker даёт failed-check без исходного текста.
Ключи, статусы и инструкции сохранены. BEFORE synthetic markers присутствовали в
API/CLI; AFTER focused9/совместно135 PASS без skip, system/drift PASS. Версия
98925b67 + сохранённый WIP/patch; команды — OFFICIAL-20-20261028 в checkpoint.
Реальная конфигурация/провайдеры и auth/reset не проверялись; публикации нет.

28.10.2026. FU-BE-01: invitation token/invite_path маскируются без текущего
TEAM MANAGE конкретного Business, включая отсутствие request context. До фикса
TEAM VIEW позволил создать новый аккаунт с паролем атакующего и назначенной ролью.
После: focused11 PASS, совместно174 PASS + 3 PG-only skip, system/drift PASS.
Легитимные share/create/accept/reissue сохранены. Версия 98925b67 + WIP/patch,
без публикации; детали — FU-BE-01-20261028 в текущем checkpoint. Старые bearer
не отзываются этим изменением; AUD-17/Business.status и другие findings отдельно.

28.10.2026. OFFICIAL-01: generic DELETE Business отключён (405); связанные данные
сохраняются, существующие create/read/update и audit не изменены. BEFORE: member
204 с каскадным удалением; AFTER focused8/affected163 PASS + 3 PG-only skip, system/drift PASS.
Локальный dirty snapshot на 98925b67, без commit/push/deploy. Команды и границы —
OFFICIAL-01-20261028 в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).
AUD-17, Business.status и остальные находки этим пакетом не закрываются.

27.10.2026. AUD-18 выполнен в локальном scope: готовый экспорт сверяет fingerprint
текущих прав/scope, команды и филиалов; отчёты — также исходных ресурсов.
Legacy/изменённый контекст требует нового экспорта; notes redaction сохранена.
Affected71 без skip, system/migration drift PASS. Версия, ограничения, команды
и публикация — AUD-18-20261027 checkpoint. Рабочая БД/deployment не затронуты;
следующий AUD-17 не начат.

23.10.2026. UI-FOCUS-20261023: общая подсветка фокуса различает мышь/касание
и клавиатурную навигацию, включая /login, формы, таблицы и виджет. DOM focus,
ввод и ошибки сохранены. Browser12 (RU/KK/EN, desktop/mobile, axe), login-policy15,
build/widget/bundle PASS. Команды, ограничения и публикация — UI-FOCUS-20261023
в checkpoint. Рабочая БД и deployment не затронуты.

21.10.2026. AUD-22 выполнен в локальном scope: ZIP/XML bounds до openpyxl,
потоковое XLSX чтение без обрезания по заниженным dimensions и finally cleanup.
Focused10/affected68 без skip, system/drift и probe256МБ/12сек PASS. Лимиты всех
листов — operations; версия/публикация/evidence — AUD-22-20261021 checkpoint.
Рабочая БД/deployment не затронуты; следующий AUD-18 не начат.

21.10.2026. AUD-21: конкурентный confirm/rollback/recovery проверен в изолированном
PostgreSQL17: 48 import-проверок без skip, system/drift PASS. После сбоя строки
или финального audit ожидающий confirm создаёт один результат, повтор отклоняется.
Код AUD-16 достаточен; добавлены regression tests. Основа3834922c; команды,
версия и публикация — AUD-21-20261021 checkpoint; опубликован66b3f64a, CI39596573384 success. AUD-22 — отдельный этап выше.

21.10.2026. AUD-20: начальное состояние API/import заявок/сделок и подтверждённый
AI create исправлены, история не дублируется. Объединённый код/lock 4056a471
опубликован в main; remote SHA подтверждён. Vite8.1.6/follow-redirects1.16.1,
Pillow13/certifi2026.10.19; npm/pip audits чистые. AI19/affected214,
accounts/API128 (3 PG-only skip), system/drift, frontend build/bundle, policy6
и браузер PASS. [Полный CI кода](https://github.com/999MAX20/PlatformaCRM/actions/runs/39590140960)
— отдельный результат на точной версии. Подробности/ограничения — AUD-20-20261021
checkpoint. AUD-21/22 проверены отдельными этапами выше; CRM-D01 и deployment не начинались.

21.10.2026. PROJECT-DEEP-AUDIT-20261020 остановлен владельцем. Остановка ожидания
в чате не сняла running в плагине; отмена подтверждена через плагин 21.10,
активных проходов 0. Сохранён частичный отчёт с 18 записями, без завершённого
независимого прохода и без сопоставления с AUD. Полного security PASS нет.
Прежний [снимок 19.10](docs/testing/security-audit-20261019-partial/README.md)
с 36 записями сохранён отдельно. Новый скан не запущен. Daybreak 21.10: доступ
не предоставлен; настройка локальных прав не заменяет одобрение аккаунта.
Путь нового partial и детали — DOCS-PILOT-PRODUCTION-20261021 в checkpoint.

21.10.2026. По поручению владельца сверены текущие контракты, паспорта и roadmap;
описание закрытого пилота для нескольких стоматологических бизнесов и целевой
production V1 — в [продуктовом документе](docs/current/product.md).
Основа ce2c290d опубликована, CI 39305184796 success. Новая сверка документационная:
runtime, рабочая БД и deployment не менялись; живой пилот и production не приняты.
Исправлены устаревшие статусы AUD-15/billing; links/anchors/registry и diff hygiene
PASS. Полный scope, остатки и checks — DOCS-PILOT-PRODUCTION-20261021 в checkpoint.

19.10.2026. По поручению владельца [текущие записи Deep Scan](docs/testing/security-audit-20261019-partial/README.md)
сохранены в репозитории: отчёт, 36 записей findings с повторами, coverage, threatmodel,
manifest и контрольные суммы. Результат canceled/partial, не полный аудит.
Сохранение опубликовано в ce2c290d, CI success. Последующий запуск 20.10
также остановлен, его отдельный результат указан выше; runtime fixes не выполнялись.

19.10.2026. PROJECT-RISK-REVIEW: Deep Scan остановлен по явному поручению владельца
в 23:34 Asia/Qyzylorda. Активных проверок 0; один полный независимый проход завершён,
остальные отменены. Сохранён частичный отчёт инструмента с 36 findings; они ещё не
сопоставлены с AUD и не означают 36 новых дефектов. Аудит этим не закрыт;
последующий запуск 20.10 и его отмена описаны выше.
Причина длительности: многопроходная конфигурация (4 параллельно, до 40, лимит 96 ч),
а не зарегистрированная ошибка. Детали и путь отчёта — PROJECT-RISK-REVIEW checkpoint.

19.10.2026. PROJECT-RISK-REVIEW: по поручению владельца подготовлен
[единый анализ дефектов и рисков](docs/testing/project-risk-register-20261019.md)
из AUD и обсуждений PlatformaCRM UI / PlatformaCRM 2. Закрытые AUD сохранены,
CI/архитектура/эксплуатация/решения отделены от security findings. Назначенный тогда
повторный аудит SQL/HTTP/API/файлов/аватаров не завершён; последующие остановки
описаны выше. Runtime fixes и AUD-20 не начаты.

19.10.2026. AUD-16 выполнен полностью в согласованном локальном scope: защищены
служебные поля/история ImportJob, mapping только через preview, confirm под
блокировкой с повторной проверкой. SQLite112 PASS, 2 PG-only skip; PostgreSQL17
PASS, system/migration drift PASS. Ошибка test label исправлена отдельными
проверками, детали — checkpoint AUD-16-20261019. Roadmap, контракты, паспорта
согласованы. AUD-10/21 частичны с явным остатком. Commit/push/CI — итог задачи;
deployment не выполнен. Следующий AUD-20 не начат.

19.10.2026. Статусы результата аудита: выполнено полностью / выполнено частично /
не выполнено. AUD-01/02/03/13/14/15/06/04/05 выполнены полностью в согласованных
локальных scope; AUD-10 частично, остаток указан в roadmap. Исправлено устаревшее
открытие AUD-05 в capabilities. AUD-05 опубликован `4a13153c`; CI39284791120
при проверке queued, не объявлен зелёным. После сверки разрешён AUD-16;
checkpoint AUD-16-20261019.

19.10.2026. AUD-05 закрыт в локальном scope: редактор существующего правила,
preview/update и полный сценарий до одной реальной задачи. Focused30, affected153
(150 PASS, 3 PG-only skip), helpers4, system/migration drift, browser RU/KK/EN
desktop/mobile, build/types/i18n/bundle PASS. Scope/команды — checkpoint AUD-05-20261019;
commit/push/CI — итог задачи. Deployment не выполнен. AUD-16 выполнен отдельно выше.

19.10.2026. AUD-04 закрыт в локальном scope: атомарное создание/замена состава
автоматизации и истории; защита активного состава при конкурентных изменениях.
Focused26 PASS; affected208: 205 PASS, 3 PG-only skip; PostgreSQL29 PASS,
system/migration drift PASS. Scope/команды — checkpoint AUD-04-20261019;
commit/push/CI — итог задачи. Deployment не выполнен. AUD-05 закрыт отдельно выше.

19.10.2026. AUD-06 закрыт в локальном scope: общая проверка действий в
preview/save/activate/execute, предметная форма, ошибки RU/KK/EN и актуальность preview.
Focused14 PASS; affected207: 206 PASS, 1 PG-only skip; system/migration drift,
browser desktop/mobile, build/types/i18n/bundle PASS. Версия/команды/границы —
checkpoint AUD-06-20261019; commit/push/CI — итог задачи. Deployment не выполнен.
AUD-06 опубликован `046c83bf`, CI success. Продолжение AUD-04 отражено выше; UI-редактор AUD-05 закрыт отдельно выше.

19.10.2026. Сверка AUD-01/02/03/13/14: закрытие соответствует коду и evidence,
все пять опубликованы в main, CI success. Сводка roadmap актуализирована.
AUD-15 закрыт локально: Business/pipeline связи стадий и переходов защищены;
перенос существующей стадии через generic API запрещён. Focused12/affected158,
system/migration drift PASS. Scope/команды — checkpoint AUD-15-20261019;
commit/push/CI — итог задачи. Deployment не выполнялся. Продолжение AUD-06 отражено выше.

17.10.2026. AUD-14 закрыт в локальном scope: история сообщений неизменяема,
входящий текст ограничен parent permissions; delivery поля управляются сервером.
Focused15 PASS; affected288: 286 PASS, 2 PG-only skip; новый concurrent intake на
PostgreSQL17 PASS; system/migration drift PASS. Scope/команды/ограничения —
checkpoint AUD-14-20261017; commit/push/CI — итог задачи. Deployment не выполнен.
Следующий незакрытый пункт AUD-15 не начат.

17.10.2026. AUD-13 закрыт в локальном scope: PATCH/PUT проверяют UPDATE исходного
объекта; переназначение заявки использует сервис с атомарной историей/уведомлениями.
Focused13 PASS; affected324: 323 PASS, 1 PG-only skip; system/migration drift PASS.
Scope, версия, команды и пропуск — checkpoint AUD-13-20261017; commit/push/CI —
итог задачи. Deployment не выполнен; продолжение — AUD-14.

17.10.2026. AUD-03 закрыт в локальном scope: Client.notes защищены общей field policy
в API/карточках/сегментах/экспорте; пустой masked edit сохраняет данные, готовый CSV
проверяет текущую роль. Focused9 и affected199, system/migration drift PASS.
Версия, scope и проверки — checkpoint AUD-03-20261017; commit/push/CI — итог задачи.
Deployment не выполнен; продолжение — AUD-13.

17.10.2026. AUD-02 закрыт в локальном scope: notes/activity проверяют связи и
авторство; формы — допустимого ответственного; submission/error API/admin read-only.
Affected/dependent 112 PASS, финальные focused17 PASS, system/migration drift PASS.
Scope, ограничения, версия и команды — checkpoint AUD-02-20261017; публикационная
квитанция — итог задачи. Deployment не выполнен; продолжение — AUD-03.

17.10.2026. AUD-01 закрыт в локальном scope: offline-кэш/очередь изолированы по
пользователю/Business/правам, очищаются при завершении сессии; empty/denied/loading
и recovery проверены. Storage9, desktop/mobile browser, build/types/i18n/bundle PASS.
Остальные критерии AUD-10 открыты; продолжение — AUD-02. Версия, команды,
граница и публикационная квитанция — checkpoint AUD-01-20261017 и итог задачи.

17.10.2026. PROJECT-AUDIT: оформлены 20 подтверждённых пунктов и два риска на
проверку. [Единый roadmap](docs/current/roadmap.md#project-audit-20261017) содержит
порядок, критерии и правила изменения статуса; [evidence](docs/testing/project-audit-20261017.md)
разделяет API/browser, source и непроверенное. Ход исправлений — AUD roadmap;
исходный security scan завершён с partial coverage, не полная сертификация.
Документационная проверка/публикация — checkpoint PROJECT-AUDIT-20261017.

16.10.2026. Этап6: завершена согласованная локальная приёмка ADMIN-01–04
и реализованной основы ADMIN-05 — SCOPED PASS. Проверена цепочка обращение/карточка →
диагностика → действие → результат → история. Незакрытые пункты ADMIN-05
оставлены на потом; полный этап6 пока не закрывается. Scope — checkpoint
PLATFORM-ADMIN-ACCEPTANCE-20261016.

16.10.2026. ADMIN-05: владелец поручил основную логику перевода/карты и 5a/5b.
Основная логика реализована; полный этап НЕ выполнен. Продавец/банк/эквайер, цены/периоды, документы,
третьи лица и возвраты/переплаты отложены. Рабочие платежи не включаются;
PostgreSQL/concurrency, целевые browser desktop/mobile/RU/KK/EN и build PASS.
Коммит/push/фактический CI — итоговая квитанция; рабочая billing0006 отдельно.
Scope/проверки/остаток — checkpoint ADMIN-05; исходные предложения — спецификация15.4.


16.10.2026. BUSINESS-LOGIC-QUESTIONS: вопросы разделены на две категории:
10 для совместной аналитической проработки и 15 для решений владельца/партнёров.
[Документ](docs/testing/business-logic-questions-20261016.md) учитывает уже принятые
полномочия ADMIN-04; рекомендации не утверждены, runtime не менялся.

16.10.2026. ADMIN-04 реализован: инспектор доступа сотрудника/приглашений,
Business-scoped исправления, обе platform-роли + MFA/обращение и личное согласие
владельца для восстановления/роли/перевыпуска. Аккаунт, специалист и история сохранены.
PostgreSQL/concurrency/поддержка, browser6, build/types/i18n/bundle PASS;
commit/push/CI — итоговая квитанция задачи. Рабочая businesses0013 отдельно,
глобальный unlock исключён. ADMIN-05 отдельно поручен выше. Evidence — checkpoint ADMIN-04.


16.10.2026. DOCS-RECONCILIATION: [действующие техдокументы и roadmap](docs/testing/docs-reconciliation-20261016.md)
сверены с dc1eedf. ADMIN-01/02/03 опубликованы; CI первых двух success, ADMIN03
на момент сверки выполняется. Исправлены MB/права/среда/старые push-блокеры;
остаток закрытых этапов и функциональные gaps Подключений записаны в roadmap.
Введено обязательное описание сделанного/остатка и обновление профильных техдоков.
Только документация; новые этапы/рабочие миграции не начаты. Проверки — checkpoint.
Старые записи о блокировке push ниже относятся к своим историческим snapshot.

16.10.2026. BUSINESS-LOGIC-QUESTIONS: по поручению владельца сохранены
[25 вопросов для обсуждения](docs/testing/business-logic-questions-20261016.md).
Сценарии связаны с существующими acceptance IDs; рекомендации не утверждены,
новая реализация не запущена. Документ зарегистрирован как аналитический материал.
Проверки и граница публикации — checkpoint BUSINESS-LOGIC-QUESTIONS-20261016.

16.10.2026. ADMIN-03 реализован и локально проверен: обе platform-роли + MFA,
обращение/идентификация, подтверждение владельца для сотрудника, новая почта,
пароль и атомарный отзыв прежних credentials. PostgreSQL affected/dependent,
concurrency3, browser4, build/types/i18n/bundle PASS; ошибки попыток — checkpoint.
Рабочая accounts0011, адрес поддержки и реальная доставка отдельно; новый этап
не начат. Commit/push/CI — итоговая квитанция задачи.

16.10.2026. ADMIN-02 реализован и прошёл локальную приёмку: передача бизнеса
активному участнику с двумя личными подтверждениями, platform_admin + MFA,
обращением и атомарным аудитом/отзывом сессий. Прежнему владельцу выбирают роль
сотрудника либо отключение только этого Business. PostgreSQL154, concurrency3,
browser4, build/types/i18n/bundle PASS. Recovery без прежнего владельца исключён;
рабочие миграции не применялись. Commit/push и фактический CI — следующий шаг;
границы, ошибки прошлых попыток и команды сохранены в checkpoint.

16.10.2026. По явному поручению владельца опубликована вся накопленная цепочка
до f7d74d5 normal push в main; удалённый SHA подтверждён. Прежние ограничения
публикации ниже сняты этим поручением. Общий static gate от c7e26f6 PASS.
CI38795538634 запущен; итог CI проверяется в текущей задаче. Новые продуктовые
этапы, рабочие миграции и деплой этим действием не выполнялись.

16.10.2026. CONNECTION-RECOVERY: исправлено восстановление после фоновой вкладки
и связь успешной проверки API с восстановлением сессии; public probe независим
от токена. Новые регрессии воспроизведены до правки; browser29 PASS/11 штатных
skip, policy9, build/types/i18n/bundle PASS. Scope/evidence — checkpoint.
Локальный коммит только этой задачи; push блокируют8 прежних outgoing-коммитов.
Чужой ADMIN-01 WIP сохранён; live/CI приёмка не объявляется.

16.10.2026. PLATFORM-ADMIN-01: локально реализованы вкладка реквизитов и отдельный
GET/PATCH API: обе platform-роли, MFA, обращение/причина, revision и атомарный аудит.
Блокер PostgreSQL-приглашений исправлен; финальные82 backend и4 browser flows,
system/schema PASS. Build/types/i18n/bundle PASS переиспользованы на неизменённых
входах. Подготовлен проверенный локальный коммит; push блокируют прежние чужие
outgoing6e1bd46/834656b. Демостенд5185/API8015 без миграций/seed; детали — checkpoint.

15.10.2026. PLATFORM-ADMIN-01-CONTRACT: подготовлен этап0 согласованного плана.
Сверены поля/сервисы/API/MFA/аудит, проект контракта реквизитов — раздел15.8
спецификации. Владелец согласовал обе platform-роли, свежий MFA, основание
и аудит без grant. Самостоятельная правка реквизитов бизнесом пока не ограничена.
Следующий результат — реализация ADMIN-01; код и runtime-права ещё не менялись.

15.10.2026. PLATFORM-ADMIN-CAPABILITIES: в существующую техническую спецификацию
/platform добавлен раздел 15 — полное покрытие и административное управление.
Владелец согласовал первые пять сценариев: реквизиты, передача владельца,
почта/доступ, проблемы сотрудника, подписка по подтверждённой оплате.
Инспектор оплаты read + explicit actions описан как проект; новые права и код
не реализованы. Проверки документации и граница публикации — в checkpoint.
Пояснение read + explicit actions дополнено разделом15.7; предложенный порядок
реализации пяти сценариев, зависимости и критерии готовности записаны в roadmap.

15.10.2026. PLATFORM-REFERENCE-REDESIGN: проанализированы шесть референсов и
реализованы все шесть компоновок Обзора, Бизнесов, CRM, Поддержки и Операций.
Scoped browser, build/types/i18n/bundle и static/system/schema PASS; backend не менялся.
Код b4ee81a зафиксирован локально на codex/ui-testing-toolkit.
Анализ, проверки и исправления — в текущем checkpoint. Публикация блокируется
предшествующим чужим коммитом; редизайн доступен на локальном демостенде.

15.10.2026. PLATFORM-DIAGNOSTICS-01: первый этап реализован и локально проверен.
Ошибки подключений согласованы между счётчиками и очередями; стенд дополнен
историей, устаревшими наблюдениями и восстановлением. 77 tests PASS, 1 SQLite skip,
system/schema, build/types/i18n и API/UI PASS. Права CRM не расширены.
Публикация блокируется предшествующим чужим commit; детали — checkpoint.
Компактная компоновка реализована в PLATFORM-REFERENCE-REDESIGN выше.

15.10.2026. PLATFORM-ADMIN-DEMO запущен локально на 127.0.0.1:5185 (API8015):
отдельная постоянная SQLite в output/platform-admin-demo-20261015,
CRM/переписка/подключения и демонстрационные инциденты.
Вход обеих platform-ролей и девять CRM API, UI карточки/поддержки проверены.
Данные вымышленные, providers отключены, AI mock; запуск/границы — checkpoint.

15.10.2026. CRM-NEUTRAL-TERMS реализован и локально проверен: нейтральные
RU/KK/EN подписи новых platform-страниц, поддержки, ресурсов и общего шаблона ИИ;
пользовательские данные сохранены. Правило — в AGENTS/контрактах и проверке i18n.
Backend53, терминология4, browser10 desktop/mobile RU/KK/EN, system/schema,
build/types/i18n/bundle PASS. Scope/evidence и публикация — checkpoint.
Код c7e26f6 опубликован normal push в main, remote SHA совпал; static PASS.
CI38715135513 выполняется, не объявлен зелёным. Автопродолжение crm-2 остановлено.

15.10.2026. PLATFORM-CLINIC-CRM реализован и локально проверен: единая карточка,
постоянный подробный GET просмотр CRM, сообщения без read-mark, scoped поддержка
и аудит. PostgreSQL123, browser12 distinct desktop/mobile, build/types/i18n/bundle,
system/schema PASS; история исправленных запусков и точные границы — checkpoint.
Новых миграций/рабочих DB изменений нет. Код aed452f опубликован normal push
в main, remote SHA совпал; committed-range static PASS. CI38711917194 выполняется.
CI предыдущего fa8a041 (38705753503) полностью SUCCESS. Следующий шаг4 не начат.

15.10.2026. PLATFORM-SHELL: по утверждённому референсу внедрены sidebar64/224px,
единый header57px, меню аккаунта и platform self-account без Business-настроек.
18 scoped browser checks, build/types/i18n/bundle и визуальная проверка PASS.
Исправлены возврат фокуса меню и Escape внутри карточки. Код5b476b7 опубликован
в main, remote SHA совпал; committed-range static PASS. CI38705646141 выполняется.
Границы, исходный референс и evidence — в checkpoint и разделе14 spec.

15.10.2026. PLATFORM-OVERVIEW реализован и локально проверен: очередь внимания,
согласованные KPI → фильтрованные клиники/поддержка, ответственные и обновление;
финансовая логика сохранена. PostgreSQL76, browser8 desktop/mobile RU/KK/EN,
build/types/i18n/bundle и system/schema PASS. Контракт/публикация — checkpoint.
Предыдущий CI38694788872: backend/frontend SUCCESS.
Код 0c9666e опубликован в main, удалённый SHA совпал; committed-range static PASS.
CI38697901995 выполняется; итог ещё не подтверждён.

15.10.2026. PLATFORM-OPERATIONS реализован и локально проверен: рабочие
списки текущих эпизодов/подключений, история ошибок и инфраструктура отдельно;
фильтры, полные counts, пагинация и переходы. PostgreSQL67, browser8 desktop/mobile,
build/types/i18n/bundle и system/schema PASS. Scope/публикация — checkpoint.
Код e464fe8 опубликован в main, SHA подтверждён; static committed-range PASS.
CI38694737037 выполняется, итог пока не подтверждён.
CI предыдущего изменения 38642701572 полностью PASS. Обзор и подробный CRM
read-path следуют отдельными результатами; рабочие миграции не входят в scope.

15.10.2026. PLATFORM-INCIDENT-LINK реализован и локально проверен: связь эпизода
с существующим/новым обращением, снимок и обратные переходы. PostgreSQL77,
browser4 desktop/mobile RU/KK/EN, build/types/i18n/bundle и system/schema PASS.
Дополнительный анализ Обзора/Операций — раздел13 спецификации; владелец утвердил
постоянный подробный просмотр CRM оператором для следующей реализации панели.
Полный редизайн/read-path ещё не реализованы; support0002 рабочей БД не применена.
Scope, проверки и публикация — checkpoint; предыдущий CI38637020865 PASS.
Код `6bb2e46` опубликован normal push в main, удалённый SHA совпал;
committed-range static PASS. CI38642643864 queued, итог ещё не подтверждён.

15.10.2026. PLATFORM-SUPPORT-ACTIVATE завершён: проверены backup/restore,
support0001 применена к локальной db.sqlite3; бизнес-данные сохранены, integrity
и read-only API/HTTP PASS. Поддержка активирована локально. CI38636405892:
frontend SUCCESS, backend IN_PROGRESS. Scope/evidence — checkpoint.

15.10.2026. PLATFORM-SUPPORT-20261015 реализован и локально проверен: очередь
команды и поддержка в CRM, публичные ответы/приватные заметки, назначение, решение
с итогом и явное возобновление. Employee — свои, owner/admin — все своей клиники.
41 PostgreSQL и 6 browser checks, build/types/i18n/bundle, system/schema PASS.
Код dd1c6bb опубликован в main, SHA подтверждён; CI38636349215 queued.
Рабочая support0001 применена отдельной операцией выше; onboarding отложен.
Предыдущий CI-B301-PAYLOAD опубликован e52db32; CI38628077604 полностью PASS.

15.10.2026. CI-B301-PAYLOAD: по поручению владельца исправлено измерение размера
ответа в B301. Диагностика: реальное HTTP-тело 135616 байт, повторная сериализация
тех же данных 150011; бюджет 150000 сохраняется. B301: 4 PASS, system/schema PASS.
Изменён только тест измерения; публикация и итоговый CI проверяются отдельно.

15.10.2026. PLATFORM-REBUILD-01 реализован и локально проверен: обзор, список и
карточка клиники разделяют настройки, записанные ошибки и свежие наблюдения сервиса;
нет данных не превращается в ноль. MRR/подписки сохранены отдельным блоком по
уточнению владельца. Меню без заглушек, status filter/return context, явный 403.
Backend/PG, целевые browser flows, build/types/i18n и system/schema PASS;
подробные команды/границы — в checkpoint. Создание клиник и очередь ещё не начаты.
Код 772bca1 опубликован в main. CI38622945054: frontend PASS, backend FAIL
на прежнем B301 payload budget карточки клиента (150019 > 150000); тот же FAIL
подтверждён на base b056c3d в CI38618663948. Общий CI не зелёный.

14.10.2026. PLATFORM-REBUILD-SPEC: подготовлена [спецификация /platform](docs/testing/platform-rebuild-spec-20261014.md):
сценарии, роли, UX, backend/API, reuse/retirement и приёмка. Решения владельца:
клинику создаёт только platform_admin; команда помогает с настройкой; обращения
создаются командой и из CRM. Реализация не начата, код и рабочая среда сохранены.
Порядок внедрения — в roadmap; открытые решения блокируют только зависимые сценарии.

14.10.2026. CRM-R02-AI-RETURN-ACTIVATE завершён: backup проверен, bots0012
применена к рабочей SQLite, отдельные worker/beat запущены. Два плановых цикла
с интервалом 60 секунд PASS; подходящих диалогов нет, состояния/сообщения сохранены.
Health/DB PASS. Runtime оставлен работающим; автозапуск после перезагрузки не настроен.
Остальные фоновые задачи и облачные подключения вне объёма; evidence — в checkpoint.

14.10.2026. CRM-R02-AI-RETURN реализован и локально проверен: возврат обычного диалога
к ИИ после часа тишины и успешного ответа сотрудника. Защитные остановки,
неотвеченные обращения и ручная пауза сохраняются. Meta и PS Cloud отложены.
186 backend +22 PostgreSQL +4 browser checks PASS; финальные 2 UI-проверки,
build/types и committed-range static PASS. Код f6d6373 опубликован в main,
удалённый SHA подтверждён; CI38612574478 queued. Scope/evidence — в checkpoint.
Последующая рабочая активация выполнена отдельной операцией выше.

14.10.2026. CRM-R02: записаны ответы владельца по бесплатному реальному пилоту
на 3–5 пользователей с ориентиром на 30.10 минимум на две недели.
Нужны Telegram + WhatsApp, клиентский AI и инфраструктура в Казахстане.
Подключение Meta и PS Cloud отложено; правило возврата AI согласовано выше;
R02 открыт, подключения и deployment не выполнены. Анализ и решения —
в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md#crm-r02-20261014--pilot-decisions-and-provider-research).
Итоговый CI S04 (38562361806) завершён успешно.

14.10.2026. CRM-S04 закрыт в локальной изолированной границе: PostgreSQL/Redis/
workers, recovery/retry/cancel, экспорт/файлы и фактическое восстановление backup.
Scope/проверки — [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md#crm-s04-20261014--isolated-operations-and-recovery).
Полный изолированный runtime и 73 зависимых теста PASS; committed-range static PASS.
Код e3dbd97 опубликован в main, удалённый SHA подтверждён; CI38562250124 in_progress.
Рабочая БД, облачная среда и внешние отправки вне объёма.

14.10.2026. CRM-S03 закрыт в согласованной scoped-границе: понятное состояние сервиса,
жизненный цикл инцидентов и уведомления без повторов. Scope/риски/проверки —
в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md#crm-s03-20261014--service-state-and-incident-notifications).
Состояние/API/UI и уведомления реализованы; scoped-проверки PASS.
Владелец выбрал owner/admin для колокольчика; сотрудникам — баннер.
26 backend +11 PostgreSQL +8 browser checks, build/types/bundle PASS.
Committed-range static PASS; код 1efc0f8 опубликован в main, SHA подтверждён.
CI38554277365 (итог S03) completed success. Рабочий запуск мониторинга отдельно.
Рабочая БД и внешние отправки не затрагивались в S03.

14.10.2026. CRM-S02 закрыт в согласованной scoped-границе: серверный поиск/пагинация,
полный журнал поддержки, реальные сводки и четыре страницы в общей дизайн-системе.
28 backend tests, build/types/bundle и9 browser checks PASS (1 штатный mobile skip).
Запись с grant/MFA работает; CORS-блокер исправлен. Static PASS, код fc322a6
опубликован в main, удалённый SHA подтверждён. CI38548233244 и38548316979 завершены: PASS.
Объём, Git-снимок, проверки и границы прав — в
[checkpoint](docs/testing/task-state/PRIMARY-SESSION.md#crm-s02-20261014--operational-platform-administration).
S01 остаётся закрытым в своей проверенной границе.

14.10.2026. CRM-S01: владелец утвердил четыре этапа внутренней готовности:
серверные сценарии → операционная админка → состояние сервиса/уведомления →
локальные фоновые процессы/восстановление. В S01 исправлены доказанные ошибки
атомарности, устаревшего состояния, повторов и текущего доступа; проверки PASS.
S01 ЗАКРЫТ в согласованной границе: D-04 утверждён, встроенная follow-up задача
повторно используется без перезаписи; create_task остаётся отдельным действием.
Регрессии и PostgreSQL-конкуренция PASS. S02 не начат.
AI, внешние интеграции, реальные клиники и рабочие миграции вне объёма.
R01 не переоткрывается, FB009 остаётся отложенным. План — в
[roadmap](docs/current/roadmap.md), scope/проверки — в
[checkpoint](docs/testing/task-state/PRIMARY-SESSION.md#crm-s01-20261014--server-scenario-completeness).

14.10.2026. R01 ЗАКРЫТ по уточнённому владельцем объёму: выбранный ежедневный
цикл проверен, CI опубликованного кода PASS. Единственный оставшийся ручной
screen-reader FB009 владелец отложил; проверка не выполнена, PASS не заявлен.
Тестовый стенд остановлен, рабочая база и продуктовый код не менялись.
Roadmap/acceptance обновлены; R02 — следующий этап, автоматически не запущен.
Это решение уточняет прежние записи об открытом R01 ниже; evidence — в checkpoint.

14.10.2026. CI/PUBLISH: фактический GitHub CI Calendar, Settings и R01 завершён
успешно, включая текущий `0b4d7da` (run38471973914): backend, frontend и аудиты
зависимостей PASS. Это уточняет прежние queued/in_progress ниже. По прямому
поручению владельца публикуется оставшийся журнал ONEC; доступ/пилот 1С не
возобновляется. Docs-only проверки и итоговая публикация — в checkpoint.
R01 FB009 остаётся открытым; следующий продуктовый этап не запущен.

14.10.2026. CRM-R01: выбранный цикл администратора проверен desktop/mobile.
Исправлены Business-время задачи Inbox, дубли при retry после потери ответа,
зависшее уведомление и возврат фокуса формы. Проверены независимые состояния,
ручная оплата, история, запрет архивации незавершённого и archive/Undo.
Ручной screen-reader FB009 остаётся открытым; общий R01 PASS не заявлен.
`f11fb05` опубликован в main, SHA подтверждён; CI38471830909 in_progress.
Проверки и ограничения — в checkpoint; R02+ не запускались.

14.10.2026. SETTINGS-ASSIGNMENT: Phase2 завершена в scoped-границе.
Исправлено явное назначение роли старому участнику без BusinessRole; сохранение
обновляет список и права, предварительные права не выдаются за применённые.
Изолированные проверки фактического доступа/retry/custom role, RU/KK/EN desktop/mobile,
сборка и static PASS; `c40aff4` опубликован в main, SHA подтверждён.
CI38467033037 queued, не объявлен PASS. После публикации receipt PlatformaCRM UI
возвращает writer основному чату для R01; общий реестр FC003 имеет два baseline-пробела.

14.10.2026. TWO-CHAT-COORDINATION: принят единый roadmap и один writer на репозиторий.
Календарь опубликован; основной чат передаёт PlatformaCRM UI запись для Settings
и переходит к read-only подготовке R01. Registry/primary не менялись.
Scope передачи и проверки — в checkpoint.

14.10.2026. CALENDAR-SETTINGS-R01: после завершённой Аналитики владелец поручил
последовательно переработать календарь, сверить полноту Settings и возобновить R01.
Календарь реализован: месяц/неделя, сводка и полноразмерный инспектор дня/визита.
Проверки 51/51, RU/KK/EN desktop/mobile, роли, записи/переноса, полной карточки,
общего выбора дат, CU, сборка и static PASS. Опубликовано `2f9035b`,
GitHub CI38464742290 queued на момент записи. Далее Settings → R01.
Scope, ограничения и проверки — в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

14.10.2026. ANALYTICS-REDESIGN: компактная аналитика с пятью вкладками,
единым периодом по датам событий, серверными агрегатами и CSV реализована.
Backend71 и после исправления скачивания40, check/migration drift, сборка
и scoped CU PASS. Опубликовано в main (`2474024`); CI выполняется. Evidence —
в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md). R01 остаётся отложенным.

13.10.2026. CRM-TOOLBARS refinement: единые элементы трёх страниц, широкий поиск,
один вход в фильтры, исправленные меню/выравнивание/выбор менеджера и компактная
пагинация. Backend24, browser14 RU/KK/EN desktop/mobile и build PASS.
Static PASS. Опубликовано в main (`45f4899`), CI выполняется; календарь вне scope.

13.10.2026. CRM-TOOLBARS: реализован согласованный первый этап — единые панели
клиентов/заявок/сделок, серверные фильтры и общий выбор дат. UI RU/KK/EN
desktop/mobile, backend и сборка PASS. Опубликовано в main (`b98381e`), CI выполняется.
Календарь — следующий отдельный этап.
Scope и evidence — в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

13.10.2026. ONEC-ODATA-PILOT: адрес API отвечает 401 Basic. До сохранения доступа
обнаружена обязательная цепочка зависимостей, включающая кадровые/зарплатные и
финансовые объекты; отказ снимает выбор исходного справочника. Расширение не принято,
служебный пользователь не сохранён. Запрошено решение владельца по этому расширению
прав; API-выборка пока не выполнена. CRM/бизнес-данные не менялись. Scope и проверки —
в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

13.10.2026. DIRECT-TASK-AUTHORIZATION: владелец отменил рутинное согласование и
отчёты между PlatformaCRM и PlatformaCRM UI. Прямое поручение разрешает исполнение
в получившем его non-retired чате; один фактический писатель, проверки Git/evidence
и явная передача сохраняются. Primary/registry не меняются, продуктовые этапы
не запускаются. Правила и read-only hook согласованы; runtime trust не заявлен.

13.10.2026. INTEGRATIONS-SIMPLIFY, уточнение владельца: карточки сделать компактными
и центрированными, подробности перенести в открываемую настройку. UI writer вновь
согласован primary; frontend-дельта готова, desktop/mobile RU/KK/EN и build PASS.
Первый browser запуск упёрся в startup timeout; отдельный повтор прошёл.
Опубликовано в main (`aaa2d97`), CI выполняется; backend вне scope.
Временный UI writer освобождён, primary/registry неизменны.

13.10.2026. INTEGRATIONS-SIMPLIFY-20261013: владелец поручил оставить на странице
Подключений только переработанные карточки МойСклад и 1C; убрать повторный заголовок,
подзаголовок, метрики, поиск/фильтры и финансовую форму. Primary подтвердил временного
единственного scoped writer PlatformaCRM UI; registry не меняется. Реализация,
desktop/mobile RU/KK/EN открытие форм/клавиатура и изолированная сборка PASS.
Опубликовано в main (`30b8f55`), CI выполняется. Scoped writer освобождён;
primary generation 5 сохранён. Backend/внешние подключения вне scope.
Контракт — [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

13.10.2026. INBOX-COMPACT-20261013: утверждённая компактная компоновка Conversations
реализована. Scoped desktop/mobile RU/KK/EN проверки (14 сценариев) и build/types/
i18n/bundle PASS. История занимает больше места; AI-preview, действия и черновики
сохранены. Опубликовано в main (`0ca57fb`), GitHub CI выполняется на момент записи.
Zoom200% не подтверждён; узкие viewport проверены отдельно. Evidence и ограничения —
в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md). R01 отложен.

13.10.2026. TASKS-REDESIGN-20261013: список/инспектор, ожидание, права, связи и
защита черновиков реализованы и опубликованы в main (`4abc60a`). Локальные backend,
PostgreSQL concurrency, desktop/mobile RU/KK/EN и сборка прошли scoped проверки.
Разрешённая локальная миграция выполнена с резервной копией и сохранением данных.
[CI реализации](https://github.com/999MAX20/PlatformaCRM/actions/runs/38302357789):
frontend success, полный backend на момент записи выполняется. Временное назначение
писателя завершено; primary generation 5 сохранён, следующая работа не назначена.
Команды, ограничения и публикация — в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

13.10.2026. R01 отложен по решению владельца до завершения интерфейса страниц
«Задачи», «Подключения», «Аналитика», «История». Полноту проверки Settings сверить
с существующим evidence перед общей приёмкой; прежние scoped PASS сохраняются
в своих границах. Возобновление приёмки — после сообщения владельца о готовности.
Текущая работа ограничена фиксацией решения, без новых продуктовых изменений.

12.10.2026. CRM-MB01-IMPLEMENT-20261012: MB1–MB5 реализованы и локально проверены.
Филиалы, услуги/цены, графики/переезды, доступ, отсутствие/архив специалиста и
выбор филиала клиентским AI связаны с текущими экранами. Backend, PostgreSQL
concurrency, desktop/mobile RU/KK/EN, build/types/i18n/bundle PASS в указанной
[границе evidence](docs/testing/task-state/PRIMARY-SESSION.md). [Этапы](docs/current/roadmap.md#crm-mb01-запрошенная-многофилиальная-работа)
закрывают локальную реализацию; публикация/CI фиксируются отдельно. Рабочая
`db.sqlite3` мигрирована по отдельному разрешению владельца: проверенная резервная
копия и сохранность данных подтверждены; филиалы автоматически не создавались.
Следующий roadmap-этап — R01, отложенный решением выше; live AI/каналы и deployment не проверялись.

12.10.2026. RECOVERY-20261012: по явному поручению владельца основной задачей
назначена «Платформа CRM продолжение», generation 5. Понимание продукта, последних
Settings/CRM-MB01, Git и ограничений проверено; прежний primary архивирован,
зависший запрос прерван. Код сохранён, dev работает; следующая продуктовая задача
ожидает поручения владельца. [Передача](actual_docs/PROJECT_HANDOFF.md) и
[checkpoint](docs/testing/task-state/PRIMARY-SESSION.md) фиксируют evidence/публикацию.

12.10.2026. DOCS-MULTIBRANCH-20261012: зафиксировано требование CRM-MB01 — одна CRM
для нескольких филиалов одного бизнеса (сценарий: пять филиалов), сотрудники,
графики и календарь по филиалам. [Технический scope](docs/current/crm.md#crm-mb01-многофилиальный-график-и-сотрудники)
и [место в плане](docs/current/roadmap.md#crm-mb01-запрошенная-многофилиальная-работа).
Документация, без реализации кода; правила доступа/переездов и приоритет ещё требуют
решений. Проверки и публикация — в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

09.10.2026. SETTINGS-WORKFLOW-20261009: профиль компании упрощён, личные уведомления
перенесены в аккаунт, права ролей открываются из сотрудника/приглашения. Дополнительные
поля выровнены и доступны на полных карточках; Inbox ведёт к созданию шаблонов,
Тариф очищен. Desktop/mobile E2E, build/types/i18n/bundle PASS. Свои сценарии сообщений
отложены владельцем. [Результат](docs/testing/settings-workflow-20261009.md),
публикация и фактический CI — в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

09.10.2026. SETTINGS-REDESIGN-20261009: все десять разделов настроек переработаны
по утверждённым референсам. Формы, матрица прав, предпросмотр приглашений,
локальные ошибки и сохранение проверены desktop/mobile RU/KK/EN и tablet RU.
Backend, browser, build/types/i18n/bundle и system/drift PASS; исправлен audit rollback
создания разрешения. [Результат](docs/testing/settings-redesign-20261009.md),
публикация и фактический CI — в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

09.10.2026. DOCS-ROADMAP-20261009: составлены [единый roadmap](docs/current/roadmap.md)
до production и [паспорта пятнадцати направлений](docs/pre-production/README.md)
на опубликованной основе `768b2675`. Открытые acceptance IDs сопоставлены этапам;
контракты, scoped evidence и отложенные решения сохранены. Docs-only scope,
без новой продуктовой фазы, provider calls или deployment. Проверки/публикация —
в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

09.10.2026. SETTINGS-FUNCTIONAL-20261008: все десять разделов настроек исправлены
и локально проверены без редизайна. Выбранный бизнес, атомарные права, очередь
сообщений, предпочтения и дополнительные поля связаны с реальными потребителями;
справочные параметры сохраняют данные. Backend, desktop/mobile RU/KK/EN,
build/types/i18n/bundle и system/drift PASS. [Реестр](docs/testing/settings-functional-20261008.md),
точные проверки и публикация/CI — в текущем checkpoint.

08.10.2026. INBOX-RELINK-20261008: владелец утвердил подтверждаемую смену клиента
с отвязкой несовместимых заявки/сделки и сохранением сущностей/истории.
Реализованы атомарная замена, защита от устаревшего подтверждения и диалог RU/KK/EN.
88 backend, 17 browser сценариев, сборка и системные проверки PASS.
Локальный scope завершён; evidence и публикация — в checkpoint.

08.10.2026. INBOX-MANUAL-20261008: ручной операторский сценарий Inbox проверен;
исправлены прочтение, даты, повторная запись, заполнение задач и подписи.
Desktop/mobile scoped tests и сборка PASS. Найденный вопрос смены клиента решается
в INBOX-RELINK выше; реальная доставка не проверялась. Evidence — в checkpoint.

08.10.2026. INBOX-DENSITY-20261008: выровнены отступы Inbox по 16px, уплотнены
строки и шапка диалога, разделены сущности инспектора. Desktop/mobile, основные
действия и сборка PASS; функциональные наблюдения и evidence — в checkpoint.

08.10.2026. INBOX-DEMO-20261008: добавлены четыре тестовых диалога в локальный
Business 2. Полный инспектор открыт и проверен в браузере владельца;
есть сценарии нескольких записей и отсутствующего клиента. Внешних отправок
не было; backup/manifest и проверки — в текущем checkpoint.

08.10.2026. INBOX-INSPECTOR-20261008 реализован и локально проверен:
компактная панель «О клиенте», будущие записи, scoped-связи и точные переходы;
AI у ответа, доставка у сообщения, CRM-действия через меню/подтверждение.
Черновики, мобильная панель и прежнее пустое состояние проверены.
Границы, команды и публикация — [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

08.10.2026. INTEGRATIONS-REVIEW-20261008: выполнен функциональный аудит
страницы подключений и подготовлен интерактивный референс редизайна.
[Отчёт](docs/testing/integrations-functional-review-20261008.md) отделяет
воспроизведённые ошибки от рисков по коду и live-границ. Продуктовый код
не менялся; реализация и запуск внешних интеграций не начинались.

08.10.2026. SIDEBAR-FLAT-NAV-20261008: группы «Каналы»/«Контроль» убраны;
«Подключения», «Аналитика» и «История» показаны отдельными пунктами desktop/mobile.
Проверки и публикация — [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

08.10.2026. INBOX-EMPTY-FILTERS-20261008: точечные правки после отката — пустые
состояния выровнены, CTA перенесён в диалог с переходом к каналам AI-агента,
меню быстрых фильтров расширены. Текст пустого списка говорит об обращениях
с подключённых каналов. Desktop/mobile и сборка PASS. Проверки и публикация —
[checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

08.10.2026. INBOX-UI-ROLLBACK-20261008: по запросу владельца возвращён прежний
интерфейс Inbox до `8bb54dd`; остальные пять экранов и поведение AI сохранены.
Точечная проверка и публикация фиксируются в [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md).

08.10.2026. UI-OPERATIONS-20261008: согласованный пакет шести экранов реализован
и локально проверен. Главная использует полные scoped-счётчики без двойного
учёта, остальные рабочие экраны исправлены по аудиту. 78 backend и 9 unit PASS,
desktop/mobile/tablet flows, build/types/i18n/bundle PASS.
[Отчёт](docs/testing/ui-operations-20261008.md) фиксирует scope, ошибки и границы;
итоговые commit/push/CI — в ответе задачи и публикационном receipt.
Клиентский AI-пилот сохранён без новых платных вызовов и внешних отправок.

08.10.2026. PREPROD-AI-EVIDENCE-20261008: обновлён
[паспорт клиентского AI](docs/pre-production/customer-ai-agent.md) с матрицей
выполненных поведенческих проверок, исправлениями, версией и успешным CI `de1867b`.
Это обновление документации по существующему evidence, без новых запусков модели.

08.10.2026. INBOX-LOCAL-PILOT-20261008: локальная приёмка PASS. Уведомление при
передаче человеку, отзыв устаревших отправок и удобная настройка существующих
функций проверены. [Отчёт](docs/testing/inbox-local-pilot-20261008.md) фиксирует
проверки, расходы и ограничения; публикация/CI — в итоговом ответе и evidence.
Мессенджеры, production-инфраструктура и развитие CRM-аналитика исключены.

08.10.2026. INBOX-LIVE-ACCEPTANCE-20261008: предметная приёмка прошла, исправлены
ложный off-topic для справочных вопросов и повторное подтверждение невозможной
записи. [Отчёт и точные проверки](docs/testing/inbox-live-acceptance-20261008.md)
содержит live-модель, backend, расходы в пределах USD1 и сохранённые ошибки.
Изолированные данные, без внешней доставки клиентам. Финальная публикация/CI
фиксируются в ответе задачи и evidence; следующий продуктовый этап не назначен.

07.10.2026. Консолидация документации DOCS-RESET-20261007 выполнена и проверена.
Подготовлены действующие контракты, карта реализации, обновлённые entrypoints
и архив с проверяемым происхождением. Проверки целостности, ссылок и маршрутов
PASS; итоговый commit определяется Git history, SHA/CI фиксируются в ответе задачи;
[checkpoint](docs/testing/task-state/PRIMARY-SESSION.md) содержит scope и evidence.

Продуктовый фокус — клиентский Inbox AI поверх обычной CRM. Последняя safety
версия реализована и прошла ограниченную live-проверку 08.10; production/каналы/клиническая приёмка
не объявлены. CRM AI/аналитика на паузе разработки без удаления runtime.

[Паспорта](docs/pre-production/README.md) · [что реализовано](docs/pre-production/capabilities.md)
· [действующие требования](docs/README.md) · [открытая приёмка](docs/current/acceptance.md).
Внешние интеграции, gateway и billing отложены. Пакет операционного UI завершён
в локальной приёмке; следующий продуктовый этап не назначен. Развитие CRM AI на паузе.

Canonical root `C:/Users/user/Desktop/PlatformaCRM`; branch `codex/ui-testing-toolkit`.
Generation 4 primary, transition idle — [.codex/project-session.json](.codex/project-session.json).
История перенесена в архив; не продолжать старые задания по прежним записям.

YCLOUD-TPLITE-20261028: implementing owner-authorized stage1 (TP Lite + Inbox text).
External effects disabled; no real accounts/sends. Contract and checks in PRIMARY.

## STAND-ACCESS-20261029
Password-only entry implemented for the dedicated stand overlay; RU/KK/EN style, server-side gate, persistent throttling, CSRF and cookie rotation.10 HTTP tests, actual Caddy edge/fail-closed, Compose port boundary and browser flows PASS. Code70d5d2e0 pushed to main; stand CI40894680725 PASS, general CI running. Local test credentials and preview activated in the follow-up below; no public deployment. Details: STAND-ACCESS in PRIMARY and operations.



STAND-ACCESS local29.10: test credentials configured in ignored ENV; CRM5174 and
Market3080 preview running. Cookie collision fixed; HTTP11/11 and real Caddy PASS.
Chrome gate-to-app verified. Public deployment remains separate; details PRIMARY.

VITE-CACHE-FIX publication:764277c6 pushed/remote confirmed; CI41642801467
in progress. Owned isolated runtimes stopped; working dev retained.

RECORDS-PERIOD-POPOVER publication:835a5985 normal-pushed to origin/main; remote
SHA835a598522dd686382ef90c1794074ae91511490 confirmed. CI41645297715 in progress.
Working/index/committed-range hygiene and owned diff/link/secret review PASS.
No remainder in requested scope; no deployment or working DB writes. Dev retained.
Stale empty index.lock18:29 removed after two no-Git-process inspections and
exclusive-open/index-hash checks. Foreign WIP preserved; own source paths clean.

CALENDAR-MONTH-NAMES-20261103: full month labels in compact picker implemented;
RU desktop/mobile390 and Intl RU/KK/EN12-month output checked; isolated build/types/
i18n PASS. No API/data change. Evidence in PRIMARY.

CALENDAR-MONTH-NAMES publication:40a807ba normal-pushed and remote SHA confirmed.
Scoped working/index/committed-range hygiene PASS; CI41645911586 in progress.
Requested scope complete; no deployment. Own source clean, unrelated WIP retained.

CALENDAR-INVENTORY-20261103: approved Records period picker recorded in frontend
contract;5 direct calls/7 areas, separate calendar grid and26 native date fields mapped.
Docs/static review only; no product changes or migration to other screens.

CALENDAR-REVIEW-20261104: requested year correction and bounded Records/Calendar audit completed locally.
Data-aware year range, unwrapped options and selected-value scrolling/focus implemented.
Node17/browser12+7/backend40/final build PASS; audit3 includes2 confirmed open P2
Records filter defects, not fixes. Isolated data only, foreign WIP preserved.
No own commit/push/CI/deploy: existing index.lock and mixed outgoing retained.
Evidence: docs/testing/evidence/calendar-review-20261104.md. Other active tasks unchanged.

VOICE-IDENTITY-20261111: conflicting phone no longer selects a same-name client silently.
Explicit clarification/selection, normalized phone, guarded execution; no partial writes.
Focused7/dependent128/final9/system-drift PASS; isolated PG12 and Redis/Celery crash/retry/replay PASS.
Real synthetic3 +final conflict outcomes/replay PASS; STT digit/name errors retained, human speech OPEN.
No workingDB/deploy; locally verified change set, push blocked by28foreign outgoing commits.
Evidence: docs/testing/evidence/voice-identity-20261111.md; output/voice-identity-20261111.

VOICE-HISTORY-20261112: requested history UI implemented and locally verified.
Latest follow-up: new/resume assistant buttons and yellow clarification state added;
Playwright selected/new/header/keyboard/locales/mobile PASS, zero mutation requests.
Owner follow-up: shared date-range calendar and untruncated statuses implemented;
Playwright range apply/cancel/clear and RU/KK/EN320/1440 +build PASS.
Title search, status/business-timezone date filters, full-list pagination search,
day groups, result-first details, named reviews and read-only outcome states.
Playwright real read-only flow + browser fixtures PASS; RU/KK/EN/mobile/keyboard PASS.
Header/sidebar dimensions preserved; frontend build/types/i18n PASS; foreign WIP retained.
No local scoped remainder; foreign outgoing history blocks own-only push/newCI/deployment.
Evidence: docs/testing/evidence/voice-workflows-20261106.md, history section.

NOTIFICATION-QUEUE-20261113: active toast protection and error colors locally verified.
Four visible cards, pending FIFO, shared AppError mapping; current design retained.
38 distinct browser scenarios,22 Node checks, build/types/i18n/bundle and audit PASS.
No scoped local remainder; publication/CI receipt in checkpoint.
Evidence: docs/testing/evidence/notification-queue-20261113.md.
Checkpoint: output/notification-queue-20261113/CHECKPOINT.md.

META-DELIVERY-20261114 (local, no publication): direct Meta webhook processes all
text/control messages and mixed statuses with route preflight and replay dedup.
Inbox send intents commit before HTTP; ambiguous outcomes block resend, explicit
rate limits retry within bounds, receipts cannot regress delivery or affect another
attempt/business. Checks: 193 PASS, 2 PostgreSQL-locking skips on isolated SQLite;
Django check/migration drift PASS. No schema/env/server/Meta changes. Real-number
and PostgreSQL acceptance are not claimed. Details: META-DELIVERY-20261114 in
PRIMARY-SESSION; log and source hashes linked there.

META-SIGNUP-20261114: standard direct Meta Embedded Signup implemented locally.
Token/app/scopes/expiry, WABA phone ownership, subscription/registration and one-use
attempts precede connected status; stale/repeated setup and failed reconnect guarded.
PIN input and callback/error/retry flow verified in RU/KK/EN. Scoped backend/browser,
build/types, isolated migration checks PASS; the originally skipped PostgreSQL
concurrency check subsequently passed in META-V4-20261117.
No Meta/server/workingDB/publication changes. Target migration, Meta setup/Advanced
Access/billing and real client-number acceptance remain open; coexistence/migration
are separate scope. Detailed evidence and limitations: META-SIGNUP-20261114 in
docs/testing/task-state/PRIMARY-SESSION.md; docs/current/integrations.md.

META-PILOT-20261114: seven-step Meta plan reconciled and recorded in roadmap CRM-R03.
Owner subsequently authorized necessary pilot deployment/Meta actions. Verified
Meta text batch/outbox fixes deployed to test stand;
pilot-only privacy/deletion RU/KK/EN published, URLs saved, Meta app Published.
AI/autoreplies off. Full frozen backend3333PASS/78skips, PostgreSQL195PASS,
frozen frontend build/types PASS. Live inbound/replay and one delivered manual
reply verified. The reply required a process-local Meta sandbox recipient alias;
ordinary sends are now verified in META-PILOT-STABLE below. Integrations worker subscription fixed.
General CRM legal v0.3,
Advanced Access, Signup deployment/client onboarding remain open. Exact evidence,
existing environment warnings and rollback: META-PILOT-20261114 in PRIMARY-SESSION.

META-PILOT-STABLE-20261114 scoped acceptance PASS: explicit sender/recipient-scoped test alias
and canonical response-identity validation deployed to the pilot stand.
Focused46, PostgreSQL202 and full frozen backend3340PASS/78skips; current-index
focused46PASS. Three-file/runtime-config deployment, readiness/auth boundaries
and actual worker configuration/integrations queue PASS; no schema/UI change.
Meta SYSTEM_USER token validated and stored encrypted; expiry13Jan2027 23:35 Asia/Qyzylorda.
Owner explicitly approved full access only to test WABA after code10 denial.
Normal Inbox->worker reply40 delivered14Nov23:43:08 local; same-row retry, no duplicate.
Signed actual receipt replay200, counts3->3. Code8585aa27 published; its CI PASS.
No remaining code/evidence/input gap in this closed test scope; client onboarding remains separate.

META-V4-20261117: audit and local fixes; external readiness remains blocked.
Meta business verified/app published; actual review Not submitted, mixed draft.
Owner confirmed settings17Nov: CloudAPI-only60day config1029142846909211 created;
SDK/embedded-browser OAuth ON, SDK domain platformacrm.kz saved. Exact redirects
remain empty; account_update subscription waits for verified handler deployment.
Deployment/migration0011 and real client acceptance remain separate gates.
Local code: PIN before launch/prompt completion/20s incomplete timeout, minimal
WhatsApp scopes, signed account-update journal without activation/messages.
Focused account7PASS; dependent backend102run101PASS1SQLite-locking skip;
PostgreSQL Signup24PASS including locking; build/types/i18n/bundlePASS.
Targeted browser/visual final result and input hashes in PRIMARY-SESSION META-V4.
No deployment, client send or App Review submission at this preparation checkpoint.
Owner subsequently authorized all-current-changes integration and deployment in
RELEASE-20261117; the former shared-dependency publication restriction is resolved.
Concrete scenario/settings/reviewer package: docs/current/operations.md,
section Meta v4 and App Review preparation. This does not close CRM-R03.

RELEASE-20261117: all captured pending changes integrated from baseb659f90b.
Full local release gate PASS:3404 backend tests passed/81 platform skips,
types/i18n/app/widget/bundle,2 mobile role checks and dependency audits.
PostgreSQL Signup24/24 and migration roundtrip PASS;214 distinct browser cases PASS.
Release verification fixed notification focus return and overlapping full-text view,
preserving hidden-notice timers; corrected stale PIN and mobile fixture expectations.
Five preceding published commits have successful GitHub CI. Production bundle
preserves same-origin API and pilot legal files; AI remains off and Scribe unchanged.
This entry records verified inputs. Actual Git/CI/server receipts are recorded during
delivery in output/release-20261117/delivery.json; detailed checks and limits:
PRIMARY-SESSION RELEASE-20261117 and output/release-20261117.

## AI-AGENTS-EMPTY-20261117

Owner correction: empty Agents now shows only a CTA centered horizontally and
vertically, without picker/top button/card. Purple robot marks removed from agent
responses, navigator and legacy bots; no runtime/API/permission change.
Fresh Chrome RU/KK/EN desktop/mobile, keyboard/create/focus and short-height
scrolling PASS; build/types/i18n/bundle PASS. Native zoom limit recorded in evidence.
No local scoped remainder. Publication/CI and exact limits:
output/ai-agents-empty-20261117/CHECKPOINT.md; registered evidence:
docs/testing/evidence/ai-agents-redesign-20261113.md#empty-state-correction17nov.
Deployment not performed; unfinished alerts work is not closed by this UI change.

## CLIENTS-FILTERS-20261117

Owner approved seven filters on /clients: date added, source, tags, appointments,
tasks, contact gaps and archive. Old segment/handoff/custom-field/saved-view menu
content removed; waiting-reply stays next to search. Applied chips, draft/cancel,
reset and URL restoration retained. Existing legacy API remains compatible.
Code scope complete; local Chrome tab http://127.0.0.1:5173/app/clients opened.
Browser extension subsequently timed out: ordinary-tab final screenshot/loading
acceptance is unverified; isolated browser acceptance is separately passed.
Checks and precise environment/publication boundary: PRIMARY-SESSION entry below
and output/clients-filters-20261117/CHECKPOINT.md. No deployment performed.

## CLIENTS-PAYMENTS-20261118

Owner superseded accepted modal with dedicated `/app/payments`: routed ledger,
compact search/kind/add toolbar, no journal modal/footer/pagination. Older payments
load on scroll by explicit owner choice; client-scoped URL survives reload.
Existing financial forms/history/permissions retained. Client list pagination
removal stays unchanged (first20 clients, no autoload).14distinct browser cases
PASS after focused locator rerun; build/types/i18n and isolated bundle PASS.
Desktop/tablet/mobile/locales/text200 screenshots inspected. Prior modal PASS is
historical; publication/actual CI receipt is recorded in the checkpoint below.
Evidence: docs/testing/evidence/clients-records-20261105.md.
Checkpoint: output/clients-payments-20261118/CHECKPOINT.md; new runs in
output/payments-page-20261118. Foreign voice/search WIP preserved. No deployment.

## RECORDS-EMPTY-20261118

Owner accepted context-sensitive appointments CTA: first record/create,
empty day or period/create+choose date, filtered/reset. Framed empty card/icon
removed; content centered below retained toolbar on page background. Creation
respects permission; existing API scope and lifecycle unchanged.
Build/types/i18n/bundle and 10 targeted browser scenarios PASS. Chrome localhost
opened and visually inspected; ordinary app also showed a connection alert,
not treated as release-health evidence. Details: PRIMARY-SESSION same task ID,
output/records-empty-20261118/CHECKPOINT.md. No deployment performed.

RECORDS-EMPTY-20261118 follow-up: owner removes duplicate header create button on
successfully loaded empty lists. Central create remains for first/day/period;
filtered empty keeps reset only; populated list restores header create.
Build/types/i18n and RU desktop/mobile state-transition/create-focus scenarios
PASS. Current contracts updated; no backend/permission/API changes.
Evidence and publication receipt: output/records-empty-20261118/CHECKPOINT.md.

META-COMMON-CALLBACK-20261118: fixed WhatsApp callback per frontend origin implemented locally;
new tenant/agent identity stays in signed state; shared webhook and automatic WABA subscription retained.
101 backend PASS/2 PostgreSQL-only skips,25 mocked browser PASS, system/drift/build/types/bundle PASS.
No commit/push/deploy/Meta URL changes. Live Coexistence blocked by observed3441107;
new-business live acceptance remains open. Details: PRIMARY-SESSION META-COMMON-CALLBACK-20261118.

VISIT-PLAN-PAYMENTS-20261118: authorized money scope implemented and locally verified.
Terms/package/per-visit, advances/allocations/refund-retain/same-client credit and approved UI delivered locally; zero-base positive package forbidden.
Final PostgreSQL21, SQLite18 regressions/39 migration-payment/122 dependent/21 finance PASS; app/widget/types/i18n/bundle and real RU/KK/EN desktop/mobile/recovery PASS.
Working migration/deploy and full AC01–14 are not claimed. The later approved correction/legacy slice is recorded below.
Publication receipt and detailed boundaries: docs/testing/evidence/visit-plan-payments-20261118.md.

VISIT-PLAN-PAYMENTS follow-up: five approved correction/legacy rules implemented and locally verified.
References preceded UI edits. Owner-only annulment, retained reversal balance,
linked replacement, explicit reuse and full legacy remainder attachment preserve history/cash receipts.
PostgreSQL19, dependent126, final pricing/correction31 PASS; build/types/i18n and
real RU/KK/EN desktop/mobile/retry/stale/draft checks PASS. Working DB unchanged.
Implementation c42c4711 normal-pushed to origin/main; remote SHA verified. CI473 in_progress at inspection.
Arbitrary reopen/rendered-service repricing/bulk reconciliation excluded.
Scope/checkpoint: docs/testing/evidence/visit-plan-payments-20261118.md.

VISIT-PLAN-PAYMENTS termination/refusal follow-up: implemented and locally verified.
Owner refusal/termination, frozen remaining prices, preserved debt, separate remainder
and linked rebooking delivered. Dependent127, PostgreSQL20, build/types/i18n/bundle
and real RU/KK/EN desktop/mobile/recovery flows PASS. No working migration/deploy.
Implementation bb051dbd pushed to origin/main; remote SHA verified; CI in_progress. Evidence: docs/testing/evidence/visit-plan-payments-20261118.md#plan-termination-refusal-20261118.

## CLIENTS-EMPTY-20261118
Implemented centered Clients empty CTA on page canvas, outside table frame;
header create hidden only for confirmed unfiltered empty list, shortcut retained.
Filtered empty keeps reset and header creation. Build/types/i18n and bundle PASS;
Chrome desktop/mobile empty CTA, Enter/open, Escape/focus and real list recovery
verified. Empty API response was temporarily substituted in test tab, then cleared;
no client data changed. Details: PRIMARY-SESSION same ID. Implementation 0bda8890 pushed to origin/main;
remote SHA verified. CI status unverified: gh CLI unavailable. No deployment claimed.

CLIENTS-EMPTY-20261118 toolbar follow-up: Clients empty body now only CTA;
Appointments confirmed globally empty body retains Calendar in inner header.
Date-empty/filtered controls preserved. Build/types/i18n/bundle PASS; Chrome
empty response preview and Calendar navigation verified; no DB changes. Implementation
7340e5d6 pushed to origin/main, remote SHA verified. CI not verified (gh unavailable).

## DASHBOARD-REDESIGN-20261118

Implemented and locally verified: reference 1 with grouped attention from reference 3,
real scoped queues/finance and existing style. Build/types/bundle, 7 focused checks,
role/error/retry browser checks and desktop/tablet/mobile RU/KK/EN visual gate PASS.
No working DB changes or deployment. Implementation8f2c95a7 normal-pushed to main;
remote SHA matched. CI44369480025 in_progress at inspection. Details:
[checkpoint](docs/testing/task-state/PRIMARY-SESSION.md#dashboard-redesign-20261118).

## YCLOUD-HISTORY-20261119 - local preparation verified

YCloud entry for new CRM channels, Coexistence text history import, observed counts and retry are implemented. Isolated PostgreSQL dependent suite 116 PASS plus final focused 14 PASS; browser 18 PASS desktop/mobile, build/types/bundle PASS. No deployment or live number connection; partner approval, server configuration and handset history consent remain. Media content unavailable. Evidence: [YCloud preparation](docs/testing/evidence/ycloud-coexistence-20261109.md#2026-11-19-history-import-preparation).

GOOGLE-AUTH-20261119: deployed backend ac9a8d71 / frontend f43f2ba2 with Google entry on login and signup. Signup checks 36/36 PASS; immutable build/types PASS; real server Google callback reaches business/documents form. No real business created; full production registration/repeat-login remains pending. Evidence: docs/testing/evidence/google-auth-20261119.md.

AUTH-HALVES-20261119 follow-up: login/signup/forgot/reset/MFA form cards and contents
are shadow-free; keyboard outline retained. Desktop/mobile visual checks and build/
types/bundle PASS. Legal-document work paused by owner; no legal product edits.
Evidence: [checkpoint](docs/testing/task-state/PRIMARY-SESSION.md#auth-halves-20261119--shadow-free-forms).

GOOGLE-STATIC-BUTTON-20261119: generic Google buttons and silent idle renewal deployed on login/signup; responsive redraw preserves attempts. Focused48/48 and immutable build/types PASS, real server desktop/mobile chooser checks PASS. Google-only overlay2e423f3b on deployedf43; backendac9 unchanged. Evidence: docs/testing/evidence/google-auth-20261119.md.
