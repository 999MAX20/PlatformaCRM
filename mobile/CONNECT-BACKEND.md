# Native CRM: подготовка подключения backend

Цель — подготовить существующие iOS/Android клиенты к подключению основного backend в понедельник **2 ноября 2026**. Это инструкция внутри mobile scope: без desktop/UX50, backend-изменений, миграций, deploy, реальных команд, устройств или credential/security операций.

## Что уже запускается локально

Debug собирает явно внедрённые synthetic repositories/ports. Release показывает `configurationRequired`: действующая сессия и сервер не подключены. API-ошибка никогда не включает fixture fallback. Текущий исходник372 прошёл Core/host и typecheck всех85 App-файлов в Debug/Release на macOS; это не iOS app build, Android current build или device/live приёмка. Исторические APK/build результаты в README относятся к своим старым исходникам.

Обычная проверка контрактов из корня проекта:

```sh
python3 mobile/scripts/check_contracts.py
```

Прочие native-проверки выполняются по текущему разрешённому preflight/checkpoint: одна полоса, Core/host300s, App180s/config, конечный общий cap результатов+canonical Checks2ГиБ и отдельный резерв2ГиБ. Android compile/JUnit пока закрыты двумя известными SF_DATALESS cache файлами: metadata only, без hydration/retry/bypass. Устройства, приложения, симуляторы, SwiftUI Preview и удалённый CI здесь не запускаются.

## Публичные параметры подключения

[connection.public.env.example](connection.public.env.example) содержит только два пустых обязательных входа: HTTPS origin и timeout. Парный `NativeConnectionConfiguration(publicValues)` разбирает ровно эти два входа; автоматического env loader нет. Missing/blank остаётся unconfigured, неизвестный ключ отклоняется. Timeout — положительные десятичные секунды с максимум тремя знаками после точки, без exponent/единиц/округления; conversion в целые миллисекунды проверяет overflow. Платформенный Android exchange дополнительно отклоняет timeout вне1…Int.MAX_VALUE до открытия connection. Он не содержит и не принимает credentials, token, device id, signing data или глобальный Business default.

Swift builder принимает явные `URL origin` и `TimeInterval timeout`; Kotlin builder принимает явные `URI origin` и положительный `timeoutMillis`. HTTPS origin должен быть корневым, без user/password/query/fragment. Существующий builder удерживает `/api/mobile/v1/`, кодирует query, создаёт только GET descriptor с `Accept: application/json`. Swift descriptor отключает cookies. Caller передаёт выбранный Business через существующие request/query контракты. Ни origin, ни timeout, ни Business не угадываются из fixture или приложения.

Подключение к произвольному host и чтение env/credentials не являются побочным эффектом конструктора. Секреты не копируются в этот шаблон, UI-copy, логи или fixtures.

## Что требуется дописать в клиенте

| Часть | Уже есть | Следующий конкретный артефакт |
| --- | --- | --- |
| Request construction | Парные builders/config, `BackendReadTransport`, `NativeReadHTTPExchange`, URLSession/URLConnection adapters; existing repositories/error mapping | Явное связывание принятой caller-owned session/connection policy; локальные проверки используют только memory exchange |
| Startup/config | Debug fixture composition, coalesced bootstrap, fail-closed Release | Явное связывание принятого origin/timeout и session provider; безопасный missing-config путь, без fixture fallback |
| Auth client | Парные pure login/refresh/logout request/response schemas написаны; local synthetic fixtures проверяют exact presence/context/raw text. Auth UI/client/session flow ещё не написан | Принятое связывание session/user identity и local client flow; реальные credentials, secure storage, stable device id и revoke/current boundary относятся к B-AUTH/принимающему |
| Product consumers | Scoped reads, Client/Task/Inbox forms/attempt ledgers; duplicate/merge preview; selected Appointment local confirm/cancel/reschedule/complete/no-show review/fixture consumers | Переиспользовать написанные consumers, добавить только exact source-backed adapters/нехватающие продуктовые формы |

Android manifest пока не объявляет `INTERNET`; этот документационный блок разрешение не добавляет. Сетевой adapter уже написан; approved session и platform capability должны быть связаны явно при разрешённой подготовке клиента, а не возникать от ошибки API. Backend schema и исходники читаются для подготовки кода, но не меняются.

## Auth: подтверждённая форма существующего source

| Source endpoint | Вход | Ответ |
| --- | --- | --- |
| `POST /api/mobile/v1/auth/login/` | required `device_id`, `platform`, `email`, `password`; optional `business`, `app_version`, `build_number`, `os_version`, `device_model` | `access`, `refresh`, `token_type`=`Bearer`, `business`, `device` |
| `POST /api/mobile/v1/auth/refresh/` | `refresh` | `access`, `refresh`, `token_type`; отклонение source возвращает401 |
| `POST /api/mobile/v1/auth/logout/` | optional `refresh`; authenticated source | `ok` |

Основание: `apps/mobile/views.py:92–197`, `apps/mobile/serializers.py:10–45`, router в `config/urls.py`. Это существующие schemas, не новое API и не разрешение выполнить запрос. Login source создаёт/обновляет device и session. Native код не придумывает device id, token, TTL, permissions, refresh replay, durable owner или security policy. Typed client schemas и synthetic fixtures уже написаны. Они не создают principal из device/email, не вычисляют permissions/TTL, не выполняют POST и не реализуют native login/session UI. Реальные credential/security действия и принятый session-owner boundary остаются отдельным входом; отсутствие сервера не паркует независимую source-backed работу.

## Внешние входы для подключения

| Точный вход | Кто предоставляет/принимает | Что он блокирует |
| --- | --- | --- |
| Candidate backend SHA, разрешённый HTTPS origin, принимаемый timeout | Никита предоставляет; Максим принимает mobile boundary | Live wiring/smoke; локальный adapter и config code можно готовить сейчас |
| B-AUTH token/device-id owner, secure persistence/logout/revoke и допуск real credentials | Владелец B-AUTH + Никита server-security; Максим принимает native scope | Реальную auth/security/persistence интеграцию; не pure client schema/fixture preparation |
| Current native validation/device window и доступность прежнего toolchain | Максим/владелец устройств/toolchain | Android/device/live evidence; не подготовку Kotlin исходников |
| Недостающий authoritative original/version/current result для конкретной операции | Никита, Максим выбирает applicable native consumer | Только соответствующий write/full-original/recovery путь |

Полное ТЗ сейчас SF_DATALESS. Последний verified hash/range snapshot и metadata receipt сохранены в существующем continuation/evidence. Независимые локальные задачи продолжаются по этим проверенным контрактам; свежий hash текущих байтов ТЗ и новые непроверенные scope не объявляются.

## Read smoke после разрешённого подключения

Этот порядок описывает будущую приёмку, а не действия, выполненные данным блоком.

1. Зафиксировать candidate SHA/origin и session boundary. Убедиться, что отсутствующая конфигурация остаётся `configurationRequired`, а API failure не подменяется synthetic данными.
2. Через разрешённый auth/session клиент получить bootstrap. Проверить предоставленные Business/таймзону/членство; не подставлять fixture IDs, дату или права.
3. Прочитать список и independent detail в двух разрешённых Business; проверить частичность, null/redaction и scoped query. При Business/user/logout/revoke смене старые pending callbacks не устанавливают контент.
4. Проверить ошибочные ответы: raw401 сохраняется в transport, existing repository классифицирует его как unavailable; будущий session coordinator должен иметь отдельный approved binding; 403/404 и недоступность не раскрывают старые данные и не выглядят успешной записью. Точный HTTP status и cancellation сохраняются adapter-ом.
5. Проверить возврат к списку, существующие Client/Task/Inbox формы и их сохранённый ввод. Повторное чтение не подтверждает неизвестный исход команды; unknown input+attempt не удаляются ради нового запроса.
6. Отдельно зафиксировать actual Android/iOS/device/language/reader/IME evidence. Ни fake outcome, ни один typecheck не закрывают эти gates.

Реальные POST/PATCH/lifecycle/send/booking, денежные действия и восстановление неизвестной команды в этот read smoke не входят. Их accepted current contracts и отдельный допуск остаются явными; новые key/version/recovery/TTL или server defaults не создаются в native слое.

## Очередь до понедельника

Существующий evidence packet `MONDAY-CLIENT-PREPARATION373.json` содержит семь конечных приоритетных направлений и разбор всех53 исходных task rows: требование/AC, артефакт, критерий, зависимость/владелец, уже написанный код. Фактическая исходная матрица — **11 AVAILABLE_LOCAL /42 зависимых**, а не прежний ошибочный summary12/41. Эти53 строки не означают53 целиком ненаписанных фичи: source-local implementation и future live/device приёмка разделены. Уже реализованные draft/reply/handoff/preview subsets повторно не кодируются и не тестируются без нового изменения, дефекта или конкретного acceptance gap.

Selected Appointment confirm/cancel теперь имеют парный локальный review/attempt/result consumer с явно отдельным synthetic UPDATE/actor/key. Fake-ответ не меняет исходный GET и не доказывает server outcome. Unknown блокирует все пять lifecycle-действий для target и сохраняет исходный input/body/key/attempt; matching reread не снимает барьер. Ни POST, ни настоящая отмена/подтверждение не выполнялись. Reschedule input/review теперь написан: явное время с timezone, явная очистка либо scoped GET связанного Resource, source-strip причины и общий unknown-барьер. Исходный ввод и body/key/attempt удерживаются. Ограниченный receipt не доказывает resource/reason/availability/version; GET не меняется. Generic complete/no-show review/result теперь написаны по отдельному plain AppointmentSerializer с отдельным synthetic UPDATE/actor, без mobile key/version/replayed. Bounded generic CREATE draft/review теперь написан: отдельные scoped Client/Service/Resource reads, явное время/очистка ресурса, отдельный synthetic CREATE и plain201 fixture. Следующий subset — явный перенос still-current candidate start_at без reservation/default resource/end_at.

Swift source366 проверен в отдельном output/cache внутри canonical Checks: прежний swiftdoc и41 generated-cache placeholders сохранены metadata-only, не гидратировались; есть resident witness последнего hash doc. Cap и отдельный резерв по2ГиБ, исходные SDK/source/process/timeout guards сохранены. Текущие outputs hash-verified; текущие байты старого placeholder не проверены заново.

Source366: selected Appointment complete/no-show local review/Back/plain AppointmentSerializer result written in SwiftUI/Compose; existing generic paths, explicit Business query and empty supported body. Separate synthetic UPDATE/actor context without mobile key/envelope/replayed/version. Shared all5 pending/unknown barrier retains original input/route/query/body/attempt; original GET unchanged, no lifecycle/followup/audit executed. All4 allowed macOS Swift stages PASS; Android/current/iOS app/device remain NOT_RUN. Next bounded generic CREATE draft/review requires existing scoped reads and separate synthetic CREATE, source-confirmed response status, no invented defaults/availability/recovery. See APPOINTMENT-TERMINAL-FINAL367.json and APPOINTMENT-BOOKING-CREATE-SOURCE-READY366.json.

Source369: bounded new Appointment form from explicit existing Client/Service/optional Resource linked reads is written in SwiftUI/Compose. Blank time and unselected fields, stable input/control visits, retained review/Back and immutable generic POST /api/appointments/ body business/client/service/start_at/resource; no status/source/lead/notes/end_at/key/version/defaults. Separate synthetic CREATE/actor only; pending/unknown retains original input/body/attempt across reread/Business return and no fake GET/calendar mutation. Current allowed macOS Core/host/all85 App Debug+Release PASS; Android/device/live NOT_RUN. No actual booking/availability/followup/audit. BOOKING-CAP-METADATA-ERRATUM369.json preserves the pre-native metadata-only cap typo; current cap/reserve remain exact2GiB. Next current-candidate time bridge audit: APPOINTMENT-BOOKING-CANDIDATE-BRIDGE-SOURCE-READY369.json.

