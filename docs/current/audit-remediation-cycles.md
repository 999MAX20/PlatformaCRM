# Исправления по полному аудиту: рабочие циклы

Статус: **C01–C07 закрыты локально; остальные циклы не начаты**. Дата: 04.11.2026.
C01 исправляет изоляцию helpers, predicates и recovery fixture; проверки и границы
записаны в [evidence](../testing/evidence/remediation-c01-20261104.md).
Следующий исполняемый цикл — **C08**. Один последующий
«приступай/продолжай» означает один следующий цикл, а не автоматическое выполнение
всего списка. Это детализация существующих находок, не новый независимый backlog.

Основание: [«Находки»](../../output/full-audit-20261104/report/findings.md),
[машиночитаемый реестр](../../output/full-audit-20261104/report/findings.json),
[исходные группы](../../output/full-audit-20261104/remediation-groups.json),
[порядок устранения](../../output/full-audit-20261104/report/remediation-plan.md).
Аудит относится к d27044b1 + учтённому WIP, материалы сохранены в58935fa.
План начинается от58935fa05469f077e1a4c45867cac02692ab64b5 на
`codex/ui-testing-toolkit` в `C:/Users/user/Desktop/PlatformaCRM`.

## Что означает один цикл

Один цикл даёт один ограниченный проверяемый результат: воспроизведение на текущем
срезе → минимальное исправление → focused checks → зависимые проверки → документация
и запись фактического статуса. Это граница работы, а не обещание времени или числа
файлов. При обнаруженной дополнительной политике/среде блокируется только зависимый
сценарий; незавершённый цикл не помечается закрытым и не расширяет scope.

Перед каждым циклом сверить его source/evidence/acceptance в исходной находке,
изменения после аудита и чужой WIP в точных затрагиваемых участках. Отсутствие нового
воспроизведения не доказывает исправление. Не повторять полный аудит. Использовать
существующие domain services, selectors, adapters и UI/API layers; не подменять
исправление новым framework. Таблицы ниже дополняют, а не сокращают исходные критерии.

Каждый цикл начинает со статуса «не начат». В ходе исполнения прямо в его строке
записывать «в работе», «заблокирован: причина» или «закрыт локально: commit/evidence».
После него обновить этот файл, выбранный checkpoint и затронутые контракты/паспорта;
указать остаток отдельно как код, доказательства, среда или решение владельца.

Все87 канонических IDs учтены. UI14 — alias ATTACHMENT-RETRY в C15, не88-я находка.
REQ01/REQ02/REQ04 намеренно встречаются в нескольких последовательных циклах:
родительская находка закрывается только при выполнении всех её критериев.
Всего63 цикла:50 текущего CRM,4 денежных,3 голосовых,2 Market и4 native.
Для Market X02 — один поток; число дополнительных потоков определяет согласованный
контракт X01. Поэтому63 — текущая декомпозиция, не обещание полного Market за2 цикла.

## Общая приёмка и обозначения проверок

Точные команды выбирать по [testing.md](../testing/testing.md) и
[шаблону задачи](../testing/CODEX_TASK_TEMPLATE.md) до правки. Полный release gate
не запускать только из-за размера списка, commit или восстановления контекста.

| Код | Минимальная обязательная граница |
| --- | --- |
| B | Backend: focused тест после каждого связного service/API изменения, happy/invalid, применимые role/tenant/lifecycle/audit/replay/rollback; в конце dependent suites + system/migration-drift в изоляции. Для concurrency — PostgreSQL. |
| U | Frontend: целевой interaction test и достижимый flow, loading/error/empty/recovery; relevant locale/viewport/keyboard; affected consumers общего компонента; build/types один раз на финальном срезе. Backend guards не заменяются скрытием кнопок. |
| BU | Обе границы B и U, включая согласованность UI/API/domain/effects. |
| T | Tooling/fixtures: минимальный regression самого helper/контракта, негативный контроль ложного PASS, isolation и affected tools; dependency изменения проверяются в чистой детерминированной среде. |
| O | Изолированные реальные broker/worker/restart/retry и Compose-конфигурация; Linux/target acceptance не подменяется локальными stubs. |
| D | Документы: собственный diff, ссылки/anchors, команды/примеры, согласованность; без install/build/DB/browser ради Markdown. |
| N | Native: actual выбранный revision + server contract, сборка и устройство/эмулятор; транспиляция исторических функций не закрывает цикл. |

