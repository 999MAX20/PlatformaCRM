# Клиентский Inbox AI — приёмка 08.10.2026

Task `INBOX-LIVE-ACCEPTANCE-20261008`. Владелец поручил обычные обращения,
запись, защиту и восстановление с реальной моделью; отдельно разрешил максимум
USD1. Canonical checkout `C:/Users/user/Desktop/PlatformaCRM`, branch
`codex/ui-testing-toolkit`, clean base `00fe0e7c8743a4b84d136db9492e9228e88beecd`.
Это ограниченная приёмка клиентского агента, не всей CRM и не production-допуск.

## Среда и бюджет

Переиспользованы `scripts.codex_verify.isolated_runtime` и `scripts/ai_behavior`.
Каждый запуск создаёт отдельную временную SQLite и синтетические данные;
рабочая БД/серверы не используются. Тестовые часы зафиксированы на
07.10.2026 10:00 UTC, Business timezone Asia/Almaty. Поэтому даты предложений
в сохранённых диалогах относятся к тестовым часам, а не ко времени публикации.

Реальная модель — OpenRouter `openai/gpt-4.1-mini`; классификация и ответы проходят
настоящий provider transport. Входящие сообщения проходят текущий Inbox service
pipeline; действия сотрудника — реальные API в изолированной среде.
Подтверждение доставки website-канала контролируется тестом: это **не доставка
в реальный мессенджер**. Проверка очереди удерживает enqueue для имитации worker
lag; network failure инъецируется на HTTP-границе, восстановленный ответ — live.

`--budget-usd 1` передаётся parent→child; до каждого вызова резервируется верхняя
оценка стоимости по актуальному provider pricing и bounded output. Все прогоны
используют один `budget.json`; неудачные/неопределённые попытки сохраняют резерв.
Дополнительный потолок — 160 попыток. Токены/headers не сохраняются. Только
синтетические диалоги/ответы и проверяемые записи остаются в локальном evidence.

## Что обнаружено и исправлено

1. Модель однажды классифицировала «Подскажите адрес клиники» как `off_topic`,
   объяснив это отсутствием покупки/записи. Уточнены независимость `intent=other`
   от `request_kind` и принадлежность адреса/часов/парковки/длительности к business.
   Добавлена серия из трёх справочных вопросов: счётчик off-topic должен оставаться 0.
2. При занятом слоте, staff-only политике или выключенном booking tool сервис
   возвращал `requires_staff`, но pipeline продолжал генерировать предложение
   подтвердить тот же слот. Данные оставались защищены, пользовательский ответ
   был противоречив. Теперь вызывается существующий handoff, AI останавливается,
   а при включённых auto replies отправляется существующий локализованный текст
   передачи администратору. Повтор сообщения не создаёт вторую отправку/запись.
   Выключенный auto reply сохраняется. Права и правила записи не расширены.

Три новые регрессии сначала упали на старом поведении; после исправления прошли.
Четвёртая проверяет выключенную автоотправку. Использованы существующие activity,
audit, manager notifications и pipeline event; новый вид событий не вводился.
Схема, настройки среды, frontend и публичный API-контракт не менялись.

Отдельные ошибки тестового окружения сохранены и не названы дефектами продукта:
старые fixture-знания требовали явного `customer_visible` до activation;
неопределённый вопрос без контекста допускает handoff по текущему контракту;
для проверки задержанной отправки нужно удержать enqueue вместо eager Celery.
Первый live-прогон: 27 сценариев, 25 machine PASS и две ошибки этих ожиданий/
окружения. Даже machine PASS потребовал семантического разбора, выявившего пункты выше.

## Проверки

Все команды ниже выполнялись из canonical root существующим `.venv` Python.

```powershell
.\.venv\Scripts\python.exe -m unittest scripts.ai_behavior.test_transport -v
.\.venv\Scripts\python.exe scripts/ai_behavior/run.py --suite customer_acceptance --live --budget-usd 1 --max-calls 160 --output output/inbox-live-acceptance-20261008
```

