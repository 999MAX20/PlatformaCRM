# CRM: инварианты и технические границы

Статус: **действующий контракт**. Срез исходников 07.10.2026, `f01d226`.
Объём задаёт [продукт](product.md); наличие метода в коде не является его новой
сертификацией или разрешением обойти [доступ](access.md).

## Общие правила

Все сущности и связи принадлежат одному Business. Client — контакт/история,
Lead — потребность, Deal — коммерческая возможность, Appointment — визит,
Task — действие, Conversation — переписка, Payment — зарегистрированные деньги.
Завершение одной сущности не закрывает остальные и не подтверждает оплату.

Сложные чтения — selectors, изменения — services/state machines. View проверяет
вход, права и вызывает сервис; React использует `frontend/src/api/*`.
Lifecycle/status/stage, владение/назначение, terminal/archive/delivery timestamps
и серверные metadata нельзя менять произвольным CRUD-запросом в обход действия.
Разрешённые поля конкретного endpoint сверять с serializer/action, не с архивной
таблицей API. Generic PATCH/PUT не переносит объект между Business.

Важные изменения пишут activity, чувствительные/разрушительные — audit.
Уведомления и BusinessEvent сохраняют существующее назначение и не дублируют
побочный эффект. Проверять rollback/replay/concurrency там, где операция этого
требует; общая транзакционность всех входов не доказана одним документом.

## Клиенты, заявки и сделки

- Client archive и мягкий DELETE требуют `clients:delete`; `clients:update`
  недостаточно. Сервис проверяет незавершённую работу, включая косвенно связанные
  задачи и Inbox. Restore не означает reopen или отмену прежних результатов.
- Duplicate preview и merge используют существующие сервисы; сохраняются
  связи, ledger, история и audit. Совпадение имени не доказывает идентичность.
  Нельзя делать скрытый merge или hard delete ради устранения дубля.
- Lead требует клиента; loss — причину. Разрешённые переходы определяются
  `ALLOWED_LEAD_STATUS_TRANSITIONS`; конвертация использует существующую сделку
  при повторе и сохраняет происхождение. Не создавать вторую Lead→Client модель.
- Стадия Deal принадлежит тому же Business и pipeline. Won/lost/reopen,
  изменение суммы и ответственного идут через сервисы с историей; lost требует
  причину. Требуемые поля стадий, действительность пользователя и ограничения
  переходов проверяются на сервере. Не превращать черновое предложение строгого
  графа D-08 в новый обязательный режим.
- Assignee/owner/responsible/watcher — активный участник того же Business с
  допустимой областью назначения. Отключённый вход не переносит работу владельцу
  автоматически. Старые записи/история сохраняются.

Код: [client lifecycle](../../apps/clients/lifecycle.py),
[merge](../../apps/clients/services.py), [leads](../../apps/leads/services.py),
[deals](../../apps/crm/services.py), [archive](../../apps/core/archive.py).
Регрессии: [clients](../../apps/clients/tests.py),
[leads](../../apps/leads/tests_crm_light.py), [deals](../../apps/crm/tests.py),
[archive](../../apps/core/tests_archive.py).

## Специалисты и календарь

Специалист — существующий staff Resource с необязательным linked_user.
CRM-аккаунт, приглашение и seat не создаются автоматически. Известного специалиста
не дублировать, по имени врача не назначать legacy-записи автоматически.

Новая запись и перенос требуют активного специалиста и услуги того же Business.
Доступность учитывает длительность, индивидуальную неделю, исключения даты,
часовой пояс и пересечения. Исключение даты перекрывает неделю специалиста,
затем применяется бизнес-график; один интервал в день, без новой модели смен.
Слот повторно проверяется при сохранении. Legacy-записи без специалиста
сохраняются, но для переноса нужно выбрать активного специалиста.

Отключение входа не деактивирует Resource. Деактивация Resource запрещает новые
бронирования/переносы, не отменяет существующие визиты. При отсутствии управляющий
видит все доступные активные записи дня, вручную меняет специалиста/время или
отменяет с причиной. Закрытие окна не означает завершение разбора/уведомление.
Ошибку загрузки нельзя показывать как пустой список; pagination не должна скрывать
необработанные визиты. Причина отмены/неявки обязательна, история сохраняется.

Графиком управляет `settings:update`; визитами — соответствующие appointment
права и OWN/TEAM/BUSINESS. OWN специалиста выводится из активного same-business
`resource.linked_user`. Рассылка при отсутствии и учёт вместимости кресел
отложены, перенос и согласие клиента — разные состояния.

Код: [availability](../../apps/scheduling/availability.py),
[services](../../apps/scheduling/services.py),
[exceptions API](../../apps/scheduling/schedule_views.py).
Проверки: [schedule tests](../../apps/scheduling/tests_specialist_schedule.py).

## Задачи, уведомления и автоматизации

Task поддерживает start/done/cancel/reopen/undo-cancel, назначение, watchers,
срок/напоминание/snooze и связи с CRM. Cancel требует причину; при undo
используется записанный предыдущий статус. Доступ и актуальный исполнитель
проверяются до изменения. Задача не меняет lifecycle связанного визита/сделки.

Уведомление адресуется активному исполнителю. Для неназначенных задач используется
существующий менеджерский fallback и затем owner; настройки уведомлений
учитываются, high/urgent сохраняют своё исключение. Owner не получает каждое
сообщение по умолчанию. Напоминанию нужны worker очереди `notifications` и beat:
сохранённое время в БД не означает доставку.

