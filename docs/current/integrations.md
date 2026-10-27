# Интеграции, импорт и экспорт

Действующие ограничения; уточнение 14.10.2026: Telegram и WhatsApp включены
в подготовку пилота R02, клиники подключают собственные аккаунты; WhatsApp-провайдер
ещё выбирается. Реальная отправка/подключение не выполнены. Прочие внешние подключения,
marketplace write-back, 1С/МойСклад и платёжный gateway остаются отложенными. Код сохраняется,
но наличие adapter/endpoint не доказывает live-ready статус. Новые подключения
требуют конкретного target и согласованного объёма. Пилот финансирует владелец;
новые коммерческие лимиты/автоотключение по расходам не вводятся. Это не отменяет
технические rate limits и защиту от злоупотреблений. Решения —
[CRM-R02](../testing/task-state/PRIMARY-SESSION.md#crm-r02-20261014--pilot-decisions-and-provider-research).

## Connector boundary

Provider-specific поведение живёт за service/provider adapter, не в views/UI.
Существующие слои: [integrations](../../apps/integrations),
[bots](../../apps/bots), [BusinessEvents](../../apps/integrations/models.py).
Использовать существующие модели/нормализацию вместо нового параллельного контура.
CRM — потребитель бизнес-сигналов, не полная копия ERP/склада.

Connector отражает supported modes, setup/status, masked credentials, health,
last sync/webhook, безопасную ошибку и доступный retry/reconnect. Проверка прав,
tenant и связей выполняется сервером. Merchant setup содержит необходимые поля;
raw webhook/debug/provider stack не занимает повседневный экран.

Platform diagnostics uses one connector classification across counters and queues:
`error`, `failed`, `expired_credentials` are failures; `needs_attention` is setup
attention, counted separately. The attention queue includes both groups; disabled,
disconnected and draft connectors do not enter it. Connector state alone does not
prove a background-service outage or recovery; component observations remain separate.

Credential хранится за `ConnectorCredential`, не в `BotChannel.config_json`.
Конфигурация канала содержит безопасные metadata/configured flags. Не возвращать
secret в serializer/log/task payload. Ротация требует совместимого чтения старого
ключа, проверки нового, ограниченного dry-run и отдельного разрешения на целевую
среду; старый ключ не удалять до доказанного завершения перепаковки и восстановления.

Webhook проверяет подлинность доступным provider-механизмом до изменения данных;
разрешение tenant берётся из серверной привязки, не из недоверенного payload.
OAuth state/redirect, credential ownership и setup версии проверяются сервером.
Запоздавшие sync/setup/results не перезаписывают более новую конфигурацию.

Нормализованные события сохраняют источник и внешний ID, дату, Business и
достаточную provenance; не создавать CRM-дубли при webhook/pull/replay.
Idempotency, транзакционная граница, concurrency, backoff, max attempts,
pagination/cursor и recovery должны быть явными. Не делать бесконечный retry
для auth/validation errors; не заявлять внешнюю доставку по локальному enqueue.
Фоновая работа повторно проверяет актуальные права, конфигурацию и отмену.

Marketplace по умолчанию read_only. Отдельный inventory_write означает только
остатки с warehouse/product mapping и локальными reservation/release, не изменение
цены, карточки или заказа. Это отложенный контракт, не текущий допуск к записи.
Нельзя смешивать внешний доступ и merchant role или включать writes по health PASS.

Финансовый reader принимает только проверяемый источник и точный период,
идентифицирует валюту, completeness/freshness и provenance. Неполные/stale данные
дают явное no-data/recovery. Выбор manual или одного external и ограничения KPI —
[CRM](crm.md#деньги-и-аналитика). Реестр external financial readers пока пуст;
общий connector не становится денежным источником автоматически.

AUD-14, 17.10: generic message API не позволяет менять историю или назначать delivery
state, external IDs, raw payload и timestamps. Authenticated inbound-text POST имеет
allowlist, client sender и parent permissions; он не подменяет доверенный webhook.
Исходящие send/retry и запись provider metadata остаются за существующими сервисами.
Проверки локальные, с mock/изолированной доставкой: checkpoint AUD-14-20261017;
активация провайдера, credentials и rollout этим не меняются.

## Импорт, экспорт и public ingress

CSV/XLSX импорт переиспользует [imports](../../apps/core/import_export.py): роли/Business,
upload limits, карантин/scan до parsing, preview/mapping/validation, проверку
связей и дублей, подтверждённое выполнение, прогресс и результат. Не применять
сырой payload как произвольные модели/поля; retry не дублирует выполненную работу.
Рабочую базу не seed/reset ради проверки. Отдельно доказывать rollback/частичный
результат согласно фактическому режиму импорта, а не обещать общую атомарность.

AUD-16: `POST /api/import-jobs/` принимает только `business`, `entity_type` и
`source_file`; остальные входные поля отклоняются400. Actor и имя файла берутся
сервером, все результаты/счётчики/timestamps управляются сервисом. Generic
PUT/PATCH/DELETE не поддерживаются405; Django admin показывает историю read-only
без ссылки на source_file. Контекст и источник существующего job неизменяемы.
`POST /api/import-jobs/{id}/preview/` принимает только `mapping` — объект
поддерживаемое поле → существующий заголовок файла. Некорректный mapping400
не меняет сохранённый preview. Без mapping сохраняется выбранное соответствие
или применяется автоопределение; неизвестные заголовки возвращают preview с
ready=false, чтобы mapping можно было исправить отдельным preview.
Preview и confirm держат row lock ImportJob до конца транзакции и перечитывают
состояние после ожидания. IMPORTED/CANCELLED нельзя открыть preview повторно;
confirm разрешён только из PREVIEWED. Проверяются актуальные actor/CREATE/модуль,
исходные ограниченные байты и AV, mapping и строки, а не доверенные клиентом
preview/errors. Ошибка до commit откатывает CRM-записи, события, sync и audit,
сохраняя предыдущее состояние job для повтора. Scanner unavailable возвращает
503 temporary_service_failure с retryable=true, без импорта. Последовательный
повтор confirm завершённого job отклоняется400. Начальное состояние lead/deal
проверяется доменными creation services (AUD-20). Импорт заявки поддерживает колонку
`lost_reason`: LOST без причины, причина при другом статусе и неизвестный непустой
status дают row/field errors в preview и повторно на confirm. Пустой status — NEW.
Сервер создаёт время/автора потери и начальную историю атомарно с импортом.
Импорт сделки выбирает только активную открытую стадию; если её нет, ошибка
откатывает импорт и позволяет повтор после исправления конфигурации.
AUD-21: в изолированном PostgreSQL17 подтверждены ожидание блокировки вторым
confirm, откат после записи строки и финального audit, затем один успешный
импорт и отказ повтору. Откатившаяся попытка не оставляет CRM-записей, событий,
sync, audit или on_commit callbacks; ожидающий запрос перечитывает PREVIEWED.
Runtime-изменений сверх AUD-16 не потребовалось. Evidence и версия —
[AUD-21 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-21-20261021--concurrent-import-rollback-and-recovery).
AUD-22: XLSX проходит ZIP/XML preflight до openpyxl: размер разжатого архива,
compression ratio, число записей, dimensions и фактические координаты/число
строк/столбцов ограничены. Заниженные dimensions не обрезают данные. Превышение
даёт400 без частичного импорта; после исправления файла возможен новый upload.
Reader/iterator/workbook закрываются и при ошибке. Лимиты всех листов, включая
пустые строки, и значения env — [operations](operations.md#лимиты-xlsx-импорта).
Обычные роли/tenant/AV и доменные транзакции сохранены. Полный UI (AUD-12) открыт.
Версия и граница проверок — [AUD-16 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-16-20261019--import-job-write-boundaries).

Public lead/widget ingress привязан к разрешённому business/form/channel,
ограничен validation/rate limits/origin policy и не раскрывает приватные CRM-данные.
Секретный API token не размещается в браузерном виджете; клиентские данные
и ответы провайдера недоверенные. Сообщение идёт через существующий Inbox flow.

Экспорт permission/capability/tenant-scoped: маленький CSV синхронно,
большой — `202` + `ExportJob`, polling и закрытый download. Worker повторно
проверяет доступ актёра и модуль. Defaults: sync 5000 строк, максимум 100000,
report range 366 дней, sync report 90 дней, stale job 900 секунд.
Очередь `reports_exports` и beat `exports.process_due_jobs` обязательны для
фонового пути; ошибки/stale видны в platform operations. Значения конфигурации
сверять с текущим кодом перед изменением среды.

## Скачивание сохранённого экспорта — AUD-18

При генерации ExportJob сервер сохраняет fingerprint контекста доступа в
parameters_json и сверяет его до/после формирования CSV. Download проверяет
активного пользователя, Business, VIEW, capability и совпадение fingerprint.
Он включает actor, scope, доступные филиалы, состав команды и набор доступных
ID для OWN/TEAM; отчёты учитывают также права исходных ресурсов и область
показателей команды. Изменение контекста при генерации даёт FAILED без файла.
Изменение контекста после генерации или старый файл без fingerprint дают403:
нужно запросить новый экспорт. Полный отзыв Business/membership сохраняет404.
Неподготовленный файл по-прежнему даёт400. При отказе байты не выдаются и
успешный file_download audit не создаётся. Старые файлы не переписываются.

Это консервативная проверка равенства: расширение прав, изменение состава
доступных записей OWN/TEAM или филиалов тоже может потребовать нового экспорта.
Branch grants не становятся фильтром чтения общей клиентской базы; действующий
CRM-MB01 сохраняется. Приватные Client.notes дополнительно маскируются при
скачивании по текущей field policy (AUD-03). Fingerprint привязан к actor:
просмотр job платформой не разрешает скачивание файла другого исполнителя.
Уже скачанные копии и начатую передачу файла отозвать нельзя. Проверка не вводит
общую блокировку изменений прав на время HTTP streaming.
Локальная проверка и версия — [AUD-18 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-18-20261027--current-export-download-authorization).
Рабочая БД, схема, live worker/storage и deployment не менялись.

## Граница доказательств

Mock/eager/SQLite подтверждают локальную логику. Реальный provider, подпись,
доставка, rate limit, worker/Redis/PostgreSQL и recovery требуют отдельного evidence.
Проверять happy path, denied role, foreign tenant, masking, duplicate/replay,
timeout, revoked credential и возобновление. Не отправлять сообщения реальным
получателям и не менять provider data в обычной автоматической проверке.
Оставшиеся gaps — [acceptance](acceptance.md); target — [operations](operations.md).

Архив происхождения (не текущий rollout-план):
[blueprint](../../archive_docs/2026-10-07/docs/integrations/CONNECTOR_BLUEPRINT.md),
[provider rollout](../../archive_docs/2026-10-07/docs/integrations/provider-rollout.md).


ADMIN-05: SaaS card payments используют отдельный billing adapter (checkout,
authenticate_notification, lookup), а не merchant Connector. Redirect и payload
не подтверждают поступление: результат повторно читается у адаптера. Неопределённый
checkout запрещает вторую попытку до сверки; receipt и application сохраняются
отдельно, повторы идемпотентны. Реальный adapter не выбран; FakeCard доступен только
в изолированных тестах. Нет BusinessEvent/AI-trigger, отправки писем или реальных денег.
Оставшиеся provider/live требования — [паспорт](../pre-production/subscription-usage.md).
