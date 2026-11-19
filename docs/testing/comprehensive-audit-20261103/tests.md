# Матрица выполненных проверок и ограничений

Версия: `0b3348e1` + исходный WIP, канонический checkout,03–04.11.2026.
Источник требований — [полная матрица](requirements.md); эта таблица добавляет
runtime-доказательства, а не заменяет accepted AC и не присваивает чужие изменения.
Синтетические данные, отдельные БД/порты/файлы, запрет внешних provider sockets,
отключённое чтение рабочего .env. Рабочая БД и dev-процессы не были тестовой целью.

## Исполняемые результаты

| Проверка | Результат | Что именно доказано / предел |
| --- | --- | --- |
| Django system check / migration drift | PASS / PASS | Текущий source и isolated settings; рабочие миграции не применялись |
| Полный SQLite backend |2752:2698PASS,4FAIL,50SKIP;1809.4s wall | [Команда](assets/full-backend.json), [24apps и failures/skips](assets/full-suite-coverage.json). Failed run не превращён в PASS после объяснения ошибок |
| Focused backend failures |3 исходных FAIL повторились; semantic AI control PASS | AI2<3, workqueues488>58, bell без selected Business400. Отдельно2named suggestions/0executed tasks. [Receipt](assets/focused-failures-results.json) |
| W018 environment control |valid audit key:FAIL; local-audit key:PASS | Изменялся только synthetic key identifier; guard не сломан, старый тест зависит от fixture. [Comparison](assets/production-fixture-comparison.json) |
| PostgreSQL concurrency |Повтор50PASS,exit0,150.33s wall; initial teardown FAIL сохранён | Все SQLite row-lock skips учтены, включая классы вне filenames concurrency. Изменена только audit cleanup: child exit→проверенная disposable DB cleanup→normal shutdown. [Final](assets/postgres-concurrency.json), [initial failed command](assets/postgres-concurrency-initial.json) |
| Automatic booking responsible/provenance |9controlsPASS;2subtestsFAIL в новом10-м тесте | REQ03: actual booking сохраняет null/null; не общая поломка всей AI-подсистемы |
| Automatic booking stale terms |4tests:2controlsPASS/2FAIL | CRM-TERMS01: цена100→200 либо30→60мин после delivered offer; actual DB write. Branch/unchanged controls работают |
| Automatic booking creation effect |2tests:manualPASS/automaticFAIL | CRM-EVENT01: actual validated rule/real engine; manual1Run/1Task, automatic0/0 при booked Appointment |
| Worker/broker/files/restore |Адаптированный audit drill PASS,242.16s | Реальные PostgreSQL/Redis/Celery/beat/ClamAV; restart, WAIT, replay, injected fault/retry/cancel, broker loss, dump/restore, private files/keys. [Final receipt](assets/recovery-full.json); штатный S04 helper отдельно [FAIL](assets/recovery-initial.json) на устаревшей fixture |
| Real antivirus import API/UI |PASS scoped | clean preview/confirm, повтор не создаёт дубль; custom signature400; scanner outage503→retry; UI retain file→preview201→import1→CSV200 |
| D01 employee confirmation/current rights |PASS scoped | Реальные suggest/approval/execute:Cancel0effect/0execute,Confirm1task; planning503 сохраняет запрос; stale execute400 не затирает правку сотрудника; manager work разрешён, config скрыта/PUT404. Ответ planner контролировался; это не real-model proof |
| Frontend types/build/i18n/bundle |PASS scoped | App/node TS noEmit; app/widget production builds;6680RU/KK/EN keys; shell342.1KiB/106.1KiB gzip. RU/KK chunk warning остаётся предупреждением |
| Все Node tests |222:215PASS/7FAIL |49files; focused повтор7FAIL. Старые regex/inventory assertions, не скрыты и не переписаны ради PASS |
| Маршруты/роли/локали |45 route cases выполнены | OwnerRU1440, EN390, managerKK390, operatorEN320, platformRU1440;0pageerrors/0horizontal overflow в этих состояниях. Не полный cross-product всех ролей/контролов |
| UI функциональные пути |PASS subsets + retained failed suites | Records recovery/period, session isolation, calendar actions, task lifecycle, clients retry/edit/archive/undo/linked task, Inbox safety/draft/retry, automation preview/WAIT/history/cancel, import/export. Точные scopes и старые failures — [UI report](ui-mobile.md) |
| Keyboard/semantics |Подтверждены UI04/05 | Actual picker arrows/Escape/axe, shared landmarks; не screen-reader сертификация |
| Zoom/reduced motion |200%reflow PASS на4страницах; motion preference FAIL | Реальный Chromium tabs zoom, не только narrow viewport; reduced motion сохраняет fade-in0.2s.400%/physical-device/browser matrix не проверялись |
| Source/build/log secret patterns |0candidates в заданной границе |2333 source text files; selected isolated bundles/own logs; не history/entropy/рабочие env/logs/remote stores |
| Dependency audits |npm0; pip14advisories/3dev packages | Условия эксплуатации анализируются отдельно; runtime exploit не установлен |
| Stand access gate |11PASS | Local Node gate tests; не live HTTPS/domain/container acceptance |
| Codex Security Deep Scan |Не стартовал | Managed filesystem permission profile недоступен; нет scan ID/clean result, ручные проверки отдельно |
| Historical native logic |3дефекта подтверждены; actor replay независимо | Только immutable73482a3 code in memory; не current web, не server mutation/device/build/push/store proof |
| Производительность/HTTP нагрузка |Метрики получены; HTTP FAIL |25/1000fixtures, heavy/distributed SQLite; realPG HTTP:each50attempts40HTTP200+10ClientsTimeout при1/5client threads. PG warmupClients28.618s. P95 censored10s, timed-out work может продолжаться; не cloud capacity. [Подробности](backend.md), [HTTP receipt](assets/http-load-summary.json) |

