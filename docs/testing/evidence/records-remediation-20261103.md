# RECORDS-REMEDIATION-20261103

Исправлены девять замечаний [компонентного аудита](records-full-audit-20261103.md)
и переработан календарь выбора периода «Записей». Отдельный redesign страницы
«Календарь» не выполнялся: календарь в этом цикле — общий компонент выбора даты/диапазона.
Его существующий потребитель на странице календаря проверен отдельно.

## Результат

Период раскрывается под компактной строкой фильтров, без модального окна, backdrop
и блокировки страницы. Общий DateRangePicker показывает диапазон, быстрые периоды,
месяц/год и поддерживает клавиатуру. Первый клик задаёт начало, второй — конец;
обратный порядок упорядочивается. До «Применить» URL и выборка не меняются.
Отмена/Escape сохраняют прежний период и возвращают фокус. Месяц/год читаются на320px.
Фон inline-календаря наследует поверхность; footer фильтров совпадает с фоном окна.
Однострочная панель и её мобильная горизонтальная прокрутка сохранены.

[Desktop RU](records-remediation-20261103-assets/period-ru.png),
[mobile KK](records-remediation-20261103-assets/period-kk.png),
[mobile EN320](records-remediation-20261103-assets/period-en.png).

| Дефект | Изменение и подтверждение |
| --- | --- |
| RF-01 | Карточка использует существующие backend available_action_details с object/TEAM/branch проверками; новая модель прав не вводится. Browser TEAM видит5 команд, viewer0 |
| RF-02 | Список и план передают локальный return context; карточка возвращает query/page. Helper отвергает внешние/чужие маршруты; Node+browser page2 |
| RF-03 | Синхронные pending refs закрывают гонку быстрого Escape; крестик/отмена переноса не закрывают активный запрос. После ухода успешный ответ не захватывает страницу. Retry сохраняет idempotency key; проверены реальные isolated create и 503 |
| RF-04 | Workspace404 при page>1 возвращает на первую с остальными условиями. Первая страница и permission/network ошибки сохраняют прежние recovery состояния |
| RF-05 | Поиск debounce300мс, replace истории; прежние строки остаются на время запроса только внутри того же actor/Business. Browser: один запрос для быстрого Audit, Back не перебирает буквы |
| RF-06 | Shortcut графика требует SETTINGS UPDATE, ссылка — VIEW; без прав предлагается другая дата/специалист. RU/KK/EN новый ключ, backend guards прежние |
| RF-07 | Direct create URL планов проверяет canCreate; viewer не получает форму. Остальные команды остаются под plan.can_change и серверными проверками |
| RF-08 | Столбец филиала появляется только при настроенных branches, в обычном бизнесе скрыт. Используется тот же признак branch mode, что и форма |
| RF-09 | Внутренний EntityWorkspaceMain стал div; в Appointment и репрезентативном Client workspace остаётся один main |

Дополнительно обнаружена гонка сохранения периода: быстрый уход после reset успевал
изменить URL, но прерывал commit/effect записи sessionStorage. Диагностический trace
зафиксировал push Today без save перед уходом. Единый setter теперь сохраняет период
синхронно до URL-перехода; три последовательных быстрых сценария прошли. Восстановление
plain URL и first-query gate сохраняются, явные client/attention ссылки не переопределяются.

## Версия и проверки

Canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
HEAD `e02a28f550e94a543c3d88acac7c1b19ee48f90b` + WIP.
[Хеши проверенных файлов](records-remediation-20261103-assets/source-manifest.json).
Before, starting-status, PLAN, own-only patch и журналы:
`output/records-remediation-20261103`. Старый общий dirty diff не приписывается задаче.

- `node --test frontend/scripts/tests/record-filters.test.mjs`: **8 PASS**.
- 11 уникальных scoped browser-сценариев исправлений: TEAM/viewer/creator,
  return/page/search, inline RU/KK/EN, create pending/retry/late success,
  shared Calendar/Client, reschedule pending/error — **PASS** в последних применимых запусках.
- Существующие6 Records read/bell recovery RU/KK/EN — **PASS**;
  обновлённые3 toolbar + remembered-period — **PASS** после исправления persistence.
  Дополнительный repeat-each3 подтверждает быстрый reset→уход→возврат.
- Playwright: `node frontend/node_modules/@playwright/test/cli.js test --config output/records-remediation-20261103/playwright.config.cjs`, сфокусированные `--grep`;
  существующие — `--config frontend/playwright.records-toolbar.config.ts` с
  `RECORDS_TOOLBAR_URL=http://127.0.0.1:57694` и `RECORDS_TOOLBAR_ISOLATED=1`.
  Outputs/логи `browser-initial`, `browser-depth`, `browser-pending`,
  `browser-completion`, `browser-reschedule-final`, `browser-reset-persist`,
  `browser-storage-final`, `browser-toolbar-final`, `browser-regression` сохранены.
- `.venv/Scripts/python.exe output/records-remediation-20261103/build.py` запускает
  `npm run build` в safe_environment: **types/i18n6667/app/widget PASS** на финальном коде.
  Предыдущие сборки сохранены; финальная повторена после исправления найденной гонки.
- Docs: собственные diff/new-file/links/JSON/whitespace проверены. Исходники backend
  не менялись: прежние56 focused backend PASS остаются только в границе аудита,
  новой серверной сертификации/PG/fullE2E/migration checks не заявляется.

Промежуточные неуспехи сохранены: TS optional previousQuery исправлен; быстрый Escape
показал реальную гонку pending, устранённую ref; первый late-navigation тест сравнил
промежуточный `/app` с redirect `/app/dashboard` — заменён реальным SPA Back;
reschedule option имеет диапазон `10:00 - 10:30`, диагностический selector исправлен.
Reset initially flaky, layout effect alone не помог; trace привёл к synchronous setter.
Итоговые утверждения опираются на последующие проверки, а не на эти неуспешные попытки.

Две disposable SQLite и canonical dev-процессы:61588/61589 (расширенная fixture) и
57693/57694 (прежние3 строки). Mock AI/eager, outbound блокирован, отдельные media;
обычная БД/действительные клиенты/уведомления/провайдеры не изменялись. Схема, API,
домен, BusinessEvent и AI не менялись. Проверено Chromium, не все браузеры/дикторы/
production workers. Полный R01, деньги и D01 этим циклом не закрываются.

## Документы и публикация

Frontend-контракт и scheduling passport описывают новый поток; STATUS/PRIMARY/registry
согласованы. README/CRM/access/AI/integrations/operations/roadmap requirements не требуют
изменений: правила бизнеса, API, setup и этап roadmap не менялись. Аудит сохранён как
исторический срез; данный отчёт закрывает RF-01–09 в названной локальной границе.

Существующий `.git/index.lock` и смешанные незакоммиченные prerequisites блокируют
own-only публикацию. Ничего не staged/committed/pushed; нового CI/deployment нет.
В принятом объёме кода/локальной проверки остатка нет; публикационный блокер остаётся.

Финальная сверка: все хеши source-manifest совпадают. Собственные временные процессы
8708/7296/12652/9648 остановлены после проверки command line/root/ports; обычный dev
не остановлен. Индекс пуст, существующий index.lock сохранён.
