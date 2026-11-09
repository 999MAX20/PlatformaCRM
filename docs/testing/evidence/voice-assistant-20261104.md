# VOICE-ASSISTANT-20261104 — локальная реализация 05.11.2026

Согласованный результат: микрофон в глобальном хедере, явная запись/stop/cancel,
редактируемый текст, отправка в приватный диалог сотрудника, предложение действия,
подтверждение кнопкой и результат со ссылкой. Провайдер STT выбран владельцем:
OpenRouter. TTS и постоянное прослушивание исключены.

Канонический checkout: `C:/Users/user/Desktop/PlatformaCRM`,
`codex/ui-testing-toolkit`, HEAD `66101d509cb7642b2928275e48c4b64354abf07b` + shared dirty tree.
Начальный status/diff и before-файлы сохранены в `output/voice-assistant-20261104`.
Другие изменения не принадлежат этой задаче. Итоговые хеши затронутых исходников:
`final-source-manifest.json` в том же каталоге.

## Реализация и пределы

- `/api/ai/speech/`: GET разрешённого активного CRM-агента/конфигурации, POST
  multipart audio/business/language. Текущий actor/Business/AI_ASSISTANT SUGGEST
  и employee workflow проверяются до и после внешней обработки. Все ответы no-store.
- AudioWorklet собирает mono PCM; WAV16kHz/PCM16 до60сек и2MB проверяется сервером.
  Upload handler использует только ограниченную память. Аудио не пишет историю,
  AIRequestLog, temp upload или CRM. HTTP errors/timeout/invalid response безопасны.
- OpenRouter `/audio/transcriptions`, отдельная STT model, privacy flags
  `zdr:true`/`data_collection:deny`, без автоматического платного повтора.
- Voice-origin сохраняется в существующем context_json. Сервер ограничивает план,
  конкретный tool payload и подтверждение. Одна операция на подтверждение; связка
  клиент→запись последовательная, с двумя подтверждениями, без общей транзакции.
  Неявка, archive/delete, деньги, bulk и изменения прав не исполняются.
  Явные формулировки удаления/неявки дополнительно блокируют подмену отменой;
  универсальное понимание естественного языка не заявляется.
- Открытая карточка передаёт только тип/ID после выбора checkbox; сервер заново
  разрешает источник. Client-фильтр списка записей не становится открытой карточкой.
- Приватная staff history и точные approval/version/idempotency/domain services
  переиспользованы. Inbox не получает голосовые turn/context. Уход/закрытие/
  смена identity освобождают микрофон; поздняя расшифровка не появляется.
- Личные настройки текущего браузера: visibility, auto/RU/KK, device/test.
  `/app/settings/voice` требует assistant suggest, не SETTINGS UPDATE.
  Ссылка Аккаунт→Интерфейс позволяет вернуть скрытую кнопку. Новых миграций нет.
  Notification/BusinessEvent/audit effects остаются в существующих domain services.

## Проверки

Все backend-команды запускались через `scripts.codex_verify.isolated_runtime`
с `.venv/Scripts/python.exe`, отдельной SQLite, disabled external clients.
Обычная рабочая БД не использовалась. Exact command wrappers сохранены в checkpoint.

| Проверка | Результат / журнал |
| --- | --- |
| `manage.py test apps.ai_core.tests_speech --noinput -v1` | 7 PASS, `speech-tests-2.log`: WAV/limits/silence, privacy payload, safe errors, tenant/account/revocation, no turn/log/write |
| Speech + voice policy + conversation api/state/memory/execution + CRM tools/planner + approval binding | 86 PASS, `completion.log`; исходный состав указан ниже |
| Последующие voice policy/execution/api | 22 PASS, `policy-final-2.log`; error-code propagation и серверные точки проверки |
| Связанный voice client→appointment | 1 PASS, `linked-scenario.log`: реальное создание клиента, отсутствие записи до второго подтверждения, запись на созданного клиента, replay без дубликатов |
| `tests_voice_policy.VoiceLanguagePolicyTests` после уточнения распознавания явных запретных формулировок | 1 PASS, `language-policy.log`; RU/EN/KK denial, допустимые отмена/чтение/фамилия Удалов |
| `manage.py check`; `makemigrations --check --dry-run` | PASS, `check.log`, `drift.log`; схемных изменений нет |
| `node --test frontend/scripts/tests/voice-audio.test.mjs` | 4 PASS, `node-final.log`: WAV header/rate/clipping/duration/chunks/empty и card-vs-filter context |
| Browser: record/edit/send/real task confirmation/result, Escape/reopen, settings, RU1440/KK390/EN390, microphone denied, delayed cancel,503/retry | PASS: `browser-1793818866639744100.log`, первые5 сценариев; denial fixture этого запуска исправлена отдельно |
| Browser: explicit role denial and settings without SETTINGS permissions | 2 PASS, `browser-1793819214306347000.log` |
| Browser: microphone release on navigation, restoring hidden button through Account, language/device selection and persistence | PASS, `browser-1793819553746874000.log` и финальный `browser-1793819883892431300.log` |
| Isolated `npm run build` (i18n, tsc, app/widget) | PASS, `build-1793819553746874000.log`; 6879 keys RU/KK/EN; worklet emitted as same-origin asset, not inline data URL |
| `node scripts/check-bundle.mjs` из frontend | PASS app shell347.4kB/400kB; advisory RU/KK dictionaries >500kB remain |
| Task diff/index/new-file/link/source review | PASS, итоговый checkpoint; shared foreign WIP не включён в собственный publish |