## Связь runtime-покрытия с требованиями

| Требования | Свежая граница проверки | Результат и остаток |
| --- | --- | --- |
| C01/AC04/PK0 | accounts/businesses/core/clients/notifications/support tests; UI session6unique cases и role denial; PG row-lock cases | Широкая локальная проверка permission/tenant/current-session; selected-Business bell test drift сохранён. Реальные домены/MFA devices/proxy/production key custody не приняты |
| C02–03/AC01/03/10/11 | client merge/archive/history/legacy tests; current client create/edit/tag/archive/undo/linkedtask; router inventory | Scoped сценарии проверены; исторические сущности не конвертировались. UI no-data/search находки и весь набор старых внешних ссылок не закрыты автоматически |
| C04/AUD08–09 | server search/query tests +58task browser repro | UI02 выявляет неполный global task search; client full-server search не объявляется сломанным по аналогии |
| C05–06/AC02/05/14 | branch/schedule/records/plan suites, PostgreSQL races; calendar actual API changes | Slot/lifecycle/branch/nonmonetary plan проверены в named tests; REQ01 money и CRM-TERMS01 stale auto offer открыты |
| C07–08/AC07 | tasks/automations suites; real worker/retry/WAIT/cancel; current UI history/cancel; creation-effects probe | Scoped durable work проверен в адаптированном drill; shipped helper/tooling и missing Compose queues требуют исправления; CRM-EVENT01 подтверждает пропуск настроенного правила при automatic creation |
| C09–11/AC06/D01 | bot/conversation/AI suites, actual booking diagnostics, Inbox manual/AI safety/retry/UI | REQ02 voice отсутствует, REQ03/default/provenance и CRM-TERMS01 подтверждены; real-model/real-channel receipts не получены |
| C12–13/18 | imports/exports/privatefile/ZIP/AV tests; real scanner API+UI; owner/operator/OWN role probes | Representative full chain PASS; конкретное cloud storage/retention/private download и все возможные spreadsheet schemas не сертифицированы |
| C14 | current web session/offline logic tests; historical native separately | Scoped web isolation сохраняется; не полная offline CRM и не money replay; MOB-H01/02/03 не приписываются web |
| C15/AC09/14 | existing receipt/refund tests + financial source selectors | Существующий журнал проверен; plan allocation/immutable money terms отсутствуют. Общая денежная приёмка остаётся открыта |
| C16 | personal API/recipient/read/migration tests, PG recipient race, session UI | Local code/WIP проверен, не deployment/рабочая миграция. Очередь notifications в Compose без consumer — OPS-Q01 |
| C17/20 | accounts/support/billing backend suites и selected platform routes | ADMIN foundation/guards scoped; legal/commercial/provider/ответственность — отдельные owner/external inputs |
| C19/CG04 | guards, real local recovery/restore и bounded perf | Windows/native local proof; Linux image/target/domains/24h operations/RPO-RTO на целевых данных ещё не приняты |
| C21/REQ04 | read-only CRM–Market schema/authority mapping; source hash check | Нет concrete binding/version transport; future after pilot, без дублирования Market-аудита и без правок соседнего проекта |
| C22/CG08 | current tree/build artifact search, historical actual-source probes | Native package/current compatible API отсутствуют в проверенной границе; SDK/device/store нужны для следующей проверки |
| AC12/13/CG01–08 | Сопоставлены все14AC,22C,8CG; UI/runtime receipts выше | Нет автоматического полного пилотного/production PASS. Два реальных Business/персонал/каналы/целевая среда и перечисленные code gaps остаются открыты |

