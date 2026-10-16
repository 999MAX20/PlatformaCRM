# Подписка, лимиты и использование

Исходная основа `768b2675`, 09.10.2026; актуальные дельты 16.10 описаны ниже.
Рабочий коммерческий запуск отложен; foundation и честный
интерфейс существуют. Требования V1 и открытые решения — [product](../current/product.md),
[acceptance](../current/acceptance.md). Это SaaS billing, не журнал платежей пациентов.

## Текущее поведение

SubscriptionPlan/Subscription/UsageCounter и entitlement layer хранят план,
состояние и ограничения. Usage показывает сохранённые данные текущего Business.
По поручению владельца 16.10 Settings → Тариф содержит новый поток заказа:
явное предложение, покупатель, банковские реквизиты и переход к оплате картой.
При выключенном commerce показана недоступность; реальные предложения не созданы.
Описанные ниже старые реквизиты и предпочтение плана остаются серверной совместимостью.
Billing email и invoice name/tax ID/address — отдельные реквизиты Subscription;
они не подменяются реквизитами Business. Выбор плана пишет requested_plan/время
как предпочтение, не меняет активный план и не создаёт счёт.
Payment method — справочное значение; metadata pause/resume/cancel не обещают
остановить CRM/списания и убраны из merchant UI при сохранённой совместимости API.

Users — активные memberships; bots/automations — текущие объекты; storage —
FileAttachment size в MiB. AI calls/messages/conversations используют UsageCounter
с подписанным календарным месяцем. Null limit означает отсутствие ограничения,
ноль не становится infinity. Старые default limits не являются утверждённым тарифом V1.
Количество calls не доказывает согласованную коммерческую единицу AI-диалога.

## Права, ошибки и восстановление

Billing VIEW/MANAGE проверяются для явно выбранного доступного Business.
Metadata пишутся атомарно с audit имён полей без реквизитов. Сервер валидирует email;
Usage UI отличает ошибку от отсутствия данных. Entitlement/service layer следует
переиспользовать при будущей политике; не разносить проверки plan names по страницам.
Оплаченный статус требует отдельного подтверждения; запись Subscription его не доказывает.

## Карта, evidence и целевой результат

[Models](../../apps/billing/models.py), [services](../../apps/billing/services.py),
[entitlements](../../apps/billing/entitlements.py), [usage](../../apps/billing/usage.py),
[API](../../frontend/src/api/billing.ts),
[UI](../../frontend/src/features/settings/sections/BillingSection.tsx).
Маршрут `/app/settings#billing`, usage-раздел, API `/api/billing/…`.
[Settings evidence](../testing/settings-functional-20261008.md) — проверенные
tenant/metadata/usage/UI; не коммерческий processing.
[CRM-R06](../current/roadmap.md) отложен до решения V1-O01/V1-O02/V1-O03/V1-O04:
цены/квоты, единица учёта, billing/processing/recovery. Принятые будущие положения V1
не объявляются реализованным поведением текущего runtime. R07 требует коммерческой приёмки.
09.10 — паспорт существующего слоя; новые тарифы/платежи/ограничения не вводились.

Сверка 16.10: в Subscription.Statuses есть trial/active/overdue/cancelled/paused;
целевой переход ACTIVE → GRACE (3 дня) → READ_ONLY из product не реализован этим enum
и metadata service и не заявляется принятым. ADMIN-05 реализует локальную основу
инспектора и восстановления, но не enforcement окончания оплаченного периода.
Это открытый остаток CRM-R06/ADMIN-05, не разрешение на рабочий запуск.

16.10: в [спецификации, раздел15.4](../testing/platform-rebuild-spec-20261014.md)
сохранён анализ amoCRM/Битрикс24/Zoho и предложение общей основы перевода и карты:
ручная проверка банковского поступления, один эквайер и автоматическое однократное
применение подтверждённой оплаты; 5a/5b общие для каналов.
[Резюме для партнёров](../testing/admin05-payments-partner-brief-20261016.txt) — для обсуждения.
Полномочия и основная логика отдельно утверждены: platform_admin подтверждает
банковское поступление; обе platform-роли читают историю и повторяют применение
со свежим MFA, открытым обращением этого Business и основанием. Заказ фиксирует
покупателя, продавца, сумму/валюту, план и точные даты из явно утверждённого предложения.
Подтверждение и применение — разные транзакции; повтор не выдаёт второй период.
Карточный адаптер имеет checkout, аутентификацию уведомления и серверную сверку;
реальный адаптер отсутствует. Неопределённый результат запрещает новое списание.
Несовпадение суммы/валюты, две оплаты, refund/dispute требуют разбора, не компенсации.
Подписка, изменившиеся условия и независимые блокировки проверяются под блокировками.

[Commerce](../../apps/billing/commerce.py), [application](../../apps/billing/application.py),
[card adapter flow](../../apps/billing/card_payments.py), [API](../../apps/billing/commerce_views.py).
Новая billing0006 проверена только в изолированной БД. BILLING_COMMERCE_ENABLED=False,
BILLING_CARD_ADAPTER=None; рабочих предложений, банка, эквайера и фискализации нет.
PostgreSQL affected/concurrency и проверки среды — [checkpoint ADMIN-05](../testing/task-state/PRIMARY-SESSION.md).
Полный ADMIN-05/5a/5b остаётся открыт: реальные деньги, документы, цены/периоды,
коммерческий expiry enforcement и приёмка выбранной среды не закрыты.


16.10, этап6: общая локальная приёмка ADMIN01–04 + основы ADMIN05 — SCOPED PASS.
Проверены PostgreSQL concurrency/permissions/rollback и совместный browser flow
desktop/mobile/RU/KK/EN; исправлены подписи ресурсов в общей истории просмотра.
Источник — база3c6939ee + эта UI-дельта; [checkpoint](../testing/task-state/PRIMARY-SESSION.md),
PLATFORM-ADMIN-ACCEPTANCE-20261016. Полный этап6 и ADMIN05 не закрыты; отложенные
коммерческие решения/код/live evidence и рабочая среда сохраняются без изменений.