Исправленный тест должен ловить исходный дефект и проходить после исправления.
Не менять assertions ради зелёного результата. Миграции тестировать только на
изолированной БД; рабочие DB, real messages/payments, deploy и платные providers
не разрешаются таблицей. Сохраняется ранее установленная граница **без push/merge/
deployment**; собственный проверенный локальный commit допустим. Публикация требует
отдельного изменения этой явной границы. Старые FAIL и закрытия сохраняют историю.

## Порядок выполнения

Номера C01–C50 задают порядок по умолчанию, зависимости — обязательные предшественники.
«—» означает отсутствие зависимости от другого исправления, а не отсутствие
проверок. При внешнем блокере можно продолжить только уже разрешённый независимый
scope; таблица не запускает все циклы автоматически. C50 закрывает старый DOC01,
но документация каждого исправления обновляется сразу, не откладывается до C50.

## Исправления текущего CRM

| Цикл / статус | Находки | Результат одного цикла | Проверка закрытия | Зависимости |
| --- | --- | --- | --- | --- |
| **C01 — Безопасный запуск проверок**; закрыт локально: [evidence](../testing/evidence/remediation-c01-20261104.md), base61554598 + C01 delta | UI31, VERIFY02 | Guards до migrate/seed, safe bootstrap, action/503 FAIL и валидные recovery faults реализованы. Dev остановлен. Код/доказательства C01 закрыты; среда: оставлена одна disposable папка после запрета ручной очистки; push/deploy не разрешены. | **T PASS**: Node7, Python23, общий prepare/serve/CSRF/login, system/drift, неизменность рабочей DB; реальный PG/Redis kill/rollback/retry/exactly-once/denial/replay. Новая тестовая среда очищена. Не full/live S04. | — |
| **C02 — Права исходных данных в аналитике**; закрыт локально: [evidence](../testing/evidence/remediation-c02-20261104.md), base704d4663 + C02 delta | TEAM-ANALYTICS | Team performance не раскрывает данные Leads при запрете чтения ресурса или выключенном модуле. | **B PASS**:10 focused/54 completion, allowed/denied/module-off/own/team/foreign/recovery, query-count/system/drift. Код/доказательства/среда/решения C02 без остатка; только local save, без push/live. | C01 |
| **C03 — Секреты в логах и readiness**; закрыт локально: [evidence](../testing/evidence/remediation-c03-20261104.md), base121d5e53 + C03 delta | PAID-BETA-BROKER, EXCEPTION-SECRET-LOGGING | Broker URL и текст исключений проходят маскирование; остаются stack/type/correlation без чувствительных значений. | **B PASS**:11 focused/105 completion, configured console/CLI JSON+text, quote/chain/args/context, persistence/API, system/drift. C03 без остатка; Sentry/иные sinks не сертифицированы; local save без push/live. | C01 |
| **C04 — Безопасный состав архива**; закрыт локально: [evidence](../testing/evidence/remediation-c04-20261104.md), base6a0dab4c + C04 delta | ARCHIVE-SENSITIVE-ARTIFACTS | Архиватор исключает вложенные env, backup DB и browser/session state, сохраняя нужные исходники. | **T PASS**:7 synthetic tests; actual Bash/rsync/Python ZIP, exact manifest/bytes/CRC, private-path/link/failure/repeat guards. C04 без остатка; реальный checkout не архивирован, local save без push/live. | C01 |
| **C05 — Честное завершение сессии**; закрыт локально: [evidence](../testing/evidence/remediation-c05-20261104.md), base112358d7 + C05 delta | UI13 | Ошибка logout не показывается как успешный выход; повтор и reload согласованы с серверной сессией. | **U PASS**: Node31/browser43,11 planned SKIP; RU/KK/EN desktop/mobile,503/network/reload/retry, single-flight/queued refresh/sibling tabs; safe build/types/i18n. C05 продуктово закрыт;2 temporary folders retained after cleanup policy block; local save без push/live. | C01 |
| **C06 — Происхождение старых черновиков Inbox**; закрыт локально: [evidence](../testing/evidence/remediation-c06-20261104.md), base13862c6d + C06 delta | FU-FE-01 | Legacy draft без владельца не присваивается текущему пользователю автоматически. | **U PASS**: BEFORE8:2FAIL/6PASS → Node14PASS, browser4PASS; legacy negative, scoped preservation, account/reload/conversation/late-send/storage recovery. Safe build/types/i18n. C06 без остатка; ранее мигрированные scoped данные сохранены; no push/live. | — |
| **C07 — Чувствительные URL в мониторинге**; закрыт локально: [evidence](../testing/evidence/remediation-c07-20261104.md), basef928d0f1 + C07 delta | FU-FE-02 | Optional monitoring очищает bearer-части URL до формирования отправляемого события. | **U PASS**: Node/actual SDK browser20PASS, actual Plausible2 scenarios; safe build/types/i18n. Final payload sanitization; PostHog flags/replay disabled; sensitive Plausible referrer suppresses tracker. C07 без scoped остатка; no push/live. | — |
| **C08 — Актуальные условия автоматической записи**; не начат | CRM-TERMS01, BOT-ZERO-PRICE | Изменившиеся цена/длительность отклоняются до создания записи; нулевая цена отличается от отсутствующей. | **B**: Подтверждение→смена условий→booking: без Appointment/effects при mismatch; unchanged/branch/replay/availability/rights; zero/null/positive. | C01 |
| **C09 — Контекст и эффекты создания записи**; не начат | REQ03, CRM-EVENT01 | Автоматическая запись сохраняет принятые source/assignee defaults и запускает эффекты создания ровно один раз. | **B**: Manual/automatic/plan/legacy callers; authorizing actor отдельно от assignee; tenant/revoked/default/replay/rollback; один BusinessEvent/automation effect. | C08 |
| **C10 — Очистка idempotency receipts**; не начат | IDEMPOTENCY-PRUNE | Prune не удаляет receipt, обновлённый после выборки просроченных строк. | **B**: Детерминированное interleave select→renew→delete; unchanged expired control; PostgreSQL race. | C01 |
| **C11 — Владение задачей экспорта**; не начат | EXPORT-STALE-FINISH | Старый worker не перезаписывает завершение новой попытки и не публикует устаревший файл. | **B**: Claim/reclaim/new success/old finish, retry и безопасная очистка старого output; PostgreSQL concurrency. | C10 |
| **C12 — Владение исходящей отправкой**; не начат | OUTBOUND-STALE-FINISH | Generic outbound completion учитывает текущую попытку; существующее fencing Ycloud сохраняется. | **B**: Старое/актуальное completion, reclaim/retry/unknown outcome; без реальной доставки. | C10 |
| **C13 — Откат при отказе аудита**; не начат | ATTACHMENT-AUDIT-ROLLBACK, CONNECTOR-AUDIT | Неуспешный audit не оставляет частично изменённые attachment/config/credential данные. | **B**: Fault injection перед commit, прежние значения/связи сохранены, happy path пишет audit один раз; отдельный tenant control каждого сервиса. | C01 |
| **C14 — Атомарность применения шаблонов**; не начат | TEMPLATE-ATOMICITY | Сбой создания второго поля/этапа откатывает весь новый form/pipeline. | **B**: Parent и все children отсутствуют после сбоя; полный успешный шаблон и повтор без частичных объектов. | C01 |
| **C15 — Повтор намерения в Inbox**; не начат | ATTACHMENT-RETRY, UI16 | Retry частичной загрузки не повторяет принятый файл; переключение бесед сохраняет idempotency identity незавершённой отправки. | **BU**: Первый файл принят/второй failed→retry; A unknown outcome→B send→A retry; по одному принятому намерению и полезный recovery UI. | C12, C13 |
| **C16 — Создание и вычисление сегмента**; не начат | SEGMENT-EMPTY, SEGMENT-SCOPE-SHAPE, UI15 | Валидная форма фильтра, правильный empty/not-empty и восстанавливаемое создание сегмента без активного пустого остатка. | **BU**: List/object/invalid filter shape, tag empty partitions; segment201/filter503/retry/duplicate; tenant/role guards. | C01 |
| **C17 — Справедливая и актуальная маршрутизация**; не начат | ROUTING-STARVATION, ROUTING-STALE-LIFECYCLE | Scanner достигает следующих Business и под lock повторно проверяет lifecycle/ручное назначение. | **B**: Малый limit, нераспределяемый первый элемент; completion/manual reassignment между selection и lock; unchanged control. | C10 |
| **C18 — Продвижение автоматизаций задач**; не начат | AUTOMATION-OVERDUE-STARVATION, PIPELINE-ARCHIVED-TASK | Уже обработанная overdue-задача не блокирует следующие; архивная задача не подменяет нужную действующую. | **B**: Повторные bounded scans, существующий run, archived/open task и создание единственной корректной замены. | C10 |
| **C19 — Consumers и состояние очередей**; не начат | OPS-Q01, HEALTH-QUEUE-WARNING | Поставляемая конфигурация обслуживает все обязательные очереди; health показывает фактическую проблему очереди. | **O**: Compose merge; isolated broker active_queues, due work/restart/retry и warning/recovery. Linux image/целевой deployment отдельно. | C11, C12, C17, C18 |
| **C20 — Полный проход рассылки**; не начат | OUTREACH-BATCH, OUTREACH-REPREPARE | Большая кампания продолжает batches; reprepare удаляет исключённых получателей без повторной отправки. | **B**: Batch+1/несколько batches; убрать клиента→reprepare; restart/retry/consent/tenant controls; provider stub. | C12, C19 |
| **C21 — Доступность уведомления о записи**; не начат | NOTIFICATION-APPOINTMENT-URL | Ссылка producer совместима с personal feed и открывает разрешённую запись. | **BU**: Producer→recipient→feed→calendar; правильный Business/права/невидимый объект; без внешней доставки. | C09 |
| **C22 — Переходы заявки и сделки**; не начат | LEAD-REOPEN-APPOINTMENT, DEAL-REQUIRED-PAYLOAD | Reopen учитывает связанную запись; обязательные значения стадии валидируются и действительно сохраняются. | **B**: Lose/reopen lifecycle, missing/valid/invalid payload, audit/activity, tenant/role и rollback; существующие terminal rules не менять. | C01 |
| **C23 — Даты, дни недели и версия задачи**; не начат | INVALID-CALENDAR, WORKING-HOURS-WEEKDAY, TASK-INVALID-VERSION | Невозможные даты/weekday/version дают предусмотренный 4xx без изменений. | **B**: Неверный формат/тип/календарная дата, високосный день; stale409/current success; no-write assertions и API controls. | — |
| **C24 — Некорректный идентификатор приглашения**; не начат | INVITE-MALFORMED | Malformed token не приводит к ORM500 и не раскрывает лишних сведений. | **B**: Non-UUID, valid active/expired/revoked controls через публичную API-границу; статус согласовать с текущим контрактом, не угадывать. | — |
| **C25 — Валидность импортируемых значений**; не начат | UTF8-PREFIX, IMPORT-NONFINITE, IMPORT-DURATION | UTF-8 boundary не отвергает валидный файл; NaN/Infinity/нулевое количество/дробная длительность не проходят скрытые преобразования. | **B**: Символ на границе512 bytes, malformed encoding, finite/nonfinite/zero/fraction; строки и BusinessEvent не появляются при ошибке. | — |
| **C26 — Лимит и число строк экспорта**; не начат | EXPORT-LIMIT-AND-ROWS | Лимит проверяется при исполнении, row_count учитывает CSV-записи, а не физические переносы строк. | **B**: Рост после enqueue, exact cap/cap+1, quoted newline, failure cleanup и обычный export. | C11 |
| **C27 — Курсор сообщений**; не начат | MESSAGE-CURSOR | Последовательное чтение страниц не теряет boundary message. | **B**: Одинаковые timestamps/порядок/limit0/limit+1, concurrent append, полный список как control; scope/tenant не расширяются. | — |
| **C28 — Продолжение публичного списка клиентов**; не начат | PUBLIC-CLIENTS-CAP | Все разрешённые клиенты перечисляются с документированным continuation; старый first-page контракт учтён. | **B**: 105+ клиентов, несколько страниц без пропусков/дубликатов, invalid cursor и permissions; проверить потребителей API. | — |
| **C29 — Полные списки в UI**; не начат | UI18 | Client drawer, Inbox и pricing history дают доступ к следующей странице. | **U**: 26/25,59/50,51/50; next/end/error/retry, сортировка, фильтры и счётчики; полный client page не переписывать. | C27 |
| **C30 — SQL-бюджеты очередей и карточки**; не начат | PERF01, PERF03 | Устраняются доказанные N+1 с сохранением payload и текущих прав. | **B**: Исходные fixtures, бюджеты58/40SQL, larger fixture, tenant/own/team/field visibility; без ослабления assertions. | C02 |
| **C31 — Задержки Clients**; не начат | PERF02 | Тяжёлые aggregate/summary queries перестают делать список практически недоступным на исходном объёме. | **B**: Те же small/heavy/distributed fixtures, SQL plans, SQLite/PG, HTTP burst/soak/recovery; записать before/after без выдуманного production SLO. | C02, C30 |
| **C32 — Независимый аварийный экран**; не начат | UI01 | Падение дочернего UI не вызывает второго падения fallback из-за provider hooks. | **U**: Forced crash внутри/вне providers; видимые reload/home реально работают; representative shared regression. | — |
| **C33 — Восстановление чтения и загрузки**; не начат | UI22 | Client card, locale chunk и invalid platform page имеют рабочее восстановление. | **U**: Initial/background503, chunk retry, page999→валидная страница; повтор приводит к данным без обходной навигации. | C32 |
| **C34 — Поиск и правдивое пустое состояние**; не начат | UI02, UI03 | Поиск ищет по разрешённому серверному набору; ошибка Clients не выдаётся за отсутствие клиентов. | **BU**: Match за первой страницей/>50, no match,503/stale data/retry/account switch; scoped queries и ключи кэша. | — |
| **C35 — Устаревшие ответы форм**; не начат | UI17, UI20 | Client/Lead duplicate lookup и Resource/Pricing save не заменяют более новое состояние пользователя. | **U**: A→B→late A, очистка контакта, submit A→edit B→success/failure A; последние данные/предупреждения корректны. | — |
| **C36 — Сохранение черновиков**; не начат | UI19, UI11 | Dirty baseline корректен; tabs/Back/Escape/reconnect не теряют несохранённый ввод без явного discard. | **U**: Все перечисленные в находке Notes/custom fields/resource/service/hours и AI editor: clean/edit/keep/discard/save/reopen/refetch; сохранить принятые AI policy. | — |
| **C37 — Состояние форм расписания и услуги**; не начат | UI21, UI24 | Ответ сохранения относится к отправленной дате; невалидная duration видна, валидное default schedule можно сохранить. | **BU**: Dec1 pending→Dec2, double save/error/retry; blank/fraction duration; новый ресурс без branch и изменение schedule. | C23 |
| **C38 — Ноль, отсутствие и ошибка pricing**; не начат | UI23 | UI различает zero/null/unknown; failed control read не показывает Active/Stop как достоверное состояние. | **U**: 0/null/nonzero,503/loading/recovery, pending controls; не менять денежную политику. | — |
| **C39 — Клавиатура и видимость меню**; не начат | UI04, UI25, UI26 | Select/search и command palette имеют согласованную семантику/focus; активный пункт и меню видны. | **U**: Arrows/Home/End/Enter/Escape/Tab/ShiftTab, focus return, accessible names; default/portal и320×480; representative consumers. | — |
| **C40 — Семантика страниц и reduced motion**; не начат | UI05, UI12 | Main/selection/route titles согласованы; reduced-motion действительно исключает движение. | **U**: Списки/детали, skip navigation и keyboard; matchMedia/computed style/route transitions. | — |
| **C41 — Состояния формы восстановления доступа**; не начат | UI06 | Invalid/expired/revoked token и network failure различаются; устаревшая форма не предлагает невозможное действие. | **U**: Valid+четыре negative/retry сценария, RU/KK/EN; без раскрытия токена. | — |
| **C42 — Переводы и названия сущностей**; не начат | UI07, UI08, UI30 | Локаль дат, route metadata, empty states и product-owned enum labels соответствуют контексту RU/KK/EN. | **U**: Все потребители из находок, заполненные/пустые состояния; пользовательские данные и functional settings сохранены. | — |
| **C43 — Бизнес-день в timeline**; не начат | UI28 | Группировка и отображение события используют согласованную business timezone. | **U**: UTC/не-UTC браузер, переход полуночи и DST; текущий timezone contract без нового правила. | — |
| **C44 — Доступные действия клиентской карточки**; не начат | UI27, UI33 | Capabilities управляют Edit/Add tag/Archive; связанная задача открывается мышью и клавиатурой. | **BU**: Owner/manage/view-only и изменение capabilities; backend403 остаётся; переход к задаче и назад к клиенту. | C02 |
| **C45 — Счётчики очередей Inbox**; не начат | UI29 | Open/Closed/All/paused/unassigned показывают согласованные разрешённые множества. | **BU**: Смешанные очереди за page limit, каждый фильтр/empty и permission scope; не считать загруженную страницу общей численностью. | C29 |
| **C46 — Восстановление website widget**; не начат | UI32 | Failed send можно повторить; storage denial не блокирует отправку; история помещается в малом viewport и локализована. | **U**: First/append success,503/unknown outcome, storage denied,320×480, RU/EN; без требования нового двустороннего чата. | — |
| **C47 — Актуальные frontend assertions**; не начат | UI09, UI10 | Исходные Node/browser failures устранены по действующему контракту, без удаления проверяемого поведения. | **T**: Каждый из7Node failures и named Calendar/Records failures; fallback/date/keyboard/rights остаются проверены. | C32, C39 |
| **C48 — Актуальные backend fixtures**; не начат | VERIFY01 | AI action count, selected Business для bell и readiness key fixtures проверяют реальное принятое поведение. | **B**: Повтор исходных4FAIL: PERF01 закрывает C30; остальные assertions исправляются только после сверки контракта, не по удобному фактическому ответу. | C30 |
| **C49 — Dev dependency advisories**; не начат | SEC-DEP-01 | Обновлён совместимый dev lock с проверенной цепочкой инструментов. | **T**: Сначала новый advisory snapshot; affected tooling/build, audit и deterministic clean CI. Старые14 advisories не объявлять текущим числом без перепроверки. | — |
| **C50 — Интеграция исправлений документации**; не начат | DOC01 | Устаревшие активные утверждения исправлены; собственные старые patches интегрированы без чужого WIP и потери открытых acceptance. | **D**: Roadmap↔контракт↔паспорт↔evidence, ссылки и рабочий/index/commit diff; исторические отчёты не переписывать. | — |

