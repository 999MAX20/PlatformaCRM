# Эксплуатация и границы целевой среды

Проверена текущая конфигурация и доступная локальная изоляция. Развёртывание в
Yandex Cloud не выполнялось; Windows, CLI-разбор Compose и локальные worker drills
не подтверждают работу Linux image или целевой инфраструктуры.

## Процессы и очереди

Web использует Gunicorn/WSGI. Notification ASGI — отдельный entry point; отключённый
по умолчанию stream не следует считать отказавшей обязательной службой. Stand
overlay добавляет Caddy и gate, но не заменяет CRM-аутентификацию или tenant checks.
Фактический Compose merge с синтетическим env подтвердил снятие обходных портов;
контейнеры при этой проверке не запускались.

| Очередь | Поставляемый consumer | Граница |
| --- | --- | --- |
| default | celery | Обычный worker не подписывается автоматически на все очереди |
| file_scans | celery-files | Private media и ClamAV dependency заданы в base |
| integrations, webhooks_outbound | celery-integrations | Нужен workers profile |
| ai | celery-ai | Нужен workers profile |
| automations | отсутствует | Сохраняется OPS-Q01 |
| notifications | отсутствует | Сохраняется OPS-Q01 |
| reports_exports | отсутствует | Сохраняется OPS-Q01 |

Beat включается отдельным profile. Изолированный recovery drill предыдущего аудита
явно предоставлял consumers и поэтому не исправляет поставляемую топологию.
Настройки inline/eager, явные dispatch queues и конфигурация оператора меняют
исполнение; их нельзя подразумевать в доказательстве штатного deployment.

Точные task names, маршрутизация и schedules: [queue topology](../queue-topology.csv),
[root architecture](../architecture-root.md), [Compose receipt](../compose-merge.log).

## Восстановление и файлы

Сохраняется изолированное доказательство остановки/возврата PostgreSQL, Redis,
worker, AV, восстановления dump/files/keys и scanner-outage/retry из предыдущего
аудита на неизменившихся входах. Исходный сбой штатного recovery helper не заменён
успехом адаптированного drill. Новый burst/soak завершён с отдельной фиксацией
ошибок и очистки собственных процессов: [performance](../performance-results.md).

Проверка clean-archive на синтетическом дереве показала включение backup DB,
вложенного env и browser auth artifacts, несмотря на исключение корневых .env/DB.
Реальные приватные данные не копировались: [receipt](../archive-probe.json).
Архивировать/передавать рабочую папку этим helper без исправления правил нельзя
считать безопасной процедурой поставки.

## Что остаётся доказать в целевой среде

Девять новых сценариев миграций на заполненных predecessor states подтверждают
rollback после data writes, отсутствие незавершённой migration record и успешные
retry/replay. Это реальный MigrationExecutor в одноразовой SQLite, не аварийное
завершение процесса и не PostgreSQL DDL. Для businesses0002/0008 и integrations0006
отдельные populated failure/retry сценарии остаются непроверенными в действующей
границе protected probes. Поддерживаемая предыдущая release-версия не объявлена:
технический predecessor не заменяет согласованную upgrade policy.
[Миграционные строки, команды и сохранённые ошибки](../backend/migration-acceptance.md).

Docker engine и подходящий Linux Django runtime недоступны в проверенной среде.
WSL без требуемых Django/psycopg/pip не заменяет Dockerfile Python3.11. Не проверены
реальные Yandex topology, DNS/TLS/origins, object-store ACL, key custody/rotation,
production AV freshness, alerts/on-call, release/rollback и live provider receipts.
Установка инфраструктуры и deployment не входят в разрешение этого аудита.

Image default user, mutable base и migrations в web startup требуют отдельной
целевой проверки запуска нескольких replicas, прав storage и graceful shutdown.
Это эксплуатационные риски/границы, а не доказанные удалённые атаки. Исторический
Render/Hoster пример не является реализованной Yandex-схемой.
