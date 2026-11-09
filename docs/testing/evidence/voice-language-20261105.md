# VOICE-LANGUAGE-20261105 — локальное доказательство языкового поведения

Срез 05.11.2026: canonical PlatformaCRM, codex/ui-testing-toolkit,
HEAD `66101d509cb7642b2928275e48c4b64354abf07b` + существующий WIP.
Этот отчёт создан при завершении VOICE-CARD-CONTEXT; языковой код уже существовал,
в этой задаче не менялся. Он заменяет отсутствовавшую ссылку на доказательство,
не восстанавливает неизвестный результат прежнего запуска.

Команда: `.venv/Scripts/python.exe output/voice-card-context-20261105/check_backend.py affected apps.ai_core.tests_voice_language apps.ai_core.tests_voice_policy apps.ai_core.tests_voice_interface apps.ai_core.tests_conversation_execution apps.ai_core.tests_speech`.
39 tests PASS, включая 4 VoiceLanguageTests; изолированные SQLite/settings,
mock provider; system check PASS, migration drift: No changes detected.
Журналы: `output/voice-card-context-20261105/affected-{0,1,2}.log`.

Подтверждено: приветствие возвращает фиксированный ответ по языку сотрудника
RU/KK/EN без источников и действий; схема отвергает произвольные факты/действия
в greeting; приветствие перед командой не отменяет обязательное подтверждение;
вопрос о бизнесе без данных сохраняет no-data и не выдумывает источники.

Не подтверждено этим прогоном: реальное распознавание, отсутствие перевода,
качество RU/KK/mixed/шума и маршрутизация текущего Whisper Large V3 Turbo.
[Прежний live-срез](voice-live-20261105.md) использовал Large V3 и синтетическую
русскую запись. Он не сертифицирует Turbo, физические микрофоны или весь D01.
Рабочая БД, провайдер, исходные аудио и настройки среды не изменялись.
Публикация/CI/deployment этим отчётом не заявляются.
