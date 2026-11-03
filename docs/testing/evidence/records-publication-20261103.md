# Records и планы — проверка пакета публикации03.11.2026

Владелец разрешил включить предшествующую реализацию Records/планов посещений,
исправления RF-01–09 и существующий коммит документации `e02a28f5`.
Кандидат выделен из смешанного рабочего дерева; прежний локальный PASS сам по себе
не использован как доказательство работоспособности этого состава.

## Поведение и граница

Основной merchant workflow использует существующий Appointment: список/карточку,
pipeline, Client/Inbox/search/tasks, очереди и метрики, подтверждаемые AI-команды.
Исторические Lead/Deal данные и API сохранены; старые ссылки разрешаются по реальным
связям и текущим правам. Автоматической конвертации данных нет.

VisitPlan/VisitPlanStep объединяют визиты клиента. Неназначенный этап не занимает
слот. Назначение использует create_record, текущие права/условия/версию, атомарные
эффекты и идемпотентность. Доступны история, изменение, ответственный, архив и
восстановление. Migration scheduling0011 проверена только в изолированных базах.

Панель Records остаётся однострочной. Период раскрывается на странице без modal;
черновик применяется атомарно, Escape/отмена возвращают фокус. Период сохраняется
отдельно для actor/Business. Исправлены TEAM actions, возврат query/page, pending
закрытие/поздняя навигация, invalid-page recovery, debounce/history, права графика
и создания плана, пустая колонка филиала и вложенный main.

Денежные версии/распределение, D01, полная AC-CRM-PILOT-01–14, live/production и
рабочие миграции не закрыты. Несвязанный рефакторинг уведомлений/приватных проекций
и другие локальные изменения исключены. Включены только необходимые зависимости:
client_projection для scoped поиска Records, resource_id/resource_type в результате
replay плана, locale-форматирование даты и тексты ошибки загрузки.

## Точный кандидат и проверки

Root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
base `e02a28f550e94a543c3d88acac7c1b19ee48f90b`.
[Git blobs проверенного исходного кода](records-publication-20261103-manifest.json).
Отдельный Git index и read-only Python/Node overlays использовали канонические пути;
другой checkout/worktree не создавался, чужие рабочие файлы не перезаписывались.
Команды, исходные снимки, патчи и журналы: `output/records-publication-20261103/`.

- `run_candidate.py dependent test ... --noinput`: **213 PASS**. Точный список
  suites сохранён в manifest: scheduling/records/plans/commands, cards/queues,
  AI tools/workflow, analytics и automations. Включены negative/role/tenant,
  rollback/replay/stale и зависимости состояний. Это не весь проект.
- `run_candidate.py focused-replay test ...`: **2 PASS**, затем вошли в общий213.
- `.venv/Scripts/python.exe output/records-publication-20261103/postgres.py`:
  **29 PASS**, disposable PostgreSQL17: планы/команды, last-slot и повтор команды,
  гонки переходов. Сервер остановлен самим runner.
- `run_candidate.py system check` и `run_candidate.py drift makemigrations
  --check --dry-run`: **PASS**, system issues0, дрейфа нет.
- `frontend_verify.py build`: **types/i18n6616/app/widget PASS** через Node overlay;
  `npm run check:bundle`: **PASS**, предупреждения ru/kk chunks>500kB сохранены.
- Node с overlay: record-filters, record-legacy-export, route-prefetch,
  timeline-presentation, task-workspace, appointment-cache: **25 PASS**.
- Playwright `--config output/records-publication-20261103/playwright.config.cjs`:
  **13 уникальных сценариев PASS** в применимых чистых запусках. Первый чистый
  запуск дал10 PASS/1 fixture failure; исправленный ID из fixture и2 сценария
  планов дали4 PASS (один ранее пройденный перенос повторён для правильного ID).
  Проверены TEAM/viewer/creator, query/page/search, RU/KK/EN1440/390/320,
  pending/retry/late navigation, shared Calendar/Client и CRUD/schedule планов.

## Сохранённые неуспехи и ограничения

Первое выделение пропустило locale-аргумент formatDateTime и тексты RecordsLoadError:
types/i18n выявили зависимости, они включены до итогового build PASS. Первый backend
запуск выявил отсутствующий client_projection; следующий — resource_id при replay
(54 из56 прошли). Зависимость добавлена, focused2 и последующий общий213 прошли.
Ни одна проверка не ослаблена для получения PASS.

Первый browser запуск на копии старой тестовой БД дал10 PASS/1 FAIL: в копии были
миграции исключённых уведомлений, несовместимые с опубликованным baseline.
Созданы чистая БД и fixtures из кандидата; рабочая БД не использовалась. В чистой
fixture первая запись имеет ID6 вместо7: исправлен только адрес в тесте, TEAM/viewer
проверены повторно. Эти исходные неуспехи не объявляются успешными запусками.

Mock AI/eager и блокировка внешней сети; Chromium, не все браузеры/дикторы.
Full-project E2E/release/live/provider suites не запускались: публикация данного
пакета не является разрешением release или deployment. Требования R01 сохранены.

## Публикация

Перед коммитом remote main проверяется напрямую. `git fetch origin main` обновлял
только FETCH_HEAD: сохранённый fetch refspec не включал main. Явный fetch
`refs/heads/main:refs/remotes/origin/main` подтвердил origin/main=HEAD=`e02a28f5`.
Поэтому прежний вывод об одном неотправленном коммите основывался на устаревшей
tracking ref; новый push этого коммита отдельно не нужен. История не переписывалась.

Фактические commit/push/remote SHA/CI фиксируются после отправки в STATUS/PRIMARY.
Этот отчёт подтверждает локальные проверки выделенного состава, не deployment.
