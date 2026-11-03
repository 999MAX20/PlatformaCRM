# Единый реестр находок

Исполняемые проверки завершены; неисправленные дефекты и внешние границы остаются открыты. Общая версия текущего CRM:
`0b3348e1ab31121a106badbde830b496ec477aac` + исходный WIP из2463 хешей.
Все записи относятся к PlatformaCRM; REQ04 затрагивает только контракт с Market.
MOB-H относятся исключительно к историческому `73482a3bea7f168113c58d8cb928214c97f032d5`.
P1/P2/P3 — порядок устранения и влияние; не CVSS и не заявление об эксплуатации.
«Подтверждено» означает доказанный описанный сценарий, не исчерпывающую проверку.
Дефекты продукта в этом аудите не исправляются. Документационный DOC01 исправляется
в разрешённом объёме, с отдельным учётом чужого WIP.

## Требования и фоновая работа

| ID / тип / статус / приоритет | Требование, место и воспроизведение | Expected → actual; влияние | Рекомендация, зависимости, приёмка и решение |
| --- | --- | --- | --- |
| REQ01 / разрыв реализации / подтверждён / P1 | R01 AC05/08/09/14; scheduling VisitPlan/Step, payments Payment, plan API. Проверить поля моделей и зарегистрированные commands; независимое чтение двумя исполнителями. | Версионированные цены/пакет, аванс, зачёт/реверс/остаток → только неденежный план и receipt/refund Appointment/Deal. Полный денежный сценарий пилота недоступен. | Ledger/versions/rounding → atomic allocation/reversal → UI/history/metrics. PostgreSQL double spend/overrefund/race/rollback/replay и AC09/14. Только открытые zero-base/terminal-correction решения владельца перед зависимой реализацией. |
| REQ02 / разрыв реализации / подтверждён / P1 | Обязательный ограниченный D01; AgentConversationPanel send, ai_core inputs/planner. Поиск и чтение actual input path: текст; отдельная voice note не D01. | Текст/голос с редактированием/подтверждением → текстовые инструменты есть, audio/transcription flow отсутствует. Голосовой критерий не закрыт. | Сохранить существующие tools/rights/approval, добавить audio после выбора provider/retention. RU/KK/mixed/noise/permission/offline/retry/current-rights tests, запрет критического действия без подтверждения. Нужны только audio-решения/внешние данные. |
| REQ03 / дефект соответствия требованиям / подтверждён / P1 | AC06, conversations/booking.py105–118,219; ручной record_commands. Изолированный automatic booking:9 существующих controls PASS, две новые проверки null responsible/source FAIL. | AI default/current responsible и source conversation → автоматический путь оставляет оба поля null. Неполная ответственность/происхождение записи. | Общий Record-контракт, отдельная проверка authorizing actor и assignee, настройка accepted default. Happy/denied/tenant/revoked/default/stale/replay/rollback. Ранее закрытый ручной scoped-пакет не объявляется регрессией целиком. |
| CRM-TERMS01 / дефект согласования условий / подтверждён независимо / P1 | ai.md95–96; conversations/booking.py199–218 и branches/schedule snapshot. Actual SENT offer100/30, no-branch Business, ответ option1 после service update.4tests:2controlsPASS/2contractFAIL. | Изменённые цена/длительность требуют нового согласования → создаётся Appointment200/30 либо100/60; fingerprint прежний. Клиент получает не те условия, которые выбрал. Денежного списания в тесте нет. | Сверять offered/current terms под lock независимо от наличия филиала, отклонять mismatch до создания/effects. ZeroAppointment при stale price/duration; unchanged/branch/replay/availability/access controls. Перепроверено coordinator и backend reviewer; live provider и гонка этим тестом не доказаны. |
| CRM-EVENT01 / пропущенный доменный эффект / подтверждён / P2 | C07/AC07; scheduling/services.handle_appointment_created vs conversations.booking. Actual validated active appointment_created→create_task rule, inline real engine; только outbound confirmation mocked.2tests:manualPASS/automaticFAIL. | Одинаковое создание Appointment запускает правило → manual1successRun/1Task; automatic booked,0Run/0Task. Настроенная задача после автоматической записи не создаётся. | Общая orchestration создания с one-effect/replay/rollback и current permissions, без слепого второго вызова followups. Manual/automatic/plan/legacy callers проверять раздельно. Notification omission этим тестом не доказан; новая политика исключения auto-trigger не найдена. |
| OPS-Q01 / дефект deployment-конфигурации / подтверждён / P1 | docker-compose.yaml/compose.stand.yaml, config Celery queues/beat. Два независимых actual Celery inspections; default consumer только default; workers перечислены явно. | Все due queues исполняются → notifications, automations, reports_exports не имеют Compose consumer. Уведомления/автоматизации/экспорт могут оставаться в очереди в этом профиле. | Добавить/распределить consumers в отдельной реализации; real broker active_queues, due work/retry/restart/idempotency/alerts. Это shipped topology, не доказанный live outage; Render-профиль отличается. |
| REQ04 / будущий межпроектный разрыв / подтверждён в проверенной области / P2 | CRM integrations302–338; Market spec§23/schema/integration boundary на36081f0. Business int/Organization UUID, Decimal/minor units, generic sync primitives. | Verified binding/version/revoke/authority/no double money → конкретный CRM transport/binding и paired receipts не найдены. Generic integration не закрывает будущий обмен. | Capability/direction/source/ID/version/consent matrix, paired duplicate/out-of-order/revoke/refund tests, никаких вторых receipts. После пилота по решению02.11; не pilot blocker и не аудит всего Market. |

