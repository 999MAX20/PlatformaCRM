# Внешние каналы и интеграции

## YCloud TP Lite — локальный первый этап, 29.10.2026

Серверная signup-попытка, подписанный durable webhook, повторная обработка,
привязка одного номера и текстовый транспорт реализованы поверх существующего
WhatsApp/Inbox. Отмена/ошибка/недоступность/подключение проверены в браузере;
права, tenant isolation, подписи, дубли, stale setup, отказ и гонки — автоматически.
Код опубликован в main b6de2956 после проверки выделенного кандидата без прочего WIP.
CI ещё выполняется, live-допуск не заявлен. Изолированные affected/
dependent, актуальная активность инициатора, порядок callbacks, PG dispatch/races
и readiness проверены; frontend i18n/types/app+widget build PASS. Первоначальные
падения сохранены, их исправления подтверждены целевыми проверками. Точные команды,
снимок — YCLOUD-TPLITE-20261028 в PRIMARY-SESSION. Совместная проверка и публикация
выполнены29.10; актуальный результат — YCLOUD-PUBLICATION-20261029 там же.
Реальные аккаунты/отправки, templates/reminders/media/history/Coexistence не проверены
и не входят в этот этап. R02/R03, рабочая миграция и deployment остаются открытыми.

## OFFICIAL-03 — локальная привязка WhatsApp webhook, 28.10.2026

Проверенный канал сохраняется от аутентификации до записи: ключ одного канала
не позволяет выбрать другой бизнес через payload. Все изменения пакета проверяются
до бизнес-эффектов; статусы ищут сообщения соответствующих Bot/Business, а сохранённые
payload и логи содержат только свою часть пакета. Подписи Meta, проверка live-режима,
обычные сообщения и дедупликация сохранены. Схема и рабочие credentials не менялись.

