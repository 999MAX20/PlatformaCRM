# Команда, аккаунт и безопасность доступа

AUD-01, 17.10: offline-кэш заявок и pending queue разделены по пользователю,
Business и снимку прав; tokenStorage.clear очищает их при logout/expiry/new login.
Legacy-данные без владельца удаляются; callbacks старой сессии не восстанавливают
записи после очистки. Проверки и версия — checkpoint AUD-01-20261017.
AUD-02 проверяет связи notes/activity и привязывает создание к actor сессии;
формы проверяют допустимого ответственного, журналы отправок read-only через API/admin.
Версия и проверки — checkpoint AUD-02-20261017. Обход UPDATE scope и
несогласованные sensitive-field проверки AUD-03/13/14/17/18 остаются открыты
в [roadmap](../current/roadmap.md#project-audit-20261017).
[Evidence](../testing/project-audit-20261017.md) уточняет конкретные входы; это
не отменяет действующие требования access и не объявляет все API проверенными.

Исходная основа `768b2675`, 09.10.2026; актуальные дельты 16.10 описаны ниже.
Владелец управляет своим Business и командой,
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
platform_admin + точный активный grant + recent MFA. Это ограничение именно support-note: ADMIN-01/03/04 разрешены обеим
platform-ролям со свежим MFA, ADMIN-02 — только platform_admin. Каждый сценарий
проверяет обращение и свою доменную политику, общего tenant write-доступа нет.
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
UI `/app/account`, `/app/settings`, `/platform/account`; API auth/team/security,
отдельная platform-зона. 15.10 PLATFORM-SHELL переиспользует личный профиль,
безопасность и язык для platform admin/manager без Business. Настройки стартовой
страницы, Business access и уведомлений остаются в merchant account. Новых прав,
API и изменений MFA нет; scope/evidence —
[checkpoint](../testing/task-state/PRIMARY-SESSION.md#platform-shell-20261015--implementation).
09.10: роли открываются из drawer сотрудника/приглашения с возвратом и сохранением
черновика; правится существующая общая роль, что явно обозначено в матрице.
Личные уведомления перенесены в Account с областью Business/User. Security сохраняет
журналы и доступы поддержки, убирает агрегаты и добавляет фильтр неуспешных входов.
[Settings evidence](../testing/settings-functional-20261008.md) и
[tenant tests](../../apps/core/tests_tenant_isolation.py) имеют разные границы:
новый общий security audit здесь не выполнялся.
[R01](../current/roadmap.md) — применимые роли, R04 — target MFA/операции,
R02/R07 — юридические тексты; V1-O06 не разрешает новую матрицу автоматически.
09.10 — паспорт существующей модели, без смены прав или credentials.

## ADMIN-02/03 — реализованные дополнения 16.10

[Передача владельца](../../apps/businesses/ownership.py) сохраняет два личных
согласия и прежнюю роль/отключение только Business; подтверждения доступны в Account,
исполнение — в карточке платформы. [Recovery](../../apps/accounts/recovery.py)
сохраняет User ID и memberships, подтверждает новый mailbox, меняет пароль,
отзывает сессии/MFA/social links и требует нового MFA enrollment. Проверка личности
ручная; автоматическая проверка документов не реализована и не обещается.
[Диагностика](../../apps/accounts/recovery_selectors.py) показывает обычный email-change
и ограниченные последние 50 recovery-заявок; это не полный почтовый журнал.
Код опубликован (`cafcea5` / `dc1eedf`), scoped backend/browser/build PASS в checkpoint.
Остаток: рабочие businesses0012/accounts0011, support email/FRONTEND_URL/SMTP и
проверка разрешённой среды. ADMIN-04 и восстановление подписки этим не закрыты.

Дельта ADMIN-04,16.10: [инспектор](../../frontend/src/features/platform/BusinessEmployeeAccessPanel.tsx)
показывает отдельно User, membership, роль, приглашения и scoped зависимости.
[Сервис](../../apps/businesses/employee_access.py) отключает/восстанавливает доступ
выбранного бизнеса, меняет существующую роль, отзывает/перевыпускает непринятое
приглашение. Восстановление/роль/перевыпуск требуют личного согласия владельца;
все команды — обе platform-роли, свежий MFA, открытое обращение, причина и аудит.
Согласие привязано к условиям/owner epoch и сроку24ч; повтор не дублирует эффект.
История, специалист, назначения, другие Business и глобальный аккаунт сохраняются.
Старый invitation token недействителен после перевыпуска; новый доступен владельцу
через обычные настройки команды, автоматической отправки нет.
Scoped PostgreSQL/concurrency/browser/build PASS — checkpoint ADMIN-04.
Остаток: рабочая businesses0013 и целевая среда; глобальный unlock исключён,
история запросов ограничена последними50 (не полный журнал/поиск).


16.10, этап6: общая локальная приёмка ADMIN01–04 + основы ADMIN05 — SCOPED PASS.
Проверены PostgreSQL concurrency/permissions/rollback и совместный browser flow
desktop/mobile/RU/KK/EN; исправлены подписи ресурсов в общей истории просмотра.
Источник — база3c6939ee + эта UI-дельта; [checkpoint](../testing/task-state/PRIMARY-SESSION.md),
PLATFORM-ADMIN-ACCEPTANCE-20261016. Полный этап6 и ADMIN05 не закрыты; отложенные
коммерческие решения/код/live evidence и рабочая среда сохраняются без изменений.
