# VOICE-DIRECT-20261105 — прямая отправка голосовой команды

Scope разрешён владельцем05.11; локальные проверки завершены06.11.2026.
Canonical `C:/Users/user/Desktop/PlatformaCRM`, `codex/ui-testing-toolkit`,
HEAD `66101d509cb7642b2928275e48c4b64354abf07b` + task-owned dirty delta.
Это изменение прежнего review-сценария по явному решению владельца, а не
разрешение новых операций, deployment или working-DB миграций.

## Получившееся поведение

Записать → «Отправить» → разрешённая команда либо необходимое уточнение →
результат со ссылкой. Расшифровка и повторная кнопка подтверждения не показываются.
Лимит60сек останавливает микрофон, но ничего не отправляет автоматически.
Текстовый fallback, отмена позднего STT, явный повтор после сетевой ошибки и
передача явно выбранной карточки сохранены. Потерянный ответ на отправку повторяется
с тем же ключом; успешная операция обновляет связанные CRM query caches.

Исходный запрос с приветствием и просьбой уже содержал «позвонить поставщику»,
но router спрашивал название. Теперь router выбирает операцию, а field planner
проверяет поля; для одного действия route сохраняет исходную реплику целиком.
Описание работы является названием, пустое «создай задачу» вызывает вопрос.
Устранено противоречивое языковое указание для структурированных планов;
значения полей сохраняют исходный язык. Отдельная модель пунктуации пропущена
только при `format_text=false`; обычный API default совместим с прежними callers.

`execution=direct` разрешён только private voice/work. Точный proposal, approval
и доменный write одного шага фиксируются одной транзакцией. Сервер сохраняет
права AI_PIPELINE APPROVE/EXECUTE, доменные права, tenant, текущую версию, слот,
отзыв доступа, отмену, replay и audit rollback. Approval payload различает
`voice_direct_submission` и `review`; он не утверждает просмотр карточки.
Два связанных шага client→appointment выполняются последовательно, а не общей
транзакцией; неуспех второго не удаляет выполненный первый. Остальные AI callers
и старые review-предложения сохраняют кнопочное подтверждение.
Удаление/архив, массовые операции, неявка, деньги и права не добавлялись.
Notification/BusinessEvent/domain services переиспользованы без новых эффектов.

## Проверки

План, baseline исходников/документов, начальный Git, собственный patch и SHA256:
`output/voice-direct-20261105/`. Все DB/browser runs используют
`scripts.codex_verify.isolated_runtime`, disposable SQLite, отдельные порты и
синтетические записи; обычный `db.sqlite3` не менялся.

- `check_backend.py direct-fixed apps.ai_core.tests_voice_direct.VoiceDirectTests`:
 8 PASS, system/drift PASS до зависимого UI. Затем добавлены role/linked-step случаи.
- `check_backend.py affected` с voice-direct/interface, conversation-execution,
 voice-policy, planner, speech, voice-language:70 PASS, system/drift PASS на
 промежуточной реализации. Не подменяет следующий финальный прогон.
- `.venv/Scripts/python.exe output/voice-direct-20261105/check_backend.py final
 apps.ai_core.tests_voice_direct.VoiceDirectTests apps.ai_core.tests_voice_interface
 apps.ai_core.tests_conversation_execution apps.ai_core.tests_conversation_state
 apps.ai_core.tests_approval_binding apps.ai_core.tests_crm_tools
 apps.ai_core.tests_voice_policy apps.ai_core.tests_crm_planner
 apps.ai_core.tests_speech apps.ai_core.tests_voice_language`:
 **113 PASS**, `manage.py check` PASS, `makemigrations --check --dry-run` PASS.
 Проверены direct/create/replay, staff flag denial, foreign context, role denial,
 missing field, cancellation/revocation during provider, audit rollback/explicit
 retry, client→appointment, прежние review/approval/domain guards и privacy audio API.
- `.venv/Scripts/python.exe output/voice-direct-20261105/concurrency.py`: PASS.
 Два одновременных start с одним ключом создали один turn/job; конкурентный commit
 дал completed/PermissionDenied, одну Task и один ApprovalRequest. Это SQLite
 file-DB concurrency, не сертификация production PostgreSQL/worker recovery.