## Денежный контур — составная находка REQ01

| Цикл / статус | Находки | Результат одного цикла | Проверка закрытия | Зависимости |
| --- | --- | --- | --- | --- |
| **M01 — Денежная модель и версии условий**; не начат | REQ01 | Принятые ledger/version/rounding invariants реализованы в существующем доменном слое. | **B**: Сначала только реально открытые zero-base/terminal-correction решения; isolated migrations, invalid input, tenant/role и rollback. | C09, C10 |
| **M02 — Распределение, обратные операции и остаток**; не начат | REQ01 | Allocation/reversal/refund сохраняют баланс и идемпотентность. | **B**: PostgreSQL double-spend/overrefund/concurrent allocation/replay/rollback; денежные вычисления и округления по контракту. | M01 |
| **M03 — Рабочий денежный сценарий в плане**; не начат | REQ01 | API и reachable UI позволяют выполнять принятые денежные операции с историей. | **BU**: Plan→advance/allocation/reversal/remainder, loading/error/recovery/permissions; сверка UI/API/ledger, RU/KK/EN. | M02 |
| **M04 — Денежная сводка и сквозная приёмка**; не начат | REQ01 | История/метрики согласованы с ledger; весь денежный остаток REQ01 проверен. | **BU**: AC09/14 и все source acceptance REQ01, зависимые money suites, invalid transitions, reversal и конкурентные операции. | M03 |