AutomationRule/Run/условия/действия ограничены Business и capability. Управление
retry/cancel требует `automations:manage`. Условия используют явный allowlist
операционных полей/`payload.*`, не arbitrary ORM/Python traversal. Неизвестное
legacy-условие не должно давать действие. Поддержанные action types: create_task,
create_notification, assign_user, add_note, create_follow_up, wait; не обещать
webhook action только потому, что есть connector.

Запуск хранит dedupe identity, следующий action index, WAIT/retry и попытку claim.
Каждый worker проверяет владение текущей попыткой перед действием/записью;
устаревший worker не переигрывает эффект и не отменяет cancel. Отмена не откатывает
уже выполненное. Сервис task/notification/audit должен сохранять свою транзакционную
границу; правила не обходят AI approvals. Eager/local recovery не доказывает
Redis/PostgreSQL production recovery.

Код: [tasks](../../apps/tasks/services.py),
[notification tasks](../../apps/notifications/tasks.py),
[automation engine](../../apps/automations/engine.py),
[allowed conditions](../../apps/automations/condition_fields.py).
Проверки: [claim ownership](../../apps/automations/tests_claim_ownership.py),
[queue runtime](../../apps/automations/tests_queue_runtime.py).

## Деньги и аналитика

Ручной журнал регистрирует фактически полученные суммы/частичные оплаты и
возвраты; банковскую операцию не выполняет. Суммы положительные точные Decimal,
валюта бизнеса, время не в будущем. Связь — клиент и необязательная сделка
**или** запись того же клиента/Business, видимые актёру. Нельзя редактировать/
удалять денежные факты обычным CRUD. Возврат с причиной не превышает остаток
получения и не предшествует ему; refund of refund недопустим.

Долговечный submission ID и hash защищают retry; другой payload под тем же ID
отклоняется. Конкурирующие записи/refund блокируются на Business. Ledger/audit
пишутся атомарно. Merge сохраняет операции и цепочку возвратов. Более широкая
история клиента не раскрывает сумму/причину/заметку из денежной операции.
Нужны `payments:view/create/manage` и scope клиента/связанных сущностей.

Финансовый источник выбирается явно: manual или один external connector.
Manual считает все доступные операции точного периода в timezone бизнеса,
требует BUSINESS view для analytics/payments/clients; пустой журнал — ноль
зарегистрированных операций, не доказанная полнота бухгалтерии.
External требует проверенный локальный снимок точного периода/валюты,
связанный с успешным завершённым sync run, а не healthcheck/connected flag.
`FINANCIAL_SOURCE_READERS` на срезе пуст: live учётный источник не реализован.

Нет снимка — unavailable/null, не ноль. Ошибка обновления сохраняет доступный
проверенный снимок с предупреждением, источником и реальным временем; не
ослабляет права. Источники не складываются. Допустимы receipts/refunds/net,
не profit/debt; стоимость услуги, выигранная сделка и SaaS billing отдельно.
Обычные CRM-метрики доступны по своим правам без финансового коннектора.

Код: [ledger](../../apps/payments/services.py),
[financial metrics](../../apps/analytics/financial_metrics.py),
[manual totals](../../apps/analytics/manual_finance.py),
[reader registry](../../apps/integrations/providers/registry.py).
Проверки: [payments](../../apps/payments/tests.py),
[manual source](../../apps/analytics/tests_manual_finance.py),
[external contract](../../apps/analytics/tests_financial_sources.py).

## API и ошибки

Действующие маршруты — [router](../../config/urls.py), точные payload/action
контракты — профильные serializers/views и [frontend API](../../frontend/src/api).
Имена endpoints не дублируются огромной таблицей, которая отстаёт от кода.
Несовпадение approved rule и кода фиксировать как разрыв, не объявлять код нормой.

Безопасный envelope: `code`, `request_id`, `detail`, `errors`, `category`,
`retryable`, `retry_after_seconds`. UI ветвится по code, не raw detail.
Причины/поля санитизируются; нельзя раскрывать чужой tenant, токены или stack.
Retryability принадлежит серверу; временный HTTP-код не разрешает автоматически
повторять мутацию. Форму сохранять при конфликте/сбое; роль и область доступа
проверять повторно при исполнении. Контракт реализации:
[API exceptions](../../apps/core/exceptions.py),
[client normalization](../../frontend/src/api/appError.ts).

## Незакрытые решения и история

Same-client правила всех комбинаций связей, ранние terminal transitions,
строгий stage graph, приоритет built-in/user follow-up и часть аналитических
формул не утверждаются автоматически. См. [acceptance](acceptance.md).
Исторические доказательства и исходные предложения:
[CRM plan](../../archive_docs/2026-10-07/docs/crm/CRM_PRODUCTION_LAYER_PLAN.md),
[entity draft](../../archive_docs/2026-10-07/docs/crm/CRM_ENTITY_BEHAVIOR_CONTRACT.md),
[scheduling](../../archive_docs/2026-10-07/docs/crm/specialist-scheduling.md),
[payments](../../archive_docs/2026-10-07/docs/crm/client-payments.md).
Они сохранены для проверки происхождения, не для выдачи задач или старых правил.
