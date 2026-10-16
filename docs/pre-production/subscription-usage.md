# Подписка, лимиты и использование

Исходная основа `768b2675`, 09.10.2026; актуальные дельты 16.10 описаны ниже.
Коммерческое развитие отложено; foundation и честный
интерфейс существуют. Требования V1 и открытые решения — [product](../current/product.md),
[acceptance](../current/acceptance.md). Это SaaS billing, не журнал платежей пациентов.

## Текущее поведение

SubscriptionPlan/Subscription/UsageCounter и entitlement layer хранят план,
состояние и ограничения. Usage показывает сохранённые данные текущего Business.
По решению владельца 09.10 содержимое Settings → Тариф полностью очищено для
будущего стандарта. Данные и API сохранены, запросы скрытой формы не выполняются;
описанные ниже реквизиты и предпочтение плана остаются серверной совместимостью.
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

Сверка 16.10: в Subscription.Statuses есть trial/active/overdue/cancelled/paused;
целевой переход ACTIVE → GRACE (3 дня) → READ_ONLY из product не реализован этим enum
и metadata service и не заявляется принятым. ADMIN-05 (инспектор подтверждённой
оплаты и recovery доступа) ещё не реализован; платёжный источник/период/повторы
требуют принятого контракта. Это остаток CRM-R06/ADMIN-05, не разрешение на billing.

16.10, ADMIN-05 оставлен на обсуждение: в [спецификации, раздел15.4](../testing/platform-rebuild-spec-20261014.md)
сохранён анализ amoCRM/Битрикс24/Zoho и предложение общей основы перевода и карты:
ручная проверка банковского поступления, один эквайер и автоматическое однократное
применение подтверждённой оплаты; 5a/5b общие для каналов.
[Резюме для партнёров](../testing/admin05-payments-partner-brief-20261016.txt) — для обсуждения.
Источник, полномочия, цена/валюта/период и возвраты не утверждены; ledger,
автоматическая сверка и восстановление эффективного доступа не реализованы.
Наличие заметки не меняет текущую подписку и не закрывает ADMIN-05a/5b.
