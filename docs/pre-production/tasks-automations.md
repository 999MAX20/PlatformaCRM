# Задачи, напоминания и автоматизации

Граница аудита 17.10 (`56dd124`): наличие engine/leases не закрывает создание
частичного активного правила, пустой состав, неполную проверку конфигурации и
ошибки истории UI. После исправлений AUD-06/04/05 пункт AUD-07 и offline task replay AUD-10 открыты в
[roadmap](../current/roadmap.md#project-audit-20261017);
[методы проверки](../testing/project-audit-20261017.md). Task command idempotency
не доказывает её использование offline-клиентом. В AUD-01 изолированы локальная
очередь и callbacks сессии; capacity/drop, durable idempotency и recovery UX
AUD-10 этим не закрыты. Logout/expiry удаляют pending queue.

Исходная основа `768b2675`, 09.10.2026; актуальные дельты 16.10 описаны ниже.
Результат для сотрудника — видимый следующий шаг,
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

AUD-06 — выполнено полностью в локальном scope, 19.10: единая проверка action config в preview/save/CRUD/activate/execute,
включая права, активных участников, trigger и типы полей. Пустой состав не включается;
предметная форма заменяет JSON, ошибки относятся к полям, изменение ввода сбрасывает
preview. Member loading/error/retry сохраняет ввод. Подтверждены scoped backend и
browser RU/KK/EN desktop/mobile; версия/команды/пропуски —
[AUD-06 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-06-20261019--executable-automation-action-configuration).
Остатка кода/доказательств в AUD-06 нет; редактор закрыт отдельно в AUD-05, история
(AUD-07), реальные worker/provider/deployment остаются за его границей.

AUD-04 — выполнено полностью в локальном scope, 19.10: create-manual/apply-template и PUT configuration существующего
правила используют общий атомарный сервис с audit/activity. Сбой условия, действия
или истории откатывает состав и поля. Generic rule/child CRUD разделяет Business
lock; последнее действие активного правила нельзя удалить/перенести. PostgreSQL
подтверждает гонки delete/delete и activate/delete. Полная замена принимает manual
payload и требует UPDATE исходного правила; response сохраняет прежнюю rule-схему.
Контракт/defaults — [CRM](../current/crm.md), версия и точные проверки —
[AUD-04 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-04-20261019--atomic-automation-configuration).
Редактор закрыт отдельно в AUD-05 ниже. Версионирование
конфигурации выполняющегося Run не добавлено; рабочие данные не мигрировались.

AUD-05 — выполнено полностью в локальном scope, 19.10: существующее правило можно открыть, изменить, проверить и сохранить
из карточки; простой черновик автоматически ведёт в редактор. Detail preview
использует UPDATE без требования CREATE/квоты нового правила. Загрузка/retry,
ошибки сохранения, защита от старого preview, сохранение typed values и
настроек действий проверены; полный локальный сценарий создал одну реальную Task.
Focused30, affected153 (150 PASS, 3 PG-only skip), system/migration drift,
frontend helpers4, browser RU/KK/EN desktop/mobile и build/types/i18n/bundle PASS.
Версия и точные команды — [AUD-05 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-05-20261019--reachable-automation-rule-editor).
Остатка кода/доказательств/решений в scope нет; AUD-07, live worker/providers
и deployment отдельно. Рабочая БД не менялась.

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

[S01](../current/roadmap.md): D-04 утверждён владельцем 14.10 — create_follow_up
для terminal-визита использует встроенную задачу без перезаписи; create_task
остаётся отдельным действием. Существующая история создания идентифицирует
встроенную задачу, Business/Appointment locks сериализуют lookup/create.
Регрессии: [policy](../../apps/automations/tests_follow_up_policy.py),
[concurrency](../../apps/automations/tests_follow_up_concurrency.py).
Другие сценарии V1-O09/импорта не получают новой политики. R04 — target
Redis/PostgreSQL/recovery; local/eager тесты этого не доказывают. R05 — рабочий цикл.
09.10 — паспорт опубликованной основы, без новых запусков правил/очередей.

Сверка 16.10: S04 уже подтвердил recovery на реальных, но изолированных
PostgreSQL/Redis/Celery. Упоминание local/eager выше не означает отсутствие этого
evidence; целевая production-среда, её task routes/alerts и R04 ещё не приняты.
