# VOICE-PLANNER-20261111 — сбой формата плана

Поручение: найти причину единичного сбоя после точной расшифровки, исправить и
проверить повторными синтетическими записями. Canonical PlatformaCRM,
codex/ui-testing-toolkit, исходныйcf66534b. Foreign business/source/docs WIP сохранён.

## Воспроизведение и причина

Исходный прежний отчёт не сохранил ответ неуспешного планировщика: точную причину
именно того HTTP-запроса доказать ретроспективно нельзя. Для нового воспроизведения
сохранены каждый ответ модели, тип/место исключения и состояние CRM; только synthetic
данные, без provider keys/real clients. Непроверенная гипотеза не объявлялась причиной.

Первая серия12(3аудио×4):12PASS. Вторая серия с существующим посещением как в исходном
контексте:11PASS/1FAIL. В неуспешной попытке STT вернул точные имя/номер, router —
валидный clients/create. Field planner вернул синтаксически неверный JSON:

```text
{"tool":"crm_create","arguments":{"entity":"clients","values":{"full_name":"Мария Соколова","phone":"+77012345678"}},{"question":""}}
```

`json.loads` в crm_planner.py вызвал JSONDecodeError, затем invalid_action_plan;
turn стал failed. Клиентов/посещений/задач до и после1/1/0; частичных записей нет.
Точные данные: output/voice-planner-20261111/reproduced-failure.json,
context-repeat-result.json; исходная неудача сохранена, не переписана новым PASS.

Причина подтверждена отдельным policy-baseline.json: downstream выбирал
`openai/gpt-4o-mini`, но generation_policy возвращал model=null/json_output=false.
Модель по умолчанию/по tier определялась только позже в generate_text, после
решения включать JSON-режим. Saved-agent путь определял модель заранее, а
самостоятельный voice/CRM без сохранённого агента обходил эту настройку.
`services.run_ai_request` добавляет response_format только при policy.json_output.

## Исправление

Две строки runtime_policy.py определяют фактическую модель через существующий
resolve_model(prompt_type,model,model_tier) до проверки JSON capability. Сохраняются
приоритет явной модели/tier/prompt-tier/default и существующий allowlist профилей.
Router и field planner получают json_object для поддерживаемого профиля по
умолчанию; неизвестные модели и обычные text-stages не получают новую capability.
Модель/температура/права/tenant/approval не заменены. Parser остаётся строгим:
неисправный ответ отклоняется, никакой догадки/ремонта JSON или нового платного retry.

## Проверки

Команды из канонической папки, существующий .venv, scripts.codex_verify.isolated_runtime:

- `.venv/Scripts/python.exe output/voice-planner-20261111/check.py focused apps.ai_core.tests_planner_json_mode`:4PASS, system/driftPASS.
  Default/prompt-tier/explicit-tier/custom-model; реальный provider adapter с
  перехваченным HTTP payload обоих этапов; точные Client поля/replay; captured invalid
  JSON отклоняется без ToolCall/Client. Mock только transport, не policy/planner/domain.
- `check.py dependent apps.ai_core.tests_planner_json_mode apps.ai_core.tests_crm_planner apps.ai_core.tests_voice_direct apps.ai_core.tests_voice_policy apps.ai_core.tests_voice_identity apps.ai_core.tests_voice_schedule apps.ai_core.tests_voice_booking_intent apps.ai_core.tests_conversation_execution apps.ai_core.tests_conversation_memory apps.ai_core.tests_quality apps.ai_core.tests_settings_certification apps.ai_core.tests_voice_language apps.ai_core.tests_voice_interface`:148,146PASS/2FAIL в handoff fixtures.
- `.venv/Scripts/python.exe output/voice-planner-20261111/quality_baseline.py`:
  обе неудачи повторены с прежней и новой policy(2FAIL+2FAIL), затем2PASS с fake key.
  Fixtures не задавали credentials для существующего readiness guard, хотя ожидали
  вызова mocked qualification. Исправлены только настройки двух тестов; добавлена
  проверка достижения qualifier. Исходные handoff/no-write/no-send assertions сохранены.
- `check.py quality-final apps.ai_core.tests_quality apps.ai_core.tests_planner_json_mode`:
  30PASS, check/driftPASS. Неизменённые остальные146PASS не повторялись; исходный148FAIL
  лог сохранён. Это совокупное доказательство148сценариев, а не утверждение о новом
  едином148PASS прогоне.
- `.venv/Scripts/python.exe output/voice-planner-20261111/fixed_repeat.py`:
  24/24PASS(3файла×8повторов),24replayPASS,48/48реальных planner requests содержат
  json_object. Каждая попытка создаёт ровно1Client с точными именем и всеми цифрами
  телефона; следующая начинается с очищенной synthetic fixture, посещение контекста
  сохранено. Реальная Scribe v2 +gpt-4o-mini, без mocked model/CRM. Длительность
  6.062–14.453с, медиана6.438с с диагностикой, не SLA. Телефоны/имена/повторы проверены
  assertions, исходные аудио и их SHA — voice-recognition corpus.

Политика/парсер/provider/STT сохраняют SHA исходного проверенного среза. Во время
работы появились чужие analytics-изменения router/preparation/services: просмотрены,
не включены в commit. response_schema=None в voice сохраняет json_object; финальные
wire-тесты проходят на текущем сервисе. Это не сертификация чужой analytics-дельты.
Изначальные и финальные inputs SHA сохранены отдельно; новая версия ветки не выдаётся
за исходный неизменённый снимок.

Изолированная SQLite, eager API; реальные Scribe v2/gpt-4o-mini только на synthetic
аудио/данных по явному поручению. Рабочая БД/env/migrations/provider config/deploy
не менялись. Frontend/build/full-project/PGqueue не нужны: UI, транзакции, очередь
не менялись, выпуск не запрошен. Human/KK/noise/fullD01/production не сертифицируются.
Полные команды, входные SHA256, неудачи, результаты: output/voice-planner-20261111.

## Завершение и остаток

Дефект настройки JSON-режима воспроизведён и исправлен; в этом scope остатка кода
и synthetic evidence нет. Исторический потерянный ответ модели не восстановлен,
общая безошибочность AI/живой речи не заявляется. Контракт, паспорт, capabilities,
roadmap согласованы с evidence. Own reviewed commit локальный;33pre-existing
outgoing commits не разрешены к публикации, push/newCI/deploy не выполнялись.
