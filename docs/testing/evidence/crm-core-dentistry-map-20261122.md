# CRM-D04: граница ядра и начатого стоматологического модуля

Дата: 22.11.2026. Режим: архитектурный анализ + документация. Исходный HEAD
`4a3214a624d2bb1bf22b9f2daa22cd682fcebb93`, `codex/ui-testing-toolkit`, canonical root
`C:/Users/user/Desktop/PlatformaCRM`; существующий auth/integrations WIP не изменяется.
Источник scope: пользователь просит анализ всего функционала и относит реализованный
план посещений к стоматологической кастомизации. Это уточнение продуктовой границы,
не поручение переносить код, применять миграции или менять runtime-доступ.

Предыдущая карта21.11 → инвентаризация всех24 backend apps, моделей, API-регистраций,
frontend страниц и ссылок на планы, поиск отраслевого содержимого → классификация
ниже. Это статический функциональный охват проекта, а не чтение каждой строки,
новая сертификация всех API, security/performance review или проверка deployment.
Использован zani-analyze-crm-product: наблюдаемая реализация, целевая принадлежность,
пользовательский результат и ограничения evidence различаются. БД и пользовательские
данные не читались; UI, провайдеры, тесты, build и paid AI calls не запускались.

Приёмка docs-only: таблица покрывает24 apps; выделены dental-функции/смешанные
участки/нейтральные области; конкретные исходники и существующие проверки;
согласованы план/product/roadmap/паспорт; ссылки/registry/diff проверены.
Схема будущего исполнения остаётся в [едином плане](../../current/crm-modularity-plan.md),
эта карта — evidence среза, не отдельный backlog или разрешение на реализацию.

## Итоговая граница

**В текущем продукте стоматологический модуль = планы посещений + связанные
денежные операции + их UI/API/голосовые сценарии + собственное отраслевое содержимое.**
Запись, календарь, клиент, специалист, услуга, помещение, общий платёж, AI runtime
и Inbox остаются общими. Механика планов может переиспользоваться другими профилями
позже, но это не отменяет её нынешней принадлежности dentistry по решению владельца.

В коде нет отдельного Django app dentistry: начатый модуль распределён между
scheduling, payments, ai_core, bots, onboarding и frontend. Его не получится
выделить только переносом страницы VisitPlansPage или условием в меню.

Три различных употребления «план лечения»:

1. VisitPlan/VisitPlanStep — реализованный организационный план услуг и визитов.
2. «План лечения» в onboarding — название стадии шаблона, не клиническая модель.
3. Клинический план с зубной формулой/диагнозами/медицинскими назначениями — отдельные
   сущности и маршруты не обнаружены в рассмотренной инвентаризации. Наличие Note,
   custom fields или пользовательского текста не доказывает медицинскую карту.

## Классификация всех приложений

«Общее» означает общую функциональную основу/переиспользуемую подсистему; это не
требование включать все её экраны и отложенные функции каждому бизнесу.

