## Website widget recovery — 12.11.2026

Widget сохраняет conversation ID, последние100 подтверждённых пользовательских
сообщений и draft/name/phone в sessionStorage текущей вкладки. Ключ включает
API URL, public token и visitor ID; reload продолжает ту же беседу. При недоступном
storage остаётся работа в памяти. Приватная история CRM не загружается.
Ввод очищается только после успешного ответа; ошибка сохраняет draft и предлагает
ручной retry. `language` ru/kk/en опционален, иначе используется язык страницы.
Нет гарантии exactly-once при потере успешного ответа или межвкладочного transcript sync.
Origin/tenant/rate limits сохранены. [Изолированные проверки F06/F07](../testing/evidence/crm-global-fixes-20261112.md).

## Мастер переноса — решение04.11.2026

[Контракт переноса и адаптации представлений](import-workspace.md) фиксирует
локально реализованное расширение: файлы → клиенты/специалисты/услуги/записи,
дополнительные поля, редактируемый черновик и preview таблиц/карточек/календаря.
Локальная целевая проверка завершена; публикация заблокирована, целевой rollout не выполнен. Существующий
ограниченный importer ниже не считается этим расширением. AI в первый этап
не входит; возможный помощник — отдельное будущее решение, не обязательство.
Владелец подтвердил сценарий и референсы. В том же контракте записана сверка
прежнего UI/API до реализации мастера: там доступна коррекция mapping, но не значений строк; preview показывает
образец исходного файла, а не будущие карточки/календарь. AUD-12a/b сохраняют свой
ранее проверенный scope, не означают реализацию нового мастера.
Прямые подключения/синхронизация/денежные остатки отдельно. Не закрывает открытые
acceptance и не разрешает рабочие миграции или deployment.

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

# Интеграции, импорт и экспорт

