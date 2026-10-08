# Действующая документация PlatformaCRM

Начать с [STATUS](../STATUS.md) и [карты реализации](pre-production/capabilities.md).
Читать только профильный контракт и выбранный checkpoint. Ниже — закрытый
реестр текущих источников; машинный вариант — [documentation-index.json](documentation-index.json).
Паспорт описывает реализацию и доказательства, контракт — требования, процедура —
порядок работы. Ни один из них сам по себе не назначает новую задачу.

| Вопрос | Действующий источник |
| --- | --- |
| Что строим и что отложено | [Продукт](current/product.md) |
| Что реализовано и где код | [Паспорта](pre-production/README.md), [карта модулей](pre-production/capabilities.md) |
| Что ещё не принято / не решено | [Приёмка](current/acceptance.md) |
| CRM, запись, задачи, деньги, автоматизации | [CRM](current/crm.md) |
| Tenant, роли, MFA, сессии, поддержка | [Доступ](current/access.md) |
| AI, знания, подтверждения, безопасность клиента | [AI](current/ai.md) |
| Интерфейс, состояния, typography/tokens | [Frontend](current/frontend.md) |
| Connectors, импорт/экспорт, реальные каналы | [Интеграции](current/integrations.md) |
| Среда, worker, AV, backup, production boundary | [Эксплуатация](current/operations.md) |
| Архитектура изменений | [Инженерные правила](current/engineering.md) |
| Выполнение задачи | [AGENTS](../AGENTS.md), [шаблон](testing/CODEX_TASK_TEMPLATE.md) |
| Точные проверки и изоляция | [Testing](testing/testing.md), [UI toolkit](testing/ui-testing-toolkit.md) |
| Текущая задача и передача | [Checkpoint](testing/task-state/PRIMARY-SESSION.md), [handoff](../actual_docs/PROJECT_HANDOFF.md), [протокол](testing/SESSION_ROLLOVER.md) |
| Регрессионные прецеденты | [ZR rules](../actual_docs/DEFECT_KNOWLEDGE_BASE.md) |
| Evidence операционного UI-пакета 08.10 | [Проверки шести экранов](testing/ui-operations-20261008.md) |
| Evidence / предложение по странице подключений 08.10 | [Функциональный анализ и редизайн](testing/integrations-functional-review-20261008.md) |

## История и новые документы

[Архив](../archive_docs/README.md) содержит старые тела и manifest с SHA256.
Он исключён из обычного поиска. Историческую ссылку открывать только для точного
evidence; она не возвращает старый документ в действующие инструкции. Текущие
контракты уже сохраняют последние решения и открытые обязательства.

`actual_docs/UNIFIED_FALLBACK_INVENTORY.generated.md` — машинный каталог по
стабильному пути, не спецификация и не PASS. Не редактировать вручную.
Технические backend/frontend README — карты исходников, не независимая политика.
Навигация `.agents/skills` обновлена на этот набор контрактов.

Новое поведение обновляет существующий контракт и соответствующий паспорт.
Новая долговечная страница требует явного назначения и регистрации роли здесь
и в JSON. Детальное evidence хранится в выбранном task checkpoint/report с SHA,
командами, средой и ограничениями; не раздувать STATUS/README историей прогонов.
Не добавлять redirect-файлы на каждый архивный путь и не восстанавливать старые
планы только потому, что их упоминал прежний чат.
