## Общая проверка CRM: исправления — 12.11.2026

Все десять подтверждённых F01–F10 исправлены и адресно проверены: архив/права
клиента, поиск, причины409, refresh переноса, widget reload/retry, смена пароля,
demo reset и локализация системных значений. Backend/Node/build/system/drift
и scoped browser PASS; составной локальный снимок, без real sends/workingDB/deploy.
Семь других test failures, три provisional observations, непокрытая204-ID матрица
и S04/load остаются открытыми. Полная CRM/release готовность не заявляется.
[Исправления, проверки и ограничения](../testing/evidence/crm-global-fixes-20261112.md).

VOICE-PLANNER11.11: воспроизведён неверный JSON field plan при точном STT.
Default/tier модель теперь определяется до JSON capability; parser/права/replay
сохранены. До исправления1из12FAIL; после24/24real synthetic API→Client/replayPASS,
48planner calls в json_object.148сценариев проверены:146PASS сразу,2старых fixtureFAIL
устранены после old/current сравнения; финальный quality+regression30PASS,system/driftPASS.
Scoped остатка кода/проверок нет; human/fullD01/production остаются открыты.
[Причина, точные границы и результаты](../testing/evidence/voice-planner-20261111.md).

## Точность голосовой диктовки — 11.11.2026

VOICE-RECOGNITION11.11: Scribe v2 и точное преобразование отдельных цифр телефона
заменили ошибочный Whisper default.10 synthetic STT/API→CRM/replay PASS,118 backend
и system/driftPASS. Отдельный дефект JSON-режима закрыт срезом VOICE-PLANNER11.11;
human/KK/mixed/noise/fullD01/production не закрыты.
[Сравнение, стоимость, проверки и остаток](../testing/evidence/voice-recognition-20261111.md).

## История действий — 11.11.2026

`/app/timeline`: понятные RU/KK/EN события, разрешённые сохранённые изменения,
название объекта отдельно от клиента и автор действия. Имена/ссылки проходят
текущие права ресурса и Business; mobile использует компактный список и раскрываемые
фильтры. Это локальный scoped результат, не новая release/live сертификация.
[Evidence](../testing/evidence/timeline-fixes-20261111.md).

## Локальная интеграция лендинга — 06.11.2026

Предоставленный лендинг включён в обычную сборку CRM и доступен в корне;
вход использует существующий `/login`. Локальные build/browser/Caddy проверки
пройдены; лендинг опубликован как1dc5a6c8 (CI PASS) и развёрнут на защищённом
стенде отдельной static/Caddy-дельтой с сохранением прежней SPA и пароля.
Главная/форма входа/языки/mobile/HTTPS/backup проверены; вход в учётную запись
после этого развёртывания не выполнялся. [Evidence](../testing/evidence/crm-landing-integration-20261106.md).

Дельта по решению06.11: автоматическая основная точка без повторного каталога,
явная настройка второй точки, серверный запрет архивирования последней активной,
контекст филиала и конкретные уточнения голосовой записи реализованы.
Локальные проверки, состояние рабочей схемы и остаток публикации —
[SINGLE-LOCATION-20261106](../testing/evidence/single-location-20261106.md).
Исторический MB1–MB5 PASS не подменяет проверку этой дельты; full D01/live открыты.


IMPORT-WORKSPACE04.11: локально реализованы CSV/XLSX → клиенты, услуги,
специалисты и записи; исправления/поля/связи/профили, preview и фоновой перенос.
Дополнительные поля доступны в обычных consumers/фильтрах/экспорте. Перенос без
creation effects, будущая активация отдельная. Публикация/рабочие миграции/live
не заявлены. [Точная граница](../testing/evidence/import-workspace-20261104.md).

C02 / TEAM-ANALYTICS, 04.11.2026: `/api/team/performance/` intersects Lead
selection with current LEADS VIEW scope and enabled capability before counts,
loss reasons, rates and team summaries. Existing report membership and source/date
filters remain; denied/disabled Leads yield zero/empty fields. Other independently
readable source metrics are unchanged and not certified by this Lead-only fix.
Local evidence: [C02](../testing/evidence/remediation-c02-20261104.md).

CRM-R01, первый пакет31.10: ручной Клиент/Inbox → один Appointment с отдельным
ответственным, source provenance, актуальными guards и общим состоянием карточки/
календаря/списка клиента реализован и локально проверен. Это частичный результат
новой R01-дельты. Первый Records workspace02.11 добавляет list/detail/pipeline,
замену merchant Lead/Deal входов и consumers, early completion, scoped задачи,
метрики и AI/automation defaults. [Исходный локальный evidence](../testing/evidence/records-workspace-20261102.md)
сохраняет границу своего снимка. Records и организационный VisitPlan/неназначенные
этапы/назначение слота затем проверены и опубликованы6349acdf:
[публикационный срез](../testing/evidence/records-publication-20261103.md),
[проверки плана](../testing/evidence/visit-plans-20261102.md). Это не deployment
и не приёмка последующего WIP. Деньги/полная D01/live открыты.

# Карта реализации и оставшихся границ