## Голосовой D01 — составная находка REQ02

| Цикл / статус | Находки | Результат одного цикла | Проверка закрытия | Зависимости |
| --- | --- | --- | --- | --- |
| **V01 — Приём аудио и транскрипция D01**; не начат | REQ02 | Audio поступает через выбранный adapter с утверждёнными retention/privacy правилами и доступным fallback. | **BU**: Сначала выбор provider/retention из уже открытых вопросов; formats/limits/noise/timeout/cancel/no-data, synthetic provider. | C01 |
| **V02 — Голосовой запрос в существующие AI tools**; не начат | REQ02 | Транскрипция проходит через текущие grounding/rights/approval, сохраняя текстовый сценарий. | **BU**: RU/KK/mixed, ambiguity, permission denial/current rights, no critical action before confirmation; сбой модели не ломает CRM. | V01 |
| **V03 — Пользовательский цикл и приёмка D01**; не начат | REQ02 | Запись/отмена/повтор/подтверждение доступны пользователю; качество подтверждено на выбранном provider. | **BU**: Offline/retry/recording errors/cancel, реальные разрешённые RU/KK/mixed/noise fixtures; без provider proof остаётся частичная приёмка. | V02; разрешённая provider-среда |

## Будущий Market — отдельная roadmap-граница

