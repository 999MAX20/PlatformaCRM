# VOICE-LIVE-20261105 — реальный OpenRouter и рабочая миграция

Владелец после сообщения об ошибке явно поручил довести реализацию и протестировать
голос. Это включает ранее предложенную целевую локальную миграцию с backup.
Canonical root `C:/Users/user/Desktop/PlatformaCRM`, ветка `codex/ui-testing-toolkit`,
HEAD `66101d509cb7642b2928275e48c4b64354abf07b` + сохранённый foreign WIP и task delta.
Предыдущая граница: [независимость от агента](voice-interface-20261105.md).
Артефакты/исходные snapshots/план/manifest: `output/voice-interface-20261105/live/`.

## Причина и изменения

Реальный POST OpenRouter `/audio/transcriptions` для `openai/gpt-4o-transcribe`
вернул404: No endpoints found matching your data policy (Zero data retention),
failed_routing_step=Filter by Data Policy. Ключ, base URL и enable flags присутствовали.
Default заменён на `openai/whisper-large-v3` после успешной реальной проверки с
неизменными `zdr:true` и `data_collection:deny`. Никакого скрытого ослабления
privacy policy или автоматического платного fallback нет.

HTTP permanent failures400/401/402/403/404 теперь provider_rejected/retryable=false;
408/429/5xx остаются временными. Журнал пишет только status/error code, без
body/URL/token/audio. Исходный payload не публикуется в ошибках.

На локальном dev отсутствуют Redis connection и AI-worker, а queue flag был default
True. В локальном `.env` установлен `AI_QUEUE_LIVE_REQUESTS=False`, задействован
существующий inline execution; production default и требования очереди ai неизменны.
Django autoreload активен, listener8000 из canonical manage.py; текущие настройки
read-back: OpenRouter/Whisper Large V3/queue=False.

Реальная модель обнаружила неоднозначную инструкцию: «без времени спросить»
относилась и к задачам. ROUTE_CONTRACT теперь явно требует время для Appointment,
а срок/исполнитель/связи Task признаёт необязательными. Задача с названием
готовится к подтверждению без выдуманного срока; права и domain schema сохранены.

## Рабочая БД

Проверены SQLite engine и точный canonical db.sqlite3. MigrationExecutor разрешил
только ai_core0009; другие pending migrations не применялись. SQLite backup API
создал локальную копию, integrity_check=ok; затем migrate ai_core0009 PASS.
Повторный read-only migration lookup и quick_check=ok. Backup содержит рабочие
данные и остаётся локальным исключённым артефактом, не материалом публикации.
Тестовые бизнесы/задачи создавались только в disposable DB, рабочие записи не seed/reset.

## Доказательства

- `check_backend.py live-fix apps.ai_core.tests_speech apps.ai_core.tests_voice_interface`:19 PASS; check/drift PASS. Новые проверки постоянных/временных отказов и отсутствия приватных данных в журнале.
- `check_backend.py live-routing apps.ai_core.tests_conversation_execution apps.ai_core.tests_voice_interface apps.ai_core.tests_voice_policy apps.ai_core.tests_crm_planner`:35 PASS; check/drift PASS. Наборы пересекаются, не54 уникальных теста.
- `.venv/Scripts/python.exe output/voice-interface-20261105/live/real_flow.py`:PASS. Реальный STT русской синтетической записи, новый voice thread без Bot, реальный gpt-4o-mini/OpenRouter routing/planning, no Task before confirmation, one Task after confirmation, replay200/count1. Финальный `real-flow.log`, model records ai_provider=openrouter.
- `.venv/Scripts/python.exe output/voice-interface-20261105/live/run_browser.py`:prepare/fixture/browser0;1 PASS. Настоящий Chromium capture/worklet/WAV из синтетического русского файла, реальный speech endpoint/OpenRouter, transcript, создание thread kind=voice/agent=null, реальная модель и явная кнопка подтверждения→Task со ссылкой. Ни одного Bot в тестовом Business. `live-browser.log`, `live-proposal.png`, `live-completed.png`; финальный screenshot просмотрен.
- Проверенная фраза: «Создай задачу с названием Проверка голосового управления». Английский текст, озвученный русским системным голосом в первой пробе, распознан плохо; эта проба не считается английской приёмкой.
- Browser runtime по умолчанию правильно блокировал внешний network; первый live browser attempt500 сохранён в `live-browser-network-guard.log`. Отдельный owner-authorized live server сохраняет disposable DB checks/запрет .env и разрешает только loopback + openrouter.ai:443. Общий browser_test_runtime не менялся. Ключ передаётся только серверу в памяти, не fixture/браузеру/файлам.
- Диагностический API-run сначала воспроизвёл лишнее уточнение срока. Несколько ошибок harness (testserver allowlist, JSON datetime/encoding, неверные поля отчёта) исправлены без изменения продуктовых assertions; финальные оба runners завершились0. Предшествующие существенные ошибки сохранены отдельно.
- Frontend не менялся в этом live-срезе; предыдущие6 UI RU/KK/EN, build/types/i18n6883 и Node4 применимы к неизменным frontend inputs. Новый реальный browser run дополнительно проверил связку. Повторный build/install/full-E2E не требуются.
- Scoped diff hygiene, changed-document links и registry проверены. Working schema и local flags прочитаны повторно. Own disposable runners завершены, dev8000/5173 оставлены работающими.

## Граница

Запрошенный локальный путь работает в проверенном реальном RU synthetic scenario;
для создания агента нет зависимости, миграция рабочей БД больше не блокер.
Пользовательский физический микрофон и речь/акустика, KK/mixed/шум, весь набор команд
с реальной моделью, worker-live/production и полный D01 не сертифицированы этим срезом.
Права/tenant/approval/replay покрыты указанными автоматическими наборами.

Существующий Git index.lock и17 чужих outgoing commits сохранены. Own commit/push,
новый CI и deployment не выполнены; реальные provider calls и локальная миграция
не означают публикацию. Секреты, backup и synthetic runtime артефакты не staged.

API contract сверён с [официальной документацией OpenRouter](https://openrouter.ai/docs/guides/overview/multimodal/stt): отдельный STT endpoint и privacy routing flags.
