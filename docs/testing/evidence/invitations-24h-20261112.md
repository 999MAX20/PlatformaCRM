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
