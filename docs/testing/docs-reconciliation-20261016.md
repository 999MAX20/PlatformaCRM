# Сверка технической документации и roadmap — 16.10.2026

DOCS-RECONCILIATION-20261016. Владелец поручил сопоставить действующие технические
документы и этапы с реализацией, актуализировать статусы, сохранить остаток закрытых
этапов и установить правила дальнейшего сопровождения.
Срез кода `dc1eedf93a1532f538cd513a339130b3b4580835`, canonical root
`C:/Users/user/Desktop/PlatformaCRM`, ветка `codex/ui-testing-toolkit`.

Это статическая сверка описаний/статусов, source paths, API/UI и существующего
evidence, а не новый полный функциональный или security-аудит. Тесты из checkpoint
сохраняют свои версии и среды. Код, БД, процессы, провайдеры и тарифы не менялись.
Архивные отчёты и generated inventory не переписаны под новый PASS.

## Главный результат

ADMIN-01/02/03, MB1–MB5, R01 и S01–S04 уже имеют реализацию и scoped-приёмку.
Устаревшие утверждения «не начато» и старые блокеры публикации исправлены.
ADMIN-04/05, приёмка всего административного набора и production-границы не закрыты.
Визуальная приёмка Подключений не устранила все функциональные замечания 08.10:
конкретный остаток приведён ниже и связан с прежним этапом, без нового backlog.

## Метод и покрытие

Граница действующих документов взята из [реестра](../documentation-index.json).
Проверены описания результатов, статусы и их связи с профильными исходниками,
маршрутами, тестами, checkpoint и Git. Для неизменённых контрактных требований
не утверждается новое доказательство их выполнения во всех сценариях.
Строки ниже покрывают все текущие предметные контракты и технические паспорта;
процедуры, навигация и dated evidence рассматриваются отдельно.

