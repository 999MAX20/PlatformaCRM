# VOICE-RECOGNITION-20261111 — имена и телефоны

Поручение: исправить ошибки распознавания имён и телефонов; проверить на синтетических
записях. Canonical PlatformaCRM, codex/ui-testing-toolkit, исходный2e715377.
Изменены STT default и сохранение отдельных цифр; права/доменные команды/UI неизменны.

## Причина и изменение

На одинаковых исходных WAV Whisper Turbo повторно дал «Канни» вместо «к Анне»
и770222222222 вместо77022222222. Large V3 повторил искажения. Qwen ошибся в имени;
Chirp3 дал «к Ане» вместо «к Анне» в одном из двух примеров. GPT4o Transcribe и
Gemini вернули404 при текущей ZDR-политике. Scribe v2 сохранил оба имени и11 цифр.
Отказ провайдера не обходится ослаблением приватности.

Default теперь `elevenlabs/scribe-v2`, temperature0; явный VOICE_TRANSCRIPTION_MODEL
сохраняется. Один STT-запрос, без платного fallback/retry. После распознавания
явно обозначенный телефон из7–15 отдельных цифр RU/KK/EN переводится в цифровую
строку один-к-одному. Нет догадок по базе, подстановки имён, восстановления
пропусков, преобразования групповых числительных или изменения дат/обычного текста.
Форматирование и UI flow сохраняются, direct capture по-прежнему format_text=false.

## Синтетический набор и границы

`output/voice-recognition-20261111/corpus.json`, WAV SHA256 в audio-hashes.json.
10 файлов,86.553с:2 исходных сбоя, новые имена, повторяющиеся/смешанные цифры/нули,
номер с8, мужской/женский голос, сниженный темп, казахское имя в русской фразе,
английский auto и контрольная Task. Windows Irina/Pavel/Zira; не человеческая речь.
Scribe STT-corpus:10/10 точных имён/цифр;1.578–3.031с, медиана2.078с на этом наборе.
Usage провайдера для10 файлов:$0.005289, около$0.00367/мин против прежних$0.000200/мин
WhisperTurbo (примерно18.35раз). Это измеренный usage, не обещание тарифа или SLA.
Настоящая KK/смешанная речь, микрофоны и шум не проверены; KK-цифры — unit evidence.

Исследование API: [OpenRouter STT](https://openrouter.ai/docs/guides/overview/multimodal/stt).
Фактические bounded ответы: comparison-initial/large-v3/alternatives/scribe.json,
corpus-scribe.json. Ключ не сохраняется, реальная клиентская информация не отправлялась.

## Проверки

Из канонической папки, существующий .venv и scripts.codex_verify.isolated_runtime:

- `.venv/Scripts/python.exe output/voice-recognition-20261111/check.py focused apps.ai_core.tests_speech apps.ai_core.tests_speech_numbers`:12PASS, check/driftPASS.
- `check.py dependent apps.ai_core.tests_speech apps.ai_core.tests_speech_numbers apps.ai_core.tests_voice_policy apps.ai_core.tests_voice_direct apps.ai_core.tests_voice_booking_intent apps.ai_core.tests_voice_schedule apps.ai_core.tests_voice_identity apps.ai_core.tests_voice_locations apps.ai_core.tests_voice_interface apps.ai_core.tests_voice_language`:118PASS, check/driftPASS. Покрыты запреты/tenant, отказ провайдера, приватность, replay, связь записи и клиента, язык, direct flow.
- `.venv/Scripts/python.exe output/voice-recognition-20261111/live.py`: итоговый10/10PASS,
  реальные Scribe v2 и gpt-4o-mini, disposable SQLite/API, synthetic data/eager.
  Шесть Client с точными именами/номерами; две Appointment с нужным Client/Resource
  и временем; конфликт телефона clarifying без записи; одна Task. Каждый replay
  сохранил turn ID и счётчики. Имена сверены дословно, телефоны — по всем цифрам.
- Первый liveAPI прогон: original-booking и original-repeated-phone PASS включая
  replay; ru-mixed-digits имеет точный transcript, но статус failed на планировании.
  Исходные лог/результат сохранены. Диагностический прогон прерван ошибкой JSON
  сериализации datetime в тестовом отчёте; исправлен только harness (default=str).
  На полном повторе тот же клиент и остальные9 сценариев прошли, job_errors пуст.
  Причина первого сбоя планировщика в этом срезе не установлена; он не объявляется
  исправленным, не удалён из evidence и ограничивает общий вывод о надёжности LLM.
  Это не повторная ошибка имени/телефона: исходный transcript был точным.

Рабочая БД/миграции/env/deployment не менялись. Frontend build/browser/full project
не запускались: UI и доменные контракты не менялись; проверяется реальный API flow.
PG/queue повторно не проверяются: транзакции/очередь не изменены, не release gate.
Human/полный D01/production остаются открытыми. Публикация пока не выполнена;
fetch подтверждает32 чужих исходящих коммита, они не разрешены к публикации.

## Итоговый сквозной срез

| Сценарий | Результат | STT,с | Всего,с |
| --- | --- | --- | --- |
| original-booking | completed; replay PASS | 2.516 | 6.844 |
| original-repeated-phone | clarifying; replay PASS | 2.25 | 6.687 |
| ru-mixed-digits | completed; replay PASS | 1.437 | 5.25 |
| ru-zeros | completed; replay PASS | 2.657 | 6.969 |
| ru-male-voice | completed; replay PASS | 1.656 | 5.828 |
| ru-kazakh-name | completed; replay PASS | 1.844 | 5.86 |
| ru-eight-prefix | completed; replay PASS | 2.484 | 6.734 |
| en-auto | completed; replay PASS | 1.734 | 5.593 |
| ru-booking-two-names | completed; replay PASS | 2.188 | 7.172 |
| ru-task-control | completed; replay PASS | 2.093 | 6.047 |

Финальные source SHA256: output/voice-recognition-20261111/verified-inputs.json;
подробные команды/процессы/неудачные попытки: CHECKPOINT.md в той же папке.
Код и локальная проверка распознавания в согласованном scope завершены. Остаток:
человеческая/KK/смешанная речь/шум и общая стабильность планировщика — доказательства;
production rollout и broker — среда; публикация собственного commit без чужой
истории заблокирована. Нового решения о доменных правилах не требуется.
