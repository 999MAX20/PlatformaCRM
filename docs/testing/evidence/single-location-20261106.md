# Одна точка, несколько филиалов и голосовая запись — 06.11.2026

Поручение владельца: автоматическая точка без лишней настройки для одного адреса;
явный выбор и настройка нескольких; конкретные сообщения голосового помощника;
запрет архивирования последнего действующего филиала. Это согласованная дельта
CRM-MB01/D01, а не повторный аудит или полная production-приёмка.

Код: канонический `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, HEAD `66101d509cb7642b2928275e48c4b64354abf07b`
и выделенный локальный diff. Во время закрытия другой исполнитель добавил commit
`219043dc` (dev launcher); его commit не относится к этому результату. Начальный snapshot, собственный patch и hashes —
`output/single-location-20261106`; чужой WIP сохранён. Рабочая схема к концу проверки уже обновлена вне этой задачи;
здесь её итог проверен только чтением.

## Поведение

- Signup/social activation/Business API создают основную точку под Business lock.
  Миграция добавляет точку существующему Business только при полном отсутствии
  Branch; существующие явные и архивные филиалы сохраняются.
- Автоматическая точка использует обычные Service/Resource/WorkingHours и
  персональные исключения. Нет повторной настройки каталога. Новые услуги и
  специалисты доступны без BranchService/SpecialistBranch. Реквизиты следуют Business.
- При создании второй точки настройки первой материализуются атомарно; сохраняются
  история, часы, исключения и доступ. Вторая точка начинает с пустой конфигурации.
- Единственный допустимый филиал подставляется при записи. Для нескольких
  используется явный выбор; настройка проходит в существующем разделе Бизнес.
- Последнюю активную точку нельзя архивировать через API или обход с паузой.
  Параллельное архивирование сохраняет активную точку; ограничения будущих визитов
  остаются. Пауза и явное возобновление не отменяют визиты.
- Голос различает недействующий/недоступный филиал, отсутствие услуги/назначения,
  недоступное время и прошедшую/невалидную дату. Не переносит дату самовольно.
  Уточнение сохраняет остальные параметры. При одной подходящей связке филиал
  выбирается автоматически; при нескольких уточняется.
- Контекст current_branch берётся из явного фильтра календаря/записей, проверяется
  сервером до модели и при планировании. Работает для аудио и текстового fallback;
  явно названный филиал имеет приоритет. Результат включает название филиала.
- Перенос визита автоматической точки сохраняет booked price/duration даже после
  изменения Service; доступные слоты и серверная проверка используют ту же длительность.

## Проверки и воспроизведение

Все команды из корня checkout, Python `.venv/Scripts/python.exe`; Windows,
изолированные БД/порты через `scripts.codex_verify.isolated_runtime`, без внешних
AI/messaging вызовов. Генерация текста в domain tests подменена фиксированным
структурированным ответом; это доказательство команд/проверок, не качества модели.

| Проверка | Результат и граница |
| --- | --- |
| Итерации сервисов/каталога/голоса | Фокусные проверки после каждого блока; исходные ошибки fixtures сохранены, исправлены и повторно проверены |
| Основная затронутая группа | 205 tests PASS, 3 SQLite skips для row locks; `completion-0.log`; system/drift PASS |
| Миграция forward/reverse + current_branch | 2 PASS после исправления fixtures; `migration-context-fixed-*`; также включены в основную группу |
| Последняя дельта переноса | 76 PASS из 77 в `reschedule-0.log`; единственная ошибка — позиционный вызов keyword-only service в новом тесте. Исправленный тест отдельно PASS, `reschedule-fixed-*`; system/drift PASS |
| Зависимые сценарии после последней backend-дельты | 102 PASS, `schedule-dependent-*`; system/drift PASS |
| Параллельная дельта общего графика | После чужих изменений WorkingHours models/serializer и scheduling0012: повторно 46 PASS для single location/миграции/графика/record commands, `concurrent-hours-delta-*`; system/drift PASS. Эти чужие изменения исключены из собственного patch |
| PostgreSQL17, реальные соединения | 17 PASS: параллельное создание/архивирование и voice scheduling; `postgres-initial.*`. После последней backend-дельты ещё 21 PASS для voice/record/plan concurrency, `postgres-concurrency.*`; собственный кластер остановлен, disposable DB удалена |
| Реальный API и браузер Chromium | Три RU1440/KK390/EN768 сценария записи → второй филиал → архивирование PASS, `browser-1793971837257347000.log`; отдельный network-retry/pause/reactivate PASS в первом прогоне |
| Выбранный филиал в голосе | Browser PASS после исправления текстового fallback, `browser-1793972339378303300.log`; backend проверяет выбранную точку/чужой Business/сохранение draft |
| Frontend completion | `npm run build`: i18n 6921 RU/KK/EN keys, TypeScript, app/widget PASS; `build-1793972401642093400.log`. `npm run check:bundle` PASS; RU/KK chunks >500kB остаются предупреждением |

Команды групп:

```text
.venv/Scripts/python.exe output/single-location-20261106/check_backend.py completion apps.branches apps.scheduling.tests_record_commands apps.scheduling.tests_visit_plans apps.scheduling.tests_specialist_schedule apps.ai_core.tests_voice_locations apps.ai_core.tests_voice_schedule apps.ai_core.tests_voice_direct apps.businesses.tests_activation apps.accounts.tests apps.bots.tests_booking_terms
.venv/Scripts/python.exe output/single-location-20261106/check_backend.py reschedule apps.branches.tests_single_location apps.branches.tests_scheduling apps.scheduling.tests_record_commands apps.scheduling.tests_specialist_schedule apps.scheduling.tests_visit_plans
.venv/Scripts/python.exe output/single-location-20261106/check_backend.py reschedule-fixed apps.branches.tests_single_location.SingleLocationTests.test_reschedule_retains_booked_terms_after_live_catalog_changes
.venv/Scripts/python.exe output/single-location-20261106/check_backend.py schedule-dependent apps.scheduling.tests apps.bots.tests_booking_terms apps.ai_core.tests_voice_schedule apps.ai_core.tests_voice_locations apps.branches.tests_compatibility
.venv/Scripts/python.exe output/single-location-20261106/check_backend.py concurrent-hours-delta apps.branches.tests_single_location apps.branches.tests_initial_location_migration apps.scheduling.tests_specialist_schedule apps.scheduling.tests_record_commands
.venv/Scripts/python.exe output/single-location-20261106/run.py --browser
.venv/Scripts/python.exe output/single-location-20261106/run.py --browser --grep "automatic booking"
.venv/Scripts/python.exe output/single-location-20261106/run.py --browser --grep "voice request"
.venv/Scripts/python.exe output/single-location-20261106/run_pg.py apps.branches.tests_single_location_concurrency apps.branches.tests_concurrency apps.ai_core.tests_voice_schedule_concurrency
.venv/Scripts/python.exe output/single-location-20261106/run_pg.py apps.ai_core.tests_voice_schedule_concurrency apps.scheduling.tests_record_concurrency apps.scheduling.tests_plan_concurrency
```

Каждый successful backend runner также выполняет `manage.py check` и
`makemigrations --check --dry-run` в своей изоляции. Это scoped gate без выдуманного
ancestor base и без полного unrelated E2E. Числа групп пересекаются и не суммируются
как уникальные тесты. Build повторён после исправления fallback; неизменённые
прошедшие браузерные сценарии не перезапускались ради счётчика.

В первом browser-прогоне три сценария использовали старый combobox locator клиента;
исправлены на существующий ClientPicker, затем 3 PASS. Четвёртый recovery PASS
переиспользован. Отдельный voice regression действительно выявил потерю current_branch
в текстовом fallback; product-исправление проверено повторно, исходный FAIL сохранён.
Снимки `single-ru.png`, `single-kk.png`, `multiple-en.png` визуально просмотрены:
обычные токены/контролы, корректная мобильная компоновка, видимая причина запрета.
Проверены клавиатурный запуск добавления и отсутствие горизонтального overflow.

Основные постоянные регрессии:
[single location](../../../apps/branches/tests_single_location.py),
[миграция](../../../apps/branches/tests_initial_location_migration.py),
[конкурентность](../../../apps/branches/tests_single_location_concurrency.py),
[голос](../../../apps/ai_core/tests_voice_locations.py).

## Данные, документация и остаток

Permissions: existing role/object/field restrictions сохранены. Активный участник
без grant получает только автоматическую точку; явный пустой grant не обходится;
при второй точке доступ фиксируется на первой, network grant не расширяется.
Audit создания/состояния сохраняется. Новых notification/BusinessEvent типов нет;
обычная запись по-прежнему проходит существующие domain effects. AI остаётся опциональным.

Обновлены CRM/voice/AI/access/frontend/operations, roadmap CRM-MB01, acceptance,
паспорт AI/capabilities и registry. README не требует изменения: setup-команды и
публичный статус не меняются, конкретная миграция описана в operations. Product,
integrations и общие money-требования не изменены; полные D01/live остаются открытыми.

Рабочая среда: первый read-only preflight показал pending branches0003, 16 Business,
15 без Branch и один архивный филиал. Пока выполнялась финальная проверка, миграции
branches0003 и параллельная scheduling0012 были применены вне этой задачи. Этот
исполнитель не запускал рабочий migrate/backup/seed/reset и не приписывает их себе.
Повторный read-only preflight подтвердил пустой план branches0003, 16 Business,
16 Branch: 15 активных автоматических точек и один архивный неавтоматический филиал;
SQLite quick_check = ok. Факт/метаданные — `working-preflight.json` в task output.
Повторного разрешения или повторного применения уже выполненной миграции не нужно.
Архивный филиал не восстановлен; он требует явной активации через Бизнес → Филиалы
и сохраняет существующую явную конфигурацию.

В согласованной реализации и локальных проверках остатка нет. Публикация и
серверный rollout не выполнены. Внешнюю операцию миграции и её backup-процедуру
этот scoped PASS не сертифицирует; утверждается только наблюдённое состояние базы.

Публикация: после fetch origin/main diverged от текущего HEAD — один входящий и
16 чужих исходящих коммитов (включая параллельный dev launcher). Index пустой,
старого lock больше нет. Собственный
commit/push не выполнялись; чужие изменения/история не включались и не переписывались.
Нового CI/deployment нет. Локальный PASS не означает рабочую миграцию или серверный rollout.

## Явная активация и проверка голоса — REACTIVATE-BRANCH-20261106

По следующему прямому поручению владельца единственный прежний архивный филиал
Branch1/Business2 активирован через change_branch_state от имени owner. После commit
is_active=true, archived_at=null, одна запись AuditLog branch_state/active.
Каталог, назначения, график и доступ не изменены; uses_business_defaults=false
сохранён: это существующий явно настроенный филиал, не новая автоматическая точка.
В его текущей конфигурации найдены услуга, специалист и доступный слот
07.11.2026 09:00 Asia/Almaty. Дополнительная настройка не потребовалась.

Проверка настоящего аудио: Windows Irina TTS, mono16kHz/16bit WAV → текущий
OpenRouter speech provider whisper-large-v3-turbo → real model planner → обычный
voice/direct API → Appointment. Доменная проверка использовала disposable SQLite
с копией фактических услуг, назначений, графика, исключений, отсутствий, ограничений
capabilities и занятых интервалов активированного филиала. Рабочие клиенты, телефоны,
токены и подключения не переносились; owner/client — синтетические. Это не запись
с физического микрофона и не проверка production worker/внешних каналов.

Результаты разделены, первый FAIL не скрыт:

1. Аудио «Запиши нового клиента … на консультацию к Анне …» распознано с искажением
   «Канни». API вернул completed/«Действия выполнены», но Appointment не добавился:
   FAIL. В первом receipt нет деталей действий, поэтому причина и созданная вместо
   визита сущность не устанавливаются предположением. Рабочая база не затронута.
2. Повторная обработка именно этого сохранённого transcript реальной моделью:
   PASS, создан один Appointment, правильные service/resource/branch/date; replay
   вернул ту же операцию без дубля. Это text replay, не второй аудиопрогон.
3. Полный аудиопрогон «Создай запись на консультацию к специалисту Анне для нового
   клиента …»: PASS за8.8s. Филиал не передавался и не уточнялся; использованы
   существующие service81/resource114/branch1. Создан один визит на выбранный слот,
   число Appointment в изоляции14→15; повторный запрос оставил15.

После каждой попытки hash фактической рабочей конфигурации и списка визитов
не менялся; в рабочем бизнесе осталось14 Appointment. Ни тестового клиента,
ни тестовой записи этот исполнитель в рабочей базе не создавал. Активация филиала
и её audit — единственное изменение рабочих данных в этом поручении.

Остаток: филиальная причина блокировки устранена, возможность голосовой записи без
новой настройки подтверждена. Надёжность свободной формулировки НЕ закрыта:
первый completed без ожидаемого Appointment остаётся открытой находкой D01.
Нужна отдельная диагностика выбора операции и проверка полноты результата до
сообщения об успехе; product-код в этом операционном поручении не менялся.

Локальные receipts/scripts: output/reactivate-branch-20261106 — activation.json,
first-live-check.log/first-voice-result.json/first-live-receipt.json,
replay-text-result.json/replay-text-receipt.json, voice-result.json/live-receipt.json,
configuration-snapshot.json, command.wav. Команды: inspect_branch.py (чтение),
activate.py (одно разрешённое изменение), live_check.py (полное аудио),
live_check.py --text-only (диагностический replay). Script fixture failures
(имя inspect.py затеняло stdlib; неверный import workflows) исправлены до live-проверки;
они не являются сбоями продукта. Ошибка локального генератора даты исправлена до
первой отправки аудио; в provider ушла будущая дата7ноября, не11июля.

Версия d6cf58294bdbdbeca58879e3a5d227cd2140ebae + существующий WIP, каноническая папка,
ветка codex/ui-testing-toolkit. Миграций/env/deployment/исправлений приложения нет.
Повторные build/full suites не нужны для операции и docs; публикация docs блокируется
расхождением origin/main (1 входящий/18 чужих исходящих), чужой индекс/WIP сохранён.


## VOICE-RELIABILITY-20261106

Отдельное поручение владельца: устранить сообщение об успехе без записи, найти
причину первого сбоя, проверить несколько голосовых формулировок. Этот срез
закрывает воспроизведённую находку выше; исторический FAIL не переписан.

### Причина и исправление

Исходное аудио повторно дало тот же transcript («Запиши нового клиента Павла
Тестового на консультацию Канни 7 ноября 2026 года в 9 часов»), `completed`,
`crm_create clients`, Appointment14→14. Полные route/field planner/tool outputs
сохранены в `output/voice-reliability-20261106/reproduced-failure.json`.
У самого первого запуска подробного плана нет; причина доказана повторным
воспроизведением того же наблюдаемого сбоя, а не восстановлением удалённой БД.

Сервер исправляет client-only route для явного booking request до создания данных;
использует существующий атомарный `crm_schedule`. Проверка stored plan не позволяет
исполнить такой неполный клиентский шаг. Дополнительно успех сверяет ожидаемое
число, уникальные ID и фактическое наличие Appointment того же Business внутри
транзакции подтверждения. Некорректный результат откатывается с `action_failed`.
Ответы сообщают «Создано записей: 1» либо «Клиент создан», RU/KK/EN по языку сотрудника.
Права, аудит, BusinessEvent/уведомления и idempotency используют прежние доменные
сервисы; новые модели, миграции, права, внешние каналы и frontend не добавлены.

### Проверки

Канонический `C:/Users/user/Desktop/PlatformaCRM`, `codex/ui-testing-toolkit`,
HEAD `d6cf58294bdbdbeca58879e3a5d227cd2140ebae` + сохранённый WIP + task-only delta.
Существующий Python3.12.13 `.venv`; `scripts.codex_verify.isolated_runtime`, disposable
SQLite, внешние доставки выключены. Полные команды/логи/хеши: `output/voice-reliability-20261106/`.

- `check.py apps.ai_core.tests_voice_booking_intent`: итоговые11 PASS; воспроизведение
  неполного route, реальный визит/replay, отсутствующее/недоступное время, самостоятельный
  клиент, текст задач/заметок/отрицания, несуществующий результат, rollback после
  создания, языки RU/KK/EN. Первый запуск нашёл `notes` plural; исправлено.
  Второй промежуточный сбой — отсутствующая UserPreference в новом тестовом fixture;
  fixture исправлен, оба первоначальных лога сохранены.
- `check.py` с13 точными классами из `dependent-labels.json`: **102 PASS** включая
  новые11, voice_schedule/direct/policy/interface/language/locations и
  conversation_execution/state. Права/tenant/approval/revocation/recovery/rollback/replay
  проверены в этом affected/dependent наборе. `check` и `makemigrations --check --dry-run` PASS.
- `multi_audio.py`: четыре реальных синтетических аудио через OpenRouter ASR
  `openai/whisper-large-v3-turbo` и действующую модель, API→domain→DB. Исходная
  фраза, «Создай запись…», «Пожалуйста, запишите…» создали по одной записи с
  ожидаемыми услугой/специалистом/филиалом/временем; replay сохранил одну запись.
  Фраза без времени: `clarifying`, ни клиента, ни визита. Каждый сценарий в
  изолированной копии текущей конфигурации с rollback; working14appointments
  и конфигурация до/после неизменны, hash25686c667152160256b8b4612cf6749b5437389f14eed32dab5d460be1471c8b.

Frontend/build/browser не запускались: frontend и capture не менялись, reachable
поведение проверено через настоящий speech/conversation API и сохранённый доменный
результат. Новая PostgreSQL/concurrency/full-project/live worker сертификация не
нужна для этой дельты: locking, schema и execution domain не менялись. Не выдавать
эти проверки за human microphone/noise, полный D01 или production acceptance.

### Остаток и публикация

В согласованном исправлении нет остатка кода/локальных доказательств или вопроса
политики. Сохраняются внешние human/fullD01/production границы. После fetch origin/main
расходится:2 входящих/18 чужих исходящих; обычный push задачи не является безопасным
fast-forward. Собственных commit/push/CI/deployment нет; чужие WIP/index сохранены.
Рабочая БД, каталог, график, настройки, env и службы не изменялись.

При первоначальном диагностическом вызове bare `python` системный Windows Python
Manager автоматически обновился до26.4 и установил3.15.2. Случайно установленный
runtime3.15.2 удалён штатным `py uninstall --yes PythonCore/3.15`; проектная `.venv`
и её зависимости не менялись. Обновление самого Manager сохранено.