Source372: paired explicit still-current candidate start_at bridge into the bounded new form and stable slot-day input visit are written. Full parent/related/slot/booking/peer controls are captured/revalidated; no resource=null from unspecified GET, copied end_at/choices/grant/reservation or unknown repeat. Existing CREATE/plain201 body and original GET remain unchanged. Current allowed macOS Core/host/all85 App Debug+Release PASS, Android/device/live NOT_RUN. Next source audit: SERVICE-SELECTOR-READ-SOURCE-READY372.json; Service read uses APPOINTMENTS/VIEW, selected-Business server filtering/pagination completeness are not guessed.

Source375/doc376: paired bounded Service directory list/detail/explicit readonly choice written with strict selected-Business projection, stable presentation and stale content controls; independent of Calendar failure. Existing GET /api/services/ and /api/services/id/ have empty query. No guessed paging/default/eligibility/currency/CREATE, automatic next URL or actual network. Core/host/all87 App Debug+Release macOS PASS; Android/current/iOS app/device NOT_RUN. Current client-preparation packet: MONDAY-CLIENT-PREPARATION376.json. Next: RESOURCE-SELECTOR-READ-SOURCE-READY375.json.

Source382/doc383: paired bounded Resource seven-field directory and common envelope written with strict selected-Business projection, stable presentation and stale content controls; independent of Calendar failure. Existing GET /api/resources/ and /api/resources/id/ have empty query. No guessed paging/default/eligibility/currency/CREATE, automatic next URL or actual network. Core/host/all89 App Debug+Release macOS PASS; Android/current/iOS app/device NOT_RUN. Current client-preparation packet: MONDAY-CLIENT-PREPARATION383.json. Next: APPOINTMENT-FORM-DIRECTORY-BINDING-SOURCE-READY382.json.

Source387/doc388: paired form-owned Service/Resource independently read choice binding written with strict selected-Business projection, stable presentation and stale content controls; independent of Calendar failure. Existing Service/Resource GETs remain empty-query; existing POST body remains the same5 fields, with separate fake-only CREATE and immutable unknown. No guessed paging/default/eligibility/currency/CREATE, automatic next URL or actual network. Core/host/all90 App Debug+Release macOS PASS; Android/current/iOS app/device NOT_RUN. Current client-preparation packet: MONDAY-CLIENT-PREPARATION388.json. Next: APPOINTMENT-FORM-CLIENT-SELECTOR-SOURCE-READY387.json.


Runtime390 Client selector is source/static only, native NOT_RUN: private manual search/profile/explicit Use reuses GET /api/mobile/v1/clients/ (business,limit50,search) and /api/mobile/v1/clients/{id}/ (business), exact raw/search/read/form ownership and separate existing fake CREATE. Typed Client proof stays outside unchanged5-field create body; unsupported fixed-fixture combinations remain immutable unknown, with no inferred outcome from matching reads. This is fixture composition only; Release remains configurationRequired. Full390 Core/host/all91 App Debug+Release checks are parked by exact finite2GiB full remaining budget (SWIFT-FULL-REMAINING-BUDGET390-BLOCKED.json), latest full allowed source387 retained. Android remains metadata-only, no current iOS app/device/live checks. Independent Inbox conversation metadata preparation uses generic /api/inbox/conversations/{id}/ GET empty query, explicit response Business/id verification; generic attachments must never be invented in bounded mobile InboxThread. No URL/download/file bytes/provider or server/security/auth changes. Documentation checkpoint391 and readiness unchanged.


Runtime394 Client selector is source/static only, native NOT_RUN: private manual search/profile/explicit Use reuses GET /api/mobile/v1/clients/ (business,limit50,search) and /api/mobile/v1/clients/{id}/ (business), exact raw/search/read/form ownership and separate existing fake CREATE. Typed Client proof stays outside unchanged5-field create body; unsupported fixed-fixture combinations remain immutable unknown, with no inferred outcome from matching reads. This is fixture composition only; Release remains configurationRequired. Full394 Core/host/all91 App Debug+Release checks are parked by exact finite2GiB full remaining budget (SWIFT-FULL-REMAINING-BUDGET394-BLOCKED.json), latest full allowed source387 retained. Android remains metadata-only, no current iOS app/device/live checks. Independent Inbox conversation metadata preparation uses generic /api/inbox/conversations/{id}/ GET empty query, explicit response Business/id verification; generic attachments must never be invented in bounded mobile InboxThread. No URL/download/file bytes/provider or server/security/auth changes. Documentation checkpoint395 and readiness unchanged.


Source397 / checkpoint398 adds fixture-only generic GET /api/inbox/conversations/{id}/ metadata projection with empty query and explicit response Business/id + all attachment Business/bot_conversation/entity_id guards; mobile InboxThread stays unchanged. Only9 metadata fields are retained, no URLs/uploader/payload/bytes/scan/download/send/grants. Manual read/retry/row/Back, source/peer/presentation controls and unknown reply independence are paired. 10299 Core/4636 actual-host/all93 App DebugRelease macOS checks PASS on exact397, including repaired Client total56 oracle. Android779 prepared/653 after126 NOT_RUN; iOS app/device/live NOT_RUN. Full finite2GiB plan passed fresh source/SDK/residency/signature/process gate after autonomous historical residency changes, preserving all originals/copies and strict witnesses without cleanup/hydration/cap increase. Next exact message-level metadata audit397 uses a separate generic first message window; no automatic cursor/full-history inference or invented attachments in mobile payloads. Release configurationRequired remains.


Source400 / documentation401: paired explicit selected-message attachment metadata. Separate fixture-only GET conversation Business/id anchor, then generic messages first window with provided bounded max_messages limit1..300; owner rechecked before the second GET, no before_id/default/full-history inference. All message conversation and attachment Business/bot_message/entity_id rows validated before selected9-field projection; selected missing unavailable vs provided attachments[] empty. Mobile InboxThread/command ledgers unchanged; no file URLs/bytes/scan/grants or real send. Stable captured owner/content/presentation, peer exclusion and retained unknown input+attempt covered. 10508 Core/4663 actual host/all95 App D/R macOS PASS exact400; Android782 prepared/656 after126 NOT_RUN; iOS app/device/current/live NOT_RUN. Finite2GiB plan/reserve and all397/older accepted/failed copies retained. Next readonly delivery observations audit400; Release configurationRequired.


Source403 / doc404: same staged generic conversation anchor/messages first-window now projects four received status/timestamp fields as missing/null/exact raw text. Every row is validated before selected projection; no timestamp parsing/default dates/chronology, bounded thread mutation or own-send recovery. Existing9-field attachments/owner/peer/manual/late/unknown controls remain. 11610 Core/4675 actual host/all95 App D/R macOS PASS; Android785 prepared/659 after126 NOT_RUN; iOS app/device/live NOT_RUN. Full finite2GiB cap/reserve and all prior outputs retained; source84 original APK metadata-only with existing verified resident witness401. Next source audit403 is explicit fake-only generic retry-message, exact message_id body/plain201, independent synthetic UPDATE, no idempotency/recovery or real POST. Release configurationRequired.


Source406 / doc407 adds paired explicit fake-only generic retry-message: independent anchor/first-window original source, separate synthetic UPDATE actor, exact message_id-only body and empty query/headers, narrow new-message/plain201/retry_of/raw receipt. No idempotency/recovery/version/replayed or real POST/provider result is implemented. Review/attempt/result retain raw source/body/actor; unknown cannot acknowledge/repeat on matching GET and blocks peer reply/handoff at submit. No bounded thread patch. Static67 source/65 receipt oracles PASS; Core/host/App406 NOT_RUN because current run_checks.py and preflight.py are SF_DATALESS. Last all4 macOS verification is403 (11610/4675/all95 D/R); Android788 prepared/662 after126 NOT_RUN, iOS app/device/live NOT_RUN. Source406/407/full prior404/inverse hashes and old403 outputs preserved; optional legacy158 overlay is metadata-only. Exact finite2GiB cap/reserve remain, no current native budget approval/retry/hydration/alternate runner. Source84 original APK metadata-only with existing identical resident witness. Next independent fake self-assignment source406 requires MANAGE and active-member synthetic context, exact empty self body/plain200. Release configurationRequired.


### Source410 local self-assignment boundary (documentation411)

Generic Inbox assign uses get_object VIEW scope, CONVERSATIONS.MANAGE and active assignee membership; omission of optional user_id selects request.user in existing source. Local support is limited to an explicit separate synthetic actor/MANAGE/member fixture and exact empty body{}. Independent generic GET id/business/assigned_to/raw updated_at is observation only. Plain200 actor echo is validated as synthetic data; no bounded thread/list result is fabricated. Unknown keeps the immutable source+attempt and sibling command barriers; matching assigned_to or refreshed GET never provides outcome/recovery evidence. There is no new idempotency/version/replayed/recovery contract and no actual POST implementation. Default command ports remain absent, DEBUG fixture command and read adapters are distinct.

Current410 Swift/native and Android checks are NOT_RUN at preserved dataless inputs, prior403 Swift PASS remains historical. Actual backend/auth/permissions/durable recovery/device/full release acceptance are still dependent and not accepted by this local static work.


### Source412 local read/unread-marker boundary (documentation413)

Existing generic mark-read/mark-unread actions use get_object VIEW scope then CONVERSATIONS.UPDATE, no request serializer/body fields, and return plain InboxConversationSerializer200. Local support prepares only{} with separate synthetic UPDATE+actor context and fake command port. Generic unread_count/raw updated_at is read observation, never authority/version/recovery. A positive unread response is validated without comparing max against an old source read. No synthetic outcome patches bounded Inbox counts/badges/thread/list. Unknown keeps original action/source/actor/body/attempt and blocks opposite markers and reply/handoff/retry/self-assignment; matching0/positive GET never proves outcome.

Current412 Core/host/all95 App Debug+Release and Android verification remain NOT_RUN at the preserved dataless inputs; prior403 Swift PASS is historical. Actual marker POST, current grant/auth, durable recovery, device and release acceptance remain dependent. No new idempotency/version/replayed/recovery or date defaults exist.


### Source414 priority boundary (documentation415)

Existing set-priority action requires generic get_object VIEW then CONVERSATIONS.UPDATE; serializer choice is exactly low/normal/high/urgent and only priority is submitted. Local support is separate synthetic actor+UPDATE and fake command with independent raw source GET; no default chosen from unknown source. Plain200 scope/priority echo is fixture data and never a bounded Inbox result or recovery proof. Unknown keeps input+attempt and all conversation sibling barriers; reread/actor/Business/epoch changes do not release it. Current414 native checks remain NOT_RUN at preserved dataless harness/cache inputs; last403 Swift PASS is historical. Actual server/permission/auth/durable/device/release acceptance stays separate.


### Source416 bounded lifecycle boundary (documentation417)

Local support is explicit fake close with omitted optional reason and fake reopen, both{}. Existing generic source requires get_object VIEW then CONVERSATIONS.UPDATE; independent synthetic UPDATE/actor context is separate from GET and other grants. Plain200 projection validates provided status/booleans; close_reason is absent from InboxConversationSerializer and cannot be echoed or recovered. Reopen never implies a bot enable/handoff reset. Actual server creates SYSTEM outbound SENT rows for both actions; no such command or message occurs locally. Unknown retains original actor/source/action/omission/body+attempt and all conversation peer barriers; matching status or reread is not outcome proof. Typed reason form is separately dependent on exact library CharField semantics, without install/hydration/guess.