Доказательства: [матрица требований](requirements.md), backend receipts и
[независимая перепроверка](independent-review.md). Порядок реализации:
[план и production-условия](production-plan.md).

## Текущий web UI

Снимки/точные команды и результаты находятся в [UI/mobile отчёте](ui-mobile.md).
Если отдельно не указано, сценарий изолирован, владелец Business, EN1440,
синтетические данные. Прежние UX IDs сохранены как aliases, а не второй backlog.

Выбранные снимки: [Clients503](assets/clients-503.png),
[поиск за первой страницей](assets/global-search-needle.png),
[общий picker](assets/task-select-open.png),
[ложные несохранённые изменения](assets/ai-false-dirty-visible.png).

| ID / alias / тип / статус / приоритет | Место, сценарий и доказательство | Expected → actual; влияние | Исправление / приёмка / зависимости |
| --- | --- | --- | --- |
| UI01 / UX01 / дефект / подтверждён независимо / P1 | main.tsx17: boundary выше AppProviders; AppErrorBoundary fallback Button→useI18n. Два actual-source SSR воспроизведения; provider control отдаёт2buttons. | Рабочий аварийный экран → второе исключение useI18n. Нельзя воспользоваться восстановлением при падении дочернего UI. | Fallback независим от отказавших providers; forced descendant crash, visible reload/home, no second throw. Shared UI regression. Новое решение владельца не нужно для плана. |
| UI02 / UX02 / дефект / подтверждён / P2 | GlobalSearch/useEntityData.ts78;58tasks, needle за первой страницей. Header0matches, Tasks server search находит. | Поиск всего доступного набора → фильтрация только загруженной страницы. Пользователь не находит существующую задачу. | Scoped server search/query key/loading/error/paging; >50match/no match/503/account switch, без загрузки всех данных. |
| UI03 / UX04 / дефект / подтверждён / P2 | ClientsPage; начальный GET clients503, затем recovery200. Снимки clients-503/recovered. | Ошибка загрузки → вместе error, No clients yet, Total0. Ложное впечатление отсутствия данных. | Разделить initial error/stale/true empty/filter empty; retry и background503 с прежними данными. |
| UI04 / UX05 / accessibility дефект / подтверждён / P2 | Tasks>Create>Additional>Client None; SearchableSelect160–206. ArrowDown остаётся в INPUT; listbox unnamed/invalid children; Escape работает. | Именованный picker с клавиатурным выбором → неоднозначная семантика/навигация. Axe severity не security severity. | Coherent combobox/listbox/active option; loaded/loading/no match/error/paging, arrows/Enter/Escape/focus return, screen reader и representative consumers. |
| UI05 / UX06/07 / семантика и навигация / подтверждён / P2 | EntityWorkspace/MobileClientCards; nested mains, aria-selected на article;45sampled routes имеют один document title. | Однозначные landmarks/selection/route title → неверные semantics и одинаковый заголовок вкладки. | Single main, valid selection, route title/heading/skip navigation; keyboard/reader списков и деталей. Отсутствие h1 само по себе не объявляется универсальным WCAG нарушением. |
| UI06 / UX09 / дефект / подтверждён / P2 | /invite/not-a-valid-audit-token; generic failure +5inputs и disabled accept. | Недоступное приглашение с полезным следующим действием → неактуальная форма пароля. | Различить invalid/expired/revoked/network; valid+4negative/retry без раскрытия токена; утверждённый RU/KK/EN текст. |
| UI07 / UX10 / локализация / подтверждён / P2 | EN390 Clients last contact и Account sessions; MobileClientCards62/ActiveSessions51 вызывают formatter с default ru-RU. | Активная локаль → русский месяц в EN. | Текущий locale formatter; RU/KK/EN date/timezone/currency, пользовательские данные сохраняются. |
| UI08 / UX11/12 / текст и metadata / подтверждён / P3 | bots/pricing/automations показывают header Главная; bots future/developer copy; routeMetadata fallback. | Заголовок текущей страницы/правдивое состояние → default dashboard и неподходящий текст. | Дополнить metadata/approved copy, проверить3локали; функциональные настройки не удалять. |
| UI11 / UX08 / dirty state / подтверждён / P2 | Новый сохранённый inactive AI profile201, повторное открытие без ввода; motion-zoom-draft receipt. | Чистая сохранённая форма → There are unsaved changes +Cancel/Save. Ложное предупреждение и лишнее действие. | Нормализовать baseline и draft одинаково; save/reopen, null/default/inactive, actual edit/discard/retry/navigation. Не менять AI policy. |
| UI12 / UX motion / доступность / подтверждён / P3 | prefers-reduced-motion=true;4живых app routes сохраняют platforma-fade-in0.2s. | Уважение системного motion preference → анимация остаётся. | Reduced-motion style без движения; verify matchMedia/computed style/route transitions. Quality issue, не автоматическое утверждение о WCAG failure. |

