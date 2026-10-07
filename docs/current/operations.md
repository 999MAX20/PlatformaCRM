# Среда, эксплуатация и файлы

Действующие ограничения и недоказанный допуск, 07.10.2026.
Публикация Git и локальная приёмка не означают deployment/production readiness.
Yandex Cloud выбран владельцем как направление; регион, бюджет, оператор,
параметры среды и сам запуск этим документом не назначаются.

## Локальная работа

Единственный writable checkout — `C:/Users/user/Desktop/PlatformaCRM`.
`Desktop/Zani` — junction, не вторая копия. Один зарегистрированный writer,
текущая ветка сохраняется. Серверы запускаются из canonical root; перед UI
проверкой сверить source root backend/frontend/worker и build/profile.
Не останавливать чужие процессы и не доверять localhost по одному HTTP 200.

Runtime/параметры определены [settings](../../config/settings.py),
[примером env](../../.env.example) и scripts. Не печатать рабочий `.env` или токены.
Технические legacy Zani/ZANI identifiers не переименовывать без отдельной
совместимой миграции. Бренд и репозиторий — PlatformaCRM.

Разрешённые ранее рабочие миграции — исторические операции конкретных задач,
не бессрочное разрешение на новые. Working/staging/prod migration, seed/reset,
очистка файлов/старых деревьев требуют конкретного target/scope и backup.
Проверки используют isolated runtime из [testing](../testing/testing.md).

## Требования целевой среды

Общий multi-tenant SaaS, отдельные local/staging/prod settings и credentials.
PostgreSQL, Redis, Celery workers и beat; private object storage, почта, TLS,
allowed hosts/CORS/CSRF, health, безопасные логи/метрики/ошибки и backup/restore.
Prod не использует debug/demo defaults; `ALLOW_DEMO` выключен. Secret rotation,
привилегированная MFA и support grant — [access](access.md).

Долгие операции выполняются через существующие queue/service границы. Следить за
queue lag, retries, oldest pending/stale, worker/beat heartbeat, DB/Redis health,
provider failure и ценой AI. Логи структурированы с безопасными correlation IDs;
не писать сообщения клиентов, prompts, файлы, auth headers или secret payload.
Health endpoint не раскрывает credentials. Алерт имеет владельца, действие,
threshold и recovery; общая dashboard-картинка не доказывает срабатывание алерта.

Проверить очереди notifications, reports_exports, file_scans и все прочие,
используемые текущими task routes. Синхронный connector sync остаётся отдельной
границей риска; не считать весь интеграционный runtime очередью автоматически.
SQLite/eager не доказывают locking и recovery PostgreSQL/Redis.

Backup покрывает БД, закрытые файлы и доступность ключей для восстановления.
Проверить восстановление в отдельной цели, целостность tenant-связей, приватные
download и выбранные RPO/RTO, затем документировать rollback приложения/миграций.
Не откатывать схему с потерей данных без согласованного плана. Из старых предложений
35 дней backup, RPO 1ч, RTO 4ч, retention 90 дней и 5/25/100GB нельзя делать
утверждённые нормы. Облачный общий cap 3GB и retention ещё требуют исполнения/
проверки в выбранной среде. Текущий upload limit 10MB не заменяется предложением 25MB.

## Карантин и антивирус

[core](../../apps/core) хранит приватные файлы и scan state; pending/scanning/
clean/infected/error. ClamAV INSTREAM разрешает файл только по корректному OK,
не по timeout/неизвестному ответу; fail closed. Worker leases/checksum защищают
от старого результата после замены/повтора. До clean запрещены download/использование
и parsing импортов; raw storage URLs/ручного обхода quarantine не добавлять.

ClamAV — внутренний сервис (3310 не публикуется наружу), scanner timeout 30с,
предельный возраст signatures 72ч по действующим defaults. Нужны file_scans worker
и периодический due-processing (15с). Проверить обновление signatures, недоступность
scanner, retry/recovery, private object cleanup и метрики в target environment.

Avatar: исходник до 5MiB JPEG/PNG/WebP, до 16M pixels и один frame; scanner проверяет
оригинал, сервер нормализует до JPEG 256px/128KiB без EXIF. Мimetype/расширение
не являются доказательством безопасности. Проверять права на загрузку/чтение.

Локальный runtime `output/local-file-antivirus` используется работающей системой:
это не одноразовый тестовый мусор. `runtime.py status` / `manage.py file_antivirus`
используются для диагностики; start/stop только в разрешённом scope и для своих
процессов. Автозапуск при входе в Windows не подтверждён. Не удалять runtime
при housekeeping документации и не заявлять local service как cloud deployment.

## Допуск и инциденты

PAID_BETA_* flags выставляются после реальных доказательств соответствующего
gate, не ради зелёного health. Проверить точный candidate, tenant/roles, целевой
DB/queues, backup/restore, мониторинг, rollback, provider delivery, клинический
рабочий день, ответственных и коммерческую границу. Незакрытое —
[acceptance](acceptance.md). Нет поручения запускать это в данной docs-задаче.

При инциденте сначала установить environment, impact, tenant boundary и текущего
оператора; сохранить безопасное evidence, ограничить ущерб, выполнить минимальное
обратимое восстановление в разрешённой границе. Не переигрывать внешние writes
и очереди вслепую. Проверить recovery и записать причину/регрессионную защиту.
Data exposure, потеря данных или необратимое действие требуют явного решения
владельца по затронутой операции; не расширять права для диагностики.

Происхождение: [production readiness](../../archive_docs/2026-10-07/docs/production/production-readiness.md),
[AV](../../archive_docs/2026-10-07/docs/security/file-antivirus.md).
