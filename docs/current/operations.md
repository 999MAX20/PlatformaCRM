# Среда, эксплуатация и файлы

Действующие ограничения и недоказанный допуск, 07.10.2026.
Публикация Git и локальная приёмка не означают deployment/production readiness.
Решение владельца 14.10: выбрать инфраструктуру на территории Казахстана,
Yandex Cloud больше не выбранное направление. Технический оператор — владелец;
провайдер, параметры среды и запуск ещё не назначены. Решения и исследование —
[CRM-R02](../testing/task-state/PRIMARY-SESSION.md#crm-r02-20261014--pilot-decisions-and-provider-research).

## Локальная работа

Единственный writable checkout — `C:/Users/user/Desktop/PlatformaCRM`.
`Desktop/Zani` — junction, не вторая копия. Текущая ветка сохраняется;
чужие изменения не перезаписываются. Серверы запускаются из canonical root; перед UI
проверкой сверить source root backend/frontend/worker и build/profile.
Не останавливать чужие процессы и не доверять localhost по одному HTTP 200.

ADMIN-03: `ACCOUNT_RECOVERY_SUPPORT_EMAIL` задаёт публичный адрес поддержки,
`FRONTEND_URL` — доверенный адрес приложения для ссылок восстановления (HTTPS;
HTTP допускается только localhost/127.0.0.1). Без адреса поддержки экран честно
показывает отсутствие настройки; без frontend origin/почтового транспорта заявка
остаётся с безопасным состоянием ошибки отправки. Console/file/dummy backend
не выводит recovery-секреты. Проверка локального test outbox не доказывает SMTP
или доставку в ящик. Новая миграция accounts0011 требует отдельной рабочей активации.

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

PLATFORM-REBUILD-01: platform read APIs отделяют записанные ошибки источников
от свежих ServiceComponentState. Последние используют существующую границу
свежести 180 секунд; эти данные не подтверждают доступность всех провайдеров.
Операционные источники читаются независимо с безопасным rollback чтения:
недоступные значения возвращаются как null и/или unavailable_sources, без текста
исключения. Отсутствующая таблица наблюдений не обнуляет очередь и другие данные.
Ошибки форм в clinic summary считаются за 30 дней; failed jobs/events в обзоре —
история, не признак текущего outage. Legacy health.score теперь null; health.status
описывает recorded_signals (clear/attention/unknown), а не процент готовности.
Миграции и запуск collector не выполняются как побочный эффект чтения.
Vite направляет /ready/ в тот же backend, что /api; HTML оболочки не является readiness.

PLATFORM-OPERATIONS-20261015 добавляет read-only `operations-worklist` с источниками
incidents/connectors/automations/integrations/webhooks, строгими bounded filters,
стабильной пагинацией и safe projections без payload/error text/credentials.
Эпизоды: только последний известный episode по компоненту, свежие degraded и
устаревшие/будущие наблюдения как unknown; fresh healthy не попадает в очередь.
Полного исторического incident ledger это не создаёт. При отсутствии таблицы
support links наблюдения остаются доступны, число обращений неизвестно.
Health CLI сохраняет прежние release/readiness gates; connector_requests count
полный, массив-превью остаётся ограниченным. В UI readiness, текущие наблюдения
и terminal failures представлены отдельно. Миграций/запуска collector нет.

PLATFORM-OVERVIEW-20261015: `overview.attention` содержит полные distinct counts
клиник и ограниченные очереди клиник/поддержки. Классификация наблюдений общая с
`merchants?service=...`: degraded имеет приоритет над unknown; здоровая клиника
требует свежих наблюдений всех компонентов. Отсутствующие/будущие/устаревшие
наблюдения — unknown. Нет источника — null, а не пустая очередь; отсутствие
support links не скрывает сами наблюдения. Обращения активны до resolved,
unassigned — без assigned_to; waiting_clinic — точный статус, не SLA-просрочка.

PLATFORM-CLINIC-CRM-20261015: отдельный platform read API показывает Business-bound
CRM и safe статусы подключений; поиск/статус/архив/client filter, page_size до50,
стабильная сортировка и audit-before-response. Переписка читается без read-mark,
сырые payload/credentials исключены. Техническая диагностика остаётся в Операциях,
из карточки доступны Business-фильтрованные переходы. Это не новые источники
наблюдений, не запуск collector и не допуск recovery/retry. Миграций нет;
рабочая support0002 и live-проверки остаются отдельным объёмом.

Проверить очереди notifications, reports_exports, file_scans и все прочие,
используемые текущими task routes. Синхронный connector sync остаётся отдельной
границей риска; не считать весь интеграционный runtime очередью автоматически.
SQLite/eager не доказывают locking и recovery PostgreSQL/Redis.

CRM-R02-AI-RETURN: `bots.resume_answered_handoffs` выполняется beat каждые
60 секунд в очереди `default`, до 100 просроченных сроков за запуск. Срок хранится
в БД, повтор не дублирует переход; после простоя worker проверяет текущие условия.
Миграция `bots/0012_answered_handoff_recovery` добавляет nullable поля без
автоматического включения прежних диалогов. Для рабочего запуска нужны отдельно
разрешённое применение миграции и работающие worker/beat; Git-публикация их не запускает.
Правило возврата и исключения — [AI](ai.md#жизненный-цикл-preview-и-сбои).

14.10 владелец разрешил активацию таймера в текущей локальной рабочей среде.
`bots0012` применена к canonical `db.sqlite3` после проверенного SQLite backup;
старые диалоги и их состояния сохранены, старым handoff таймер не назначается.
Машинный runtime: `output/local-handoff-recovery/runtime.py`, команды через
`.venv/Scripts/python.exe`: `run` / `status` / `stop`. Один supervisor запускает
worker/beat только для `bots.resume_answered_handoffs` раз в 60 секунд; собственная
файловая очередь использует существующие Windows-зависимости local-file-antivirus.
Runtime, broker и backup — рабочие локальные файлы, не тестовый мусор.
Автозапуск после перезагрузки Windows не настроен; это не облачный Redis runtime.
Остальные задания, core0012, Meta/PS Cloud и production остаются вне этой операции.

CRM-S04: для локальной изолированной проверки есть
[`verify_recovery_s04.py`](../../scripts/verify_recovery_s04.py),
[команда и граница](../testing/testing.md#s04-postgresqlredis-recovery-drill).
Стенд создаёт собственные PostgreSQL/Redis, worker/beat и ClamAV, проверяет
перезапуск/аварийную остановку, повторы и отмену, экспорт/карантин файлов,
потерю очереди с восстановлением из БД и фактический restore БД/файлов/тестового
ключа. Отчёт хранит проверки и отказы доступа; временные данные и процессы удаляются.
Это не настройка рабочих служб или production backup: Windows solo/локальные
файлы не заменяют приёмку Linux workers, object storage и восстановления на другом
хосте. Испытание не назначает RPO/RTO и не выставляет PAID_BETA_* flags.

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

CRM-S03 (решение владельца 14.10.2026): сотрудники видят баннер влияния на
работу, владелец и активные администраторы — персональные SYSTEM-уведомления
о начале и устранении задержки. Учитываются настройки категории system;
повторное наблюдение не создаёт новый колокольчик. Неактивные аккаунты исключены.
Сохранение перехода и уведомлений атомарно; in-app доставка не зависит от
очереди уведомлений. В колокольчике каждый получает только своё такое сообщение.

Состояние строится по текущей просроченной работе автоматизаций, внутренних
уведомлений, экспорта и проверки файлов. Исторические ошибки и неподключённые
необязательные провайдеры остаются диагностикой оператора. Сборщик запускается
beat раз в 60 секунд, обрабатывает до 100 бизнесов за проход с ротацией;
наблюдение старше 180 секунд считается неизвестным, а не восстановленным.
При росте числа бизнесов требуется проверить пропускную способность сборщика.
Устранение задержки не подтверждает успех каждой операции: результат доступен
в её истории. Полный отказ CRM требует будущего независимого внешнего мониторинга.
Миграция core0012 проверена в изоляции; её применение в рабочей среде и запуск
целевого worker/beat требуют отдельного согласованного окружения.

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

## Локальная активация поддержки — 15.10.2026

По поручению владельца support0001 применена к canonical `db.sqlite3` после
SQLite online backup и проверки восстановления/целостности. Созданы пять пустых
таблиц поддержки; существующие бизнес-данные сохранены. Очереди доступны через
локальные backend8000/frontend5173; read-only API и HTTP smoke PASS.
Backup и отчёт находятся в `output/local-support/` и не публикуются в Git.

PLATFORM-INCIDENT-LINK-20261015 добавляет миграцию `support0002` с зависимостью
от `core0012`. Она проверяется в изолированных БД; к рабочей БД в этом scope
не применяется. Локальная активация support0001 не означает активацию связей.
Поддержке не нужен отдельный worker; существующие процессы оставлены без изменений.
Это локальная активация, не deployment или приёмка облачной среды.
