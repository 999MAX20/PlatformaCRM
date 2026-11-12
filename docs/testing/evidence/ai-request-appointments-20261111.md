# AI-REQUEST-APPOINTMENTS-20261111

Поручение владельца: новые заявки направлять в appointments вместо Lead; обновить
тесты/документацию и повторить Playwright/API с реальным AI без рабочих изменений.
Начато11.11, заключительные проверки12.11.2026 (Asia/Qyzylorda).
Новый порученный повтор и публикация12.11 описаны в
[CRM-GLOBAL-REMAINING](crm-global-remaining-20261112.md); ниже сохранена граница
первоначального live-среза, включая тогдашние ошибки и отсутствие публикации.
Канонический checkout `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, starting HEAD `2537e8b6`; локальная незакоммиченная дельта.
Чужие source/docs WIP сохранены. Публикация в этом боковом чате не запрашивалась.

## Поведение

- Новая заявка/лид/өтінім/inquiry в «Работе с CRM» — appointments/create.
  Инструкция модели исправлена; сервер нормализует ошибочный leads/create до
  проверки источников/инструментов и планировщика, включая старый pending plan.
- Требуются клиент, услуга, специалист и будущее время. Недостающее уточняется;
  новое предложение требует подтверждения. Модельный Lead payload отклоняется.
- Исторические Lead сохраняют реальные ID, чтение/изменение и backend API.
  Нет миграции, автоматической конвертации, удаления данных или новой Record-модели.
- Domain services, права/tenant, подтверждение, fingerprints, idempotency и
  исключение пересечений сохранены; новые роли/схема/уведомления/BusinessEvent не введены.

Это исправляет ошибочную W3-приёмку из
[предыдущего среза](ai-work-crm-fixes-20261111.md), противоречившую R01.
Старые результаты не переписаны в новый PASS; к ним добавлено уведомление о замене.

## Проверки

Все Django проверки — `.venv/Scripts/python.exe output/ai-request-appointments-20261111/verify.py`
с `scripts.codex_verify.isolated_runtime`, без рабочей БД.

- Адресные `apps.ai_core.tests_request_appointments`:5PASS. Первый прогон4PASS/1ERROR:
  тест читал context_json вместо plan_json; исправлен тест, исходный лог сохранён.
- Зависимые labels: tests_request_appointments, tests_conversation_targets,
  tests_conversation_execution, tests_conversation_api, tests_crm_planner,
  tests_voice_policy, tests_resource_booking (все с префиксом apps.ai_core).
  64 теста:63PASS/1ERROR. Сбой в чужом tests_resource_booking/voice_schedule_commands:
  ожидание DRF ValidationError, фактический ScheduleConflict при занятом оборудовании.
  Общий зависимый gate НЕ PASS. `baseline.py` повторил тот же ERROR в isolated DB
  с загрузчиком исходных трёх модулей из2537e8b6; тест вообще не импортировал эти
  модули (маршрутизатор/подготовку/планировщик). Сбой воспроизводится независимо
  от этой дельты. Первый запуск контрольного harness без DJANGO_SETTINGS_MODULE
  завершился до теста; исправлен только harness, лог сохранён. Чужие файлы этим
  поручением не исправлялись.
- `--checks`: system check и makemigrations --check --dry-run PASS.
- Frontend source не менялся: build/types не повторялись. Full project/E2E, PG
  concurrency, live queue, human speech и production не сертифицировались.

Реальный OpenRouter `openai/gpt-4o-mini`:23calls/99570tokens,0mock,0provider errors.
Отдельный SQLite/eager, synthetic users/data, backend без autoreload, Vite и Playwright
Chromium. Ключ прочитан из настроек только в память процесса; настройки не менялись.

API `output/playwright/ai-request-appointments/cases.py`: RU/KK/EN создание,
missing details→followup, explicit confirm, fingerprint tamper409, replay без дубля,
cancel и последующий confirm denial, readonly refusal, foreign-client no proposal,
чтение исторического Lead.8PASS/1FAIL в исходной9-case матрице.
FAIL был ожиданием, что занятый слот отклоняется до предложения; фактически текущий
CRM planner валидирует поля, а domain availability проверяется при выполнении.
Дополнительный `overlap.py`: подтверждение возвращает failed, HTTP200 envelope,
CRM snapshot полностью неизменен. Сам overlap guard PASS на правильной границе;
исходный FAIL сохранён. Улучшение предварительного отображения конфликта не входило
в данную дельту. Foreign-client case завершился invalid_action_plan без предложения;
это доказательство отсутствия записи/утечки, не сертификация удобства такого отказа.

Playwright `browser.cjs`: новая заявка→уточнение→Appointment proposal→подтверждение
клавиатурой→completed PASS;1440×1000/390×844, скриншоты осмотрены.
SQL `audit.py`: только5 новых Appointment; все прежние строки Client/Task/Lead/Deal/
Appointment полностью совпадают с baseline;0Lead/Deal create tool logs.
Снимки сняты через readonly SQL до удаления disposable DB.
Свои backend/Vite/Chromium остановлены; отсутствие disposable DB проверено.
Рабочие данные, env, provider settings, чужие процессы и deployment не затронуты.

## Документы и остаток

Исправлены AI/CRM contracts, паспорт CRM-AI, D01 note и ссылка на заменённую W3-приёмку;
registry/STATUS/PRIMARY дополнены этим срезом. Frontend/access/integrations/operations/
README не менялись этой задачей: UI, policy, setup и external effects не изменились.
Код маршрутизации и API/Playwright доказательства получены. Общий зависимый gate
имеет один открытый сбой оборудования; его нельзя считать зелёным по этому отчёту.
Нет собственного stage/commit/push/newCI/deploy. Полный D01/R01 этим не закрывается.

Команды, попытки, снимок чужих изменений:
`output/ai-request-appointments-20261111/CHECKPOINT.md`.
Real-provider/API/browser/SQL/source hashes: `output/playwright/ai-request-appointments/`.