| Документ / область | Реализация и доказательства сверки | Вывод / актуализация |
| --- | --- | --- |
| [Продукт](../current/product.md) | apps/branches, scheduling, platform actions; MB1–MB5 и ADMIN checkpoint | Многофилиальность уже выполнена; Telegram/WhatsApp в подготовке R02; три ADMIN-действия реализованы; коммерческий billing не готов |
| [Roadmap](../current/roadmap.md) | Git до dc1eedf, checkpoint S/R/MB/ADMIN | Обновлены срез и статусы, добавлены заметки «сделано/осталось/условие закрытия»; D-04 решён, определения текущей аналитики приняты |
| [Приёмка](../current/acceptance.md) | apps/analytics/workspace.py, S01/R01/MB evidence | D-06 уточнён по принятым определениям 14.10; общие FC/UX, live/target, новые D-сценарии сохранены |
| [CRM](../current/crm.md) | services клиентов/заявок/сделок/задач/записи, branches, analytics/workspace | MB1–MB5 не будущая разработка; локальное закрытие отделено от target; деньги/жизненные циклы не переопределены |
| [Доступ](../current/access.md) | platform_crm_views/selectors, platform_details, businesses/ownership, accounts/recovery, support/access | Постоянное GET-чтение CRM и узкие ADMIN-права отделены от старого support-note; manager не получает общего write-доступа |
| [AI](../current/ai.md) | branches/bot_context, conversations/booking, bots/handoff_recovery, safety и approvals | Филиалы реализованы; старый real-model PASS не сертифицирует новые входы/таймер/шаблон; пауза внутреннего AI сохранена |
| [Frontend](../current/frontend.md) | router, platform/account/support, shared controls, calendar/inbox/settings | Поддержка в меню и ADMIN-02/03 отражены; основной CRM read-path GET-only; scoped UI не общая accessibility-приёмка |
| [Интеграционный контракт](../current/integrations.md) | integrations/providers/registry, import_export, export_jobs | Требования сохраняются; финансовый reader registry пуст. Контракт не выдаёт live-допуск; обнаруженный UI-разрыв описан в паспорте/roadmap |
| [Эксплуатационный контракт](../current/operations.md) | config/settings, migrations, verify_recovery_s04, service_status; activation receipts | Казахстан вместо прежнего Yandex; ADMIN02/03 рабочая активация отдельно; backup/RPO/RTO/target не приняты локальным стендом |
| [Инженерные правила](../current/engineering.md) | AGENTS и task template | Добавлено обязательное сопровождение roadmap и профильных документов вне него; архитектурные требования сохранены |
| [Карта возможностей](../pre-production/capabilities.md) | домены/API/UI из строк выше | Добавлены ADMIN01/02/03 и филиалы, общий срез и остаток интеграционного UI |
| [Состояние проекта](../pre-production/project-state.md) | Git, CI API и scoped checkpoints | Срез обновлён; старые PASS оставлены историческими; общий production не объявлен |
| [Клиенты](../pre-production/clients.md) | clients/services/lifecycle/workspace, ClientsPage; CRM-TOOLBARS/S01/R01 | Основные сценарии сохраняются; уточнена связь с уже закрытым scoped R01 и новой общей границей |
| [Заявки/сделки](../pre-production/leads-deals.md) | leads/crm services/workspace, LeadsPage/DealsPage, server scenario tests | S01/toolbar дельты учтены; новый stage graph и terminal corrections не утверждены |
| [Запись](../pre-production/scheduling.md) | branches/services/schedule, scheduling/availability, CalendarPage, MB tests | Исправлено ложное «рабочая БД не мигрировалась»; receipt12.10 подтверждает отдельную активацию после backup |
| [Задачи/автоматизации](../pre-production/tasks-automations.md) | tasks/services/mutations, automations/engine; TASKS-REDESIGN/S01/S04 | Waiting/revision/replay и D-04 отражены; локальный реальный recovery не заменяет target workers |
| [Inbox](../pre-production/inbox.md) | bots/inbox_service, conversations/client_linking, handoff_recovery, ConversationsPage | UI/relink и таймер имеют разные версии; живые каналы/terminal policy остаются |
| [Клиентский AI](../pre-production/customer-ai-agent.md) | branch context, booking, handoff_recovery, neutral profile; dated model reports | Добавлена явная граница новых дельт после 08.10; нет нового real-model PASS |
| [Внутренний AI](../pre-production/crm-ai-agent.md) | apps/ai_core, work/analytics routes | Без изменения: код сохранён, направление D01 на паузе; обычная аналитика 14.10 не возобновляет AI-аналитика |
| [Identity/access](../pre-production/identity-access.md) | recovery/ownership API, platform panels и Account confirmations | Исправлен слишком широкий запрет manager write; добавлены recovery/transfer и остаток активации |
| [Деньги/аналитика](../pre-production/money-analytics.md) | payments/services, analytics/workspace/manual_finance, registry | Определения текущего отчёта уже приняты; manual ledger не SaaS billing/прибыль; новые метрики отдельно |
| [Данные/архив](../pre-production/data-lifecycle.md) | core/archive/import_export/export_jobs, clients merge; S01/S04 | Существующие инварианты и ограниченные виды импорта сохранены; target storage/recovery и спорный приоритет импорта не закрыты |
| [Настройки](../pre-production/settings-notifications.md) | settings sections, team forms, scheduling/message_settings, preferences | Редизайн/роль legacy-участника и скрытые формы отражены; SMTP/очереди не закрываются старым CI |
| [Интеграции](../pre-production/integrations.md) | IntegrationsPage, ProviderCard, API CRUD, TenantModelViewSet/serializer | R02 уточнён до двух каналов; функциональный остаток UI сохранён ниже |
| [Подписка](../pre-production/subscription-usage.md) | billing models/services/entitlements, пустой BillingSection | Foundation существует; GRACE/READ_ONLY целевого V1 и recovery по оплате не заявляются реализованными |
| [Файлы/AV](../pre-production/files-antivirus.md) | core/file_scanning/antivirus/file_attachments, S04 runner | Без смены политики; локальный AV/recovery есть, cloud storage/retention/R04 открыты |
| [Эксплуатация](../pre-production/operations.md) | S03/S04, platform worklists/read-path, activation receipts | Исправлен Yandex, разделены support-note/обращения/ADMIN и старый CI |
| [Шаблон паспорта](../pre-production/module-template.md), [реестр паспортов](../pre-production/README.md) | AGENTS/engineering | Добавлен обязательный результат/остаток с evidence и проверкой согласованности |