AUD-12c,31.10: история фоновых экспортов в Аналитике читает сохранённые ExportJob.
GET /api/export-jobs/ принимает business/kind/status до пагинации,20 записей по
умолчанию, максимум100, порядок -created_at/-pk. Список и detail ограничены текущим
actor/Business и действующим VIEW/capability соответствующего ресурса. В параметрах
истории выдаются только start/end/expected_rows, без внутреннего fingerprint.
Скачивание повторно проверяет текущие права и исходный permission fingerprint.
Синхронный небольшой CSV не создаёт ExportJob и в эту историю не попадает.
Страницы/размер, фильтры, reload/download, polling и503/retry проверены локально.
Новые каналы экспорта, worker/storage целевой среды и deployment не заявлены.
[Evidence AUD-REMAINING](../testing/task-state/PRIMARY-SESSION.md#aud-remaining-20261031--aud-12c-and-aud-v01).


Действующие ограничения; уточнение 14.10.2026: Telegram и WhatsApp включены
в подготовку пилота R02, клиники подключают собственные аккаунты. Уточнение27–29.10:
официальный временный BSP с переносимостью к Meta; GREEN-API QR не замена. Для первого этапа
28.10 выбран YCloud TP Lite; локально реализованы подключение и текстовый Inbox.
Реальная отправка/подключение не выполнены. Прочие внешние подключения,
полный marketplace write-back, 1С/МойСклад и платёжный gateway остаются отложенными.
Принятый ограниченный CRM-Market exchange/кампании описаны отдельно ниже. Код сохраняется,
но наличие adapter/endpoint не доказывает live-ready статус. Новые подключения
требуют конкретного target и согласованного объёма. Пилот финансирует владелец;
новые коммерческие лимиты/автоотключение по расходам не вводятся. Это не отменяет
технические rate limits и защиту от злоупотреблений. Решения —
[CRM-R02](../testing/task-state/PRIMARY-SESSION.md#crm-r02-20261014--pilot-decisions-and-provider-research).

## Connector boundary

### YCloud TP Lite — первый этап

Существующие BotChannel/BusinessConnector и WhatsApp Inbox переиспользуются.
Сервер создаёт временную ссылку, связывает попытку с каналом и подтверждает номер
только по подписанному webhook и серверному API YCloud. Redirect/состояние браузера
не подтверждают подключение. Ссылка не сохраняется в БД или browser storage;
ключ API и signing secret находятся только в серверном окружении. Доступ к setup:
INTEGRATIONS VIEW для чтения, MANAGE для начала, отмены и повторной обработки.
Фоновая привязка повторно проверяет права инициатора и ревизию настройки.
Сервисы перечитывают активность аккаунта; отключённый инициатор не завершает
ожидающее подключение, даже если передан ранее загруженный объект пользователя.

Приём сохраняет подписанное событие до ответа 204; worker/beat обрабатывает его
с дедупликацией, транзакцией и ограниченными повторами. Business определяется
серверной связью WABA/номера, а не переданным CRM ID. Текст идёт через существующий
Inbox/CRM/AI pipeline. Один номер на подключение; media, templates, напоминания,
история в этот этап не входят. Расширение Coexistence от 09.11 описано ниже.
Подписанное сообщение без готовой привязки получает retryable503, а не успешный
ответ: callback может опередить подтверждение номера. После привязки повтор
сохраняется и обрабатывается один раз; чужой маршрут не создаёт CRM-эффектов.

Отправка фиксирует отдельную попытку до HTTP, повторно проверяет канал, текущие
права сотрудника и 24-часовое окно. `accepted` означает только приём провайдером;
`sent`/доставлено/прочитано подтверждаются его результатом или подписанным статусом.
Неопределённый POST получает `delivery_unknown` и не повторяется автоматически
или вручную до разрешающего события. Явный rate limit повторяется ограниченно;
старые статусы не откатывают доставку и не меняют новую попытку. Обычные Meta-пути
не принимают YCloud-канал. Пауза блокирует новый обмен, сохраняя приём статусов.

Версия и проверки: [YCLOUD-TPLITE-20261028](../testing/task-state/PRIMARY-SESSION.md#ycloud-tplite-20261028--tp-lite-and-inbox-text-local-scope-complete).
Это локальная реализация; TP Lite eligibility, целевой HTTPS webhook, доступ к номеру,
финансирование, рабочая миграция и live delivery остаются отдельной приёмкой R02/R03.

Coexistence (локальная подготовка 09.11.2026): форма позволяет выбрать сохранение
WhatsApp Business App и обязательный ожидаемый номер E.164. Сервер запрашивает
`WHATSAPP_BUSINESS_APP`; подтверждённый номер должен совпасть с ожидаемым.
Существующие связи после integrations0010 сохраняют режим WhatsApp API.
Подписанные `whatsapp.smb.message.echoes` и `whatsapp.smb.message.created` сохраняются
как уже отправленный ответ сотрудника с дедупликацией по wamid. Они не запускают AI,
не отправляются повторно, не увеличивают unread и не открывают 24-часовое окно.
Ответ из приложения приостанавливает AI до ручного возобновления; ожидающие
автоответы отменяются. Уже выполняющийся внешний HTTP-запрос отозвать невозможно.
Вложения отображаются как сообщение о недоступном содержимом без загрузки файлов.
История, шаблоны и напоминания не добавлены. При паузе CRM-канала ответы из приложения
продолжают отражаться в Inbox: приложение работает независимо от паузы CRM.
Допуск конкретного номера, включение TP Lite и обмен с провайдером требуют live-приёмки.

### Общие правила и подтверждённые исправления

OFFICIAL-03: WhatsApp verification carries an explicit Meta/global-internal/channel
identity into routing. Channel mode revalidates its active channel, Bot and Business;
supplied phone IDs must match that channel's configured/external aliases. Global
verified modes require an unambiguous active route. Every Meta change is resolved
before business writes, including changes ignored by the existing status-first /
first-message behavior. Status lookup also binds the Bot, and stored payload/log
copies contain only their associated change. HMAC precedence/live requirements,
generic channel messages, deduplication and existing credential storage remain.
Local102-test evidence: OFFICIAL-03-20261028 in PRIMARY-SESSION. No provider rollout,
real delivery, working credentials or live readiness is implied.

META-DELIVERY-20261114 extends direct Meta text delivery locally. The webhook
preflights the entire envelope, then handles every message and status across
entries/changes in one transaction. Per-message copies retain only the matching
contact and authenticated business route; replay reuses the inbound message and
does not repeat its CRM effects. The response retains the legacy single-message
IDs and adds a list for batches. Unsupported media still rejects the packet;
media download/transcription is not part of this change.

Inbox Meta sends commit an attempt ID in the existing outbox before HTTP and
echo it through `biz_opaque_callback_data`. API acceptance is `accepted`; a signed
receipt establishes sent/delivered/read. Ambiguous POST results or a stale worker
with a committed send intent become `delivery_unknown`, without automatic or
manual resend. Explicit rate-limit rejections use bounded delayed retries; other
definite rejections fail. Receipts remain tenant/recipient/attempt-bound and do
not regress read/delivered state or overwrite a newer attempt. Missing receipts
leave an unknown result unresolved; this is not an exactly-once provider promise.
The original local-only change did not include deployment. Under subsequent
META-PILOT-20261114 authorization, its seven runtime files were deployed to the
test stand, a temporary credential was refreshed, and the Meta app was published.
AI/autoreplies remain off; no schema change or Embedded Signup deployment was
included. Live inbound and duplicate replay passed; one manual reply was delivered
using a process-local workaround for Meta's test-recipient formatting. Ordinary
queued sending with the persistent opt-in setting and a validated SYSTEM_USER token
subsequently passed on14Nov18:43:08UTC (reply40); actual signed receipt replay made no duplicate.
Scope, exact frozen candidate checks and rollback: META-PILOT-20261114 in
PRIMARY-SESSION. Publication is not proof of Advanced Access or client onboarding.

META-PILOT-STABLE-20261114 adds an opt-in server setting
`WHATSAPP_META_TEST_RECIPIENT_ALIASES`, default `{}`. Its JSON shape is
`{"sender_phone_id":{"canonical_recipient":"meta_test_recipient"}}`.
Only an explicitly listed Kazakhstan recipient (11 ASCII digits starting76/77)
can use the demonstrated Meta test-list variant with national8 after country7.
Other sender IDs and recipients retain their original addresses. Arbitrary
forwarding aliases fail before HTTP. This is not a general number-normalization
rule and must not be populated from customer input or copied to live-number setup.
An operator must first verify the test list's generated request and a signed
callback identifying the same canonical recipient. The aliased API response must
confirm that canonical `wa_id`; missing/mismatched identity leaves delivery unknown
and forbids blind resend. Conversation identity, service window, tenant routing
and receipt matching remain canonical. Remove the entry when the test-list defect
is resolved or the sender is replaced. Deployment/acceptance status is recorded
under the same task in PRIMARY-SESSION.

OFFICIAL-09: catalog ingestion of Service metadata uses the same SETTINGS UPDATE
and all-current-branches boundary as ordinary Service changes, in addition to
existing INTEGRATIONS admission. Existing inactive/archive flags remain unchanged;
activation/restoration require their explicit actions. Manual Service/event/audit
and imported Service/event writes are atomic; denied confirmation rolls back the
whole import. Product-only events, aliases, exact-name matching and summary semantics
are preserved. Local evidence: OFFICIAL-09-20261028 in PRIMARY-SESSION; no live-provider
or PostgreSQL concurrency certification is implied.

Provider-specific поведение живёт за service/provider adapter, не в views/UI.
Существующие слои: [integrations](../../apps/integrations),
[bots](../../apps/bots), [BusinessEvents](../../apps/integrations/models.py).
Использовать существующие модели/нормализацию вместо нового параллельного контура.
CRM — потребитель бизнес-сигналов, не полная копия ERP/склада.

Connector отражает supported modes, setup/status, masked credentials, health,
last sync/webhook, безопасную ошибку и доступный retry/reconnect. Проверка прав,
tenant и связей выполняется сервером. Merchant setup содержит необходимые поля;
raw webhook/debug/provider stack не занимает повседневный экран.

Platform diagnostics uses one connector classification across counters and queues:
`error`, `failed`, `expired_credentials` are failures; `needs_attention` is setup
attention, counted separately. The attention queue includes both groups; disabled,
disconnected and draft connectors do not enter it. Connector state alone does not
prove a background-service outage or recovery; component observations remain separate.

Credential хранится за `ConnectorCredential`, не в `BotChannel.config_json`.
Конфигурация канала содержит безопасные metadata/configured flags. Не возвращать
secret в serializer/log/task payload. Ротация требует совместимого чтения старого
ключа, проверки нового, ограниченного dry-run и отдельного разрешения на целевую
среду; старый ключ не удалять до доказанного завершения перепаковки и восстановления.

Webhook проверяет подлинность доступным provider-механизмом до изменения данных;
разрешение tenant берётся из серверной привязки, не из недоверенного payload.
OAuth state/redirect, credential ownership и setup версии проверяются сервером.
Запоздавшие sync/setup/results не перезаписывают более новую конфигурацию.

Нормализованные события сохраняют источник и внешний ID, дату, Business и
достаточную provenance; не создавать CRM-дубли при webhook/pull/replay.
Idempotency, транзакционная граница, concurrency, backoff, max attempts,
pagination/cursor и recovery должны быть явными. Не делать бесконечный retry
для auth/validation errors; не заявлять внешнюю доставку по локальному enqueue.
Фоновая работа повторно проверяет актуальные права, конфигурацию и отмену.

Marketplace по умолчанию read_only. Отдельный inventory_write означает только
остатки с warehouse/product mapping и локальными reservation/release, не изменение
цены, карточки или заказа. Это отложенный контракт, не текущий допуск к записи.
Нельзя смешивать внешний доступ и merchant role или включать writes по health PASS.

Финансовый reader принимает только проверяемый источник и точный период,
идентифицирует валюту, completeness/freshness и provenance. Неполные/stale данные
дают явное no-data/recovery. Выбор manual или одного external и ограничения KPI —
[CRM](crm.md#деньги-и-аналитика). Реестр external financial readers пока пуст;
общий connector не становится денежным источником автоматически.

AUD-14, 17.10: generic message API не позволяет менять историю или назначать delivery
state, external IDs, raw payload и timestamps. Authenticated inbound-text POST имеет
allowlist, client sender и parent permissions; он не подменяет доверенный webhook.
Исходящие send/retry и запись provider metadata остаются за существующими сервисами.
Проверки локальные, с mock/изолированной доставкой: checkpoint AUD-14-20261017;
активация провайдера, credentials и rollout этим не меняются.

## Импорт, экспорт и public ingress

CSV/XLSX импорт переиспользует [imports](../../apps/core/import_export.py): роли/Business,
upload limits, карантин/scan до parsing, preview/mapping/validation, проверку
связей и дублей, подтверждённое выполнение, прогресс и результат. Не применять
сырой payload как произвольные модели/поля; retry не дублирует выполненную работу.
Рабочую базу не seed/reset ради проверки. Отдельно доказывать rollback/частичный
результат согласно фактическому режиму импорта, а не обещать общую атомарность.

AUD-12a,31.10: DTO задания включает read-only `mapping_fields` и компактный
`errors_json` (первые50 `rows` и полный `count`). Все ошибки сохраняются в пределах
лимитов исходного файла; `GET /api/import-jobs/{id}/errors/?page=1&page_size=20`
возвращает count/next/previous/results, максимум100 на страницу, с текущей
проверкой Business/actor/VIEW. Старые усечённые ошибки пересчитываются через
preview. В существующем импорте заявок доступны ручное сопоставление, повторный
preview, все страницы ошибок с полем/причиной и загрузка исправленного файла.
После изменения mapping, неуспешного preview или выбора нового файла подтверждение
недоступно до проверки. Preview не запускает import автоматически. CREATE остаётся
обязательным; новый источник/тип не меняют существующее задание. Полная история
импортов реализована в AUD-12b ниже; история фоновых экспортов реализована в AUD-12c ниже. Проверки — [AUD12a](../testing/task-state/PRIMARY-SESSION.md#aud-12a-20261030--import-mapping-and-error-recovery-verified).

AUD-12b,31.10: `GET /api/import-jobs/?business=<id>&entity_type=leads&page=1&page_size=20`
валидирует необязательные фильтры до пагинации, возвращает count/next/previous/results
со стабильным порядком `-created_at,-pk`,20 по умолчанию и максимум100. Без фильтров
сохранён список доступных заданий текущего actor; Business/CLIENTS VIEW проверяются
как прежде. Detail принимает тот же контекст, неверный Business/entity даёт404.
Общий ImportPanel использует серверные страницы/счётчики и отдельно читает выбранное
задание. Ошибки списка/деталей имеют повтор без показа старого задания; смена actor/
Business/entity сбрасывает состояние. Загрузка выбирает новое задание на странице1.
Проверен существующий вход через Заявки; новые входы/каналы не добавлялись.
[Evidence AUD12b](../testing/task-state/PRIMARY-SESSION.md#aud-12b-20261031--complete-import-history-verified).

AUD-16: `POST /api/import-jobs/` принимает только `business`, `entity_type` и
`source_file`; остальные входные поля отклоняются400. Actor и имя файла берутся
сервером, все результаты/счётчики/timestamps управляются сервисом. Generic
PUT/PATCH/DELETE не поддерживаются405; Django admin показывает историю read-only
без ссылки на source_file. Контекст и источник существующего job неизменяемы.
`POST /api/import-jobs/{id}/preview/` принимает только `mapping` — объект
поддерживаемое поле → существующий заголовок файла. Некорректный mapping400
не меняет сохранённый preview. Без mapping сохраняется выбранное соответствие
или применяется автоопределение; неизвестные заголовки возвращают preview с
ready=false, чтобы mapping можно было исправить отдельным preview.
Preview и confirm держат row lock ImportJob до конца транзакции и перечитывают
состояние после ожидания. IMPORTED/CANCELLED нельзя открыть preview повторно;
confirm разрешён только из PREVIEWED. Проверяются актуальные actor/CREATE/модуль,
исходные ограниченные байты и AV, mapping и строки, а не доверенные клиентом
preview/errors. Ошибка до commit откатывает CRM-записи, события, sync и audit,
сохраняя предыдущее состояние job для повтора. Scanner unavailable возвращает
503 temporary_service_failure с retryable=true, без импорта. Последовательный
повтор confirm завершённого job отклоняется400. Начальное состояние lead/deal
проверяется доменными creation services (AUD-20). Импорт заявки поддерживает колонку
`lost_reason`: LOST без причины, причина при другом статусе и неизвестный непустой
status дают row/field errors в preview и повторно на confirm. Пустой status — NEW.
Сервер создаёт время/автора потери и начальную историю атомарно с импортом.
Импорт сделки выбирает только активную открытую стадию; если её нет, ошибка
откатывает импорт и позволяет повтор после исправления конфигурации.
AUD-21: в изолированном PostgreSQL17 подтверждены ожидание блокировки вторым
confirm, откат после записи строки и финального audit, затем один успешный
импорт и отказ повтору. Откатившаяся попытка не оставляет CRM-записей, событий,
sync, audit или on_commit callbacks; ожидающий запрос перечитывает PREVIEWED.
Runtime-изменений сверх AUD-16 не потребовалось. Evidence и версия —
[AUD-21 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-21-20261021--concurrent-import-rollback-and-recovery).
OFFICIAL-10 Inbox scope, 28.10: child DTO replies require current independent
VIEW. Write acknowledgements/status, Client duplicate confirmation and actual creation/
dedup logic remain. Inbox Task/Appointment idempotent replies resolve stored model/id
inside the same Business, apply current read scope and actor-aware serialization;
receipt JSON is retained, with no cached-body fallback for missing/foreign/invalid
resource. Generic other command callers keep their previous behavior and are not
newly certified. Pipeline/booking typed metadata copies follow the same read policy;
offered slot without saved Appointment remains parent workflow data. Checkpoint/report
OFFICIAL-10-INBOX-20261028 provides synthetic evidence and exact scope.

OFFICIAL-16, 28.10: Lead duplicate-check scopes related Lead DTOs before its
existing five-row limit; hidden messages/status/IDs are not serialized. Generic warning
is retained through an optional restricted-match boolean, without hidden count. Existing
Client duplicate projection is reused; internal matcher, public form writes,
legacy archived matching and provider behavior unchanged. Import Client writes follow
OFFICIAL-17 per-row CREATE/UPDATE and private-field policy. OFFICIAL-16-20261028 evidence.

FU-BE-03, 28.10: stored import duplicate DTOs are projected on every response using
the current reader's Client visibility, not the job creator's earlier authority.
Hidden/missing/foreign Client details become a generic warning; uploaded row payload,
summary, file-local Duplicate row N warnings and stored evidence remain intact.
Import matching and scanner behavior remain unchanged. Confirm Client writes now
additionally enforce current per-row CREATE/UPDATE and private-field policy (OFFICIAL-17). Current VIEW revocation
cannot re-release a stored duplicate contact. Form submission/activity copies use the
same projection. See FU-BE-03-20261028 checkpoint and local synthetic packet report.

FU-BE-02, 28.10: outreach preview/consent/recipient/failed appointment read
projections require current Client visibility before returning contact IDs/values,
personalized text or provider/evidence copies. Audience eligibility/counts, delivery,
consent writes and W1 STOP remain unchanged. Parent Lead/Deal CSV masks hidden Client
IDs and ready-export access includes Client policy/capability/scope in fingerprint;
files made under the previous fingerprint require regeneration. Existing CSV headers
and permitted values remain. Local synthetic checks in FU-BE-02-20261028 evidence.

OFFICIAL-13: appointment automation status also checks NOTIFICATIONS VIEW/capability
and current row scope before counts/top-eight failures. An unreadable linked Appointment
returns no appointment ID/navigation URL. Calendar URLs use the current readable linked
Appointment rather than saved identifier copies, including detached links. Client redaction remains independent. The
three-scenario response and delivery/retry behavior are unchanged. Notifications has
no module toggle in the current mapping; use of the shared guard does not add one.

OFFICIAL-05, 28.10: public lead-form and website-chat capture continue accepting
intake, but affirmative marketing flags cannot reset matched contact OPTED_OUT.
Both use the common helper's conditional write. New/unknown/already-IN explicit
consent behavior, aliases and channel independence remain. Existing Telegram/
WhatsApp inbound START and authorized management paths are unchanged; no message/
confirmation service or new re-consent standard added. W1 STOP remains separate.
Evidence and local controls: OFFICIAL-05-20261028 checkpoint and packet report.

OFFICIAL-11, 28.10: consent bulk-import-file XLSX delegates to the same bounded
read_xlsx_rows used by tabular imports, after bounded actual-byte read. Reader errors
are returned under file; no consent writes occur before complete valid normalization.
Header aliases, cell normalization, statuses/evidence, authorized Business/role and
CSV/JSON business flows unchanged. Resource-limit overflow is explicit, never silently
trimmed. API/control evidence: OFFICIAL-11-20261028 checkpoint and packet report.

AUD-22: XLSX проходит ZIP/XML preflight до openpyxl: размер разжатого архива,
compression ratio, число записей, dimensions и фактические координаты/число
строк/столбцов ограничены. Заниженные dimensions не обрезают данные. Превышение
даёт400 без частичного импорта; после исправления файла возможен новый upload.
Reader/iterator/workbook закрываются и при ошибке. Лимиты всех листов, включая
пустые строки, и значения env — [operations](operations.md#лимиты-xlsx-импорта).
Обычные роли/tenant/AV и доменные транзакции сохранены. UI mapping/errors/history
AUD-12a/b/c локально проверен30–31.10; описание и evidence приведены выше.
Версия и граница проверок — [AUD-16 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-16-20261019--import-job-write-boundaries).

Public lead/widget ingress привязан к разрешённому business/form/channel,
ограничен validation/rate limits/origin policy и не раскрывает приватные CRM-данные.
Секретный API token не размещается в браузерном виджете; клиентские данные
и ответы провайдера недоверенные. Сообщение идёт через существующий Inbox flow.

Экспорт permission/capability/tenant-scoped: маленький CSV синхронно,
большой — `202` + `ExportJob`, polling и закрытый download. Worker повторно
проверяет доступ актёра и модуль. Defaults: sync 5000 строк, максимум 100000,
report range 366 дней, sync report 90 дней, stale job 900 секунд.
Очередь `reports_exports` и beat `exports.process_due_jobs` обязательны для
фонового пути; ошибки/stale видны в platform operations. Значения конфигурации
сверять с текущим кодом перед изменением среды.

## Скачивание сохранённого экспорта — AUD-18

При генерации ExportJob сервер сохраняет fingerprint контекста доступа в
parameters_json и сверяет его до/после формирования CSV. Download проверяет
активного пользователя, Business, VIEW, capability и совпадение fingerprint.
Он включает actor, scope, доступные филиалы, состав команды и набор доступных
ID для OWN/TEAM; отчёты учитывают также права исходных ресурсов и область
показателей команды. Изменение контекста при генерации даёт FAILED без файла.
Изменение контекста после генерации или старый файл без fingerprint дают403:
нужно запросить новый экспорт. Полный отзыв Business/membership сохраняет404.
Неподготовленный файл по-прежнему даёт400. При отказе байты не выдаются и
успешный file_download audit не создаётся. Старые файлы не переписываются.

Это консервативная проверка равенства: расширение прав, изменение состава
доступных записей OWN/TEAM или филиалов тоже может потребовать нового экспорта.
Branch grants не становятся фильтром чтения общей клиентской базы; действующий
CRM-MB01 сохраняется. Приватные Client.notes дополнительно маскируются при
скачивании по текущей field policy (AUD-03). Fingerprint привязан к actor:
просмотр job платформой не разрешает скачивание файла другого исполнителя.
Уже скачанные копии и начатую передачу файла отозвать нельзя. Проверка не вводит
общую блокировку изменений прав на время HTTP streaming.
Локальная проверка и версия — [AUD-18 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-18-20261027--current-export-download-authorization).
Рабочая БД, схема, live worker/storage и deployment не менялись.

## Принятые CRM-Market сценарии — 29.10.2026

Будущая граница CRM-D02/CRM-C21 из ТЗ§23 не возвращает весь ERP/write-back.
Решение владельца02.11: обмен CRM↔Market и кампании Market через CRM исключены
из текущего пилота; реализация после отдельного возобновления. Требования ниже
сохранены для дальнейшего развития, не являются gate пилотных каналов R03.
Опциональная проверенная связь Market legal entity↔CRM Business допускает
настроенный обмен заказами/статусами/документами и платёжными/возвратными фактами.
Нужны object/direction/source/purpose/version/actor/idempotency/correlation и
revoke/replay/reconciliation без sync-loop. Предлагаемые поля события — проект,
не уже согласованный endpoint. Market хранит подписанный оригинал; назначенная
CRM-роль получает разрешённый документ без обязательного Market-login через
защищённую повторную авторизацию. Полученный факт не второй manual receipt и
не команда подписи/refund; финансовая панель Market остаётся в Market.
Критерий AC-CRM — обе стороны, tenant/role/revoke/duplicate/outage/version и
история; готового нового транспорта/API/live evidence этим не объявлено.

Команда ведёт кампании Market через CRM: сегменты потенциальных/новых/действующих
участников, покупателей/поставщиков/агентов; invitation/onboarding/cart/repeat/
reactivation. WhatsApp/email/Telegram обязательны в этом отдельном scope,
Instagram желателен. Preview → малая стартовая группа → расширение по результатам;
тексты/сегмент/размер/критерии/бюджет и канал выбираются явно, не 50/200 по примеру.
Общий лимит — не более одного рекламного контакта человеку за семь суток по всем
кампаниям; сервисные сообщения отдельно. Current versioned consent/STOP проверяется
до launch/delivery; первый входящий и Market event не дают рекламного согласия.
Нужны reachable UI/continuation/errors/recovery без дублей и controlled receipts
AC-CAMPAIGN; W1/OFFICIAL/FU scoped guards не закрывают весь flow.
После ограниченных retries важной service-недоставки создаётся задача
ответственному; другой канал только разрешённый. Retry count/schedule, единый
recipient key и in-flight STOP/unknown — подготовка CG-05, не обещание отмены
уже отправленного HTTP. Telegram требует разрешённого контакта, email — своей
настоящей доставки. Клинический R03 не превращается в массовую рекламу.

Для BSP нужны capabilities и полный cost/eligibility/onboarding/WABA/number/
ownership/webhook/migration-to-Meta receipt. GREEN-API QR не принят как замена;
YCloud local text slice и подготовка Coexistence не подтверждают templates/reminders/media,
live Coexistence,
договорную/правовую пригодность или доставку двум клиникам. [Roadmap](roadmap.md#crm-d02--принятая-граница-связи-с-market-и-кампаний).

## Граница доказательств

Mock/eager/SQLite подтверждают локальную логику. Реальный provider, подпись,
доставка, rate limit, worker/Redis/PostgreSQL и recovery требуют отдельного evidence.
Проверять happy path, denied role, foreign tenant, masking, duplicate/replay,
timeout, revoked credential и возобновление. Не отправлять сообщения реальным
получателям и не менять provider data в обычной автоматической проверке.
Оставшиеся gaps — [acceptance](acceptance.md); target — [operations](operations.md).

Архив происхождения (не текущий rollout-план):
[blueprint](../../archive_docs/2026-10-07/docs/integrations/CONNECTOR_BLUEPRINT.md),
[provider rollout](../../archive_docs/2026-10-07/docs/integrations/provider-rollout.md).


ADMIN-05: SaaS card payments используют отдельный billing adapter (checkout,
authenticate_notification, lookup), а не merchant Connector. Redirect и payload
не подтверждают поступление: результат повторно читается у адаптера. Неопределённый
checkout запрещает вторую попытку до сверки; receipt и application сохраняются
отдельно, повторы идемпотентны. Реальный adapter не выбран; FakeCard доступен только
в изолированных тестах. Нет BusinessEvent/AI-trigger, отправки писем или реальных денег.
Оставшиеся provider/live требования — [паспорт](../pre-production/subscription-usage.md).


## OFFICIAL-17 Client mutation authority in import, 28.10.2026

OFFICIAL-17, 28.10.2026: Client import writes now distinguish current UPDATE
for existing matches (including archived/no-op) from CREATE for new Clients, under
the existing object policy. Shared Client notes write rule is reused by API/import;
proposed fields are validated before mutation. Client/Lead/Deal sheets use the same
Client boundary/current request actor; legacy direct row calls use job.actor, no actor
fails closed. Fill-only matching, duplicate warning, archive state and atomic rollback
remain. Existing ImportJob CREATE admission remains, not an update-only upload feature.
27 new tests within103 affected and combined1040 PASS/no skips; syntax/system/drift/
diff/reverse PASS. HEAD98925b67 + previous WIP/16 closed findings + patch, local only.
Evidence OFFICIAL-17-20261028 checkpoint and output/security-remediation-20261028/
client-import-update-permission/fix-report.md. Current OWN/TEAM UPDATE semantics for
unowned Client retained exactly; no new ownership rule or production certification.
