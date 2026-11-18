## Смена пароля и системная роль — 12.11.2026

Change-password возвращает `{ok, access}` нового device session; refresh остаётся
HttpOnly cookie, старые access/refresh отзываются. UI принимает replacement access
того же пользователя внутри очереди cookie operations; обычный refresh по-прежнему
отклоняет неожиданный device-session/account switch. TTL и права не расширены.
CurrentUser.memberships добавляет `business_role_system_key` только для неизменённого
системного preset; авторское имя роли сохраняется. [Проверки F08/F10](../testing/evidence/crm-global-fixes-20261112.md).

## Доступ к физическим ресурсам — 09.11.2026

Требования помещения/оборудования к услуге меняются через существующее
settings.update и доступ к активному филиалу. Связанные услуга и ресурс обязаны
принадлежать тому же Business, ресурс — выбранному филиалу. Настройка аудируется;
сбой аудита откатывает изменение. Создание/изменение физического ресурса сохраняет
обычные права Resources и дополнительно проверяет доступ к исходному и целевому
филиалу. Staff продолжает использовать SpecialistBranch; Resource.branch для
него запрещён. Новый permission framework не вводится.
[Контракт](crm.md#помещения-и-оборудование-филиала--решение09112026) ·
[Проверки](../testing/evidence/branch-workspace-20261109.md).

## Доступ к автоматической основной точке — 06.11.2026

Активный участник Business без BranchAccess имеет доступ к автоматической
основной точке в пределах существующих ролевых/object/field permissions.
Явный BranchAccess, включая пустой список, всегда имеет приоритет.
При создании второй точки отсутствующий grant материализуется только на первую;
all_branches и существующие явные ограничения сохраняются. Создание новой точки
по-прежнему требует SETTINGS UPDATE и network grant/owner. Архивирование
перепроверяет право и оставшуюся активную точку на сервере под Business lock.
[Проверки и границы](../testing/evidence/single-location-20261106.md).

## C09 — настройка ответственного AI-записи

GET businesses/{id}/booking-responsible-options/ и PATCH ai_booking_responsible_user
требуют существующего SETTINGS UPDATE. Кандидаты — активные доступные участники
того же Business/owner. Назначение не предоставляет права; при записи отдельно
проверяются authorizing actor, scope CREATE, текущий ответственный и его филиал.
Политика ролей не менялась. [C09 evidence](../testing/evidence/remediation-c09-20261104.md).

C02 / TEAM-ANALYTICS, 04.11.2026: `/api/team/performance/` intersects Lead
selection with current LEADS VIEW scope and enabled capability before counts,
loss reasons, rates and team summaries. Existing report membership and source/date
filters remain; denied/disabled Leads yield zero/empty fields. Other independently
readable source metrics are unchanged and not certified by this Lead-only fix.
Local evidence: [C02](../testing/evidence/remediation-c02-20261104.md).

# Доступ, приватность и границы аккаунта

PILOT-ACCESS-20261031: integrated access candidate preserves existing role grants
on repeated initialization, masks invitation token/invite_path without current
TEAM MANAGE, rejects generic Business DELETE, and removes private matching/CRM IDs
from anonymous form/widget receipts. Signup defaults to neutral other. Existing
auth/MFA/session/reset and employee services remain; disabling Business membership
does not disable specialist/history or another Business membership. Two-business
and PostgreSQL race evidence: [checkpoint](../testing/task-state/PRIMARY-SESSION.md#pilot-access-20261031--two-business-onboarding-and-access).
This is isolated acceptance, not live admission.

AUD-V01,31.10: anonymous cookie-auth защищён Django csrf_protect внутри DRF
dispatch. GET /api/auth/csrf/ возвращает masked csrf_token, устанавливает CSRF cookie
и запрещает кэширование. POST token, refresh, logout, social, signup/owner,
mfa/enrollment/confirm, mfa/verify и password-reset/confirm требуют эту cookie и
X-CSRFToken; Origin/HTTPS Referer проверяет Django. Нет обхода для form-urlencoded.
Bearer-only операции сохраняют прежнюю авторизацию. Существующие direct API clients
должны выполнить bootstrap тем же cookie jar. CORS не заменяет CSRF-проверку.
[Evidence AUD-REMAINING](../testing/task-state/PRIMARY-SESSION.md#aud-remaining-20261031--aud-12c-and-aud-v01).


AUD-19: TenantModelViewSet и IsTenantMember используют объявленный `business_lookup`
для определения Business дочерней сущности, включая `form__business`. Проверки
текущего объекта, кандидата записи, удаления и tenant истории согласованы.
Для LeadFormField действуют существующие LEADS action/scope; VIEW не даёт write.
Подмена формы другим Business запрещена даже при доступе к обоим. Новых grants нет.
Проверки отдельного кандидата и публикация — [AUD-19 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-19-20261029--lead-form-field-tenant-resolution-and-editor-verified).

Персональные уведомления — решение владельца 28.10.2026, реализация
NOTIFICATIONS-PERSONAL-20261028. Активный участник видит только собственную
фиксированную аудиторию внутренней ленты текущего Business. Для рабочих уведомлений
дополнительно проверяются текущие права и capability связанного объекта до пагинации
и счётчиков. Исторический текст рабочего события не раскрывает закрытые поля;
лента показывает локализованный тип и безопасную ссылку на доступный источник.
Для серверных service-status событий разрешён только ключ из фиксированного набора
компонентов и переходов started/recovered, с проверкой Business и номера эпизода.
Это не разрешает отдавать сохранённый текст/технический reference или обходить
recipient/access-фильтр. [Проверка](../testing/evidence/records-bell-fix-20261103.md).
Объявления доступны всем зафиксированным действующим участникам независимо от
NOTIFICATIONS VIEW и настроек категорий. Личное open/read/unread/acknowledge
не требует UPDATE/MANAGE и никогда не меняет состояния другого пользователя.
Detail и индивидуальные mark-read/mark-unread используют ту же персональную
границу, что список и счётчики; общий NOTIFICATIONS VIEW не закрывает доступ
к объявлению или рабочему событию с доступным источником.

Публикация, отзыв и поимённый мониторинг объявлений разрешены только фактическому
владельцу Business или активному администратору с текущим NOTIFICATIONS MANAGE.
Одного MANAGE у маркетолога недостаточно. Общая запись неизменяема; API не принимает
подмену автора, получателя или времени. Generic create/update/delete внутренних
уведомлений запрещены. cancel/mark-sent/retry также запрещены для всего канала
SYSTEM, включая рабочие события; отзыв объявления остаётся отдельным действием
с аудитом. Клиентская внешняя доставка сохраняет прежние проверки VIEW/MANAGE.
Ручной retry атомарно захватывает конкретную версию failed и пишет audit;
пересекающийся запрос не может повторить уже начатую или завершённую попытку.

«Прочитать всё» атомарно обновляет доступную личную ленту выбранного Business
на начало операции, независимо от фильтров показа; новые поступления, opened_at
и acknowledged_at не затрагиваются. OFFICIAL-21 / AUD-17 остаётся закрытым
исправлением прежнего общего состояния; новый согласованный персональный контракт
заменяет его VIEW+UPDATE-правило только для внутреннего личного прочтения.
Доказательства и границы: NOTIFICATIONS-PERSONAL-20261028 в PRIMARY-SESSION.

FU-HIST-02: anonymous form/widget input is not authority to read private Client
membership or CRM links. Public form duplicate_warning remains false solely for
response compatibility; it does not describe internal matching. Website chat returns
client_id/lead_id as null in every creation mode, retaining its fresh conversation
capability and message/status receipt. Stored duplicate evidence and authenticated
staff-read authorization are unchanged. Local evidence: FU-HIST-02-20261028 in PRIMARY.

Статус: **действующий контракт**. Срез 07.10.2026, `f01d226`.
Сохраняет принятые ограничения; не вводит роли, grants или новую permission-модель.

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

CREATE does not grant child record VIEW in an Inbox response. Current independent
record read policy applies to fresh/reused/replayed child DTOs and typed ID copies.
Safe write acknowledgement is not a new permission or read grant. Parent text/workflow
state remains parent-authorized data; no general free-text DLP policy introduced.

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

Lead duplicate-check is not authority to read a hidden Lead. Existing Business-member
endpoint access is preserved (no new CREATE/VIEW workflow gate invented); personal
details independently require canonical LEADS read scope. A restricted-match boolean
keeps the existing generic warning, not an exact hidden count. Client details follow
their independent Client policy even when related Lead details are readable.

FU-BE-03, 28.10.2026: Client duplicate details now require current Client VIEW,
object scope, capability and same Business. CREATE-only keeps one non-identifying
warning for hidden matches; exclude_client_id cannot suppress an unreadable match.
Shared read projection covers Client check/Inbox warning and stored import snapshots,
plus the same DTO copies in form submissions/activity. Current reader used on every
read; stored evidence, matching and public warning semantics unchanged. Import
writes additionally follow OFFICIAL-17 current per-row CREATE/UPDATE and notes policy.
UI keeps duplicate banner/confirmation/create-anyway, no hidden open/merge target.
BEFORE18 security assertions across11 methods +2 reproduced snapshot copies; five
baseline controls PASS after fixture corrections. AFTER20 new tests within136 affected
and combined942 PASS, zero skips. Syntax/system/drift/component/i18n/types/build
PASS. HEAD98925b67 + WIP/twelve prior fixes + patch. FU-BE-03-20261028 checkpoint;
output/security-remediation-20261028/client-duplicate-visibility/fix-report.md.
Local synthetic evidence only. OFFICIAL16/10 remain separate and unclosed.

Duplicate detection for a CREATE workflow does not authorize reading an existing
Client's other contacts/name/ID. Preserve its existing generic warning while projecting
only currently readable Client details. Client OWN/TEAM remains canonical, with no
implicit ownership via a Lead. Exclusion IDs are effective only for readable Client
records. This does not impose new create/merge rights or redesign anti-enumeration.

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

A readable Lead/Deal/Appointment/Task does not grant independent Client access.
Current Client policy governs linked IDs/PII and typed projections even for readable
parents. Existing Client OWN/TEAM semantics are reused (no implicit ownership via a
Lead); capabilities and same Business apply. Parent-authored text remains governed
by its parent; this is not free-text DLP or a new permission framework.

## Применение прав к новому пилоту — требование 29.10.2026

Две независимые клиники — разные Business, пять филиалов MB01 не заменяют
multi-tenant приёмку. Единая Запись/план сохраняют server tenant/object/field/branch
и child-read guards; скрытие Lead/Deal из UI не отключает их API capabilities.
Ответственный и Специалист различаются; назначение/наследование/override не выдают
доступ. Выбранный manual/AI assignee — допустимый активный участник, проверяемый
в момент действия. Старые nullable/hidden зависимости имеют безопасный путь без
раскрытия данных; replay использует текущую projection, не старый широкий DTO.
Опциональная Market-связь требует проверки tenants/полномочий и повторного
скачивания/revoke; БИН/email и импортный event не право на подпись/refund.
Новая permission-модель не введена. [Принятые границы и открытые проверки](roadmap.md#трассировка-всех-crm-c-требований).

## Business и серверные права

OFFICIAL-22: generic ApprovalRequest UPDATE/MANAGE does not authorize replacing
the command, payload/fingerprint, source evidence or validity window. These fields
are immutable from creation in all states; a new action requires a new approval.
Existing reason-only edits and decision endpoints retain their current permissions.
Reason/no-op saves do not overwrite concurrent decision/execution state. Underlying
CRM rights and current approver authority remain independently checked at execution.

OFFICIAL-13: appointment automation status requires NOTIFICATIONS VIEW and the
existing capability guard. Counts and failed rows use current Notification scope
before aggregation/LIMIT8, including ordinary private-conversation restrictions.
OWN retains business-wide notifications; TEAM retains its existing team-recipient
semantics. Linked Client and Appointment data require their independent current read
rights. Hidden Appointment IDs and navigation URLs are masked; readable notification
status remains. Calendar target URLs are rebuilt from the readable linked Appointment;
detached links expose no stale ID. Direct calls without an authorized actor expose no
counts or rows.

OFFICIAL-09: catalog CSV/XLSX confirmation and manual catalog service writes require
current SETTINGS UPDATE on the existing Service or unsaved candidate, including
the shared-object branch restriction. INTEGRATIONS admission alone is insufficient.
Product-only catalog events retain their existing integration policy. ImportJob
ownership remains unchanged; the row helper uses the current request actor, with
job.actor only for legacy direct calls. Missing actor fails closed for Service writes.

CRM-MB01, решение владельца 12.10.2026: клиентская база и история остаются общими
внутри Business с действующими record/field permissions; создание/изменение записи
и конфигурации филиала дополнительно ограничено доступными филиалами. Branch grant
не выдаёт роль или permission. Owner сохраняет все филиалы, член команды получает
явно назначенные филиалы либо разрешённую управляющим область «все филиалы».
Нельзя выдать доступ шире собственного или изменять общий объект, затрагивающий
недоступные филиалы. Вход в CRM, доступ к филиалам и доступность специалиста для
записи — самостоятельные состояния. Реализация/проверка ведётся в текущем checkpoint.

Каждая merchant-сущность принадлежит Business либо безопасно выводит его через
связь. Queryset ограничивается до поиска, подсчёта, pagination и сериализации.
Generic update не меняет владельца Business, включая ownership через parent.
Same-business связь сама по себе ещё не даёт актёру права на связанный объект.

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

Matching an anonymous supplied phone/email is not authority to remove a saved
marketing refusal. Public positive flags may retain existing first-consent behavior
but cannot override OPTED_OUT. This does not redefine authorized consent-management
or existing channel-bound inbound START evidence rules; no public force-override or
new role permission is introduced. Refusal is per Business/client/channel.

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

The existing sensitive-field rule is unchanged, including manager/accountant role
exceptions; this patch does not invent a new BILLING requirement for those roles.
Denied monetary values are null/empty currency or empty CSV; record counts and
independent scope remain. Mixed-Business summaries with any hidden contributing
amount mask the whole monetary aggregate. Saved typed monetary metadata is redacted
on read, not rewritten; arbitrary user-authored prose is not a field-policy parser.

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

Analytics membership/report visibility does not substitute for source-record VIEW.
Resource/capability denial yields existing zero/empty metrics; it does not alter
permissions or automatically deny independently readable records of another resource.
Field-level amount masking, Client retention denominator and connector/setup reporting
remain separate boundaries and are not certified by this source-resource fix.

OFFICIAL-07, 28.10.2026: ensure_default_roles now initializes absent presets
only; onboarding never overwrites existing role metadata, activation, JSON, denies,
scope or permission rows. Initialization of a new role is atomic. Explicit audited
TEAM MANAGE permission editing remains separate; no reset API/permission added.
Corrected BEFORE12:11 failing assertions across10 methods,2 controls PASS;
AFTER23/combined316 PASS without skips, syntax/system/migration-drift PASS.
HEAD98925b67 + preserved WIP/six prior fixes + patch. OFFICIAL-07-20261028 in
PRIMARY-SESSION; output/security-remediation-20261028/onboarding-preset-preservation/
fix-report.md. Local isolated synthetic evidence only; no publication/live acceptance.

Existing presets with missing permission rows are preserved as existing, not
automatically repaired or reset. This initializer does not alter access-resolution
fallbacks. Explicit reset/repair requires separately agreed scope; no such action
or automatic migration of actual roles was performed.

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

OFFICIAL-08, 28.10: pricing competitor offer сверяет Business и rule по эффективным
сохранённым/входящим значениям, включая PATCH без business. Владение обоими Business
не разрешает cross-link; обычные same-Business изменения/явный repair допустимы.
Recommendation и autopilot observation gate используют только offers того же
Business. Legacy ошибочные строки автоматически не мигрируются. Проверки и границы —
OFFICIAL-08-20261028 в текущем checkpoint; ценовая формула и права не меняются.

FU-BE-01, 28.10: общий BusinessInvitationSerializer возвращает пустые строки
в token и invite_path без текущего TEAM MANAGE для Business приглашения; отсутствие
request/user context также закрывает секреты. TEAM VIEW сохраняет только прежние
метаданные. Управляющие сохраняют ссылку для доставки; preview/accept и consented
reissue сохраняют существующие проверки. Старые уже полученные bearer не отзываются
автоматически. Проверки и границы — FU-BE-01-20261028 в текущем checkpoint.

OFFICIAL-01, 28.10: generic `DELETE /api/businesses/{id}/` не поддерживается
и возвращает 405 после аутентификации, включая owner/admin/platform actors.
Членство и право настройки не дают отдельного lifecycle удаления Business.
GET/POST/PUT/PATCH/HEAD/OPTIONS сохраняют прежние проверки и audit при записи.
Изолированные проверки и границы — OFFICIAL-01-20261028 в текущем checkpoint.

AUD-16, 19.10: ImportJob не принимает служебные поля из запроса и не поддерживает
generic изменение/удаление. Business/entity/source фиксируются при upload, actor —
из сессии. Preview/confirm перечитывают job под блокировкой и проверяют текущие
права CREATE на соответствующий ресурс; обычный пользователь видит только свои
job в доступном Business. Django admin не обходит lifecycle и показывает историю
только для чтения. API и проверки — [интеграционный контракт](integrations.md#импорт-экспорт-и-public-ingress)
и checkpoint AUD-16-20261019. Новая permission-модель не вводится.

AUD-15, 19.10: PipelineStage API не принимает чужой pipeline и не переносит
существующую стадию; StageTransition API сверяет Business/pipeline обоих концов
при создании и редактировании, включая поля, отсутствующие в PATCH. Проверки
существующих ролей, shared configuration scope и неизменяемого Business сохранены.
Версия/проверки — checkpoint AUD-15-20261019; рабочие старые связи не мигрировались.

AUD-02, 17.10: POST/PATCH notes и activity-events проверяют client и текстовую
ссылку entity_type/entity_id в том же Business, а также VIEW/UPDATE связанной
CRM-сущности. При relink проверяется и прежняя связь; неподдержанные типы/неполные
ссылки отклоняются. Поддержаны Client, Lead, Deal, Appointment, Task, Conversation,
BotConversation, Message, BotMessage и Payment; имена без учёта регистра и bot-алиасы
приводятся к имени модели, ID — к проверенному PK. Пустая ссылка допустима.
Author/actor берётся из сессии при создании и не меняется входным PATCH/PUT;
редактирование не переписывает исторического автора. Чужие и отсутствующие client
или default_responsible_user дают одинаковую безопасную ошибку. Это граница
пользовательского API, а не запрет серверным сервисам создавать системные события.

AUD-03, 17.10: Client.notes выдаётся только по can_view_sensitive_field для
текущего пользователя и Business: одинаково в списках/detail, CRM-карточках,
сегментах и CSV. Без actor, в том числе для public API token с clients:read,
поле пустое; права создателя токена не наследуются. Запрещённое непустое изменение
отклоняется, пустой masked round-trip сохраняет прежнюю заметку. Сегменты с
notes-предикатом, их условия/счётчики и клиентская выборка через них недоступны
роли без доступа к полю. Готовый CSV повторно маскируется при скачивании по
текущим правам; приватный исходный файл не переписывается. Отдельные записи
истории Note сохраняют свою политику. Проверки — checkpoint AUD-03-20261017.

Основные merchant presets: owner, admin, manager, operator, specialist.
Director — отображаемое название admin, не новая роль и не owner. Исторические
staff/doctor/marketer/accountant/support сохраняют совместимость, но не задают
новую базовую модель. Профессия врача не является разрешением. Для каждого
действия применяются текущий membership, permission, OWN/TEAM/BUSINESS и capability.
Матрица пресетов и её overrides находятся в [access.py](../../apps/businesses/access.py);
копия общей таблицы «manager может всё» не заменяет per-record проверку.

Вложенные карточки, counts, next-task, board, timeline, custom fields, файлы,
экспорт и AI проверяют доступ к каждому ресурсу. Разрешённый parent не раскрывает
запрещённых children. Sensitive-field masking действует и во вложенном ответе.
Недоступная сущность возвращает безопасный denial, без имени чужого Business.

AUD-13, 17.10: обычные PATCH/PUT через TenantModelViewSet проверяют UPDATE
сохранённого объекта до обработки новых полей. VIEW business не разрешает
присвоить себе чужую запись при UPDATE own/team. Проверка итогового кандидата
и запрет смены Business сохраняются; при CRM lock reload исходные права проверяются
повторно. Смена responsible_user заявки проходит assign_lead и его assignment policy,
историю/аудит/уведомления в одной транзакции с остальными полями. Чужой tenant остаётся
недоступным. Message payload/lifecycle отдельно защищён в AUD-14 ниже.
Версия и изолированные проверки — checkpoint AUD-13-20261017.

AUD-14, 17.10: BotMessage и legacy Message наследуют OWN/TEAM от родительского
диалога, в object check и queryset до pagination. Generic PATCH/PUT/DELETE истории
запрещены. Authenticated POST сохраняет только входящий текст от client; требует
CREATE сообщения и VIEW/UPDATE диалога, повторно проверяемых под блокировкой.
Произвольный sender, provider payload/ID, delivery status/retry/timestamps не принимаются.
Исходящие сообщения и retry проходят существующие Inbox actions с UPDATE диалога;
чужой message_id нельзя повторить через другой диалог. Версия/проверки — AUD-14 checkpoint.

Назначения проверяют активного участника того же бизнеса и область caller.
Новый assignee не может быть временно недоступен. Operator может self-claim
разрешённую неназначенную работу, manager перераспределяет в своей области,
owner/admin — в пределах существующих бизнес-прав. Специалист OWN привязан к
активному `resource.linked_user`; legacy staff/doctor не меняются молча.

Для задач (решение владельца TASKS-REDESIGN-20261013) operator/specialist имеют
`tasks:create:own` и создают задачу себе; исторические staff/doctor и custom overrides
сохраняются. Создание проверяет CREATE отдельно от UPDATE. Manager назначает в своей
области, owner/admin — в Business. Авторство и watcher дают просмотр в разрешённом
scope, но не право менять задачу другого исполнителя. «Мои» — только назначенные
текущему пользователю; созданные и наблюдаемые доступны отдельными фильтрами.
Ответ API содержит доступные действия и маскирует недоступные связанные сущности;
UI не отправляет скрытые связи обратно как обнуление при редактировании.

Business type — метаданные, не автоматическое скрытие Deals, переименование Lead
или включение медкарты. Capabilities серверно ограничивают API, очереди,
агрегаты, AI и автоматизации. Выключение не удаляет данные; повторное включение
возвращает доступ согласно текущим правам. Settings изменения требуют своих прав.

Кнопки области видимости роли меняют только scope выбранных существующих permissions
одним атомарным действием `team:manage`; `is_allowed` каждого действия сохраняется.
NONE не стирает набор разрешённых действий. Управление определениями custom fields
требует `settings:update`; запись значения также требует доступа VIEW/UPDATE к самой
CRM-сущности и разрешённой роли поля. Списки значений ограничиваются объектным scope.
Право отвечать в диалоге не заменяет `conversations:manage` для общих быстрых
ответов. Реестр и граница проверки — [Settings evidence](../testing/settings-functional-20261008.md).

Код: [tenant viewsets](../../apps/core/viewsets.py),
[capabilities](../../apps/businesses/capabilities.py),
[CRM projections](../../apps/core/crm_cards.py).
Регрессии: [tenant](../../apps/core/tests_tenant_isolation.py),
[nested scopes](../../apps/core/tests_crm_projection_access.py),
[mixed roles](../../apps/core/tests_mixed_membership_scope.py).

## Критические действия

ADMIN-04, решение владельца16.10: обе platform-роли со свежим MFA, открытым
обращением и причиной исправляют доступ только выбранного Business. Отключение
membership и отзыв непринятого приглашения не требуют ожидания владельца;
восстановление, изменение существующей роли и перевыпуск приглашения требуют
личного подтверждения текущего владельца в аккаунте. Запрос хранит неизменяемые
условия, revision, владельца/epoch и срок24ч; изменённые/просроченные условия
нельзя выполнить по старому согласию. Повтор безопасен, изменение и аудит атомарны.
Глобальный User.is_active, credentials, владелец Business, другие memberships,
специалист, история и назначения сохраняются. Глобальная разблокировка исключена.
Диагностика аудитируется и не возвращает invitation token; новая ссылка доступна
владельцу в обычных настройках команды, автоматической отправки нет.
[Контракт](../testing/platform-rebuild-spec-20261014.md#1511-admin-04--утверждённые-границы-16102026),
[сервис](../../apps/businesses/employee_access.py); фактическая приёмка и отдельная
рабочая миграция businesses0013 — в checkpoint.

ADMIN-02, решение владельца16.10.2026: обычную передачу Business готовит и
выполняет platform_admin со свежим MFA, причиной и обращением того же бизнеса.
Прежний и новый владелец лично подтверждают неизменяемые условия в своих аккаунтах;
получатель уже должен быть активным участником Business. Прежнему владельцу явно
выбирают существующий профиль сотрудника либо отключают только этот Business.
platform_manager имеет просмотр и работу с обращением, но не выполняет передачу.
Без подтверждения прежнего владельца передачи нет; assisted recovery не входит
в этот сценарий. Изменение участников/ролей, отзыв авторизации, истечение срока,
отказ и повтор выполнения не могут молча применить старые условия.
Смена Business.owner, membership, отзыв прежних сессий обоих участников и аудит
атомарны; история авторства, специалист и другие Business сохраняются.
Реализация: [сервис](../../apps/businesses/ownership.py),
[API](../../apps/businesses/ownership_views.py); фактическая граница проверки,
миграций и публикации — [checkpoint](../testing/task-state/PRIMARY-SESSION.md).

| Действие | Необходимая граница |
| --- | --- |
| Client archive/soft DELETE/merge | `clients:delete`, object scope, доменные зависимости; update недостаточно |
| Restore критичных CRM-данных | Существующее owner/admin ограничение и action permission; не общий обход lifecycle |
| Payment view/create/refund | `payments:view/create/manage`, доступ к клиенту и связанным Deal/Appointment; manager по умолчанию не получает refund |
| VisitPlan money | Текущие `payments:view` и доступ к чувствительному amount обязательны также при записи; CREATE для условий/прихода, MANAGE для возврата/сохранения и источника переноса. Доступ к клиенту, всем шагам и источникам оплаты; согласование, приход и команды плана требуют UPDATE плана/шагов; прямой возврат из журнала сохраняет существующий MANAGE. Повтор команды заново проверяет права; при отсутствии финансового VIEW проекция `money: null`. Новых grants нет ([evidence](../testing/evidence/visit-plan-payments-20261118.md)) |
| Appointment/заметка | `appointments:update`, доступ к записи; специалист только к своей связанной Resource-записи |
| Аннулирование ошибочного завершения / старая оплата плана | Только текущий владелец Business, дополнительно прежние financial VIEW/MANAGE, доступ к клиенту/всем шагам/источнику и UPDATE плана. Финансовый grant менеджеру сам по себе не разрешает эти команды. Предварительный расчёт, причина, явное подтверждение; replay заново проверяет доступ |
| График/исключение специалиста | `settings:update`, same Business; отсутствие не отменяет визиты автоматически |
| Task lifecycle/assign/watch/comment | `tasks:update`, scope, действительный target; отмена с причиной |
| Inbox AI pause/resume | `conversations:update` и `ai_assistant:suggest`, открытый диалог и readiness при resume |
| Agent settings/knowledge | Существующие `ai_automation` permissions; создание approval само по себе не решение |
| AI mutation | Exact approval там, где он обязателен, плюс underlying CRM permission; controlled creation отдельно в [AI](ai.md) |
| Automation retry/cancel | `automations:manage`, Business и действующий run; не replay завершённых effects |
| Connector retry/health/config | Профильные integrations права; безопасный retry не включает provider write-back |

## Platform support и MFA

Решение владельца 15.10.2026 расширяет целевой scope панели административными
действиями, включая смену владельца, recovery доступа и восстановление подписки.
Пять согласованных сценариев и предлагаемый инспектор read + explicit actions —
в [разделе 15 технической спецификации](../testing/platform-rebuild-spec-20261014.md).
Для ADMIN-01 владелец явно согласовал: platform_admin и platform_manager могут
исправлять реквизиты со свежим MFA, основанием и аудитом, без временного grant
владельца; исполнитель и история сохраняются. Отдельный
[GET/PATCH API](../../apps/core/platform_details_views.py) реализован локально:
[сервис](../../apps/core/platform_details.py) ограничивает поля, проверяет свежую
DB identity/epoch, принадлежность обращения и revision, сохраняет атомарный аудит.
Локальная проверка — в checkpoint; `f7d74d5` опубликован, CI success.
Прежний блокер push снят; deployment не выполнен.
ADMIN-02/03/04 согласованы отдельными контрактами ниже/выше; прочие
write-сценарии требуют своих решений. Support-note
ниже сохраняет прежние grant/MFA: это отдельная операция. Запрет самостоятельной
правки юридических реквизитов бизнесом пока не принят.

Platform и merchant-права не смешиваются. Отдельный platform GET read-path предоставляет постоянный подробный просмотр
CRM с аудитом по решению 15.10; это не merchant membership и не право произвольной
записи. ADMIN-01/02/03/04 имеют отдельные узкие полномочия; support-note ниже
сохраняет собственный grant/MFA-контракт. SupportAccessGrant создаёт/меняет/отзывает только
owner с recent MFA; grant навсегда привязан к исходному Business и получателю,
получатель не продлевает собственный grant. Истёкший grant не действует.

Support-note требует platform_admin (с существующей superuser semantics),
активный grant конкретного бизнеса этому actor и свежую MFA, даже если общий
`SUPPORT_REQUIRES_GRANT=False`. Platform_manager может читать разрешённую platform
диагностику, но не писать support-note с grant/MFA. UI использует
`can_log_support_action`, POST повторно проверяет сервер. BE-GAP-004/D-09 решены.

Для staging/production/первого платного пилота `AUTH_PRIVILEGED_MFA_REQUIRED=True`.
Обязательные identities: superuser, platform_admin, platform_manager, owner и
активные owner/admin memberships. Одна лишь роль manager/operator/specialist
не требует MFA этой политикой, но уже включённый фактор остаётся обязательным.

Primary factor выдаёт одноразовый challenge, не JWT-сессию до проверки фактора.
TOTP replay отсекается счётчиком, recovery codes одноразовые и хранятся хешами;
TOTP secrets зашифрованы keyring. Секреты/коды/refresh/challenge не логируются.
Вход Django admin применяет ту же политику MFA: TOTP или одноразовый recovery code
проверяется до создания административной сессии. Требуемый enrollment выполняется
через существующий вход CRM. Каждый admin route проверяет proof пользователя,
auth epoch и устройства; прежняя password-only сессия не обходит включённую MFA.
Вход admin ограничен по IP и идентификатору (`AUTH_ADMIN_LOGIN_RATE`, 5/min),
смена пароля — по пользователю (`AUTH_PASSWORD_CHANGE_RATE`, 5/min) до проверки
пароля/фактора. Общий Django Redis cache хранит квоты всех web workers;
`DJANGO_CACHE_URL` по умолчанию использует `REDIS_URL`. Недоступный cache не
разрешает попытку. DRF read/write throttling остаётся базовым abuse-контролем,
не атомарным пределом для одновременных запросов. Изолированные проверки явно
используют отдельный locmem cache; staging/production такой backend отвергают.
Password/security/MFA reset проверяют текущий пароль/фактор по своему контракту,
отзывают сессии и audit. Reset обязательной MFA требует повторного enrollment,
не выдаёт MFA-free privileged session. Step-up привязан к user/auth epoch.
Нет фактора — только отдельно авторизованное восстановление после проверки
владельца; экспорт/восстановление старого секрета недопустимы.

Код: [support](../../apps/core/platform_views.py),
[grants](../../apps/core/security_views.py), [MFA](../../apps/accounts/mfa.py).

## Сессии и личный аккаунт

ADMIN-03, решение16.10: при утрате всех доступов — обращение в поддержку и ручная
идентификация по ранее проверенным данным. Обе platform-роли со свежим MFA могут
запустить восстановление. Для сотрудника требуется личное подтверждение действующего
владельца; при других Business — дополнительно проверка владельца самого аккаунта.
Публичные сведения не достаточны; без доказательств/при расхождениях доступа нет.
Условия, новый mailbox, сроки, отзыв credentials и аудит —
[контракт ADMIN-03](../testing/platform-rebuild-spec-20261014.md#admin-03--согласованный-контракт-16102026).
Обычная передача Business в ADMIN-02 остаётся отдельной операцией.

- Access/refresh проверяют auth epoch; security-изменения отзывают прежние
  credentials. Нормальный tracked logout отзывает текущее устройство, не все
  другие. Старый sid-less logout сохраняет совместимое широкое отзывное поведение.
- Merchant session: idle 7 дней foreground-использования или absolute 30 дней
  от login, что раньше. Access default 15 минут. Background reads не продлевают
  idle; параметры в `config/settings.py`, не в клиентском таймере.
- Session API работает только для request.user, не по чужому user ID.
  Отзыв другого своего устройства idempotent, текущего через этот endpoint
  отвергается; enabled MFA проверяется. Список не выдаёт токены/JTI.
- Все операции refresh-cookie сериализуются; generation checks отвергают
  старые ответы/продолжения после смены аккаунта. Web Locks координируют вкладки
  на поддержанных origins; fallback остаётся per-page. BroadcastChannel не
  сохраняет credentials и не переключает открытую страницу на чужой аккаунт.
- Network/429/5xx сохраняют текущий аккаунт/URL/draft, дают bounded retry и
  Retry-After. Invalid/expired credentials требуют login. Бизнес-мутации не
  переигрываются автоматически после восстановления auth.
- Email/login change относится только к request.user, не меняет ID/memberships;
  требует пароль и enabled MFA, подтверждение одноразовым mailbox code.
  Обычный profile PATCH email не меняет. Подтверждение повторно проверяет
  доступность/epoch, отзывает старые sessions и выдаёт замену. Locmem-тест не
  доказывает SMTP-доставку.
- Принятие приглашения существующим email возможно только из сессии этого
  аккаунта; меняется membership, не пароль/глобальные атрибуты пользователя.

Код: [auth views](../../apps/accounts/auth_views.py),
[device sessions](../../apps/accounts/session_views.py),
[email change](../../apps/accounts/email_change_views.py),
[browser API](../../frontend/src/api/client.ts).

## Файлы, секреты и публичный периметр

CRM-S02, решение владельца 14.10.2026: платформенная админка показывает диагностику
и журнал поддержки; восстановление фоновых операций выполняет уполномоченный
сотрудник клиники через существующие права. Новых platform retry/cancel прав нет.
GET `platform/merchants/{id}/support-actions/` доступен platform-ролям и возвращает
только журнал выбранного Business с sanitization; POST сохраняет требования
platform_admin + exact active grant + recent MFA. CORS разрешает заголовок
`X-Zani-MFA-Step-Up` только в рамках уже разрешённых origins; это не отменяет
серверную проверку токена и прав.

Загрузка/скачивание проверяют entity/Business и соответствующие права.
AUD-18: готовый ExportJob требует совпадения сохранённого и актуального
контекста доступа; legacy файл без fingerprint и изменённый scope требуют
нового экспорта. Подробная граница — [интеграционный контракт](integrations.md#скачивание-сохранённого-экспорта--aud-18).
Quarantine/clean fingerprint обязательны даже для platform_admin; публичный
bucket или прямой storage URL не заменяют download permission. Нет ручного
merchant-override «считать чистым». CSV/XLSX сканируются до parsing; экспорт
сохраняет scope и защиту от spreadsheet formula injection.

Аватар — только request.user, original scan до decode, проверенный crop,
перекодированный JPEG без EXIF/GPS; original/имя не сохраняются. Изменение
аватара не публикует приватный media URL. Детали эксплуатации — [operations](operations.md).

Provider credentials — env/config или encrypted ConnectorCredential, masked
serializers; не channel config_json, browser, audit или raw error. Key rotation
не уничтожает ключ до проверки перешифровки и потребителей MFA. Webhook проверяет
provider signature/secret и Business binding. DRF throttles — базовый слой,
не доказательство общей защиты от abuse; не отключать их для зелёного теста.
Точные defaults/flags — [settings](../../config/settings.py) и
[пример конфигурации](../../.env.example), без чтения реальных секретов.

## Юридические страницы и незакрытая приёмка

Signup требует `terms`, `privacy`, `personal-data`, `company-data` и пишет audit
атомарно с созданием. Текущий `content_status: placeholder` означает техническое
подтверждение IDs, не согласие с опубликованным юридическим текстом. Тела страниц
ожидают предоставленный владельцем текст; не генерировать его как принятую policy.
Реальные данные/production, ручная доступность и broad abuse acceptance остаются
в [acceptance](acceptance.md).

Исторические источники, не текущие инструкции:
[прежняя матрица](../../archive_docs/2026-10-07/docs/security/PERMISSION_MATRIX.md),
[MFA](../../archive_docs/2026-10-07/docs/security/privileged-mfa.md),
[файловая защита](../../archive_docs/2026-10-07/docs/security/file-antivirus.md).

## Обращения поддержки — PLATFORM-SUPPORT-20261015

Отдельный домен `apps.support`: platform_admin/platform_manager (и superuser)
читают очередь, создают обращения, отвечают, назначают активных сотрудников
платформы и решают с обязательным итогом. Это узкое право поддержки,
не расширение grant/MFA и не доступ к CRM или пациентам.
Clinic API требует активного аккаунта и принадлежности к Business: сотрудник
видит собственные обращения; owner/admin — все своей клиники. Автор/контакт
и owner/admin могут явно возобновить обращение с причиной. Потеря доступа
проверяется также при повторе идемпотентного запроса.
Внутренние заметки хранятся отдельно и отсутствуют в clinic API, поиске,
счётчиках непрочитанного и глобальном аудите. Публичные события неизменяемы;
аудит содержит метаданные без текстов переписки, заметок и причин.

PLATFORM-INCIDENT-LINK-20261015: platform-роли явно связывают обращение с
эпизодом фоновой обработки той же клиники. Связь и безопасный снимок доступны
только platform API; clinic API не раскрывает их и не принимает incident input.
Повторная связь не создаёт второй аудит; создание обращения со связью атомарно.
Это не выдаёт доступ к внутренним CRM-данным и не меняет grant/MFA.

### Решение владельца 15.10.2026: постоянный просмотр CRM оператором

PLATFORM-CLINIC-CRM-20261015 реализует это решение отдельными GET platform API:
`merchants/{business}/crm/{kind}/`, карточка, дочерние записи и `crm-access-log/`.
Активная platform_admin/platform_manager (и существующая superuser semantics)
перепроверяется по БД при каждом чтении; временный grant не нужен. Business
явно задан в URL, основная и связанные сущности проверяются в его границах.
В merchant API новые права не добавлены. Читаются клиенты, заявки, сделки,
задачи, визиты, переписка, журнал платежей и safe статусы подключений/каналов.
Сообщения, заметки, комментарии, custom fields, теги и активность доступны
страницами; чтение переписки не меняет unread/read cursor и не отправляет ответы.

Каждый успешный ответ требует записи SUPPORT_ACCESS с метаданными оператора,
Business, вида записи, ID и времени; тексты, поисковые строки и payload в аудит
не попадают. При ошибке аудита ответ503 не содержит CRM-данных. Ответы no-store;
UI не сохраняет CRM cache после ухода и скрывает карточку при отказе чтения.
Проекции исключают токены, credentials, raw JSON и технический payload. Доступ
к экспорту, файлам, изменениям/удалению, операционному retry и AI этим правом
не выдаётся. Прежние grant/MFA для support-note сохраняются.
Код: [selectors](../../apps/core/platform_crm_selectors.py),
[read API](../../apps/core/platform_crm_views.py),
[проверки](../../apps/core/tests_platform_crm.py); граница приёмки/публикация —
[checkpoint](../testing/task-state/PRIMARY-SESSION.md), требования —
[раздел13 спецификации](../testing/platform-rebuild-spec-20261014.md).


ADMIN-05, локальная основа16.10: merchant orders требуют billing VIEW/MANAGE
выбранного Business. Банковское поступление подтверждает только platform_admin;
обе platform-роли читают инспектор с аудитом и выполняют recovery/reconcile со свежим
MFA, открытым обращением этого Business и основанием. Платёж не снимает независимые
блокировки; изменившаяся подписка/условия блокируют применение. Полный коммерческий
доступ не заявлен; границы — [паспорт](../pre-production/subscription-usage.md).
## Повторные проверки при чтении — 06.11.2026

JWT authentication создаёт свежий User на каждый запрос. Для GET/HEAD его членства
и явные правила ролей повторно используются только внутри этого запроса. Следующий
запрос заново читает БД; отзыв членства/прав, auth_epoch и device session проверены
регрессионными тестами. Для write-запросов такой snapshot не создаётся. Проверки
конкретного объекта, OWN/TEAM, филиала и актуального support grant не заменяются
общим разрешением. SSE повторно авторизуется через `get_user` без read snapshot.
Это оптимизация существующих проверок, не новая модель прав или кеш между запросами.
[Профиль и проверки](../testing/evidence/performance-20261106.md).

## Приглашения сотрудников — 12.11.2026

TEAM MANAGE выпускает Business/email/role-bound приглашение на24ч. Новый
пользователь задаёт пароль с подтверждением; существующий принимает из своей
сессии без изменения пароля/профиля. Backend проверяет active account, роль,
отдел, membership и лимит. После принятия выбирается пригласивший доступный Business.
Resend требует revision и60с cooldown, заменяет token/expiry; accepted/revoked
не пересылаются. Отзыв прекращает доступ по ссылке. Старые ссылки сохраняют свой
срок до отзыва/перевыпуска. Generic PATCH/DELETE недоступны.
SMTP выполняется после commit; delivery_status отделён от статуса приглашения.
Support repair с личным согласием владельца остаётся без автоматической отправки.
[Реализация, проверки и SMTP-граница](../testing/evidence/invitations-24h-20261112.md).
