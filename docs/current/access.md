# Доступ, приватность и границы аккаунта

Статус: **действующий контракт**. Срез 07.10.2026, `f01d226`.
Сохраняет принятые ограничения; не вводит роли, grants или новую permission-модель.

## Business и серверные права

Каждая merchant-сущность принадлежит Business либо безопасно выводит его через
связь. Queryset ограничивается до поиска, подсчёта, pagination и сериализации.
Generic update не меняет владельца Business, включая ownership через parent.
Same-business связь сама по себе ещё не даёт актёру права на связанный объект.

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

Platform и merchant-права не смешиваются. Поддержка не получает общий доступ
к рабочим данным клиники. SupportAccessGrant создаёт/меняет/отзывает только
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
