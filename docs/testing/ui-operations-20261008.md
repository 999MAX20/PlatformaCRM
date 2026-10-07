# UI-OPERATIONS-20261008 — операционные экраны

Авторизован весь пакет аудита: Заявки, Сделки, Календарь, Сообщения,
Настройки и Главная. Canonical root `C:/Users/user/Desktop/PlatformaCRM`,
branch `codex/ui-testing-toolkit`, исходный clean HEAD
`79ffca5c2b4437750bb7559ce34453ab6c247a29`, тот же generation 4 primary.
Проверен task-owned dirty snapshot; итоговый commit/push/CI — в публикационном
receipt и ответе задачи. [Контракт задачи](task-state/PRIMARY-SESSION.md).

## Реализованный результат

| Экран | Изменение и проверяемое поведение |
| --- | --- |
| Заявки | Одна create CTA, один вход в фильтры возле поиска, правильно названный импорт в дополнительных действиях. Нет пустых checkbox/pagination. No-data, filter-empty/reset и ошибка/retry различаются. Компактная форма сохраняет все поля и создаёт реальную заявку. Русская терминология — «Заявка». |
| Сделки | Высокий риск называется «Требуют внимания» без смены risk model. Заданный `next_action_at` отображается как следующий шаг и не попадает в no-step filter. У пустой стадии своя подпись. Улучшена иерархия заголовка, клиента, суммы и действия; kanban сохранён. |
| Календарь | Стрелки учитывают day/week/month, заголовок показывает соответствующий период, выбранный режим доступен через aria-pressed. Пройдены переходы года, 31-е число и високосный февраль. |
| Сообщения | Одно согласованное пустое состояние, filter-empty/reset, читаемые селекты, разные owner/AI-agent labels, иконка фильтра и количество условий. Панели заполненного диалога не обрезаются на десктопе; черновик, pause/resume, ручное назначение и история сохраняются. |
| Настройки | Четыре группы существующих полей: профиль/контакты, записи, финансовые реквизиты, оформление. Черновик сохраняется между группами и при ошибке сервера; validation раскрывает/фокусирует поле. Сохранение подтверждено чтением API и reload. Expansion соответствует видимости; проверен keyboard и axe для профиля. |
| Главная | Четыре scoped операционных счётчика, полные distinct totals отдельно от preview, очередь конкретных действий и ближайшие записи. Финансы — net receipts с source/period/freshness/no-data; AI summary только с источниками, команда вторична. Нет broad daily-list preload и ошибочной подстановки нулей при failure/403. |

Серверная часть добавляет read-only агрегаты и устраняет возврат неназначенных
сущностей отключённого/запрещённого модуля. Неверный business ID даёт 400.
Пересечение unread/handoff и SLA/no-step не удваивает сущности. День считается
в timezone бизнеса, порядок и предел preview детерминированы. Backend regression
выполнена до зависимого UI. Никаких новых lifecycle, денег, назначения прав,
notification/BusinessEvent, AI-политик, схем или миграций.

## Проверки и среда

Все backend/browser запуски используют `scripts.codex_verify.isolated_runtime`:
одноразовые SQLite, media, loopback-порты, test accounts и mock providers;
обычная БД и существующие серверы не использованы. Установленные зависимости
переиспользованы, lock files не менялись. Команды из canonical root, кроме Node/npm
(рабочая папка `frontend`). Локальные логи/скриншоты в
`output/ui-operations-20261008/`; helpers — оболочки штатной изоляции, не новая среда.

```powershell
.venv/Scripts/python.exe output/ui-operations-20261008/verify.py apps.core.tests_work_queues apps.core.tests_b301_performance apps.businesses.tests_access apps.bots.tests_automatic_booking apps.bots.tests_customer_safety apps.bots.tests_safety_recovery
```

**78 tests PASS**, `check` PASS, `makemigrations --check --dry-run` без изменений.
Лог `backend-1791411501420078900.log`. Покрыты counts beyond limit, dedupe/order,
business-day boundary, tenant/roles/capabilities, invalid input, bounded queries,
AI booking/safety/recovery. Work queues: 58 queries на scale fixture — установленный
budget не повышался. Это SQLite evidence, не нагрузочная приёмка PostgreSQL.

```powershell
node --test scripts/tests/calendar-period.test.mjs scripts/tests/dashboard-appointment-dedupe.test.mjs scripts/tests/daily-workspaces-policy.test.mjs
```