Current416 native and Android checks are NOT_RUN at preserved dataless inputs; last403 Swift PASS is historical. Actual lifecycle, current grant/auth, durable recovery, device and release remain unaccepted.


### Source418 qualified Client linking (documentation419)

Local Inbox linking uses a separately injected fake-only port. Existing generic POST source is get_object VIEW then CLIENTS.UPDATE plus object CONVERSATIONS.UPDATE; required client_id must resolve within the same Business. No active/archive/member filter, idempotency/version/recovery or Client DTO is invented. Generic conversation GET and existing mobile Client Search/Profile GET adapters remain separate from synthetic authority and command execution. Current query window and independently resolved profile are required before explicit Use/review. Plain200 validates captured selected client; it does not mutate bounded mobile Inbox/thread/Client state. Unknown retains source/raw input/candidate/body/attempt and blocks peers; matching GET cannot establish outcome or permit retry.

Current418 Swift Core/host/all97 App checks and Android compile/JUnit are NOT_RUN at preserved dataless inputs. PBX plutil and independent Python fixture expectations are static evidence only. Native source403 is historical, current server grants/auth, actual POST, durable recovery, device and release remain unaccepted.


### Source420 Lead read boundary (documentation421)

The new separate read adapter consumes existing /api/mobile/v1/leads/ with explicit Business+limit50+search and independent /api/mobile/v1/leads/{id}/ with Business. Both use existing VIEW scope+unarchived source; this is not synthetic command authority or an added generic link-lead restriction. The bounded projection requires envelope Business and correlated positive item client_id/nested client.id. It does not substitute generic LeadSerializer business/client fields, claim full message from200/1000 previews, follow href or invent updated_at/version. Local qualified reference requires current query window and independent matching profile; captured visits/tickets protect raw input/selection across late reads/Back/cancel/scope changes.

The panel has no command port. Linking is the next independent fake-only step with LEADS.UPDATE plus CONVERSATIONS.UPDATE, exact lead_id and a conditional client effect: preserve an original nonnull client, otherwise fill selected Lead client. No real POST/current grants/auth/durable recovery/device/release acceptance. Current420 Core/host/all99 App and Android compile/JUnit are NOT_RUN; Python fixture expectations and PBX lint are static evidence only.


### Source422 separate fake Lead link (documentation423)

Existing generic link-lead requires get_object VIEW then LEADS.UPDATE and object CONVERSATIONS.UPDATE, required lead_id from the same Business, and returns plain200 InboxConversationSerializer. Source sets lead and fills client from Lead only if original conversation.client is null. Local receipt validates this exact conditional effect; it must preserve a preexisting different Client. Mobile qualified Lead GET and its unarchived VIEW subset are separate from generic command authority. No live POST, current grant, lifecycle/version/idempotency/recovery semantics are inferred. Frozen original source/qualified ref/raw query/body/attempt survives unknown; matching Lead/Client GET cannot establish outcome, release a peer barrier or permit retry. Known response acknowledgement requires new explicit reads, without bounded Inbox/Client/Lead patch.

Current422 Swift Core/host/all101 App and Android compile/JUnit remain NOT_RUN at preserved dataless inputs. Static Python fixture expectations/PBX lint are not runtime/current/device acceptance. Next generic Deal candidate read must validate returned Business and exact nullable Lead before any separate fake-only link-deal command.


### Source424 generic Deal read boundary (documentation425)

A separate optional adapter reads existing GET /api/deals/{id}/ with empty query from an explicitly supplied id. It validates returned Business AND id against the captured owner before exposing a narrow generic DealSerializer projection: client is required positive, lead required nullable, title/updated_at remain raw read data. No mobile alias/DTO/selected-Business business query or catalogue is invented. Sensitive amount/currency/notes/lost_reason are not retained or inferred; GET does not grant UPDATE or prove current auth. Native input grammar/visits/request tickets are local controls only. Use qualifies a read-only reference; input changes, clear/hide/late work/cancellation/Business ABA invalidate it without any linking/unlinking.

Current424 Core/host/all103 App and Android compile/JUnit are NOT_RUN at preserved dataless inputs. Python fixture expectations/PBX lint are static only. Next fake link-deal requires separate DEALS.UPDATE plus CONVERSATIONS.UPDATE and exact source conditional Client/Lead preservation/fill; unknown cannot recover from matching GET. Actual POST/current grants/durable recovery/device/release remain unaccepted.


### Source426 separate fake Deal link (documentation427)

Existing generic link-deal uses get_object VIEW, DEALS.UPDATE and object CONVERSATIONS.UPDATE, required same-Business deal_id, and plain200 InboxConversationSerializer. It sets deal, fills Client only if original Client null, and fills Lead only if original Lead null and Deal.lead nonnull. Local fake receipt validates exactly those effects, preserving existing different relations and nullable absence. No additional Client/Lead UPDATE grants or Deal mobile DTO/catalogue, defaults, version/idempotency/recovery semantics are invented. Conversation GET, qualified generic Deal GET and synthetic command context are separate. Frozen source/input/ref/body/attempt survives unknown and blocks all peers; matching links via GET cannot establish outcome/release/retry. Known response never patches bounded state and requires fresh reads after acknowledgement.

Three previous own Lead check JSON literals were corrected to structured builders under the new journal, without rewriting old source422 evidence. Current426 Core/host/all105 App and Android compile/JUnit remain NOT_RUN at preserved dataless inputs; Python expectations/source guards/PBX lint are static only. Next selected-user assign requires an exact qualified Business member read, separate MANAGE context and active target membership; omitted/null user_id is self-assignment, not clear. Actual commands/current grants/auth/durable recovery/device/release remain unaccepted.


### Source428 Team member detail boundary (documentation429)

Existing /api/team/members/{membership_id}/ GET uses TEAM VIEW accessible-business scope and returns TeamMemberManagementSerializer with nested TeamUserSerializer. Native read validates response record id and selected Business, reuses only nested MobileUserItem id/email/full_name, and distinguishes record id from User id. Required strict BusinessMember.is_active is an observation; inactive source is readable but cannot qualify. User role/is_active/flat user_id cannot replace this flag or confer MANAGE/target-active command authority. No catalogue, selected-Business business query or new User/Member API/DTO is inferred.

A local qualified reference captures current read/owner/raw number and is invalidated by edits, clear/hide, late/cancel/Business ABA. It performs no assignment/team mutation. Next separate fake command must independently receive MANAGE actor and target active-membership context and send positive source.user.id only; null/omitted user_id is existing self-assignment, not clear. Current428 Core/host/all107 App and Android compile/JUnit remain NOT_RUN. Python expectations/PBX lint are static only; actual current permissions/membership freshness/POST/durable recovery/device/release remain unaccepted.


### Source430 selected-user assign boundary (documentation431)

Existing /api/inbox/conversations/{id}/assign/ accepts user_id optionally/null for self behavior. Native selected-target subset always prepares only positive qualified member.source.user.id, with empty query/headers, through an explicit synthetic port. Membership record id is retained separately and never sent as User id. Existing self-assignment is separate. Required synthetic CONVERSATIONS.MANAGE actor and separately injected Business/User active-member context cannot be derived from GET is_active, role, account flags or other commands.

Generic conversation GET requires scoped id/business/nullable numeric assigned_to/raw updated_at. Plain200 synthetic reply must echo selected User. No thread/list/bot/handoff mutation, actual server assignment, current membership/permission/lease/idempotency/recovery claim exists. Review/pending freeze input/ref, Back retains them, known response acknowledgement requires fresh independent reads; unknown retains source/input/ref/body/attempt across all peer commands/ABA and matching rereads never prove/release/retry it. Current430 Core/host/all109 App and Android remain NOT_RUN. Next source audit covers separate create-task endpoint omitted-field subset/TASKS.CREATE/plain201 Task response; typed text/date semantics remain independently dependent.


### Source432 conversation task input read boundary (documentation433)

The existing create-task action copies conversation Client/Lead, so the optional native read/reference now requires both exact nullable fields from generic conversation GET, plus scoped id/business/raw updated_at; bounded aliases, assigned_to/member/link DTOs and other task endpoints do not supply this input. Explicit Read then Capture qualifies only the current owner/read result, invalidated on reread/hide/failure/cancel/scope change/late responses. No TASKS.CREATE, Task DTO/task creation/server title/date/default is inferred. Current432 Swift Core/host/all111 App and Android remain NOT_RUN. Next fake {} command must independently inject TASKS.CREATE actor, freeze this source and use the exact plain201 TaskSerializer receipt without reconstructing generated title, patching bounded state or recovering unknown through rereads.


### Source434 / documentation435: separate fake omitted-field task creation from Inbox

Only prepared /api/inbox/conversations/{id}/create-task/ with empty {} body/query/headers. Required separately injected TASKS.CREATE actor and current explicit QualifiedInboxTaskSource capture; no grant from GET/other task endpoints or added CONVERSATIONS.UPDATE assumption. Existing action copies Client/Lead and actor assignee/created_by; omitted description empty, priority normal and due_at null are checked from exact source, never supplied in UI. Plain201 result uses existing TaskSerializer id/business/raw observed nonempty title/description/nullable links/assignee/created_by/priority/due_at/raw updated_at lens. Title is not reconstructed; positive returned Task id is not proof of global newness and may equal a conversation id in a different namespace.

Read/capture then review, source freeze during review/pending, Back preserves capture; known response acknowledgement requires fresh independent source read/capture and retains attempt history. No bounded Inbox/task list/bot/handoff patch. Missing port/CREATE/current capture fails closed. Unknown/cancelled/failed/invalid/late retains original source/read/body/actor/attempt across actor/epoch/Business ABA and every peer; unchanged conversation reread or matching Task result never reconciles/releases/retries unknown. Three links/selected-user/self-assignment/reply/handoff/retry/markers/priority/lifecycle share barriers. Typed title/description/DateTime editors and actual POST/current/device remain independently dependent. Current434 Swift Core/host/all113 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source436 / documentation437: separate fake existing-client early return from Inbox

Prepared /api/inbox/conversations/{id}/create-client/ only through an explicit separate synthetic port, empty {} body/query/headers. Generic conversation client-only projection/repository is reused without link-client picker/grants/command. Required positive observed existing source.client and independently injected CLIENTS.CREATE AND CONVERSATIONS.UPDATE actor; null source cannot enter a new-client branch. Plain200 wrapper requires strict created=false and empty duplicates, scoped nested Client id/business and raw full_name/phone/email/updated_at identity only; annotation/count/manager/is_active/role/permission fields are not retained or defaulted. The selected existing-only subset expects the confirmation marker absent and never defaults it false; confirmation/new/duplicate/force branches are unavailable or unknown. No typed contact/name/email coercion or normalization is invented.

Explicit generic read/review with original source/raw updated_at/actor/body/attempt freeze through review/pending; Back preserves source. Known synthetic response acknowledgement clears source for fresh explicit GET and retains history. No bounded Inbox/Client/Task list or relationship patch and no actual creation claim. Unknown/cancelled/failed/invalid/late preserves original source/body/attempt across actor/epoch/Business ABA and all commands; matching Client or conversation reread never proves/reconciles/releases/retries. Task creation, selected-user/self-assignment, three links, reply/handoff/retry/markers/priority/lifecycle all share barriers. New-client/duplicate confirmation/force branches and typed editors/current/device remain separately dependent. Current436 Swift Core/host/all115 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source438 / documentation439: separate fake existing-Lead early return from Inbox

