## Маршрутизация лендинга CRM — 06.11.2026

В `deploy/stand-access/Caddyfile` точные `/` и `/index.html` выдают
`/srv/landing/index.html`; `/landing/*` обслуживает статические файлы с404
для отсутствующего файла. Остальные UI-маршруты используют SPA fallback.
Все обработчики расположены после существующего stand forward_auth:
публичное назначение лендинга не отключает защиту стенда. Конфигурация проверена
локально настоящим Caddy и затем развёрнута на защищённом platformacrm.kz.
Добавлены только файлы лендинга и маршруты; действующая SPA-сборка, SSE,
пароль и конфигурация CRM сохранены. HTTPS/browser/backup PASS; подробности —
`output/crm-landing-deploy-20261106/RESULT.md`.
[Проверки и предложение трёх доменов на одной VM](../testing/evidence/crm-landing-integration-20261106.md).

## Явное возобновление филиала — 06.11.2026

По поручению владельца существующий архивный Branch1 активирован доменным сервисом;
изменение отражено в audit. Каталог и график сохранены, повторная настройка не нужна.
Рабочая конфигурация/14визитов не менялись при тесте голоса: тест выполнялся на её
изолированной копии с реальными ASR/model. Первоначальный неуспешный голосовой прогон
не скрыт последующим PASS. [Подробности](../testing/evidence/single-location-20261106.md#явная-активация-и-проверка-голоса--reactivate-branch-20261106).

## Локальная БД и очистка токенов, 06.11.2026

Позднее в тот же день локальная CRM переведена на PostgreSQL17.10,
`127.0.0.1:55432/platformacrm`, отдельная роль без superuser. SQLite сохранена
как исходный срез; текущие записи идут в PostgreSQL. Перед переключением сделаны
финальный SQLite backup, полная сверка152таблиц/10117строк, pg_dump и проверенное
восстановление. [Доказательства, rollback и нагрузка](../testing/evidence/postgres-load-20261106.md).
Windows `PlatformaCRM-Local-PostgreSQL` запускает закреплённый кластер при входе
пользователя; `dev.ps1` также проверяет его до миграционного preflight.
Существующий PostgreSQL5432 не менялся. Секреты и backup находятся только в
игнорируемом локальном output. Это локальная операция, не production deployment.

По поручению владельца создана и проверена SQLite-копия, применены branches0003
и scheduling0012 к локальной db.sqlite3. После миграций данные вне филиалов/журнала
миграций сохранились; затем удалены только просроченные JWT и связанные blacklist.
[Backup, SHA256, восстановление и проверки](../testing/evidence/db-maintenance-20261106.md).

Celery Beat вызывает accounts.flush_expired_tokens раз в86400 секунд на default
через штатную flushexpiredtokens. Нужны Beat и worker. Локально отдельное задание
Windows PlatformaCRM-Local-ExpiredTokens выполняется ежедневно12:00 по времени
Windows, с ограниченными правами текущего пользователя и StartWhenAvailable.
Компьютер должен быть включён, пользователь должен войти в Windows. Задание
запускает pythonw.exe scripts/cleanup_local_tokens.py из канонического checkout;
скрипт допускает существующую db.sqlite3 либо закреплённый локальный PostgreSQL
профиль в local/development; чужой host/database/user/port отклоняется. Лог без
токенов: output/local-db-maintenance/tokens.log. Два запуска завершились с кодом0.
Это обслуживание БД, не автозапуск dev-сервисов. Production не менялся.

## Единая команда local dev — 06.11.2026

`./dev.ps1` из корня канонической папки запускает в скрытых окнах:
закреплённый PostgreSQL при его выборе в `.env`, Redis6379
(только127.0.0.1/::1, AOF в `output/local-import-runtime`), ClamAV3310,
freshclam, Celery solo `reports_exports`, Django8000 и Vite5173. Скрипт не запускает
beat/другие очереди, не меняет `.env`, не устанавливает зависимости, не применяет
миграции и не создаёт Windows автозапуск. Процессы продолжают работать после
завершения команды. Их логи/receipt находятся в `output/local-dev`.

Предварительно требуются `.venv/Scripts/python.exe`, Node и установленный frontend,
существующий Redis в `output/crm-s04-20261014/deps/redis/Redis-7.4.9-Windows-x64-msys2`
и ClamAV/config/signatures в `output/local-file-antivirus`. Отсутствующий dependency
даёт явную ошибку; скачивание и установка не скрываются внутри запуска.
Поддержан только local/development с Redis localhost6379 без пароля и ClamAV3310;
другую конфигурацию скрипт не переписывает.

Запуски сериализованы файловой блокировкой. Уже работающий процесс принимается
по каноническому пути командной строки/родителю reloader либо ранее сохранённым
PID+creation time; совпадения только PID недостаточно. Неопознанный владелец порта
останавливает запуск до новых процессов; чужие процессы не завершаются. После
частичного сбоя уже запущенные службы остаются для диагностики/повторного запуска.

Проверки готовности: backend `/health/`200, frontend200, проксированный anonymous
`/api/auth/me/`401, Redis PING, свежие scanner signatures, ответ worker с очередью
`reports_exports`. Код0 означает готовность этих служб и отсутствие ожидающих
миграций; код2 — службы доступны, но найдены неприменённые миграции, отдельные
сценарии могут не работать; код1 — ошибка запуска/конфигурации/готовности.
Применение рабочей миграции требует отдельного разрешения по AGENTS.md.
Код0 не означает прохождения всей бизнес-приёмки CRM.

Проверки реализации и live запуск: `output/dev-command-20261106/CHECKPOINT.md`.

## Миграция автоматической основной точки — 06.11.2026

branches0003 добавляет uses_business_defaults и создаёт точку только Business
без любых строк Branch; не восстанавливает архивные филиалы. Зависимость:
scheduling0009. Forward/reverse проверяются в изолированной БД. Reverse сохраняет
точки и историю, материализуя их каталог/график/доступ перед удалением флага;
это совместимый откат схемы, а не удаление созданных записей.
Рабочая branches0003 к завершению проверки уже применена вне этой задачи;
read-only preflight подтвердил 15 автоматических точек и SQLite quick_check=ok.
Этот срез не сертифицирует чужую backup/migrate процедуру и не означает deployment.
Для других сред branches0003 требует отдельного разрешения целевой базы с backup.
Все ранее архивированные точки требуют явного возобновления владельцем.
[Проверки и границы](../testing/evidence/single-location-20261106.md).

## Локальный runtime переноса — 06.11.2026

Scanner/updater и Redis/import worker восстановлены после остановки. Redis доступен
только на loopback IPv4/IPv6 localhost6379; AOF — `output/local-import-runtime`.
Worker канонического checkout слушает `reports_exports`. Перед стартом очередь
была пустой; beat/AIworker не запускались. Scanner VERSION, Redis PING и worker PONG
подтверждены; PID/logs — `output/import-full-excel-20261106`. Процессы оставлены
для локальной работы, Windows автозапуск отсутствует. После перезапуска компьютера
требуется запуск этих служб, health-check до загрузки/preview/confirm.
Полный XLSX→20 Client проверен в отдельной БД с отдельными Redis/Celery процессами;
рабочие клиенты не добавлялись. [Evidence](../testing/evidence/import-upload-alert-20261106.md#полный-перенос-исходного-excel--06112026).

## Локальная схема мастера переноса — 06.11.2026

По прямому разрешению владельца без резервной копии применены core0014–0017
к локальной `db.sqlite3`. Создание черновика API201, история200 и SQLite quick_check
прошли; количество записей существующих бизнес-таблиц сохранено. Тестовый
черновик откатан. Это закрывает локальный schema gap кнопки «Новый перенос»;
production rollout, broker/antivirus и полный перенос этим не подтверждены.
Срез: `output/import-create-20261106/working-migration.log`.

## Голосовой ввод — 05.11.2026

STT использует серверные OPENROUTER_API_KEY/BASE_URL и отдельные
VOICE_INPUT_ENABLED (default true), VOICE_TRANSCRIPTION_MODEL
(default openai/whisper-large-v3-turbo), VOICE_HTTP_TIMEOUT_SECONDS (default60).
Маршрут `/audio/transcriptions` получает `zdr:true`/`data_collection:deny`;
несовместимость обрабатывается отказом без ослабления политики и без автоматического
платного повтора. Ключи не передаются браузеру. Audio upload до2MB проходит только
через ограниченный memory handler; API возвращает no-store. Для независимых
голосовых диалогов требуется ai_core0009; она применена к локальной db.sqlite3
05.11 с резервной копией и явным разрешением владельца. Браузеру требуется secure context/localhost и разрешение микрофона.
Наличие ключа не доказывает доступность модели: gpt-4o-transcribe реально
отклонён ZDR-фильтром. Whisper Large V3 прошёл реальную проверку русской записи
с неизменными privacy flags. HTTP-ошибки логируют только status/error code; body
и аудио не сохраняются. Постоянный отказ отличается от retryable сбоя.
На локальном dev установлен AI_QUEUE_LIVE_REQUESTS=False; AI-worker не запущен
(06.11 восстановлены Redis и отдельный import worker);
существующий inline путь обрабатывает запрос синхронно. Production default=True
с очередью ai не изменён. При возвращении local queue=True нужен работающий
broker/worker. [Реальная проверка и граница](../testing/evidence/voice-live-20261105.md).
[Контракт и остаток](voice-assistant.md).

После STT текст проходит GPT-4o mini для пунктуации с теми же ZDR/no-data-collection
ограничениями. Этот дополнительный запрос увеличивает время обработки; при ошибке
возвращается исходная расшифровка. Неотправленный текст не записывается этим шагом
в историю/AIRequestLog; отправленные разговорные ходы используют обычный учёт
AI-запросов. [Текущая проверка](../testing/evidence/voice-natural-20261105.md).

## IMPORT-WORKSPACE — локальная основа 04.11.2026

Новый мастер `/app/integrations/import` требует core0014–0017 и worker очереди
`reports_exports` с задачей `imports.process_workspace`. UI ставит preview/confirm
в очередь; отказ broker виден как ошибка, повторная публикация использует operation id.
Claim token и транзакция результата защищают от повторного worker; зависшая попытка
может быть перехвачена после5мин. Это управляемое восстановление, не обещание live-SLA.
Черновик хранит разобранные строки, corrections и результат в БД; cancel очищает
источники, completed history остаётся. Новый мастер не хранит исходный бинарный файл
после scanner. Автоматический retention/очистка завершённой истории не вводятся.
Миграции/очередь проверены локально в изоляции; core0014–0017 дополнительно
применены к локальной рабочей базе06.11 (см. выше). Deployment и живой
broker/antivirus не выполнены. [Контракт](import-workspace.md),
[evidence](../testing/evidence/import-workspace-20261104.md).

## C11 — владение попыткой экспорта, 04.11.2026

Каждый claim/reclaim ExportJob получает новый внутренний UUID claim_token.
Успех и ошибка записываются только при совпадении token и текущем status=running.
Старый worker возвращает актуальную строку и не меняет результат новой попытки.
Имя CSV включает token; неопубликованный файл проигравшей попытки удаляется по
собственному storage name, без удаления победившего файла. Ошибка удаления логируется;
гарантия очистки при аварии процесса/недоступном remote storage здесь не заявляется.
Existing permissions/fingerprint/download, retry eligibility и ограничения прежние.
core0013 добавляет nullable token без backfill; история и прежние файлы сохранены,
token не включён в API. Миграция применена только к disposable DB, рабочая БД прежняя.
При отдельном rollout необходимо завершить/остановить workers старой версии перед
работой новой: старый код не проверяет token. Live worker/storage/deploy не проверены.
SQLite focused20/expanded7/dependent32 и PG9 PASS; system/drift PASS.
[C11 evidence](../testing/evidence/remediation-c11-20261104.md).

## C10 — очистка записей повторных команд, 04.11.2026

prune_expired_crm_commands повторно проверяет expires_at по исходному cutoff
непосредственно в DELETE. Запись, продлённая после выборки ID посредством
begin/run_idempotent_crm_command, сохраняет claim/успешный результат и replay;
неизменённые просроченные записи удаляются. Порядок, лимит и retention прежние.
SQLite BEFORE3:2FAIL/1PASS; AFTER3 и dependent23 PASS; PostgreSQL8 PASS, включая
разные соединения select→renew/commit→delete и реальный Task без повторного создания.
System/migration drift PASS. No migration/env/UI/workingDB/push/live changes.
[C10 evidence](../testing/evidence/remediation-c10-20261104.md).

## C09 — миграция настройки автоматической записи

businesses0014 добавляет nullable ai_booking_responsible_user без backfill. Проверена
только в одноразовых SQLite/PostgreSQL и при обратной/прямой миграции; рабочая БД
не мигрирована. После разрешённого применения требуется явный выбор в профиле
компании; null/недоступный сотрудник оставляет безопасный handoff. Новых env нет.
[C09 evidence](../testing/evidence/remediation-c09-20261104.md).

## C07 — конфиденциальность URL телеметрии, 04.11.2026

Frontend Sentry/PostHog/Plausible заменяют reset-password, invite и invitation-preview
bearer URLs шаблонами в проверенных payload, включая вложенные/кодированные значения
и автоматически добавленные metadata. Обычные события и URL сохранены. PostHog
replay и неиспользуемые flags/remote-config отключены: эти каналы обходят before_send.
Plausible manual получает явный безопасный URL; при чувствительном referrer tracker
не запускается весь срок жизни документа, поскольку legacy SDK сам читает referrer.
Включение дополнительных SDK-каналов требует отдельной проверки этого ограничения.
Это локальная проверка frontend payload, не backend Sentry/live ingestion или
универсальный PII filter. [Проверки и границы C07](../testing/evidence/remediation-c07-20261104.md).

C04,04.11.2026: source archive uses `bash scripts/make_clean_archive.sh [name.zip]`
on Linux/WSL with rsync and Python3; standard `python3 -m zipfile` replaces Info-ZIP.
Flat filename only, default zani-clean.zip; archive prefix zani/ retained. Private
runtime/output/backup/browser/auth paths, env/DB artifacts and symlinks/special files
are excluded; declared env examples and intended sources/docs remain. Build failure
does not remove the prior archive. This is not a working-data backup or a scanner
for arbitrary secrets embedded in source/templates. Review intended inputs before
distribution; excluded runtime evidence can leave docs links outside the package.
[Synthetic archive evidence](../testing/evidence/remediation-c04-20261104.md).

C03,04.11.2026: paid-beta readiness reports broker configured/TLS/inline state,
never the configured URL. The configured JSON console normalizes and sanitizes
message arguments, exception chains and allowlisted context with the shared
credential-pattern sanitizer; error type/frames/request correlation remain.
Quoted multiword/escaped/newline credential assignments are fully masked.
Do not log raw sensitive payloads: arbitrary unlabeled values cannot be inferred
as secrets. Backend Sentry/other handlers/external pipelines remain unverified sinks;
send_default_pii=False alone is not a redaction proof. No live telemetry sent.
[Local C03 evidence](../testing/evidence/remediation-c03-20261104.md).

# Среда, эксплуатация и файлы

AUD-V01,31.10: cookie-auth требует GET /api/auth/csrf/ и последующий POST с
X-CSRFToken в том же cookie jar. Для отдельного frontend origin нужны точные
CSRF_TRUSTED_ORIGINS, CORS_ALLOWED_ORIGINS и credentialed requests; для HTTPS —
корректный proxy scheme и secure cookies. Не отключать CSRF для smoke/автотестов:
scripts/api_load_smoke.py и Playwright authPost используют штатный bootstrap.
Read-only review: compose.stand скрывает backend/DB/Redis порты и выставляет Caddy
80/443, HTTPS/HSTS и запрет private media; обычный compose публикует backend8000.
Это проверка конфигурации, не доказательство работающего сервера/backup/delivery.
[Evidence AUD-REMAINING](../testing/task-state/PRIMARY-SESSION.md#aud-remaining-20261031--aud-12c-and-aud-v01).


YCloud TP Lite: `YCLOUD_ENABLED=False` по умолчанию; `YCLOUD_API_KEY` и
`YCLOUD_WEBHOOK_SECRET` задаются только на сервере. Новые миграции integrations0007/
0008 и bots0013 проверены в одноразовых SQLite/PostgreSQL, к рабочей БД не применялись.
Webhook `/api/integrations/ycloud/webhook/` требует подпись YCloud и свежий timestamp;
внешняя среда требует HTTPS. Подписки: `whatsapp.business_account.updated`,
`whatsapp.inbound_message.received`, `whatsapp.message.updated`. Celery beat вызывает
`integrations.process_ycloud_events` каждые 30 секунд; исходящие используют обычную
очередь bots. Production требует worker/beat/Redis; локальный eager PASS этого не доказывает.
Readiness WhatsApp учитывает включение YCloud и отдельно проверяет его секреты,
очередь и мониторинг. Успешный readiness не подтверждает доступ TP Lite или доставку.
Повтор failed ingress доступен через настройку; неопределённую внешнюю отправку
нельзя слепо повторять. Пауза канала — оперативная остановка новых сообщений.
Подписанный message webhook без готовой привязки возвращает retryable503: провайдер
должен повторить его после подтверждения номера; ответ204 выдаётся после сохранения.
Ни аккаунты, ни secrets, ни настройки провайдера в этой задаче не менялись.
Подробности и остаток — YCLOUD-TPLITE-20261028 в PRIMARY-SESSION.

Coexistence 09.11: перед активацией нового кода требуется integrations0010
(`onboarding_type`, `expected_phone_number`), проверенная только в изоляции.
Для сохранения Business App нужны события `whatsapp.smb.message.echoes` и
`whatsapp.smb.message.created`; точные подписки и eligibility подтверждает YCloud.
Историю не подписывать для этого этапа. Внешний webhook должен проходить HTTPS
до обработчика подписи без stand-login, с исключением только точного POST-пути
`/api/integrations/ycloud/webhook/`. Текущий шаблон stand-access такого исключения
не содержит. Его изменение, миграция рабочей БД, секреты и worker/beat являются
отдельной активацией целевой среды. Локальные тесты не подтверждают её готовность.

NOTIFICATIONS-PERSONAL-20261028: новые миграции notifications0006/0007 добавляют
персональные состояния и фиксированную аудиторию, переносят legacy read_at без
повторной доставки. Сначала проверены на одноразовых БД;29.10 по отдельному
поручению применены к локальной рабочей БД после backup вместе с зависимостями
core0012, support0002 и businesses0012/0013. Проверены integrity, legacy state,
backfill и текущий UI; evidence — NOTIFICATIONS-PERSONAL-20261028 в PRIMARY.
Это историческая локальная операция, не новая миграция в аудите04.11 и не deployment.
Другие целевые среды требуют отдельной согласованной активации и release-проверки.
После обновления кода до миграции старой рабочей БД новый API ленты использовать
нельзя. Новых env-переменных, внешних каналов сотрудникам или worker-процессов нет.
Тестовый UI использует канонические исходники с отдельной синтетической базой;
live-приёмка этим не подтверждается. Подробности — PRIMARY-SESSION.

Действующие ограничения и недоказанный допуск, 07.10.2026.
Публикация Git и локальная приёмка не означают deployment/production readiness.
Последнее поручение владельца на комплексный аудит03.11 задаёт целевое направление
Yandex Cloud. Оно заменяет прежний выбор направления14.10; регион, состав сервисов,
ресурсы, операционные роли и запуск ещё не согласованы. Размеры Hoster.kz не критерий.
Ранее принятое требование размещения в Казахстане сохраняется как ограничение
для сверки с выбранной конфигурацией; выбор Yandex Cloud сам по себе не выбирает
регион и не отменяет требования к данным. Противоречие решает владелец до запуска;
новая облачная среда этим решением не развёрнута и не допущена к production.
Историческое исследование14.10 — [CRM-R02](../testing/task-state/PRIMARY-SESSION.md#crm-r02-20261014--pilot-decisions-and-provider-research).

## Принятый target восстановления — 29.10.2026

По §0.8/28.1 объединённого ТЗ для CRM приняты цели RPO обычных данных≤15 минут
и RTO основных операций≤4 часов. Они заменяют прежние цели5мин/2ч и старые
неутверждённые варианты; это не измеренный результат или клиентский SLA.
Платежи и подписанные документы сверяются с внешними фактами без тихих потерь/
дублей; RPO=0 не обещается. Требуются проверенная конфигурация Yandex Cloud, БД/PITR,
private files/keys/config/queues/inbox/outbox и согласованное restore/rollback.
Manifest нагрузки отдельно описывает две независимые клиники и подготовку до
пяти: пользователей/визиты/сообщения/файлы/базу/очереди, не только число tenants.

Принято техническое дежурство24/7 для серьёзных сбоев, обычная поддержка по
опубликованному графику. Люди/замещение, severity/response/runbooks/стоимость и
измерения ещё нужны; один ответственный не доказывает 24/7. Restore фиксирует
момент аварии/последний восстановленный факт/полезное восстановление, hashes и
external reconciliation; повтор очереди не дублирует бизнес-операцию.
Release manifest отделяет TEST/DEMO/UNCLASSIFIED, версии schema/config/артефактов
и provider capabilities. При угрозе данным/деньгам изолируется опасный путь с
уведомлением владельца; весь продукт останавливается, если изолировать нельзя.
Ни cleanup/seed, ни deployment/рабочие миграции этим документом не разрешены.
[CRM-R04/CG-04 и AC-RESTORE/AC-RELEASE](roadmap.md#зависимости-cg-и-оставшиеся-решения).

## Лимиты XLSX импорта

`MAX_UPLOAD_SIZE_MB` ограничивает исходный файл (по умолчанию10МБ); AV проверяет
те же байты перед разбором. XLSX дополнительно проверяется до `load_workbook`:

| Настройка | По умолчанию | Ограничение |
| --- | --- | --- |
| `IMPORT_MAX_ROWS` | 5000 | Строки данных плюс одна строка заголовка на лист; учитываются физические пустые строки и координаты |
| `IMPORT_MAX_COLUMNS` | 256 | Столбцы, координаты ячеек и заявленный диапазон XLSX |
| `IMPORT_XLSX_MAX_ENTRIES` | 256 | Число записей ZIP |
| `IMPORT_XLSX_MAX_EXPANDED_MB` | 20 | Суммарный разжатый размер всех записей ZIP |
| `IMPORT_XLSX_MAX_COMPRESSION_RATIO` | 200 | Максимальное отношение разжатого размера записи к сжатому |

Проверяются все XML-части/листы книги, хотя импортируется активный лист. DTD,
дублирующиеся ZIP-записи и шифрование отклоняются. Завышенные dimensions дают400;
заниженные не обрезают реальные строки. Превышение лимита не обрезает файл молча:
нужно уменьшить файл, удалить лишние листы/пустые диапазоны или разделить импорт.
Настройки — технические ограничения ресурсов, не коммерческие квоты.
Preview/confirm повторяют проверки; рабочие env/БД этой задачей не изменялись.
Версия и scoped evidence — AUD-22-20261021 в
[checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-22-20261021--bounded-xlsx-parsing).

## Локальная работа

Единственный writable checkout — `C:/Users/user/Desktop/PlatformaCRM`.
`Desktop/Zani` — junction, не вторая копия. Текущая ветка сохраняется;
чужие изменения не перезаписываются. Серверы запускаются из canonical root; перед UI
проверкой сверить source root backend/frontend/worker и build/profile.
Не останавливать чужие процессы и не доверять localhost по одному HTTP 200.

ADMIN-03: `ACCOUNT_RECOVERY_SUPPORT_EMAIL` задаёт публичный адрес поддержки,
`FRONTEND_URL` — доверенный адрес приложения для ссылок восстановления (HTTPS;
HTTP допускается только localhost/127.0.0.1). Без адреса поддержки экран честно
показывает отсутствие настройки; без frontend origin/почтового транспорта заявка
остаётся с безопасным состоянием ошибки отправки. Console/file/dummy backend
не выводит recovery-секреты. Проверка локального test outbox не доказывает SMTP
или доставку в ящик. Новая миграция accounts0011 требует отдельной рабочей активации.

ADMIN-04: businesses0013 хранит запросы исправления доступа и личное согласие
владельца. Рабочая миграция требует отдельного target/scope и backup. Новых env
или каналов отправки нет: перевыпуск меняет ссылку существующего приглашения,
владелец копирует её в настройках команды. Локальные PostgreSQL/browser проверки
не означают применение миграции или доставку приглашения в рабочей среде.

Runtime/параметры определены [settings](../../config/settings.py),
[примером env](../../.env.example) и scripts. Не печатать рабочий `.env` или токены.
Технические legacy Zani/ZANI identifiers не переименовывать без отдельной
совместимой миграции. Бренд и репозиторий — PlatformaCRM.

Разрешённые ранее рабочие миграции — исторические операции конкретных задач,
не бессрочное разрешение на новые. Working/staging/prod migration, seed/reset,
очистка файлов/старых деревьев требуют конкретного target/scope и backup.
Проверки используют isolated runtime из [testing](../testing/testing.md).

## Требования целевой среды

Общий multi-tenant SaaS, отдельные local/staging/prod settings и credentials.
PostgreSQL, Redis, Celery workers и beat; private object storage, почта, TLS,
allowed hosts/CORS/CSRF, health, безопасные логи/метрики/ошибки и backup/restore.
Prod не использует debug/demo defaults; `ALLOW_DEMO` выключен. Secret rotation,
привилегированная MFA и support grant — [access](access.md).

Долгие операции выполняются через существующие queue/service границы. Следить за
queue lag, retries, oldest pending/stale, worker/beat heartbeat, DB/Redis health,
provider failure и ценой AI. Логи структурированы с безопасными correlation IDs;
не писать сообщения клиентов, prompts, файлы, auth headers или secret payload.
Health endpoint не раскрывает credentials. Алерт имеет владельца, действие,
threshold и recovery; общая dashboard-картинка не доказывает срабатывание алерта.

PLATFORM-REBUILD-01: platform read APIs отделяют записанные ошибки источников
от свежих ServiceComponentState. Последние используют существующую границу
свежести 180 секунд; эти данные не подтверждают доступность всех провайдеров.
Операционные источники читаются независимо с безопасным rollback чтения:
недоступные значения возвращаются как null и/или unavailable_sources, без текста
исключения. Отсутствующая таблица наблюдений не обнуляет очередь и другие данные.
Ошибки форм в clinic summary считаются за 30 дней; failed jobs/events в обзоре —
история, не признак текущего outage. Legacy health.score теперь null; health.status
описывает recorded_signals (clear/attention/unknown), а не процент готовности.
Миграции и запуск collector не выполняются как побочный эффект чтения.
Vite направляет /ready/ в тот же backend, что /api; HTML оболочки не является readiness.

OFFICIAL-11, 28.10.2026: consent XLSX now uses existing bounded core reader
after actual upload max+1 byte check. ZIP expansion/entries/ratio and XML/worksheet
bounds run before openpyxl; rows stream to unchanged consent normalizer, with explicit
file errors and iterator/workbook cleanup. No eager worksheet list or silent trim.
Existing aliases, values, active sheet/cached formulas, CSV and consent rules retained.
BEFORE18:14 failing assertions across10 methods, one old underreported-dimension
error,7 controls PASS. AFTER52/combined551 PASS without skips; syntax/system/drift
PASS. HEAD98925b67 + WIP/nine previous fixes + patch. OFFICIAL-11-20261028 in PRIMARY;
output/security-remediation-20261028/consent-xlsx-limits/fix-report.md.
Only synthetic tiny fixtures/mocks; no stress/production or publication claim.

Consent XLSX shares the existing IMPORT_MAX_ROWS/IMPORT_MAX_COLUMNS and archive
settings below. Worksheet resource bounds count physical rows/coordinates, including
blank/unknown cells and inactive-sheet XML; they are not a change to consent meaning.
Oversized/invalid input fails clearly instead of being truncated. Static parser caps
are not an OS memory quota; no hostile-size production experiment was performed.

OFFICIAL-12, 28.10: Deal entity-export fingerprint now includes current sensitive
amount access in addition to existing AUD-18 resource/scope/capability checks. A
previously generated file cannot be downloaded after field access changes. Older
Deal export fingerprints require a new request; files are not migrated or deleted.
Generation itself renders denied amounts empty. Evidence: OFFICIAL-12-20261028.

OFFICIAL-06, 28.10: техническая граница outreach template — 16384 символа до parse,
personalized result/plain recipient text — 65536 символов до join/launch. Это
внутренние resource bounds, не лимиты провайдера. Поддержаны client_name, phone,
email, business_name, channel и escaped braces; непустые format specs, conversions,
attribute/index/positional fields не исполняются. Invalid/oversized input даёт
field error API либо отказ prepare/render/launch, без silent truncation. Stored
plain text не парсится повторно. Legacy unsupported templates требуют явной правки;
автоматической миграции/проверки рабочей БД нет. Версия/проверки — OFFICIAL-06-20261028.

OFFICIAL-20, 28.10: production readiness и Telegram rollout не возвращают значения
URL конфигурации broker/origins/providers. Detail показывает configured flags,
для broker также TLS; ключи/status/severity/action сохраняются для API/UI/CLI.
Malformed broker — failed-check без исходного значения. Реальные параметры изучают
в разрешённом канале настройки, а не в диагностическом ответе. Scoped9/совместно135
и system/drift PASS; версия/границы — OFFICIAL-20-20261028 в текущем checkpoint.
Это redaction, не изменение настроек доступа или запуск provider/production checks.

PLATFORM-OPERATIONS-20261015 добавляет read-only `operations-worklist` с источниками
incidents/connectors/automations/integrations/webhooks, строгими bounded filters,
стабильной пагинацией и safe projections без payload/error text/credentials.
Эпизоды: только последний известный episode по компоненту, свежие degraded и
устаревшие/будущие наблюдения как unknown; fresh healthy не попадает в очередь.
Полного исторического incident ledger это не создаёт. При отсутствии таблицы
support links наблюдения остаются доступны, число обращений неизвестно.
Health CLI сохраняет прежние release/readiness gates; connector_requests count
полный, массив-превью остаётся ограниченным. В UI readiness, текущие наблюдения
и terminal failures представлены отдельно. Миграций/запуска collector нет.

PLATFORM-OVERVIEW-20261015: `overview.attention` содержит полные distinct counts
клиник и ограниченные очереди клиник/поддержки. Классификация наблюдений общая с
`merchants?service=...`: degraded имеет приоритет над unknown; здоровая клиника
требует свежих наблюдений всех компонентов. Отсутствующие/будущие/устаревшие
наблюдения — unknown. Нет источника — null, а не пустая очередь; отсутствие
support links не скрывает сами наблюдения. Обращения активны до resolved,
unassigned — без assigned_to; waiting_clinic — точный статус, не SLA-просрочка.

PLATFORM-CLINIC-CRM-20261015: отдельный platform read API показывает Business-bound
CRM и safe статусы подключений; поиск/статус/архив/client filter, page_size до50,
стабильная сортировка и audit-before-response. Переписка читается без read-mark,
сырые payload/credentials исключены. Техническая диагностика остаётся в Операциях,
из карточки доступны Business-фильтрованные переходы. Это не новые источники
наблюдений, не запуск collector и не допуск recovery/retry. Миграций нет;
рабочая support0002 и live-проверки остаются отдельным объёмом.

Проверить очереди notifications, reports_exports, file_scans и все прочие,
используемые текущими task routes. Синхронный connector sync остаётся отдельной
границей риска; не считать весь интеграционный runtime очередью автоматически.
SQLite/eager не доказывают locking и recovery PostgreSQL/Redis.

CRM-R02-AI-RETURN: `bots.resume_answered_handoffs` выполняется beat каждые
60 секунд в очереди `default`, до 100 просроченных сроков за запуск. Срок хранится
в БД, повтор не дублирует переход; после простоя worker проверяет текущие условия.
Миграция `bots/0012_answered_handoff_recovery` добавляет nullable поля без
автоматического включения прежних диалогов. Для рабочего запуска нужны отдельно
разрешённое применение миграции и работающие worker/beat; Git-публикация их не запускает.
Правило возврата и исключения — [AI](ai.md#жизненный-цикл-preview-и-сбои).

14.10 владелец разрешил активацию таймера в текущей локальной рабочей среде.
`bots0012` применена к canonical `db.sqlite3` после проверенного SQLite backup;
старые диалоги и их состояния сохранены, старым handoff таймер не назначается.
Машинный runtime: `output/local-handoff-recovery/runtime.py`, команды через
`.venv/Scripts/python.exe`: `run` / `status` / `stop`. Один supervisor запускает
worker/beat только для `bots.resume_answered_handoffs` раз в 60 секунд; собственная
файловая очередь использует существующие Windows-зависимости local-file-antivirus.
Runtime, broker и backup — рабочие локальные файлы, не тестовый мусор.
Автозапуск после перезагрузки Windows не настроен; это не облачный Redis runtime.
Остальные задания, core0012, Meta/PS Cloud и production остаются вне этой операции.

CRM-S04: для локальной изолированной проверки есть
[`verify_recovery_s04.py`](../../scripts/verify_recovery_s04.py),
[команда и граница](../testing/testing.md#s04-postgresqlredis-recovery-drill).
Стенд создаёт собственные PostgreSQL/Redis, worker/beat и ClamAV, проверяет
перезапуск/аварийную остановку, повторы и отмену, экспорт/карантин файлов,
потерю очереди с восстановлением из БД и фактический restore БД/файлов/тестового
ключа. Отчёт хранит проверки и отказы доступа; временные данные и процессы удаляются.
Это не настройка рабочих служб или production backup: Windows solo/локальные
файлы не заменяют приёмку Linux workers, object storage и восстановления на другом
хосте. Само историческое испытание не назначало RPO/RTO и не выставляло
PAID_BETA_* flags; поздние принятые цели29.10 указаны ниже, их достижимость открыта.

Backup покрывает БД, закрытые файлы и доступность ключей для восстановления.
Проверить восстановление в отдельной цели, целостность tenant-связей, приватные
download и принятые цели RPO обычных данных≤15мин / RTO основных операций≤4ч,
затем документировать rollback приложения/миграций.
Не откатывать схему с потерей данных без согласованного плана. Из старых предложений
35 дней backup, RPO 1ч, retention 90 дней и 5/25/100GB нельзя делать
утверждённые нормы. Облачный общий cap 3GB и retention ещё требуют исполнения/
проверки в выбранной среде. Текущий upload limit 10MB не заменяется предложением 25MB.

## Карантин и антивирус

[core](../../apps/core) хранит приватные файлы и scan state; pending/scanning/
clean/infected/error. ClamAV INSTREAM разрешает файл только по корректному OK,
не по timeout/неизвестному ответу; fail closed. Worker leases/checksum защищают
от старого результата после замены/повтора. До clean запрещены download/использование
и parsing импортов; raw storage URLs/ручного обхода quarantine не добавлять.

ClamAV — внутренний сервис (3310 не публикуется наружу), scanner timeout 30с,
предельный возраст signatures 72ч по действующим defaults. Нужны file_scans worker
и периодический due-processing (15с). Проверить обновление signatures, недоступность
scanner, retry/recovery, private object cleanup и метрики в target environment.

Avatar: исходник до 5MiB JPEG/PNG/WebP, до 16M pixels и один frame; scanner проверяет
оригинал, сервер нормализует до JPEG 256px/128KiB без EXIF. Мimetype/расширение
не являются доказательством безопасности. Проверять права на загрузку/чтение.

Локальный runtime `output/local-file-antivirus` используется работающей системой:
это не одноразовый тестовый мусор. `runtime.py status` / `manage.py file_antivirus`
используются для диагностики; start/stop только в разрешённом scope и для своих
процессов. Автозапуск при входе в Windows не подтверждён. Не удалять runtime
при housekeeping документации и не заявлять local service как cloud deployment.

06.11 local scanner был недоступен. В рамках исправления upload обновлены signatures
и скрыто запущены прежние clamd/freshclam (daemon) с прежними конфигурациями;
worker/beat не запускались и не останавливались. Health и реальная загрузка Excel
прошли. PID и журналы: output/import-upload-alert-20261106/{scanner,updater}.pid,
scanner.out.log/updater.out.log. Сервисы оставлены для рабочего local upload;
автозапуск ОС не добавлялся. [Срез](../testing/evidence/import-upload-alert-20261106.md).

## Допуск и инциденты

CRM-S03 (решение владельца 14.10.2026, размещение уточнено03.11): по последующему
решению HEADER-CLEANUP индикатор фоновой обработки из merchant-шапки убран;
общая полоса также не отображается. Владелец и активные администраторы получают персональные SYSTEM-уведомления
о начале и устранении задержки. Учитываются настройки категории system;
повторное наблюдение не создаёт новый колокольчик. Неактивные аккаунты исключены.
RECORDS-BELL-FIX03.11: персональная проекция распознаёт серверный service-status
reference и выдаёт локализованный тип компонента/перехода вместо общего текста.
Произвольный исторический text/provider_reference не раскрываются; принадлежность
состояния Business проверяется, текущие recipient/access-фильтры сохранены.
Service-status API сохранён без индикатора в шапке. Прежний дефект конкретного
текста закрыт локальными API/browser-проверками; live не сертифицирован.
[Новый срез](../testing/evidence/records-bell-fix-20261103.md).
Сохранение перехода и уведомлений атомарно; in-app доставка не зависит от
очереди уведомлений. В колокольчике каждый получает только своё такое сообщение.

Состояние строится по текущей просроченной работе автоматизаций, внутренних
уведомлений, экспорта и проверки файлов. Исторические ошибки и неподключённые
необязательные провайдеры остаются диагностикой оператора. Сборщик запускается
beat раз в 60 секунд, обрабатывает до 100 бизнесов за проход с ротацией;
наблюдение старше 180 секунд считается неизвестным, а не восстановленным.
При росте числа бизнесов требуется проверить пропускную способность сборщика.
Устранение задержки не подтверждает успех каждой операции: результат доступен
в её истории. Полный отказ CRM требует будущего независимого внешнего мониторинга.
Миграция core0012 проверена в изоляции и29.10 применена к локальной рабочей БД
как зависимость notifications0007 по отдельному поручению (см. выше). Запуск
целевого worker/beat и применение в других средах требуют согласованного окружения.

PAID_BETA_* flags выставляются после реальных доказательств соответствующего
gate, не ради зелёного health. Проверить точный candidate, tenant/roles, целевой
DB/queues, backup/restore, мониторинг, rollback, provider delivery, клинический
рабочий день, ответственных и коммерческую границу. Незакрытое —
[acceptance](acceptance.md). Нет поручения запускать это в данной docs-задаче.

При инциденте сначала установить environment, impact, tenant boundary и текущего
оператора; сохранить безопасное evidence, ограничить ущерб, выполнить минимальное
обратимое восстановление в разрешённой границе. Не переигрывать внешние writes
и очереди вслепую. Проверить recovery и записать причину/регрессионную защиту.
Data exposure, потеря данных или необратимое действие требуют явного решения
владельца по затронутой операции; не расширять права для диагностики.

Происхождение: [production readiness](../../archive_docs/2026-10-07/docs/production/production-readiness.md),
[AV](../../archive_docs/2026-10-07/docs/security/file-antivirus.md).

## Локальная активация поддержки — 15.10.2026

По поручению владельца support0001 применена к canonical `db.sqlite3` после
SQLite online backup и проверки восстановления/целостности. Созданы пять пустых
таблиц поддержки; существующие бизнес-данные сохранены. Очереди доступны через
локальные backend8000/frontend5173; read-only API и HTTP smoke PASS.
Backup и отчёт находятся в `output/local-support/` и не публикуются в Git.

PLATFORM-INCIDENT-LINK-20261015 добавляет миграцию `support0002` с зависимостью
от `core0012`. Она проверена в изолированных БД и первоначально не применялась в scope15.10.
Позднее29.10 support0002/core0012 применены локально как зависимости notifications0007
после backup; это не подтверждение целевой облачной активации связей.
Поддержке не нужен отдельный worker; существующие процессы оставлены без изменений.
Это локальная активация, не deployment или приёмка облачной среды.


ADMIN-05: billing0006 создаёт offer/order/receipt/attempt/event; миграция проверена
в изолированных SQLite/PostgreSQL, к рабочей БД не применялась. Runtime defaults:
BILLING_COMMERCE_ENABLED=False, BILLING_CARD_ADAPTER=None. Нет рабочих предложений,
автоматического seed цен или выбранного банка. Активация, provisioning утверждённых
условий и реальный adapter требуют отдельного scope после коммерческих решений.
Тестовый адаптер включается только изолированным browser runner с проверкой disposable DB.
Рабочий rollout и expiry enforcement остаются открыты — [паспорт](../pre-production/subscription-usage.md).


## SSE мониторинга объявлений — локальная реализация

NOTIFICATIONS-SSE-20261029: выключен по умолчанию. Для выбранной среды API и
отдельный ASGI-процесс должны использовать одинаковые `NOTIFICATION_EVENTS_ENABLED=True`,
`NOTIFICATION_EVENTS_REDIS_URL` (по умолчанию REDIS_URL), `NOTIFICATION_EVENTS_NAMESPACE`,
настройки БД и JWT. Namespace разделяет среды. Redis не публикуется в браузер.
Запуск из канонической папки: `.venv/Scripts/python.exe -m uvicorn config.notification_asgi:application --host 127.0.0.1 --port 8001 --no-access-log`.
WSGI API остаётся отдельным. Vite направляет только `/api/notifications/events/`
в `NOTIFICATION_EVENTS_PROXY_TARGET` (по умолчанию http://127.0.0.1:8001).
Для будущей целевой среды необходим same-origin reverse proxy без buffering/cache,
с передачей Authorization и тайм-аутом больше heartbeat15с; deployment не выполнен.
Не передавать токены в query string и не логировать Authorization/Redis URL.

Поток доступен текущему owner/admin с MANAGE выбранного Business. Сессия, срок JWT,
активность и права перепроверяются при каждом событии и heartbeat. Максимум256
соединений на процесс,3 на пользователя; срок потока300с. В браузере backoff0.5–30с,
idle timeout40с, refresh JWT и resync после подключения. Потеря Redis не откатывает
сохранённую отметку: on-commit публикует лишь сигнал, API/БД — источник истины.
Опрос60с сохраняется; Redis Pub/Sub не гарантирует историю событий.
Локальная проверка: две независимые сессии, реальный Redis и отдельный ASGI,
остановка/запуск и пропущенное изменение восстановлены. При разрыве Vite защитное
восстановление заняло около40с; обычные изменения около1с. Точные проверки — PRIMARY.

## STAND-ACCESS-20261029 — пароль доступа к сетевому стенду

Для закрытого стенда обязателен `compose.stand.yaml` поверх базового Compose.
Обычная локальная конфигурация не включает эту защиту. Это дополнительный вход
перед приложением, не замена аккаунтов, MFA или tenant permissions.

`deploy/stand-access` — автономный Node24 сервис без npm-зависимостей. Caddy
проверяет каждую страницу, API и статический файл через forward_auth до upstream.
Форма `/_stand/access` содержит только пароль, RU/KK/EN, показ/скрытие, состояния
проверки и ошибки. Использует снимок semantic tokens проекта в brand.json;
изменения исходных tokens нужно синхронизировать в этот адаптер.

Пароль хранится как scrypt salt/hash. Cookie HttpOnly/Secure/SameSite=Lax,
без Domain, действует8 часов. Смена hash или signing key с пересозданием gate
отзывает все старые сеансы. `/_stand/access` после входа позволяет закрыть доступ
на текущем устройстве (очистка cookie); это не отзыв украденной копии токена.
CSRF проверяется подписью cookie/token и точным Origin. Referrer-Policy должна
оставаться strict-origin-when-cross-origin: no-referrer делает Origin:null при
отправке формы Chromium. Нет session/query secrets, пароля в HTML или логах.

Не более10 проверок пароля/IP и120 суммарно за15 минут. Счётчики сохраняются
в named volume `/state`; gate не масштабируется несколькими экземплярами с этим
локальным файлом. Перезапуск не сбрасывает лимит; удаление volume сбросит его.
Ключ IP берётся из перезаписанного Caddy X-Stand-Client, а не входного XFF.
За внешним CDN/reverse proxy потребуется отдельная проверка trusted-proxy/IP
настройки; текущий контракт — прямой публичный Caddy на VM.

На каждом сервере оператор запускает из корня проекта:

```text
node deploy/stand-access/setup.mjs https://REAL_STAND_DOMAIN
```

Интерактивный ввод скрыт; пароль минимум16 символов, отдельный для каждого
проекта. Скрипт создаёт игнорируемый `.env.stand.local` (не перезаписывает),
содержит STAND_ORIGIN, WEB_DOMAIN, STAND_PASSWORD_HASH, STAND_SIGNING_KEY,
STAND_WEBHOOK_PATHS. Это секретный server-only файл: не коммитить/публиковать.
STAND_ORIGIN должен совпадать с HTTPS origin публичного домена. Локальные тестовые пароли заданы в игнорируемых ENV; публичный сервер ещё не настроен. Для ротации новый файл генерируется оператором в закрытом
каталоге, затем безопасно заменяет серверную конфигурацию и пересоздаётся gate.

По умолчанию webhook-исключений нет. STAND_WEBHOOK_PATHS — JSON-массив точных
API paths; исключается только POST, не GET/OPTIONS или подмаршруты. Добавлять
только реально используемые входящие endpoints с собственной проверкой подписи,
секрета и повтора в backend. Не разрешать целиком /api/, login, files, health.
Gate не подтверждает подлинность webhook: это обязанность действующего адаптера.
Нативные тестовые приложения должны пройти тот же form/CSRF flow с cookie jar
и Origin; их токен обычного входа не заменяет допуск к стенду. Cross-site OAuth
POST callbacks и внешние виджеты требуют отдельной проверки перед активацией.

Публичны только80/443; остальные контейнеры/БД/gate не имеют published ports.
Проверить firewall и отсутствие альтернативных origin/IP перед приёмкой сервера.
Объектное хранилище остаётся приватным: gate не может закрыть публичный S3 URL
или отозвать уже выданный presigned URL. Резервные копии/бакеты отдельно защищены.
Отказ gate даёт502/503 и не открывает приложение. No-store/noindex не заменяют
контроль доступа и не удаляют ранее скачанные файлы/кэш на устройствах.

Проверки (без рабочей БД и реальных провайдеров):

```text
node --test deploy/stand-access/gate.test.mjs
node deploy/stand-access/verify-compose.mjs
node deploy/stand-access/verify-edge.mjs
```

Для verify-edge задать CADDY_BIN (Caddy2.10.2); для standalone Compose можно
задать COMPOSE_BIN, иначе используется docker compose. CI stand-access.yml
повторяет HTTP/Compose/реальный Caddy boundary. Docker image build и реальная
HTTPS/cloud/provider приёмка остаются этапом серверного развёртывания.

CRM stand activation (после подготовки рабочего env, frontend build и разрешения
на конкретное развёртывание; команды здесь не выполнялись):

```text
docker compose --env-file .env --env-file .env.stand.local -f docker-compose.yml -f compose.stand.yaml --profile workers --profile beat config --quiet
docker compose --env-file .env --env-file .env.stand.local -f docker-compose.yml -f compose.stand.yaml --profile workers --profile beat up -d --build
```

Нужен Docker Compose>=2.24: overlay снимает published8000/5432/6379 через !reset.
Caddy раздаёт заранее собранный frontend/dist; без index.html не стартует.
/static доступен после gate; /media не раздаётся напрямую, использовать private
file API/S3. YCloud opt-in path: /api/integrations/ycloud/webhook/ (подпись и
привязка Business остаются в backend). Полная настройка CRM, включая dedicated
ASGI/SSE при его включении, остаётся частью deployment runbook, не этого gate.


### Local password-gate preview (29.10.2026)

Start normal dev servers first, then run from the canonical root:

```text
node deploy/stand-access/dev.mjs CRM
```

Requires Node and Caddy; set CADDY_BIN in ignored .env.stand.local or process
environment. That file holds STAND_ORIGIN, password hash and signing key.
Local entry: http://127.0.0.1:5174 (upstream5173).
Cookies are namespaced per product so both gates coexist on localhost.
Direct development ports remain loopback-only and bypass this preview entry.
For deployment securely provision the file on the server, replace STAND_ORIGIN
with its exact HTTPS origin and WEB_DOMAIN with the real host, and use the
compose.stand.yaml activation commands above. Local HTTP URLs are not production
configuration. Test credentials are not committed; choose a private server password
before real user data. Public HTTPS/container acceptance remains unperformed.

## Vite development cache isolation (03.11.2026)

The application Vite config isolates optimized dependencies by resolved server
port and mode; production builds use a separate cache. Ports are strict: an
occupied port fails instead of silently selecting another port. Use a distinct
explicit `--port` for each concurrent test server. The default dev port is 5173.
`frontend/tsconfig.node.json` uses `noEmit` so `tsc -b` cannot generate a stale
`vite.config.js` that shadows `vite.config.ts` and restarts an active dev server.
For an existing checkout, stop its own frontend, inspect/remove only ignored
generated `frontend/vite.config.js` and `frontend/vite.config.d.ts` if present,
then restart frontend and reload the browser. Do not delete source configs or
stop unrelated servers. Backend and working database changes are not required.


### Приватное хранилище защищённого стенда — 06.11.2026

Стенд использует существующий приватный бакет `platforma-crm-private-kz-20261106`
в регионе `kz1`. Аккаунт приложения имеет ACL READ+WRITE только этого бакета;
политика ограничивает операции объектами и просмотром их списка. Анонимное чтение
и доступ к резервному бакету запрещены; подписанные ссылки включены.
Пятиминутная резервная копия сначала синхронизирует S3 в закрытый локальный кэш
с манифестом SHA256, затем сохраняет его существующим зашифрованным restic-процессом.
Восстановление проверено на синтетическом объекте. Пароль стенда сохранён.
Для проверки свежести антивирусных баз на локальном ClamAV включена команда VERSION.
Доказательства, границы проверок и пути отката: `output/observability-storage-20261106/STORAGE-RESULT.txt`.
