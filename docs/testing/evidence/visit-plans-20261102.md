# CRM-R01-PLANS-20261102 — локальный цикл планов посещений

Продолжение поручения после первого Records workspace. Реализованы план Клиента,
неназначенные этапы и назначение через существующий Appointment. Денежные версии,
распределение/авансы/зачёты/возвраты, D01, deployment и рабочие миграции вне цикла.
Это scoped acceptance, не закрытие R01/AC-CRM-PILOT-01–14 или release gate.

Канонический root `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, HEAD `e02a28f550e94a543c3d88acac7c1b19ee48f90b` + task diff.
[Manifest текущих файлов](visit-plans-20261102-manifest.json) фиксирует SHA256,
но не приписывает этому циклу весь pre-existing diff этих файлов.
Начальный снимок/копии/patch и журналы: `output/visit-plans-20261102/`.

## Реализованная граница

| Слой | Поведение и доказательство |
| --- | --- |
| models, migration0011 | VisitPlan/VisitPlanStep, стабильный ID, one-to-one Appointment, soft-remove; только isolated migrations |
| plan_services/access/selectors | Business/client/module/branch/OWN/TEAM guards, hidden rows до count/page, coordinator не даёт доступ, whole-plan изменения проверяют все сохранённые этапы |
| plan_views/serializers | list/detail/history, команды schedule/revise/responsible/archive/restore; expected_revision и Idempotency-Key, повтор проверяет текущие права и проекцию |
| booking/status/plan_lifecycle | Общая блокировка Business→plan→step→Appointment, один create_record и его эффекты; отмена сохраняет связь; статус/перенос повышают revision |
| clients lifecycle/merge | Планы переносятся при merge, неназначенный активный этап блокирует archive клиента; rollback атомарный |
| core cards/read scope | Ссылка в Appointment только при доступе к плану; история плана не раскрывается через общий Client timeline |
| VisitPlansPage/PlanEditor/PlanHistory | Записи→планы, Client→планы, список/история с пагинацией; создание, правка, назначение, координатор, архив/восстановление |
| AppointmentForm/cache | Общая форма слота с фиксированным контекстом; после мутации перечитываются mounted plans; stale требует refresh/reconsent, lost response сохраняет payload/key |

Публичная история содержит команду/actor/time, без денежных audit snapshots.
Audit сохраняет состав до/после; изменения состава требуют причины и согласия.
Новых BusinessEvent/каналов уведомлений/автономных AI-команд нет; назначение
использует существующие эффекты Appointment один раз. Старые записи без плана
не получают фиктивный план. UI использует существующие компоненты, токены и
RU/KK/EN; карточки показывают реальные этапы/статусы/действия.

## Автоматические проверки

Из корня `.venv/Scripts/python.exe output/visit-plans-20261102/run_candidate.py`
запускает `scripts.codex_verify.isolated_runtime`, `django_safe.py` игнорирует
рабочий .env, блокирует внешнюю сеть и включает mock AI. SQLite базы одноразовые.

| Аргументы runner после имени файла | Результат |
| --- | --- |
| `plans-foundation-corrected test apps.scheduling.tests_visit_plans --noinput` | 9 PASS на первой service-итерации |
| `plans-api test apps.scheduling.tests_visit_plans --noinput` | 11 PASS на API-итерации |
| `plans-lifecycle-corrected` и `plans-boundaries` | 49 и46 PASS; точные labels в одноимённых JSON receipts |
| `plans-final-backend test apps.scheduling.tests_visit_plans apps.scheduling.tests apps.scheduling.tests_record_commands apps.scheduling.tests_record_completion apps.clients.tests_merge_atomicity apps.clients.tests_archive_dependencies apps.core.tests_crm_cards apps.automations.tests_follow_up_policy --noinput` | 128 PASS,0 skips,45.889s |
| `system-check check` | PASS |
| `migration-drift makemigrations --check --dry-run` | PASS |

`.venv/Scripts/python.exe output/visit-plans-20261102/postgres.py`:23 PASS в
одноразовом PostgreSQL17. Реальные гонки: одна команда, два плана на последний
слот, снятие этапа против назначения; также существующие record races. Прогон
был до добавления последних history/strict-input тестов; протокол блокировок
после него не менялся, последние additions покрыты финальными128.

`node --test frontend/scripts/tests/appointment-cache.test.mjs`:1 PASS.
В `frontend`: `npm run build` → i18n6650 ключей, `tsc -b`, app/widget PASS
после последнего исправления отображения события плана. Журнал `frontend-build-completion.log`;
предупреждение bundler о крупном chunk сохраняется, full performance не заявлен.
Зависимости не переустанавливались. Полный E2E/release gate не запускался:
это один bounded цикл, применены affected/dependent и concurrency проверки.

Сохранённые первоначальные ошибки: уникальные email в fixture (до выполнения
тестов), сериализация datetime в audit (1/49), blank reason в UI-команде смены
координатора (400). Fixtures, DjangoJSONEncoder и payload исправлены; проверки
повторены. Старые журналы не заменены новыми. Навигация до завершения сохранения
языка отменяла тестовый запрос; повтор выполнен с ожиданием видимого Saved.

## Browser evidence

Synthetic owner в изолированной SQLite, canonical Python/Vite, final ports56863/56864.
Рабочая БД и внешние провайдеры не использовались. Собственный runtime остановлен
через stop-runtime, wrapper exit0; отсутствие PID16036/5844 подтверждено.
Тестовая вкладка закрыта, viewport/Network overrides восстановлены. RU desktop/mobile390, EN
desktop и KK mobile390/form/keyboard — выборочные проверки, не полная матрица
всех ролей/локалей. Role/tenant/branch/revoke/partial visibility доказаны backend.

- Создание: намеренный503 после сохранения, поля сохранились, повтор вернул тот
  же Plan1. Read-only SQLite подтвердил один план/этап, Appointment не добавлен.
- Две вкладки: координатор меняет revision; старая форма409, Refresh сохраняет
  причину, показывает актуальный состав, сбрасывает согласие. Повтор согласия
  и сохранение успешно. Назначение Nov3,10:00 создаёт Appointment3 через общую форму.
- Card→Plan, отмена того же Appointment3, архив и восстановление. Отменённый
  этап сохраняет ID и не предлагает повторное назначение/удаление.
- EN: восстановление возвращает команды; добавленный этап без времени можно
  снять с причиной/согласием. Он остаётся видимым как Step removed и в истории.
- KK390: реальная локализация карточки и формы без видимого горизонтального
  переполнения. Tab/Enter открывает Select; первый Escape закрывает Select,
  второй Modal и возвращает фокус на «Кезең қосу».
- Блокировка только API планов: явная ошибка, не ложный empty. Снятие блокировки
  и Retry возвращает список. Browser overrides затем очищены.
- Client workspace→планы передаёт client=1 и показывает Plan1. Новое системное
  событие в Client drawer/workspace локализовано; технический event_type для него
  скрыт. Повторная KK-проверка подтверждает перевод; старый HMR blank исчез после
  reload. Остальные существующие event тексты не переопределялись.

Снимки в output: `plan-ru-desktop.png`, `plan-ru-mobile.png`,
`plan-en-desktop.png`, `plan-kk-mobile.png`. Screen-reader, реальные клиенты,
production latency и день персонала не сертифицированы.

## Документация и публикация

CRM/frontend/roadmap/acceptance и passports scheduling/clients/capabilities
обновлены. Денежный контракт ниже реализованного subset остаётся проектом.
README/setup, access framework, AI, integrations, operations не требуют изменения:
новых настроек/ролей/интеграций/AI-действий нет; схема и отсутствие working migration
явно описаны здесь и в scheduling. Исторические отчёты сохранены.

Preflight02.11: `git ls-remote origin refs/heads/main` вернул e02a28f5, равный HEAD;
старый foreign-outgoing blocker больше не актуален. Index пуст, `.git/index.lock`
существует с17:52:21, владелец неизвестен. Кроме lock, цикл зависит от
незакоммиченного предыдущего Records (`record_workspace.py`, RecordsPage и связанные
проекции), а рабочий frontend включает чужие notifications. Публиковать эти
prerequisites этим циклом нельзя без отдельного разрешения/их публикации.
Docs: `.venv/Scripts/python.exe output/visit-plans-20261102/final_manifest.py`
проверил34 source hashes/new-file whitespace, локальные ссылки/registry и
working/index diff hygiene. Первое чтение ссылки с угловыми скобками исправлено
в проверяющем скрипте, повтор PASS. Committed-range проверка неприменима без
собственного коммита. Own delta просмотрена относительно starting snapshot;
проверка новых строк на секреты/внешние URL совпадений не дала.
Ничего не staged/committed/pushed; нового CI этого цикла нет. Lock не удалялся,
история/ветка/чужие изменения сохранены. Deployment не выполнялся.

Остаток принятого code/evidence scope: нет выявленных незакрытых критериев.
Остаток интеграции: публикация после разрешения lock/prerequisites. Среда:
working scheduling0011 и live отдельно. Следующий кодовый цикл — версии цены и
распределение; решение для положительной пакетной цены при нулевой базе открыто.