| Область | Наблюдаемые возможности | Принадлежность / граница |
| --- | --- | --- |
| accounts | Регистрация, Google/social identity, сессии, MFA, recovery, настройки пользователя | Общая идентичность; не пациентский кабинет |
| businesses | Business, сотрудники, роли, scope, команды, приглашения, ownership transfer, capabilities, routing/SLA | Общее ядро; хранит выбор сферы, но не dental-данные |
| branches | Филиалы, доступ, услуги/специалисты филиала, графики, отсутствия, travel time, требования ресурсов | Общее ядро; кабинет/оборудование не специфичны для стоматологии |
| clients | Контакты, идентификация/дубли, merge, архив | Ядро; проверки/перенос связей VisitPlan являются точками интеграции модуля |
| services | Каталог, длительность и цена услуги | Ядро; названия «лечение кариеса» относятся к данным/шаблону, не модели Service |
| scheduling | Resource, часы/исключения, Appointment, ресурсные связи, сообщения визита, VisitPlan/Step | Смешанный app: записи/календарь общие; VisitPlan/Step и plan_* принадлежат dental-модулю |
| payments | Payment, возвраты, шесть Plan*-моделей | Общий Payment и обычный возврат остаются; плановые условия/распределение/остатки/corrections выделяются в dental-функции |
| leads | Заявки, внешние формы/поля/submissions/errors | Общие продажи; прежний backend/API сохраняется независимо от pilot-навигации |
| crm | Pipeline/Stage/Deal, terminal transitions, истории цены/стадии | Общие продажи; dental stage template — содержимое, не отдельная CRM-модель |
| conversations | Conversation/Message/QuickReplyTemplate, связанные действия | Общие диалоги и handoff |
| bots | Боты/каналы, Inbox, сообщения и batching, клиентские AI-сценарии | Общий runtime; dentistry-ветка PLAYBOOKS — отраслевое содержимое |
| ai_core | AgentProfile, знания, conversation/turn, jobs/logs/approvals, команды/аналитика/голос | Общее ядро AI; ветка создания VisitPlan внутри voice_schedule_commands — dental-адаптер |
| activities | История, заметки, теги, сегменты | Общая подсистема; VisitPlan events/read scope — интеграция модуля |
| tasks | Задачи, комментарии, напоминания | Общая подсистема; follow-up визита не dental-only |
| notifications | Уведомления, получатели, предпочтения, доставка | Общая подсистема; отраслевое имя/текст не меняет её принадлежность |
| automations | Rules/conditions/actions/runs, обработка событий и доменных команд | Общий механизм; плановые события/действия требуют доступа к модулю |
| analytics | События, виджеты, scheduled reports, workspace/management/finance projections | Общие отчёты; нет обнаруженного отдельного клинического отчётного домена. Плановые деньги должны входить без двойного учёта |
| integrations | Коннекторы, credentials, BusinessEvent, sync, webhooks, tokens, WhatsApp/YCloud и другие адаптеры | Общая инфраструктура; клиники используют тот же WhatsApp, не отдельный dental-канал |
| outreach | Шаблоны, кампании, получатели, согласия | Общие рассылки; отложенный Market scope не активируется этой картой |
| onboarding | Применение отраслевых templates, checklist, demo, первые channel actions | Общий механизм; dentistry-пакет услуг/ресурсов/стадий — отраслевое содержимое |
| core | Audit, support grants, idempotency, attachments/custom fields, import/export workspace, service status, management/platform routes | Общее ядро; plan projections/read filters остаются обязательными точками интеграции |
| billing | Subscription/UsageCounter, offer/order/attempt/receipt/event | Контур подписки на саму платформу; не лечение и не платежи клиентов |
| pricing | Каталог товаров, Kaspi rules/offers/recommendations/price changes/alerts | Отдельный торговый модуль; **не SaaS billing и не стоматология** |
| support | SupportCase, public/internal messages, read states, incidents | Общий платформенный контур поддержки |
| (frontend для перечисленных доменов) | Страницы CRM, настройки, голос, platform/support | Соответствует владельцу домена; общая оболочка не переносится в dentistry |

Контроль полноты:24 backend apps — accounts, activities, ai_core, analytics,
automations, billing, bots, branches, businesses, clients, conversations, core,
crm, integrations, leads, notifications, onboarding, outreach, payments, pricing,
scheduling, services, support, tasks. Frontend перечислен отдельно.

Основные источники охвата: [API](../../../config/urls.py),
[модели клиента](../../../apps/clients/models.py), [ресурсы/записи/планы](../../../apps/scheduling/models.py),
[филиалы](../../../apps/branches/models.py), [платежи](../../../apps/payments/models.py),
[торговый pricing](../../../apps/pricing/models.py), [billing](../../../apps/billing/models.py).
У остальных приложений проверены декларации моделей и зарегистрированные API;
внутренние алгоритмы всех операций заново не сертифицировались.

## Реализованная часть dental-модуля: данные и команды

| Часть | Реализация | Граница выделения |
| --- | --- | --- |
| План и этапы | VisitPlan, VisitPlanStep: клиент, ответственный, revision, архив/прекращение, service/resource/branch, назначенный Appointment, отказ/rebook provenance | Владение модулем; Client/Service/Resource/Branch/Appointment остаются общими ссылками |
| Работа с планом | create, revise, schedule, responsible, archive/restore, rebook | plan_services/plan_rebooking, selectors/access/serializers и VisitPlanViewSet принадлежат модулю |
| Договорённая стоимость | PlanTerms: per_visit/package, состав, версия, сумма/валюта, consent/reason, frozen условия | Плановая финансовая часть модуля |
| Зачёт оплаты | PlanAllocation: receipt → terms → appointment, reversal | Модульный расчёт поверх общего Payment; не новое поступление |
| Остаток | PlanRemainderDecision, PlanCreditTransfer: refund/retain/reuse/перенос между планами клиента | Модуль; общий возврат Payment используется повторно |
| Старые оплаты | PlanLegacyAttachment: связывание однозначного старого остатка | Модуль; receipt не дублируется |
| Исправление завершения | PlanCompletionCorrection: снятая цена/освобождённая сумма, replacement, actor/reason | Модуль; общая запись сохраняет свою историю |
| Прекращение/отказ | preview/refuse-service/terminate: согласие, версия preview, исключение неоказанной части, отмена времени | Модуль; блокировки, отмена follow-up и запись activity синхронны |

