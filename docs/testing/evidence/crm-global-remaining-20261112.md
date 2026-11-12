# Остаток общего аудита и маршрутизация заявок — 12.11.2026

Task: `CRM-GLOBAL-REMAINING-20261112`. Семь неуспешных проверок T01–T07
разобраны и исправлены; три наблюдения O01–O03 классифицированы. Подтверждённые
дефекты исправлены и адресно проверены. Новые заявки в помощнике проходят через
Appointment с уточнением и подтверждением. Это не полная release-приёмка.

Канонический checkout: `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, база текущего кандидата `8fa102496f1fa63afc72209756198402910f177b`.
Публикация разрешена владельцем; экспериментальные speech.py/speech_numbers.py,
их тесты и документация исключены. Чужой WIP сохранён. Итоговые commit/remote/CI
фиксируются в `output/crm-global-remaining-20261112/CHECKPOINT.md` и ответе задачи.

## Результат по каждому пункту

| ID | Причина и минимальное исправление | Проверка и итог |
| --- | --- | --- |
| T01 | Fixture configured-provider не задавал KIMI base URL, обязательный для readiness. Добавлен синтетический `.invalid` URL; продуктовая readiness сохранена | Foundation suite в итоговом наборе86 PASS |
| T02 | Устаревшее ожидание немедленного создания голосового клиента. Тест теперь проверяет review, подтверждение и отсутствие дубля | Уже опубликовано `8fa10249`; CI43227614044 SUCCESS, повторное изменение не требуется |
| T03 | Тест первоначального филиала ошибочно проверял defaults после migration0006. Разделены состояния0003 и0006, сохранены reverse/history assertions | Уже опубликовано `8fa10249`; тот же зелёный CI |
| T04 | Decimal сериализуется как `9900` в SQLite и `9900.00` в PostgreSQL. Проверяются строковый тип и точное Decimal-значение; добавлены дробные `9900.37` | PostgreSQL3 PASS, SQLite в итоговом наборе86 PASS; округление/продуктовые суммы не менялись |
| T05 | В fallback registry отсутствовал management API | Policy добавлена, инвентарь регенерирован; Node PASS |
| T06 | В реестре маршрутов не было company/staff, optional invite token расходился с router | Добавлены фактические маршруты/действия, сохранены NOT_RUN статусы; Node PASS, это не новый browser coverage |
| T07 | S04 ожидал внешнюю доставку SYSTEM notification. Такие уведомления остаются pending и доступны в личной ленте | Реальные PostgreSQL/Redis/Celery: один reminder и notification, recipient, API чтение/mark-read, повтор без дубля и потери read state PASS |
| O01 | Activity text записи форматировал UTC вместо часового пояса бизнеса | Единый business-local formatter для отмены/завершения/переноса; API regression, зависимые тесты и браузер:11:00 вместо06:00 UTC PASS |
| O02 | Retry Inbox всегда показывал success независимо от результата | Send/retry используют status ответа: sent→success, failed/unknown delivery→warning, queued/accepted→info; Node и browser RU/KK/EN PASS |
| O03 | У lifecycle задач отсутствовали from_status/to_status | Metadata добавлена в существующие события start/complete/cancel/reopen/undo/wait/resume;80 dependent PASS, реальный API и timeline drawer RU/KK/EN PASS |

Финансовая часть O03 не является подтверждённым дефектом: история клиента имеет
более широкие права, чем финансовые записи. `apps/payments/services.py` намеренно
не публикует сумму/примечание/причину, а timeline projection не открывает Payment.
Эта граница сохранена; права и финансовые данные не расширены. Старые события
задач без metadata и старые тексты записей не переписывались задним числом.

## Маршрутизация новых заявок

Проверена и включена существовавшая локальная дельта
[AI-REQUEST-APPOINTMENTS](ai-request-appointments-20261111.md): новая
заявка/лид/өтінім/inquiry нормализуется в appointments/create до проверки
источников и планирования, включая pending plan. Отсутствующие детали уточняются;
исторические Lead сохраняют entity/ID. Нет миграции или конвертации старых данных.

Итоговый набор75 PASS покрывает нормализацию, запрещённый Lead payload,
отключённый источник appointments, цели, API, подтверждения/replay, voice policy,
оборудование и перенос резервирования. Ранее падавший equipment case в этом
наборе прошёл. Chromium через настоящий изолированный API проверил
заявка → уточнение → именованное предложение Appointment → подтверждение Enter →
одна созданная запись, desktop1440/mobile390. Ответы планировщика заданы тестом;
новой проверки платной модели или распознавания речи здесь нет.

## Проверки и воспроизводимость

Логи и тестовые сценарии: `output/crm-global-remaining-20261112/`.
Python запускается из `.venv/Scripts/python.exe`; `verify-final.py` использует
`scripts.codex_verify.isolated_runtime`, отключает загрузку рабочего env и внешние
сетевые соединения. Экспериментальные речевые модули в памяти заменены blobs базы
`8fa10249`, файлы на диске не изменялись. Рабочая БД не использовалась.

- `verify-final.py --name completion-domain-corrected` с labels из одноимённого
  JSON:86 PASS (record commands, resource booking, completion, AI foundation,
  platform dashboard, task reminders).
- `verify-final.py --name routing-completion` с labels из JSON:75 PASS.
- `verify.py --name o03-after apps.tasks.tests_workspace apps.tasks.tests
  apps.activities.tests_timeline_workspace`:80 PASS на неизменённых task/activity входах.
- PostgreSQL PlatformDashboardTests:3 PASS, `pg-summary.json`; system/drift PASS.
- `verify-final.py --name final-system --checks`: Django check и makemigrations
  check/dry-run PASS. Новых миграций нет, рабочие миграции не выполнялись.
- `scripts/verify_recovery_s04.py --phase queue --pg-bin "C:/Program Files/PostgreSQL/17/bin"
  --redis-server output/crm-s04-20261014/deps/redis/Redis-7.4.9-Windows-x64-msys2/redis-server.exe`:
  PASS; реальная локальная очередь и FakeSMTP, без реальных отправок.
- Node:9 PASS, registry/fallback/delivery notice/idempotency policy; `node-after.log`.
- В frontend `npm run build` (i18n + tsc + app + widget) и `npm run check:bundle`:
  PASS; `build-completion.log`, `bundle-completion.log`.
- `node output/crm-global-remaining-20261112/browser-remaining.mjs`: timeline и Inbox PASS.
  `browser-routing.cjs` и `browser-activity.cjs`: routing и локальное время PASS.

Числа наборов пересекаются; это не сумма уникальных тестов. Локальный UI использует
составной рабочий checkout; чистый публикуемый кандидат отдельно проверяется CI.
Предыдущие ошибки сохранены: исходные fixture/registry assertions, неверные имена
двух modules в completion-domain, выбор скрытого mobile row, демонстрационный
is_mock в тестовом planner adapter, неверная очередь ответов и кодировка fixture.
После исправлений соответствующие финальные проверки PASS; продуктовые assertions
и права не ослаблялись.

Собственные API/Vite/Chromium остановлены. Автоматическая очистка последней
тестовой SQLite получила WinError32; последующее явное удаление было отклонено
автоматической проверкой безопасности (`blocked by policy`). Каталог оставлен,
обхода нет; точный путь находится в checkpoint. Рабочая БД не затронута.

## UI acceptance и Anti Slop Delivery Gate

- Hard Gate PASS в изменённой области: существующие labels/tokens, keyboard Enter,
  Escape и возврат фокуса; 1440/390 RU/KK/EN без горизонтального overflow.
  Скриншоты timeline, Inbox warning/info/error и routing просмотрены визуально.
- Purpose Gate PASS: уведомление сообщает реальный статус ответа, переход истории
  показывает реальные from/to; новых декоративных блоков, assets или copy нет.
- Liveliness: N/A для нового дизайна; композиция и визуальный язык не менялись.
- Craftsmanship PASS: failed/queued/accepted/sent/delivery_unknown,503/recovery,
  loading/disabled повторной отправки и сохранение черновика проверены. Повтор
  несёт idempotency key; сообщения в БД после mock transport не изменились.
  Пустой/запрещённый список не изменён этим status mapper; существующие guards сохранены.

## Остаток и границы

В принятом объёме T01–T07/O01–O03 и маршрутизации остатка кода/локальных
доказательств нет. Публикация и зелёный CI являются отдельной завершающей проверкой.
Непокрытые варианты204-ID матрицы, нагрузочная ёмкость, полный S04 с файловыми/
антивирусными/restore сценариями, live providers, human STT и production остаются
открыты; queue-only PASS не закрывает весь S04. Экспериментальное распознавание
речи не входит в публикацию. Новые permissions, notification types, BusinessEvent,
схема, env и deployment не вводились.
