# RECORDS-SINGLE-ROW-20261103

## Причина пустого списка и результат

В браузере была открыта `/app/appointments` без query-параметров: период по умолчанию
03.11.2026. Ранее владелец разрешил десять демонстрационных записей на04.11.2026;
они сохранились, но не попадали в выборку за сегодня. Повторного создания/переноса
данных не было. После выбора04.11 реальный dev показал10 строк.

Выбранный явный период запоминается в sessionStorage отдельно для actor/Business.
При переходе на чистый URL списка, включая повторный клик текущего меню, даты
восстанавливаются в URL до запуска запроса списка. Это память текущей вкладки;
первый визит без сохранённого периода остаётся за сегодня. Явные URL, client/attention/
create-сценарии не получают скрытый дополнительный период. Общий сброс фиксирует
сегодняшние from/to, заменяя сохранённый выбор. Невалидный диапазон не сохраняется;
недоступное браузерное хранилище не ломает URL-фильтрацию.

Шапка реализована по одобренному однострочному референсу: поиск → период →
выпадающие статусы со счётчиками → дополнительные фильтры → переключатель порядка →
сброс → календарь/планы. Вторая строка статусов/chips удалена; счётчик дополнительных
условий и доступ к ним остаются на кнопке фильтров. Специалист/ответственный/
подтверждение/филиал и client/attention редактируются в черновике окна, применяются
одной операцией. На телефоне прокручивается только панель, не вся страница.
Shared primitives/API/backend/права/схема/уведомления/AI не изменялись.

## Проверки и версия

Каноническая PlatformaCRM, `codex/ui-testing-toolkit`, HEAD `e02a28f5` + сохранённый WIP.
План, before, исходный Git snapshot, логи и owned.patch —
`output/records-single-row-20261103`. Исходная граница —
[предыдущий цикл](records-toolbar-20261103.md), новая правка явно разрешена владельцем.

- `node --test frontend/scripts/tests/record-filters.test.mjs`: **7 PASS** —
  даты/exclusive end, клиент/attention, invalid date, patch/reset, только даты в
  сохранённом периоде, явный сброс заменяет прежний период сегодняшним.
- Browser: `RECORDS_TOOLBAR_URL=http://127.0.0.1:58035`, `RECORDS_TOOLBAR_ISOLATED=1`;
  `node frontend/node_modules/@playwright/test/cli.js test --config=frontend/playwright.records-toolbar.config.ts --grep 'records toolbar|remembered period respects|records real' --output=output/records-single-row-20261103/final-results`.
  Итог: **7 PASS** (browser-final.log). Проверяются RU/KK/EN, заполненный список,
  search/status/sort, draft/cancel/apply/reset, reload/back/forward, Escape/focus,
  mobile390×844 и desktop1440, отсутствие переполнения страницы, диапазон и даты,
  возвращение периода после ухода со страницы/повторного меню, сброс и drilldown,
  400/403/404/503/retry. До уточнения same-route reset: scoped3+4 PASS; этот старый
  срез не подменяет финальный прогон после правки.
- `npm run build` через `scripts.codex_verify.safe_environment`: types/i18n/app/widget.
  Первичная сборка PASS; финальная выполнена после уточнения same-route/reset,
  итог **PASS / exit0** (build-final.log). Новых переводов нет; используются текущие6666 ключей RU/KK/EN.
- Реальный Chrome dev5173:10 записей на04.11; после Клиенты → Записи и повторного
  клика по текущему разделу URL сохраняет from/to04.11 и таблица содержит10 строк.
  Панель48px, scrollWidth=clientWidth1392 на данном viewport. Сохранены screenshots.
  Один full-page capture timeout; обычный viewport screenshot успешно сохранён.

Изолированный backend58034, frontend58035 запущены из canonical root; повторно
использована неизменённая synthetic SQLite предыдущего scoped-цикла, без повторного
seed/install. Backend wrapper запрещает внешние socket-запросы. Рабочая БД не менялась.
Backend/PG/full-project E2E не требовались: изменён ограниченный frontend-поток.

## Доказательства и публикация

[Реальный dev с10 записями](records-single-row-20261103-assets/actual-records.jpg),
[mobile](records-single-row-20261103-assets/mobile.png),
[хеши исходников](records-single-row-20261103-assets/source-manifest.json).

Публикация остаётся заблокирована существующим index.lock и prerequisite WIP;
RecordsPage/Toolbar/filter источники ещё не входят в HEAD. Нет staging, commit,
push, нового CI или deployment. Обновлены действующий frontend-контракт и scheduling
passport. README/CRM/access/AI/integrations/operations/roadmap acceptance не меняются:
домен/API/права/setup/этапы не затронуты; это согласованная UI-дельта, не закрытие R01.

В согласованном scope остатка по коду и доказательствам нет. Финальные source hashes,
JSON registry, ссылки отчёта и diff hygiene проверены; предыдущие отчёты не переписаны.
Изолированные backend58034/frontend58035 остановлены после проверки command line и
владельцев портов; обычные dev5173/8000 сохранены.
