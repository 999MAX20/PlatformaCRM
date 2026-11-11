# AI-WORK-CRM-FIXES-20261111

Поручение: исправить W1–W4 «Работы с CRM» и повторить API/Playwright с реальным AI без изменения рабочих данных.
Исходная проверка: [AI-WORK-CRM-LIVE](ai-work-crm-live-20261111.md).

## Результат и граница

Четыре исправления реализованы и проверены на изолированных синтетических данных.
Финальная совместимость общей папки ещё проверяется: первоначальный system check
заблокировала чужая SyntaxError в `apps/branches/staff_lifecycle.py`; затем файл изменён
другим автором, запущен адресный повтор. Свои исправления этого файла не выполнялись.
До завершения проверки commit/push не выполнены. Полный D01/production не закрыт.

| Группа | Получившееся поведение | Доказательство |
| --- | --- | --- |
| W1 | Модельный recent ID не доказывает цель. Буквальное название проверяется по полному scoped queryset; дубли и отсутствие уточняются. Один явный тип+ID имеет приоритет над старым выбором модели, но ID связанного объекта не меняет другую сущность; multiple steps не получают общий override. | Unit targets, API duplicate/missing/explicit selection/own/hidden/foreign; браузер duplicate/missing. |
| W2 | Завершение, начало и статус идут через transition; archive — явное удаление. | Основное завершение и два адресных повтора; браузерное завершение реально созданной задачи. |
| W3 | Явная заявка на услугу остаётся Lead; запись на время остаётся Appointment. | Создание/изменение Lead, два повтора исходного текста, explicit Lead, браузерный Lead; Appointment create/update. |
| W4 | access_changed объясняется на RU/KK/EN. UI скрывает retry; сервер запрещает повтор прежнего отказа без нового запроса/job. | Readonly API, retry403 с0model calls/0writes, браузер1440/320/390; planner не может подтвердить. |

Дополнительно исправлена потеря кодового префикса в кратком ответе на вопрос о
названии задачи. После неустойчивого prompt-only исправления добавлена ограниченная
серверная проверка: одна ожидающая задача, точный суффикс названия, буквальный префикс
из прописных букв/цифр, без командных слов. Нет hardcoded имён/корпуса или внешних
подсказок. `OPS-17`, `ҚР`, `Q4 2026` проверены unit-тестами; исходный случай повторён
дважды и отдельный пример один раз через реальный API; ещё один — через браузер.

Domain services, tenant/role checks, актуальная версия записи и явные подтверждения
сохранены. Нет моделей/миграций/env/dependencies/новых прав, notification или
BusinessEvent семантики. Рабочая БД, provider settings, сообщения клиентам и deployment
не затронуты действиями этого поручения.

## Реальный API и браузер

Канонический checkout `C:/Users/user/Desktop/PlatformaCRM`, сохранена ветка
`codex/ui-testing-toolkit`; starting HEAD `f01d2d8b`, позднее чужой HEAD `286c9cf6`.
Каждый runtime использовал `scripts.codex_verify.isolated_runtime`: отдельные SQLite,
backend без autoreload, Vite, Chrome; eager queue и синтетические аккаунты/каталоги.
Реальный OpenRouter `openai/gpt-4o-mini`, ключ только в памяти процесса.

- `output/playwright/ai-work-crm-final`:22 основных API PASS и7 адресных PASS.
  Создание/изменение пяти типов сущностей; до подтверждения снимки неизменны;
  fingerprint tampering/cancel/stale/revoked/direct bypass/own/foreign/replay проверены.
- Расширение:6PASS; случай потерянного префикса сохранён как FAIL и заменён новыми
  доказательствами после исправления: `ai-work-crm-title` —3API PASS, exact title,
  реальная запись и повторное подтверждение без новых вызовов/дублей.
- Браузер:7owner +readonly +planner +title =10 сценариев PASS, включая восстановление
  после уточнения. RU1440, KK320, EN390; alert читается, horizontal overflow отсутствует,
  retry отказа отсутствует, keyboard confirmation работает. Скриншоты осмотрены.
