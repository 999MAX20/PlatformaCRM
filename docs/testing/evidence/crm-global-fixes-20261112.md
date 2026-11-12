# Исправления F01–F10 общей проверки CRM

Task: `CRM-GLOBAL-FIXES-20261112`, 12.11.2026. Все десять подтверждённых
дефектов [исходного аудита](crm-global-run-20261112.md) исправлены и адресно
проверены локально. Это scoped PASS, не полная приёмка CRM или release gate.

Поручение владельца: исправить F01–F10, повторить затронутые сценарии в
изоляции без реальных отправок, обновить отчёт с выполненным и остатком.
Checkout: `C:/Users/user/Desktop/PlatformaCRM`, ветка `codex/ui-testing-toolkit`,
исходный HEAD `46b5d22dc1ed5f5a51793743dd3fb3311a56ff2b` плюс сохранённый чужой WIP.
Проверялся составной рабочий снимок. Собственные пути и хеши записаны в
`output/crm-global-fixes-20261112/owned-paths.json` и `verified-source.json`.

## Исправлено и проверено

| ID | Изменение | Адресное доказательство |
| --- | --- | --- |
| F01 | Чтение клиентской CRM-карточки явно включает архив. В странице и modal доступно подтверждаемое восстановление с прежним backend permission | Backend archive/card/tenant; браузер: страница, reload, modal503→retry, Escape без записи, Enter с одной записью, обновление архивного статуса |
| F02 | Телефонная нормализация применяется только к строкам телефонного вида; цифры в имени/email не расширяют OR-поиск | До исправления 3 subtest FAIL; после 23 search/duplicate tests PASS; браузер и API возвращают только нужного клиента |
| F03 | Отдельные коды unfinished_work/future_appointments_conflict и сообщения для last_active_branch/schedule_conflict/invalid_transition. Stale version определяется отдельно | 92 domain/card/dependent tests PASS; 11 error/feedback Node PASS; браузер архивирования с активной работой показывает реальную причину409 |
| F04 | Полная страница клиента учитывает разрешения карточки и архивный статус для edit/tag/create/custom fields; archive/restore сохраняют проверку delete | Read-only browser/API: действий записи нет, прямой запрещённый запрос не изменяет данные |
| F05 | Refresh переноса обновляет запись и query cache, дату/ресурс/филиал/revision; отменённая или архивная запись не переносится | Реальный API: конкурентная отмена→409→refresh→видимый cancelled, очищенный слот и disabled submit; статус/время сохранены |
| F06 | Widget хранит conversation ID, последние100 подтверждённых пользовательских сообщений и draft в sessionStorage с ключом API/public token/visitor | Node parser/isolation; браузер reload продолжает тот же conversation ID, другой visitor не видит историю; запрет storage не ломает текущую отправку |
| F07 | Widget очищает ввод только после успешного ответа, сохраняет текст при ошибке и предлагает явный retry | Browser mock transport: отказ без записи→сохранённый draft→клавиатурный retry, один подтверждённый bubble; RU/KK/EN |
| F08 | Change-password возвращает replacement access вместе с HttpOnly refresh cookie; UI принимает access того же пользователя внутри cookie queue | 17 auth/MFA focused tests; 56 dependent tests; Node generation/identity/queue; реальная смена пароля→sessions/reload, старые credentials отозваны |
| F09 | Explicit demo reset удаляет защищённые настройки филиала/ресурсов в пределах выбранного demo Business перед collector | 10 demo tests PASS, повторный reset после room/requirement/schedule; чужой филиал и график сохранены |
| F10 | Системные follow-up задачи, шаблоны автоматизации, неизменённые preset roles, даты и audit/automation entity labels локализованы | 45 task/role tests и56 configuration/card/auth tests; RU/KK/EN tasks/account/records/templates; создание KK/EN draft rules с локальным action title |

