# VOICE-HARDENING-20261105 — фильтр команд и текущий STT

Поручение: после анализа владелец разрешил исправление ложных запретов и проверку
текущей модели/команд/очереди. Canonical `C:/Users/user/Desktop/PlatformaCRM`,
`codex/ui-testing-toolkit`, HEAD `66101d509cb7642b2928275e48c4b64354abf07b` + existing WIP.
План, исходные копии затронутых файлов, собственный patch/hashes и журналы:
`output/voice-hardening-20261105/`. Чужой diff сохранён.

## Изменения

`voice_policy.py`: явное создание задачи и добавление заметки допускают слова
«архив»/«не пришёл» в содержимом. Исключение ограничено одной соответствующей
операцией и явным RU/KK/EN маркером до запрещённого слова. Оно не разрешает
переходы записей, другие сущности или несколько действий. Неизвестные формулировки
по-прежнему могут отклоняться: это ограниченный лексический guard, не универсальный
семантический классификатор. Проверка payload по-прежнему разрешает update только
поля notes/description. Подтверждение повторяет проверки; права/tenant/аудит неизменны.

При реальном проверочном создании записи модель дважды сформировала недопустимый
`arguments.notes=null` вне `values`. Схема корректно отказала `invalid_action_plan`.
В `crm_planner.py` уточнены разрешённые ключи arguments и расположение notes;
валидация не смягчена, автоматический платный повтор не добавлен.

Следующий live-срез выявил отмену, ошибочно маршрутизированную как archive, затем
причину, помещённую моделью в question вместо arguments.reason. Уточнены ROUTE_CONTRACT
и shape/инструкция planner; question не преобразуется автоматически в разрешение.
Перенос только времени терял специалиста и верхнеуровневую причину в AI-adapter.
`crm_transitions.py` теперь передаёт текущий resource, если поле отсутствует,
и reason в существующий serializer/service. Явные значения не заменяются.
Service заново проверяет активность/tenant/слот; сохранены approval/version/replay.
Причина теперь доходит до существующих activity/audit, новые эффекты не вводятся.

Повтор общей матрицы выявил противоречие: shapes рекламировали archive/restore,
хотя voice capabilities их запрещают. Теперь shapes фильтруются доступными tools,
а conversation preparation ограничивает planner уже выбранной операцией; возврат
другого tool отвергается сервером. При create допускается пропуск null-placeholder
только для известных необязательных nonnullable полей: новой записи нечего очищать.
Required/unknown поля и update остаются строгими; nullable null сохраняется.

## Проверки

Все DB fixtures — disposable `isolated_runtime`; рабочие записи, миграции,
настройки `.env`, общий dev и production не менялись. Зависимости не устанавливались.

- `.venv/Scripts/python.exe output/voice-hardening-20261105/check_backend.py focused apps.ai_core.tests_voice_policy`:19 PASS, system/drift PASS.
- `check_backend.py affected apps.ai_core.tests_voice_policy apps.ai_core.tests_voice_interface apps.ai_core.tests_speech apps.ai_core.tests_voice_language apps.ai_core.tests_conversation_execution apps.ai_core.tests_conversation_state apps.ai_core.tests_approval_binding apps.ai_core.tests_crm_tools apps.ai_core.tests_crm_planner`:93 PASS, system/drift PASS. Это граница до дополнительного note regression и уточнения prompt.
- `check_backend.py note-regression apps.ai_core.tests_voice_policy.VoicePolicyTests.test_no_show_note_is_text_only_and_requires_confirmation`:1 PASS, system/drift PASS.
- `check_backend.py planner apps.ai_core.tests_crm_planner apps.ai_core.tests_conversation_execution apps.ai_core.tests_voice_policy`:29 PASS, system/drift PASS после первого уточнения planner prompt. Наборы пересекаются; их количества не суммируются как уникальные тесты.
- Первый `.venv/Scripts/python.exe output/voice-hardening-20261105/real_flow.py`:PASS. Фактически настроенный `openai/whisper-large-v3-turbo`, реальный OpenRouter, неизменные ZDR/no-data-collection, синтетическая русская запись → gpt-4o-mini → предложение → API confirm → одна Task; replay не дублирует. STT около7.1s, подготовка около3.5s; журнал `real-flow-initial.log`. Это не percentile/SLA.
- Первый `.venv/Scripts/python.exe output/voice-hardening-20261105/queue_flow.py`:частичный результат. Настоящий Celery worker `solo`, `task_always_eager=False`, изолированный memory broker и реальная модель. Task «Проверить архив документов», Client, Note «клиент не пришёл», search завершены; подготовка3.6–4.2s в этих единичных пробах. Booking FAILED invalid_action_plan; move/cancel не запускались без созданной записи. Журнал `queue-initial.log`.
- `queue_flow.py --booking`: диагностический повтор сохранил `queue-booking-before-prompt.log` с синтетическим ответом модели и доказал лишнее notes:null; затем изменена гипотеза/инструкция. Результат следующей проверки фиксируется ниже.
- `queue-booking-before-transition-fix.log`: booking PASS, move FAILED из-за потерянного resource, cancel FAILED из-за archive. `queue-booking-before-reason-schema.log`: booking/move PASS, cancel CLARIFYING из-за reason в question. Эти ошибки не выдаются за зелёный прогон.
- `check_backend.py reschedule apps.ai_core.tests_crm_tools.CRMCommandTests.test_time_only_reschedule_keeps_specialist_reason_and_rechecks_activity apps.ai_core.tests_crm_tools.CRMCommandTests.test_appointment_create_reschedule_cancel_and_busy_slot_recheck`:2 PASS, system/drift PASS. Проверены сохранение специалиста/причины, один аудит при replay, отказ после деактивации без переноса, занятый слот, create/reschedule/cancel.
- `check_backend.py final` с теми же9 labels, что affected:95 PASS, system/drift PASS на промежуточном срезе. После уточнения reason в prompt/shape: `check_backend.py reason-schema apps.ai_core.tests_crm_planner`:9 PASS, system/drift PASS. Последующая дельта bounded planner проверена отдельно ниже.
- `queue-before-bounded-planner.log`: task/note/search/booking/move PASS, client CLARIFYING из-за optional null placeholders, cancel FAILED из-за предложенного archive. Поиск здесь дополнительно проверял имя и реальный source ID. Не считается чистым общим PASS.
- `check_backend.py bounded-planner apps.ai_core.tests_crm_planner apps.ai_core.tests_conversation_execution apps.ai_core.tests_voice_policy`:31 PASS, system/drift PASS после ограничения tools и нормализации create. Последующий тест required/unknown null входит в заключительный affected run, а не в31.

