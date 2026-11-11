# TIMELINE-FIXES-20261111 — история действий

Scope: все пять замечаний аудита `/app/timeline`, по поручению владельца11.11.
Canonical checkout, branch `codex/ui-testing-toolkit`, base
`1645163a754e075c384c304e4a2b846d8cca7d96`. Чужие STATUS/checkpoint и UI WIP
зафиксированы до изменений; не включаются в собственный продуктовый diff.

## Поведение

- Каталог ActivityEvents и известные generic model actions получили явные
  RU/KK/EN названия; dotted aliases читаются без миграции. Неизвестные типы
  сохраняют нейтральный fallback, сырой text не выводится.
- Детали читают сохранённые from/to и from_status/to_status, перенос времени,
  суммы из уже отфильтрованного API, сроки, активность и разрешённые названия
  изменённых полей. Произвольные fields/reason/source/token не показываются.
  Отсутствующее историческое значение не восстанавливается из текущего объекта.
- API list/retrieve добавляет read-only entity_name/entity_available/reference_names.
  Объекты выбираются пакетно через readable_queryset; имя услуги записи проверяет
  Business услуги. Этапы ограничены Business/pipeline сделки, имена ответственных —
  membership бизнеса либо его владелец. Текущие названия отделены от истории.
- Колонка показывает объект и отдельно клиента; задача без клиента имеет название.
  Ссылки требуют серверного entity_available и фронтенд-разрешения ресурса.
- Actor называется автором действия, а не исполнителем задачи.
- На телефоне компактные кнопки событий, поиск на доступную ширину, раскрываемые
  фильтры, закреплённая пагинация и одна прокрутка списка. Desktop сохраняет таблицу,
  категории, токены и inspector/drawer.

## Проверки

Команды из root через `.venv/Scripts/python.exe` и existing isolated_runtime;
одноразовые SQLite/loopback backend/Vite, synthetic accounts, внешняя сеть закрыта.

- `output/timeline-fixes-20261111/verify.py projection apps.activities.tests_timeline_workspace`:
  16 PASS/1 FAIL нового измерительного теста: холодный кэш сравнивался с прогретым
  (4 против1 SQL). Одинаковый прогрев исправил тест; продуктовый код не менялся.
- `.../verify.py projection-corrected apps.activities.tests_timeline_workspace`:
  17 PASS, system check и migration drift PASS.
- `.../verify.py references apps.activities.tests_timeline_workspace apps.core.tests_crm_projection_access apps.crm.tests_amount_projections`:
  62 PASS, system/drift PASS.
- `.../verify.py completion apps.activities.tests_timeline_workspace apps.activities.tests apps.activities.tests_note_read_scope apps.core.tests_crm_projection_access apps.core.tests_client_pii_projections apps.crm.tests_amount_projections`:
  113 PASS, system/drift PASS. Проверены роли/OWN/TEAM, foreign Business/object,
  отключённые capabilities, клиентские проекции, суммы, foreign user/stage/service.
- `node --test frontend/scripts/tests/timeline-presentation.test.mjs`:9 PASS.
  Каталог проверяется по исходной taxonomy для всех языков; aliases, статус/время,
  неизвестные поля, недоступный объект и отсутствие вымышленных значений покрыты.
- `npm run build` (frontend): i18n7105 keys, TypeScript, app/widget builds PASS.
  Повторён после последней правки отображения; `npm run check:bundle` PASS.
  Vite сохраняет advisory о двух RU/KK chunks >500kB; app-shell в бюджете400kB.

Browser: Chrome, отдельный fixture runtime из `output/timeline-fixes-20261111/runtime.py`.
RU desktop1536/mobile390, KK320, EN1024/1440/1536/390: список/детали, no_show,
перенос с timezone, этап сделки, назначение, переход к реальной task card,
категория, пустой поиск/сброс, обе страницы пагинации, Enter в inspector,
Escape/возврат фокуса. На1024×768 также нет внешней/горизонтальной прокрутки.
На390×844 и320×740 document равен viewport: внешней/горизонтальной прокрутки нет.
Пользовательские названия сохраняют язык исходных данных.
Контролируемая блокировка activity-events запросов только тестовой вкладки:
No connection; после снятия блокировки Retry восстановил28 результатов.
Неверный KK selector в ручной проверке исправлен по видимой подписи; это ошибка
проверки, не продукта. Скриншоты и исходные журналы находятся в task output.
Прямой переход оператора на timeline показывает отказ роли analytics, без данных.

## Границы

Нет миграций, domain writes, новых прав, notifications/BusinessEvent/AI/provider
действий. Рабочая БД не менялась; locale/fixture менялись только в одноразовой среде.
Full E2E/release gate и deployment вне scope. Выходящий диапазон содержит25 чужих
локальных коммитов: отправка этого диапазона не разрешена данным поручением.
Финальные build/browser проверки PASS. Scoped code/local-evidence остатка нет.
Публикация заблокирована чужим выходящим диапазоном; push/newCI/deployment не было.
Точный собственный коммит фиксируется в checkpoint после commit.

<a id="layout-refinement"></a>

## Layout refinement — TIMELINE-LAYOUT-20261111

User-requested refinement of timeline width/height and single date control complete.
Base2e555385; canonical root/current codex/ui-testing-toolkit retained. Foreign starting
STATUS/PRIMARY/leads-header/TaskFormModal changes preserved; explicit own paths only.
Clients workspace and timeline both x88/width1328 at1440; desktop top/bottom gaps16px,
page scrollHeight900 at viewport900. Mobile390x844 no document overflow;320 calendar
uses its existing internal scroll to keep controls reachable. Common DatePickerPanel
retained, no new picker; range atomic URL updates/page reset, apply/cancel/clear and
Enter/Escape/focus verified. RU/KK/EN actual browser inspected; desktop controls one row.
Commands: .venv/Scripts/python.exe output/timeline-layout-20261111/runtime.py (isolated
synthetic SQLite/API/Vite), build.py (node --test scripts/tests/timeline-presentation.test.mjs:
9PASS; npm run build: types/i18n/app/widget PASS; npm run check:bundle PASS).
Final checks repeated after viewport spacing corrections; earlier successful builds
are not claimed as proof for later changes. Final logs in output folder. Browser used
Chrome on isolated54402/54401. Working DB/dev services untouched. Test runtime stopped.
No backend contract/schema/permission/notification/BusinessEvent/AI/provider changes;
prior113 backend PASS remains unchanged-input evidence, no redundant full gate.
Frontend contract and existing evidence updated; roadmap/passport/README/other contracts
need no change: this is layout/filter presentation only, no changed business behavior.
No scoped code/local-evidence remainder. Publication blocked by26foreign outgoing
commits at task base; no permission to publish that range. Own local commit only,
no push/newCI/deployment. Screenshots and initial diff: output/timeline-layout-20261111.
