# DENTAL-MCS-20261122: полная реализация медицинского ТЗ

## Активный этап К06; К05 открыт и ожидает решений по assistant/support

К06 plan_steps current checks: focused28PASS1.448s, dependent84PASS7.492s (пересекаются; content/API/services/reads/correction/snapshot/preview); TEMP/dental-k06-plan-{focused,dependent}-20261123.log. Check/drift PASS, migration не нужна. BuildR1 остановлен i18n: отсутствующий common.delete заменён собственным medical.plan.remove; медицинский KK заголовок зарегистрирован точным ключом в industry-terms. BuildR2 types/i18n8048/widget PASS. BrowserR1 ошибочный anchored grep не выбрал тесты, данных не создал. R2 обнаружил fixture business ID≠1 и нестабильное getByLabel после reorder/reopen при корректном accessible textbox в trace; остановлен принадлежащий задаче run после повторения. Recovery теперь получает Business/Patient из реального appointment context; новый шаг ищется по textbox+accessible name, проверки содержимого/фокуса сохранены. CorrectionR1 desktop дошёл до сохранения и упал на таком же locator; mobile получил409 из-за незавершённой desktop correction. R3:2PASS1.2m (RUdesktop+recovery); R4:5PASS2.6m (остальные locale/viewport). Итого7 distinct main browser scenarios. CorrectionR2:2PASS1.1m; при просмотре mobile screenshot тест уточнён, чтобы заполнять именно новый последний шаг, а не ранее сохранённый первый; отдельный mobileR3:1PASS50.4s на свежей БД. Это2 distinct correction scenarios, повтор не суммируется. Final17 captures inspected:6 editor+6 history RU/KK/EN1440/390,3 recovery,2 correction; дополнительно просмотрен предыдущий mobileR2. Anti Slop scoped Delivery Gate PASS:44px actions, wrapped mobile controls without overflow, keyboard reorder/focus, cancel/confirm, exact versions, loading/empty/retry/409/403/dirty flow, axe0. TEMP/dental-k06-plan-browser-r3/r4-20261123.log; dental-k06-plan-correction-r2/mobile-r3-20261123.log; output/playwright одноимённые папки. Static base4897b964 PASS: dental-k06-plan-static-20261123.log. Локальная приёмка этого сценария завершена; публикация готовится. Полный К06/M10 OPEN — VisitPlan/tooth links, подтверждённое преобразование, templates/snippets/team отдельно. README/access/operations/integrations/внешнее ТЗ не меняются: прежние права/среда/согласованные требования. Миграций/working DB/deployment нет.

К06 M10 contract before code: существующий encrypted encounter.content.plan уже хранит общий текст и имеет версии/автора/audit. Минимальный code delta — optional plan_steps [{id UUID, description text≤4000}], максимум100, последовательность задаёт порядок. Это шаги черновика текущего приёма, без нового агрегата/прав/календаря/денег. Старые версии и plan text сохраняются; structured steps несовместимы с not_applicable.plan. UI переиспользует ClinicalSectionInput, Textarea/Button и dirty/retry/403/409 guards: добавить, изменить, переместить кнопками, удалить с подтверждением, перечитать историю. Correction и snapshot сохраняют те же данные. Skills прежние zani-domain/frontend/verification + Anti Slop during/ui/human/layoutmobile/copy: existing tokens,44px actions, keyboard reorder/focus, RU/KK/EN desktop/mobile. Checks: validator/encrypted roundtrip/API/replay/revocation/snapshot/correction/no-money effects, affected suites/check/drift/build и browser changed flow+recovery. Отдельные незакрытые критерии M10: связи VisitPlanStep/одонтограмма и явное подтверждение преобразования в календарь; данный срез их не закрывает. CI9c2b run45089337188 пока in_progress.

К06 черновик назначения — scoped local acceptance PASS: domain/API +57 dependent SQLite и13 PostgreSQL (2 real races), check/drift и intentional0030. Финальная build/types/i18n8038/widget PASS: TEMP/dental-k06-orders-build-final2-20261123.log. Browser7 distinct scenarios приняты по R4(6PASS) +R5ENdesktop(1PASS27.3s): RU/KK/EN1440/390 create/edit/version history, dirty-close retention, focus return, axe0/overflow0; mobile503→same-key retry, real409 preserves draft/reload, actual role revoke403 clears orders. R4ENdesktop не дошёл до medical workspace: auth/csrf net::ERR_ABORTED после немедленной навигации из bootstrap; тест ждёт успешного auth/me перед переходом, R5 повторил только этот сценарий. Это не отказ медсервиса и не повод переписывать auth.
Просмотрены21 capture:6 неизменённых draft форм из orders-r2-20261123;10 history/list из orders-r4-20261123 для5passed locales/widths,2 ENdesktop из orders-en-desktop-r5-20261123,3 recovery из R4. Anti Slop scoped Delivery Gate PASS: существующие tokens/controls,44px targets, readable labels/states, no overflow, keyboard/focus, empty/errors/retry/history и desktop/mobile. Snapshot не доказывает права: backend negatives отдельно выше. Предыдущие попытки сохранены; повторы не суммируются как новые сценарии. README/access/operations/integrations/внешнее ТЗ не менялись — прежние permissions/provider/env и утверждённые требования; новые endpoints/данные/UI описаны frontend/modularity/capabilities. Подпись, PDF/выдача, утверждённые snippets/шаблоны назначений, клинический план и остальные критерии К06 остаются OPEN. Рабочая БД не мигрирована; schema rollback проверен для пустых order tables, не заявлен как удаление реальных назначений. Опубликован9c2b9fae93970dc3df985b44aad3155c51b125dc normal FF origin/main и SHA readback PASS; static base59cbd85b и committed-range hygiene PASS (TEMP/dental-k06-orders-static-20261123.log). CI нового commit ещё проверяется; deployment/working-DB migration не выполнены. Следующий независимый сценарий К06 — клинический план лечения (M10) поверх существующих VisitPlan/Step связей.

К06 назначения initial checks: validator3PASS; domain+validator9PASS0.423s (R1 NameError BusinessMember в new model.clean, исправлен локальный import); API5PASS0.586s. Dependent57PASS36.194s, включая empty schema0030→0029→0030 и существующие encounter/participation/tooth/document audit/read/write suites. TEMP/dental-k06-order-content-20261123.log, order-services[-r2], order-api, orders-dependent logs. PostgreSQL17 disposable13PASS14.053s, включая duplicate-create и competing-update races; TEMP/dental-k06-orders-postgres-20261123.log. PG остановлен, рабочие БД не использованы. Check/drift PASS, migration0030 intentional.
BrowserR1:2PASS4FAIL: fixture flag очищался safe_environment; перенесён до configure_browser_runtime, как остальные flags. Обнаружен focus-return дефект нового history dialog. R2:5PASS1FAIL (RUdesktop focus), R3:RUdesktopPASS после stable return-id + запрета history во время list refresh; recovery assertion ожидал raw503, а API client правильно показал localized actions.errorTemporary. Исправлено ожидание, сохранены проверки удержания ввода/same key/real409/revoke. Неверный reused label «История приёмов» заменён на «История назначения» RU/KK/EN. R4/R5 и финальная visual/build приёмка описаны выше. Повторные прогоны не считаются новыми сценариями.

К06 следующий scenario contract: M16/§2.2,6/D09 — врач создаёт отдельное назначение-черновик текущего приёма, перечитывает версии и редактирует своё. Gap code. Reuse patient/encounter, existing medical_prescriptions permissions, appointment/participation basis, encrypted storage, idempotency/audit and existing form/dialog/history patterns. Новые MedicalOrder/Revision с явным author/state; семь типов §6, свободный текст и ручные medication fields (название/доза/путь/частота/длительность). Никакой автоматической дозировки, брони или денег; подпись/PDF/выдача остаются зависимыми К08–К11. Ассистент/team ждут К05, не получают новый обход. Проверки: tenant/role/branch/current basis, author-only update, stale/replay/revoke, encrypted payload/tamper/audit rollback, migration isolated forward/back, API private errors, UI desktop/mobile locales/loading/empty/error/retry/dirty/focus; affected suites/check/drift/build и PG concurrency. Skills прежние zani-domain/access/frontend/verification, Anti Slop during+ui/human/layoutmobile/copy: existing components/tokens,44px controls, scoped memory-only PHI, honest draft state. Рабочая БД/провайдеры не меняются.

К06 неприменимость — локальная приёмка PASS. Focused22/0.700s и dependent78/7.938s (пересекаются): TEMP/dental-k06-not-applicable-focused-20261123.log и dental-k06-not-applicable-dependent-20261123.log. Дополнительный полный API module10/0.626s подтвердил replay и отказ replay после отзыва; dental-k06-not-applicable-api-module-20261123.log. Два отдельных method-only запуска Python завершились native Windows0xC0000005 (replay/replay-r2 logs; faulthandler указывает pathlib); причина не установлена, это не FAIL assertion. Проверяемые assertions прошли в модуле, код ради аварии не менялся.
Build/types/i18n8018/widget и check/drift PASS: dental-k06-not-applicable-build-20261123.log, dental-k06-not-applicable-check-drift-20261123.log. Миграций нет; рабочая БД не затронута. Browser7PASS2.5m (6locale/viewport + recovery), template2PASS26.1s, correction2PASS48.7s; соответствующие TEMP/dental-k06-not-applicable-{browser,template-browser,correction-browser}-20261123.log. Просмотрены10 новых captures:6 clinical-not-applicable,2 template selector,2 corrected-not-applicable в output/playwright/{clinical,template,correction}-not-applicable-20261123. RU/KK/EN desktop/mobile geometry, labels, required reason/focus, отмена замены сохраняет текст, save/reopen/history, literal template insert, correction сохранение, axe/overflow и прежний recovery PASS. Mobile selector сокращает длинную выбранную подпись; полный текст доступен в option, соседняя кнопка помещается.
Anti Slop scoped Delivery Gate PASS; это приёмка конкретного сценария, не всего К06/ТЗ. Frontend contract/паспорт/modularity согласованы; README/access/operations/integrations/внешнее ТЗ не меняются: прежние права/окружение и утверждённое B09. Остаток К06 — структурированные план/назначения; финализация К10 отдельно. Опубликован4897b964e103f41163b9144e7f6983286ad85b72 normal FF origin/main, SHA readback PASS; static base4a69f538 и committed-range hygiene PASS (TEMP/dental-k06-not-applicable-static-20261123.log). CI4897 ещё не проверен. CI59cbd85b run45085057479 in_progress, не PASS.

К06 contract before code: B09/§22.6 +design§5.2 требуют явной
неприменимости раздела с обоснованием. Gap code; reuse encrypted content/version/
audit/writers/history/snapshot и existing checkbox/Textarea. Технический формат:
optional content.not_applicable {clinical_field: reason}, только существующие
clinicalFields, непустая причина≤2000, исключает одновременно непустой clinical
text того же поля. Старые версии без map остаются без отметок; никакой миграции/
автоматического «не применимо». Запись — только по прежним полномочиям врача;
snapshot сохраняет map, template получает отдельную явную reason-подстановку,
обычная clinical.field не превращается в выдуманный медицинский текст.
UI checkbox44px +обоснование, подтверждение замены непустого текста; история
показывает отметку и причину. Existing PHI memory/denial/dirty/retry guards сохраняются.
Checks: validation/roundtrip/history/snapshot/render/API/denial/rollback, dependent
writers/readers, reachable desktop/mobile RU/KK/EN, new marker in correction/
template consumers, build/check/drift/static. Новых permissions/money/notifications/
BusinessEvent/AI/env эффектов нет. Не закрывает финализацию К10 или весь К06.

К05 regression tests опубликованы4a69f538e0c8cbbc6c93e0a54686033bdbc9be9b,
normal FF origin/main и SHA readback PASS. CI текущего commit ещё не проверен.
К05 не закрыт: два заданных вопроса о полномочиях блокируют оставшиеся assistant/
support сценарии. Единственный активный этап теперь К06; К03/К04 вопросы сохранены.

К06 contract before code: M08, §4.2, E2. First independent scenario — врач в текущем
приёме записывает аллергии/противопоказания, перечитывает точную версию и использует
эти поля в утверждённом шаблоне. Gap code: сейчас7 clinical fields, этих двух нет.
Reuse encrypted encounter versions, primary/correction writers, read/audit/ACL,
existing draft/history/forms and document snapshot/template field selector.
Не новая модель/общий CRM текст; не автоматическое заключение «рисков нет».
Scope не меняет назначение/лекарства/деньги/права/AI; team projections ждут К05.
Риск PHI и потеря нового поля при чтении/исправлении/документе. Focused storage/
service/API/snapshot tests, existing dependent read/write tests once at completion;
RU/KK/EN desktop/mobile real save/read and applicable recovery, visual inspection,
build/types/i18n once. Schema migrations не ожидаются. Skills: прежние zani-domain/
frontend/access/verification, Anti Slop during +ui/layoutmobile/human/copy.
Applied UI: existing Textarea/control sizes/tokens; labels RU/KK/EN from §4.2;
memory-only PHI and retained input/retry; empty field means not recorded, never
absence of risk. Полный К06 (план/назначения/неприменимость) остаётся открытым.

К06 risk fields local acceptance: focused3PASS0.508s, dependent74PASS16.239s,
TEMP/dental-k06-risk-fields-focused-20261123.log и dental-k06-risk-dependent-
20261123.log. Покрыты encrypted API save/read/history/denial/invalid type, literal
template placeholders/missing fields, immutable document snapshot после изменения
encounter, новые поля через24h correction writer, прежние permission/replay/audit
guards. Check/drift PASS (dental-k06-risk-check-drift-20261123.log), миграций нет.
Build/types/i18n8014/widget PASS (dental-k06-risk-build-20261123.log), session89611exit0.
Static basef745bab1 PASS (dental-k06-risk-static-20261123.log).

Browser main7PASS2.8m:6RU/KK/EN desktop1440/mobile390 save/reopen/current+old history,
unsaved navigation/focus/axe0/overflow0,1mobile503/retry same key/real409/revoke403.
TEMP/dental-k06-risk-browser-20261123.log. R2 main6PASS2.2m: повтор для visual capture
с явным scroll center; после проверки PNG выяснилось, что исходные файлы также
полные130px, сокращённым выглядел вывод просмотрщика. Это повтор, не6 новых сценариев.
TEMP/dental-k06-risk-browser-r2-20261123.log;12 final field screenshots из
output/playwright/clinical-risk-fields-r2-20261123 просмотрены.3 recovery screenshots
из первого run также просмотрены; длинная форма прокручивается внутри dialog.
Template selector2PASS23.3s desktop/mobile, literal insertion/focus/save,2captures
просмотрены: dental-k06-template-risk-browser-20261123.log,
output/playwright/template-risk-fields-20261123.
Correction consumer2PASS46s desktop/mobile request→approve→edit→reopen→finish;
2captures просмотрены: dental-k06-correction-risk-browser-r2-20261123.log,
output/playwright/correction-risk-fields-r2-20261123. R1: exact getByLabel не находил
label с загруженным textarea content; trace подтверждает textbox с правильным
именем/значением. Исправлен locator на getByRole(textbox), assertions сохранены.
Второй R1 получил409 от оставшегося active request первого; R2 на свежей disposable
fixture исключил зависимость. Product logic ради теста не изменялась.
Anti Slop scoped gate PASS:19 final captures inspected, geometry/labels/states/
keyboard/focus/locales/recovery; не весь модуль. Реальные PHI не использовались.
README/access/operations/integrations/внешнее ТЗ не требуют изменения: права,
провайдеры, окружение и уже описанное требование §4.2 прежние. Frontend contract/
capabilities/modularity и матрица согласованы. Опубликован59cbd85b57026d1da677fd48b528c2eb6b55d186,
normal FF origin/main и SHA readback PASS. Final static basef745bab1 PASS
(TEMP/dental-k06-risk-static-final-20261123.log), committed range hygiene PASS.
CI текущего commit ещё не наблюдался; f745 CI45082898662 frontend success/backend
in_progress на последнем чтении. Далее К06 explicit not-applicable sections.

Срез К05: проверка совместного существования appointment/participation/
24h correction и приоритета security revoke. Prior result: каждое основание уже
проверено отдельно → недостаёт совместной матрицы → минимальная дельта focused
regression tests, без переписывания writers/readers. Base f745bab1. Высокий риск:
старые actor/basis и idempotency replay не должны переживать отзыв account/member/
medical role/branch/module. Проверить независимость закрытия оснований, чтение и
запись/replay, неизменность истории при отказе; изолированная SQLite, targeted suite.
UI/миграций/провайдеров нет, прежние browser/build/PG результаты сохраняются при
неизменном product code. Если обнаружится дефект, расширить проверки по его влиянию.
Вопрос о назначении ассистента отправлен владельцу: primary physician/head,
подтверждение ассистентом, отзыв и завершение вместе с приёмом. Ответ ожидается;
это блокирует только зависимый assistant scenario, не независимые проверки К05.

Результат:6 focused tests PASS (5 в1.543s, отдельный real role revoke в0.131s),
TEMP/dental-k05-basis-combinations-r2-20261123.log и dental-k05-security-revoke-
20261123.log. R1:3PASS/2ERROR из-за неверного аргумента action вместо decision
в новом test helper; исправлен только тест, assertions сохранены. Проверены
три одновременно действующих основания и7 вариантов security revoke для read/
saved command replay; старые загруженные actor/Business не восстанавливают доступ.
Реальный owner revoke с audit/idempotency работает при draft/active treatment,
не меняет медицинскую историю/назначение/участие. Это service/read boundary;
новые assistant/support/file/export/AI consumers сохраняют отдельную приёмку.
Production code/API/UI/schema без изменений относительно f745bab1; прежние
сборка/визуальные/PG результаты не запускались повторно. Static base8f93c194 PASS,
TEMP/dental-k05-combinations-static-20261123.log. Новые тесты до публикации.
SupportCase уже содержит business/assigned_to/status/resolved_at, повторно используем
его вместо нового реестра инцидентов. Ожидается решение: конкретные цели и сотрудник
поддержки, согласование head в своей филиальной области; owner без medical role
не разрешает раскрытие PHI. Сам общий support ACL не предоставляет clinical access.
Ответ по этому вопросу блокирует только реализацию support medical grant.

К05 текущий незавершённый срез: добавлены модель/isolated migration0029,
request/review/withdraw/complete/revoke/expiry services, versioned audit reference,
узкий correction basis существующего encounter draft writer. SQLite focused8PASS
1.495s (TEMP/dental-k05-correction-domain-r1-20261123.log), затем23PASS1.689s:
9correction +14existing encounter services (TEMP/dental-k05-correction-writer-r1-
20261123.log). Target-only reads10PASS1.418s (TEMP/dental-k05-correction-read-r1-
20261123.log); initial API3 + imported domain10PASS1.789s (TEMP/dental-k05-correction-
api-r1-20261123.log; imported test class затем заменён module import). Document
correction2 + existing storage15PASS0.869s, source snapshot immutable even after
later clinical/identity/business changes (TEMP/dental-k05-correction-document-r1-
20261123.log). API/UI добавлены. PG R1 выявил FOR UPDATE nullable join: исправлено
на of=(self) при сохраняющейся общей Business lock. R1 dependent29 PASS; R2
affected18PASS12.045s, включая3 настоящие конкурентные гонки;
TEMP/dental-k05-postgres[-r2]-20261123.log. PG0029→0028→0029 +check/drift PASS;
TEMP/dental-k05-roundtrip-20261123.log; PG остановлен, disposable cluster удалён.
Дополнительные API5/audit16PASS0.752s: TEMP/dental-k05-api-final-20261123.log.
Explicit cross-Business roles +target read/audit regression2PASS0.286s:
TEMP/dental-k05-tenant-20261123.log; действующие роли того же врача/head в другом
Business не разрешают request/review/read исходной цели.
Рабочая БД не мигрировалась.

Browser основной6PASS2.0m (request→head approve→own encounter/document draft→finish),
RU/KK/EN1440/390, keyboard/focus/axe0/overflow0. TEMP/dental-k05-browser-r3-20261123.log;
12 request/edit captures в output/playwright/correction-access-r3-20261123 просмотрены.
R1/R2 failures были test locator для custom Select; после чтения Select используется
getByLabel.click +option, product Select не менялся. Approved screenshots раннего R3
сняты до завершения reload, не доказательство полной строки; заменены history ниже.
History/recovery8PASS1.3m (503 retain/retry, withdraw,403 clear, actors/expiry),
TEMP/dental-k05-browser-review-20261123.log;4 recovery screenshots просмотрены.
После добавления дат reviewer/closer финальная history6PASS57.4s, TEMP/dental-k05-
browser-history-final-r2-20261123.log;6 history screenshots просмотрены, включая
полный mobile ряд без наложения fixed nav. Предыдущий history-final R1 ошибочно
ждал reviewer у withdrawn request; selector уточнён до completed, assertion сохранён.
Anti Slop scoped gate: geometry/meaning/keyboard/dialog/focus/recovery/locales PASS;
не full module. Build/types/i18n8012 +widget PASS, TEMP/dental-k05-build-final-20261123.log;
static basee5546ea8 PASS, TEMP/dental-k05-static-20261123.log. Fresh fixture/history
1PASS21.5s (TEMP/dental-k05-browser-fresh-20261123.log),23-й финальный screenshot
просмотрен: инициализация проверена отдельно без зависимости от прошлых browser tests;
переиспользована только пустая disposable schema (Business count0), не рабочая БД.
Срез опубликован f745bab19f363fd44bec312a9de7ab84d088fe11, normal FF origin/main и
remote SHA readback PASS; outgoing range состоял только из собственного commit31files.
CI45082898662 in_progress (не green); исходный индекс был пуст,
чужие STATUS/access hunks и password/Google/ycloud WIP не включены.
CI опубликованного8f93c194 run45078503071 completed/success,
frontend и backend jobs success; это не CI нового набора regression tests.
README/operations/integrations не требуют изменений: новых env/provider/notification/
BusinessEvent/AI эффектов нет. Access/frontend/capabilities/modularity и эта матрица
обновлены вместе; внешние L IDs и подписанные коррекции К08/К09 сохранены.

К04 projection опубликован8f93c194978ba6909b5f5336b343e4e04796fb53, normal FF и
remote SHA readback PASS; static на basee5546ea8 PASS, TEMP/dental-list-projection-
static-20261123.log. Общая локальная граница К04 принята по перечисленным ниже
сценариям, весь этап OPEN по mixed-history owner decision и L04. Pending вопрос
не повторять; signed records не переносить. К03 owner-clinician также OPEN.

К05 contract before code: M02/M06/M07, D03/B05–08/B28, E1/E2. Gap code/evidence;
reuse current medical roles/branch, Appointment basis, TreatmentParticipation,
encrypted immutable versions, MedicalAuditEvent/idempotency, existing medical
workspace/forms. Base8f93c194, canonical root/branch unchanged; foreign WIP untouched.
Closed invitation/transfer/head-end/role UI не переписывать. Ordinary end with
complete obligations остаётся К11. К05 должен дать: полную комбинацию оснований,
team assistant scope, согласуемый24h correction, security precedence и ≤4h readonly
support incident. Внешняя клиническая приёмка/протоколы не заменяются mock.

Первый пользовательский сценарий: врач после окончания участия запрашивает
исправление конкретного собственного приёма/документа; head в том же scope
согласует без самосогласования; врач открывает только разрешённую цель и правит
свой draft, повтор/отзыв/24h граница работают. Подписанное исправление отдельной
версией зависит от К08/К09 и сохраняется там, не разрешать draft writer менять
final/signed состояние. Запрос и metadata не открывают клиническую историю.
Точный state/target contract записать после чтения существующих callers и до
модели; не добавлять grant как blanket bypass общего clinical workspace.

Риск высокий: PHI scope/time/authorship, replay after revoke, concurrency, audit
rollback. Domain focused после каждого перехода, затем API strict/tenant/role/
expiry/denial и reachable UI с errors/retry/focus/desktop/mobile RU/KK/EN; PG race,
isolated migration roundtrip/check/drift и build на завершённом срезе. Skills:
zani-change-crm-domain/review-access/run-verification, прежние frontend/Anti Slop
during modules. UI requirements: reuse approved shell/shared controls44px,
memory-only PHI, clear target/expiry/state, no access on pending and no silent
retry against stale target. Один активный К05; остальные K/M/E/L IDs сохраняются.

24h technical contract (existing agreement implementation, not a new business option):
request targets one own primary encounter or one document of that encounter;
metadata picker is limited to own authored targets +current role/branch/CRM scope,
without clinical text. Request pending gives no content. Head review requires
current medical_records.manage +view and branch scope, requester != reviewer;
review checks target/patient versions and requester current role again. Approved
interval is [reviewed_at, reviewed_at+24h), never extended in-place. New request
and reason are required for another interval. Current account/member/medical/branch
revocation remains stronger. No cross-Business target or blanket history grant.

States: pending→active/rejected/withdrawn; active→completed/revoked/expired;
terminal states immutable. Expiry is effective by timestamp on every access,
independent of lazy state materialization. First authorized observation materializes
expired with audit (actor is observer, effective expiry remains expires_at).
One pending/live grant per requester/target; after expiry a new request is separate.
Business lock, expected revision, HMAC command payload, encrypted reasons/decision,
PROTECT relations. All transitions audited atomically. Audit failure never opens
access. Explicit finish closes the correction workspace early; future final-sign
consumer K09 must close it with the accepted correction transaction.

Dedicated correction workspace reads only selected target version(s); for document
target its captured source snapshot is reused, not the whole current patient chart.
Draft writers reuse existing validation/version storage, require own authorship
and current revisions; final/signed originals stay blocked pending К08/К09 linked
correction implementation. No raw grant accepted by general history/tooth/export
routes. Related extra data requires explicit narrow support in its owning stage,
not a boolean granting all patient context. Review/expiry/revoke/list/UI evidence
must precede any claim that this scenario is delivered.

## К04: локальные сценарии опубликованы, перепривязка и L04 открыты

К04 finished search/registration/IIN slices опубликованы e5546ea831560c7cdebb01040c4ef5b090f5fe1e:
normal FF origin/main и SHA readback PASS; static на base3de53af2 PASS
(TEMP/dental-k04-static-20261123.log). CI нового коммита ещё не проверен.
Рабочая БД не мигрировалась. Весь К04 не закрыт; один активный этап сохраняется.

Следующий минимальный gap S§3.1/M05: ClientsPage прежний список сохранён → нет
разрешённого медицинского статуса рядом с клиентом → bounded POST projection
только IDs текущей страницы/выбранный филиал, current reception+CRM readable scope,
medical audit/no-store, без расшифровки/диагнозов. Показать факт наличия DentalMedicalRecord
отдельно от identity verification; не называть PatientProfile медицинской картой.
Роли врача/команды используют clinical ACL в К05, не получают reception shortcut.
Reuse existing table custom-column rendering desktop/mobile; отдельный медицинский
адаптер, без медицинских полей общего Client serializer. Skills прежние; требования:
role-hidden column, scope/denial clears memory, shared44px controls и RU/KK/EN.
Риск PHI existence: domain/API denied/tenant/hidden/branch/audit failure/size bounds;
затем desktop/mobile статус→карточка, recovery/revocation, inspected screenshots,
affected build/types. Не повторять неизменённые PG races. Schema не меняется.

List projection implemented: domain/API5 PASS0.179s (TEMP/dental-list-projection-api-r2-20261123.log):
foreign/missing/duplicate IDs, core role deny intersection, owner medical deny,
revoked branch, strict bounds/body, audit failure rollback/no-store; no decryption.
UI uses existing custom-column contract as strings; initial typecheck caught JSX
vs string mismatch, fixed within medical adapter without changing shared tables.
Completion build62403 exit0 (TEMP/dental-k04-projection-build-20261123.log), i18n7981.
Browser R1:3 PASS,1 locator failure,2 not run; mobile existing renderer prefixes
the column label, screenshot confirmed correct status. Assertion changed to include
that label; R2 only failed/unrun3 PASS33.9s. Combined6 locale/viewport flows PASS,
record exists/absent distinct from identity, filter→existing CRM card, scoped axe0,
no horizontal page overflow; RU mobile503 clears→retry restores, real role revoke403
clears medical column, ordinary CRM remains.8 named captures inspected across
output/playwright/patient-list-r{1,2}-20261123 (includes repeated kk mobile state),
including denial; geometry, wrapping, labels, focus/native controls PASS.
Logs TEMP/dental-list-projection-browser-r{1,2}-20261123.log; schema dry-run no changes
(TEMP/dental-list-projection-schema-20261123.log). New migration not required.
Provider/notification/BusinessEvent/AI effects none. Read projection does not certify
clinical doctor/team ACL or p95 under load; these retain К05/К17 acceptance.

К04 локальные готовые сценарии: поиск/переиспользование/atomic registration,
identity/representative lifecycle and negatives, audited IIN review, reception list
status. Whole-stage OPEN: controlled relink/mixed histories needs owner decision
already requested; no signed-document reassignment implemented by assumption.
External L04 needs approved identity/representative protocols and training facts;
synthetic fixtures do not establish them. Clinical tabs/doctor projection remain
mapped to К05/К06, document-recipient enforcement to К12. After this slice publication
continue independent К05; do not mark К04 closed or create a parallel backlog.
CI e5546ea8 run45077416096 in_progress on latest check, not green.

Дополнительный keyboard gate обнаружил потерю фокуса у refresh при native disabled
во время загрузки. Минимальная UI правка: aria-disabled + guarded handler, кнопка
остаётся focusable, повторный запрос во время загрузки игнорируется. Приёмка этого
критерия до rerun НЕ PASS. Повтор RU desktop keyboard и RU mobile recovery/revoke,
новая completion build обязательны; unchanged locale/layout/domain evidence reuse.
Focus R2:2 PASS50.0s, keyboard open/refresh retains focus, RU mobile recovery and
real revoke повторены;3 captures inspected. TEMP/dental-list-projection-focus-r2-
20261123.log, output/playwright/patient-list-focus-r2-20261123. Completion build R2
session15080 exit0, TEMP/dental-k04-projection-build-r2-20261123.log; source after
focus fix included. Scoped UI Delivery Gate now PASS, no unresolved local UI defect.

К03 rollout опубликован3de53af201511c75660b1304ec2a6a97e6aa324a в origin/main,
обычный fast-forward и remote SHA проверены. Static на фактическом base096cd591
PASS: TEMP/dental-medical-rollout-static-20261123.log. CI45070985178 in_progress,
не green. Позднейший результат CI: frontend success, backend failure1/4619,
101 skipped. Единственная ошибка tests_template_search foreign fixture:
submitted_at auto_now_add вычисляется после заранее заданного decided_at,
нарушая medical_template_review_state на более точных часах Linux.
К02 scoped PASS → CI доказывает nondeterministic fixture → минимальная правка
только подготовки foreign approved review: сначала pending insert, затем decision.
Constraint и visibility assertions сохранены; focused template search8 PASS1.389s
(TEMP/dental-template-ci-fix-20261123.log). Локальный original reproducer PASS
из-за гранулярности Windows clock; CI traceback и auto_now_add доказывают причину.
Новая CI проверяется отдельно после публикации, прежний failure не переименован. Прежняя UI/production реализация К02 не меняется.
Весь К03 остаётся открытым по owner-clinician решению; вопрос уже задан.
К04 продолжается независимо на существующих медицинских ролях. Owned processes
К03 не осталось; К04 держит disposable runtime62302. Все прежние внешние условия L01–L19 и требования сохраняются.

### Контракт К04 — перед реализацией

Mode implementation; gaps code/evidence, внешние протоколы личности L04 отдельно.
Observable result: ресепшн в выбранном Business/филиале находит существующего
пациента, отличает подтверждённое совпадение от кандидатов, оформляет личность/
представителя и контролируемое исправление без объединения чужих историй.
Reuse Client/нормализация/CRM readable scope, PatientProfile/identity crypto/HMAC,
patient/representative services/API, ClientWorkspace/Panel/Form, shared UI и i18n.
Scope M03/M04/M05, D04/D07/B01–04/B26, E1. Base3de53af2; canonical root и branch
прежние, foreign auth/integrations WIP не трогать.

Готово: create/verify/preliminary/обычные административные correction, encrypted
revisions, representative verify/revoke, merge/hard-delete guards, patient happy/
recovery и representative happy UI. Не переписывать эти сценарии. Остаток:
полный разрешённый поиск/medical list projections/вкладки; ИИН и перепривязка с
медсогласованием; controlled medical correction без обычного merge; представитель
negatives, будущий recipient enforcement contract; PG уникальность/гонки.

Первый coherent slice: поиск в существующем patient API через POST, чтобы ИИН
не попал в URL/общие логи. Только текущие medical reception +CRM Client/branch
права; точное verified ИИН отдельно от возможных ФИО/телефон/email/дата рождения.
Reuse нормализацию и scope, не общий plaintext search index; ограниченный ответ,
пагинация, rate-limit без raw query, medical read audit/no-store, одинаковая
пустая выдача для отсутствующего и скрытого пациента. Перед добавлением storage
проверить существующие поля/index/helpers. Никаких provider calls/notifications,
AI или изменения денег/записей/рабочей БД в этом slice.

Риск высокий: PHI, tenant/branch/hidden existence, подмена личности, concurrent
verify/correction, audit failure. После каждого domain/API slice focused tests
(valid/invalid/denied/foreign/archive/revoked/pagination/audit rollback/rate-limit);
далее reachable UI/desktop-mobile RU/KK/EN, ошибки/повтор/сохранение контекста,
снимки и visual, affected build/type и system/drift. PG для согласованной identity
уникальности. Приёмка всего К04 требует целого сценария и перечисленного остатка;
отсутствие внешнего протокола не выдавать за клиническую готовность. Неясное
правило исправления сначала сверить с D04/B04, не придумывать право на merge.

Первый К04 domain delta: новый patient_search.resolve_patients переиспользует
reception_context/readable_queryset/normalizers/tenant HMAC и MedicalAuditEvent.
ИИН в SQL только digest; обычные контакты/непроверенные совпадения possible,
verified ИИН exact_confirmed. Архив только явно. Ответ без ИИН/адреса/clinical text,
с date_of_birth и административным identity_status. Shared demographics decoder
выделен из прежнего read без смены его semantics. DOB остаётся encrypted и пока
ищется batch50 scan с пагинацией совпадений, без скрытого лимита полноты;
его p95/нагрузка требуют отдельного К17 доказательства. Новых schema/index нет.
Business lock +повтор current access; scope-read audit и patient-read до выдачи,
audit failure откатывает результат. HTTP/rate-limit/denial audit/UI ещё НЕ готовы.
Первый gate:8 новых domain cases +существующий patient API для shared decoder;
при провале сначала минимальный reproducer, не переписывать прежние services.

Domain gate:26 PASS1.893s (8 новых +18 existing patient API) в owned isolated
SQLite. Первая попытка runner не стартовала тесты из-за отсутствующего settings
TEST dict; setdefault исправил только runner, лог R1 сохранён. PASS в
TEMP/dental-patient-search-domain-r2-20261123.log. Runtime62302 сохраняет только
одноразовую focused-test.sqlite3 (--keepdb) для focused повторов без миграций
рабочей БД; Python REPL держит context до явной очистки. Прежние application
servers не запущены. Schema не менялась.

После domain PASS добавлен POST /api/medical/patients/resolve/, strict body,
no query-string, current scope и no-store на ошибках. Новый actor-wide throttle
medical_patient_lookup default60/min (MEDICAL_PATIENT_LOOKUP_RATE); смена Business
не сбрасывает лимит. Отказ права/модуля пишет access_denied без patient/query только
для собственного/действующего membership бизнеса; чужие tenant не получают такие
записи. Сбой audit блокирует и успешный ответ, и обработку такого отказа (503).
6 API checks +8 domain rerun идут в TEMP/dental-patient-search-api-20261123.log.
UI/права конечного сценария/весь К04 ещё не приняты; не публиковать как готовый поиск.

API/domain14 PASS0.501s. Для достижимого входа добавлен GET search-access: только
medical reception+CRM clients.view, список пересечения действующих medical/CRM
филиалов, без PHI. Это устраняет N запросов для подбора доступного филиала и
не показывает поиск owner без роли. Отдельный API check подтверждает пересечение,
неактивный филиал, пустой grant, owner denial/strict fields; rerun7 API checks.

Перед UI применяются antislop during (прежнее решение), UI/human/layoutmobile/copy,
zani-review-frontend и design-taste-frontend app guidance; app-screens прочитан
целиком, main skill routing к app (page run N/A). Дизайн уже утверждён DESIGN_SPEC
§3/§5.1/S14 и существующими Clients/Modal: случайный draw, смена shell/type/palette,
графики/новые assets/иллюстрации не требуются и противоречат сохранению дизайна.
Задача окна: найти правильного человека и открыть существующую карточку. Данные:
реальные разрешённые Client/Patient, ФИО/контакты/DOB, факт проверки/архива,
confirmed vs possible, scope Business/филиал. Простая форма +список результатов,
одна основная кнопка поиска; i18n RU/KK/EN, shared controls44px/focus, mobile reflow,
полные длинные имена и ясное открытие. Только memory draft/результаты, не URL/cache;
abort/очистка при смене пользователя/бизнеса/филиала/отзыве, retry без потери ввода.

К04 UI WIP: PatientSearchEntry в существующем ClientsPage только при medical
capability, search-access проверяет reception и доступные филиалы. POST через
medicalPatients adapter, memory-only query/results, explicit archive, possible/
confirmed labels, существующая карточка /app/clients/:id. RU/KK/EN, shared Modal/
Input/Select/Button; смена формы abort/очищает выдачу,403 очищает PHI,503 retry
сохраняет ввод. API access7 PASS0.335s; TypeScript `npx tsc -b --pretty false`
PASS (62799). Browser6 scenarios запущены в том же disposable runtime62302,
отдельная gate.sqlite3 от focused-test.sqlite3; TEMP/dental-patient-search-browser-r1-20261123.log,
output/playwright/patient-search-r1-20261123. Пока не заявлять browser/visual PASS.
CI К03: frontend success, backend tests in_progress;45070985178 ещё не green.

Поиск browser R1:6 PASS2.3m RU/KK/EN×1440/390, real POST/no-store/без query URL,
possible/empty/open existing card,503 retained/retry, Escape/focus return,
axe WCAG2A/AA scoped0. Boundaries:2 PASS34.1s в том же disposable runtime,
27 active/28 including archive/25 page, семейный телефон→2 отдельные possible,
реальный revoke→403 и очистка PHI, fixture role restored.10 снимков captured AND
visually inspected:6 results+recovery+2 family+denied; geometry/reflow/labels PASS.
Логи TEMP/dental-patient-search-{browser-r1,boundaries}-20261123.log; screenshots
output/playwright/patient-search-{r1,boundaries}-20261123. Это8 distinct cases,
не полная приёмка К04. I18n первый FAIL:2 новых medical labels не были в точном
allowlist. Добавлены только medical.search.title/empty (capability+role-gated);
общая нейтральность не ослаблена. Rerun parity7961 PASS +5 terminology tests PASS.
Final build/system/drift/dependent suites/docs/publication ещё впереди.

Следующий coherent slice того же К04: verified ИИН correction по B04, reuse
identity verification/encryption/revision/idempotency и current head permissions.
До изменений определить зависимые medical history/uniqueness/replay/audit права;
никаких переносов signed documents/обычного merge. Владелец отдельно спрошен о
разборе смешанных историй: заявка ресепшн с конкретными связями, подтверждение
медруководителя, оригиналы signed остаются, исправление с историей. Ответ ещё
не получен; зависимый сценарий не реализовать по умолчанию. Остальные К04 части
продолжать. Прежний owner-clinician К03 вопрос также остаётся без ответа.

ИИН correction domain WIP: PatientIdentityCorrection(pending/applied/rejected),
encrypted proposal/recheck/reason/decision, exact patient/client revisions. Без
clinical history применяется атомарно обученным reception; при dental record/
encounter/tooth history ждёт head. Решение head перепроверяет текущие права обоих
участников и актуальный protocol, stale требует новой заявки. History/clinical
links не переносятся. Idempotency payload только HMAC, audit failure rollback.
Миграция0028 с моделью/audit FK/actions/state constraints сгенерирована в owned
runtime; рабочая БД не затрагивалась. Первый domain gate8 PASS0.660s, лог
TEMP/dental-iin-domain-r1-20261123.log. После PASS review выявил SQL NULL в applied
constraint: добавлено explicit isnull=False; permission prerequisite перенесён
до lookup correction. Unpublished0028 уточнена, reverse0028→0027 выполняется
ТОЛЬКО на disposable focused-test.sqlite3 (migration_env в62302), затем повторное
применение/affected tests. TEMP/dental-iin-roundtrip-20261123.log. Текущие модель/
services/audit после этих правок ещё требуют rerun, API/read/UI НЕ реализованы.
До зависимого frontend выполнить focused domain расширение foreign/revoked head/
changed policy/collision/replay/audit, shared audit regression. Обязательны итоговые
PG race/system/drift и reachable UI, build/docs/publication всего К04.

ИИН domain R2:39 PASS2.066s (12 новых+administrative correction+shared audit
participation/encounter/tooth), после исправления NULL constraint и isolated
0028→0027→0028. API R1:17 PASS2.357s; после добавления head view prerequisite/
foreign tenant case R2:18 PASS1.407s. Логи TEMP/dental-iin-{domain-r2,api-r1,api-r2}-20261123.log.
GET identity-corrections scope/client/pagination, POST :patient/iin-correction,
POST identity-corrections/:id/decision: strict/no-store/idempotency/audit,
reception request и head-only approve/reject, denied audit fail→503. PHI только
в encrypted storage и авторизованном read; общая idempotency response без PHI.

UI добавлен в существующий PatientAdministrationPanel: correctIin mode повторно
использует verification form; pending/dirty guard, pending/applied/rejected list,
head decision через прежний MedicalRoleCommand с reason/retry409/503. При known
denial очищается весь медицинский panel. Parent/form исходные flows сохраняются,
их affected representative negative browser ещё будет проверен. Types8862 PASS,
i18n7972 PASS (первый ошибочный запуск из root дал ENOENT, повтор из frontend PASS).

Browser IIN R1 FAIL1/5 not run: сохранение201, затем список503 medical_audit_unavailable
(код подтверждён network trace), concurrent audited GET в SQLite. Product audit
не ослаблялся. Fixture correction flag теперь использует serial middleware как
прежний template fixture, сохраняя browser sockets. R2:6 PASS1.5m real request/
head decision/reception reread RU/KK/EN×1440/390, dirty Escape/focus,request503
retained/retry,axe0;12 screenshots captured AND inspected, geometry/reflow PASS.
TEMP/dental-iin-browser-r{1,2}-20261123.log; output/playwright/identity-correction-r{1,2}-20261123.
Recovery stale/reject503/same key/denial UI запущен отдельно62302:
TEMP/dental-iin-browser-recovery-20261123.log, результаты пока ожидаются.

К04 PostgreSQL gate52312 PASS: check, migration drift none,82 targeted tests19.637s,
включая4 настоящие races: verified IIN unique, same approval replay once, two
different approvals stale conflict, parallel patient/correction read audits.
Новый PG17 initdb в disposable isolated_runtime, localhost random port,
codex_dental/dental_gate; test_dental_gate удалена, PG остановлен и runtime очищен.
Команда manage.py test tests_identity_concurrency/identity_iin_corrections/
identity_correction_api/identity_corrections/patient_search/patient_search_api/
patient_api/participation_audit/encounter_audit/tooth_audit --noinput -v2.
Лог TEMP/dental-k04-postgres-20261123.log. Миграция0028 применена лишь к disposable
SQLite и PG; не к рабочей БД. Это не весь К04, не production/concurrency-load PASS.

Recovery IIN1 PASS20.3s: actual409 stale revision retains reason, explicit reload,
reject503→retry same key→rejected, frontend injected403 clears panel (backend real
role denial separately tested).3 captures visually inspected, PASS.
Representative boundary первый FAIL: старый тест выбирал имя из первых20 options,
но текущий fixture уже содержит49 клиентов; target отсутствовал на первой странице.
ClientPicker remote search реализован ранее, product не переписан. Тест уточнён:
вводит нужное имя в поиск. Повтор в новом disposable browser runtime с теми же
large search/correction fixture flags (чтобы исходная patient creation была новой,
а не replay), log TEMP/dental-representative-boundary-k04-r2-20261123.log,62302;
context очищен после subprocess. Повтор PASS1.8m,3 captures visually inspected:
protocol unavailable, retained invalid-period draft, real role denied/PHI cleared.
Исходный focused-test runtime остаётся.

Следующий установленный gap К04, источник S§3.2.6: прежнее create PatientProfile
для уже существующего Client PASS → нет атомарного создания нового Client+Patient
при отсутствии совпадений → добавить отдельную составную service/API команду,
reuse Client serializer/normalization/current CRM permissions/audit/activity и
patient create/idempotency, без нового реестра людей. Exact verified ИИН блокирует
дубль без раскрытия; разрешённые контактные/ФИО candidates требуют явного выбора
отдельного человека. Не показывать hidden candidates. Все записи/аудит атомарны,
повтор не создаёт второго Client. UI в существующем patient search. Риски: tenant/
duplicate/rollback/replay/role; focused domain/API до UI, затем reachable flow и
affected completion. Schema0028 не меняется ради этой команды. S01 clinical tabs
зависят от К05/К06: сохраняются в матрице, не имитировать готовые клинические вкладки.

Атомарная регистрация реализована в patient_registration service, strict POST
register/ и PatientRegistrationForm внутри поиска. Использует ClientSerializer/
readable scope/normalizers, core audit/activity, PatientProfile/idempotency; PHI
в payload hash только HMAC, idempotency response пустой. Verified ИИН блокирует
дубль, visible name/contact/unverified IIN candidates требуют отдельного подтверждения.
Current role/branch/CRMcreate+view и replay access проверяются сервером; весь
Client+profile+audit/activity откатывается при medical audit failure.

Registration domain R1:6 PASS/1 test-helper error (request_hash ошибочно назван
payload_hash); исправлен только assertion поля, affected case R2 PASS0.146s.
API4 +existing search API7 PASS0.530s. TEMP/dental-registration-domain-r{1,2}-
20261123.log и dental-registration-api-20261123.log. Дополнительная PostgreSQL
проверка регистрации/одновременного same-key:12 PASS3.595s, отдельный PG17 initdb,
TEMP/dental-registration-postgres-20261123.log. PG остановлен/runtime очищен;
предыдущие неизменённые82 PG результата не перезапускались.

Registration browser R1:6 PASS1.0m, RU/KK/EN×1440/390. Поиск→создание→реальная
карточка с unverified profile, уникальный Client; RU desktop dirty Escape,
503 retry same key→real409 candidate→explicit confirmation→201. PHI отсутствует
в URL/storage, scoped axe0, overflow0.6 screenshots captured AND visually inspected:
labels/spacing/44px/focus/desktop two columns/mobile one column, actions reachable.
TEMP/dental-registration-browser-r1-20261123.log; output/playwright/patient-registration-r1-20261123.
Completion `npm run build` session52347 exit0; TEMP/dental-k04-build-20261123.log.
Vite existing chunk-size warning, не ошибка. Этот build включает все текущие К04
product UI изменения; последующие правки только tests/docs не требуют новой сборки.
Rerun trigger: affected source/dependency/config changes or reproduced UI failure.

Anti Slop scoped Delivery Gate: geometry/real purpose/state recovery/keyboard/focus/
labels/translations PASS на указанных browser и inspected captures. Existing design
tokens/components preserved; no invented marketing/assets/metrics. Decorative motion,
media, themes/new navigation N/A: не добавлялись. Полная приёмка К04 остаётся открытой
по controlled relink/mixed histories и medical projections; clinical tabs К05/К06,
recipient consumer К12, реальный identity protocol L04 сохраняют свои требования.

## К03: подключение профиля принято и опубликовано; owner-clinician открыт

К02 завершён в принятой локальной границе и опубликован096cd591bbdb04d27741cfe31cf13fee00dfd9ca
в origin/main обычным fast-forward; remote SHA совпал. Committed-range static
на base272f5f23 PASS (TEMP/dental-template-availability-static-committed-20261123.log).
CI45068261530 in_progress, не green. Внешняя/PG/нагрузочная приёмка остаётся К17/К18.

К03 начинает с существующих profiles.py/capabilities/initializer/medical role guards
и сохранённых evidence M01/M02. Новый полный аудит не проводится. D02 означает
автоматическое additive подключение после готовности модуля; не интерфейс выбора
модулей/смены сферы. Перед кодом уточнить фактический остаток и записать ниже контракт
backfill/новых create paths/owner-clinician, проверки и критерии; прежние flow сохранить.
Текущий source base096cd591, branch прежний, foreign auth/integrations WIP сохраняется.
Живых owned серверов/тестовых runtime после К02 нет. Рабочая БД не менялась.

### Контракт К03, 23.11.2026 — до реализации

Mode implementation, gaps code/evidence и один owner decision. Переиспользуем
PROFILE_SPECS dentistry2, BusinessCapability, create_profiled_business и все5
готовых callers, medical роль/branch/доступ и S18. Изменяем только профильный
переход/его запуск и зависимый достигнутый UI; чужой serializers/auth WIP не трогаем.

Наблюдаемый результат: после явной технической готовности релиза новые стоматологии
получают v2 при создании; существующие переходят одной служебной процедурой для
всех dentistry без ручного списка и без потери Client/Appointment/Service/Payment,
ID, CRM capabilities/settings или создания patient/record/role grants. До готовности
новые остаются v1. Готовность задаётся общей конфигурацией выпуска (default false),
а не merchant toggle; она не означает внешнюю приёмку или аварийный отзыв доступа.

Additive backfill: только legacy/dentistry1 → dentistry2; готовый v2 не чинится и не
перезаписывается повтором. Существующие обычные capability rows/явные false сохранять,
отсутствующие базовые defaults добавить; медицинскую capability назначить в рамках
согласованного D02. Другую/неизвестную конфигурацию не переклассифицировать. По одному
Business под блокировкой, атомарные profile/capabilities/audit, повтор без новых audit.
CLI по умолчанию dry-run; --apply требует release-ready конфигурации. Прерванный
запуск возобновляется безопасно. Никакого выполнения --apply на working DB сейчас.
Закупочных настроек в текущей модели ещё нет: новые настройки/сохранение false
реализуются в К14; профильный переход не сбрасывает никаких имеющихся настроек.

Риски: tenant/profile authorization, stale cache, гонки создания/перехода и частичный
сбой. Focused tests: legacy/v1/v2/другая сфера, no-data/ID/настройки preservation,
dry-run/flag false, retry/no-op, invalid config, audit rollback; затем create-path
dependent suites и check/drift, PostgreSQL конкурентность при доступной isolated среде.
UI: существующий entry после назначенной роли, owner без медицинского доступа,
другая сфера; browser desktop/mobile и affected build при UI изменениях. Полный
аудит не повторять; прежние неизменённые доказательства использовать по входам.

Owner-clinician decision ранее оставался pending: async вопрос повторно показан
23.11 о подтверждении роли врача другим head/deputy в своей области. До ответа
запрет owner→self остаётся, независимый профильный переход продолжается. Будущие
jobs/files/AI endpoints наследуют тот же gate в К07/К15; их ещё нет, это не PASS
несуществующих интеграций. К03 не закрывать при непроверенном обязательном остатке.

Первый К03 domain/initializer gate1672:23 tests,22 PASS/1 fixture error
(Django TestCase.client затенял нашу Client fixture). Переименована только fixture
в patient_client; production/assertions не ослаблены. TEMP/dental-medical-rollout-
domain-20261123.log. Добавлен отдельный PG concurrency test двух одновременных
rollout: один activated, один unchanged, одна audit row и один набор capabilities.
Session11490 завершился exit0: isolated PostgreSQL17 check/drift и tests_medical_rollout/
profile_initialization/profiles/medical_capabilities. TEMP/dental-medical-rollout-
postgres-20261123.log. Новый initdb внутри isolated_runtime, случайный localhost port,
синтетический codex_dental/dental_gate, stop в finally. Обычный local-postgres и
working DB не используются. Внешнее перенаправление вывода не сохранило stdout
вложенных native subprocess: exit0 подтверждён, счётчики/skip не заявляются.
После добавления двух dependent API/signup проверок выполняется focused PG R2
только tests_medical_rollout с явными stdout/stderr handles в logfile; туда входит
реальная конкурентность. Новые клиники должны получить v2 без patient/record/role
и без owner medical access. Широкие наборы повторно не запускаются.

PG R2: 12 tests/10 PASS/2 test-helper errors (ошибочный lookup business вместо
member__business у MedicalRoleAssignment). Все9 domain checks и конкурентность
двух PostgreSQL17 transactions PASS; audit/профиль создаются один раз. Исправлен
только lookup двух API tests; повторяются эти2 API checks +check/drift в isolated
SQLite с явным logfile TEMP/dental-medical-rollout-api-r3-20261123.log. R2 полный
лог TEMP/dental-medical-rollout-postgres-r2-20261123.log; PG остановлен/удалён.
CI К0245068261530: Frontend build success, Backend checks and tests ещё in_progress.

API R3: 2 PASS0.659s, check PASS, migration drift отсутствует, session88102 exit0.
Production после PG10 PASS не менялся; исправлена только test query. Браузерная
проверка К03 использует существующий UI без его переработки: opt-in fixture
E2E_MEDICAL_ROLLOUT переводит synthetic v1→v2 реальным service, затем проверяются
врач/owner без роли/другая сфера на1440/390. Existing templates/roles fixtures
переиспользуются; обычные suites без нового env сохраняют прежнюю подготовку.
Owned runtime93527 держит отдельную SQLite только для этих проверок/повторов.
Browser R1:4 passed/2 failed, но это не rollout evidence: configure_browser_runtime
удалил непропущенный E2E flag, поэтому новый переход и other-industry fixture не
запустились. Минимальная диагностика подтвердила отсутствие synthetic пользователя.
Флаг захватывается до guard, release setting задаётся только после его успешной
проверки; fixture утверждает profile2 и ровно1 rollout audit. R2 повторяет все6
сценариев с фактическим переходом на том же disposable runtime, новый logfile
TEMP/dental-medical-rollout-browser-r2-20261123.log и output/playwright/medical-rollout-r2-20261123.

**К03 rollout принят локально, весь этап не закрыт.** R2:6 PASS39.3s (врач/owner/
другая сфера ×1440/390). Visually inspected все6; один other-industry mobile снимок
поймал загрузку. R3 ждёт завершения loading и проверяет отсутствие medical option
в мобильном Select:4 denied cases PASS28.8s, все4 снимка просмотрены. Итог6 distinct
сценариев +4 адресных повтора; наличие/отсутствие entry, dialog open/Escape/focus,
real API200/403, overflow PASS. RU достаточно: UI/copy/layout в К03 не изменены;
К02 RU/KK/EN, recovery/keyboard/axe и final build переиспользуются с неизменными
frontend source/dependencies/config сборки. Новый full build/full suite не нужен
для backend профиля и opt-in browser fixtures. Test TS исполнен Playwright.
Runtime93527 exit0, процессы/одноразовая БД убраны; working DB не затронута.

Публикуемый остаток: review/static/commit/normal push. После него остаётся owner
decision (кто подтверждает медицинскую роль владельца-врача), без самовыдачи;
его отсутствие не блокирует независимый К04 с уже назначенными ролями. Полный
К03/M01/M02 не отмечать закрытым. К07/К15 проверяют новые files/jobs/AI consumers,
К14 реализует новые закупочные настройки, К17/К18 — общую интеграцию/нагрузку;
эти требования не удаляются. App README/product/spec не требуют изменения:
бизнес-правила прежние; config/runbook обновлены в .env.example и модульном плане,
права в access, паспорт в capabilities, browser flags в testing.md.

## К02: поиск и применимость шаблонов — локально принят и опубликован

Код и пользовательские сценарии приняты локально; CI fixture regression20 PASS,
документация/static PASS. Опубликован096cd591, base этапа272f5f23; branch codex/ui-testing-toolkit,
canonical root C:/Users/user/Desktop/PlatformaCRM. В commit только30 task-owned paths.
Один активный этап; M01–M30/E0–E7, К03–К18 и внешние L01–L19 ниже сохранены.

**Поведение и граница.** Personal/common/approved поиск по названию, сохранённому
названию процедуры, категории/специальности (NFKC/casefold), language/category/
specialty/service_id filters, approved scope personal/common. Поиск только по
авторизованным версиям; clinical body не ищется. Decrypt+audit кандидатов, без plaintext
индекса; SQL batches50, пагинация по совпадениям без скрытого лимита полноты.
Большой каталог/p95 и PostgreSQL race evidence остаются К17/К18, локальный SQLite
их не подтверждает. Прежние запросы без фильтров сохраняют быстрый путь.

Owner23.11 подтвердил pause/resume всего шаблона медруководителем с причиной и
историей; правило внесено в Desktop ТЗ v1.2 §6.1. Head business-scope view+approve,
Business/template locks, availability_revision, encrypted reason/history, audit и
идемпотентность; текущие права проверяются до replay. Врач/owner без медроли не могут
управлять применением. Утверждённые версии/созданные документы неизменны; resume не
утверждает новый draft. Неактивные не выдаются approved selector; прежняя доступная
own/common approved версия даёт409 при новом применении, чужая/неутверждённая403.
UI: поиск/сброс, head-вкладка применения, фильтр активности, причина/история,
конфликт/повтор/отзыв; новый документ возвращается к выбору после paused-preview409.

**Переиспользование/риски.** MedicalRoleCommand/Modal/Input/Select/Button, shared
error normalization, API adapters, существующие template snapshots/ACL/audit/crypto.
Anti Slop during +UI/human/layoutmobile/copywriting, project frontend/domain/
verification skills: прежние токены и типографика; удержание ввода/focus; safe retry;
RU/KK/EN responsive, длинные значения. Новых dependencies/assets/design system нет.
Миграция0027 добавляет активность и encrypted history; isolated roundtrip проверен,
working DB не менялась. Откат после новых audit/history rows требует отдельного
плана сохранения данных; проверенный roundtrip относится к состоянию до таких rows.
Notification/BusinessEvent/AI/provider paths не менялись.

**Доказательства (TEMP/ = C:/Users/user/AppData/Local/Temp/).**

| Проверка | Результат / граница / повтор |
| --- | --- |
| Search domain/API |19 PASS3.240s (99229);26 PASS2.981s (95496), NFKC/cross-batch/foreign approved. TEMP/dental-template-search-domain-r2-20261123.log и search-api-20261123.log |
| Availability domain/dependent/API |15 PASS2.783s (89922);19 PASS16.864s (93620, включая migration roundtrip/source);6 PASS1.547s (79046). TEMP/dental-template-availability-domain/dependent/api-20261123.log; наборы пересекаются |
| Completion affected suites |80 PASS11.300s/check/drift PASS (75900): template_services/common_templates/template_reviews/template_api/common_template_api/template_review_api/document_previews/document_preview_api. TEMP/dental-template-availability-completion-20261123.log |
| Последний backend delta409 |33 PASS6.659s: availability/availability_api/document_template_source/common_templates. TEMP/dental-template-availability-conflict-20261123.log. Backend после этого не менялся, кроме отдельной CI fixture ниже |
| Availability browser |R6 все6 RU/KK/EN ×1440/390 PASS; R7 RU1440 +три mobile PASS после responsive fix. R7 также personal/common поиск и переключение scope. TEMP/dental-template-availability-browser-r6/r7-{locale}{width}-20261123.log |
| Document browser |R3 все6 RU/KK/EN ×1440/390 PASS: поиск/empty, реальная пауза409/reselection, preview503/retry, create/history, retained clinical input, stale/denied, axe/focus. TEMP/dental-document-search-browser-r3-{locale}{width}-20261123.log |
| Final build |npm run build exit0:7949 keys/types/app/widget. TEMP/dental-template-availability-build-final-20261123.log. Bundle PASS: app-shell361.3KiB<400; прежние locale chunks>500KiB warnings. terminology5 PASS |
| Visual |18 affected document-search-empty/template-picker/paused-template снимков во всех6 вариантах просмотрены. Availability R5 пять состояний +R6 RU/KK/EN mobile/desktop/history-page/denied +R7 personal/common и все3 mobile result просмотрены. Длинный EN390 title исправлен/перепроверен; прочие geometry/labels/error/history OK. Неизменённые editor/history используют прежнюю visual evidence |

Screenshots: output/playwright/medical-template-availability-r5/r6/r7-20261123 и
output/playwright/medical-document-search-r3-20261123. Это synthetic isolated local
runtime, не native devices/live provider. Все12 distinct browser cases PASS;
повторы R7 не называются новыми уникальными cases. Keyboard/dirty/pending/Escape/
focus return, search no-match/reset/retention, history paging/503, POST503/same-key,
actual stale409 и403 clear+explicitReload проверены. Media/animation/marketing N/A:
их нет в изменённой области. Shared shell не перерабатывался.

**Попытки и найденные дефекты.** Первые19 domain:2 fixture permission errors;
исправлена fixture, права приложения не ослаблены, repeat19 PASS. Browser60553
превысил180s до тестов; диагностика72041 доказала fresh migrate211.64s. Подготовка
schema вынесена перед Playwright в том же disposable runtime, UI timeout не ослаблен.
Диагностика3499 faulthandler не установила причину и не повторяется. R2:1 docs PASS,
RU390 timeout до нового поиска,10 notrun; free RAM123MiB, это не доказанная причина.
R3 availability: anchored grep не выбирал тест; исправлен grep и --list=1. R4:
exact Select locator ошибочно не учитывал value в aria-name; исправлен locator.
R5: одноразовый mock503 поглощался отменённым mount read; держать outage до retry,
assertions сохранены. R6/R7 заменяют эти незавершённые browser результаты.
Наблюдавшиеся UI defects: transient empty→loading (sync loading), same-value Select
(guard), denied search clearing без refetch loop (applied ref), EN390 узкая колонка
названия (mobile full-width title). Каждый delta проверен последующими browser/build.

**CI предыдущей публикации.** Run45058686703 для272f5f23: frontend success,
backend job137319523815 FAILED (4583 tests,1 error,100 skips), не green.
OwnParticipationEndTests.test_foreign_participation_cannot_be_closed_under_current_patient
нарушал medical_participation_accept при создании fixture: accepted_at вычислялся
раньше default proposed_at. Предыдущий scoped PASS → CI failure → минимальная правка
одного общего timestamp proposed_at/accepted_at; production constraint/denial assertion
сохранены. Focused own_end +closure:20 PASS2.396s, exit0; TEMP/dental-own-end-fixture-
ci-regression-r2-20261123.log. Первая попытка завершилась native exit3221225477 без
лога; причина не установлена. Startup diagnostic подтвердил импорт Python/Django,
но не setup (без DJANGO_SETTINGS_MODULE). Повтор через manage.py с -u -X faulthandler
успешен, assertions/production не менялись. Полный CI повторно будет проверен после push.

**Runtime/публикация.** Python REPL69863 завершён через exit(); disposable runtime
очищается штатным context cleanup, browser processes завершены. Финальный static35551
exit0, base656dbd19318b6e146dbc0026afd1727fa719c14e (исходный base полной задачи),
TEMP/dental-template-availability-static-final-20261123.log. После правки только
Markdown diff hygiene повторён; новые executable inputs после gate не менялись.
Контракт access, frontend, capabilities и матрица согласованы; README не требует
правки (команды setup и публичный статус не изменены). Task-only commit/normal push
и remote SHA подтверждены выше; следующим выполняется К03. Рабочая БД/реальные
данные/провайдеры не затронуты. Внешние проверки не выдаются за выполненные.

К01 завершён и опубликован fff0555c1b6842eac933970ad865ed0f5d659518 в origin/main;
normal fast-forward push и remote SHA подтверждены. CI45058377584 in_progress,
не PASS. Собственный commit36 файлов, foreign WIP сохранён. В принятом scope
К01 остатка нет; working DB и внешняя проверка реквизитов не выполнялись.

К02 contract (23.11): implementation, gap code; M11 §6.1/16.2, M16, D06/D09,
E3/E4. Переиспользовать encrypted metadata, personal/common drafts/reviews,
approved selector, version readers/audit/idempotency, существующие Settings и
редактор документа. Не переписывать принятую классификацию/утверждение/preview.
Наблюдаемый результат: врач находит доступный утверждённый шаблон по
процедуре/категории/специальности и использует его в документе; медруководитель
управляет активностью клинического применения с причиной/историей. Неактивный
шаблон не выбирается для нового документа, сохранённый документ не меняется.
Поиск сохраняет tenant/own/common/approved границы; классификация шифруется,
строки поиска не попадают в общий audit/BusinessEvent/AI. Списки пагинируются;
проверку p95 на целевом объёме сохраняем в К17. Смена активности отделена от
редактирования утверждённой версии и не удаляет её историю.
Проверки до зависимого UI: поиск/фильтры/пагинация/Unicode/пусто, current ACL,
чужое/неутверждённое/неактивное, устаревшая команда/replay/audit rollback,
старый document snapshot и невозможность нового применения. Затем API,
reachable RU/KK/EN desktop/mobile сценарий поиска→выбора→создания документа,
управление активностью и errors/focus/retention; affected suites/check/drift,
миграция при необходимости, build/types и визуальная приёмка. Один активный
этап, внешний нормативный состав форм не подменяется этими шаблонами.
UI skills/reuse constraints прежние: Settings/Select/Modal/Button, dial1/1/1,
типографика/spacing tokens, формы без декоративных секций, abortable read,
dirty/pending и запрет автоматической потери текста.

## Закрытие К01: подтверждённые медицинские реквизиты

К01 пользовательский сценарий локально принят: медруководитель подтверждает
реквизиты клиники/врача, врач читает свои сведения; обе роли видят разрешённую
историю. Точные подтверждённые версии включены в schema4 документа и source_digest.
В принятом scope К01 остатка кода/локальных доказательств нет. Опубликован fff0555c;
полный M11 и нормативная/интеграционная приёмка не закрываются этим этапом.

Completion26275 exit0:105 tests PASS17.377s; check/drift PASS. Команда через
isolated_runtime: manage.py test apps.medical.tests_{credential_content,
credential_services,credential_api,document_credentials,document_identity,
document_previews,document_preview_api,document_content,document_services,
document_template_source,template_api} --noinput -v1 (явные dotted labels).
Лог TEMP/dental-credential-completion-backend-20261122.log.
Migration4735 exit0:1 test PASS10.654s, tests_credential_migration,
0026→0025→0026 сохраняет encrypted legacy history, confirmation не фабрикуется.
Лог TEMP/dental-credential-migration-20261122.log. Обратная миграция после новых
confirmation events не сертифицирована: нужен отдельный план сохранения данных.

Browser46305 exit0:7 PASS6.0m;28962 exit0:2 PASS2.3m (credential boundary +
прежний templates ru desktop). Команды через isolated_runtime,
E2E_MEDICAL_TEMPLATES=1, npx playwright test medical-credentials.spec.ts
--config=playwright.clinical.config.ts --max-failures=1; второй прогон:
medical-credentials.spec.ts medical-templates.spec.ts --grep
"empty read recovery|templates ru desktop" с тем же config.
Логи TEMP/dental-credential-browser-20261122.log и
TEMP/dental-credential-browser-boundaries-20261122.log. Все43 снимка из
output/playwright/medical-credentials-20261122 и
output/playwright/medical-credentials-boundaries-20261122 просмотрены.
PASS geometry/RU-KK-EN/1440-390/long values, real save/history/own read,
503 retry/key retention,409 retain/reload,403 clear, read retry,
keyboard Escape/Enter/focus return/dirty decline, pending-close guard,
history pagination. Axe dialog scans PASS. Loading/history snapshots могут
показывать промежуточное чтение; действия и итоговые версии проверены assertions.
Anti Slop delivery gate в затронутом scope PASS: existing tokens/control sizes,
functional data/forms/actions, no invented metrics/assets, visible labels/focus,
purpose/dials1-1-1/consistent layout; media/animation/marketing N/A.
React review: API adapter only, abortable reads, current role guards, no persisted
medical text, existing command idempotency/dirty protection reused.
Build21408 exit0:7931 keys/type/app/widget PASS; unchanged product inputs reused.
Terminology5 PASS; npm run check:bundle PASS (app shell361.0kB <400kB; RU/KK size warnings retained). Static13235 exit0, --mode static --base-ref
656dbd19318b6e146dbc0026afd1727fa719c14e; log
TEMP/dental-credential-final-static-20261122.log. No full suite/deployment/live
provider/working DB/PG-concurrency claim; финальный E0–E7 остаётся К18.
Следующий этап после публикации: К02 поиск и применимость утверждённых шаблонов.
Ниже сохранён ход итераций К01, его прежние WIP-отметки не текущий статус.

К01 текущая дельта: HTTP/workspace/member/history готов локально; gate95311
exit0,15 tests PASS1.562s (tests_credential_api +tests_credential_services),
check и migration drift PASS. TEMP/dental-credential-api-20261122.log.
Документы schema4 сохраняют точную подтверждённую clinic/clinician revision;
preview digest включает реквизиты, renderer добавляет4 literal fields.
Gate28027 FAIL5:4 новых fixture вызова без reason,1 legacy schema2 fixture
не удалял новое поле. Исправлены фикстуры, повтор3013 exit0:31 tests PASS4.400s
(tests_document_credentials/identity/previews/template_source),
TEMP/dental-document-credentials-r2-20261122.log. Добавлен отдельный schema3
compatibility regression, ожидает completion gate.
Settings credential UI/API adapter RU/KK/EN реализованы локально, UI ещё
не принят. Build first FAIL на6 медицинских ключах вне explicit allowlist;
добавлены только ключи нового медицинского раздела. Repeat21408 exit0:
i18n/types/app/widget PASS, TEMP/dental-credential-ui-build-r2-20261122.log.
Browser46305 in progress,7 scenarios, isolated DB/template fixture,
TEMP/dental-credential-browser-20261122.log; output/playwright/medical-credentials-20261122.
Не заявлять browser/visual PASS до результата и просмотра снимков.
UI direction: существующие Settings/Modal/Input/Button, dial1/1/1;
dirty/pending guard, retry same key,409 retain/reload,denial clear;
новая сущность только внутри явного medical module. Все изменения К01 WIP,
не staged/committed/published; рабочая БД не менялась.

К00 завершён и опубликован be235444; план опубликован90557c85, remote SHA
подтверждён. К01 implementation, gap code: существующее encrypted storage64 PASS
не имеет подтверждения/аудируемого пользовательского сценария. Минимальная дельта:
явная команда «сохранить и подтвердить» медруководителя, версия/подтвердивший/время,
история, doctor own read, private HTTP/UI и точный источник документа.
Используются Business/Member, current medical_documents view/approve (head business
scope), role guards, idempotent commands, MedicalAuditEvent, credential_content,
существующие Settings/Modal/command forms. Новый универсальный permission framework
не вводится. Внутренняя проверка не означает госреестр или ЭЦП.
Миграция только additive в medical; проверяется в isolated DB с roundtrip.
PHI не входит в общий audit/BusinessEvent/AI/уведомления; внешних эффектов нет.
Проверки: own/foreign/owner/doctor/head/revocation, stale/replay/payload conflict,
encrypted content, atomic audit failure, old-version preservation; затем API,
document source и reachable RU/KK/EN desktop/mobile UI, errors/focus/retention.
Не закрывать этап на одном storage/service PASS. Рабочая БД не изменяется.
Skills zani-change-crm-domain/verification и прежние UI skills сохраняются.

К01 первый серверный шаг локально проверен, этап НЕ закрыт: новая явная команда
confirm_medical_credentials создаёт encrypted revision и подтверждение head,
read_medical_credentials разрешает врачу только свой профиль, head business —
клинику/сотрудника. Аудит связан с точной credential_version и атомарен с записью;
идемпотентный receipt содержит HMAC вместо медицинского текста. Добавлены
confirmed_by/at и constraints, migration0026 (reviewed, рабочая БД не затронута).
Focused65164 exit0:20 tests PASS/0.470s (10 services +10 прежних storage),
`manage.py test apps.medical.tests_credential_services apps.medical.tests_credential_content
--noinput -v1` через isolated_runtime после генерации0026. Лог:
TEMP/dental-credential-confirmation-focused-20261122.log. System check PASS.
Проверены own/head/owner/doctor denial, foreign target, revoke до replay,
stale/payload conflict, обязательные поля, old history, encrypted receipt,
write/read audit failure и DB constraints. Следующий шаг того же К01:
workspace/history/member options и HTTP, снимок реквизитов документа, затем
достижимый UI и affected completion gate + isolated migration roundtrip.
Модели/services/tests/migration0026 остаются локальным WIP, не опубликованы;
не заявлять рабочий пользовательский сценарий К01 или PG concurrency PASS.

Публикация завершённых К00/плана: be235444 и90557c85 в origin/main, SHA прочитаны.
CI45055286299 и45055636682 на последней проверке in_progress, не PASS.
Внешний актуальный Desktop v1.2 §5.3 дополнен согласованной политикой реквизитов
(раньше она была записана только в v1.1 и access); это локальный файл вне Git.
План docs-only: исходные30 строк M01–M30 сохранены,19 этапов К00–К18 иE0–E7
покрыты, local links/table shape/diff hygiene PASS. Новый backlog не создавался.

## Текущее продолжение: классификация шаблонов, приёмка 22.11.2026

Владелец возобновил полное ТЗ: один пользовательский этап до приёмки, затем
следующий по зависимостям; новая очередь задач не создаётся. Objective прочитан:
attachment d215a8de-58bc-4ed3-b385-a315673716ee/goal-objective.md. Предыдущий
статусный ход дал новое evidence: ранее запущенный R2 завершился20 PASS;
он не был повторным запуском. Матрица M01–M30 ниже остаётся полной границей.
Root/branch/HEAD подтверждены: canonical PlatformaCRM, codex/ui-testing-toolkit,
1cde2dbcf578da9b98e8ca5a397ff5a88f2735c2. Чужой WIP auth/integrations/evidence
и чужие части STATUS/access сохранены; текущий этап не меняет их.

Предыдущий результат: metadata domain/API опубликованы → текущий R2 PASS и
визуальная проверка → завершить только classification editor/catalogue и docs.
Режим verification/delivery, риск API scope + functional UI; существующие
template ACL/commands/history/UI-kit переиспользованы. Без миграций, рабочих БД,
провайдеров, уведомлений, BusinessEvent/AI изменений. Skills antislop during
ui/human/layoutmobile/copywriting и zani-run-verification: прежние токены/1-1-1,
читабельный перенос, labels/keyboard/focus, retained input/denial clearing.

Локальная приёмка классификации завершена:
- API90252:26 PASS/1.543s, tests_template_metadata + tests_template_api +
  tests_common_template_api в isolated runtime; TEMP/dental-template-classification-api-20261122.log.
- Browser64149 R2:20 PASS/6.1m, `npx.cmd playwright test medical-templates.spec.ts
  --config=playwright.clinical.config.ts --grep 'templates (ru|kk|en)|common template:|template review:|template fields:|template services:'
  --max-failures=1`, E2E_MEDICAL_TEMPLATES=1, disposable DB pre-migrated.
  TEMP/dental-template-classification-browser-r2-20261122.log.102 оригинальных PNG
  в output/playwright/medical-template-classification-20261122-r2; все визуально
  просмотрены (16 до паузы,86 после). Sheets review*.jpg — только средство просмотра.
- Final build50216 exit0: `npm.cmd run build`, types/i18n/app/widget PASS после
  последней span-правки переноса. TEMP/dental-template-classification-final-build-20261122.log.
- Check/drift прежнего isolated запуска переиспользованы: backend/schema после
  них не менялись. Общий medical/full gate не повторяется без нового риска.

UI Delivery Gate в изменённой области PASS: геометрия390/1440 и RU/KK/EN,
длинные услуги, пустой каталог/поиск,503/retry без потери ввода,403 с очисткой,
keyboard Space/Enter/Escape и возврат фокуса, axe в authoring/detail, история
старой классификации и версия на рассмотрении. Закрытые ниже части формы
прокручиваются внутри существующего Modal; save/retry реально выполнены в R2.
Новых ассетов, декоративных блоков, палитры/движения/темы нет; media/marketing
проверки неприменимы. Purpose/quality: существующая форма и read-only dl служат
редактированию/просмотру версии; shared tokens сохранены, дублирования каталога нет.

Остатка кода/локальных проверок именно classification-сценария нет.
Опубликован be235444ef0c3831828a8a5c13af7562a97e447f normal push origin/main;
remote SHA совпал. Static55215 PASS (TEMP/dental-template-classification-final-static-20261122.log),
working/index/committed-range diff hygiene PASS. CI45055286299 in_progress,
не PASS. Deployment/рабочие миграции не выполнялись. Полный M11 открыт: поиск шаблонов, реквизиты,
PDF/подпись/выдача и остальные требования матрицы. Access/frontend/capabilities
обновлены; Desktop spec§5.3 содержит уже принятое решение по медреквизитам.
Дизайн/README не меняются: новая композиция и setup не вводились.

Ниже — хронология прежних попыток и результатов; её pending/running не заменяют
текущий статус выше. Последовательный план обновлён в разделе
«Актуальный порядок выполнения после возобновления22.11.2026» этого checkpoint.

Browser19171 terminal startup FAIL: webServer180000ms before any scenarios ran.
Owned clinical-runtime children terminated (current process inventory verified).
Build48401 PASS7916 keys/types/app/widget. Change hypothesis: clean migration
setup under concurrent build exhausted server readiness window; next isolated
runtime pre-migrates with logged output before same unchanged readiness/scenario
timeouts. Added RU service error/empty screenshots and metadata-only dirty/history
assertions before rerun; no product fix or weakened test. R2 log/output below.

Owner reply22.11: head enters/confirms clinic license, clinician specialty and
position; version history retained, doctor sees own profile, owner without medical
role has no confirmation permission; internal clinic check, not registry validation.
Recorded in Desktop technical spec§5.3 and access contract. Pending confirmation
question resolved; historical pending notes below describe earlier checkpoints.
Current classification UI gate continues unchanged; next credential services can
use this decision without asking again. Do not treat approved policy as implemented.

Classification service-options backend90252 PASS26/1.543s, log
TEMP/dental-template-classification-api-20261122.log. UI implemented after focused
PASS: existing template form classification, paged/searchable service selection,
selected-service removal/focus, retained input/retry, private denial clearing;
exact snapshot displayed in Detail/Review. Omitted unchanged metadata preserves
historical service references on text-only edit. Service catalogue search is NOT
template search; that separate full criterion remains open.
Build48401 and browser19171 running; browser20 scenarios RU/KK/EN390/1440 personal/
common/review plus field/service boundary, check/drift in isolated runtime.
Logs TEMP/dental-template-classification-build-20261122.log and
TEMP/dental-template-classification-browser-20261122.log. Output screenshots:
output/playwright/medical-template-classification-20261122; not yet accepted.

M11 classification UI contract, base1cde2dbc. Previous turn progress: metadata
backend/API111 verified/published. Reuse TemplateEditor/Detail/Review, existing
Input/Select/Button and command guards/API. Add medical-view service catalogue
lookup with bounded pagination/search, then language/category/specialty/selected
services editor and exact-version display. Same template ACL, no patient data,
no added write permission/audit for catalogue; retained metadata included only
when edited so removed historical services do not break text-only update.
Skills reused antislop during/ui/human/layoutmobile/copywriting, zani frontend/
verification: existing tokens/dials1/1/1, stacked mobile form, keyboard/focus,
retained drafts and RU/KK/EN. Endpoint scope/denial/pagination tests first, then
build/types and actual personal/common/review flows at390/1440, screenshots
captured AND inspected. Full template search remains later; no migration/provider/
working DB/notification/AI effects. Full goal ACTIVE, credential question pending.

Template metadata published1cde2dbcf578da9b98e8ca5a397ff5a88f2735c2,
normal push origin/main and remote SHA exact.10 task-owned files302+/17-;
canonical root/current branch codex/ui-testing-toolkit retained, foreign WIP
excluded via partial STATUS/access staging, index empty. Committed static22658
PASS; TEMP/dental-template-metadata-static-committed-20261122.log.
CI45040594824 in_progress, not PASS. All own processes terminal; no deployment/
working-DB migration. Post-publication checkpoint WIP retained for next commit.
Goal ACTIVE. Next: classification editor + medical service-options endpoint,
version/review display, then template search; current metadata draft/read API is
verified but not reachable through new UI yet. Credential confirmation question
remains pending; do not infer consent or reopen verified storage/field picker.

Template metadata backend/API local gate PASS111/15.559s (71490), check/drift
PASS. Static25756 PASS. Logs TEMP/dental-template-metadata-dependent-20261122.log
and TEMP/dental-template-metadata-static-20261122.log. Ten new metadata cases cover
literal encrypted data/no plaintext SQL, clinic service scope, shapes/limits,
old version and approval retention, renamed/deleted Service, omitted metadata
inheritance, explicit clearing, idempotency payload conflicts, revoked write,
audit rollback, corrupt snapshot, personal/common HTTP and common head denial.
Remaining101 cover existing template/review/document-source/preview behavior.
No migration/env/notification/BusinessEvent/AI change; current ACL reused. No
frontend/build/browser run because this slice changes backend/API only; metadata
editor, service selector and search remain required before feature acceptance.
Access/capabilities/M11 matrix/STATUS synchronized; spec/design/frontend/README
unchanged as requirements/design/setup remain valid. Full goal ACTIVE. Next:
reachable classification editor + service options and search; credential confirmation
still awaits owner reply. Publication recorded above.

Metadata first focused84750 terminal FAIL:20 PASS/1 error, fixture omitted
required decision reason in approve call; product path not failed. Fixed test
reason, added common HTTP head-only roundtrip. Final71490 running10 metadata
plus template/review/common/document-source/preview dependent suites, with
check/drift; log TEMP/dental-template-metadata-dependent-20261122.log.
Initial log TEMP/dental-template-metadata-focused-20261122.log. No equivalent
retry unchanged, no assertion weakened. Schema2 metadata remains backend-only;
UI authoring and search still outstanding, approval of credentials still pending.

M11 template metadata continuation contract, basebd236aed. Previous turn progress:
credential storage verified/published; confirmation owner question still pending.
Independent gap §2/6.1: versions lack language/category/specialty/service metadata.
Reuse encrypted template snapshots, revision approval, existing Service catalogue,
current personal/common service authorization/audit/idempotency. Add optional
metadata in version schema2, immutable service IDs/names from same Business,
strict fields/types and per-version history; omitted update preserves existing
metadata. Legacy schema1 stays readable. No new role/notification/BusinessEvent/
AI/provider/migration policy. Focus domain/API tests, affected review/document
suites, check/drift/static; then reachable metadata editor/search UI and browser
checks remain required. No working DB changes. Full M11/goal remain active.

Credential storage publishedbd236aed216409f86993fbfa188736c2ac1e0779,
normal push origin/main; remote SHA exact.8 task-owned files384+/3-.
Canonical root/current branch retained, foreign WIP excluded, index empty.
Committed static17634 PASS, TEMP/dental-credential-static-committed-20261122.log.
CI45039613406 queued, not PASS. All own processes terminal. Working DB untouched,
no deployment. Post-publication checkpoint WIP retained for next change.
Goal ACTIVE; previous turn progress = implemented and verified storage dependency.
Pending owner question: head enters/confirms medical license/specialty/position/
qualification versus doctor enters/head confirms. Do not infer an answer. Next:
confirmation/audit services after decision; independent PDF/template metadata work
remains available. Full matrix and external confirmations remain open.

Credential storage focused79643 PASS10/0.274s; log
TEMP/dental-credential-storage-20261122.log. Intentional migration0025 creates
only two module tables and five constraints, reviewed; no working DB changes.
Dependent68090 tests PASS64/7.212s (credential + document/template/content/identity/
source/preview suites), check/drift PASS; isolated migrate0025→0024→0025 PASS.
Log TEMP/dental-credential-dependent-20261122.log. Static31747 PASS,
TEMP/dental-credential-static-20261122.log. No browser/build gate: no UI changed,
feature is internal only and is not marked ready. Owner confirmation policy
question remains pending; independent storage does not grant any role rights.

Credential slice local gate complete; docs consistency reviewed. Spec/design/frontend/
README unchanged: no public behavior/setup change yet. PostgreSQL concurrency and
API/UI/approval/source integration unverified; full M11 remains open. Publication recorded above.

M11 credential storage contract, base548c831d. Previous turn = progress: field
picker verified/published. Evidence: Business/BusinessMember/Resource have no
medical license/specialty/position source (§5.2–5.3). Reuse their identity links,
medical encryption/transaction/version patterns; add module-owned versioned
clinic/clinician credential content, without duplicating names/requisites.
Internal storage only in this slice: no approval assertion, public endpoint or
permission grant before pending owner answer about confirmation responsibility.
Content is clinic-entered descriptive text, not a registry/licensing verdict.
Acceptance: same-Business links, unique scope/revision, encrypted literal data,
exact binding, stale rejection, old history intact, failure atomic rollback.
Check focused storage tests, affected document/template tests, isolated migration
forward/back, check/drift/static. No working DB, provider, notifications,
BusinessEvent or AI effects. Intentional schema migration; API/UI/audit/approval/
document source integration remain necessary before this feature is usable.
Skills zani-change-crm-domain and zani-run-verification applied. PDF skill read
for subsequent PDF work; no PDF implementation in this storage slice.

Published548c831df6a22639921d2387a916902aab52f0c1: normal push origin/main,
remote SHA read back exact;16 task-owned files366+/9-. Canonical root/current
branch codex/ui-testing-toolkit retained; foreign WIP excluded via partial STATUS/
access staging, index empty. Committed static24481 PASS against declared base
656dbd19318b6e146dbc0026afd1727fa719c14e; log TEMP/dental-template-fields-static-committed-20261122.log.
CI45038530416 in_progress, not PASS. gh unavailable; connector statuses empty;
authenticated GitHub Actions REST confirms actual run without exposing credentials.
Own tests/builds terminal; no deployment/working DB migration. Post-publication
checkpoint WIP retained for next change, no extra publication loop. Full goal
ACTIVE; next dependency: M11 clinic license/professional identity sources and
remaining template/PDF lifecycle, using existing settings/staff before adding data.

Field picker local acceptance complete on base1fea4bb2, branch codex/ui-testing-toolkit,
canonical C:/Users/user/Desktop/PlatformaCRM. R5 terminal PASS12/4.8m;
R4 unchanged boundary PASS1 (whole R4 failed later on fixture, see attempts).
Final build25564 PASS7907 keys/types/app/widget and static29149 PASS.
Backend8196 PASS15/1.064s; industry label tests PASS5; check/drift PASS in R1
isolated runtime. No schema/env/notification/BusinessEvent/AI changes.
Commands: tests_template_api + tests_common_template_api --noinput in isolated
runtime; node --test scripts/tests/industry-terms.test.mjs; npm run build;
Playwright medical-templates.spec.ts --config=playwright.clinical.config.ts
--grep 'templates (ru|kk|en)|common template:' --max-failures=1,
E2E_MEDICAL_TEMPLATES=1. Boundary command adds 'template fields:' to grep.
Logs: TEMP/dental-template-fields-browser-r5-20261122.log,
TEMP/dental-template-fields-browser-r4-20261122.log,
TEMP/dental-template-fields-build-final-20261122.log,
TEMP/dental-template-fields-static-final-20261122.log,
TEMP/dental-template-fields-api-20261122.log.
Screenshots: output/playwright/medical-template-fields-20261122-r5 (48),
r4 boundary folder (4); all52 captured and visually inspected. Existing tokens,
control sizes, mobile stacking, localized labels, no overflow in affected area;
keyboard/focus, dirty close, retained draft, empty/error/retry/denied and size
boundary exercised. Axe WCAG2a/aa passes personal editors. No new assets/motion
or decorative claims; Anti Slop scoped delivery gate PASS. Native device/provider/
PostgreSQL/full-release acceptance not claimed. Tests use synthetic data and
injected UI failures; backend authorization separately verified.
M11 matrix/access/frontend/capabilities synchronized; spec/design/README require
no change (approved requirements/design/setup unchanged). Entire goal ACTIVE:
field authoring gap closed locally, full M11 still needs license/professional
sources, PDF/checksum/lifecycle and remaining matrix. Publication recorded above.

R4 process44338 terminal: boundary PASS1 (empty/limit/replacement/focus/denial),
then personal RU desktop failed expecting catalog503 alert. One-shot route fault
was consumed by dev StrictMode aborted first load; second GET200 succeeds.
Confirmed React.StrictMode at frontend/src/main.tsx. Fault now remains503 until
explicit retry click, no product change. R5 process82303 reruns only12 dependent
personal/common scenarios; unchanged boundary evidence from R4 retained.
Logs: TEMP/dental-template-fields-browser-r4-20261122.log and
TEMP/dental-template-fields-browser-r5-20261122.log.

R3 process17611 terminal: boundary passed length preservation/replacement/focus,
but failed on expected medical.denied wording. Actual TemplateWorkspace deliberately
uses shared getApiErrorMessage sanitizer; dialog closed, actions/data cleared.
Verified current handler at TemplateWorkspace.tsx:29-30/87. Corrected test to
existing contract: visible sanitized alert, no rows/create/dialog; no product
wording change or weakened access criterion. R4 process44338 running13 scenarios,
TEMP/dental-template-fields-browser-r4-20261122.log. No duplicate live runtime.

Browser22838/R2 terminal FAIL boundary: after max-length insertion error,
Textarea accessible name included nested error text, exact labelled locator no
longer resolved. Screenshot inspected: content retained and limit error visible.
Minimal product fix: explicit localized aria-label on TemplateEditor textarea;
error remains aria-describedby. Added limit-state screenshot. R3 process17611
rechecks boundary first then dependent12 scenarios; TEMP/dental-template-fields-browser-r3-20261122.log.
Static77919 PASS before this aria-label delta; final build/static still required.

Build73536 R3 PASS7907 i18n keys/types/app/widget. Browser76886 R1 terminal
exit1: no tests matched (anchored --grep matched full Playwright title, not only
test name); check/drift PASS, no browser acceptance executed. Corrected grep to
unanchored scoped names and included new boundary case; R2 launched with
TEMP/dental-template-fields-browser-r2-20261122.log and output/playwright/
medical-template-fields-20261122-r2. No product change for this runner error.
Boundary case covers empty catalog, length refusal without truncation, selection
replacement recovering from limit and catalog403 clearing workspace.

Field catalog backend8196 PASS15/1.064s (tests_template_api + tests_common_template_api),
TEMP/dental-template-fields-api-20261122.log. Frontend insertion implemented after
this PASS: server allowlist, localized existing/new labels, cursor/selection replace,
focus return, length refusal, catalog503 retry preserves draft. Exact six medical
label exemptions added to industry-terms guard; generic/unreviewed labels still
rejected,5 node tests PASS. BuildR1 correctly caught unregistered medical-only
labels; R2 caught Object.hasOwn unsupported by current TS target. Fixed exact
keys and used hasOwnProperty.call, no tsconfig weakening. Logs TEMP/dental-template-fields-build[-r2]-20261122.log.
Final build73536 R3 and browser76886 R1 running (12 personal/common RU/KK/EN
390/1440 scenarios, isolated runtime + check/drift). Preserve attempts; no equivalent
retry without changed inputs. Full goal ACTIVE; current field picker not yet verified.

Field insertion continuation contract, base1fea4bb2, canonical root/current branch.
Previous goal turn = progress: published verified source snapshots + reachable
preview. Current gap: TemplateEditor requires manually typing known field tokens.
Reuse renderer DOCUMENT_FIELDS, existing template workspace ACL, API adapter,
Select/Button/Textarea and dirty/retry guards. Add authenticated field-options
catalog without patient data, localized selection and insertion at saved selection
with focus return, size limit and recoverable catalog errors preserving draft.
No schema/env/notification/BusinessEvent/AI changes; no new medical policy.
Skills reused antislop during/UI/human/layoutmobile/copywriting and zani domain/
frontend/verification: same tokens/dials1/1/1, meaningful controls, keyboard/focus,
RU/KK/EN +390/1440 layout and retained text. Test catalog scope/denial, then real
personal/common editor insert/save/reopen/recovery; build/types/check/drift/static,
capture+inspect affected screenshots. Full M11/goal remains open.

Preview API/editor published1fea4bb22561abad3a3402bca10ad169b2cf2bcc,
normal push origin/main and remote SHA exact.13 own files249+/24-; preceding
snapshot/domain5469fee8 also published. Committed static26562 PASS:
TEMP/dental-document-preview-ui-static-committed-20261122.log. CI45036064247
in_progress (not PASS). Canonical C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit retained; foreign WIP excluded, index empty.
Own test/build processes terminal, no deployment/working-DB mutation. This
post-publication checkpoint remains WIP for next task commit, no publish loop.
Turn progress: approved template auto-fill now reaches real document editor;
server identity/source snapshots and stale-source guard verified. User decision
head-only template approval retained in contract and implementation. Full goal
ACTIVE; next dependent work is template-authoring field selection, then remaining
M11 profiles/license/PDF/lifecycle and full matrix. Do not mark M11/goal complete.

Final EN copy evidence:16 screenshots captured and visually inspected in
output/playwright/medical-document-preview-en-final-20261122 (review-1..4.jpg).
Final applicable set:32 unchanged RU/KK +16 final EN =48 screenshots;64 viewed
across both runs. No remaining observed scoped UI defects. Logs:
TEMP/dental-document-preview-en-final-20261122.log and
TEMP/dental-document-preview-ui-build-final-20261122.log. Full release/provider/
PostgreSQL concurrency/native-device acceptance not claimed. Own runtime sessions
terminal. Commit/publication pending. Next: template-authoring field picker;
other M11 and full-goal matrix remains active, no reduced MVP scope.

Preview API/UI local acceptance:5608 PASS22/4.553s,89335 PASS6/4.5m;
check/drift PASS in89335 runtime. Build94929 PASS; static84607 PASS.
Logs TEMP/dental-document-preview-api-20261122.log,
dental-document-preview-ui-browser-20261122.log,
dental-document-preview-ui-build-20261122.log,
dental-document-preview-ui-static-20261122.log.
Browser command: isolated_runtime + E2E_MEDICAL_TEMPLATES=1 npx playwright test
medical-documents.spec.ts --config=playwright.clinical.config.ts --max-failures=1.
Real preview substitutes patient/doctor/record and reports absent/unknown fields;
real save/update/history preserves edited text, stable retry, original clinical
draft and old-version race fix. UI503/409/403 injected; actual source409/ACL/rollback
proven separately by backend tests, not by the injection. No real provider claim.
All48 named screenshots captured AND visually reviewed via review-1/2.jpg in six
scenario folders under output/playwright/medical-document-preview-20261122.
No observed geometry/overflow/focus/readability failure; lower dialog actions are
reachable by scrolling and exercised. English singular grammar corrected after
review; EN2 rerun3172 PASS2/2.9m and final build19019 PASS. Unchanged RU/KK4 evidence
remains applicable. New text uses count-neutral wording.
Delivery gate scoped: purpose real fields/status/actions, same tokens/Modal/Textarea,
1/1/1 dials and primary save accent, labels/focus/axe/keyboard, error/retry/empty,
mobile long title and retained drafts PASS, including final EN-copy rerun.
New assets/motion/marketing/provider/security claims N/A. No new migrations,
working DB/env/notifications/BusinessEvent/AI changes. Full goal ACTIVE;
field insertion in template editor remains next dependency, full M11 not closed.

Preview HTTP focused5608 terminal PASS22/4.553s; tests_document_preview_api,
tests_document_previews,tests_document_api, log TEMP/dental-document-preview-api-20261122.log.
Proceeding to dependent existing DocumentEditor: use server preview for new text,
retain existing saved text on edit, submit digest and preview revisions. Missing/
unknown template fields reported with localized status; no auto-rewrite on refresh.
UI skills reused: antislop during/UI/human/layoutmobile/copywriting, zani frontend,
React best practices. Applied requirements: approved tokens/Modal/Textarea geometry;
private component state+abort on unmount; preserve dirty/error/retry/conflict guards;
RU/KK/EN status and desktop/mobile keyboard/a11y. No new screen/design/assets.
Acceptance: real auto-fill/save, retained edit text, source-change409/recovery,
preview failure retry/denial, existing history/clinical retention; build/types,
affected browser screenshots captured AND inspected, dependent backend check/drift.
Template-authoring field picker remains separate open requirement, not claimed here.

Snapshot/preview domain published5469fee832b06d7e2627ceb8e58d5a2e4bac8ec9;
normal push origin/main, remote SHA exact.11 own files602+/15-, foreign WIP
excluded. Committed static13291 PASS (TEMP/dental-document-source-static-committed-20261122.log).
CI45034772493 in_progress, not PASS. Canonical root/current branch retained.
Next dependency contract: expose GET /medical/documents/preview/ through strict
scope/template/document serializers and optional expected_source_digest on draft
commands. Reuse current domain authorization/audit/no-store and retain existing
manual clients. Test HTTP rendered text, source change409/replay, malformed input,
owner/tenant/branch/unapproved denial, exact audit and rollback503 before UI wiring.
No schema/env/notification/BusinessEvent/AI impact. Focused API+domain suite,
check/drift/static; build/browser deferred until frontend changes. Full goal ACTIVE.

Source snapshot/preview domain verified locally on base89fd49b7 + own dirty delta.
Focused73746 PASS33/4.026s; focused81431 PASS26/7.366s (before final race guard).
Dependent42872 terminal exit0:85 tests/21.660s PASS including post-snapshot race
rollback; system check PASS; makemigrations --check --dry-run: no changes.
Commands: isolated_runtime, manage.py test apps.medical.{tests_document_identity,
tests_document_previews,tests_document_services,tests_document_content,
tests_document_reads,tests_document_api,tests_document_template_source,
tests_common_template_api,tests_template_review_api} --noinput; manage.py check;
manage.py makemigrations --check --dry-run. Log TEMP/dental-document-source-dependent-20261122.log.
Current source digest is checked against both pre-save context and actual retained
schema3 snapshot. Simulated doctor edit between checks rolls back. This is not
PostgreSQL concurrent transaction proof. No working DB or migration applied.
Updated access/capabilities/STATUS/M11; corrected stale UI-not-connected claims
using already published89fd49b7 evidence. Spec/design/README/frontend contract:
no change required (approved requirements, setup and UI remain unchanged).
Static9275 PASS (TEMP/dental-document-source-static-20261122.log);
commit/publication pending. Next: HTTP preview/digest API and editor flow;
license/professional profiles, PDF and full M11 remain open. Goal ACTIVE.

Identity snapshot focused73746 PASS33/4.026s (tests_document_identity,
tests_document_template_source, tests_document_content); log
TEMP/dental-document-identity-focused-20261122.log. Proceeded to dependent literal
auto-fill domain: fixed {{field}} allowlist, one pass/no eval, missing values empty
and reported, unknown tokens preserved/reported,131072 output bound. Current
patient/clinic/branch/doctor/clinical source digest prevents saving a stale preview;
replayed successful commands retain exact old version after source changes.
Preview authorizes create/update through current workspace permissions, approved
template visibility and exact encounter read audit. HTTP/UI not yet connected.
Focused preview process81431, TEMP/dental-document-preview-focused-20261122.log.
Original full goal preserved; these foundations do not close auto-fill UI/M11.

M11 source snapshot continuation contract, base89fd49b7: previous turn progress
(document UI implemented/verified/published). Proven gap: approved document schema2
has patient_id only; patient identity and record/timezone source are not retained.
Before auto-fill, add schema3 for new approved-source drafts: encrypted identity
snapshot from current PatientProfile/Client plus exact encounter revision metadata.
Reuse Business lock, existing current ACL/audit/replay, crypto, version storage;
schema1/2 history remains readable, no rewriting of issued/stored versions.
Check source shape/tenant binding, malformed ciphertext/digest, later identity/
record/timezone edits preserving old data, rollback, legacy reads and no plaintext
ledger. Focused tests before dependent suite; check/drift/static at completion.
UI/schema/env/providers/notifications/BusinessEvent/AI unchanged in this delta;
current frontend tolerates additional snapshot fields. No app build/browser solely
for internal additive storage. Auto-fill/UI and professional/license profiles
remain next dependent work, not declared complete. No source for verified medical
license or specialty found in current medical/Business models; do not invent values.

Document UI опубликован89fd49b7439e4055eda05f72f4f3e45b87cdc582, normal push
origin/main, remote SHA совпал.14 own files601+/12-, foreign WIP excluded,
canonical root/branch codex/ui-testing-toolkit retained. Committed static59350
PASS: TEMP/dental-documents-ui-static-committed-20261122.log. CI45033149862
in_progress, не PASS. Индекс пуст, owned test/build processes terminal. Этот
post-publication абзац WIP для следующего task commit, не отдельный publish loop.
Turn progress: reachable document draft flow implemented/verified/published;
full goal ACTIVE. Next work: approved auto-fill/full source snapshot contract,
plus explicit remaining M11 and other matrix items. Do not reopen tested flow
without a reproduced defect/unmet requirement; retain old-version race fix.

Document UI локально проверен:38877/R6 PASS6/4.7m, build67323 PASS (7889 keys,
tsc/vite/widget), static36332 PASS. Logs TEMP/dental-documents-ui-browser-r6-20261122.log,
dental-documents-ui-build-race-fix-20261122.log, dental-documents-ui-static-20261122.log.
Commands: npm run build; isolated_runtime + E2E_MEDICAL_TEMPLATES=1 npx playwright
test medical-documents.spec.ts --config=playwright.clinical.config.ts --max-failures=1;
static --base-ref 656dbd19318b6e146dbc0026afd1727fa719c14e. Backend/schema unchanged,
no additional backend suite required; existing41 metadata tests apply unchanged.
Document cases: actual approved template via head decision, create/update/exact
version/history,503 retained input+stable retry,409 retained text+confirmed reload,
403 content clearing, pending Escape blocked, clinical dirty retained across save,
back focus, long unbroken mobile title, no medical local/sessionStorage, axe.
503/409/403 are injected HTTP UI checks; not new real role/concurrency evidence.
Six R6 inspection sheets cover36 screenshots, all visually inspected; plus25
clinical regression screenshots =61 applicable images. No visible overflow or
geometry/focus/readability defect remains in observed states. Scrolled dialog body
keeps controls reachable; lower controls outside screenshot are exercised by tests.
Delivery Gate scoped PASS: geometry/responsive (1440/390,long title); meaning
(real title/author/revision/draft, no fabricated signature); behavior (real commands,
errors/empty/recovery and protected drafts); a11y (axe, labelled fields, Escape,
focus return); design purpose/identity (existing tokens/Modal/Button/Tabs,1/1/1,
primary save accent). No new assets, themes, animations, provider claims: N/A.
Canonical root/branch retained, base774486d1, foreign WIP excluded. Working DB,
schema/env/notifications/BusinessEvent/AI/providers untouched. Frontend contract,
capabilities, STATUS and M11 matrix updated; spec/design/README need no requirement
or setup changes. Full goal ACTIVE: M11 still lacks auto-fill/full identity-license
snapshot/PDF/checksum/finalize/signature/issuance and remaining template metadata.
Next: inspect approved field substitution contract and identity snapshot sources;
implement safe literal auto-fill with immutable source, then expose it in editor.
Additional document pagination/read-failure browser coverage remains to broaden;
current browser acceptance covers the six scenarios above, not every M11 criterion.

R5/54533 reproduced UI race: update succeeded but row remained clickable during
list refresh, so old version_id reopened (expected corrected text, got original).
Minimal fix: disable document row buttons while loading, matching established
template workspace fix. Browser create/update/read scenario is the regression.
No backend rewrite. Previous template closure preserved; new document caller now
applies same protection. Full document UI acceptance still pending.

Clinical regression52461 terminal PASS8/6.5m: medical-clinical, clinical-recovery,
history-recovery specs; real clinical conflict/revocation, retained input, save-close,
history recovery and RU/KK/EN desktop/mobile.25 screenshots inspected through four
inspection sheets in output/playwright/medical-documents-clinical-regression-20261122;
existing geometry/controls/dialog states preserved. No new visual defect observed.
Document R4/93446 terminal exit1: webServer startup exceeded180s, no scenario ran;
parallel startup under host load is a hypothesis, not app failure proof. R5/54533
started after regression terminated, same isolated inputs plus finalized focus/
scroll/patient label and long title/pending-close tests; no timeout relaxation.
TEMP/dental-documents-ui-browser-r5-20261122.log. Build73653 PASS, but subsequent
mobile focus effect requires final completion build. New files staged explicitly;
no foreign WIP staged; publication awaits document/browser/static acceptance.

UI attempts: R2/21589 FAIL1 +5 not run at test locator (wrapped Textarea label,
accessible textbox present in snapshot/screenshot); changed to getByRole textbox.
R3/74720 FAIL1 +5 not run at test expectation of raw503 detail; shared API correctly
sanitizes infrastructure errors, changed assertion to visible alert as existing
template tests. These are distinct test hypotheses, no repeated identical run.
R4/93446 active, TEMP/dental-documents-ui-browser-r4-20261122.log, now also checks
409 retained input/confirmed reload and403 document content clearing (synthetic
HTTP injection, not real role revocation proof). Clinical regression52461 in separate
isolated DB/ports, log TEMP/dental-documents-clinical-regression-20261122.log.
Build8875 PASS, final added patient-name paragraph still requires completion build.

Documents UI implementation WIP: typed adapter + approved template reads, document
list/detail/history and nested editor, RU/KK/EN, separate guard/clinical retention.
Build20118 PASS (7889 keys); later focus/scroll/timezone edits require final rebuild.
Browser91036 terminal FAIL6 at setup head login via page.request (line25), before
document UI. Changed hypothesis/fixture: use separate real browser login for head
as established template tests; keep doctor cookies isolated. No product auth edits.
R2 process21589, log TEMP/dental-documents-ui-browser-r2-20261122.log,
max-failures1. Visual acceptance not yet proven, no commit/publication of this WIP.

Documents UI work contract, base774486d1: previous goal turn progress (verified
metadata publication). Code gap: reachable S06/S07 list, version history, approved
template selection and editable draft. Reuse document API, ClinicalReadScope,
MedicalRoleCommand, Modal/Button/Textarea and private component state. Separate
document guard from clinical dirty; retain clinical draft across document save.
Design §5.5: desktop list/preview, mobile list/detail with return focus; calm medical
workspace, energy/rhythm/motion 1/1/1, approved Platforma tokens, primary save accent.
Skills unchanged: antislop during/ui/human/layoutmobile/copywriting, design-taste
app-screens, zani frontend/access/verification. Applied: genuine server actions,
44px controls, labelled plain-text content, retained input/error/focus recovery.
Checks: frontend build/types, isolated real API browser flows RU/KK/EN desktop/mobile,
create/update/history, retry/conflict/denial, clinical dirty retention, axe/screenshots
visually inspected, static. No schema/provider/working DB/AI/notifications changes.
PDF/signature/autofill remain explicit open M11 requirements, not implied by UI.

Document workspace permissions опубликованы 774486d14483b2e9141f58aba1639a09def3da9e:
normal push origin/main, remote SHA совпал. Canonical root и ветка
codex/ui-testing-toolkit сохранены; 8 own files, 157+/5-, чужой WIP исключён.
Committed static PASS: TEMP/dental-document-metadata-static-committed-20261122.log.
CI 45030228503 in_progress, не PASS. Индекс пуст; post-publication запись WIP.
Текущий turn восстановил фактический commit после потери tool output и завершил
публикацию проверенного изменения; новая UI реализация ещё не начата.
Следующий шаг остаётся Documents UI: frontend/src/api/medicalTemplates.ts пока не
имеет approved list/version методов; добавить их вместе с document adapter и
достижимым экраном, а не объявлять один adapter завершённым пользовательским flow.
ClinicalReadScope/ClinicalBasis из medicalClinical.ts уже переиспользуемы.
Полный goal ACTIVE, все незакрытые требования матрицы сохраняются.

Document workspace metadata локально проверена:88683 PASS41/6.274s +check/drift.
TEMP/dental-document-metadata-20261122.log. Isolated runtime command:
manage.py test apps.medical.tests_document_reads apps.medical.tests_document_api
apps.medical.tests_document_services apps.medical.tests_document_template_source
--noinput; затем check и makemigrations --check --dry-run. Поля actions не выдают
полномочий, save service повторяет их; metadata read аудируется по record.
Проверены независимые create/update от medical_records, снятие create, unverified
identity, finalized encounter, owner/foreign encounter/lost branch denial,
audit failure и строгий HTTP scope. UI ещё не менялся, поэтому browser/build N/A.
Schema/env/notifications/BusinessEvent/AI/provider без изменений; рабочая БД прежняя.
Spec/design/README/frontend contract не меняются — реализация prerequisite текущего
UI scope. Access/capabilities/STATUS/matrix обновлены. Source/root/branch сохранены,
starting b73f710a, foreign WIP не затронут. Полный goal ACTIVE; UI остаётся открытым.
Следующий шаг: открыть S06/S07 design и fixture clinical-runtime, затем UI Documents
в ClinicalWorkspace с api.workspaceAccess (не context.actions.save_draft).
Учитывать отдельный guard документа: dirty clinical draft нельзя сбросить при
сохранении документа; pending нельзя закрыть/размонтировать через вкладку. Desktop
list+preview, mobile list→detail, editor/approved selector и history по design.

Продолжение document UI: предыдущий turn progress — b73f710a/82 tests PASS.
Обнаружен конкретный gap: clinical context сообщает только medical_records actions;
medical_documents независимы. До UI добавить document workspace-access на текущем
лечебном основании/приёме с create/update по тем же условиям primary draft service,
patient/encounter revisions и view. Не выводить права из CRM role/clinical save.
Focused metadata/HTTP tests до зависимого UI, затем affected/check/drift/static.
Следующий UI reuse ClinicalWorkspace Tabs и существующие формы/guard, S06/S07 design;
antislop during/ui/human/layoutmobile/copywriting: approved tokens, читаемые состояния,
сохранность ввода и focus, mobile list→detail. Фактический UI ещё не изменён.

Document API опубликован b73f710a45ebd87d37ee95ed9fea7e10705c6dc2, normal-push
origin/main remote SHA совпал. Canonical root/branch codex/ui-testing-toolkit
сохранены;10 own files477+/12-, чужой WIP исключён. Committed static86719 PASS,
TEMP/dental-document-api-static-committed-20261122.log. CI45029374009 in_progress,
не PASS. Индекс пуст, своих процессов нет; этот post-publication абзац WIP.
Следующий конкретный шаг: document UI из клинического workspace. Сначала прочитать
существующие ClinicalWorkspace/Encounter UI, дизайн S-документы, текущие metadata
permissions. Подключить approved template selector, literal editable document text,
create/update/read/history с сохранением ввода/409/retry/denial. Если metadata
прав недостаточно, добавить server-derived document actions на current basis,
не выводить права из CRM role или только наличия clinical editor. Source snapshot
API готов; auto-fill/PDF/finalization/signature ещё нет. Полный goal ACTIVE.

M11 document API локально проверен. Selectors82029:30 PASS3.376s; API/dependent4745:
81 PASS7.704s, check/drift PASS. Дополнительный cross-patient HTTP test60171:
1 PASS0.299s; всего82 применимых backend tests после добавления этой проверки.
TEMP/dental-document-reads-focused-20261122.log, dental-document-api-20261122.log,
dental-document-api-isolation-20261122.log. Команды isolated_runtime manage.py test:
focused tests_document_reads/tests_document_services/tests_document_template_source;
completion tests_document_api/tests_document_reads/tests_document_services/
tests_document_content/tests_document_template_source/tests_document_templates/
tests_template_api/tests_template_review_api/tests_common_template_api (apps.medical),
затем check и makemigrations --check --dry-run. Новый тест запущен отдельно:
apps.medical.tests_document_api.DocumentAPITests.test_other_patient_documents_are_absent_and_exact_routes_deny.
Static87982 PASS, TEMP/dental-document-api-static-20261122.log. Source scope:
357064f6 → document read context/payload reuse + selectors + strict HTTP +config URL.
Проверены create/update/replay/stale, raw-template/source/state rejection,
private responses, отсутствие чужого пациента в списке и отказ exact/history/filter,
owner/tenant/revoked denial, audit rollback, paging и отсутствие текущей версии.
UI/build/browser N/A: frontend не менялся; рабочая БД, schema/env/providers,
notifications/BusinessEvent/AI без изменений. PostgreSQL concurrency не проверена.
Canonical root/branch сохранены, чужой WIP исключается partial staging STATUS/access.
Access/capabilities/matrix/STATUS обновлены. ТЗ/design/README/frontend contract не
требуют правки: реализуется согласованная часть, setup/UI прежние.
Следующий шаг — reachable document UI из текущего приёма с approved selector,
редактором, историями и текущими правами; автоподстановка полей/PDF/finalization/
подпись и остальные требования M11 остаются открытыми. Полный goal ACTIVE.

M11 document API contract: предыдущий turn progress357064f6/115 PASS. Gap code:
нет list/history и HTTP документа. Reuse read context/primary draft/approved source,
StrictSerializer/no-store/Idempotency-Key. Сначала read selectors с единой проверкой
лечебного основания и exact-version audit, pagination; focused tests перед API.
Затем HTTP create/update/list/history/version без raw template и source metadata.
Риски: tenant/patient mismatch, metadata leak, read без аудита, stale/replay/rollback.
Проверки: selectors, HTTP negative/happy paths, dependent document/template tests,
check/drift/static. UI, schema, env, BusinessEvent/notifications/AI не меняются;
рабочая БД не затрагивается, полноценный document UI остаётся следующим шагом.

Approved source integration опубликована357064f641abcffd81a1a37e827c3c9cd6d12126,
normal-push origin/main SHA совпал. Canonical root/branch codex/ui-testing-toolkit
сохранены;7 own files298+/22-, чужой WIP исключён. Committed static27291 PASS,
TEMP/dental-document-source-static-committed-20261122.log. CI45028426359 in_progress,
не PASS. Индекс пуст, своих процессов нет. Post-publication запись остаётся WIP.
Следующий шаг: document API create/update/read/list/history на действующем
лечебном основании, только template_version_id/document_text для команд,
без входных raw template/approval metadata; no-store, strict serializers,
idempotency, tenant/role/stale/rollback HTTP tests. Затем editor/approved selector
из текущего приёма. Перечень/история документов пока не реализованы: сначала
авторизованные selectors + exact-version audit, затем API. Полный goal ACTIVE.

M11 approved document source локально проверен: focused36162 PASS38/4.271s
(до добавления2 дополнительных source tests), dependent52490 PASS115/12.982s,
check и migration drift PASS. TEMP/dental-document-source-focused-20261122.log,
TEMP/dental-document-source-dependent-20261122.log. Isolated SQLite; рабочая БД
не затронута. Команда manage.py test apps.medical.tests_document_template_source
apps.medical.tests_document_content apps.medical.tests_document_services
apps.medical.tests_document_templates apps.medical.tests_template_services
apps.medical.tests_template_reviews apps.medical.tests_common_templates
apps.medical.tests_template_api apps.medical.tests_template_review_api
apps.medical.tests_common_template_api --noinput; затем check и makemigrations
--check --dry-run через isolated_runtime. Static98297 PASS,
TEMP/dental-document-source-static-20261122.log. Нет собственных процессов.
Source IDs/approval metadata берёт сервер после current patient/encounter ACL
и approved selector; отдельный encrypted document_text входит в idempotency digest.
Schema1 и прежние raw service payload/replay совместимы; schema2 snapshot не читает
живой template при просмотре старого документа. Это не finalize/ЭЦП/PDF/форма.
Frontend/build/browser N/A: UI не изменён; HTTP/UI document flow ещё отсутствует.
PostgreSQL concurrency и внешняя medical/legal review не подтверждены. Scope этой
domain интеграции закрыт локально, M11 и полная цель ACTIVE. Следующий шаг:
строгий document API без raw template/source metadata входа, затем reachable UI.
ТЗ/design/shared frontend contract/README без изменений: согласованный сценарий,
setup/UI не менялись. Access/capabilities/M11 matrix/STATUS синхронизированы.
Starting e7f0c837, canonical root/branch сохранены; чужой WIP не затронут.

M11 document source integration contract: предыдущий turn progress — S17 common UI
e7f0c837 published/verified. Gap code: документ принимает только внутренний raw
snapshot. Добавить разрешённый approved template ID и отдельный doctor-edited text;
schema2 хранит исходный template snapshot + source IDs/approval metadata + итоговый
текст. Schema1 читать без изменений; raw internal service не выставлять через API.
Reuse primary encounter ACL, approved selector/receipt, encrypted snapshot,
idempotency/audit. Риски: неверная source version, личный/foreign шаблон, повреждение
receipt, подмена текста в replay, смена старых документов. Focused source tests +
document/template dependent suites/check/drift/static; UI/API позже. DB schema,
рабочие миграции, уведомления/BusinessEvent/AI/provider не меняются. Полный scope
сохранён, это foundation для document flow, не закрытие M11.

S17 common UI опубликован e7f0c83758b79db4ecd5e6dab179463ed51e89fe, origin/main
SHA совпал, normal-push56595. Canonical root/branch codex/ui-testing-toolkit
сохранены,15 own files205+/35-, чужой WIP не включён. Committed static50643 PASS,
TEMP/dental-common-template-ui-static-committed-20261122.log. CI45027584657
in_progress, не PASS. Своих процессов нет; индекс пуст. Этот post-publication
абзац остаётся WIP для следующего commit. Следующий конкретный шаг M11:
approved source template revision в primary document draft, сохраняя doctor-edited
text отдельно и проверяя актуальные permissions/receipt/idempotency/rollback.
Сначала document_services/document_content и schema contracts, затем focused
domain tests; не заменять raw internal snapshot без совместимости/явной версии.
Full goal ACTIVE; common UI проверен, весь M11/ТЗ не завершён.

S17 common UI локально проверен: common API adapter передаётся
в существующие Editor/Detail/History, submit использует common route, очередь и
decision общие. Head permissions отдельные, doctor common tab не получает.
Node9 PASS (API personal/common/review + terminology). Build58097 PASS,
7878 i18n keys/types/vite/widget; TEMP/dental-common-template-ui-build-20261122.log.
Browser29583:21 PASS7.5m (15 personal/review regression +6 common RU/KK/EN1440/390),
TEMP/dental-common-template-ui-browser-20261122.log,
output/playwright/medical-common-templates-20261122;66 screenshots inspected.
Визуальная проверка выявила неверный «Создать личный шаблон» в common режиме.
Исправлены commonCreate labels и dialog title RU/KK/EN; только common tests/build
повторяются: build75052 PASS7879 keys/types/vite/widget; browser65485 PASS6/6,5.4m. R2 evidence paths:
TEMP/dental-common-template-ui-browser-r2-20261122.log,
TEMP/dental-common-template-ui-build-r2-20261122.log,
output/playwright/medical-common-templates-20261122-r2.
R2:18 screenshots inspected. Применимая приёмка21 browser tests =15 regression
первого прогона +6 common r2;66 применимых снимков просмотрены (48+18).
UI Delivery Gate PASS: прежние токены/компоненты, geometry/locale/mobile без overflow,
состояния loading/retry/retained input, keyboard/Escape/focus return, axe без
serious/critical. React review: API слой и abort для чтения, приватный текст только
в component state, стабильный adapter передаётся в общий редактор без новых deps.
Static17485 PASS; TEMP/dental-common-template-ui-static-20261122.log.
Common UI готов к own-only publication; document source integration и остальное
M11 открыты. Spec/design соответствуют согласованному flow, изменений не требуют.
Backend code/schema не менялись;106 backend PASS afaca3d4 применимы к тому же коду;
browser fixture только выдаёт synthetic head create/update, рабочая БД не меняется.

Продолжение S17 common UI: предыдущий turn — progress (afaca3d4 published,
106 backend tests PASS). API готов → общего интерфейса нет → расширить существующий
workspace режимом common, переиспользовать Editor/Detail/History/Submit и очередь.
Skills antislop during/ui/human/layoutmobile/copywriting, frontend contract:
сохранять токены/компоненты; переносить tab/actions на mobile; сохранять ввод при
ошибке; проверять keyboard/focus и отрицательные права в реальном браузере.
Риск: смешение личного/common API, stale permissions и потеря ввода. Приёмка:
head create/edit/history/submit/approve, doctor denial, personal regression;
RU/KK/EN desktop/mobile screenshots inspected, build/types и focused API adapter.
Backend повторять только при изменении контракта; fixture изолированный.

Common domain/API опубликован: afaca3d4bf989e84f86ae3d637609e248628c762,
origin/main remote SHA совпадает; branch codex/ui-testing-toolkit, canonical root.
10 собственных файлов594+/17-, чужой WIP сохранён. Static29408 committed PASS,
TEMP/dental-common-template-static-committed-20261122.log; CI45025906159 queued,
не PASS. Индекс пуст, своих процессов нет. Следующий шаг: общий UI S17 и
подстановка утверждённой версии в документ; permissions/domain/API использовать
из common_template_services.py.63 focused +43 dependent/check/drift PASS;
не выдавать это за UI/PG/production-приёмку. Этот post-publication абзац остаётся
WIP для следующего commit. Полная цель ACTIVE.

M11 common domain/API: локально реализованы common workspace metadata,
create/update/list/history/read/submit и approved list/exact selector.
Фактический starting HEAD f956f568, branch codex/ui-testing-toolkit, canonical root
не менялся; чужой WIP сохранён. ТЗ §6.1 уже содержит принятое owner-решение об
утверждении медруководителем, повторное изменение формулировки не требуется.
Focused19393:43 tests,2 FAIL из-за ошибочного предположения нового теста об отсутствии
исходного fixture template. Исправлено на сохранность исходного набора IDs;
focused92919:43 PASS2.718s. API12594:63 PASS6.014s, system check PASS;
TEMP/dental-common-template-focused-r2-20261122.log и
TEMP/dental-common-template-api-20261122.log. Команда isolated_runtime:
manage.py test apps.medical.tests_common_template_api apps.medical.tests_common_templates
apps.medical.tests_template_api apps.medical.tests_template_review_api
apps.medical.tests_template_services apps.medical.tests_template_reviews --noinput.
Dependent49383: document_templates/content/services43 PASS2.395s; check/migration
drift PASS; TEMP/dental-common-template-dependent-20261122.log.
Этот срез пока не committed/published; frontend/build/browser N/A для данного API
среза, common UI предстоит. Schema/env/provider/notification/BusinessEvent/AI без
изменений; рабочая БД не затронута. PostgreSQL concurrency не подтверждена.
Static67230 PASS; полный intended diff просмотрен, только собственные изменения
подготовлены к commit/push, STATUS/access staged отдельными hunks.
Следующий шаг: own-only publication, затем common UI
и approved source version в документе. Полная цель ACTIVE, M11 не закрыт.

Продолжение M11: personal workflow f956f568 проверен → отсутствует управление
общими шаблонами и approved selector → переиспользовать save/submission engine
с отдельным common scope (owner_member=None). Медруководитель с business-scope
create/update/view управляет общими черновиками; approve остаётся отдельным
явным действием. Врач читает только утверждённые common или свои версии.
Новый черновик не отзывает прежнее утверждение: selector списка выбирает последнюю
утверждённую версию, exact selector проверяет receipt выбранной версии.
Риски: common/private scope escalation, подмена версии, replay/rollback.
Проверки: focused common domain + personal regression, affected suites/check/drift,
static. UI/API и document integration следуют после domain; схема пока прежняя.

Опубликовано f956f56834041b80edf67677767fabb1dfadced0 normal-push origin/main,
remote SHA совпал. Canonical C:/Users/user/Desktop/PlatformaCRM,
branch codex/ui-testing-toolkit;16 own files482+/28-, чужой WIP сохранён,
STATUS/access staged только своими hunks. Static63319 и committed37624 PASS;
TEMP/dental-template-review-ui-static-final-20261122.log,
TEMP/dental-template-review-ui-static-committed-20261122.log. CI45024496003
in_progress (не PASS). Своих процессов нет, индекс пуст; этот post-publication
абзац остаётся checkpoint WIP для следующего commit.
Следующий конкретный шаг M11: common template management для head и approved
selector для обычного документа, переиспользуя Template/Revision owner_member=None,
review receipt/audit/idempotency/current permissions. Сначала прочитать текущий
document_templates/document_services и условия §6.1, затем focused domain checks.
Не выдавать common draft врачу, не подменять approved revision новым draft;
сохранить personal submission/queue/retry/focus и отсутствие доступа у owner-only.
Категории/услуги/специальности и поиск, revoke, подстановка/источник версии в
документе, PDF/полный snapshot и оставшееся ТЗ открыты. Цель ACTIVE.

## M11: S17 personal review UI локально проверен

Наблюдаемый результат: врач отправляет точную текущую версию, head видит очередь,
утверждает/возвращает с причиной; автор читает status/reason в истории. Создание
новой версии не наследует approval. Owner без медицинской роли права не получает.
Boundary30335 PASS1/1,13.9s (1.7m с setup);3 native screenshots просмотрены:
queue-ready, conflict, denied. Всего применимых browser сценариев15:8 draft r3,
6 review r4,1 boundary-r2.48 screenshots inspected. Backend58/check/drift, node8,
build/types/i18n PASS; UI не заменяет PostgreSQL concurrency и внешнюю medical review.

UI Delivery Gate в принятом scope PASS: существующие токены/Modal/Input/Button,
ENERGY/RHYTHM/MOTION1/1/1 сохранены; primary обозначает выбранную очередь/действие.
Каждый блок обслуживает список/версию/решение/ошибку; новых декоративных блоков нет.
Geometry/locales/mobile PASS по48 снимкам, горизонтальный overflow отсутствует;
клавиатура/Escape/focus return и axe serious/critical PASS в dialogs + queue.
Loading/empty/retry/stale/denial/retained input PASS; pending не позволяет закрыть
команду или сменить версию. React review: API слой, abort на reads, приватный текст
только в component state, plain-text rendering, без новых dependencies/стилей.
Новые provider/env/working migrations/notifications/BusinessEvent/AI изменения N/A.
ТЗ/design/shared frontend contract/README не меняются: реализуются согласованные
правила, setup не менялся. Access/capabilities/M11 matrix/STATUS синхронизированы.
Остаток M11: общие шаблоны и clinical selector, metadata/search категории/услуги,
revocation, snapshot/full identity, document API/UI, PDF/печать и подпись далее.
Локальный UI-срез готов к own-only commit/push после static; цель ACTIVE.

Текущий срез: API4bb12bb7 проверен → UI не подключён → добавить verified own-version
review summary и approve metadata, затем существующий S17 review flow. Риски:
ложное утверждение новой версии/утрата ввода/доступ после revoke. Backend focused:
template API/review/service; UI: RU/KK/EN desktop/mobile, submit/reject/approve,
503 retry, stale/revoke, keyboard/focus, screenshots inspected, build/types.
Применяются прежние antislop during/ui/human/layoutmobile/copywriting и frontend
контракт: существующие токены/Modal/Command, явная версия и действие, сохранение
ввода при retry, перенос действий на mobile без горизонтального overflow.

Metadata84142:27 PASS3.130s; affected8112:58 PASS6.773s +check/drift PASS.
TEMP/dental-template-review-metadata-20261122.log,
TEMP/dental-template-review-ui-backend-20261122.log. Node8 PASS (API reads/commands
и industry terms). Build49575 PASS и финальный build90220 PASS после защиты
подтверждения отправки от переключения истории/редактирования;7875 i18n keys.
Логи TEMP/dental-template-review-ui-build(-r2)-20261122.log.
Browser10985:13 PASS/1 FAIL5.2m (RU390 review GET остался pending; request initiated
12:28:42.830, server completed only12:28:58.839 при teardown; screenshot loader).
Trace в output/playwright/medical-template-reviews-20261122/...5f479.../trace.zip.
Изменён hypothesis: два contexts на single-thread fixture могут блокировать
соединения. Только templates fixture теперь use_threading=True, production не
изменён. Повтор51309 в работе, output/...medical-template-reviews-20261122-r2,
TEMP/dental-template-review-ui-browser-r2-20261122.log. Старый FAIL не скрывать.
R2 получил medical_audit_unavailable503 при concurrent SQLite writes (trace
response versions/2). Прогон51309 прерван после установленной причины, own shell
PID13084 проверен по полной command line и остановлен вместе с деревом; exit1.
В templates fixture добавлен lock middleware: запросы к SQLite последовательны,
сокеты обслуживаются отдельными threads, чтобы aborted/preconnected sockets не
блокировали второй context. Это сохраняет прежнюю serial DB границу browser
evidence, НЕ доказывает PostgreSQL concurrency. Production/backend не менялся.
R3 session32955 в работе, TEMP/dental-template-review-ui-browser-r3-20261122.log,
output/playwright/medical-template-reviews-20261122-r3; добавлен queue screenshot.
Static75244 PASS до последнего изменения только fixture; committed gate повторить.
R3 завершён exit0:14 PASS4.2m. Все8 прежних draft сценариев сохранены;21 их
скриншот просмотрен через visual-check-1..4.jpg в r3 output. Изменение среды
устранило transport hang и SQLite audit collisions без изменения production.
На review снимках обнаружена неоднозначная подпись edit у approved/rejected
версии: заменена на «Создать новую версию» (RU/KK/EN), выбранный режим выделен
существующим primary Button. Final build62054 PASS (7876 keys), лог
TEMP/dental-template-review-ui-build-final-20261122.log. Повтор6 review сценариев
12672 в работе, TEMP/dental-template-review-ui-browser-r4-20261122.log,
output/playwright/medical-template-reviews-20261122-r4. Draft flow/геометрия
редактора от этой правки не изменены,8 PASS r3 остаются применимы.
R4 завершён exit0:6 PASS3.5m.24 review снимка просмотрены через r4 visual-check-1..4,
RU mobile queue/approved также в native size. Вместе с21 draft snapshot r3
просмотрено45 снимков применимого среза. Queue снимки при раннем screenshot
частично захватывают150ms transition; дополнительно stable queue screenshot
с animations disabled и workspace axe включены в boundary test12452 (в работе).
Этот тест также проверяет head409 после новой авторской версии и очистку данных
при403 на decision. HTTP реальный revoke/tenant deny уже покрыты backend.
Production unchanged после R4; build62054 применим. Новый test не требует build.
Boundary12452 FAIL на подготовке: прямой auth/token POST не установил CSRF cookie,
403 до review flow. Исправлен только test: обычный browser login в отдельном doctor
context, затем close, далее head login в основном context. Защита CSRF сохранена.
Повтор30335 в работе; TEMP/dental-template-review-ui-boundaries-r2-20261122.log,
output/playwright/medical-template-review-boundaries-20261122-r2. Никаких product
изменений после R4; тестовый отказ не считается отказом готового review сценария,
но boundary acceptance остаётся непроверенной до завершения повтора.

Опубликован review API:4bb12bb7bc416af20526debc53497fca9b816523, normal push
origin/main, exact remote SHA подтверждён. Canonical root/branch прежние,
исходящий диапазон только этот own commit; чужие WIP сохранены. Committed
static91668 PASS, TEMP/dental-template-review-api-static-committed-20261122.log.
CI45021788122 in_progress, не PASS. Своих процессов нет, индекс пуст.
Следующий шаг M11: подключить UI статусы/submit/head queue/approve/reject. Для
авторского UI добавить verified review summary/null в personal version (сейчас
GET review неотправленного draft возвращает403). Workspace-access должен сообщать
approve только при head + approve/view business scope. Не трактовать простой state
из DB как подтверждение: reuse read_review_decision после exact audit/decrypt.
TemplateWorkspace draftStatus пока утверждает «не утверждены» для всех, заменить
при подключении review UI; сохранить проверенные dirty/retry/focus/mobile сценарии.
Переиспользовать MedicalRoleCommand, существующие Modal/Input/Textarea и языки.
Нужны head browser fixture и desktop/mobile реальные сценарии с просмотром снимков.
Полный goal ACTIVE; common/revoke/clinical selection и остальной ТЗ не закрыты.

Продолжение M11: проверенный domain00f9c346 → отсутствует очередь рассмотрения →
добавить tenant-scoped пагинацию только отправленных текущих pending версий.
Переиспользуются _context/_head, version audit и receipt verification. Риск:
раскрытие личных черновиков/чужого Business; проверки: head/doctor/owner denial,
pagination, stale exclusion, audit rollback, затем affected backend/check/drift.
Queue domain focused11248:19 PASS1.917s. HTTP submit/read/decision/pending-reviews
добавлен поверх domain; affected76851:56 PASS3.004s, check/drift PASS.
Логи TEMP/dental-template-queue-focused-20261122.log и
TEMP/dental-template-review-api-20261122.log. Static65607 PASS, лог
TEMP/dental-template-review-api-static-20261122.log. Дополнительный HTTP boundary
прогон20034:6 PASS1.298s после добавления двух тестов tenant/stale/revocation;
TEMP/dental-template-review-api-boundaries-20261122.log. Production code неизменен
между affected и boundary прогонами. Новых миграций нет. Своих процессов нет.
Схема не менялась, рабочая БД/провайдеры не затронуты. Notifications/BusinessEvent/AI
N/A: только внутренний template review/audit. Build/browser N/A для этого backend
среза; UI ещё не подключён и не признан готовым. Весь M11 остаётся открыт.

## M11: утверждение версии шаблона, domain в работе

Опубликовано00f9c34640e24ac26b494f5edbed9b989068fae6 normal-push origin/main,
remote SHA подтверждён;10 files614+/12-, outgoing только свой commit. Root/branch
прежние. Working/index/committed static26927 PASS; чужой WIP сохранён, STATUS/access
staged частично. CI45020659770 in_progress, не PASS. Своих процессов нет.
Продолжить review HTTP/queue + UI статусы/send/approve/reject, используя этот
domain и receipt verification; обычный personal API не расширять чтением чужих
неотправленных черновиков. Общие шаблоны/revoke/clinical selection далее в M11.

Affected23777 завершён exit0:141 tests PASS5.985s, check/drift PASS; clean migrate
и0024→0023→0024 PASS в disposable SQLite. Этот roundtrip на пустой базе не доказывает
rollback после новых review/audit данных; рабочие миграции не выполнялись.
Static94023 exit0 PASS. Logs TEMP/dental-template-review-focused-20261122.log,
TEMP/dental-template-review-affected-20261122.log,
TEMP/dental-template-review-static-20261122.log. Все свои процессы завершены.
Access/capabilities/M11 matrix обновлены. ТЗ/design/frontend/README не требуют
изменения: принятое authority реализуется, публичный UI пока только personal drafts.
Build/browser N/A для domain slice. PostgreSQL concurrency, review HTTP/UI,
common templates/revoke/clinical selection остаются открытыми, полный M11 не закрыт.
Следующий шаг: review API/queue и UI submit/decision/status с current receipt
verification. Не публиковать approval API с прежним безусловным UI текстом
«не утверждены»: статусы и copy должны соответствовать фактическому состоянию.

Focused24209 exit0:14 tests PASS1.062s/check PASS, isolated SQLite. Затем добавлены
2 integrity checks (валидно зашифрованная подмена content и перенос receipt),
cross-Business version с валидной локальной ролью и модельная проверка membership
submitted/decided users. Affected23777 running: template/domain/API/storage,
role/access/services/reads/API и shared audit/document services; check/drift,
clean0024→0023→0024 в disposable DB. Migration0024 прочитана целиком.
PostgreSQL race/lock evidence ещё отсутствует; SQLite не подтверждает эти гонки.
API/UI review ещё нет; не заявляем готовый workflow. Working DB не менялась.

Предыдущий turn — progress:3eca32c6 UI опубликован/8+2 browser PASS. Owner reply
закрыл authority: head утверждает личные шаблоны/управляет общими, owner без роли
не получает доступа. Новый gap code: нет submission/approval records и переходов.
Scope первого domain шага: автор отправляет конкретную текущую личную версию,
head с явным medical_documents:approve (business scope) и view принимает/отклоняет
её; только submitted версии доступны review-reader, остальные private draft API
не расширяем. Review pending→approved/rejected; новая редакция отдельная версия,
не наследует approval; stale pending нельзя утвердить. Решение и его основание
привязаны к версии, reason/content digest encrypted, точный medical audit.
Переиспользуем Business lock, role_access, encrypted template storage и HMAC
command idempotency. Permission approve только head, без автоматического backfill.
Migration review+audit constraints; только disposable DB. Нет уведомлений,
BusinessEvent/AI/providers/working DB. API/UI/common templates следуют после
domain gate; полный M11 не закрываем наличием foundation.
Skills zani-change-crm-domain/zani-review-access/zani-run-verification; gates:
submit/approve/reject/read, role/module/member/Business denial, current scope,
stale/replay, rollback audit/crypto, version integrity; affected template/role
suites, check/drift, isolated migration roundtrip и static. UI не меняется здесь.

## S17 UI личных черновиков: локальная приёмка завершена

Опубликовано3eca32c61c2cf2cb827cb998520b16731d2cfa44 normal-push origin/main;
remote SHA совпал,25 files620+/25-, outgoing только свой commit. Canonical root
и ветка codex/ui-testing-toolkit сохранены. Committed static86602 exit0 PASS,
TEMP/dental-template-ui-static-committed-20261122.log. CI45019415965 in_progress,
не PASS. Чужой WIP сохранён, STATUS/access staged частично; своих процессов нет.
Следующий scope M11: согласованное утверждение конкретной версии медруководителем
и общие шаблоны. Сначала inspect текущих storage/role_access/audit и тестов;
новый template lifecycle permission и workflow через domain→API→UI, без
автоматического утверждения существующих drafts. Full goal ACTIVE.

Итог:8 distinct template browser scenarios PASS (80664:7/2.9m;74765:1/2.1m),
2 settings boundary regressions PASS30699/2.8m.22 screenshots captured+inspected:
output/playwright/medical-templates-20261122-r2 (20; review-1..4.jpg),
output/playwright/medical-template-settings-regression-20261122 (1),
output/playwright/medical-template-pagination-20261122-r3 (1).
Native mobile editor/history/conflict и regression/pagination также просмотрены.
Logs TEMP/dental-template-ui-browser-r2-20261122.log,
TEMP/dental-template-settings-regression-20261122.log,
TEMP/dental-template-pagination-r3-20261122.log. R1/R2 failures выше сохранены;
не объявляются PASS. UI source после build49677 не менялся, менялся только test.
Commands: frontend npm run build (types+i18n7859+Vite+widget), node --test
scripts/tests/medical-templates-api.test.mjs scripts/tests/industry-terms.test.mjs
(7 PASS); isolated_runtime + npx playwright test medical-templates.spec.ts
--config=playwright.clinical.config.ts, отдельно grep pagination; roles.spec.ts
grep roles boundaries. E2E_MEDICAL_TEMPLATES=1, для regressions также
E2E_MEDICAL_ROLES=1; отдельные DB/ports от isolated_runtime, рабочая БД не менялась.

Anti Slop Delivery Gate scoped PASS: геометрия/переносы desktop/mobile RU/KK/EN
проверены снимками и overflow assertion; Modal keyboard Escape/focus return и
labels/serious+critical axe PASS в6 locale/viewport сценариях. Purpose PASS:
только список данных, status черновика, формы/история/действия и ошибки;
декоративных блоков/assets/новых зависимостей нет. Liveliness PASS: существующий
ENERGY1/RHYTHM1/MOTION1, focal create/save, shared brand accent/Settings rhythm.
Craft PASS: literal text rendering,503 retains input+key,409 reload confirmation,
403 removes private state, pagination/read retry; реальных PHI/providers нет.
Marketing/media/animation/theme-toggle gates N/A: не добавлялись.
Backend33 tests из7bc77b7b применимы без изменения production backend; новые
migrations/system/full-project/live gates N/A для UI; scoped evidence не full goal.
Contracts access/frontend, capabilities и M11 matrix обновлены; внешнее ТЗ §6.1
обновлено по owner reply. Design/README без изменений: существующий S17 pattern,
новых setup/env нет. Своих процессов больше нет. Остатка личного draft UI scope
нет; полный S17/M11 открыт: approval/common templates, metadata/search/substitution,
PDF/подписи/выдача. Публикация готовится; goal ACTIVE.

OWNER REPLY22.11.2026: утверждает медруководитель. Личные черновики создаёт врач;
медруководитель утверждает их для клинического применения и управляет общими.
Владелец без медицинской роли этого права не получает. Внешнее ТЗv1_2 §6.1
обновлено, решение больше не pending. Workflow approval остаётся code gap;
существующие drafts не становятся утверждёнными автоматически. Следующий M11 scope
после UI — version-scoped approval/common templates с этим authority и аудитом.
Предыдущие заметки о pending сохраняют исторический контекст, актуально это решение.

R2 UI80664 PASS7 scenarios/2.9m;20 снимков просмотрены (4 contact sheets +
native mobile editor/history/conflict). Regression30699 PASS2/2.8m, owner revoke
при module-disabled и nonowner boundary сохранены; screenshot просмотрен.
Pagination98918/6146 не прошли synthetic read recovery: trace подтвердил отменённый
первый GET и успешный второй (StrictMode), одноразовая503 попадала в отменённый.
Тест исправлен на persistent503 до явного retry; runner74765 running. UI source
не менялся, остальные PASS сохраняются. Static7861 PASS.

Добавлены frontend API/access hook, Settings section/editor/history/list, sidebar
и route guard используют отдельный medical access. RU/KK/EN, shared Modal/forms,
ephemeral content state, abort read, replay-key retry, stale/denial handling.
Types3718 PASS; build49677 PASS после i18n точечного allowlist draftStatus (KK
слово «Клиникалық» разрешено только в medical module).7 node transport/terms PASS.
Browser70798 r1:4 PASS/2 FAIL (RU/KK mobile): сохранение обновляло список асинхронно,
повторный open успевал взять старый version_id. Исправлено disabled open при reload
и synchronous pending в saved. Дополнительно убрано повторное discard confirmation
при409 reload. R2 runner80664:7 scenarios running, включая stale/denial.
Settings boundary regression30699 running, pagination/read recovery98918 running;
все отдельные disposable DB/ports. Build PASS уже на финальном UI source;
после него добавлены только browser test coverage. Visual acceptance ещё pending.
React review: hooks unconditional, abort stale reads, user/Business-scoped metadata
cache only, template content stays component state, no raw component requests;
direct imports/shared primitives, no new dependencies. Sequential access then list
intentional: avoid reading/auditing template content until current access succeeds.

7bc77b7b server access опубликован/33 tests PASS → frontend ещё отсутствует →
подключаем API/list/editor/history в Settings, текущий доступ doctor/head через
workspace-access, не через owner bypass. Shared route/sidebar consumers сохраняем.
Роль/задача: врач создаёт и правит личный черновик, читает прошлые версии.
Источник данных: document-templates API; approval/PDF/clinical use отдельно.
Skills zani-review-frontend + Anti Slop during/ui/human/layoutmobile/copywriting,
design-taste app-screens: существующие Settings/Card/Modal/Input/Button, ENERGY1/
RHYTHM1/MOTION1; реальные действия/статусы; dirty/retry/conflict/denial cleanup;
RU/KK/EN desktop/mobile keyboard/focus/overflow. Без нового дизайна/провайдеров.
Риск: shared settings navigation, устаревшие права, утрата ввода. Проверки:
API transport, types/build/i18n, browser create/edit/history/retry/denial,
несохранённый ввод и representative settings regression; screenshots просмотр.
Нет миграций/working DB, новых полномочий, уведомлений/BusinessEvent/AI.

## S17: текущая работа — достижимость личных шаблонов

Опубликовано7bc77b7b5af78db4ece738a547452a4a261703d5 normal-push origin/main,
remote SHA подтверждён. Собственный outgoing commit,7 files104+/4-; branch
codex/ui-testing-toolkit/canonical root сохранены. Committed static27759 PASS;
CI45017523121 queued (не PASS). Чужой WIP исключён, STATUS/access staged частично.
UI S17 не реализован; следующий шаг — frontend API, settings access и редактор.

Workspace-access реализован. Runner80912 exit0:33 template API/service/storage
tests PASS0.840s, Django check/drift PASS, disposable SQLite. Лог:
TEMP/dental-template-access-20261122.log. Diff hygiene/static84828 exit0 PASS (TEMP/dental-template-access-static-20261122.log).
UI ещё не менялся; browser/build N/A для серверного шага, S17 остаётся открытым.
CI предыдущего5618f932 run45016811472 всё ещё in_progress при проверке.
Своих живых процессов нет. Следом подключить frontend API и доступ к settings.

Предыдущий turn повторно подтвердил уже записанный B07, нового результата не дал.
5618f932 API проверен → SettingsAccessRoute/Sidebar допускают только CRM settings
или integrations, medical-access section owner-only → нужен текущий server access
для личных шаблонов, затем подключение S17 без выдачи общих прав настроек.
Сначала добавляем read-only workspace-access к существующему template API:
doctor/head с medical_documents:view, флаги create/update из текущей роли.
Переиспользуем role_access; никаких текстов шаблонов, пациентов, новых ролей,
уведомлений, BusinessEvent/AI, миграций или working DB изменений.
Skills: zani-change-crm-domain, zani-run-verification; UI позже использует прежние
shared controls/tokens, RU/KK/EN, dirty/retry/focus и desktop/mobile.
Проверки backend: текущие права, отзыв, Business/module/owner denial, no-store,
отсутствие чтения/аудита документов; affected template suites, check/drift.
S17 UI и его browser/build acceptance остаются открытыми до фактической проверки.

## M11: личные черновики шаблонов, backend/API проверены

Опубликовано5618f9323150fa22a77d06099e56a1929c0983f9 normal-push origin/main;
remote SHA совпал. Ветка codex/ui-testing-toolkit/root прежние;12 files677+/5-,
outgoing range только свой commit. Working/index/committed static/diff hygiene
PASS, чужой WIP сохранён, STATUS/access staged частично. CI45016811472
in_progress, не PASS. Собственных процессов нет. Goal ACTIVE.
Следующий independent scope: UI S17 личных черновиков по существующим list/form
паттернам Settings/medical section; проверить достижимость именно для doctor/head,
а не только owner. Использовать новый API, history и current-role denial cleanup,
RU/KK/EN desktop/mobile, dirty/retry/conflict/focus, browser screenshots+inspection.
Authority шаблонов всё ещё ожидает async-ответа; не включать approval/clinical use
и не повторять вопрос. Full M11/PDF/полный snapshot/signatures/выдача открыты.

Affected76510 exit0:63 tests PASS3.200s, check/drift PASS, isolated SQLite; ожидаемый
503 в API test подтверждает audit-failure recovery (не regression). Clean migration
0023 и0023→0022→0023 PASS в disposable DB. Static25022 exit0 PASS;
TEMP/dental-personal-template-static-20261122.log. Working DB не менялась. UI/browser/build N/A для backend/API; S17 остаётся
следующим независимым шагом. Permission contract/capabilities/M11 matrix
обновлены; ТЗ/design/README не меняются: authority не выбрана, UI не заявлен.

Focused44182 exit0:12 domain tests PASS0.319s/check PASS, isolated SQLite;
TEMP/dental-personal-template-20261122.log. Migration0023 прочитана целиком.
После domain PASS добавлены history/list и HTTP /medical/document-templates/:
POST create, GET list, POST{id}/draft, GET{id}/revisions, GET versions/{id}.
Strict serializers не принимают owner/code/approved; no-store/private на ответах.
Affected76510:7 API +template services/storage +document services/shared audit
suites, check/drift, isolated0023→0022→0023; итоговый PASS выше,
TEMP/dental-personal-template-api-20261122.log. UI ещё не подключён (S17 в design);
browser/build N/A для этого backend/API среза, UI-критерии остаются открытыми.

Предыдущий turn progress:5f9a13e5 storage опубликован,43 tests/migration PASS.
Новый gap: registry пока внутренний, авторизованного личного draft workflow нет.
Scope: врач/head со своей явной medical_documents create/update/view ролью
создаёт/редактирует/читает только собственные личные черновики. BusinessMember
берём из текущего контекста, технический code генерирует сервер. Общие шаблоны,
утверждение/подпись и просмотр чужих личных шаблонов не входят в этот срез;
authority-решение всё ещё ожидается. Это не clinical approval.
Reuse template storage, role/capability, Business lock, idempotency и MedicalAuditEvent;
добавить exact template version audit без patient-связи/PHI в журнале.
Root/ветка прежние, HEAD5f9a13e5/base656dbd19; foreign WIP сохраняется.
Skills domain/access/verification: current role до replay, own scope, fail-closed
read audit, atomic write. Notification/AI/BusinessEvent/рабочая DB не затрагиваются.
Проверки: create/update/history/read/replay, другой member/tenant/owner/assistant,
отзыв/module/permissions, stale/conflict, audit/key rollback; affected document/
template/audit tests +check/drift +isolated migration roundtrip/static. После
domain PASS подключить API с strict input/no-store и отрицательными HTTP checks.
UI приёмка отдельна; весь M11 этим не закрывается.

## M11: версии общих и личных шаблонов, локально проверено

Опубликовано5f9a13e57e80664de4894a5544953b4a358cc85d normal-push origin/main;
remote SHA совпал. Root/ветка codex/ui-testing-toolkit прежние.8 files375+/3-,
весь outgoing range свой; working/index/committed static/diff hygiene PASS.
CI45015763336 queued, не PASS. Чужой WIP сохранён, STATUS staged частично.
Своих процессов нет, goal ACTIVE. Async-вопрос об authority шаблонов ожидает
ответа; не повторять его и не выбирать ответ за владельца. Независимый следующий
шаг: личные черновики шаблонов (current medical role, ownership, audit, API/UI),
связь exact template version с документом и подстановка snapshot-полей.
Клиническое утверждение/допуск не включать до решения; полное M11 не закрыто.

Affected69874 exit0:43 tests PASS2.083s, check/drift PASS, isolated SQLite.
Clean migration0022 и0022→0021→0022 PASS в disposable DB; working DB не менялась. Новое поле владельца не выдаёт полномочий;
auth/approval/template lifecycle не включены. Access contract/README/design/ТЗ
не меняются: ни новая authority, ни UI, ни утверждённая форма не добавлены.
Capabilities/M11 matrix обновлены; единственный checkpoint сохраняет весь остаток.
Новый code gap после этого среза: связать сохранённую версию шаблона с документом,
подстановка разрешённых snapshot-полей, API/UI; approval ждёт ответа на async-вопрос.

Focused28136 exit0:12 tests PASS0.284s/check PASS, isolated SQLite;
TEMP/dental-document-templates-20261122.log. Migration0022 прочитана целиком.
Дополнены проверка whitespace-only title и разных авторов; affected69874
проверяет template/content/services +check/drift +0022→0021→0022 clean isolated
migration, лог TEMP/dental-template-dependent-20261122.log. Static3852 exit0 PASS,
TEMP/dental-template-static-20261122.log; после последних правок ещё committed gate.
Async-решение authority по-прежнему ожидается, независимая работа продолжается.

Предыдущий turn progress:9d65712b document domain опубликован,109 tests PASS.
Gap code: источник template snapshot пока не имеет собственного version registry.
Источник §5.1/§6.1 и L05: общие/персональные утверждённые шаблоны, сохранённая
версия источника. Кто утверждает личные/общие шаблоны, в прочитанных правилах
не определено; async-вопрос владельцу отправлен, ответа пока нет. Не назначаем
новую медицинскую authority автоматически. Продолжаем независимый storage:
Business-scoped template с optional owner BusinessMember, append-only encrypted
revisions с real author/reason/source binding, optimistic revision и atomic rollback.
Эти версии ещё не клинически утверждены; approval/допуск к клиническому применению
зависят от решения. Авторизация/аудит/API/UI личных черновиков — независимый
следующий слой. Пациенты/документы не мигрируются.
Reuse AES-GCM, Business lock, template shape validator; skills domain/verification.
Root/branch прежние, HEAD9d65712b/base656dbd19; свой metadata WIP, чужой сохранён.
Нет новых user permissions/notification/BusinessEvent/AI/provider или working DB.
Проверки: Unicode/no plaintext, author/member/owner/tenant links, historical
versions, stale/duplicate/tamper, encryption rollback; affected document suites,
check/drift, isolated migration roundtrip/static. Full template workflow остаётся
открытым; PG concurrency/нормативная матрица отдельно.

## M11: доменные операции черновиков и аудит, локально проверено

Опубликовано9d65712b7c8191d61d1869179532dffb171a996a normal-push origin/main;
remote SHA совпал. Canonical root/ветка codex/ui-testing-toolkit прежние.
10 files517+/10-, весь outgoing range только свой commit, STATUS/access staged
частично; чужой WIP сохранён. Committed static/diff hygiene PASS.
CI45014684932 in_progress, не PASS. Собственных процессов нет, goal ACTIVE.
Следующий шаг M11 — versioned template registry/selection перед HTTP/UI;
не принимать произвольный клиентский template snapshot как утверждённую форму.
Существующие операции пока domain-only; PDF/полный snapshot/assistant/team/24h/
signature/issuance и внешняя нормативная матрица остаются открытыми.

Affected49539 exit0:109 tests PASS5.628s, check/drift PASS, isolated SQLite;
clean migration0021 и0021→0020→0021 PASS. Static87272 exit0 PASS,
TEMP/dental-document-services-static-20261122.log. Новые16 service tests
включены в109. Файлы/прямой HTTP, browser/build и live providers N/A в этом
domain slice; все открытые API/UI/registry/signature критерии сохраняются.
Access contract/capabilities/M11 matrix согласованы с текущей границей;
ТЗ/design/README не требуют изменения: утверждённое поведение не менялось.
Новых процессов нет, рабочая БД/ядро/уведомления/деньги не затрагивались.

Focused11680 exit0:14 tests PASS1.430s/check PASS, isolated SQLite,
TEMP/dental-document-services-20261122.log. Migration0021 с exact document
version audit прочитана целиком. Ещё2 теста (чужой patient document при валидном
own basis; update audit rollback) включены в affected49539: document storage/
services +encounter/audit/tooth/participation/patient/representative/record suites,
check/drift, isolated clean migration и0021→0020→0021. Итоговый PASS выше.
Лог TEMP/dental-document-services-dependent-20261122.log. Проверка rollback
миграции относится к пустой disposable DB, не разрешает откат БД с новыми событиями.

Предыдущий turn — progress: storage311aee6f опубликован,37 tests/migrations PASS.
Исходный gap: helpers не являются границей доступа, document audit отсутствует.
Implementation: create/update своего документа в своём Encounter, чтение конкретной
версии через текущее основание Appointment/Participation и medical_documents права.
Переиспользуем role/branch/basis guards, verified identity, encrypted snapshots,
Business lock, CRM idempotency и MedicalAuditEvent. Миграция добавит ссылку
на document version и ограничения событий; медицинский текст не попадает в ledger.
Scope: домен и тесты, без HTTP/UI до versioned template registry. Переданный
внутренним caller текст шаблона остаётся черновиком, не утверждённой формой.
Assistant/team/24h workflow ещё не реализован: этот срез — основной врач.
Root/branch прежние, HEAD311aee6f/base656dbd19; свой metadata WIP, чужие файлы
не меняются. BusinessEvent/notification/AI/provider/рабочая DB не затрагиваются.
Skills domain/access/verification: current authorization до replay; branch scopes;
атомарность audit+write; явная граница локальной проверки.
Acceptance: create/update/read с точным version audit, stale/replay/conflict,
отзыв/tenant/branch/module/identity denial, rollback audit/key failure, нет
изменений календаря/денег. Focused tests, affected audit/encounter/document suites,
check/drift, isolated migration roundtrip и static; PostgreSQL concurrency отдельно.

## M11: хранение версий документов, локально проверено

Опубликовано311aee6f6b7c76ef3b2d2dd411215e4ab2de7507 normal-push origin/main;
remote SHA совпал. Ветка codex/ui-testing-toolkit, canonical root прежний.
7 files472+/2-, outgoing range только свой commit; working/index/committed
static и diff hygiene PASS. CI45013689537 in_progress, не PASS. Чужой WIP
сохранён, STATUS staged частично; собственных процессов нет. Goal ACTIVE.
Следующий gap M11: versioned templates и сервисы draft create/read с текущим
medical ACL/audit/replay, затем PDF и интерфейс; не объявлять этот storage
полным lifecycle или утверждением нормативных форм. Полнота обязательств
M07 и финализация M08 зависят от document matrix/signature policy.

Dependent23960:37 tests PASS0.579s (15 document +13 encounter content +9 storage),
check/drift PASS, isolated SQLite. Migration clean install +0020→0019→0020 PASS;
23960 exit0, рабочая DB не менялась.
TEMP/dental-document-dependent-20261122.log. Static exit0 PASS,
TEMP/dental-document-static-20261122.log. Подтверждены исторические реквизиты/
текст при новой версии, source/tenant/patient binding, stale, tamper и rollback.
Это не проверка PostgreSQL concurrency, HTTP permissions или готового документа.
UI/build/browser N/A: маршруты/компоненты не меняются. Новый permission/audit
контракт пока не вводится; docs/current/access не меняем (там чужой WIP).
ТЗ/design/README не меняются: agreed behavior прежнее; capabilities и M11 matrix
обновлены с точным остатком. Нового паспорта/конкурирующего backlog нет.

Focused7635 exit0:12 tests PASS0.215s/check PASS, isolated SQLite,
TEMP/dental-document-storage-20261122.log. Создана миграция0020 (прочитана целиком).
Добавлены ещё3 регрессии source/history/patient binding; они включены в итоговый
dependent PASS выше (document/encounter +check/drift +migration roundtrip).
Последний CI-readback:45012637290 и45011775478 in_progress, не PASS.

Исходный implementation/code gap: MedicalDocument отсутствовал; M10 — план лечения,
документы относятся к M11. Предыдущее закрытие own-end foundation3182714e →
проверка §5/D06 подтверждает отсутствие document storage → добавляем только
внутреннее хранение черновиков/версий и снимков источника/реквизитов.
Root/branch прежние, HEAD3182714e, base656dbd19; чужой WIP сохранён.
Переиспользуем encounter revisions, Business lock, AES-GCM и реальные
Business/Branch/User/BusinessMember. Skills domain/verification; UI не меняется.
Версия связывает точный исходный clinical revision, автора и snapshot шаблона;
текст/реквизиты зашифрованы, чтение проверяет binding, изменение реквизитов
не переписывает историю. Запись следующей версии атомарна и проверяет revision.
Это внутренние storage helpers: вызывающий сервис обязан проверять медицинский
доступ и сохранять аудит в общей транзакции; новых HTTP/прав/уведомлений/AI нет.
Не создаём легальную форму, ЭЦП, PDF, выдачу или фиктивную матрицу обязательности.
Миграция только в isolated DB. Проверки: Unicode/encryption, source/tenant binding,
stale revision, история после смены реквизитов, tamper, rollback и DB constraints;
affected encounter suites + check/drift + isolated migration roundtrip и static.
PG concurrency, API/UI, полный snapshot личности/лицензии и утверждённые шаблоны
остаются следующими зависимостями, этот срез не закрывает M11.

## M07: обычное завершение участия и остаток обязательств, работа

Опубликовано3182714ef58e7e7596294632c8e41d00b648c62a normal-push origin/main;
remote SHA совпал.8 files268+/8-, весь исходящий диапазон собственный; static и
working/index/committed diff hygiene PASS. CI45012637290 queued, не PASS;
предыдущий45011775478 при последней проверке in_progress. Root/ветка прежние,
foreign WIP сохранён, STATUS/access staged частично. Собственных процессов нет.
Общий goal ACTIVE. Следующая работа по зависимости: сверить M08/M11 medical
finalization/document lifecycle, реализовать обязательства документов и завершить
own-end API/UI; не включать текущий неполный selector как полную приёмку M07.

Affected58116 exit0:44 tests PASS6.915s,check/drift PASS, isolated SQLite,
TEMP/dental-own-end-dependent-20261122.log. Публикуется только domain foundation;
HTTP/UI не включаются до полной композиции обязательных документов. Это не закрытие
M07 и не подтверждение PG concurrency. Следующий dependency: медицинские документы/
их обязательства и окончание MedicalEncounter, затем own-end API/UI и24h scope.
Frontend/build/browser сейчас N/A: новых UI/API маршрутов в этом срезе нет;
ранее проверенный S18/M21 не менялся. README/design/ТЗ не меняются: agreed rules
прежние; access/capabilities/матрица отражают точную границу. Новых миграций нет.

Foundation17681:17 tests PASS2.389s,check/drift PASS, isolated_runtime;
TEMP/dental-own-end-20261122.log. Добавлены own-end domain и ограниченный selector
Appointment/Encounter (count+первые50 ID без медицинского текста). Общий end audit
сохраняет требование текущей closure/revision/actor; отсутствие remaining_responsible
допускается только при закрытии своего участия, head override прежний. Новый сервис
пока не подключён к HTTP/UI; полнота обязательных MedicalDocument ещё не обеспечена.
Дополнены tenant/missing permission/inactive member/past unresolved/reassignment tests;
affected run58116 (own-end/head closure/services/notifications +check/drift) выполняется,
лог TEMP/dental-own-end-dependent-20261122.log. Working DB не менялась.

Предыдущий turn — progress: S18/M21 опубликованc135008d,9 browser/19 backend PASS.
Новый подтверждённый code gap: есть только end_participation_by_head; обычное
завершение своим врачом и перечень обязательств отсутствуют. Источник: ТЗ D03,
правила завершения участия1–3 (§18.1.3). Переиспользуем TreatmentParticipation,
MedicalEncounter, Appointment, role/branch guard, Business lock, idempotency,
encrypted closure и medical audit. Skills domain/verification применяются.
Первый dependency slice: selector открытых собственных приёмов/медицинских записей
и own-end service с повторной проверкой под Business lock. Незавершённые прошлые
записи не исчезают из обязательств только из-за течения времени; терминальные
и переданные записи не блокируют. Другие врачи/Business и деньги не меняются.
Область: существующие сущности. Полнота обязательных подписанных документов зависит
от ещё не реализованного MedicalDocument lifecycle; до подключения этого источника
и UI/API обычное завершение не объявляется готовым M07. Head override сохраняется.
Права own-end требуют medical_participation:update, текущую роль/членство/филиал;
replay не обходит отзыв. No new migration/BusinessEvent/AI/provider/working DB;
аудит и существующий нейтральный notification routing переиспользуются.
Проверки: own happy/replay, чужой сотрудник/tenant/роль/филиал, открытые Appointment
и Encounter, terminal/reassignment, stale revision, audit rollback; затем affected
participation closure/services и check/drift в isolated_runtime. PG concurrency,
полнота документов и reachable API/UI остаются явными зависимостями полного M07.

## M02/M06/B08: интерфейс S18/M21, локально проверен

Опубликованоc135008d8e445147567b35841bd89c3cb1c26793 normal-push origin/main;
remote readback совпал.28 files1012+/9-, исходящий диапазон содержал только этот
task-owned commit. Static final gate и working/index/real committed-range diff
hygiene PASS. CI45011775478 in_progress, не PASS. Canonical root/ветка сохранены;
STATUS/access staged частично, foreign auth/integration WIP не включён. Полная
цель ACTIVE; следующий turn продолжает оставшиеся строки матрицы, не переоткрывает
проверенный scoped UI без новой причины. Нет собственных работающих процессов.

Финальный backend95088:19 tests PASS0.923s, check/drift PASS в isolated_runtime;
TEMP/dental-role-ui-context-final-20261122.log. Все собственные runners завершены.
Собственный diff/new files просмотрен, foreign WIP сохранён. Изменения не создают
новых миграций/BusinessEvent/уведомлений/AI действий; существующие role audit и
encrypted basis переиспользованы. README/testing/design/внешнее ТЗ не требуют
изменения: agreed behavior/setup прежние, статус отражён frontend/access/capabilities
и матрицей M06. Подготовка own-only commit/normal push; полное ТЗ ACTIVE.
Следующий незакрытый результат: оставшиеся ACL/участие/24h и последующие строки
матрицы. PostgreSQL concurrency, owner self-approval и внешняя приёмка не закрыты
этими локальными9 browser/19 backend проверками.

Scoped UI result: создание определения/назначение/отзыв/история доступны owner через
Settings medical-access.15878/r3:7 browser PASS3.0m (6 desktop/mobile RU/KK/EN и
read503/self restriction/реальный stale409/инъекция403),36142 boundaries:2 PASS2.3m
(обычный сотрудник не видит management и получает403; реальное выключение medical
capability в disposable DB сохраняет UI revoke/history).26 viewport screenshots
просмотрены: типографика/выравнивание/переносы/диалоги без горизонтального overflow,
shared focus/controls, длинный список прав прокручивается внутри Modal. Axe WCAG2A/AA
для definition/member panels PASS. Escape/dirty dismissal, focus return, основания
и scope,503 stable retry key, disabled controls после409 проверены действиями.
Полный текст ошибки в длинном definition-form достигается прокруткой; viewport
снимки показывают текущую позицию, не весь scroll container. Скриншоты не доказывают
серверные права: они покрыты role backend tests и отдельным реальным403 в boundaries.
Финальные i18n/types/build57074 PASS после placeholder fix,7847 keys; Vite warning
о крупных shared chunks остаётся, это не результат измерения D12. Backend19 target
ещё выполняется95088 (добавлена проверка foreign branch name не выдаётся, inactive
branch history сохраняется). Предыдущий CI45008985438 completed/success подтверждён
REST API; origin/main==HEAD2fc04d04 после fetch. Новая UI публикация ещё впереди.

Восстановление: HEAD2fc04d04, текущая ветка codex/ui-testing-toolkit, индекс пуст;
собственные UI/role-context изменения отделены от foreign auth/integration WIP.
B07 owner reply сверено с внешним ТЗ §22.7: плановая дата без автоматического
отзыва уже записана, повторного изменения формулировки не требуется.
Role-context projection assigned_branches (имя/активность существующих филиалов):
18 tests PASS0.806s, check/drift PASS, TEMP/dental-role-ui-context-20261122.log.
Types/i18n/build PASS (92189 exit0), TEMP/dental-role-ui-build-20261122.log;
после этого добавлен business key для сброса локального состояния при смене tenant,
поэтому финальный types/build ещё требуется. API transport3 PASS; industry terms5
PASS, включая точечные исключения medical.roles без ослабления общих labels.
Browser первая попытка не стартовала: системный Python3.15 без environ; изменён
только interpreter на .venv/Scripts/python.exe. Повтор59496 в isolated_runtime,
E2E_MEDICAL_ROLES=1; рабочая БД не используется. Browser/visual acceptance пока
не подтверждена. Скриншоты output/playwright/medical-roles-20261122, лог
TEMP/dental-role-ui-browser-20261122.log. Commit/push этого UI ещё не выполнялись.

Browser59496:6 FAIL на login (fixture flag удалялся safe_environment), исправлено
чтением roles_fixture до configure_browser_runtime.33071/r2:1 FAIL,5 not run:
exact accessible name Select ошибочно ожидал только label без выбранного значения;
создание роли/503 stable key/axe прошли до остановки. Исправлен locator; retry15878/r3
добавляет отдельного target6 для stale409/read503/denial/self restriction сценария.
Просмотрен r2 failure screenshot: desktop layout читаемый, найден неверный placeholder
«Выберите сотрудника» у роли → shared common.select. Длинный locator screenshot
не годится для оценки прокручиваемой модалки; заменён viewport top/bottom capture.
Final build72139 PASS до этой локальной copy-правки; static86967 PASS на task base
656dbd19318b6e146dbc0026afd1727fa719c14e. UI acceptance остаётся открытой.

Предыдущий goal turn progress: backend опубликован2fc04d04,66 tests/check/drift
PASS. Gap UI: нет достижения role-management из настроек. Переиспользуем API,
SettingsSection/navigation/Modal/Input/Select/Textarea/Button, текущие токены.
Добавляем medical-access только владельцу стоматологического/medical-enabled
Business; отключение модуля не скрывает возможность отзыва. Сервер остаётся authority.
Списки сотрудников/ролей/филиалов/history с пагинацией; explicit create definition,
assign/revoke с reason/current revision; чтение ролей не предоставляет карту.
Skills frontend, Anti Slop during (сохранённая настройка), human/layoutmobile/ui/
copywriting, design-taste/app-screens применяются в прежней утверждённой стилистике
ENERGY1/RHYTHM1/MOTION1: shared tokens/controls, visible labels/focus,44px actions,
mobile reflow, данные из API/i18n. Без assets/dependencies/новой visual system.
Guard формы: dirty close/reload/navigation, stable retry key,503 retains input,
409 read-only+reload,401/403/404 clears private state; локальный state без хранения.
Проверки: typed transport,types/build/i18n, реальные owner define→assign→revoke→history
desktop/mobile RU/KK/EN; loading/empty/error/retry/stale/denial/self restriction;
скриншоты capture+inspect/axe. Backend повторять только при изменённом контракте.
Root/current branch сохранены; foreign WIP исключён. Полное ТЗ ACTIVE.

## M02/M06/B08: управление медицинскими ролями, работа

Опубликовано2fc04d04e37e2dfe8c3f82985024fb341524ec53 normal-push origin/main;
remote SHA совпал.16 files864+/11-, весь outgoing range — task-only commit.
Root C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit сохранены.
Static gate и working/index/real committed-range diff hygiene PASS; собственный
полный diff/new files просмотрены, STATUS/access staged только собственными hunks.
CI45008985438 in_progress, не PASS. Все runners завершены; чужой WIP сохранён.
README/testing/design/TЗ не требуют изменения: правила/запуск прежние, реализация
описана в access/capabilities и этой матрице. Полный goal ACTIVE, UI следующий.

Domain basis72598 exit0:59 tests PASS3.889s; check/drift PASS, migration0019
roundtrip сохраняет прежние назначения без выдуманных оснований. Лог
TEMP/dental-role-basis-20261122.log. Добавлены write API roles/assign/revoke и
owner-only history;24534 exit0:66 tests PASS5.870s, check/drift PASS в isolated
runtime. TEMP/dental-role-api-20261122.log. Backend/API boundary проверена;
UI/build/browser неприменимы к этому срезу без frontend изменений. PostgreSQL
конкурентность не запускалась/не доказана; Business lock/replay tests на SQLite
не объявляются доказательством PostgreSQL. UI и полный M02/M06/B08 открыты.
Следующий шаг: S18 в существующих настройках, owner-only entry, typed API, формы
определения роли/сотрудника/филиалов/основания, история, no-store ephemeral state,
503 retry/409 reload/403 clear; desktop/mobile RU/KK/EN и screenshot review.
Дизайн источник DESIGN_SPEC S18/M21, существующие SettingsSection/Modal/controls.
Backend код поверх6b7153fc; рабочие миграции/внешние сообщения не выполнялись.
Reason не попадает в общий AuditLog/CRMCommandIdempotency/командный ответ;
AESGCM связывает Business/assignment/purpose, JSON проверяет action/revision.
Новые команды требуют основание, исторические успешные service receipts replay
с прежним hash. No-op не создаёт ложную запись истории. UI ещё не подключён.

Read foundation18139 exit0:52 tests PASS1.801s (role_reads/services/access),
check/drift PASS; TEMP/dental-role-reads-20261122.log. Затем добавлен serializer
mapping для introspection; будет включён в следующий affected run.
Далее закрываем доказанный domain gap B08: обязательное основание grant/revoke,
encrypted append-only revision рядом с существующим assignment. Общий audit
остаётся без текста основания. Исторические назначения не backfill догадками;
старые успешные receipts replay без новых полей, новые изменения требуют reason.
Проверки: invalid/missing reason, replay/hash conflict, encryption/no plaintext,
grant/revoke/regrant history, failure rollback, migration/check/drift и affected roles.

Предыдущий goal turn — progress: дополнение B07 опубликовано6b7153fc, проверки
пройдены. Новый code gap: role_services create/assign/revoke существуют и проверены,
но отсутствуют management read/API/UI; B08 дополнительно требует основание выдачи/
отзыва, которого пока нет в domain. Это необходимо добавить до write API/UI.
Первый зависимый шаг: owner-only paginated read definitions/members/member context,
повторно используя _owner_context/MedicalRoleAssignment/BusinessRole/BranchAccess.
Чтение не выдаёт клинический доступ, не меняет CRM роли/филиалы; отключённый модуль
и inactive member доступны для последующего отзыва. Чужой tenant/platform/inactive
actor запрещены, актуальная авторизация каждый раз; no-store; строгие параметры.
Skills access/domain/verification применяются: tenant first, thin views, свежие
права, ограниченные страницы, изолированные tests до зависимого UI. UI пока не
меняется. Нет migration/provider/Notification/BusinessEvent/AI effects этого read.
Проверки: owner happy/read pagination/search/empty; member/admin/platform/foreign
denial; owner transfer/deactivation; disabled module/revoked assignment; strict API
и no-store. После domain дополнения — affected tests/check/drift/static; UI отдельно.
Канонический root/current branch6b7153fc сохранены, foreign WIP исходного snapshot
не трогаем (access.md смешанный, при профильной записи stage только свой hunk).
Полное ТЗ остаётся ACTIVE; это подготовка связного сценария, не закрытый M06.

## M06/B07: сведения приглашения, локальная приёмка

Текущая проверка: backend58 PASS до уточнения даты; финальные100 PASS38.772s
после planned_work_date, включая прошедшую дату/accept, старый receipt replay,
crypto/ACL/rollback и migration roundtrip; check/drift PASS. Логи
TEMP/dental-invitation-{date-}20261122.log. Рабочая БД не менялась.
Transport10 PASS. Первая UI-проверка остановилась на i18n: workDirectionHint
содержит медицинский термин в явно медицинском модуле. Добавлен только этот
ключ в существующий exact allowlist; generic-label запрет сохранён,5 tests PASS.
Повтор59598 exit0: i18n/tsc-b/vite PASS, прежний locale chunk warning.
TEMP/dental-invitation-build-retry-20261122.log. Browser39328 exit0:7 PASS3.7m
(source proposal);67395 exit0:8 PASS5.3m(head). Отдельные isolated runtime/DB.
Проверены RU/KK/EN desktop/mobile: новые required поля, calendar keyboard/open/select,
503 сохраняет значения/ключ,409/reload,role revoke403,accept/end/withdraw,
приёмник до accept видит организационные сведения, но clinical workspace403.
Логи TEMP/dental-invitation-{proposal,head}-20261122.log; снимки
output/playwright/medical-invitation-{proposal,head}. Просмотрены6 recovery forms,
6 head forms,recipient RU desktop и outgoing RU mobile: controls/spacing/wrapping
без горизонтального overflow. На mobile длинная recovery форма прокручивается;
нижние действия достижимы и исполнены тестами. Axe в основных сценариях PASS.
80532 exit0:9 PASS5.8m notification projection/reply/recovery/conflict/denial.
TEMP/dental-invitation-notifications-20261122.log. При визуальном просмотре
notice-pending KK обнаружен M12 вместо месяца (Intl long month в Chromium).
Минимальное исправление: locale map и numeric KK month как в существующем
DateRangePicker; добавлен exact rendered date assertion для RU/KK/EN.
73075 exit1: types/build PASS;4 RU/EN browser PASS,2 KK FAIL из-за неверного
ожидания тестом01.12.2026. Реальный Intl numeric kk-KZ даёт2026-12-01, как
существующий CalendarInput/DateRangePicker; M12 устранён. Исправлено только
точное ожидание KK (семантическая дата/полный текст проверяются по-прежнему).
73573 exit0:2 KK PASS2.9m в новом isolated runtime/DB;
TEMP/dental-invitation-date-kk-20261122.log, output/playwright/medical-invitation-date-kk.
Исходный прогон/failed trace сохранены:
output/playwright/medical-invitation-dates, TEMP/dental-invitation-dates-20261122.log.
CI предыдущегоa46f624f45004907944 завершился success, проверено GitHub API.
Static2375 и финальный65410 exit0 PASS на base656dbd19. Итог:24 distinct browser
сценария PASS (7+8+9), после форматирования даты4 RU/EN+2 KK повторно PASS;
это пересекающиеся проверки, не30 различных сценариев.20 затронутых снимков
просмотрены (6 source forms+6 head forms+recipient+outgoing+6 final notice).
Все собственные runners завершены. Остатка в этом дополнении B07 нет; полный
M06/ACL/назначение медицинских ролей и M07 остаются открытыми. Следующий шаг —
read/API/UI назначения ролей поверх существующих role_services; самоназначение
владельца не разрешать без отсутствующего решения.
Полный own diff/new files reviewed; foreign WIP исключён. README/testing не требуют
изменения: запуск прежний. Внешний ТЗv1_2 обновлён локально отдельно от Git.
Опубликовано6b7153fcdb8b58c9039b04ea7aad5ed9bcd1bb2b normal-push origin/main;
remote SHA совпал. Весь исходящий диапазон — один проверенный task-only commit.
30 files425+/20-, STATUS staged только первая строка. Канонический root
C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit сохранены.
CI45007654514 in_progress, не PASS. Working/index/реальный committed-range diff
hygiene PASS. Чужой WIP сохранён, index чист после commit. Deploy/working DB
migrations/внешних сообщений не было. Полная цель ACTIVE; следующий шаг — API/UI
назначений медицинских ролей (существующие domain services уже есть).

Предыдущий turn progress: причина отказа опубликованаa46f624f, локальные проверки
пройдены. Новый gap code: инициатор есть в DTO, но не показан; направление работы
не выделено. Добавляем отдельное encrypted work_direction для организационных
сведений приглашения и read projection внутри текущего ACL; не раскрываем прежнюю
причину передачи или карту. Новое приглашение требует непустого направления;
исторические строки без выдуманного backfill; replay старой команды сохраняется.
Имя инициатора/направление показываются получателю до принятия, в списках и карточке.
Scope: medical model/service/read/API, существующая форма/3 read surfaces,i18n/tests.
Нет нового доступа, Notification PHI, BusinessEvent/AI/provider/working migration.
Владелец ответил async22.11.2026: срок — плановая дата работы без автоматического
отзыва приглашения/доступа. Согласованное ТЗv1_2 §22.7/B07 обновлено на Desktop.
Добавляем planned_work_date, календарную дату без автоматических переходов состояния.
Не вводим запрет прошедших дат или срок ответа/окончания участия.
Skills zani-change-crm-domain,zani-run-verification,frontend и прежний Anti Slop
 during/human/layoutmobile/ui/copywriting: токены/shared controls, видимые labels,
перенос длинных значений, сохранение ввода/retry,focus/disabled/denial. Направление
дизайна прежнее ENERGY1/RHYTHM1/MOTION1. Никаких новых assets/styles.
Проверки: validation/private read/crypto/replay/current ACL/rollback; affected
participation suites+schema roundtrip/check/drift; затем typed API/build/i18n и
head/doctor→recipient реальные desktop/mobile RU/KK/EN, screenshots inspect.
Базаa46f624f, тот же root/branch. Own dirty: только postpush checkpoint/STATUS;
foreign WIP сохранён, не stage целый STATUS. Полное ТЗ/M06 ACTIVE.

## M06/B07: причина отказа, работа

Опубликовано a46f624fc77b0d063b5b3700d73be1a63c47e375 normal-push origin/main;
remote SHA совпал, исходящий диапазон только этот task-owned commit. Канонический
root C:/Users/user/Desktop/PlatformaCRM, branch codex/ui-testing-toolkit сохранены.
CI45004907944 in_progress; предыдущий45003077751 также in_progress. CI PASS не заявлен.
Working/index/real committed-range diff hygiene PASS; полный собственный diff
code/tests/docs и новые файлы просмотрены. Foreign WIP исключён; STATUS staged
только первой строкой. Все локальные runners завершены, рабочих миграций/внешних
сообщений/deploy не было. README/testing без изменений: способ запуска прежний.
Причина отказа в B07 локально принята. Полный B07/M06 НЕ закрыт: в приглашении
ещё надо довести организационные сведения (инициатор уже есть в read DTO, но не
показан, направление работы/срок не оформлены); срок не превращать в автоматический
отзыв доступа без утверждённого правила. Далее продолжить этот разрыв и full ACL/
назначение medical roles, затем M07. Матрица M01–M30 и полное ТЗ остаются ACTIVE.


Текущий срез WIP поверхe4dca5c7, не опубликован. Backend initial16454:67 PASS;
final64661:29 PASS/1 ERROR в старом notice migration test, который обращался к
текущей модели после rollback до0015. Исправлено чтение исторической модели;
retry58571:30 PASS9.845s,check/drift PASS. Логи TEMP/dental-decline-{final,final-retry}-20261122.log.
Source migration test имел тот же current-model шаблон после rollback0014→0015;
исправлен аналогично, без ослабления assertions. Проверка56265 exit0:30 PASS37.793s,check/drift PASS:
tests_participation_decline/services/api/source_migration + check/drift.
В respond сохранён прежний accept payload hash: новый digest только decline;
добавлен replay тест receipt прежней версии. TEMP/dental-decline-compatibility-20261122.log.
UI build68322 exit0:10 transport PASS,7795 i18n keys PASS,tsc-b/vite PASS;
TEMP/dental-decline-ui-build-20261122.log. Transport тест затем дополнен точным
многострочным reason и отдельно10 PASS. Locale chunk warning прежний.
Browser41606 exit0:9 PASS5.1m;6 RU/KK/EN desktop/mobile отказов с реальной командой,
503 mock retry сохраняет текст/ключ; real stale409/reload/revoke403; legacy
workspace decline/withdraw/head-end/conflict и accept long-name regression.
TEMP/dental-decline-browser-20261122.log; output/playwright/medical-decline.
12 новых form/reply снимков RU/KK/EN и2 conflict/denied просмотрены: перенос текста,
кнопки/контраст/фокус/disabled без overflow; axe forms6 PASS. Existing pending и
long-name screenshots без новой геометрии не считаются отдельной новой приёмкой.
Дополнительный browser9843 FAIL:60s total timeout. Trace подтвердил keep/discard/focus;
после18.46s CLI revoke начался submit на границе общего срока, server403 получен.
Assertions не упрощены; total120s как другие revoke scenarios, retry89946 exit0:1 PASS21.1s, screenshot decline-denied просмотрен; PHI очищены.
Итого10 browser сценариев PASS,15 новых снимков просмотрены. Повтор выполнен
после завершения основных проверок, TEMP/dental-decline-denial-retry-20261122.log.
Сценарий: cancellation keep/discard и role revoke после
ввода причины, output/playwright/medical-decline-denial,
TEMP/dental-decline-denial-20261122.log. Продукт после build не менялся; backend
accept hash уточнён отдельно, проверяется56265.
Final static34512 exit0/PASS на текущем backend/UI; TEMP/dental-decline-final-static-20261122.log.
После него только120s harness budget: browser retry и diff hygiene перед публикацией.
Индекс пуст, foreign WIP сохранён.
Delivery gate в изменённом scope: shared controls/tokens и реальный B07 content;
6 form axe PASS;6 viewport/locales и14 новых снимков просмотрены; no new assets,
media,decorations,theme,nav или performance claims (N/A). Enter/submit/required,
retry/key,409/read-only/reload,existing modal и возврат фокуса проверены;
cancel/role-denial final proof PASS89946. Все локальные runners завершены. Build PASS,scope не полный кабинет врача.

Backend16454 exit0:67 tests PASS9.462s,check/drift PASS, isolated_runtime;
TEMP/dental-decline-20261122.log. Migration0017 создана, working DB untouched;
roundtrip проверен последующим58571 (см. выше).
UI продолжение: reused zani-review-frontend + Anti Slop during/human/layoutmobile/
copywriting/ui. Дизайн прежний: shared Textarea/Button/StateViews, ENERGY1/RHYTHM1/
MOTION1; видимая обязательная причина, перенос текста, сохранение ввода при503,
409 требует перечитать, отказ роли очищает PHI; focus/cancel/unsaved guard. Форма
доступна из окна участия и notification page; причина инициатору в текущем read UI.
Проверки UI: types/build/i18n,6 locale/viewport + recovery/conflict/revocation,
снимки получить и просмотреть. Новых assets/styles нет.


Предыдущий turn — progress: e4dca5c7 опубликован, уведомления/UI локально проверены.
Новый gap code по §22.7 правило7: отказ ещё без причины. Добавляем обязательную
причину в существующую respond-команду, encrypted storage и private read только
инициатору в уже разрешённых списках/context. Причина не даёт нового доступа,
не попадает в Notification/audit/idempotency plaintext. Старые declined строки
без причины не заполняем выдуманным текстом. Accept остаётся без причины.
Риски: replay с другим текстом, rollback шифрования/аудита/уведомления, foreign
actor/Business, чтение после отзыва исходного основания. Проверки: новые focused
service/API/read tests, dependent participation suite, migration roundtrip/check/drift;
после backend — существующие UI формы, RU/KK/EN desktop/mobile и recovery/focus.
Skills zani-change-crm-domain/zani-run-verification. Базаe4dca5c7, тот же root/branch,
foreign WIP сохранён. Нет новых BusinessEvent/AI/providers/рабочей миграции.
M06 не закрывать до UI и остальных критериев; всё ТЗ ACTIVE.

## M06: подключение личной ленты

Опубликовано e4dca5c7869d0b7d0ee8ee82d05dcd98582aacf1: normal-push origin/main,
remote SHA совпал. Канонический root C:/Users/user/Desktop/PlatformaCRM,
ветка codex/ui-testing-toolkit. Исходящий диапазон содержал только этот проверенный
коммит; чужие изменения исключены, STATUS staged только первой строкой.
CI45003077751 in_progress, не PASS; предыдущий CI44999695951 success.
Все локальные runners завершены; рабочая БД не мигрировалась. Следующий незакрытый
критерий M06 — B07 обязательная причина отказа: domain/API/read projection/UI/tests.
Всё ТЗ и цель ACTIVE, PG6 skips и остальные строки матрицы не закрыты.


UI продолжение: прежний backend — progress/201 PASS. Новый экран переиспользует
PageHeader/Button/StateViews и существующие ParticipationEntry/SourceProposalEntry;
данные только из private context/access API, без generic CRM permission grant.
Anti Slop during + frontend/human/layoutmobile/copywriting и design-taste (направление
существующего рабочего интерфейса, ENERGY1/RHYTHM1/MOTION1). Применяем: прежние
токены/контролы; перенос длинных имён и кнопок на390px; загрузка/повтор/403/404/409
без старых PHI; клавиатура/фокус после ответа; RU/KK/EN. Никаких новых assets/styles.
Проверки: transport/types/build/i18n и реальный notification→context→respond flow,
изолированный desktop/mobile browser, снимки получить И просмотреть. Объём полного
ТЗ сохраняется; B07 причина отказа остаётся отдельным незакрытым критерием M06.

Текущий результат: backend локально проверен, рабочее дерево поверх8d6a8e36,
UI приёмка пройдена, подготовка публикации. Final runner98541 exit0:207 tests,
201 PASS/6 PostgreSQL-only skips,89.096s; check/drift PASS. Лог
TEMP/dental-participation-notifications-final-20261122.log. Isolated_runtime,
manage.py test apps.medical.tests_participation_notifications
apps.medical.tests_participation_notice_reads apps.medical.tests_participation_notice_migration
apps.medical.tests_participation_source apps.medical.tests_participation_services
apps.medical.tests_participation_closure apps.medical.tests_participation_api
apps.notifications --noinput -v1; затем check; makemigrations --check --dry-run.
Пропуски:3 personal concurrency и3 delivery concurrency требуют PostgreSQL;
не объявлены PASS. Проверены fixed recipient/no owner fallback/preferences,
atomic rollback/replay, current branch/role/module/original basis, foreign/corrupt
source, list/detail/count/open/read/unread/read-all, private audited context API,
пакетные permission queries без N+1 и migration0016 roundtrip без повторной отправки.
Static40979 exit0/PASS с исходной базой656dbd1, лог
TEMP/dental-notifications-static-20261122.log. Все local runners завершены.
Frontend подключён: typed transport, route,6 ключей RU/KK/EN, карточка текущего
участия, ответ и существующие окна. Node transport10 PASS; check:i18n7794 keys PASS;
tsc-b PASS. Runner25474 build PASS; после onClosed refresh повтор21503 build PASS
(TEMP/dental-notifications-final-build-20261122.log), прежнее предупреждение chunks.
Browser6133 exit0:7 PASS,6 locale/viewport flows + negative mobile. Изолированная
БД, реальные команды/права,503 response mock отдельно; stale409/revoke403 реальные.
TEMP/dental-notifications-browser-retry-20261122.log;14 снимков в
output/playwright/medical-notifications-retry получены и визуально просмотрены:
перенос кнопок/текста, читаемость, error/denial, без overflow. Axe6 PASS, keyboard,
focus, no PHI browser storage. Первый runner55921 упал на fixture CSRF до UI;
исправлено получение CSRF перед setup token и очистка cookies, продукт auth не менялся.
Runner41599:2 RU desktop/mobile PASS; дополнительный long-name/close тест FAIL
до действия: одноразовая подстановка имени поглощена повторным context запросом.
Подстановка теперь действует до снимка, затем явно unroute; runner22922 проверяет
этот сценарий отдельно (TEMP/dental-notifications-long-20261122.log):exit0,1 PASS12.7s.
Это не повтор неизменённого failed входа. Новое onClosed обновляет родителя после
ответа внутри существующего окна; приёмка PASS, оба новых снимка просмотрены:
длинное имя переносится на390px, новый статус и видимый focus после закрытия.
Итого8 различных browser сценариев PASS;2 RU повторены после onClosed изменения.
Backend не менялся после201 PASS/6 skips, повтор не требуется. Внешних отправок нет.
Индекс пуст; изменения остаются одним неопубликованным срезом.
Собственные новые файлы: medical/participation_notifications.py,
participation_notice_reads.py, migrations/0016_participation_notice.py и3 tests;
notifications/module_sources.py. Изменены medical apps/models/services/closure/views,
notifications selectors/serializer/views/migration-test, CRM contract/capabilities,
checkpoint и только первая строка STATUS. Foreign WIP не включать в будущий commit.

База8d6a8e36; предыдущий шаг — progress (схема/команды/67 проверок/публикация).
Режим implementation, gap code/UI: источник уже сохранён, уведомления отсутствуют.
Добавляем medical-owned связь Notification с MedicalAuditEvent и адресный producer
в той же транзакции. Общая лента получает нейтральную точку расширения через AppConfig;
медицинские фильтры/проекция остаются в apps.medical. Фиксированный адресат, текущая
роль/филиал/исходное основание до pagination/counts, без owner fallback и PHI.
Повтор команды не создаёт второе уведомление; preferences переиспользуем.
Проверки: event atomicity/replay/preferences, current role/module/branch/source,
foreign/corrupt links, list/detail/count/read-all и существующие notification tests;
check/drift/изолированная миграция. Следом private medical lookup и UI переход,
desktop/mobile/i18n/browser. Пока этого нет, полный M06 не закрывается.
Нет внешних отправок/AI/BusinessEvent/рабочей миграции. Чужие изменения сохраняются.

Focused runner6332 exit0:66 tests PASS14.404s + check/drift. Лог
TEMP/dental-participation-notifications-20261122.log. Затем добавлен private lookup
и его4 проверки, tenant/link corruption и batch query-count тесты; повторная
проверка включает весь apps.notifications и schema roundtrip. Core migration test
теперь восстанавливает исходные leaf migrations, иначе новый зависимый medical
0016 оставался бы снятым после его теста; прежние assertions не ослаблены.
Новая миграция не применялась к рабочей БД. Для запуска обновлённого backend нужна
обычная согласованная процедура миграции; это не её авторизация.
Следующий UI: route /app/medical/participations?notification=<id>, server lookup,
текущая карточка/ответ и переиспользование ParticipationEntry/SourceProposalWorkspace,
6 medical.notifications.* переводов, typed API, desktop/mobile и recovery/403/404/409.
Этот UI подключён выше; здесь сохранено исходное направление работы.
Отдельный незакрытый критерий B07: существующий decline ещё не принимает причину;
это нужно довести в M06, а не считать закрытым наличием уведомления об отказе.
CI747e915/44998314566 и8d6a8e36/44999695951 completed success, проверено GitHub API.
Final static98656 exit0/PASS, TEMP/dental-notifications-final-static-20261122.log.
Рабочий/index/range diff hygiene PASS; весь собственный code/tests/docs diff просмотрен.
README/testing без изменений: setup и запуск fixture не менялись.
Fetch origin/main=8d6a8e36, исходящий диапазон до коммита пуст. Foreign WIP исключён.

## M06: уведомления и исходное основание, текущая работа

Опубликовано8d6a8e365353b4ffe98ceca285be2e96952abf6d normal-push origin/main,
remote SHA совпал. Веткаcodex/ui-testing-toolkit. CI44999695951 in_progress;
зелёный CI не заявлен. В STATUS частично staged только собственная первая строка;
чужие27 строк, как и остальной foreign WIP, сохранены вне коммита. Все локальные
runners завершены. Следующий шаг: medical notification projection/producer/current
access и UI переход; основание теперь доступно без восстановления по догадке.

Режим implementation; gap code. Предыдущий срез747e915 доказал передачу между
филиалами; проверка показала, что исходное основание проверяется командой, но не
сохраняется. Минимальное дополнение: защищённые nullable-ссылки на исходную запись
или участие, без восстановления оснований старых строк по догадке. Они нужны для
повторной проверки доступа к ответу из уведомления; сами по себе прав не дают.
Медруководитель использует собственную филиальную роль, без фиктивного основания.
Переиспользуем доменные команды, medical audit, idempotency и общую личную ленту.
Далее: адресные нейтральные уведомления, текущий ACL до pagination/counts и переход
в существующий UI. M06 остаётся открыт до полного вертикального сценария.
Риск: чужой пациент/Business/автор основания, повтор команды и изменение доступа.
Проверки первого доменного изменения: focused service/storage tests, migration
roundtrip в isolated_runtime, зависимые participation tests, check/drift/diff.
Рабочую БД не мигрируем. Нет новых внешних сообщений, BusinessEvent или AI данных.
Канонический root и ветка прежние; HEAD747e915, чужие изменения не затрагиваются.
Применяется zani-change-crm-domain; UI в этом подшаге не меняется.

Результат: сохранение источника реализовано. Final runner10782 exit0:67 тестов
PASS15.766s, включая7 source tests, migration0014→0015 roundtrip с существующей
строкой, participation services/storage/withdrawal/closure/proposals/API. Команда:
isolated_runtime + manage.py test apps.medical.tests_participation_source
apps.medical.tests_participation_source_migration apps.medical.tests_participation_services
apps.medical.tests_participation_storage apps.medical.tests_participation_withdrawal
apps.medical.tests_participation_closure apps.medical.tests_participation_proposals
apps.medical.tests_participation_api --noinput -v1; затем check и
makemigrations --check --dry-run PASS. Лог TEMP/dental-participation-source-final-20261122.log.
Предварительный runner38422:57 PASS до последней проверки неизменяемости источника;
финальные67 заменяют его границу. Static49885 exit0/PASS, исходная база656dbd1,
TEMP/dental-participation-source-static-20261122.log; working/index diff hygiene PASS.
Это изолированный SQLite, не PostgreSQL/рабочая миграция. UI/API payload не менялись:
browser/build не повторялись, прежний UI PASS не объявляется новой проверкой.
CRM contract/capabilities обновлены; README, паспорт и operations не требуют правок:
новых настроек/способа запуска/границ документа нет, схема отмечена здесь и в CRM.
Все local runners завершены. Для публикации только9 собственных файлов; чужие
password/Google/WhatsApp изменения исключены. Следом реализовать медицинскую
проекцию общей ленты, безопасные нейтральные уведомления и достижимый переход.

Текущая публикация:747e915d24ec5dd005e710b0df643797a2051b92,
feat(medical): enable clinician handoffs across branches, normal-push origin/main;
remote SHA прочитан обратно и совпал. Веткаcodex/ui-testing-toolkit, канонический
C:/Users/user/Desktop/PlatformaCRM. CI44998314566 in_progress, PASS не заявлен.
Все локальные test/build/static runners завершены; ранее опубликованные9990bcbf/
23a007a8 CI success. Этот post-push статус сохранён локально для следующего среза.
Следующее независимое требование M06: внутренние уведомления о приглашении/ответе
и достижимый переход в существующий medical UI без PHI в общих уведомлениях;
сначала проверить текущие notification/BusinessEvent контракты и реализацию.
Полное ТЗ остаётся активным; никаких новых отправок реальным получателям этим
сохранением статуса не разрешено и не выполнено.


## Врачебная передача между филиалами: локальная приёмка, 22.11.2026

Результат: врач из действительной записи или собственного active-участия выбирает
филиал/получателя, отправляет приглашение, видит собственные исходящие и отзывает
pending. Получатель принимает через существующий список; до принятия нет clinical
basis. Исходное назначение/участие не заканчивается автоматически. Прямые API
перепроверяют Business, медицинскую роль, исходное основание, целевого получателя
и филиальные права; чтения no-store с атомарным аудитом. Новых миграций нет.

Проверено на базе23a007a8 плюс собственный diff:
- 82 backend PASS:54 focused и28 API/responsible/closure dependent; check и
 migration drift PASS. Логи/runner IDs ниже. SQLite; PostgreSQL не заявлен.
- 14 node transport/terminology PASS, i18n7788 PASS. После исправления focus:
 tsc-b + app build PASS, runner23825, TEMP/dental-proposal-final-build-20261122.log.
 Неизменный widget использует прежний PASS; live/provider проверки не запускались.
- 6 основных RU/KK/EN desktop/mobile сценариев PASS:4 RU/KK в runner87957,
 TEMP/dental-proposal-browser-focus-20261122.log;2 EN в runner39499,
 TEMP/dental-proposal-browser-en-recovery-20261122.log. Эти два запуска в целом
 не PASS: первый остановился на неоднозначном EN locator, второй — на выборе
 двух dialog для screenshot последнего recovery-теста. Продуктовый код после
 успешных6 сценариев не менялся; locator уточнён по имени поля/окна.
- Заключительный mobile loading/read503/retry/create409/withdraw409/role403 PASS:
 runner86823 exit0,1 test(3.9m), TEMP/dental-proposal-final-recovery-20261122.log.
- Регрессия: клинический черновик/история/unsaved desktop и participation mobile
 decline/withdraw/head conflict/revocation,2 PASS(4.9m), runner49254 exit0,
 TEMP/dental-proposal-existing-regression-20261122.log.
- Все 12 новых снимков формы/исходящих RU/KK/EN desktop/mobile и2 итоговых mobile
 conflict/denial получены и визуально просмотрены. Источники: output/playwright/
 proposal-workspace-focus, proposal-workspace-en-recovery и proposal-final-recovery.
 Геометрия/переносы/состояния/primary44px, ввод, keyboard focus и axe AA проверены
 в соответствующих случаях; tablet/zoom/physical mobile/full S13 не сертифицированы.

Исправлен реальный focus defect: refresh теперь убирает прежнюю страницу до layout
focus; целевая кнопка фокусируется после новых данных и не исчезает сразу после этого.
Test fixture fixes не ослабляют DB constraints; историю не переписываем в общий PASS.
Общий Playwright ошибочно собирал21 медицинский сценарий с generic fixture:
диагностика71138 подтвердила. Default config теперь исключает medical-*.spec.ts,
специализированные configs сохраняют весь набор. Проверка collection0 и успешный
специализированный запуск входят в86823. Инструкция в testing.md обновлена.

Static39923 PASS(base656dbd1), TEMP/dental-proposal-static-retry-20261122.log.
Первая попытка была отклонена из-за base=HEAD23a007a8; исправлен аргумент на исходную
зафиксированную базу задачи, не изменены правила проверки. Завершающий static32666 PASS, TEMP/dental-proposal-final-static-20261122.log;
working/index hygiene PASS, состав24 собственных файлов просмотрен. Чужие
password/Google/WhatsApp изменения исключены. Commit/push выполняются после этой записи. Сервер9990bcbf и сохранённый
UI23a007a8 уже имеют completed/success CI44994844553/44995519658.
Остаток: уведомления/достижимые переходы, полный ACL/назначение роли, остальные
M06/M07 и M01–M30/E0–E7, PG и внешняя приёмка. Согласованные19 направлений в §22.8–22.9
действующего desktop ТЗ сохранены; внешние подтверждения не получены автоматически.
README/operations не меняются этим срезом: настройки продукта и эксплуатация без
дельты, рабочая БД и внешние каналы не затронуты. Активных local runner после86823 нет.


## Врачебная передача: связный сценарий M06, 22.11.2026

База23a007a82ae857ccbd48fe18f157d450a3a105cb опубликована normal-push,
remote SHA совпал. Предыдущие UI/evidence сохранены; цель полная, не закрыта.
Пробел code/UI: врач не может выбрать межфилиальную цель и просмотреть свои
отправленные предложения через интерфейс. Существующие propose/respond/withdraw,
кандидаты, основания appointment/participation и аудит переиспользуются.
Добавить source-scoped список активных филиалов и собственных предложений по
пациенту: действующее основание врача проверяется каждый раз; у медруководителя
сохраняется область филиалов. Выбор филиала не даёт доступ к его пациентам/истории.
Чужие предложения, причины, ИИН и клиническое содержимое не раскрываются.
Затем подключить форму/отправленные предложения из приёма и активного участия,
сохранить стабильный ключ повторов, ввод, текущую роль, фокус и существующий UI.
Никаких рабочих миграций/уведомлений внешним получателям этим срезом.

Срез проверки:54 backend PASS(2.986s), check/migration drift PASS,
runner75333, TEMP/dental-proposal-workspace-backend-retry-20261122.log.
Первый запуск49299: одна неверная fixture branch grant и незаполненный closed_by
для ended нарушали ограничения; исправлены только fixtures, ожидания сохранены.
Affected API/responsible/closure:28 PASS(4.448s), runner83125 exit0,
TEMP/dental-proposal-dependent-backend-20261122.log. Node14 PASS,
i18n7788 PASS, tsc-b PASS(runner16356). App build PASS(runner78857),
TEMP/dental-proposal-build-20261122.log; неизменный widget не пересобирался.
Первый browser82768 остановлен test timeout: точный accessible name Select
содержит также выбранное значение. Снимок просмотрен; поле было на странице.
Исправлен locator без изменения UI или ослабления сценария; retry12869 запущен.
Новый browser/visual PASS ещё не заявлен. Последние проверенные CI двух commits
44994844553/44995519658 in_progress, общий CI PASS не заявлен.

Риск: tenant/branch/basis revocation, раскрытие пациента, повтор команды.
Проверки сначала server: оба основания, head/owner/foreign, отмена/отзыв,
пагинация, atomic audit failure, strict/private HTTP и регрессия participation.
Затем transport/types/build и реальные RU/KK/EN desktop/mobile действия,
retry/conflict/denial/dirty/focus с визуальным просмотром снимков.
UI skills сохраняются: Anti Slop during, shared tokens/Modal/Select/StateViews,
минимум44px для основных touch-действий, сохранение вводимых данных и keyboard focus.


## Сохранение проверенных медицинских интерфейсов, 22.11.2026

Предыдущий goal-turn: прогресс — §22.8–22.9 действующего ТЗ и этот checkpoint
обновлены по 19 направлениям, отдельно сохранены внешние подтверждения.
Текущий контракт: сохранить собственные ранее реализованные и проверенные
patient/representative/clinical/history/tooth/participation интерфейсы, их API,
переводы RU/KK/EN, изолированные browser fixtures/tests и frontend-контракт.
Не менять поведение при сохранении; не включать чужой auth/WhatsApp/Google WIP.
Переиспользуются опубликованный сервер9990bcbf, shared UI и существующие входы
ClientWorkspace/Calendar. Полная медицинская UI-приёмка остаётся открытой.

Доказательства повторно сверены: participation spacing browser2 PASS(2.3m),
reception regression2 PASS(1.6m), полные ранее указанные RU/KK/EN desktop/mobile
проверки/визуальный просмотр и recovery/denial evidence сохраняются. Изменения
после этих проверок затрагивали серверные документы и фиксацию, не UI-код.
Новая публикация не основание повторять неизменённые дорогостоящие проверки.
Проверить перед commit: состав новых файлов/всего собственного diff, imports,
переводы, intended index и hygiene. Секреты/реальные пациенты в fixtures запрещены.
Static gate(base656dbd1) PASS, runner76160 exit0; лог TEMP/dental-ui-preservation-static-20261122.log.
Staged относительные imports PASS после нормализации ../ путей в проверяющем скрипте;
первая проверка ошибочно передавала ненормализованный путь в git cat-file, код не менялся.
Рабочий/index diff hygiene PASS. Повторно просмотрены входы, participation формы,
API и синтетические runtime guards; остальные ранее просмотренные медицинские файлы
сохраняются без изменений с их локальными проверками.
Внешний ТЗ остаётся desktop-файлом; Git сохраняет ссылку и журнал решений,
не создаётся конкурирующая копия ТЗ. CI сервера44994844553 наблюдался in_progress.


## Подготовка запуска: 19 направлений согласованы, 22.11.2026

По переданному поручению владельца актуальное ТЗ v1.2 дополнено §22.8
(L01–L19, все 19 направлений) и §22.9 (только неполученные решения владельца,
материалы клиник и внешние подтверждения). Источник:
[C:/Users/user/Desktop/PLATFORMA_CRM_DENTAL_TECH_SPEC_v1_2_2026-11-22.md](C:/Users/user/Desktop/PLATFORMA_CRM_DENTAL_TECH_SPEC_v1_2_2026-11-22.md).
Каждая строка связывает M/E, конкретный блокируемый сценарий, независимую работу
и доказательство закрытия. Согласованы подготовительные направления, не конкретные
люди/клиники/провайдеры, не нормативный PASS и не реальные операции.
Медицинскую/нормативную проверку теперь организуем параллельно разработке;
назначения и заключения ещё не получены. Остальные ранее отложенные внешние
результаты не объявлены закрытыми. Все D01–D12/B01–B28/M01–M30/E0–E7 сохраняются.

Контракт этой правки: docs-only; прежнее согласование → поручение по 19 направлениям
→ дополнение существующего ТЗ и ссылки в единой матрице. Не создаётся отдельный
backlog. Проверки: полнота 19 направлений и внешних строк, соответствие M/E,
согласованность статуса, отсутствие whitespace-ошибок. Приложение/БД не изменяются
этой правкой; backend/UI проверки повторно только из-за Markdown не запускаются.

Актуальный Git-результат: сервер и контракты сохранены commit
9990bcbf1df299d0796b2bac000242a8a6ba5565 и normal-push в origin/main;
remote SHA прочитан обратно и совпал. Проверено 540 серверных тестов,
check/migration drift/static PASS в указанной ниже изолированной среде.
Это не завершение всего ТЗ: медицинский UI остаётся локальным WIP, PostgreSQL,
полные сквозные сценарии и внешняя приёмка открыты. CI этого commit пока не подтверждён.
Разрешённое удаление только последней пустой строки foreign evidence выполнено;
его содержимое и остальные чужие правки сохранены, файл не включён в наш commit.
Следующий независимый шаг: сохранить проверенный UI, продолжить врачебную
инициативу передачи и доступ между филиалами по существующему контракту.


## Сохранение медицинского сервера и контрактов, 22.11.2026

Серверный набор подготовлен поверх c5799198: PatientProfile/представители,
медицинские роли и отдельные основания записи/участия, клиническая карта/черновики,
история/одонтограмма, API с tenant/branch/role проверками, private/no-store,
зашифрованные версии, idempotency и атомарный аудит. Связи с ядром защищают историю
Client и назначений; общий владелец/поддержка не получают медицинского доступа.
Состав включает14 последовательных миграций medical без backfill/активации v2.
К рабочей БД они не применялись. UI исходники не входят в этот серверный commit;
описанные в контрактах UI проверки относятся к локальному WIP и своим evidence.

Завершён просмотр исполняемых сервисов/selectors/API, криптографии, моделей,
core hooks и всей цепочки миграций; состав тестов сопоставлен с ранее проверенными
сценариями, дополнительно просмотрены migration roundtrip, Client guards и role
commands. Нет изменений тестируемого кода после540 PASS. Старые неверные утверждения
об отсутствии уже подключённых clinical/representative/tooth UI исправлены в
access/crm/operations/capabilities; незавершённые пути не объявлены готовыми.
В смешанных документах/serializers выделены свои hunks; foreign password/Google
правки и остальные чужие файлы не включены. AST/import closure и staged hygiene PASS.

Проверки: manage.py check; makemigrations --check --dry-run; manage.py test
apps.medical apps.businesses.tests_access apps.clients.tests --noinput -v1:
540 PASS,171.278s, isolated SQLite, runner23872 exit0.
Лог TEMP/dental-server-preservation-20261122.log. Static runner с base
656dbd19318b6e146dbc0026afd1727fa719c14e PASS, runner75585 exit0,
лог TEMP/dental-server-static-20261122.log. Повтор backend после docs-only сверки
не требуется. PostgreSQL concurrency, полная приёмка и внешние протоколы открыты.

Предыдущие три собственных commits доc5799198 опубликованы в main после разрешённого
удаления единственной пустой строки чужого evidence. Последняя проверка CI44993838546:
frontend success, backend in_progress; общий PASS не заявлен. Сервер опубликован как
9990bcbf; следующий шаг —
сохранение локально проверенного UI, затем врачебная
инициатива передачи между филиалами. Полная M01–M30 цель остаётся активной.

## Проверка медицинского серверного набора, 22.11.2026

После публикации c5799198 собран в index собственный серверный набор:110 файлов,
apps/medical и связи с Business/Client/config, без password WIP. Staged syntax,
absolute local import closure и diff hygiene PASS. Полный заключительный просмотр
накопленного diff ещё не закончен: набор не закоммичен и не опубликован.
Повторно просмотрены core hooks, models, audit, identity_crypto, role_access,
appointment_access, participation_access, role_services, record_services,
patient_services, identity_verification, identity_corrections, views/serializers,
encounter_services/content и tooth_content. Остальные ранее созданные services,
selectors/API, migrations и tests требуют завершения просмотра состава перед commit.

Текущий server/dependent gate: isolated_runtime; manage.py check и
makemigrations --check --dry-run PASS; manage.py test apps.medical
apps.businesses.tests_access apps.clients.tests --noinput -v1:540 PASS,171.278s,
runner23872 exit0. Лог TEMP/dental-server-preservation-20261122.log.
Это SQLite и выбранные зависимости, не полная PostgreSQL/production приёмка.
Runner80301 syntax/import closure также завершён exit0. Живых локальных runners
этого продолжения больше нет; внешняя CI имеет отдельный статус выше.

В operations исправлены два устаревших утверждения об отсутствии UI участия и
одонтограммы; foreign Google-раздел не тронут. Эти документационные изменения
ещё WIP. Следующий шаг — завершить review серверного набора, сохранить его с
профильными контрактами/evidence, затем сохранить проверенный UI и продолжить
передачу, инициируемую врачом. Полный объём M01–M30 не сокращён.

## Сохранение профильного механизма, 22.11.2026

Сохранено локальным commit c57991981d36872cf6bdc13a6c9789ade3530a42.
Committed-range hygiene PASS. После fetch origin/main диапазон 0 behind/3 ahead,
все три коммита собственные; foreign outgoing commits отсутствуют.
После точечного разрешения владельца удалена только последняя пустая строка
чужого google-button-design evidence (CRLF после строки с LF; остальные байты
сохранены). Static runner --base-ref 656dbd19318b6e146dbc0026afd1727fa719c14e PASS,
лог TEMP/dental-publication-static-20261122.log, runner49866 exit0.
Normal push HEAD:main выполнен; ls-remote подтвердил c57991981d36872cf6bdc13a6c9789ade3530a42.
GitHub API: CI44993838546 in_progress, conclusion=null (не PASS).
https://github.com/999MAX20/PlatformaCRM/actions/runs/44993838546
Сама чужая документация не staged/committed; медицинский server/UI WIP не опубликован.

Предыдущий ответ владельцу о состоянии плана не менял реализацию. Следующее
продолжение проверило текущий Git и сохранило связный профильный набор поверх
05ed9ebb: nullable профиль/ограничение БД, реестр и resolver, общий initializer,
все пять путей создания, запрет смены профиля обычными настройками, enforcement
планов и их платежей. Это сохранение ранее реализованного, без переписывания.
Медицинский домен и интерфейс остаются отдельным WIP; D02 rollout не выполнен.

Состав проверен целиком; в смешанных serializers/views подготовлены только
профильные hunks. Чужие password-правки и медицинские role guards не включены.
AST синтаксис и наличие абсолютных локальных imports в Git index PASS;
staged diff hygiene PASS. Секреты и реальные данные в набор не добавлены.

Новая проверка текущего рабочего дерева (не отдельного checkout): isolated_runtime,
check и makemigrations --check --dry-run PASS; 123 теста, 121 PASS/2 PostgreSQL-only
SKIP, 39.751s, runner46188 exit0. Команда manage.py test --noinput -v1 с labels:
apps.businesses.tests_profiles, tests_profile_initialization, tests_profile_writes,
tests_profile_plan_access, tests_medical_capabilities, tests_activation (все с
префиксом apps.businesses); apps.accounts.tests_google_auth,
apps.accounts.tests_legal_documents; apps.payments.tests_plan_payments;
apps.core.tests_b301_performance, apps.core.tests_b5_performance.
Лог: C:/Users/user/AppData/Local/Temp/dental-profile-preservation-20261122.log.
SQLite не доказывает PostgreSQL-конкурентность. Рабочая БД не изменялась.
UI не менялся в этом сохранении; существующие UI evidence не расширены.

Полный working diff hygiene вновь FAIL только на чужом
docs/testing/evidence/google-button-design-20261119.md:41 (blank EOF).
Этот прежний блокер снят последующим разрешением владельца и точечной правкой;
результат публикации указан в начале этого раздела.
Все запущенные здесь проверки завершены. Следующий шаг: сохранить связный
медицинский сервер/UI набор, затем сценарий передачи от врача между филиалами.
Вся M01–M30 матрица и исходная полная цель остаются открыты в прежнем объёме.

## Текущий результат: участие врача через интерфейс, 22.11.2026

Локально реализован и проверен сквозной сценарий: медруководитель открывает
«Участники лечения» в карточке клиента, приглашает врача; врач открывает свои
участия из календаря, принимает/отклоняет приглашение и читает историю по активному
участию; медруководитель завершает участие с причиной и ответственным. После
завершения сервер отклоняет чтение по этому основанию. Независимая действующая
запись не отменяется и остаётся отдельным основанием согласно ранее проверенному
доменному контракту. Отзыв приглашения также доступен медруководителю.

План обновлён: ниже закреплены все шесть правил владельца, сохранены M01–M30 и
разделены сервер/API/UI/доказательства/конкретный остаток. Исходный objective не
переписан. Полная цель ACTIVE; M06/M07/M24 остаются частичными, этот результат
не закрывает весь кабинет врача, нормативную/инфраструктурную приёмку или ТЗ.

Проверки текущего результата:

- Backend:73 affected participation tests, check/drift PASS, SQLite isolated DB;
  %TEMP%/dental-participation-final-backend-20261122.log (84494 exit0).
- UI:7 сценариев PASS3.3m — все RU/KK/EN desktop1440/mobile390 плюс mobile
  decline/withdraw/реальный stale409/реальный role revoke403; dirty Escape,
  восстановление503 с тем же ключом и причиной, история до/после принятия,
  отказ после закрытия, focus return, отсутствие причины в browser storage;
  %TEMP%/dental-participation-browser-focus-20261122.log (58989 exit0).
- Loading/read503/retry/правдивый empty state:1 отдельный сценарий PASS1.8m;
  %TEMP%/dental-participation-browser-list-20261122.log (45750 exit0).
- Визуальный осмотр выявил слипшиеся кнопки в mobile409: добавлен shared gap2/
  одинаковая высота. После этой единственной layout-дельты повторены en mobile
  lifecycle + negative mobile:2 PASS2.3m;
  %TEMP%/dental-participation-browser-spacing-20261122.log (79501 exit0).
- Регрессия изменённого PatientAdministrationPanel: прежние reception recovery
  и representative mobile boundary/revocation:2 PASS1.6m;
  %TEMP%/dental-participation-reception-regression-20261122.log (70616 exit0).
- Последние types/app build PASS после layout-правки (76996 exit0);
  %TEMP%/dental-participation-spacing-app-build-20261122.log. Widget build PASS
  (56494 exit0), последующие изменения не затрагивают widget imports/entry.
  Node transport8 + industry5 PASS, i18n parity7786 PASS. Warning chunks>500k
  не является подтверждением достижения D12; нагрузочная приёмка остаётся открытой.

Снимки получены И просмотрены: invitation/closure-recovery для6 локаль/viewport
в output/playwright/participation-focus (RU desktop эквивалентный снимок из
participation-final также просмотрен); mobile conflict/denied; list error/empty
в participation-list; исправленные closure/conflict в participation-spacing;
reception/representative denial в participation-reception-regression. Изменённые
кнопки больше не соприкасаются, текст/контролы помещаются, длинный список скроллится.
UI gate в этом сценарии: geometry PASS, purpose PASS (данные/формы/действия/ошибки),
behavior PASS, keyboard/focus PASS, localized desktop/mobile PASS; axe AA checks
формы завершения PASS. Shared tokens/components сохранены. Новые assets/motion/
themes N/A; tablet/zoom/физические устройства и полная библиотека экранов не сертифицированы.
SQLite и последовательные конкурирующие запросы не доказывают PostgreSQL races.

Git: typed transport+tests сохранены в05ed9ebb10ada25d27c562413b311c3366429b04;
профильный механизм и плановые gates сохранены вc5799198.
Остальная медицинская серверная/UI/docs работа пока WIP. Нужен полный review
собственного связного diff/зависимостей и следующие проверенные commits перед
заявлением о сохранении всего сценария. Ранее выявленный foreign EOF41 исправлен
только после явного разрешения владельца; остальные байты чужого файла сохранены.
Три собственных коммита опубликованы до c5799198; server/UI WIP остаётся локальным.
Working DB, внешние отправки и deployment не менялись.
Все запущенные в этом продолжении runners terminal. Следующее независимое действие:
сохранение проверенного собственного сервер/UI комплекта с зависимостями, затем
достижимая передача, инициируемая врачом, включая другой филиал. Ordinary end,
24h corrections, команда/поддержка, уведомления, полный S01/S13 navigation/design
и остальные строки полного ТЗ не исключены из объёма.

## Актуальный порядок выполнения после возобновления 22.11.2026

Это порядок исполнения существующей матрицы M01–M30, а не второй backlog.
Источник: согласованная Desktop v1.2 от22.11, D01–D12, B01–B28, §22.2–22.9,
DESIGN_SPEC. Новое поручение владельца: закончить текущий сценарий, затем вести
один этап до приёмки. Все строки матрицы, отрицательные сценарии и внешние
обязательства сохраняются. Таблица ниже группирует остаток; подробные требования
и старые доказательства остаются в своих строках M и исторических записях.

Статус: К00 принят/опубликован be235444; К01 следующий активный этап.
Остальные К02–К18 запланированы, не объявлены выполненными. Зависимость означает
необходимый результат, а не обязательный повтор всей проверки её реализации.
При внешнем блокере этап сохраняет незакрытые критерии и точный L-ID; выбирается
следующий независимый этап. Нет параллельной реализации и неявных разрешений
на production/рабочие БД/покупки/сообщения пациентам.

Общая приёмка каждого этапа: законченный достижимый сценарий с серверными
инвариантами, текущими ACL/Business/филиалами, API, аудитом, обработкой ошибок,
идемпотентностью/revision там, где применимо; desktop/mobile RU/KK/EN, loading/
empty/error/recovery, сохранение ввода и клавиатура. Focused backend после связной
операции, affected suites/check/drift при завершении backend; build/types и
браузерные действия/визуально просмотренные снимки для изменённого UI. PG нужен
для доказательства гонок. Документация/паспорт/матрица, reviewed commit/normal
push и фактический CI учитываются отдельно. Mock не закрывает реальный provider.
Повторяем неизменённые проверки только при изменении входов/дефекте/новом риске;
полная регрессия остаётся на К18, а не запускается после каждого коммита.

| Этап и пользовательский результат | Требования и зависимости | Уже готово / переиспользуем | Конкретный остаток | Дополнительные проверки и критерий завершения |
| --- | --- | --- | --- | --- |
| К00. Автор задаёт классификацию шаблона, руководитель видит её при рассмотрении | M11/M24/M25; E3; D06 | Версии, утверждение, editor, Service, typed API | Остатка этого сценария нет; template search не входит в его закрытие |26 API +20 browser,102 снимка, final build/static PASS; опубликован be235444. Полный M11 открыт |
| К01. Медруководитель подтверждает реквизиты клиники и врача; врач читает свои сведения | M11 §5.2–5.3, M02/M24/M25; E3; существующие medical role guards | CredentialProfile/Revision, encrypted history, Business/Member и shared forms; storage64 dependent PASS | В принятом сценарии остатка нет; подтверждение/API/UI/история/schema4 готовы; опубликован fff0555c |105 affected/dependent +1 migration roundtrip,8 credential browser +1 template regression,43 снимка,build/types/static PASS; собственная роль/head scope/tenant/stale/replay/audit rollback проверены. Госреестр и нормативная достаточность отдельно |
| К02. Врач находит подходящий утверждённый шаблон; руководитель управляет его применимостью | M11/M16, D06/D09; E3/E4; К00 | Personal/common drafts/review/history, классификация и approved selector; поиск/фильтры, head pause/resume, encrypted история и UI реализованы | Код/пользовательский сценарий локально принят, остатка в этой границе нет; опубликован096cd591, CI45068261530 выполняется. CI fixture regression20 PASS/static PASS. Полные M11/M16 не закрываются этим этапом | Domain/API/migration/check/drift,12 distinct browser RU/KK/EN ×desktop/mobile +4 повтора, affected visual и final build PASS. Чужое/неутверждённое скрыто, paused create409, старый документ неизменен; p95/PG отдельно К17/К18. Точные доказательства в начале checkpoint |
| К03. Новая и существующая стоматология получает модуль без сброса CRM | M01/M02; D01/D02/D03,B22; E0/E1 | Profile registry/resolver/guards/create paths, BusinessCapability, role settings; release-ready v2 и additive CLI реализованы, PG domain/concurrency10 PASS +API2 PASS | Переход опубликован3de53af2,6 browser/visual и static PASS; весь К03 открыт: owner-clinician ждёт решения. Защита новых jobs/files/AI остаётся обязательной в К07/К15; B22 новые настройки в К14, существующие false сохраняются здесь | Повтор backfill ничего не сбрасывает, IDs/настройки/не-стоматология сохранены, нет owner/platform bypass, изолированные миграции и PG; пользователь видит правильные доступные инструменты |
| К04. Ресепшн находит пациента и безопасно оформляет личность/представителя/исправление | M03/M04/M05; D04,D07,B01–04,B26; E1; К03 | ClientWorkspace, identity/representatives/merge guard; К04 поиск, atomic registration и ИИН correction/head review: backend/PG/browser/build PASS | Reception list projection backend5/browser6/build PASS; перепривязка/разбор смешанных историй ждёт решения. Клинические вкладки К05/К06, recipient enforcement К12; L04 внешний протокол. Search/registration/IIN опубликованыe5546ea8; projection8f93c194 опубликован, CI success | Семейный телефон не объединяет пациентов; verified ИИН PG race, foreign/отзыв/возрастные сценарии, атомарный отказ merge; оформленный пациент доступен для приёма. Реальный протокол личности L04 остаётся отдельной приёмкой |
| К05 WAITING owner decisions. Врач получает доступ по записи/передаче, команда и исправления имеют точные границы | M02/M06/M07; D03,B05–08,B28; E1/E2; К03/К04 | Appointment basis, invitations/transfer/notifications/head-end, role UI;24h correction request/review/target-only draft/close/expiry с domain/API/PG/browser evidence выше | Комбинация appointment/participation/correction и security override6 focused PASS; командный ассистент ждёт назначения/подтверждения, support-инцидент≤4h readonly и проекции будущих files/export/AI consumers открыты; подписанная коррекция в К08/К09 | Нет доступа до принятия; запись сразу даёт основание; отзыв сильнее temporary; два основания независимы; запрещённые подпись/export/изменение отсутствуют и на API. Обычное завершение с полной проверкой обязательств закреплено за К11 |
| К06 ACTIVE. Врач ведёт карту, зубы, назначения и клинический план лечения | M08/M09/M10/M16; D05/D09; E2/E4; К04/К05 | Encounter draft/history, odontogram/surfaces, VisitPlan/Step, шаблоны; аллергии/противопоказания и явная неприменимость с причиной, snapshot/template/correction и scoped acceptance выше; отдельные черновики назначений/версии/API/UI и structured clinical steps/history/correction приняты локально | Связи клинических шагов с VisitPlan/зубами, явное преобразование, snippets/утверждённые шаблоны для назначений, связи зубов/плана, остальные вкладки и доступ команды | Врач сохраняет и перечитывает историю целого приёма/плана/назначений; клинический план не создаёт долг/бронь, stale/tenant/replay/PG. Снимки подключаются К07, финальное завершение К10; справочник L12 |
| К07. Врач безопасно прикрепляет и просматривает снимки/файлы | M09/M13; D07; E2/E3; К05/К06 | Private storage и crypto/audit, связи карты | Карантин/MIME/антивирус, preview/original ACL, связи с зубами/приёмом, история, отказ сканера, резервный защищённый read audit | Заражённое/непроверенное не открывается, URL не обходит ACL, отмена/повтор/tenant/прямое скачивание; разрешённый файл проходит загрузку→проверку→просмотр. Реальные форматы L12 и retention L08 остаются открытыми |
| К08. Врач оформляет неизменяемую версию документа и печатает её | M11/M13; D06/D07; E3; К01/К02/К06/К07 | Document drafts/history/preview, source digest, template versions | Матрица обязательности/момента/подписантов, утверждение документа, PDF/логотип bytes/checksum, ограниченный DOCX/печать, исправления отдельной версией | Изменение профиля/клиники/шаблона не меняет прежний PDF; нет stale-source/HTML исполнения; точные bytes/версия в UI; документ не называется подписанным без К09. Реальные формы L05 |
| К09. Подписант подписывает нужную версию на desktop/Android/iPhone | M12/M11; D06; E3; К08 | Версии документов/ACL, provider adapter patterns | Signature intent/states, provider adapter, сертификат/валидность, несколько подписантов, retry/cancel/late callback, рабочий UI на трёх платформах | Реальный полный цикл, в том числе на одном телефоне; callback replay/отмена не финализирует; точная версия неизменна. L06: без провайдера/условий/доступов этап не закрыт, локальные контракты не подменяют реальную подпись |
| К10. Врач завершает обычный/частичный или внеплановый приём | M08/M11; D05/D06,B09–11; E2/E3; К06/К08/К09 для обязательной ЭЦП | Encounter/Appointment, существующие деньги и draft UI | Полнота разделов/документов/подписей, walk-in/раннее оформление, атомарное завершение календаря/финансов, отмена/восстановление | Неоплата не запрещает помощь; PG гонка/replay ровно один денежный переход; provider вне транзакции денег; пользователь получает согласованный результат и историю |
| К11. Врач завершает участие, передав оставшиеся обязательства | M07/M06; D03,B05–08; E2; К05/К10 | Own-end domain44 PASS, head-end API/UI и responsible selector | Полный перечень обязательств документов/приёмов/будущих записей, HTTP/UI собственного завершения, передача ответственному и связь с24h correction | Нельзя потерять незакрытую обязанность, нельзя автоматически переназначить чужую работу, независимое основание сохраняется; завершение и дальнейший доступ проверены сквозным сценарием |
| К12. Пациент/представитель получает документы по коду и уведомлению | M14/M15/M03; D08,B12–19; E7; К04/К08/К09/К07 | WhatsApp adapter, контакты CRM, private versions | Grant/hash/session/лимиты,72h, комплект/готовность, повтор/новая вкладка/отзыв/перевыдача, исправления, recipient enforcement, outbox и отдельные delivery/read/doc-open | Семейный телефон не является личностью; смена телефона не переносит grant; PHI/секрет не URL/log/Meta, повтор не дублирует выдачу. L09/L10 для реальной дистанционной выдачи/отправки; хранение не истекает вместе с кодом |
| К13. Врач поручает повторную запись, ресепшн доводит её до результата | M18/M19; D10,B20–21; E5; К04/К05/К06 | Calendar booking/permissions, tasks/notifications/branches | Очередь/claim/book-link, прямая запись при праве,5/30 рабочих минут, эскалация/смены/попытки/2дня/reopen | PG один claim/одна бронь, часы/праздники/нет замены, отказ≠не связались; врач видит реальный результат. UI обновление p95≤5с измеряется К17; L18 для реальной смены |
| К14. Врач заявляет материалы, ответственный закупает и закрывает остаток | M21/M22/M23; D11,B22–25; E6; К03, popup после К10 | Общие задачи/уведомления/сотрудники, существующие настройки | Одна форма/два входа, одноразовый post-completion popup, batch совместимых строк, approval/order/partial receive/substitute/return/остаток | Явный false не сброшен, нет PHI, PG/replay не дублирует popup/получение; существенные изменения повторно согласованы; инициатор/руководитель подтверждает остаток |
| К15. Врач использует AI/диктовку; бот отвечает только проверенному получателю | M17/M20; D09; E4/E7; К05/К06/К12 для бота | Общие AI runtime/provider adapters, ручной ввод | Минимальный разрешённый контекст, Tab/Esc/mobile accept, текущая форма/поле, stale guard, аудиополитика, проверка личности канала, аудит | Отзыв/смена пациента/версии не перезаписывает ввод, ручной процесс работает без AI; RU/KK зубы/числа/отрицания/дозы и живой звук. L14/L15 для внешних данных и клинической приёмки |
| К16. Клиника выгружает полную историю и завершает обслуживание без потери документов | M29/M04/M13; B26–27; E7; К07–К09/К12 | История/версии/ACL/private files | Читаемые+структурные данные/файлы/авторы/подписи/связи, полнота архива, доступ к прежней истории без обязательного импорта | Выгрузка читается вне CRM и сверяется с источником; tenant/role/отзыв, расторжение не удаляет автоматически; договорный срок L03/L17 |
| К17. Оператор восстанавливает систему и подтверждает скорость/размещение | M13/M26/M27/M28; D01/D07/D12; E0/E7; готовые функциональные этапы | Yandex Cloud KZ как согласованное направление, existing ops/monitoring | Retention/legal hold/rotation, независимые копии, restore/runbook/alerts, конфигурация KZ, нагрузочный профиль2→5 клиник, нормативные/обменные подключения по применимости | Измеренные RPO15мин/RTO4ч, p95 card/search/save2с/PDF15с/queue5с с ошибками; версии/подписи/audit сохранены. L01–L03/L07/L08/L11/L13/L16/L18; разрешение целевой среды обязательно |
| К18. Полный сценарий ТЗ проходит итоговую приёмку | M24/M25/M26/M30 и все M01–M29; E0–E7; предыдущие этапы и обязательные L | Сохранённые scoped PASS, единый дизайн и typed API | Оставшиеся экраны/вкладки/21 окно, общие API/events/проекции, итоговый full gate на точном кандидате, PG/мобильная/не-dentistry/финансовая регрессия, согласование docs/паспортов/матрицы | Все исходные требования имеют прямые доказательства; нет скрытых mock/пропусков, реальные обязательные интеграции приняты; L19 для пилота/deployment, без него не заявлять запуск |

Покрытие: M01→К03; M02→К03/К05; M03→К04/К12; M04→К04/К16;
M05→К04; M06→К05/К11; M07→К05/К11; M08→К06/К10; M09→К06/К07;
M10→К06; M11→К00/К01/К02/К08/К09/К10; M12→К09; M13→К07/К08/К16/К17;
M14–M15→К12; M16→К02/К06; M17→К15; M18–M19→К13; M20→К15;
M21–M23→К14; M24–M25→каждый этап иК18; M26→проверки каждого этапа/К17/К18;
M27–M28→К17/К18; M29→К16; M30→К18. Все Q/B/D остаются у исходных строк M;
никакое групповое закрытие К не закрывает оставшиеся критерии строки M.

Внешние подтверждения: единый реестр L01–L19 уже существует в §22.9 Desktop v1.2.
Его не заменяем новыми статусами. Сразу нужны от владельца/клиник: L05 образцы и
матрица документов, L06 провайдер/тестовые доступы ЭЦП, L04 протокол личности,
L08 retention, L12 образцы файлов/словарь. До внешних тестов: L09–L10 порядок
выдачи и разрешённый WhatsApp-канал/получатель; L14–L15 условия AI/STT/корпус;
L11/L13/L16 среда/операции/нагрузка/restore. До реального запуска: L01–L03/L07
заключения/договоры/обмен, L17 экспорт, L18 ответственные/часы, L19 разрешение
конкретного кандидата и среды. Секреты передаются через защищённую конфигурацию,
не в checkpoint. Недоступность этих материалов не останавливает независимый код.

## Предыдущие технические результаты и доказательства

Текущий Git после сохранения transport: HEAD 05ed9ebb, task-only conventional
commit содержит только frontend/src/api/medicalParticipation.ts и его8 node tests.
Полный staged diff обоих файлов просмотрен, cached/committed hygiene PASS;
transport/industry tests13 PASS, types и app build PASS на текущем UI/API срезе
(77277 exit0; %TEMP%/dental-participation-final-app-build-20261122.log), widget
build PASS ранее в этом продолжении (его входы не менялись). Fetch origin/main
повторён: 0 behind /2 ahead, только собственные commits. Working hygiene повторно
FAIL только foreign EOF google-button-design-20261119.md:41; лог
%TEMP%/dental-participation-publication-hygiene-20261122.log. Push не выполнен,
нового CI/deployment нет. Сервер/React UI/docs остаются WIP, не включены в transport commit.

Итог затронутого backend на текущем срезе:73 participation tests PASS6.036s,
check/drift PASS, isolated SQLite (84494 exit0), лог
%TEMP%/dental-participation-final-backend-20261122.log. Включены candidates,
responsible, reads, API, closure, commands, withdrawal. Новый patient-context
разрешает head с medical view/branch плюс CRM Client VIEW получить только
patient_id/branch_id/business_id и пишет READ audit. Это отдельный вход от
reception-only identity panel, не расширение медицинских ролей.

Browser attempts:57587 FAIL на login (fixture flag был удалён safe_environment;
исправлено сохранением только локального boolean до configure_browser_runtime);
99404 FAIL на недостижимом head-входе внутри reception-only панели (исправлено
отдельным head patient-context и вынесенным входом);2408 FAIL на неверном ожидании
сырого текста503 вместо согласованного actions.errorTemporary (исправлен тест,
проверки сохранённого ввода/ключа и конечного состояния не ослаблены).
Browser20183 завершился FAIL на возврате фокуса: обновление access удаляло кнопку
входа. Исправлено сохранением допущенного trigger при перепроверке без сохранения
данных workspace; дальнейшие PASS и граница приёмки приведены в текущем результате.
UI включает head invite/end, own accept/decline/history,
branch selection, retained input, close guard, role-denial clearing и focus return.
Полная для выбранного сценария визуальная и negative UI проверка завершена выше;
остальные пользовательские сценарии полного ТЗ остаются открытыми.

Текущее продолжение сценария (не отдельный закрытый этап): responsible selector/API
прошёл 67 affected participation tests/check/drift (20721 exit0, 5.981s tests),
workspace-access/mine затем 21 affected read/API tests (23336 exit0, 2.855s).
Логи %TEMP%/dental-participation-workflow-20261122.log и
%TEMP%/dental-participation-workspace-20261122.log. Typed transport: 6 node tests
PASS; tsc -b PASS до добавления workspace-access/mine типов, повтор потребуется
на финальном UI. Нет новой миграции, notifications/BusinessEvent/AI/external sends.
UI implementation использует zani-review-frontend, zani-change-crm-domain,
zani-run-verification и ранее прочитанные Anti Slop UI/human/layout/copy + design-taste.
Применяемые требования: существующие Modal/Button/Select/StateViews и токены;
RU/KK/EN; отсутствие PHI в browser storage; отзыв очищает данные, 409 требует
перечитывания, исправимая ошибка сохраняет ввод/ключ; клавиатура/focus и mobile.
Композиция S13/M04: список реальных участников и форма действия; спокойный
рабочий интерфейс ENERGY/RHYTHM/MOTION 1/1/1, без новых декоративных блоков.
Сквозная UI приёмка, build/browser/screens и сохранение в Git пока не завершены.

Slice62 result: proposal candidate selector/private strict HTTP and shared proposal
context/branch authorization implemented, verified59 tests PASS5.164s, runner7667
terminal0; system check/migration drift PASS. Isolated-runtime command manage.py test
apps.medical.tests_participation_candidates apps.medical.tests_participation_reads
apps.medical.tests_participation_api apps.medical.tests_participation_closure
apps.medical.tests_participation_services apps.medical.tests_participation_withdrawal
--noinput -v1; manage.py check; manage.py makemigrations --check --dry-run.
Log %TEMP%/dental-participation-candidates-20261122.log. Nine new tests cover match
with proposal command, self/open/inactive/foreign exclusion, current recipient
approve/medical+CRM branch/revocation, source cancellation/create denial, doctor
cross-branch preservation, head scope/owner denial, empty-page cursor/name search,
audit failure and strict authenticated/no-store HTTP with no write key required.
Write still reauthorizes after selection. Reviewed shared helper callers (commands,
closure and candidate reader); all their affected tests included. Syntax/whitespace
and tracked docs diff hygiene PASS. No schema/UI/shared generic code changes;
no frontend build/browser/full medical repeat (unaffected areas); PG concurrency
and D12 performance remain unverified. Candidate names are current labels, no
clinical content returned. Next responsible selector/action availability/outgoing
proposal visibility, then frontend integration. Full M06/M07 scope remains open.
CRM/access/capabilities/matrix updated. Operations/README/frontend unchanged:
no environment/provider or UI behavior changed. Canonical root/branch/HEAD unchanged;
local unpublished WIP, prior foreign outgoing-range blocker retained. Working DB,
notifications/BusinessEvent/AI untouched. All runners terminal; full goal ACTIVE.


Slice62 contract: previous61 progress; proposal candidate selector shares the
command's current source/head authorization and recipient approve/branch checks.
Extract existing patient context/proposal branch authorization without changing
approved doctor cross-branch proposal behavior. Candidate lookup requires create
(the command permission), not a general staff/clinical directory grant. Exclude
self, inactive/foreign members, open pending/active participation at destination;
return member ID/current name, patient revision, cursor only. Bounded scan <=50
members with continuation even if all scanned recipients denied; filter names
before pagination. Patient READ audit including empty results; no key needed for
read. Existing command still reauthorizes selected recipient. Tests permissions,
branch/cross-branch, revocation/race between select+write, empty continuation,
foreign/self/existing member, audit failure and strict/private API. Affected
participation command/read suites +check/drift, no schema/UI/provider changes.
Next responsible selector/action availability/outgoing UI; full objective intact.


Slice61 result: incoming invitations and branch-scoped head participation lists
implemented and locally verified. Runner5174 terminal0/50 tests PASS3.346s; check
and migration drift PASS. Command .venv/Scripts/python.exe isolated_runtime invokes
manage.py test apps.medical.tests_participation_reads apps.medical.tests_participation_api
apps.medical.tests_participation_closure apps.medical.tests_participation_services
apps.medical.tests_participation_withdrawal --noinput -v1; manage.py check;
manage.py makemigrations --check --dry-run. Log %TEMP%/dental-participation-reads-20261122.log.
Nine new tests prove recipient-only metadata/no clinical basis, accepted removal,
head state/patient filtering, current medical+CRM branch intersection/future timing,
owner/doctor/head boundaries, revoked role/view denial, foreign Business/corrupt
links, bounded cursor/empty audit, collection+row audit rollback and strict/private
HTTP. Existing41 command/service tests retain lifecycle and generic GET/PATCH denial.
No clinical reasons decrypted; patient/staff/branch names are current display labels.
Entire new reader/test/view delta reviewed, syntax/whitespace PASS; docs diff hygiene
PASS. No schema/shared audit helper changes, no broad medical rerun warranted by this
isolated reader; no frontend delta/build/browser. PostgreSQL concurrency and production
performance not certified. Incoming/managed are not candidate selectors or finished UI.
Next: authorized candidate selectors/action availability plus outgoing proposal
visibility, then reachable invitations/management UI with current scopes. Original
ordinary completion/security revoke/24h correction/team/support scope remains open.
CRM/access/capabilities/M06 matrix updated; operations/README/frontend unchanged
because no new environment requirement or UI. Canonical root/branch/HEAD unchanged;
local WIP/unpublished, prior foreign outgoing-range blocker retained. Working DB,
providers, notifications, BusinessEvent and AI untouched. All handles terminal.
Full goal ACTIVE; M06/M07 remain partial.


Slice61 contract: previous60 progress; add incoming pending invitations and scoped
head-management reads. Explicit medical_participation.view, current medical role,
CRM plus medical branch intersection; no owner/platform/reception implicit access.
Incoming is only recipient's effective pending invitations in active branches;
managed is only head's selected permitted branch, optional patient/state. Return
operational identity/status/revision/date metadata, never encrypted reasons/IIN/
clinical content; invitation read does not grant clinical basis. Business collection
read audit even empty + exact participation read per exposed row, atomic failure.
Bounded id-desc pagination20/max50. Names are current display labels. Strict GET
actions/no-store use existing viewset; generic GET/PATCH remains unsupported.
Tests recipient/head/role/branch/tenant/isolation/revocation/pagination/audit/API.
No migration/UI/provider/notifications/BusinessEvent/AI effects. Candidate selectors,
outgoing invitation UI and full lifecycle UI remain next; root/HEAD/ownership unchanged.

Slice60 result: strict authenticated participation command API implemented and
verified. Runner63302 terminal0:41 tests PASS3.199s, system check/drift PASS.
Isolated-runtime command: manage.py test apps.medical.tests_participation_api
apps.medical.tests_participation_closure apps.medical.tests_participation_services
apps.medical.tests_participation_withdrawal --noinput -v1; then manage.py check and
makemigrations --check --dry-run. Log %TEMP%/dental-participation-api-20261122.log.
Eight HTTP tests prove proposal/accept/head-end/replay, recipient decline/pending
withdraw, strict unknown fields and key requirements, stale/reused payload409,
anonymous/owner/recipient/revoked head denial, branch/foreign Business, audit503
rollback/retry and unsupported read/PATCH. Responses are metadata-only and private
no-store on tested success/errors. Services/role semantics unchanged; no UI/PHI
reader invented. All new source/tests and router delta reviewed; syntax/whitespace
and tracked docs diff hygiene PASS. No schema/env/working DB/provider changes;
no browser/build needed (no frontend delta). Prior445 medical suite remains scoped
service evidence, not claimed rerun; affected41 covers this HTTP composition.
CRM/access/capabilities/operations/matrix synchronized; README/frontend unchanged
(no reachable flow yet). Next required work: authorized participation lists and
candidate selectors, then UI for proposing/responding/withdrawing/head closure.
Ordinary completion with obligations/security revoke/24h corrections/support/team
remain in original full scope. M06/M07 not complete. Canonical root, branch
codex/ui-testing-toolkit and HEAD31b90484df7662a63fe3245dcb96636cab1158b0 unchanged;
local WIP/unpublished with earlier foreign outgoing-range blocker retained.
All processes terminal. Full goal ACTIVE.


Slice60 contract: previous59 progress verified445 medical; expose existing authorized
participation commands at /api/medical/participations/: propose, respond, withdraw,
end-by-head. Strict fields, authenticated requests, metadata-only response and private
no-store on success/errors, required command key. Views never write state directly.
Reuse current services/role/branch/tenant/revision/audit/replay; do not add implicit
clinical read access or generic CRUD. Focused API lifecycle/denial/branch/tenant/
unknown fields/key/conflict/replay/audit failure/unsupported methods tests plus
participation service dependencies and system/drift. No schema/UI changes; list,
candidate selectors and reachable UI remain next required work. No notifications/
BusinessEvent/AI/provider/working DB effects; root/HEAD/ownership unchanged.

Slice59 result: head-authorized active -> ended domain transition implemented and
locally verified. Focused60597 terminal0/29 PASS1.433s; expanded shared-medical71306
terminal0/445 PASS44.794s, system check and makemigrations --check --dry-run PASS.
Commands via .venv/Scripts/python.exe + isolated_runtime: manage.py test
apps.medical.tests_participation_closure apps.medical.tests_participation_services
apps.medical.tests_participation_withdrawal --noinput -v1; then manage.py test
apps.medical --noinput -v1; manage.py check; manage.py makemigrations --check --dry-run.
Logs %TEMP%/dental-participation-closure-focused-20261122.log and
%TEMP%/dental-participation-closure-medical-20261122.log. New12 tests include closure,
reason encryption, preserved proposal/appointment, basis removal, replay/conflict,
owner/doctor/current-role/branch/manage denial, inactive departing doctor, foreign
responsible/patient/Business, missing keys/audit rollback, false/stale end audit denial.
Migration0014 generated intentionally and applied only to disposable test DB; adds
closure reason/responsible and participation_ended audit choices/constraints. Source,
migration and whole new test reviewed; syntax/whitespace and docs diff hygiene PASS.
No UI changed: no browser/build repeated; API/UI flow not yet delivered. Concurrency
in PostgreSQL still required; serial SQLite does not prove locks. Existing ordinary
end/obligations, security revocation across independent bases,24h correction/support
and assistant scope remain open. No silent broad patient ban introduced: head end
removes only this participation basis, current appointment basis remains separate.
Next: read/command API for participation lifecycle and its reachable interface,
then obligation-aware ordinary completion and limited correction authorization.
Access/CRM/capabilities/matrix updated. Operations notes migration boundary; README
unchanged because no public setup/flow exposed yet. No notifications/BusinessEvent/
AI/provider/working DB/infrastructure effects. Canonical root and branch/HEAD
unchanged; local unpublished WIP, earlier foreign outgoing-range blocker retained.
All handles terminal; full goal ACTIVE, M06/M07 not closed by backend-only evidence.


Slice59 contract: previous58 progress, objective/current HEAD restored. M06/M07
D03 section18.1.3 rule2: scoped medical head can end active participation with
required reason and explicitly selected active same-Business responsible member.
Reuse participation state/branch role/manage check, Business lock, encrypted content,
revision/idempotency/audit. New closure reason and responsible preserve original
proposal and author/history. Does not cancel/reassign appointments, tasks or payments,
and does not grant responsible person medical access. Separate appointment basis
remains independently evaluated. Ordinary doctor completion with obligation list,
security revocation across bases and24h correction grant remain separate open scope.
Skills domain+verification: service-only lifecycle, same-Business relations, atomic
current authorization/replay and audit. Schema migration only isolated DB. Focused
success/denial/branch/tenant/replay/stale/inactive target/rollback/encryption tests;
then full medical suite due shared audit constraint, check/drift. API/UI not claimed.
No notification/BusinessEvent/AI/provider effects. Root/branch/HEAD/foreign WIP
unchanged. Intentional new fields/event/migration; no working DB migration.


Slice58 result: configured per-tooth surface selector implemented and locally
verified. Second localized browser41641 terminal0/6 PASS3.9m, final Map regression
76197 terminal0/1 PASS1.8m (30.8s en-mobile). Six final localized editor screenshots
AND final Map en-mobile screenshot captured/visually inspected. Real isolated HTTP
writes prove a revision0->1->2, b0->1, constructor0->1->2; whole-tooth revision and
independent clinical draft preserved. Current server policy reference sent exactly.
Dirty target locked with accessible explanation, desktop keyboard select/focus,
unsaved continue/discard/save, pending duplicate guard,503 stable retry,409 retained
text and explicit reload, vocabulary503/retry, historical cutoff, primary/mixed
selection and actual revoked-role clearing covered by these scoped tests.
Final types/app/widget2464 terminal0 PASS; logs %TEMP%/
dental-tooth-surfaces-map-{app,widget}-build-20261122.log. Browser logs %TEMP%/
dental-tooth-surfaces-final-20261122.log and dental-tooth-surfaces-map-20261122.log.
Commands: .venv/Scripts/python.exe isolated_runtime invoking npx.cmd playwright
 test medical-tooth.spec.ts --config=playwright.clinical.config.ts --max-failures=1
(and --grep "en mobile" after Map fix); frontend npx.cmd tsc -b and vite build
--outDir ../output/dental-tooth-surfaces-map/app plus --config widget/vite.config.ts
--outDir ../output/dental-tooth-surfaces-map/widget. Node11 PASS and i18n7764 PASS
retained for unchanged transport/dictionaries. Changed-source whitespace/fixture
syntax and tracked docs diff hygiene PASS. No application backend changes/migrations;
no repeated backend suite. SerialSQLite is not PostgreSQL concurrency certification.
Visual acceptance covers changed form geometry, localized wrapping, focus, labels,
44px controls and viewport overflow. Full axe/keyboard traversal/tablet/zoom/real
mobile devices/long-label visual and performance gates remain outside this evidence.
Synthetic vocabulary is only browser fixture, not real clinical approval. README/
operations need no change: setup and real configuration unchanged. Frontend/CRM/
capabilities and M09 matrix synchronized. Full S04/M09 remains partial: clinical
notation review, linked plans/images, team permissions and concurrency/performance.
Next independent full-goal work: M06/M07 participation lifecycle and time-limited
correction permissions, preserving current appointment basis and completed evidence.
Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit;
HEAD31b90484df7662a63fe3245dcb96636cab1158b0 unchanged. Local WIP/unpublished;
previous foreign outgoing-range publication blocker retained. Working DB/provider/
infrastructure untouched. All owned runner handles terminal. Full goal ACTIVE.


Slice58 second browser41641 terminal0/6 PASS3.9m; final labels plus desktop keyboard
selection/accessibility descriptions verified. All six surface-editor.png screenshots
in output/playwright/tooth-surfaces-final captured AND visually inspected: RU/KK/EN,
1440x1000 and390x844, wrapping/controls/focus/localized copy pass within changed form.
Review diagnostic: JSON.stringify({expected_tooth_revision:
Object.fromEntries([])['constructor']??0}) produced {}. Valid configured code could
inherit Object.prototype rather than zero. Minimal fix: ReadonlyMap + Map.get for
per-position revisions, no domain/code restriction added. New en-mobile regression
saves constructor twice (expected0 then1), alongside a twice,b once,whole-tooth and
clinical draft checks. Runner76197 active, log %TEMP%/dental-tooth-surfaces-map-20261122.log.
Final Map types/build2464 active; no visual structure change from inspected final6.


Slice58 interim: first browser50580 terminal0/6 PASS3.8m, log %TEMP%/
dental-tooth-surfaces-20261122.log. Visual inspection found misleading whole-tooth
label; fixed RU/KK/EN to neutral observation. Final browser41641 running (new
keyboard target selection and accessible-description assertions); output/playwright/
tooth-surfaces-final. Types18454 PASS;11 focused node PASS343.711ms; i18n7764 PASS.
Pre-copy builds62591 terminal0 PASS. Final copy/build evidence still pending.


Slice58 visual finding during first browser50580: surface-editor.png RU desktop
shows stale whole-tooth observation label after selecting a surface. Preserve run
until terminal; change label to neutral observation in RU/KK/EN, then rerun affected
localized evidence. Geometry/shared controls intact; not yet visual PASS.


Slice58 contract: previous57 progress verified transport; integrate current approved
surface selector into ToothEditor, per-surface revision map from current snapshot.
Reuse shared Select/labels/clinical dirty guard; lock target while text is dirty with
clear instruction (save or clear fields), never silently move text to another tooth
surface. Whole-tooth entry remains independent of absent/broken vocabulary; options
errors retry separately, denial clears workspace, stale save retains text. Existing
AntiSlop during/UI/human/layout/copy requirements: shared tokens, explicit labels,
44px controls, mobile overflow/focus and localized states. No new assets/styles.
Risk: wrong clinical target/revision; checks real API UI saves to two surfaces and
repeat same surface, untouched whole tooth, dirty lock, options failure/retry,
historical read-only and existing save/close/recovery. RU/KK/EN desktop/mobile screenshots
captured and inspected; types/i18n/build plus focused transport/terminology tests.
Synthetic vocabulary only in isolated browser fixture; no clinical approval claimed.
No backend/schema/provider/working DB/notification/AI changes; ownership/base unchanged.

Slice57 transport result: typed surfaceOptions implemented; 11 clinical/tooth
transport tests PASS (514.943ms), npx.cmd tsc -b PASS, session10601 terminal0.
App/widget Vite builds PASS; logs %TEMP%/dental-tooth-options-{app,widget}-build-20261122.log.
Commands: node --test scripts/tests/medical-tooth-api.test.mjs
scripts/tests/medical-clinical-api.test.mjs; npx.cmd tsc -b; npx.cmd vite build
--outDir ../output/dental-tooth-options/app; npx.cmd vite build --config
widget/vite.config.ts --outDir ../output/dental-tooth-options/widget (frontend cwd).
Tests prove exact tenant/basis/tooth/signal, no caching, absent policy, legacy labels,
current language labels and unchanged denial/conflict/outage/cancellation propagation.
UI unchanged; no new browser/visual acceptance claimed. Backend unchanged; no repeated
DB suite. Next is still selector integration, unsaved target-change protection,
per-surface expected revisions and localized browser evidence. No requirement closed
merely by transport. Local unpublished WIP; earlier outgoing-range blocker retained.
All processes terminal; full objective remains active.


Срез57 contract: restore verified56 surface-options endpoint; add typed frontend
transport before selector integration. Previous ping turn was no progress; current
objective/Git/files revalidated. Reuse apiClient, ClinicalReadScope and abort signal;
preserve server labels/reference/empty choices and propagate failures without cache
or retry. Transport tests cover both access bases, cancellation and error identity.
Then integrate selector/current per-surface revisions and verify localized UI before
claiming reachable completion. No backend/schema/env/provider changes. Canonical root,
branch/HEAD and foreign WIP boundary unchanged; no UI acceptance claimed by transport.

Срез56 result: approved surface choices API +shared read/write policy validator
implemented and locally verified. Session58686 terminal0;41 tests PASS/2.502s,
manage.py check and makemigrations --check --dry-run PASS. Isolated-runtime command:
manage.py test apps.medical.tests_tooth_options apps.medical.tests_tooth_services
apps.medical.tests_tooth_api apps.medical.tests_tooth_reads --noinput -v 1.
Log %TEMP%/dental-tooth-options-20261122.log. Nine new tests prove absent-policy
empty+audit, whole-tooth independence, per-tooth choices/localized labels/internal
approval omission, legacy code-only read/write, malformed labels/config failclosed,
foreign policy nofallback+tenant denial, owner/revoked denial, strict tooth/basis,
audit failure and authenticated strict/no-store HTTP. Existing save tests retain
stale reference/protocol snapshot/replay coverage. No live approval inferred.
Source/policy/read/view/test diff reviewed; new-file whitespace checks clean (exit1
for no-index additions is expected). CRM/operations/capabilities/matrix/status synced.
Frontend unchanged: no types/build/browser rerun, existing editor evidence not expanded.
No schema migration, real env setting, working DB, provider, notification/BusinessEvent/
AI effect. README/frontend docs unchanged (no consumer yet). Full goal ACTIVE.
Next: typed surface-options method and UI selector with approved language labels,
per-surface expected revision and preserved unsaved text. Medical approval/default
configuration gap remains external; do not seed invented clinical notation.
Canonical root/branch/HEAD unchanged; local WIP/unpublished, previously recorded
foreign outgoing-range publication blocker retained. All test handles terminal.


Срез56 contract: previous55 progress editor6+1browser PASS. Expose configured
per-tooth surface choices via current treatment-basis read +audit/no-store API.
Reuse same validated policy for reads and writes; absent Business policy =>disabled
choices, malformed policy =>503 (never silently accepted). Optional labels map exact
configured code set to complete RU/KK/EN labels; no invented clinical vocabulary.
Legacy code-only policies remain valid. Public result reference+codes/labels only,
not internal approval reference; write snapshot continues exact approval reference.
No real policy configured/approval claimed. Tests config/absent/malformed/labels/
tenant/role/audit/HTTP/stalewrite; isolated DB, affected services+API and check/drift.
No schema/UI/env value/notification/AI/BusinessEvent changes. Next frontend selector.

Срез55 result: whole-tooth primary observation editor +three-way unsaved guard
implemented and verified. Final localized browser19905 terminal0/6 PASS3.1m;
expanded en-mobile79332 terminal0/1 PASS1.4m (21.6s). New primary tooth expected0 and
fresh encounter revision after saved clinical draft proven. Six locale/viewports
editor screenshots captured AND visually inspected in output/playwright/tooth-editor-focus.
Tests invoke npx.cmd playwright test medical-tooth.spec.ts --config=playwright.clinical.config.ts
--max-failures=1, then --grep "en mobile"; each isolated_runtime/.venv/disposable DB,
real HTTP/synthetic fixture (serialSQLite, not PG race proof). Logs %TEMP%/
dental-tooth-editor-focus-20261122.log and dental-tooth-editor-new-20261122.log.
Final types/app/widget build10693 terminal0, log dental-tooth-editor-focus-build-20261122.log;
i18n7762 and10 transport/terminology PASS (unchanged dictionaries since these checks).
Prior failures preserved above: exact textarea label then focus after reload. Both
product fixes keep assertions; local focus ref only, no shared component rewrite.
Acceptance includes all close choices, pending/duplicate/Escape,503same-key retry,
409 local-text retention/read-only/cancel+explicit reload,read-role403wholeworkspace
clear,exact historical versions and independent clinical draft retention. Direct
write-role403 behavior remains backend-proven; separate browser write-denial not run.
UI geometry/tap targets/locales/overflow and modal focus checked. Full axe/keyboard
traversal,tablet/zoom/realdevice/longvalues and performance remain unverified.
New files/changed sections reviewed, whitespace PASS. No backend/migration/env/
provider/notification/BusinessEvent/AI changes; no backend suite repeated. Operations
and README unchanged; frontend/CRM/capabilities/matrix/status synchronized.
Full S04/M09 not closed: configured surfaces, clinical notation review, linked plans/
images, assistant/team permissions and wider acceptance remain. Next independent step:
expose approved surface vocabulary for selector and wire authorized per-surface writes;
missing real approval remains fail-closed, not a fabricated clinical legend.
Canonical root/branch/HEAD unchanged. Goal ACTIVE; local WIP/unpublished, existing
foreign outgoing-range blocker retained; no live/working DB/deployment changes.
All runner handles terminal, no owned browser/backend process left running.


Срез55 progress: focus correction browser19905 terminal0/6 PASS3.1m. Real UI create
revision/history, continue/save/discard, heldsaveEscape/pending/one request,503samekey
retry,409retainedreadonly/discardcancel+reload,role403clear and retained clinical draft
covered across six locale/viewports. Six editor screenshots captured+visually inspected
under output/playwright/tooth-editor-focus. Build10693 terminal0 (types/app/widget),
7762 i18n keys and10 node tests PASS retained unchanged inputs. Source unchanged since.
Additional en-mobile test79332 terminal0/PASS: save clinical draft first (context revision
changes), then tooth write and first observation of primary tooth51 (expected0).
Log dental-tooth-editor-new-20261122.log. Not a rerun without cause: adds uncovered
fresh-context/new-location UI acceptance. No backend rerun required (unchanged).

Срез55 second browser67933: textarea aria-label fix allowed real save; new focus
assertion reproduced loss after reload. Stopped owned run with Ctrl-C (terminal1),
verified no clinical-runtime/Playwright tooth processes remain. Added local target
ref +layout effect after fresh rows arrive; no shared Modal rewrite/assertion removal.
Next run uses --max-failures=1 to avoid equivalent cases after known failure.

Срез55 progress: ToothEditor +inspector close guard implemented. Initial browser38274
terminal1:6 cases failed exact label lookup after controlled textarea update/continue;
DOM snapshot retained correct input text. Added explicit aria-label matching visible
label as existing ClinicalDraftForm does; assertions unchanged. Added held firstsave
pending/Escape/one-request checks and focus-return after successful save. Rerun67933
active, log dental-tooth-editor-fixed-20261122.log; fixture remains isolated.
Initial build31435 terminal0; rerun build for changed aria markup follows. No shared
Textarea/Modal rewrite. No backend/schema or surface-policy changes.

Срез55 contract: previous54 progress read UI6+1 browser PASS. Add whole-tooth primary
observation editor in inspector. Fresh appointment-context before editing avoids stale
encounter revision after independently saved clinical draft. Reuse typed service/API,
DS Textarea/Button and three-way unsaved Modal. Inspector traps focus; while open,
parent tabs/close are inaccessible, so guard tooth locally; parent clinical draft stays
mounted and its existing guard applies after inspector closes. beforeunload for both.
Pending synchronous ref blocks duplicate/close; stable payload key retry;409 retains
text readonly until explicit discard+reload;401/403 clear all clinical workspace.
Successful save closes inspector and reloads formula, preserving parent draft.
Historical date view stays read-only. Surface vocabulary editor remains separate
pending approved configuration/UI endpoint; no invented codes. No backend changes.
Skills reused AntiSlop during/ui/human/layout/copy+React: existing DS,44px controls,
real labels/states,focus return/noPHIstorage. Tests real UI save/history/unsaved/retry/
conflict/denial/pending on isolated desktop/mobile plus build/types/i18n and screenshots.

Срез54 result: read-only odontogram UI connected and scoped verification complete.
Six RU/KK/EN desktop/mobile PASS/2.3m,26882 terminal0; extended ru-mobile1 PASS/1.3m
(18.1s test),28838 terminal0 after fixture locator correction. Expanded scenario
proves primary/mixed/quadrant controls, snapshot503 retry, realrole403 clears hidden
encounter draft+tooth view. Mixed mobile screenshot captured and visually inspected.
Build/i18n/types PASS82343;10 terminology/transport tests PASS. Logs:
%TEMP%/dental-tooth-ui-20261122.log, dental-tooth-ui-edges-fixed-20261122.log,
dental-tooth-ui-build-20261122.log. All handles terminal; disposable DB only.
Full intended new component/test/locale/entry changes reviewed; whitespace PASS.
UI gates: real authorized observations/history/date/no-data/recovery, keyboard
Escape/focus return,44px tooth targets, localized responsive screenshots/overflow
verified. Full keyboard traversal/axe,tablet/zoom/physical devices remain unverified,
not claimed. DS tokens/controls reused; no new color system/assets/dependencies.
Main snapshot readonly view complete within slice; full S04 still requires writing
editor and joint unsaved guard, surface protocol controls, plan/images, medical
notation review and wider acceptance. No full-goal closure. Profile docs/matrix/
status synchronized; operations/README unchanged (no env/setup effects).
Canonical root/branch/HEAD unchanged, local WIP/unpublished; foreign outgoing-range
publication blocker retained. No working DB migrations, live sends or deployment.
Next: authorized primary tooth observation editor inside inspector, coordinating
unsaved/pending state with existing clinical draft before browser write/recovery tests.


Срез54 edge attempt:93464 terminal1 after successful snapshot503 recovery; selector
expected exact combobox label, while shared Select accessible name includes label
AND selected value (Select.tsx:174). Corrected test locator to label match, retained
all assertions and production UI. Focused ru-mobile rerun28838 terminal0/PASS;
%TEMP%/dental-tooth-ui-edges-fixed-20261122.log, output/playwright/tooth-ui-edges-fixed.
Added beforeEach-equivalent real role restore so full suite can follow prior revoke
tests. No product-source change after six-browser/build PASS, no rebuild required.

Срез54 progress: ToothChart read tab implemented; permanent/primary/mixed numeric
FDI buttons, patient-relative quadrants/mobile selector, datetime snapshot, nested
shared Modal inspector with audited exact-version/history and cancellation guards.
No fake clinical shapes/healthy defaults. Mounted clinical draft retained; selected
version remount prevents stale response overwrite; denied callback clears workspace.
Six RU/KK/EN desktop/mobile browser tests PASS/2.3m (26882 terminal0), disposable
runtime real HTTP/synthetic data. Twelve chart/inspector screenshots captured AND
visually inspected: output/playwright/tooth-ui/medical-tooth-tooth-chart-*/.
Verified historical selection,date boundary,44px tooth targets,Escape/focus return,
retained unsaved encounter text,zero page overflow. Focused expanded ru mobile
93464 running: primary/mixed/quadrant controls, snapshot503 retry,realrole403clear.
Build82343 terminal0:7758 i18n keys/types/app2.91s/widget621ms PASS; existing chunk
warning. Initial i18n command ran wrong cwd (ENOENT), rerun frontend passed. Initial
script edit via implicit cp1251 corrupted terminology tests; restored exact UTF8
regex/test strings, reviewed diff and10 terminology/transport tests PASS/861ms.
No assertions weakened, only two explicit medical UI keys added to exceptions.
React skill refreshed: stable scope/effect cancellation, remounted exact reader,
no PHI cache/browser storage, existing DS retained; no framework/dependency rewrite.
Writing editor/joint dirty state, surfaces protocol picker,plan/images,full S04
and tablet/zoom/realdevice/performance/PG tests remain open. No full UI PASS claimed.

Срез54 contract: prior53 progress transport10 tests/build PASS. Connect S04 read
workspace tab with permanent/milk/mixed, patient-relative quadrants, explicit unknown,
date snapshot +exact history inspector. Reuse DS Button/Input/Select/Modal and
medicalToothApi; no authored clinical symbol legend. Preserve mounted encounter draft,
parent denied clearing and unsaved guard. Read view first; writing editor +joint dirty
control remains next dependent increment, not removed from goal. Skills already read:
frontend, AntiSlop during/ui/human/layout/copy, design-taste/app-screens. Apply >=44px
controls, mobile quadrant reflow, explicit labels/empty/error/retry, no PHI storage.
Acceptance browser desktop/mobile with real API historical data and date filter,
selection/recovery/retained encounter draft; screenshots inspect, types/i18n/build.
No backend/schema/env/notification/BusinessEvent/AI changes. No new permissions.

Срез53 result: frontend/src/api/medicalTooth.ts implements typed snapshot/history/
exact-version/save transport using existing apiClient +ClinicalReadScope. Ten
transport tests PASS/460ms (new tooth5 +existing clinical5), preserving date offset,
empty-page cursor, scope, revision zero, content, cancellation, caller key and exact
errors without retry/cache. No TSX/layout/i18n changes; S04 not yet reachable.
Commands: node --test frontend/scripts/tests/medical-tooth-api.test.mjs
frontend/scripts/tests/medical-clinical-api.test.mjs; frontend node scripts/check-i18n.mjs
(7740 keys PASS), npx.cmd tsc -b PASS, npx.cmd vite build --outDir
../output/dental-tooth-transport/app PASS/3.76s (existing >500k warning).
Initial build runner50335 terminal1: widget outDir ../../output rejected by canonical
root guard; output printing also hit cp1251 UnicodeEncodeError. Full log inspected:
%TEMP%/dental-tooth-transport-build-20261122.log. Corrected only widget command to
npx.cmd vite build --config widget/vite.config.ts --outDir
../output/dental-tooth-transport/widget: exit0/272ms. Prior app/types not repeated.
New files reviewed and whitespace clean. No backend/source contract changes;
prior52 API evidence retained; no backend rerun or browser/UI claim for transport.
No working DB/provider/deployment changes, local WIP/unpublished; publication
blocker unchanged. Frontend contract/capabilities/M09/status updated, CRM/operations/
README unchanged (same wire contract/setup). Next S04 uses approved §5.3: numbered
permanent/milk/mixed teeth, patient-relative orientation, >=44px mobile quadrant
controls and inspector; preserve ClinicalDraftForm mounted unsaved state and joint
close guard. Shape/surface legend not medically approved; no invented healthy states.
Full specification goal ACTIVE, not complete.


Срез53 contract: previous52 is progress (snapshot/history41+12 PASS).
Add typed medicalTooth API transport consuming verified four endpoints, reusing
apiClient and ClinicalReadScope XOR basis. Preserve date/cursors/revisions/whitespace,
caller idempotency and AbortSignal; no cache, browser storage, retry or silent
error conversion. No UI composition or backend policy change. Skills frontend +
verification: API-only network boundary, server ACL remains authority, no PHI cache.
Acceptance: transport runtime tests read/write/failure/cancel, type/build gates;
UI/browser remains explicitly unverified until S04 consumer is implemented.
No notification/AI/BusinessEvent/migration/env effect. Preserve other writers.

Срез52 result: snapshot and per-location revision-history services/API verified.
Combined41 PASS/2.992s +check/drift (60526 terminal0); expanded focused12 PASS/0.955s
(1173 terminal0). Logs %TEMP%/dental-tooth-lists[-edges]-20261122.log. Commands:
manage.py test apps.medical.tests_tooth_lists apps.medical.tests_tooth_reads
apps.medical.tests_tooth_api --noinput -v 1; manage.py check;
manage.py makemigrations --check --dry-run; then expanded tests_tooth_lists only.
Both runs isolated_runtime/.venv/disposable SQLite; source unchanged between runs.
Proven selected-date boundary and +05:00 same instant, milk/permanent pagination,
revision history/author, no synthesized healthy teeth, empty read audit, strict
HTTP/no-store, revoked/foreign denial, missing current503, audit-before-decrypt
failure and full rollback when a later row is corrupt. New source/docs hygiene PASS.
No new migration/env/working DB change; no UI edits, build/browser not rerun.
No live provider/deployment or PostgreSQL concurrency proof. Metadata list names
and encounter state are current display values, not immutable signature evidence.
Capabilities/CRM/M09/status updated; operations/frontend/README need no change for
these backend read endpoints. Next implement typed frontend transport and S04
reachable odontogram, preserving approved DS and existing unsaved draft handling.
Full goal ACTIVE; canonical branch/HEAD unchanged, local WIP/unpublished; previously
recorded foreign outgoing-range blocker remains, no commit/push claimed.


Срез52 progress: snapshot/history services and GET actions implemented. Combined
apps.medical.tests_tooth_lists +tests_tooth_reads +tests_tooth_api:41 PASS/2.992s;
check/drift PASS,60526 terminal0, %TEMP%/dental-tooth-lists-20261122.log.
Added explicit cross-tenant list denial, +05:00 equivalent instant and corrupt
second-row whole-snapshot rollback tests; focused12 PASS/0.955s,1173 terminal0, log
%TEMP%/dental-tooth-lists-edges-20261122.log. Production source unchanged since41PASS.
Snapshot current_revision distinct from historical revision, missing current503,
empty audited, stable state/revision pagination and strict HTTP filters verified.
No UI/browser gate claimed. Code/source and new-file hygiene reviewed clean.

Срез52 contract M09 (§4.2): previous turn progress = verified tooth HTTP40 PASS.
Add authorized snapshot as_of (aware instant, observed_at <= cutoff, latest observed
instant then revision per location) and per-location descending revision history.
Reuse current treatment basis, exact audit/encrypted reader. Snapshot paged by stable
state ID, history by revision, max50; unknown observations stay absent, never healthy
by default. Current state revision returned separately from selected history revision.
Missing current history =>503, no silent fallback. No calendar/money/env/migrations,
notifications/AI/BusinessEvent changes. Test boundaries/time offsets/paging/empty,
audit failure, role/tenant, missing/corrupt data, HTTP filters/no-store; isolated DB.
Backdated write policy and full UI remain separate unfinished requirements.

Срез51 result: tooth HTTP create/retrieve implemented and locally verified.
40 focused/dependent tests PASS/5.008s; manage.py check and makemigrations --check
--dry-run PASS. Session18564 terminal0, %TEMP%/dental-tooth-api-20261122.log.
Command in isolated_runtime(.venv Python): manage.py test
apps.medical.tests_tooth_api apps.medical.tests_tooth_reads
apps.medical.tests_tooth_services apps.medical.tests_encounter_api --noinput -v 1.
Seven HTTP tests prove historical content/whitespace, metadata-only command result,
replay,409 stale/key conflict, strict fields/missing key, anonymous/owner/revoked
role denial, unknown/foreign scope, audit503 write rollback/read withholding,
no-store headers. Services/read50 PASS from prior log retained for unchanged inputs.
Reviewed both new files and scoped router/docs diff; whitespace checks PASS.
No frontend changes: browser/build not rerun, existing UI evidence not expanded.
No new migration; working DB untouched. No notification/AI/BusinessEvent/external
provider effect. SQLite local evidence does not prove PostgreSQL concurrency.
CRM/capabilities/matrix/status synchronized; operations retains surface config
contract. README unchanged (no setup change beyond documented config).
Next M09: current/history list and date selection, then reachable odontogram UI;
assistant/team permissions, plan/image links and approved notation remain open.
Full goal ACTIVE. Canonical root/branch/HEAD unchanged; local WIP/unpublished.
Existing foreign outgoing-range publication blocker remains (see prior evidence),
no new commit/push/deployment claimed.


Срез50 reader result: isolated combined tooth reads/services/content/audit +encounter
reads 50 PASS/1.768s; check and migration drift PASS. Recovered completed log
%TEMP%/dental-tooth-read-write-20261122.log; no restart. Exact version read audits
before decryption and rolls back audit on corrupt content. Previous brief presence
reply was no-progress; current continuation restores evidence and proceeds.

Срез51 contract: expose existing tooth save/exact-read via authenticated strict
HTTP serializers and no-store responses. Reuse services/ACL/audit; no new domain
policy, migration, notification, BusinessEvent, AI or external effects. Risks:
PHI/cache, unknown fields, replay/stale writes and unauthorized access. API tests
cover success/history/replay/conflict/validation/role/tenant/audit failure; run
with dependent tooth and encounter API suites plus check/drift in isolated DB.
UI/list/date filtering remain subsequent work within full goal, not waived.

Срез50 command gate64314 terminal0:48 PASS/1.588s, check/drift PASS. Proceed to exact
revision reader in same M09 scope: reuse _clinical_read_context current treatment
basis, durable tooth READ audit before decryption, return selected version/author/
location/times. No metadata list/date filter/API yet. Focused read tenant/role/basis,
audit-before-decrypt failure and immutable historical version tests before API work.

Срез50 progress: tooth_services +Business-scoped tooth_policy and optional encrypted
surface_protocol snapshot implemented; legacy encrypted payloads remain readable.
Initial2992 terminal1:45 tests/one failure in fixture that set archived_at only,
while actual CRM archival predicate is is_archived. Set both fields in fixture;
added branch-revocation, other-primary-clinician, missing approval tests. Revised48
suite64314 running with check/drift; log dental-tooth-services-fixed-20261122.log.
No product ACL weakened. Current tests are serial SQLite, not PostgreSQL race proof.

Срез50 contract M09: authorized primary-clinician tooth save command. Reuse medical
role/branch/current appointment or active participation and verified identity; primary
clinician doctor/head only for this path (assistant/team paths still required later).
Business/patient/encounter/tooth locks, expected patient/encounter/tooth revisions,
active record/draft; new location expected0, existing appendnext. Atomic encrypted
history/audit/idempotency; keyed digest/empty response ledger, reauthorize before replay.
No calendar/finance transition. Whole-tooth free observation needs no surface notation;
nonblank surfaces require Business-scoped externally approved configured vocabulary,
per-tooth codes and current reference. Persist reference/approval in encrypted payload.
This refines prior blanket 'no public writes' note: no HTTP entry yet, and unapproved
surface notation remains disabled; no built-in clinical legend invented. Surface config
empty by default, no live approval claimed. Tests success/replay/stale/tenant/role/
identity/branch/basis/failure rollback/protocol; affected previous services+crypto/audit
and check/drift. No working DB migration, no UI/provider call.


Срез49 result: exact tooth-history audit implemented (protected FK/action/helper and
migration0013). Focused32 PASS/0.802s +full affected apps.medical380 PASS/34.819s,
73922/48962 terminal0; check/drift PASS. Isolated-runtime commands:
manage.py test apps.medical.tests_tooth_audit apps.medical.tests_encounter_audit
apps.medical.tests_tooth_content apps.medical.tests_record_services --noinput -v 1;
manage.py check; manage.py makemigrations --check --dry-run;
manage.py test apps.medical --noinput -v 1 (separate disposable DB).
Logs %TEMP%/dental-tooth-audit-20261122.log and dental-tooth-audit-medical-20261122.log.
Proven: exact immutable-version reference/PROTECT, no clinical text in event, historical
read versus current draft write, foreign/mixed/missing/invalid references blocked by
helper and structural DB checks, absent audit event/error fails closed, outer transaction
rolls back both history and state revision. Full module run justified by shared audit
helper/model change; does not certify entire CRM, PostgreSQL races, providers or UI.
Generated migration and whole intended source changes reviewed, four new-file hygiene
checks +docs diff clean. CRM/capability/M09 updated; no frontend/README/config change.
Operations unchanged: no working activation/deployment or new env requirements.
Next implement authorized idempotent primary-clinician tooth command and audited reader,
then API/UI; assistant/team and temporary rights remain full-goal requirements. Existing
surface vocabulary approval gap retained. Goal ACTIVE, local WIP/unpublished; working
DB untouched and all test handles terminal.


Срез49 progress: exact tooth audit FK/action/helper/DB constraints +migration0013.
6 new audit tests plus existing encounter audit/tooth crypto/record services32 PASS
(0.802s),73922 terminal0/check/drift PASS. Log dental-tooth-audit-20261122.log.
Because write_patient_audit and MedicalAuditEvent serve all medical operations,
run full affected apps.medical suite (not full-project):48962 terminal0/380 PASS, log
%TEMP%/dental-tooth-audit-medical-20261122.log. Final result is above.
Four new-file whitespace checks clean, generated migration inspected. Working DB
unchanged; no public tooth command or UI yet. Full affected result recorded above.

Срез49 contract: prior tooth encrypted30 PASS → exact-version audit gap. Extend
MedicalAuditEvent with protected tooth_history FK and tooth_observation_saved action;
read supports historical version, writes require current tooth revision and draft
encounter. Reject mixed entity references, wrong patient/Business and unrelated action;
no clinical content in event. Existing audit helper reused; no parallel logger or ACL.
Intentional migration0013; isolated focused tooth audit +existing audit suites/content
checks/check/drift. Failure in outer transaction must roll back version and state revision.
No role/API/frontend/notification/BusinessEvent/AI change. Public commands follow only
after this audit boundary passes. Working DB untouched; full M09 remains incomplete.


Срез48 result: tooth_content encrypted internal append/read implemented, current
Business/state locks and exact current revision, predecessor required, metadata-bound
AES256GCM and staging rollback.10 focused tests +20 dependent storage/encounter crypto
=30 PASS/0.411s;99778 terminal0, check PASS, drift none. Exact command in this turn:
manage.py test apps.medical.tests_tooth_content apps.medical.tests_tooth_storage
apps.medical.tests_encounter_content --noinput -v 1 through isolated_runtime .venv,
then check and makemigrations --check --dry-run. Log dental-tooth-content-fixed-20261122.log.
Roundtrip Unicode/no plaintext SQL, prior values/authors, stale/duplicate/missing
predecessor, ciphertext swap, valid metadata tamper, missing key and staged-encryption
failure rollback, normalized +05 time and strict content validation covered.
Helpers are NOT public authorization/audit; no role/HTTP/UI proof claimed. Existing
AES key configuration used, no provider call or migration/working DB change. Scoped
new-file/docs whitespace clean. CRM contract/capabilities/M09 updated; frontend/README
unchanged because no interface/setup change. Next extend medical audit with exact
DentalToothHistory link/action and test rollback/tenant binding, then authorized
idempotent tooth commands, API and full UI. No public writes until approved surface
vocabulary exists. Goal ACTIVE/local WIP/unpublished; all test handles terminal.


Срез48 progress: internal tooth_content helpers +10 focused tests implemented.
First66946 terminal1:29 tests/one fixture error (owner author lacked BusinessMember).
Added explicit synthetic membership, no medical role/ACL bypass. Review found non-UTC
observed_at metadata mismatch risk; refresh persisted row before encrypting and added
+05:00 roundtrip regression. Revised affected30 suite99778 terminal0 with check/drift PASS;
%TEMP%/dental-tooth-content-fixed-20261122.log. Final result is above. Product
source has no public entry yet; caller authorization/audit remains required next.

Срез48 contract: schema29 PASS → encrypted tooth payload gap. Add internal append/read
helpers using existing AES256GCM/keyring with Business/history/purpose AAD and encrypted
metadata binding state/patient/tooth/surface/revision/previous/encounter/author/times.
Append only at caller's current revision; prior revision must exist; rollback staging
on encryption failure. Payload is clinician observation text plus optional reason,
not an invented diagnostic codebook. No public writes, permissions or medical legend
changes. Caller must authorize and audit in outer transaction; helpers alone not M09.
Focused roundtrip/no-plaintext SQL, swap/tamper, duplicate/stale/missing predecessor,
key/error rollback tests +dependent storage/content suites/check/drift. Isolated DB.


Срез47 result: DentalToothState/DentalToothHistory +migration0012 implemented.
7 new schema tests +22 affected encounter storage/content tests =29 PASS/0.353s;
session9694 terminal0, system check PASS, makemigrations --check --dry-run no changes.
Log %TEMP%/dental-tooth-storage-20261122.log. Migration applied only by disposable
Django test DB creation, working DB untouched. Tested all52 numbers, invalid codes,
unique location/revision, separate surfaces, positive revisions, previous-chain links,
wrong Business/patient, retained preceding envelope and PROTECT parents. These are
storage tests with synthetic ciphertext placeholders, not encrypted write/ACL proof.
Three new-file whitespace checks and scoped docs diff clean; generated migration read.
No UI/build run: no frontend change. Prior slice46 UI results remain scoped evidence.
No endpoint/admin/model CRUD exposed. Full M09 remains partial: next add encrypted
append/read helpers bound to metadata, then current ACL/audit/idempotent commands,
API and reachable odontogram UI/history/date navigation. Surface vocabulary/legend
medical confirmation remains open. No provider/production change/publication; existing
foreign outgoing range boundary unchanged. Goal ACTIVE; test runner terminal.


Срез47 contract M09: spec§2.2/4.2 +design§5.4 require permanent/deciduous/mixed
teeth, surfaces, author/time/encounter and append history. No existing tooth models.
Add DentalToothState stable business/patient/tooth/surface key and revision; history
rows link encounter, author, observed/recorded time and protected previous revision,
with encrypted content placeholder field (no plaintext state). Unique key/revision,
positive revision/FDI tooth checks, chain/tenant/patient validation. Previous value is
read through immutable previous row, not copied/overwritten JSON. No new clinical
permissions, notifications, BusinessEvents/AI or public endpoint in this schema slice.
Surface terminology/legend remains medically unapproved: blank denotes whole tooth,
nonblank technical identifier has syntax only; future command must enforce configured
approved vocabulary before enabling writes. No diagnosis inference or preset findings.
ISO3950 numbering verified against ISO2016 primary publication preview and ISO page:
https://www.iso.org/standard/68292.html ; 32 permanent +20 deciduous tooth identifiers.
This is technical numbering support, not medical/legal certification. Models alone
are not M09 completion: encrypted append/read+ACL/audit/API/UI remain required.
Generate migration via isolated runtime only; focused schema tests +affected encounter
storage/content tests, system check/migration drift. No working DB migration.


Срез46 closed local scope: spec§4.3 three-action close implemented and verified.
API failure retains draft/dialog; held response blocks Escape/X/leave and remains
one request; same-key retry, conflict and role denial preserved. Rapid input/Escape
race fixed in source, not delayed in tests.8-case suite +1 focused held-response PASS,
10 transport/terminology PASS, final types/i18n7740/app/widget build PASS. Seven final
captures (six localized dialogs +failed-save mobile) viewed: text/controls fit, visible
focus and shared geometry retained. No native-device/tablet/zoom certification claimed.
Seven new-file whitespace checks +tracked docs diff clean. Frontend contract and
capability main text updated; CRM/API/schema/README unchanged by this UI-only slice.
M08 remains partial: full workspace/team, temporary ACL, finalization/documents,
odontogram and other full-spec requirements are open. Next domain work M09 odontogram
storage/history with approved read/write/audit boundaries; restore exact spec/contract
before implementation. Encounter-list pagination UI evidence remains open separately.
Working DB untouched; local WIP/unpublished, recorded outgoing foreign-range blocker
unchanged. Full objective ACTIVE; no pending test process.


Срез46 final browser48190 terminal0:8 PASS/3.5m,
all6 RU/KK/EN desktop/mobile three-action close, persisted save/reopen, discard/reopen,
continue, focus return, scoped axe and existing history/recovery/role denial passed.
All6 final unsaved screenshots actually viewed. Final build7906 passed. Added focused
held-response test to prove Escape/X/leave cannot close while save pending and one
request remains in flight; session89123 terminal0,1 PASS/1.3m (scenario19.0s). No product change after successful
full scoped suite/build. Log dental-unsaved-pending-20261122.log; output clinical-unsaved-pending.

Срез46 progress: implemented awaited ClinicalDraftControl save/isPending and localized
shared unsaved Modal. First browser28261 terminal1: recovery+RU desktop/mobile PASS,
KK desktop exposed rapid input→Escape race: parent dirty effect lagged, window closed.
Fixed synchronous dirtyNow ref in input handler and imperative isDirty checked at close;
assertions/timing unchanged. Final all8 browser48190 terminal0; log dental-unsaved-close-fixed-
20261122.log, output/playwright/clinical-unsaved-fixed. No live runner remains.
Initial build23942 app/types/i18n7740 PASS, widget command had incorrect config path;
corrected to package.json widget/vite.config.ts (PASS1.17s). Final build after race fix7906 terminal0: i18n7740/types/app2.71s/widget491ms
PASS; log dental-unsaved-fixed-build-20261122.log. No server changes. React best-practices skill read/applied: event
work stays handlers, transient concurrency in refs, no cache/storage/dependencies;
existing DS/layout retained. Prior RU desktop/mobile and failed-save captures viewed.

Срез46 contract: spec§4.3 requires three-action unsaved close; prior native confirm
is insufficient. Reuse shared Modal/Button and draft API, expose awaited save outcome
from draft form to parent. Save success closes; failure retains draft/dialog; pending
prevents duplicate save/close; continue/discard explicit. Role denial clears dialog.
AntiSlop existing during/ui/human/layoutmobile/copy requirements apply: shared tokens,
localized labels,44px controls, keyboard/focus, responsive wrapping, no new decoration.
Check RU/KK/EN desktop/mobile actions, error/retry and existing history/denial flows;
run types/i18n/build plus affected isolated browser suite. No backend/schema changes.

Срез45 result: evidence-only progress, no production code change. Focused browser
session42947 terminal0:1 PASS/1.4m (scenario20.3s). Real empty history before record
creation,21 revisions via actual draft API,20→1 older page→20 latest page, selected
old version has no latest text, injected exact-version503 removes reader→retry
loads correct latest text, retained unsaved draft and actual role403 still PASS.
%TEMP%/dental-history-edge-20261122.log and output/playwright/clinical-history-edge/.
Empty/older mobile screenshots captured AND viewed: controls fit width and older
reader scrolls; no fabricated data. Previous product build/backend/6-locale evidence
reused because product inputs unchanged. Browser test/checkpoint whitespace clean.
Encounter-list pagination UI remains unverified; full lifecycle/design remains open.
Next implement spec§4.3 three-action unsaved close, as detailed below. Goal ACTIVE.


Срез45 contract: prior slice44 verified history → missing evidence for empty state,
revision pagination and exact-version read recovery. Evidence gap, no product rewrite.
Extend isolated real-API browser case with empty patient history,21 revisions through
existing commands, older/latest navigation and injected version503/retry. Preserve
unsaved draft and existing denial checks. No working DB/provider/schema effects.
Run only affected browser case; reuse unchanged product build and backend evidence.
Encounter-list pagination and full design/lifecycle remain separate open criteria.
Next concrete UI gap confirmed against spec§4.3: native window.confirm only supports
continue/discard, while approved close flow requires Save / Continue editing / Leave
without saving. Existing ClinicalDraftForm owns save and pending/conflict state; next
change must expose an awaited save outcome to close controller, reuse shared Modal,
retain dialog/editor after failed save, and prevent duplicate saves/close during pending.
Browser beforeunload stays native; app close flow is the missing requirement.



Срез44 final local result: session17737 terminal0, all8 clinical browser cases PASS/3.0m
in one fresh isolated runtime. Six RU/KK/EN desktop/mobile cases include chart/open/save,
exact old revision, readonly history, author labels, unsaved draft preserved across tabs,
resave/revisit, scoped axe, focus/overflow/storage checks. Recovery cases prove retained
text/same-key retry/real409 and real role403; history injected503→retry and revoked
revision403 clear both history and hidden editor. Final two history recovery screenshots
actually viewed; six unchanged production-layout history captures from42541 also viewed.
Evidence: %TEMP%/dental-history-final-venv-20261122.log;
output/playwright/clinical-history-final/. No clinical runtime/runner processes remain.
31 affected backend tests,10 transport/terminology tests and build/types/i18n7735 PASS
as detailed below. Eleven new-file whitespace checks and scoped tracked diff clean.
No runtime/schema/production/provider change; no working DB migration. Current names
are live labels, not historical signature evidence. Serial SQLite UI verification does
not prove PostgreSQL concurrency; full S01–03/native mobile/tablet/zoom/long values,
UI pagination/empty/version-read failure coverage and remaining domain scenarios stay
open. Source/contracts/capabilities/M08 updated; README unaffected (no setup change).
No commit/push/deploy: recorded foreign outgoing range boundary remains unresolved.
Next close history pagination/empty/read-error acceptance, then remaining full clinical
workspace and lifecycle requirements. Full objective remains ACTIVE, not completed.


Срез44 continuation: goal reread; HEAD31b90484 unchanged/current branch retained.
Prior status-only reply was no progress; resumed concrete fixture correction and checks.
ClinicalHistory and current author/branch labels implemented. Backend affected31 PASS
(1.095s, dental-history-label-boundary-20261122.log); prior check/drift PASS. Build33747
exit0: i18n7735, types, app3.85s/widget625ms; existing chunk warning. Transport and
terminology10 PASS again (944ms). Six happy history flows42541 PASS; all six RU/KK/EN
history captures actually viewed in pairs: desktop context aside/mobile above, readonly
old revision and real labels, no clipped horizontal text. Long reader continues vertically.
Recovery25551 terminal1: fixture was changed from6 to8 patients during runner startup,
appointment8 returned403. Final isolated suite uses8 distinct patients, restores role
before each case, distinct history recovery command keys AND unique chart number.
First final-run attempt used system Python and failed preflight (missing environ);
corrected to existing .venv without installing dependencies. Session17737 ran
all8 with fresh disposable DB/ports, log %TEMP%/dental-history-final-venv-20261122.log,
output/playwright/clinical-history-final. Terminal0 result is recorded above. No working DB writes.
Contracts/frontend/capabilities now describe history UI; final unified result recorded above.

Срез44: prior reachable draft7 browser PASS → history UI gap. Approved S03 needs
branch/author labels, currently APIs expose IDs only. Add current display names from
linked Business branch/clinical author/primary clinician after existing authorization
and audited read; preserve IDs and existing encryption/audit boundary. Blank names stay
blank, no fabricated labels/email fallback. No schema/ACL changes. Focused read,
workspace/history HTTP tests before UI. Then history/version reader via existing API,
readonly selected text, preserve current draft when switching, abort on scope change,
clear whole workspace on denial. Existing DS/UI skills apply; test actual history,
old version, draft preservation, recovery and desktop/mobile captures.

Срез43: prior typed context/build PASS → reachable clinical UI gap. Add medical-only
calendar entry and xl shared Modal workspace, doctor draft form, chart opening and
history reader. Reuse common API/Button/Input/Textarea/Modal, existing tokens/font and
scoped memory. Skills AntiSlop core/ui/human/layoutmobile/copywriting +design-taste app
patterns apply: real server actions/data only; 44px targets/labels/focus; desktop2/3
editor+1/3 context with mobile stack; preserve recoverable drafts, same-key retry,
abort on unmount and clear on denied access. No PHI persistence. Existing clinical
permissions unchanged, commands reauthorize. Validate types/i18n/build and real API
browser desktop/mobile, recovery/conflict/revocation, captures visually inspected.
Full chart/team/finalization/signature/odontogram remain open until implemented.

Implemented ClinicalAppointmentEntry/ClinicalDraftForm, gated CalendarPage mounting,
22 RU/KK/EN strings, exact module-only terminology exemption, synthetic isolated clinical
runtime and six browser happy scenarios plus recovery test. No backend behavior change.
Initial browser18549 stopped deliberately after duplicate audited SQLite reads returned
503; only owned process tree2920 stopped, wrapper terminal1. Serial test server is an
explicit SQLite UI boundary (not PostgreSQL concurrency evidence). Serial75013 exercised
create/start/save/axe but failed reopened getByLabel: accessible name existed while
implicit label lookup included populated textarea content. Added explicit aria-labels
and stable focus-return control. Labels81842 passed RU desktop/mobile, then exposed real
opening race in KK: old preloaded context briefly rendered editable form before refresh,
so fast number input was discarded. Fixed synchronous loading/clear on open/reload;
no timeouts/assertions weakened. Latest happy68298 and recovery17363 used separate disposable DBs/ports/output
directories; terminal results below. Build68556 also terminal. Earlier build40383 exit0
not final evidence after fixes.10 transport+terminology tests PASS/649ms; new9-file
whitespace/fixture compile and scoped tracked diff clean. Initial RU saved/failed and
RU mobile screenshots inspected: actual fields/2:1 desktop/stacked mobile rendered;
final captures still needed, no full UI PASS yet. History, full workspace/odontogram,
completion/signatures/team, error coverage and final visual evidence remain required.


Final slice43 evidence: happy68298 exit0,6/6 RU/KK/EN desktop/mobile real API flows
PASS/2.4m; recovery17363 exit0,1/1 mobile PASS/2.4m. Open chart→start encounter→save→
close/reopen persisted content, Escape/focus return, no PHI in browser storage,
no horizontal overflow and scoped axe WCAG2A/AA checked in all6 happy flows. Recovery:
injected503 retains text and same-key retry; real competing API write→409 retains
local draft/blocks save; cancelling reload preserves it, confirmed reload reads latest;
real DB medical-role revocation→403 clears medical form/context. Synthetic verification
fixture is not a real identity protocol approval. Serial SQLite browser host deliberately
excludes concurrency proof; PostgreSQL race checks remain open. No real provider used.
Final build68556 exit0: i18n7725 RU/KK/EN, tsc -b, app3.86s/widget995ms PASS. Existing
large-chunk warning remains. `%TEMP%/dental-clinical-screen-final-build-20261122.log`.
Browser logs `%TEMP%/dental-clinical-ui-loading-20261122.log` and
`%TEMP%/dental-clinical-ui-recovery-20261122.log`. Screenshots under
`output/playwright/clinical-loading/` (all6 actually viewed) and `/clinical-recovery/`
(conflict/denied both viewed). Prior unchanged-layout RU top capture also inspected.
Screenshots are viewport captures at saved/error scroll positions: lower save/error
content can continue below viewport; action reachability proved by interactions, not
an assertion that full form fits one screen. Labels, field widths, mobile stack and
role-denied clearing inspected. Full design S01–03, native mobile keyboard/device,
tablet/zoom/long-value acceptance and history/version picker remain open.
AntiSlop scope: existing DS/tokens and shared controls retained, no new decorative
blocks/assets/dependencies. All visible new blocks serve entry/form/context/error;
no invented clinical findings. No working DB/backend schema changes. Latest source,
new files and relevant docs hygiene clean. All handles terminal, process inventory
shows no clinical runtime/runner alive. Local WIP, no commit/push/deploy under existing
recorded publication boundary. Next implement history list and exact revision viewer,
then complete remaining clinical workflows; full goal remains ACTIVE.

Срез42: prior appointment context44 PASS → frontend context transport missing.
Preserve backend proof; add exact context types and common apiClient GET with caller
AbortSignal, no persistent cache/retries, no fabricated patient ID. Extend transport
tests to prove scope/result/error/cancellation contracts; types and required builds.
No visible UI change in transport; browser gate deferred until actual screen.
Existing frontend/domain skills retained. Calendar entry located in CalendarPage,
AppointmentDrawerPanel (not RecordsPage). Next actual screen uses approved DS and
server actions with authorization rechecked on every command. Full scope unchanged.

Implemented AppointmentClinicalScope/Context and appointmentContext typed GET.5 transport
checks PASS/394ms: server patient ID distinct from Client ID retained, all-false action
flags retained, exact Business/appointment/signal, repeated calls not cached, errors
and cancellation propagated without retries. This is mocked transport evidence only.
Build session50993 terminal exit0: i18n7703 RU/KK/EN, tsc -b, Vite app2.81s/widget773ms
PASS; log `%TEMP%/dental-appointment-client-build-20261122.log`; isolated outputs
`output/dental-appointment-client/{app,widget}`. Chunk>500kB warning retained.
Source/test reviewed; no-index hygiene clean (CRLF notices only). Frontend contract
updated to distinguish appointment scope from patient-scoped clinical reads. No backend,
schema, working DB, provider or visible UI changes. No browser gate claimed/no live
process. Local WIP unpublished under existing foreign-range blocker.
Next implement reachable clinical workspace via CalendarPage selected appointment.
Design §5.1–5.4 reread: desktop2/3 editor+1/3 context, mobile stacked context, separate
save/finalize/sign/pay states, historical version read-only. No fake risk/tooth data.
AntiSlop human+layoutmobile+ui refreshed fully; initial combined read truncated but
layoutmobile/ui recovered separately. design-taste first90 lines only refreshed;
read remaining skill and full app-screens reference before screen edits. Copywriting
skill also needs restoration. Existing approved DS takes precedence over new styles.

Срез41: prior typed frontend/build PASS → calendar entry lacks medical patient ID and
server action flags. AppointmentDrawerPanel has Appointment/Client, not PatientProfile;
reception-only by-client endpoint cannot be reused by doctor. Add audited appointment
clinical context resolver using shared assigned-doctor appointment prerequisite (extract
without relaxing existing patient basis). Valid branch/role/assignment before resolving
patient; missing profile404 only after valid basis, no owner bypass. Return patient/
appointment/active record/current encounter metadata +create_record/open_encounter/
save_draft booleans using fresh medical permissions, identity, state and primary author.
Flags are UX snapshot, commands still reauthorize. No clinical text/decrypt or mutation.
Strict GET endpoint/no-store; focused entry +existing appointment/access/API regressions
before frontend dependency. No schema/provider/UI changes. Domain/frontend verification
skills retained. Next typed method and actual approved calendar→clinical UI integration.

Restoration: prior goal implementation turn made code progress; intervening presence
reply added no evidence. Current files confirmed, HEAD unchanged. Added10 HTTP context
tests. Initial session38418: check/drift PASS;44 tests ran,43 passed and1 fixture error
(verification-completeness DB constraint). Corrected unverified fixture to clear all
verification fields; no production assertion/constraint weakened. Rerun session45010
terminal exit0:44 affected tests PASS/1.238s (context10, appointment basis14,
open12, clinical API8). Logs `%TEMP%/dental-appointment-context-20261122.log` and
`%TEMP%/dental-appointment-context-fixed-20261122.log`; check/drift PASS before
fixture-only correction. Metadata/audit/action flags, identity/read-only restrictions,
missing profile ordering, current role/branch/cancellation, bad query, audit503 and
missing-current503 atomic rollback covered. Existing appointment14 include tenant
corruption, reassignment and no24h cutoff. No PostgreSQL concurrency claim.
Source/new tests inspected; no-index hygiene clean (CRLF notices only), scoped docs
hygiene clean. CRM and capabilities contracts updated. No schema/working DB/provider
changes, no frontend changes this slice, no browser/build required. No live process.
Clinical UI remains unconnected; next add typed appointmentContext method then approved
calendar→clinical screen, including desktop/mobile interaction evidence. Full scope
remains active; local WIP unpublished under recorded foreign range hygiene blocker.

Срез40: prior history30 PASS → typed frontend clinical transport prerequisite.
Skills zani-review-frontend +checklist and AntiSlop core refreshed; saved during mode.
Current boundary transport only: no visual/copy/layout changes, UI gate not applicable
until actual screens. Apply API-only networking, exact server types, mutually exclusive
access basis, AbortSignal on all calls, caller-owned idempotency keys, no persistent/
query cache or swallowed401/403/409/503. Reuse apiClient/session-generation interception;
no alternate auth, retries or credential handling. Next UI preserves approved S01–03
DS (Manrope/NotoSansKK,semanticgreen,1/1/1), existing primitives and scoped local state.
Meaningful transport contract tests for scope/cursor/signal/keys/no retries; types/i18n
and isolated app/widget build once. No dependencies/provider/backend/working DB changes.
This client alone is not reachable clinical workflow; frontend integration remains open.
Implemented medicalClinical.ts types/client +4 executable transport contract tests
(node --test scripts/tests/medical-clinical-api.test.mjs):4 PASS/411ms, exit0. Tests
use mocked common apiClient, not actual backend/provider; previous HTTP evidence remains
separate. Scope/cursors/signal, no read cache, exact payload/key reuse, missing/long key
rejection and error/cancel propagation without own retries covered.
Build session44103 exit0: check:i18n7703 keys RU/KK/EN PASS, tsc -b PASS, Vite app3.40s
and widget0.608s PASS. Outputs `output/dental-clinical-api/app` and `/widget`; log
`%TEMP%/dental-clinical-api-build-20261122.log`. Vite warns chunks>500kB; not suppressed
or presented as performance PASS. No dependency install/lock change. Source/tests reviewed,
no-index hygiene clean. Frontend contract updated. Existing DS/screens/copy unchanged;
AntiSlop visual/interaction/responsive gates N/A for transport-only change, not UI PASS.
No browser run because no new reachable control; future UI still needs actual captures,
interaction and accessibility evidence. No live process; local WIP unpublished under
existing blocker, working DB unchanged. Next use typed client in approved clinical UI
and implement role-aware entry resolution, preserving full goal scope.

Срез39: prior workspace24 PASS → version-picker API gap. Add bounded revisions list
for one patient/Business encounter, reusing current read context; same access to other
authors/history, no write grants. Exact current version required; older pages ordered
revision descending with before_revision cursor, default20/max50. Return version IDs,
revision,author/time only; audit exposed current metadata +each page version exactly once.
No decrypt or PHI cache. Empty tail is explicit, missing current version fails503.
Strict GET encounter/{id}/revisions schema, no-store. Tests pagination after insertion,
actual other-patient encounter denial, role revocation, no decrypt, audit rollback,
missing current version and old-version read integration; affected read/workspace/API
checks plus system/drift. No schema/provider/UI/working DB mutation; domain/verification
skills retained. Full UI/performance/team/clinical completion remain required.
Implemented read_encounter_history +strict revisions GET action and6 HTTP tests.
Session39759 terminal exit0:30 affected tests PASS/1.174s (history6,workspace7,reader9,
clinicalAPI8), check PASS, migration drift PASS/no changes. Log
`%TEMP%/dental-history-20261122.log`. Exact author/history selection +old-version read,
pagination with concurrent-in-time insertion, real other-patient encounter denial,
revocation/invalid fields, missing-current503, second-audit failure atomic rollback
and no decrypt verified. This is sequential cursor evidence, not PostgreSQL race proof.
New/changed source reviewed; no-index hygiene and scoped docs diff clean. CRM and
pre-production contracts updated. No schema or working DB/provider/UI changes; no
browser/build until actual frontend edits. Local WIP unpublished under existing blocker,
no live process. Next typed frontend clinical API and approved workspace integration;
full MCS matrix remains active, previous full333 evidence not presented as new full run.

Срез38: prior chart/API+B03 final333 PASS → workspace metadata discovery gap.
Reuse treating-clinician read context (current basis/role/Business/patient), active chart
and bounded encounter page (default20,max50,ID-desc cursor). Return IDs/version/time/
state/author metadata, not clinical text; content remains exact-version audited endpoint.
Audit active record (or patient for empty chart) and each exposed current encounter
version; fail closed if version missing/inconsistent or audit fails. No implicit write
permission, no role bypass. Shared read-context extraction must preserve prior reader.
API GET encounters/workspace; strict pagination input and no-store. Tests populated/empty,
pagination/stale cursor, isolation/revocation/audit failure/no decrypt, then read+API
regressions/check/drift. No schema/provider/notification/UI changes; DB isolated only.
Domain/verification skills retained; complete UI and performance acceptance still pending.
Implemented shared clinical read context +workspace service/action/strict page schema.
Session73367 terminal exit0:24 affected tests PASS/0.778s (workspace7,reader9,clinical
HTTP8), check PASS, makemigrations --check --dry-run PASS/no changes. Log
`%TEMP%/dental-workspace-20261122.log`. Tests exact current version pointer, no decrypt,
READ audits, explicit empty state, cursor continuity after insertion, other-patient
isolation, current revocation, invalid pagination, audit503 and missing-version503 with
no partial page. Existing exact-version reader/API regression remains PASS after helper
extraction. New source/tests reviewed; no-index diff hygiene and scoped docs clean.
CRM/capability contract updated. No schema/working DB/provider/UI changes; browser/build
not applicable yet. D12 load/latency and PostgreSQL races not claimed. Prior333 full
medical result stays its earlier boundary, not a new full run. Local WIP unpublished,
no live process. Next frontend API/client +approved clinical workspace, plus version
history discovery, team/temporary ACL and remaining completion/signatures scope.

Срез37: prior clinical API319 PASS → first-visit chart creation missing. Add explicit
local-number DentalMedicalRecord opening, one active patient chart and unique Business
number; no Client.id reuse or invented automatic numbering policy. Current medical
create +appointment/active participation basis, patient revision, Business lock and
existing keyed CRMCommand replay. Dedicated MedicalAuditEvent record FK/record_opened
with protected reference/same patient/Business and no mixed links. Atomic rollback on
audit failure; no number in command ledger/audit payload. Additive audit migration only
in isolated DB. Tests success/duplicate/tenant/role/replay/revision/rollback plus audit
constraints; affected medical/check/drift. No calendar/money/provider/notification/UI
change. Domain/verification skills retained. API/UI next; no PostgreSQL race claim.
Record service +record FK/action/constraints migration0011 implemented. Focused
session89990 exit0:15 tests PASS/0.297s (record9+encounter audit6), log
`%TEMP%/dental-record-open-20261122.log`. Added records POST API only after focused PASS;
2 HTTP tests cover chart→first encounter/replay and private400/403/503 rollback.
Initial full session86531 exit0:330 PASS/28.514s/check/drift, log
`%TEMP%/dental-record-medical-20261122.log`. NOT final acceptance: matrix/source review
then exposed B03 gap: unverified patient allowed ordinary clinical writes. Spec §22.6
item3 explicitly requires verified identity. Added common verified-state prerequisite
before idempotent execution/replay for chart/open/save; read basis remains distinct.
Added3 negative tests; happy command fixtures now explicitly synthetic verified states
(not external identity evidence). Recheck all medical required after security change.
Final session98752 terminal exit0:333 medical tests PASS/27.010s, system check PASS,
migration drift PASS/no changes. `%TEMP%/dental-clinical-identity-medical-20261122.log`.
M08 matrix synchronized with chart/encounter/audit/API and remaining UI/team/completion.
CRM/access/capability documents corrected; B03 prerequisite now enforced by all3 clinical
write commands before replay. Source/tests/migration reviewed; new-file no-index/scoped
docs hygiene clean. Working DB untouched, no provider/live/browser changes; migration
only in isolated test DB. PostgreSQL races/UI/external identity policy still unverified.
No live process. Local WIP unpublished under existing foreign hygiene blocker. Next
clinical workspace discovery/list APIs +frontend integration and remaining team ACL.

Migration0011 reviewed: nullable PROTECT field, action choice/checks; no existing data
rewrite. Source/tests/new migration diff hygiene clean. CRM/capability contract updated.

Срез36: prior audited read51 PASS → clinical HTTP integration gap. Add independent
MedicalEncounterViewSet (not reception-only patient endpoint): POST open, POST draft,
GET exact version via explicit appointment/participation basis. Strict request schemas,
existing services are sole ACL/state boundary; writes return only IDs/revision/replay,
reads use audited decrypt. All responses/errors no-store/private. No general model CRUD.
No schema/provider/notification/BusinessEvent/UI changes; existing config/urls own WIP
only add registration. Domain/verification skills reused. HTTP tests: full open/save/read,
replay/conflict, malformed fields, auth/tenant/role/revocation, no-store errors, audit503
rollback, PHI absent from writes/errors. Focused then affected medical/check/drift.
Working DB unchanged; browser/API-client frontend still next, not complete UI flow.
Implemented encounter_views strict serializers/actions and router registration.
Focused session71038 terminal exit0:8 HTTP tests PASS/0.392s; log
`%TEMP%/dental-encounter-api-20261122.log`. Complete open/save/read-old/read-new,
preserved clinical whitespace, metadata-only writes, replay/conflict, stale409,
unknown fields400, missing key, owner/anonymous/revoked role, foreign patient/Business,
audit503 rollback/retry and private/no-store errors verified. Full medical suite with
check/drift completed session47071 exit0:319 tests PASS/25.251s, system check PASS,
migration drift PASS/no changes; `%TEMP%/dental-encounter-api-medical-20261122.log`.
CRM API contract, access prerequisite text and pre-production capability boundary updated.
New source/tests and entire config/urls own diff reviewed; no-index new-file and scoped
tracked diff hygiene clean. No UI source changes, so browser/build not run; HTTP TestCase
is isolated backend evidence, not deployed/provider/end-user acceptance. Working DB not
migrated; no live process. Local WIP unpublished; existing foreign hygiene blocker remains.
Next active chart creation +clinical workflow API client/UI, other author/team ACL and
completion/signatures. Entire medical module test PASS does not close full MCS goal.

Срез35: prior open66 PASS → missing clinical read boundary → implement treating-clinician
exact-version reader using current appointment OR active participation basis, patient/
Business isolation and existing READ audit before decrypt. D03 history includes other
authors/branches inside Business; source basis branch checked, not a new target-branch
write grant. Explicit one basis per call; assistant/head-wide/support/temporary grants
remain separate required ACL paths. No implicit owner access. Return exact revision,
author/time/content only after successful transaction; no cache or idempotent PHI ledger.
Reuse existing decrypt/audit/access helpers. Tests success/history/crossbranch/tenant,
revocation/cancel/no basis/audit failure/corrupt payload; focused then affected suites
and check/drift. No schema, provider, notification, BusinessEvent, frontend changes;
working DB untouched. Domain/verification skills retained; no PostgreSQL race claim.
Implemented encounter_reads exact-version boundary +9 read tests. Session94138 terminal
exit0:51 affected tests PASS/0.685s (read9, content13, audit6, appointment14, participation9),
system check PASS, migration drift PASS/no changes. Log
`%TEMP%/dental-encounter-read-20261122.log`. Exact version/author, repeat read audit,
historical author and crossbranch history via participation, ended/cancelled basis,
role/owner/assistant denial, foreign Business/patient, missing version, mandatory single
basis, audit failure before decrypt, corrupt envelope fail closed verified. No cached PHI
or command ledger used for reads. Failed decryption rolls back success audit; dedicated
failure/denial audit remains outstanding. Source/tests reviewed; no-index diff hygiene
clean. CRM contract updated; docs-only diff hygiene clean. No schema/provider/UI changes,
no working DB mutation, no live process; local WIP unpublished under existing blocker.
Next chart creation, additional author/team access and clinical API/UI; full goal active.

Срез34: prior primary-save55 PASS → missing encounter opening → add authorized opening
against existing active DentalMedicalRecord and Appointment, exact patient/Business.
D05 one primary encounter per appointment; primary clinician derived from fresh medical
role +appointment basis (not request-author ID), branch from appointment. Patient and
appointment updated_at reject stale forms. Business→patient→appointment locks; atomic
encounter/first encrypted version/audit/idempotency; no calendar state/payment changes.
Reuse existing crypto/audit/command services. Duplicate different-key open conflicts;
replay rechecks current role/basis, returns exact initial version. Active-chart creation,
additional authors and read/API/UI remain required separately (not abandoned scope).
No schema/provider/notification/BusinessEvent/UI change. Domain/verification skills
retained. Focused open tests then encounter dependent suites/check/drift; PostgreSQL
concurrency proof remains required later. No working DB migration.
Initial focused session53491 exit1:11 tests,9 errors. Incorrectly used Appointment.revision
(field belongs to VisitPlan); inspected scheduling._assert_appointment_version and fixed
to required timezone-aware expected_appointment_updated_at. No core model modification.
Log `%TEMP%/dental-encounter-open-20261122.log`; rerun justified by corrected contract.
Corrected affected session49778 terminal exit0:66 tests PASS/1.335s, system check PASS,
makemigrations --check --dry-run PASS/no changes. Log
`%TEMP%/dental-encounter-open-fixed-20261122.log`. Covers11 open tests plus save13,
content13,audit6,storage9,appointment basis14. Open success/empty draft, derived author/
branch, preserved calendar, stale patient/timestamp, foreign chart/patient/Business,
role/branch/replay revocation, duplicate primary, crypto/audit rollback and retry covered.
No schema change; existing migrations applied only in isolated test DB. New source/test
reviewed; no-index hygiene +scoped docs diff clean. CRM contract updated. API/browser
and PostgreSQL concurrent requests remain unverified; not a completed clinical flow.
No live process, working DB untouched, local WIP unpublished; existing publication
blocker unchanged. Next audited clinical reader and chart opening/contributions/API/UI.

Срез33: prior audit278 PASS → missing authorized draft command → implement primary
clinician save with fresh medical role/branch and appointment or active participation
basis. Reuse Business lock, encrypted revision append, MedicalAuditEvent and CRMCommand
idempotency with keyed content digest/empty response (no PHI in command ledger).
Expected encounter revision, draft state, same patient/Business and active chart;
no Appointment/money mutation. This command is only the primary-clinician path:
coauthor/assistant contributions, opening, audited readers, API/UI remain required.
Risk: clinical ACL, stale/replay and atomic encryption/audit rollback. Focused isolated
service tests (happy/denial/branch/tenant/revocation/conflict/replay/rollback) then affected
encounter+basis suites/check/drift. Existing domain/verification skills apply. No schema,
provider, notification, BusinessEvent or frontend change; PostgreSQL race proof pending.
Implemented save_primary_encounter_draft and13 service tests. Initial focused session66469
exit0:10 PASS/0.492s (`%TEMP%/dental-encounter-command-20261122.log`). Added real foreign
Business/patient, primary-clinician ownership and other-branch participation negatives.
Affected session66801 exit1:46 tests passed, one loader error because selected nonexistent
tests_participation_access; actual basis tests are in tests_participation_storage. This
was a command selection error, not PASS. Check/drift passed on unchanged source.
Corrected completion suite session2826 runs same46 +actual9 participation tests;
`%TEMP%/dental-encounter-command-final-20261122.log`: terminal exit0,55 PASS/1.014s.
Final source/new tests reviewed; no-index diff hygiene and scoped docs diff clean.
CRM contract records primary-draft command and remaining author/read/open/UI paths.
No working DB migration, schema or provider change; no frontend build/browser needed
for this internal command. Sequential stale/replay tests are not PostgreSQL race proof.
Local WIP remains unpublished (existing foreign hygiene blocker); no live process.
Next opening a primary encounter against existing appointment/chart with revision and
idempotency, then audited reads/contributions/API/UI. Entire goal remains active.

Срез32: previous progress encrypted encounter helpers10/affected33 PASS. Next audit
prerequisite reuses MedicalAuditEvent: protected FK to exact MedicalEncounterRevision
(instead of unattached numeric revision), opened/draft_saved actions and READ history.
No clinical content/reason in audit. Fresh version/encounter/patient/Business/link check,
write event current draft version only, historical READ may name an older valid version.
DB requires version/patient for encounter write actions, forbids mixed representative/
participation/encounter links. Existing patient/representative/participation audit stays.
Atomic caller rollback if audit unavailable; reference protects audited version deletion.
Additive migration isolated DB only; focused audit/encounter then affected medical/check/
drift. No notification/BusinessEvent/provider/UI changes. Public draft commands/read ACL
still required; schema/helper must not be presented as complete clinical workflow.
Implemented exact protected version FK/actions +migration0010. Focused log recovered
from previous tool truncation:19 tests PASS/0.147s, terminal OK; process inventory has
no surviving Python job. No restart of that completed test. Full affected run session52502
terminal exit0:278 medical tests PASS/24.038s, system check PASS, migration drift PASS.
Logs: `%TEMP%/dental-encounter-audit-20261122.log` and
`%TEMP%/dental-encounter-audit-medical-20261122.log`. Tests cover cross-patient/Business,
historical read/current-write distinction, missing/mixed audit links, PROTECT and
atomic rollback of encrypted version+parent revision on audit failure. Migration0010
reviewed: additive FK/actions/check constraints, no data/calendar/payment mutation.
New audit source/tests/migration no-index diff hygiene clean. CRM contract updated.
Working DB untouched; browser/build not applicable to internal backend audit. PostgreSQL
concurrency and reachable clinical API/UI remain unverified/unimplemented. Local WIP,
no publication; existing foreign diff-hygiene blocker unchanged. No live test process.
Next authorized encounter draft commands and audited read, then API/UI. Full goal active.

Срез31: previous progress encounter storage9/medical259 PASS. Next code gap encrypted
clinical revision append/read helpers before public draft commands. Reuse AES256GCM
keyring/purpose isolation, not new crypto. Schema1 text fields from §2.2: complaints,
anamnesis,examination,diagnosis,procedures,plan,epicrisis; draft fields optional, no
invented required medical template. Technical limits32768chars/field,reason2000; unknown
fields/nontext rejected without echoing clinical values. Versions bind Business+rowID
and authenticated parent/author/version metadata. Atomic encrypted staging→row-bound
final envelopes, no plaintext SQL; stale revision/duplicate do not overwrite history.
Internal storage helpers are NOT authorization/audit boundary. Public access remains
closed until clinical role/participation/audit commands. DB loss/config/corruption not
silently returned as empty clinical data. No calendar/money/provider/UI changes.
Focused crypto/storage tamper+rollback tests then affected crypto/encounter/check/drift;
no schema change. Full goal unchanged; draft commands/audit/read ACL next.
Implemented encounter_content append/read +strict draft shape. Focused session29615
exit0:10 PASS/0.167s; `%TEMP%/dental-encounter-content-20261122.log`. Roundtrip RU/KK,
no plaintext SQL, append history, duplicate rejection, AEAD row/purpose swap, author
metadata tamper, malformed snapshot, empty draft, missing key and post-staging rollback.
Added current-parent revision upper bound and3 tests for stale snapshot/parent rollback/
branch mismatch. Completion session57235 terminal exit0:33 affected tests PASS/0.162s,
check PASS, makemigrations --check --dry-run PASS/no changes;
`%TEMP%/dental-encounter-content-affected-20261122.log`. No unrelated full-suite rerun:
no existing callers or modified crypto; prior259 remains prior evidence. New source/tests
reviewed and explicitly no-index diff --check clean; CRM contract/scoped docs diff clean.
No working DB/provider/frontend changes, no migration. Build/browser not applicable to
internal backend helper; no PostgreSQL concurrency acceptance. Current local WIP remains
uncommitted/unpublished; no live process. Next existing MedicalAuditEvent encounter FK/
revision +draft created/saved actions, then role/basis/version-checked open/save commands,
audited clinical read and reachable UI. Helpers alone do not establish clinical access.


Срез30: previous progress pending withdrawal8/affected34 PASS. M08 dependent gap:
ordinary participation end needs actual encounters/doc obligations. Source §2.2,§4.4,
D05§18.1.5 read: one primary encounter per Appointment; draft/finalization separate
from document signatures and money; no new Payment or Appointment.notes clinical text.
Schema step: DentalMedicalRecord business+patient/local number, one active record;
MedicalEncounter OneToOne Appointment +record/patient/branch/primary clinician,
draft/finalized with explicit start/end/finalizer/revision. Signature lives in document
workflow, not a fabricated encounter signed flag. Clinical snapshots in separate
MedicalEncounterRevision (unique encounter/revision, encrypted content/optional reason,
author/time), not common CRM notes. History parents PROTECT; tenant/link validation.
No implicit finalize/sign/paid. Model constraints are storage, not authorized commands
or append-only guarantees. Draft services/audit/ACL/readers then completion coupling
and obligatory-document policy remain required. Unknown signature policy fail closed.
Skills domain/verification retained. Additive migration disposable DB only; focused
constraints/tenant/history tests then medical/check/drift. No core scheduling mutation,
notifications/BusinessEvent/provider/UI/env changes in this schema step.
Implemented3 models, additive migration0009 reviewed (CreateModel/constraints only).
Focused session56017 terminal exit0:9 PASS/0.061s; `%TEMP%/dental-encounter-storage-20261122.log`.
Storage fixtures use synthetic envelope markers, not proof of encryption service or
clinical authorization. Active chart uniqueness/number/history, one Appointment→Encounter,
state/date constraints, cross-patient/Business/branch validation and PROTECT checked.
Completion session11478 terminal exit0:medical259 PASS/19.049s, Django check PASS,
makemigrations --check --dry-run PASS/no drift; `%TEMP%/dental-encounter-storage-medical-20261122.log`.
Migration0009 tested only in disposable DB; working DB unchanged. No new public routes,
frontend/build/browser not rerun; no financial/calendar state changes. No PostgreSQL
concurrency proof. Full schema/test/migration reviewed; task diff hygiene clean.
HEAD31b90484/same current branch; own local WIP, no commit/push; no live sessions.
Next: draft content schema/encryption +append revision/audit +authorized open/save and
read; clinical completion still depends on document/required-field policy and existing
Appointment/financial transaction. Do not treat empty obligations as completed work.
New files explicitly no-index whitespace checked: no findings, LF→CRLF notices only.
CRM domain contract updated to distinguish storage from required completion workflow.


Срез29: previous progress audit/propose/respond +medical242 PASS. Implement pending
withdrawal as a request lifecycle command, not termination of active treatment.
Original proposer with current doctor/head medical create permission may withdraw own
pending invitation; cancelling this request does not read clinical content or grant
patient access. Other actor only scoped medical head with manage in target branch.
Recipient uses decline, not proposer withdrawal. Target's revoked role must not prevent
cleanup by authorized proposer/head. Replay rechecks actor rights; pending/revision
checked inside idempotent operation. accepted/declined/withdrawn cannot be withdrawn
with a fresh key; race ordering tested sequentially, PG race proof still separate.
Reuse existing Business lock, audit participation_withdrawn, encrypted proposal unchanged;
no new migration/notification/provider/API/UI. Focused commands then affected medical,
check/drift; no build/browser for backend-only. Full goal and end/obligations remain.
Implemented withdraw_treatment_participation; no schema change. Focused session55930
exit0:8 PASS/0.350s; `%TEMP%/dental-participation-withdrawal-20261122.log`.
Proposer/recipient/owner/scoped head/manage denial, stale revision, both sequential
accept/withdraw orders, recipient revocation cleanup, actor revoke replay, audit rollback.
Final affected boundary: all4 participation suites (commands/withdraw/audit/storage),
check/drift; unchanged patient/representative suites not repeated (previous medical242).
Session37602 terminal exit0:34 affected tests PASS/1.158s, check PASS,
makemigrations --check --dry-run PASS; `%TEMP%/dental-participation-withdrawal-affected-20261122.log`.
No new migration, unchanged public UI/API, no build/browser; no new full-medical run
claimed. Existing242 evidence kept at its prior snapshot. Sequential ordering is not
PostgreSQL concurrency proof. Current HEAD31b90484, own local WIP/unpublished, no live
sessions; working DB/providers untouched. Access contract updated, scoped hygiene clean.
New source/test reviewed; explicit no-index whitespace check: no findings, LF→CRLF
notice only. Ordinary end still must check actual document/encounter obligations:
missing clinical models must not be treated as proof of no obligations. Next dependency
is explicit obligation/encounter contract before completing ordinary end, while head
closure needs reason and responsible member. No placeholder "always empty" checker.


Срез28: previous progress participation storage9/medical225 PASS. Next code gap is
existing medical audit → atomic invitation commands. Reuse audit table, not new log;
participation FK/revision, proposed/accepted/declined/withdrawn actions. Link validation
same patient/Business/member/branch, no plaintext reasons, required relation constraints.
Then proposal authorization: scoped medical head or currently participating doctor;
target must current medical doctor/head with branch authority. Recipient personally
accepts/declines; pending grants no content. Existing Business lock/idempotency, fresh
rights before replay, expected revisions, encrypted reason. No implicit old-doctor end.
Skills domain/verification retained: focused audit then services, medical/check/drift at
close, isolated migration only. No provider sends/working DB/UI changes. Notification
and user-facing flow remain unfinished; no claim of delivered clinical access.
Audit/storage focused session42155 exit0,13 PASS/0.117s; migration0008 inspected,
`%TEMP%/dental-participation-audit-20261122.log`. Existing patient/representative audit
not replaced; added participation IDs/version and4 action names, no plaintext reason.
Next code implemented propose +recipient accept/decline; withdrawal action reserved but
withdrawal/end services still pending. Proposal uses source appointment/participation or
scoped head; explicit target role/approve+branch prerequisite. Encrypt proposal reason
bound to participation PK, hash key/reason for command ledger, empty response_json.
Commands atomic under Business lock; stale revision and open duplicate rejected inside
idempotent operation; role checks before replay. No automatic previous-participant end.
Focused session69315 terminal exit0,10 PASS/0.504s;
`%TEMP%/dental-participation-commands-20261122.log`. Additional cross-branch source/target,
foreign Business/target and source-cancel replay negatives added; fixture accepted_at
made explicitly later than proposed_at to avoid clock-resolution dependence.
Completion session93749 terminal exit0: medical242 PASS/16.731s, check PASS,
makemigrations --check --dry-run PASS; `%TEMP%/dental-participation-commands-medical-20261122.log`.
No public API/UI or notifications yet; withdraw/end/revoke pending. Updated access
contract; tracked scoped diff --check clean; new files explicitly checked with
`git diff --no-index --check -- /dev/null <path>` (audit/models/services/tests/migration),
no whitespace findings, only LF→CRLF notices; no-index may return1 for added content.
Full source/migration delta reviewed. HEAD31b90484/current branch unchanged, own WIP
uncommitted/unpublished; working DB untouched, migration0008 only disposable test DB.
No browser/build rerun (backend-only, no new endpoint); no PostgreSQL concurrency proof.
No live sessions. Next withdraw pending by authorized proposer/scoped head, ordinary
and head/security end with obligations, audit and explicit successor; correction24h,
composed clinical ACL, notifications/API/UI remain in full matrix.


Срез27: previous progress appointment prerequisite14/medical216 PASS. M06/M07 code
gap: нет отдельного жизненного цикла продолжающегося участия. Reuse PatientProfile,
BusinessMember, Branch, medical role guards; не дублировать Appointment/VisitPlan.
Контракт состояния: pending→active/declined/withdrawn; active→ended/revoked; terminal
не открывается снова, новый цикл отдельной строкой. pending/declined/withdrawn не
имеют accepted_at, active/ended/revoked имеют; terminal требует closed_at/closed_by.
Предложение и принятие разные факты, proposed_at≤accepted_at≤closed_at. Один незакрытый
цикл на patient/member/branch; история PROTECT, revision≥1, actor/branch сохранены.
Причины хранятся encrypted; обязательность причины и права перехода проверяются
будущими сервисами, не придуманы из schema defaults. Нет automatic accept/expiry.
Первый schema+active-basis слой, не finished scenario: миграция только disposable DB,
DB constraints/tenant validation +fresh role/branch/status tests перед services/API/UI.
No notification/BusinessEvent/AI/provider effects; audits и transactional transitions
следующим связным шагом. Shared model change: focused tests then medical/check/drift.
Implemented TreatmentParticipation +migration0007 and assert_treatment_medical_basis.
Migration inspected: additive CreateModel only, no data rewrite. Focused session35583
exit0,9 PASS/0.108s; `%TEMP%/dental-participation-storage-20261122.log`. Constraint
invalid-state/date/duplicate-open, terminal denial, independent appointment completion,
foreign links and role/branch revocation covered. Test transitions use ORM to verify
storage; this is NOT proof of command authorization/idempotency/audit.
Completion session27019 terminal exit0:medical225 PASS/13.009s, check PASS,
makemigrations --check --dry-run PASS/no drift; `%TEMP%/dental-participation-storage-medical-20261122.log`.
Migration0007 applied only by isolated test DB setup. Scoped diff hygiene PASS; new
model/selector/tests/migration reviewed. No frontend changes: build/browser not rerun.
No PostgreSQL concurrency proof, no production migration/deploy/provider effects.
Full clinical scenario unfinished, no API/UI routes added. HEAD31b90484 same branch,
local WIP uncommitted/unpublished; no live process. Foreign WIP untouched.
Next connected slice: extend existing MedicalAuditEvent with participation/revision and
transition actions; propose/accept/decline/withdraw services under Business lock and
existing command idempotency. Proposer must current participant or scoped head, target
must active medical doctor; invitation does not grant chart; recipient accepts personally.
Then ordinary/head/security end with explicit remaining obligations, correction grants,
composed ACL/read audit/API/UI. State transitions are not currently service-enforced.


Срез26: previous progress S14 mobile acceptance. M06 code gap: role prerequisite
существует, appointment clinical basis отсутствует. Skills zani-change-crm-domain /
zani-run-verification: fresh server authorization, same-Business joins, reuse scheduling,
isolated focused negative/revocation tests before dependent state-machine work.
Первый связный шаг: source-specific appointment basis selector (не полный clinical ACL).
PatientProfile→Client, Appointment→primary staff Resource.linked_user; physical reserved
resources/responsible_user не основание. created/confirmed/rescheduled действительны
по current CRM; terminal/archive не основание. Без 24h cutoff/своего срока истечения:
pending_result остаётся незавершённой записью, завершённый прошлый визит не основание.
Fresh role/member/account/branch check; appointment/Client/service/resource/branch tenant
validated even for malformed links; deactivated specialist is not account revocation.
Returns identifiers only, no PHI; future audited clinical reader must compose accepted
participation/correction grants, read journal and transaction locking before exposure.
No notifications/BusinessEvent/AI output/provider/UI/schema/env changes in this source
selector. Security-sensitive permission prerequisite: not connected to public API yet.
Checks: focused future/current/rescheduled/terminal/reassignment/role and branch revoke,
tenant corruption, no responsible/physical fallback; then medical suite/check/drift.
Focused attempt session99201 exit1:14 tests,13 PASS; test fixture used reserved
Django TestCase.client name (HTTP Client shadows model fixture), AttributeError before
corruption check. Renamed fixture patient_client; product code unchanged. Retry61509
terminal exit0,14 PASS/0.196s; `%TEMP%/dental-appointment-basis-retry-20261122.log`.
Completion session44802 terminal exit0: medical216 PASS/10.830s, Django check PASS,
makemigrations --check --dry-run PASS/no changes. Log `%TEMP%/dental-appointment-basis-medical-20261122.log`.
Scoped diff hygiene PASS; both new source/test files reviewed. Canonical root/branch
unchanged; HEAD31b90484, own uncommitted delta; no working DB/migration/provider/UI changes.
No browser/build rerun: no frontend or reachable API changed. No PostgreSQL race proof:
this prerequisite is not yet a composed transactional clinical reader. No commit/push,
known foreign static-gate blocker retained. No live sessions.
Next: continuing participation invitation/acceptance/end state and audit, separate from
appointment basis; ordinary end checks obligations, medical head override reason/assignee;
then compose clinical read/write scope +24h correction before exposing PHI.
Full M06/M07 still requires continuing participation, obligations, security revocation,
24h grant, head/assistant scope, API/UI and PostgreSQL concurrency acceptance.

Срез25: previous progress — representative recovery + affected regression9 PASS.
Evidence gap: mobile protocol503/retry, self-selection, invalid period400, real role
revocation403 clearing draft. Existing guarded fixture/API/DS reused; test-only change,
no product rewrite. Focused Chromium mobile run + capture/inspect, scoped hygiene.
Session2515 terminal exit0:1 PASS/1.2m, `%TEMP%/dental-representative-mobile-boundaries-20261122.log`.
Mobile390x844: injected representative protocol503 disables save → Retry loads real
protocol; self representative rejected; real invalid period400 retains proof/permissions;
corrected date stays editable; real role revoke →403 closes dialog and removes profile
content, draft absent from local/sessionStorage. Axe wcag2a/aa zero violations.
All3 captures inspected in output/playwright/medical-representative-mobile-boundaries/
medical-patient-representa-fe970-ty-and-real-role-revocation: protocol-unavailable,
retained-draft,role-denied. Mobile fields/errors wrap; long selected name ellipsized
within existing picker; form scrolls to submit (click executed), no layout rewrite.
Scoped diff hygiene PASS. Product code unchanged, prior build still applicable;
backend suites not rerun for browser-fixture/test-only change. No working DB/providers.
S14 local UI evidence now covers6 happy locales/viewports + desktop recovery/stale +
mobile protocol/validation/403. Native mobile OS/provider issuance not proven.
Next M06/M07: no participation model yet; existing MedicalRoleContext explicitly only
role prerequisite. Appointment has primary resource.linked_user, status and optional
branch; inspect additional resources and lifecycle before assigning a clinical basis.
Confirmed source §18.1.3 +§22.6: appointment immediate basis, accepted continuing care,
transfer acceptance, ended/security revocation, correction24h scoped grant, cross-branch
history but branch-bound writes. Must not infer basis from responsible_user or old plan.
No clinical code changed yet; next implement participation state contract/domain/tests,
then audited selectors/API/UI. Full requirements and external approvals remain open.


Срез24: предыдущий ответ на ping — no progress; состояние повторно сверено, HEAD прежний.
Продолжение evidence gap S14: representative keyboard/Escape/focus, axe,503 retry с
сохранением полей и idempotency key; затем stale revoke409 и регрессия patient UI.
Используем существующие реальные browser/API fixtures; fault injection обозначается
отдельно от real API. Product code не меняется без воспроизведённого дефекта.
Срез24 focused session39842 exit0:1 PASS/1.2m; `%TEMP%/dental-representative-recovery-20261122.log`.
Keyboard Enter/Escape/focus, axe wcag2a/aa zero violations, no-permission save disabled,
injected503 retains proof/checkbox/end; real retry201 uses same nonempty key.
`output/playwright/medical-representative-recovery/medical-patient-representa-4cf3c-and-revoke-through-real-API/representative-retry.png`
визуально просмотрен: поля/ошибка/действия читаются, не обрезаны.
Расширение: real competing revoke200 → UI stale409; affected patient6+recovery+boundaries.
Завершённый session43529, `%TEMP%/dental-representative-regression-20261122.log`,
output/playwright/medical-representative-regression; session43529 terminal exit0,9 PASS/2.3m.
Real competing revoke200→UI409 сохраняет reason, disables save, cancel reloads revoked.
Patient6 RU/KK/EN desktop/mobile lifecycle + recovery + boundaries PASS после S14.
Просмотрены representative-conflict.png и RU desktop/mobile profile.png: конфликт
читается, disabled action понятен; desktop layout сохранён, mobile одноколоночный,
нижняя fixed navigation перекрывает нижнюю часть cropped profile capture (доступность
действия при прокрутке подтверждена предыдущими mobile representative flows).
Diff hygiene scoped PASS. Product code в этом срезе не менялся; предыдущий build
остаётся применимым. Рабочая БД/провайдеры/деплой не затронуты, commit/push не выполнены.
Следующий evidence gap: representative-specific missing protocol/retry,403 draft clearing,
self-selection/date validation и mobile recovery; затем клинический ACL из полной матрицы.
Patient-panel403 и missing identity protocol не заменяют эти проверки представителей.
Это scoped evidence, не полная приёмка S14/ТЗ. Процессов этого среза не осталось.

Срез23 S14: previous progress API medical200 PASS. UI gap: нет reachable формы/списка
представителя. Сначала сохранить approved permission labels в encrypted snapshot,
вернуть whitelist labels без зависимости от текущего approve/protocol. Старым
unlabeled grants не придумывать смысл: явный unavailable label state. Затем typed
API + existing ClientPicker/Modal/Input/Select/Textarea/Button, RU/KK/EN, local-memory
drafts, stale/retry/denied handling и scope abort. Применяются zani-review-frontend,
AntiSlop during ui/human/layoutmobile/copywriting, existing design S14/DS; dials1/1/1.
Прикладные требования: никаких новых цветов/шрифтов, mobile controls44px, понятные
подписи/keyboard focus, loading/error/empty/recovery; никаких PHI persistent cache.
Backend label focused gate перед UI; затем build и real API browser/capture+inspect.
Whole goal не сокращается; role issuance/clinical/docs/integrations остаются в матрице.

Label prerequisite PASS: session50071 exit0,34 tests/2.442s, representative API+services,
`%TEMP%/dental-representative-labels-20261122.log`; approved labels сохраняются в
encrypted authority, reader проверяет их полный состав, list возвращает whitelist.
Наличие нового/current протокола или approve не нужно для исторической подписи;
unlabeled snapshot возвращает null. Новой migration нет.
Frontend добавлен: medicalRepresentatives.ts, PatientRepresentatives/RepresentativeForm,
подключение к PatientInBranch; existing ClientPicker, pagination25, approve-gated
verify/revoke, protocol fields/permissions/date range, current Client timestamp,
stable idempotency per payload, conflict/save lock,401/403 denial, memory state only.
RU/KK/EN keys добавлены по accepted S14/actions. Pending browse acceptance.
Build session94132 exit0: npm run build через safe isolated env, types/i18n7703keys/
app/widget PASS; `%TEMP%/dental-representative-ui-build-20261122.log`.
Browser session72225 (6 RU/KK/EN desktop/mobile representative flows), лог
`%TEMP%/dental-representative-browser-20261122.log`, output/playwright/medical-representatives.
Опрашивать этот handle до terminal; timeout наблюдения не причина повторного запуска.
Отдельные fixture Clients сохраняют исходные6 patient lifecycle кейсов; реальные
provider calls/working DB запрещены. Synthetic representative policy только guarded
browser runtime, не внешнее утверждение. Проверить и визуально просмотреть снимки;
после этого ещё нужны errors/recovery/keyboard и регрессия затронутого patient UI.

Session72225 terminal exit1: RU desktop остановлен на неверном test locator combobox;
5 кейсов не запускались. Existing SearchableSelect имеет native button с accessible
name «Представитель Выберите клиента»; screenshot/error-context просмотрены, форма
показывает нужные поля/контролы. Исправлен только locator на button с label prefix.
Повтор session97857, `%TEMP%/dental-representative-browser-retry-20261122.log`,
output/playwright/medical-representatives-retry — terminal exit0,6/6 PASS,1.7m.
RU/KK/EN ×desktop1440x1000/mobile390x844: real ClientPicker/API verify201→list200→
revoke200→revoked list, no horizontal overflow, no proof in local/sessionStorage.
Визуально просмотрены все6 representative-form.png, RU desktop active и RU mobile
revoke: DS сохранена, поля/лейблы/кнопки не обрезаны, mobile одноколоночная форма,
RU footer переносится без горизонтального overflow. Runtime screenshots — synthetic
fixtures, не real patient data. После build production source не менялся; reused PASS.
Gate geometry/purpose/i18n/basic actions PASS в этой границе; keyboard/focus/axe,
recoverable errors/stale/revoked permission и regression прежнего patient UI ещё
открыты. Native iOS/Android не проверены. Следующий шаг — эти boundary checks,
не новый дизайн и не повтор6 happy cases без причины. Новых live handles нет.
Также первый dev-run показал503 mandatory read audit при параллельных StrictMode
запросах SQLite (соседний read200); это не provider failure/PG evidence. UI сохранил
ошибку списка, данными не заменил её. Проверить recovery и причину при повторе.

Срез22 M03 API: previous progress representative domain186+21 PASS. Reuse strict
serializers, reception_context, existing patient route, domain commands and audit.
Добавить paginated list без evidence/контактов, whitelist формы с RU/KK/EN labels,
verify/revoke commands с no-store даже при ошибках. Нет обычного update/delete,
нет owner bypass. Read проверяет Patient/представителя Client view и tenant, пишет
medical audit до возврата. Проверки HTTP happy/replay/stale/denial/foreign/unknown
fields/audit failure; backend gate после coherent API slice. Нет новой migration,
notifications/AI/BusinessEvent/external effects; UI и recipient integration остаются.

Срез22 результат: PatientRepresentativesMixin добавляет list/verify/revoke/form в
существующий `/api/medical/patients/`, без второго router/permission engine. Строгие
serializers, inherited no-store/private/error headers, без generic update/delete.
List25/default,max50, next_offset, authorized Client projection и audit каждого
возвращаемого relation; empty page пишет patient read event. Evidence/approval/
training/revocation reason не раскрываются. AEAD decode вынесен в общий internal
reader с проверкой IDs/периода, одинаковый для списка и authority prerequisite.
Business lock берётся перед fresh reception check, как в command writers.
Form requires полный methods label/field_labels + permission_labels RU/KK/EN;
без них503, valid patient protocol не заменяет representative protocol.

Session56316 exit0:47 PASS,3.322s, check/drift PASS,
`manage.py test apps.medical.tests_representative_api apps.medical.tests_representative_services
apps.medical.tests_patient_api -v 1`; `%TEMP%/dental-representative-api-20261122.log`.
Затем уточнён lock order списка и добавлены3 regressions: actual foreign Patient,
tampered period, incomplete permission labels. Session97373 terminal exit0:
`manage.py test apps.medical -v 1`,200/200 PASS,10.361s; check/drift PASS,
`%TEMP%/dental-representative-api-complete-20261122.log`. SQLite isolation, не PG race.
App build/browser не запускались: frontend в этом срезе не менялся. Новой migration
нет. Клиентские/import suites258 срез20 остаются применимы к unchanged guards.
Следующий gap: S14 UI в PatientAdministrationPanel, существующий Client selector,
typed API client, RU/KK/EN forms, memory-only drafts/abort/denial/recovery и browser
acceptance. Для списка необходимо отображение человекочитаемых полномочий независимо
от доступности approve/form (сохранённые утверждённые labels либо явно закрытый статус);
не показывать коды конфигурации как продуктовые подписи и не придумывать их смысл.
UI/выдача/PG и полный ТЗ остаются открытыми. Все изменения local WIP поверх31b90484;
working DB/инфраструктура не менялись, publication blocker прошлого среза не разрешён.

Срез21 M03: previous progress schema/guards affected258 PASS. Реализовать commands
подтверждения/отзыва представителя: reuse reception medical_patients.approve,
Business/Client locks, CRM idempotency HMAC, AES-GCM и MedicalAuditEvent. Отдельный
server-configured протокол представительства использует общий валидатор evidence,
но не наследует автоматически patient identity approval. Полномочия и обязательность
конечной даты задаются утверждённой конфигурацией; default отсутствует. Revocation
не зависит от доступности протокола первоначального подтверждения. Проверять
роль/филиал/Business до replay, ожидания версий, no PHI в command/audit, rollback,
expiry/revoke boundaries. API/UI/выдача документов после domain gate, не закрывать
M03/M14 только сервисами. Migration audit linkage только isolated DB. Нет отправок,
AI/BusinessEvent или изменений рабочего окружения. Skills/контракты срез20 сохраняются.

Срез21 реализация: representative_services.verify/revoke + representative_policy,
новый пустой MEDICAL_REPRESENTATIVE_POLICIES; общий evidence validator переиспользован
без расширения автоматически approved patient policy. Actor/medical reception/approve/
medical+CRM branch/Client view обоих лиц проверяются до replay. Business и Client locks,
expected Patient revision/representative Client.updated_at, period UTC, explicit permissions;
authority/reason шифруются, HMAC защищает command fingerprints. Связь и MedicalAuditEvent
с её ID/revision коммитятся атомарно; прежнее основание при отзыве неизменно. Отзыв
не требует старого протокола и допускает archived Client. Authority prerequisite
отказывает foreign person/Business/Patient, future/expired/revoked/неуказанному действию;
проверяет AEAD конкретной связи и соответствие периода authenticated snapshot.
Финальная выдача документа должна дополнительно проверить получателя/версию/аудит
и согласовать конкурентный revoke с собственным transaction; эта интеграция ещё открыта.
0006_representative_audit прочитана целиком: nullable linkage/revision, action choices,
constraints; без backfill, применяется только isolated runtime.

Session31523 exit0: focused32 PASS,1.335s (representative services + identity verification),
check/drift PASS; `%TEMP%/dental-representative-services-20261122.log`.
После этого AEAD привязан к allocated representation PK (внутри той же транзакции),
добавлены authority prerequisite и границы времени/ciphertext swap/UTC offset tests.
Session89958 exit0: `manage.py test apps.medical -v 1`,186 PASS,10.024s,
check/drift PASS; `%TEMP%/dental-representative-authority-20261122.log`.
Далее только3 дополнительных negative tests (реальный foreign Client, verify replay
после revoke, unavailable crypto keys); app source неизменен. Focused session33612
`manage.py test apps.medical.tests_representative_services -v 1`, лог
`%TEMP%/dental-representative-negative-20261122.log`: terminal exit0,21/21 PASS,1.032s.
PostgreSQL гонки/HTTP/UI/настоящий протокол/выдача ещё не доказаны. Working DB не менялась.
Следующий шаг: scoped list/form/verify/revoke API c no-store, private evidence projection,
затем S14 reachable UI и browser сценарии; не повторять пройденные backend suites
без изменений затронутых входов. Полная цель и матрица остаются ACTIVE.

Срез20 M03: предыдущий ход progress (boundary gate PASS). Gap code: нет отдельной
связи представителя. Сначала хранение PatientRepresentative на существующих
PatientProfile/Client, шифрованные основания/проверка/полномочия, период и отзыв;
не создавать PatientProfile представителю автоматически. Защитить связь от
обычного merge/смены Business/молчаливой смены проверенного имени через Client.
Skill zani-change-crm-domain: domain invariants, tenant relationships, traceable
lifecycle; zani-run-verification: isolated focused tests + check/migration drift.
Слой хранения не даёт доступа сам по себе: service/approved protocol, audit,
API/UI и recipient enforcement остаются обязательными зависимыми частями M03/M14.
Никаких notification/BusinessEvent/AI/provider effects; отдельная migration только
в disposable DB. Проверки: same-tenant/самопредставительство, сроки/отзыв/версия,
PROTECT, family contacts без дублей, merge/identity guards и сохранение контактов.
Root/base/WIP прежние: canonical PlatformaCRM, codex/ui-testing-toolkit/31b90484;
чужие изменения сохраняются. Документы/возрастные основания внешне не утверждены.

Срез20 focused PASS: session75862 exit0,34 tests/0.310s, check/drift PASS,
`%TEMP%/dental-representative-storage-20261122.log`. Команда:
`manage.py test apps.medical.tests_representative_storage.RepresentativeStorageTests
apps.medical.tests_client_identity_guards apps.medical.tests_patient_profile -v 1`.
Создана intentional0005_patient_representative; прочитана целиком, только CreateModel,
без backfill. После focused изменён только import тестовой fixture на module alias,
чтобы discovery не запускал импортированный чужой TestCase повторно.
Affected gate session21348: check, makemigrations --check --dry-run,
`manage.py test apps.medical apps.clients.tests apps.clients.tests_concurrent_updates
apps.core.tests_import_workspace_engine apps.core.tests_import_workspace_api
apps.core.tests_import_export apps.core.tests_client_import_permissions -v 1`.
Лог `%TEMP%/dental-representative-affected-20261122.log`; terminal exit0,
258/258 PASS,42.397s; check/drift PASS. SQLite isolated runtime, не доказательство
PostgreSQL concurrent race. Новая migration применена только в тестовой БД.
Это schema/guard evidence, не cryptographic/service/HTTP/UI acceptance представителя.
Следующий минимальный зависимый шаг: сервисы проверенного назначения и отзыва с
актуальной reception role/branch/training, утверждённым отдельным протоколом,
проверкой обоих Client, encrypted authority/reason, revision/idempotency и атомарным
medical audit; затем API/UI S14 и проверка срока/отзыва в recipient gate M14.

Срез19 UI boundary evidence: предыдущий ход progress6 lifecycle+1 recovery/build.
Не переписывать проверенные формы; проверить явную смену филиала, delayed old read,
нет протокола503/retry и длинные значения на tablet/mobile, scoped a11y scan.
Reuse existing guarded browser fixture; второй филиал создаётся только explicit
test setup, прежние single-branch fixture/доказательства сохраняются. Production
изменения только если воспроизведён конкретный дефект. Full goal/M matrix ACTIVE.

Срез19 результат: session53127 terminal exit1 — тест ожидал Retry, но одноразовый
503 был потреблён отменяемой загрузкой; следующая загрузка получила200. Исправлен
только test transport:503 сохраняется до явного действия Retry, перед снятием
ошибки проверяется видимость Retry и disabled submit. Production-код не менялся.
Повтор session81122 terminal exit0:1/1 PASS,18.1s тест/1.1m suite, лог
`%TEMP%/dental-patient-browser-boundaries-retry-20261122.log`.
Проверены реальные API create/update/read, смена филиала с задержанным старым
ответом, отсутствие старых данных при загрузке и после возврата,503/retry протокола,
длинные значения, отсутствие horizontal overflow, scoped axe WCAG2A/AA для обеих
форм без violations. Инъекция503 не доказывает реальную аварию провайдера.
Визуально просмотрены tablet-long-form.png/mobile-long-form.png первого прогона
и mobile-long-profile.png повтора в `output/playwright/medical-boundaries*`:
перенос ФИО, ширина полей, одноколоночная mobile/двухколоночная tablet форма,
видимые подписи и кнопки соответствуют существующим компонентам. Native устройства
и весь медицинский модуль не сертифицированы. Предыдущий build остаётся применим:
после него менялись только browser tests/fixture/docs. Рабочая БД не менялась.
Следующий gap M03: представительство отсутствует в apps/medical/models.py;
источники §2.4,§18.1.4 требуют отдельной проверенной связи с основанием,
проверившим, сроком, объёмом полномочий и отзывом, без вывода прав из телефона.
Состав подтверждающих документов/возрастные правила не подменять тестовым протоколом.

Срез18 UI evidence: предыдущий ход progress — формы подключены, browser acceptance
открыта. Использовать isolated_runtime + configure_browser_runtime, отдельные
порты/синтетические profile_v2/medical role/protocol fixtures, реальный Django API.
Добавить воспроизводимый browser gate в existing Playwright test infrastructure,
без рабочей БД/внешних provider calls. Проверить create→edit→verify→correct и ошибки,
RU/KK/EN desktop/mobile; capture/inspect screenshots; final build после fixes.
Ни этот scoped gate, ни тестовый протокол не доказывают весь ТЗ/real approval.
Реализован reproducible gate: frontend/e2e/medical-runtime.py (guarded disposable
DB, random temp crypto keys, synthetic clinic role/protocol, disabled external sockets),
medical-patient.spec.ts и playwright.medical.config.ts. Backend/frontend запускаются
из canonical root, отдельного worker нет (для административных commands не нужен).
Первый run session18835 FAIL: создание201 прошло, prefilled Textarea getByLabel exact
не найден; screenshot/ARIA snapshot показали доступный textbox «Адрес». Selector
заменён на getByRole(textbox, accessible name), без изменения component/ослабления
assertion. Лог `%TEMP%/dental-patient-browser-20261122.log`, сохранённые trace/screens
`output/playwright/medical/`. По visual inspection добавлено имя Client в create
dialog, чтобы сотрудник видел контекст; существующие typography/tokens сохранены.
Session28731 exit0:6/6 lifecycle browser PASS,2.0m; RU/KK/EN ×1440x1000/390x844,
реальный login + Django API create201→preliminary200→verify200→correct200,
актуальное имя и в medical panel, и общей CRM header; no horizontal overflow,
evidence не попадает в local/session storage. Лог
`%TEMP%/dental-patient-browser-retry-20261122.log`, screenshots
`output/playwright/medical-retry/`. Это Chromium viewport, не настоящий iOS/Android.
Session83475 exit0:recovery1/1 PASS,18.3s test/1.1m runtime. Keyboard Enter/Escape/
focus return; injected HTTP503 retains draft and same idempotency key; реальная
вторая API-команда обновляет revision → UI409 сохраняет draft/запрещает save;
cancel reload показывает конкурентное значение. Реальный fixture DB role revoke
→403 следующего POST, UI закрывает dialog и убирает patient data. Лог
`%TEMP%/dental-patient-browser-recovery-20261122.log`, screenshots
`output/playwright/medical-recovery/`. 503 инъекция — проверка UI recovery, не сбой
реального провайдера. Header/permission/mutation API здесь настоящие.
Снимки реально просмотрены: RU create desktop/mobile, RU verify mobile/profile desktop,
KK create desktop/mobile/verify mobile, EN verify desktop/mobile/profile mobile,
retry/conflict/denied. Labels/колонки/переносы/контекст/44px actions без перекрытия;
длинная conflict form прокручивается (Cancel реально доступна и нажата тестом).
Session23121 exit0 final npm run build в safe environment, после name/invalidation
changes: types/i18n/app/widget PASS; `%TEMP%/dental-patient-ui-verified-build-20261122.log`.
5 terminology tests предыдущего среза сохраняют границу,158 backend PASS не менялись
этим frontend/test срезом. Whitespace/compile новых5 scoped files PASS.
Оба browser handles terminal; medical-runtime процессов после cleanup нет.
Working DB/provider/rollout не менялись. Local WIP, no commit/push/deploy, прежний
foreign static blocker сохраняется. Полный ТЗ НЕ завершён: representatives,
patient participation/clinical ACL, clinical records/docs/sign/code distribution,
role UI, read fallback и остальные M/E матрицы впереди. Следующий независимый шаг:
представители пациента и ограничение их полномочий по утверждённым B-правилам;
UI narrow residual: branch/client switch isolation, missing protocol/long values,
tablet/native mobile and full accessibility remain acceptance work, не скрывать.

Срез17 M03/UI: предыдущий ход progress158 medical PASS. Подключить administrative
patient panel внутри ClientWorkspacePage только при явной medical_records capability;
никакого owner role bypass. Выбор существующего филиала, live access/read/API формы.
Skills Anti Slop core/ui/human/layoutmobile/copywriting, zani-review-frontend,
design-taste app: approved DS/Manrope/tokens/Button/Input/Modal, energy/rhythm/motion1.
Применить labels и44px/mobile16px, один столбец mobile/2desktop, retained draft при
recoverable error, PHI только в памяти scoped component (не query/persistent cache).
409 требует пересмотра, ключ повтора сохраняется для неизменного payload; смена
user/business/client/branch уничтожает draft/abort requests. Acceptance: real API
create/edit/verify/correct + errors/denial/keyboard/mobile; types/build/browser.
Реальных keys/protocols/rollout не включать. Внешние проверки и весь остаток сохраняются.
Код: PatientAdministrationPanel + PatientIdentityForm, ClientWorkspacePage entry,
medical RU/KK/EN dictionaries. Ключ компонента scope/user/client отменяет запросы
и очищает memory; medical API не сохраняется в Query cache. Общая branch metadata
использует существующий branchesApi/query. ИИН показан в форме проверки/редактирования,
не постоянной шапке. Protocol fields реальные server schema, no built-in legal list.
Stable caller key для неизменного payload, repeated click guard, conflict409 locked,
permission401/403 clears draft/data. После controlled name correction invalidates
existing CRM card/client queries, без записи PHI в общий cache.
Начальная проверка нашла JSX missing close и i18n fallback order: исправлены.
Terminology gate сохраняет запрет generic labels; exact reviewed exceptions только
medical.fullName/create (доступны в явно включённом medical module). Новый negative
test сохраняет запрет clients.create и medical.unreviewed. Session2970: types/parity
7684 keys/5 terminology tests PASS. No backend changes this slice;158 prior PASS retained.
Build log `%TEMP%/dental-patient-ui-build-20261122.log` содержит завершённые app/widget
builds; wrapper затем упал на CP1251 print Unicode, это не ошибка compiler. Исправлен
только вывод runner. Session46611 exit0 npm run build (safe isolated environment),
лог `%TEMP%/dental-patient-ui-build-final-20261122.log`, types/i18n/app/widget PASS.
Во время последнего build добавлен query invalidation после correction: точная
latest-snapshot build acceptance требует повторной проверки вместе с browser.
Actual UI/browser/screenshots пока НЕ выполнены; формы не приняты. Не объявлять UI
готовым по build. Следующий шаг: isolated real API browser desktop/mobile RU/KK/EN,
create/preliminary/verify/correct, ошибки/retained draft/revoke/409/focus/long text,
capture AND inspect screenshots и final unchanged-input build. Playwright skill
прочитан; npx доступен. Source roots/backend/frontend/worker доказать до localhost.
Current own UI files перечислены выше; foreign auth/integrations WIP сохранён.
Local branch codex/ui-testing-toolkit HEAD31b90484, no commit/push/deploy, goal ACTIVE.

Срез16 M03/D04: предыдущий ход progress,14 HTTP/154 medical/types PASS.
Для настоящей формы verify/correct нужен safe protocol projection: только reference,
методы/поля с RU/KK/EN labels; approval reference и trained member IDs не отдавать.
Reuse единого config validator/evidence validation и reception/approve/branch gate.
Добавить optional presentation metadata к методам; существующие доменные протоколы
без labels остаются совместимы, но UI projection без полного описания503.
Это не утверждение реального протокола и не список нормативных документов.
Проверки: projection/redaction/training/revoke/malformed/missing labels и прежние
verify/correct; без migrations/working DB/external effects. Затем формы UI.
Реализованы общий parser policy, strict optional localized labels, verification_form
projection и GET verification-form/ с current reception/approve/branch/training.
Frontend API typed contract дополнен metadata. Это не клинический/нормативный
справочник и не real approval; никаких реальных настроек протокола не добавлено.
Session49483 exit0:158 medical tests PASS,6.654s; check/drift PASS, isolated DB.
Лог `%TEMP%/dental-verification-form-20261122.log`; command `manage.py test apps.medical -v 1`,
затем check и makemigrations --check --dry-run. Проверены redaction, required/optional,
три локали, неполные/лишние/пустые labels503, training/permission/owner403 и verify
с новым описанием; прежние unlabeled verify/correct tests тоже PASS.
Session27633 exit0: `npx tsc -b` PASS. UI/browser/build ещё не выполнены: screen
не подключён. Документы access/operations обновлены, прежние gates ядра не повторялись
без изменений. Local WIP/branch/HEAD и blocker publication прежние; рабочая БД нетронута.
Следующее: реализовать формы с актуальными API и проверить reachable desktop/mobile.
App-screens.md sections300–900 теперь прочитаны; предыдущие начала/конец сохранены;
комбинированное чтение240–300/frontend checklist было усечено, перед UI дочитать их
отдельно. Approved DS имеет приоритет перед случайным draw и эстетическими заменами.

Срез15 M03/D03: после восстановления цель/HEAD/dirty сверены; ответ на ping
не являлся progress, работа продолжена. Перед UI добавить безопасную серверную
проекцию текущих reception actions в выбранном Business/branch: shared CRM owner
bypass неприменим. Reuse reception_context/assert_medical_branch_permission,
no-store; без PHI, списков сотрудников или новых разрешений. Это подсказка UI,
не authorization token: каждая команда по-прежнему проверяет актуальные права.
Проверки: exact actions, revoke между запросами, owner/doctor/foreign branch denial,
strict query/no-store; затем affected medical API/roles. Без migration/env/AI/
notification/BusinessEvent effects. UI и protocol metadata остаются следующим
зависимым шагом; весь объём матрицы сохранён. Root/branch/HEAD прежние, foreign WIP
не меняется, publication blocker предыдущего среза остаётся.
Реализован GET access/ и typed frontend/src/api/medicalPatients.ts через общий
apiClient: scope/types, AbortSignal, caller-owned обязательный Idempotency-Key
(повтор команды сохраняет тот же ключ), без persistent storage/query cache.
Session98345 exit0:14 HTTP PASS,0.644s; лог
`%TEMP%/dental-patient-access-20261122.log`. Owner/doctor/invalid branch/query denial,
exact action revoke и assignment revoke проверены; projection не читает PHI.
Статус approve означает role permission, не заменяет protocol/training проверки.
UI пока не подключён, runtime browser/build проверка остаётся обязательной.
Session80891 exit0:154 medical tests PASS,6.248s; manage.py check и
makemigrations --check --dry-run PASS, изолированная БД; лог
`%TEMP%/dental-patient-access-dependent-20261122.log`. Core Client/import writers
не изменены этим срезом, их предыдущие evidence остаются с прежней границей.
Session89166 exit0: `npx tsc -b` PASS. Никакого runtime UI PASS это не доказывает.
Следующий шаг: metadata утверждённого identity protocol для человеческих labels
и формы пациента в существующем ClientWorkspacePage; UI skills/design сохранены.
Design-taste SKILL прочитан до150 (app routing); app-screens.md1199 строк слишком
длинный вывод был усечён: до markup прочитать недостающие разделы порциями.
Срез15 local WIP, не commit/push/deploy; working DB/реальные протоколы не затронуты.

Срез14 M03/D03/D07: предыдущий ход progress (31/161 PASS), цель/HEAD/WIP сверены.
Подключить административный patient workflow к HTTP: reception-only routes для
create/read-by-client/read-id/preliminary-update/verify/administrative-correction.
Reuse Client permissions + medical exact role/branch + existing services; никакого
TenantModelViewSet owner bypass/автоматического общего PHI audit. Read возвращает
только идентификационные/контактные поля и версии, не clinical/evidence/history.
Чтение требует успешного MedicalAuditEvent до возврата; при сбое503 без данных.
Резервный журнал/denial audit ещё остаются отдельными требованиями D07, не считать
их выполненными. No-store на ответы/ошибки, строгие поля, HMAC idempotency headers,
без generic PUT/PATCH/DELETE/list/export. Эти first administrative endpoints не
заменяют будущие doctor/assistant clinical routes и не включают dentistry_v2 rollout.
Focused HTTP tests: lifecycle/create/replay/update/verify/correct/read, unauth/owner/
role/branch/tenant denial, audit/key failures, no cache/PHI leak, stale/unknown fields;
affected medical/client + check/drift. UI/frontend следующим срезом после backend.
Реализованы patient_selectors/read_patient_administration, строгие serializers,
PatientAdministrationViewSet и router `/api/medical/patients/`. POST ответ содержит
только id/client_id/revision/identity_status/replayed. Read с current reception/branch/
CRM Client view блокирует архив/foreign и пишет READ event до возврата; отсутствие
ключа/аудита503 без PHI. Врач/owner без reception не используют этот administrative
surface; будущие clinical routes обязаны реализовать отдельный patient basis.
Session16759 exit0:9 focused HTTP PASS,0.448s, `%TEMP%/dental-patient-api-20261122.log`.
После этого добавлены stale409, protocol503 и permission revoke/archive tests.
Session18944 exit0:173/173 PASS,24.497s, check/drift PASS,
`%TEMP%/dental-patient-api-dependent-20261122.log`; isolated commands:
`manage.py test apps.medical apps.clients.tests apps.clients.tests_concurrent_updates -v 1`,
`manage.py check`, `manage.py makemigrations --check --dry-run`.
Проверен полный HTTP create→read→preliminary→verify→correct→by-client read,
idempotency, strict fields, owner/doctor/unauth/foreign/branch revoke, no-store,
read-audit/key failure, no generic mutations/list. Fallback journal и отдельный
denial audit ещё не реализованы; при отказе основного журнала чтение fail-closed.
Новые33 medical Python files compile/whitespace, scoped docs/router diff hygiene PASS;
intended source просмотрен. UI/browser/build ещё N/A, frontend не изменён.
Это локальная API-проверка с синтетическими v2 role/protocol fixtures; реальные
профили/роли/протоколы/working DB не настраивались, rollout не выполнен. PostgreSQL
race/live provider/production readiness не доказаны. Local WIP codex/ui-testing-toolkit/
31b90484; commit/push/deploy нет, предыдущий foreign static blocker не изменён.
Следующее: frontend административного профиля на утверждённой DS и реальные browser
flows; ИИН/перепривязка/head approval, representatives, clinical ACL/read fallback
и остальные строки матрицы сохраняются в scope. Полная цель активна.

Срез13 M03/D04/B04: предыдущий ход progress (215 affected/20 verify PASS).
Добавить controlled correction имени/даты рождения/пола/адреса verified пациента:
обученный reception, medical_patients.update + approve, current branch/Client view,
обязательные причина/recheck evidence по действующему протоколу и обе версии.
Сохранить старые encrypted identity/evidence и автора, атомарно изменить Client
имя и Patient demographics/revision/evidence с medical audit/HMAC replay. Обычный
Client writer по-прежнему запрещает такую запись. ИИН/перепривязку этот сервис
не принимает: отдельный workflow с head approval при clinical history остаётся
в полном scope, не считать его реализованным. Подписанные документы не изменяются.
Reuse existing verification context/history/audit; это обоснованное выделение
общей авторизации для второго сценария, не новый permission engine. Проверить
reason/protocol/training/role/revocation/stale/replay/audit rollback/Client guards,
encrypted SQL/history/foreign scope + affected medical/client/import suites.
Миграции/провайдеры/AI/уведомления/UI N/A; working DB не затрагивать.
Реализован correct_patient_administrative_identity с общим _verification_context;
initial verify использует ту же свежую авторизацию, сохранены его negative tests.
Client name меняется только внутри locked transaction с recheck/history/audit,
не через публичный bypass ordinary writer. Старые evidence/verified_by/time и
идентичность сохраняются в PatientIdentityRevision; ИИН/client link неизменны.
Session37188 exit0:31 PASS,1.506s, `%TEMP%/dental-identity-correction-20261122.log`
(`apps.medical.tests_identity_corrections` + `apps.medical.tests_identity_verification`).
Session92384 exit0:161 PASS,22.502s, check/drift PASS,
`%TEMP%/dental-identity-correction-dependent-20261122.log`; isolated commands:
`manage.py test apps.medical apps.clients.tests apps.clients.tests_concurrent_updates -v 1`,
`manage.py check`, `manage.py makemigrations --check --dry-run`.
Import suites не запускались повторно: их PASS в срезе12, Client/import code/config
и fixtures после него неизменны; correction новый private domain writer, shared
verification/history проверены medical suite. Это не PostgreSQL concurrency proof.
29 medical Python files compile/whitespace и scoped docs diff hygiene PASS;
intended source просмотрен. UI/build N/A, публичного medical API пока нет.
Local WIP на codex/ui-testing-toolkit/31b90484; commit/push/deploy не выполнялись,
общий static blocker чужого WIP не затронут. Working DB/протоколы/ключи неизменны.
Следующие критерии: ИИН/перепривязка/head approval с clinical history, представители,
patient ACL/read audit/API/UI; полный M03/D04/E1 не закрыт, цель активна.

Срез12 M03/D04 §22.3 п9–12: предыдущий ход progress (199 PASS), цель/HEAD/WIP
сверены. Реализовать initial identity verify без исправления verified истории.
Обученный reception + явное medical_patients.approve, current branch/CRM Client
view, expected_revision, проверенный конфиг протокола конкретного Business.
Перечень документов/поля фиксации не выдумывать: server configuration по внешне
утверждённому протоколу, approval reference/method schemas/trained member IDs,
по умолчанию отсутствует и verify503. Реальные approvals не создавать. Config
является техническим входом для подтверждённых данных, не юридической экспертизой.
Operation: Client/Patient locks, decrypt/validate stored identity, no verified IIN
collision, encrypted evidence/prior revision + mandatory audit + idempotency atomic.
Replay проверяет свежие rights/training/protocol; no PHI в command store/audit.
Verify не меняет Client или идентичность, не даёт clinical ACL. Focused tests:
missing/invalid protocol, training/role denial, schema/revision/replay/duplicate,
alternative identity, decrypt/key failure/audit rollback, Client guard afterverify;
affected medical/client suites + check/drift. Никаких migrations/live/UI/providers.
Реализованы identity_policy/identity_verification и общий retain_identity_revision.
Протокол/обучение перечитываются до replay; schema fields/values ограничены, поля
фиксации выбираются внешним протоколом, не зашиты как нормативный перечень.
Role kind reception обязателен, одной approve permission у doctor/owner недостаточно.
Evidence хранит source Patient revision, Client updated_at, full_name snapshot,
encrypted demographics/IIN, protocol/approval reference, method fields и branch;
всё зашифровано, общий command store получает HMAC, audit только IDs/revision.
Focused session53208:29 PASS,1.142s, `%TEMP%/dental-identity-verify-20261122.log`
(verify + update history). При review обнаружен stale Client риск: изменение
предварительного имени не увеличивает Patient revision. Добавлен обязательный
expected_client_updated_at; частичный Client.save(full_name) теперь обновляет
updated_at. Предыдущее guard closure199 PASS → новый verification scenario →
минимальная дельта timestamp и regression test; обычный contact/editor flow сохранён.
Affected session50323 exit0:215 PASS,41.425s, check/drift PASS,
`%TEMP%/dental-identity-verify-dependent-20261122.log`; isolated commands:
`manage.py test apps.medical apps.clients.tests apps.clients.tests_concurrent_updates apps.core.tests_import_workspace_engine apps.core.tests_import_workspace_api apps.core.tests_import_export apps.core.tests_client_import_permissions -v 1`,
`manage.py check`, `manage.py makemigrations --check --dry-run`.
После этого добавлены4 boundary tests: foreign patient/branch, JSON environment,
missing crypto key, malformed protocol/training schema. Session54895 exit0:
20/20 PASS,0.735s, `%TEMP%/dental-identity-verify-boundaries-20261122.log`, команда
`manage.py test apps.medical.tests_identity_verification -v 1` в isolated runtime.
App source после215 PASS не менялся. Новых migrations нет. Scoped diff hygiene/
compile27 medical files PASS. Полный intended source этого среза просмотрен.
Local WIP codex/ui-testing-toolkit/31b90484; commit/push/deploy не выполнялись,
общий static blocker чужого evidence не изменён. Working DB/ключи/протоколы не
настраивались. Реальных медицинских/нормативных утверждений нет. Следующие критерии:
controlled correction/recheck/approval, представители, patient ACL и API/UI,
read audit fallback, PostgreSQL concurrency. M03/D04/E1 не закрыты целиком.

Срез11 D04/B04: предыдущий ход progress (111 PASS/1 PG skip), цель/HEAD/WIP
сверены. Закрыть обход controlled correction через изменение Client.full_name
после verified identity и перенос Client в другой Business при любом профиле.
Общие metadata/contact edits и unverified name остаются доступны по прежним правам.
Reuse Client.save/import и conditional update_client_snapshot; Client row lock
сериализует guard с будущей verify/correct командой. Обычный QuerySet writer
проверяется отдельно, поскольку save не вызывается. Не добавлять публичный bypass.
Scope: medical guard, Client model/save и snapshot writer, focused tests + existing
clients concurrent updates/import suites, check/drift. Без миграции/UI/AI/events/
уведомлений; штатный audit отказанной операции не пишет ложный success.
Реализован assert_client_identity_write_allowed в medical; его вызывают Client.save
и conditional update_client_snapshot под Client row lock. Save также проверяет
новый Python-object с явно указанным уже существующим PK. Импорт получает отказ
через существующий save, без отдельной копии политики. Same-name/contact metadata
разрешены; отключение medical capability не снимает ограничение verified имени.
Session62247:20 tests,19 PASS/1 FAIL — новое ожидание normalized_phone ошибочно
содержало `+`; исправлено по существующему normalize_phone без изменения продукта.
Лог `%TEMP%/dental-client-identity-guards-20261122.log`. После review добавлены
existing explicit PK denial/new explicit PK creation и правильный DB alias guard.
Session69721 exit0:199/199 PASS,40.413s; check/drift PASS,
`%TEMP%/dental-client-guards-dependent-20261122.log`. В isolated runtime:
`manage.py test apps.medical apps.clients.tests apps.clients.tests_concurrent_updates apps.core.tests_import_workspace_engine apps.core.tests_import_workspace_api apps.core.tests_import_export apps.core.tests_client_import_permissions -v 1`,
`manage.py check`, `manage.py makemigrations --check --dry-run`.
Покрыты API owner denial, direct/partial save, module off, stale object/version,
import refusal/no false success audit, unverified/ordinary edit, contact normalization
и прежние CRM/import сценарии. Это SQLite, PostgreSQL race ещё не доказан.
Diff hygiene и compile/whitespace4 changed Python files PASS. Все intended source
изменения просмотрены; UI/build N/A для этого backend среза. Новых миграций нет;
working DB/внешние системы неизменны. Локальный WIP, не commit/push/deploy;
предыдущий общий static blocker в чужом evidence не изменялся. Следующие критерии:
verification/correction с причиной/повторной проверкой/согласованием и identity
history, затем patient ACL/API/UI. Medical protocol/documents/training confirmation
внешне не утверждены; сам guard не означает готовую проверку личности или МЦС.

Срез10 M03/D04: предыдущий ответ «тут» — no progress; цель перечитана, HEAD/WIP
сверены, доступная независимая работа продолжается. Добавить изменение только
предварительного unverified профиля (§22.6 п.3–4): свежая medical_patients.update
и CRM Client view, Business/Client/Patient lock, expected_revision, обязательная
причина, зашифрованная предыдущая версия и атомарный audit/idempotency.
Verified-профиль требует отдельного correction/recheck workflow, не этого writer.
Переиспользовать crypto/role/command/audit. Риск PHI/auth/concurrency; проверить
denial/revoke/tenant/stale/replay/verified/duplicate IIN/audit rollback/encryption.
Миграция history только в isolated runtime. Skills domain/access/verification;
UI/уведомления/BusinessEvent/AI/провайдеры не затрагиваются. Технический slice
не закрывает M03, подтверждение личности, клинический ACL или публичный UI.
Результат: update_unverified_patient_profile и PatientIdentityRevision/migration0004
реализованы. Полная замена предварительных demographic/IIN полей требует причины;
предыдущая версия/имя/причина зашифрованы с AAD Business/patient/revision. Обычные
контакты Client не изменяются. Verified identity этот сервис не редактирует.
Первый focused run session52458:12 tests/6 errors — purpose `identity-revision:1`
не соответствовал существующему строгому crypto regex. Исправлено на
`identity_revision_1`, правила crypto не ослаблены. Session18819:15/15 PASS,0.486s,
`%TEMP%/dental-patient-update-fixed-20261122.log`; прежняя ошибка сохранена в
`%TEMP%/dental-patient-update-20261122.log`. Проверены encrypted SQL/history/reason,
revision conflict, denied/revoked role/branch/module, foreign/archived patient,
verified collision, missing encryption key и audit rollback. Replay после второго
изменения возвращает текущую версию, не восстанавливает прежний ИИН.
Affected session48839 exit0:112 total,111 PASS/1 PostgreSQL skip,18.986s,
`%TEMP%/dental-patient-update-dependent-20261122.log`; команды isolated runtime:
`manage.py test apps.medical apps.clients.tests apps.core.tests_idempotency_prune -v 1`,
`manage.py check`, `manage.py makemigrations --check --dry-run` — PASS.
Skip остаётся select_for_update idempotency-prune concurrency; PostgreSQL clinical
concurrency пока не доказана. Migration0004/roundtrip только изолированно, рабочая
БД/ключи неизменны. Scoped docs diff hygiene и compile/whitespace всех22 medical
Python files PASS. Публичного API/UI ещё нет, браузер/build этому backend срезу N/A.
Следующее: guard общих Client writers + контролируемый verify/correct и patient ACL.
Обнаружены конкретные пути: `apps/clients/updates.py` делает QuerySet.update;
`apps/core/import_workspace/entities.py` сохраняет изменённые поля через save.
Проверка только serializer или Client.save не покроет оба пути. Не переписывать
их без сохранения существующего expected_updated_at и import acceptance.
Код остаётся local WIP на codex/ui-testing-toolkit/31b90484, commit/push/deploy нет;
общий static blocker в чужом WIP по-прежнему не исправлялся. Полная цель активна.

Срез9 M03/D04/D07: предыдущий ход progress (96 PASS/1 PG skip), owner-clinician
вопрос остаётся pending, независимая работа продолжается. Создание PatientProfile
через действующую medical_patients.create роль + текущий branch scope и CRM Client
view, под Business/Client lock. Профиль всегда unverified; даты/пол/адрес и ИИН
шифруются, контакты не копируются. Проверенный совпавший ИИН другого Client
блокирует создание без раскрытия ID; совпавший семейный телефон не объединяет.
Общий CRMCommandIdempotency переиспользуется, но PHI payload передаётся туда только
как keyed HMAC fingerprint; ответ кэша без содержимого. Новая medical audit таблица
с фиксированными action/result/ID/revision, без произвольного metadata/text.
Create + обязательный audit + command result атомарны; audit/key failure всё
откатывает. Никакой клинической верификации по одному формату ИИН, API/провайдеров,
рабочей миграции или медицинской активации. Tests: allowed/revoke/replay,
foreign/owner/no role, encrypted at rest/SQL, same-phone clients, known verified
duplicate, audit rollback, key missing, schema/check/drift и affected clients.
Skills access/domain/verification продолжаются; требования UI неприменимы здесь.
Session25592 exit0:13/13 PASS,0.284s, `%TEMP%/dental-patient-create-20261122.log`.
Проверены SQL at-rest без открытого ИИН/адреса/даты, replay и rollback audit.
После этого добавлены CRM denial, foreign verified ИИН, missing HMAC key и DB audit
constraints. Affected session63256: `%TEMP%/dental-patient-create-dependent-20261122.log`
(весь medical, clients, shared idempotency prune): exit0,97 total,96 PASS/1 skip,
15.497s; check/drift PASS. Skip — PostgreSQL/select_for_update prune concurrency,
не доказательство clinical create concurrency. Миграция0003 применялась только
в изолированной БД; полный medical migration roundtrip existing test также PASS.
Реализация также HMAC-обрабатывает сам idempotency key, чтобы произвольный входной
ключ не сохранял PHI в общем command store. Создана migration0003 medical audit,
реальная БД/ключи/инфраструктура не менялись. Read fallback/denial audit ещё не
включены; primitive writer сейчас вызывается только созданием пациента.
Следующий незакрытый критерий: ручное подтверждение личности по процессу клиники,
её версия/исправления и запрет обхода через общие Client writers, затем API/UI.
Patient participation/encounter/documents/files и резервный read journal остаются
в полном scope. Scope9 не закрывает M03/D04/D07 целиком. Новые файлы просмотрены,
scoped diff hygiene PASS в срезе10; commit/push по-прежнему не выполнены из-за
ранее зафиксированного общего static blocker в чужом WIP. Внешних отправок нет.

Срез8 M02/D03/Q02: предыдущий ход progress; исходный HEAD31b90484/WIP сохранён.
Добавить атомарные owner-only definition/assign/revoke services поверх существующих
BusinessRole/RolePermission, MedicalRoleAssignment и CRMCommandIdempotency.
Сначала свежая авторизация владельца под Business lock, затем member/role/assignment.
Выдача другим активным сотрудникам, точные действия/вид работы/филиалы; самовыдача
запрещена. Отзыв работает и при выключенном medical модуле/сотруднике, история
остаётся; изменение назначения требует revision. Replay проходит свежую авторизацию,
не восстанавливает отозванные права и не удваивает audit. В audit только ID,
вид полномочий, scope/revision, без PHI и произвольных медицинских текстов.
CRM membership/business_role и филиальные grants не переписываются автоматически.
Сбой audit откатывает права/назначение/idempotency. Нет API/UI или внешних отправок
в этом срезе; clinical patient basis остаётся отдельной следующей работой.
Skills прежние access/domain/verification. Focused: grant/revoke, stale revision,
replay/hash mismatch, owner transfer/inactive/support, foreign member/role/branch,
self/assistant restrictions, audit rollback и сохранение CRM grants; isolated tests.
Реализованы create_medical_role/assign_medical_role/revoke_medical_role. Definition
использует явные immutable medical_* BusinessRole/RolePermission, generic role
editor не меняет medical preset, в том числе после stale validate. Assign не
меняет CRM role/BranchAccess; network scope требует существующего CRM network
grant. Revoke не требует активного medical capability/target membership.
Session10580 exit0:16/16 PASS,0.328s,
`%TEMP%/dental-medical-role-services-20261122.log`. После этого добавлены branch
rollback, invalid IDs и stale role-definition save tests. Affected session43578:
`%TEMP%/dental-medical-role-command-dependent-20261122.log` — medical/settings-team/
role visibility/employee access/idempotency prune: exit0,97 total,96 PASS/1 skip,
5.532s; check/drift PASS. Skip — IdempotencyPruneConcurrencyTests требует
select_for_update/PostgreSQL; это не подтверждение конкурентности на production.
Новых schema changes в этом срезе нет. Новые helpers/definitions/commands проверены
в изоляции; API/UI, назначение прав владельцу как врачу и patient basis ещё открыты.
Отдельный owner decision pending (async вопрос отправлен): ТЗ разрешает владельцу
получать клинические полномочия отдельно, запрещает самовыдачу, но не определяет
подтверждающего для самого владельца. Предложено другое действующее head/deputy
в своей области, без самоназначения owner в head. Пока такого разрешения нет,
owner→self assignment не включён; это блокирует только этот сценарий, не весь goal.

Срез7 M02/D03: предыдущий ход progress (97 PASS). Проверены актуальные shared
can/get_membership/RolePermission writers: owner/platform bypass и кеш непригодны
для PHI; произвольные resource сейчас принимаются RolePermissionSerializer.
Добавить MedicalRoleAssignment к существующему BusinessMember с FK BusinessRole,
типом медицинской работы, явной областью филиалов, автором/отзывом/revision.
Это дополнительное медицинское назначение, не второй общий role/permission engine:
действия остаются в RolePermission. Один assignment/member; заместитель — head
с назначенными scope/actions. Clinical role check всегда перечитывает account,
membership, assignment, role/rule; без wildcard/manage fallback или owner/support
bypass. Branch check не расширяет CRM branch scope и не выдаётся за разрешение
всей карты: patient participation/24h/support grants будут следующими слоями.
Закрыть общий permission writer/visibility для medical_* ресурсов до специального
сервиса выдачи; обычные CRM правила не менять. Нет новых публичных medical API.
Skills zani-review-access/change-crm-domain/run-verification; риск auth/tenant/
revocation. Focused: exact permission, отсутствие/отзыв/кеш, owner/platform,
cross-Business role/branch, assistant kind, generic-writer denial, ordinary preserve.
Миграция только изолированно; создание реальных назначений не выполняется.
Срез7 evidence: session58388 exit0,15 focused PASS,0.091s,
`%TEMP%/dental-medical-role-access-20261122.log`; session36730 exit0,
100 affected PASS,53.226s, check/drift PASS,
`%TEMP%/dental-medical-role-dependent-20261122.log` (medical + role visibility/team/
access/permission reads). После этого добавлен отказ team DELETE409 для истории
назначений вместо ProtectedError500, отключение member остаётся разрешённым.
Self-grant отвергается; обычный role-permission PATCH перепроверяет свежую строку
под lock после validate. Session12053 exit0,32 PASS,0.410s, check/drift PASS,
`%TEMP%/dental-medical-role-writers-20261122.log`.
При review найден отдельный stale-input риск в existing accessible_branches:
business.owner_id/user platform flags на переданных объектах. Medical branch
wrapper теперь читает их заново перед пересечением scope; общая CRM не меняется.
Focused повтор session13993 exit0:22/22 PASS,0.214s,
`%TEMP%/dental-medical-role-fresh-branch-20261122.log`. Проверены актуальные owner/
platform flags при пересечении branch scope. Предыдущие100/32 проверки относятся
к своим снимкам,22 — к последней дельте; counts не суммируются. Новые fields/schema
после check/drift32 не менялись. Scope среза — prerequisite роли/филиала и shared
writer/history guards; grant/revoke сервис с аудитом, patient participation и
medical API/UI ещё не реализованы. PostgreSQL concurrent acceptance остаётся.
Рабочая БД/инфраструктура/назначения не менялись; root/branch/HEAD подтверждены:
PlatformaCRM, codex/ui-testing-toolkit,31b90484; чужой WIP сохранён. Публикация не
выполнена, прежний full-static блокер чужого EOF остаётся отдельным.

Срез6 (M03/D04/D07), предыдущий ход — progress: plan gates/rollback и bounded
queries проверены; новый код не повторяет этот срез. Добавить изолированный
медицинский криптографический слой на уже установленном cryptography AES-GCM:
отдельные явно настроенные ключи, аутентифицированная привязка к Business/subject/
purpose, HMAC ИИН с областью Business и отдельным ключом поиска. Не использовать
ключи коннекторов/SECRET_KEY и не писать открытый ИИН в exception/log. Проверка
формата не подтверждает личность; принятие доказательств и медицинский ACL идут
следом. Scope apps/medical + config key inputs; без API, рабочего key provisioning,
БД, уведомлений, AI и внешних отправок. Риск PHI/configuration; focused tests:
roundtrip/random nonce, tamper/cross-tenant/cross-subject/purpose denial, missing/
invalid key, old key read after encryption-key rotation, tenant HMAC и формат.
Повторно применяются zani-change-crm-domain/zani-review-access/zani-run-verification.
Crypto focused11/11 PASS,0.031s (`%TEMP%/dental-identity-crypto-20261122.log`).
Следующая связная дельта M03/M04: PatientProfile OneToOne Client, зашифрованные
административные сведения/доказательство, tenant-scoped verified ИИН uniqueness,
DB verification-state constraints и PROTECT удаления Client. Обычный merge/dry-run
блокируется до переноса связей при профиле любой стороны независимо от capability;
архив не уничтожает профиль. Создание/проверка через API пока не публикуется до ACL.
Изолированная миграция, тесты ограничений/tenant validation/merge rollback/архива;
обычные clients suites остаются обязательной affected boundary.
Patient focused: первоначальный запуск65199 FAIL по тестовой фикстуре `self.client`
(Django заменяет её HTTP client), production-код не менялся для обхода failure.
Фикстура переименована в patient_client; session21278 exit0:20/20 PASS,0.045s,
`%TEMP%/dental-patient-schema-fixed-20261122.log`. Затем добавлены API409/no leak
и empty-schema migration roundtrip/no backfill. Affected session44759:
`%TEMP%/dental-patient-dependent-20261122.log` — medical, clients, payments,
plan payments, visit plans: exit0,97/97 PASS,42.206s; check и migration drift PASS.
Проверены API merge/preview409 без содержимого, отказ до snapshot/переноса плана,
PROTECT Client и сохранение профиля при архиве. Миграция вперёд/назад проверена
только на пустом medical schema с сохранением существующего Client и без backfill;
это не разрешение отката с клиническими данными. PostgreSQL race/реальное управление
ключами остаются открыты. Рабочие ключи/БД не менялись.
Следующий срез M02/M03: явные медицинские полномочия поверх membership/RolePermission,
затем сервис создания/подтверждения профиля с tenant validation, шифрованием,
ревизией/идемпотентностью и обязательным аудитом. У модели пока нет публичного
writer/read API/admin: schema clean() не выдаётся за полную серверную авторизацию.

Возобновление после ответа «тут»: предыдущий ответ был no-progress; файл активной
цели перечитан полностью, Git подтверждён на31b90484, чужой WIP сохранён.
Session23251 получен exit0:45 tests PASS,4.333s, лог
`%TEMP%/dental-profile-plan-access-20261122.log`.
Дополнительно найден финансовый путь `allocate_completed` из завершения записи:
`require_current_terms` теперь проверяет plan_payments перед распределением.
План без финансовых условий сохраняет прежний no-op. Session23782 exit0:
47 tests PASS,5.628s, `%TEMP%/dental-profile-plan-effects-20261122.log`.
После этого добавлен полноценный regression completion rollback/recovery;
его результат не включён в47. Запуск80492:
`%TEMP%/dental-profile-plan-dependent-20261122.log` — payments/corrections/
termination/migration, profile-plan access и B301/B5:72 total,62 PASS/9 skips/
1 FAIL (client card42 queries >40); check/drift не запускались после failure.
Rollback/recovery тест прошёл. Причина performance: общий plan selector повторно
вызывал публичный step selector с тем же module gate. Выделен внутренний scoped
selector; оба публичных входа сохраняют свежую проверку, вложенный путь не дублирует.
Повтор после изменения входов: session75347,
`%TEMP%/dental-profile-plan-dependent-fixed-20261122.log`: exit0,72 total,
63 PASS/9 skips,26.872s. Девять select_for_update concurrency-тестов пропущены
в SQLite, PostgreSQL evidence остаётся открытым. Check и migration drift PASS.
Карточка клиента40≤40 SQL, scaled41 в отдельном разрешённом scaling-бюджете;
dashboard65, inbox11, остальные B301/B5 budgets PASS. Порог не изменён.
Scope среза: серверное ограничение планов/плановых денег и rollback завершения,
не medical ACL, не UI и не D02 rollout. Следующий остаток: PostgreSQL/profile
миграции, UI profile availability и M02–M04 (клинические ACL/идентичность).
Scoped diff hygiene PASS для шести изменённых production-файлов; полный static
по-прежнему отдельно заблокирован чужим EOF, публикация не выполнена.

Срез5: verified gap — profile flags присутствуют, plan_access/selectors проверяют
только старые clients/appointments. Добавить два mappings в существующий resolver,
visit_plans gate в общий plan context и оба selectors, plan_payments в денежный
guard. Отключённая денежная проекция возвращает None, не скрывает разрешённый план.
Риск чтения/денег; тесты core deny/dental allow/legacy preserve, отзыв и selector
leak, без изменения переходов или денежных значений. Затем affected plan suites.

Срез4, возобновление: session6804 exit0, HTTP тест PASS1/1,1.421s (200 без сферы,
409 при явном other), лог сохранён. Предыдущий ход — прогресс, не ожидание.
Следующая дельта: единый initializer принимает только новый несохранённый Business;
повтор уже совпадающего профиля no-op, сохранённый legacy не переинициализируется.
Выбор core_v1/dentistry_v1 серверный, medical v2 пока не запускается до готовности
модуля по D02. Создание Business/capability rows/метки/audit атомарно; audit failure
откатывает создание. Проверки: состав разных сфер, неизвестная сфера, подделка
metadata, повтор/дрейф, rollback, отсутствие медицинской активации. После focused
PASS подключить существующие create paths без дублирования членства/подписки/локации.

Возобновление22.11: новая активная цель из
`C:/Users/user/.codex/attachments/a097bc69-fa2d-4da1-9c73-87db5abb1f50/goal-objective.md`
полностью прочитана; сохраняет полный объём. Прежняя цель была остановлена владельцем,
новая явно разрешает продолжение. Матрица и согласованное ТЗv1.2 переиспользуются.
Session38320 больше не существует; её полный лог содержит окончательный PASS30/30,
6.948s: dashboard65≤70, inbox11≤12, остальные B301/B5 поверхности в бюджете.
Это подтверждение последней оптимизации, не повтор старого неуспешного запуска.

Срез3: защита существующих writers. Под lock Business проверять неизменность сферы
полного профиля, запрет шаблона/onboarding, защиту capability PATCH с повторной
авторизацией и audit в той же транзакции. Одинаковый bool — no-op; legacy старые
ключи сохраняют редактирование, новые служебные не редактируются. Read-only metadata
в admin дополняется проверкой сохранения. Не включать публичную инициализацию до
проверки оставшихся signup/landing путей. Риск permissions/tenant/atomic audit;
tests: stale instance,403/409/400, rollback audit failure, no-op, normal legacy.

## Поручение и граница

Владелец включил цель полной реализации 22.11.2026. Полный текст поручения прочитан
из `C:/Users/user/.codex/attachments/0a6c306b-cc62-45c1-b451-3f11d58d322b/goal-objective.md`.
Источник требований: `C:/Users/user/Desktop/PLATFORMA_CRM_DENTAL_TECH_SPEC_v1_2_2026-11-22.md`;
дизайн: `C:/Users/user/Desktop/PLATFORMA_DENTAL_DESIGN_v1/DESIGN_SPEC.md`.
Это новое явное разрешение реализации заменяет прежнюю границу «только ТЗ»;
оно не разрешает deployment, рабочие миграции, покупки или передачу PHI провайдерам.
Все E0–E7, D01–D12, 28 последних бизнес-правил и остальные требования сохраняются.
Цель не сводится к MVP/первому этапу. Матрица требований приведена ниже;
источник полностью прочитан, включая последние 28 правил и раздельные сроки.

## Контракт работы

Режим implementation; пробелы code/evidence/environment и ранее отложенная внешняя
проверка. Результат: действующие UI/API desktop/mobile и подтверждённые сценарии
всего ТЗ. Не переоткрывать принятые бизнес-решения. Реальные внешние проверки не
подменять тестовым адаптером. Общие Client/Appointment/Payment/BusinessCapability,
планы посещений/плановые деньги, UI-kit, AI runtime и provider adapters переиспользуются.
Новый медицинский домен содержит собственные данные/ACL/версии, без второго ядра.

Риски: PHI, идентичность, филиалы/Business, подпись/файлы, конкурентность, повтор
завершения и деньги. Порядок: контракт → инварианты/модели → права/переходы → аудит
→ API → UI → сквозные проверки. Минимальный backend gate после связного изменения:
изолированные focused tests; завершение среза: check/drift и affected/dependent suites;
PostgreSQL для конкурентности. UI: build/types/i18n + реальные browser flows и
визуальная проверка по правилам проекта. Полный release gate для итогового кандидата.
Миграции создаются/проверяются в изоляции, не применяются к рабочей базе.

Permissions, уведомления, BusinessEvent и AI затрагиваются: отдельно медицинский
ACL без owner/support bypass; общие события содержат только разрешённую проекцию;
PHI не попадает в общий поиск/логи/уведомления. Никаких новых действующих внешних
отправок до проверки условий и разрешённого тестового получателя.

## Исходный срез и чужая работа

Canonical root `C:/Users/user/Desktop/PlatformaCRM`; ветка `codex/ui-testing-toolkit`;
HEAD/base начала `656dbd19` (предок для будущего committed range, сейчас HEAD).
Чужие изменения при начале: STATUS/PRIMARY; accounts/passwords.py, serializers.py,
businesses/serializers.py; access/google-sign-in/integrations/operations contracts;
google-auth/google-button/google-sheets/ycloud evidence; auth и YCloud frontend tests;
ResetPasswordPage/SignupPage/WhatsAppSetup и RU/KK/EN integrations.
Чужие untracked: accounts/tests_password_policy.py, frontend password-policy.test.mjs,
features/auth/passwordPolicy.ts. Не включать их в наши коммиты. Индексы обновлять
только отдельными собственными блоками; существующий WIP сохранять.

## Координация модулей

Прочитаны два последних ответа чата «Бизнес-модули»
`01a1f268-397a-74d3-b863-a5ce00f00b61`: на момент чтения idle; прежняя работа была
docs-only, runtime-профиль не реализован. Согласованы один resolver/BusinessCapability,
ключ medical_records, additive D02, сохранение IDs/таблиц/URL; обязательная подпись
проверяется до завершения, внешние подпись/доставка вне денежной транзакции.
22.11 направлено уведомление о новом поручении владельца и запрос о занятых файлах;
новая задача другому чату не выдавалась. Ответ прочитан: незавершённых изменений
и занятых файлов CRM-D04 нет; реализацию и процессы другой чат не запускает. Сам по себе idle/чат
не является блокировкой: проверять фактические пересечения перед правкой.

## Выполнено / доказательства / следующий шаг

- Полностью прочитан файл цели; повторно проверены Git HEAD/status и исходные модели
  Client, Business/BusinessCapability/BusinessMember, scheduling Appointment locations.
- Проверен capabilities.py: неизвестный ключ сейчас разрешён по fallback; medical gate
  должен fail closed, сохраняя общие CRM-права. Runtime medical domain пока не создан.
- Прочитаны zani-change-crm-domain, zani-review-access, engineering и изолированный
  focused verification workflow. Их правила применять, не считать чтение проверкой кода.
- Исходное ТЗ полностью прочитано; восстановлены ранее обрезанные фрагменты,
  включая §22.1, 38 уточнений, все 28 бизнес-правил и §22.7.
- Добавлен серверный medical capability gate и шесть focused regression tests.
  Рабочая БД, процессы/провайдеры не менялись; полного E0/E1 PASS ещё нет.

Следующий шаг: медицинская серверная граница capability, затем профильная активация
и идентичность пациента с медицинским ACL. Матрица ниже сохраняет все следующие этапы.

Публикация: первый срез закоммичен локально в31b90484; push/CI не выполнены. Backend focused
проверка завершена ниже; UI не изменялся, build/browser для этого среза неприменимы. Внешние условия не закрыты,
не блокируют чтение/контракты/независимую реализацию. Цель активна, не достигнута.

Проверка текущей документационной дельты: JSON registry загружен Python успешно;
scoped git diff --check для README/registry/STATUS/PRIMARY без ошибок whitespace.
Полный git diff --check обнаружил pre-existing blank EOF в чужом
docs/testing/evidence/google-button-design-20261119.md:41; чужой файл не исправлялся.
Это не проверка продукта и не основание закрыть E0. Новый checkpoint просмотрен;
матрица завершена; публикация связного среза ограничена общим static gate ниже.

## Единая матрица требований

Источник S: внешнее ТЗ v1.2 по указанному выше абсолютному пути; B01–B28 означают
пункты §22.6, Q01–Q38 — §22.3. Ссылки § относятся к S. Статусы ниже разделяют реализацию и её доказательства; наличие backend/API
не означает готовность пользовательского сценария. Общие доказательства чтения/исходного
Git-среза находятся выше; runtime-доказательства добавляются к соответствующей строке.

| ID / источник | Согласованное поведение и переиспользование | Остаток / зависимости | Приёмка и необходимое доказательство | Статус  Сервер | API | Доступный UI | Конкретный следующий остаток | Внешние зависимости |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| M01 §1–2,14; D01,D02; Q06–08,21 | Самостоятельная МЦС частных платных стоматологий; одно ядро, Client/Appointment/Service/Payment неизменны; Platforma Digital, Yandex Cloud KZ | Согласованные версии профиля CRM-D04, additive активация новых/старых dentistry без сброса; не создавать карты автоматически | Повтор backfill сохраняет настройки/ID; другие сферы и CRM работают; миграции в изоляции | Частично: schema/registry/guards/create paths и server plan gates проверены SQLite; D02 backfill/PG/UI ещё нужны | Профиль/registry/guards/create paths и plan gates | Существующие create paths; отдельная активация не завершена | Медицинская активация не завершена | D02 backfill; PostgreSQL; настройки UI | Инфраструктура KZ подтверждается отдельно |
| M02 §2.1,12–13; D03 | BusinessCapability и существующие tenant/member/RolePermission дополняются медицинской проверкой | Fail-closed gate API/files/search/jobs/AI; никакого owner/platform bypass | Нет capability/роли/Business → отказ; актуальный отзыв действует после кеширования | Частично: capability, role/branch prerequisite, generic guards и owner grant/revoke/audit/replay PASS; owner-clinician confirmer pending; patient ACL/API/jobs ещё нужны | Capability, role/branch guards, grant/revoke/audit | Медицинские ACL применены к реализованным endpoints | S18/M21 role management опубликованc135008d,9 browser PASS | Owner-clinician confirmer; jobs/files/AI ACL | Нет внешнего блокера текущих ACL |
| M03 §2.2–2.4,3,16.1; D04; B02–04; Q09–12 | PatientProfile OneToOne Client, отдельные дети/представители; контакты из Client | Шифрованный ИИН + tenant HMAC, проверенная идентичность отдельно от синтаксиса; основание/срок/отзыв представительства | Семейный телефон не merge; конкурентный verified ИИН уникален; административные действия до проверки, клинические запрещены | Частично: patient schema/crypto/services/audit/reception API/UI с lifecycle/recovery/boundary evidence. Представители: schema/guards/services/audit/authority prerequisite + list/form/verify/revoke API; medical200 SQLite + labels34 PASS; S14 UI6 happy flows/build/screens PASS. К04: поиск8 browser, ИИН correction/head approval7 browser и PG82 (4 races) PASS; registration PG12 (same-key race), browser6, representative negative1 и final build PASS; перепривязка/разбор смешанных историй и recipient enforcement остаются; документы/возраст внешне не подтверждены | Patient/identity/crypto и представитель lifecycle | Patient administration; representatives list/form/verify/revoke | ClientWorkspace: профиль/идентичность/представители | Перепривязка/разбор смешанных историй; recipient enforcement К12; L04 | Документы/возраст и протоколы требуют подтверждения |
| M04 §2.3–2.4; D04,D07; B04,26–27 | Медицинские зависимости блокируют обычный merge до любого переноса; архив сохраняет историю | Hooks существующего merge/dry-run/delete, контролируемое исправление с причиной и медсогласованием | Отказ атомарен, Appointment/VisitPlan не перемещены частично; hard delete не уничтожает PHI | Частично: merge/preview409 до переноса, PROTECT Client и архив PASS; административное исправление и ИИН с head review реализованы/проверены; перепривязка смешанных историй ещё нужна | Merge guard/PROTECT/archive | Существующий merge/preview отклоняет медицинские зависимости | ИИН request/approve/reject UI и audit проверены | Controlled relink/mixed-history policy и реализация | Нет внешнего блокера merge guard |
| M05 §3–4,11; D03; B01–04 | Существующие ClientsPage/ClientWorkspace/ClientForm; медицинские статусы только разрешённым ролям; свободные услуги | Resolve пациента/поиск ИИН с безопасными ошибками, вкладки и сохранение контекста | Список/поиск без утечки PHI; повтор создания/смена Business; свои реальные данные | Частично: PatientAdministrationPanel и patient API уже существуют; patient lifecycle/recovery evidence сохранено выше. К04 поиск в ClientsPage: POST/роль/филиал/точные и возможные совпадения,8 browser PASS; atomic new Client+Patient domain/API/PG/browser6/build PASS; reception list projection5 backend/6 browser/build PASS; clinical projections/вкладки К05/К06 остаются. | Patient resolve/administration на Client | Patient administration API | PatientAdministrationPanel в ClientWorkspace | Clinical list projections и вкладки К05/К06; итоговая интеграция К18 | Протокол идентификации отдельно |
| M06 §13; D03; B06–08; Q01–02,04 | Запись немедленно даёт основание; активное лечение независимо от следующей даты; передача требует принятия | Состояния приглашения/участия/причин доступа, филиальный scope, назначение медруководителя владельцем без саморасширения | Будущая запись >24ч доступна; отмена убирает только своё основание; до принятия нет карты; другой Business запрещён | Частично: прежние server/UI опубликованы9990bcbf/23a007a8, CI success. Новый source-scoped transfer:82 backend,14 node,types/build/i18n,6 locale/viewport +1 recovery +2 regression browser PASS;14 снимков просмотрены. Полный M06 открыт. | Appointment basis; propose/accept/decline/withdraw; head end | Commands; invitations/managed/mine; workspace-access; candidates; source-scoped proposal-branches/outgoing с текущим основанием и аудитом | Head invite/end, own accept/history; source-scoped филиал/получатель/предложение/исходящие/отзыв из записи или active-участия, проверены desktop/mobile RU/KK/EN | Transfer опубликован747e915d; источник предложения migration0015:67 backend/API/roundtrip PASS локально. Уведомления/context:201 PASS/6 PG skips; UI переход/ответ/окна подключены,8 browser сценариев,types/build/i18n/10 node PASS;16 снимков просмотрены, опубликованоe4dca5c7. Причина отказа B07:encrypted domain/API/private read и оба UI входа добавлены,67/30/30 backend runs PASS (наборы пересекаются),10 browser PASS;types/build/i18n/transport/static PASS. Организационные сведения B07 добавлены: направление/дата/инициатор,100 backend и24 distinct browser PASS;20 снимков просмотрены,types/build/i18n/static PASS. Управление medical role: owner-only read/write API и encrypted основание/история migration0019 добавлены,66 affected backend PASS/check/drift. S18/M21 settings UI подключён:9 browser PASS,26 снимков просмотрены;types/build/i18n/transport/terminology PASS. Полный ACL и остальные критерии M06 открыты | Нет внешнего блокера основного сценария |
| M07 D03; Q01–05; B05,28 | Завершение участия отдельно от приёма; исправления 24ч; support один инцидент ≤4ч readonly; ассистент только команда/текущий приём | Проверки обязанностей/будущих записей, согласование не самим собой, досрочное закрытие/новое продление | Отзыв роли сильнее временного разрешения; точный scope; ассистент не подписывает/не выдаёт/не экспортирует историю | Частично: head end domain/API/responsible selector и форма локально проверены. Ordinary end/обязательства/security revoke/24h/support/team открыты. | Head end с причиной/ответственным; own-end domain с Appointment/Encounter obligations,44 affected PASS | end-by-head; own-end пока без HTTP, полнота документов pending | Head end с причиной/ответственным локально проверен; остальные временные/командные сценарии отсутствуют | Ordinary end/обязательства; security revoke; 24h correction; support/team | Правила уже согласованы; подтверждение заново не требуется |
| M08 §4.2–4.4; D05; B09–11; Q13–15 | Один Encounter на реальный Appointment того же Client/Business; свои клинические данные | Черновик/revision/обязательные разделы/явная неприменимость; обычный/частичный исход; walk-in текущим днём, ранний через руководителя | Чужие связи/revision отклонены; финансовый переход через существующий сервис ровно один раз, unpaid не блокирует помощь, rollback | Частично: chart/open/draft/read/workspace services и API, encrypted versions/audit, migrations0009–0011; current role/basis/identity/replay checks. Срезы30–37 содержат доказательства и исправление B03. Срез43 добавил calendar→chart/open/draft UI; текущая проверка в начале checkpoint. Срез44 добавил history/revision reader, current display labels; проверки ниже/в начале checkpoint. Full UI/team/temporary ACL, signatures/obligations, walk-in и atomic calendar completion ещё нужны | Chart/open/draft/versions/audit; current ACL | Appointment context; workspace; draft; history/revision | Calendar → приём/черновик/история | Завершение+calendar/money; walk-in; team/temporary; остальные вкладки | Подписи/формы см. M11–M12 |
| M09 §2.2,4,16.2 | Одонтограмма постоянных/молочных/смешанных зубов, поверхности, наблюдения, авторство и история | Модели текущего состояния/append history, связи приём/план/снимки | Изменение сохраняет прежнее и новое, неверный зуб/поверхность отвергнуты, права/конкурентность | Частично: срез47 добавил state/history schema и migration0012;29 storage/dependent tests/check/drift PASS. Срез48 encrypted helpers:30 tests/check/drift PASS; Срез49 exact-version audit:380 medical tests PASS; срез50 primary command/exact reader:50 PASS; срез51 HTTP:40 PASS/check/drift. Срез52 snapshot/history API:41 tests PASS, дополнительные12 edge tests PASS. Срез53 typed frontend transport10 tests/types/build PASS; Срез54 read UI:6 localized+1 recovery browser PASS; Срез55 whole-tooth editor:6+1 browser PASS; Срез56 surface-options API/shared validator41 tests PASS; Срез58 surface UI:6 localized+1 Map regression browser PASS, types/build/i18n/screens PASS; team/linked plans/images/clinical legend/concurrency ещё открыты | Tooth state/encrypted append history; surface policy | Write/exact read/snapshot/history/surface options | Постоянные/молочные/смешанные зубы; история; редактор поверхностей | Планы/снимки/team; PG concurrency; клиническая легенда | Утверждённый справочник поверхностей не получен |
| M10 §2.4,4,6 | Клинический план отдельно, ссылки на VisitPlan/Step и существующие деньги | Клинические шаги/версии/связи; подтверждённое преобразование в календарь без неявного долга | Изменение медплана не создаёт Payment/бронь, сохраняет организационные ссылки | Частично: encrypted plan_steps в EncounterRevision, validator/history/snapshot/correction;84 dependent,7 main+2 correction browser,build/static/check/drift и visual PASS | Версии шагов внутри медицинского приёма, без нового организационного агрегата | Существующие encounter API/ACL/audit/idempotency | Добавление/редактирование/keyboard reorder/удаление и история | Связи VisitPlanStep/зубов; шаблонное представление; подтверждённое преобразование в календарь без неявного долга | Внешний блокер независимой реализации не установлен |
| M11 §5,16.2; D06; Q16–17 | Версионные шаблоны документов по виду/услуге, бренд и реквизиты, автор/врач/реальный подписант отдельно | Матрица обязательности/момента/подписантов; снапшоты источников, PDF, ограниченный DOCX, печать | Старый PDF/checksum не меняется после редактирования клиента/шаблона; новые исправления отдельными версиями | Частично: draft document/revision storage, зашифрованные снимки clinical/template/requisites/авторов; проверки в начале checkpoint | MedicalDocument/Revision + primary draft create/update/read, current ACL/audit/replay; approved source/template metadata + separate edited text in schema2,115 dependent/check/drift PASS; schema3 identity/encounter source + literal preview domain/digest,85 dependent/check/drift PASS; Template/Revision + own drafts; version review submit/approve/reject/read domain/API + pending queue,58 affected tests/check/drift PASS; credential profile/version encrypted storage +10 focused/64 dependent PASS, migration0025 isolated forward/back/forward PASS; metadata schema2 language/category/specialty/service snapshots + personal/common HTTP111 dependent/check/drift PASS; К01 confirmation/audit/API/UI/schema4 snapshot105 dependent +migration roundtrip PASS; signed/finalized открыты | Personal templates create/update/list/history/read + verified review summary/approve metadata; common management/history/submit + approved selector domain/API; document create/update/list/history/version API,82 backend/check/drift PASS; independent workspace actions/revisions,41 affected/check/drift PASS; preview/digest HTTP22 API/domain tests PASS | S17 личные и общие шаблоны, редактор/история/отправка/очередь/решения;21 browser PASS, 6 common r2 PASS после исправления подписи,66 применимых снимков просмотрены; document list/detail/history/approved editor:6 browser +8 clinical regressions PASS,61 новых снимков просмотрены; build/types/i18n PASS; preview/edit retention6 browser PASS,48 screenshots reviewed (final EN2 rerun PASS); field catalog15 API tests, authoring12 browser +1 boundary PASS,52 screenshots reviewed, build/types/static/check/drift PASS; classification editor/service catalogue/detail/review26 API +20 browser PASS,102 screenshots reviewed, final build PASS; К01 credentials8 browser +1 template regression,43 screenshots reviewed,build/types/static PASS | К02 поиск/применимость domain/API/UI локально принят (доказательства в начале checkpoint); остаются матрица обязательности, PDF/asset bytes/checksum, lifecycle, assistant/team/temporary ACL, API/UI этих сценариев, DOCX/печать | Формы/подписи требуют внешней проверки |
| M12 §5.6; D06; Q17 | Подпись desktop/Android/iPhone, черновик ≠ утверждение ≠ подтверждённая ЭЦП | Адаптер выбранного провайдера, проверка сертификата/подписи, несколько подписантов | Callback replay/поздний/отменённый/невалидный не финализирует; реальные испытания всех платформ | Не реализовано; провайдер/доступы не определены | Не реализовано | Не реализовано | Не реализовано | Адаптер выбранного провайдера, проверка сертификата/подписи, несколько подписантов | Провайдер подписи и доступы не определены |
| M13 §2.5; D07; Q20–24; §22.7 | Приватные файлы, карантин/фактический MIME/антивирус, аудит без PHI; reuse private storage | Медицинский ACL на оригинал/preview/export; ключи/ротация; резервный защищённый журнал; retention по категориям | Сбой сканера не публикует; сбой аудита блокирует write/issue, read только с надёжным журналом; прямой URL не обходит ACL | Частично: криптография и patient-create/update audit rollback PASS; files/retention/read fallback ещё нет, сроки/ресурсы внешне не подтверждены | Medical crypto; атомарный аудит реализованных чтений/записей | Реализованные medical endpoints private/no-store | Файлы/retention отсутствуют | Quarantine/scanner/files ACL; read fallback; retention/rotation | Сроки хранения и инфраструктурные ресурсы не подтверждены |
| M14 §5.5–5.6; D08; B12–19; Q25–27 | Лично отдельный случайный код, нейтральная ссылка; конкретные версии/комплект обращения, без оплаты/ежедневного OTP | Хеш секрета/лимиты попыток/сессия/новая вкладка; дистанционно дополнительная проверка | До готовности нет доступа; 72ч с активации; repeat/revoke/reissue/представитель/смена контакта; секрет не URL/log | Не реализовано | Не реализовано | Не реализовано | Не реализовано | Хеш секрета/лимиты попыток/сессия/новая вкладка; дистанционно дополнительная проверка | Удалённая проверка получателя и нормативная приёмка |
| M15 §5.5,15; D08; B18 | Существующий WhatsApp adapter, согласие и проверенный получатель, без PHI/PDF в Meta по умолчанию | Outbox/idempotency и привязка точных версий; отдельные delivery/read/doc-open статусы | Retry не дублирует выдачу; новая версия отдельно; template/window; реальный receipt не заменён mock | Не реализовано; нормативная допустимость выдачи отложена | Не реализовано | Не реализовано | Не реализовано | Outbox/idempotency и привязка точных версий; отдельные delivery/read/doc-open статусы | Допустимость выдачи/реальный провайдер |
| M16 §6–7; D09; Q28–30 | Назначения типов лекарство/обследование/направление/уход/контроль/иное; личные snippets и утверждённые шаблоны | Структура+текст, версия/автор/язык/категория; поиск и безопасные подстановки | Разные scope клиники/врача, нет назначения без явного подтверждения | Частично: самостоятельный черновик назначения/версии/API/UI scoped acceptance PASS; полный M16 открыт | MedicalOrder/Revision encrypted, author-only draft writer, medical_prescriptions ACL/audit/replay | Private orders create/update/list/history/exact version/workspace-access | Вкладка Назначения,7 типов, medication fields, create/edit/history и recovery | Личные snippets/утверждённые шаблоны/применение; подпись/PDF/выдача в К08–К11; клинический план отдельно M10 | Внешний блокер независимой реализации не установлен |
| M17 §6.2–7; D09 | AI Tab/Esc и mobile принять; диктовка только текущего разрешённого поля, ручная работа всегда | Минимальный allowlist/tenant caches/stale response guards; approved provider chain, срок аудио | Отзыв/смена пациента/новая revision не перезаписаны; RU/KK числа/зубы/отрицания/дозы; живой звук | Не реализовано; провайдер/корпус/пороги требуют подтверждения | Не реализовано | Не реализовано | Не реализовано | Минимальный allowlist/tenant caches/stale response guards; approved provider chain, срок аудио | AI/STT provider chain, корпус, пороги и аудиополитика |
| M18 §8; D10; B20–21; Q31–32 | Врач с calendar create записывает через существующую форму; иначе поручение очереди филиала | ReceptionBookingRequest, claim одним сотрудником, атомарное book/link, idempotency | Реальная запись с корректным Client/Business; гонка один победитель/одна бронь; permission recheck | Не реализовано | Не реализовано | Не реализовано | Не реализовано | ReceptionBookingRequest, claim одним сотрудником, атомарное book/link, idempotency | Внешний блокер независимой реализации не установлен |
| M19 §8.5; D10; B20–21 | 5мин в клинике /30 рабочих минут, старший/заместитель; попытки сегодня/следующий день, 2 рабочих дня → не связались | Часы/очередь/эскалация/явная смена/ожидание/reopen; notifications projections | Нет подмены отказом/автобронью; без замены видно просрочку; p95 обновления очереди ≤5с | Не реализовано | Не реализовано | Не реализовано | Не реализовано | Часы/очередь/эскалация/явная смена/ожидание/reopen; notifications projections | Внешний блокер независимой реализации не установлен |
| M20 §9; D03,D09 | Бот получает только разрешённую проекцию после проверки личности канала | Связь recipient identity, семейный контакт не пациент, аудит | До проверки нет имён/истории; нет admin-token bypass; tenant/role/consent negatives | Не реализовано | Не реализовано | Не реализовано | Не реализовано | Связь recipient identity, семейный контакт не пациент, аудит | Проверка идентичности канала |
| M21 §10; D11; B22 | PurchaseRequest/Line/Batch/Line/History отдельно от PHI; одна форма из кабинета и после приёма | Серверный actor, количество/единица/модель/характеристики/срок/филиал; approval default true только unset | Явный false сохранён, PHI отсутствует в проекции закупок; оба входа реальны | Не реализовано | Не реализовано | Не реализовано | Не реализовано | Серверный actor, количество/единица/модель/характеристики/срок/филиал; approval default true только unset | Внешний блокер независимой реализации не установлен |
| M22 §10.2,10.6; D11 | Popup после подтверждённого завершения и выхода, отдельный event claim; crash может пропустить, не повторить | Серверное одноразовое решение/идемпотентная заявка | Две вкладки/повтор/возврат/отмена не дублируют; запуск без открытого пациента | Не реализовано | Не реализовано | Не реализовано | Не реализовано | Серверное одноразовое решение/идемпотентная заявка | Внешний блокер независимой реализации не установлен |
| M23 §10.3–10.6; D11; B23–25 | Группировать только совместимые характеристики/единицу/филиал; согласование до заказа | Переходы approval/order/partial receive/substitute/overage/return/remainder, история/аллокации | Увеличение/замена повторно согласованы; остаток подтверждён инициатором/руководителем; concurrency/replay без двойного получения | Не реализовано | Не реализовано | Не реализовано | Не реализовано | Переходы approval/order/partial receive/substitute/overage/return/remainder, история/аллокации | Внешний блокер независимой реализации не установлен |
| M24 §11; DESIGN_SPEC/GALLERY/REVIEW | Shared UI-kit и существующая композиция, desktop/mobile RU/KK/EN | Все экраны/вкладки/21 окно и роли, достижимые маршруты/API clients | Browser: loading/empty/error/forbidden/recovery, retained input, focus/keyboard/overflow; снимки получены и просмотрены | Частично: runtime patient/representatives/clinical/history/tooth UI; scoped browser/build/i18n/screens evidence в срезах43–58. Остальные экраны не приняты; макеты не runtime PASS. | Используются реальные medical services | Typed clients patient/representatives/clinical/tooth | Профиль/представители; clinical/history/teeth; head participation lifecycle локально проверен | Полный S01/S13 navigation/design, врачебная передача; остальные экраны/21 окно и ролевая приёмка | Реальная подпись зависит от M12 |
| M25 §12–15 | Единые API envelope, серверный actor/Business, revision/idempotency, safe activity/events | CRUD/команды patient/encounter/order/doc/sign/issue/files/teeth/templates/representatives/access/reception/procurement | 400/403/404 foreign/409 stale+payload; пагинация; события после commit без клинического текста | Частично: service/API evidence patient/representatives/clinical/tooth; participation commands/reads/candidates подтверждены срезами60–62. Полный API ТЗ не завершён. | Actor/Business/revision/idempotency/audit реализованных команд | Patient/representatives/clinical/tooth/participation частично | Typed clients patient/representatives/clinical/tooth/participation; последний transport закоммичен | Остальные команды ТЗ/events и сценарии участия; сохранить сервер/UI diff | Внешние протоколы см. профильные строки |
| M26 §16–17; D12 | Изолированные миграции и сервисные/API/негативные/UI/PG тесты, сохранение CRM | Проверки каждого E0–E7 до итогового кандидата | Конкурентность PG, регрессия non-dentistry/платежей/календаря; не выдавать SQLite/mock за полную проверку | Частично проверено локально: изолированные backend/API и UI проверки реализованных областей; последний полный medical запуск срез59, affected participation срез62. PG/full candidate/live остаются непроверенными. | Есть isolated fixtures и тесты реализованных областей | Есть service/API negative tests | Есть localized desktop/mobile clinical/patient/tooth evidence | Итоговый кандидат E0–E7, PG races и зависимые регрессии | Нужна подходящая PG/нагрузочная среда |
| M27 D07,D12; Q21,24,35–36 | KZ приложение/БД/файлы/копии/ключи, независимый restore; RPO15мин/RTO4ч | Конфигурация, monitoring/alerts/rollback, профиль нагрузки первых 2 клиник с запасом до5 | Практический restore с версиями/подписями/audit; p95 card/search/save2с/PDF15с/queue5с, ошибки учтены | Не выполнено; ресурсы/ответственные/измерения открыты | Эксплуатационные требования не реализованы полностью | Метрики/restore не подтверждены | Эксплуатационный результат не подтверждён | RPO/RTO restore; p95; alerts; 2→5 клиник | Ресурсы, ответственные и реальные измерения |
| M28 D01; Q07–08,16–19,27,38 | Самостоятельная МЦС без обязательной второй МЦС; внешние обязательства по применимости | Нормативная матрица/формы/договоры/гособмен/тестовые доступы; лаборатория/PACS только подтверждённая необходимость | Утверждённый перечень и фактическое принятие внешней системой; не обещать непроверенное соответствие | L02: проверку организовать параллельно; заключение не получено | Самостоятельная МЦС остаётся целевым требованием | Гособмен не реализован/не подтверждён | Внешняя приёмка не пройдена | Нормативная матрица и применимые интеграции | L02,L07: назначить проверяющих и получить заключения/условия обмена (§22.9 ТЗ) |
| M29 B26–27; Q37–38 | Импорт необязателен, прежняя история не объявляется отсутствующей; экспорт сразу | Читаемые документы+структурные данные+файлы/версии/авторы/подписи; завершение обслуживания без автоудаления | Проверка полноты архива/ACL/восстановления связей; договорный состав/срок отдельно | Не реализовано | Не реализовано | Не реализовано | Не реализовано | Читаемые документы+структурные данные+файлы/версии/авторы/подписи; завершение обслуживания без автоудаления | Договорные состав/срок экспорта |
| M30 §18–22,19.1 | Полный сценарий от пациента/приёма/подписи до выдачи/повторной записи/частичной закупки | Итоговый аудит всей матрицы, документы/паспорт/roadmap и публикация по правилам | Все E0–E7 с доказательствами, реальные обязательные интеграции; запуск отдельно разрешается | Не достигнуто | Частично по строкам выше | Частично по строкам выше | Полный сквозной процесс отсутствует | Все незакрытые критерии M01–M29, E0–E7 и публикация | Все обязательные внешние подтверждения остаются открытыми |

§20 — карта источников, §21 — история решений, §22.1–22.7 — актуальные уточнения:
они применены к строкам выше, а не трактуются как отдельное разрешение пропускать
незакрытые требования. §1.3 исключает автоматические закупки/Market checkout,
автономную клиническую AI-практику и неподтверждённые дополнительные отрасли.

## Первый связный срез: серверный gate медицинских ресурсов

Предыдущий результат: общие capabilities реализованы → чтение обнаружило разрешающий
fallback неизвестного ключа → минимальная дельта: отдельная строгая ветка для
medical_records и mapping медицинских ресурсов в существующем resolver.
Это необходимая защита до добавления API, не завершение M01/M02 и не активация D02.
После среза2 медицинский ресурс требует известный dentistry_v2 и явные зависимости;
до готового профиля/релиза legacy-строка не разрешает медицинский ресурс.
Даже явная строка вне dentistry не разрешает модуль. Медицинскую capability читать
свежей из БД: старый объект/cache не должен сохранять отозванное включение.
Общие capability defaults/payload/права не менять в этом срезе. Следующий срез
добавляет версионный профиль и writers, затем медицинские ACL без owner bypass.

Изменяемые пути: apps/businesses/capabilities.py и новый focused test файл.
Моделей/миграций/внешних эффектов/уведомлений/BusinessEvent/AI-вызовов пока нет.
Риск: серверный доступ и совместимость общего resolver. Проверки: отсутствие строки,
false/true, другая отрасль, другой Business, отзыв после кеша, все медицинские resource
keys; регрессия десяти общих defaults. UI gate неприменим: UI ещё не меняется.


### Проверка первого среза — 22.11.2026

Исходный HEAD 656dbd19 + перечисленный WIP, новые capabilities.py и
tests_medical_capabilities.py. Команды выполнены через
`from scripts.codex_verify import isolated_runtime`, `.venv/Scripts/python.exe`,
`subprocess.run(..., env=runtime.environment, check=True)`:

- `manage.py check`: PASS, 0 issues.
- `manage.py makemigrations --check --dry-run`: PASS, No changes detected.
- `manage.py test apps.businesses.tests_medical_capabilities -v 2`: PASS, 6/6,
  0.360s тестов после применения существующих миграций к disposable SQLite.
  Unified exec session23065 завершён exit0; тестовая БД уничтожена runner-ом.

Проверены отсутствие/false/true/удаление строки, другой Business/отрасль, изменение
отрасли и отзыв при stale instance/cache, сохранение общих defaults и явного false.
Все пять медицинских resource mappings проверены на отказ без включения.
Это проверки resolver, не конечных медицинских прав/эндпоинтов, PG-конкурентности,
профильной активации или готовности всей МЦС. Миграций продукта пока нет.

Следующий срез: Business profile_key/version/assigned_at и один profiles resolver
по CRM-D04 (immutable core_v1/dentistry_v1 + medical dentistry_v2), writers и
контролируемая additive активация по D02. Прочитана схема плана §Хранение/Legacy;
нужно закончить inventory writers и проверить чужой serializers WIP перед изменением.
Не включать medical runtime до зависимого ACL/UI и release gate.


### Коммит и ограничение публикации

`31b90484` — feat(medical): deny clinical resources without explicit capability.
Просмотрены собственные изменения; в STATUS/PRIMARY/access staged только новые
блоки DENTAL-MCS через отдельные hunks. Чужой auth/WhatsApp WIP сохранён.
`git fetch origin main`: PASS; исходящий диапазон содержит только31b90484.
`git diff --cached --check`, scoped working diff, JSON registry и whitespace
новых файлов: PASS. CI workflow запускает проверки, deploy в затронутых workflows нет.

Команда `.venv/Scripts/python.exe scripts/codex_verify.py --mode static
--base-ref 656dbd19318b6e146dbc0026afd1727fa719c14e` завершилась exit1
(session31817): working-tree diff hygiene обнаружил pre-existing чужой
`docs/testing/evidence/google-button-design-20261119.md:41: new blank line at EOF`.
Этот дефект был зафиксирован до нашего первого изменения. Не исправлялся и не
включён в commit. Общий static gate НЕ PASS, push пока не выполнен по правилу
публикации при failed gate. Это блокирует публикацию данного среза, не независимую
разработку. Повтор без изменения этого входа не нужен. Committed-range diff hygiene
проверяется отдельно, не подменяет failed working-tree gate.

После первого среза sessions23065/31817 завершены; текущие проверки среза2 указаны ниже.
Цель остаётся активной. Следующее действие — реализация profile schema/resolver
по уже прочитанному контракту, затем защита writers и медицинский ACL.

## Срез 2: схема и чтение версионного профиля

Base31b90484; предыдущий срез прогресс (код+6 тестов), не ожидание. Состав WIP сверён,
чужая правка serializers.py затрагивает только trim_whitespace у двух паролей;
профильные изменения в иных методах сохраняют эти строки.
Вводятся nullable profile_key/version/assigned_at с DB check, неизменяемый реестр
core_v1/dentistry_v1/dentistry_v2 и строгий resolver. Старые строки остаются legacy;
legacy планы вычисляются из clients+appointments, медицинские права требуют v2.
Профильные reads не дописывают отсутствующие capabilities. Обязательные зависимости
модулей проверяются вместе с true-строкой; invalid profile →503, missing row →false.
Риски: auth payload/shared resolver/schema. Требуются тесты legacy/версии/дрейфа,
DB constraints, spoofed input/readonly admin, isolated migrations/check/drift и
совместимость первого medical gate. Публичные пути создания ещё не переключаются
на новый профиль до защиты всех writers. UI, уведомления и провайдеры не меняются.

Срез2 локально: models.py, migration0016_business_profile.py, profiles.py,
capabilities.py, BusinessSerializer raw-input/read-only guard, admin readonly,
tests_profiles.py и обновлённые tests_medical_capabilities.py. Существующие строки
БД получают NULL, новые поля не означают автоматическую активацию.
Контракт чтения уточняет первый срез: legacy/старая версия не получают PHI даже
от посторонней true-строки; назначение полноценного v2 ещё впереди.

Проверки `.venv/Scripts/python.exe` через isolated_runtime:
`manage.py makemigrations businesses --name business_profile` создала0016;
`manage.py check` и `makemigrations --check --dry-run` PASS;
`manage.py test apps.businesses.tests_profiles apps.businesses.tests_medical_capabilities -v 2`
PASS18/18 (1.448s тестов, миграции отдельно), session28928 exit0.
Полный лог `C:/Users/user/AppData/Local/Temp/dental-profile-20261122.log`.
Рабочая БД не менялась, тестовая SQLite уничтожена. Reverse/PG/live не проверены.

Affected/dependent suite запущен в другом isolated_runtime, session12214:
`manage.py test apps.businesses.tests_access apps.core.tests_b301_performance
apps.core.tests_b5_performance apps.conversations.tests_inbox_tasks -v 1`.
Лог `C:/Users/user/AppData/Local/Temp/dental-profile-regression-20261122.log`.
Session12214 завершён exit1:64 теста,62 PASS/2 FAIL,74.660s. Оба FAIL —
query budgets owner dashboard:85 запросов при лимитах70 (B301) и75 (B5).
Причина: добавленное чтение Business при каждом обычном module check. Тестовые
лимиты не менялись. Минимальная дельта: сохранить существующий per-instance
legacy _capability_map для десяти общих keys; новые/profile-managed/medical keys
читают свежую БД, как раньше задумано. Это не новый долгоживущий кеш. Профильные
writers обязаны инвалидировать snapshot, команды работают со свежим Business.

После исправления запущена session55374: тот же isolated_runtime,
`manage.py test apps.businesses.tests_profiles apps.businesses.tests_medical_capabilities
apps.businesses.tests_access apps.core.tests_b301_performance
apps.core.tests_b5_performance apps.conversations.tests_inbox_tasks -v 1`.
Лог `C:/Users/user/AppData/Local/Temp/dental-profile-regression-fixed-20261122.log`.
Session55374 завершён exit1:82 теста,81 PASS/1 FAIL,87.576s. Dashboard67
в пределах70; client card42/43 при росте строк. Остался Inbox15 при лимите12.
Вторая точечная дельта: после уже прочитанного свежего Business читать сохранённые
capabilities один раз; ensure только когда отсутствуют legacy defaults. Ранее
повторная ensure повторно читала Business и оба набора строк. Правила доступа и
пороговые значения тестов не меняются.

Завершена session38320, повтор через isolated_runtime:
`manage.py test apps.businesses.tests_profiles apps.businesses.tests_medical_capabilities
apps.core.tests_b301_performance apps.core.tests_b5_performance -v 1`.
Лог `C:/Users/user/AppData/Local/Temp/dental-profile-query-fix-20261122.log`.
После возобновления handle отсутствует; лог содержит PASS30/30,6.948s.
Inbox11/dashboard65 в бюджете. Повтор не нужен без изменения входов.
Новые исходники среза2 пока не закоммичены. Публикация первого среза по-прежнему
заблокирована ранее доказанным чужим whitespace; повтор static без изменения
входа не запускался. Все E0–E7 остаются в scope.

Inventory следующего среза: create_owner_account в accounts/google_auth_signup.py
общий для password/Google; BusinessViewSet.perform_create; landing _get_or_create_business;
legacy social _ensure_first_business и Django admin. Existing guards нужны в
BusinessSerializer.update (view уже reload/lock), capability perform_update,
apply_business_type_defaults, apply_niche_template (до изменения business_type),
повторном landing (различать отсутствующее поле и other). AI memory fingerprint
в ai_core/conversation_access.py сейчас берёт defaults+raw rows: при внедрении
полного профиля включить profile identity/effective modules в fingerprint,
не превращать fingerprint в grant. Это не изменение AI scope или разрешение PHI.


### Срез3: текущие проверки

Подтверждено наличие согласованной v1.2 (344550 bytes) рядом с исходнойv1.1;
новой редакции на Desktop нет. Полнота ранее прочитанного ТЗ сохраняется.
`manage.py check`, `makemigrations --check --dry-run` PASS; isolated
`manage.py test apps.businesses.tests_profile_writes apps.businesses.tests_profiles
apps.businesses.tests_medical_capabilities apps.onboarding.tests -v 1` PASS40/40,
16.488s, session91396 exit0. Лог TEMP/dental-profile-writes-20261122.log.

Затем добавлены HTTP negatives/no-op и landing omitted-vs-explicit-other guard.
Завершена session52020: PASS68/68,62.319s, exit0; isolated `manage.py test apps.businesses.tests_profile_writes
apps.businesses.tests_activation apps.businesses.tests_access -v 1`,
лог C:/Users/user/AppData/Local/Temp/dental-profile-writes-api-20261122.log.
В read-only трассировке обнаружено, что platform_views.platform_activate_landing
ещё подставляет other в caller: после текущего прогона убрать этот default и
проверить HTTP повтор с отсутствующим business_type с настоящим тестовым MFA.
Не выдавать service-only проверку за полный публичный сценарий.


Последующая проверка: platform_views caller исправлен (отсутствующий business_type
передаётся как None, без подстановки other). Добавлен HTTP тест с реальным
синтетическим MFA. Session80125 выполняет isolated
`manage.py test apps.businesses.tests_profile_writes apps.businesses.tests_activation -v 1`,
лог TEMP/dental-profile-landing-api-20261122.log. Во время read-only сверки теста
обнаружены неверные ожидания нового теста: повторный endpoint возвращает200 (не201),
и business_type не входит в существующую response-проекцию. После завершения этого
запуска поправить только новый тест:200 и refresh_from_db для проверки сохранённой
сферы, без изменения контракта response ради теста. Затем focused повтор.
Исходники не менялись во время session80125. Не заявлять этот HTTP критерий PASS.


Session80125 завершён exit1:27 тестов,26 PASS/1 FAIL. Единственный FAIL — неверное
ожидание201 у нового HTTP теста на повтор активации (фактически ожидаемый200).
Исправлены только ожидания теста:200 и проверка business_type через refresh_from_db;
продуктовый response не менялся. Запущен focused повтор session6804:
`manage.py test apps.businesses.tests_profile_writes.BusinessProfileWriteTests.test_http_landing_repeat_distinguishes_missing_industry_from_other -v 1`
через isolated_runtime, лог
`C:/Users/user/AppData/Local/Temp/dental-profile-landing-focused-20261122.log`.
ЭТО текущий живой handle; на продолжении опросить его, не запускать копию.

Следующий шаг после подтверждения: закончить guards admin/signup raw input,
добавить единый atomic initializer нового Business с audit/rollback и подключить
все пять путей создания без назначения legacy при GET/login. D02 backfill и
медицинская активация остаются отдельной зависимой частью общего полного scope.
Код срезов2–3 пока WIP; первый commit31b90484 остаётся локальным. Чужие password
строки serializers.py и все auth/WhatsApp файлы сохранены; при staging выделять
только собственные hunks. Рабочая БД/облако не менялись. Static publication blocker
(чужой blank EOF) не перепроверялся без новых входов. Цель не достигнута и активна.


### Срез4: назначение профиля при создании

`manage.py test apps.businesses.tests_profile_initialization -v 1` через
isolated_runtime PASS8/8,0.329s, session1686 exit0; TEMP/dental-profile-init-20261122.log.
Проверены core/dentistry состав, неизвестная сфера, server-only поля, повтор без
новых строк/аудита, drift без ремонта, отказ saved legacy, audit rollback.

После PASS единый initializer подключён к create_owner_account (password/Google),
BusinessSerializer.create, landing created branch, legacy social и admin save_model.
OwnerSignupSerializer/наследуемый GoogleSignupSerializer отклоняют profile input
до валидации остальных полей; существующий password WIP не меняется.
Landing передаёт actor платформы для audit. Тест platform activation уточнён по
metadata.kind=platform_activation: новый отдельный profile audit не подменяет
существующий административный event, который проверял тест.

Прогон session66595 завершён exit0:50 tests,48 PASS/2 PostgreSQL-only skips,21.594s:
`manage.py check`, `makemigrations --check --dry-run`,
`manage.py test apps.businesses.tests_profile_initialization apps.businesses.tests_activation
apps.accounts.tests_google_auth apps.accounts.tests_legal_documents -v 1`.
Лог `C:/Users/user/AppData/Local/Temp/dental-profile-create-paths-20261122.log`.
Рабочая БД не меняется; migrations только isolated runtime. Публичный медицинский
модуль всё ещё выключен: создаются core_v1/dentistry_v1, v2 требует готового medical
домена/ACL/UI и D02 rollout. Это не отказ от D02 и не сокращение полного объёма.


Следующий конкретный пробел подтверждён чтением: новые Business получают профиль,
но scheduling/plan_access.py пока проверяет только clients/appointments, а не
visit_plans. Нужно довести enforcement до selectors/services/API/AI и plan_payments,
с сохранением legacy и текущей денежной логики. Просмотрены места:
apps/scheduling/plan_access.py, plan_selectors.py, plan_services.py, plan_views.py;
apps/payments/plan_balances.py (assert_plan_money), plan_services.py и plan_pricing.py.
Полное чтение этих файлов/переходов ещё требуется перед изменением; часть вывода
была усечена, не считать её полной проверкой. Нужны реальные профилированные core
и dental fixtures и отказ на прямых reads/commands/AI, не только флаг в payload.
После этого медицинский домен/ACL; весь E0–E7 остаётся активным.

Session66595 доказал check/drift PASS и creation flow tests, два SKIP принадлежат
GoogleAuthConcurrencyTests с явным Requires independent PostgreSQL transactions.
Это открытая PostgreSQL-проверка, не PASS конкурентности. Своих живых процессов
после этого прогона нет. Исходники срезов2–4 пока WIP поверх31b90484; публикация
по-прежнему не выполнялась из-за ранее установленного внешнего static gate.
