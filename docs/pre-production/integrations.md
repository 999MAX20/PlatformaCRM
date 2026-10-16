# Внешние каналы и интеграции

Исходная основа `768b2675`, 09.10.2026; актуальные дельты 16.10 описаны ниже.
Telegram/WhatsApp включены в подготовку пилота R02 решением 14.10;
фактическое подключение/доставка не приняты. Остальные внешние подключения отложены;
существующий код сохранён. Цель — получать полезные CRM-сигналы и доставлять
сообщения через выбранного провайдера, без копирования всей ERP.
Нормативный источник — [интеграционный контракт](../current/integrations.md).

## Реализованная основа

BusinessConnector хранит provider/capability/modes/status и sync metadata;
ConnectorCredential — защищённые credentials, ConnectorSyncRun — выполнение,
BusinessEvent — нормализованное событие с Business/source/external identity.
BotChannel связывает канал с Inbox. Webhooks/pull/setup/health/retry существуют
в provider/service слое; supported mode не равен доступному live-продукту.
Merchant UI показывает настройку/состояние/ошибку/восстановление; технический provider
stack не должен занимать повседневную CRM.
13.10: по решению владельца на странице оставлены только карточки МойСклад и 1C.
Повторный заголовок, подзаголовок, счётчики, поиск/фильтры и форма финансового
источника убраны. По уточнению владельца пара компактных карточек центрирована;
логотип/название/статус/действие видимы сразу, подробности и настройки — по клику.
Сохранённые финансовые предпочтения Business и backend остаются; их выбор не
делает connector валидным reader. Редизайн не означает запуск внешних подключений.

Подлинность ingress проверяется до записи, tenant берётся из серверной привязки.
OAuth/setup version и credential ownership защищают смену конфигурации; устаревший
результат не должен перезаписать новое подключение. Дедупликация/нормализация
не должны создавать повторные CRM-эффекты при webhook/pull/replay.

## Доступ и восстановление

Integrations permissions и scope проверяются сервером. Токены не возвращаются
в channel config_json, UI, audit или логи; сериализуется configured/masked состояние.
Retry/reconnect зависят от ошибки: validation/auth не исправляются бесконечным retry.
Enqueue/health/connected не доказывают delivery. Rotation имеет отдельный target/scope;
старый ключ сохраняется до доказанного восстановления/перешифровки потребителей.
Marketplace read_only по умолчанию; inventory_write не разрешает цены/карточки/заказы.
External financial readers пока не зарегистрированы, произвольный connector не
становится финансовым источником автоматически.

## Карта и доказательства

[Models](../../apps/integrations/models.py), [services](../../apps/integrations/services.py),
[providers](../../apps/integrations/providers), [bots](../../apps/bots),
[API](../../frontend/src/api/connectors.ts),
[UI](../../frontend/src/features/integrations/IntegrationsPage.tsx).
UI `/app/integrations`; API business-connectors/connector-credentials/connector-sync-runs
и профильные webhooks в [router](../../config/urls.py).
[Аудит 08.10](../testing/integrations-functional-review-20261008.md) — анализ и предложение,
не исправление всех замечаний и не live-сертификация. Изолированные mocks не target evidence.

## Цель и открытое

[R02/R03](../current/roadmap.md): Telegram и WhatsApp каждый отдельно, реальная доставка,
подпись, повтор, timeout/отзыв/восстановление; R04 — runtime. Остальные коннекторы,
marketplace/1С сохраняют D02/D03 и BE-GAP-009/010. Публичный abuse BE-GAP-008
не закрыт лимитом AI на диалог. 09.10 — паспорт без новых подключений/внешних вызовов.

## Остаток закрытого UI-этапа — сверка 16.10

INTEGRATIONS-SIMPLIFY завершил компактную компоновку, не всю функциональность.
В текущем IntegrationsPage запрос list не передаёт выбранный Business, читает одну
страницу и выбирает первый connector только по provider; backend scoped по всем
доступным businesses. Это риск неверного контекста среди разрешённых бизнесов,
не доказанная утечка в запрещённый tenant. Ручная 1С форма в ProviderCard отправляет
api_key/webhook_secret в config_json, который serializer запрещает. Оба разрыва
сохраняются по коду; новый runtime-тест в docs-задаче не выполнялся.
Остаток: business filter/полнота списка, согласованный encrypted credential flow
либо исключение неподдержанной формы; targeted multi-business/ошибка/retry проверки.
Также требуют приёмки unknown/error при загрузке, view без manage и обновление
истории sync runs. Старые счётчики/фильтры удалены, их прежние дефекты не актуальны;
ошибка мутации теперь находится внутри Modal. Источники и точные различия —
[сверка](../testing/docs-reconciliation-20261016.md#подключения-ui-закрыт-функциональное-подключение-не-принято).
Связь с CRM-D03/BE-GAP-010 сохраняется; подключение провайдера не начато.
