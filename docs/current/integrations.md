# Интеграции, импорт и экспорт

Действующие ограничения; срез 07.10.2026. Внешние подключения, мессенджеры,
marketplace write-back, 1С/МойСклад и платёжный gateway отложены. Код сохраняется,
но наличие adapter/endpoint не доказывает live-ready статус. Новые подключения
требуют отдельного поручения, target и ограниченного тестового бюджета.

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

## Импорт, экспорт и public ingress

CSV/XLSX импорт переиспользует [imports](../../apps/core/import_export.py): роли/Business,
upload limits, карантин/scan до parsing, preview/mapping/validation, проверку
связей и дублей, подтверждённое выполнение, прогресс и результат. Не применять
сырой payload как произвольные модели/поля; retry не дублирует выполненную работу.
Рабочую базу не seed/reset ради проверки. Отдельно доказывать rollback/частичный
результат согласно фактическому режиму импорта, а не обещать общую атомарность.

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
