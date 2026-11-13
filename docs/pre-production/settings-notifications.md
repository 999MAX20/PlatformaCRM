## Фильтрация дополнительных полей — 09.11.2026

Исправлены пустые числовые границы и multiselect значения в общих фильтрах клиентов
и услуг. Настройки видимости, значения, field-role и Business scope сохранены.
API regression и12 браузерных сценариев RU/KK/EN desktop/mobile прошли локально.
[Контракт](../current/import-workspace.md), [evidence](../testing/evidence/push-fixes-20261109.md).

## Компактные ошибки переноса — 06.11.2026

ImportWorkspace переведён с inline error banners на общий fixed host справа снизу.
Рабочий support request_id доступен компактным копированием; это не отправка тикета.
Кнопка refresh названа «Обновить данные», не повторяет мутации. Остальные ошибки
полей/строк и общие fallback-страницы сохраняют своё назначение.
[Доказательства и граница](../testing/evidence/import-upload-alert-20261106.md).

## Согласование уведомлений сессии и соединения — 05.11.2026

Сообщения авторизованного восстановления сессии и выхода включены в общий контейнер
уведомлений. При общей недоступности связанное сообщение сессии подавляется, после
восстановления /ready/ отдельная проблема сессии остаётся видимой. Локальная проверка
описана в [evidence](../testing/evidence/session-notices-20261105.md); это исправление
показа, не диагностика причины периодических сбоев локального сервера.

## Настройки дополнительных полей переноса, 04.11.2026

CustomFieldDefinition дополнен Service/Specialist; текущие tenant/entity/field-role
проверки распространяются на значения и context API. `options_json.display`
поддерживает boolean in_card/in_table/in_filters/in_calendar, не удаляя значения
при изменении видимости. Импорт не запускает уведомления; отдельная активация
будущих записей использует существующие creation effects ровно один раз.
[Граница проверки](../testing/evidence/import-workspace-20261104.md).

## C09 — контекст и эффекты создания записи, 04.11.2026

Автоматическая запись сохраняет source_conversation и ответственного из явной
настройки Business.ai_booking_responsible_user. Авторизующий actor и ответственный
различаются; текущие членство, активность, доступность, scope и филиал проверяются
при создании. Пустая/невалидная настройка передаёт запись сотруднику без fallback.
Успешный replay возвращает исходную запись без переназначения и повторных эффектов.
Общий транзакционный обработчик создания пишет один BusinessEvent appointment.created
(source=crm, ключ appointment:{id}:created), планирует followups, уведомляет
ответственного и запускает действующую автоматизацию. Повторный вызов не дублирует
эффекты. Manual/plan/legacy callers используют тот же обработчик; API rollback проверен.
Настройка доступна в «Настройки → Компания», RU/KK/EN, по SETTINGS UPDATE; GET
businesses/{id}/booking-responsible-options/ отдаёт только допустимых сотрудников
этого бизнеса, PATCH businesses/{id}/ принимает nullable user ID и перепроверяет его.
Миграция businesses0014 добавляет nullable FK без backfill. Рабочая БД не изменялась:
применение миграции к ней/серверу требует отдельного разрешённого target. После
миграции существующий бизнес явно выбирает ответственного; до этого AI handoff.
Локальная приёмка C09 завершена; push/live model/channel/deployment не выполнялись.
[Проверки и границы C09](../testing/evidence/remediation-c09-20261104.md).

# Настройки и уведомления

