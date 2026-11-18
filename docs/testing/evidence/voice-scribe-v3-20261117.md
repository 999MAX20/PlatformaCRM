# VOICE-SCRIBE-V3-20261117: прямое подключение и synthetic-проверка

## Текущее состояние, 18.11.2026

Подключение Scribe v3 проверено на трёх коротких вымышленных русских фразах.
Рабочая активация для клиентских данных НЕ выполнена. 56 изолированных тестов,
Django system check и migration drift прошли. Ключ сохранён только в локальном
gitignored .env. Ограничения ключа проверены в ElevenLabs: только Speech to Text,
5000 кредитов за период, истечение19Nov15:53 по отображению кабинета, автоотключение
при обнаружении утечки включено. Остальные права No Access.
Владелец разрешил18Nov synthetic-тесты без Zero Retention и максимум5000 кредитов.
В кабинете Analytics/Usage после проверки:3 billable requests,14s,8 credits,
average2.67 credits/request. Остаток согласованного тестового бюджета4992.
Пополнение/подписка/автопополнение не включались.

Начальная подготовка17Nov:4cc19068, без тестов по тогдашнему указанию.
Продолжение18Nov: canonical C:/Users/user/Desktop/PlatformaCRM,
codex/ui-testing-toolkit; HEAD48f201be при старте проверки, затем чужой CI commit
58a6427e. Ранее подготовленный voice diff сохранён; чужие Meta footer PRIMARY
не входят в эту задачу. Текущие проверки относятся к unchanged voice source.

## Реализация и защита реальных данных

- Fixed model scribe_v3, direct HTTPS multipart WAV, bounded in-memory transport.
- Рабочий build_request всегда использует enable_logging=false.
- ELEVENLABS_SCRIBE_ENABLED и ELEVENLABS_SCRIBE_PRIVACY_CONFIRMED default False.
  Ключ сам по себе не включает отправку. Существующий provider=openrouter сохранён.
- Privacy flag фиксирует внешнее подтверждение Enterprise STT ZRM/no-training,
  а не техническое доказательство условий аккаунта. Для текущего free-аккаунта
  такое подтверждение не получено, флаг не установлен.
- Неизвестный provider/выключенный AI/voice/неполная конфигурация дают отказ до сети.
  Прежние backend role/Business permissions и подтверждения CRM сохранены.
- No redirects, retries, fallback, raw audio/text/key logging; response64KB/text4000,
  WAV mono16kHz PCM16 до2MB/60s. Нет SDK/dependency/schema изменений.
- Прямой STT не использует баланс OpenRouter; planner остался отдельным.

Только локальный ignored output/voice-scribe-v3-20261117/live_synthetic.py
строит запрос с enable_logging=true. Это одноразовый инструмент проверки,
не imported application code, не env-флаг и не публичный API.
Он генерирует три фиксированные фразы локальным Microsoft Irina Desktop:
не принимает произвольный файл, текст, микрофон или CRM-сущность.
Повтор отсекается существованием live-20261118.json, не более3 запросов/30с,
ошибка останавливает серию; дополнительный provider cap5000.
Test-only mock is_configured позволяет переиспользовать multipart builder;
настройки ENABLED/PRIVACY остаются False, readiness проверен False до/после.
Эта проверка доказывает transport/model/parse, не рабочий customer API без ZRM.

## Проверки

Из корня, установленный .venv/Scripts/python.exe:
- output/voice-scribe-v3-20261117/verify.py, через scripts.codex_verify.isolated_runtime:
  manage.py check; makemigrations --check --dry-run; test следующих модулей:
  apps.ai_core.tests_elevenlabs_speech, tests_speech, tests_speech_audio,
  tests_speech_diagnostics, tests_speech_numbers, tests_speech_formatting,
  tests_voice_interface. 56 тестов PASS,51.572с; system0issues, drift none.
  Отдельная disposable SQLite, сеть provider mocked, ключ пуст.
- output/voice-scribe-v3-20261117/live_synthetic.py --live:
  отдельный isolated_runtime, реальный ключ только в памяти процесса;
 3 HTTP200, без OpenRouter/TTS API/CRM mutations.
- Source/diff review, git diff --check, registry JSON, local link existence.
  UI Delivery Gate N/A: продуктовый интерфейс не менялся.

| Synthetic case | Seconds | API elapsed | Результат |
| --- | ---: | ---: | --- |
| Создай тестовую задачу проверить расписание завтра | 4.780 | 1.453 | Смысл и слова сохранены |
| Перенеси вымышленную встречу на завтра на пятнадцать тридцать | 5.145 | 1.281 | Завтра и15:30 сохранены словами |
| Тестовый номер ноль ноль один один два два три три | 4.315 | 1.344 | Все восемь цифр и повторы сохранены |

Суммарно14.24с. Полный synthetic transcript в локальном live-20261118.json.
Это не пользовательские данные. Сервис ничего в CRM не создал/не перенёс.
Попытка генерации до сети сначала дала audio_format: System.Speech возвращал PCM
без WAV header. Исправлен только test harness: PCM упакован в WAV через wave.
До исправления запросов провайдеру не было. Живые запросы не повторялись.

Локальные артефакты: CHECKPOINT.md, verify.py, verification-20261118.log,
live_synthetic.py, live-20261118.json/log в output/voice-scribe-v3-20261117.
Секрет не включён в tracked source/evidence; временный ключ переноса удалён.

## Граница приёмки и остаток

Scope подключения и первых synthetic-проверок завершён локально.
Реальные клиенты/аудио не использовались; рабочая БД, миграции, серверы и deployment
не затронуты. Прежние accuracy failures и D01 не закрыты.
Код: нового рабочего privacy bypass нет. Доказательства: широкая точность RU/KK/mixed,
шум/живые голоса/имена/телефоны и полный voice->CRM flow этим набором не покрыты.
Среда: Enterprise STT ZRM/no-training для real data не подтверждены; тестовый ключ
короткоживущий. Решение владельца: рабочая активация и дальнейший объём отдельно.
Frontend/access/CRM contracts без изменений: публичный API/права/flow прежние.
Operations/voice/README/roadmap/passport/STATUS синхронизированы с этим срезом.

Официальные условия:
- https://elevenlabs.io/docs/api-reference/speech-to-text/convert
- https://elevenlabs.io/docs/eleven-api/resources/zero-retention-mode

Publication записывается в checkpoint отдельно; local/live PASS не означает deploy.
