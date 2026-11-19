# INVITATIONS-24H-20261112 — /invite и приглашения сотрудников

12.11.2026. Локальная реализация и изолированные проверки завершены. Рабочая
миграция, deployment и реальное письмо нового сценария не выполнялись.
Канонический checkout PlatformaCRM, ветка codex/ui-testing-toolkit, база4792f93a.
Чужие изменения AI/Management и документов сохранены.

## Поведение

TEAM MANAGE выпускает приглашение для конкретных Business/email/роли.
Новые и перевыпущенные ссылки живут24ч; существующие сохраняют записанный срок.
Новый пользователь выбирает пароль с подтверждением; существующий входит своим
аккаунтом, пароль/профиль не перезаписываются. Чужой email и inactive account
не принимают приглашение. Принятие проверяет актуальные роль/отдел/лимит участников.
После подтверждения пользователь входит именно в пригласивший Business; выбор
ограничен доступными ему memberships и хранится отдельно по пользователю.

/invite без токена, неверная/просроченная/отозванная ссылка не показывают форму
пароля. Есть состояния accepted, wrong account, retry и сохранение draft при
ошибке. RU/KK/EN, desktop/mobile и keyboard проверены. Owner UI использует email;
legacy manual/messenger API остаётся совместимым. PATCH/DELETE приглашения закрыты.

Повторная отправка требует revision, меняет token и срок, ограничена60с между
попытками. Accepted/revoked нельзя переслать: после отзыва создают новое приглашение.
Issue/accept/resend сериализованы блокировкой Business, аудит входит в транзакцию.
Письмо отправляется после commit с тайм-аутом10с. Доставка имеет отдельные поля
not_requested/pending/accepted/failed и безопасный код ошибки. accepted означает
приём SMTP-сервисом, НЕ принятие приглашения и НЕ доставку в почтовый ящик.
Автоматических повторов нет. После аварии pending восстанавливается явным resend
с новой ссылкой; already accepted SMTP письмо невозможно отозвать транзакцией БД.
Support repair остаётся отдельным consent flow без автоматического письма.
Invitation bearer paths скрываются в sanitization. AI/BusinessEvent не менялись.

## Проверки и границы

- Первый server slice12PASS после исправления тестового ожидания rollback на
  принятый проектом HTTP500 envelope; исходный1FAIL сохранён.
- Зависимые84PASS: delivery/token/onboarding/access/employee repair.
- PostgreSQL17PASS: acceptance/resend races, repair races, rollback.
- Redaction15PASS; system check и migration drift PASS.
- Initial browser3PASS/5FAIL: неверный locator/ожидание имени и общая fixture
  достигла реального лимита10members. Лимит продукта не ослабляли.
  Recovery6PASS; дополнительные error/draft/locale2PASS; финальный subset4PASS.
  Новый получатель desktop/mobile прошёл в исходном запуске. Это перекрывающиеся
  наборы, не сумма уникальных сценариев.
- Финальные build/types/i18n и bundle budget PASS. Сохраняются предупреждения
  RU/KK dictionary chunks >500kB; app-shell budget PASS.

Журналы и точные команды: output/invitations-24h-20261112 (CHECKPOINT.md,
backend-slice.log, dependent.log, postgres.log, redaction.log, browser-*.log,
build-final.log, bundle-final.log, system.log, drift.log).
Браузерный воспроизводитель: `.venv/Scripts/python.exe scripts/verify_invitations.py`;
использует одноразовую БД, локальный outbox и реальные API, без внешних отправок.
PG-модули перечислены в pg_inner.py; тесты не применяют миграции к рабочей БД.
В документационном завершении код не менялся; прежние результаты не называются CI.

## SMTP: что подключено

**Resend подключали06.11.2026.** Историческое операционное доказательство:
output/email-readiness-20261106/RESULT.txt и resend-delivered.jpg. На сервере
использовались Django SMTP, smtp.resend.com:587 STARTTLS, username resend,
отправитель PlatformaCRM <no-reply@notify.platformacrm.kz>. Домен был Verified,
ключ ограничен отправкой с notify.platformacrm.kz. Один synthetic email получил
Delivered в Resend, владелец подтвердил Inbox. Это доказательство транспорта
06.11, не сквозная проверка новой логики приглашения12.11. Тогда автоматической
отправки приглашений ещё не было. Тариф/остаток квоты сегодня не перепроверены.

Локальная .env12.11: console.EmailBackend, пустые host/user/password,
EMAIL_PORT587, EMAIL_USE_TLSTrue, sender no-reply@zani.local, FRONTEND_URL
не задан. Process overrides для проверенных почтовых ключей отсутствуют.
Новый сервис корректно считает console backend неготовым к отправке.
Локальное приглашение поэтому не доказывает работу Resend.

