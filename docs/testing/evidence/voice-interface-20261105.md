# VOICE-INTERFACE-20261105 — голос без пользовательского AI-агента

Решение владельца05.11: голосовое управление — функция интерфейса CRM. Создание,
активация или employee workflow AI-агента не являются предварительным условием.
Каноническая папка `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, HEAD `66101d509cb7642b2928275e48c4b64354abf07b` + task WIP.
Существующая чужая работа сохранена. Исходные snapshots и план:
`output/voice-interface-20261105/`; новый срез заменяет только зависимость
от агента из [первоначальной проверки](voice-assistant-20261104.md).

## Результат

Speech API не ищет CRM-агента и не возвращает его ID. Голосовой диалог создаётся
с `kind=voice`, без agent; сервер отвергает agent и analytics mode. История доступна
только её сотруднику в разрешённом Business. Встроенный runtime проходит через
queue/prepare/tools/confirm и не выбирает первый Bot даже при добавлении,
паузе или удалении агента. Модель, инструкции и источники пользовательского
агента не используются. Общие permissions, approvals, stale/replay, аудит,
BusinessEvent/уведомления доменных команд остаются действующими.

Frontend создаёт voice-диалог и хранит ID по user/Business в `voice-thread:v2`.
Старые agent-keyed threads сохраняются, но не подхватываются голосовой панелью.
История с неверным business/kind/agent отклоняется; no-agent путь доступен через
существующую кнопку микрофона и персональные настройки. Новых UI блоков/копирайта нет.

Миграция `ai_core.0009_interface_voice_conversations` допускает agent=NULL только
у voice; staff/Inbox сохраняют обязательную связь. Старые строки не преобразуются.
Откат на0008 после создания voice-истории требует отдельного плана сохранения данных;
проверенный обратный переход выполнен на чистой базе без voice-строк.

## Проверки

Все команды из canonical root, существующая `.venv`, `isolated_runtime`, без
переустановки зависимостей, платных provider calls и изменений рабочей БД.

- `.venv/Scripts/python.exe output/voice-interface-20261105/check_backend.py affected apps.ai_core.tests_voice_interface apps.ai_core.tests_speech apps.ai_core.tests_voice_policy apps.ai_core.tests_conversation_api apps.ai_core.tests_conversation_state apps.ai_core.tests_conversation_memory apps.ai_core.tests_conversation_execution apps.ai_core.tests_agent_runtime apps.ai_core.tests_crm_tools apps.ai_core.tests_crm_planner`: **92 PASS**, затем `check` и `makemigrations --check --dry-run` PASS. Логи `affected-{0,1,2}.log`.
- Новые10 тестов покрывают noBot/status/create/history/DB constraints, paused/deleted-agent independence, отсутствие чужих инструкций/знаний/model, voice-policy без origin, подтверждение реальной Task/replay, отключение/отзыв доступа и rollback при audit failure. Начальные coherent backend checks12+5 PASS сохранены отдельно; не суммируются с92 как уникальные тесты.
- `.venv/Scripts/python.exe output/voice-interface-20261105/check_migration.py`:0008→0009→0008→0009 PASS, чистая disposable SQLite, `migration.log`.
- `.venv/Scripts/python.exe output/voice-interface-20261105/run.py --browser`: **6 PASS**, RU1440/KK390/EN390, настоящее создание voice-диалога без agent и подтверждение Task, запись/edit/send, Escape/focus/track cleanup, permission denial/cancel/recovery, настройки без SETTINGS и серверный role403. `browser-1793823025484148500.log`, screenshots proposal/settings по3locale. Fixture явно проверяет отсутствие всех Bot в тестовом Business; STT и модель синтетические, API/history/domain confirmation реальные.
- Первая подготовка fixture остановилась до UI: стандартный seed создавал Bot. Исправлено только в guarded disposable fixture: seeded Bot/history/knowledge удалены, zero-Bot assert сохранён. Это не изменение рабочей базы; исходный failure log сохранён.
- `.venv/Scripts/python.exe output/voice-interface-20261105/run.py --build`: build/types/i18n **PASS**,6883 ключа RU/KK/EN; `build-1793823037887988100.log`.
- `node --test frontend/scripts/tests/voice-audio.test.mjs`: **4 PASS**.
- Scoped diff hygiene, registry/relative links и исходный task delta проверены; снимки KK mobile proposal/RU desktop settings просмотрены. Полный project/E2E gate не запускался: задана scoped архитектурная дельта.

## Остаток

Код и локальные проверки принятой дельты завершены. Рабочая `db.sqlite3` read-only
проверена: ai_core остановлен на0008. Применение0009 требует отдельного разрешения
владельца по AGENTS.md; пока не выполнялось. Поэтому работающий стенд ещё не
объявляется обновлённым. Live STT RU/KK/mixed/шум, совместимость privacy route,
worker-live/production не сертифицированы. Полный D01 остаётся открытым.

Publication: существующий `.git/index.lock`,17 чужих исходящих коммитов относительно
локального origin/main; lock/index/history не менялись. Собственного commit/push,
нового CI или deployment нет. Старый PASS не выдаётся за текущий live PASS.
Документы AI/frontend/voice/roadmap/passport/README синхронизированы; остальные
контракты прав/доменов не менялись: новых разрешений или доменной политики нет.
