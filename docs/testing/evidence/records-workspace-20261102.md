# RECORDS-WORKSPACE-20261102 — первый рабочий цикл «Записей»

Поручение: реализовать первый результат R01, затем перепроверить фактическую
реализацию, зафиксировать её и продолжить незакрытые пункты. Это работа чата
«PlatformaCRM UI» по Записям; аудит UIUX и референсы алертов не являются её результатом.

Срез: 02.11.2026, `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, HEAD `e02a28f550e94a543c3d88acac7c1b19ee48f90b` + локальный
task diff поверх сохранённого чужого WIP. Исходные dirty paths/hashes/before-копии,
команды и логи сохранены в `output/records-workspace-20261102/`.
Финальный manifest фиксирует полные файлы кандидата, но не объявляет весь их diff
собственной работой: часть файлов содержит прежние изменения других задач.

## Наблюдаемый результат

Основная страница `/app/appointments` и карточка `/app/appointments/:id` используют
существующий Appointment. Список имеет серверные поиск/фильтры/пагинацию/сортировку,
период Business timezone и полный итог по состояниям. Created/rescheduled/confirmed
составляют «Запланировано»; подтверждение показано отдельно. Завершение, отмена,
неявка и перенос используют существующие доменные команды и версию записи.

Клиент, Inbox, календарь, поиск и новые задачи ведут в эту модель. Lead/Deal не
создаются как техническая предпосылка нового визита. Старые сущности, события,
импорт, API и исторические правила не удалены и не конвертированы. Их URL открывают
безопасный просмотр реальных связей, а не старые рабочие страницы/воронки.

Early completion требует причины и actor; activity/audit сохраняют причину и время.
Ошибка откатывает доменный переход и эффекты, повтор не дублирует их. Перенос после
409 сохраняет введённые поля и позволяет перечитать актуальную версию/слоты.
Задача из карточки Appointment связывается с ним, а не с последней заявкой клиента.

## Матрица фактических потребителей

Пути frontend ниже относительно `frontend/src`, backend — корня репозитория.
Все действия сохраняют действующие module/object/field/Business/branch guards;
кнопки не служат заменой серверной авторизации.

| Файл / вход | Прежний сценарий → результат | Доступ и доказательства |
| --- | --- | --- |
| `app/merchantRoutes.tsx`, `routeLoaders.tsx`, `routeMetadata.ts` | Рабочие Lead/Deal routes → `LegacyRecordsPage`; новые list/detail Appointment; старый `calendar/:id` остаётся совместимым alias карточки | Route permission сохранён; owner/specialist browser, прямой чужой ID → 404 без данных |
| `components/layout/Sidebar.tsx`, `MobileNav.tsx`, `lib/startPage.ts` | Основные ссылки Lead/Deal → Записи; старое сохранённое start_page=leads читается как Записи без миграции preference | Текущий appointments VIEW; RU/KK/EN desktop/mobile |
| `GlobalSearch.tsx`, `CommandPalette.tsx`, `hooks/useRecordSearch.ts` | Локальные Lead/Deal результаты/команды → серверный paged поиск Appointment, create/open по его ID | Actor/Business/query key, debounce, error/retry/show-more; browser поиск и API scope tests |
| `features/calendar/RecordsPage.tsx`, `recordFilters.ts`, `RecordsTable.tsx`; `apps/scheduling/record_workspace.py` | Новый список и pipeline, полный summary до пагинации; client/pending-result drilldown не ограничен сегодня | 12 workspace cases в record-card-scope; Node filters; browser смена даты/сброс/сеть/390px |
| `AppointmentWorkspacePage.tsx`, `AppointmentRescheduleForm.tsx`, Calendar commands/dialog | Confirm/complete/cancel/no-show/reschedule/repeat на одном ID, отдельная причина раннего завершения; refresh после stale | Commands/completion/PG races; browser create/early complete/cancel/no-show/repeat/stale/Calendar |
| `features/clients/ClientWorkspacePage.tsx`, `ClientWorkspaceSections.tsx`, drawers client/config/shell | Основное действие → запись; новые Lead/Deal действия/секции убраны; история клиента сохранена | Текущий Client/Appointment доступ; browser create из клиента, shared-card tests |
| `features/conversations/ConversationsPage.tsx`, `InboxCustomerContext.tsx`, `PipelineConfirmationDialog.tsx` | Новая работа → выбранный Client + Appointment с source_conversation; Lead/Deal create/convert не предлагаются | Conversation VIEW/UPDATE + Client VIEW + Appointment CREATE; browser provenance, commands/AI suites |
| `apps/core/crm_cards.py`, `components/crm/CrmEntityDrawer.tsx` и drawers | Primary Appointment читает только фактическую Lead-связь, свои задачи/события и source conversation; не подставляет последнюю заявку/задачи клиента | Regression: null Lead/Deal, чужие задачи/события исключены; shared core card suite |
| `features/tasks/components/TaskEditor.tsx`, `drawers/EntityTasksPanel.tsx`, `TasksPage.tsx`, `taskWorkspaceQueries.ts` | Новая связь с записью; legacy редактирование сохраняет прежние связи; full-list/task create сохраняет appointment_ids | Backend tasks guards переиспользованы; browser exact Appointment binding, Node query/invalidation |
| `features/dashboard/*`, `apps/core/{work_queues,operational_dashboard}.py` | Новый workflow=appointments убирает lead/deal очереди; expired planned records требуют результата | Record queue + existing queue tests; метрики полные, source links канонические |
| `features/analytics/*`, `apps/analytics/{workspace,workspace_export}.py` | Appointment source/responsible/completion/no-show; отдельные records_* CSV schemas, старые exports сохранены | Record metrics + workspace suites; browser 5=3 planned+1 cancelled+1 no-show, 20%; деньги не переименованы из Deal |
| `features/automations/{AutomationsPage,AutomationTemplates,useAutomationEditor}.tsx/ts` | Новые формы default appointment_created, новые Lead/Deal triggers/templates скрыты; существующие правила/история доступны с прежним смыслом | Existing owner-run authority и lifecycle suites; browser new trigger menu без Lead/Deal; нет автоматического выключения/перепривязки |
| `apps/ai_core/{assistant,crm_planner,crm_writes,crm_tools,crm_transitions,conversation_router,tool_registry,recommendations}.py` | Новый визит через create_record, обязательный специалист, подтверждённая причина раннего завершения; default suggestion не создаёт Lead; owner brief workflow=appointments | AI creation/replay/no Lead/Deal, revocation after approval, reason audit, pending scope; dependent AI85 |
| `apps/scheduling/services.py`, `apps/automations/engine.py`, `features/timeline/timelinePresentation.ts` | Новые ссылки → `/app/appointments/:id`; старые факты Lead/Deal ведут в исторический resolver; старые calendar links сохраняют действующую совместимость | Domain effects/notification/automation tests; Node timeline filters/routes. Notification transport/personality refactor — чужой WIP, не результат этой задачи |
| `features/calendar/LegacyRecordsPage.tsx`, `LegacyAssignment.tsx`; `apps/scheduling/legacy_record_links.py` | Фактические связи Lead/Deal→Appointment с пагинацией; source-only разрешённый просмотр, files/notes/custom fields/history; ручное переназначение для retirement | Archived/multi(27)/hidden-source/no-grant tests; browser old Lead2→actual Appointment4; исторический статус не объявляется статусом записи |
| `LegacyRecordsPage.tsx`, `api/importExport.ts`, `features/settings/sections/CustomFieldsSection.tsx`, `features/resources/components/SpecialistLifecycle.tsx` | Импорт/формы/CSV/export history и retirement dependencies остаются достижимыми через исторический контекст | Browser import/forms/history entry; export endpoint200 + Node sync/202/malformed; импорт Lead не выдаётся за импорт Appointment |

## Проверки и границы

Изолированные SQLite и PostgreSQL17, synthetic fixtures, mock AI, блокировка
исходящей сети через safe runner; `.env` не загружалась. Рабочая `db.sqlite3`,
dev5173/8000, реальные каналы/пользователи и deployment не менялись.

Командный префикс backend:
`.venv/Scripts/python.exe output/records-workspace-20261102/run_candidate.py <label>`.
После него исполнялись команды в таблице; JSON receipts содержат exit0 и путь лога.
Прогоны пересекаются; их числа нельзя суммировать в число уникальных тестов.

| Receipt | Команда после префикса / результат |
| --- | --- |
| `record-card-scope` | `test apps.scheduling.tests_record_workspace.RecordWorkspaceTests apps.core.tests_crm_cards --noinput` — 21 PASS |
| `completion-focused` | `test apps.scheduling.tests_record_completion.RecordCompletionTests --noinput` — 5 PASS |
| `final-card-automation` | `test apps.core.tests_crm_cards apps.automations.tests apps.automations.tests_follow_up_policy --noinput` — 43 PASS |
| `dependent-ai-metrics` | `test apps.ai_core.tests_record_workflow apps.ai_core.tests_crm_tools apps.ai_core.tests_approval_binding apps.core.tests_work_queues apps.core.tests_record_queues apps.analytics.tests_record_metrics apps.analytics.tests_workspace --noinput` — 85 PASS |
| `scheduling-dependent` | `test apps.scheduling.tests apps.scheduling.tests_record_commands.RecordCommandTests apps.scheduling.tests_record_completion.RecordCompletionTests apps.automations.tests_follow_up_policy apps.automations.tests_action_validation apps.automations.tests --noinput` — 119: 116 PASS, 3 early-completion fixtures failed; все три исправлены и покрыты followups-corrected7 и final-card-automation43. Исходный failed receipt сохранён |
| `system-check`, `migration-drift` | `check`; `makemigrations --check --dry-run` — PASS, без новых миграций этого цикла |
| `postgres` | `.venv/Scripts/python.exe output/records-workspace-20261102/postgres.py` — 21 PASS: команды + last-slot, same-key replay, confirm/cancel и early-complete/cancel races; disposable PG остановлен |
| `frontend-focused-final.log` | Из frontend: `node --test scripts/tests/record-legacy-export.test.mjs scripts/tests/record-filters.test.mjs scripts/tests/route-prefetch.test.mjs scripts/tests/timeline-presentation.test.mjs scripts/tests/task-workspace.test.mjs scripts/tests/appointment-cache.test.mjs` — 21 PASS |

Frontend build/types/i18n: `npm run build` — exit0,
`frontend-build-verified.log`; i18n/types/app+widget PASS, chunk warning сохранён,
без переустановки зависимостей. Full-project E2E,
Storybook, live/provider и production performance не запускались: это scoped
функциональный цикл, а не release-кандидат. Backend PASS повторно использован
только при отсутствии последующих изменений относящегося исходника/окружения.

Browser доказательства: три create entrypoints; lost response503 после сохранения
→ сохранённые поля → повтор возвращает тот же Appointment3, read-only SQL подтверждает
одну строку без Lead. Реальная гонка двух вкладок: подтверждение меняет версию,
старый reschedule получает409, refresh сохраняет причину и позволяет выбрать слот
и перенести тот же ID. Early completion требует причины. Cancel/no-show terminal
скрывают недопустимые команды; repeat создаёт отдельный Appointment5. Calendar
показывает тот же no-show. Task имеет appointment3, lead/deal NULL.

RU/EN/KK проверены на затронутых list/card/form flow,390px список, keyboard date,
Escape Select→форма→возврат opener, поиск, error/retry, empty/reset. Specialist
видит одну собственную запись вместо пяти и не видит CREATE; чужая карточка404
не раскрывает данных и показывает недоступность. Это не полная локализация всех
исторических серверных шаблонов: их сохранённые названия/содержимое не переводились.

Артефакты локально: `card-en.png`, `list-kk-desktop.png`, `list-kk-mobile.png`,
`analytics-kk.png`, ранний `mobile-records.png`, `browser-runtime.log`.
CSV-кнопка получила200/381bytes от API и unit download path PASS; браузерный
download-event завершился timeout, файл скачивания не был независимо прочитан.
Чтение служебной страницы downloads запрещено browser policy и не обходилось.
Поэтому отдельный browser-file receipt не заявляется. Временная потеря вкладки,
CDP timeout и blank HMR восстановлены обычным созданием/перезагрузкой страницы.

Исправленные ранние проверки: неверные поля test fixtures role/capability,
event taxonomy dot вместо underscore; три будущих completion без обязательной
причины. Исходные логи сохранены; новые tests сохраняют lifecycle assertions.
Первый build упал на неверном пути timeline helper, импорт исправлен. Последующие
изменения UI потребовали итоговой сборки. Это не замена failed receipt старым PASS.

## Остаток и публикация

Первый Records cycle отделён от всего R01: планы/неназначенные этапы, пакетные цены,
авансы/зачёты/возвраты, полная D01 и live/release acceptance остаются следующими
обязательствами roadmap. Новая Record-модель, permission framework или денежный
статус не введены. README/setup, access/integration/operations contracts не требуют
новых изменений этого цикла: схемы/окружение/права/каналы не расширялись.

Публикация блокирована существующим `.git/index.lock` неизвестного владельца,
предшествующим чужим непубликованным `e02a28f5` и зависимостями от dirty prerequisite
изменений. Fresh fetch: origin/main `c74e0fa0d536a71eac7e7f0c4a79a385e19c9994`.
Индекс пуст; lock не удалён, чужой WIP не staged, commit/push/deployment не выполнены.
Нового CI нет. Эти ограничения не означают согласование публикации чужой работы.
Финальный статус scoped implementation/checks и остановка собственного runtime —
в [checkpoint](../task-state/PRIMARY-SESSION.md#records-workspace-20261102--implementation-in-progress).