F10 не переводит пользовательские данные: task `system_copy` выводится только
при совпадении provenance ActivityEvent и неизменённого генерируемого текста;
edited title/description остаются авторскими. Events загружаются одним запросом
на список. Preset-role key выдаётся только для неизменённой системной роли.
`apply-template.language` принимает ru/kk/en, default ru; созданное правило после
этого является обычным редактируемым правилом. Существующие правила не переписаны.

## Команды и результаты

Полные команды, fixtures, логи и снимки находятся в
`output/crm-global-fixes-20261112/CHECKPOINT.md`. Backend runner:
`.venv/Scripts/python.exe output/crm-global-fixes-20261112/verify.py --name NAME LABELS`.
Он использует `scripts.codex_verify.isolated_runtime`, отключённое чтение `.env`
и запрет внешних socket connections. Результаты групп не суммируются как уникальные:

| Проверка | Итог / журнал |
| --- | --- |
| Client search + duplicate detection | 23 PASS, `f02-after.log` |
| Demo seed/reset | 10 PASS, `f09-after.log` |
| Archive/card/client/plan/branch domain | 92 PASS, `f01-f03-domain.log` |
| Password rotation + MFA | 17 PASS, `f08-backend.log` |
| Task provenance, system roles, task domain | 45 PASS, `f10-dependent.log` |
| Automation configuration/authority, CRM cards, auth security | 56 PASS, `f10-template-dependent.log` |
| Error normalization/action feedback | 11 PASS, `f03-node.log` |
| Password replacement/widget session/token-CSRF | 13 PASS, `widget-auth-node.log` |
| Django check + makemigrations --check --dry-run | PASS, `completion-system-venv.log` |
| npm run build: i18n, tsc, app, widget | PASS, `build-completion.log`; 7289 keys RU/KK/EN |
| npm run check:bundle | PASS, `bundle-completion.log`; existing large locale warnings retained |
| Playwright targeted flows | PASS per named result files; initial failures retained below |

Browser scripts: `browser.mjs`, `browser-modal.mjs`, `browser-auth.mjs`,
`browser-reschedule-final.mjs`, `browser-widget.mjs`, `browser-template.mjs`.
Real isolated API is used except explicit widget transport mocks and injected503.
Final runtime used loopback58140/58141 and a disposable synthetic SQLite DB.
No real provider/send/working-data operations. These reruns use Playwright,
not a claim that the entire original Computer audit was repeated.

Cookie continuation regression: original suite 2 PASS/3 FAIL while holding
responses; Playwright click waited until request timeout in failed runs.
Adapted diagnostic harness uses noWaitAfter/direct DOM click only for that held
logout action, preserving order/identity assertions. Recovery4 PASS/2 FAIL;
remaining disableMfa and expired-access tests then2 PASS. Diagnostic timestamps
show click and release within63ms; earlier login failure is confirmed HTTP429.
Six distinct continuation/recovery scenarios passed across these runs, not one
clean original-suite PASS. Logs: `account-session-continuations.log`,
`account-session-recovery.log`, `account-session-diagnostic.log`.

Other retained attempts: initial F02 browser selector matched hidden native
elements; modal timing/selectors; reschedule fixture lacking available slots;
locales selector became ambiguous after creating a same-name rule. Selectors/fixtures
were corrected without weakening product assertions. Visual review found missed
ActiveSessions locale formatting; code was corrected, RU/KK/EN and full frontend
build rerun. `completion-system-final.log` used global Python without django-environ;
the required check passed using the existing `.venv`, with no dependency install.

## UI acceptance and review

Anti Slop during, existing design retained; React Best Practices scoped review.
No new assets, layout system, tokens, dependency or product navigation.

- Geometry/localization PASS: inspected actual screenshots at1440 and390 for
  client modal/page, reschedule, task, automation, account and widget; long KK
  labels wrap, affected content remains within containers.
- Actions/recovery PASS: archive restore/cancel/retry, permission denial, stale
  reschedule refresh, password/reload, widget retry and storage denial exercised.
