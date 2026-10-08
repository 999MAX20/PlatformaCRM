# Подписка, лимиты и использование

Срез `768b2675`, 09.10.2026. Коммерческое развитие отложено; foundation и честный
интерфейс существуют. Требования V1 и открытые решения — [product](../current/product.md),
[acceptance](../current/acceptance.md). Это SaaS billing, не журнал платежей пациентов.

## Текущее поведение

SubscriptionPlan/Subscription/UsageCounter и entitlement layer хранят план,
состояние и ограничения. UI показывает сохранённые данные текущего Business.
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
UI отличает ошибку от отсутствия подписки/usage. Entitlement/service layer следует
переиспользовать при будущей политике; не разносить проверки plan names по страницам.
Provider recovery/reconciliation и оплаченный статус не доказаны существованием записи.

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