Prepared /api/inbox/conversations/{id}/create-lead/ only through an explicit separate synthetic port, empty {} body/query/headers and no typed message/default. Generic Lead/Client source/repository aliases are reused without link-lead/mobile catalogue/detail/picker/grants. Positive existing conversation.lead plus independent LEADS.CREATE AND CONVERSATIONS.UPDATE actor are mandatory; null Lead does not enter pipeline/new creation. Plain200 direct LeadSerializer id+Business must match source, required positive Lead.client may differ from source.client or source.client may be null. Raw message allows blank and updated_at stays raw; no invented title/status=new/responsible_user=actor/current membership or other fields retained. No conversation Client fill/reset or real result claim.

Explicit read/review freezes original Lead/Client source/raw timestamp/actor/body/attempt during review/pending; Back preserves source. Known response ack clears source for fresh read and preserves history. No bounded Inbox/Lead/Client/Task list/relationship patch. Unknown/cancelled/failed/invalid/late retains the original attempt across actor/epoch/Business ABA and all peers; matching Lead/conversation GET or late matching reply cannot prove/reconcile/release/retry. Existing Client and Task create, selected-user/self-assignment, three links, reply/handoff/retry/markers/priority/lifecycle share barriers. Plain201 pipeline/new Lead, typed message CharField/AI/current/device remain independently dependent. Current438 Swift Core/host/all117 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source440 / documentation441: separate fake existing-Deal early return from Inbox

Prepared /api/inbox/conversations/{id}/create-deal/ only through an explicit separate synthetic port, empty {} body/query/headers; title/amount/currency omitted without local defaults. Generic three-link source/repository aliases are reused without link-deal authority/picker or catalogue DTO. Positive existing conversation.deal plus independent DEALS.CREATE AND CONVERSATIONS.UPDATE actor are mandatory; null Deal does not enter pipeline/new creation. Plain200 direct DealSerializer narrow result requires matching id/Business, required positive Deal.client and required nullable Deal.lead; neither must equal original conversation Client/Lead, and early return fills/resets neither. Raw title (blank accepted as observation) and updated_at retained only; financial/currency/notes/lost_reason/SLA/owner/status are excluded, no field-mask/default/actor/current permission inference. Existing server serializer/request-context policy remains outside local acceptance; no server/security changes made.

Explicit read/review freezes original Deal/Client/Lead source/raw timestamp/actor/body/attempt through review/pending; Back preserves source. Known response ack clears source for fresh explicit GET and preserves history. No bounded Inbox/Deal/Client/Lead/Task list or relationship patch. Unknown/cancelled/failed/invalid/late preserves original attempt across actor/epoch/Business ABA and all peers; matching Deal/conversation GET or late matching reply cannot prove/reconcile/release/retry. Existing Lead/Client and Task create, selected-user/self-assignment, three links, reply/handoff/retry/markers/priority/lifecycle share barriers. Pipeline201/new Deal/Lead/client/AI and typed CharField/Decimal/currency editors/current/device remain independently dependent. Current440 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source442 / documentation443: paired identifier field error association

Existing nonempty raw ASCII positive Int32 identifier grammar, input generation/context/tickets, leading zeros, explicit GET/Use and localized copy remain unchanged. Swift field keeps its label/raw value and adds conditional invalid hint; visual error text remains visible but AX-hidden to avoid duplicate speech. Compose field uses the already present project Material3 isError/supportingText polite-error pattern; the independent standalone error node is removed. No new SDK/dependency/keyboard filtering or default input.

Exact inverse presenter comparison proves only error association changed; isCurrent/controlsBlocked/disabled/read/use/update/clear controls, owner/tickets/late/cancel/Business ABA and all pending/review/unknown command barriers are byte-preserved. Existing meaningful input/stale/freeze/cancel/ABA fixtures remain prepared; no implementation-mirroring tests added. VoiceOver/TalkBack/IME/human language/device and native execution remain NOT_RUN, readiness unchanged. Current442 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source444 / documentation445: paired source-scoped read-state accessibility names

Existing generic read state and localized copy only. Swift ProgressView keeps visible loading label and adds source-scoped accessibilityLabel; error Text keeps visible reason/updatesFrequently and adds the source+reason name. Compose preserves default progress semantics and adds owning source contentDescription; error Text preserves visible reason/polite region and gains the same contextual description. Lead list/search and selected detail use existing selectedID to distinguish scope, never raw query/hidden data. Existing unedited local accessibilityLabel/contentDescription patterns are reused, no SDK/dependency added.

Exact inverse comparison removes only scope names and accessibility modifiers to reproduce all8 presenters byte-for-byte. Read/use/retry/update/clear/back, values/reasons, label roles/progress state, isCurrent/controlsBlocked/disabled, owner/input/async ticket guards and pending/review/unknown history remain unchanged. No auto GET/retry/Use, API/DTO/permissions/default/model changes or new implementation-mirroring tests. Native/VoiceOver/TalkBack/IME/device/human language/current acceptance NOT_RUN; readiness unchanged. Current444 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source446 / documentation447: paired source context for generic read-panel button names

Existing readScope from444 and existing searchClear/searchSubmit/retry/back localized copy build button accessibility names. Swift adds accessibilityLabel to the Button and Compose adds contentDescription semantics to TextButton. Visible labels/child Text and default button roles remain. Member/Deal scope uses existing source title; Lead list uses search context and selected detail uses existing selectedID. No raw query or new source data is added. Read-only GET retry is unchanged and never described as command recovery.

Exact inverse removes only added accessibility modifiers to reproduce all6 original presenters byte-for-byte, including enabled/disabled, isCurrent/controlsBlocked, read/input/control/selected id captures and commands/unknown history. Models, fixtures, copy, API/DTO/grants and dependencies unchanged. Native/VoiceOver/TalkBack/IME/device/human-language/current acceptance NOT_RUN; readiness unchanged. Current446 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source448 / documentation449: paired Client Directory search-list accessibility context

Use existing clients plus clientServerSearch localized labels: the latter alone is generic search-on-server in RU. Swift ProgressView/error Text and three Buttons add source-scoped accessibilityLabel while retaining visible text/updatesFrequently/default roles. Compose preserves progress and polite error semantics and adds scoped contentDescription; three buttons retain visible child Text/default roles. Scope never contains query, phone, profile id, business or hidden data. No copy/SDK dependency added.

Removing only source-scope definitions and accessibility modifiers reproduces both presenters byte-for-byte. Query input/IME/onSubmit and ownsInput/ownsControl/control/selection, search/clear/retry/row-open callbacks, partial/empty/count/result values and profile destination remain identical. Back stays unchanged because Android can return selected profile/work. No automatic search/retry, GET/command/model/grant changes, new or repeated behavior tests. Native/VoiceOver/TalkBack/IME/device/human-language/current acceptance NOT_RUN; readiness unchanged. Current448 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source450 / documentation451: paired Client profile loading/error/retry accessibility context

Existing clients plus details labels scope Swift outer stale-route and inner loading ProgressViews, error Text and both error/empty retry Buttons; Kotlin loading/error and both retry Buttons use same static context. Visible values/reasons and existing default roles, progress and polite error semantics are preserved. No id/name/phone/email/notes/business/query/fetched relation data is added to names. No new localized copy/SDK/dependency.

Exact inverse removes only scope definitions and accessibility modifiers to reproduce both original presenters byte-for-byte, including isCurrent/current/readSelection/scopeEpoch/localOverlayVisit/work/edit/merge and child visibility, onRetry callback/model fallback and error/empty retry conditions. No automatic retries, command recovery, model/fixture/grant/API changes, additional behavior tests or native/device/current acceptance. Readiness unchanged. Current450 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source452 / documentation453: paired Directory Business bootstrap versus Client list accessibility context

Existing clients/business labels scope bootstrap failure/retry while clients scopes list failure/retry and common loading. Server-search entry uses clients+clientServerSearch copy. Swift accessibilityLabel and Compose contentDescription preserve visible labels/default roles/progress and existing polite error semantics. Names contain no Business/client id/name/raw query or fetched relation data. No locale/SDK additions.

Removing only static scope definitions and accessibility modifiers reproduces both presenters byte-for-byte. Bootstrap agenda.start remains distinct from guarded model.retry/retryList; list/epoch/current/control/selected/profile/overlay/merge/work/edit/Back and auto-load ownership remain exact. Existing callbacks/default roles/disabled/input/result/partial/empty semantics unchanged. No new or repeated behavior tests, models/fixtures/grants/commands/real effects; native/reader/device/current/language acceptance NOT_RUN and readiness unchanged. Current452 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source454 / documentation455: paired nested Client picker parent and read-phase accessibility context

Existing taskDraftTitle+taskDraftClient, bookingTitle+clients and taskClientAction labels identify parent. Selected profile presence chooses existing details versus clientServerSearch phase without exposing id/query/fetched data; whole-picker Cancel uses parent context only. Swift accessibilityLabel and Compose contentDescription retain visible values/reasons, default roles/progress, existing error mappings/traits/live regions, source-specific Use labels and all bindings. No locale/SDK/dependency additions.

Removing only static scope definitions and accessibility modifiers reproduces all6 original presenters byte-for-byte. Task Client outer edit/review/clear/unknown sections separately compare byte-for-byte unchanged. Owner/control/input/parent/child captures, raw query, selected valid identity, disabled/loading/current/freeze/ABA barriers, counts/partial/empty/row selection and all search/retry/Use/Back/Cancel callbacks remain exact. No auto read/retry/confirm, real booking, model/fixture/API/grant/default changes or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current454 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source456 / documentation457: paired Task draft Appointment and Parent picker accessibility context

Existing taskDraftTitle+taskDraftAppointment/taskDraftParent labels identify parent/relation. Existing details label is appended only for selectedID presence, without id/title/day/query/fetched data; Cancel uses whole-picker parent/relation scope. Swift accessibilityLabel and Compose contentDescription preserve visible labels/default roles/progress and existing error mapping/traits/polite regions. No Client server-search label or Task text-search/cursor/default date is added. Source-specific load/Use labels unchanged.

Removing only scope definitions/accessibility modifiers reproduces all4 original presenters byte-for-byte, including day input/hint/validation/read.canRead, owner/control/input/current/loading/disabled/selection validity/freeze/ABA guards, count/partial/empty/rows and read/retry/Back/cancel/Use callbacks. No auto read/retry/confirm, models/fixtures/API/grants/commands/SDK changes or real booking. No new/repeated behavior tests for reversible presenter-only changes; native/reader/device/IME/current/language acceptance NOT_RUN and readiness unchanged. Current456 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source458 / documentation459: paired Task Appointment relation-edit private read picker accessibility context

Existing taskAppointmentAction label scopes private read states and generic read actions; existing details is appended only for selectedID presence. Names contain no id/title/day/raw input/fetched data. Swift accessibilityLabel and Compose contentDescription retain visible labels/reasons, native roles/progress, TaskAppointmentReadFeedback mapping and existing traits/polite regions. No Client server-search label, text-search/cursor/default date, locale/SDK/dependency added.

Removing only readScope/accessibility modifiers exactly reproduces both original presenters. Explicit prefix comparison proves outer edit/review/clear/destructive confirmation/fake pending/rejected/confirmed/unknown/ack/Back controls byte-identical. Private raw day/hint/validation/canRead, parent/child/input/current/set/loading/freeze/ABA guards, choice validity/rows/counts/partial/empty and all read/retry/Back/Use callbacks unchanged. No auto read/retry/confirm or real booking/model/fixture/API/grant/command changes. No new/repeated behavior tests for reversible presenter edits; native/reader/device/IME/current/language acceptance NOT_RUN and readiness unchanged. Current458 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source460 / documentation461: paired Task Business bootstrap, list and detail accessibility context

