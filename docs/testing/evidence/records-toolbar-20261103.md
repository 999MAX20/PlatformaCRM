# RECORDS-TOOLBAR-20261103

## Результат и граница

По одобренным владельцем desktop/mobile референсам страница «Записи» получила
компактную локальную панель: поиск, период, дополнительные фильтры и сортировка.
Статусы отделены от ссылок «Календарь»/«Планы посещений»; на телефоне статусы
прокручиваются одной строкой. Активные дополнительные условия, клиент и attention
показываются с индивидуальным удалением; общий сброс доступен и при непустой выборке.
Окно фильтров использует черновик, отмену и применение. Сброс внутри окна меняет
только черновик. Даты применяются вместе, обратный/неполный диапазон не отправляется.
Обычный сброс возвращает «Сегодня»; существующая семантика client/attention без дат
сохранена. Пагинация сбрасывается при изменении условий, прочие параметры сохраняются.

API, backend-права, данные, схемы, уведомления, BusinessEvent и AI не изменялись.
Использованы текущие Button/Input/Select/Modal, focus-return и токены; общие компоненты
не модифицировались. Новая панель — отдельный RecordsToolbar, запрос остаётся в API-слое.
Визуальный ориентир — [предшествующий аудит](appointments-ui-audit-20261103.md),
одобренные изображения и промпты сохранены в output/appointments-ui-references-20261103.
Изображения были концептами, размеры и поведение подтверждены уже в браузере.

## Проверки

Канонический `C:\Users\user\Desktop\PlatformaCRM`, ветка `codex/ui-testing-toolkit`,
HEAD `e02a28f550e94a543c3d88acac7c1b19ee48f90b` + сохранённый существующий WIP.
До изменения RecordsPage/recordFilters сохранены в output/records-toolbar-20261103/before;
starting-status, PLAN, runtime и логи — в том же каталоге.

- `node --test frontend/scripts/tests/record-filters.test.mjs`: **5 PASS** —
  business-day/exclusive end, client/attention, invalid date, атомарный patch,
  сброс с сохранением несвязанных параметров.
- `npm run build` через `scripts.codex_verify.safe_environment`: **PASS**,
  включает i18n, TypeScript, приложение и widget. Зависимости не переустанавливались.
- `node node_modules/@playwright/test/cli.js test --config=playwright.records-toolbar.config.ts records-toolbar.spec.ts`:
  **3 PASS**, RU/KK/EN. Заполненная выборка3 → confirmed1; черновик/отмена/применение,
  chips/count/remove/reset, reload/back/forward, Escape и возврат фокуса,
  неправильный диапазон, атомарные даты и exclusive end, пустой результат,
  desktop1440/mobile390×844, отсутствие горизонтального переполнения,
  текст результата и кнопки окна в видимой области.
- Тот же config, `records-bell-recovery.spec.ts --grep 'records real'`
  с отдельным `--output=../output/records-toolbar-20261103/recovery-results`:
  **3 PASS**, RU/KK/EN, список/статусы/поиск/пустота,404/503/400/403 и retry с клавиатуры.
- Просмотрены сохранённые RU desktop/mobile/filter screenshots; новые пользовательские
  строки используют существующие переводы; профильные проверки React/antislop выполнены.

Browser env: `RECORDS_TOOLBAR_URL=http://127.0.0.1:49671`,
`RECORDS_TOOLBAR_ISOLATED=1`; backend49669, отдельная SQLite records-toolbar.sqlite3,
synthetic fixtures, safe_environment, внешний socket-доступ backend запрещён.
Обычная база/dev-серверы не использовались для тестовых записей.
Первый bootstrap завершился ошибкой fixture slug после переноса runner; исправлен
только fixture path/slug, лог fixture-initial-failure.log сохранён. Первый вызов
обёртки build не стартовал сборку из-за отсутствующих аргументов портов; исправлен,
итоговая сборка exit0. Продуктовых/браузерных падений в этом цикле нет.
Полный backend/E2E, PostgreSQL и live-сертификация не запускались: серверные
контракты не менялись, задача — ограниченный frontend-поток.

Изолированные backend/frontend49669/49671 остановлены после проверки command line
и владельцев портов; обычные dev-серверы сохранены. Итоговые source hashes, whitespace,
ссылки отчёта, JSON registry и docs diff hygiene PASS.

## Доказательства и остаток

[Desktop](records-toolbar-20261103-assets/desktop.png),
[mobile](records-toolbar-20261103-assets/mobile.png),
[окно фильтров](records-toolbar-20261103-assets/filters.png),
[хеши исходников](records-toolbar-20261103-assets/source-manifest.json).

В принятом scope остатка по коду/проверкам нет. Publication заблокирована ранее
существовавшим `.git/index.lock` и незакоммиченными prerequisites: RecordsPage и
recordFilters целиком отсутствуют в HEAD. Чужой WIP не включался в staging;
commit/push/новый CI/deployment не выполнялись. Это локальная реализация, не release.
Frontend-контракт, scheduling passport и текущий checkpoint обновлены.
README/CRM/access/AI/integrations/operations/roadmap acceptance не требуют изменения:
setup/API/права/домен/операции/этапы остаются прежними; здесь закрыты только четыре
UI-находки аудита, не полный R01 и не новый этап roadmap.
