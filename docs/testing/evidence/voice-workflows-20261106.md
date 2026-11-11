# VOICE-WORKFLOWS-20261106 — связанные команды и история

Согласованный06.11 scope реализован и проверен локально: поиск/создание клиента
вместе с записью, датированный план посещений, история со ссылками на результаты,
одинаковые размеры колокольчика/микрофона, один крестик и подписанные действия записи.
Канонический checkout `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, HEAD `66101d509cb7642b2928275e48c4b64354abf07b` + собственная
dirty delta поверх существующего WIP. Исходные снимки/план и журналы:
`output/voice-workflows-20261106/`; итоговый owned patch и SHA256 там же.

## Наблюдаемое поведение

- Поиск имени охватывает доступных клиентов, включая находящихся за пределами
  прежней выборки50. Неоднозначное совпадение требует выбора. Новый клиент
  создаётся по имени; телефон необязателен.
- Клиент, план и записи создаются атомарно. Недоступный слот/ошибка позднего шага
  не оставляют частичный набор. Повтор команды не создаёт дубли.
- Недостающие услуга/специалист/время уточняются с сохранением предыдущих данных.
  Единственный вариант допустим; несколько вариантов не выбираются произвольно.
  Явное разрешение «любой свободный» позволяет выбрать свободного специалиста.
  Часовой пояс вычисляет сервер; отсутствующее время не придумывается.
- Результат и `/app/voice/history` показывают клиента, каждую запись с датой/годом,
  услугой/специалистом и ссылку на план. История приватна для сотрудника/Business,
  пагинируется; устаревший доступ скрывает результат. История только для чтения.
- Звуковая линия занимает строку, отмена записи и отправка подписаны, крестик один.
  Иконки хедера20px/stroke2, существующие области нажатия сохранены.

Права и точная авторизация сохраняются через существующие AI/domain services.
Новых permission grants, моделей, миграций и env нет. Используются штатные
BusinessEvent/notification эффекты доменных операций; отдельной рассылки нет.

## Проверки

Все данные синтетические, БД изолированы. Команды запускаются из канонического root
через `.venv/Scripts/python.exe`. `check_backend.py` использует `isolated_runtime`
и после тестов запускает `manage.py check` и `makemigrations --check --dry-run`.

| Срез | Результат |
| --- | --- |
| `check_backend.py service apps.ai_core.tests_voice_schedule` до зависимых изменений | 11 PASS, system/drift PASS |
| `check_backend.py workflow-fixed apps.ai_core.tests_voice_schedule apps.ai_core.tests_voice_direct` | 31 PASS после исправления потери draft при superseded clarification |
| `check_backend.py affected` с перечисленными ниже labels | 165 PASS, system/drift PASS; до финальных уточнений extractor/SQL lock |
| `check_backend.py final-focused apps.ai_core.tests_voice_schedule apps.ai_core.tests_voice_direct apps.ai_core.tests_conversation_memory apps.ai_core.tests_conversation_execution apps.ai_core.tests_voice_policy` | 64 PASS, system/drift PASS после финальных изменений planner |
| `run_pg.py apps.ai_core.tests_voice_schedule_concurrency apps.scheduling.tests_plan_concurrency apps.scheduling.tests_record_concurrency apps.ai_core.tests_crm_tools apps.ai_core.tests_approval_binding` | 58 PASS на native PostgreSQL17 после исправления SQL lock |
| `run.py --grep 'history\|labelled discard\|lost send response\|microphone denial\|recognition failure'` | 8 PASS + финальный build PASS |
| `run.py --browser --grep 'history loading'` | 1 PASS: ожидание/пустое состояние/пагинация |
| `npm run build` через isolated runner | types, i18n6916, Vite app/widget PASS |
| `npm run check:bundle` из frontend | PASS; app shell348.9kB <400kB, предупреждения RU/KK >500kB до gzip сохранены |

Labels affected: `apps.ai_core.tests_voice_schedule`, `tests_voice_direct`,
`tests_voice_policy`, `tests_voice_interface`, `tests_conversation_api`,
`tests_conversation_state`, `tests_conversation_execution`, `tests_conversation_memory`,
`tests_agent_runtime`, `tests_crm_tools`, `tests_crm_planner` (все с prefix
`apps.ai_core.`), `apps.scheduling.tests_visit_plans`, `tests_record_commands`
(последний также с prefix `apps.scheduling.`).

Проверены happy path, invalid input, permissions/tenant, изменившиеся цена/длительность,
rollback позднего шага, скрытие истории, точное approval, replay. PostgreSQL отдельно
доказывает повтор одной команды, одновременное создание клиента с одним именем и
конкуренцию за слот без оставленного клиента проигравшей операции. Изолированный
кластер остановлен, временная БД удалена с проверкой собственного пути/порта.

Browser использует реальную изолированную API-историю плана с тремя записями;
аудио/STT в этих UI-тестах подменены. RU1440/KK390/EN768, keyboard Enter к плану,
privacy/error recovery, размеры иконок и отсутствие горизонтального overflow PASS.
Снимки `history-ru.png`, `history-kk.png`, `history-en.png`, `recording-controls.png`
в output просмотрены. Отдельный paging test использует контролируемый API-ответ.

## Реальная модель и исправленные отказы

`live_schedule.py` с реальным OpenRouter, синтетическими сущностями и in-process
non-eager Celery memory broker: 7 сценариев PASS (8 ходов),
`live-schedule-final-result.json` / `queue-flow-final.log`. Существующий клиент
за пределами50 и ответ на уточнение, новый клиент, план из3 дат, любой свободный,
английская/казахская команды и запрос без времени. Последний корректно уточняет
время, не пишет данные. Время текстового хода4.11–7.72сек; это не замер полного STT.
Язык ответов определяется настройкой сотрудника (в этой матрице RU).

Начальные неуспешные результаты сохранены, не объявлены PASS:
`workflow-0.log` — потеря draft; `queue-flow*.log` — схема/даты/потеря специалиста
в коротком ответе. Сокращён контекст, явное поле extractor `specialist` заменило
неоднозначный `resource`; минимальный диагностический сценарий и полная матрица
после исправления PASS. `postgres-initial-failure.log` и
`postgres-nullable-diagnostic.log`: PostgreSQL запрещал FOR UPDATE nullable join.
`select_for_update(of=("self",))` ограничивает lock записью tool log; Business
блокируется отдельно. Финальный PostgreSQL пакет58 PASS. Первое UI-падение было
ожиданием неверного role для штатного NotFound; исправлено ожидание реальной кнопки
Retry, проверка сокрытия чужих данных сохранена, финальный прогон PASS.

## Граница завершения

В принятом scope остатка кода/локальных доказательств нет. Human микрофон,
RU/KK/mixed/noise, полный D01, production broker/recovery/rollout остаются открытыми.
Полный проектный/E2E gate не запускался: scoped изменение, не release candidate.
Рабочая БД, env, зависимости и deployment не изменялись.

Commit/push/newCI не выполнены: существующий `.git/index.lock`, 17 чужих исходящих
коммитов относительно локального `origin/main`; staged diff пуст. Lock и чужой WIP
сохранены. На сервер изменение не выкладывалось. Согласованы текущий voice-контракт,
AI/frontend, паспорт D01, roadmap, evidence registry и STATUS. CRM money/access/
integration contracts и README изменений не требуют: соответствующие правила,
setup и публичный статус не менялись.

## История запросов, 12.11.2026

Отдельное поручение: `/app/voice/history` по предоставленному референсу.
Добавлены поиск по доступному названию запроса, фильтры текущего статуса и даты
обновления в timezone бизнеса, сброс и сохранение фильтров в URL. При фильтрации
догружаются следующие страницы API; до окончания загрузки виден поиск по истории.
Список сгруппирован по дням. Результат расположен перед исходным текстом; отдельно
показаны уточнение, ожидание подтверждения, число выполненных шагов и отсутствие
выполненных CRM-действий. Доступные серверные review-названия заменяют ID в деталях.
История остаётся read-only; недоступные сведения не восстанавливаются из текста.

Playwright CLI: поиск/пустая выдача/status/date/invalid-range/reset/selection PASS;
клавиатура Select и календаря, возврат к списку, 320/390/768/1440 PASS.
RU/KK/EN 320/1440 PASS. Header48.8px/sidebar64px при1440 неизменны.
Подмена API только в браузере: совпадение на второй странице50+, индикатор поиска,
503→retry→empty, очистка фильтра PASS. База не изменялась. Скриншоты просмотрены.
Первоначальные проверки без ожидания React и передача многострочного сценария
через CLI-аргумент не прошли; исправлены ожидания и запуск `--filename`, итог PASS.
Дополнительный сценарий первоначально остановлен истечением сессии (refresh401).
После входа владельца review-названия, отсутствие кнопки исполнения, частичный
результат1/2, completed без действий и redacted без исходного текста: PASS.
Подмена ответов удалена; открыта исходная реальная история.

Команды и журналы: `output/playwright/voice-history-20261112/`:
`check-browser.js`, `browser-final.log`, `check-states.js`, `states.log`,
`check-details.js`, `details.log`, `details-diagnostic.log`, `details-final.log`,
`build-completion.log`. Неиспользованный `check-details-isolated.js` не является
доказательством проверки; вспомогательная пустая browser-сессия закрыта.
`npm run build` (i18n/types/app/widget) PASS. Backend/full-project gates не нужны:
API/permissions/schema/execution не менялись. Страница использует прежние API и shell.
Полная D01/provider/live приёмка этим поручением не закрывается.
Публикация отдельно от локального результата: чужой исходящий диапазон сохраняется.
В принятом локальном scope остатка кода/проверок нет. Поиск ограничен названием,
которое разрешено API; это не полнотекстовый поиск по скрытым сообщениям.
README, roadmap, AI/access/CRM contracts и паспорт D01 не меняются: новое поведение
ограничено интерфейсом истории и не меняет действующие acceptance/policy.
