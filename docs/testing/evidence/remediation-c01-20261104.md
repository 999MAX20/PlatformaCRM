# C01 — безопасный запуск проверок и валидный recovery drill

Задача: следующий цикл C01 (UI31/VERIFY02) и остановка dev по поручению владельца
04.11.2026. Каноническая папка `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, исходный HEAD `615545987df2e7b6da11aeba3d7d3a3ab81524f7`
с сохранённым чужим WIP. Контракт до реализации и исходный снимок:
`output/remediation-c01-20261104/CONTRACT.md`, `starting-status.txt`.

## Изменение и граница

Диагностические helpers отказываются от запуска до migrate/seed без явно
изолированной БД и выделенных loopback-портов. Python bootstrap повторяет guard,
собирает safe environment, запрещает загрузку рабочей `.env` и внешние socket
connections; тестовый connector key/media остаются внутри временной папки.
Audit helpers не используют существующие серверы и завершают свои процессы
при ошибке подготовки/запуска браузера. Отсутствующее, disabled или failed
обязательное действие и API5xx теперь дают FAIL; skipped-submit остаётся явно
неисполненным действием, не доказательством проверки записи.

В S04 удалены невалидный `_s04_hold` из action config и несуществующий assignee.
Идентификаторы валидных действий задают точки сбоя отдельным временным manifest:
crash после эффекта до commit, transient exception до выполнения действия,
затем release и повтор без изменения business config. Production validation,
права, lifecycle и assertions exactly-once не ослаблены.

Остановлены только проверенные dev-процессы CRM: Python1112/23248/16976/24520,
Node16916. Источники/root подтверждены до остановки; порты8000/5173 освобождены.
Доказательства: `dev-roots.json`, `dev-stopped.json` в папке результатов.
Dev не перезапускается. Нет working-DB migrations, внешних отправок, push/merge/deploy.

## Проверки

- `node --test frontend/scripts/tests/audit-runtime.test.mjs`:7 PASS. Включены
  непосредственный отказ трёх entrypoints с рабочей DB, отказ обоих audit helpers
  на занятом TCP-порту без HTTP health, action/503 negative controls.
- `.venv/Scripts/python.exe -m unittest scripts.tests.test_browser_test_runtime`:
  4 PASS: отказ без побочных эффектов, safe env/key, Django без dotenv, запрет
  внешних connect/connect_ex, прямой отказ Python entrypoints.
- `.venv/Scripts/python.exe -m unittest scripts.tests.test_recovery_faults`:
  4 PASS: валидное действие, точка crash после эффекта, transient/release,
  отсутствие воздействия на другое действие.
- Зависимый Python pack вместе с `scripts.tests.test_codex_verify`:23 PASS.
  Node pack включает `gate-env.test.mjs` в safe environment;7 named tests PASS,
  gate-env выполняет top-level assertions. Лог `dependent-checks.log`.
- `.venv/Scripts/python.exe scripts/verify_recovery_s04.py --phase queue --pg-bin
  "C:/Program Files/PostgreSQL/17/bin" --redis-server
  "output/crm-s04-20261014/deps/redis/Redis-7.4.9-Windows-x64-msys2/redis-server.exe"`:
  exit0. Реальные PG17/Redis7.4.9/Celery solo на Windows: restart/wait-resume,
  duplicate dispatch, kill внутри транзакции, rollback/stale claim/exactly-once,
  cancel/retry, role/tenant denial, transient resume, notification replay PASS.
  `output/crm-s04-20261014/runtime-1793771216725887700.log` и соответствующий
  `.worker.log` сохраняют намеренный RuntimeError и штатное завершение PG/Redis.
  Точные байты обоих логов сохранены также в `output/remediation-c01-20261104/`
  как `recovery-runtime.log.gz` и `recovery-worker.log.gz`; SHA256 — в
  `recovery-log-copies.json`. Исходные логи не нормализованы ради diff hygiene.
- `.venv/Scripts/python.exe output/remediation-c01-20261104/verify_helpers.py`:
  общий Node→Python prepare/serve, disposable migrations/fixture, HTTP health,
  реальный CSRF/login, system check/migration drift и cleanup: финальный exit0,
  все PASS в `helper-results.json`. Рабочая DB SHA256 неизменна относительно начала:
  `7612cbd5b2ac840ea38b93fa267d3abd0ce26e6f5846f5e4035bbda4b1677c38`.

В первом интеграционном harness пропущен CSRF bootstrap: HTTP403, серверная
защита сработала. Во втором harness соединение SQLite не закрывалось контекстным
менеджером SQLite: проверки поведения PASS, cleanup WinError32. Исправлен сам
harness (`closing`), исходные логи сохранены с суффиксами failure. Ручное удаление
оставшейся временной папки `zani-quality-gate-4ffdi273` отклонено автоматической
проверкой разрешений; папка оставлена. Это остаток одноразовой среды, не рабочая БД.

Полный browser audit, frontend build/types, установка зависимостей, весь backend,
ClamAV/backup/full S04, Linux/production/live не запускались: изменены только
verification helpers, fixture/fault injection и docs; UI/product/domain/dependencies
не менялись. Предыдущие ошибки общих аудитов и CI не превращены в PASS. C01 не
сертифицирует актуальность всех route/action inventories старых UI helpers.

## Документы и остаток

Testing contract и строка C01 в плане обновляются вместе с этим evidence.
Продуктовые CRM/access/AI/frontend/operations contracts, паспорта и README не
меняются: API, продуктовые данные/права, notification/BusinessEvent/AI, deployment
и release acceptance не затронуты. Исходные аудиты сохранены без переписывания.
Следующий отдельный цикл — C02; это поручение его не запускает.

Код и доказательства C01 закрыты локально. Остаток среды — только названная
одноразовая папка неуспешного harness; её очистка не была разрешена инструментом.
Решений владельца по реализации C01 не требуется. Публикация/новый CI/deployment
не выполнялись по заданной границе. Локальный commit и исходные hashes записываются
в `output/remediation-c01-20261104/final-validation.json`.
