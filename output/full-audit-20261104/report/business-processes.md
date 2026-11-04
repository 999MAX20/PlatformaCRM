# Бизнес-процессы и инварианты

Каталог описывает фактическое поведение текущего среза, включая legacy API и
внутренние сервисы. Наличие реализации не означает согласованное обещание
продукта. Соответствие требованиям проверяется отдельно; нерешённые политики
не превращены в дефекты только по наличию полей модели.

Основной подробный каталог: [backend/business-processes.md](../backend/business-processes.md).
Он охватывает identity, Business/team/roles, файлы/import/export, клиентов,
заявки/сделки, записи/ресурсы/планы, задачи, филиалы/услуги, историю/сегменты,
платёжные записи, pricing/billing, аналитику, автоматизации, уведомления,
ботов/Inbox, AI, интеграции, onboarding, рассылки и поддержку.

Для413 производственных модулей с публичными callable сохранён
[process-module-catalog.json](../backend/process-module-catalog.json): назначение,
входы/выходы, эффекты, вызовы, ошибки, связанная проверка и семантическая заметка
полного чтения. Включены существующие процессы без найденного утверждённого
основания; они не получают молчаливого одобрения через этот отчёт.

Существенные команды собраны в
[semantic-transition-registry.json](../backend/semantic-transition-registry.json):
59 графов для38 сущностей, guards и эффекты по39 source files. Для13 графов
выполнены89 явных allowed/forbidden случаев;45 связаны с именованными assertions
и результатами; для PricingAlert исполнены оба хранимых исходных состояния.
[Validator](../backend/semantic-transition-validation.json) не нашёл ошибок
связи. Это не все комбинации ролей, данных и внешних отказов.

Права сохраняются условными: [role-permission-matrix.csv](role-permission-matrix.csv)
не выдаёт680 статических строк за680 исполненных тестов. Membership, overrides,
module visibility, own/team, branch и money rules могут изменить итоговое решение.
Жизненный цикл, авторизация и побочные эффекты проверяются совместно в named
scenario evidence, а не выводятся из enum модели.

Сквозные процессы проходят через UI → API/domain → audit/activity/events → jobs
и delivery. Частичный UI save, повторная доставка, worker claim и восстановление
имеют отдельные доказательства. Реальная provider delivery, целевое deployment
и native device не подтверждены локальными stubs. Эксплуатационные процессы
backup/restore, restart, AV/retry и очереди описаны в [operations.md](operations.md).

UI action/state и требования сверены: [3014 UI instances](routes-and-ui.csv),
[1557 исходных утверждений](../requirements/requirements.csv),
[итоговый validator](../completion-validation.json). Это полное статическое покрытие
с названными runtime receipts, а не все сочетания ролей/состояний или внешняя приёмка.
