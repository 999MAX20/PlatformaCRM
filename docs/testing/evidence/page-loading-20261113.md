# PAGE-LOADING-20261113

## Результат и граница

Начальная загрузка затронутых CRM/platform страниц объединена в один индикатор.
После первого показа готовый экран не скрывается из-за polling или локального
действия. Inbox сохраняет список и черновики при переключении; временный сбой
обновления оставляет полученные данные с повтором, отказ доступа скрывает их.
Загрузка каналов и календаря больше не добавляет сдвигающие список строки.

Локальная приёмка завершена. Это проверка загрузки и связанных регрессий,
не полная сертификация всех действий CRM, production, real-provider или deployment.
В принятом scope остатка по коду, локальным доказательствам, среде и решениям
владельца нет. Git-публикация и фактический CI фиксируются отдельно в checkpoint.

Основа: `9cc5f5ffbfe8634dc2bd4ff91b2efd27c7bae9f8`, текущая ветка
`codex/ui-testing-toolkit`, canonical `C:/Users/user/Desktop/PlatformaCRM`.
Проверена исходная рабочая версия на этой основе; frontend source не менялся
после успешной сборки. Последующие изменения касались тестов и документации.
Исходные и итоговые манифесты, команды и логи:
`output/page-loading-20261113/CHECKPOINT.md` и `source-manifest.json`.

## Реализация

- `PageLoadingBoundary` учитывает явно зарегистрированные начальные зависимости
  и Suspense. Дочерние компоненты остаются смонтированными; скрытая часть имеет
  `hidden`/`inert`. После готовности boundary не возвращается к общей загрузке.
- `LoadingState initial`, `scope="page"` и `usePageLoading` переиспользуют
  существующий индикатор. Локальные индикаторы компактны; глобальный счётчик
  запросов, необязательный AI, polling и скрытые настройки не блокируют страницу.
- `Dialog`/`Drawer` ждут видимости страницы перед порталом, scroll lock и фокусом.
- Inbox разделяет загрузку списка, переписки и контекста; временные ошибки с
  готовыми данными показывают retry без потери черновика. Permission errors
  сохраняют отказ доступа. Изменение ключа анимации не перемонтирует весь Inbox
  при смене выбранного диалога.
- Применение включает dashboard, calendar/records, account/settings, tasks,
  общие таблицы, management/branches, notifications, imports, voice history,
  pricing и platform panels. Проверены представительные потребители, а не каждая
  бизнес-операция этих модулей.

Backend/API/schema/permissions, notifications, BusinessEvent и AI execution не
менялись. Рабочая БД, `.env`, провайдеры и deployment не затронуты. Тестовые записи
созданы только в disposable SQLite через `scripts.codex_verify.isolated_runtime`.
Задержки/503/403 и второй диалог задавались browser interception; остальные
проверяемые данные получались от изолированного реального API. Реальных отправок нет.

## Проверки

| Проверка | Результат и доказательство |
| --- | --- |
| Итоговая загрузка страниц | 22 PASS, `loading-visual-final.log`: Inbox, 11 семейств CRM, platform details, hidden settings, empty, cached navigation, error/retry, polling503/403, switch/draft |
| Узкий экран и увеличение текста | 1 PASS, `loading-accessibility.log`: 320px, текст200%, reduced motion, отсутствие overflow и фокуса внутри hidden/inert, отсутствие `pageerror` |
| Существующие регрессии | 19 сценариев подтверждены: 14 PASS в `regressions.log`, 3 исправленных ожидания PASS в `regressions-adapted.log`, последние2 PASS в `regressions-unique.log`; это объединение сценариев, не один полностью зелёный запуск |
| Node | 17 PASS, `node-focused.log`: readiness lifecycle, draft provenance, sending model, error normalization |
| Frontend build | PASS, `build.log`: i18n, TypeScript, app и widget; повторно использован неизменённый source/lock snapshot |
| Bundle | PASS, `bundle.log`: app shell352.3KB при бюджете400KB; предупреждения RU/KK lazy dictionaries563.2/564.8KB сохранены |
| Контраст | Текст `#4F5E58` на белом6.83:1, ring/focus `#007A59` на белом5.35:1; существующие semantic tokens |
| Diff/docs | Рабочий, staged и реальный committed range проверяются перед публикацией; ссылки/registry и новые файлы включены в итоговый обзор |

