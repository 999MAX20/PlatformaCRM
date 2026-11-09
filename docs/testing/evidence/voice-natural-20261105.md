# VOICE-NATURAL-20261105 — диктовка и естественный диалог

Владелец сообщил о потерянных словах и запросил полную диктовку с пунктуацией,
естественные ответы GPT-4o mini и сохранение CRM-команд. Реализовано локально в
`C:/Users/user/Desktop/PlatformaCRM`, `codex/ui-testing-toolkit`, HEAD `66101d50`
плюс scoped dirty delta. Базовые снимки, план, patch/hashes и логи:
`output/voice-natural-20261105`. Большой чужой WIP сохранён.

AudioWorklet загружается до открытия микрофона. Stop ждёт завершения передачи
PCM; отмена отбрасывает поздний результат, timeout не отправляет неполный звук.
После STT отдельный GPT-4o mini запрос добавляет пунктуацию. Проверяется точное
совпадение нормализованных слов/чисел и порядка; при изменении или ошибке остаётся
оригинал. Нераспознанные STT слова этот шаг не восстанавливает.

Голосовые greeting/chat теперь используют реальную GPT-4o mini без mock fallback,
CRM tools и фиктивных источников. История ограничена шестью доступными ходами
того же пользователя/Business/диалога/эпохи. CRM запросы сохраняют источники,
права, подтверждение и replay. Изменения прав, моделей БД, миграций, уведомлений,
BusinessEvent и рабочего окружения отсутствуют.

Проверки в изолированном SQLite/runtime, существующие зависимости:

- `.venv/Scripts/python.exe output/voice-natural-20261105/check_backend.py chat apps.ai_core.tests_voice_language apps.ai_core.tests_voice_interface` — 16 PASS; system/drift PASS.
- Тот же runner `punctuation apps.ai_core.tests_speech_formatting apps.ai_core.tests_speech` — 12 PASS на первоначальных трёх formatting-тестах; `private-format apps.ai_core.tests_speech_formatting` — окончательные 4 PASS; system/drift PASS.
- Тот же runner `affected apps.ai_core.tests_voice_language apps.ai_core.tests_voice_interface apps.ai_core.tests_voice_policy apps.ai_core.tests_speech apps.ai_core.tests_speech_formatting apps.ai_core.tests_conversation_api apps.ai_core.tests_conversation_state apps.ai_core.tests_conversation_execution apps.ai_core.tests_conversation_memory apps.ai_core.tests_agent_runtime apps.ai_core.tests_prompt_preferences` — 84 PASS; system/drift PASS.
- `node --test frontend/scripts/tests/voice-audio.test.mjs` — 5 PASS, включая finish/flush.
- `.venv/Scripts/python.exe output/voice-natural-20261105/run.py --browser` — 6 PASS, RU desktop/KK+EN mobile, запись/отмена/повтор/редактирование/подтверждение/настройки/роль; STT подменён в этом наборе.
- `.venv/Scripts/python.exe output/voice-natural-20261105/run_live.py` — 1 PASS с настоящим OpenRouter: естественное приветствие, честный отказ назвать текущую погоду, browser microphone→Turbo→пунктуация→preview→confirmed Task. Синтетическая русская речь, 4.64сек; все шесть слов получены: «Создай задачу с названием „Позвонить поставщику“». API подтвердил completed и название созданной задачи, аудиотреки остановлены. Скриншот completed снят до завершения перерисовки и сам по себе не доказывает итог; доказательство — проверенный ответ API.
- `.venv/Scripts/python.exe output/voice-natural-20261105/run.py --build` — i18n/types/app+widget build PASS. Известное предупреждение chunk >500kB сохранено.

Первый live-прогон получил лишнее начало повторяющегося fake microphone файла;
assertion полного совпадения слов упал. Fixture дополнен тишиной, assertion не
ослаблен; окончательный прогон PASS. Исходный лог сохранён. На длинном synthetic
образце Turbo ошибся в слове «бро»; идеальное распознавание не заявляется.
OpenRouter mini-transcribe несовместим с текущим privacy route; политика не ослаблена,
STT остаётся Turbo. [Официальный STT-контракт](https://openrouter.ai/docs/guides/overview/multimodal/stt).

Неотправленная расшифровка форматируется в памяти без AIRequestLog; OpenRouter
получает ZDR/no-data-collection. Отправленные диалоги используют обычную историю
и учёт AI-запросов. Дополнительный запрос пунктуации добавляет задержку.

В принятом scope код и локальные проверки завершены. Живая человеческая речь
RU/KK/mixed/шум, production broker/recovery и полный D01 остаются открытыми;
полный E2E/release gate не запускался без основания. Рабочая БД, env и deployment
не менялись. README/setup/access/product изменений не требуют; контракт AI,
voice/frontend/operations, roadmap, паспорт и реестр evidence синхронизированы.
Существующий `.git/index.lock` от04.11 и17 чужих outgoing commits блокируют
собственную публикацию: commit/push/new CI не выполнены, lock/history сохранены.