- `.venv/Scripts/python.exe output/voice-hardening-20261105/check_backend.py final-bounded apps.ai_core.tests_voice_policy apps.ai_core.tests_voice_interface apps.ai_core.tests_speech apps.ai_core.tests_voice_language apps.ai_core.tests_conversation_execution apps.ai_core.tests_conversation_state apps.ai_core.tests_approval_binding apps.ai_core.tests_crm_tools apps.ai_core.tests_crm_planner`: **98 PASS**, system/drift PASS на окончательном коде. Включены required/unknown null, строгий update и отказ при подмене выбранной операции.
- Повторный `real_flow.py` на окончательном коде: Turbo STT→реальная текстовая модель→Task→replay PASS; одна задача, completed, replay200. STT5.77s; исходный срез сохранён в `real-flow-initial.log`.
- Финальный `queue_flow.py`: **7/7 PASS** (Task, Client, Note, search, booking, move, cancel) в одном прогоне;7 jobs succeeded, FAILURES []. Реальная модель OpenRouter/gpt-4o-mini, worker solo, memory broker, eager=False; отсутствие новых записей до подтверждения и повторный confirm проверены. Поиск проверяет имя и source ID. Подготовка3.62–5.67s в единичных пробах, не SLA. Это текстовые команды через voice API, не семь аудиопроб и не Redis/production. Исходные неуспешные прогоны сохранены, включая `queue-before-bounded-planner.log`.

Frontend не менялся: build/browser/full-E2E не запускались. Реальный новый путь
проверяется через API, а не выдаётся за повторную браузерную приёмку. Исторические
browser отчёты сохраняют собственную границу. У приложения `ready` по контракту
означает наличие конфигурации, не платный health check; это поведение не менялось.

## Оставшаяся приёмка

Новая проверка Turbo закрывает только синтетическую русскую API-пробу. Требуются
живые разрешённые записи RU/KK/mixed, реальные микрофоны/шум, имена/телефоны/даты,
полная предметная матрица D01 и измерение качества/латентности. Этих записей в
поручении не предоставлено; синтетическая речь не заменяет их.
Локальный queue flag False; listener Redis6379 отсутствует. Memory broker доказывает
worker dispatch, но не production Redis, отдельный процесс/перезапуск/recovery или
целевой deployment. WorkingDB и инфраструктура не перенастраивались.

Существуют `.git/index.lock` и17 чужих outgoing commits; index пуст. Не удалялись
lock/история и не публиковались чужие изменения. Собственного commit/push/нового CI/
deployment нет. Требование публикации остаётся блокированным.

Контракт голоса, AI, CRM, roadmap, паспорт, индекс и STATUS согласованы с этим срезом.
В принятом объёме исправлений и локальных проверок остатка нет; перечисленная
выше полная продуктовая/языковая/production-приёмка и публикация не закрыты.
Access/operations/root README не требуют изменений: права, доменные действия,
схема, настройки и setup сохранены. Полный D01 не закрывается.

Финальная проверка: scoped diff hygiene/new-file links PASS; task-owned patch и
SHA256 обновлены. Index пуст, lock сохранён; remote main0b3348e1,17 outgoing.
Запуски тестов/queue/audio завершены. Публикация/CI не выполнялись.
После явного разрешения владельца согласована параллельная правка этого отчёта:
удалены дубли, уточнены границы промежуточных31/95 и финальных98 тестов.