| Цикл / статус | Находки | Результат одного цикла | Проверка закрытия | Зависимости |
| --- | --- | --- | --- | --- |
| **X01 — Контракт CRM↔Market**; не начат | REQ04 | Для принятого после пилота объёма определены направления, IDs, версии, источник и consent. | **D**: Сверить оба контракта; запрет второго receipt и поведение revoke/refund; без изменений Market и внешних операций. | Отдельный scope после пилота |
| **X02 — Один согласованный поток CRM↔Market**; не начат | REQ04 | Один выбранный transport/binding реализован и проверен с обеих сторон. | **BU**: Paired duplicate/out-of-order/revoke/refund tests; live effects только при отдельном target-разрешении. Для нескольких потоков каждый получает собственный цикл; REQ04 не закрывается первым потоком автоматически. | X01; разрешение на выбранный межпроектный поток |

## Исторический native — не дефекты текущего web

| Цикл / статус | Находки | Результат одного цикла | Проверка закрытия | Зависимости |
| --- | --- | --- | --- | --- |
| **H01 — Native session и авторство очереди**; не начат | MOB-H01, MOB-H04 | В выбранной поддерживаемой версии очередь привязана к аккаунту, transient refresh не уничтожает сессию, refresh согласован. | **N**: A enqueue→logout→B,503/network/401, concurrent refresh; настоящий device/emulator и server contract. | Решение о поддержке и revision native |
| **H02 — Native deep links**; не начат | MOB-H02 | Разрешённые app/HTTPS links открывают нужный объект после проверки scheme/host/path. | **N**: Valid/invalid links, cold/warm start, auth redirect и права объекта на устройстве. | Выбранный native revision |
| **H03 — Сохранность native offline queue**; не начат | MOB-H03 | Capacity и replay/enqueue не теряют принятое намерение молча. | **N**: Queue limit, concurrent enqueue/replay, process death, offline/restart; явный результат пользователю. | H01 |
| **H04 — Native command replay**; не начат | MOB-H05 | Истёкший receipt и изменившееся состояние не ломают корректный повтор принятой команды. | **N**: First/replay/expired/changed payload/stale transition, rollback/concurrency и PostgreSQL; совместимость выбранных client/server revisions. | H01; выбранный server revision |

