# ENTITY-CARDS-20261105 — client modal

State: local implementation and scoped verification complete; publication blocked. Owner requested complete discussion documentation
and implementation beginning with Client. Canonical checkout, branch
codex/ui-testing-toolkit, HEAD66101d509cb7642b2928275e48c4b64354abf07b + preserved WIP.
Starting status/diff and exact affected-file copies: output/entity-cards-20261105.

## Contract before implementation

Mode: implementation + documentation. Observable result: client opens in a centered,
unblurred modal matching the approved reference, retaining real data and permitted
actions. Gap: UI code + scoped evidence. Reuse Dialog focus/scroll primitives,
crmCardsApi, appointments workspace API, related panels and existing client actions.
No other entity redesign, backend/domain/migration/live change. Risks: focus/nested
layers, action parity, truncated related lists, stale actor data and drafts.
Focused checks: real HTTP isolated client flows, roles, nearest appointment, retries,
locales/viewports/keyboard; representative old overlay. Completion: safe isolated
build/types/i18n/bundle, documentation consistency and diff hygiene. No installs.

Specification and all future proposals: [entity-cards](../../current/entity-cards.md).
Existing .git/index.lock and foreign outgoing history require publication review;
do not delete lock, stage mixed files wholesale, or push unrelated work.

## Implemented local behavior

- Client routing through CrmEntityDrawer now selects ClientCardModal, keyed by
  actor/Business/id. Other entity types retain the previous Drawer.
- Shared Dialog has an opt-in entity presentation: centered1080px, unblurred
  backdrop at the drawer layer, independent header actions and footer. Existing
  dialogs retain their size, background and layer. No global blur/token replacement.
- Client has contact/responsible/note/tag aside, booking/message actions and action
  menu; existing edit/tag/archive/payment flows remain. Main tabs are Overview,
  History, Appointments; remaining six sections use More. No decorative KPIs.
- Record-scoped available_action_details gates editing/booking; existing resource
  permissions gate other actions and related view entry points. Backend remains
  authoritative; no permission framework or domain writes were changed.
- Next appointment reads existing /api/appointments/workspace/ with client,
  planned workflow, Business-local date and ascending order. It walks pages until
  finding end_at>now; backend excludes archived records. This is independent of
  the25-row descending related preview. A current unfinished visit qualifies.
- Card re-open refreshes data. Authentication/permission/not-found errors conceal
  cached payload; a temporary background failure retains the draft and exposes retry.
  Nearest query
  has its own empty/error/retry state and minute refresh while Overview is mounted.
- Notes/custom fields/file selections report draft/pending state to the modal.
  Escape, backdrop, footer, tab changes and route changes protect them. Client
  edit/tag dialogs launched from this card also protect drafts/pending saves;
  ordinary callers of ClientForm retain their previous behavior.
- Overview and optional reused history/appointment/note formatting use the current
  locale and Business timezone; timezone also controls history date grouping.
- Existing full client/appointment pages are navigation targets. A single-shell
  client↔appointment stack remains a future proposal, not implemented in this stage.

## Verification receipts

All commands from C:/Users/user/Desktop/PlatformaCRM. No dependency install.

1. `node --test frontend/scripts/tests/clients-toolbar.test.mjs frontend/scripts/tests/client-search.test.mjs`:
   12PASS. Filter/search consumer behavior retained; not a complete client suite.
2. `node node_modules/typescript/bin/tsc --noEmit -p tsconfig.app.json` from frontend:
   PASS after fixing an initially missing JSX closer. The earlier tsconfig.json
   invocation has references only and is not counted as application type evidence.
3. `.venv/Scripts/python.exe output/entity-cards-20261105/run.py`:
   run1793825284688587200:7PASS/2FAIL; run1793825555491082500:9PASS/1FAIL;
   run1793825790949624200:11PASS/1FAIL. Failures retained, not relabelled green.
4. Same runner `--grep 'forbidden refresh|mobile sections'`:
   run1793826023078130600: denial/retry/empty PASS, new mobile harness failed.
5. Same runner `--grep 'mobile sections'`: run1793826236620097100:1PASS.
6. Same runner `--build`: run1793825815447491800: build/types/i18n6894 and bundle
   PASS. After the final locale/timezone delta, run1793826415687145900 also PASS.
   Superseded by the final background-error build below. RU/KK dictionary chunks >500kB
   are advisory; the required400kB app-shell budget passes.