- Модель один раз спросила необязательные поля у planner. После явного ответа
  «другие поля не нужны» предложение получено, подтверждение disabled. Исходный
  failed browser assertion сохранён; отсутствие любых лишних вопросов не доказано.
- Завершающие cohorts:77+16=93 real calls. Все попытки, включая предыдущие итерации:
 197calls/803482tokens,0provider errors,0mock. Это не гарантирует поведение других моделей.

В core SQL-аудите4 защищённые строки не изменены; отменённый клиент и planner-задача
не созданы. В title cohort per-turn snapshots/записанные задачи/replay PASS.
Дополнительное сравнение всех baseline-таблиц остановилось на представлении
`Deal.amount` (JSON string/SQL number); полный финальный снимок до удаления временной
БД не сохранён. Полная SQL parity этого дополнительного cohort не заявляется.
Четыре временные БД удалены, собственные backend/Vite/Chrome остановлены.

## Автоматические проверки и сохранённые сбои

Точные команды используют `.venv/Scripts/python.exe output/ai-work-crm-fixes-20261111/verify.py`
с явными Django labels; wrapper вызывает `manage.py test ... -v 1` в isolated_runtime.
`--checks` отдельно вызывает `manage.py check` и `makemigrations --check --dry-run`.

| Срез / labels | Результат |
| --- | --- |
| tests_conversation_targets, tests_conversation_execution |15/16PASS на первых итерациях; окончательный target+execution21PASS |
| state/targets/execution/api/memory/crm_planner/crm_tools/voice_policy +ошибочный tests_voice_api |85:83PASS,1loaderERROR,1voicefixtureFAIL |
| targets/voice_policy/voice_interface/voice_direct/voice_language/voice_locations/voice_identity |79PASS; в старой note-фикстуре добавлен явный ID, подтверждение/сохранение не ослаблены |
| targets/crm_planner/execution/voice_policy |43PASS |
| targets/execution/voice_policy во время изменения сигнатуры |33:8FAIL/1ERROR; исходное исключение process скрывал за provider_unavailable. Не считается PASS |
| Повтор targets/execution/voice_policy на неизменном срезе |34PASS |
| Финальный prefix guard: targets/crm_planner/voice_language |36PASS |
| Совместимость с новыми чужими изменениями: targets/conversation_api/crm_tools/voice_policy/voice_locations |75PASS (verify-1794422484816380700-0.log) |
| system/drift |Первоначально PASS; повтор общей папки SyntaxError; после стороннего исправления system/drift PASS (verify-1794422296939450000-0/1.log) |

Полные labels имеют префикс `apps.ai_core.tests_`; точные stdout/ошибки в
`output/ai-work-crm-fixes-20261111/verify-*.log`, последовательность в CHECKPOINT.md.
Frontend: check-i18n, tsc -b --force, Vite app/widget в отдельных output-папках,
check-bundle PASS (`frontend-0..4.log`). После этого собственный frontend не менялся.
Полный проект/E2E, PG concurrency, production и human-STT не запускались: это не release,
новые транзакции/модели/очереди не вводились. Снимки исходников отделяют чужие изменения
speech/resource scheduling/каталогов; их реализация не приписывается этому поручению.

## Документы, Git и остаток

AI/frontend contracts, CRM-AI passport, D01 note, registry, STATUS и PRIMARY обновлены.
README/setup/CRM/access/integrations/operations не требуют изменений: их правила,
данные и настройки не менялись. Остатка реализации и локальных доказательств W1–W4 нет; совместимость
текущей общей папки PASS. Публикация пока открыта. Новое продуктовое решение не требуется.
43 чужих outgoing commits дополнительно блокируют own-only normal push в origin/main;
чужие WIP не staged и не исправлялись. Собственный локальный commit; нет push/newCI/deployment.

Артефакты и source hashes: `output/ai-work-crm-fixes-20261111/RESULT.json`.
Все ранние результаты сохранены в `ai-work-crm-fixed`, `ai-work-crm-verified`,
`ai-work-crm-final`, `ai-work-crm-title` под `output/playwright`.