## Отдельная приёмка среды — не исправления кода

Эти6 границ не входят в87 находок и не закрываются завершением циклов C/M/V/X/H.
Назначать их после связанных исправлений и предоставления конкретной среды.

| Граница | Что потребуется и что доказывать |
| --- | --- |
| ENV-SECURITY | Доступный разрешённый security workflow; точный safe scope оставшихся protected scenarios. Повторять ранее отклонённую операцию в обход ограничения нельзя; static/reused evidence не выдавать за active PASS. |
| ENV-LINUX | Изолированный Linux/container runtime: реальный image, UID, signals, startup/replicas, shutdown, migration/recovery. |
| ENV-TARGET | Явно разрешённый target/candidate, DNS/TLS/proxy/storage ACL, alerts/on-call, release/rollback, RPO/RTO. |
| ENV-PROVIDERS | Разрешённые sandbox credentials/получатели/эффекты для messages/webhooks/email/платежей; unknown outcome и reconciliation. |
| ENV-LLM | Выбранные model/version/provider, разрешённые расходы/privacy, оценочные fixtures RU/KK/mixed/grounding/injection. |
| ENV-NATIVE | Принятый поддерживаемый revision, device/emulator, OS permissions/background/push и совместимый API. |

99 protected/external UI command instances и3 protected migration-failure случая
остаются перечисленными в [границах аудита](../../output/full-audit-20261104/report/coverage-gaps.md).
Отсутствие их новой проверки не снимает security acceptance с будущего исправления:
если необходимый сценарий недоступен, соответствующий цикл остаётся частично принят.

## Первый цикл: C01

Начать с UI31/VERIFY02: это обеспечивает безопасные и осмысленные проверки всех
последующих изменений. Scope — только диагностические helpers/их regression tests
и соответствующие инструкции. Не исправлять одновременно права, UI продукта,
зависимости, рабочие конфигурации или данные. До правок найти точные source paths
и старые receipts по двум IDs и зафиксировать выбранные commands/environment.
Готовность C01: helpers не могут неявно мигрировать/наполнять обычную DB; негативные
контроли не проходят gate; recovery воспроизводит требуемый отказ и восстановление.
После C01 следующий цикл — C02, с самостоятельной проверкой разрешений и tenant.

Текущий результат этого документа — только разбивка и порядок. Ни одна находка
не считается исправленной созданием списка; общая готовность релиза не заявляется.
