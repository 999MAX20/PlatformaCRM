# C05 — честное завершение сессии

Закрыто локально: UI13, 04.11.2026. C06 не начат.
Canonical `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
base `112358d77dae0c0d148e9d9bc87e2cc782d90f91` + preserved foreign WIP. Pre-edit contract:
[CONTRACT](../../../output/remediation-c05-20261104/CONTRACT.md).

## Поведение

Выход ожидает успешный POST logout с актуальным CSRF. До ответа сохраняет сессию
и показывает выполнение; при 503/network failure остаётся на текущем экране с
постоянным RU/KK/EN сообщением: выход не завершён, сессия может оставаться активной,
и кнопкой повтора. Ошибка не выдаётся за успешный выход. Reload получает фактическое
состояние cookie/server session; ошибка не сохраняется как новый persistent marker.
Потерянный ответ не доказывает ни успех, ни отказ сервера — текст намеренно условный.

Успех очищает access/identity и существующий offline Lead cache через tokenStorage,
рассылает logout другим вкладкам и завершает UI-сессию. Очистка выполняется внутри
существующей cookie queue до освобождения lock; queued refresh старого generation
не отправляется. Logout старой generation не отзывает новую сессию. Повторные клики
во время запроса single-flight. Обычная expiration/broadcast убирает старую ошибку.
Platform menu больше не переходит на Login до результата. Merchant Account и
wrong-account invitation используют общий provider без изменения их чужого WIP.

Серверная политика отзыва, права, Business isolation, schema/migrations,
notifications/BusinessEvent/AI и внешние отправки не менялись. Shared StatusNotice,
Button и recovery placement переиспользованы; редизайна нет.

## Проверки

- Исходный дефект: retained audit UI13, injected logout503 → Login → reload
  возвращает cookie session. [Историческое доказательство](../../../output/full-audit-20261104/ui/logout-recovery.json).
- `node --test frontend/scripts/tests/token-csrf.test.mjs`:8 PASS.
  CSRF bootstrap/credentials, failed503/network/retry, pending identity,
  queued refresh cancellation, old-generation logout cancellation.
- `node --test frontend/scripts/tests/token-csrf.test.mjs frontend/scripts/tests/auth-request.test.mjs frontend/scripts/tests/auth-return-path.test.mjs frontend/scripts/tests/lead-offline-storage.test.mjs frontend/scripts/tests/lead-offline-commands.test.mjs`:31 PASS.
- `.venv/Scripts/python.exe output/remediation-c05-20261104/run_browser.py`:
  41 PASS,11 SKIP (existing session-persistence intentionally desktop-only).
  Four specs: logout-recovery, logout-callers, session-cache-isolation,
  session-persistence; desktop1280x720/mobile412x839 Chromium. Real isolated
  backend/SQLite, cookie/CSRF/login/logout; injected failures only at named endpoints.
  New logout flow: RU/KK/EN503/network, reload before/after success, keyboard retry,
  duplicate click, pending and sibling tab; platform menu and invite caller.
  Invitation preview synthetic; its server domain behavior not certified here.
  Existing session/account-switch/late-response/cache/refresh/restart tests retained.
- `.venv/Scripts/python.exe output/remediation-c05-20261104/run_browser.py e2e/logout-cross-tab.spec.ts`:
  ещё2 PASS (desktop/mobile): ошибка первой вкладки исчезает после подтверждённого
  выхода во второй; reload не восстанавливает завершённую сессию. Итого43 browser PASS.
- `.venv/Scripts/python.exe output/remediation-c05-20261104/run_build.py`:
  safe-environment `npm run build` PASS, TypeScript/i18n6682/app/widget PASS.
  Repeated only after final expiration-error cleanup change.
- Scoped diff/index/committed-range hygiene, intentional paths/links and secret
  pattern review PASS; source/log/screenshot hashes in source-manifest.json.

Первый browser run остановлен после fixture ошибок: профиль возвращал RU вместо
localStorage KK/EN, затем loopback login rate limit429. Исправлена подготовка языка
через настоящий isolated profile API; отдельный backend wrapper устанавливает
только тестовый auth_login1000/min в safe environment. Рабочие production rates
не менялись, rate-limiting acceptance здесь не заявлена. Initial log сохранён.
Второй run обнаружил перенос языка профиля в зависимые tests; подготовка теперь
возвращает RU после localized case. Старый тест pending refresh ожидал Login до
logout response; теперь явно проверяет текущий account/pending, затем завершает
refresh → logout → login. Pending refresh разрешается до logout, queued refresh
после logout отменяется (Node proof); порядок и межаккаунтная изоляция сохранены.
Final run использует исправленную подготовку и новый контракт ожидания выхода.

Изоляция: existing isolated_runtime + guarded browser bootstrap, unique temporary
SQLite/loopback ports, dotenv/provider/external socket suppression. Dev8000/5173
выключен, working db hash unchanged. Browser screenshots содержат только synthetic
seed data. Build reused installed locked dependencies. No backend/full-project/PG/
live/native test gate: no backend/domain/schema/concurrency implementation change.
Existing unrelated failed gates остаются открытыми; это не release PASS.

## Закрытие и границы

Plan ↔ frontend contract ↔ identity passport ↔ evidence согласованы. Access/CRM/AI/
operations/integration contracts и README не требуют изменений: серверные политики,
настройка и запуск прежние. Полный аудит/исторические отчёты не переписаны.
В продуктовом C05 нет остатка кода/доказательств/решений владельца.
Операционный остаток: удаление двух прерванных временных test folders заблокировано
автоматической политикой; папки оставлены, процессы остановлены. Собственный локальный
коммит; без push/merge/deploy/нового CI. Foreign WIP сохранён. Final receipt:
`output/remediation-c05-20261104/final-validation.json`. C06 не запущен.
