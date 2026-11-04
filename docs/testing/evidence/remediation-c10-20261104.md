# C10 — очистка сохраняет продлённые записи команд

IDEMPOTENCY-PRUNE, локальная проверка 04.11.2026. Canonical
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
base `fa8a12b2c964cec98078dba77dfc9a8f10e4ac0d` +233 preserved foreign WIP entries.
[Контракт до изменений](../../../output/remediation-c10-20261104/CONTRACT.md).

## Изменение

Выборка просроченных ID и DELETE выполняются раздельно. Между ними реальная команда
могла заново захватить receipt, продлить expires_at и даже сохранить успешный
результат, после чего очистка удаляла обновлённую запись. Повторный запрос терял
защиту от дублирования операции.

DELETE теперь содержит expires_at <= исходный cutoff вместе с выбранными ID.
Продлённые processing/succeeded receipts остаются, неизменённые просроченные
удаляются. Выборка/порядок/лимит (максимум5000), retention, tenant/actor/key scope,
Celery task envelope и API не менялись. Production delta — одна строка
apps/core/idempotency.py; новый файл тестов tests_idempotency_prune.py.
Нет model/migration/env/UI/notification/BusinessEvent/AI policy изменений.

## Доказательства

Команды запускались `.venv/Scripts/python.exe` из canonical root. Runners в
output/remediation-c10-20261104 используют isolated_runtime и safe bootstrap,
одноразовые SQLite/native PostgreSQL17, отключённые dotenv/providers/external sockets.

- `run_checks.py baseline apps.core.tests_idempotency_prune.IdempotencyPruneTests`:
  3 tests, **2 FAIL/1 PASS** на старом production коде. Реальные begin/run обновляют
  receipt после выборки ID; прежний DELETE удаляет его. Контроль границы/лимита проходит.
- Та же команда с phase `focused` после исправления: **3 PASS**. Processing claim
  сохраняет новый token/attempt; successful replay возвращает прежний Task без второго
  создания. Проверены <=cutoff, будущая строка, limit1, zero/negative limit и empty.
- `run_checks.py completion` с labels из commands.json: **23 PASS**. Дополнительно
  existing command conflict/reclaim, actor/business isolation, failed-command retry,
  record commands/current permissions/tenant/rollback/replay. `check` PASS,
  `makemigrations --check --dry-run`: no changes.
- `run_pg.py apps.core.tests_idempotency_prune apps.scheduling.tests_record_concurrency`:
  **8 PASS,0 SKIP**. Worker выбирает expired IDs и останавливается перед настоящим
  DELETE; другое соединение выполняет реальную команду/Task и commit; worker удаляет
  только unchanged control. Replay возвращает тот же результат, Task ровно один.
  Дополнительно реальные record slot/idempotency/lifecycle races. Пауза внедрена
  test hook вокруг QuerySet.delete, DB-операции не заменены mock.

Исходные FAIL сохранены; production после focused не менялся. Scoped gate не
является full-project/release/live PASS. Browser/build не запускались: UI и contracts
frontend не затронуты. Модель/provider и рабочие внешние сообщения не вызывались.

## Граница завершения

WorkingDB hash unchanged, dev8000/5173 выключен. PostgreSQL data_directory/port
проверены, собственная test DB удалена, кластер остановлен; изолированные runtimes
очищены. Dependencies не переустанавливались. C05 retained folders не трогались.
Git staging дважды встретил занятый индекс; чужие Git процессы не останавливались.
После их завершения оставшийся пустой lock перемещён при повторных no-process
проверках, exclusive-open и неизменном index SHA; сохранены два recovery receipts.
Foreign source hashes и233 исходных Git entries сохранены; docs индексированы
только собственными изменениями. Diff/link/secret/committed-range checks и точные
SHA — source-manifest/final-validation в output/remediation-c10-20261104.

Plan/CRM/operations/passport/evidence согласованы. README/product/access/AI/frontend/
integrations и общий roadmap не требуют изменения: setup, права и бизнес-сценарии
прежние; исторические отчёты не переписаны. В C10 нет scoped code/evidence остатка.
Собственный локальный commit; без push/merge/newCI/deploy/live. C11 не начат.
