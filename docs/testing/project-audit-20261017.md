# PROJECT-AUDIT-20261017 — результаты и границы проверки

Дата: 17.10.2026. Исходники: `56dd1243ef1ad5a4b15ddb94115aaaa6d2b0047a`,
`codex/ui-testing-toolkit`, канонический checkout PlatformaCRM.
Это evidence, а не второй backlog. Статусы и порядок исправления принадлежат
[единому roadmap](../current/roadmap.md#project-audit-20261017).

## Результат и метод

Сохранены исходные 12 пунктов AUD-01–12; дополнительный анализ дал восемь
подтверждённых по коду дефектов AUD-13–20. AUD-21/22 — отдельные риски,
которым нужны экспериментальные подтверждения. «Подтверждено по коду» не означает
runtime PASS. Исправления в этой фазе не выполнялись.

Первая проверка 16.10 использовала изолированные SQLite/API/Chromium сценарии.
Исходники с тех пор не менялись. Дополнение 17.10 — последовательное чтение
маршрутов, сериализаторов, permission helpers, сервисов и consumers с поиском
контрпримеров в тестах. Автономные другие чаты/агенты не привлекались.
Нет утверждения, что найдены все возможные ошибки или просмотрена каждая строка.

## Реестр доказательств

### AUD-01 — Кэш заявок раскрывает данные предыдущего аккаунта

Приоритет: **P1**. Метод: **browser**.
Источник: [frontend/src/features/leads/hooks/useLeadOfflineQueue.ts](../../frontend/src/features/leads/hooks/useLeadOfflineQueue.ts).

Браузер: A → выход → B → offline показал заявку A. Ключи localStorage общие; пустая загрузка не очищает старый кэш.

Критерий исправления: Разделить кэш по пользователю и Business; очищать при logout/смене контекста. Проверить A/B, пустую базу, offline и восстановление сети.

### AUD-02 — Чужие связи и подмена авторства заметок/событий

Приоритет: **P1**. Метод: **API + source**.
Источник: [apps/activities/serializers.py](../../apps/activities/serializers.py).

POST notes и activity-events с собственным business и чужими client/author/actor вернул 201. Дополнительный анализ LeadFormSerializer/Submission выявил аналогично непроверенные связи и default_responsible_user.

Критерий исправления: Все связанные объекты одного Business; автор из сессии; активный допустимый ответственный. Проверить POST/PATCH заметок, событий и форм; журнал submissions сделать управляемым сервером. Доступ ко всей чужой базе не доказан.

### AUD-03 — Внутренние заметки клиента доступны через общий API

Приоритет: **P1**. Метод: **API + source**.
Источник: [apps/clients/serializers.py](../../apps/clients/serializers.py).

GET клиента оператором вернул внутренние notes, хотя can_view_sensitive_field запрещает поле и Inbox его скрывает.

Критерий исправления: Применить одну политику чувствительных полей ко всем serializers/projections/экспорту; проверить owner/operator/custom role, list/detail/карточки.

### AUD-04 — Сбой создания автоматизации оставляет активный фрагмент

Приоритет: **P1**. Метод: **isolated fault injection**.
Источник: [apps/automations/views.py](../../apps/automations/views.py).

Искусственный сбой второго Action оставил активное правило с первым действием. create_manual/apply_template не объединяют запись состава транзакцией.

Критерий исправления: Атомарное создание/изменение состава; сбой любой части откатывает правило/действия/историю. Активация только валидного состава.

### AUD-05 — Простая форма создаёт включаемое правило без действий

Приоритет: **P2**. Метод: **API + source**.
Источник: [frontend/src/features/automations/AutomationsPage.tsx](../../frontend/src/features/automations/AutomationsPage.tsx).

Простая форма задаёт название/триггер, редактора состава карточки нет. API создал и включил правило с actions=0.

Критерий исправления: Достижимый редактор существующего правила и проверки активации; создать → настроить → проверить → включить → выполнить реальное действие.

### AUD-06 — Preview автоматизации принимает неисполняемую конфигурацию

Приоритет: **P2**. Метод: **API + source**.
Источник: [apps/automations/serializers.py](../../apps/automations/serializers.py).

assign_user с config={} получил valid=true, исполнителю нужен user_id. Проверка не покрывает полный контракт действий.

Критерий исправления: Обязательные поля/типы/связи/права каждого действия; предметные поля UI, понятные ошибки. Одинаковая проверка preview/save/activate/execute.

### AUD-07 — История автоматизаций скрывает ошибки и старые запуски

Приоритет: **P2**. Метод: **browser + source**.
Источник: [frontend/src/features/automations/AutomationsPage.tsx](../../frontend/src/features/automations/AutomationsPage.tsx).

При API 503 показаны ноль запусков и «Запусков пока нет». Отображаются восемь запусков, показатели берутся из страницы.

Критерий исправления: Разделить loading/error/empty, добавить retry; полная история/фильтры/пагинация и полные серверные показатели. Проверить 503 и несколько страниц.

### AUD-08 — Поиск и выбор клиента ограничены первой страницей

Приоритет: **P2**. Метод: **browser + source**.
Источник: [frontend/src/components/layout/GlobalSearch.tsx](../../frontend/src/components/layout/GlobalSearch.tsx).

На 57 клиентах старый существующий клиент не найден. Основная форма сделки использует clients.map из ограниченной выборки.

Критерий исправления: Серверный поиск и асинхронные селекторы с подгрузкой; проверить старый объект, разные страницы, пустой результат, ошибку и роль. Не загружать всю базу в браузер.

### AUD-09 — Показатели услуг используют неполные выборки

Приоритет: **P2**. Метод: **API + source**.
Источник: [frontend/src/features/services/ServicesPage.tsx](../../frontend/src/features/services/ServicesPage.tsx).

API для 101 услуги вернул 100 и next; экран считает активные/среднюю длительность по этой странице, использование — по странице записей.

Критерий исправления: Серверные агрегаты в той же области доступа; сверка на данных больше страницы, фильтрах/архиве/ролях.

### AUD-10 — Offline-очередь теряет действия и допускает повторы

Приоритет: **P2**. Метод: **source**.
Источник: [frontend/src/features/leads/hooks/useLeadOfflineQueue.ts](../../frontend/src/features/leads/hooks/useLeadOfflineQueue.ts).

При превышении 40 удаляется старейшая команда; очередь общая для аккаунтов. Создание задачи не использует устойчивый ключ. Сетевой дубль не воспроизводился.

Критерий исправления: Изоляция очереди, без молчаливой потери; стабильные command keys, replay/конфликт/ошибка и ручное восстановление. Проверить потерянный ответ после commit, 41 команду, смену аккаунта.

### AUD-11 — Merge клиента фиксирует данные до внешнего audit failure

Приоритет: **P2**. Метод: **isolated fault injection**.
Источник: [apps/clients/views.py](../../apps/clients/views.py).

При DatabaseError в write_audit_log после merge дубликат уже архивирован и ClientMergeLog сохранён, запрос завершился ошибкой. След объединения есть; общий аудит не атомарен.

Критерий исправления: Один transaction boundary для merge и обязательной истории/аудита; ошибка откатывает изменения. Проверить повтор, права и связи.

### AUD-12 — Импорт и экспорт не имеют полного рабочего интерфейса

Приоритет: **P2**. Метод: **source**.
Источник: [frontend/src/features/integrations/components/ImportPanel.tsx](../../frontend/src/features/integrations/components/ImportPanel.tsx).

Нет UI mapping, показаны лишь первые ошибки/задания; selected job не ограничен allowedEntities. Асинхронный экспорт теряет доступный результат после ухода/перезагрузки; list API уже есть.

Критерий исправления: 12a mapping→preview→полные ошибки→повтор; 12b история импортов с правильным entity и пагинацией; 12c сохраняемая история export jobs/download после reload. Закрывать подпункты отдельно, весь пункт только после всех трёх.

### AUD-13 — PATCH переназначает чужую заявку в обход scope

Приоритет: **P1**. Метод: **source**.
Источник: [apps/core/viewsets.py](../../apps/core/viewsets.py).

get_object проверяет VIEW старого объекта; UPDATE проверяется на кандидате с новым responsible_user. Оператор с VIEW business/UPDATE own может присвоить чужую заявку себе.

Критерий исправления: Проверять UPDATE исходного объекта; assignment через сервис, с историей/уведомлениями. Тест generic PATCH против assign, own/team/business, null/self/чужой member; проверить затронутые общие consumers.

### AUD-14 — Обычный PATCH сообщения обходит отправку через Inbox

Приоритет: **P1**. Метод: **source**.
Источник: [apps/bots/serializers.py](../../apps/bots/serializers.py).

status/text/sender_type/payload_json writable; direction можно не передавать. OWN UPDATE сообщения без owner проходит без родительского scope; queued outbound обрабатывается delivery worker.

Критерий исправления: Серверное управление delivery metadata и право на родительский диалог; send/retry только через сервис. Проверить подмену sender/payload, requeue, редактирование истории и legacy Message API.

### AUD-15 — Стадии и переходы принимают чужие воронки

Приоритет: **P1**. Метод: **source**.
Источник: [apps/crm/serializers.py](../../apps/crm/serializers.py).

PipelineStageSerializer и StageTransitionSerializer не сверяют связи. POST своей стадии с чужим pipeline проходит общие guards; pipeline.stages используется вложенной выдачей/board.

Критерий исправления: Проверить Business и pipeline у всех концов перехода; отрицательные POST/PATCH с foreign и same-business wrong pipeline, отсутствие изменения чужой доски.

### AUD-16 — ImportJob разрешает подменять серверные поля

Приоритет: **P2**. Метод: **source**.
Источник: [apps/core/serializers.py](../../apps/core/serializers.py).

Meta ImportJobSerializer не содержит read_only_fields; декларация ошибочно находится после return другого метода. PATCH меняет status/errors/mapping/actor; confirm доверяет сохранённому preview state.

Критерий исправления: Allowlist входов, immutable actor/status/counters/preview; mapping только через повторный preview, locked confirmation с повторной валидацией. AV/лимит исходных байтов уже проверяются при confirm и должны сохраниться.

### AUD-17 — Массовое прочтение уведомлений не проверяет UPDATE

Приоритет: **P2**. Метод: **source**.
Источник: [apps/notifications/views.py](../../apps/notifications/views.py).

mark_all_read обновляет VIEW queryset без UPDATE guard. Marketer имеет VIEW business, UPDATE own; action_permission_map сам по себе не исполняется permission class.

Критерий исправления: Проверка UPDATE и scope всех обновляемых строк; owner/marketer/VIEW-only/другой Business, персональные и общие уведомления. Inbox имеет дополнительный фильтр, дефект не означает чтение всех его уведомлений.

### AUD-18 — Старый экспорт доступен после сужения прав

Приоритет: **P2**. Метод: **source**.
Источник: [apps/core/import_export_views.py](../../apps/core/import_export_views.py).

download проверяет membership и VIEW, но отдаёт ранее созданный широкий файл при сужении BUSINESS→OWN/TEAM/филиал. Полный отзыв VIEW/Business блокируется.

Критерий исправления: Проверять актуальность permission/scope snapshot или безопасно пересобирать экспорт. Проверить narrowing, отзыв роли/филиала и разрешённое скачивание; уже скачанную копию отозвать нельзя.

### AUD-19 — CRUD полей лид-форм не определяет Business через form

Приоритет: **P2**. Метод: **source**.
Источник: [apps/leads/views.py](../../apps/leads/views.py).

LeadFormFieldViewSet использует form__business; IsTenantMember/get_object/_business_from_serializer не обходят form. Обычный владелец получает отказ на detail/write, хотя список может работать.

Критерий исправления: Единообразно разрешать business_lookup и сохранять tenant guards. Проверить create/detail/edit/delete поля через API и достижимый редактор, foreign form и отказ роли.

### AUD-20 — Создание и импорт заявки обходят terminal invariants

Приоритет: **P2**. Метод: **source**.
Источник: [apps/core/import_export.py](../../apps/core/import_export.py).

import_lead_row принимает любой Lead.Statuses и делает objects.create(status=...). LeadSerializer запрещает lifecycle-поля только при update. LOST можно создать без обязательной причины/момента потери.

Критерий исправления: Согласованный create/import путь через домен; lost reason и timestamps/history обязательны, невалидные строки отклоняются. Проверить API create, импорт LOST и обычную новую заявку; аналогичные deal-create paths сверить.

### AUD-21 — Параллельный confirm импорта: риск двойной обработки

Приоритет: **P2?**. Метод: **risk — не воспроизведён**.
Источник: [apps/core/import_export.py](../../apps/core/import_export.py).

confirm атомарен, но не блокирует ImportJob; imported проверяется во view до транзакции. Дедупликация через exists не доказывает конкурентную безопасность.

Критерий исправления: Сначала изолированный PostgreSQL тест двух confirm; затем lock/idempotency при подтверждении риска. Проверить один результат/набор событий, повтор и rollback.

### AUD-22 — XLSX материализуется до ограничения количества строк

Приоритет: **P2?**. Метод: **risk — не воспроизведён**.
Источник: [apps/core/import_export.py](../../apps/core/import_export.py).

read_tabular_file выполняет list(sheet.iter_rows(...)) до normalize_tabular_rows. Лимит байтов относится к сжатому файлу; AV не является ограничителем разжатого объёма.

Критерий исправления: Контролируемый subprocess с жёстким memory/time лимитом; проверить dimensions/rows/columns и compressed ratio без нагрузки рабочей среды. При подтверждении — ранняя потоковая остановка и закрытие workbook при ошибке.

## Воспроизведения 16.10: что именно проверено

Изолированный Python probe через `scripts.codex_verify.isolated_runtime`: миграции только
в одноразовую SQLite, APIClient/testserver и controlled fault injection.
Результаты: EMPTY_RULE_CREATE=201; EMPTY_RULE_ENABLE=200/actions=0;
PARTIAL_RULE_AFTER_ERROR=exists/active/actions=1; INVALID_ASSIGN_PREVIEW=200/valid;
MERGE_AFTER_AUDIT_ERROR=archived/merge_logs=1; SERVICE_OVERVIEW=count101/rows100/next.
Первый запуск получил ALLOWED_HOSTS/testserver 400; после исправления только
изолированных настроек повтор завершился exit 0. Это не ошибка продукта и не
PostgreSQL/concurrency proof. HTTP probes notes/activity создали foreign references
(201); operator client detail вернул внутренние notes (200).

Chromium запускался через локальный cached Playwright CLI, с backend/frontend из
канонического checkout, dedicated ports и disposable DB. Сценарии: смена аккаунта
и offline; поиск старого клиента среди 57; API automation-runs=503.
Локальные артефакты в игнорируемом `output/playwright/project-audit/`:
`offline-cross-account.png`, `global-search-missing.png`,
`automation-error-as-empty.png`, `servers.log`.
Это локальные свидетельства, не переносимые CI fixtures; точные regression tests
нужно добавить при исправлении. Browser session и собственные серверы остановлены,
одноразовая база удалена. Рабочие данные и провайдеры не изменялись.

## Дополнительная security-проверка 17.10

Codex Security Standard scan: `1997f7a8-3449-4add-98d8-4bc1d5adc571`.
Завершён с **partial coverage**: шесть новых security findings AUD-13–18
(3 high / 3 medium); исходные AUD-01–03 сохранены отдельно, без двойного счёта.
Канонические report/threatmodel/findings/coverage хранятся в локальном workbench,
scan directory `56dd1243ef1ad5a4b15ddb94115aaaa6d2b0047a_20261017T054122Z_bsvs09q_`.
Исходный generated report не редактировался. Warning об изменении working tree
относится к документационному checkpoint; application code остаётся на исходном SHA.
Два отказа схемы final draft (формат explicitExclusions) исправлены до принятия;
finalization выполнен один раз успешно.

Проверены контрограничения: membership и неизменяемый owning Business уже защищены;
это не заменяет проверки связанных FK или исходного UPDATE scope. В экспорте полный
отзыв VIEW уже запрещает download. При confirm импорта проверяются те же ограниченные
байты и AV; обход антивируса не заявляется. В outbound delivery существуют guards
AI, но writable sender_type/payload позволяют обойти именно этот вход.
В тестах есть положительное mark-all-read и проверки assign action; они не
доказывают отрицательные bulk-scope/generic PATCH сценарии.

## Покрытие и открытые вопросы

| Область | Проверенная граница / остаток |
| --- | --- |
| CRM/access | Generic CRUD, notes/activity, client sensitive fields, lead assignment/create, pipeline links, merge, forms; найденные проблемы выше |
| Automation/tasks | Creation/preview/activation, reachable UI/history и offline replay; не все комбинации команд/worker failures |
| Inbox/AI | Message mutation → outbound sink, parent scope, AI sender guards; нет реальной отправки или повторной live-сертификации AI |
| Import/export | Job metadata/preview/confirm/download, UI mapping/history; concurrency и XLSX resource budget открыты |
| Frontend/data | Reachable global search, deal picker, service aggregates и offline storage; TasksPage и calendar используют другие пути и не объявлены сломанными по неиспользуемому hook |
| Identity/files/webhooks | Просмотрены session epoch/device/refresh locking, token scopes, private-file guards, pinned-DNS/private-IP/redirect guards; новых доказанных дефектов в выбранных путях нет |
| Среда/полный проект | Не выполнены полный dependency-advisory аудит, построчная сертификация всех 1988 inventory files, pentest production, реальная доставка/backup restore/нагрузочная приёмка |

В AUD-V01 roadmap остаются: проверить политику automation actor (исполнение от
владельца при настройке другим сотрудником); допустимость публичного duplicate_warning
формы; отдельная проверка login-CSRF. Они **не объявлены уязвимостями** без достаточной
проверки и сверки решений. Следующая проверка должна закрывать конкретную неизвестность,
а не повторять весь аудит после каждого исправления.

Существующие незакрытые ADMIN-05, target environment, real channels/mail/payment,
working migrations, эксплуатационные acceptance IDs остаются в прежних разделах
roadmap/acceptance. Этот отчёт их не закрывает, не дублирует и не разрешает deployment.
