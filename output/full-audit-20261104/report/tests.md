# Проверки расширенного аудита

Семантическое чтение, реестры процессов и доступные дополнительные сценарии
завершены. PASS ниже относится только к указанной границе; известные FAIL сохранены.

## Сохраняемые результаты предыдущего прогона

`../source-baseline.json` сравнивает прежние входы с текущим деревом: изменения
только в документах, не в приложении. Поэтому неизменившиеся scoped-проверки
сохраняют применимость; они не доказывают новое требование полного покрытия.
Команды, fixture, исходные ошибки и ограничения остаются в
`docs/testing/comprehensive-audit-20261103/tests.md` и его assets.

| Граница | Результат |
| --- | --- |
| Django system / migration drift | PASS / PASS в изоляции |
| Полный SQLite backend | 2 752: 2 698 PASS, 4 FAIL, 50 SKIP |
| PostgreSQL row-lock/concurrency | 50 PASS; исходный teardown FAIL сохранён |
| Frontend types/build/i18n/bundle | PASS; предупреждения chunk size сохранены |
| Node | 215 PASS, 7 FAIL; повтор исходных 7 FAIL сохранён |
| Automatic booking | Stale terms, responsible/source и creation effect FAIL с работающими controls |
| Worker/broker/AV/backup restore | Адаптированный изолированный drill PASS; штатный helper fixture FAIL сохранён |
| UI | 45 route cases и отдельные reachable flows; не полный набор нового поручения |
| Dependency advisory scan | npm 0; Python 14 advisories в 3 dev packages; не доказанная эксплуатация |
| Исторический native | Локальные logic repro; не build/device/live API acceptance |

## Новые проверки и независимые перепроверки

| Команда / receipt | Результат и граница |
| --- | --- |
| `.venv/Scripts/python.exe -m unittest scripts.tests.test_codex_verify scripts.tests.test_api_load_smoke scripts.ai_behavior.test_transport -v` | 24 PASS; `../tooling-unittest.log`; не проверяет загрузку рабочего .env |
| `../continuity-tests.log` | 3 PASS; только continuity hooks |
| `../compose-merge.log` | Реальный Compose merge PASS с synthetic env и исключённым working env_file; без старта контейнеров |
| `../performance/summary-with-sampler-limit.json` | Burst 40/50 HTTP200, 10 deadlines; soak 109/110 HTTP200, 1 deadline; ошибка sampler сохранена |
| `../performance-soak-corrected/extended-load.json` | Новый soak 120/120 HTTP200, p95 51,504s, ноль sampler errors; это тяжёлая задержка, не SLO PASS |
| `../sampler-selftest.json` | Исправленный audit helper выдержал concurrent sampling/new-child control |
| `.venv/Scripts/python.exe output/full-audit-20261104/backend/run_pagination_probe.py` | 1 FAIL: Inbox пропускает boundary message; control полного списка и limit0 работают; disposable DB уничтожена |
| `../backend/team-visibility-probe-1793741027.log` | 1 reproducer PASS подтверждает source visibility defect; не acceptance PASS; foreign Business403 control |
| `../team-analytics-independent-review.md`, `../inbox-pagination-independent-review.md` | Независимое чтение source/contract/probe/result; повторный runtime не заявлен |
| `../exception-logging-independent-review.md` | Условный вывод exception secrets, подтверждён статически; фактическая утечка не заявлена |
| `../root-read-validation.json` | 918 assigned paths + 2 cross-review, диапазоны и hashes PASS |
| `../archive-read-validation.json` | 153 captured versions validated: 152 own historical + 1 third-party |
| `../archive-payload-summary.json` | 250 ZIP, 40 556 members, 2 599 260 305 bytes, zero CRC/read errors |
| `../python-installed-provenance.json`, `../node-installed-provenance.json` | Current installed hashed bytes match RECORD/cached lock tarballs; unhashed entries и platform omissions отдельно |

Новые TEAM/Inbox runners используют disposable DB и запрет connect в probe,
но не подавляют settings.read_env: отсутствующие в SAFE_ENV переменные могут
загрузиться из рабочего .env. Поэтому эти два процесса не названы полностью
герметичными. Рабочая DB не была целью; внешние эффекты не воспроизводились.
Предыдущий полный прогон и новый performance используют отдельный audit guard,
который подавляет read_env до settings import и блокирует внешние sockets.

## Не выдаётся за PASS

Codex Security Deep Scan ранее не стартовал из-за отсутствующего managed
filesystem permission profile. Позднее подзадача получила отказ автоматической
проверки безопасности; точная заблокированная операция не была предоставлена.
Повтор/переформулировка заблокированного действия не выполнялись. Независимое
безопасное статическое чтение завершено; полный active-security PASS отсутствует.

Нет live provider/LLM, Linux image, Yandex topology, physical mobile или release
acceptance. Финальные UI/backend реестры различают выполненные проверки,
доказанные дефекты, representative handler equivalence и недоступное выполнение.
99 UI protected/external command instances не объявлены новыми успешными кликами;
[финальная UI-сверка](../ui/final-ui-validation.json) сохраняет эту границу.

## Дополнительная сверка переходов и реестров

