# Карта реализации и оставшихся границ

Дельта аудита 17.10 на `56dd124`: прежние scoped PASS не закрывают обнаруженные
обходы generic CRUD/изоляции, offline storage, автоматизации и неполные UI-сценарии.
[Результаты по областям](../testing/project-audit-20261017.md) и
[единственная очередь исправлений AUD](../current/roadmap.md#project-audit-20261017).
AUD-01 реализует изоляцию/очистку offline-данных заявок; AUD-02 — связи/авторство
notes/activity, назначение в формах и серверные журналы отправок. AUD-03 закрывает
выдачу Client.notes через API/карточки/сегменты/CSV по существующей field policy.
Версии и проверки — checkpoint AUD-01-20261017, AUD-02-20261017 и AUD-03-20261017.
AUD-13 закрывает обход UPDATE исходного объекта через PATCH/PUT и проводит
переназначение заявки через сервис; версия и проверки — checkpoint AUD-13-20261017.
AUD-14 защищает неизменяемую историю сообщений, parent scope и server-only delivery
metadata; send/retry сохраняют существующий путь. Версия/проверки — AUD-14 checkpoint.
AUD-15 проверяет связи конфигурации стадий/переходов и сохраняет pipeline существующей
стадии; версия и проверки — checkpoint AUD-15-20261019.
AUD-06 объединяет проверку конфигурации действий в preview/save/activate/execute;
предметная форма и ошибки RU/KK/EN проверены; версия/проверки — AUD-06 checkpoint.
AUD-04 обеспечивает атомарное создание/замену состава и audit/activity, защищает
активный состав при generic CRUD и конкурентных записях. Версия/проверки —
AUD-04-20261019 checkpoint. AUD-05 выполнен полностью в согласованном локальном
scope: редактор существующего правила, preview с UPDATE, атомарное сохранение
и сценарий до реальной Task; версия/проверки — AUD-05-20261019 checkpoint.
AUD-01/02/03/13/14/15/06/04 также выполнены полностью в своих локальных scope.
AUD-16 выполнен полностью в локальном scope: служебные поля ImportJob защищены,
preview/confirm используют row lock, повторную проверку прав, файла и строк.
Проверки112 SQLite +17 PG, system/migration drift; команды и границы — AUD-16 checkpoint.
AUD-20 выполнен полностью в локальном scope: доменное начальное состояние
API/import заявок и сделок, причины потери, серверные metadata, атомарная история
и фильтр активных открытых стадий UI/import/Inbox. Версия/проверки — AUD-20 checkpoint.
AUD-10 выполнен частично: готова изоляция очереди; остаются capacity без потерь,
durable command keys, replay/конфликты и recovery UX. Остальные пункты аудита
не выполнены, кроме частичного AUD-21: узкие PG races добавлены в AUD-16;
проверка полного критерия исходного риска/rollback/recovery остаётся. AUD-22 требует доказательства. Публикация и CI — отдельные
состояния; deployment/live приёмка не заявлены локальным PASS.
Остальные исправления не закрыты; это не новая
общая сертификация проекта.

Общая карта сверена 16.10.2026 на исходниках `dc1eedf`.
[Покрытие сверки и исправления статусов](../testing/docs-reconciliation-20261016.md).
Сверка статическая: маршруты, сервисы, UI и существующие test/evidence paths.
Новые runtime-тесты в документационной задаче не запускались. «Есть в коде»
не значит полная сертификация, deployment или допуск реальных клиентов.

Backend routes: [config/urls.py](../../config/urls.py).
Reachable UI: [router.tsx](../../frontend/src/app/router.tsx).
API слой: [frontend/src/api](../../frontend/src/api).
Это общая карта, не замена подробным паспортам и не новый backlog.
Предметные описания всех направлений — [реестр паспортов](README.md), порядок
оставшихся результатов и mapping acceptance — [единый roadmap](../current/roadmap.md).
Settings завершён: [реестр UI/API/потребителей](../testing/settings-functional-20261008.md).
Дополнение 08.10: [операционный UI-пакет](../testing/ui-operations-20261008.md)
обновляет шесть экранов и scoped work queues; это отдельная локальная проверка,
не общая сертификация или новая разработка CRM-аналитика.

| Область | Что присутствует в реализации | Источник / граница оставшейся работы |
| --- | --- | --- |
| Доступ сотрудников, ADMIN-04 | Scoped диагностика аккаунта/membership/роли/приглашений и зависимостей; отключение/восстановление, роль, отзыв/перевыпуск; обе platform-роли + MFA/обращение, личное согласие владельца для выдачи доступа, атомарный аудит и идемпотентность | [Сервис](../../apps/businesses/employee_access.py), [панель](../../frontend/src/features/platform/BusinessEmployeeAccessPanel.tsx), Account confirmations; локальные PostgreSQL/concurrency/browser/build PASS — checkpoint. Рабочая businesses0013 отдельно; глобальный unlock исключён, автоматической отправки нет, история ограничена50 последними запросами |
| Восстановление аккаунта, ADMIN-03 | Диагностика смены почты/MFA; обе platform-роли со свежим MFA и обращением, ручная проверка личности, подтверждение владельца для сотрудника, одноразовая новая почта/пароль, атомарный отзыв старых credentials; интерфейс оператора, владельца и получателя | [service](../../apps/accounts/recovery.py), [UI](../../frontend/src/features/platform/BusinessRecoveryPanel.tsx); опубликован dc1eedf, scoped PostgreSQL/concurrency/browser PASS — checkpoint; CI на момент сверки выполняется. Рабочая accounts0011, адрес поддержки/FRONTEND_URL и реальная SMTP-доставка отдельно. Это не автоматическая проверка достоверности документов и не передача Business |
| Административные реквизиты, ADMIN-01 | Отдельные GET/PATCH и вкладка карточки: allowlist, обе platform-роли, MFA, обращение/причина, revision, атомарный аудит и история | [сервис](../../apps/core/platform_details.py), [форма](../../frontend/src/features/platform/BusinessDetailsForm.tsx), [тесты](../../apps/core/tests_platform_details.py); опубликован f7d74d5, scoped PASS и CI success; не owner/recovery/billing и не deployment |
| Передача владельца, ADMIN-02 | Заявка с двумя личными подтверждениями, роль сотрудника или отключение доступа прежнему владельцу; platform_admin + MFA, атомарный аудит и отзыв сессий | [сервис](../../apps/businesses/ownership.py), [интерфейс](../../frontend/src/features/platform/BusinessOwnershipPanel.tsx), [тесты](../../apps/businesses/tests_ownership.py); опубликован cafcea5, локальная API/UI приёмка и CI PASS. Recovery без прежнего владельца и рабочая миграция не входят в эту границу |
| Platform console, PLATFORM-REBUILD-01 | Обзор/клиники/карточка: настройки, записанные ошибки и свежесть фоновых наблюдений разделены; MRR/подписки сохранены; status filter и no-data/403; прежние grant/MFA и журнал | [selectors](../../apps/core/platform_selectors.py), [UI](../../frontend/src/features/platform), [spec](../testing/platform-rebuild-spec-20261014.md); проверки в checkpoint; ручное создание клиники не реализовано; обращения — отдельная строка ниже |
| Филиалы, MB1–MB5 | Branch access, услуги/цены, несколько интервалов/переезды/отсутствие, календарь и AI booking | [Домен](../../apps/branches), [паспорт записи](scheduling.md); b48a822, scoped PASS, рабочая локальная активация 12.10 после backup; live отдельно |
| Операционная Главная | Полные distinct-счётчики, очередь действий, ближайшие записи, честное отсутствие финансовых данных | [work queues](../../apps/core/work_queues.py), [UI](../../frontend/src/features/dashboard/OperationalDashboard.tsx); локальная приёмка пакета 08.10, target/полный рабочий день отдельно |
| Обзор оператора, PLATFORM-OVERVIEW | Полные счётчики свежих сбоев/непроверенных клиник и активной поддержки с точными переходами; ограниченные очереди, компоненты/эпизоды, связанные обращения, ответственные; финансы сохранены | [read model](../../apps/core/platform_overview.py), [UI](../../frontend/src/features/platform/OverviewAttention.tsx); scoped проверки в checkpoint; подробный CRM read-path — отдельная строка ниже |
| Карточка клиники, PLATFORM-CLINIC-CRM | Пять разделов, постоянный подробный просмотр CRM/переписки/платежей, связанные записи и дочерние списки, scoped поддержка и аудит чтения | [read API](../../apps/core/platform_crm_views.py), [UI](../../frontend/src/features/platform/ClinicCrmBrowser.tsx); GET-only, без экспорта/impersonation/provider secrets; scoped проверки и публикация — checkpoint, live activation отдельно |
| Операции платформы, PLATFORM-OPERATIONS | Текущие фоновые эпизоды, подключения, история ошибок automation/integration/webhook и инфраструктура отдельно; фильтры клиники/компонента/свежести/UTC периода, полные counts, пагинация и обратный контекст | [read API](../../apps/core/platform_worklists.py), [UI](../../frontend/src/features/platform/PlatformOperationsPage.tsx); scoped проверки в checkpoint; журнал всех прошлых эпизодов и новые наблюдения не добавлены |
| Клиенты | Карточки, поиск/связи, история, archive/restore, проверка активных зависимостей | [clients](../../apps/clients), [services](../../apps/clients/services.py); общие edge cases и приёмка FC остаются |
| Заявки | Lifecycle, ответственный, конверсия/связи, lost reason | [leads](../../apps/leads/services.py), [tests](../../apps/leads/tests_crm_light.py); не обходить services |
| Сделки/воронки | Стадии, terminal actions, связи и история | [crm](../../apps/crm/services.py); новые stage-policy сценарии D-08 требуют правила |
| Календарь/специалисты | Resource без обязательного аккаунта, график/исключения, проверки slot/overlap, изменение записи | [scheduling](../../apps/scheduling/services.py), [availability](../../apps/scheduling/availability.py); кресла/оборудование отложены |
| Задачи/напоминания | Lifecycle, роли, назначение, due processing | [tasks](../../apps/tasks/services.py); target workers и follow-up policy отдельно |
| Inbox | Диалоги/сообщения/связи, ручная работа и human handoff; компактный scoped-инспектор клиента/будущих записей/CRM, точные переходы, мобильная панель и сохранение черновика | [conversations](../../apps/conversations), [проверки инспектора](../testing/task-state/PRIMARY-SESSION.md#inbox-inspector-20261008--approved-customer-context-and-action-placement); внешняя доставка не доказана наличием UI |
| Клиентский AI | Настройки/знания/память, публичные источники, контролируемое создание, safety budget, handoff/recovery | [Подробный паспорт](customer-ai-agent.md); 28 live-сценариев 08.10 PASS; реальный канал ещё не принят |
| CRM AI / аналитик | Существующие настройки, инструменты, подтверждённые команды и аналитические запросы | [ai_core](../../apps/ai_core), [пауза](crm-ai-agent.md); развитие остановлено решением, runtime не объявлен выключенным |
| Автоматизации | Conditions, 6 действий, WAIT/retry, leases/idempotency/cancel; редактор существующего состава, preview с UPDATE, атомарное сохранение | [engine](../../apps/automations/engine.py); реальная очередь/target recovery отдельно |
| Поддержка, PLATFORM-SUPPORT-20261015 | Клиника создаёт обращения; платформа назначает, отвечает, решает; явное повторное открытие, приватные заметки, read cursor, поиск/пагинация и черновики; employee — свои, owner/admin — все своей клиники | [domain/API](../../apps/support), [UI](../../frontend/src/features/support); scoped evidence в checkpoint. Миграция support0001 применена в локальной рабочей БД после backup/restore и проверки сохранности; вложений, внешних уведомлений, SLA и AI нет |
| Команда/безопасность | Business membership/roles, scoped APIs, сессии/MFA, support grant | [accounts](../../apps/accounts), [core](../../apps/core); target privileged MFA/операционные проверки обязательны |
| Связь эпизода и поддержки, PLATFORM-INCIDENT-LINK | Явное связывание существующего/нового обращения с component/episode той же клиники; неизменяемый снимок, текущая свежесть, обратные переходы, platform-only API | [domain](../../apps/support/incidents.py), [UI](../../frontend/src/features/support/SupportIncidentPage.tsx); изолированные проверки в checkpoint; support0002 не применена к рабочей БД; полного журнала всех эпизодов и автосоздания обращений нет |
| Импорт/дубли/архив | CSV/XLSX flow, preview/validation, domain links и работа с архивом | [imports](../../apps/core/import_export.py), [clients](../../apps/clients); не общий импорт произвольных моделей |
| Ручные деньги | Поступления/возвраты, неизменяемый журнал, replay/locks/overrefund защита | [payments](../../apps/payments/services.py), [tests](../../apps/payments/tests.py); не gateway пациента и не ERP |
| Финансовая аналитика | Явный manual или один external источник, period/freshness/no-data контракт | [financial_metrics](../../apps/analytics/financial_metrics.py); [external registry](../../apps/integrations/providers/registry.py) пуст, прибыль/долг не утверждены |
| Файлы/AV | Private access, quarantine/scan, leases/recovery, нормализация avatar | [core](../../apps/core), [operations](../current/operations.md); локальный AV работает, облачная приёмка/retention открыты |
| Экспорт | Sync CSV, async ExportJob, current permissions в worker, private download | [exports](../../apps/core/export_jobs.py); reports_exports/beat нужны в target |
| Состояние сервиса (S03) | Просроченная фоновая работа, начало/восстановление/устаревание инцидента; баннер сотрудникам и персональный колокольчик owner/admin с защитой от дублей; проверка связи с API | [service status](../../apps/core/service_status.py), [evidence](../testing/task-state/PRIMARY-SESSION.md#crm-s03-20261014--service-state-and-incident-notifications); isolated checks, рабочая миграция/worker/beat и независимый внешний мониторинг отдельно |
| Локальное восстановление (S04) | Реальные PostgreSQL/Redis/Celery/ClamAV в одноразовом стенде; restart/crash/retry/cancel без дублей, восстановление очереди из БД, pg_dump/restore и приватные файлы/тестовый ключ | [runner](../../scripts/verify_recovery_s04.py), [evidence](../testing/task-state/PRIMARY-SESSION.md#crm-s04-20261014--isolated-operations-and-recovery); Windows solo и локальное хранилище, целевая production-среда отдельно |
| Интеграции | Connector/provider services, credential store, webhook/pull/status/recovery foundation | [integrations](../../apps/integrations), [bots](../../apps/bots); Telegram/WhatsApp в подготовке R02, прочие подключения отложены; provider-specific live допуск не заявлен; остаток UI — [паспорт](integrations.md) |
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
