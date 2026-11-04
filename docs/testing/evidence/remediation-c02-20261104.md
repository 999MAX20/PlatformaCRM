# C02 — права источника Leads в team performance

**Закрыто локально**, 04.11.2026. Пользователь разрешил следующий цикл после C01;
C03 не начат. Canonical `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, base `704d4663729e288be6c3c8c3ee4897f15031e18a` + сохранённый WIP.
Контракт до правок: `output/remediation-c02-20261104/CONTRACT.md`.

## Результат

`GET /api/team/performance/` теперь пересекает исходную выборку Lead по Business
и участникам отчёта с действующим LEADS VIEW scope и capability до группировки.
Повторно использованы `scope_queryset` и `resource_is_enabled`; новых прав или
permission framework нет. Denied/module-off возвращает прежний формат с нулями
и пустыми списками причин потери. Own/team/business не расширяет доступный состав
участников. Отзыв/восстановление доступа действует на следующий запрос.
Сохранены period/source filters и независимо читаемые показатели других ресурсов.

Устранена TEAM-ANALYTICS в подтверждённой Lead-границе: счётчики, статусы, проценты,
loss reasons и производные сводки команд. Другие source metrics этого endpoint
не сертифицированы этой задачей. Исторический аудит не переписан.
Файл `apps/businesses/views.py` был чистым; чужие analytics views/crm_metrics/reports
и tests_resource_visibility не изменены. Изменение source — imports и четыре
строки guard перед существующими date/source filters.

## Доказательства

Все команды запускаются `.venv/Scripts/python.exe` через
`output/remediation-c02-20261104/run_checks.py`. Runner использует
`scripts.codex_verify.isolated_runtime`, C01 guarded Python bootstrap, одноразовую
SQLite, safe environment без рабочей dotenv/внешних socket connections.

1. `run_checks.py baseline`:10 tests,6 PASS/4 FAIL. До исправления воспроизведены
   denied source, disabled module, own scope inside team report и permission revocation.
2. `run_checks.py focused`:10 PASS после изменения. Проверяются allowed control,
   deny/module-off, own/team, сохранение report membership/source filter,
   foreign-Business403/отсутствие foreign reason, analytics permission, inactive member,
   восстановление capability/permission и пустые Lead aggregates команд.
3. `run_checks.py completion apps.businesses.tests_team_source_visibility
   apps.businesses.tests_access
   apps.core.tests_b5_performance.BackendPerformanceRegressionTests.test_team_performance_query_count_does_not_scale_with_team_size
   apps.core.tests_b301_performance.B301MeasuredPerformanceTests.test_performance_surfaces_preserve_tenant_boundaries`:
   **54 PASS**, system check и migration drift PASS. Включены существующие owner/
   team/operator controls и лимит SQL queries при13 участниках, без изменения порога.

Логи baseline/focused/completion сохранены в папке результатов; точные копии
`.log.gz` включены в локальный commit, SHA256 исходных логов — в source-manifest.json.
UI/build/types,
весь backend/E2E, PostgreSQL concurrency и live не запускались: изменён read-only
backend queryset без UI/schema/mutations; применены focused/dependent gates.
Это локальная проверка со всем исходным WIP, не release или production PASS.
Прежние общие audit/CI failures не закрываются этой проверкой.

## Сохранение и остаток

Рабочая DB неизменна по SHA256; dev8000/5173 остаётся выключенным. Нет миграций
рабочей DB, внешних отправок, notification/BusinessEvent/AI/lifecycle изменений.
Обновлены C02 plan row, access contract, capabilities passport, STATUS/checkpoint
и registry. CRM/frontend/operations/AI contracts и README не требуют изменения:
их workflow/setup/data/API shape не менялись. Исходные аудиты неизменны.

Код и доказательства в scope C02 закрыты; среды или решений владельца для C02
не требуется. Чужой WIP сохранён. Только собственный локальный commit; без push,
merge, deployment и нового CI. SHA/ownership/diff checks и source hashes:
`output/remediation-c02-20261104/final-validation.json`.
Следующий отдельный цикл — C03.