## Чтение результатов

Повтор после исправления тестовой среды не стирает прежний FAIL. Stale selector
не доказывает product bug, но оставляет тест нерабочим; прямой актуальный сценарий
закрывает только свою проверку. PASS воспроизведения дефекта означает, что дефект
подтверждён, а не исправлен. Скриншот не доказывает деньги/транзакции/tenant isolation.

Ни полный release candidate, ни live provider, ни production deployment этим
аудитом не объявлены. Все исходники, зависимости и рабочие настройки сохранялись.
После окончательной сверки хешей повторять неизменившиеся успешные проверки не
требуется; новые изменения потребуют именно затронутых rechecks.

## Пилотный CRM: адресная сверка 19.11.2026

Отдельное поручение владельца через чат «Менеджер»: сопоставить AC-CRM-PILOT-01–14
с текущим кодом/доказательствами и выполнить недостающие focused проверки.
Это дополнение не заменяет исторические результаты03–04.11 и не является новым
полным аудитом. Режим verification, исходный gap evidence/candidate integration.
Canonical root C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit,
начальный HEAD b9415d71e89167fcbf74c55187009481da066389; индекс пуст.
Чужой WIP accounts/businesses/integrations/auth/access/Overlay/STATUS/PRIMARY
сохранён; его наличие не даёт права редактировать или включать его в релиз.
Не менять продукт, рабочую БД/сервер, STATUS/PRIMARY; без commit/push.

Prior closure: MANAGEMENT-BOOKING dd096795 и деньги2012fd2/c42c471/bb051db
локально проверены -> после них менялись AI tools и Records toolbar, а полный
кандидат ещё не выделен -> проверяем текущую связку на disposable БД, не переписываем.
Риск: деньги/права/lifecycle/replay; повторно используем доменные тесты и
scripts.codex_verify.isolated_runtime. Skill zani-run-verification; внешние sockets
и dotenv отключены. Scoped completion: матрица всех14 критериев, свежие focused
результаты, конкретный остаток; общий pilot PASS только при полной приёмке.
Артефакты текущего запуска: output/management-booking-20261112/pilot-20261119/.

### Матрица перед исполнением