## Конкретные остатки закрытых работ

### Подключения: UI закрыт, функциональное подключение не принято

Сверка прежнего [анализа 08.10](integrations-functional-review-20261008.md) на dc1eedf:

| Наблюдение | Текущее доказательство | Статус и критерий будущего закрытия |
| --- | --- | --- |
| Выбранный Business и полнота списка | [IntegrationsPage](../../frontend/src/features/integrations/IntegrationsPage.tsx): query key с business.id, но list без параметра, затем find только по provider. [CRUD](../../frontend/src/api/crud.ts) читает одну страницу; [TenantModelViewSet](../../apps/core/viewsets.py) возвращает доступные businesses | Разрыв сохраняется по коду: возможен неверный контекст среди уже разрешённых бизнесов и скрытие экземпляров. Нужны серверный фильтр выбранного Business, корректный клиентский запрос и multi-business/pagination проверка. Это не доказанная утечка в запрещённый tenant |
| Ручная конфигурация 1С | [ProviderCard](../../frontend/src/features/integrations/components/ProviderCard.tsx) отправляет api_key/webhook_secret в config_json; [serializer](../../apps/integrations/serializers.py) отвергает sensitive_config_paths | Несовместимость сохраняется по коду; новое runtime-воспроизведение не запускалось. Нужен согласованный encrypted credential flow либо удаление неподдержанного действия; backend-защиту не ослаблять |
| Обработка ошибки внутри формы | ProviderCard теперь включает ErrorState в connectionDetails внутри Modal | Прежнее размещение ошибки за окном изменено; новый browser PASS в этой сверке не заявляется |
| Счётчик/URL фильтров и огромные плитки | Текущий IntegrationsPage содержит две компактные карточки без прежних счётчиков/фильтров | Старые замечания к удалённым элементам не являются текущими неисправностями; visual scope13.10 сохраняет закрытие |
| Ошибка загрузки, view без manage, история операций | При pageError каталог/кнопки остаются; первичная кнопка disabled без manage; healthCheck инвалидирует connectors, но не sync-runs; отдельного syncRuns error UI нет | Остаток функциональной приёмки: unknown/error и доступность действий, отдельное чтение разрешённых деталей, обновление истории/ошибок. Требует targeted flow при поручении исправления |

Это уточняет закрытие INTEGRATIONS-SIMPLIFY/UI и существующие CRM-D03/BE-GAP-010;
не запускает live1С и не поручает новую реализацию. Platform diagnostics с собственной
классификацией connector states — отдельный экран и не исправляет merchant list.

### ADMIN и эксплуатация

