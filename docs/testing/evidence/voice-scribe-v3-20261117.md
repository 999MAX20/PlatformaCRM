# VOICE-SCRIBE-V3-20261117: прямое подключение и synthetic-проверка

Current result: expanded19 RU/KK/mixed requests completed; accuracy failures remain.
Total97/5000 credits used,4903 remaining. See expanded acceptance below.
The initial three-clip section records the earlier snapshot.

## Initial three-clip snapshot, 18.11.2026

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

## Expanded synthetic acceptance — 18.11.2026

Owner authorized RU/KK/mixed, names, numbers and dates with 4992 credits remaining.
Source a3753708; production voice code unchanged from b5dde74b. Prior56 isolated
tests reused as unchanged-source evidence, not rerun. No production activation.

19/19 HTTP200; 163.111 seconds audio, no retries. Command (PYTHONPATH=root):
`.venv/Scripts/python.exe output/voice-scribe-v3-20261117/expanded_synthetic.py --live`
Exit0 proves transport only. Synthetic corpus:7 RU Microsoft Irina/Pavel clips,
6 KK and6 mixed kk-KZ-AigulNeural/DauletNeural clips, reused from11Nov.
KK/mixed SHA256 verified against historical native-manifest; all WAV hashes pinned.
Fixed two corpus directories; <=24 requests/400seconds, exclusive report marker,
isolated runtime. No new TTS, OpenRouter, real client data, CRM writes or deployment.
Production enable/privacy flags and readiness remain False before/after. Logging=true
exists only in this ignored synthetic harness, not application API/configuration.

| Group | Requests | Exact client names | Normalized phones |
| --- | ---: | ---: | ---: |
| ru | 7 | 6/6 | 4/6 |
| kk | 6 | 4/5 | 4/4 |
| mixed | 6 | 3/5 | 2/5 |

Specialist names3/5; task titles2/3 (RU control reviewed manually).
All5 spoken dates/times preserved by manual transcript comparison:
kk-booking2030-11-07 12:00; mixed-booking2030-11-08 10:00;
kk-conflict2030-11-09 12:00; mixed-conflict2030-11-10 12:00;
ru-booking-two-names2030-11-09 10:00. This does not verify date parser/planner/CRM.

Failures retained without transcript correction:
- kk-client-auto, mixed-booking, mixed-conflict: Kazakh name spelling changed;
  mixed-task: final Kazakh letter in first title word changed.
- mixed-digits: spoken digit values preserved but commas prevent application phone
  normalization. mixed-booking: grouped seventy-seven preserves prefix value but
  compound numbers are unsupported by the normalizer.
- mixed-conflict: repeated Kazakh twos recognized as Russian ones: actual digit error.
- ru-male-voice, ru-eight-prefix: grouped number words change digit sequence as well
  as preventing normalization; blind concatenation cannot repair these safely.
- mixed-eight: command words distorted despite preserved name/phone.

Synthetic pronunciation may contribute; these results do not establish live-human
accuracy or comparative model superiority. Recognition acceptance remains FAIL.
Noise/live voices and full voice-to-CRM flow remain unverified. Follow-up needs phone
handling/ambiguity confirmation and further fictional voice checks; no product fix
was included in this verification scope. Enterprise STT ZRM/no-training and production
activation remain separate. Existing privacy/customer-data protection unchanged.

ElevenLabs authenticated Analytics/Usage:22 billable requests,97credits,3m rounded,
4.41credits/request. Prior3 requests cost8: expanded series89 credits; remaining
5000-97=4903. No additional calls. Budget is cumulative, not reset per run.
Local ignored artifacts: expanded_synthetic.py, expanded-corpus.json,
expanded-live-20261118.json/log under output/voice-scribe-v3-20261117.
No secrets in tracked evidence. Test execution scope complete, quality failures open.

Median request 2.235s; range 1.297–4.641s.
