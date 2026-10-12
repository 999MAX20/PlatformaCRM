# Задачи, напоминания и автоматизации

Срез `768b2675`, 09.10.2026. Результат для сотрудника — видимый следующий шаг,
срок и ответственный; для управляющего — просроченная работа и управляемый retry.
Требования: [CRM](../current/crm.md), [доступ](../current/access.md).

## Текущие действия

Task поддерживает start/wait/resume/done/cancel/reopen/undo-cancel, assign/self-assign,
watchers, due date, snooze и связи с CRM. Отмена требует причину; undo использует
сохранённый предыдущий статус. Действие задачи не меняет lifecycle её визита/сделки.
Назначение требует активного участника Business; actions проверяют scope и права.
Activity/audit позволяют отличить изменение от простого чтения списка.

Обновление TASKS-REDESIGN-20261013: список и выбираемый правый инспектор/полная
карточка, мобильный экран, фильтры «Мои/Все/Созданные/Наблюдаемые», группы срока,
командные количества, явное редактирование и сохранение черновика после ошибок.
Ожидание хранит причину и необязательную дату напоминания; срок не переносится.
Версия/ключ команды защищают от устаревшей записи и повтора эффекта. Ответственный
проверяется единообразно; специалист без входа остаётся контекстом. Operator и
specialist создают себе, custom/legacy права сохранены. Evidence и публикация —
[checkpoint](../testing/task-state/PRIMARY-SESSION.md#tasks-redesign-20261013--approved-task-workspace-and-domain-behavior).

AutomationRule/Condition/Action/Run используют Business и capabilities.
Условия ограничены allowlist; неизвестное legacy-условие не должно запускать действие.
Есть create_task, create_notification, assign_user, add_note, create_follow_up, wait.
Webhook action не следует из наличия интеграционного endpoint. Управление retry/cancel
требует `automations:manage`; automation не обходит approvals AI или права CRM.

## Очередь и ошибки

Run хранит dedupe identity, индекс действия, WAIT/retry и текущий claim. Устаревший
worker не должен переиграть effect или перезаписать cancel; отмена не откатывает
уже выполненное. Напоминанию нужны notifications worker и beat: срок в БД не доставка.
Внутренние уведомления идут активному исполнителю, затем существующему manager/owner
fallback для неназначенной работы; owner не получает всё. NORMAL учитывает личные
предпочтения, HIGH/URGENT сохраняют принятое исключение.

## Код, UI и evidence

[Task services](../../apps/tasks/services.py), [engine](../../apps/automations/engine.py),
[conditions](../../apps/automations/condition_fields.py),
[claim tests](../../apps/automations/tests_claim_ownership.py),
[queue tests](../../apps/automations/tests_queue_runtime.py),
[Tasks UI](../../frontend/src/features/tasks/TasksPage.tsx),
[Automations UI](../../frontend/src/features/automations/AutomationsPage.tsx),
[API](../../frontend/src/api/automations.ts).
UI `/app/tasks`, `/app/automations`; API tasks/automation-rules/automation-runs.
[Settings evidence](../testing/settings-functional-20261008.md) проверяет потребителей
предпочтений; [операционный UI](../testing/ui-operations-20261008.md) — scoped queues.

## Цель и ограничения

[R01](../current/roadmap.md): D-04/V1-O09 при пересечении встроенного follow-up,
импорта и правила; новая политика не выбирается автоматически. R04 — target
Redis/PostgreSQL/recovery; local/eager тесты этого не доказывают. R05 — рабочий цикл.
09.10 — паспорт опубликованной основы, без новых запусков правил/очередей.
