# Inbox и ручная работа с обращениями

Срез `768b2675`, 09.10.2026. Оператор видит обращения, отвечает и передаёт работу;
управляющий контролирует неотвеченное. [Клиентский AI](customer-ai-agent.md) — отдельный
участник этого процесса, обычная ручная CRM должна работать при его недоступности.

## Реализованный пользовательский цикл

Список/фильтры → переписка → прочтение/ответ/быстрый шаблон → сведения клиента,
будущие записи, связанные заявка/сделка → задача или запись. Компактный инспектор
содержит scoped-сущности и точные переходы. AI-действия у ответа, delivery — у сообщения,
CRM-действия доступны через меню/подтверждение; мобильная панель сохраняет черновик.
Применение QuickReplyTemplate заполняет composer и само ничего не отправляет.

BotConversation/BotMessage обслуживают Inbox; существующий Conversation-контур
не переименовывается и не объединяется миграцией этой документации. Связи ограничены
Business и разрешёнными объектами. При смене клиента несовместимые lead/deal связи
показываются в preview и снимаются после подтверждения; сущности и история сохраняются.
Подтверждение связано с actor/target/снимком; устаревшее требует нового preview.
Тот же клиент — no-op, совместимая смена — без лишнего подтверждения.

## Права и сбои

Сервер повторно проверяет conversations и доступ к новым связям. Скрытая сущность
не раскрывает имя в preview. Замена атомарна с activity/audit и инвалидирует прежний
qualification preview. Pause/resume AI требует conversations:update и ai_assistant:suggest;
resume — открытый диалог и readiness. Ошибка/timeout не доказывает доставку и не
разрешает слепое повторение внешнего effect. Human handoff и его уведомление имеют
локальную приёмку; канал остаётся отдельной границей.

## Техническая карта и доказательства

[Inbox service](../../apps/bots/inbox_service.py),
[client linking](../../apps/conversations/client_linking.py),
[UI](../../frontend/src/features/conversations/ConversationsPage.tsx),
[API](../../frontend/src/api/inbox.ts), [модели](../../apps/bots/models.py).
Reachable `/app/inbox`, backend `/api/inbox/conversations/` и профильные actions.
[Checkpoint](../testing/task-state/PRIMARY-SESSION.md) содержит завершённые
INBOX-INSPECTOR/MANUAL/RELINK; [локальный пилот](../testing/inbox-local-pilot-20261008.md)
и [live-model evidence](../testing/inbox-live-acceptance-20261008.md) сохраняют свои версии.
Settings-приёмка дополняет quick replies/предпочтения, не external delivery.

## Оставшиеся границы

[R02/R03](../current/roadmap.md): выбранный реальный канал и D-02/V1-O09 новых
входящих/replay; R04 — инфраструктура, R05 — персонал. Закрытый relink не утверждает
все новые same-client комбинации. 09.10 — составлен паспорт, новых сообщений не отправляли.