Backend transition registry содержит59 command graphs для38 сущностей в39 source
файлах. Для13 graphs выполнены89 state-pair cases:43 разрешённых и46 запрещённых
переходов. Для45 указаны именованные прежние проверки с точными assertions/results;
ещё один graph PricingAlert покрывает оба сохранённых source states. Валидатор
source hashes/ranges/log/test receipts не обнаружил ошибок. Это не полный
cross-product всех прав, состояний и конкурентных interleavings.

Первый batch сохранил24 Appointment fixture errors из-за отсутствующего service FK.
Исправлена только fixture, повторены затронутые24 случая и2 operational observations;
Task35/Lead30 не повторялись. Сам reproducer PASS может доказывать дефект, поэтому
его результат не следует читать как acceptance продукта. Точные данные:
backend/semantic-transition-summary.json и backend/semantic-transition-validation.json.

Role matrix охватывает680 preset cells и отдельно effective decision conditions,
13 source functions и28 named existing test receipts. При проверке генератора
найдена собственная ошибка прямого lookup: не учитывался wildcard/manage fallback.
Исправлены136 owner/admin строк и генератор; приложение не менялось. preset_allowed
не выдаётся за runtime effective permission. Коррекция и zero-error receipt:
backend/role-decision-summary.json и backend/role-decision-contract.json.

API/jobs/events CSV сохраняет976 операций,17 jobs и245 event sites (1238 строк),
source/evidence references и ограничения. Это экспорт статических связей;
число строк не является числом успешно выполненных HTTP запросов.

## Дополнительные миграции и shared UI

Девять новых ordinary migration scenarios PASS на заполненных технических
predecessor states: billing2, bots2, clients1, CRM2, AI1, notifications1.
MigrationExecutor выполняет реальные data operations, затем synthetic failure
после записей проверяет rollback/отсутствие migration record; retry и повтор
data function сохраняют результат. Это SQLite, не PostgreSQL/process kill и
не объявленная поддерживаемая предыдущая release-версия. Initial fault harness
failure и затем missing Deal.client fixture error сохранены; повторён только
исправленный stage case. Точные команды, строки и оставшиеся3 protected migration
boundaries: [migration acceptance](../backend/migration-acceptance.md).

`node frontend/node_modules/@playwright/test/cli.js test --config
output/full-audit-20261104/shared-ui/playwright.config.cjs`: **45 PASS**.
Копии четырёх существующих specs меняют только import/artifact paths; assertions
сохранены. [Provenance](../shared-ui/provenance.json), [результаты](../shared-ui/results.json).
Проверены calendar controls, alerts, state/recovery/clipboard/connectivity и
action color matrix на фактических текущих fixture pages.

Дополнительный isolated callback harness проверяет actual shared components:
Switch/Tabs/menu, local/remote SearchableSelect, portal Select, modal/drawer,
field-focus и route-view callbacks. Первое создание harness не отрисовалось;
после исправления только audit JSX/import.meta build settings отрисовка появилась.
Первоначальный pageerror не был сохранён, поэтому точная причина не сертифицирована. Затем
ошибочный combobox selector у SearchableSelect оставил один failed probe;
исправлен на реальную button semantics, повторён только он. Продуктовые
assertions не ослаблялись. [Основные результаты](../shared-ui/extra-results.json),
[повтор search](../shared-ui/extra-search-retry.json),
[дополнительные calendar keys](../shared-ui/calendar-extra.json).

109 исходных shared UI sites сопоставлены по уникальному site_key и SHA в
[action-state-root-shared.json](../ui/action-state-root-shared.json). Два root
fallback действия заблокированы подтверждённым UI01; неиспользуемые варианты,
hidden form adapters и parser wrapper declarations имеют отдельные статусы.
Шесть non-JSX widget events/states учтены дополнительно, без изменения знаменателя
исходного JSX inventory. [Widget review](../widget-independent-review.md) отличает
реальные клиентские observations от перехваченной доставки.

373 account/platform/support AST occurrences дополнительно сверены с точными
выражениями/хешами и исходным контекстом. 348 имеют named consumer/shared handler
equivalence;25 защищённых command dispatch сохраняют static/reused boundary ENV-SECURITY.
Это не373 независимых browser tests. [Реестр](../ui/action-state-root-platform-support-account.json).

Новые обычные UI probes использовали текущий изолированный runtime, перехватывая
запросы записи до сервера. Profile/preferences503 сохраняют ввод и показывают
нормализованную ошибку; локальная фотография реагирует на клавиатуру/перетаскивание;
public/internal support drafts сохраняются при переключении; create503 и явный
discard проверены. Synthetic incident GET pages1→2 и link503 проверяют UI, без
реальной связи или отправки сообщения. [Account](../ui/account-extra-root.json),
[support](../ui/support-ordinary-root.json), [incident](../ui/incident-ui-root.json).
Platform finance disclosure работает, page999 Retry повторяет404 и остаётся
находкой, хотя search позволяет восстановиться. [Platform](../ui/platform-followup-root-runtime.json).

Первый account harness перехватил собственный обычный refresh-cookie запрос и
не дошёл до страницы; после разрешения штатного refresh получен scoped результат.
Первый incident probe ожидал неверную RU-подпись Next вместо «Вперёд»; исходный
частичный receipt сохранён, исправлен только selector. `errorVisible=false` в
первом account receipt проверял буквальный fixture detail, который штатно заменён
понятной ошибкой; дополнительный receipt подтверждает feedback. Немедленное
`aria-selected=false` после операции tabs не трактуется как дефект: снимок сделан
до React commit, а конечный URL подтверждает переключение.
