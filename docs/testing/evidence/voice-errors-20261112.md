# VOICE-ERRORS-20261112 — ошибки и безопасная диагностика

## Объём и результат

Поручение владельца: реализовать понятные ошибки и безопасную диагностику, проверить
без платных вызовов OpenRouter. Канонический checkout:
`C:/Users/user/Desktop/PlatformaCRM`, ветка `codex/ui-testing-toolkit`, начальная
база `372ec4f8`; параллельный HEAD перед закрытием `1fa364b0`.

Различаются payment/timeout/unavailable/rate limit/configuration/no speech/invalid
response/audio errors. RU/KK/EN используют фиксированный текст без содержимого
провайдера. STT-ошибка не маскирует отказ дальнейшего действия CRM. Временный сбой
сохраняет запись в памяти и допускает явный повтор; Retry-After выдерживается.
Постоянный отказ блокирует повтор этой записи, доступны удаление/новая запись/текст.
Автоповтора и новых платных запросов не добавлено.

Структурированные события содержат этап, модель, статус, длительность, время до
заголовков, локальный request_id и допустимые provider/generation IDs. Нет аудио,
расшифровки, prompt, тела ошибки, URL, заголовков или ключей. Форматтер принимает
новые поля только для двух событий speech logger. Новых схем/настроек нет;
права, tenant scope, CRM подтверждения, BusinessEvent/notifications не меняются.

## Проверки

Все команды из канонического checkout; backend через `.venv/Scripts/python.exe`
и `scripts.codex_verify.isolated_runtime`, одноразовая БД/порты. Логи и harness:
`output/voice-errors-20261112/`.

- `check.py focused apps.ai_core.tests_speech_diagnostics`: 5 PASS, system/drift PASS.
- `check.py dependent` с speech, speech_audio, speech_formatting, voice_interface,
  core observability: 47 PASS, system/drift PASS; полные labels в командах harness.
- `check.py api-errors apps.ai_core.tests_speech.SpeechTests.test_api_error_codes_are_safe_and_never_create_commands`:
  1 PASS, system/drift PASS. API возвращает только code/retryable; команд/AI logs не создаёт.
- Node: 3 проверки voice-speech-errors и 7 существующих appError PASS; после исправления
  несовместимого Object.hasOwn повторены 3 затронутые проверки PASS.
- `frontend_verify.py`: i18n PASS (7249 keys). Первый types FAIL из-за Object.hasOwn
  сохранён; заменён на hasOwnProperty.call.
- `frontend_complete.py`: финальные tsc -b --force, app/widget vite build,
  check-bundle PASS. Сборки в dist-final/dist-widget, dependencies не переустанавливались.
- `browser_runtime.py`: 15 PASS, RU1440/KK320/EN390, fake microphone, реальные
  локальные login/API с перехваченными speech/conversation responses. Payment,
  timeout, invalid response, keyboard retry, CRM denial проверены; screenshots просмотрены.
- `browser_extra_runtime.py`: 2 PASS — Retry-After countdown/явный повтор и переход
  к тексту с очисткой ошибки/фокусом/возвратом фокуса после Escape. Первый harness FAIL
  из-за проверки счётчика до async submit сохранён; исправлен bounded wait, продукт не менялся.
- Дополнительный кандидат без прежнего неопубликованного Carbon-эксперимента проверен: **38 PASS**, без skip.
  `check_index.py`: модуль speech компилируется из подготовленного текста в памяти,
  checkout не подменяется. Первый harness запуск без DJANGO_SETTINGS_MODULE упал
  до тестов; сохранён отдельно и исправлен.

Платных вызовов: **0**. Backend provider замокан; браузерный backend имеет пустой
ключ и запрещённый urlopen для speech, запросы распознавания перехвачены. Нет
рабочих DB изменений/миграций, env/default изменений или deployment. Собственные
браузерные runtimes завершены. Это проверка ошибок, не повтор качества STT.

## Граница закрытия

Код/локальные доказательства понятных ошибок и безопасной диагностики выполнены.
Старые два live-таймаута, точность KK/mixed, человеческая речь, fullD01 и production
остаются отдельными открытыми границами. Новая диагностика не устанавливает задним
числом точную причину прежних сбоев. Неопубликованный speech candidate и другие
чужие изменения сохраняются в рабочем дереве и не входят в этот коммит.

Публикация ограничена чужим исходящим диапазоном: own-only normal push невозможен
без публикации чужих коммитов. Новый CI/deploy не запускались. Точный commit и
финальная проверка кандидата записаны в checkpoint.

Обновлены voice contract, frontend/operations, roadmap, AI passport, registry,
STATUS и PRIMARY. README не требует изменения: setup/default не меняются;
CRM/access/AI domain contracts не меняются.
