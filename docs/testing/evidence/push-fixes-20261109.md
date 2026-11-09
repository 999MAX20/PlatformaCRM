# Исправления перед подготовкой push — 09.11.2026

Поручение: исправить все находки PUSH-PREPARATION, проверить и подготовить изменения
к push, сохранив чужую работу и исходные тестовые гарантии/лимиты. Канонический
checkout `C:/Users/user/Desktop/PlatformaCRM`, ветка `codex/ui-testing-toolkit`,
HEAD `6a8af190`; проверяется dirty snapshot. Исходные patch/index/status сохранены
в `output/push-fixes-20261109`. Push/deployment и рабочая БД не затрагиваются.

## Изменения

- Пустая числовая граница получает400 до SQL; multiselect использует JSON-массив
  и существующую валидацию options/roles. UI клиентов и услуг переиспользует одну
  форму флажков. Совпадение массива точное; пустые значения доступны через is_empty.
- Восстановлены две строки истории комментариев задач и пять строк bot tests.
  Добавлены assertions на реальные тексты activity.
- Клиентский selector использует SQL alias для промежуточных latest_* выражений.
  CRM conversation serializer не вычисляет необязательный Inbox ai_safety.
  Связи задач, entities, история и права не удалены. Полный Inbox сохраняет ai_safety;
  это отдельно проверяется regression test.
- Voice test loader обрабатывает несколько exports. Проверки action colors ищут
  действия в выделенных компонентах; daily workspaces проверяют утверждённый
  appointments workflow и его permission guards. Удалённые старые billing действия
  заменены проверкой текущего commerce flow; нет снижения лимитов или skip.
- Route inventory учитывает split Routes и metadata, неизвестные пути остаются
  ошибкой. Новые записи реестра остаются NOT_RUN, без вымышленных receipts.
  API inventory разбирает arrow/conditional wrappers статически и учитывает
  дополнительные axios clients; module policies и endpoint paths актуализированы.
  Новые parser fixtures сохраняют контроль найденных и неизвестных API/маршрутов.

## Проверки

- Изолированная SQLite focused фильтров:26 PASS (`filters.log`).
- PostgreSQL:35 фактических тестов карточек/фильтров/клиентов PASS. Первая команда
  также содержала несуществующий модуль tests_crm_read_scope и завершилась loader
  ERROR; этот исходный результат сохранён. Корректные dependent modules
  tests_crm_projection_access, tests_client_pii_projections,
  tests_mixed_membership_scope, tests_crm_cards:62 PASS (`card-access-pg.log`).
- PostgreSQL representative fixture budget:148383/150000 bytes; max SQL12181/15000 chars; при росте
  fixture60→300 query count36→37. Порогов и assertions производительности не меняли.
  Отдельный UTF-8 metric fixture150673bytes проверяет корректность измерения байтов,
  не содержит payload-budget assertion; PASS фиксированного fixture не означает
  универсальный предел любых реальных данных или доказанный production SLO.
- Node aggregate:288 PASS (`node-final.log`); последняя корректировка endpoint
  metadata отдельно:6 PASS (`node-registry-final.log`). Ранний Node loader failure
  сохранён в исходном логе и исправлен; это не итоговый FAIL.
- Build/types/i18n и bundle PASS (`build.log`, `bundle.log`).
- Браузер реального isolated API:12 сценариев client/service × RU/KK/EN ×1440/390,
  single/multiple/exact results, no-data, blank boundary, recovery, keyboard,
  отсутствие горизонтального overflow (`browser-filters-3.log`). Locale подменяет
  только preferences в auth/me; business endpoints реальные. Первые попытки
  harness падали из-за cookie-auth и locator, исходные логи сохранены.
- CRM-card browser: задачи и последние сообщения на desktop/mobile, task relations
  в API, отсутствие ai_safety только в CRM (`browser-card-final.log`).