NOTIFICATIONS-SERVER-FIXES-20261113: шесть подтверждённых серверных дефектов
исправлены и локально проверены, включая конкурентность PostgreSQL.
Detail/read/unread согласованы с персональной лентой без лишнего VIEW;
delivery-действия закрыты для SYSTEM. Ручной retry захватывает конкретную failed
попытку атомарно и пишет audit; зависший sending завершается как неизвестный failed
без автоматической пересылки. Окончательные исключения и отрицательные ответы
провайдера создают одинаковые атомарные failure/activity/оповещения. Монитор
оценивает внешнюю очередь, а не уже опубликованные внутренние события.
Сценарии объявлений, fixed audience, source access, внешнего consent и backoff
сохранены; схема не меняется. Проверки, срез, публикация и оставшиеся ограничения:
[checkpoint](../testing/task-state/PRIMARY-SESSION.md#notifications-server-fixes-20261113).

CONNECTIONS-SETTINGS-20261105: «Подключения» перенесены из основного desktop/mobile
меню во вкладку настроек. Вход settings.update OR integrations.view; права каждой
секции сохранены. Старые ссылки перенаправляются. [Scoped UI evidence](../testing/evidence/connections-settings-20261105.md); publication заблокирована.

ALERT-REMEDIATION-20261103: локальные исправления ошибок Client/Resource/Account,
счётчиков Bell и постоянных причин в финансовом блоке. Индикатор сервиса
удалён из шапки по последующему решению HEADER-CLEANUP. Подключения
предлагаются по реальной причине и правам; настройки не подменяют исправление
сбоя workers. Последующий RECORDS-BELL-FIX03.11
исправил конкретный текст service events безопасными локализованными ключами;
API и RU/KK/EN browser PASS. Доставка/production вне этой приёмки.
[Новый срез](../testing/evidence/records-bell-fix-20261103.md).
[Точный срез и проверки](../testing/evidence/alert-remediation-20261103.md).

ALERT-COMPONENTS-20261102,03.11: локально проверены насыщенные общие alert-карточки
и единая область справа снизу для toast/undo/сети и сообщения о новых чатах.
Сохранены ограниченный стек, локализация, recovery и read-refresh после соединения.
Ошибки форм остаются в контенте; ServiceStatusNotice удалён из шапки по последующему
решению владельца HEADER-CLEANUP03.11. Modal/drawer keyboard, мобильные отступы
и сроки жизни проверены; серверная доставка/колокольчик/recipients не менялись.
[Evidence и ограничение публикации](../testing/evidence/alert-components-20261102.md).

PILOT-ACCESS-20261031: signup/auth/MFA/session/reset, complete invitation lifecycle,
current roles, disable/restore and two-Business isolation verified on an isolated
candidate. Existing access/security patches integrated; neutral signup default and
specific invalid-MFA-code recovery copy added. Team UI and corrected MFA retry
checked; backend suites and PostgreSQL races prove authorization/preservation.
Real delivery, legal texts and deployed pilot acceptance remain open.
[Checks and publication](../testing/task-state/PRIMARY-SESSION.md#pilot-access-20261031--two-business-onboarding-and-access).

AUD-V01,31.10: cookie-auth получил CSRF bootstrap и guard для восьми операций,
включая вход/MFA/refresh/logout/reset. Enforced-CSRF tests доказывают отказ чужому
Origin/форме/отсутствующему токену и валидный same-cookie flow. Browser: bootstrap503,
повтор входа, dashboard, reload/refresh и logout PASS на изолированном кандидате.
MFA/session-policy suites и frontend generation tests сохранены. Deployment не выполнен.
[Evidence AUD-REMAINING](../testing/task-state/PRIMARY-SESSION.md#aud-remaining-20261031--aud-12c-and-aud-v01).


NOTIFICATIONS-SSE-20261029: локально реализован опциональный канал Redis → отдельный
ASGI → открытый мониторинг owner/admin. Две сессии: изменения около1с, resync после
разрыва подтверждён; резервный опрос60с сохранён. Backend105, PostgreSQL3, Node10,
системные проверки и сборка PASS; HEAD98925b67 + сохранённый WIP, точный срез в PRIMARY.
Код/доказательства/решение владельца в этом scope: остатка нет. Среда: включение
на рабочем сервере и deployment не выполнялись. Публикация зависит от ранее
неопубликованной основы; следующий критерий — согласованный target/publication scope.


Персональная лента и объявления (NOTIFICATIONS-PERSONAL-20261028): `/app/notifications`
доступен активным участникам бизнеса из колокольчика. Состояния сотрудников независимы;
публикация, отзыв и мониторинг по каждому получателю доступны только владельцу/админу.
Аудитория фиксируется при публикации. Открытие, текущее прочтение и явное ознакомление
разделены; массовое прочтение не подтверждает ознакомление. После отзыва история
сохраняется у руководителя, из личных лент объявление исчезает.

Рабочие уведомления сохраняют маршрутизацию и дополнительно требуют текущего доступа
к источнику. Объявления не скрываются настройками категорий. Снимки рабочего текста
заменены локализованным типом и безопасной ссылкой; подробности читаются в CRM-объекте.
Клиентская доставка и её полномочия остаются отдельными. Миграции0006/0007 проверены
в изоляции и29.10 отдельно применены к локальной рабочей БД после backup.
Рабочий owner UI: публикация6 получателям, отметки/мониторинг и отзыв проверены.
NOTIFICATIONS-REFRESH-20261029 устраняет ожидание polling после собственных
изменений отметок: связанные представления обновляются через общий cache helper. Это новая согласованная
модель поверх закрытого OFFICIAL-21, его исторические результаты не переписаны.
Версия, проверки, оставшиеся ограничения — NOTIFICATIONS-PERSONAL-20261028 в
[checkpoint](../testing/task-state/PRIMARY-SESSION.md).

Исторический [audit](../testing/project-audit-20261017.md) описывает прежний код.
AUD-09 закрыт локально30.10: полная серверная сводка и счётчики записей услуг,
фильтры/архив/роли, загрузка/ошибка/повтор и RU/KK/EN проверены отдельным
кандидатом на base a45b0d80. Команды и публикация — AUD09 в
[checkpoint](../testing/task-state/PRIMARY-SESSION.md). В принятом scope остатка
нет; deployment/live отдельно. Прежняя приёмка настроек не заменяет эти проверки.

09.10.2026. Текущая структура после обратной связи владельца описана в
[SETTINGS-WORKFLOW](../testing/settings-workflow-20261009.md), основа `3026debb`.
Предыдущие границы функциональной проверки и редизайна сохранены в
[SETTINGS-FUNCTIONAL](../testing/settings-functional-20261008.md) и
[SETTINGS-REDESIGN](../testing/settings-redesign-20261009.md).
Здесь описание модуля, а не копия изменяемых счётчиков тестов.

## Что настраивается и кем

Business profile — имя/контакты/timezone/currency и реквизиты
по `settings:update`. Контакт WhatsApp не подключает канал. Язык бизнеса, общий
SLA, booking buffer, cancellation/prepayment текст и brand metadata сохранены
в данных и скрыты из формы; язык UI в личном профиле. Источник финансового анализа
и учётные предпочтения сохранены в данных; форма удалена из Подключений по решению
владельца 13.10. В Подключениях остаётся настройка провайдеров, не редактор этих полей.
Команда/роли/безопасность описаны в [паспорте доступа](identity-access.md),
подписка/usage — в [billing](subscription-usage.md).

У сотрудника без связанной BusinessRole сохранение явно назначает выбранную роль,
даже если её базовое название не изменилось. До сохранения форма показывает статус
несохранённого назначения и не открывает редактирование/предпросмотр применённых прав.
Уже назначенная пользовательская роль сохраняется. Простое открытие формы не меняет
доступ; серверный fallback для старых участников и миграции не менялись.

AppointmentMessageSetting задаёт confirmation/reminder/thank-you, enabled, offset,
шаблон с allowlist placeholders и канал. Auto выбирает готовый Telegram, затем
WhatsApp/email, иначе внутреннее уведомление сотруднику. Mock/mail locmem не
считаются клиентской доставкой; новое SMS-назначение недоступно. Старые данные не стираются.

NotificationPreference принадлежит Business/User/Category. NORMAL учитывает
in_app_enabled, HIGH/URGENT сохраняют исключение; отсутствие записи означает
включённые обычные уведомления. Это не выключатель внешних клиентских сообщений.
Quick replies: title/text/category/channel/active/order → picker → черновик,
без автоматической отправки; управление общими шаблонами требует своих прав.
Custom fields валидируют типы/options/roles, entity access и сохраняют исторические значения.
Они доступны также на полных страницах клиента, заявки, сделки и записи; колонки
таблицы определений выровнены, действия собраны в меню. Пустой picker быстрых ответов
ведёт к настройкам при праве управления; текст вставляется в сохранённый черновик.
Личные предпочтения уведомлений находятся только в Аккаунте, с явной областью Business/User.
Три сценария сообщений сохранены; добавление собственных сценариев отложено владельцем.

## Ошибки, транзакции и доступ

Выбранный Business передаётся явно; API авторизует фактический объект, cache/form
не смешивают бизнесы. Списки проходят pagination, ошибка не изображает отсутствие данных.
Формы сохраняют независимые черновики. Неверная timezone/template/тип поля отклоняется.
Правка message setting атомарна с audit и пересозданием только подходящих незавершённых
заданий. Retry/SENDING claims отзываются, старый worker не восстанавливает статус.
Отправленное не дублируется, thank-you не запускает рассылку всей истории.
Уже начавшийся внешний HTTP/SMTP запрос не гарантирует отзыв/exactly-once.

## Карта, статус и следующий допуск

[Settings UI](../../frontend/src/features/settings/SettingsPage.tsx),
[конфигурация](../../frontend/src/features/settings/settingsConfig.ts),
[message service](../../apps/scheduling/message_settings.py),
[delivery](../../apps/notifications/delivery.py),
[custom fields](../../apps/core/custom_fields.py),
[notifications API](../../frontend/src/api/notifications.ts).
Reachable `/app/settings`; backend businesses/team/security/appointment-message-settings/
notification-preferences/quick-replies/custom-fields/billing по профильным правам.
Локальные проверки и [CI](https://github.com/999MAX20/PlatformaCRM/actions/runs/37832658462)
PASS; external delivery не проверялась. [R03/R04](../current/roadmap.md) отвечают
за канал/очереди, R05 — рабочий день. Закрытую Settings-приёмку не переоткрывать без основания.
09.10 — обновлены интерфейсы всех десяти разделов, локальные ошибки и сохранение;
новые scoped runtime-проверки перечислены в SETTINGS-REDESIGN.
Последующая обратная связь владельца упрощает навигацию и профиль, очищает Тариф
и проверяет сквозные переходы: [SETTINGS-WORKFLOW](../testing/settings-workflow-20261009.md).

Сверка 16.10: актуальная scoped сверка Settings и исправление роли опубликованы
в c40aff4; старый CI37832658462 относится только к основе 09.10. Настройки/потребители
сохраняют свои границы доказательств; R01 закрыт, R03/R04/R05 отдельно.
