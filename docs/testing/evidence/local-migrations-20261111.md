# Локальные миграции — 11.11.2026

Пользователь явно поручил сделать backup, применить три ожидающие миграции
к локальной БД и проверить работу. Каноническая папка PlatformaCRM, ветка
codex/ui-testing-toolkit, продуктовый HEAD4895a3b7; продуктовый код не менялся.
Цель проверена через scripts.local_postgres.validate_database:
PostgreSQL127.0.0.1:55432/platformacrm, development, роль crm_app.
Чужие изменения STATUS/PRIMARY и две прежние stat-only записи сохранены.

## Backup и безопасное применение

Snapshot-consistent pg_dump custom format создан до изменений. Backup:
`output/local-migrations-20261111/pre-three-migrations-1794398089570564500.dump`.
Размер 1009993bytes, SHA256 `6844f53ec1ea6bc22df62ff8d0a2ac8da96cc3c81516b3ac28cfe724bf3b8f57`.
Восстановление в отдельную БД проверено по схеме и хешам всех строк:
154таблицы/9855строк совпали. В этой копии сначала выполнены те же три миграции
с проверкой сохранности прежних колонок. Одноразовая restored DB удалена,
исходный dump сохранён. Backup содержит рабочие данные и остаётся локальным ignored artifact.

Применены только:

- bots.0014_historical_delivery_resolution;
- integrations.0009_historical_delivery_resolution;
- integrations.0010_ycloud_coexistence.

Первые две меняют choices статусов; никаких исторических сообщений/connector runs
не разрешают и не повторяют. Третья добавляет onboarding_type и expected_phone_number.
Рабочая операция выполнена атомарно, с проверкой точного migration plan и
сравнением всех прежних колонок до commit:153таблицы данных/9662строки неизменны.
Отдельный django_migrations изменился только ожидаемым применением. В рабочей БД
нет YCloudConnection; существующие подключения не создавались и provider setup
не запускался. Поля/defaults проверены в schema/rehearsal и на синтетических данных тестов.

## Проверки после изменений

- 27изолированных PostgreSQL tests PASS за61.293s: historical resolution,
  YCloud coexistence и concurrency. Test DB создана/удалена штатным runner;
  внешние провайдеры замоканы, рабочая БД не использовалась для tests.
- Django system check и migration drift PASS; ожидающих миграций нет.
- Пять реальных read-only API views на рабочей БД200: clients, appointments,
  inbox/conversations, business-connectors, connector-sync-runs. Авторизация
  проверена через in-process force_authenticate; это не новый пользовательский login.
- ORM корректно читает новые поля YCloud; counts16messages/4connectors/1sync run
  совпадают с сохранёнными данными. WhatsApp channel отсутствует, live setup GET
  не проверялся; его контракт покрыт изолированными тестами.
- Live backend /health/200, frontend200, proxy /api/auth/me/401 без авторизации.
- Chromium открыл /login: поле пароля видно, uncaught JS errors нет.
- Повторный ./dev.ps1 завершился0: Redis/scanner/updater/worker/backend/frontend
  проверены и переиспользованы, без предупреждений о миграциях.

Команды, логи, SHA и результаты: `output/local-migrations-20261111/`:
`migrate_local.py backup`, `migrate_local.py apply`, `backup-receipt.json`,
`migration-result.json`, `focused-postgres.log`, `smoke-result.json`,
`browser-smoke.log`, `dev-final.log`. Focused command:
`.venv/Scripts/python.exe output/performance-20261106/verify.py
apps.core.tests_historical_resolution apps.integrations.tests_ycloud_coexistence
apps.integrations.tests_ycloud_coexistence_concurrency`.

Остатка в согласованной локальной операции нет. Dev-сервисы оставлены работающими.
Full E2E/build/installation не повторялись: source/dependencies не менялись,
операция проверена миграционной репетицией, целевыми tests и live smoke.
Рабочие сущности не пересоздавались, отправки/провайдеры/production/deployment
не затрагивались. Push не выполнялся. При необходимости восстановления сначала
остановить запись в эту локальную БД и восстановить dump в отдельную проверяемую
БД; автоматическое затирание текущих данных этим отчётом не разрешается.
