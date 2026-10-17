# Доступ, приватность и границы аккаунта

Статус: **действующий контракт**. Срез 07.10.2026, `f01d226`.
Сохраняет принятые ограничения; не вводит роли, grants или новую permission-модель.

## Business и серверные права

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
Право менять обычные сообщения не заменяет `conversations:manage` для общих быстрых
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
| Appointment/заметка | `appointments:update`, доступ к записи; специалист только к своей связанной Resource-записи |
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