- Keyboard/focus PASS: modal Escape and Enter, focus returned to the action menu,
  widget retry by keyboard; existing controls/focus styles retained.
- Purpose/copy PASS: additions are domain errors, real restore action, system
  translations or send status. User data and API authorization remain intact.
- Loading/empty/error PASS for affected recovery paths; no new standalone list
  or media. Asset, motion, theme-redesign and marketing gates N/A because unchanged.

Screenshots inspected include `archived-client.png`, `modal-restored-mobile.png`,
`readonly-client.png`, `reschedule-settled.png`, `task-kk.png`, `account-en.png`,
`sessions-en.png`, `sessions-kk.png`, `widget-error.png`, `template-created-kk.png`.
Screenshots of transient refresh were replaced by captures after final state;
original failed-run logs remain. Not a whole-product accessibility certification.

## Остаток и публикация

В принятом scope F01–F10 остатка кода/локальных адресных проверок нет.
Общая приёмка остаётся открытой: семь иных неуспешных test methods, три
неклассифицированных наблюдения, непокрытые варианты204-ID матрицы, load/S04,
live provider, production/deployment и полный release gate не закрыты этим исправлением.
Widget сохраняет локальную историю в текущей вкладке; серверный inbox sync и
exactly-once при потерянном успешном ответе не заявляются. Права/tenant/expiry,
notification/BusinessEvent semantics, AI confirmation, схемы и рабочая БД не изменены.

Контракты access/CRM/frontend/integrations и capability passport обновлены.
Roadmap phase/acceptance IDs не закрывались; README/setup, operations и AI contract
не требуют изменений для этих исправлений. Собственные runtimes остановлены;
никакие чужие процессы не останавливались. Git receipt и cleanup boundary в checkpoint.
Только собственный локальный коммит; normal push заблокирован чужим исходящим
диапазоном текущей ветки. Новые remote CI/deployment этим запуском не инициированы.

## Backend CI corrections — 12.11.2026

Owner separately authorized publication of all62 existing commits, then repair of
both failed backend tests, preserving local work, with green remote CI acceptance.
Published31fe3115; run43223669616: frontend PASS, backend3329 tests/2FAIL/77SKIP.
The two failures were outdated expectations already corrected in local test files;
this task reviewed and verified those existing edits without claiming authorship.

- VoicePlannerWireTests now asserts awaiting_confirmation and zero clients before
  explicit approval; confirmation and replay leave exactly one client with correct
  values. JSON-mode and malformed-output assertions remain.
- InitialLocationMigrationTests checks uses_business_defaults at historical0003,
  then0006 converts to explicit configuration; archived branches, service price,
  reverse migration, specialist schedule and appointment history remain asserted.

Base34f79b30. No production behavior, permission, notification, BusinessEvent,
AI policy, schema or working-DB changes. Contracts already describe these decisions;
roadmap/passport/UI/setup changes are not required. No general acceptance closed.

Isolated runner `output/backend-ci-fixes-20261112/verify.py` loads dirty Python
 dependencies from base Git blobs in memory, except the two selected test files.
No source checkout replacement or other writer edits. External sockets disabled.
Commands: `.venv/Scripts/python.exe output/backend-ci-fixes-20261112/verify.py`:

- `--name baseline apps.ai_core.tests_planner_json_mode apps.branches.tests_initial_location_migration`:5PASS. Despite name, this is candidate evidence; the isolated environment stripped the attempted baseline flag. Before-fix evidence is the remote failed run above.
- `--name dependent apps.ai_core.tests_voice_policy apps.ai_core.tests_voice_direct apps.ai_core.tests_approval_binding apps.branches.tests_management_transition apps.branches.tests_single_location`:64PASS.
- `--name system --checks`:Django check and migration drift PASS.

No local frontend rerun: test-only change; remote configured frontend job still runs.
Full remoteCI and push receipt are recorded in the checkpoint after publication;
local scoped PASS alone does not claim green remoteCI or deployment.