Источники: [plan services](../../../apps/scheduling/plan_services.py),
[API команд](../../../apps/scheduling/plan_views.py), [повтор этапа](../../../apps/scheduling/plan_rebooking.py),
[денежные операции](../../../apps/payments/plan_services.py),
[исправления](../../../apps/payments/plan_corrections.py),
[прекращение](../../../apps/payments/plan_termination.py).
`/api/visit-plans/` уже отдельный API, но текущие gates основаны на клиентах/записях,
а не на уже реализованном dentistry-профиле. Назначение профиля пока спецификация.

## UI и пользовательские входы

Dental-owned: VisitPlansPage, PlanEditor, PlanHistory, PlanPayments, PlanMoneyDialog,
PlanTermsHistory, PlanCorrectionDialog, AppointmentPlanPanel, API `visitPlans.ts` и
их planMoney/plans-подписи. Локализацию RU/KK/EN сохранять вместе с поведением.

Смешанные точки, где нельзя переносить компонент целиком:

- [RecordsPage](../../../frontend/src/features/calendar/RecordsPage.tsx): `view=plans`
  открывает план; список одиночных записей — ядро.
- [AppointmentCardOverview](../../../frontend/src/components/crm/appointment-card/AppointmentCardOverview.tsx)
  и AppointmentWorkspacePage встраивают панель плана; остальная карточка общая.
- [PaymentForm](../../../frontend/src/features/payments/PaymentForm.tsx) имеет optional
  plan, revision/stale recovery и выбор визита плана; общий платёж/возврат остаётся общим.
- ClientWorkspaceSections/ClientCardOverview/drawers показывают события/ссылки планов;
  карточка клиента не становится пациентской медицинской картой.
- [VoiceTurnResult](../../../frontend/src/features/voice/VoiceTurnResult.tsx) показывает
  результат плана и deep link; voice shell/useVoiceConversation общие.
- appointmentCache и shared types содержат связи с планами; инвалидация должна
  охватывать и план, и запись, и деньги, а не исчезнуть при разделении файлов.

Источники выделенных частей: [VisitPlansPage](../../../frontend/src/features/calendar/VisitPlansPage.tsx),
[API client](../../../frontend/src/api/visitPlans.ts),
[панель плана](../../../frontend/src/features/calendar/AppointmentPlanPanel.tsx).
Это статически достижимые входы по коду, не новая browser-проверка их исполнения.

## Настоящее отраслевое содержимое и ложные совпадения

1. [NICHES.dentistry](../../../apps/onboarding/templates.py): консультация стоматолога,
   чистка, лечение кариеса с примерными duration/price; врач/кабинет; стадия «План
   лечения», быстрые ответы. Dental-содержимое следует отделить от общего apply
   engine. **Не активировать этот seed при регистрации:** он пишет цены/ресурсы/
   графики/автоматизации, тогда как принятый профиль назначает возможности без demo.
2. [PLAYBOOKS.dentistry](../../../apps/bots/sales_playbooks.py): вопросы о проблеме,
   враче и срочности, правило цены после осмотра и подбора времени. Это уже dental
   preset. [bots.ai](../../../apps/bots/ai.py) подключает playbook по business_type
   только в auto_mode с booking_intent; он не является отдельным стоматологическим
   AI runtime и не заменяет врачебную диагностику.
3. В PLAYBOOKS/NICHES есть beauty/medical/sauna/autoservice/education. Это другие
   отраслевые presets, а не доказательство готовых самостоятельных модулей. Их
   содержимое не переносится внутрь dentistry.
4. Ключи aiSetup.dentalRole/dentalPrompt/applyDentalRole в RU/KK/EN сейчас содержат
   нейтральную роль администратора бизнеса. [aiAgentsUtils](../../../frontend/src/features/assistant/aiAgentsUtils.ts)
   использует их вне staff CRM mode. Переименование ключей не является разделением
   модулей; общие тексты и safety-ограничения остаются общими.
5. Упоминания «пациент» в safety matching и запрет диагнозов/лечения — общая защита
   диалога. Не удалять её у других сфер. DOCTOR как compatibility role и отрасль
   dentistry как enum/перевод тоже не самостоятельные dental-сущности.
6. «Кабинет» как помещение, график специалиста, цена услуги, отмена/неявка и
   напоминание нужны другим сферам. Их клиническое использование не меняет владение.