Состав completion:
`apps.ai_core.tests_speech apps.ai_core.tests_voice_policy apps.ai_core.tests_conversation_api
apps.ai_core.tests_conversation_state apps.ai_core.tests_conversation_memory
apps.ai_core.tests_conversation_execution apps.ai_core.tests_crm_tools
apps.ai_core.tests_crm_planner apps.ai_core.tests_approval_binding`.
Результаты86/22/1 не складываются в число уникальных тестов: dependent cases
перекрываются, последующие проверки относятся к соответствующим изменениям.

Browser runner: `.venv/Scripts/python.exe output/voice-assistant-20261104/run.py`;
`--browser` исключает build, `--grep` сужает сценарии. Runner и fixture/config/spec
сохранены вместе с локальными логами. Guarded prepare, выделенные loopback ports,
synthetic Chromium microphone и данные; STT HTTP response подменён только в тесте.
Подтверждение подготовленной задачи и запись результата проходят настоящий backend.
Свободный текст использует mock AI. Это доказательство механики, не качества модели.

Сохранённые неуспехи: первоначальные ошибки модели Bot/base URL исправлены;
Escape при исчезновении record button и stale readiness воспроизведены/исправлены.
Fixture до owner-membership normalization была корректно redacted; затем подготовка
перенесена после нормализации. Request без bearer дал401; проверка перенесена в
настоящий API client. Отсутствие custom permission не отменяет role preset: fixture
denial теперь явная. Sidebar hover мешал тестовому клику; pointer moved outside,
без force-click и без изменения чужого sidebar. Последний harness уточнил
accessible name shared Select (label + current value); выбор обоих полей прошёл.
Старые логи не переписаны.

## UI gate: согласованное направление и проверенный scope

Направление: принятые владельцем references, существующие CRM tokens/Manrope,
компактная рабочая панель и зелёная кнопка действия. ENERGY1/RHYTHM2/MOTION0:
приоритет текущему действию, разделение history/capture/transcript, без анимационного
декора. Скриншоты `proposal-{ru,kk,en}.png`, `settings-{ru,kk,en}.png` осмотрены.

- R02 PASS: новый copy без декоративных тире; existing empty-cell placeholder сохранён.
- R03 PASS:390px KK/EN и1440px RU, отсутствие page overflow проверено браузером.
- R17/R18/R36/R38/C5 PASS: нет придуманных метрик/отзывов/обещаний; test names только в isolated fixtures.
- R23/R24 PASS: assets не добавлялись; согласованные entry/settings/account links существуют.
- R25 PASS: semantic tokens на белом surface-card: primary16.64, secondary6.83,
  muted5.17, brand5.35, danger6.49; рассчитано по WCAG relative luminance.
- R26/R27/C2/C4 PASS: реальные API/handlers, pending/error/permission/retry/empty/text fallback и cancel paths проверены.
- R28 PASS: FAQ не добавлялся.
- R32/R39 PASS: native controls, labels, focus ring, Escape/return focus; status/meter имеют имена.
- R33 PASS: source edits, без runtime source/CSS patching.
- R34/R21 PASS: theme toggle/default не менялись; используются существующие theme tokens.
- R35 PASS: приложение запускалось, primary flow/settings/role/recovery проверены; production build/types PASS.
- R37 PASS: owner-approved references предшествовали реализации; scope не расширялся до общего redesign.
- R40 PASS: новых media/third-party scripts/hero/performance promises нет; voice panel lazy-loaded.
- R01/R07/R08/R09/R10/R13/R14/R19/R22 PASS: новый декоративный gradient/grid/arrow/badge/glow/card-grid/motion/illustration отсутствует.
- R04 PASS: microphone=record, square=stop, X=close; existing turn actor icons переиспользованы.
- R06 PASS: существующая CRM typography; нет нового monospace/uppercase presentation.
- R12 PASS: shadow отделяет popover от текущей страницы, не каждый control.
- Liveliness PASS: focal action, структурные отступы history/capture/transcript, один brand accent; CRM card motif.
- C1/C3/R05/R11/R15/R16/R20/R29/R30/R31 PASS: каждый блок обслуживает запрос/статус/действие; shared controls/tokens, конкретные CTA, без marketing templates или чужого visual clone.

## Что осталось

Код/локальные проверки принятого голосового scope выполнены, остатка внутри этой
границы нет. Live STT/AI quality остаётся:
нужны разрешённые RU/KK/mixed записи с шумом/именами/телефонами/датами и проверка
конкретного OpenRouter privacy route. Локальный ключ присутствует, paid calls не
выполнялись. Не проверялись физические микрофоны/Safari/Firefox и live queues.

Публикация: существующий `.git/index.lock`, пустой index и17 чужих outgoing commits
не позволяют own-only normal push; lock/history не менялись. Remote main readback:
`0b3348e1ab31121a106badbde830b496ec477aac`. Собственных commit/push/new CI/deploy нет.
Working-DB migrations и release-wide gate не запускались: они не входят в этот
scope. Полная D01-приёмка/roadmap acceptance не закрыта данным локальным изменением.
