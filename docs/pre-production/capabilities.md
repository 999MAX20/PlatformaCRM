# Карта реализации и оставшихся границ

Срез 07.10.2026, исходники `f01d22610118e3a24df86257943a8be91314f916`.
Сверка статическая: маршруты, сервисы, UI и существующие test/evidence paths.
Новые runtime-тесты в документационной задаче не запускались. «Есть в коде»
не значит полная сертификация, deployment или допуск реальных клиентов.

Backend routes: [config/urls.py](../../config/urls.py).
Reachable UI: [router.tsx](../../frontend/src/app/router.tsx).
API слой: [frontend/src/api](../../frontend/src/api).
Это общая карта, не замена подробным паспортам и не новый backlog.
Дополнение 08.10: [операционный UI-пакет](../testing/ui-operations-20261008.md)
обновляет шесть экранов и scoped work queues; это отдельная локальная проверка,
не общая сертификация или новая разработка CRM-аналитика.

| Область | Что присутствует в реализации | Источник / граница оставшейся работы |
| --- | --- | --- |
| Операционная Главная | Полные distinct-счётчики, очередь действий, ближайшие записи, честное отсутствие финансовых данных | [work queues](../../apps/core/work_queues.py), [UI](../../frontend/src/features/dashboard/OperationalDashboard.tsx); локальная приёмка пакета 08.10, target/полный рабочий день отдельно |
| Клиенты | Карточки, поиск/связи, история, archive/restore, проверка активных зависимостей | [clients](../../apps/clients), [services](../../apps/clients/services.py); общие edge cases и приёмка FC остаются |
| Заявки | Lifecycle, ответственный, конверсия/связи, lost reason | [leads](../../apps/leads/services.py), [tests](../../apps/leads/tests_crm_light.py); не обходить services |
| Сделки/воронки | Стадии, terminal actions, связи и история | [crm](../../apps/crm/services.py); новые stage-policy сценарии D-08 требуют правила |
| Календарь/специалисты | Resource без обязательного аккаунта, график/исключения, проверки slot/overlap, изменение записи | [scheduling](../../apps/scheduling/services.py), [availability](../../apps/scheduling/availability.py); кресла/оборудование отложены |
| Задачи/напоминания | Lifecycle, роли, назначение, due processing | [tasks](../../apps/tasks/services.py); target workers и follow-up policy отдельно |
| Inbox | Диалоги/сообщения/связи, ручная работа и human handoff | [conversations](../../apps/conversations); внешняя доставка не доказана наличием UI |
| Клиентский AI | Настройки/знания/память, публичные источники, контролируемое создание, safety budget, handoff/recovery | [Подробный паспорт](customer-ai-agent.md); 28 live-сценариев 08.10 PASS; реальный канал ещё не принят |
| CRM AI / аналитик | Существующие настройки, инструменты, подтверждённые команды и аналитические запросы | [ai_core](../../apps/ai_core), [пауза](crm-ai-agent.md); развитие остановлено решением, runtime не объявлен выключенным |
| Автоматизации | Conditions, 6 действий, WAIT/retry, leases/idempotency/cancel | [engine](../../apps/automations/engine.py); реальная очередь/target recovery отдельно |
| Команда/безопасность | Business membership/roles, scoped APIs, сессии/MFA, support grant | [accounts](../../accounts), [core](../../apps/core); target privileged MFA/операционные проверки обязательны |
| Импорт/дубли/архив | CSV/XLSX flow, preview/validation, domain links и работа с архивом | [imports](../../apps/core/import_export.py), [clients](../../apps/clients); не общий импорт произвольных моделей |
| Ручные деньги | Поступления/возвраты, неизменяемый журнал, replay/locks/overrefund защита | [payments](../../apps/payments/services.py), [tests](../../apps/payments/tests.py); не gateway пациента и не ERP |
| Финансовая аналитика | Явный manual или один external источник, period/freshness/no-data контракт | [financial_metrics](../../apps/analytics/financial_metrics.py); [external registry](../../apps/integrations/financial_sources.py) пуст, прибыль/долг не утверждены |
| Файлы/AV | Private access, quarantine/scan, leases/recovery, нормализация avatar | [core](../../apps/core), [operations](../current/operations.md); локальный AV работает, облачная приёмка/retention открыты |
| Экспорт | Sync CSV, async ExportJob, current permissions в worker, private download | [exports](../../apps/core/export_jobs.py); reports_exports/beat нужны в target |
| Интеграции | Connector/provider services, credential store, webhook/pull/status/recovery foundation | [integrations](../../apps/integrations), [bots](../../apps/bots); направление отложено, provider-specific live допуск не заявлен |
| Billing | Код entitlements/subscription и интерфейсы существуют | [billing](../../apps/billing); коммерческий пакет/цены/процессинг не завершены, развитие отложено |
| Интерфейс | Рабочие маршруты, общие компоненты, RU/KK/EN, neutral/emerald tokens, состояния восстановления | [frontend](../../frontend/src); полная FC/manual/reader приёмка остаётся |
| Эксплуатация | Настройки/скрипты health, workers, monitoring, backup/restore foundation | [scripts](../../scripts), [settings](../../config/settings.py); нет утверждения о развёрнутом paid production |

## Что делать дальше при новом поручении

Сначала выбрать один требуемый результат и [непройденную границу](../current/acceptance.md).
Для актуального Inbox AI [локальный пилот 08.10](../testing/inbox-local-pilot-20261008.md)
прошёл, включая handoff и настройки; следующая отдельная граница — согласованный channel/target flow. Бюджет,
получатели, deployment и следующий этап здесь не утверждаются.
Для остальной CRM использовать существующие слои и проверять конкретный
regression/недостающий критерий; не реализовывать модуль заново по старому плану.

Разделение готовности, Git/CI и среды — [состояние проекта](project-state.md).
Действующие требования — [реестр документов](../README.md).
