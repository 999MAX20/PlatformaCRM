# C08 — согласованные условия автоматической записи

**Исправлено и проверено локально**, CRM-TERMS01/BOT-ZERO-PRICE, 04.11.2026.
Canonical `C:/Users/user/Desktop/PlatformaCRM`, `codex/ui-testing-toolkit`,
base `64e9f2ce8147001c3c99c1f87fab84d80e065531` +233 preserved foreign WIP entries. C09 не начат.
[Контракт до изменений](../../../output/remediation-c08-20261104/CONTRACT.md).

## Поведение

Варианты автоматической записи без филиала теперь сохраняют price_from и
duration_minutes. При подтверждении эти условия сравниваются с текущим
appointment_snapshot непосредственно в create_appointment_from_conversation
до проверки availability и любых эффектов создания. Проверка применяется к
филиалам и бизнесам без филиала. Цена null отличается от0.00; нулевая цена в
AI service context остаётся строкой0.00, прежнее отсутствие остаётся пустым.
Старые варианты без одного из полей требуют нового согласования. Их цена не
восстанавливается из текущего каталога задним числом.

Несовпадение возвращает существующий requires_staff; полный pipeline использует
прежнюю безопасную передачу администратору без подтверждения устаревшей записи.
Не создаются Appointment, creation audit/activity/followups/confirmation; Lead
не меняется. Уже успешный replay возвращает исходную запись, даже если прайс
позже изменён; повторная авторизация остаётся обязательной. Legacy ручные callers
без expected_terms сохраняют прежнюю совместимость. Политика прав/tenant не менялась.

Для автоматической записи Service удерживается под row lock до конца транзакции:
каталог не может изменить цену/длительность между сверкой и созданием. Филиальный
save_offer уже сериализован Business lock. PostgreSQL выявил старые недопустимые
FOR UPDATE над nullable outer joins в booking и общем conversation pipeline.
Блокировка ограничена строкой беседы через of=(self); существующая Business
блокировка автоматического сценария сохранена. Это необходимая поправка проверяемого
booking/handoff пути, не переработка pipeline или реализация C09.

Production files: bots/scheduling_context.py, conversations/booking.py и
conversations/pipeline.py. Existing automatic-booking fixture теперь содержит
реальные поля нового предложения. Добавлены tests_booking_terms.py и
tests_booking_terms_concurrency.py. Нет frontend/schema/migration/env изменений.
BusinessEvent/notification создание не добавлялось: этот отдельный остаток — C09.

## Проверки

Все команды ниже запускались `.venv/Scripts/python.exe` из canonical root.
Runner `output/remediation-c08-20261104/run_checks.py` использует isolated_runtime,
safe bootstrap, disposable SQLite, отключённый dotenv и внешние sockets/providers.

- `run_checks.py baseline apps.bots.tests_booking_terms`:8 tests,
  **6 failing methods/7 assertions,2 PASS** на исходном production коде.
  Stale price/duration, missing terms, null→zero, lost context zero, absent slot terms.
- `run_checks.py focused apps.bots.tests_booking_terms apps.bots.tests_automatic_booking apps.branches.tests_bot`:
  **21 PASS** сразу после согласованного service/context изменения.
- `run_checks.py expanded apps.bots.tests_booking_terms`: **13 PASS**.
  Добавлены pipeline handoff, revoked actor, foreign service, final-point recheck и
  branch duration. Existing suites покрывают branch price/selection, availability,
  undelivered/reconfigured offer и полный delivered offer→customer choice→booking.
- `run_checks.py completion` с labels из `commands.json`: **48 PASS**;
  затем Django `check` PASS и `makemigrations --check --dry-run` — no changes.
  Включены runtime config, disabled-capability/tenant Inbox guards, действующие
  manual/API booking, invalid lead transition и API idempotency.
- `run_checks.py final-focused apps.bots.tests_booking_terms apps.bots.tests_automatic_booking apps.branches.tests_bot`:
  **26 PASS** после PostgreSQL booking-lock поправки.
- `run_pg.py apps.bots.tests_booking_terms_concurrency apps.bots.tests_booking_terms apps.bots.tests_automatic_booking apps.branches.tests_bot apps.bots.tests_controlled_creation`:
  **36 PASS,0 SKIP** на финальном source, native PostgreSQL17 в новом loopback cluster.
  Проверен реальный row lock: конкурентный UPDATE получает lock timeout во время
  сверки/создания; после commit UPDATE проходит, booked snapshot остаётся100.00.
  Проверены реальный booking/handoff/replay и дополнительные consumers общего lock:
  controlled creation, отозванное согласие/actor/tools, публичный intake.
  Initial PG14:13 errors (booking nullable join); second PG14:13PASS/1ERROR
  (pipeline nullable join); оба FAIL сохранены. Final PG36 после обоих исправлений.
  SQLite checks не доказывают PG-lock; финальный PG прогон закрывает эту границу.
  System check повторён PG runner; migration check переиспользован — model inputs
  не менялись после него. Остальные неизменённые зависимые проверки не повторялись.

AI classification/reply и внешняя доставка заменены controlled test doubles;
реальная БД/домен/API остаются настоящими. Не отправлялись реальные сообщения,
не вызывались модели/providers. Existing safe handoff template использован без
нового текста UI. Нет browser/build/i18n/full-project/live/native gate: frontend
не изменён, reachable backend/pipeline/API проверены непосредственно.

## Сохранность и граница

WorkingDB hash unchanged; dev8000/5173 остаётся выключен. Собственные test DB/PG
sessions проверены по data_directory/port, disposable test DB удалена, PG остановлен,
isolated runtimes очищены. Старые retained folders C05 не трогались. Dependencies
не переустанавливались. Exact logs compressed; source hashes, commands, DB/ports,
foreign WIP и final commit/range hygiene — source-manifest/final-validation здесь:
`output/remediation-c08-20261104/`.
Local save: stale empty index.lock moved after two no-Git-process checks,
exclusive-open and unchanged index SHA verification (`lock-recovery.json`).
Initial diff-hygiene FAIL for a trailing blank line in PG helper fixed; recheck PASS.

Plan, CRM/AI contracts, customer-AI/scheduling passports и evidence согласованы.
Access/operations/integrations/product/frontend/README не требуют правки: политика,
API shape ручной записи, env/setup и интерфейс не менялись. Исторические reports
не переписаны. В C08 нет scoped code/evidence/environment/owner-decision остатка.
Без push/merge/deploy/newCI; только собственный локальный commit. Live channel/model
и deployment не сертифицированы. Следующий C09 остаётся отдельным не начатым циклом.