## Проверки и зависимости

| ID / тип / статус / приоритет | Факт и влияние | Следующий шаг / приёмка |
| --- | --- | --- |
| UI09 / долг проверок / подтверждён / P2 |222Node tests:215PASS7FAIL; focused rerun воспроизводит7. Часть regex/inventory ожидает старый router/create-lead/fallback shape. Полный gate не зелёный. | Контракт→смысл assertions→точная корректировка теста/inventory, не удаление acceptance. Все относящиеся тесты должны проходить осмысленно, UI01 recovery проверяется отдельно. |
| UI10 / долг проверок / подтверждён / P2 | Records toolbar RU/KK/EN ожидают0dialogs, но утверждённый shared CalendarPopover — nonmodal role=dialog;3FAIL. Calendar tests также содержат старое ожидание отсутствия owner client_name. | Согласовать конкретную запрещённую старую modal/filter поверхность и актуальное право/текст, сохранить date/keyboard/current-flow проверки. Не маскировать продуктовый дефект изменением assertion. |
| SEC-DEP-01 / dependency policy gap / подтверждён / P2 | pip audit runtime+dev:14advisories в3dev-lock packages; frontend npm audit0. Direct apps/config/scripts use не найден. Удалённая эксплуатация runtime не доказана. | Совместимый обновлённый dev lock, deterministic clean CI/tooling/build и повторный audit. CVSS advisory не равен severity приложения; no dependency edits в аудите. Детали/primary advisories в security report. |
| PERF01 / производительность / подтверждён / P2 | B301 fixture, GET /api/work-queues/?limit=10 в legacy workflow:488SQL при бюджете58, полный и focused прогоны. Helpers вызывают per-item client readability без batch context. Измерение appointments workflow и масштаба отдельно в backend report. | Batch текущих разрешённых Client IDs/relations внутри запроса и actor+Business scope; не удалять проверки прав и не вводить общий cross-user cache. Повторить тот же query/payload budget,25/1000rows, limits10/50 и current appointments; отрицательные tenant/role/revoke cases. Число488 не объявляется числом запросов текущего dashboard. |
| PERF02 / стоимость выборки Clients / подтверждён независимо / P1 в измеренной границе готовности | GET /api/clients/,N=1000сущностей/domain и дополнительных клиентов: SQLite heavy median18.4s/20SQL; distributed single17.26s/20SQL/19KB. PG heavy warmup28.618s200; каждый50request профиль даёт10ClientsTimeout на10s deadline и40успехов прочих API. Несколько annotated COUNT/DISTINCT/summary/page queries занимают3.2–3.7s каждый в SQLite. | Разделить нужные annotations для page/count/summary/facets; сохранить scoped filters и полные counts. Сравнить25/1000heavy/distributed, SQLite/PG и query plans. Это блокер быстрого Clients-сценария на проверенном объёме, не всеобщий outage/cloud capacity. Distributed PG не измерялся; p95 attempts ограничен timeout и не равен latency завершения. [Независимая проверка](independent-performance.md). |
| PERF03 / N+1 карточки клиента / подтверждён / P2 | Client crm-card184SQL на25и1000fixtures, по5samples; существующий budget40. Shapes:51Business,50Client,25Deal fetches. crm_cards.py509 timeline без select_related при serializer, читающем business/client; conversation relation deal также не подгружен. | Подгрузить реально используемые relations и batch permission projection без выдачи скрытых данных; добиться действующего query/payload budget. Проверить owner/OWN/TEAM/denied, timeline limit, скрытые client/deal/branch, текущие права и сохранение response contents. Не считать повторные запросы оправданием ослабить guards. |
| VERIFY01 / долг тестов/фикстур / подтверждён / P2 | Full backend4FAIL: PERF01 плюс AI action-count2<3, multi-Business bell без selected business400, W018 при valid synthetic key. Semantic AI2named/0executed PASS; W018 local-audit key control PASS. | Закрепить текущий контракт в assertions/fixture; не скрывать исходный failed run. Изменение synthetic key объясняет W018, а не чинит production guard. Пересмотреть проверки количества/selected Business по принятому контракту, сохранив права и отсутствие execution. |
| VERIFY02 / устаревший recovery helper / подтверждён / P2 | Штатный S04 drill передаёт _s04_hold/invalid-user fixture, которые нынешняя action_validation отклоняет до ожидаемого fault window. Audit helper использует допустимые данные и отдельную имитацию сбоя. | Обновить shipped diagnostic в отдельной задаче без ослабления validation/rollback/retry assertions. Успех адаптированного audit drill не означает, что штатная команда исправлена. Исходный failure сохранён; production runbook должен ссылаться на фактически проверенный профиль. |
| DOC01 / документационная неточность / подтверждён / P2–P3 | Yandex/D01/Records/RPO/старые scoped остатки/миграции/публикация расходились с решениями и receipts. | Исправлены подтверждённые активные утверждения, исторические bodies сохранены. Полный per-file журнал/карта перемещений и local commit boundary в documentation report; архивирование0. |

