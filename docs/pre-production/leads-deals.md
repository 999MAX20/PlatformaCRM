# Заявки, сделки и воронки

Исходная основа `768b2675`, 09.10.2026; актуальные дельты описаны ниже.
Lead хранит потребность клиента, Deal — коммерческую
возможность. Оператор обрабатывает обращение, управляющий распределяет работу
в своей области. Контракт: [CRM](../current/crm.md); публикация не равна production.

## Реализованный цикл

Lead: создать с клиентом → назначить/взять в работу → контакт → запись, сделка
или follow-up → закрытие/lost с причиной. Повторная конверсия использует существующую
сделку и сохраняет происхождение. Новая заявка не создаёт параллельную модель клиента.
Deal: список/kanban → стадия своей воронки → следующий шаг → won/lost/reopen.
Для стадии, суммы и ответственного есть сервисные действия с историей.
AUD-13: generic PATCH/PUT проверяет UPDATE исходной заявки и переназначает через
assign_lead с действующими scope/role/availability и атомарной историей/уведомлениями;
AUD-20 проверяет начальное состояние API/import через доменные creation services:
LOST требует причину; время/автор и начальная история управляются сервером.
Won не регистрирует фактическую оплату и не завершает визит автоматически.

Pipeline/PipelineStage имеют Business; сервис сделки проверяет соответствие стадии
воронке. AUD-15, 19.10: generic API стадий/переходов проверяет Business и pipeline
всех связей при POST/PUT/PATCH; перенос существующей стадии запрещён, обычные поля
редактируются. Частичный PATCH проверяет и прежние значения. Допустимая конфигурация,
move-stage и board сохранены; scope/версия/проверки — checkpoint AUD-15-20261019.
Старые рабочие данные не мигрировались, строгий stage graph не вводился.
Требуемые поля стадии проверяются сервером. Lead status следует существующему
`ALLOWED_LEAD_STATUS_TRANSITIONS`, а не произвольному PATCH. Назначаемый сотрудник
активен в том же Business; AUD-13 применяет assignment policy и в generic PATCH.
Owner-исключение сохраняется; неизменённый ответственный не проходит повторное
назначение и не создаёт уведомления. Null не снимает существующее назначение;
обычное редактирование уже неназначенной заявки допустимо. Команды, версия,
локальная проверка и граница публикации — checkpoint AUD-13-20261017.
AUD-02 проверяет default_responsible_user через assignment policy и повторно
при capture, включая отключённого после загрузки аккаунта пользователя.
Недопустимый default даёт контролируемую ошибку без частичного Client/Lead;
submissions/error журналы доступны через API/admin только для чтения.
Версия и проверки — checkpoint AUD-02-20261017; старые записи не мигрировались.
AUD-19 исправляет разрешение Business через form для CRUD полей и истории.
Редактор доступен из «Заявки → Ещё → Формы заявок», с текущими правами LEADS и
RU/KK/EN. Отдельный кандидат поверх acb8687e: backend80/system/drift, frontend
build/types/options2 и targeted browser PASS; рабочие миграции/deployment не выполнялись.
Версия, публикация и CI —
[AUD-19 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-19-20261029--lead-form-field-tenant-resolution-and-editor-verified). Поиск/выбор остаётся AUD-08. AUD-10 добавляет durable keys для заметок/задач,
отказ без потери ввода при storage error, видимый conflict/retry/discard и достижимые
формы в карточке. Replay/окно1ч и текущие права — [контракт](../current/frontend.md#offline-данные-заявок--aud-01-17102026);
опубликовано8d710f03 после OFFICIAL18 bae967bd; remote SHA подтверждён, CI40957243699 выполняется.
Проверки точного кандидата и ограничения — AUD-10-20261030 в PRIMARY. AUD-01 реализует изоляцию offline-кэша и очереди
по пользователю/Business/правам, очистку при logout/expiry, замену пустым ответом
и fallback только при временной/сетевой ошибке. Это до 50 ранее загруженных строк,
не полная offline-база; pending queue очищается вместе с сессией.
Версия и проверки AUD-01/02/13 — checkpoint; остальные исправления открыты в
[едином roadmap](../current/roadmap.md#project-audit-20261017);
[evidence 17.10](../testing/project-audit-20261017.md) на `56dd124`.

## Ошибки и восстановление

Дополнение CRM-S01, 14.10: сервисные команды и обычные изменения заявок/сделок
атомарны с историей/аудитом; состояние перечитывается под блокировкой. Точный
повтор terminal-команды не портит previous_status/previous_stage. Старая копия
сделки не затирает новую сумму при переходе; quick terminal actions соблюдают
обязательные поля стадии. Некорректная сумма отклоняется до записи. Повтор
Lead→Deal проверяет текущую область просмотра сделки и видимость полей.
Регрессии — [server scenarios](../../apps/core/tests_crm_server_scenarios.py) и
[PostgreSQL concurrency](../../apps/core/tests_crm_server_concurrency.py);
точные версии/проверки и оставшаяся граница —
[checkpoint](../testing/task-state/PRIMARY-SESSION.md#crm-s01-20261014--server-scenario-completeness).

Неверная стадия/связь/назначение или отсутствующая причина отклоняются до перехода.
Tenant и per-record права обязательны в списке, board и вложенных карточках;
AUD-13/15/20 закрыты в своих локальных scope; новый строгий stage graph —
отдельное решение D-08. API сделки согласует начальный status со стадией, проверяет
required fields/роли и пишет initial history. Обычная UI-форма предлагает только
активные открытые стадии. Подробности и проверки — [AUD-20 checkpoint](../testing/task-state/PRIMARY-SESSION.md#aud-20-20261021--initial-lead-and-deal-lifecycle-invariants).
Reopen — отдельное действие, не редактирование terminal timestamps. Ошибка UI не
должна уничтожать введённые поля или изображать успешный переход; API envelope
и общие recovery-компоненты принадлежат [frontend-контракту](../current/frontend.md).
Отключение логина не перераспределяет заявки и сделки автоматически.

## Карта реализации и evidence

[Lead services](../../apps/leads/services.py), [Deal services](../../apps/crm/services.py),
[Lead tests](../../apps/leads/tests_crm_light.py), [Deal tests](../../apps/crm/tests.py),
[API leads](../../frontend/src/api/leads.ts), [API deals](../../frontend/src/api/deals.ts),
[Lead UI](../../frontend/src/features/leads/LeadsPage.tsx),
[Deal UI](../../frontend/src/features/deals/DealsPage.tsx).
Маршруты `/app/leads`, `/app/deals`; API `/api/leads/`, `/api/deals/`,
`/api/pipelines/`, `/api/pipeline-stages/` и профильные actions.
Обновления связанных work queues проверялись в
[операционном пакете](../testing/ui-operations-20261008.md), не как полная сертификация.

## Цель и вопросы

[R01](../current/roadmap.md) закрыт в принятом scope; оставшиеся D-03/D-08 и
BE-GAP-003 рассматриваются только по конкретному новому сценарию; R05 — реальный рабочий цикл. Новый строгий stage graph и fallback pipeline
не утверждены самим наличием StageTransition. Новые требования относятся к D06 roadmap.
09.10 — паспорт существующего поведения; новые прогоны и изменения domain не выполнялись.

Сверка 16.10: CRM-TOOLBARS реализует общие фильтры/Все–Мои и серверные workspace
selectors; R01 закрыт в принятом scope. D-03/D-08 и BE-GAP-003 выше — оставшиеся
конкретные границы, а не утверждение, что прежний R01 целиком не выполнен.
S01 закрывает свою матрицу; новый stage graph/исправление истории не запущены.
