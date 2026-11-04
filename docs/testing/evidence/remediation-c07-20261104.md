# C07 — чувствительные URL в frontend monitoring

**Исправлено и проверено локально**, FU-FE-02, 04.11.2026. C08 не начат.
Canonical `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
base `f928d0f1424ed86842d0f36f28a7256bdb3dba99` + preserved233 foreign WIP entries.
[Контракт до изменений](../../../output/remediation-c07-20261104/CONTRACT.md).

## Результат

Optional Sentry/PostHog/Plausible больше не отправляют bearer-части маршрутов
`/reset-password/:uid/:token`, `/invite/:token` и
`/api/team/invitations/preview/:token` в проверенных payload. Общий sanitizer
обрабатывает URL внутри вложенных объектов/массивов/ключей, сообщений и кодированных
значений. URL заменяется шаблоном без query/hash после чувствительного пути.
Обычные URL, числа, контекст и события сохраняются; объект вызывающего кода не меняется.
Repeated references сохраняют содержимое, циклы/depth limit безопасно обозначаются.

Sentry очищает final error/transaction/span/breadcrumb hooks, включая автоматически
добавленные request.url/Referer и span URL attributes. PostHog before_send очищает
уже обогащённые события; session replay выключен. Независимое candidate review
нашло отдельный flags канал вне before_send; parent воспроизвёл его реальным SDK
в Chromium. Неиспользуемые flags/remote-config и feature-flag reload отключены,
включая отправку ранее сохранённых initial URL/referrer. В приложении нет потребителей
PostHog flags; обычный capture/autocapture сохранён. Не включать эти каналы без
отдельной URL-confidentiality проверки.

Plausible использует legacy manual script, явный очищенный URL для initial/SPA/custom
events и bounded queue до загрузки. Если document.referrer содержит чувствительный
маршрут, tracker не запускается весь срок жизни документа: этот SDK не поддерживает
override referrer. На обычной следующей загрузке без такого referrer analytics доступна.
Существующий чужой tracker не переопределяется и не используется этой обёрткой.

Изменены `monitoring.ts`, новые `telemetryPrivacy.ts`, `plausibleMonitoring.ts` и
два focused regression tests. Публичные функции приложения и env names сохранены.
Нет изменений UI copy/layout, API, schema, ролей/tenant, BusinessEvent/notification/AI.

## Проверки и попытки

- BEFORE `node output/security-frontend-followup-20261027/monitoring-url-reproducer.cjs`:
  установленный Sentry HttpContext передал synthetic reset token в request.url,
  zero network. Log `output/remediation-c07-20261104/sdk-baseline.log.gz`.
- AFTER `node --test frontend/scripts/tests/telemetry-privacy.test.mjs frontend/scripts/tests/telemetry-sdk-browser.test.mjs`:
  **20 PASS,0 FAIL,0 SKIP**. Raw/relative/case/escaped/encoded/nested/whitespace/malformed
  routes; обычные URL и props; null/Date/cycles/repeated refs/no mutation/depth;
  disabled providers, delayed/repeated init, hooks; Plausible queue/SPA/back/pageshow,
  sensitive-referrer suppression, ordinary controls.
- Actual Chromium SDK pipeline: Sentry10.56.0 + PostHog1.379.3, real automatic
  request/referrer/current_url/initial props, exceptions/breadcrumbs/transaction/spans,
  manual events/pageview/autocapture. All outgoing requests fulfilled in memory.
  Synthetic tokens absent from emitted payload; normal /clients/42 and count retained.
  Zero flags requests on startup, explicit reload and document reload with persisted info.
- Actual legacy Plausible manual v37 snapshot executed in Chromium with all requests
  intercepted: ordinary referrer1 script/6 events, safe pageview/custom/engagement/SPA;
  sensitive referrer0 scripts/0 events. Source SHA256
  `83b7338c1ef8e609c5a530233fa3fafffaf4cd9387da7d56c5a3c9b3e0e991df`.
  Managed artifacts for target PlatformaCRM: `artifacts/c07/plausible-probe.cjs`,
  `plausible-manual.js`, `plausible-validation.md`, `independent-review.md`, `fix-report.md`.
  Public script download was read-only; synthetic ingestion requests never left browser.
- Initial browser harness attempts failed because page.goto did not supply a referrer,
  then PostHog filtered automation. Harness now explicitly supplies synthetic referrer
  and disables user-agent filtering only inside test; production filter unchanged.
  Subsequent actual FAIL revealed flags leakage; production config fixed and rerun PASS.
  No failed assertion was weakened. Review used one independent candidate cycle.
- `.venv/Scripts/python.exe output/remediation-c07-20261104/run_build.py`:
  safe isolated `npm run build` **PASS**, TypeScript/i18n6682/app/widget bundles.
  Installed dependencies reused; no local reinstall.
- Scoped working/index/committed-range diff hygiene, links/registry and intended
  content/secret-pattern review: see final receipt and source-manifest.
  Local save initially met stale empty index.lock; two no-Git-process checks,
  exclusive open and unchanged index hash allowed reversible lock move. Receipt:
  `output/remediation-c07-20261104/lock-recovery.json`.

## Границы и остаток

No workingDB connection/write or working migration. Dev remains off; temporary browser
contexts closed. Build uses isolated_runtime. No backend/PG/full-project/native/live
provider suites: this is client telemetry payload behavior, no CRM or server change.
Backend Sentry/other log handlers and arbitrary unlabeled secrets remain outside scope.
Remote provider accounts/configuration and future changes of unversioned Plausible
script are unverified; local proof is not deployed readiness or universal PII scanning.

Plan, frontend/operations contracts, operations passport and evidence agree.
Other domain/access/AI/integration contracts and README need no change: server/setup
env names/public APIs and business workflows unchanged. Historical audit reports
remain intact. C07 has no code/evidence/environment/owner-decision remainder in this
scope. Own local commit only, no push/merge/deploy/newCI. Previous C05 temp-directory
cleanup limitation unchanged. Final receipt:
`output/remediation-c07-20261104/final-validation.json`. Next C08 unstarted.