7. Final affected rerun `--grep 'notes preserve|localized responsive|mobile sections'`:
   run1793826405413895000:5PASS, including actual localized history grouping and
   appointment dates, mobile navigation and the unchanged Appointment drawer.
8. After separating transient refresh failures from access loss, same runner
   `--grep 'temporary refresh|forbidden refresh|nested client edit|pending note'`:
   run1793826648900590300:4PASS. A503 after reconnect retains unsaved note text;
   retry recovers, while403 conceals the previous payload. Nested edit/tag and
   pending-save boundaries passed again.
9. Final same runner `--build`, run1793826659143431400: build/types/i18n6894/bundle
   PASS. No product source changed after this build and final affected rerun.

Fourteen distinct scoped browser scenarios passed across the recorded runs and
affected reruns. This is not a claim of one all-green full-project/E2E suite.
Documentation checker: `.venv/Scripts/python.exe output/entity-cards-20261105/validate.py`:
links/unique registry entries/new-file whitespace plus working/index diff hygiene.
No own committed range exists; committed-range checking is therefore inapplicable.

Real HTTP/browser scenarios include nearest outside truncated relations; keyboard
tabs/focus/list restoration; notes save/discard/navigation/pending; edit/tag/custom
fields; payment drawer; create-booking and full-page routes;403/retry; empty next
visit; viewer denial; file upload; archive reason/cancel; RU/KK/EN1440/768/390;
mobile secondary sections and existing Appointment drawer. Fixtures are synthetic
and isolated; clicks do not send external messages or perform real payments.

Failure analysis: re-open initially reused a fresh five-minute cache; explicit
staleTime0 now revalidates. The original empty test clicked preserved previous rows;
subsequent diagnostic showed numeric00 also matched fixture phone numbers, so the
empty scenario now selects an actual matching demo client using a nonnumeric term.
English login once stayed on /login after successful token/me responses; subsequent
stable runs passed; no unrelated auth rewrite. The new mobile test initially selected
the hidden desktop opener; it now targets the visible mobile/desktop controls.
Visual inspection found conflicting Dialog body padding/background and an
appointment-specific responsible label; both corrected. Earlier pictures are not
the final visual receipt. Source and harness failures are distinguished above.

## Environment, documentation and publication

Uses scripts.codex_verify.isolated_runtime, guarded runtime prepare and canonical
sources, disposable SQLite/media/ports, fake scanning/eager jobs and disabled external
providers. Working database was not used or migrated. No backend change, so no new
backend/system/migration gate; no full-project, release, live-provider or deployment
claim. Each runner owns/stops its test runtime.

Registered specification and evidence, retained reference image, updated frontend
contract/clients passport and checkpoint/STATUS. Domain/access/AI/operations contracts,
root README and existing roadmap acceptance need no changes: no policy, setup,
domain or authorized roadmap phase beyond this new Client task changed.

Publication remains blocked: existing .git/index.lock; current branch has no upstream;
local comparison to origin/main shows17 pre-existing outgoing commits. Origin is
https://github.com/999MAX20/PlatformaCRM.git. No stage/commit/push/newCI/deployment,
no lock deletion, history edits or publication of foreign work. Own dirty delta and
hash manifest are recorded separately under output/entity-cards-20261105.


## Final boundary and visuals

No remaining Client implementation or scoped local verification item. Other
entities are documented proposals only; Appointment is the next unstarted stage.
Publication remains unresolved as above; no CI or deployment acceptance inferred.
Owned test runners exited; no shared development server was started/restarted.

- [Owner reference](entity-cards-20261105-assets/reference.png)
- [Client desktop — isolated synthetic data](entity-cards-20261105-assets/client-ru-1440.png)
- [Client mobile](entity-cards-20261105-assets/client-ru-390.png)
- [Mobile history](entity-cards-20261105-assets/client-ru-mobile-history.png)

Screenshots reviewed for composition, unblurred backdrop, white surface, spacing,
readable headings, scrolling and reachable controls. Keyboard/focus/draft behavior
comes from browser scenarios, not from screenshots. No full WCAG certification.

## Компоновка клиента и общая строка вкладок05.11

