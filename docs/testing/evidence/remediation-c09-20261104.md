# C09 — контекст и эффекты создания записи

Исправлено и проверено локально 04.11.2026: REQ03/CRM-EVENT01.
Canonical `C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`,
base `1838722ac12ca08c01c6cfda23bcb2224371dd29` +233 preserved foreign WIP entries.
[Контракт до изменений](../../../output/remediation-c09-20261104/CONTRACT.md).

## Получившееся поведение

Business.ai_booking_responsible_user задаётся явно в существующем профиле компании.
GET `/api/businesses/{id}/booking-responsible-options/` и PATCH настройки защищены
SETTINGS UPDATE. Опции содержат id/label активных доступных участников своего
бизнеса/owner. Nullable ID перепроверяется при валидации и сохранении. Неизвестные,
чужие, отключённые и недоступные кандидаты не принимаются.

Автоматическая запись сохраняет source_conversation и текущего ответственного из
настройки Business, отдельно от authorizing actor. Проверяются CREATE scope,
текущее членство/активность/доступность и филиальные права. Null/невалидное значение
ведёт в существующий requires_staff/handoff без произвольного fallback на owner.
Уже успешный replay сохраняет исходное назначение и не создаёт эффектов повторно;
право actor на повторный вызов остаётся обязательным.

Общий атомарный handle_appointment_created сериализуется Business lock и создаёт
один BusinessEvent (`source=crm`, `event_type=appointment.created`,
`deduplication_key=appointment:{id}:created`, IDs-only payload, processed).
Только первое выполнение планирует followups, уведомляет ответственного и запускает
существующий automation engine. API/manual/plan/legacy используют общий обработчик.
Legacy Lead сохраняет свой valid responsible либо существующий actor/owner default;
ручная беседа использует actor. Автоматическая запись использует только настройку.
Generic appointment API вызывает обработчик внутри транзакции создания.
Исключение оркестрации откатывает запись и эффекты; успешный replay их не повторяет.

Форма использует shared Select, save/cancel/feedback и API слой. Проверены RU/KK/EN,
desktop/mobile, loading/error/retry, сохранение/перезагрузка/очистка/отмена и stale
candidate. Ошибка переводит фокус на видимый Select. Новых декоративных блоков,
глобальных токенов или общего permission framework нет. Antislop during выбран
пользователем; проверены purpose/существующие стили/клавиатура/снимки затронутой формы.
Общие страницы и независимые UI-дефекты не перерабатывались.

## Проверки и первоначальные ошибки

Все команды из canonical root через `.venv/Scripts/python.exe`.
`output/remediation-c09-20261104/run_checks.py` использует isolated_runtime,
fresh disposable SQLite, configure_browser_runtime, отключённые dotenv/providers
и внешние sockets. Полные labels/команды — commands.json, исходные логи сохранены.

- settings-baseline: 5 fixture errors из-за повторного пустого email; исправлена
  только фикстура. settings-before: 5 failing methods на исходном API.
- settings-focused: 5 PASS сразу после model/API slice.
- creation-before: 3 FAIL подтверждают отсутствие context/effects/отказа без default.
- creation-focused: 29 PASS после общего creation slice; automatic/terms/branches.
- expanded: 12 PASS, включая раздельные actor/assignee, смену default после offer,
  replay, revoked/unavailable/foreign/inactive, role/tenant и save-time revalidation.
- completion: 145 tests, 144 PASS и 1 FAIL старого ожидания двух уведомлений в
  legacy Lead. Новый общий обработчик обоснованно добавляет уведомление ответственному.
  Проверка уточнена: ровно 3 уведомления, из них 1 confirmation, 1 reminder,
  1 creation notice нужному получателю; также ответственный и один BusinessEvent.
  `legacy-recheck ...CorePlatformTests.test_create_appointment_from_lead_updates_lead`:
  1 PASS. Production код после completion не менялся; остальные 144 PASS переиспользованы.
  Зависимые наборы: scheduling core, record commands, visit plans, settings delivery,
  automatic/terms/branches и controlled creation. Django check PASS,
  makemigrations --check --dry-run: no changes.
- migration-and-boundaries: migration preservation и OWN denial PASS; branch test
  первоначально FAIL, поскольку create_branch сохраняет grants первого филиала.
  Фикстура явно отзывает этот grant; branch-recheck: 1 PASS. Обратная/прямая миграция
  сохраняет бизнес/owner/created_at; новый default остаётся null. Доменный код не менялся.
- `run_pg.py` с labels в postgres-concurrency.json: 21 PASS, 0 SKIP, isolated native
  PostgreSQL17 loopback cluster. Два одновременных подтверждения дают одну запись;
  два callback дают один BusinessEvent/AutomationRun/task. Реальный automation engine
  выполняет create_task. Дополнительно manual-record и plan races/idempotency.
  Сессии/data_directory/port проверены; test DB удалена, кластер остановлен.
- `run_browser.py`: initial4 PASS; final6 PASS (desktop+mobile Chromium), реальная
  isolated Django DB/API/login/Settings форма. Перехват GET моделирует503 и устаревшую
  опцию; PATCH действительно отклоняет неизвестный ID. Выбор/сохранение/reload/cancel/
  clear, RU/KK/EN и Enter/Escape/focus проходят. Снимки в output/.../ui.
- `run_build.py`: final PASS — safe isolated npm build, types, i18n6685, app/widget.
  До локальной focus поправки был ещё один PASS; финальный build повторён из-за неё.
  Existing >500kB chunk warnings сохранены. Dependencies не переустанавливались.

AI classification/reply и внешняя доставка контролируются test doubles. Реальные
модели, API, БД и automation engine проверены; живые AI/provider/channel не вызывались.
Нет full-project/E2E/release gate: выбран затронутый и зависимый контур C09.

## Миграция и сохранность

businesses0014 — nullable FK SET_NULL, без backfill. Применена только в disposable
БД. WorkingDB hash unchanged; dev8000/5173 выключен. Для рабочего/серверного применения
нужен отдельный разрешённый target; существующему бизнесу после миграции нужно явно
выбрать сотрудника, иначе AI передаёт запись для ручной обработки.

Foreign WIP сохранён, в scheduling/views.py индексируется только собственный
перенос callback внутрь atomic, без чужого client projection/filter diff.
Пустой stale index.lock перемещён после двух проверок отсутствия Git процессов,
exclusive-open и неизменности index SHA. Diff hygiene сначала обнаружил лишние
пустые строки EOF в двух test runners; они убраны, повторная проверка PASS.
Plan/current contracts/passports/README/evidence согласованы. Product/integrations
и общий roadmap не требуют изменения: закрыта аудированная часть действующих
требований, не весь CRM-R01/money/D01. Исторические evidence не переписаны.

В C09 нет остатка кода или локальной проверки. Собственный local commit после
diff/link/secret/manifest проверок; receipt `output/remediation-c09-20261104/final-validation.json`.
Без push/merge/newCI/deploy/live-сертификации. C10 не начат. Ранее сохранённые
временные папки C05 после заблокированной очистки не трогались.
