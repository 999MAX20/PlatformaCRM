# VOICE-SCRIBE-V3-20261117: прямое подключение и synthetic-проверка

## Live dialogue pilot 20261118

Owner explicitly approved200 ElevenLabs credits and$0.15 OpenRouter for the four
pilot dialogues. [Raw results, model outputs, usage and adjudication](voice-scribe-v3-pilot-20261118.json).
Source0dfbffa5; no application source or production settings changed. Only fictional
data, a disposable SQLite DB and the fixed synthetic clock were used. Existing
customer-audio activation/privacy flags remained false. The synthetic-only ElevenLabs
logging exception was applied only to test requests, as previously authorized.

Outcome:12 dialogue/track combinations started,0 fully correct;16 of24 planned
turns scored, with later turns skipped after a mismatch. One male-track cancellation
request timed out and was not retried. The sole not-yet-started male mixed dialogue
was then attempted with the same ledger/caps; no previous request was replayed.
This small deliberately difficult sample is not a population accuracy estimate.

Concrete failures:

- Even perfect text did not produce reliable understanding. The planner retained
  the Kazakh accusative surname `Сынақты` instead of `Сынақ` in one initial request.
  The same initial text in another dialogue was handled correctly, demonstrating
  variation at the configured temperature0.4.
- The name correction produced a top-level client-name patch AND an invalid
  visit-level `client_name`. The server rejected it with `invalid_action_plan`.
- A request to change the final phone digit from8 to9 returned the original full draft;
  the draft still contained the old number. Review prevented execution.
- Negated booking routed to `appointments/create` on reference text and both
  voices. It stopped at a missing-specialist question, not at a semantic rejection.
  No writes is therefore insufficient to call this a correct refusal.
- Six of nine successful STT transcripts have zero normalized word errors, but
  the planner dropped the ambiguous fictional surname in the clean KK examples.
  Mixed RU/KK speech changed `Әсел Сынақ` to `Асель Снаг` / `Осель Снах`.
  Female speech changed `Алдыңғы әрекеттен бас тарт` to `Алдыңғы әрекеттен баста`.
  These are separate ASR and planner failures. Repeated phrases/voices are correlated,
  and `Сынақ` is also a common word: do not generalize this name sample to all KK names.

The D03 runtime evaluator originally checked no writes/tools but missed the booking
route/draft. Manual review tightened scoring to the original `no_booking_proposal`
expectation. The original runtime result is retained next to adjudication. Its second
turn was already executed despite the first semantic failure; this evaluator defect
is disclosed, not hidden by calling the no-write outcome PASS. No further paid rerun.
No incorrect proposal was confirmed and no Client/Appointment/Task was created in
the live runs. Domain confirmation/replay paths were exercised in the offline harness.

Cost/control evidence:

- OpenRouter:31 successful API requests,66,771 prompt tokens +2,316 completion
  tokens; provider-reported total cost$0.00733485, below$0.15. Model fixed to
  `openai/gpt-4o-mini`; max output1,200, provider price ceilings$0.15/$0.60 per million
  input/output tokens, request fee ceiling0 and fallback disabled.
- ElevenLabs:10 attempted requests,9 successful +1 timeout,76.872s attempted audio.
  Conservative reserved credits92, including the timed-out request, below200.
  These reserves are not a claim of exact provider billing.16 prepared WAVs total
  97.728s; only requested clips were charged/reserved. No paid TTS used.
  Final account reconciliation was unavailable: subscription GET timed out at25/60s;
  the old browser showed cached9,070, and after reload the balance field disappeared.
  Do not interpret the cached value as zero spend or invent an exact credit charge.
- Persistent pre-dispatch reservations survive failure/resume. UTF-8 byte count
  plus1,024 framing tokens conservatively bounds input cost; actual provider usage
  settles completed LLM requests. Unknown STT charge remains reserved. No automatic
  retry, redirects, customer-data access or working-database writes.