**9 PASS**: календарная арифметика/локали, dedupe, актуальные permission/loading/
grounding guards. Старые source-pattern assertions обновлены под общий операционный
компонент; runtime-права отдельно проверяются backend и браузером.

```powershell
.venv/Scripts/python.exe output/ui-operations-20261008/verify_frontend.py
```

`npm run build` (i18n, TypeScript, app/widget) и `npm run check:bundle` **PASS**
в изолированном Vite environment, лог `frontend-isolated-final.log`.
Сам helper после успешных child commands завершился ошибкой вывода Unicode в
cp1251; проверен полный лог двух успешных команд, кодировка вывода helper исправлена.
Продуктовую сборку без причины повторно не запускали.

## Браузерные сценарии

Runner: `.venv/Scripts/python.exe output/ui-operations-20261008/verify_ui.py`
с параметрами ниже. Каждый запуск — собственные DB/порты, Chromium, один worker,
без retries и внешней отправки. Общий `--grep-invert=channel forms` не исключает
ни один из перечисленных сценариев. Fail-fast: `--max-failures=1`.

| Project / spec / grep | Результат и лог |
| --- | --- |
| desktop-chromium, ui-operations.spec.ts | Календарь PASS в `browser-1791410919046866000.log`; после уточнения селекторов Заявки/Сделки/Inbox PASS в `browser-1791411130254583700.log`; Settings/Inbox/Dashboard 3 PASS в `browser-1791411381885687000.log` |
| mobile-chromium, ui-operations.spec.ts | Все 6 PASS, `browser-1791411479584303500.log` |
| desktop-chromium, ui-operations + dashboard-data-loading + daily-workspaces + inbox-agent-safety, grep `business settings\|operational summary\|financial failure\|manager uses\|denied operational\|desktop roles\|Inbox pause` | 7 PASS, `browser-1791411627408797200.log`: пять ролей, failure/retry, 403, no list preloads, настройки/expansion, AI limit/manual controls |
| mobile-chromium, daily-workspaces + inbox-agent-safety + merchant-journeys-certification + smoke, grep `mobile owner, manager\|Inbox pause\|ZD-015\|owner summary omits` | 4 PASS, `browser-1791411750725061100.log`: роли/tenant-boundary в UI, AI recovery, бизнес-день, dedupe записей |
| tablet-chromium, ui-operations.spec.ts, grep `dashboard distinguishes\|Inbox empty` | 2 PASS, `browser-1791411858482673000.log`: пустой/заполненный Inbox и Главная, ошибки/восстановление, ширина 1024 px |

Визуально просмотрены реальные screenshots тестового интерфейса: компактная форма,
календарь, Настройки, пустой/заполненный Inbox, Главная. Desktop 1280 px, tablet 1024 px и mobile
Pixel 7, RU/KK/EN для периода/пустой Главной; keyboard и горизонтальный overflow
проверены в затронутых сценариях. Axe профиля — без нарушений; это не полная
ручная screen-reader сертификация. Данные на снимках исключительно test fixtures.

## Сохранённые ошибки и ограничения

- Начальная backend regression была красной до реализации. Первая реализация
  превысила budget (63 вместо 58 queries); переиспользование загруженных preview
  устранило лишние запросы. PASS после исправления, лимит не ослаблен.
- Первая сборка обнаружила неправильный порядок i18n spread, вторая — отсутствующий
  в текущем TS lib `Intl.formatRange`; обе ошибки исправлены. Финальный build PASS.
- Первые UI-запуски выявили неточные accessible-name селекторы (подсказка клиента,
  validation text логотипа). Уточнены селекторы, сохранены бизнес-проверки. По
  screenshot заполненного Inbox также исправлена минимальная ширина средней панели.
- Сборка, ошибочно запущенная с обычным process environment, заменена проверкой
  через штатную Vite-изоляцию; её результат не использован как финальный gate.
- Полный E2E/полная функциональная сертификация не запускались: scope — этот пакет.
  Нет новых paid AI calls, внешних сообщений, deployment, working-DB migration,
  dependency install или изменения процессов другого пользователя.
- Общие FC/manual/clinical/production обязательства в [acceptance](../current/acceptance.md)
  остаются открытыми. Следующий продуктовый этап не назначен.