Проверенные декларации моделей/API не содержат отдельной зубной формулы, карты
диагнозов, медицинских назначений или авторизованного пациентского портала.
Файлы/notes/custom fields могут хранить произвольные данные бизнеса; их содержимое
не исследовалось. Поэтому не утверждается отсутствие любой медицинской информации
в пользовательских данных или полная юридическая готовность клинического продукта.

## Обязательные швы между ядром и модулем

| Ядро / место | Найденная связь | Как сохранить при дальнейшем выделении |
| --- | --- | --- |
| Appointment lifecycle | [services](../../../apps/scheduling/services.py): lock/touch плана при переносе/смене статуса, allocate_completed при completion | Синхронный модульный вызов внутри той же транзакции; порядок lock не менять произвольно |
| Общие платежи | Payment.plan, services/serializers используют plan_balances и guards | Общая запись receipt/refund остаётся в Payment; плановый adapter проверяет revision/доступ/остаток |
| Client merge | [services](../../../apps/clients/services.py) переносит VisitPlan и revision | Не терять план/деньги при merge, в том числе у legacy-бизнесов |
| Client archive | [lifecycle](../../../apps/clients/lifecycle.py) учитывает неназначенные незавершённые этапы | Скрытый модуль не разрешает архивировать клиента с обязательствами |
| Cards/activity/export scope | [crm_cards](../../../apps/core/crm_cards.py) добавляет plan_id; [crm_read_scope](../../../apps/core/crm_read_scope.py) фильтрует VisitPlan | Модуль поставляет разрешённую проекцию; не удалять фильтр и не раскрывать чужие/запрещённые данные |
| AI/голос | [voice_schedule_commands](../../../apps/ai_core/voice_schedule_commands.py): plan=true создаёт план и назначает этапы, plan=false создаёт один Appointment | В ядре оставить распознавание/approval/одиночную запись, plan-ветку отнести модулю; право проверять до любых созданий |
| Ввод/настройки | Создание Business и старые capability/onboarding writers | Следовать схеме профиля из плана; общий seed не подменяет однократное назначение |
| Общие отчёты | Финансовые и appointment projections | Суммировать общие receipt/refund/визиты; плановый зачёт не считать повторной выручкой |

Нужны явные небольшие сервисные интерфейсы, а не бизнес-логика через frontend
if(dentistry) или безымянные асинхронные signals. Односторонние imports — цель
структуры, но не основание ломать atomic money/booking. На первой реализации
оставить модели/app labels/таблицы/ID и существующие URL на месте.

## Порядок фактического разделения после отдельного поручения

1. Зафиксированная здесь принадлежность: общие сущности; VisitPlan и вся плановая
   оплата как dental-модуль; presets отдельно от механизма. Без массового rename.
2. По уже описанной схеме: resolver/profile gates и совместимость legacy, затем
   назначение при создании Business. Нет интерфейса управления/смены модулей.
3. Изолировать plan-операции/проекции через узкие интерфейсы в текущих apps;
   отдельно защитить существующие shared consumers и voice plan=true.
4. Подключать plan UI/AI-инструменты к серверной доступности; одиночная запись и
   общий платёж остаются рабочими у core. Отраслевые presets не применяются как seed.
5. Проверить один кандидат: core без планов; dentistry с полным plan-money циклом;
   legacy с историческими планами/остатками; отрицательные права и повторные запросы.

Не требуется перенос всех scheduling/payments/ai_core в dentistry или новый Patient.
Не требуется включение clinical features. Клиентский кабинет пока отдельная будущая
возможность, а не часть уже выполненной кастомизации.

## Проверки и предел вывода

Опорные существующие evidence: [планы](visit-plans-20261102.md),
[плановые деньги/corrections](visit-plan-payments-20261118.md),
[голосовой планировщик](voice-planner-20261111.md). Они относятся к своим срезам.
Новые runtime PASS здесь не заявляются; полный день клиники/deployment/AI RU-KK
не сертифицировались. Не путать реализованную команду с проверенной на сервере.

Для будущего разделения переиспользовать scheduling tests_visit_plans/
tests_plan_concurrency, payments tests_plan_payments/tests_plan_termination/
tests_plan_corrections/tests_plan_concurrency, client merge/archive и CRM-card/read
scope тесты; отдельно voice single vs plan, same-business/role/branch denial,
плановые возвраты/отказы/rebook, rollback/retry и PostgreSQL concurrency. Проверить
RU/KK/EN видимость plan-вкладок/ссылок и общий путь записи/оплаты. Это будущие gates,
не выполненные команды текущей docs-only задачи.

Итог текущего scope: функциональная граница определена и документирована;
физическое разделение кода и серверная активация не выполнялись. Следующая работа
требует отдельного поручения на реализацию. Старые функции/история не переписаны.