Все статусы ниже частичные, не полное закрытие AC. Точные требования остаются в
[roadmap](../../current/roadmap.md#новые-критерии-единой-записи-ac-crm-pilot).
Источники: [Records](../evidence/records-publication-20261103.md),
[Management](../evidence/management-implementation-20261111.md#management-booking-integration--12112026),
[деньги/коррекции/прекращение](../evidence/visit-plan-payments-20261118.md).

| AC | Существующий код и evidence | Конкретный остаток / focused проверка |
| --- | --- | --- |
| 01 | record_commands.create_record, InboxContext; Records/Management | Перепроверить manual/Inbox без обязательного Lead и закрытый Lead; current browser отдельно |
| 02 | Один Appointment, record_workspace, appointmentCache; Records13 browser cases | Текущие commands/workspace/cache; UI list/calendar/card после изменений Records не считать исторически принятым |
| 03 | legacy_record_links использует реальные lead/client links; Records | Current legacy link tests и старые business flows; полный список прежних UI входов отдельно |
| 04 | plan_access, record_commands, branch/resource policies; Management и money denial | Current role/tenant/revoked/object tests; незакоммиченные изменения auth/access требуют отдельного принятия кандидата |
| 05 | record completion, plan allocation, frozen prices; деньги18.11 | Current early-completion/replay/rollback; last-slot/денежные гонки требуют PG, не SQLite |
| 06 | Inbox provenance, responsible validation, Management manual/AI | Current commands/context/AI tools; live-model accuracy не доказывается mock planner |
| 07 | FollowUpPolicy/claim ownership; старый isolated recovery drill | Current follow-up/claim tests; реальный worker WAIT/restart/provider recovery на кандидате не закрыт eager tests |
| 08 | record metrics и financial sources, отдельные receipt/allocation/refund | Current analytics tests; complete-period UI navigation остаётся отдельной проверкой |
| 09 | plan_services/pricing/balances/corrections/termination;18.11 API/UI/PG | Current money regressions и PG; working migration/deployed flow не выполнены этим поручением |
| 10 | legacy links, plan merge/archive, import/export; Records и money dependent suites | Current merge/import/export/migration checks; production-history/fingerprint сохранение требует target evidence |
| 11 | legacy resolver, shared Appointment route/cache; Records | Current resolver/cache, UI deeplinks; native revision/device acceptance отсутствует в этой границе |
| 12 | Синтетические CRM business flows, Management и18.11 money browser | Нет одного принятого кандидата и полного дня двух независимых бизнесов/ролей с персоналом и outage/support |
| 13 | Records RU/KK/EN320–1440, Management и money responsive/keyboard | Исторические scoped captures; изменённые toolbar/auth/shared Overlay требуют текущей UI-проверки, удобство с персоналом отдельно |
| 14 | plan_services, plan_rebooking, immutable terms, undated steps;18.11 | Current gradual-booking/version/termination/payments; полный cross-consumer candidate flow отдельно |

План проверок: isolated Django check/drift и явные labels records/workspace/
completion/plans/Management/money/Inbox/metrics/followups/AI/business flows;
затем недостающие history/import/export и PostgreSQL races по результату.
Frontend focused cache/filter/legacy tests и существующий Management browser flow
при доступности изолированного harness. Build/full candidate gate и target приёмка
относятся к сводимому кандидату; этот тематический срез не подменяет их.

Уточнение владельца19.11: стартовый канал только WhatsApp; Telegram не gate выдачи.
Имена/назначения сотрудников не блокируют подготовку, но роли и tenant guards
проверяются на двух синтетических Business. Персонал/live Telegram не требуется
для этой подготовки; это не отменяет сквозную проверку двух Business и recovery.
Общий frontend build/types/i18n/bundle выполняет координатор после стабилизации
кандидата; здесь npm ci и shared build/dist не запускаются. Browser использует
isolated_runtime, отдельные порты и OUTPUT с уникальным timestamp.

### Уточнённая минимальная дельта AC10

Координатор передал явное поручение владельца исправить execution-time лимит и
CSV row_count после воспроизведения. На проверке apps/core/export_jobs.py и
apps/core/tests_export_attempts.py чистые, конфликта с чужим WIP нет.
Исторический C26 подтверждён чтением текущего кода: лимит только при enqueue,
row_count по числу LF. Минимальная дельта: повторная проверка entity queryset и
фактического CSV перед публикацией; счёт логических CSV records. C11 claim_token,
owned update, fingerprint/permissions и orphan cleanup сохранить.
Риск объём/корректность экспорта; focused cap/cap+1/quoted newline/empty/failure,
dependent export access/attempt ownership/import history. Без новых прав,
notification/BusinessEvent/AI/env/migrations. Общие контракты/STATUS не менять;
координатор сводит кандидат и документацию. Один устаревший browser selector
Management заменяется tab→button согласно текущему editor, assertions сохранены.

### Результат тематического среза19.11

AC10 execution-limit/CSV-count исправлен локально. Повторный cap применяется к
текущей permission-scoped выборке до генерации и к фактическому CSV до сохранения.
Счётчик учитывает quoted multiline/двойные кавычки/CRLF, не ограничивает размер
поля и не меняет глобальный csv parser. Проверены cap+1 до/во время генерации,
ровно cap, пустой экспорт, реальное большое notes. C11/права/fingerprint/cleanup
сохранены. Read-only независимое ревью финального diff: замечаний нет.

| Запуск / точный артефакт | Результат и граница |
| --- | --- |
| `pilot_check_20261119.py` с labels в `pilot-20261119/1795069333711484600-receipt.json` | Django check/drift PASS,214 тестов PASS: records/workspace/completion/plans/Management/money/Inbox/metrics/followups/AI/business flows. Во время прогона чужой voice patch/tests менялись; эти voice изменения не сертифицированы здесь |
| `1795069790838366400-test.log` / receipt |73-test batch завершён FAIL:2 export reproducer FAIL и3 error reports одной двух-Business fixture из-за пустых одинаковых email. Остальные named import lifecycle/merge/legacy migration/automation retry-cancel checks PASS; общий batch не переименован в PASS |
| `pilot_check_20261119.py pilot_two_businesses_20261119 pilot_export_20261119 apps.core.tests_export_access apps.core.tests_export_attempts.ExportAttemptTests apps.core.tests_import_export apps.analytics.tests_record_metrics` | Финальный `1795070392365211100-test.log`:64 PASS, check/drift PASS; `changed_during_run=[]`. Включает corrected fixture, оба original reproducer,5 permanent export regressions, access/fingerprint/cleanup и report consumers |
| `pilot_pg_20261119.py`, `1795070273897007400-pg.log/json` |21 PASS, no skips: last-slot/same-key/status races, plan/resource locks, money completion/refund/legacy/termination,2 C11 stale-worker races. Disposable PostgreSQL17 loopback; test child вышел, test DB удалена, свой server остановлен, exit0 |
| `pilot_csv_counter_20261119.py` |1000 deterministic comparisons с csv.reader PASS: generated valid CSV, quoted quotes/newlines и отсутствие конечного terminator. Не введён parser field-size cap |
| `node --test scripts/tests/record-filters.test.mjs scripts/tests/record-legacy-export.test.mjs scripts/tests/appointment-cache.test.mjs` из frontend |12 PASS, filters/context/export/cache. Это не полный frontend gate |
| `output/management-booking-20261112/browser.py` | Финальный `browser-result-1795070499454389500.json`: prepare/fixture/browser exit0,1 complete scenario PASS. Chromium owner RU1280: Management→manual create/transfer→AI create/transfer+review/approval, ровно2 persisted visits с rooms. Новое время10:00 реально отрисовано в карточке; screenshots manual-transfer.png и ai-confirmation.png захвачены и просмотрены |

Пересекающиеся batches не складываются в число уникальных тестов. PG21 стартовал
после добавления cap и первоначального CSV parsing; последующая замена чистого
счётчика для больших полей не меняла C11 locking/fencing. Её финальный код покрыт
64-test suite и1000 comparisons, новые concurrency claims для parser не делаются.
Первый PG19 дал assertion PASS, но teardown FAIL из-за2 оставшихся sessions;
его log `1795069609437301800-pg.log` сохранён. Повтор использовал --keepdb только
внутри нового disposable server; после выхода child выполнил exact-database cleanup
и drop. Ни ordinary PostgreSQL, ни working DB не затронуты.

Первый browser остановился на старом tab locator в изменённом редакторе; product
ошибкой это не объявлялось. После tab→button сценарий PASS, затем усилен ожиданием
нового времени в карточке перед screenshot и повторён PASS. Assertions не ослаблены.
AI planner response подставлен, реальные suggest/approval/execution/API/DB проверены;
это не оценка точности live модели. Полностраничный AI screenshot содержит fixed
header в позиции прокрутки; не является проверкой всей геометрии на всех viewport.
Обновлённый manual screenshot сделан viewport-only после scroll-to-top.

Два синтетических Business прошли независимые ручные plan/partial-payment/
completion/repeat-visit циклы при AI_ENABLED=False. В каждом2 самостоятельных
Appointment/2 receipts, точный allocation150; неназначенный этап до schedule не
занимает слот, роль без UPDATE получает403, чужие plan/visit получают404.
Это service/API vertical slice, не полный день двух Business в браузере/WhatsApp.

### Состав для сводимого кандидата и остаток

Own tracked delta: apps/core/export_jobs.py, apps/core/tests_export_attempts.py,
frontend/e2e/management-booking.spec.ts и этот tests.md. До редактирования все4
пути были чистыми; чужих конфликтов на них не было. Остальной dirty tree чужой.
Канонический root/ветка/HEAD b9415d71 сохранены, индекс не менялся, commit/push нет.
Обязательный новый код этого тематического среза локально проверен; own code gap
не остался. Helpers/logs/synthetic artifacts остаются в output, не в release payload.

Для schema manifest координатора: текущие money contracts используют payments0002,
payments0003 и scheduling0015 поверх ранее принятого Management catalog. Это список
зависимостей кода, не утверждение о missing/applied state сервера. Target не читался.
Новых migrations/env/dependencies/permissions/notifications/BusinessEvent/AI-tools
в этой дельте нет. Профильные shared docs/roadmap/STATUS/PRIMARY не менялись по
поручению координатора; ему передаются delta и этот evidence для сводки кандидата.

AC01–06/08/09/14 имеют named domain/API и scoped browser доказательства; продолжение
ниже добавляет WhatsApp cross-flow двух Business,6consumer и2money browser cases.
AC07 дополнен claim/retry/cancel и provider-transport retry/dedup; реальный
worker/provider restart остаётся целевой приёмкой. AC10 исправленный subgap закрыт
локально. AC11 дополнен notification/search/report/legacy click-through RU/KK/EN.
AC12 подтверждён составным synthetic набором на одном source candidate; независимые
disposable fixtures не объявляются одним непрерывным live днём. AC13 проверен
в затронутых consumer/money областях, не во всём продукте; KK cosmetic wrap отмечен.
Имена/реальный персонал, Telegram и native/device не gate этого web/WhatsApp среза.

Общий build/types/i18n/bundle/full gate выполнен координатором PASS; здесь повторно
не запускался. CI/сервер, рабочие migrations, YCloud activation и deployed recovery
ведёт координатор. Эта задача не выполняла live sends, working migrations/deploy,
stage/commit/push. Полная AC01–14 и production PASS не заявлены. Первоначальный
source snapshot/patch сохранён в pilot-20261119/final-manifest.json и own.patch;
последующие receipts/checkpoint ниже уточняют новый evidence boundary.

### Продолжение AC01–14: два синтетических бизнеса, 19.11.2026

Авторизация: продолжить оставшиеся критерии WhatsApp-пилота; общий build и
проверку сервера согласовывать с координатором; рабочую БД не изменять.
Mode verification; gap evidence/environment. Предыдущий scoped PASS сохраняется
→ отсутствует связный двух-Business browser/WhatsApp срез → добавить только
недостающие consumer и cross-flow проверки, не переписывать завершённые функции.

Root C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit,
HEAD b9415d71e89167fcbf74c55187009481da066389. Own tracked paths остаются
перечисленными выше четырьмя файлами; другие dirty paths не принадлежат этому
срезу. Общий кандидат и публикация находятся у координатора. До его release-slot
заморожены application/test/dependency inputs и новые runtime/test jobs.

Проверяемый результат и проверки после освобождения ресурсов:

- AC02/03/08/11/13: реальные входы list/calendar/card/search/notification,
  сохранение ID и legacy history, отказ чужому Business, фильтры и drilldown,
  reload/503 recovery, клавиатура и RU/KK/EN на desktop/mobile. Переиспользовать
  canonical crmSession/i18n и предыдущие доказательства; screenshots захватить
  и визуально проверить, отдельно от API assertions.
- AC09/12/14: два независимых плана, неназначенный этап без слота, частичная
  оплата, назначение/завершение/повторный визит и точное распределение денег;
  проверить неизвестный результат платежа и повтор без второго receipt.
- AC01/04/06/07/12: подписанный synthetic YCloud webhook → durable event →
  Inbox/client → handoff/provider retry → ручная запись при выключенном AI →
  повторный визит. Один внешний номер в двух Business, distinct bindings,
  duplicate event/wamid и cross-tenant denial. Provider transport подставлен;
  live activation/worker outage этим не подтверждаются.

Риски: связность tenant/provenance, идемпотентность денег и сообщений, устаревшие
версии записей, недоступность AI/provider. Использовать изолированные DB/порты,
не запускать параллельные тяжёлые runtime при дефиците памяти. Existing domain,
Inbox60/PG23 и money evidence переиспользуются в их границах; новый suite проверяет
связи между ними. Общие build/types/i18n выполняет координатор. Продуктовые правки
возможны только при воспроизведённом in-scope дефекте и после проверки ownership;
они потребуют нового согласования candidate inputs и affected checks.

Применяются ранее выбранные zani-run-verification/playwright и antislop during:
сохранять существующие компоненты/копирайт, проверять реальные действия и recovery,
не выдавать screenshot за доказательство доменных инвариантов. UI-редизайн,
новые migrations/env/permissions/BusinessEvent/AI tools не планируются.
Сервер и YCloud activation остаются отдельной средовой приёмкой координатора.
Этот план не является PASS или разрешением на working-DB migration/deploy.

Подготовка после согласования с координатором: три новых ignored harness без
изменения frozen inputs. Последовательность после общего gate и restore:

1. `.venv/Scripts/python.exe output/management-booking-20261112/whatsapp-day-20261119/run.py test_whatsapp_day.WhatsAppDayTests`
2. `.venv/Scripts/python.exe output/pilot-consumers-20261119/run.py`
3. `.venv/Scripts/python.exe output/pilot-money-day-20261119/run.py`

У каждого свой SCOPE/runner/fixtures; receipt содержит хеши harness и relevant
tracked/untracked inputs, добавления/удаления во время запуска. Непустой drift
при успешных assertions даёт exit2, а не candidate PASS. Money fixture сохраняет
output path до configure_browser_runtime; это исправление найдено pre-run review.
На подготовительном этапе проверен синтаксис money Python/TS; итоговые runtime и
screenshots приведены ниже. Money query-negative проверяет membership, foreign-object denial отдельно
проверяется consumers/WhatsApp. WhatsApp plan/payment helpers доказывают backend,
а money browser — реальные действия UI; эти границы не смешиваются с PG/live outage.

Общий gate координатора завершён `QUALITY GATE PASSED (full)`; прочитан итог
`output/pilot-release-20261119-full.log`. Команда координатора:
`scripts/codex_verify.py --mode full --base-ref 58a6427ed360fc4b99cee8df0aeb152a5ff92e54`.
Backend3689:3591 PASS/98 skipped; skipped не являются PASS. Общие types/build/
bundle/mobile smoke/dependency audits выполнены координатором, здесь не повторялись.
Эта запись сама по себе не закрывает prepared suites выше; их отдельные результаты
после WSL restore/rehearsal приведены ниже. Рабочая БД этой задачей не затронута.

#### WhatsApp cross-flow — выполнено после освобождения slot

Команда1 выше: final1795077023593116900 — system check PASS, migration drift PASS,
1 сквозной тест двух Business PASS, exit0, changed_during_run=[]. Receipt/logs:
`output/management-booking-20261112/whatsapp-day-20261119/runs/1795077023593116900-*`.
HEAD b9415d71; relevant tracked/untracked inputs и own harness hashes сохранены.
Первый1795076816081730200 FAIL и diagnostic1795076920950165400 ERROR сохранены:
synthetic channel config не содержал phone_number_id; реальный onboarding.confirm
его заполняет. Исправлена только ignored fixture phone_number_id/business_account_id,
не routing приложения. Диагностическая обёртка вызывает реальный inbound handler.

Подтверждены signed webhook HTTP→durable process→Inbox/client→handoff→provider
rate-limit/retry→delivered receipt; повтор inbound/event/wamid/send/receipt/booking
не создаёт второго эффекта. При AI_ENABLED=False запись сохраняет исходный диалог,
client/business/start/status. В каждом бизнесе2 этапа независимого плана,
100+50 receipts и75+75 allocations; неназначенный этап без Appointment, повторный
визит без пересечения. Итого6 Appointment/4payments/2clients, одинаковый внешний
телефон разделён по2 Business. Manager create403 и foreign Inbox/plan/visit404.

Граница: isolated SQLite/API/domain, provider transport подставлен, money mutations
через действующие service helpers. Это не live provider/AI outage и не PG/browser
certification. Тестовая DB уничтожена, собственных Python процессов не осталось;
slot передан consumers. Общий build не повторялся, app source не изменялся.

#### Consumer browser — 6 PASS

Команда2: final1795077653680698400 — prepare/fixture/browser exit0,6 PASS(3.5m),
changed_during_run=[]. Receipt и подробные attempts/ограничения:
`output/pilot-consumers-20261119/receipt-1795077653680698400.json` и
`output/pilot-consumers-20261119/CHECKPOINT.md`. Temporary DB удалена,
порты50689/50690 освобождены; затем начат money runtime, без пересечения.

Два synthetic Business × RU1440/KK390/EN390: list/filter/reload, draft Escape и
focus return, keyboard row/drawer, empty search, actual503→retry recovery,
Appointment/calendar same-ID, archived linked Lead и unlinked same-client negative,
foreign record denial, global search, notification source и metric drilldown3
реальных Appointment. Уведомление использует фактический producer route
`/app/calendar?appointment={id}` (apps/notifications/delivery.py), не произвольную
ссылку из первоначальной фикстуры. Каждый переход проверяет идентичность записи.

Предыдущие FAIL/interrupt receipts сохранены: ожидание header/desktop-vs-mobile
поиска, дубли hidden+visible search inputs и неподдерживаемый synthetic notification
route исправлены только в ignored harness. Продуктовый дефект не подтверждён.
24 screenshots captured; агент просмотрел15, root дополнительно просмотрел9
Business1 error/notification/analytics для RU/KK/EN. Все24 визуально осмотрены.
Длинные имена в списках/уведомлениях переносятся, действия и close видны, error/retry
ясны. Analytics detail использует внутренний горизонтальный scroll для широкой
таблицы. Full-page capture ниже viewport-modal не доказывает ошибку backdrop.
Неблокирующее наблюдение: KK mobile подпись Messages разбивается на2 строки,
последняя буква отдельно; текст доступен, косметический остаток не исправлялся.

Границы: owner в обоих Business и foreign-ID denial, не полный staff workflow.
Locale preference response подставлен, entity/list/drilldown API реальные; нет
live providers/native claims. Общий build координатора переиспользован при
неизменном приложении. AC13 не объявлен безусловно закрытым для всех UI/ролей.

#### Money browser — функциональный и scoped visual PASS

Команда3:1795078454184796500 — prepare/fixture/browser exit0,2 PASS(1.5m),
changed_during_run=[]. Два Business RU1440/390: UI create2undated steps, agreement,
receipt100 с фактическим commit и подставленным503, frozen input сохраняет100,
keyboard retry создаёт ровно один receipt. Schedule/early completion первого
визита распределяет80/100; доплата140/200, schedule/complete второго дают
received=allocated=240/300, unallocated=remaining=0, ровно2receipts/2Appointment.
Per-step prices точно80+160 либо100+200; сравнение в minor units без округления.
Membership-negative query получает403/404; foreign-object проверен другими suites.

FAIL1795078051807446600: own API read не передавал обязательный business.
FAIL1795078225056902800: после успешного первого денежного цикла oracle ожидал
"80.00" вместо численно равного JSON "80" из plan_pricing.py. Исправлен only
ignored read helper и strict decimal→BigInt cents comparator; app не менялся.
Оба FAIL имеют drift=[] и сохранены. Последний runner49762 вышел0, temp DB
zani-quality-gate-bf__lp_l удалена,62523/62524 без listeners, own process query пустой.
Ресурс передан координатору для voice/same-origin.

Просмотрены6 screenshots: final и uncertain формы читаемы; оба partial-payment
capture пустые — сняты до React render после goto. Это evidence FAIL, не объявлен
дефектом UI; functional PASS не закрывает visual acceptance. Ignored spec теперь
ждёт видимый plan-payments и точный UI allocated, затем снимает partial; отдельно
снимает верхнее uncertain-message на mobile. Повтор выполнен только после voice
cleanup и нового runtime slot координатора; поверх чужого runtime не запускался.

Final capture1795079004778775900:2 PASS(1.2m),prepare/fixture/browser exit0,
changed_during_run=[]. Все8 новых screenshots просмотрены: uncertain message,
disabled retained100 и доступный keyboard retry; partial allocated80/100,
неназначенный второй этап; final240/300 и2completed visits. Пустых снимков нет.
Mobile modal имеет внутренний scroll: верхнее сообщение и нижний retry показаны
отдельно. Full-page fixed bottom navigation не трактуется как document-level overlay
дефект. Scoped geometry/meaning/recovery/keyboard/desktop-mobile checks PASS;
редизайн/новая копия/новые компоненты N/A — продуктовые UI файлы не менялись.
Runner4135 exited0, temp jrkco5tt удалён,55610/55611 без listeners, ownPython/Node
query пустой. Slot окончательно возвращён координатору для same-origin artifact.

### Итоговая матрица AC01–14 этого продолжения

Это границы локальной проверки, не замена полных acceptance IDs roadmap.
Существующие214/64/PG21/Node12/Management browser и evidence18.11 переиспользованы
для неизменных слоёв; новые сквозные сценарии не заменяют concurrency/authorization.

| AC | Подтверждённый локальный результат | Остаток за этой границей |
| --- | --- | --- |
| 01 | Signed WhatsApp→Inbox/client→manual Appointment при AI off, без обязательного Lead/Deal | Реальный подключённый канал |
| 02 | Единый ID list/calendar/card, edit/transfer/domain lifecycle, reload и503 recovery | Target-version проверка после согласованного deployment |
| 03 | Legacy archived Lead→точная запись; unlinked same-client не подменяет связь; history/import tests | Сохранение реальных target-данных при rollout |
| 04 | Named permission/tenant suites, manager create403, foreign Inbox/plan/visit404, membership denial | Реальные staff sessions/target policy — у координатора |
| 05 | Domain transitions/replay/last-slot/PG locks и UI early completions с точным allocation | Нового code gap не выявлено |
| 06 | Persisted source_conversation, handoff/retry и Inbox context; reused Inbox60/PG23 | Live AI/provider приёмка остаётся отдельной |
| 07 | Claim/retry/cancel suites и synthetic provider retry/dedup без второго сообщения | Deployed worker/beat/outage recovery |
| 08 | Record/financial selectors +3-record drilldown из аналитики для обоих Business | Live данных/всех отчётов этот набор не сертифицирует |
| 09 | UI partial receipts, unknown-response replay, exact package/per-visit allocation; existing correction/refund/PG proofs | Нового локального code gap нет; ручной учёт, не банковская интеграция |
| 10 | Export execution cap/CSV count fixed;64suite, import/merge/history/access; shared full gate PASS | Target rollout/history preservation |
| 11 |6cases actual web list/card/calendar/search/notification/legacy links | Native вне текущего пилота |
| 12 | Два Business в WhatsApp/API и browser money циклах на неизменном candidate; no-data/recovery и isolation | Один live день/реальный channel outage не подменены mock transport |
| 13 | RU/KK/EN consumer desktop/mobile, money RU desktop/mobile,32 финальных screenshots осмотрены | KK bottom-label cosmetic wrap; все роли/весь UI не сертифицированы |
| 14 |2undated steps без Appointment, постепенные2визита/точные деньги; reused terms/corrections tests | Нового локального code gap не выявлено; целевая среда отдельно |

В согласованном дополнительном local evidence scope остатка нет. Code: новых
дефектов продукта не воспроизведено, исходный export fix сохранён. Evidence: три
подготовленных suites и visual gates выполнены; FAIL/промежуточные partial proofs
не переименованы. Environment: рабочая DB не тронута, deployed acceptance/activation
и same-origin artifact остаются у координатора. Owner decision: новые product
решения здесь не требовались; публикацию общего кандидата ведёт координатор.
Общие roadmap/contract/passport/STATUS обновляет координатор по этому evidence;
описанное API/права/env/migrations не менялись, новые изменения технических
контрактов от этого verification-only продолжения не требуются.