По поручению владельца клиент использует компоновку записи: имя/признаки и
контакты слева, действия/голос/страница/закрытие сверху, вкладки сразу справа.
На телефоне/планшете действия отдельным рядом; «Написать» на телефоне — иконка
с прежним доступным названием. Ничего автоматически не отправляется.
ClientCardOverview сохраняет ближайшую запись, но service/resource имеют
минимальную flex-basis144px: длинные значения на планшете не сжимаются в одну букву.
В Client и Appointment один EntityCardTabs: полная строка доступных вкладок,
скрытый scrollbar, touch/trackpad, стрелки по переполнению, Left/Right/Home/End,
автопрокрутка активной вкладки только по горизонтали. Старый Select «Ещё» удалён.
Исторические связи содержали только EntityDealsPanel: вкладка/рендер удалены
только из Client, initialTab=deals возвращает Обзор. Данные/API/прочие consumers
сделок не удалялись. Права, guard черновика/pending, переходы, учёт и формы сохранены.

Canonical codex/ui-testing-toolkit/66101d50, существующий WIP сохранён. PLAN,
исходники/owned.patch/SHA256, harness/receipts: `output/client-layout-tabs-20261105/`.
Никаких новых зависимостей, рабочей БД, миграций, провайдеров или deploy.
- `.venv/Scripts/python.exe output/client-layout-tabs-20261105/records-run.py --browser --grep 'modal layout|draft close'`:4 PASS (`records-browser-1793895297297646200.log`), обе карточки/переходы и RU1440/KK390/EN390, notes/save/recovery/pending.
- `run.py --grep 'reference layout|notes preserve|nested client|pending note|viewer|localized responsive|mobile sections|single tab|nested edit'`:9 PASS/2FAIL (`browser-1793895286673415100.log`). Прошли новые overflow/keyboard/draft/no-legacy проверки, role и формы. Два старых ожидания были от прежней клиентской фазы: next appointment Link и Appointment Drawer/direct reschedule button. Текущая принятая модель — modal button + action menu; локальный harness уточнён, продуктовые требования не ослаблены.
- `run.py --grep 'reference layout|mobile sections'`:1 PASS/1FAIL (`browser-1793895538777713300.log`): ближайшая запись/возврат PASS, оставшееся старое ожидание direct reschedule заменено проверкой menuitem и двухшагового Escape.
- Первый build/types/i18n6895/bundle PASS. При визуальной проверке выявлено сжатие service/resource на768 и перенос мобильного меню в третий ряд; внесена описанная выше scoped-правка. После неё финальные locale/browser/build проверки указаны ниже.
Backend/full E2E/release не запускались: контракт сервера неизменен, выбран affected
UI boundary. Client/server permissions проверены прежними API и scoped viewer case.

Spec/frontend согласованы с новым расположением и отсутствием deals tab. CRM/access/
AI/product/operations/README не меняются: домен/права/setup прежние. Существующий
roadmap не имеет отдельной строки этого уточнения; этапы других сущностей не начаты.
Публикация заблокирована существующим index.lock/17foreign outgoing; index пуст,
история/lock сохранены. Собственного commit/push/newCI/deploy нет.

Финальная проверка после scoped responsive fix:
`run.py --grep 'localized responsive|mobile sections|single tab|viewer'`:6 PASS
(`browser-1793895684549556200.log`). Итого11 различных клиентских сценариев прошли
в перечисленных запусках; плюс4 appointment-case. Это не единый полный rerun.
`run.py --build`:build/types/i18n6895/widget/bundle PASS
(`build-1793895643093481000.log`, `bundle-1793895643093481000.log`).
Повторные неизменённые backend/full suite/dependency install не требовались.
[Desktop](entity-cards-20261105-assets/tabs-layout-desktop.png),
[tablet](entity-cards-20261105-assets/tabs-layout-tablet.png),
[mobile](entity-cards-20261105-assets/tabs-layout-mobile.png),
[вкладки записи](entity-cards-20261105-assets/appointment-tabs.png).
Скриншоты просмотрены: полная строка desktop, arrow/обрезанный следующий tab на
узких экранах, без видимого scrollbar; readable nearest record и два ряда mobile.
Taste/AntiSlop scoped purpose/quality PASS: реальные разделы и действия, прежние
токены/типографика, без новой стилистики/ассетов/маркетингового текста. React review:
единственный общий tab component, ResizeObserver/listener cleanup, прежний guarded
onChange, API/query/tenant identity сохранены. Scoped docs links/whitespace/owned
patch review PASS. В принятом scope остатка кода/локальных проверок нет; публикация
по прежнему блокирована. Тестовые runner завершены, working DB/dev не менялись.

## Фиксированный размер клиента и записи05.11

