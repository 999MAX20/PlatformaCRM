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
