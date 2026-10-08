# Ручные платежи, операционные показатели и аналитика

Срез `768b2675`, 09.10.2026. Управляющий видит состояние работы и зарегистрированные
деньги; сотрудник в рамках прав вносит факт оплаты. Контракт — [CRM](../current/crm.md).
Сумма сделки, цена услуги, фактическая оплата и SaaS-подписка — разные данные.

## Текущее поведение

Payment — неизменяемый журнал receipts/refunds, не банковский перевод. Положительный
Decimal в валюте бизнеса, не будущее время; клиент и необязательная сделка либо
запись того же клиента/Business доступны actor. Возврат требует manage и причину,
не превышает остаток receipt, не предшествует ему; refund of refund запрещён.
Submission ID/hash защищают retry; Business lock сериализует ledger writes.
Запись и audit атомарны, широкая клиентская activity не раскрывает сумму/причину/заметку.

Главная показывает distinct work queues и реальные ближайшие записи с соблюдением
прав; ограничение preview не обрезает полный счётчик. Операционная аналитика
использует свои источники и не требует финансового коннектора для обычных CRM-метрик.
Финансы выбирают manual либо один external источник, не сумму нескольких систем.
Manual — журнал точного периода в timezone бизнеса; пустой журнал означает ноль
записанных операций, не полноту бухгалтерии. External требует проверенный локальный
snapshot точного периода/валюты с успешным sync run; registry readers пока пуст.

## Доступ и ошибки

Payments view/create/manage и scope клиента/связей обязательны; manager по умолчанию
не получает refund. Финансовая сводка требует BUSINESS-доступ по контракту.
Нет проверенного источника — unavailable/null, не ноль; доступный старый снимок при
сбое обновления обозначается stale с временем. Receipts/refunds/net не объявляются
прибылью или долгом. UI не заменяет запрещённые данные фиктивной статистикой.

## Реализация и доказательства

[Ledger](../../apps/payments/services.py), [tests](../../apps/payments/tests.py),
[financial report](../../apps/analytics/financial_metrics.py),
[manual](../../apps/analytics/manual_finance.py), [registry](../../apps/integrations/providers/registry.py),
[work queues](../../apps/core/work_queues.py),
[payment API](../../frontend/src/api/payments.ts), [analytics UI](../../frontend/src/features/analytics/AnalyticsPage.tsx).
API `/api/client-payments/`, `/api/work-queues/`, `/api/analytics/…`;
UI карточки CRM, `/app/dashboard`, `/app/analytics`.
[Операционный UI evidence](../testing/ui-operations-20261008.md) — scoped local PASS,
не финансовая/production сертификация всех метрик.

## Цель и открытое

[R01](../current/roadmap.md): D-06/V1-O08 определений выбранных метрик;
R05 — работа персонала. Gateway пациентов — D05, external accounting — D03,
новые KPI — D06, CRM AI-аналитик — D01; эти направления не запущены паспортом.
09.10 — описание опубликованной основы без новых денежных операций.