Existing tasks label scopes common/list loading/error/failure+empty retry; tasks+business scopes bootstrap failure/retry; tasks+details scopes detail loading/error/retry. Static copy only with no Business/task id/title/query/fetched/private data. Swift accessibilityLabel and Compose contentDescription preserve visible values/reasons/default roles/progress and polite regions. Kotlin detail gets separate accessibility modifier with same role/region/branch condition.

Removing scope definitions/accessibility modifiers and reversing the accessibility-only detailProgress split exactly reproduces both Task presenters. Separate comparisons preserve Swift child routes/taskActions and Kotlin rendered fake-command detail block. Status/due filters/local query/limited windows/results/current/control/querySelection/detailSelection/epoch, auto-load effects, all retry callbacks, child observation/guards/ledgers/unknown and layered Back unchanged. No model/fixture/copy/API/grant/SDK/default/text-search/cursor changes or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current460 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source462 / documentation463: paired Task and Inbox read-only file-metadata accessibility context

Existing taskFileMetadata/inboxFilesTitle/inboxMessageFilesTitle scope metadata states and actions; selected-file Back adds details, message whole-window loading uses inboxMessageReadTitle. No file name/id/URL/business/message/task/query/fetched data added to names. Swift accessibilityLabel and Compose contentDescription preserve visible text/reasons, existing traits/polite regions and default roles. Task Kotlin loading remains Text. fileVerificationUnknown and all file values/projections/windows remain unchanged; no content download/open/upload/verification or capability claim.

Removing only static scope definitions/accessibility modifiers exactly reproduces all6 original presenters. Task inline ViewModel, Swift Conversation routes/command sections, Kotlin private Conversation commands, both Message send-retry review/pending/unknown sections and Swift toolbar close separately compare byte-identical. All current/control/selected/window/observation/pending/disabled/read-freeze/row selection/load/read-retry/Back callbacks unchanged. No model/fixture/copy/API/grant/SDK/port/effect changes or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current462 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source464 / documentation465: paired Notification bootstrap, list and Appointment target accessibility context

Existing notifications static copy scopes common/list loading and list error/failure+empty retry; notifications+business scopes bootstrap; notifications+appointments+details scopes target loading/error/read-retry. Kotlin targetProgress split preserves same conditions/progress role/polite region. No notification/business/target id/text/query/notes/fetched data added. Swift accessibilityLabel and Compose contentDescription preserve visible values/reasons/default roles/regions.

Removing only scope definitions/accessibility modifiers and reversing targetProgress split reproduces both entire presenters byte-for-byte. Card content/DEBUG relative-route editor/provenance/fake read+unread marker commands/ledgers/navigation separately compare unchanged. Category/unread/query/Business/window/marker/current/control/routeControl/epoch/target gating, every openTarget/read-retry callback, auto-load effects and layered Back exact. No model/fixture/copy/API/grant/SDK/default/new-target/mark effect/route acceptance changes or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current464 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source466 / documentation467: paired Agenda and Appointment detail read accessibility context

Existing appointments label scopes common/list loading/failure/failure-partial-day-mismatch-empty retry; appointments+details scopes detail loading/error/read-retry. Static labels only, no date/business/appointment id/title/notes/time/fetched data added. Swift accessibilityLabel and Compose contentDescription preserve visible reasons/values/default roles/traits/polite regions. Existing3 Swift versus2 Kotlin loading branches remain; no new state/counterpart introduced.

Removing scope definitions/accessibility modifiers and reversing detailLoadingStatus split exactly reproduces both original presenters. Separate comparisons preserve Business/date/mode/source-directory controls/detail route, Kotlin date-owner/visit/picker block and loaded fields/booking/lifecycle/relation guards/bridges. Source-day mismatch/partial/empty/raw selected day/timezone/count/rows/control/generation/current/request, every retry callback/auto-load/scroll/Back effect unchanged. No default-date/input/model/fixture/API/grant/SDK/booking effect or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current466 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source468 / documentation469: paired Service and Resource directory read accessibility context

Existing services/resources labels identify owner; details is appended only for selected presence without Business/item id/name/type/price/fetched data. Swift accessibilityLabel and Compose contentDescription preserve default progress roles, visible reasons and existing failure traits/polite regions. Compose adds only existing SDK contentDescription import, no dependency. Selected-detail no-retry/BackToWindow rule remains.

Removing static readScope/accessibility modifiers and2 existing-SDK imports exactly reproduces all4 original presenters. Access routes/fields/choice/caller-use/window/Refresh/Close/BackToWindow/owner readonly boundary separately compare unchanged. All control/current/selected/presentation/owner/active/unknown-type/observed-change/read-bridge guards/callbacks exact. No model/fixture/copy/API/grant/default/type/price/booking effect or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current468 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source470 / documentation471: paired Home bootstrap, Home summary and Today read accessibility context

Existing home+business labels scope bootstrap, home scopes summary and home+today scopes Today. No Business/day/id/title/counter/fetched data added to names. Swift accessibilityLabel retains ProgressView roles; Compose contentDescription retains loading Text and existing polite announcements. Visible values/reasons/headers/combined child semantics unchanged.

Removing only static scope definitions/accessibility modifiers exactly reproduces both original presenters. Home counters, Today optional windows/dates/counters/rows/combined-or-merged children, navigation and clock/owner auto-load separately compare byte-identical. Independent agenda.start/reloadHome/reloadToday callbacks, homeControl/todayControl/navigation/Business/epoch/owner/disabled guards exact. No aggregation/date/time/default/model/fixture/copy/API/grant/SDK/navigation/effect changes or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current470 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source472 / documentation473: paired Attention bootstrap, list and typed read-target accessibility context

Existing attention scopes common/list, attention+business bootstrap and attention+details detail. Kotlin detailProgress split preserves same progress role/polite region/branch conditions. No entity kind/id/title/Business/query/count/fetched data added to names. Swift accessibilityLabel and Compose contentDescription retain visible reasons/values and roles/regions.

Removing static scope definitions/accessibility modifiers and reversing detailProgress split exactly reproduces both entire presenters. Row kind/fields/combined semantics, typed stableKey/identity/readTarget conditional clickability and target renderer/navigation/Back/auto-load separately compare unchanged. Query/ownerBusiness/Business/epoch/current/control/ownsAgenda/count/limit/windowCapped/partial/empty/scroll and every read-retry/open callback exact. No new targets/route claims/row grants/model/fixture/copy/API/SDK/default/effect changes or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current472 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source474 / documentation475: paired loaded-only Search stale-feed, list and detail accessibility context

Existing inboxSearch+searchLoadedOnly labels scope stale-feed/list placeholder and appended details scopes non-Client detail/error/read-retry and Swift stale-detail placeholder. Existing3 Swift vs2 Kotlin loading branches retained; Kotlin detailProgress split preserves same role/polite region/condition. No kind/id/title/query/day/count/Business/fetched/private data added to names. No remote search/refresh/cursor/new-feed claim.

Removing scope definitions/accessibility modifiers and reversing detailProgress split exactly reproduces both original presenters. Feed kind/coverage/day/order/hits/typed keys/clickability/sourceTab/openSource rows, ClientProfileContent onRetry/isCurrent delegation, target renderer/navigation/Back/workReturn/list scroll/input-control lines separately compare unchanged. Raw query/empty-on-stale/feed/source token/Business/epoch/control/isCurrentFeed guards and callbacks exact. No default/model/fixture/copy/API/grant/SDK/effect changes or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current474 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source476 / documentation477: paired Inbox bootstrap, list, thread and linked-Client read accessibility context

Existing inbox list/common, inbox+business bootstrap, inbox+details thread and inbox+senderClient+details linked-Client wrapper labels scope read states. Kotlin threadProgress/clientProgress split preserves existing roles/polite regions/conditions. No conversation/message/client id/title/query/notes/content/fetched data inserted. Swift accessibilityLabel and Compose contentDescription preserve visible values/reasons/default roles/regions.

Removing scope definitions/accessibility modifiers and reversing progress splits exactly reproduces all3 original presenters. Reply/handoff/Client root routes, file/message/handoff thread routes, payload/source-state/command-entry/freeze blocks, observers, ClientProfile delegation and layered root/file/message/handoff/reply/Client/work Back separately compare unchanged. Captured listInput/listControl/threadRetry/threadSelection/Business/epoch/current/inspector/presentation/return/work controls and read callbacks exact. No relabeling command send-retry, model/fixture/copy/API/grant/SDK/default/send/lifecycle/effect changes or extra behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current476 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source478 / documentation479: paired ClientWork predefined relation-target detail accessibility context

Existing clients and existing title(target)/title key map only predefined tasks/inbox/appointments labels, adding details; original enum title mapping remains byte-identical and ignores associated ids. No target id/row title/Business/notes/date/fetched data inserted. Swift accessibilityLabel and Compose contentDescription retain visible title/reason/default roles/polite region.

Removing only readScope/accessibility modifiers exactly reproduces both entire presenters. Original title mapper/all ClientWorkLinks/window count-vs-limit/optional rows/open callbacks, parent ClientProfileBody delegation/navigation/owns guards, target renderer/timezone/presentation/selected lines separately compare unchanged. Captured presentation and work.retry/current/parent-read guards exact. No target/relation authority/full-window/model/fixture/copy/API/grant/SDK/default/effect/Client-command change or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current478 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source480 / documentation481: paired Appointment parent-read versus related Task detail accessibility context

Existing appointments+tasks+details scopes Task child loading/error/read-retry and appointments+details scopes parent onRetryParent button. Static labels only, no associated client/task/appointment id/title/Business/date/price/notes/fetched data added. Visible titles/reasons/default roles/traits/polite regions retained. Parent retry remains distinct from child links.retry without recovery or parent refresh effect claim.

Removing scopes/accessibility modifiers exactly reproduces both original presenters. Linked Client ambiguity/reference links/Task payload-budget window/optional rows/open callbacks, ClientProfile/Service-Resource reference delegates, renderer/timezone/navigation/owns guards/booking bridges separately compare unchanged. Parent onRetryParent and child links.retry callbacks/captures/conditions exact. No new targets/relation authority/model/fixture/copy/API/grant/SDK/default/booking effect or extra behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current480 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source482 / documentation483: paired Appointment Service and Resource reference read accessibility context

Existing appointments + existing service/referenceResourceTitle kind ternary + details labels scope only three read states/actions. No service/resource/appointment id/name/type/activity/Business/price/date/fetched data inserted. Swift accessibilityLabel and Compose contentDescription retain visible kind header/reasons, updatesFrequently/default progress roles and polite regions. No booking proof/new kind claim.

Removing only readScope/accessibility modifiers exactly reproduces both original presenters. Loaded name/activity/resource type/readOnly/referenceNoBookingProof fields, visible kind header and Service-only AppointmentSlotReadContent/isCurrent/bookingBridge/useBookingCandidate delegation/guard lines separately compare unchanged. Kind/target/presentation/current/links.matches and captured read-retry callback exact. No model/fixture/copy/API/grant/SDK/default/effect/booking change or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current482 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source484 / documentation485: paired Appointment slot-read state and whole-flow Back accessibility context

Existing appointments+slotReadTitle labels scope four existing state/action names per platform. No date/zone/time/IDs/names/price/fetched data or booking/availability-proof claim added. Swift accessibilityLabel and Compose contentDescription preserve updatesFrequently/default progress roles/polite region. Generic Back remains only model.close; slotReviewBack remains separate and untouched.

