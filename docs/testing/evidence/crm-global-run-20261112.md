# Общая функциональная проверка CRM — 12.11.2026

Task: `CRM-GLOBAL-RUN-20261112`. **Отчёт подготовлен; общая приёмка НЕ PASS.**

Обновление12.11: все F01–F10 ниже исправлены и адресно проверены отдельной
задачей [CRM-GLOBAL-FIXES](crm-global-fixes-20261112.md). Таблица сохраняет исходные
воспроизведения; их текущий статус — FIXED / scoped local verification PASS.
Семь других неуспешных методов, три дополнительных наблюдения, непокрытые
варианты матрицы и S04/load остаются открытыми. Общий аудит не стал full PASS.

[48 браузерных сценариев и все204 ID матрицы](crm-global-run-20261112-coverage.md),
[100 route declarations](crm-global-run-20261112-routes.md),
[точные результаты backend test methods](crm-global-run-20261112-tests.json).
Это полный отчёт о выполненном запуске с открытыми границами, а не утверждение,
что все варианты согласованного плана выполнены. Покрытие матрицы частичное;
неатрибутированные варианты явно оставлены NOT PROVEN.

Поручение: выполнить согласованный [план](../crm-global-plan-20261111/README.md),
функциональные тесты и пользовательский прогон через «Компьютер» в изоляции,
без реальных отправок; ошибки пока не исправлять. Продуктовый код и тестовые
assertions в рамках аудита не изменялись. Изменения других задач не присваиваются.

## Снимок и среда

