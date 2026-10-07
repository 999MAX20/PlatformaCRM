# Клиентский AI: завершение локального пилота 08.10.2026

Task `INBOX-LOCAL-PILOT-20261008`. Разрешённый результат: завершить существующие
клиентские сценарии, безопасную передачу человеку и удобную настройку агента.
Без новых возможностей, развития CRM-аналитика, внешних мессенджеров, deployment
и production-инфраструктуры. Canonical root `C:/Users/user/Desktop/PlatformaCRM`,
branch `codex/ui-testing-toolkit`, clean base `0112475850c631cd946424c86f49e363c6b80881`.
Тот же зарегистрированный generation 4 owner; исходных чужих изменений не было.

## Изменения

- Автоматическая эскалация при включённой автоотправке отправляет существующий
  локализованный текст: «Нужна помощь администратора. Я передал ему обращение;
  вы можете продолжить писать в этом чате». Модель для этого не вызывается.
  Уведомление проходит через обычный outbox и квоту сообщений. Повтор входящего
  использует исходный результат; новые входящие при handoff не запускают AI.
- Перед отправкой проверяются актуальные агент, канал, настройки, состояние
  диалога и память. Resume/ответ сотрудника/закрытие/архив/reset/изменение настроек
  отзывают старую отправку. Retry использует один outbox ID. Выключенная
  автоотправка и отказ квоты не отменяют саму передачу человеку.
- Пустой ответ модели теперь останавливает AI и передаёт человеку. Исправлен
  обнаруженный live-прогоном случай: последний разрешённый вызов расходуется
  на классификацию, reply уже блокируется лимитом, но уведомление не создаётся.
  Сохраняется защита от автоматического ответа после ручного takeover.
- У настройки записи один переключатель вместо двух независимых условий:
  он согласованно сохраняет tool permission и pipeline setting. В режиме
  выключено/только ответы создание недоступно; смена режима не выдаёт booking.
  Главная инструкция видна сразу; модель/правила/память/вариативность и числовые
  safety limits находятся в раскрываемых блоках. Дополнительный fallback control
  перенесён в расширенные ограничения. Обязательная защита остаётся включённой.
- Исправлено противоречие шаблона стоматологии: инструкции следуют сохранённым
  разрешениям и подтверждают запись только после сохранения системой. Ранее
  шаблон требовал staff confirmation даже при разрешённой автоматической записи.
  Сохранённые пользовательские инструкции не переписываются.

Схема БД, роли, публичные API, credentials и конфигурация среды не менялись.
Использованы существующие handoff/activity/audit/notifications; нового типа
BusinessEvent нет. Shared профиль CRM проверен как зависимый потребитель UI,
развитие его функций в задачу не входило.

## Проверенная матрица

| Область | Подтверждённая граница |
| --- | --- |
| Обычные обращения | Цена «от», длительность, адрес/часы, приветствие/благодарность, отсутствие знаний, память, RU/KK/EN, серия справочных вопросов без off-topic |
| Запись | До выбора нет визита; точные Business/client/service/resource/start/end; replay без второго визита/вызова; busy/no consent/staff policy/tool disabled |
| Опасные запросы | Секреты, прямые/косвенные и quoted injection, Unicode обход, личные записи, подмена сотрудника, медицинские вопросы, жалоба/возврат, перенос/отмена существующего визита |
| Лимиты | Слишком длинный текст, повторы/rate/call budget, отдельный случай лимита между classification и reply; usage сохраняется при resume/reset |
| Передача/восстановление | Фиксированный текст, одно уведомление, no paid replay, provider failure/empty output, ручной ответ/resume, stale queue cancellation, transient retry, отказ квоты |
| Доступ/источники | Tenant/role denial, private markers вне prompt/output, явная публикация знаний, отзыв источников и неизменность CRM при запрещённом действии |
| Настройки | Сохранение/перезагрузка/отмена, одна booking control, атомарный payload, безопасные defaults, desktop/mobile, RU/KK/EN, keyboard, axe, overflow |
| Реальный шаблон | Текст читается из frontend i18n, не из тестовой копии: цена/длительность RU/KK/EN и запись с точным выбором/replay |

Это конечный проверенный набор, не гарантия всех возможных формулировок.
Семантический разбор подтвердил факты, отсутствие выдуманной скидки/услуги,
безопасную передачу и соответствие подтверждения записи реальным строкам БД.
Приветствие может быть избыточно подробным; свободное «Можно подробнее?» может
дать общую справку либо handoff. Эти вариации не объявлены универсальным качеством.

## Среда, команды и результаты

Использован существующий `.venv`, `scripts.codex_verify.isolated_runtime`, отдельные
временные SQLite/порты/медиа. Исходники серверов — canonical checkout, reuse false.
Рабочая БД и чужие процессы не затрагивались, зависимости не переустанавливались.
Локальный evidence: `output/inbox-local-pilot-20261008/`.

