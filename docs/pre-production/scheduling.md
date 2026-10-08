# Запись, услуги, календарь и специалисты

Срез `768b2675`, 09.10.2026. Администратор записывает клиента на услугу к специалисту,
управляющий разбирает отсутствие; специалист работает со своей разрешённой записью.
Контракт — [CRM](../current/crm.md). Это административный визит без клинических записей.

## Поведение

Service определяет услугу/длительность; staff Resource — специалист с необязательным
linked_user. Создание специалиста не создаёт аккаунт, приглашение или платный seat.
Appointment связывает бизнес, клиента, услугу, время и ресурс. Создание/перенос требуют
активных same-business услуги и специалиста; слот проверяется при сохранении.
Доступность учитывает timezone, неделю, исключение даты, длительность и overlap.
Исключение перекрывает неделю специалиста, затем применяется бизнес-график;
новая модель смен/вместимости не вводилась.

Есть подтверждение, перенос, отмена с причиной, completion, no-show с причиной,
заметка и follow-up. Completion не подтверждает деньги. При отсутствии управляющий
вручную переносит/отменяет существующие визиты; деактивация ресурса запрещает новые
бронирования, но не удаляет историю. Отключение входа не деактивирует специалиста.

## Доступ, сообщения и восстановление

График требует `settings:update`, действия визита — appointment permissions/scope.
OWN выводится из активного `resource.linked_user`. Legacy-запись без специалиста
сохраняется; перенос требует выбора активного. Ошибка загрузки списка отсутствия
не является пустым днём, pagination не должна скрывать оставшиеся записи.
Сообщения confirmation/reminder/thank-you используют настройки и очередь;
перенос/отмена отзывают незавершённые задания. Уже начатый внешний запрос БД не отзывает.
Согласие клиента на перенос и изменение Appointment — разные состояния.

## Реализация и проверка

[Services](../../apps/scheduling/services.py), [availability](../../apps/scheduling/availability.py),
[message settings](../../apps/scheduling/message_settings.py),
[ресурсы](../../apps/scheduling/resource_services.py),
[schedule tests](../../apps/scheduling/tests_specialist_schedule.py),
[API](../../frontend/src/api/appointments.ts),
[календарь](../../frontend/src/features/calendar/CalendarPage.tsx).
UI `/app/calendar`, `/app/business/services`, `/app/business/resources`,
`/app/business/working-hours`; API appointments/resources/services/working-hours/schedule-exceptions.
[Settings evidence](../testing/settings-functional-20261008.md) закрывает локальные
настройки и mocked delivery; [UI evidence](../testing/ui-operations-20261008.md) — свой scope.

## Оставшаяся граница

[R01](../current/roadmap.md): D-01/D-04/D-05 для конкретных legacy/terminal/follow-up
сценариев; R03/R04 — доставка и worker; R05 — день персонала. Кресла/оборудование
и автоматическая рассылка при отсутствии не получают разрешения из этого паспорта.
09.10 — документирован текущий срез; никаких рабочих миграций/визитов не изменялось.