Владелец утвердил [визуальный референс](entity-cards-20261105-assets/fixed-size-reference.png)
и попросил применить ко всем текущим карточкам — Client и Appointment.
Dialog presentation=entity теперь имеет ширину до1080px, высоту90dvh от640px;
на телефоне calc(100dvh - 24px). Размер не зависит от вкладки/loading/error.
При1440×900 фактическая карточка1080×810, центр x180/y45. Остальные Dialog/Drawer
не получают фиксированную высоту; проверены два существующих entity callers.
От768px шапка/вкладки остаются на месте, sidebar и tabpanel прокручиваются
независимо. В правой панели stable scrollbar gutter предотвращает горизонтальные
сдвиги содержимого. На узком экране единое тело, вкладки sticky. При смене вкладки
панель начинает сверху, переключение по-прежнему проходит draft/pending guard.
Нет domain/API/permissions/DB/migration/notification/BusinessEvent/AI изменений.

Canonical codex/ui-testing-toolkit/66101d50 + сохранённый WIP. PLAN/originals/
owned.patch/SHA256/exact logs: `output/entity-fixed-size-20261105/`.
- `.venv/Scripts/python.exe output/entity-fixed-size-20261105/run.py --grep 'fixed client|notes preserve|pending note|nested client edit'`:5 PASS/1FAIL (`browser-1793897899296739800.log`). Desktop/tablet geometry/loading/error/scroll, notes/draft/pending и обычные вложенные edit/tag dialog PASS. Mobile остановился в test-only strict selector: direct div находил также portal NotificationHost. Уточнён до header+body; runtime не изменён.
- `.venv/Scripts/python.exe output/entity-fixed-size-20261105/records-run.py --browser --grep 'fixed appointment|draft close|reschedule pending'`:5 PASS (`records-browser-1793897909506702200.log`), все вкладки RU1440×900/KK768×900/EN390×844, unchanged x/y/width/height, draft/recovery/pending и вложенный перенос/отмена.
- `run.py --build`:build/types/i18n6895/widget/bundle PASS (`build-1793897919880090000.log`, `bundle-1793897919880090000.log`). Существующие locale chunk warnings сохранены, shell budget PASS.
Browser использует изолированные DB/порты; build без переустановки зависимостей.
Backend/full-project/E2E не запускались: frontend-only изменение. Скриншоты не
выдаются за backend/production доказательство. Проверки геометрии проверяют
наблюдаемую стабильность при переходах/ошибках, не только наличие CSS-классов.

Spec/frontend обновлены; паспорта клиента/расписания отражают общую оболочку.
Roadmap не имеет отдельной строки этого уточнения; новые сущности не начинались.
CRM/access/AI/operations/README без изменений — домен, права и setup сохранены.
Публикационный блок прежний index.lock/17foreign outgoing; нет собственного
commit/push/newCI/deployment. Чужие diff/lock/history и общий dev/workingDB сохранены.

Финальный mobile rerun `run.py --grep 'fixed client.*en'`:1 PASS
(`browser-1793898205235111600.log`). Итого6 различных Client и5 Appointment
сценариев прошли в указанных запусках; повторные случаи не суммируются.
После build изменялся только test-only locator, продуктовый код неизменен.
[Клиент desktop](entity-cards-20261105-assets/fixed-client-desktop.png),
[клиент mobile](entity-cards-20261105-assets/fixed-client-mobile.png),
[запись desktop](entity-cards-20261105-assets/fixed-appointment-desktop.png),
[запись mobile](entity-cards-20261105-assets/fixed-appointment-mobile.png) просмотрены.
Проверены геометрия/скролл с настоящими API/synthetic fixtures, не статическая
подмена данных. RU/KK/EN,1440/768/390, клавиатура/focus/guards и nested dialog PASS.
Taste/AntiSlop: размер и пустое место служат стабильности рабочей области;
прежние tokens/fonts/цвета, нет декоративных блоков. React review: conditional
entity-only shell, прежние query/permission hooks; key панели меняется только
после guarded tab switch, refresh не уничтожает draft. Scoped diff/links/whitespace
и SHA256 сверка PASS. Тестовые runner завершены. В принятом scope остатка
кода/локальных проверок нет. Index пуст, lock/17foreign outgoing сохранены,
remote main0b3348e1 подтверждён; публикация/CI/deploy не выполнялись.

Первый финальный link scan застал отсутствующую voice-natural-20261105.md из
параллельного голосового изменения. До повторной проверки файл появился;
повторный scan не нашёл отсутствующих ссылок. Чужой раздел/файл не изменялся.
Финальные source SHA256 и scoped links/whitespace PASS.