Команды из корня: `.venv/Scripts/python.exe output/page-loading-20261113/check.py
<run-name> <spec> [--grep <expression>]`. Проверки запускались последовательно
в одном disposable runtime, без конфликтующих setup/reset. Точные аргументы
содержатся в checkpoint. Node из `frontend`:
`node --test scripts/tests/page-loading-state.test.mjs scripts/tests/inbox-draft-provenance.test.mjs scripts/tests/inbox-sending-model.test.mjs scripts/tests/app-error-normalization.test.mjs`.
Сборка: `npm run build`, `npm run check:bundle`.

Полный backend/PG/full-release gate не запускался: серверная семантика неизменна.
Browser evidence не заменяет проверки прав сервера и не заявляет их новую сертификацию.

## Разобранные падения

Сохранены первоначальные ошибки harness: неверный legacy endpoint второго диалога,
405 при попытке создания bot conversation, шаблон URL без query string, неверные
tasks/branches endpoints и records selector. Исправлены fixtures/ожидания;
продуктовые проверки одного loader, геометрии и черновиков не ослаблялись.

Пять старых Inbox сценариев использовали устаревшие booking route/title/client
control, меню приоритета, набор AI-действий и лишнюю кнопку связи. Ожидания приведены
к существующим подтверждённым сценариям; проверка явного подтверждения сохранена.
Два последующих strict-selector падения вызваны одноимёнными тестовыми клиентами
после повторных запусков. Уникальные имена устранили коллизию; проверка точного
Client ID после реальной привязки сохранена. Продуктовые обходы не добавлялись.

## Визуальная приёмка / Anti Slop Delivery Gate

Режим `during`; направление: существующая CRM, спокойная плотность и типографика,
ENERGY1/RHYTHM1/MOTION1 с функциональным индикатором ожидания. Общий белый экран
показывает одну стадию готовности; локальная строка сохраняет место рабочему содержимому.
Новые assets, декоративные блоки, статическая продуктовая copy и зависимости не добавлены.

- PASS geometry: начальные/готовые dashboard, calendar, account, tasks, records,
  clients/branches и новые notifications/import/voice/platform поверхности;
  локальное ожидание Inbox не сдвигает список. Снимки захвачены и просмотрены.
- PASS states/actions: initial/empty/error/retry, background503/recovery/403,
  cached navigation, hidden settings, переключение и сохранение черновика.
- PASS accessibility: status/aria-live, hidden/inert, reduced motion,320px/text200%,
  Enter открывает inspector, Escape закрывает и возвращает видимый focus.
- PASS localization/responsive: RU390, KK768, EN1440; длинное имя остаётся
  читаемым в контексте и сокращается в ограниченной строке; горизонтального overflow нет.
- PASS purpose/consistency: существующие цвета/шрифты/отступы/иконки; spinner
  означает реальный pending, retry выполняет refetch; нет вымышленных production данных.
- N/A: новые темы, медиа, marketing/FAQ, формы и мобильная экранная клавиатура
  не изменялись. Полный аудит всех существующих controls и WCAG conformance не заявлен.

Снимки: `output/page-loading-20261113/browser/loading-visual-final/` и
`browser/loading-accessibility/`. Первые кадры переходов иногда снимались до
завершения200ms появления: итоговые снимки фиксируют завершённые анимации,
а отдельные проверки reduced motion выполняются до снимка.

## Согласованность документации

Обновлены [frontend contract](../../current/frontend.md),
[frontend README](../../../frontend/README.md), [Inbox passport](../../pre-production/inbox.md),
registry, STATUS и PRIMARY-SESSION. Roadmap не закрывается: это локальная UI-задача,
нового бизнес-этапа нет. Product/CRM/access/AI/integrations/operations и root README
не требуют изменения: API, права, данные, setup и серверное поведение прежние.
Чужие изменения в совместных документах сохранены и исключены из коммита задачи.