PILOT-ACCESS-20261031 adds isolated two-Business onboarding/access acceptance:
public signup, invited correct account, current role/tenant denial, revocation and
restoration preserving specialist/history, auth/MFA/session/reset and races.
Existing security fixes are integrated, not a new permission model. No live pilot
or production readiness claim. [Evidence](../testing/task-state/PRIMARY-SESSION.md#pilot-access-20261031--two-business-onboarding-and-access).

YCloud TP Lite, 29.10: локально реализованы подключение одного WhatsApp API-номера,
подписанный приём, текстовый обмен через существующий Inbox и статусы доставки.
Изолированные backend/PG/readiness и frontend build/browser результаты —
[паспорт интеграций](integrations.md#ycloud-tp-lite--локальный-первый-этап-29102026)
и YCLOUD-TPLITE-20261028 в PRIMARY-SESSION. Это не live-активация: доступ TP Lite,
целевой сервер, рабочие миграции и реальная доставка остаются открытыми R02/R03.

NOTIFICATIONS-PERSONAL-20261028, локальная проверка 29.10.2026: личная лента,
независимые отметки сотрудников, фиксированная аудитория объявлений, owner/admin-only
публикация/отзыв/поимённый мониторинг реализованы. Read-all не фиксирует ознакомление;
отзыв скрывает публикацию, сохраняя историю. Рабочий источник проверяется по текущим
правам; внешняя клиентская доставка остаётся отдельной. Backend304 в итоговой
совокупности (255 с четырьмя исправленными фикстурами +49 dependent), migration1,
PG concurrency3, system/drift, frontend types/i18n/build и targeted RU/KK/EN browser PASS.
Точное разбиение прогонов и ограничения — NOTIFICATIONS-PERSONAL-20261028 в PRIMARY.
HEAD98925b67 + WIP, без commit/push/working migration/deployment. Код/доказательства/
решения без остатка в принятом scope; окружение и публикация отдельно. OFFICIAL-21 /
AUD-17 сохраняет прежнее scoped evidence; shared-read правило заменено новым
согласованным персональным контрактом, исторические отчёты не переписаны.

FU-HIST-02, 28.10.2026: public form/widget success hides private contact matches
and CRM associations using constant compatibility fields. Internal matching and
staff evidence retained; preview reports new conversation only. Final106 isolated
tests PASS (12 new), system/drift/syntax/frontend checks and app+widget builds PASS;
independent review no findings. HEAD98925b67 + prior WIP + patch, local only.
Evidence/limits: FU-HIST-02-20261028 in PRIMARY-SESSION; no live/publication claim.

OFFICIAL-03, 28.10.2026: WhatsApp verified channel/Bot/Business binding is retained
through routing; all-change preflight, per-change status/log routing and Bot-scoped
message lookup close the local cross-tenant path. Final102 isolated tests PASS,
including20 new regressions; independent review no findings. Initial failures and
compatibility correction retained in OFFICIAL-03-20261028, PRIMARY-SESSION.
HEAD98925b67 + prior WIP + patch; no publication, live delivery or PG certification.

OFFICIAL-22, 28.10.2026: AI approval identity/payload/validity is immutable from creation;
reason-only generic edits preserve current decision/execution state. Legitimate exact-command
approval/replay and permission checks retained. Final17 new regressions and78 dependent tests
verified on unchanged source; initial expectation failure/correction visible in OFFICIAL-22,
PRIMARY-SESSION. HEAD98925b67 + prior WIP + patch; local scope closed, publication/live and
PostgreSQL concurrency certification remain separate. No new schema/provider behavior.

OFFICIAL-13, 28.10.2026: appointment automation status requires current Notification
VIEW/scope before counts and failed rows; Client/Appointment projections and calendar
URL copies obey independent read access. Final116 isolated tests PASS (21 new); evidence,
review repair and exact limitations in OFFICIAL-13-20261028, PRIMARY-SESSION. Local scope
closed at HEAD98925b67 + prior WIP + patch. No new delivery behavior, schema or module;
publication and production acceptance remain separate and unclaimed.

OFFICIAL-09, 28.10.2026: catalog Service import/manual writes require current SETTINGS
UPDATE and shared-object branch scope. Inactive/archive flags survive metadata updates;
atomic rollback and ordinary permitted/product-only paths verified locally. Evidence and
exact environment/commands: OFFICIAL-09-20261028 in PRIMARY-SESSION. HEAD98925b67 + prior
WIP + patch; no new schema, provider delivery or production/PG certification. Local scope
closed; publication not performed and target-environment acceptance remains separate.


OFFICIAL-19, 28.10.2026: existing outreach role eligibility is now intersected
with current NOTIFICATIONS action/object decisions at all12 role-helper callsites.
CRUD uses CREATE/UPDATE and server-owned candidate; campaign actions and consent bulk
use existing MANAGE map/actual campaign or consent candidate. Explicit overrides and
OWN/TEAM/current membership apply before writes/domain calls. No new role eligibility
or Client-derived consent owner. Capability helper reused; notifications currently has
no module mapping/toggle, only injected disabled-boundary integration proof claimed.
BEFORE22:14 failing methods/17 security assertions,8 controls PASS. AFTER27 new tests
within98 affected and combined1095 PASS/no skips; syntax/system/drift/diff/reverse PASS.
HEAD98925b67 + WIP/18 prior closed packets + patch. Evidence OFFICIAL-19-20261028 and
output/security-remediation-20261028/outreach-mutation-permissions/fix-report.md.
No real delivery or production/PG/full browser certification.

OFFICIAL-18, 28.10.2026: Lead follow-up Task creation now validates the
resolved assignee with ordinary validate_assignment(creating=True) and checks TASKS
CREATE on the final unsaved Task, not on the source Lead. Current source Lead VIEW,
Business/module and archive/lock checks remain; direct service calls also enforce actor.
Wrong source-based TASKS guards removed for this action only. No TASKS UPDATE required,
default/null/unassigned behavior retained where normal creation policy permits.
BEFORE20:8 security gaps,2 false denials,10 controls. AFTER28 new tests within113
affected and combined1068 PASS, zero skips; syntax/system/drift/diff/reverse PASS.
HEAD98925b67 + WIP/17 prior closed findings + patch. Evidence OFFICIAL-18-20261028
checkpoint and output/security-remediation-20261028/lead-task-assignment/fix-report.md.
Local assignment-boundary proof only; generic replay/production/PG not certified.
This is OFFICIAL-18, unrelated to already-closed historical AUD18 export.

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

OFFICIAL-15, 28.10.2026: no_change to production code. Current FU-BE-02
already passes actor into CRM-card Task previews and uses it for linked-field masking,
relations/actions; missing actor fails closed. Dedicated12 new regressions cover all
four card routes, forbidden/allowed fields, scalar/list/request/actor, OWN/TEAM/current
rights, Client aliases, parent task/specialist and Business/capability controls.
Current-tree initial11 PASS; final owning131 and combined1004 PASS, zero skips;
syntax/system/migration drift/diff PASS. HEAD98925b67 +15 prior fixes/WIP + tests/docs.
Evidence OFFICIAL-15-20261028 checkpoint and output/security-remediation-20261028/
task-preview-context/fix-report.md. Local scoped closure of an already-remediated
finding; no new functional patch, generic replay or production certification.

OFFICIAL-10 Inbox scope, 28.10.2026: create-action responses now require current
child VIEW/scope/capability and same Business before returning CRM data. Without VIEW,
writes still succeed but direct responses acknowledge read_restricted without record
fields; pipeline child fields are null, created flags unchanged. Task/Appointment keyed
replies reserialize current resource under current actor, never replay old DTO blindly.
Stored receipts, creation/dedup/locking/status unchanged; known metadata ID copies also
guarded. Pending booking without saved Appointment keeps its offered slot.
BEFORE17:15 security failures,2 controls. AFTER20 new tests within75 affected and
combined992 PASS, zero skips; syntax/system/drift/actual frontend consumers/
i18n/types/build PASS. HEAD98925b67 + WIP/fourteen prior fixes + patch. Evidence:
OFFICIAL-10-INBOX-20261028 checkpoint; output/security-remediation-20261028/
inbox-create-read-visibility/fix-report.md. Local scoped proof, not production PASS.

OFFICIAL-16, 28.10.2026: Lead duplicate-check details now pass existing LEADS
VIEW/object scope/capability and Business filtering BEFORE LIMIT5. Hidden rows return
no IDs/messages/status/source; optional restricted-match boolean preserves generic
duplicate warning without private count. Client projection reuses BE02/BE03: no hidden
Client FK or contact lookup/exclusion derived from an unreadable Client ID.
LeadForm preserves allowed counts/self-only editing and generic create-anyway warning,
clearing restricted state on error/no selection. No new endpoint permission or writes.
BEFORE10 security failures +5 controls after timestamp-fixture correction. AFTER15
new tests within86 affected and combined957 PASS, zero skips; syntax/system/
drift/component/i18n/types/build PASS. HEAD98925b67 + WIP/thirteen prior fixes + patch.
Evidence OFFICIAL-16-20261028 checkpoint and output/security-remediation-20261028/
lead-duplicate-visibility/fix-report.md. Local synthetic only; OFFICIAL10 remains open.

FU-BE-03, 28.10.2026: Client duplicate details now require current Client VIEW,
object scope, capability and same Business. CREATE-only keeps one non-identifying
warning for hidden matches; exclude_client_id cannot suppress an unreadable match.
Shared read projection covers Client check/Inbox warning and stored import snapshots,
plus the same DTO copies in form submissions/activity. Current reader used on every
read; stored evidence, matching/import writes and public warning semantics unchanged.
UI keeps duplicate banner/confirmation/create-anyway, no hidden open/merge target.
BEFORE18 security assertions across11 methods +2 reproduced snapshot copies; five
baseline controls PASS after fixture corrections. AFTER20 new tests within136 affected
and combined942 PASS, zero skips. Syntax/system/drift/component/i18n/types/build
PASS. HEAD98925b67 + WIP/twelve prior fixes + patch. FU-BE-03-20261028 checkpoint;
output/security-remediation-20261028/client-duplicate-visibility/fix-report.md.
Local synthetic evidence only. OFFICIAL16/10 remain separate and unclosed.

FU-BE-02, 28.10.2026: linked Client projections now apply existing CLIENTS VIEW,
object scope, capability and same-Business policy. Readable parent records remain;
hidden Client IDs/contact labels and typed copies are masked in serializers, CRM-card,
history, queues, AI context/rules, outreach previews/evidence and CSV. Contact-search and exact Client-ID filter
branches respect Client visibility; stored Lead/Deal export fingerprints include it.
Actor context is explicit; no actor fails closed. Frontend accepts nullable links,
retains generic placeholders and avoids null-equality joins. No new ownership rule.
BEFORE22:61 failing assertions across18 methods,4 controls PASS after fixture correction.
Focused25 PASS; final27 plus affected history/card suites 105 PASS; combined
894 PASS without skips. Syntax/system/drift/component/i18n/types/build PASS.
HEAD98925b67 + prior WIP/eleven fixes + this patch. Evidence FU-BE-02-20261028 in
PRIMARY and output/security-remediation-20261028/client-pii-projections/fix-report.md.
Local synthetic evidence only; no production/provider/browser-E2E certification.

OFFICIAL-05, 28.10.2026: unverified public form/chat flags no longer replace
existing per-channel OPTED_OUT. Common record_explicit_consent creates absent rows
and conditionally updates only non-OUT rows at SQL write, then refreshes existing
result. Refusal evidence/timestamps retained; normal intake/new/UNKNOWN/IN unchanged.
Existing inbound START and authorized management re-consent remain separate and PASS.
BEFORE15 security failing assertions across7 methods; corrected existing404 denial
control PASS before source patch. AFTER106/combined654 PASS without skips;
syntax/system/drift PASS. HEAD98925b67 + WIP/ten prior fixes + patch. Evidence:
OFFICIAL-05-20261028 in PRIMARY; output/security-remediation-20261028/
public-intake-optout/fix-report.md. Only local synthetic consents, no actual sends.

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

OFFICIAL-12, 28.10.2026: alternate Deal readers now share existing sensitive
amount policy (owner/admin/manager/accountant or BILLING VIEW as already defined).
CSV/queues/summary/typed activity metadata/CRM timeline/AI rule sources/Deal-value
analytics mask denied monetary fields and derivatives; actor context explicit.
Amount filters/order denied before use; stored Deal export fingerprint includes
field access. Missing context fails closed. Nullable frontend types and two money
helpers show existing '-' for hidden values, preserving ordinary numeric formatting.
BEFORE30 failing assertions across15 methods,3 controls PASS (see fixture correction
in checkpoint); AFTER18+3 supplemental controls,19 unique methods PASS; combined
523 PASS without skips. Syntax/system/drift, i18n/types/main Vite build PASS.
HEAD98925b67 + WIP/eight prior fixes + patch. OFFICIAL-12-20261028 in PRIMARY-SESSION;
output/security-remediation-20261028/deal-amount-projections/fix-report.md.
Local synthetic evidence only; no provider/production/publication certification.

OFFICIAL-02, 28.10.2026: legacy analytics intersects source Lead/Deal/
Appointment/Task VIEW, object scope and capability before counts/grouping/sums.
Reuses existing analytics _scoped in manager metrics, dashboard and legacy summary/
CSV. Member boundary and permitted formulas retained; Lead-to-Deal conversion also
requires a readable Lead without changing the historical reporting-period formula.
BEFORE15:13 failing assertions across10 methods,5 controls PASS; AFTER38/combined
375 PASS without skips, syntax/system/migration-drift PASS. HEAD98925b67 + WIP/
seven prior fixes + patch. OFFICIAL-02-20261028 in PRIMARY-SESSION; evidence in
output/security-remediation-20261028/analytics-resource-visibility/fix-report.md.
Scoped local synthetic evidence only; no production acceptance or publication.

OFFICIAL-07, 28.10.2026: ensure_default_roles now initializes absent presets
only; onboarding never overwrites existing role metadata, activation, JSON, denies,
scope or permission rows. Initialization of a new role is atomic. Explicit audited
TEAM MANAGE permission editing remains separate; no reset API/permission added.
Corrected BEFORE12:11 failing assertions across10 methods,2 controls PASS;
AFTER23/combined316 PASS without skips, syntax/system/migration-drift PASS.
HEAD98925b67 + preserved WIP/six prior fixes + patch. OFFICIAL-07-20261028 in
PRIMARY-SESSION; output/security-remediation-20261028/onboarding-preset-preservation/
fix-report.md. Local isolated synthetic evidence only; no publication/live acceptance.

OFFICIAL-04, 28.10.2026: Notes reads now intersect inherited tenant/Clients
access with the linked record's current VIEW/object scope using existing
scope_entity_history before pagination and serialization. Hidden recognized links
return404 for detail and inherited object actions; ordinary CRUD, archived/unlinked
history and existing non-CRM/system policy remain. BEFORE13:21 failing assertions,
4 controls PASS; inherited archive baseline1 failed. AFTER23/combined270 PASS without
skips; system/migration-drift and syntax/diff PASS. HEAD98925b67 + preserved WIP/five
prior fixes + this patch. Evidence: OFFICIAL-04-20261028 in PRIMARY-SESSION;
output/security-remediation-20261028/notes-linked-object-access/fix-report.md.
Local synthetic SQLite only, no production/live acceptance or publication.

28.10, OFFICIAL-06: outreach использует bounded named-variable render, сохраняет
plain/Unicode/escaped braces и проверяет stored personalized text без повторного
parse. Ordered13/совместно184 без skip, system/drift PASS на 98925b67 + WIP/patch.
Лимиты и совместимость — [operations](../current/operations.md), версия/команды —
OFFICIAL-06-20261028 в [checkpoint](../testing/task-state/PRIMARY-SESSION.md).
Реальных отправок/миграции legacy-данных и production acceptance нет.

28.10, OFFICIAL-08: competitor offer PATCH проверяет effective Business/rule;
recommendation/autopilot observation gate исключают чужие legacy offers. Валидные
create/PUT/PATCH/relink сохранены; focused13/совместно171 без skip и system/drift
PASS на 98925b67 + WIP/patch. Версия/команды — OFFICIAL-08-20261028 в
[checkpoint](../testing/task-state/PRIMARY-SESSION.md). Рабочие данные/провайдеры,
DB constraint и production acceptance не входили в этот scope.

28.10, OFFICIAL-20: readiness/rollout detail использует configured-state flags вместо
raw broker/origin/provider URLs; существующие keys/status/action сохранены. Focused9,
совместно135 без skip, system/drift PASS на 98925b67 + WIP/patch. Это локальный
redaction fix без inspection реальной среды и без production PASS; версия/команды —
OFFICIAL-20-20261028 в [checkpoint](../testing/task-state/PRIMARY-SESSION.md).

28.10, FU-BE-01: invitation token и invite_path доступны только по текущему
TEAM MANAGE конкретного Business, иначе пустые строки. Metadata VIEW и легитимный
share/create/accept/reissue сохранены. Focused11 и совместно174 PASS + 3 PG-only skip,
system/drift PASS на 98925b67 + WIP/patch; публикации нет. Версия/ограничения —
FU-BE-01-20261028 в [checkpoint](../testing/task-state/PRIMARY-SESSION.md).
Старые уже полученные bearer не отозваны; общего security/production PASS нет.

28.10, OFFICIAL-01: generic API не удаляет Business (DELETE 405 для всех actors).
Create/read/update и их audit/tenant guards сохранены. Focused8/affected163 PASS + 3 PG-only skip,
system/drift PASS на локальном 98925b67 + WIP/patch; публикация не выполнялась.
Версия, команды и ограничения — OFFICIAL-01-20261028 в
[checkpoint](../testing/task-state/PRIMARY-SESSION.md). Это узкий fix, не новая
общая сертификация и не реализация lifecycle удаления бизнеса.

23.10: общая UI-политика фокуса разделяет pointer и keyboard, включая auth,
CRM primitives, диалоги и виджет. Scoped browser/build PASS; это не полная
сертификация всех экранов или live deployment. Контракт —
[frontend](../current/frontend.md), evidence — UI-FOCUS-20261023 в
[checkpoint](../testing/task-state/PRIMARY-SESSION.md).

Дельта аудита 17.10 на `56dd124`: прежние scoped PASS не закрывают обнаруженные
обходы generic CRUD/изоляции, offline storage, автоматизации и неполные UI-сценарии.
[Результаты по областям](../testing/project-audit-20261017.md) и
[единственная очередь исправлений AUD](../current/roadmap.md#project-audit-20261017).
AUD-01 реализует изоляцию/очистку offline-данных заявок; AUD-02 — связи/авторство
notes/activity, назначение в формах и серверные журналы отправок. AUD-03 закрывает
выдачу Client.notes через API/карточки/сегменты/CSV по существующей field policy.
Версии и проверки — checkpoint AUD-01-20261017, AUD-02-20261017 и AUD-03-20261017.
AUD-13 закрывает обход UPDATE исходного объекта через PATCH/PUT и проводит
переназначение заявки через сервис; версия и проверки — checkpoint AUD-13-20261017.
AUD-14 защищает неизменяемую историю сообщений, parent scope и server-only delivery
metadata; send/retry сохраняют существующий путь. Версия/проверки — AUD-14 checkpoint.
AUD-15 проверяет связи конфигурации стадий/переходов и сохраняет pipeline существующей
стадии; версия и проверки — checkpoint AUD-15-20261019.
AUD-06 объединяет проверку конфигурации действий в preview/save/activate/execute;
предметная форма и ошибки RU/KK/EN проверены; версия/проверки — AUD-06 checkpoint.
AUD-04 обеспечивает атомарное создание/замену состава и audit/activity, защищает
активный состав при generic CRUD и конкурентных записях. Версия/проверки —
AUD-04-20261019 checkpoint. AUD-05 выполнен полностью в согласованном локальном
scope: редактор существующего правила, preview с UPDATE, атомарное сохранение
и сценарий до реальной Task; версия/проверки — AUD-05-20261019 checkpoint.
AUD-01/02/03/13/14/15/06/04 также выполнены полностью в своих локальных scope.
AUD-16 выполнен полностью в локальном scope: служебные поля ImportJob защищены,
preview/confirm используют row lock, повторную проверку прав, файла и строк.
Проверки112 SQLite +17 PG, system/migration drift; команды и границы — AUD-16 checkpoint.
AUD-20 выполнен полностью в локальном scope: доменное начальное состояние
API/import заявок и сделок, причины потери, серверные metadata, атомарная история
и фильтр активных открытых стадий UI/import/Inbox. Версия/проверки — AUD-20 checkpoint.
На историческом срезе21.10 AUD-10 был частичным; позднее30.10 его локальный
scope закрыт и опубликован8d710f03. Актуальные закрытия AUD-07/08/09/11/12/17/19
и ограниченного AUD-V01 находятся в [roadmap](../current/roadmap.md#project-audit-20261017).
Они не являются полной production-сертификацией. AUD-21: полный локальный критерий concurrent rollback/recovery
проверен в PostgreSQL17, 48 import-проверок PASS без skip; код AUD-16 сохранён.
Версия/evidence — AUD-21-20261021 checkpoint. AUD-22 также выполнен полностью
локально: ZIP/XML bounds, потоковый XLSX reader и cleanup; focused10/affected68,
bounded subprocess и system/drift PASS. Лимиты всех листов и env — operations,
версия/evidence — AUD-22-20261021 checkpoint. Публикация и CI — отдельные
состояния; deployment/live приёмка не заявлены локальным PASS.
Этот исторический перечень не заменяет актуальные строки roadmap;
локальные закрытия не являются общей сертификацией проекта.

Общая карта сверена 16.10.2026 на исходниках `dc1eedf`.
[Покрытие сверки и исправления статусов](../testing/docs-reconciliation-20261016.md).
Сверка статическая: маршруты, сервисы, UI и существующие test/evidence paths.
Новые runtime-тесты в документационной задаче не запускались. «Есть в коде»
не значит полная сертификация, deployment или допуск реальных клиентов.

Backend routes: [config/urls.py](../../config/urls.py).
Reachable UI: [router.tsx](../../frontend/src/app/router.tsx).
API слой: [frontend/src/api](../../frontend/src/api).
Это общая карта, не замена подробным паспортам и не новый backlog.
Предметные описания всех направлений — [реестр паспортов](README.md), порядок
оставшихся результатов и mapping acceptance — [единый roadmap](../current/roadmap.md).
Settings завершён: [реестр UI/API/потребителей](../testing/settings-functional-20261008.md).
Дополнение 08.10: [операционный UI-пакет](../testing/ui-operations-20261008.md)
обновляет шесть экранов и scoped work queues; это отдельная локальная проверка,
не общая сертификация или новая разработка CRM-аналитика.

| Область | Что присутствует в реализации | Источник / граница оставшейся работы |
| --- | --- | --- |
| Доступ сотрудников, ADMIN-04 | Scoped диагностика аккаунта/membership/роли/приглашений и зависимостей; отключение/восстановление, роль, отзыв/перевыпуск; обе platform-роли + MFA/обращение, личное согласие владельца для выдачи доступа, атомарный аудит и идемпотентность | [Сервис](../../apps/businesses/employee_access.py), [панель](../../frontend/src/features/platform/BusinessEmployeeAccessPanel.tsx), Account confirmations; локальные PostgreSQL/concurrency/browser/build PASS — checkpoint. Рабочая businesses0013 отдельно; глобальный unlock исключён, автоматической отправки нет, история ограничена50 последними запросами |
| Восстановление аккаунта, ADMIN-03 | Диагностика смены почты/MFA; обе platform-роли со свежим MFA и обращением, ручная проверка личности, подтверждение владельца для сотрудника, одноразовая новая почта/пароль, атомарный отзыв старых credentials; интерфейс оператора, владельца и получателя | [service](../../apps/accounts/recovery.py), [UI](../../frontend/src/features/platform/BusinessRecoveryPanel.tsx); опубликован dc1eedf, scoped PostgreSQL/concurrency/browser PASS — checkpoint; CI на момент сверки выполняется. Рабочая accounts0011, адрес поддержки/FRONTEND_URL и реальная SMTP-доставка отдельно. Это не автоматическая проверка достоверности документов и не передача Business |
| Административные реквизиты, ADMIN-01 | Отдельные GET/PATCH и вкладка карточки: allowlist, обе platform-роли, MFA, обращение/причина, revision, атомарный аудит и история | [сервис](../../apps/core/platform_details.py), [форма](../../frontend/src/features/platform/BusinessDetailsForm.tsx), [тесты](../../apps/core/tests_platform_details.py); опубликован f7d74d5, scoped PASS и CI success; не owner/recovery/billing и не deployment |
| Передача владельца, ADMIN-02 | Заявка с двумя личными подтверждениями, роль сотрудника или отключение доступа прежнему владельцу; platform_admin + MFA, атомарный аудит и отзыв сессий | [сервис](../../apps/businesses/ownership.py), [интерфейс](../../frontend/src/features/platform/BusinessOwnershipPanel.tsx), [тесты](../../apps/businesses/tests_ownership.py); опубликован cafcea5, локальная API/UI приёмка и CI PASS. Recovery без прежнего владельца и рабочая миграция не входят в эту границу |
| Platform console, PLATFORM-REBUILD-01 | Обзор/клиники/карточка: настройки, записанные ошибки и свежесть фоновых наблюдений разделены; MRR/подписки сохранены; status filter и no-data/403; прежние grant/MFA и журнал | [selectors](../../apps/core/platform_selectors.py), [UI](../../frontend/src/features/platform), [spec](../testing/platform-rebuild-spec-20261014.md); проверки в checkpoint; ручное создание клиники не реализовано; обращения — отдельная строка ниже |
| Филиалы, MB1–MB5 | Branch access, услуги/цены, несколько интервалов/переезды/отсутствие, календарь и AI booking | [Домен](../../apps/branches), [паспорт записи](scheduling.md); b48a822, scoped PASS, рабочая локальная активация 12.10 после backup; live отдельно |
| Операционная Главная | Полные distinct-счётчики, очередь действий, ближайшие записи, честное отсутствие финансовых данных | [work queues](../../apps/core/work_queues.py), [UI](../../frontend/src/features/dashboard/OperationalDashboard.tsx); локальная приёмка пакета 08.10, target/полный рабочий день отдельно |
| Обзор оператора, PLATFORM-OVERVIEW | Полные счётчики свежих сбоев/непроверенных клиник и активной поддержки с точными переходами; ограниченные очереди, компоненты/эпизоды, связанные обращения, ответственные; финансы сохранены | [read model](../../apps/core/platform_overview.py), [UI](../../frontend/src/features/platform/OverviewAttention.tsx); scoped проверки в checkpoint; подробный CRM read-path — отдельная строка ниже |
| Карточка клиники, PLATFORM-CLINIC-CRM | Пять разделов, постоянный подробный просмотр CRM/переписки/платежей, связанные записи и дочерние списки, scoped поддержка и аудит чтения | [read API](../../apps/core/platform_crm_views.py), [UI](../../frontend/src/features/platform/ClinicCrmBrowser.tsx); GET-only, без экспорта/impersonation/provider secrets; scoped проверки и публикация — checkpoint, live activation отдельно |
| Операции платформы, PLATFORM-OPERATIONS | Текущие фоновые эпизоды, подключения, история ошибок automation/integration/webhook и инфраструктура отдельно; фильтры клиники/компонента/свежести/UTC периода, полные counts, пагинация и обратный контекст | [read API](../../apps/core/platform_worklists.py), [UI](../../frontend/src/features/platform/PlatformOperationsPage.tsx); scoped проверки в checkpoint; журнал всех прошлых эпизодов и новые наблюдения не добавлены |
| Клиенты | Карточки, поиск/связи, история, archive/restore, проверка активных зависимостей | [clients](../../apps/clients), [services](../../apps/clients/services.py); общие edge cases и приёмка FC остаются |
| Заявки | Lifecycle, ответственный, конверсия/связи, lost reason | [leads](../../apps/leads/services.py), [tests](../../apps/leads/tests_crm_light.py); не обходить services |
| Сделки/воронки | Стадии, terminal actions, связи и история | [crm](../../apps/crm/services.py); новые stage-policy сценарии D-08 требуют правила |
| Календарь/специалисты | Resource без обязательного аккаунта, график/исключения, проверки slot/overlap, изменение записи | [scheduling](../../apps/scheduling/services.py), [availability](../../apps/scheduling/availability.py); кресла/оборудование отложены |
| Задачи/напоминания | Lifecycle, роли, назначение, due processing | [tasks](../../apps/tasks/services.py); target workers и follow-up policy отдельно |
| Inbox | Диалоги/сообщения/связи, ручная работа и human handoff; компактный scoped-инспектор клиента/будущих записей/CRM, точные переходы, мобильная панель и сохранение черновика | [conversations](../../apps/conversations), [проверки инспектора](../testing/task-state/PRIMARY-SESSION.md#inbox-inspector-20261008--approved-customer-context-and-action-placement); внешняя доставка не доказана наличием UI |
| Клиентский AI | Настройки/знания/память, публичные источники, контролируемое создание, safety budget, handoff/recovery | [Подробный паспорт](customer-ai-agent.md); 43 real-model сценария08.10 PASS (включая прежние28); реальный канал ещё не принят |
| CRM AI / аналитик | Существующие настройки, инструменты, подтверждённые команды и аналитические запросы; диагностика конфигурации, отключённой аналитики и recovery статуса операций | [ai_core](../../apps/ai_core), [D01 и остаток](crm-ai-agent.md), [срез готовности11.11](../testing/evidence/ai-agents-fixes-20261111.md); ограниченный помощник обязателен в пилоте, расширенная аналитика отложена; полный text/voice PASS не получен |
| Автоматизации | Conditions, 6 действий, WAIT/retry, leases/idempotency/cancel; редактор существующего состава, preview с UPDATE, атомарное сохранение | [engine](../../apps/automations/engine.py); реальная очередь/target recovery отдельно |
| Поддержка, PLATFORM-SUPPORT-20261015 | Клиника создаёт обращения; платформа назначает, отвечает, решает; явное повторное открытие, приватные заметки, read cursor, поиск/пагинация и черновики; employee — свои, owner/admin — все своей клиники | [domain/API](../../apps/support), [UI](../../frontend/src/features/support); scoped evidence в checkpoint. Миграция support0001 применена в локальной рабочей БД после backup/restore и проверки сохранности; вложений, внешних уведомлений, SLA и AI нет |
| Команда/безопасность | Business membership/roles, scoped APIs, сессии/MFA, support grant | [accounts](../../apps/accounts), [core](../../apps/core); target privileged MFA/операционные проверки обязательны |
| Связь эпизода и поддержки, PLATFORM-INCIDENT-LINK | Явное связывание существующего/нового обращения с component/episode той же клиники; неизменяемый снимок, текущая свежесть, обратные переходы, platform-only API | [domain](../../apps/support/incidents.py), [UI](../../frontend/src/features/support/SupportIncidentPage.tsx); изолированные проверки в checkpoint; support0002 применена29.10 к локальной рабочей БД по отдельному поручению после backup; [операционная запись](../current/operations.md); target-активация отдельно; полного журнала всех эпизодов и автосоздания обращений нет |
| Импорт/дубли/архив | CSV/XLSX flow, preview/validation, domain links и работа с архивом | [imports](../../apps/core/import_export.py), [clients](../../apps/clients); не общий импорт произвольных моделей |
| Ручные деньги | Поступления/возвраты, неизменяемый журнал, replay/locks/overrefund защита | [payments](../../apps/payments/services.py), [tests](../../apps/payments/tests.py); не gateway пациента и не ERP |
| Детализация и сравнение аналитики | Списки записей из KPI/статусов/источников/услуг/команды, предыдущий равный период, guarded Decimal разница финансов; прежние права и архив | [read endpoint](../../apps/analytics/workspace_records.py), [comparison](../../apps/analytics/workspace_comparison.py), [локальная проверка](../testing/evidence/analytics-detail-compare-20261111.md); текущие очереди/CSV без сравнения, не полная R01/production-приёмка |
| Финансовая аналитика | Явный manual или один external источник, period/freshness/no-data контракт | [financial_metrics](../../apps/analytics/financial_metrics.py); [external registry](../../apps/integrations/providers/registry.py) пуст, прибыль/долг не утверждены |
| Файлы/AV | Private access, quarantine/scan, leases/recovery, нормализация avatar | [core](../../apps/core), [operations](../current/operations.md); локальный AV работает, облачная приёмка/retention открыты |
| Экспорт | Sync CSV, async ExportJob, current permissions в worker, fingerprint доступа при private download (AUD-18) | [exports](../../apps/core/export_jobs.py); reports_exports/beat нужны в target |
| Состояние сервиса (S03) | Просроченная фоновая работа, начало/восстановление/устаревание инцидента; персональные уведомления owner/admin с защитой от дублей и проверка связи с API. По решению03.11 глобальная полоса и индикатор шапки удалены: временные уведомления используют общий host, постоянная причина остаётся в затронутом отчёте; [текущий UI](../current/frontend.md) | [service status](../../apps/core/service_status.py), [evidence](../testing/task-state/PRIMARY-SESSION.md#crm-s03-20261014--service-state-and-incident-notifications); isolated checks, рабочая миграция/worker/beat и независимый внешний мониторинг отдельно |
| Локальное восстановление (S04) | Реальные PostgreSQL/Redis/Celery/ClamAV в одноразовом стенде; restart/crash/retry/cancel без дублей, восстановление очереди из БД, pg_dump/restore и приватные файлы/тестовый ключ | [runner](../../scripts/verify_recovery_s04.py), [evidence](../testing/task-state/PRIMARY-SESSION.md#crm-s04-20261014--isolated-operations-and-recovery); Windows solo и локальное хранилище, целевая production-среда отдельно |
| Интеграции | Connector/provider services, credential store, webhook/pull/status/recovery foundation | [integrations](../../apps/integrations), [bots](../../apps/bots); Telegram/WhatsApp в подготовке R02, прочие подключения отложены; provider-specific live допуск не заявлен; остаток UI — [паспорт](integrations.md) |
| Billing | Код entitlements/subscription и интерфейсы существуют | [billing](../../apps/billing); коммерческий пакет/цены/процессинг не завершены, развитие отложено |
| Интерфейс | Рабочие маршруты, общие компоненты, RU/KK/EN, neutral/emerald tokens, состояния восстановления | [frontend](../../frontend/src); полная FC/manual/reader приёмка остаётся |
| Эксплуатация | Настройки/скрипты health, workers, monitoring, backup/restore foundation | [scripts](../../scripts), [settings](../../config/settings.py); нет утверждения о развёрнутом paid production |

## Что делать дальше при новом поручении

Сначала выбрать один требуемый результат и [непройденную границу](../current/acceptance.md).
Для актуального Inbox AI [локальный пилот 08.10](../testing/inbox-local-pilot-20261008.md)
прошёл, включая handoff и настройки; следующая отдельная граница — согласованный channel/target flow. Бюджет,
получатели, deployment и следующий этап здесь не утверждаются.
Для остальной CRM использовать существующие слои и проверять конкретный
regression/недостающий критерий; не реализовывать модуль заново по старому плану.

Разделение готовности, Git/CI и среды — [состояние проекта](project-state.md).
Действующие требования — [реестр документов](../README.md).