Канонический checkout `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, исходный HEAD
`00f575e95f85da088ffb9ffc943cd8d4c3d1192e` с сохранённым чужим dirty diff.
Это проверка составного рабочего снимка, а не чистого release commit.
Хеши исходников до/после SQLite, PostgreSQL, frontend и dependency checks совпали;
финальная сверка также не обнаружила изменений этих входов.

Автотесты: одноразовые SQLite и PostgreSQL; браузер: отдельная SQLite,
API `127.0.0.1:64707`, frontend `127.0.0.1:64708`, mock AI/transport/card,
FakeClamd и отдельные имена cookies. Браузерные действия выполнялись через
«Компьютер»; SQL/API-readback и подготовка fixtures обозначаются отдельно.
Рабочая БД, `.env`, рабочие каналы и deployment не изменялись.

Браузерный набор: Business1 для основного дня, Business2 с контрольной чужой
записью, новый Business3 после регистрации владельцем. Проверялись owner,
manager, operator, specialist, custom read-only, platform admin и anonymous.
RU desktop, KK mobile390, EN desktop; отдельные формы320 и календарь1024.
Это не подтверждение каждого маршрута во всех сочетаниях ролей/локалей/размеров.

## Автоматизированные результаты

| Слой | Фактический результат | Граница |
| --- | --- | --- |
| Полный Django/SQLite | 3329: 3249 PASS, 3 FAIL, 2 ERROR, 75 SKIP | SKIP требуют PostgreSQL; проблема общего лога описана ниже |
| Адресное воспроизведение SQLite | 13: 8 PASS, 3 FAIL, 2 ERROR | Те же пять неуспешных методов, отдельный вывод |
| PostgreSQL, первый набор | 284: 283 PASS, 1 FAIL | Реальные транзакции и блокировки |
| PostgreSQL, недостающий coexistence-модуль | 4 PASS | Все 75 SQLite SKIP теперь имеют PG PASS по точным test IDs |
| Frontend Node | 306: 304 PASS, 2 FAIL | Реестры fallback/маршрутов не актуальны |
| Build, TypeScript, i18n, bundle budget | PASS | Без повторной установки зависимостей |
| Django system / migration drift | PASS | Изолированные БД; рабочие миграции не применялись |
| pip-audit / npm audit | PASS | Результат текущего запуска, не гарантия отсутствия любых уязвимостей |
| PostgreSQL/Redis/Celery recovery S04 | FAIL на проверке reminder status | Предшествующие restart/rollback/reclaim/retry/tenant-denial шаги PASS; последующие шаги не объявлены PASS |

SQLite первоначально был ошибочно запущен дважды собственными harness-процессами
после восстановления контекста. Базы были раздельными, но выходные файлы общими.
Старший запуск остановлен; завершившийся runner сообщил3329 методов. В журнале5582
строки,3329 уникальных test IDs,2253 повторов и ни одного противоречивого статуса.
Числа выше сверены с итогом runner, а не суммированы по строкам. Чистая атрибуция
каждого события одному запуску отсутствует. Исходные логи сохранены; это ограничение
не скрыто и не превращено в «чистый full gate».

## Подтверждённые проблемы исходного запуска

Приоритет дефекта отделён от приоритета тестового сценария. В проверенных вариантах
не обнаружено чужих записей, несанкционированной записи или нарушения суммы возврата;
это не доказательство отсутствия таких ошибок во всех возможных путях.

| ID | Приоритет | Наблюдение и воспроизведение | Доказательство / участок |
| --- | --- | --- | --- |
| F01 | P1 | Архивный клиент остаётся в архивной выборке, но карточка и отдельная страница возвращают ошибку; обычный путь восстановления через карточку недоступен | Client4: default detail/card404, с include_archived200; `crmCardsApi.get` не передаёт этот параметр; B12 |
| F02 | P1 | Поиск имени с цифрами расширяется до телефонного совпадения: `QA Pagination 01` возвращает84 клиента вместо одного буквального совпадения | `read-probes.json`; `apps/clients/selectors.py`, нормализация phone и OR; B10 |
| F03 | P2 | Доменный409 показан как «Данные изменились», хотя обновление не устраняет причину: последний филиал, активная работа клиента/плана, конфликт расписания | B06/B12/B18/B19 и Branch3; `last-branch-conflict.jpg`; общий error mapping |
| F04 | P2 | Полная страница клиента показывает RO действия редактирования/тегов/архива; попытка сохранения заканчивается отказом | B04, `readonly-ui-readback.json` подтверждает отсутствие изменения; `ClientWorkspacePage.tsx` |
| F05 | P2 | После отмены записи во второй вкладке перенос корректно получает409, но «Обновить» обновляет revision/слоты без обновления текущей карточки и статуса | Appointment8 остаётся cancelled17:00; нет reschedule event; `AppointmentRescheduleForm.tsx` |
| F06 | P1 | Widget после reload теряет историю и создаёт новую беседу тому же visitor | Conversation2→3; visitor ID сохраняется, conversationId только в памяти; `frontend/widget/src/index.ts` |
| F07 | P2 | Widget очищает отправляемый текст до ответа; при ошибке канала нет сохранённого draft/Retry | При выключенном тестовом канале запись не создана; после ручного повторного ввода сохранена один раз; B37 |
| F08 | P2 | Успешная смена пароля заканчивается Session ended несмотря на выдачу сервером replacement cookie | POST200→sessions401→refresh200→login; `AccountPage.tsx`, `token.ts` сравнивает старый и новый device-session ID; пользователь затем успешно вошёл |
| F09 | P1 | Повторный seed/reset демонстрационного бизнеса падает на ProtectedError Branch.business→ScheduleDay | Два ERROR полного и focused suite; `seed_pilot_demo.py:127`; подготовка демо не завершается |
| F10 | P2 | Системные тексты и даты не полностью локализованы: английские follow-up задачи в RU, русские системные шаблоны/роль/даты в KK/EN, технические имена в audit/automation | B15/B29/B40/B46/B48; это системные значения, а не введённые пользователем названия |

Другие наблюдения требуют отдельной классификации перед исправлением: время в
тексте appointment activity отличается от локального времени записи; retry Inbox
показывает success toast при последующем failed; отдельные timeline details не
показывают old/new values и называют источник недоступным. Раннее предположение
о постоянно устаревших counts клиента не подтвердилось: после завершения fetch
counts обновились. Оно не включается в подтверждённые дефекты.

## Неуспешные проверки, отличные от продуктовых дефектов

- `AICoreFoundationTests.test_ai_assistant_status_reports_configured_provider`:
  fixture задаёт KIMI key/model, но изоляция оставляет KIMI base URL пустым;
  текущая readiness проверяет оба значения. Исходный FAIL сохранён.
- `VoicePlannerWireTests.test_default_voice_route_and_field_plan_use_json_and_execute_once`:
  ожидается completed, фактически awaiting_confirmation. Текущий контракт11.11
  требует review нового голосового клиента. Это несогласованное старое ожидание,
  а не разрешение убрать подтверждение.
- `InitialLocationMigrationTests.test_backfill_preserves_archived_locations_and_reverse_keeps_bookable_history`:
  ожидается uses_business_defaults=true после всех leaf migrations; branches0006
  переводит филиалы в явные настройки. FAIL остановил метод до последующих reverse
  assertions; эти assertions в этом методе не считаются проверенными.
- PostgreSQL `PlatformDashboardTests.test_platform_users_can_open_overview_and_merchants`:
  строка `9900.00` вместо `9900`. Числовое значение одинаково, но межбазовый контракт
  представления и тестовое ожидание расходятся; исходный FAIL остаётся.
- Node fallback inventory: отсутствует policy API-модуля `management`.
- Node functional certification registry: отсутствуют `business/company` и
  `business/staff`. Текущий router имеет100 declarations против98 в исходном плане.
- S04 reminder replay ожидает Notification.status=sent. Диагностика обнаружила
  ровно один TaskReminderDelivery и одну SYSTEM Notification в pending;
  текущий delivery исключает SYSTEM из внешнего транспорта. Это не live delivery
  и не PASS первоначального assertion. Следующие broker-loss/restore шаги не выполнены.

## Данные и восстановление

Readback подтвердил receipt100.00/refund30.00/refund70.00/net0; лишний возврат
отвергнут. CSV20 строк импортирован с точным совпадением полей; повтор дал20unchanged
без новых клиентов. Invalid CSV: исправленная строка создана, исключённая не создана.
Автоматизация создала одну связанную задачу; после offline recovery клиента86
ровно одно событие изменения. Отмена Appointment8 во второй вкладке не позволила
сохранить устаревший перенос. Чужой sentinel65 не изменён и недоступен.

Новый Business3 создан пользователем ровно с одним owner/membership и одним
обычным филиалом. Пустой dashboard после reload не показывает чужие данные.
Добавленный Branch4 и Service5 прошли archive→restore; restore оставил их
неактивными согласно текущему контракту. Последний активный Branch3 защищён.
MFA подключена владельцем; неверный код отвергнут, корректный вход состоялся.
Пароли, QR и recovery codes агент не собирал.

## Нагрузка и ограничения среды

Для нагрузки создан новый одноразовый кластер PostgreSQL и чистая мигрированная
схема, без чтения dump рабочей БД. Набор:10 synthetic Business,330 пользователей,
250 клиентов,120 записей,120 сделок,100 исходных задач; API1worker, отдельные Redis/Celery.

| Этап | Запросов/с | p95 | Ошибки | Доступная RAM минимум |
| --- | ---: | ---: | ---: | ---: |
| Warmup2,15с | 3.73 | 1417мс | 0% | 257МБ |
| 1пользователь,60с,think1с | 0.75 | 803мс | 0% | 116МБ |
| 5пользователей,60с,think1с | 3.35 | 1414мс | 0% | 181МБ |

Записанные задачи совпали с числом201 в завершённых ступенях. На ступени10
прогон остановлен из-за дефицита RAM.180с подтверждение,4workers и большой набор
не выполнены. Один краткий PASS не подтверждает ёмкость или production SLA;
условие спокойной среды не выполнено. Чужие процессы не останавливались.

Реальные AI/ASR, микрофон, YCloud/прочие provider receipts, банковские платежи,
SMTP delivery и production в этот запуск не входят. FakeClamd не доказывает
работу реального AV; имеющиеся сигнатуры устарели. Human screen reader не проверен.
Browser download API дал timeout; API200 выдачи файла не принят за доказательство
получения файла пользователем. Служебную страницу Downloads инструмент отклонил;
обход не предпринимался. Непроверенные варианты и маршруты перечислены в приложениях.

## Артефакты и завершение

Подробные локальные журналы: `output/crm-global-run-20261112/`:
`CHECKPOINT.md`, `sqlite-reconciled.json`, `sqlite-unique-tests.json`, `pg-unique-tests.json`,
`pg-remaining/`, `frontend-run.json`, `browser-observations.json`, `route-ledger.json`,
`http-metadata.json`, `final-readback.json`, `read-probes.json`, `load/`.
792 сохранённых текстовых наблюдения браузера не равны792 успешным сценариям;
loading/error/повторные наблюдения остаются в журнале.

Основной браузерный runtime остановлен, disposable SQLite удалена; его порты
закрыты. Нагрузочные процессы и собственный PostgreSQL остановлены, порты закрыты.
Рекурсивное удаление двух нагрузочных temp-каталогов отклонено автоматической
проверкой безопасности: `blocked by policy`; каталоги оставлены, обхода нет.
Их точные пути записаны в `load/cleanup.json`.

Продуктовые исправления, release acceptance и deployment не выполнялись.
Документационные проверки и Git-граница зафиксированы ниже; ошибки приложения
остаются результатом аудита и не заменяются зелёной проверкой Markdown.

## Команды и воспроизводимость

Команды выполнялись из канонической папки, Python — `.venv/Scripts/python.exe`.
Локальный harness в `output/crm-global-run-20261112/` использует
`scripts.codex_verify.isolated_runtime`; backend child запрещает чтение `.env`
и внешние socket connections. PostgreSQL suites используют отдельные test DB;
нагрузка — отдельный temporary PG cluster. Рабочие данные не очищались.

```text
.venv/Scripts/python.exe output/crm-global-run-20261112/run.py sqlite
.venv/Scripts/python.exe output/crm-global-run-20261112/run.py pg <modules from pg-modules.json>
.venv/Scripts/python.exe output/crm-global-run-20261112/run.py frontend
.venv/Scripts/python.exe output/crm-global-run-20261112/run.py audits
.venv/Scripts/python.exe scripts/verify_recovery_s04.py --phase queue
.venv/Scripts/python.exe output/crm-global-run-20261112/load_run.py
```

Focused reproducer и дополнительный PG-модуль используют отдельный
`GLOBAL_AUDIT_OUTPUT`; точные аргументы сохранены в соответствующих `*-run.json`.
Последний PG-модуль: `apps.integrations.tests_ycloud_coexistence_concurrency`.
Frontend stages: `node --test scripts/tests/*.test.mjs` (раскрытый список файлов),
`npm run build`, `npm run check:bundle`; build включает types/i18n.
Audits: `python -m pip_audit -r requirements.txt`, `npm audit --audit-level=moderate`.
System/drift: `call_command('check')`,
`call_command('makemigrations', check=True, dry_run=True)` внутри изоляции.
Load остановлен намеренно по RAM; это не PASS команды или всей нагрузочной матрицы.

Профильные контракты/roadmap/паспорта не менялись: аудит не меняет поведение,
разрешения, схему или acceptance. План получил ссылку на фактический запуск;
статический inventory11.11 сохранён как исходный срез.

Docs checks: `git diff --check`, `git diff --cached --check` — PASS;
`python output/crm-global-run-20261112/finish_docs.py` — PASS для локальных ссылок,
JSON/registry,48/204 IDs, точных test totals и credential-pattern проверки.
Новые файлы содержат только результаты и имена test methods, без browser sessions,
паролей или полных HTTP payloads. Неуспешная первая попытка индексировать mixed
документы была вызвана CRLF patch; после нормализации LF patch применён успешно.
Чужие рабочие изменения в STATUS/PRIMARY/registry не включены в собственный commit.

Публикация: после fetch `origin/main` = `1cec6af1596264cd5679cc62ab9880dec3c65d24`.
Перед собственным docs commit ветка содержала55 чужих/смешанных outgoing commits.
Normal push опубликовал бы их вместе с отчётом и поэтому не выполнялся.
Нового push-triggered CI/deployment нет; локальные тесты не называются CI.
