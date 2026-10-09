# Команда, аккаунт и безопасность доступа

Срез `768b2675`, 09.10.2026. Владелец управляет своим Business и командой,
сотрудник — собственным аккаунтом; platform support имеет отдельную ограниченную роль.
Единственный нормативный источник прав — [access](../current/access.md).

## Реализованные процессы

BusinessMember/BusinessRole/RolePermission/Team задают membership и
NONE/OWN/TEAM/BUSINESS. Presets owner/admin/manager/operator/specialist сохраняются;
Director — название admin, профессия не permission. Backend сохраняет атомарный
visibility action без выдачи ранее запрещённых действий. После редизайна 09.10 UI
редактирует разрешение/scope отдельно для действия; строка сохраняется независимо.
POST отсутствующего override атомарен с audit; owner остаётся readonly.
[Проверки редизайна](../testing/settings-redesign-20261009.md) включают rollback,
role denial и tenant boundary. Приглашение существующего email принимает соответствующий аккаунт;
его пароль и глобальный профиль не переписываются приглашением.

Личный профиль, пароль/email, свои устройства/сессии и MFA имеют отдельные действия.
Security-изменения отзывают прежние credentials; tracked logout отзывает текущее
устройство. Foreground idle/absolute expiry и auth epoch проверяются сервером.
Смена email подтверждается mailbox code; locmem не доказывает SMTP.
Отключение membership не отключает специалиста и не переносит его работу автоматически.

## Защита и восстановление

Tenant/scope/capability применяются до выдачи списков/counts/children, также в worker,
экспорте и AI. Support grant выдаёт owner с recent MFA; support-note требует
platform_admin + точный активный grant + recent MFA. Platform_manager write не получает.
Для production/платного пилота требуется privileged MFA по текущему контракту.
Recovery codes одноразовые, TOTP secrets зашифрованы; reset обязательной MFA
не выдаёт privileged сессию без фактора. Восстановление владельца — отдельная операция.

UI сохраняет аккаунт/URL/draft при временной сети, учитывает Retry-After; invalid
credentials требуют login. Бизнес-мутация не переигрывается автоматически после auth.
Signup legal IDs пока имеют placeholder-тексты; юридический допуск не подтверждён.

## Код, evidence и остаток

[Access](../../apps/businesses/access.py), [role services](../../apps/businesses/role_services.py),
[accounts](../../apps/accounts), [security API](../../apps/core/security_views.py),
[API auth](../../frontend/src/api/auth.ts), [account UI](../../frontend/src/features/account/AccountPage.tsx).
UI `/app/account`, `/app/settings`; API auth/team/security, отдельная platform-зона.
[Settings evidence](../testing/settings-functional-20261008.md) и
[tenant tests](../../apps/core/tests_tenant_isolation.py) имеют разные границы:
новый общий security audit здесь не выполнялся.
[R01](../current/roadmap.md) — применимые роли, R04 — target MFA/операции,
R02/R07 — юридические тексты; V1-O06 не разрешает новую матрицу автоматически.
09.10 — паспорт существующей модели, без смены прав или credentials.