Removing scopes/accessibility modifiers exactly reproduces both entire presenters. Raw day/input visit/id-or-key/resource selection/selected traits/canRead and candidate/review/fields/day/timezone/boundary/bridge/source-specific Back separately compare unchanged. Every current/available/presented/presentation/context/read/review.valid and submit/retry/edit/refresh/select/back/close callback exact. No validation/default/resource/TTL/version/recovery/model/fixture/copy/API/grant/SDK/booking/effect change or extra behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current484 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source486 / documentation487: paired Slot day field feedback from existing public validator

Existing public validDay already enforces raw ASCII/calendar date validity in canRead/intent. UI uses only nonempty raw day failing that predicate, independent of !canRead/resource/context; no trim/format/default/date replacement. Swift preserves Binding/id(input.visit), adds conditional accessibilityHint plus visible error hidden from duplicate reader speech. Compose preserves onValueChange/key(input.visit) and uses existing Material3 isError/supportingText Polite pattern with internal Core import. Existing generic taskDraftAppointmentDayIssue RU/KK/EN text unchanged; original source289 provenance retained with additive Slot trace, human/device review NOT_RUN.

Removing only field-feedback declarations/modifiers/supporting text/internal import exactly reproduces both original presenters. Additive provenance removal restores entire original metadata JSON. All resource/request/close/candidate/review/bridge source after resource heading is byte-identical; Core/model/fixture/copy-text JSON unchanged,12 existing intent cases preserved. Empty/resource-not-chosen cannot be mistaken for invalid day since predicate excludes canRead. No new grammar/default/validation gate/request/grant/API/SDK/booking effect or extra behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current486 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source488 / documentation489: paired Slot candidate choose-button names from visible interval values

Existing slotReviewChoose plus intervalStart/intervalEnd and exact instant(candidate, context timezone) expressions build candidate-row accessibilityLabel/contentDescription only. No new formatter/conversion/default/timezone/data/hold/availability/booking proof. Duplicate intervals may retain identical names; no invented uniqueness/dedupe/reorder. Visible copy/button roles unchanged.

Removing only the candidate-row accessibility modifier reproduces both entire presenters byte-for-byte. Original index/id-offset/control/selectCandidate callback, source arrays/context/read/review/current/availability guards, visible fields/date feedback/formatter/review boundaries and booking bridge unchanged. Each name reuses exactly the two formatter expressions already rendered in that same row. No copy/model/fixture/API/grant/SDK/effect changes or additional behavior tests. Native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current488 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source490 / documentation491: paired Task draft existing field-issue reader association

No new validation or command contract. Existing issue mappings, limits, date policy, raw values/inputControl and issue-show timing are unchanged. Swift existing text-field hints remain; Priority Picker adds conditional issue(.priority) hint. Compose four existing Material3 fields stay byte-identical; standalone Priority error adds existing label and Polite semantics only. No new copy/SDK APIs.

Removing only five Swift error-row accessibilityHidden modifiers and Priority hint, and reversing only contextual polite Compose Priority error, reproduces both entire presenters byte-for-byte. All raw bindings/fields/focus policy/enums/default/menu/input/current guards, due/reminder modes, review/submit/ack/pending/unknown/clear-confirmation/Back and child picker callbacks/records preserved. Models/core/ports/fixtures/copy unchanged. No behavior tests added/rerun; native/reader/device/IME/current/language acceptance NOT_RUN; readiness unchanged. Current490 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source492 / documentation493: paired Client draft existing field-issue reader association

Existing issue(field) mappings/timing/validation/limits/raw values only. Swift all existing text-field hints and iOS/macOS phone/email branches retained; Source Picker adds conditional issue(.source) hint. Compose standalone Source error adds existing field label and Polite semantics only, no error in button name/new SDK APIs. No copy/model/contract changes.

Exact whole-presenter inverse removes only five Swift error-row hidden modifiers and Source hint, and reverses only Compose contextual polite Source error. Four-field loop/bindings/keyboard/focus, source labels/enums/default/menu/input/current guards, duplicate-preview read/control/clear guard, review/fake-submit/ack/pending/unknown/clear-confirmation/Back callbacks and records preserved. No native/reader/device/IME/current/language acceptance or readiness promotion. Current492 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source494 / documentation495: paired Client edit existing field-issue reader association

Existing ClientEditValues issues derived from ClientDraftValues excluding notes and current issue(field) only. Swift existing iOS/macOS phone/email branches and hints retained; Source Picker adds conditional issue(.source) hint. Compose existing label(ClientDraftField.SOURCE) and Polite semantics only. No model/validation/raw-value/copy/SDK contract changes.

Removing four Swift error-row hidden modifiers and Source hint, and reversing only contextual polite Compose Source error, reproduces both whole presenters byte-for-byte. Three-field loop/keyboard/error/supportingText/focus, values/bindings/input/current/source enum/labels/default/menu, origin/needsReset/storedChanges/availability, original/modified/no-changes review, cancel/discard confirmation capture/consumption/dismiss/Back unchanged. No POST/PATCH/submit/permission/source/version addition or readiness promotion. Current494 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source496 / documentation497: paired booking existing start-time error association

Exact existing nonempty rawStart and !timeValid predicate. timeValid remains TaskSnoozeValue.parse(rawStart) and microseconds%1000==0. Empty remains neutral. Existing time/error/hint copy already consumed in both presenters; no new copy key/date/parser/normalization/timezone/millisecond/default/focus/model/API/grant/SDK/effect change.

Only Swift conditional error hint/error-row reader-hidden modifier and Compose relocation of identical conditional Polite Text into supportingText. Exact whole-presenter inverse passed. Raw setStart/input visit/id/key/enabled/disabled, child selector/directory/reference reads, candidate/open/review/canReview/summary/submit/ack/pending/unknown/Back ownership/control/records preserved. No real booking result or native/reader/device/IME/current/language acceptance; readiness unchanged. Current496 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source498 / documentation499: paired reschedule existing start-time error association

Existing nonempty rawStart and !timeInputValid only; timeInputValid remains TaskSnoozeValue.parse(rawStart) and microseconds%1000==0. Existing error/hint copy, visible Swift row/updatesFrequently retained. No parser/date/default/normalization/timezone/millisecond/reason/focus/model/copy/API/grant/SDK/effect change.

Exact whole-presenter inverse removes only conditional Swift hint/error-row hidden modifier and reverses relocation of same Compose conditional Polite Text. Raw start/reason/input visit/id/key/enabled/disabled/editing, resource choice/load/failure, reviewReschedule/canReview/review/summary/submit/ack/pending/unknown/terminal receipts/replayed display/Back/control/current/ownership/records remain exact. Fake-only, no real lifecycle acceptance or readiness promotion. Current498 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source500 / documentation501: paired Task snooze existing showsIssue field association

Existing showsIssue follows prepare parser failure and existing transition resets; no eager validation/parser call/date/millisecond/default policy added. Current taskSnoozeInput/taskSnoozeInputIssue copy reused. Raw binding/current/inputControl/singleLine/fillMaxWidth retained. No focus/model/core/port/copy/API/grant/SDK/effect changes.

Exact whole-file inverse removes only Swift conditional showsIssue hint/error hidden modifier and reverses Compose isError and relocation of same conditional Polite Text. Entire inline Swift ViewModel prefix independently byte-identical before inverse; Kotlin model unchanged. Owner business/epoch/raw buffers/attempt/ledger/consumed reads/prepare/review/submit/ack/pending/unknown/clear-confirmation captured raw+visit/Back exact. No retry/recovery or readiness promotion. Current500 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source502 / documentation503: paired Task title edit existing showsIssue field association

Existing TaskTitleValue.parse failure on prepare and issue resets remain unchanged. Current taskTitle/taskTitleEditInputIssue copy reused; no eager validation/parser call/trim/length/character/default/focus policy change. Raw binding/input/current/singleLine/fillMaxWidth retained, models/core/ports/copy/API/SDK unchanged.

Exact whole-file inverse removes only Swift conditional showsIssue hint/error-row hidden modifier and reverses Compose isError and relocation of same conditional Polite Text. Entire inline Swift ViewModel prefix independently byte-identical; Kotlin model unchanged. Owner business/epoch/raw buffers/attempt/ledger/consumed reads/prepare/review/submit/ack/pending/unknown/clear capture raw+visit/Back preserved. No retry/recovery or readiness promotion. Current502 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source504 / documentation505: paired Description issue field association with no-mode fallback

Swift adds existing taskDescriptionEditInputIssue hint to labeled REPLACE TextEditor, retaining visible error/updatesFrequently and hiding separate reader traversal only when mode==replaceText. Compose adds showsIssue isError/supportingText to REPLACE field and keeps standalone same Polite error for showsIssue && mode!=REPLACE including nil. No eager validation, new trim/length/character/default/focus/mode/raw/model/core/SDK policy.

Exact whole-file inverse removes only Swift hint/conditional hidden modifier and reverses Compose field-feedback args/non-REPLACE fallback condition. Inline Swift ViewModel prefix independently byte-identical; Kotlin model unchanged. Editor label/size/minLines/raw binding/input/current, nil/replace/remove choices, raw UTF8 identity/owner epoch/buffers/modes/attempt/ledger/consumed reads/review raw+proposed/submit/ack/pending/unknown/clear capture raw+visit/Back preserved. No retry/recovery or readiness promotion. Current504 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source506 / documentation507: paired Task date issue field association with missing-selection fallback

Swift adds existing taskDateInputIssue conditional hint to current date field; visible global error/updatesFrequently remain and separate reader traversal hidden only for draft.field nonnil && mode==setDate. Compose adds showsIssue isError/same Polite supportingText to SET field and retains standalone error for showsIssue && (field==null || mode!=SET). No eager validation/parser/normalization/default date/focus/model/core/SDK policy.

Exact whole-file inverse removes Swift hint/selected-field+SET reader-hidden modifier and reverses Compose field-feedback args/fallback condition. Inline Swift ViewModel prefix independently byte-identical, Kotlin model unchanged. Due/reminder raw buffers/selected field and mode choices/labels/defaults/input/current/singleLine/width, owner epoch/draft/attempt/ledger/consumed reads/review/submit/ack/pending/unknown/clear captured draft+visit/Back preserved. No retry/recovery or readiness promotion. Current506 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source508 / documentation509: paired-source comment/reply/cancel existing error association

One existing Swift error-row accessibilityHidden(true) per presenter only. Existing visible error text/red style/updatesFrequently and field hints/error mapping/timing remain. Compose existing isError/supportingText/Polite pattern byte-identical; no validation/copy/model/core/SDK/API/permission changes.

Removing only three hidden modifiers recovers all three Swift files exactly. All paired Compose presenters and twelve model/core files match prior hashes. Raw bindings/line limits/focus/prepare focus assignment/routes/current/input/control/review/fake-submit or separate send-port boundaries/ack/pending/unknown/clear-confirmation/Back/ownership/attempt/source buffers/records preserved. No real comment/cancel/send or readiness promotion. Current508 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source510 / documentation511: paired-source Description/date existing selected-state semantics

One Description model.mode==value trait, one date draft.field==option trait and SET/CLEAR draft.mode traits only. Existing visible labels/checkmarks/captions/order/nil-default/no automatic selection remain. Existing accessibilityAddTraits isSelected pattern reused. No copy/validation/default/date/model/core/API/permission/SDK/effect change.

Removing four trait modifiers recovers both Swift files exactly; both inline Swift model prefixes independently unchanged. Two Compose selected FilterChip presenters and six other model/core files match prior hashes. Select/choose callbacks/current/control/input/raw buffers/modes, previous issue-field association and missing-field/mode fallback, attempt/review/submit/ack/pending/unknown/clear/Back preserved. No reader/native/device/current acceptance or readiness promotion. Current510 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source512 / documentation513: paired-source Task relation mode selected-state semantics