Окончательные измерения, исходные неуспешные попытки и границы восстановления
сохранены в [backend отчёте](backend.md) и [матрице проверок](tests.md).

## Исторический native

Эти дефекты нельзя переносить на текущую web offline очередь: её реализация другая.
Текущий checkout не содержит исторического mobile API/приложения; OS/device proof
не получен. Поэтому P1 ниже условен относительно повторного использования native.

| ID / тип / статус / приоритет | Сценарий / expected → actual / влияние | Рекомендация и приёмка |
| --- | --- | --- |
| MOB-H01 / client intent/authorship defect / подтверждён независимо / P1 при reuse | A enqueue→logout→B login→actual replay/client; pending A command отправляется с B Authorization. Queue не actor-scoped. Fetch capture, без server mutation/утверждения tenant bypass. | Actor+Business+version scope, switch quarantine/clear policy, explicit recovery. A/B same/different Business, revoke, unknown response, stable retry; независимые server auth tests и OS lifecycle. |
| MOB-H02 / deep link дефект / подтверждён / P2 | zani://tasks/42→tasks42; advertised HTTPS /mobile/tasks/42→home из-за hostname parsing. | Trusted scheme/host/path, cold/warm/login-return/foreign/invalid; app association на устройстве отдельным proof. |
| MOB-H03 / silent queue loss / подтверждён / P2 |51enqueue→50retained, старейшая команда исчезла из-за slice50. | Нет молчаливого eviction, видимый capacity/storage error/conflict; concurrent enqueue/replay и lost-response idempotency. |

## Внешние ограничения и предложения

Это отдельные категории, не маскируемые дефектами и не закрываемые локальным PASS:

- **EXT-SEC:** Codex Security Deep Scan не стартовал из-за отсутствия managed
  filesystem permission profile. Нет scan ID или clean result; ручная проверка
  границ и isolated tests описаны отдельно. Нужен исправленный профиль для scan.
- **EXT-PROD:** нет установленного авторизованного облачного target и подготовленного
  Linux/container runtime; регион/ресурсы, фактические restore/HTTPS/операторы,
  sandbox/provider receipts и день пилота остаются открыты.
- **EXT-MOBILE:** Android SDK/emulator/java и Xcode/device/store/push credentials
  недоступны; native install/background/process recovery/camera/mic/update не
  проверены. Mobile web viewport/zoom не заменяет OS.
- **EXT-POLICY:** конфигурацию Yandex согласовать с действующим Kazakhstan data
  constraint; открытые деньги/audio/legal решения не подменять предположениями.
- **OPT-BUNDLE:** RU/KK chunk warning при проходящем app-shell budget; возможный
  split только после cold-load измерения, это необязательное улучшение.
- **OPT-RELEASE:** non-root/immutable images/separate migration job — hardening
  предложения с Linux/release acceptance, не доказанный exploit.

Все существенные реализации/проверки и оставшиеся данные связаны с
[матрицей](requirements.md) и [планом](production-plan.md); закрытия чужих задач,
новые бизнес-правила, deployments или разрешение следующего этапа не создаются.
