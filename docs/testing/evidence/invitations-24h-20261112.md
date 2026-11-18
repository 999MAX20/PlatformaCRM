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