Подробные три реализации и остаток — [спецификация 15.10](platform-rebuild-spec-20261014.md#1510-сверка-реализации-и-остатка--16102026).
ADMIN-03 локально закрыт; остаются accounts0011, support email, FRONTEND_URL,
почтовый транспорт и фактическая доставка в разрешённой среде. Ручная идентификация
проверяет человека организационно; наличие строки verified_reference не доказывает
истинность документов. Recovery не активирует заблокированные аккаунты, список
последних 50 заявок не является полноценным поиском всей истории.

ADMIN-02 требует отдельной рабочей businesses0012. ADMIN-04/05 не закрыты;
Billing metadata и MRR не доказывают оплату и не выполняют восстановление подписки.
Локальные активации branches/scheduling, support0001 и bots0012 подтверждены
собственными receipts; core0012/support0002 и target collector/worker остаются
отдельной границей. Состояние работающих процессов 16.10 здесь не проверялось.

### Ранее принятые этапы

R01 закрыт с явным исключением FB-009; reader PASS отсутствует. S01 решает D-04,
но не закрывает все новые lifecycle/приоритетные вопросы. S04 имеет настоящий
изолированный PostgreSQL/Redis/Celery/ClamAV recovery, но не Linux/cloud/target
приёмку. MB5 и таймер AI появились позже real-model отчётов 08.10; их нельзя
считать автоматически покрытыми теми 43 сценариями. Полный остаток закрытых этапов
теперь находится непосредственно в [roadmap](../current/roadmap.md#заметки-к-выполненным-этапам--сверка-16102026).

## Остальные действующие документы

- [Спецификация платформы](platform-rebuild-spec-20261014.md) актуализирована по
  коду/сценариям; исходные анализы 14–15.10 явно отделены от текущей сводки.
- [Settings functional](settings-functional-20261008.md), [redesign](settings-redesign-20261009.md),
  [workflow](settings-workflow-20261009.md), [UI operations](ui-operations-20261008.md)
  сохраняют историческое evidence. Позднейшие toolbar/calendar/settings изменения
  отражены в контрактах/паспортах; старые интерфейсы отчётов не становятся требованиями.
- [Inbox model](inbox-live-acceptance-20261008.md) и [локальный пилот](inbox-local-pilot-20261008.md)
  сохраняют исходные версии/модель/контролируемый канал; свежий PASS не приписан.
- [Вопросы бизнеса 16.10](business-logic-questions-20261016.md) остаются предложениями,
  не одобрением новой политики. Их исходный статус ADMIN03 в работе исторический;
  текущий статус — в этой сверке и профильной спецификации.
- [Testing](testing.md), [UI toolkit](ui-testing-toolkit.md), [SESSION_ROLLOVER](SESSION_ROLLOVER.md)
  сохраняют правила изоляции и пропорциональности; новых runtime-проверок для Markdown
  не требуется. [Task template](CODEX_TASK_TEMPLATE.md), [AGENTS](../../AGENTS.md)
  и engineering дополнены обязательными заметками и обновлением профильных документов.
- [README](../../README.md), [docs index](../README.md), [handoff](../../actual_docs/PROJECT_HANDOFF.md),
  [STATUS](../../STATUS.md) актуализированы; прежние межчатовые процедуры помечены историей.
  [Backend README](../../apps/README.md), [frontend README](../../frontend/README.md),
  [служебная навигация](../../actual_docs/README.md) не нуждаются в изменении карты исходников.
- [Defect knowledge](../../actual_docs/DEFECT_KNOWLEDGE_BASE.md), agent skills и
  [generated fallback inventory](../../actual_docs/UNIFIED_FALLBACK_INVENTORY.generated.md)
  не являются roadmap/паспортами модулей. Регрессионные правила не переписывались,
  каталог не регенерировался и его счётчики не объявлены свежей сертификацией.

## Публикация реализации и проверки этой сверки

Git history подтверждает ADMIN-01 `f7d74d5`, ADMIN-02 `cafcea5`, ADMIN-03 `dc1eedf`.
GitHub Actions API16.10: CI38795538634 и CI38862446607 completed/success;
CI38873408099 (ADMIN03) in_progress на момент чтения. Отдельная публикация docs
не превращает этот промежуточный статус в success. Workflow CI не содержит deploy.

Точные docs-only команды, результаты ссылок/реестра/diff, commit/push/actual CI
сохраняются в [checkpoint](task-state/PRIMARY-SESSION.md#docs-reconciliation-20261016--current-documentation-and-roadmap)
и итоговой квитанции задачи. App install/build/DB/browser suites не запускались:
runtime не изменён. Следующие продуктовые этапы этим отчётом не начаты.
