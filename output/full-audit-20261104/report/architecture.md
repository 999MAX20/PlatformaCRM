# Карта реализации

Приложение — React web-клиент и Django/DRF backend с отдельными Celery workers,
публичным widget и optional notification ASGI stream. Данные бизнеса принадлежат
Business либо выводят scope через связанные сущности. Исторический native-клиент
рассматривается отдельно; наличие его исходников не означает поставляемую текущую
mobile-сборку. Market изучается только как связанный контракт.

## Основные границы

| Слой | Реализация и назначение | Детальная карта |
| --- | --- | --- |
| Web entry/router/layout | frontend/src/app, общая оболочка, auth/role guards, lazy feature routes | ui/route-action-state-static.json, ui/state-declarations.csv |
| UI → API | frontend/src/api, общий transport/query client, feature hooks | ui source journal и зависимости; runtime-scenario-register.json |
| HTTP ingress | config/urls.py, DRF routers, explicit auth/platform/public/widget/webhook/file routes | backend/registered-endpoints.json, backend/registered-view-classes.json |
| Domain behavior | apps/* services/selectors, lifecycle helpers, текущие permissions и field projections | backend/module-registry.json, backend/behavior-node-registry.json |
| Data/schema | Django models, constraints/indexes и migrations | backend/migration-registry.json и model/runtime registry |
| Jobs/events | Celery wrappers, beat, BusinessEvent/activity/audit, notification and provider effects | backend/job-registry.json, backend/event-registry.json, backend/effect-site-registry.json |
| AI | assistant/analyst/context/tools, approval и execution paths, agent configuration | apps/ai_core и backend/transition-table-registry.json |
| Integrations | provider adapters, inbound signature/replay, durable outbound/retry, import/export | apps/integrations, apps/core; semantic transition registry |
| Runtime/deployment | WSGI/Gunicorn, optional ASGI, Compose/Caddy/stand gate | [operations.md](operations.md), [root evidence](../architecture-root.md) |

Пути реестров в таблице относительны родительскому каталогу этого отчёта. Реестры
сохраняют source path, symbol/ranges и связи; AST вызов или import сам по себе
не доказывает выполнение. Dynamic registrations и route callbacks разобраны
отдельно. Тестовые/mocked эффекты не называются реальной доставкой провайдеру.

## Доменные области

Accounts и Businesses задают identity, sessions, membership, роли, field access,
availability/routing и platform administration. Branches/Services/Scheduling
задают места, каталог, специалистов/ресурсы, часы, записи и планы посещений.
Clients/Leads/CRM/Tasks/Activities обслуживают клиентские карточки, воронки,
переходы, задачи, заметки/теги/сегменты и историю. Analytics/Core строят производные
карточки, очереди, отчёты, import/export и health/readiness.

Bots/Conversations связывают каналы, Inbox, диалоги и подтверждённые CRM-действия.
Integrations изолирует поставщиков и внешние контракты. Notifications и Outreach
отвечают за персональные состояния/доставку и аудитории кампаний. Automations
выполняет условия/действия и ожидания; AI Core готовит grounded ответы и действия
с отдельной approval boundary. Billing/Payments/Pricing имеют разные назначения:
платформенный billing, платёжные записи и marketplace pricing нельзя объединять
в утверждение о готовом денежном контуре. Onboarding и Support обслуживают
настройку и обращения; их фактические эффекты входят в общий каталог процессов.

## Связи и ограничения доказательств

Python graph содержит989 текущих модулей и12076 import edges. После отделения994
function-local imports от immediate/conditional edges многомодульных SCC в
последнем графе нет. Большой SCC исходного графа не является доказанным startup
cycle. Размер модуля, отсутствие текстового вызова и импорт через barrel также
не достаточны для вывода о мёртвом коде или необходимости переписывания.

У API нормализованы976 операций из1804 raw route/method rows; format-suffix
дубликаты сохранены в сыром реестре. Отдельно связаны4170 production behavior
nodes,888 state-write sites и1296 potential effect sites. Это объём статической
карты, не число пройденных runtime-ветвей. На стороне UI учитываются95 routes,
2279 control sites и735 state sites; render matrix не заменяет проверку всех
действий. Семантические переходы, permissions и проверки связаны в итоговых
реестрах; [структурная сверка](../completion-validation.json) прошла без ошибок.
Статическое покрытие не подменяет ограничения динамического выполнения.

Главные обнаруженные нарушения проходят через границы слоёв: производная
аналитика обходит ограничения исходного ресурса; multi-request UI сохраняет
частичный результат без восстановления; повтор после ambiguous delivery меняет
idempotency identity; worker selection не всегда повторяет lifecycle/claim checks;
поставляемая топология не содержит consumers трёх очередей. Каждый вывод требует
своего source/probe receipt; общая архитектурная схема не заменяет эти доказательства.