Текущий DNS platformacrm.kz:94.131.94.248. Read-only SSH к текущему адресу
и историческому5.35.105.125 завершился connect timeout. Актуальный серверный env,
запущенный release, наличие businesses0015, валидность ключа, состояние домена,
квоты и история новых писем сегодня НЕ подтверждены. Секреты не копировались
в отчёт; рабочая конфигурация и провайдер не изменялись, писем не отправляли.

[Официальная SMTP документация Resend](https://resend.com/docs/send-with-smtp)
подтверждает host smtp.resend.com, username resend, API key как пароль,
587 для STARTTLS. Нынешний Django SMTP transport совместим: новый SDK не нужен.
Для запуска нового flow нужны SMTP backend/host/credentials, валидный sender,
HTTPS FRONTEND_URL целевой CRM и отдельно разрешённая рабочая миграция0015.
Не подменять STARTTLS587 на implicit TLS465 без поддержки SSL в конфигурации.

## Ограничения реализации и следующий шаг

Provider message ID, delivered/bounce/complaint webhook и сверка с Resend сейчас
не сохраняются в приглашении; delivery_status — результат SMTP-вызова.
При timeout после приёма письма провайдером результат может быть неоднозначным;
blind retry отсутствует, resend аннулирует старый token. Resend поддерживает SMTP
idempotency header, но этот сервис его не выставляет. Это предложение улучшения,
не выполненная интеграция. Письмо синхронно удерживает business lock до10с;
при медленном SMTP возможно ожидание других операций приглашения этого бизнеса.

Код/локальные доказательства по принятому scope закрыты. Среда остаётся отдельно:
доступ к действующему серверу, проверка настроек/миграции и controlled live invite
на согласованный адрес с подтверждением получения и входа. Никакого deployment,
рабочей миграции или реального письма текущая задача не выполняла.
Документация: access, operations, identity-access и README обновлены; roadmap
acceptance не закрыта, поскольку release/live certification не проводилась.

## Документационное завершение и публикация

Ссылки новых разделов, registry JSON, task-owned diff/credential-pattern review,
working/index diff hygiene PASS. Код в этом завершении не менялся; зависимости
не переустанавливались, приложение ради Markdown повторно не собиралось.
После fetch origin/main перед commit остаются56 предыдущих исходящих коммитов.
Обычный push включил бы чужие изменения, поэтому не выполняется; нового CI нет.
Работа сохранена отдельным локальным commit; точный SHA — в checkpoint и Git.

## Рабочий прогон — 18.11.2026

Owner первоначально запросил новый business→приглашения, затем явно выбрал
проверку приглашений в текущем бизнесе: указанный owner email уже зарегистрирован.
Новый аккаунт/Business не создавались. Target https://platformacrm.kz, Chrome,
текущий Business владельца. Получатели и две роли подтверждены пользователем
непосредственно перед предоставлением доступа; адреса не дублируются в Git.

До действий: один владелец, активных приглашений нет. Через обычную форму
созданы ровно два приглашения: первому получателю Manager, второму Operator.
Проверены реальные role previews: Manager имеет business-wide clients/calendar,
payments view/create и analytics; Operator без payments/analytics, с own tasks
и ограничением изменений клиентов/чатов. Оба без TEAM, billing и integrations.
Роли не редактировались. Секреты/пароли сотрудников не запрашивались.

**Результат отправки FAIL для обоих.** UI показал «Приглашение создано», статус
«Ожидает» и «Не удалось отправить письмо». Сроки:19.11.2026 22:24:02 и22:24:19
(Asia/Qyzylorda). После reload обе записи/роли/ошибки сохранены; в сотрудниках
по-прежнему только владелец. Каждая кнопка создания нажата один раз; повторная
отправка, отзыв, принятие и ручная передача bearer-ссылок не выполнялись.

Снимок результата захвачен и визуально проверен:
output/playwright/invitations-live-20261118/send-results.png (локально, содержит
адреса получателей, не включён в Git). Страница списка оставлена в Chrome.
SMTP acceptance/Resend delivery/Inbox/вход сотрудников НЕ подтверждены.
UI не различает not_configured и unavailable. Read-only SSH к текущему известному
серверу94.131.94.248:22 завершился ConnectTimeout8s; remote env/logs недоступны.
Поэтому причина не приписывается Resend или конкретной переменной без доказательств.
Исторический Inbox PASS06.11 не закрывает текущий FAIL.

Продуктовый код, конфигурация, миграции, provider settings и deployment не менялись.
Это live browser evidence текущей страницы, не сертификация локального HEAD или
всего релиза. Исходная регистрация исключена решением владельца, не объявлена PASS.
Следующий незакрытый результат: восстановить серверную отправку на основании
диагностики, затем отдельно подтвердить повторную отправку двух существующих
приглашений и получение писем. Изменение сервера/почты не выполнялось в этом прогоне.

## Уточнение SSH и причины отправки — 18.11.2026

По прямому поручению владельца запрошены сведения у чата «Менеджер».
Актуальный host94.131.87.21, прежний94.131.94.248 устарел. Проверка SSH с
проверкой known_hosts прошла: platforma-kz-main, crm-web active, WorkingDirectory
/opt/platforma/releases/20261118-58a6427e. Firewall/IP allowlist не изменялись.

Shared crm.env, на который ссылается .env релиза: production + locmem.EmailBackend,
placeholder SMTP host/sender, SMTP user/password отсутствуют, FRONTEND_URL пустой.
Значения секретов не выводились. PostgreSQL read-only transaction подтвердила
Business18, приглашения1(manager)/2(operator), delivery failed/not_configured.
Это конфигурационный блокер до реальной отправки, не доказательство сбоя Resend.
Историческая рабочая Resend-настройка06Nov в текущем shared env отсутствует;
когда/кем она заменена, не установлено.

При повторном чтении оба приглашения уже revoked (17:28:48/51UTC), accepted_atnull;
у operator delivery_attempted_at17:28:41UTC — внешнее изменение после нашего
прогона. Эти действия данный чат не выполнял; первичная browser evidence сохранена.
Первый диагностический Python без явного env загрузил defaults и не открыл SQLite;
его профиль не считается серверным. Исправленный вызов явно загрузил shared env
и выполнил только SELECT внутри READ ONLY транзакции PostgreSQL.
Никаких отправок, изменений БД/config/firewall/deploy не выполнено.
Следующий шаг требует согласованного восстановления Resend/FRONTEND_URL на этом
сервере; отозванные ссылки не пересылать — для проверки нужны новые приглашения.

## Восстановление Resend и новые письма — 18.11.2026

Owner явно разрешил восстановить Resend/FRONTEND_URL и создать новые приглашения
тем же двум получателям с согласованными Manager/Operator. Отдельно разрешил
отменить только Notification630/632/635: pending,0attempts,Business2,example.test.
Условия повторно проверены под row lock; изменены только status/updated_at,
добавлены3audit records, исходные строки сохранены в защищённой резервной копии.
Активная email-очередь после отмены0. Старые приглашения1/2 не изменены.

Сохранённый domain-scoped Resend key проверен через SMTP STARTTLS с проверкой
сертификата и authentication, без тестового письма. Затем восстановлены ровно
8полей shared crm.env: EMAIL_BACKEND/HOST/PORT/HOST_USER/HOST_PASSWORD/USE_TLS,
DEFAULT_FROM_EMAIL, FRONTEND_URL. Host smtp.resend.com, port587, sender
PlatformaCRM <no-reply@notify.platformacrm.kz>, frontend https://platformacrm.kz.
Секрет не выводился и не сохранялся в репозиторий. Root-only backup directory
/opt/platforma/shared/email-restore-20261118 содержит crm.env.before, manifest.json,
queue-before.json и resend-smtp.json(0600). Rollback: восстановить только8почтовых
полей из backup с учётом более поздних env-изменений; перезапустить affectedCRM.
Отменённые historical notifications не возвращать автоматически в pending.

Django check и email_runtime_smoke --fail-on-missing PASS (без --send).
crm-web/events/worker перезапущены; все5CRM/stand/Caddy services active.
Хеши stand.env/stand-password/Caddyfile неизменны. Source release остаётся
20261118-58a6427e; код, миграции, firewall, DNS, чужие интеграции не менялись.

Через Chrome UI созданы приглашения3(manager) и4(operator). Каждая отправка
выполнена один раз:18.11 22:36:38 и22:36:56 Asia/Qyzylorda. Оба UI показывают
«Письмо принято почтовым сервисом»; независимый PostgreSQL READ ONLY readback
подтверждает delivery_status=accepted, delivery_error пустой, TTL24h,
accepted_at/revoked_at null. Согласованные роли сохранены, старые revoked записи
не восстановлены. Следовательно, реальная SMTP-отправка обоих писем PASS.
Снимок захвачен и визуально проверен: output/playwright/invitations-live-20261118/send-success.png.

После входа владельца в Resend оба новых письма имеют статус Delivered:

- Manager, invitation 3: provider ID 01a1efbb-6ce0-7049-910d-de612c3e280d.
- Operator, invitation 4: provider ID 01a1efbb-b50d-791b-ad71-ed4f33fa2b78.
Снимок захвачен и визуально проверен:
output/playwright/invitations-live-20261118/resend-delivered.png.
Доставка почтовому серверу получателей подтверждена. Папка Inbox/Spam и принятие
приглашений сотрудниками не проверены. Scope восстановления и реальной отправки закрыт.
Повторных отправок или дополнительных smoke email нет. Прежние FAIL остаются
историческим доказательством причины и не переписываются под новый PASS.

## Состояния приглашений и отключённого сотрудника, 18.11.2026

После успешной регистрации обоих сотрудников владелец воспроизвёл два дефекта:
завершённые приглашения продолжали показывать старую ошибку доставки и срок
ссылки; отключённый сотрудник видел предложение создать бизнес. Кнопка отключения
находилась после длинного списка прав. Это новая согласованная доработка,
успешная отправка и принятие приглашений сохраняются.

В `TeamSection` действия, статус доставки и срок ссылки показываются только для
pending/expired. Accepted/revoked сохраняют итоговый статус и исторические записи,
но не предлагают недоступные действия. `TeamAccessControl` перенесён к началу
карточки, кнопка имеет минимальную высоту44px и прежнее подтверждение.
Auth-me добавляет boolean `business_access_revoked` без данных недоступного
бизнеса; merchant guard показывает отдельное состояние с текстом владельца
и кнопкой выхода. Новички без членств, владельцы и пользователи с другим доступным
бизнесом не блокируются. Переводы RU/KK/EN, серверные права и аудит сохранены.
Миграций, изменения ролей, повторных писем и очистки истории нет.

Локальные проверки на исходной базе1ca57345 с отдельными БД/портами:
- Django check и migration drift PASS;5 новых auth-me тестов и9 тестов доставки PASS.
- `npm run build`: i18n/types/Vite/widget PASS.
- `scripts/verify_invitations.py --grep "new employee accepts|owner creates emailed"`:
  4/4 PASS, desktop/mobile. Реальные API изолированной среды: регистрация,
  принятие, отсутствие срока у accepted, видимая кнопка отключения, подтверждение,
  revoked экран после reload, клавиатурный выход; ошибка/срок скрыты после revoke.
  Log: output/invitations-24h-20261112/browser-1795025426470529000.log.
- Мобильный снимок revoked-mobile-chromium.png захвачен и визуально проверен:
  перенос заголовка, видимый фокус, кнопка выхода и отсутствие overflow.

Affected backend:90/90 PASS (`apps.accounts.tests`, `apps.businesses.tests_access`,
`apps.businesses.tests_employee_access`); log access-ux-backend.log,275.733s.
Дополненный сценарий с мобильной карточкой и RU/KK/EN:2/2 PASS,
browser-1795025918351756300.log. Изменение теста не меняло product inputs.
Снимки access-action-mobile-chromium.png и revoked-mobile-chromium.png визуально
проверены. Контраст существующих токенов: основной текст16.64:1,
warning-кнопка4.92:1, фокус5.35:1, AA PASS.

На стенд выложены только9 исходных файлов поверх release20261118-58a6427e,
каждый baseline проверен по SHA256. Чужие WIP настроек/главной/интеграций не вошли.
Сборка выполнена из исходников сервера: npm ci по его lock, i18n/types/Vite PASS,
VITE_API_URL пустой (same-origin). Старые widget и hashed assets сохранены.
Backup: /opt/platforma/shared/invite-access-ux-20261118 (source,dist,manifest,build.log).
Для отката вернуть source и frontend/dist из backup, удалить добавленный
BusinessAccessRevoked.tsx и перезапустить crm-web. Автоматический откат не понадобился.
Перезапущен только crm-web; readiness200. Shared crm.env и Caddyfile неизменны,
миграции/почтовые отправки/изменения членств не выполнялись.
Серверный check без ошибок, с W006(Sentry) и W019(legacy connector decrypt);
эти предупреждения не исправлялись в данной задаче.

Chrome на рабочем стенде: accepted/revoked строки без ошибок и срока, оператор
активен, менеджер уже отключён владельцем. Кнопка отключения видна вверху;
Tab/Enter открывают прежнее подтверждение, Escape отменяет и возвращает фокус.
Снимки closed-invitations-fixed.png и access-action-fixed.png сохранены в
output/playwright/invitations-live-20261118 и визуально проверены.
PostgreSQL READ ONLY проверка нового serializer: owner=false/1 доступный бизнес,
manager=true/0, operator=false/1. Ни одного изменения данных в этой проверке.
Live экран отключённого сотрудника пока ожидает входа владельца в Chrome под
этим аккаунтом; локальный реальный API/browser сценарий уже PASS.

Anti Slop scoped gate: purpose/tokens/copy PASS (существующий стиль, текст владельца,
без новых assets); keyboard/recovery/terminal states PASS по указанным сценариям;
mobile/contrast/i18n PASS по снимкам, размерам, вычислениям и тестам. Live employee
visual acceptance остаётся незакрытым до проверки в его сессии. Полный проектный
gate не запускался: ограниченная правка представления и read-only auth-me поля.


## INVITATIONS-FLOW-20261119: согласованный сценарий приглашения

Владелец одобрил вариант1 из разбора пяти экранов: широкое модальное окно без
блюра, понятное отображение прав, вход внутри `/invite`, прямой переход в CRM,
остальные предложенные исправления, проверку на стенде и документацию.
Предыдущие изменения terminal rows и отключённого доступа сохранены.

Реализация: существующий Dialog, лёгкое затемнение, две колонки и мобильная
полноэкранная форма; разрешённые разделы роли видны сразу, запрещённые раскрываются.
Настройка явно обозначена как изменение общей роли всех её сотрудников.
SMTP accepted отображается как «Отправлено» с галочкой; это не подтверждение доставки.
Срок без секунд сохраняется только у актуальных приглашений; повторная отправка
предупреждает о замене ссылки. Принятые/отозванные не показывают старые ошибки.

`/invite` показывает реальное имя бизнеса, получателя и назначенную роль;
`preview` добавляет `role_name` и `access_summary` (resource/action/scope без ID
записей прав). Вычисление использует существующий explicit → preset lookup.
Это настроенные права роли, а не обход object/branch/capability проверок.
Чужая/неактивная роль не раскрывает grants, terminal приглашения имеют пустой список.

Новый аккаунт создаётся прежним accept endpoint и сразу проходит обычный login
с только что заданным паролем. Существующий аккаунт сначала подтверждает пароль
и при необходимости MFA на той же странице. Refresh/session-cookie/CSRF механизмы
не заменены. При успешном принятии обновляется профиль, проверяется доступ к
приглашённому бизнесу, запоминается бизнес и открывается `/app` с существующим
ролевым start redirect. Обязательного экрана «Принято / Открыть бизнес» нет.
При сбое после принятия повторяется вход/открытие, а не создание аккаунта.

Проверки: финальные18 focused backend PASS (preview3, delivery9, revoked6),
Django check и migration drift PASS. Зависимые accounts/MFA/access/employee-access:
104PASS. Browser: второй общий прогон10PASS/2FAIL; MFA failures вызваны ключом
шифрования тестовой fixture, не рабочим сервером. После выравнивания runtime:
MFA и post-accept recovery4PASS; после добавления удаления участия и мобильной
геометрии owner/new-recipient4PASS. В сумме каждый из14 сценариев имеет PASS
на соответствующем актуальном коде. Первый прогон9PASS/1FAIL сохраняется как
диагностика429 общего loopbackIP. Добавленный тогда AUTH_LOGIN_RATE=1000/min
в isolated runner фактически отбрасывался configure_browser_runtime; effective
auth_login оставался10/min. Неэффективный override удалён при финальном review19Nov
(focused proof ниже); успешные прогоны не были результатом повышения этого лимита.
Сбойные попытки не засчитываются как PASS.

Логи: `output/invitations-24h-20261112/flow-backend-final.log`,
`flow-dependent.log`, `browser-1795036508453064800.log`,
`browser-1795036902748967400.log`, `browser-1795037189555343000.log`.
Сборка локального frontend PASS; финальные исходники также прошли server
build/types/i18n и readiness. Полный проектный gate не запускался: scoped auth/UI
изменение; рабочие миграции не выполнялись. На сервере прежние W006(Sentry) и
W019(legacy connector decrypt) остаются вне scope.

19.11 exact13-file patch развёрнут на platformacrm.kz поверх
`/opt/platforma/releases/20261118-58a6427e`, с проверкой SHA каждого исходника.
Backup и manifest: `/opt/platforma/shared/invite-flow-20261119`.
Конфигурации Resend/FRONTEND_URL и Caddy не изменялись; readiness200.
`flow-deploy.log` фиксирует сборку и активацию. Единственное последующее локальное
отличие от server source — удаление пустой строки в конце invitations.py.

Chrome live: после reload список содержит владельца и действующего оператора,
удалённого сотрудника нет. Снимок `live-members-removed.png` сохранён и осмотрен.
Enter открывает новый Dialog, фокус на закрытии; AX подтверждает поля, общую роль,
раскрытие запрещённых разделов и CTA «Отправить приглашение». Затем Chrome потерял
подключение отладчика: итоговый live screenshot формы и оставшиеся действия пока
не проверены. Вкладка сохранена, владельцу отправлен запрос восстановить управление.
Локальные снимки modal1440/768/390 и MFA mobile осмотрены: читаемые поля/переносы,
фиксированный footer, видимый фокус, без горизонтального переполнения. Повторный
вход реального получателя после этой выкладки не выполнен: сотрудник удалён по
решению владельца; новое приглашение/выдача доступа не подразумеваются этим решением.
Live visual/auth acceptance остаётся открытой. Commit/push пока не выполнены.

### Удаление участия по отдельному поручению владельца

Владелец уточнил: серверный аккаунт сохранить, удалить только участие в текущем
бизнесе и аккаунт из локальной БД, если он существует. Локальная рабочая PostgreSQL:
совпадений0, memberships0, ownedBusinesses0; изменений не выполнялось.
Сервер: Business18, member29, user24. Участие уже было отключено. Предварительная
проверка каскада: только1BusinessMember,0TeamMember. Удаление выполнено через
существующий TeamMemberManagementViewSet.destroy от владельца, ответ204, аудит
DELETE. Аккаунт user24 активен и сохранён, приглашения сохранены. Backup:
`/opt/platforma/shared/invite-member-removal-20261119/membership.json` (root0700 dir).
Принятое приглашение позволяет сохранить экран отсутствия доступа после удаления
самой записи участия. Дополнительная регрессия PASS:18 focused и desktop/mobile browser с удалением участия.
Новых писем и выдачи доступа в этом продолжении не выполнялось.

### Пилот: повторная scoped-проверка 19.11.2026

Поручение координатора: завершить доступную локальную приёмку приглашений,
исправлять только подтверждённые дефекты; без deploy, реальных приглашений,
изменения серверных memberships/паролей, commit/push и общих STATUS/PRIMARY.
Старт: canonical checkout, codex/ui-testing-toolkit,
HEAD b9415d71e89167fcbf74c55187009481da066389, индекс пуст; own/foreign WIP
соответствует передаче. Предыдущий результат → новая проверка: 14 уникальных
browser PASS в нескольких запусках → единый isolated прогон текущего WIP
и проверка отображения настроенных прав → продуктовый delta только при дефекте.
Риск: вход/MFA/tenant access и общий Dialog. Используются существующие runner,
одноразовая БД, свободные loopback-порты и captured mailbox; обычная БД не нужна.
Skills: zani-run-verification; Anti Slop during по решению владельца.
Сохранить согласованный дизайн, проверить реальные права, восстановление ошибок,
клавиатуру и desktop/mobile. Полный release gate относится к общему кандидату.
Свежая CUA inventory/listBrowsers показывает только MCP Apps, без Chrome
extension browser; native Chrome не используется как обход. Live visual/auth
остаётся открытой. Проверки и итог текущего прогона будут записаны ниже.

Минимальная live-проверка координатором в его собственной доступной вкладке:

1. В существующей owner-сессии Business18 открыть `/app/settings#team-access`.
   Убедиться, что в команде owner/operator; удалённого manager нет.
2. Открыть «Пригласить сотрудника», ничего не отправлять. Для роли «Оператор»
   дождаться загрузки прав. Снять и осмотреть desktop screenshot: широкая форма,
   затемнение без blur, реальные строки прав (клиенты/записи/чаты/задачи).
   Если строк нет, сохранить снимок/AX и текущее состояние загрузки; не менять роль
   или реальные grants ради исправления отображения.
3. Раскрыть/скрыть разделы без доступа. Escape закрывает форму и возвращает фокус
   на открывающую кнопку. Проверить мобильный viewport, полноэкранную форму,
   доступный footer, отсутствие горизонтального overflow; восстановить viewport.
4. В «Приглашения» проверить accepted/revoked: дата результата, без expiry,
   старой ошибки доставки и resend. В карточке действующего оператора открыть
   подтверждение отключения и только отменить, проверить возврат фокуса.
5. Отдельная сессия удалённого сотрудника нужна для live empty-state. Вход выполняет
   пользователь; не выходить из общей owner-сессии без координации. Ожидается
   «У вас больше нет доступа к этому бизнесу» без меню/создания бизнеса.
6. Live wrong-account/password/MFA/direct-CRM для нового принятия остаётся отдельным
   критерием: нужен явно разрешённый получатель и выдача доступа. Удаление manager
   такого разрешения не даёт. Без него не создавать/пересылать приглашения.

Состав task-owned WIP для кандидата (24 файла; новых продуктовых правок в этом
продолжении пока нет):

- Backend: `apps/accounts/serializers.py`,
  `apps/accounts/tests_revoked_business_access.py`, `apps/businesses/invitations.py`,
  `apps/businesses/views.py`, `apps/businesses/tests_invitation_preview_access.py`.
- Frontend: `frontend/src/api/team.ts`, `frontend/src/app/routeGuards.tsx`,
  `frontend/src/components/ui/Overlay.tsx`, `frontend/src/types/identity.ts`,
  `frontend/src/features/auth/BusinessAccessRevoked.tsx`, `InviteAcceptPage.tsx`,
  `MfaPage.tsx`, `useInvitationEntry.ts` (последние три в той же auth-папке),
  `frontend/src/features/settings/components/RoleAccessPreview.tsx`,
  `TeamAccessControl.tsx` (в той же components-папке),
  `frontend/src/features/settings/sections/TeamSection.tsx`,
  `frontend/src/lib/i18n/{ru,en,kk}/identity.ts`.
- Проверки: `frontend/e2e/pilot-invitations.spec.ts`, `scripts/verify_invitations.py`.
- Документы: `docs/current/access.md`, `docs/current/frontend.md`, этот evidence.

Собственные INVITATIONS-фрагменты `STATUS.md` и `PRIMARY-SESSION.md` уже существуют,
но файлы смешанные, не входят целиком в эти24; в этом продолжении не редактируются.
SHA256 snapshot: `output/invitations-24h-20261112/pilot-owned-manifest-20261119.json`.
Чужие AI/integrations/YCloud/roadmap изменения исключены. Source drift по24-путевому
manifest отсутствует (для кода/тестов); scoped `git diff --check` PASS, четыре новых
файла просмотрены. Продуктовый diff и тестовые сценарии reviewed без найденного
подтверждённого scoped-дефекта. Конкретные ссылки frontend→access→evidence существуют.

Сверка с сохранённым `flow-payload.json`:12 файлов совпали текстом, у
`apps/businesses/invitations.py` только удалённая пустая строка EOF. Это сравнение
с артефактом успешной выкладки, не новая аттестация текущей серверной версии.
Исторический server build/types/i18n/readiness PASS сохраняет свою границу;
общий кандидат с чужими WIP этим не сертифицирован. Новая сборка неизменённого
scoped кода не запускалась; full candidate gate остаётся у координатора.
Осмотрены сохранённые modal1440/390 и MFA desktop/mobile: реальные строки прав,
читаемые поля/ошибка, видимый focus, доступный footer. Mobile full-page artifact
содержит страницу ниже viewport fixed-modal, это не дополнительная высота modal.
Новый live visual PASS не заявляется.

Текущий единый browser run `browser-1795069357011062800.log`:11PASS/3FAIL.
Первый desktop new-recipient исчерпал общий60s timeout; mobile counterpart PASS.
Trace двух mobile failures (MFA accept, recovery invitation creation) содержит
точный backend400: users usage10/limit10, plan growth. Это ошибка ёмкости общей
fixture после накопления принятых сотрудников, а не отказ MFA/password.
Минимальный delta: `scripts/verify_invitations.py` создаёт отдельный synthetic
SubscriptionPlan с users50 для одноразового бизнеса. Entitlement enforcement
остаётся включённым, рабочая БД/тарифы не затронуты. Проверка: повтор всего14-case
suite с этой fixture; timeout диагностируется повтором после окончания backend
проверки, без ослабления assertions или повышения production limits.

Backend повтор текущего snapshot: PASS122 tests за394.819s; `check` PASS,
`makemigrations --check --dry-run` PASS (No changes detected). Команда по documented
isolated focused path: `.venv/Scripts/python.exe -c <isolated_runtime wrapper>`;
wrapper последовательно запускал `manage.py check`,
`manage.py makemigrations --check --dry-run`, затем `manage.py test` с labels
`apps.businesses.tests_invitation_preview_access`,
`apps.businesses.tests_invitation_delivery`, `apps.accounts.tests_revoked_business_access`,
`apps.accounts.tests`, `apps.accounts.tests_mfa`, `apps.businesses.tests_access`,
`apps.businesses.tests_employee_access`, `--verbosity 1`.
Полный лог `output/invitations-24h-20261112/pilot-backend-20261119.log`.
Изолированный SQLite runtime и синтетические данные, без миграций рабочей БД.
После этого изменён только test runner fixture, backend исходники не изменялись.

Дополнительная текстовая сверка `access-ux-payload.json`: routeGuards.tsx,
types/identity.ts, BusinessAccessRevoked.tsx и TeamAccessControl.tsx MATCH.
Итого17 продуктовых файлов соответствуют сохранённым двум deploy payloads
(invitations.py отличается только EOF whitespace). Это не заменяет серверную
сверку координатора. Текущий runner delta предназначен только локальной проверке,
не должен переноситься как конфигурация рабочего тарифа.

Координатор сообщил о своей live-попытке19Nov: после user-reconnect прочитаны
dashboard/settings в owner-сессии ЦКТ; переход на `#team-access` завершился CDP
Input.dispatchMouseEvent timeout, затем AX/DOM Emulation.setFocusEmulationEnabled
timeout. Вкладка остаётся в inventory, native fallback не использован, отправок
и изменений не было. Это сообщение координатора, не новая проверка данного чата.
На момент этой попытки form/keyboard/screenshots и employee auth оставались
UNVERIFIED; последующее восстановление owner-проверок зафиксировано ниже.

Последующая live owner-приёмка координатора19Nov после снижения нагрузки: PASS
в Chrome extension на `/app/settings#team-access`, owner-сессия ЦКТ/Business18.
В списке2 строки owner/operator, удалённого manager нет. В форме приглашения
для оператора видны реальные grants; desktop screenshot снят и осмотрен:
широкая форма без blur, читаемые колонки/footer. Разделы без доступа раскрываются;
Escape возвращает фокус на кнопку приглашения. Viewport390x844: screenshot снят
и осмотрен, полноэкранная форма, читаемые поля/grants/footer, без горизонтального
overflow. Viewport восстановлен, Escape возвращает фокус корректно.
Accepted/revoked строки показывают дату результата без expiry/старой ошибки/resend.
Подтверждение отключения сотрудника открыто и только отменено; фокус вернулся
на кнопку отключения, Escape вернул на строку сотрудника. Оператор остался Active.
Писем и изменений доступа не было. Это результаты координатора, не действия
данного чата. Снимки находятся в CUA tool output соответствующего хода чата
«Менеджер» (01a1f269-1892-7803-a140-94664a6411e2); на диск не сохранены.
Live экран удалённого сотрудника и real acceptance wrong-account/password/MFA/
direct CRM остаются pending. Новые локальные тесты ради этой записи не запускались.

Итог повторной локальной приёмки: `.venv/Scripts/python.exe
scripts/verify_invitations.py` exit0, **14/14 PASS одним прогоном,5.3m**,
`output/invitations-24h-20261112/browser-1795070152461697100.log`.
Первый desktop new-recipient повторно PASS30.8s без изменения timeout/assertions;
mobile MFA/recovery PASS с достаточной fixture capacity. Предыдущие11PASS/3FAIL
сохранены как неуспешная попытка, не переименованы в PASS. Новые реальные письма,
server membership/password, deploy/commit/push не выполнялись.

Scoped UI evidence: реальные права оператора видны на заново осмотренном
modal1440; mobile MFA screenshot осмотрен, неверный код отображается и следующий
валидный код принят по тесту. R26/R27/R32: scoped PASS по14 browser cases
(создание/captured mail, ошибка/повтор/revoke, Escape/focus return, wrong-account
logout, новый/существующий получатель, MFA, login recovery, invalid states,
RU/KK/EN reflow). Geometry/purpose/brand сохранены, новых UI/assets нет.
Live owner geometry/actions PASS в наблюдённой координатором границе выше;
employee empty-state и real acceptance UNVERIFIED, общий delivery gate
не объявляется закрытым. Build/types/i18n остаётся ранее выполненным, новым
изменением затронута только Python fixture и evidence, не frontend source.

Остаток: код нового scoped-дефекта не подтверждён; локальные необходимые проверки
пройдены, live owner форма/права/клавиатура/screenshots проверены координатором.
Evidence/environment: live экран удалённого сотрудника и real acceptance;
owner decision/input: разрешённый получатель для нового
live accept и ввод credentials пользователем. Публикация и общий candidate gate
отложены по поручению координатора. STATUS/PRIMARY в этом продолжении не изменены.
Следующий шаг: выполнить оставшиеся employee-session/live acceptance шаги5–6
выше в согласованной сессии, затем свести кандидат и его проверки. README/setup/API/schema/env не менялись,
дополнительные изменения этих документов не требуются.

### Финальный review runner: неэффективный rate override, 19.11.2026

По замечанию координатора удалены только присваивание `AUTH_LOGIN_RATE=1000/min`
и его два комментария в `scripts/verify_invitations.py`. Цепочка
invitation_browser_runtime → configure_browser_runtime → browser_environment →
safe_environment очищает этот ключ: он не входит в passthrough/overrides.
Production/config и shared environment helper не изменены. Fixture users50
сохраняется; итоговые14/14 PASS уже получены при effective auth_login10/min.

Focused verification PASS: в одном disposable isolated_runtime сравнены полные
результаты browser_environment до/после удаления (равны); два отдельных Python
процесса выполнили configure_browser_runtime и прочитали Django settings без
django.setup/БД/сервера. Все DEFAULT_THROTTLE_RATES равны, auth_login10/min в обоих
случаях. AST runner валиден. Лог:
`output/invitations-24h-20261112/pilot-rate-override-removal-20261119.log`.
Команда: `.venv/Scripts/python.exe -c <isolated_runtime/browser_environment comparison>`.
Тяжёлые/backend/browser/build проверки не повторялись по поручению координатора:
удалённый override не меняет effective runtime, новые пользовательские сценарии
не добавлены. Прежний122 backend/14 browser PASS сохраняет свою scoped-границу.
Full candidate gate PASS сообщён координатором, этим чатом повторно не запускался
и не присваивается как собственный результат. Live pending-границы выше сохранены.