Four accessibilityAddTraits modifiers use current draft.mode==set/clear only. Existing visible labels/selected-mode captions/order/nil/no-default selection remain; both Compose SET/CLEAR chips already expose same selection. No model/core/copy/default/API/DTO/permission/SDK/effect changes.

Removing four trait modifiers exactly recovers both entire Swift presenters. Two paired Compose presenters and eight model/core files match prior hashes. Choose/current/control/input/relation draft/validation/client or appointment picker read owner/control/window/query/date/selection/detail/Back routes/source/epoch/attempt/review/fake-submit/ack/pending/unknown/clear capture/Back exact. No real relation update or readiness promotion. Current512 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source514 / documentation515: paired-source Task filter menu selected-state semantics

Status selected predicate uses option==(sourceFiltering ? appliedFilter.status : status); due uses appliedFilter.due==due inside existing sourceFiltering branch. Existing wildcard semantics import/selected property reused. Null All/status order/raw unknown labels/due entries/order/defaults/pending-versus-applied distinction unchanged; no query/model/core/server/clock/date/copy/SDK/permission/effect changes.

Removing exactly two item semantics modifier arguments recovers entire Compose TaskListScreen. Entire Swift bound Picker presenter and six model/core files match prior source hashes. FilterSelection/current/control/previous-status callbacks/menu dismiss/search/query/refresh/clear/list/detail/child draft/commands preserved. No filter requests executed or readiness promotion. Current514 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source516 / documentation517: paired-source Task/Search current business selected-state semantics

Task item uses member.id==scope.business.id in existing scope!=null block; loaded Search uses member.id==business.id in business!=null branch. Existing wildcard semantics import/selected property only. Catalogue order/names/IDs/current display/menu flags/dismiss/nil-defaults unchanged, no new lookup or selection invocation.

Removing one item modifier per Compose file exactly recovers both baseline files. Two paired Swift Picker presenters and six model files retain prior hashes. Exact agenda.load callbacks/day, Search current-business/epoch guard/feed/source coverage/loaded-only query/matches/hit/profile/Back/control, Task previous filter semantics/list/detail/children/commands preserved. No source/authorization/API/model/core/permission/default/day/SDK effect or readiness promotion. Current516 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source518 / documentation519: paired-source six business menu selected-state semantics

Six item semantics modifiers only plus two required explicit imports of existing selected property in Agenda/ClientDirectory; other four use wildcard imports. Immutable Ready516 preserved and import-scope refinement recorded in audit. Agenda compares to nullable current selection ID; Home/current scope menus use existing nonnull business ID. Catalogue order/names/IDs/nil/defaults/rendered labels unchanged. No new SDK API/dependency/version.

Removing six item modifiers and two explicit selected imports recovers all six whole Compose files. Six paired Swift business Picker presenters and two Agenda models match prior hashes. Every menu flag/dismiss/load/switchBusiness callback/day/current/epoch/ownsAgenda/control/availability/bootstrap/read list/query/navigation/target/child command/prior semantics preserved. No business selection invoked or new lookup/source/authorization/API/DTO/permission/model/date/default/effect or readiness promotion. Current518 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source520 / documentation521: paired-source Priority/Source/category selected-state semantics

Task priority raw==state.values.priority, draft Source value==state.values.source, edit Source value==values.source, Notification category option==state.category including null All. Existing wildcard semantics selected property only; labels/order/raw unknown/nil/default/All/no automatic selection unchanged.

Removing four item modifiers recovers four whole Compose files. Four paired Swift files and eight models match prior hashes. Input/menu identity/dismiss/previous-value/current/control/focus/error hints/supportingText/validation, loaded-category filter/route/readMarker/target, all draft/edit review/fake-submit/ack/pending/unknown/duplicate preview/origin/reset/clear/discard/Back exact. No actual selection/filter/command/model/core/ports/copy/permission/API/SDK/default changes. Current520 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source522 / documentation523: handoff rejected prepare publishes visible feedback with raw retained

Existing HandoffDraftSession sets inputError on rejected NUL reason and accepts optional blank; validators and SourceTextTrim unchanged. Original blocked/null/equal-control guard retained; one session.prepare call, sync on either result, visit invalidation only success. Rejection keeps raw/input/control/attempt ledger. No new limits/defaults/normalization/API/permission/real handoff/send.

Exact model replacement inverse and Swift hint/duplicate-error-row inverse passed. Swift model, Compose field feedback, core/fixture unchanged. Optional-reason caption/focus-on-prepare/clear/Back/owner/submit/ack/pending/unknown preserved; no automatic retry or matching-reread recovery. Paired AppChecks/JUnit source regressions use 13 existing shared cases through actual UI models with current versus stale/null prepare, rejected error/raw/input retention, optional blank/corrected explicit prepare, zero attempts/record/port calls. These model regressions are PREPARED NOT_RUN at native gates; readiness unchanged. Current522 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source524 / documentation525: paired Quick reply existing read-state owner context

Five existing state/action templates per platform reuse existing owner and same visible state/error/query.isEmpty-selected empty copy. Existing roles/live regions/visible strings remain. No send/new API/permission/SDK/copy/model/core/fixture/default changes.

Removing readScope variable and five reader-context modifiers per platform recovers both entire presenters. Template rows/title/text/category/channel/insert callback/list IDs/order/query/search/focus/selection/control/input/current/route close/retry/read window/partial/parent draft ownership unchanged. Handoff522 fix and paired prepared regressions retained exactly. Native/reader/device/current/language NOT_RUN; readiness unchanged. Current524 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source526 / documentation527: paired identity preview owner context and existing Kotlin loop closure repair

Existing clientDuplicatePreview/clientMergePreviewTitle plus same visible loading/error/empty/Back/branch-specific action keys only. Normal duplicate action retains owner title without duplication, retry gains context. Rows/matched fields/channels/selected traits/provided-only counts/archive-policy/fixture-only boundary unchanged. No source/DTO/permission/default/hidden-link/count-zero/actual merge/archive/POST/SDK/copy/model/core/fixture changes.

Removing only context variables/reader labels and the single proven missing-loop closure repair recovers all four whole baseline presenters. Baseline and both own edit stages preserved. Inline Kotlin duplicate model prefix and five model/owner files exact. Load/retry/preview/choose/Back/visit/generation/current/owner/mergeEntry/control and failure mapping unchanged. Delimiter guard caught identical unclosed function stack in original and contextual edit; one brace closes candidate loop, matching Swift sibling structure. Guard now passes, but is not Kotlin parser/compile acceptance. Handoff522 fix and prepared regressions retained; readiness unchanged. Current526 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source528 / documentation529: paired selected-user Inbox assignment read-state owner context

Three existing templates per platform reuse same visible loading/error/load strings and exact current error mapping. Swift updatesFrequently and current roles/region policy retained; Kotlin spinner gets contextual contentDescription only. No API/permission/copy/SDK/model/core/ports/default/recovery change.

Removing owner variable and three context modifiers recovers both entire presenters. Four model/core files retain source hashes. Pending/response/rejected/unknown/retained records, original assigned user versus Member membership/user/reference raw values, review/prepare/submit/ack/blocked/Back/enabled/canLoad/source controls and separate fake UPDATE/actor/membership proof/GET boundaries preserved. No actual assignment/read invoked or readiness promotion. Current528 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source530 / documentation531: paired existing Inbox Client/Lead/Deal read-state owner context

Three templates per platform/entity reuse exact existing owner title, loading/error/per-entity Load keys and error mapping. Visible fields/regions/roles/traits unchanged. No creation/link/update/read invocation, new API/DTO/permission/model/core/ports/copy/default/recovery/server success.

Removing only readScope and three reader context modifiers recovers all six whole presenters. Kotlin source-helper prefixes independently exact, twelve model/core hashes unchanged. Original source/absence/Client-versus-Lead/Deal graph IDs/result DTO/rendered fields/omissions/fake boundary/pending/response/rejected/unknown/retained/review/prepare/submit/ack/Back/enabled/canLoad/current/control/actor/reference/grants/attempt/owner preserved. Handoff522 fix/tests and merge526 syntax repair retained; readiness unchanged. Current530 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source532 / documentation533: paired Inbox review Back owner context

Exactly one existing review Back template per platform/flow receives reader name only. Target/existing identity flows reuse current owner scope, create-task uses existing title inline. No new/moved/removed Back or Back/recovery in pending/unknown/blocked branches.

Removing one reader modifier per file recovers all ten presenters; twenty model/core hashes unchanged. Current/control callbacks and DTO/raw/source/reference/actor/membership/graph IDs/omissions/results/review/prepare/submit/ack/pending/unknown/retained/canLoad/read labels/owner/ledger/input/attempt/Back effects preserved. No action/read invocation/API/permission/SDK/copy/model/core/ports/default/version change; readiness unchanged. Current532 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source534 / documentation535: paired Task editor ordinary Back owner context

Exactly two existing model.back(current control) templates per platform/editor receive names only. Visible text/roles/regions/traits and all availability branches unchanged; no pending/unknown/blocked Back or recovery added. Existing modal dismissClear/confirmClear and cancellation labels remain exact.

Removing two modifiers per file recovers ten whole presenters. Five inline Swift model prefixes independently byte-identical, fifteen other model/core files retain hashes. Raw/mode/date buffers/UTF8/selection/input/focus/issue hints/selected traits/validation/current/control/review/submit/ack/pending/unknown/ledger/consumed reads/clear capture/owner/Back effects preserved. No action invocation/API/permission/SDK/copy/model/core/ports/default/version change; readiness unchanged. Current534 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source536 / documentation537: paired Task relation/draft existing Back owner context

Two ordinary relation Back templates or one draft root Back template per platform receive existing title+Back name only. Already-contextualized nested backClient/backAppointment, clear dialog Back/cancel, BackHandler/sheet/returnControl and existing outcome-closing availability unchanged. No new/removed/moved Back or recovery inferred.

Removing only reader modifiers recovers six whole presenters; twelve model/core hashes exact. Fields/focus/hints/selected traits/partial-original policy/child read owner/window/query/day/selection/detail/review/submit/ack/pending/unknown/clear/parent picker/ledger/buffers/omissions/results/callbacks preserve old bytes. No action/read/command/API/DTO/permission/SDK/copy/model/core/default/version changes; readiness unchanged. Current536 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source538 / documentation539: paired Reply/Handoff visible root Back access to existing route

One TextButton per Compose root after current title, existing Back/owner copy, click body identical to existing BackHandler isCurrent guard and typed model.back callback. No new route/control/model effect. Reply quick-reply child early-return unchanged, so no duplicate root Back in child UI. Swift existing toolbar receives owner name only.

Removing one new Compose control or one Swift name modifier recovers four whole presenters. Ten model/core hashes unchanged. Original handlers/sheet/clear-confirmation/returnControl/current/selection/focus/input/raw/optional reason/validation/hints/previews/submit/ack/pending/unknown/record/source/owner/actor/fake ports/ledger/buffers remain exact. Existing outcome close retains attempt; no ack/retry/recovery/cancellation policy added, no actual action invoked. Native/model/reader/device/current/language NOT_RUN, readiness unchanged. Current538 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source540 / documentation541: paired existing form root Back owner context

One existing root toolbar/TextButton per flow/platform receives title+Back name only. Client edit exact confirmation-dismiss else back helper/body retained, other roots retain returnControl callbacks. No new/removed/moved control/availability/Back/cancel/recovery.