Версия: HEAD98925b67 + прежний WIP + scoped patch. 102 изолированных теста PASS,
включая 20 новых; system/drift/syntax PASS, независимое ревью без замечаний.
Первоначальные падения и исправление совместимости сохранены в
[OFFICIAL-03](../testing/task-state/PRIMARY-SESSION.md#official-03-20261028--whatsapp-authenticated-tenant-binding-fixed-locally).
Остатка кода/доказательств в этом scope нет. Совместная проверка с YCloud и публикация
выполнены29.10 (b6de2956); результат — YCLOUD-PUBLICATION-20261029 в PRIMARY-SESSION. Реальные
каналы и R02/live приёмка остаются открытыми границами; этот PASS их не закрывает.


AUD-12a локально закрыт31.10: ручной mapping, повторный preview, полный список
ошибок с пагинацией и исправление/повтор доступны в существующем импорте заявок.
Общий ImportPanel переиспользован; API metadata проверены для всех5 entity.
Backend50/Node5/system/drift/build/types/i18n и RU/KK/EN browser PASS на кандидате
от4c6587c6; опубликовано f9a7a6c8, remote SHA подтверждён, CI выполняется; [evidence AUD12a](../testing/task-state/PRIMARY-SESSION.md#aud-12a-20261030--import-mapping-and-error-recovery-verified).
Остатка кода/доказательств/решений в12a нет. AUD-12b локально закрыт31.10: полная
история импортов с серверной фильтрацией Business/entity/actor, страницами/размером,
общим итогом и актуальными деталями. Backend27/Node12/system/drift/build/types/i18n
и RU/KK/EN browser PASS на кандидате от72dda967; опубликовано1b25694a,
remote SHA подтверждён, CI41118186023 выполняется.
[Evidence AUD12b](../testing/task-state/PRIMARY-SESSION.md#aud-12b-20261031--complete-import-history-verified).
Остатка кода/доказательств/решений в12b нет. **AUD-12 закрыт в принятом UI scope31.10:**12c добавляет полную историю фоновых
export jobs, фильтры/страницы/размер/скачивание после reload с текущими правами.
Backend17 и зависимые проверки, Node4, build/types/i18n и RU/KK/EN browser PASS.
Малый синхронный CSV не создаёт job. Остатка кода/доказательств/решений в12c нет;
опубликовано0db46068, remote SHA подтверждён, CI41127057520 выполняется. Evidence AUD-REMAINING в PRIMARY. Worker/storage целевой среды отдельно. Новые точки входа, live-приёмка и deployment не выполнялись. AUD-18 исправлен
27.10: download проверяет fingerprint текущего доступа; legacy/изменённый
контекст требует нового экспорта. AUD-20 закрыт в локальном scope ниже. Защита ImportJob реализована в AUD-16
ниже. AUD-21 проверен в локальном PostgreSQL17: конкурентный rollback/recovery
и отсутствие двойного результата подтверждены; XLSX resource bounds AUD-22
реализованы и локально проверены, ограничения ниже.
[Roadmap](../current/roadmap.md#project-audit-20261017),
[evidence](../testing/project-audit-20261017.md). AV на confirm сохранён.

Исходная основа `768b2675`, 09.10.2026; актуальные дельты 16.10 описаны ниже.
Telegram/WhatsApp включены в подготовку пилота R02 решением 14.10;
фактическое подключение/доставка не приняты. Остальные внешние подключения отложены;
существующий код сохранён. Цель — получать полезные CRM-сигналы и доставлять
сообщения через выбранного провайдера, без копирования всей ERP.
Нормативный источник — [интеграционный контракт](../current/integrations.md).

## ImportJob — AUD-16

Служебные поля управляются сервером; upload принимает только Business, тип и файл.
Generic PUT/PATCH/DELETE и редактирование/удаление через admin закрыты; история
и source metadata сохраняются. Mapping меняется только через валидируемый preview;
без распознанных колонок можно получить preview с ошибкой и затем исправить mapping.
Preview/confirm сериализуются row lock; повтор не открывает завершённый job.
Confirm перечитывает состояние, права, capability, файл/AV/лимит, mapping и строки.
Ошибка откатывает импорт, события и историю; scanner503 оставляет повтор возможным.
Контракт/API — [integrations](../current/integrations.md#импорт-экспорт-и-public-ingress).
Проверки и публикация — [AUD-16 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-16-20261019--import-job-write-boundaries).
Статус: выполнено полностью в согласованном локальном scope. Остатка кода,
доказательств и решений владельца нет. Scoped проверки: 112 SQLite PASS, 2 PG-only
skip выполнены в PostgreSQL17 PASS; system/migration drift PASS. Публикация/CI —
итог задачи. Рабочая БД, миграции и deployment не затронуты.
Полный интерфейс mapping/errors/history (AUD-12), экспорт scope (AUD-18)
и XLSX resource limits (AUD-22) этим не закрываются.

## Конкурентный rollback/recovery — AUD-21

21.10: выполнено полностью в локальном scope на основе3834922c. PostgreSQL17
проверяет фактическое ожидание row lock: первая попытка падает после записи
строки либо финального audit, вторая видит чистое PREVIEWED и завершает импорт.
Остаётся один набор данных/events/sync/audit; повтор400, callbacks первой
транзакции не выполняются. Runtime не изменён; 48 import-проверок PASS без skip,
system/migration drift PASS. Команды/окончательная версия и публикация —
[checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-21-20261021--concurrent-import-rollback-and-recovery).
Остатка кода, доказательств и решений в принятом scope нет. Рабочая БД,
deployment/live не затронуты; CI SQLite не заменяет локальную PG-проверку.

## Ресурсы XLSX — AUD-22

21.10: выполнено полностью в локальном scope на основе66b3f64a. Изолированный
probe с жёсткими пределами256МБ/12сек подтвердил зависание на завышенных
dimensions и молчаливый пропуск строк при заниженных. ZIP/XML preflight теперь
ограничивает разжатый объём, compression ratio, entries и координаты/число
строк/столбцов до openpyxl. Потоковый reader читает реальные строки и закрывает
ресурсы при успехе/ошибке. Все листы проходят bounds; импортируется активный.
Настройки и ограничения — [operations](../current/operations.md#лимиты-xlsx-импорта).
Focused10, affected68 без skip, system/drift и повторный bounded probe PASS.
Версия/команды/публикация — [checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-22-20261021--bounded-xlsx-parsing).
Остатка кода/доказательств/решений в scope нет. Live/deployment не выполнялись;
проверка одного файла не является общей нагрузочной сертификацией сервиса.

## Начальное состояние импорта — AUD-20

21.10: preview/confirm проверяют статус и lost_reason заявки через общий доменный
валидатор; confirm создаёт запись, начальную историю и серверные lost metadata
атомарно с существующим BusinessEvent. Невалидная строка не оставляет CRM-записей.
Импорт сделки использует доменный create_deal и только активную открытую стадию;
исправление конфигурации позволяет повтор после атомарной ошибки. API create
проверен теми же регрессиями, новая терминальная форма импорта не добавлялась.
Локальный scope выполнен полностью; код/доказательства/решения без остатка.
Среда — disposable SQLite, mock/eager; deployment/live не выполнялись.
307 affected backend tests + отдельный Inbox rollback/retry PASS; system/drift,
frontend build/bundle и достижимая форма PASS. Версия и команды — [AUD-20 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-20-20261021--initial-lead-and-deal-lifecycle-invariants).

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