Verification: budget reserve/reject/settle and resume-preservation checks PASS;
24 mocked harness steps PASS after fixing test-only settings/replay fixtures;
audio hashes/duration, exact persisted fields, stale approval denial, confirmation
replay and transaction rollback checked. Live commands: `pilot_run.py --live`, then
`--resume` for the sole never-started case. Logs and ledger are under the existing
local checkpoint. No application build/full suite rerun for evidence-only changes.

Next code priorities, not implemented in this pilot: reject negated booking at the
main action boundary; constrain the correction schema; detect an unchanged value
after an explicit correction and ask instead of presenting it as fixed; preserve
or clarify ambiguous names. Retest those with reference text before spending more
on speech. Human KK, live accuracy acceptance and production privacy remain open.

## Dialogue preparation 20261118

Prepared, not executed: [24 synthetic dialogues / 48 turns](voice-scribe-v3-dialogues-20261118.json),
16 KK,4 mixed and4 RU. Four pilot dialogues target time correction, Kazakh names,
negation and mixed-language phone correction. Remaining cases cover missing fields,
duplicate names, occupied slots, a selected visit in a plan, cancellation vs starting,
quoted task instructions, forbidden operations, tenant scope and date boundaries.
This is a targeted dialogue sample, not coverage of every possible voice request.

Each dialogue specifies fixture state and per-turn expected fields/status or semantic
outcome. Fixed business clock2030-11-06 10:00 Asia/Qyzylorda makes relative dates
reproducible. Three independent tracks: reference text→real planner, female synthetic
audio→Scribe→planner, male synthetic audio→Scribe→planner. Reset synthetic DB state
between tracks. Unexpected questions stop the case, rather than inventing helpful
answers. Compare raw transcription, normalized critical fields, intent, unchanged
fields, clarification, review and actual isolated mutation. Never confirm an incorrect
proposal. Report ASR and planner failures separately, plus fully correct dialogue rate
per language; no claim about live-human accuracy from synthetic voices.

Read-only account inspection18Nov: ElevenLabs Free10,000 total /9,070 remaining;
OpenRouter credits page displays$0.20. Effective local fast/smart/model settings all
`openai/gpt-4o-mini`; ElevenLabs activation/privacy flags remain false. No billing,
keys, flags or model settings changed. Key validity and per-key cap were not inspected
in this preparation and must be checked before a live run.