`verify.py <labels>` в этой папке вызывает `manage.py check`,
`makemigrations --check --dry-run`, `manage.py test <labels> -v 2` внутри
`isolated_runtime`. До последнего исправления: **241 PASS**, log
`backend-1791404097304478100.log`, labels:

```text
apps.bots apps.conversations
apps.ai_core.tests_inbox_continuity apps.ai_core.tests_job_recovery
apps.ai_core.tests_agent_runtime apps.ai_core.tests_knowledge_isolation
apps.ai_core.tests_prompt_preferences apps.ai_core.tests_settings_certification
```

После call-limit fix: **72 PASS**, system/drift PASS,
`backend-1791405373755424400.log`, labels:

```text
apps.bots.tests_handoff_notice apps.bots.tests_customer_safety apps.conversations
apps.bots.tests_automatic_booking apps.bots.tests_runtime_configuration
apps.bots.tests_safety_recovery
```

Незатронутые зависимости из 241 не запускались повторно; числа не суммируются
как уникальные тесты. RED новой call-limit регрессии сохранён в
`backend-1791404699697403300.log`.

`verify_ui.py <project> <spec> [filter]` запускает в изоляции
`npx.cmd --no-install playwright test e2e/<spec> --project=<project>
--grep-invert="channel forms" --max-failures=1 --reporter=line --output=<unique>`.
**16 выбранных сценариев PASS**: desktop/mobile для
`ai-agent-settings-certification.spec.ts` (3 на viewport),
`inbox-agent-safety.spec.ts` (3), `inbox-local-pilot.spec.ts` (2).
Desktop shared-knowledge проверен отдельным `--grep="shared knowledge"`.
После исправления порядка i18n fallback ещё раз PASS mobile
`--grep="profile and safety"` (все три языка); последний log
`browser-1791405384546518200.log`. Просмотрены desktop/mobile screenshots.
`npm.cmd run build` (i18n/TypeScript/app/widget) и `npm.cmd run check:bundle` PASS.

```powershell
.\.venv\Scripts\python.exe scripts/ai_behavior/run.py --suite customer_pilot --live --budget-usd 1 --max-calls 160 --output output/inbox-local-pilot-20261008/live
```

**43/43 live PASS**, run `customer_pilot-1791405340114934200`, 76 полученных
ответов модели. Реальный OpenRouter `openai/gpt-4.1-mini`, синтетические данные,
фиксированные тестовые часы 07.10 10:00 UTC, Business Asia/Almaty. Provider failure
инъецирован на HTTP-границе; восстановленный ответ — настоящий. Receipt доставки
контролируется тестом, enqueue удерживается для сценария задержки; это не live channel.
Все Python и i18n SHA256 финального manifest совпали с проверенными исходниками.

Отдельный разрешённый бюджет этой задачи USD1, один cumulative ledger для всех
попыток. Итого 143 полученных ответа, два сохранённых резерва искусственной ошибки:
provider-reported USD0.1290448, вместе с резервами **USD0.1416664**. Ledger содержит
145 попыток, cases — 82 (39 первоначальных + 43 итоговых), ни одна не удалена.

## Сохранённые неудачные попытки

Первоначальные RED подтвердили отсутствие уведомления; некорректный mock
provider failure заменён исключением. Новый тест takeover выявил лишнее
уведомление — ограничен набор automatic decision statuses, focused 38 PASS.
Первый live запуск 38/39 machine PASS обнаружил call-limit defect; после
исправления весь расширенный набор прошёл. Первая browser batch смешивала
quota-limited fixtures (5 PASS/11 FAIL), затем spec/project разделены по DB.
Селектор textarea исправлен на accessible textbox. Два промежуточных backend
запуска содержали несуществующие test labels и получили import error; итоговый
запуск использует проверенные labels выше. Один browser grep не нашёл тестов;
исправлен на точное имя. Build остановился на i18n fallback ordering, исправление
прошло build и повторный локализованный UI flow. Эти неудачи не скрыты итоговым PASS.

Не запускались full-project/E2E local gate, рабочие миграции, production worker/
Redis/PostgreSQL drill, WhatsApp/Telegram и клиническая приёмка сотрудниками.
Они исключены из этого поручения. Внешняя доставка, эксплуатационная надёжность
и приёмка персоналом остаются отдельными границами, без нового разрешения на запуск.

## Публикация

Scope готов к проверенному commit и обычному push `HEAD:main`. Коммит отчёта
определяет candidate; remote SHA и фактический push CI фиксируются в итоговом
ответе задачи и локальном `publication.json`. До readback не считать публикацию
или CI завершёнными. [Checkpoint](task-state/PRIMARY-SESSION.md).