- Общий isolated SQLite backend:3106 tests,3038 PASS,68 PostgreSQL-only skips,
  без FAIL/ERROR;2287.549s тестового времени. Все68 skip требуют реальных row locks;
  это не68новых PASS на PostgreSQL. Затронутые PG suites приведены выше; неизменные
  concurrency evidence прежнего review не выдаются за новый полный PG прогон.
- System check, migration drift и working/index/committed-range diff hygiene PASS
  (`backend-results.json`); база сравнения0b3348e1ab31121a106badbde830b496ec477aac.
  Команда: `.venv/Scripts/python.exe output/push-fixes-20261109/verify_backend.py`.
  Она использует `scripts.codex_verify.isolated_runtime` и backend stages.
- Build: `npm run build`; bundle:`npm run check:bundle`; Node:`node --test
  frontend/scripts/tests/*.test.mjs` (runner передаёт явный список файлов).
  Focused PG runner:`output/performance-20261106/verify.py`; точные modules/logs
  указаны в checkpoint. Зависимости не переустанавливались:8inputs неизменны,
  audits/lock/tooling evidence PUSH-PREPARATION переиспользованы пропорционально.
- Рабочая БД не менялась. Собственный browser runtime остановлен, full backend
  завершился и удалил disposable DB. Полный E2E/deployment не запускались.

## Git и границы

20 локальных и3 remote-only коммита; origin —999MAX20/PlatformaCRM.
Пустой index.lock существует с06.11; основной index не изменён. В отдельном
временном index собран кандидат842явных путей. Staged diff-check обнаружил
лишнюю пустую строку EOF в ранее untracked notification-refactor.spec.ts;
исправлена только эта whitespace-строка, повторный staged diff-check PASS.

Preview полного dirty candidate выявил9конфликтов: README, STATUS,
config/settings, current/frontend, current/operations, documentation-index,
pre-production/capabilities, PRIMARY-SESSION, landing/styles.css. Автоматическое
объединение также дублирует crmLanding import в vite.config.ts. Предложенное
разрешение сохраняет текущие проверенные версии этих10файлов. Все добавленные
remote строки документов присутствуют; remote safeguards и landing CSS сохранены.
После разрешения proposed merged tree точно совпадает с candidate tree.
Это предложение через временные индексы, не merge/commit рабочей ветки.

План и точные hashes: `output/push-fixes-20261109/PUBLICATION-PLAN.md`,
`merge-resolution-preview.json`, `proposed-stage-paths.txt`. Из1184ранее проверенных
путей1164не изменились;20изменений в них принадлежат текущей задаче. Ещё13путей —
ранее clean файлы и новые regression/evidence. Неожиданных чужих изменений или
удалений нет. Проверка новых/изменённых файлов по secret-patterns:0совпадений;
175локальных Markdown-ссылок разрешаются. Удалённые страницы/anchors не проверялись.

Полного release/live PASS не заявляется. Рабочие миграции, провайдеры, сообщения,
production и новые CI не запускались. Неизменные audits/mobile/tooling из
PUSH-PREPARATION переиспользуются только после проверки соответствующих hashes.
Документы: обновлены контракт import-workspace/entity-cards, паспорта clients и
settings-notifications; остальные CRM/domain/AI/notification contracts и README
не меняются, поскольку lifecycle, effects, setup и deployment не изменены.

## Итог и оставшаяся граница

Все исходные продуктовые находки и обязательные красные проверки исправлены в
согласованном объёме. Новые regression assertions добавлены, лимиты сохранены.
Остатка по коду и применимым локальным проверкам нет. Подготовлен конкретный
candidate и разрешение Git-конфликтов без потери обеих сторон. Реальное объединение
истории требует решения владельца по правилу AGENTS о concrete affected-path
conflicts; до него основной index/branch/lock не изменяются. Commit, push, новый CI
и deployment не выполнены. Этот scoped результат не закрывает другие acceptance IDs.