Planning estimate (not measured WAV or token usage): two audio voices,2 planner
requests/turn in each of3 tracks;8,000 input and1,200 output tokens/request. Current
[GPT-4o-mini pricing](https://openrouter.ai/openai/gpt-4o-mini) is$0.15/$0.60 per million
input/output tokens. [Scribe v3 PAYG](https://elevenlabs.io/pricing/api) is$0.20/hour;
this is not a conversion rate for the free-credit allocation.

| Set | STT requests / estimated audio | Credit reserve estimate | LLM requests / estimated cost incl.25% reserve | Proposed caps |
| --- | --- | --- | --- | --- |
| Pilot4 dialogues,8 turns |16 /104.4s |126 |48 /$0.1152 |200 ElevenLabs credits +$0.15 OpenRouter |
| Full24 dialogues,48 turns, including pilot |96 /579.6s |710 |288 /$0.6912 |1,000 credits +$0.75 OpenRouter |

Audio estimate assumes2.2 words/s plus1s per clip, minimum3s; credit reserve uses
ceil(estimated_seconds+1) per request from the earlier conservative harness. It is
not a verified billing formula. Full estimate exceeds the current OpenRouter balance;
the pilot fits its displayed balance. No paid TTS is included. Actual WAV durations,
exact prompt tokens and per-request reservation must be checked before calls; never
clip meaningful context merely to fit this estimate. Count attempted requests/errors,
disable automatic retries and stop before either separately approved cap is exceeded.

Preparation checks: JSON parse,24 unique IDs,48 nonempty turns,16/4/4 language split,
4 pilot IDs, fixture references, expected no-write assertions, budget arithmetic,
local links and secret/diff hygiene. No app source changed; app build/backend suites
are not rerun for this corpus/evidence-only change. The four-dialogue pilot budget
was subsequently approved and its execution is recorded above. The full24-dialogue
run remains unexecuted/unapproved; neither the earlier2,000-credit series nor the
pilot approval authorizes that expansion.

## Short corrections 20261118

Owner approved the first two additional improvements: focused clarification and
short corrections. Scope: unconfirmed booking/visit-plan drafts in the existing
voice panel, starting from46443e18 in the canonical checkout. Other integration
WIP is excluded. This does not add a new client/task correction workflow.

The latest open draft is bound to the next turn on the server and read only through
permission-filtered memory. A bounded patch changes client fields or explicitly
indexed visits; omitted fields and visit ordering are retained. Changed time needs
evidence in the latest utterance. Corrected client name/phone invalidates an old
client ID unless a newly supplied ID passes the existing selectable/access checks.
An unnamed replacement specialist asks for a choice even with one catalog option.
Continuation asks one missing field at a time. The old proposal is superseded;
the corrected proposal rechecks scheduling conditions and requires fresh review.
Cancelled/completed/reset/inaccessible drafts cannot supply patch context.

Verification (mocked providers, fictional data, disposable SQLite):

- 9 focused tests PASS,6.342s: RU time, KK name/date, selected visit in a plan,
  specialist clarification, retained fields, replay, stale approval denial,
  completed/cancelled/reset/access-changed context and foreign client denial.
- 194 affected/dependent tests:190PASS/4SQLite row-lock skips,141.739s; voice,
  speech, provider, conversation execution/memory/state/review/API. Django system
  check and migration drift PASS. No working database migrations.
- Chromium reachable flow PASS,18.6s: two successive short RU/KK corrections,
  updated name/time with service/specialist retained, no appointment until review,
  keyboard confirmation and exactly one appointment.390px screenshot captured
  and inspected: labels, wrapping, controls and focus usable, no horizontal overflow.
  Existing panel/layout/copy are unchanged; previous locale/recovery checks remain
  scoped evidence, not new runs. Initial browser failure was the fixture matching
  a prompt example instead of user messages; fixed the fake provider and used a
  distinct fictional name to avoid an unrelated existing-client match.
- Frontend `npm run build` (types/i18n/app/widget) and `npm run check:bundle` PASS.
  Existing dictionary chunk-size warnings remain; app-shell budget passes.

Commands: `.venv/Scripts/python.exe output/voice-scribe-v3-20261117/corrections_checks.py`
and `corrections_browser.py`, with repository PYTHONPATH and UTF-8. The first uses
`scripts.codex_verify.isolated_runtime`; the second starts canonical Vite/Django on
dedicated ports with a fake provider. Logs: `corrections-final-{0,1,2}.log`,
`corrections-narrow.log`, browser run1795017069987136100 under the local checkpoint.
No live STT/LLM requests or credit spend. Production audio activation/privacy flags
remain unchanged/off. Live language interpretation and human KK speech remain open;
these checks prove draft/approval handling, not new ASR accuracy or full D01 readiness.

## Improvements 20261118

Owner annotation authorizes the four follow-up improvements. Implementation is
in the canonical checkout on `codex/ui-testing-toolkit`, starting `e9f45929`;
unrelated integrations/global-search documentation WIP is excluded.

- KK fallback rejects the three reproduced negated/quoted booking examples and
  recognizes `сағат ... жаз`. Router and scheduling prompts explicitly preserve
  corrected names/times and distinguish cancellation from starting.
- Existing-client booking, rescheduling and cancellation now require reviewed
  confirmation. Backend direct-mode bypass is denied; preview shows client and
  date/time, with original/new times for rescheduling. Client references retain
  redaction after access changes. Existing new-client/task review remains.
- Fresh RU/KK UI preferences select an explicit bilingual STT profile. Explicit
  saved auto/RU/KK choices are preserved; English UI still defaults to auto.
- Opted-in card context can supply only the authorized client's name/name parts
  to direct ElevenLabs. Linked task/appointment clients receive a separate access
  check. No tenant directory, phone or notes are supplied. Maximum10 unique terms,
  50characters/5words each, letters/spaces/hyphen/apostrophe only. Foreign/invalid
  context is rejected, archived names omitted, access rechecked after STT.
- Literal phone conversion accepts comma after plus without changing repeated
  digits. Known distorted labels require clarification; grouped numbers are not
  guessed. `numbers_format=words` remains because digits mode had regressions.

Privacy: no live provider calls or credit spending in this implementation cycle.
Existing production activation/privacy flags remain off; logging=false, no audio
storage, no redirects/retries/provider fallback and server-only key remain.
Names are hints, not identity evidence or transcript replacement. Production
usage still requires separate Enterprise STT ZRM/no-training acceptance.

Verification uses isolated SQLite and Chromium with fictional fixtures and mocked
providers. Broad affected/dependent voice/speech/conversation run:156 tests,
152PASS/4SQLite row-lock skips,96.417s; system check and migration drift PASS.
After preview-reference/redaction changes:37 affected tests PASS,45.468s.
Final speech/context validation run:44 tests,43PASS/1SQLite skip,23.083s.
Final name-context run after binding the interface voice runtime:14PASS,5.521s,
including paused-agent independence, linked-client access and archived-name omission.
Frontend `npm run build` (types/i18n/app/widget) PASS after final date formatting.
Chromium:9 scenarios PASS in the combined run, then the remaining recording
scenario PASS with the corrected stable client route (10 distinct scenarios total).
Actual isolated API verifies review/no mutation before confirmation, existing-client
booking, cancelled cancellation proposal, rescheduling, replay, correction of
client/task text and outage input retention. UI locales RU/KK/EN and320/390/1440
widths covered. Synthetic microphone capture verifies KK multipart and context
omitted/included on opt-in, plus retained audio/discard after mocked503.

UI delivery gate (scoped, existing design retained):
- R26/R32/R35 PASS: confirmation/cancel via keyboard and real isolated API; custom
  language selection survives reload; existing edit/retry/input retention exercised.
- R03/R39 PASS: affected320/390/1440 screenshots captured and visually inspected;
  names, original/new local dates and controls remain readable, no page overflow.
  Existing named buttons, focus styles and shared typography/tokens retained.
- R17/R18/R23/R36/R38 PASS: preview uses authorized records; all test identities
  are explicitly fictional. No invented production metrics/assets/content.
- R01/R05/R11/R20/R29/R31 and visual/motion/performance additions N/A: no visual
  redesign, new palette, media, theme or motion. Operational panel retained;
  only target identity/date content and existing settings behavior changed.
- Empty/loading/error/redaction reuse existing components; error retention and
  redaction are exercised. Full-app WCAG, dark-theme recertification and field
  performance are not claimed by this bounded change.

Attempt history: old existing-client-direct test correctly failed under the newly
approved review policy and was replaced with review/no-write/bypass checks. New
transition fixtures first lacked explicit identity and then attached the ID to
the client noun; corrected to explicit appointment ID, preserving the application's
clarification guard. Browser selector initially treated the shared custom Select
as native; fixture initially omitted a synthetic provider base URL. Both fixture
issues corrected without weakening product readiness or privacy checks. Legacy
client query URL redirects to the permanent card route; recording test now opens
that stable route and waits for the actual card before opening the voice panel.

Remaining evidence: no live Scribe/LLM remeasurement after these code changes,
no human KK speech corpus and no production activation. Prompt changes do not
prove live intent accuracy; historical STT accuracy FAIL and full D01 remain open.
No migrations, notification/BusinessEvent behavior or access-policy expansion.
Existing speech/AI/operations contracts updated; CRM lifecycle/access contracts
unchanged because underlying permissions and domain transitions are reused.

Commands/artifacts: `output/voice-scribe-v3-20261117/improvements_checks.py`
(default affected suite; focused labels recorded in checkpoint),
`benchmark_checks.py`, `improvements_browser.py` (then `--grep 'recording sends'`),
`frontend: npm run build`. Logs: `improvements-final-{0,1,2}.log`,
`improvements-speech-final.log`, `improvements-narrow.log` (final14-test run),
`improvements-build-final.log`, `browser-*-1795015422668717800.log` and subsequent
recording-only log.37-test result retained in checkpoint; its temporary log was
overwritten by the final14-test focused run. Screenshots under
`browser-1795015422668717800/` show final localized dates/identity/review UI.

## Обширный синтетический тест, 18.11.2026 — актуальный результат

Проверка выполнена в пределах нового лимита 2000 кредитов. Это тест распознавания
и локальных обработчиков, не сертификация понимания произвольной живой речи.
64 разных вымышленных обращения: 44 KK, 12 mixed, 8 RU. Два Microsoft neural
голоса для KK/mixed (Aigul/Daulet), один подтверждённый локальный Irina для RU.
120 чистых WAV, дополнительные варианты с фиксированным шумом и ускорением.

Матрица покрывает создание клиента/задачи/записи, перенос/отмену, заметки, вопросы
о расписании, относительные/абсолютные/високосные даты, имена, посимвольные и групповые
номера, исправления, отрицания, несколько действий, выбор клиента, неподдерживаемые
деньги/удаление/права, общую речь, тишину и шум без речи. Не все возможные формулировки,
диалекты, микрофоны, реальные шумы и голоса покрыты.

Всего 298 условий: основная матрица 290 и 8 отдельных опытов с keyterms.
295 HTTP200,2 HTTP429, тишина отклонена локально как audio_empty до сети.
Один из 429 содержит system_busy; после паузы серия продолжена с интервалом 4.2 с.
Уже отправленные случаи не повторялись; две неудачи сохранены. Шум без речи дал
пустую строку: рабочий parser отклоняет её как отсутствие речи.
Успешно отправлено 1483.793 с аудио. Продуктовые код/настройки/БД/серверы не менялись;
OpenRouter/planner не вызывались, реальные клиенты не использовались.

### Бюджет и граница атрибуции

Лимит существующего STT-only ключа уменьшен 5000 → 2097 за период:
97 прежних кредитов +2000 на эту серию. Срок и права ключа не расширялись.
Консервативный резерв основной серии и keyterms —1940; это защитная оценка,
не счёт провайдера. Analytics/Usage вырос 97 → 930, то есть на 833 кредита;
остаток этой границы — не менее 1167. Billable Request Count вырос 22 → 327,
тогда как локально подтверждены 295 новых HTTP200: разница 10 запросов
не атрибутирована. Журнал показывает наши последние STT-вызовы и обращения
кабинета, но не доказывает причину расхождения. Поэтому 833 — прирост аккаунта
и верхняя граница расхода серии, не точная отдельная стоимость 295 вызовов.
Лимит соблюдён; дальнейшие STT-вызовы остановлены.

### Точность на чистом аудио

WER — доля вставленных/пропущенных/заменённых слов, ниже лучше; это не доля
неправильно выполненных команд. Пунктуация и регистр исключены, ё/е уравнены,
казахские буквы не заменялись русскими. CER аналогично оценивает символы.
Для KK сравнение строго парное:86 одинаковых аудиофайлов с успешным ответом
в обоих профилях. KK/RU означает language_code=kk и secondary_language_codes=ru;
auto не задаёт оба поля. Имена проверены с границей начала слова и допустимым
падежным окончанием: «Кәсел» не засчитывается как «Әсел».

| Речь / профиль | Записей | WER | CER | Точные имена | Телефон после обработки |
| --- | ---: | ---: | ---: | ---: | ---: |
| KK, KK/RU | 86 | 1.36% | 0.27% | 48/54 | 10/12 |
| KK, auto | 86 | 6.53% | 4.53% | 48/54 | 7/12 |
| Mixed, KK/RU | 24 | 15.98% | 7.26% | 10/20 | 4/6 |
| Mixed, auto | 24 | 19.26% | 8.35% | 9/20 | 4/6 |
| RU, RU/KK | 8 | 0.00% | 0.00% | 4/4 | 2/2 |


Результат чистого KK не распространяется на mixed: имена сохранены лишь
в 10/20 (KK/RU) и 9/20 (auto) проверенных вхождениях. Среди 86 KK-auto метаданные
языка: kaz79, ukr4, rus2, tur1. Часть mixed-цифр передана русскими словами
при правильных значениях: это увеличивает WER без обязательной потери смысла.
Ошибки произношения синтезатора тоже возможны; независимое прослушивание носителями
языка и живые записи ещё не выполнены. Эта выборка не оценивает всю популяцию.

### Что дали настройки и условия

- На 20 одинаковых телефонных записях words + штатная нормализация сохранили номер
  в 16/20, digits —18/20. Три улучшения и одна регрессия: у RU номера 77010002030
  в digits появился лишний ноль —770100002030. У mixed номера 77022222222
  в digits потерялась цифра: +7 [70] 222-22-22. В двух words-ошибках правильные
  групповые числительные сохранены моделью, но намеренно не преобразованы
  приложением без уточнения. Это не ошибка STT.
- На 8 выбранных проблемных примерах имён единый словарь 10 вымышленных имён
  улучшил написание 4/8 → 7/8. Осталось Айгерімнің → Әйгерімнің.
  Это прицельный опыт на известных ошибках, не независимая общая оценка.
- Для 12 одинаковых файлов WER: чистые 9.52%, шум 20dB11.11%, шум 10dB28.57%,
  ускорение 1.25×11.90%. Только KK (8 файлов):20dB2.70%,10dB20.27%,
  ускорение 1.25×1.35%. При 10dB оба KK номера ошибочны. Это искусственный
  белый шум относительно RMS всего WAV и цифровое ускорение, не реальные
  помещения или естественная быстрая речь.
- Вручную сверены 17 чистых транскриптов пяти абсолютных дат:07.11.2030 12:00,
  31.12.2030 23:55,29.02.2032 08:30,08.11.2030 10:00,09.11.2030 10:00.
  Значения сохранены словами; календарный parser/timezone/создание записей
  не проверены. Время 23:55 иногда разделено запятой.

### Что доработать — подтверждённые основания, без реализации в этом тесте

1. **P1: важные поля и смысл исправления.** «бас тарт» стало «баста»
   (отказаться → начать), «Әсел емес, Әсем» теряет отрицание; имена специалиста
   и клиента искажаются в mixed. Сохранять существующие identity review/проверку
   совпадений, усилить проверки исправлений/отмен и конкретного имени, телефона,
   времени перед изменением. Низкий WER не доказывает безопасность действия;
   фактическое опасное изменение CRM здесь не воспроизводилось.
2. **P1: локальный признак команды записи.** На идеальном тексте
   voice_booking_request возвращает True для «Әселді қабылдауға жазып жіберме»,
   «Әселді қабылдауға жаз деп айтқан жоқпын» и «Әселді қабылдауға жазыңыз деген
   тапсырма жаса». Для команды 15 без слова «қабылдауға/консультацияға» — False.
   Это вспомогательный признак восстановления неполного маршрута, не полный NLU;
   используется в conversation_router и validate_voice_plan. Нужны регрессии
   отрицаний, цитируемой команды и явного запроса задачи.
3. **P1: неразобранные номера.** В 09-kk-phone-f-auto язык отмечен tur, текст
   начинается «Telefon nömrə…»: телефон не нормализован,
   ambiguous_spoken_phone=False. Сигнала уточнения также нет у двух KK шумовых
   случаев и одного неверного цифрового mixed номера. Расширить безопасное
   обнаружение диктовки/пунктуации/меток и проверку полного номера по региональному
   формату; цифры не дополнять догадкой. Неверное, но допустимое число всё равно
   требует проверки соответствия клиенту. Существующее уточнение для распознанной
   неоднозначности сохраняется.
4. **P2: язык и словарь.** Для преимущественно KK использовать существующий явный
   выбор KK с дополнительным RU; frontend сейчас default auto. Отслеживать
   неожиданный язык ответа: production speech возвращает text/duration,
   detected_language не передаётся. Keyterms показал пользу; рабочий словарь
   должен быть ограничен Business и прежними условиями приватности.
5. **P2: numbers_format.** Кандидат digits улучшил счёт, но создал регрессию:
   не переключать глобально без проверки цифр, новых регрессий и review.
   Не скрывать ошибку за LLM-«исправлением». Платные повторы автоматически не включать.

Понимание полной команды планировщиком, многотуровый контекст и исполнение на живом
OpenRouter не оценивались; баланс OpenRouter не расходовался. Регрессии используют
mock provider. Далее нужны эти доработки, полный изолированный
voice→plan→review→CRM и живые вымышленные KK-записи 2–3 людей, как согласовано.
Реальные данные по-прежнему требуют Enterprise STT ZRM/no-training;
ENABLED/PRIVACY_CONFIRMED остаются False.

### Воспроизводимость и проверки

Canonical C:/Users/user/Desktop/PlatformaCRM, codex/ui-testing-toolkit, исходный
HEAD61a7946f; voice-файлы не менялись. Чужие integrations/payments/scheduling/frontend
WIP сохранены. Обычная БД, миграции и deployment не затронуты.

- benchmark_prepare.py: фиксированное synthetic-аудио. Dmitry в online TTS дважды
  не вернул звук; недоступный локальный Pavel не засчитан как отдельный голос.
  Финальный manifest RU содержит только Irina, неиспользованные файлы не отправлены.
  Внешняя TTS-подготовка вымышленных текстов — без ElevenLabs.
- benchmark_manifest.py и benchmark_run.py --preflight: SHA256/WAV/объём/флаги PASS.
  Тишина дала audio_empty и учитывается как локально заблокированная.
- benchmark_run.py --live, затем --continue после паузы:287 HTTP200/2 HTTP429/
  1 local block. Exit2 сохраняет две ошибки; это не 290 успешных вызовов.
- benchmark_keyterms.py --live:8 HTTP200, cumulative reserve1940, exit0.
- benchmark_checks.py через scripts.codex_verify.isolated_runtime: найдено 37,
  36 PASS/1 skipped (SQLite не поддерживает select_for_update),21.137 с;
  Django system check0issues. Модули: tests_elevenlabs_speech, tests_speech_numbers,
  tests_voice_booking_intent.BookingInstructionTests, tests_voice_kazakh,
  tests_voice_identity. Ключ пуст, provider mocked, disposable DB.
- Build/UI/full-project gate/migration drift не запускались заново ради evidence:
  продуктовых изменений нет. PostgreSQL concurrency PASS не заявляется.
  Итоговые docs/artifact checks и publication записываются в checkpoint.

Локальные инструменты/логи находятся в ignored output/voice-scribe-v3-20261117.
Точные строки, профили, SHA аудио, результаты/ошибки и расчёт метрик — в
[JSON-артефакте](voice-scribe-v3-benchmark-20261118.json), без ключа и локальных путей.
Номер оценивается как вся последовательность цифр без пунктуации, не ограниченный
regex форматирования: +7 [70]… не считается ошибкой из-за скобок. Исходный
regex-результат сохранён отдельно. Критичные фрагменты оцениваются буквально,
не как семантическое понимание. Ошибочные транскрипты не исправлялись.

Официальные параметры сверены по
[Create transcript](https://elevenlabs.io/docs/api-reference/speech-to-text/convert):
digits/words, primary/secondary languages и keyterms; последний добавляет 20%
к стоимости STT. В production экспериментальные настройки не включались.
Scope синтетической диагностики завершён; качество mixed/критичных полей не закрыто.
Остаток: код — указанные доработки; доказательства — живые голоса/полный flow;
среда — ZRM и planner; решение — активация отдельно.

## История предыдущих проверок

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