Локальный `output/inbox-live-acceptance-20261008/verify.py` вызывает `check`,
`makemigrations --check --dry-run` и `manage.py test <labels> -v 2` внутри
`isolated_runtime`. Итоговые labels:

```text
apps.bots.tests_customer_safety
apps.bots.tests_safety_state
apps.bots.tests_safety_recovery
apps.bots.tests_automatic_booking
apps.bots.tests_runtime_configuration
apps.ai_core.tests_inbox_continuity
apps.ai_core.tests_job_recovery
apps.bots.tests_controlled_creation
apps.bots.tests_pause_inbound
apps.bots.tests.InboxBackendTests
apps.conversations.tests_ai_confirmation
apps.conversations.tests_ai_behavior_boundaries
```

Промежуточно: baseline 53 PASS; бюджетный harness 6 PASS; pre-provider dry 4 PASS;
booking regression 3 FAIL до исправления; focused booking/safety/behavior 24 PASS
после исправления. Итог: **130 backend PASS**, system/migration drift PASS; **28/28 live scenarios
PASS** после ручного семантического разбора ответов и записей. На финальном
прогоне 57 реальных вызовов, совокупно 110 полученных ответов и 2 консервативных
резерва инъецированной ошибки. Provider-reported cost USD0.1104668; вместе с
резервами USD0.1228916 из USD1. Все 55 live case attempts сохранены. SHA256
итогового run manifest совпали с текущими Python sources. Приветствие иногда
избыточно подробное; косметическая настройка тона не расширяла этот scope.

| Направление | Что проверяет итоговый набор |
| --- | --- |
| Обычные обращения | Цена «от», длительность, адрес/часы, приветствие/спасибо, неизвестная парковка, неоднозначность, память, RU/KK/EN, серия обычных вопросов |
| Запись | Никакой записи до выбора; точные Business/client/service/resource/start/end; один результат на replay; занятый слот, отсутствие согласия, staff policy и disabled tool |
| Защита | Прямые/косвенные запросы секретов и личных записей, подмена полномочий, клинические советы, запрос человека; последовательность off-topic и приватные marker-поля вне prompt/output |
| Восстановление | Ошибка provider, ручной ответ, authorized resume без обнуления расхода, исчерпание лимита, отзыв queued ответа, denial чужому actor |

Пропущены full-project gate, browser/build и установка зависимостей: изменены
backend prompt/pipeline и test harness; frontend/dependency inputs не менялись.
Нет рабочей миграции, Redis/PostgreSQL/cloud worker drill, настоящей доставки,
deployment и приёмки персоналом клиники. Эти границы остаются открытыми.

## Evidence и публикация

`output/inbox-live-acceptance-20261008/`: append-only `cases.jsonl`, `transport.jsonl`,
`run-manifests.jsonl` (SHA256 всех затронутых Python sources), cumulative `budget.json`,
`provider-prices.json`, backend logs, semantic review/summary и publication receipt.
Полные синтетические transcript-файлы не публикуются в Git; исходный воспроизводимый
набор находится в `scripts/ai_behavior/customer*_cases.py` и `customer_cases.py`.
Первичные ошибки и повторные попытки не удаляются.

После предметного PASS выполняются diff/link/registry checks, reviewed commit, обычный push
HEAD:main, readback SHA и отдельное наблюдение CI. Точный commit определяется
историей этого отчёта и итоговым ответом; прежний docs CI37667508038 SUCCESS.
Ограниченный PASS не доказывает универсальную защиту от prompt injection или
безошибочность любых свободных диалогов. Следующий отдельный этап — выбранный
канал/целевая среда и ручная клиническая приёмка, без автоматического возобновления
отложенных направлений. [Остаток приёмки](../current/acceptance.md).
