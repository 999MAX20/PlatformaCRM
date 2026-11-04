# C11 — завершение только текущей попытки экспорта

EXPORT-STALE-FINISH, локальная проверка 04.11.2026. Canonical
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
base `080da13450c91113f2ed292af48f21ffc383d0a9` +233 preserved foreign WIP entries.
[Контракт до изменений](../../../output/remediation-c11-20261104/CONTRACT.md).

## Поведение

ExportJob получает новый UUID claim_token при каждом claim/reclaim. Текущий
running/token проверяется при чтении попытки и в условном UPDATE успеха/ошибки.
Устаревший worker не меняет status, file, count, fingerprint, completed_at/error
нового результата; возвращает актуальную строку. Один непросроченный running job
не запускает генерацию повторно.

Каждая попытка пишет CSV с собственным token в имени. После проигранного UPDATE
или ошибки финализации удаляется только свой неопубликованный storage name.
Победивший файл остаётся доступным через существующий permission-checked download.
Файл и история старых exports не мигрируются/не удаляются. Internal token не виден
в API. Sanitization ошибки сохраняется и при conditional update.

Production: core/export_jobs.py и core/models.py; новая миграция core0013 добавляет
nullable UUID без backfill. Нет изменений UI, env, queue/retry policy, прав,
BusinessEvent/notification/AI. Row count и limits — отдельный открытый C26.

## Проверки

Команды: `.venv/Scripts/python.exe output/remediation-c11-20261104/<runner>` из
canonical root; exact labels в commands.json. isolated_runtime/safe bootstrap,
disposable SQLite/native PostgreSQL17 и private temporary local storage; dotenv,
внешние sockets/providers отключены. Dependencies не переустанавливались.

- `run_checks.py baseline apps.core.tests_export_attempts`:3 tests,2 FAIL/1 PASS.
  Старый success заменял файл нового worker, старый failure менял новый success
  на failed. Обычная ошибка и explicit requeue служили успешным контролем.
- `run_checks.py focused apps.core.tests_export_attempts apps.core.tests_export_access apps.core.tests_export_history`:
  20 PASS сразу после coherent claim/finalization slice.
- `run_checks.py expanded apps.core.tests_export_attempts.ExportAttemptTests apps.core.tests_export_attempts.ExportAttemptMigrationTests`:
  7 PASS. Reclaim после фактического storage save удаляет только losing output;
  ошибка DB finalization не публикует файл и удаляет его; повтор живого claim
  не генерирует второй CSV. Реальный API detail скрывает token, download отдаёт
  winning bytes. Обратная/прямая миграция сохраняет старые status/file/count/params/
  created_at, новый token null.
- `run_pg.py apps.core.tests_export_attempts`:9 PASS,0 SKIP. Два соединения/worker:
  старый остановлен при генерации, новый reclaim/commit завершается первым;
  старый success/failure не меняет новый результат. Файлы старой успешной попытки
  удалены, winning file сохранён. Также migration и все scoped attempts.
- `run_checks.py completion` с labels из commands.json:32 PASS. Entity/report/
  workspace background exports, private download, permission/tenant/history,
  revoked field/Client access, existing synchronous CSV/formula checks и attempts.
  Django check PASS; makemigrations --check --dry-run: no changes.

В гонках подменена генерация CSV управляемыми байтами; реальные claim/DB/storage/
finalization и API не заменены. Остальные проверки строят экспорт из реальных
тестовых сущностей. PostgreSQL data_directory/port и сессии проверены, собственная
test DB удалена, кластер остановлен. Initial FAIL сохранены без переписывания.
Нет browser/build/full-project/live/storage-provider gate: UI не менялся,
затронутый reachable API проверен напрямую; это scoped local acceptance.

## Граница

WorkingDB hash unchanged; dev8000/5173 выключен. Миграция только disposable DB.
При отдельном rollout нужно применить миграцию к разрешённому target и завершить/
остановить старые workers: прежний код не знает проверки token. Deployment не выполнен.
Удаление unpublished output — best effort; storage deletion error логируется и
не перезаписывает победителя. Авария процесса/недоступность внешнего storage могут
оставить приватный orphan; crash reconciliation и live-storage здесь не сертифицированы.

Foreign WIP233 сохранён. Integrations/operations/passport/plan/evidence согласованы;
Пустой stale index.lock перемещён после повторных no-Git-process проверок,
exclusive-open и подтверждения неизменного index SHA (lock-recovery.json).
README/product/CRM/access/AI/frontend/roadmap не требуют изменения при прежних setup,
правах и бизнес-процессах. Исторические отчёты не переписаны. В scoped C11 нет
code/evidence остатка. Собственный local commit, без push/merge/newCI/deploy.
C12 не начат. C05 retained temp folders не трогались. Source hashes, checks,
сохранность и commit — output/remediation-c11-20261104/final-validation.json.