- `run.py --browser`:7 PASS, RU1440/KK390/EN390, keyboard Send/Escape, no transcript/
 confirm, cancellation of late STT, lost-response retry same key, microphone denial,
 real60sec limit without automatic submission. После найденного по коду состояния
 двух Send при STT fallback выполнен `run.py --browser --grep 'recognition failure|microphone denial'`:
 2 PASS на финальном UI. Итого8 различных scoped browser cases; снимки проверены.
- `.venv/Scripts/python.exe output/voice-direct-20261105/run_live.py`: PASS,
 настоящий OpenRouter STT + текстовая модель, Chromium file-microphone с20.92сек
 синтетической RU речи → непосредственная Task с названием и всеми деталями
 середины/конца. Нет textarea или confirm. Наблюдаемый Send→result8.071сек,
 включая UI ожидание/снимок; это единичная проба, не SLA и не человеческий микрофон.
 `live-result.json`, `live-completed.png` содержат результат синтетической фикстуры.
- `.venv/Scripts/python.exe output/voice-direct-20261105/probe.py`: финальная
 реальная модель,4 сценария/5 реплик PASS: исходная фраза с приветствием,
 пустой запрос→уточнение→ответ и создание, EN и KK. Проверяются completed и
 точные названия на исходном языке; результаты в `final-command-probe.json`.
- `.venv/Scripts/python.exe output/voice-direct-20261105/queue_flow.py`:7/7 PASS,
 Task/Client/Note/search/booking/move/cancel, direct submit replay. Реальная модель,
 Celery solo worker, memory broker, eager=False, все7 jobs succeeded. Поиск проверяет
 реальные source ID/имя; доменные записи проверяются после действий.2.92–4.56сек
 на команду в этом прогоне, без STT; не Redis/production acceptance.
- `.venv/Scripts/python.exe output/voice-direct-20261105/run.py --build`:
 финальные types/build/widget/i18n6898 PASS (`build-1793905472785593700.log`).
 Первый build PASS до последней правки fallback; повтор обоснован этой правкой.
 `npm.cmd run check:bundle` из frontend: PASS app-shell<400kB; остаются предупреждения
 RU/KK chunks>500kB. Новых dependencies нет. Capture/audio Node checks не повторялись:
 capture/worklet/encoding не менялись, их предыдущая граница сохранена в VOICE-REBUILD.

## Сохранённые неуспешные попытки

Начальный `direct-0.log`: новый тест случайно импортировал весь foundation TestCase,
обнаружив также сторонний `test_ai_tool_suggest_logs_actions_without_execution`
(2 suggestions при ожидании>=3). Этот отдельный старый endpoint не входит в scope;
его assertion не менялся и общий full-project PASS не заявляется. В собственных
фикстурах исправлены null tool для вопроса и повторный setUp с дублирующим email;
focused rerun8 PASS и final113 PASS показаны отдельно.

`probe-before-empty-fix.log`: после исправления маршрута модель назвала пустую
задачу «Создай задачу». Исправлен field-planner contract. Следующая проба выявила
перевод EN-названия; устранено противоречие инструкции языка и lossy routed step.
Исходные пробы сохранены (`probe-before-language-fix.log`, `probe-before-atomic.log`).
Первый live browser run завершился без панели после обновления UI-исходников во
время записи; `live-browser-hmr-failure.log`/`live-results-hmr` сохранены.
Чистый повтор на неизменном коде прошёл. Ошибка не маскируется повышением таймаута.

## Публикация и остаток

Index пуст, существующий `.git/index.lock`04.11 сохранён;17 чужих outgoing commits
не включались в публикацию. Remote main проверен через ls-remote:
`0b3348e1ab31121a106badbde830b496ec477aac`. Собственного commit/push/нового CI нет;
публикация блокирована lock/чужой исходящей историей. Внешние deployment и
workingDB/env изменения не выполнялись; прежние dev-процессы сохранены.

В принятом scope кода и локальных проверок остатка нет. Полный D01 остаётся открыт:
human RU/KK/mixed/noise, предметная приёмка и production broker/recovery/rollout
не закрываются синтетическими пробами. Roadmap ↔ voice/AI/CRM/frontend contracts ↔
паспорт ↔ evidence обновлены. README изменён из-за нового наблюдаемого flow;
access/operations не требуют правки: grant matrix, schema, setup/environment
не менялись. Новый этап или расширение списка команд этим не разрешены.

Финальная scoped проверка diff/новых файлов, добавленных ссылок, регистрации
и secret signatures PASS; source SHA256 совпадают с проверенным срезом.
Все собственные runners завершены. `owned-final.patch`/`final-hygiene.json` сохранены.
