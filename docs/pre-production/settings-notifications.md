# Настройки и уведомления

Срез `768b2675`, 09.10.2026. Все десять существующих разделов Settings функционально
актуализированы; последующий редизайн 09.10 на основе `5434296a` описан в
[SETTINGS-REDESIGN](../testing/settings-redesign-20261009.md). Полный реестр параметров и точные
границы проверки — [SETTINGS-FUNCTIONAL](../testing/settings-functional-20261008.md).
Здесь описание модуля, а не копия изменяемых счётчиков тестов.

## Что настраивается и кем

Business profile — имя/контакты/timezone/currency/финансовый источник и реквизиты
по `settings:update`. Контакт WhatsApp не подключает канал. Язык бизнеса, общий
SLA, booking buffer, cancellation/prepayment текст и brand metadata сохранены
как справочные значения без обещания неработающего эффекта; язык UI в личном профиле.
Команда/роли/безопасность описаны в [паспорте доступа](identity-access.md),
подписка/usage — в [billing](subscription-usage.md).

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