Removing names recovers eight whole presenters; sixteen model/core hashes unchanged. Handlers/sheets/captured consent/current/selection/input/focus/errors/enums/origin/reset/stored changes/duplicate preview/review/fake-submit/ack/pending/unknown/clear/discard/attempt/owner/raw/ledger/source/permission/partial-original policies exact. No action/read/command/API/SDK/copy/model/core/ports/default/version change; readiness unchanged. Current540 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source542 / documentation543: paired ordinary booking and lifecycle Back reader names

Two existing ordinary Back templates per presenter receive bookingTitle or appointmentLifecycle plus Back reader names only. Booking retains its injected parent back(control) callback and lifecycle retains its own model.back(expected control). No controls, availability branches, routing, submit or acknowledgement behavior added, removed or moved.

Exact inverse of names recovers all four presenters. Twelve model/core/Agenda owner sources unchanged. Parent entry/child control binding, current guards, private reschedule fields, child selectors, slot candidates, raw time and reason, resources, sibling barriers, review, fake-submit, acknowledgement, receipts, replayed/terminal status, pending/unknown immutable input+attempt and no-blind-retry policies preserved. No GET/command/API/DTO/SDK/copy/model/core/port/default/version change. Prior handoff522 fix/tests, merge526 repair and root538 visible same-route Back retained. Current542 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source544 / documentation545: existing detail/profile Back reader owner names

One semantics argument on each existing Agenda/Tasks/Inbox/Client directory detail Back, using existing detailScope/threadScope/readScope+details copy. Full callbacks, helpers, handlers, availability and child dispatch unchanged.

Four whole Compose inverse comparisons recover baseline; four Swift navigation and ten model hashes unchanged. Agenda date modal, parent controls/epochs/selection/query/filter/input/raw/partial/permission/source and child return/merge/edit/work/list policies preserved. No controls/routes/GET/commands/models/API/copy/default/version added or changed. Handoff522 fix/tests, merge526 repair and root538 Back preserved. Current544 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source546 / documentation547: existing secondary Back reader owner names

Compose Attention/LoadedSearch detail buttons use existing detailScope+Back; ClientSearch existing controls on both platforms use readScope+Back. Notifications Compose capturedBack and Swift relative-route review Back use notifications+Back. No destination/effect or result assertion added.

Six whole-presenter name inverses exact; two Swift navigation files and eight model hashes unchanged. Swift ClientSearch model.close and Compose profile/work-aware model.back remain exact existing contracts. Captured route, current/control/epoch/feed/profile/work/query/scroll/source/permission/partial/input/availability/handler and fake command/unknown policies preserved. No added/removed/moved controls, route, command, GET, model/core/API/copy/default/version changes. All prior fixes/prepared tests and WIP preserved. Current546 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source548 / documentation549: seven paired Task command Back reader names

Sixteen existing ordinary Back templates across fourteen presenters receive action-title+Back names only: Assign two per platform, each other flow one. Existing current guards and model.back(expected control) callbacks retained. Assign dismissClear consent Back untouched.

Exact whole-presenter inverses include all embedded Swift model bodies; seven Kotlin model and fourteen core hashes unchanged. Source/grants/actor/control/input/clear/prepare/review/launchSubmit/fake ports/ack/receipt/sibling/unknown immutable input+attempt/no-blind-retry remain exact. No new/removed/moved controls or availability/routes/GET/commands/API/DTO/permission/copy/model/core/ports/default/version change. Prior fixes/prepared tests/WIP preserved. Current548 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source550 / documentation551: paired Inbox command and existing Swift root Back reader names

Eighteen existing paired ordinary command Back templates receive their own existing title+Back names. Two existing Swift root close toolbar controls receive existing fileScope/windowScope+Back. Compose parent Back already named in546 stays unchanged; no new close control. LinkClient child picker Back excluded.

Exact name inverse recovers ten whole presenters; ten model/ten core hashes match. Already named metadata detail Back, child picker, root close, callbacks/current/control/grants/actor/selection/review/prepare/fake-submit/ack/pending/unknown retained input+attempt/sibling/partial/permission/attachment metadata/ledger remain unchanged. No new/removed/moved controls/availability/routes/GET/commands/API/DTO/copy/model/core/ports/default/version or server result assertion. Prior fixes/prepared tests and all WIP preserved. Current550 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source552 / documentation553: eight paired Task clear-consent dismiss Back reader names

Sixteen existing consent dismiss controls named only. Visible Back text, Swift cancel role, captured question/current guard, modal title/destructive confirm/onDismissRequest/Binding and confirmClear remain byte-identical. Ordinary editor/review Back unchanged.

Sixteen whole-presenter name inverses exact, including embedded Swift models; ten external model/sixteen core hashes match. All consent/source/grant/actor/control/input/partial-original/review/clear/pending/unknown immutable input+attempt policies unchanged. No new/removed/moved controls, modal/focus/availability/recovery/action/read/command/API/copy/model/core/port/default/version change. Prior fixes/prepared tests/WIP and old evidence preserved. Current552 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source554 / documentation555: existing review, selected-client and date Back reader names

Four existing notification review Back templates use own review-title+Back; two selected-client inspector Back controls use inboxLinkTitle+details+Back; one Compose date dismiss Back uses appointments+date+Back. Existing review source, parent/child controls, captured date owner/visit and closeDate callbacks unchanged.

Seven whole-presenter name inverses exact including Swift notification model bodies. Paired Swift Agenda source and six external model/six core hashes match. Review/prepare/submit/ack/grants/ledger/unknown/sibling/date selection/parser/timezone/confirm/input/availability policies preserved; no default date/control/route/action/API/model change. All prior fixes/prepared tests/WIP and old evidence retained. Current554 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source556 / documentation557: two related Task and root consent reader-name blocks

Eight Task clear-confirm controls per platform use existing action titles. ClientDraft/ClientEdit/TaskComment/TaskCancelReason/ReplyDraft/InboxHandoff root consent confirm and dismiss controls use existing own titles and visible question/action copy. All roles, visible text, captured consent and asymmetric guards preserved; explicit ClientEdit sheet consumption order unchanged.

Forty name modifiers inverse exactly to28 whole presenters including embedded Swift models. Twenty-two external model/thirty core hashes unchanged. Ask entries/ordinary Back/confirmation Binding/onDismissRequest/modal/availability/source/grant/actor/control/input/partial-original/pending/unknown immutable input+attempt/ledger and no-blind-retry policies exact. No new controls/routes/focus/modal/clear-discard behavior/GET/command/API/copy/model/core/ports/default/version changes. All prior fixes/prepared tests/WIP/old artifacts retained. Current556 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source558 / documentation559: two related Task and root consent-entry reader-name blocks

Thirty existing consent-entry templates across28 presenters use their own existing titles and visible clear/discard actions. ClientEdit keeps separate askDiscard(entry) and askCancel(control) paths. Task entries keep no-role buttons; root Swift destructive roles remain exact. No consent behavior or outcome promised.

Thirty names inverse exactly to28 whole presenters including embedded Swift models.22 external model/30 core hashes unchanged. Existing entry/form controls, current guards, needsReset/hasStoredChanges/blocked availability, ask callbacks, confirm/dismiss/ordinary Back/modal/Binding/input/source/grant/actor/partial-original/unknown immutable input+attempt/ledger policies exact. No added/moved/removed controls, focus, availability, clear/discard behavior, GET/command/API/copy/model/core/ports/default/version changes. All prior fixes/prepared tests/WIP and old artifacts retained. Current558 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source560 / documentation561: two paired Task and Inbox acknowledgement reader-name blocks

Exactly24 existing templates across18 presenters named only. Task confirmed/rejected and Inbox response/rejected phase gates, isCurrent guards, expected controls/records and callbacks are byte-identical. Pending/unknown still has no acknowledgement control; names do not assert real server success or add retry/recovery semantics.

24 names inverse exactly to18 whole presenters including embedded Swift models;11 external model/28 core hashes unchanged. All source/grant/actor/control/receipt/metadata/review/submit/ledger/sibling/pending/unknown retained input+attempt policies preserved. No new/moved/removed/enabled controls or availability/read/command/API/copy/model/core/ports/default/version change. All prior fixes/prepared tests/WIP and old artifacts retained. Current560 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source562 / documentation563: two paired root and appointment acknowledgement reader-name blocks

Four root flows keep their exact phase-dependent Done/Edit expressions in names and visible text. Booking/lifecycle keep existing Done text; booking invokes injected parent acknowledge(control,record), lifecycle invokes its own model. Existing phase/current/control/record gates remain exact.

Twelve names inverse exactly to12 whole presenters. Paired Agenda2 UI,14 external model/14 core hashes unchanged. Root confirmed/rejected and appointment acceptedFixture/rejectedFixture gates, pending/unknown no-ack barriers, parent entry/child controls, receipts/ledger/raw input/grants/source/actor/sibling policies retained. No new/moved/removed/enabled controls or acknowledgement/retry/recovery/read/command/API/model/core/copy/default/version or actual server-result claim. All prior fixes/prepared tests/WIP and old artifacts preserved. Current562 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source564 / documentation565: two paired Task field and relation acknowledgement reader-name blocks

Five field editors (Title/Description/Date/Priority/Snooze) and two relation editors (Client/Appointment) keep exact confirmed/rejected phase gates, current/control/record callbacks and pending/unknown no-ack barriers. Fourteen existing controls named only; no new acknowledgement semantics or real server result.

Fourteen names inverse exactly to14 whole presenters including embedded Swift models;9 external model/14 core hashes unchanged. Partial-original/SET-CLEAR/raw input/grants/source/actor/sibling/ledger/receipt/confirmation/back policies exact. No new/moved/removed/enabled controls/availability/GET/commands/retry/recovery/API/copy/model/core/ports/default/version change. All prior fixes/prepared tests/WIP/old artifacts retained. Current564 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source566 / documentation567: two paired Inbox link/create/existing/target acknowledgement reader-name blocks

Eight flows across16 presenters retain exact response/rejected gates, pending/unknown no-ack barriers, current/control/record callbacks and existing visible acknowledgement text. Sixteen names only; no new action/outcome/retry/recovery semantics or actual server result.

Sixteen names inverse exactly to16 whole presenters;16 external model/16 core hashes unchanged. Immutable source/raw input/payload/attempt, synthetic grants separate from GET, sibling/partial/permission/owner/epoch/ledger/receipt/ordinary Back/review policies exact. No new/moved/removed/enabled controls/availability/GET/commands/API/copy/model/core/ports/default/version change. All prior fixes/prepared tests/WIP and old artifacts retained. Current566 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.


### Source568 / documentation569: two paired draft/receipt and notification dynamic acknowledgement reader-name blocks

Eight existing templates keep their original Done/Edit or notification edit expressions byte-for-byte. Submission/record/read/attemptID arguments, confirmed/rejected gates, current guards and pending/unknown no-ack barriers unchanged. No new action/result/retry/recovery semantics.

Eight names inverse exactly to8 whole presenters including embedded Swift notification models. Four parent UI/8 external model/12 core hashes unchanged. Reply receipt delivery/status wording, quick-reply/root ownership, TaskDraft optional/source/parent/appointment/client controls and notification peerBlocked/onDispatch/source/grant/actor/ledger policies exact. No new/moved/removed/enabled controls/availability/GET/commands/send/booking/API/model/core/ports/copy/default/version or real outcome assertion. All prior fixes/prepared tests/WIP/old artifacts preserved. Current568 Swift Core/host/all119 App and Android remain NOT_RUN; static expectations and PBX metadata lint do not establish current/server/device acceptance.
