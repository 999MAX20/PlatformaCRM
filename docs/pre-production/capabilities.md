## Медицинский модуль: начата реализация — 22.11.2026

К06 представители из клинического обзора: readonly список имён, полномочий и сроков по appointment/participation с сохранёнными Clients ACL и аудитом. Подтверждение/отзыв остаются административными.46 dependent backend,6 clinical+2 administrative browser,9 inspected captures,build/check/drift PASS; публикация в DENTAL-MCS checkpoint. Реальный протокол L04/выдача К12 и весь К06 не закрыты.

К06 исторические документы: список и точные версии выбранного приёма доступны через календарь/active participation в режиме чтения с отдельным medical_documents VIEW. Текущий редактор и несохранённый клинический текст сохранены.34 backend,8 browser,17 inspected captures,build/types PASS; публикация в DENTAL-MCS checkpoint. Это не закрывает подпись/PDF/выдачу или весь К06.

К06 исторические назначения: из выбранного приёма в истории доступны read-only список и точные версии через календарное основание или active participation. Отдельные права назначений и отзыв участия проверяются сервером; текущий редактор сохранён.22 dependent backend,8 browser,17 inspected captures,final build/types PASS; публикация и ограничения — DENTAL-MCS checkpoint. Полный К06 и подпись/PDF/выдача остаются открытыми.

К06 формула через участие: собственное active participation открывает существующую зубную формулу в режиме чтения с текущим/историческим срезом, версиями наблюдений и связанными шагами плана. Запись наблюдения сохраняет календарный путь.26 focused backend,8 browser,19 inspected captures,build/types PASS; publication — DENTAL-MCS checkpoint. Это не закрывает остальные вкладки, полную приёмку К06 или внешнюю легенду L12.

К06 обзор через участие: собственное активное участие открывает тот же read-only обзор и существующую историю без календарной записи. При завершении участия новое чтение запрещается и интерфейс очищает сведения.6 localized browser +2 shared appointment regression PASS,build/types PASS; финальная визуальная приёмка/публикация и остальные критерии К06 — DENTAL-MCS checkpoint.

К06 вход из клиента: собственная календарная запись выбирается в медицинском блоке ClientWorkspace и открывает существующее клиническое окно. Backend55 dependent,6 distinct localized browser,14 inspected captures,build/check/drift PASS; подробности и публикация в DENTAL-MCS checkpoint. Выбор не раскрывает наличие PatientProfile, открытие повторно проверяет права; участие в лечении сохранено. Полный К06 остаётся открыт.

К06 обзор: private audited clinical projection и вкладка с датой рождения/последним приёмом/точной сохранённой версией сведений. Backend41 dependent PASS;6 localized browser PASS,build/check/drift PASS; visual/publication status в checkpoint. Несохранённая форма не подменяет источник, автоматической сводной оценки риска нет. Представители/команда и другие незакрытые критерии К06 сохранены.

К06 навигация: выбранная вкладка сохраняется при повторном открытии окна той же записи и повторе загрузки. Browser desktop/mobile2PASS,4 inspected captures,build/types PASS; dirty/denial guards сохранены. Фильтры вложенных списков и новые клинические вкладки остаются открытыми в checkpoint.

К06 M09: PostgreSQL17 tooth-state races и affected service/options31PASS; история и идемпотентность проверены для целого зуба/synthetic поверхности. Production не менялся. Реальный справочник L12 остаётся внешним. Подробности — текущий DENTAL-MCS checkpoint.

К06 M16: применение утверждённых общих/личных шаблонов к тексту назначения принято локально:57 dependent/12 final PG,6 browser,25 inspected captures,final build/check/drift/static PASS; опубликовано85d2d867. Manual medication fields сохраняются, exact template/approval/source привязаны к encrypted версии через migration0033; история источника и denial/recovery в UI. Рабочая БД не мигрирована, подпись/PDF/выдача отдельно. Доказательства и открытый остаток — DENTAL-MCS checkpoint.

К06 план: optional encrypted plan_steps, редактирование/keyboard reorder/подтверждённое удаление в основной и correction форме, точная история. Backend28 focused/84 dependent,7 main+2 correction browser,17 final inspected captures,build/static/check/drift PASS; опубликовано eb03906a. Дополнительно реализована связь с существующим VisitPlanStep: encrypted snapshot, protected history, medical+CRM ACL, picker и24h correction. Backend26 focused/84 dependent и25 PostgreSQL PASS (пересекаются); browser/visual приёмка PASS, опубликовано d6e05865. Дополнительно реализованы FDI teeth refs, current/as-of tooth inspector и snapshot/correction; scoped backend/PG,6 main+2 correction browser,20 inspected captures,final build/check/drift/static PASS (детали и попытки — checkpoint). Связи зубов опубликованы7a4b58dc. Явное преобразование в календарь принято локально: atomic booking/link/revision, current ACL/replay/rollback,87 dependent и14 PostgreSQL PASS (пересекаются),6 distinct browser locales/viewport,20 inspected captures,build/check/drift/static PASS. Booking опубликован78e5d7b8. M10 шаблонное представление принято локально:25 focused/29 dependent,4 browser,4 inspected captures,build/static PASS; clinical.plan_steps берёт literal нумерованный текст/FDI из сохранённой версии. Scoped остатка M10 нет, интеграция К18 отдельно. Renderer опубликован21e76257.

К06 назначения: отдельные encrypted MedicalOrder/Revision и medical_prescriptions ACL, domain/API черновиков/версий и вкладка текущего приёма добавлены. Backend57 dependent и13 PostgreSQL (включая2 races) PASS; 7 browser сценариев,21 inspected captures,build/check/drift PASS; опубликовано9c2b9fae. Подпись/PDF/выдача и личные snippets не закрыты.

К06 неприменимость: добавлен explicit not_applicable map с обязательным
обоснованием, несовместимым с непустым текстом того же раздела. Версии/снимки
сохраняют решение, история показывает причину; шаблон может явно подставить её.
Backend focused/dependent/API,11 browser сценариев, visual/build/check/drift PASS; опубликовано4897b964.
Это не закрывает клиническую финализацию, назначения или весь К06.

К06: в versioned encrypted encounter content добавлены аллергии и противопоказания.
Те же поля доступны в draft/history/24h correction и allowlist подстановок шаблона;
старые записи/документы не дополняются выдуманными значениями. Это ручной ввод
текущего приёма, без клинической интерпретации или изменения прав. Focused backend
и зависимые74 tests, build/check/drift и scoped desktop/mobile browser/visual PASS;
опубликовано59cbd85b. Полный К06 открыт; актуальный результат — DENTAL-MCS checkpoint.

Управление медицинскими ролями B08: добавлены owner-only read/API определения,
назначения, отзыва и истории оснований. Основания шифруются в отдельной revision
(migration0019); общий CRM audit не содержит текста. Старые назначения сохраняются
без выдуманного основания.66 HTTP/domain/read/access/migration tests, check/drift
PASS в isolated runtime; доказательства — DENTAL-MCS checkpoint. S18/M21 подключён
и опубликованc135008d:9 browser PASS,26 снимков просмотрены,19 backend/check/drift,
types/build/i18n PASS. Полный M02/M06 остаётся открытым.

Локально реализована интеграция личных уведомлений об участии (migration0016):
фиксированный адресат, нейтральная проекция без PHI, current ACL общей ленты,
атомарность с командой и private medical notification-context API. Подключены UI
переход из личной ленты, ответ адресата и окна участия/передачи, переводы RU/KK/EN.
Основные desktop/mobile и отказ/recovery сценарии проверены; проверка
обновления после закрытия окна пройдена. Точный Git-срез — DENTAL-MCS checkpoint.
Продолжение B07 добавило обязательную шифрованную причину отказа, private projection
инициатору и форму в обоих UI входах.67 focused backend tests/check/drift PASS;
миграция0017/зависимые проверки и10 UI сценариев PASS,15 снимков просмотрены.
Точный Git-срез и ограничения отслеживаются в checkpoint. Полный M06
и PostgreSQL concurrency остаются открытыми.

Следующее дополнение B07: отдельное шифрованное направление работы, плановая дата
без автоматического отзыва и имя инициатора в разрешённых проекциях приглашения.
Новые команды требуют направление и дату, старые успешные команды сохраняют replay;
migration0018 не выдумывает сведения для прежних строк.100 affected backend tests,
check/drift и isolated migration roundtrip PASS; UI поля подключены, сборка/types/i18n
PASS;24 distinct browser сценария PASS,20 снимков просмотрены. Формат даты
дополнительно перепроверен на всех языках/viewport. Точный срез — DENTAL-MCS checkpoint.

Срез59: серверная команда завершения active-участия медруководителем с причиной
и явно выбранным ответственным, encrypted closure reason и participation_ended audit.
445 medical tests/check/drift PASS в изолированной БД (migration0014). Это доменный
переход; срез60 подключил команды HTTP (41 API/dependent tests/check/drift PASS).
Срез61:incoming/managed read API проверен50 tests/check/drift PASS.
Срез62:proposal candidate lookup с общими проверками команды —59 tests/check/drift PASS.
Responsible selector/private API добавлен и проверен вместе с затронутыми командами
в isolated DB; lookup не выдаёт медицинские права ответственному. Typed frontend
transport реализован; workspace-access/mine и head patient-context подключены.
UI приглашения/принятия/head end локально проверен на desktop/mobile RU/KK/EN,
включая loading/empty/read+write recovery, optimistic conflict и role revocation.
Снимки просмотрены; доказательства в DENTAL-MCS checkpoint. Это не полный M06/M07.
Обычное завершение получает доменную основу: own-end с medical_participation:update,
проверкой открытых назначенных Appointment и черновиков MedicalEncounter, audit/replay.
44 affected tests/check/drift PASS. Полный набор обязательных MedicalDocument,
HTTP/UI обычного завершения ещё не готовы. К05 добавляет отдельный24h correction
request/review/close и target-only workspace своего приёма/документа. Draft write
версионирован; документ сохраняет captured source. SQLite/domain/API и PG race
проверены по checkpoint; browser/visual/recovery acceptance фиксируется там отдельно.
Это не full К05 и не подпись исправления: team assistant/support и К08/К09 остаются.
Назначения, задачи и оплаты автоматически не меняются.

M11 получил внутреннее хранение черновиков MedicalDocument/MedicalDocumentRevision:
зашифрованные снимки клинического источника, версии текста шаблона, реквизитов
Business/Branch и раздельного авторства prepared_by/performed_by. Изменение текущих
реквизитов не переписывает снимок. Это не готовая форма или подписанный документ:
нет PDF/файла логотипа, снимка медицинской лицензии/квалификации, утверждённой матрицы,
подписи и выдачи. Добавлены доменные create/update своего черновика основным
врачом и read точной версии: current medical_documents role/branch/basis,
verified identity для записи, audit exact version, HMAC replay и atomic rollback.
Assistant/team/24h workflow ещё открыт; внутренний raw template
snapshot не объявляется утверждённой формой. Добавлен approved source path:
основной врач выбирает доступную утверждённую версию и передаёт document_text.
Schema3 хранит исходный template и source/approval metadata отдельно от текста
документа, зашифрованную личность пациента и источник приёма (точная версия,
номер карты, дата/время и timezone); schema1/2 остаются читаемыми. Новые версии шаблона не меняют старые
документы. Проверки source path отмечены в checkpoint. Низкоуровневые storage helpers
по-прежнему требуют авторизованного вызывающего сервиса и общей audit-транзакции.
Добавлены /medical/documents/ create/update/list/history/version: строгий вход,
no-store/private, current treatment basis и exact-version audit; ограниченная
пагинация, фильтр приёма, audit failure rollback. UI подключён через вкладку
документов приёма: list/detail/history, создание из утверждённого шаблона и
редактирование текущего черновика.6 document RU/KK/EN desktop/mobile сценариев,
8 clinical регрессий, build/types/i18n PASS;61 снимок просмотрен. HTTP503/409/403
в document UI проверены инъекцией ответов; backend ACL доказан отдельными тестами.
Полный M11 остаётся открытым; результаты и граница в DENTAL-MCS checkpoint.
Document workspace-access сообщает текущие самостоятельные права на документы и
revisions для редактора;41 affected tests/check/drift PASS, включая отсутствие
зависимости от clinical edit, unverified/finalized ограничения и owner/branch denial.
Добавлен внутренний preview: однопроходная подстановка разрешённых полей без
вычисления выражений; неизвестные поля сохраняются, отсутствующие отмечаются.
Текущие права create/update, утверждённый источник и аудит обязательны. HMAC
источника проверяется до и после записи снимка; устаревший preview отклоняется,
успешный replay возвращает прежнюю версию.85 affected tests/check/drift PASS.
Preview и expected_source_digest подключены к HTTP/UI: новый текст заполняется
из источника, ручные правки сохранённого документа не перезаписываются.22 API/domain
теста PASS; браузерная приёмка нового среза указана в checkpoint. Выбор полей при
создании личного/общего шаблона подключён к renderer catalog;15 API +12 browser
+1 boundary PASS,52 снимка просмотрены; build/types PASS. Лицензия/квалификация и полный M11 ещё открыты. Проверки и точная граница M11 — в DENTAL-MCS checkpoint.

Классификация шаблонов: личный/общий draft API и version reader поддерживают
зашифрованные language/category/specialty и снимки существующих Service (ID/имя).
Метаданные принадлежат версии, сохраняются при text-only update и не меняют
утверждённую версию задним числом. Редактор классификации подключён: язык,
категория, специальность, поиск/пагинация существующих услуг, выбор и удаление
привязок. История и рассмотрение показывают снимок конкретной версии. Локально
26 серверных и20 браузерных сценариев PASS,102 снимка просмотрены; итоговая
сборка PASS. Точный срез и команды — DENTAL-MCS checkpoint. К02 добавляет поиск
доступных шаблонов и приостановку/возврат применения медруководителем с причиной
и историей. Domain/API, roundtrip миграции, browser/visual RU/KK/EN desktop/mobile
и итоговая сборка проверены локально. Из найденной версии создаётся документ;
пауза во время выбора обрабатывается без потери контекста. Публикация и команды
зафиксированы в DENTAL-MCS checkpoint. Полный M11 остаётся открытым: PDF/подписи,
матрица обязательности и остальные критерии документов не входят в закрытие К02.

Медицинские реквизиты: добавлен внутренний versioned storage
MedicalCredentialProfile/Revision для лицензии клиники и специальности/должности/
квалификации BusinessMember. Тексты зашифрованы, имена и общие реквизиты не
дублируются. Это не подтверждение действительности лицензии/квалификации.
Добавлены явное подтверждение медруководителем, атомарный аудит, HTTP current/
history/member options и Settings UI. Врач читает только свой профиль. Документ
schema4 сохраняет точную подтверждённую версию реквизитов, preview выявляет смену
источника. К01 локально принят:105 affected/dependent tests и отдельный migration
roundtrip PASS,8 credential browser scenarios +1 template regression PASS,
43 снимка просмотрены, сборка/types/i18n/static PASS. Точный срез и публикация
в DENTAL-MCS checkpoint. Рабочая БД не
мигрировалась. Госреестры, нормативная достаточность и ЭЦП этим не подтверждаются.

Добавлено внутреннее хранение MedicalDocumentTemplate/Revision для общих и личных
шаблонов: scope Business/owner member, зашифрованные title/text/reason, отдельное
авторство и история версий. Название не может состоять только из пробелов.
Версия в registry не означает клиническое утверждение:22.11.2026 владелец согласовал
утверждение личных шаблонов и управление общими медруководителем, без этого права
у владельца Business без медицинской роли. Выбор утверждённого шаблона при создании
медицинского документа подключён на domain/HTTP/UI уровне через документы приёма.
Добавлен domain submission/decision/read
MedicalTemplateReview: конкретная версия, head-only approve с business scope,
encrypted receipt, audit/replay/stale/rollback;141 affected backend tests/check/drift
и isolated migration roundtrip PASS. Добавлены review API submit/read/decision
и очередь текущих pending версий с пагинацией;56 affected tests/check/drift PASS,
дополнительный прогон6 HTTP tests с tenant/stale/revocation PASS.
Review UI S17 подключён: автор отправляет версию с подтверждением, медруководитель
открывает очередь, утверждает или возвращает с обязательным комментарием;
статус и причина доступны в конкретной версии и её истории.6 review RU/KK/EN
desktop/mobile сценариев и1 reviewer conflict/denial PASS;8 draft регрессий PASS,
48 снимков просмотрены;58 affected backend tests/check/drift PASS. Полные команды
и границы evidence в checkpoint, это не подтверждение PostgreSQL concurrency.
PostgreSQL concurrency не подтверждена. Для личных черновиков реализованы domain/API create/update/list/
history/read: текущая роль doctor/head, own scope, server-owned identifiers,
точный version audit, no-store/private, replay/stale/rollback. UI S17 личных
черновиков подключён: список, редактор, история;8 desktop/mobile browser сценариев
на RU/KK/EN с пагинацией/read recovery и2 settings regressions PASS;22 снимка
просмотрены, подробные проверки в checkpoint. Добавлен workspace-access для получения текущих прав на личные
шаблоны без чтения их содержимого. Подстановка полей и PDF также остаются открытыми.
Добавлены domain/API общих шаблонов: head-only управление, версии, явная отправка
и утверждение, metadata текущих прав; approved selector выдаёт только общие либо
собственные утверждённые версии. Новый draft сохраняет прежнюю approved версию
доступной.63 focused domain/API tests PASS в изолированной SQLite, включая personal
регрессии, replay/stale, scope denial и audit rollback. Общий UI подключён к S17:
отдельный режим head, существующие редактор/история/отправка и очередь утверждения.
6 common RU/KK/EN desktop/mobile сценариев и15 personal/review регрессий PASS;
66 применимых снимков просмотрены, build/types/i18n PASS, подробности в checkpoint. Интеграция selector в создаваемый
документ реализована на domain/HTTP уровне, UI ещё нет; PostgreSQL concurrency не проверена.

Добавлены source-scoped филиалы и исходящие предложения врача:82 focused/dependent
backend tests/check/drift PASS в изолированном SQLite. UI из записи и active
participation позволяет выбрать другой филиал, предложить участие и отозвать
pending; до принятия получатель не получает clinical basis, исходное основание
сохраняется. Основные6 RU/KK/EN desktop/mobile сценариев проверены, снимки форм/
статусов просмотрены; mobile recovery/conflict/denial и2 существующих регрессионных
сценария PASS. Публикация этого дополнения отслеживается в checkpoint; PostgreSQL/полный ACL/уведомления и
остальной M06/M07 этим не закрыты.

Для новых приглашений добавлено хранение проверенного исходного основания врача
(migration0015), отдельно от действующих прав. Старые строки сохраняются без
догадочного backfill; head-назначение остаётся основанным на роли/филиале.
Проверки и публикация этого дополнения — в DENTAL-MCS checkpoint. На этом основании
работает описанная выше личная лента; внешняя доставка пациентам этим не реализована.

Одонтограмма: добавлена схема DentalToothState/DentalToothHistory с ключом
пациент/зуб/поверхность, цепочкой редакций, автором и приёмом (migration0012).
29 schema/dependent tests/check/drift PASS в изолированной БД. Добавлены внутренние
encrypted append/read helpers с привязкой к метаданным и откатом ошибки шифрования;
30 crypto/storage/dependent tests/check/drift PASS. Добавлен аудит конкретной редакции
с PROTECT и проверками ссылок (migration0013);32 focused и380 apps.medical tests PASS,
check/drift PASS. Добавлены авторизованная команда основного врача и чтение точной
редакции с аудитом:50 focused/dependent tests/check/drift PASS. HTTP-контур
/api/medical/tooth-observations/ проверен:40 focused/dependent tests и check/drift PASS (срез51). Добавлены snapshot на момент наблюдения и
постраничная история каждой позиции:41 focused/dependent tests/check/drift PASS
(срез52; дополнительные12 edge tests PASS). Typed frontend transport добавлен (срез53:10 tests/types/build PASS); Read UI подключён:формула/дата/точная история,6 RU/KK/EN desktop/mobile tests PASS (срез54); срез55 добавил редактор зуба целиком с защитой несохранённого текста (6 browser PASS). Срез56:API допустимых поверхностей/переводов и общий валидатор чтения/записи проверены41 tests/check/drift. Срез58:выбор поверхности в UI проверен6 localized+1 regression browser/types/build/screens (checkpoint); полная S04 ещё не завершена; медицинская легенда остаётся
неподтверждённой, поверхности требуют явно настроенного одобренного словаря.


Добавлен клинический HTTP-контур `/api/medical/encounters/`: открытие по существующей
карте/записи, сохранение основным врачом, чтение точной версии по действующему основанию.
Использует encrypted revisions, атомарный audit/idempotency и no-store на ответах/ошибках.
Создание активной карты с локальным номером подключено через `/api/medical/records/`,
с отдельным record_opened audit и запретом дубликатов. Workspace API выдаёт активную карту
и ограниченную страницу приёмов без расшифровки текста, с READ audit и текущим ACL.
API revisions перечисляет прежние редакции с автором/временем и пагинацией, без текста;
выбранная версия читается отдельным audited endpoint. Appointment-context определяет
профиль пациента и доступные действия из назначения врача в календаре; чтение
аудируется и не возвращает клинический текст. Это серверная часть: командные
вклады, полный ACL и завершение/подпись ещё не готовы. Начат клинический интерфейс:
из календаря доступны открытие карты/приёма, форма черновика и история с просмотром
редакций только для чтения. Переключение вкладок сохраняет несохранённый черновик;
отказ доступа очищает медицинский контекст. При закрытии изменённого черновика
доступны сохранение с выходом, продолжение редактирования и выход без сохранения.
Ошибка сохранения оставляет текст и окно открытыми. Остальные клинические разделы остаются открытыми. Доказательства — основной DENTAL-MCS checkpoint.

По новому поручению DENTAL-MCS создана единая матрица полного ТЗ. Первый срез кода
добавляет строгую проверку medical_records в существующий capability resolver.
Следующий срез содержит nullable схему профиля/DB check и реестр core_v1,
dentistry_v1/v2: медицинские ресурсы требуют v2 и явных зависимых разрешений;
отзыв читается без устаревшего кеша, лишние строки не расширяют профиль.
Initializer создаёт core_v1/dentistry_v1 в существующих create paths, а К03
добавляет dentistry_v2 для новых стоматологий при release-ready config (default
false). Additive CLI для существующих legacy/v1 имеет dry-run по умолчанию,
атомарный audit и безопасный повтор. Domain/concurrency10 проверок PG17 и2 API
проверки SQLite PASS;6 distinct desktop/mobile browser и visual PASS. К03 открыт
по owner-clinician решению; проверки/публикация в checkpoint. Working rollout
не запускался, медицинские данные и роли автоматически не создаются. Серверные
планы и деньги проверяют профиль. Добавлен apps/medical: криптография с отдельными
ключами и привязкой к Business/Client/полю, PatientProfile OneToOne Client,
ограничения подтверждённой идентичности и защита ordinary merge/hard delete Client.
Также реализована основа явного MedicalRoleAssignment с существующими role/rules,
проверкой отзыва/филиалов и без owner/support обхода; общие редакторы прав не
выдают medical_* и сохраняют историю назначений при попытке удаления.
Owner define/assign/revoke services используют общие role/rules/idempotency,
revision и атомарный audit; replay не восстанавливает отзыв. Общий CRM role/branch
grant не меняется при медицинском назначении. Подтверждающий права владельцу-врачу
пока не определён; самовыдача запрещена. Owner-only role-management API подключён;
S18/M21 в настройках подключён:9 browser-сценариев PASS,26 снимков просмотрены,
desktop/mobile RU/KK/EN. Это не закрывает полный ACL и остальные критерии M06.
Доменное создание unverified пациента проверяет medical role/branch и CRM Client
view; шифрует административные поля и атомарно пишет MedicalAuditEvent. Общий
idempotency store получает только keyed fingerprints, replay проверяет отзыв прав.
Контакты не копируются; проверенный ИИН в том же Business требует разбора без утечки.
Добавлен writer предварительных unverified данных: revision/reason, зашифрованная
предыдущая версия, audit и повтор команды без повторной записи; verified-профиль
требует отдельного процесса. Initial verify реализован как доменная команда с
явной ролью/обучением, per-Business protocol config, Client/Patient version guards,
шифрованными evidence/history и атомарным audit. Без внешне утверждённого настроенного
протокола verify503; реальных approvals не получено. Controlled correction имени/
даты/пола/адреса реализована с причиной/recheck/history/audit и update+approve;
К04 добавляет исправление ИИН с повторной проверкой и head approval при медицинской
истории, encrypted revisions/audit и UI request/approve/reject. Перепривязка историй
и резервный read audit остаются открытыми. Поиск пациента и атомарное создание
Client+PatientProfile доступны из ClientsPage; verified ИИН не создаёт дубль,
контактные совпадения требуют отдельного подтверждения. Scoped backend/PG/browser
и сборка проверены; точная граница и публикация в DENTAL-MCS checkpoint.
Дополнительный bounded list-projection показывает reception наличие медкарты и
identity status только в разрешённом CRM/medical/branch scope, без clinical text.
Колонка переиспользует desktop table/mobile card; отдельная клиническая проекция
врача/команды и все вкладки остаются в К05/К06.
Общие Client.save/import и conditional editor защищают имя
verified пациента и Business привязанного Client; обычные контактные поля сохранены.
Reception-only административный HTTP API соединяет create/read/preliminary/verify/
correct; read требует успешного medical audit, ответы no-store, обычные
PUT/PATCH/DELETE/list/export отсутствуют. Clinical/evidence/history не возвращаются.
GET access/ возвращает текущие reception role actions в выбранном филиале без PHI.
Typed frontend API client и административная панель в ClientWorkspacePage подключены;
create/preliminary/verify/correct формы прошли6 локальных Chromium lifecycle
сценариев RU/KK/EN desktop/mobile viewport и1 recovery с реальными409/403.
Отдельный boundary сценарий PASS: филиалы/задержанный ответ, protocol503/retry,
длинные значения tablet/mobile и scoped axe WCAG2A/AA форм без violations.
Снимки просмотрены, final build PASS; native mobile/full medical acceptance открыта.
Verification-form API отдаёт утверждённые конфигурацией labels RU/KK/EN и схему
полей только обученному reception с approve; внутренние approvals/member IDs скрыты.
Без полного описания формы503; реального протокола и внешнего утверждения пока нет.
Read journal fallback остаётся открытым; denial audit реализован для scoped API,
medical v2 rollout реализован в К03, рабочая БД не переводилась;
локальная граница клинического UI описана выше.
Представители: добавлен слой хранения PatientRepresentative на существующем Client,
период/проверивший/отзыв/revision и поля для зашифрованных оснований и полномочий.
Merge/identity guards защищают представителя, контакты и архив остаются доступны.
Добавлены доменные подтверждение/отзыв, отдельный протокол/обучение, шифрование,
версии/idempotency и атомарный medical audit. Authority prerequisite проверяет
конкретную связь/полномочие/период/отзыв. Administrative list/form/verify/revoke API
подключён с reception guards, no-store и audit read; закрытые основания не выдаются.
UI представителей подключён в медицинском профиле:6 RU/KK/EN desktop/mobile happy
flows verify/list/revoke PASS, screenshots inspected; build/types/i18n PASS.
Keyboard/axe,503 retained draft/same key, real stale revoke409 PASS на RU desktop;
affected patient regression с representative recovery9/9 PASS. Mobile protocol retry,
self-selection, invalid period400/retained draft, real role403/clearing и axe PASS.
Подключение к выдаче документов и native mobile verification ещё требуются.
Это пока не принятый законченный пользовательский сценарий; внешние документы/
возрастные правила не утверждены. Текущий объём проверок указан в checkpoint.
Основание врача по конкретной записи реализовано как отдельный server prerequisite:
14 focused и216 medical tests/check/drift PASS (срез26). Сам helper не выдаёт карту:
TreatmentParticipation storage/active-basis добавлены (migration0007,medical225/check/drift
PASS); propose/recipient accept/decline с audit0008 и idempotency добавлены, итоговый
medical242/check/drift PASS. Pending withdrawal добавлен (8 focused/34 affected PASS,
check/drift); завершение медруководителем и audited reader/API/UI подключены позже
и описаны выше. Обычное завершение с обязательствами, временные grants и notifications
остаются открытыми.
Medical record/Encounter/revision storage добавлены (migration0009,medical259/check/drift
PASS). Encrypted revision append/read helpers добавлены (33 affected/check/drift PASS),
после них подключены authorized draft commands/audit и clinical reader/API/UI.
Atomic completion ещё не реализован. Эти проверки не подтверждают полный
ACL/подпись/медицинскую приёмку.
[Текущие проверки и весь остаток](../testing/task-state/DENTAL-MCS-20261122.md).

## Ядро и стоматологическая кастомизация — 22.11.2026

[Карта24 backend apps, frontend и интеграционных связей](../testing/evidence/crm-core-dentistry-map-20261122.md)
на4a3214a6 + WIP: планы/плановые деньги/UI/голосовая plan-ветка отнесены владельцем
к dental-модулю. Также найдены dentistry-presets onboarding/Inbox; общие сущности,
AI runtime, каналы, записи и обычные платежи остаются общими. Pricing — отдельная
торговая подсистема Kaspi. Клинические модели/пациентский портал не обнаружены
в этой инвентаризации. Это статический анализ, не новый runtime PASS или code split.

## Границы модулей — 21.11.2026

BusinessCapability, профильный resolver/initializer и сервисы/API/UI планов
реализованы. Планы связаны с lifecycle записи, платежами и merge клиентов.
[Карта связей и план CRM-D04](../current/crm-modularity-plan.md) сохраняют исходное
статическое обследование02682f04; актуальные проверки реализации находятся в
[DENTAL-MCS checkpoint](../testing/task-state/DENTAL-MCS-20261122.md).
Уточнение владельца21.11: только однократное серверное назначение профиля при
создании бизнеса по выбранной сфере, без пользовательского управления/смены/отключения.
Первоначальная спецификация core_v1/dentistry_v1, пяти create paths, nullable-метки,
legacy resolver и writer guards реализована в отдельно разрешённом DENTAL-MCS.
Dentistry_v1 добавляет visit_plans/plan_payments; medical_records требует v2.
Серверные writers запрещают пользовательскую смену сферы/состава. К03 реализует
согласованное D02 подключение v2 после готовности выпуска; его проверки и открытый
owner-clinician сценарий описаны выше. Это не разрешение рабочей миграции или
deployment; прежние scoped evidence не превращаются в полную приёмку модуля.

## Глобальный поиск — 18.11.2026

Единая область CRM без выбора текущей страницы; локальные фильтры страниц независимы.
Клиенты/записи: серверный поиск с пагинацией. Задачи/диалоги: первая API-страница,
неполная выдача и состояния ошибок; поиск диалогов по имени/сообщению не обеспечен
используемым API. Локальная проверка удаления селектора пройдена; это не сертификация
полноты глобального поиска. [Полный анализ и проверки](../testing/evidence/global-search-20261118.md).

## Общая проверка CRM: исправления — 12.11.2026

Все десять подтверждённых F01–F10 исправлены и адресно проверены: архив/права
клиента, поиск, причины409, refresh переноса, widget reload/retry, смена пароля,
demo reset и локализация системных значений. Backend/Node/build/system/drift
и scoped browser PASS; составной локальный снимок, без real sends/workingDB/deploy.
Семь других проверок и три наблюдения закрыты в адресной границе
[нового среза](../testing/evidence/crm-global-remaining-20261112.md): fixtures/registries,
SYSTEM reminder, локальное время истории, переходы задач и retry Inbox.
Непокрытая204-ID матрица, полный S04/load и CRM/release готовность остаются открыты.
[Исправления, проверки и ограничения](../testing/evidence/crm-global-fixes-20261112.md).

VOICE-PLANNER11.11: воспроизведён неверный JSON field plan при точном STT.
Default/tier модель теперь определяется до JSON capability; parser/права/replay
сохранены. До исправления1из12FAIL; после24/24real synthetic API→Client/replayPASS,
48planner calls в json_object.148сценариев проверены:146PASS сразу,2старых fixtureFAIL
устранены после old/current сравнения; финальный quality+regression30PASS,system/driftPASS.
Scoped остатка кода/проверок нет; human/fullD01/production остаются открыты.
[Причина, точные границы и результаты](../testing/evidence/voice-planner-20261111.md).

## Точность голосовой диктовки — 11.11.2026

VOICE-RECOGNITION11.11: Scribe v2 и точное преобразование отдельных цифр телефона
заменили ошибочный Whisper default.10 synthetic STT/API→CRM/replay PASS,118 backend
и system/driftPASS. Отдельный дефект JSON-режима закрыт срезом VOICE-PLANNER11.11;
human/KK/mixed/noise/fullD01/production не закрыты.
[Сравнение, стоимость, проверки и остаток](../testing/evidence/voice-recognition-20261111.md).

## История действий — 11.11.2026

`/app/timeline`: понятные RU/KK/EN события, разрешённые сохранённые изменения,
название объекта отдельно от клиента и автор действия. Имена/ссылки проходят
текущие права ресурса и Business; mobile использует компактный список и раскрываемые
фильтры. Это локальный scoped результат, не новая release/live сертификация.
[Evidence](../testing/evidence/timeline-fixes-20261111.md).

## Локальная интеграция лендинга — 06.11.2026

Предоставленный лендинг включён в обычную сборку CRM и доступен в корне;
вход использует существующий `/login`. Локальные build/browser/Caddy проверки
пройдены; лендинг опубликован как1dc5a6c8 (CI PASS) и развёрнут на защищённом
стенде отдельной static/Caddy-дельтой с сохранением прежней SPA и пароля.
Главная/форма входа/языки/mobile/HTTPS/backup проверены; вход в учётную запись
после этого развёртывания не выполнялся. [Evidence](../testing/evidence/crm-landing-integration-20261106.md).

Дельта по решению06.11: автоматическая основная точка без повторного каталога,
явная настройка второй точки, серверный запрет архивирования последней активной,
контекст филиала и конкретные уточнения голосовой записи реализованы.
Локальные проверки, состояние рабочей схемы и остаток публикации —
[SINGLE-LOCATION-20261106](../testing/evidence/single-location-20261106.md).
Исторический MB1–MB5 PASS не подменяет проверку этой дельты; full D01/live открыты.


IMPORT-WORKSPACE04.11: локально реализованы CSV/XLSX → клиенты, услуги,
специалисты и записи; исправления/поля/связи/профили, preview и фоновой перенос.
Дополнительные поля доступны в обычных consumers/фильтрах/экспорте. Перенос без
creation effects, будущая активация отдельная. Публикация/рабочие миграции/live
не заявлены. [Точная граница](../testing/evidence/import-workspace-20261104.md).

C02 / TEAM-ANALYTICS, 04.11.2026: `/api/team/performance/` intersects Lead
selection with current LEADS VIEW scope and enabled capability before counts,
loss reasons, rates and team summaries. Existing report membership and source/date
filters remain; denied/disabled Leads yield zero/empty fields. Other independently
readable source metrics are unchanged and not certified by this Lead-only fix.
Local evidence: [C02](../testing/evidence/remediation-c02-20261104.md).

CRM-R01, первый пакет31.10: ручной Клиент/Inbox → один Appointment с отдельным
ответственным, source provenance, актуальными guards и общим состоянием карточки/
календаря/списка клиента реализован и локально проверен. Это частичный результат
новой R01-дельты. Первый Records workspace02.11 добавляет list/detail/pipeline,
замену merchant Lead/Deal входов и consumers, early completion, scoped задачи,
метрики и AI/automation defaults. [Исходный локальный evidence](../testing/evidence/records-workspace-20261102.md)
сохраняет границу своего снимка. Records и организационный VisitPlan/неназначенные
этапы/назначение слота затем проверены и опубликованы6349acdf:
[публикационный срез](../testing/evidence/records-publication-20261103.md),
[проверки плана](../testing/evidence/visit-plans-20261102.md). Это не deployment
и не приёмка последующего WIP. Оплата планов добавлена локально18.11: версии цен, пакет/визиты, аванс/зачёт, возврат/сохранение/перенос. Утверждённый follow-up локально проверен: owner-only аннулирование ошибочного завершения, связанная замена, явный reuse и присоединение всего однозначного старого остатка без нового поступления; [проверки и ограничения](../testing/evidence/visit-plan-payments-20261118.md). Отдельно реализованы и локально проверены прекращение плана, отказ от неоказанной услуги по согласованной доле, отмена будущего времени, сохранение долга и связанная повторная запись без изменения цены; возврат/сохранение остатка остаются отдельным решением. [Результат и ограничения](../testing/evidence/visit-plan-payments-20261118.md#plan-termination-refusal-20261118). Полная D01/live, произвольный terminal reopen, переоценка оказанных услуг и неоднозначные legacy источники не закрыты.

# Карта реализации и оставшихся границ

PILOT-ACCESS-20261031 adds isolated two-Business onboarding/access acceptance:
public signup, invited correct account, current role/tenant denial, revocation and
restoration preserving specialist/history, auth/MFA/session/reset and races.
Existing security fixes are integrated, not a new permission model. No live pilot
or production readiness claim. [Evidence](../testing/task-state/PRIMARY-SESSION.md#pilot-access-20261031--two-business-onboarding-and-access).

YCloud TP Lite, 29.10: локально реализованы подключение одного WhatsApp API-номера,
подписанный приём, текстовый обмен через существующий Inbox и статусы доставки.
Изолированные backend/PG/readiness и frontend build/browser результаты —
[паспорт интеграций](integrations.md#ycloud-tp-lite--локальный-первый-этап-29102026)
и YCLOUD-TPLITE-20261028 в PRIMARY-SESSION. Это не live-активация: доступ TP Lite,
целевой сервер, рабочие миграции и реальная доставка остаются открытыми R02/R03.

NOTIFICATIONS-PERSONAL-20261028, локальная проверка 29.10.2026: личная лента,
независимые отметки сотрудников, фиксированная аудитория объявлений, owner/admin-only
публикация/отзыв/поимённый мониторинг реализованы. Read-all не фиксирует ознакомление;
отзыв скрывает публикацию, сохраняя историю. Рабочий источник проверяется по текущим
правам; внешняя клиентская доставка остаётся отдельной. Backend304 в итоговой
совокупности (255 с четырьмя исправленными фикстурами +49 dependent), migration1,
PG concurrency3, system/drift, frontend types/i18n/build и targeted RU/KK/EN browser PASS.
Точное разбиение прогонов и ограничения — NOTIFICATIONS-PERSONAL-20261028 в PRIMARY.
HEAD98925b67 + WIP, без commit/push/working migration/deployment. Код/доказательства/
решения без остатка в принятом scope; окружение и публикация отдельно. OFFICIAL-21 /
AUD-17 сохраняет прежнее scoped evidence; shared-read правило заменено новым
согласованным персональным контрактом, исторические отчёты не переписаны.

FU-HIST-02, 28.10.2026: public form/widget success hides private contact matches
and CRM associations using constant compatibility fields. Internal matching and
staff evidence retained; preview reports new conversation only. Final106 isolated
tests PASS (12 new), system/drift/syntax/frontend checks and app+widget builds PASS;
independent review no findings. HEAD98925b67 + prior WIP + patch, local only.
Evidence/limits: FU-HIST-02-20261028 in PRIMARY-SESSION; no live/publication claim.

OFFICIAL-03, 28.10.2026: WhatsApp verified channel/Bot/Business binding is retained
through routing; all-change preflight, per-change status/log routing and Bot-scoped
message lookup close the local cross-tenant path. Final102 isolated tests PASS,
including20 new regressions; independent review no findings. Initial failures and
compatibility correction retained in OFFICIAL-03-20261028, PRIMARY-SESSION.
HEAD98925b67 + prior WIP + patch; no publication, live delivery or PG certification.

OFFICIAL-22, 28.10.2026: AI approval identity/payload/validity is immutable from creation;
reason-only generic edits preserve current decision/execution state. Legitimate exact-command
approval/replay and permission checks retained. Final17 new regressions and78 dependent tests
verified on unchanged source; initial expectation failure/correction visible in OFFICIAL-22,
PRIMARY-SESSION. HEAD98925b67 + prior WIP + patch; local scope closed, publication/live and
PostgreSQL concurrency certification remain separate. No new schema/provider behavior.

OFFICIAL-13, 28.10.2026: appointment automation status requires current Notification
VIEW/scope before counts and failed rows; Client/Appointment projections and calendar
URL copies obey independent read access. Final116 isolated tests PASS (21 new); evidence,
review repair and exact limitations in OFFICIAL-13-20261028, PRIMARY-SESSION. Local scope
closed at HEAD98925b67 + prior WIP + patch. No new delivery behavior, schema or module;
publication and production acceptance remain separate and unclaimed.

OFFICIAL-09, 28.10.2026: catalog Service import/manual writes require current SETTINGS
UPDATE and shared-object branch scope. Inactive/archive flags survive metadata updates;
atomic rollback and ordinary permitted/product-only paths verified locally. Evidence and
exact environment/commands: OFFICIAL-09-20261028 in PRIMARY-SESSION. HEAD98925b67 + prior
WIP + patch; no new schema, provider delivery or production/PG certification. Local scope
closed; publication not performed and target-environment acceptance remains separate.


OFFICIAL-19, 28.10.2026: existing outreach role eligibility is now intersected
with current NOTIFICATIONS action/object decisions at all12 role-helper callsites.
CRUD uses CREATE/UPDATE and server-owned candidate; campaign actions and consent bulk
use existing MANAGE map/actual campaign or consent candidate. Explicit overrides and
OWN/TEAM/current membership apply before writes/domain calls. No new role eligibility
or Client-derived consent owner. Capability helper reused; notifications currently has
no module mapping/toggle, only injected disabled-boundary integration proof claimed.
BEFORE22:14 failing methods/17 security assertions,8 controls PASS. AFTER27 new tests
within98 affected and combined1095 PASS/no skips; syntax/system/drift/diff/reverse PASS.
HEAD98925b67 + WIP/18 prior closed packets + patch. Evidence OFFICIAL-19-20261028 and
output/security-remediation-20261028/outreach-mutation-permissions/fix-report.md.
No real delivery or production/PG/full browser certification.

OFFICIAL-18, 28.10.2026: Lead follow-up Task creation now validates the
resolved assignee with ordinary validate_assignment(creating=True) and checks TASKS
CREATE on the final unsaved Task, not on the source Lead. Current source Lead VIEW,
Business/module and archive/lock checks remain; direct service calls also enforce actor.
Wrong source-based TASKS guards removed for this action only. No TASKS UPDATE required,
default/null/unassigned behavior retained where normal creation policy permits.
BEFORE20:8 security gaps,2 false denials,10 controls. AFTER28 new tests within113
affected and combined1068 PASS, zero skips; syntax/system/drift/diff/reverse PASS.
HEAD98925b67 + WIP/17 prior closed findings + patch. Evidence OFFICIAL-18-20261028
checkpoint and output/security-remediation-20261028/lead-task-assignment/fix-report.md.
Local assignment-boundary proof only; generic replay/production/PG not certified.
This is OFFICIAL-18, unrelated to already-closed historical AUD18 export.

OFFICIAL-17, 28.10.2026: Client import writes now distinguish current UPDATE
for existing matches (including archived/no-op) from CREATE for new Clients, under
the existing object policy. Shared Client notes write rule is reused by API/import;
proposed fields are validated before mutation. Client/Lead/Deal sheets use the same
Client boundary/current request actor; legacy direct row calls use job.actor, no actor
fails closed. Fill-only matching, duplicate warning, archive state and atomic rollback
remain. Existing ImportJob CREATE admission remains, not an update-only upload feature.
27 new tests within103 affected and combined1040 PASS/no skips; syntax/system/drift/
diff/reverse PASS. HEAD98925b67 + previous WIP/16 closed findings + patch, local only.
Evidence OFFICIAL-17-20261028 checkpoint and output/security-remediation-20261028/
client-import-update-permission/fix-report.md. Current OWN/TEAM UPDATE semantics for
unowned Client retained exactly; no new ownership rule or production certification.

OFFICIAL-15, 28.10.2026: no_change to production code. Current FU-BE-02
already passes actor into CRM-card Task previews and uses it for linked-field masking,
relations/actions; missing actor fails closed. Dedicated12 new regressions cover all
four card routes, forbidden/allowed fields, scalar/list/request/actor, OWN/TEAM/current
rights, Client aliases, parent task/specialist and Business/capability controls.
Current-tree initial11 PASS; final owning131 and combined1004 PASS, zero skips;
syntax/system/migration drift/diff PASS. HEAD98925b67 +15 prior fixes/WIP + tests/docs.
Evidence OFFICIAL-15-20261028 checkpoint and output/security-remediation-20261028/
task-preview-context/fix-report.md. Local scoped closure of an already-remediated
finding; no new functional patch, generic replay or production certification.

OFFICIAL-10 Inbox scope, 28.10.2026: create-action responses now require current
child VIEW/scope/capability and same Business before returning CRM data. Without VIEW,
writes still succeed but direct responses acknowledge read_restricted without record
fields; pipeline child fields are null, created flags unchanged. Task/Appointment keyed
replies reserialize current resource under current actor, never replay old DTO blindly.
Stored receipts, creation/dedup/locking/status unchanged; known metadata ID copies also
guarded. Pending booking without saved Appointment keeps its offered slot.
BEFORE17:15 security failures,2 controls. AFTER20 new tests within75 affected and
combined992 PASS, zero skips; syntax/system/drift/actual frontend consumers/
i18n/types/build PASS. HEAD98925b67 + WIP/fourteen prior fixes + patch. Evidence:
OFFICIAL-10-INBOX-20261028 checkpoint; output/security-remediation-20261028/
inbox-create-read-visibility/fix-report.md. Local scoped proof, not production PASS.

OFFICIAL-16, 28.10.2026: Lead duplicate-check details now pass existing LEADS
VIEW/object scope/capability and Business filtering BEFORE LIMIT5. Hidden rows return
no IDs/messages/status/source; optional restricted-match boolean preserves generic
duplicate warning without private count. Client projection reuses BE02/BE03: no hidden
Client FK or contact lookup/exclusion derived from an unreadable Client ID.
LeadForm preserves allowed counts/self-only editing and generic create-anyway warning,
clearing restricted state on error/no selection. No new endpoint permission or writes.
BEFORE10 security failures +5 controls after timestamp-fixture correction. AFTER15
new tests within86 affected and combined957 PASS, zero skips; syntax/system/
drift/component/i18n/types/build PASS. HEAD98925b67 + WIP/thirteen prior fixes + patch.
Evidence OFFICIAL-16-20261028 checkpoint and output/security-remediation-20261028/
lead-duplicate-visibility/fix-report.md. Local synthetic only; OFFICIAL10 remains open.

FU-BE-03, 28.10.2026: Client duplicate details now require current Client VIEW,
object scope, capability and same Business. CREATE-only keeps one non-identifying
warning for hidden matches; exclude_client_id cannot suppress an unreadable match.
Shared read projection covers Client check/Inbox warning and stored import snapshots,
plus the same DTO copies in form submissions/activity. Current reader used on every
read; stored evidence, matching/import writes and public warning semantics unchanged.
UI keeps duplicate banner/confirmation/create-anyway, no hidden open/merge target.
BEFORE18 security assertions across11 methods +2 reproduced snapshot copies; five
baseline controls PASS after fixture corrections. AFTER20 new tests within136 affected
and combined942 PASS, zero skips. Syntax/system/drift/component/i18n/types/build
PASS. HEAD98925b67 + WIP/twelve prior fixes + patch. FU-BE-03-20261028 checkpoint;
output/security-remediation-20261028/client-duplicate-visibility/fix-report.md.
Local synthetic evidence only. OFFICIAL16/10 remain separate and unclosed.

FU-BE-02, 28.10.2026: linked Client projections now apply existing CLIENTS VIEW,
object scope, capability and same-Business policy. Readable parent records remain;
hidden Client IDs/contact labels and typed copies are masked in serializers, CRM-card,
history, queues, AI context/rules, outreach previews/evidence and CSV. Contact-search and exact Client-ID filter
branches respect Client visibility; stored Lead/Deal export fingerprints include it.
Actor context is explicit; no actor fails closed. Frontend accepts nullable links,
retains generic placeholders and avoids null-equality joins. No new ownership rule.
BEFORE22:61 failing assertions across18 methods,4 controls PASS after fixture correction.
Focused25 PASS; final27 plus affected history/card suites 105 PASS; combined
894 PASS without skips. Syntax/system/drift/component/i18n/types/build PASS.
HEAD98925b67 + prior WIP/eleven fixes + this patch. Evidence FU-BE-02-20261028 in
PRIMARY and output/security-remediation-20261028/client-pii-projections/fix-report.md.
Local synthetic evidence only; no production/provider/browser-E2E certification.

OFFICIAL-05, 28.10.2026: unverified public form/chat flags no longer replace
existing per-channel OPTED_OUT. Common record_explicit_consent creates absent rows
and conditionally updates only non-OUT rows at SQL write, then refreshes existing
result. Refusal evidence/timestamps retained; normal intake/new/UNKNOWN/IN unchanged.
Existing inbound START and authorized management re-consent remain separate and PASS.
BEFORE15 security failing assertions across7 methods; corrected existing404 denial
control PASS before source patch. AFTER106/combined654 PASS without skips;
syntax/system/drift PASS. HEAD98925b67 + WIP/ten prior fixes + patch. Evidence:
OFFICIAL-05-20261028 in PRIMARY; output/security-remediation-20261028/
public-intake-optout/fix-report.md. Only local synthetic consents, no actual sends.

OFFICIAL-11, 28.10.2026: consent XLSX now uses existing bounded core reader
after actual upload max+1 byte check. ZIP expansion/entries/ratio and XML/worksheet
bounds run before openpyxl; rows stream to unchanged consent normalizer, with explicit
file errors and iterator/workbook cleanup. No eager worksheet list or silent trim.
Existing aliases, values, active sheet/cached formulas, CSV and consent rules retained.
BEFORE18:14 failing assertions across10 methods, one old underreported-dimension
error,7 controls PASS. AFTER52/combined551 PASS without skips; syntax/system/drift
PASS. HEAD98925b67 + WIP/nine previous fixes + patch. OFFICIAL-11-20261028 in PRIMARY;
output/security-remediation-20261028/consent-xlsx-limits/fix-report.md.
Only synthetic tiny fixtures/mocks; no stress/production or publication claim.

OFFICIAL-12, 28.10.2026: alternate Deal readers now share existing sensitive
amount policy (owner/admin/manager/accountant or BILLING VIEW as already defined).
CSV/queues/summary/typed activity metadata/CRM timeline/AI rule sources/Deal-value
analytics mask denied monetary fields and derivatives; actor context explicit.
Amount filters/order denied before use; stored Deal export fingerprint includes
field access. Missing context fails closed. Nullable frontend types and two money
helpers show existing '-' for hidden values, preserving ordinary numeric formatting.
BEFORE30 failing assertions across15 methods,3 controls PASS (see fixture correction
in checkpoint); AFTER18+3 supplemental controls,19 unique methods PASS; combined
523 PASS without skips. Syntax/system/drift, i18n/types/main Vite build PASS.
HEAD98925b67 + WIP/eight prior fixes + patch. OFFICIAL-12-20261028 in PRIMARY-SESSION;
output/security-remediation-20261028/deal-amount-projections/fix-report.md.
Local synthetic evidence only; no provider/production/publication certification.

OFFICIAL-02, 28.10.2026: legacy analytics intersects source Lead/Deal/
Appointment/Task VIEW, object scope and capability before counts/grouping/sums.
Reuses existing analytics _scoped in manager metrics, dashboard and legacy summary/
CSV. Member boundary and permitted formulas retained; Lead-to-Deal conversion also
requires a readable Lead without changing the historical reporting-period formula.
BEFORE15:13 failing assertions across10 methods,5 controls PASS; AFTER38/combined
375 PASS without skips, syntax/system/migration-drift PASS. HEAD98925b67 + WIP/
seven prior fixes + patch. OFFICIAL-02-20261028 in PRIMARY-SESSION; evidence in
output/security-remediation-20261028/analytics-resource-visibility/fix-report.md.
Scoped local synthetic evidence only; no production acceptance or publication.

OFFICIAL-07, 28.10.2026: ensure_default_roles now initializes absent presets
only; onboarding never overwrites existing role metadata, activation, JSON, denies,
scope or permission rows. Initialization of a new role is atomic. Explicit audited
TEAM MANAGE permission editing remains separate; no reset API/permission added.
Corrected BEFORE12:11 failing assertions across10 methods,2 controls PASS;
AFTER23/combined316 PASS without skips, syntax/system/migration-drift PASS.
HEAD98925b67 + preserved WIP/six prior fixes + patch. OFFICIAL-07-20261028 in
PRIMARY-SESSION; output/security-remediation-20261028/onboarding-preset-preservation/
fix-report.md. Local isolated synthetic evidence only; no publication/live acceptance.

OFFICIAL-04, 28.10.2026: Notes reads now intersect inherited tenant/Clients
access with the linked record's current VIEW/object scope using existing
scope_entity_history before pagination and serialization. Hidden recognized links
return404 for detail and inherited object actions; ordinary CRUD, archived/unlinked
history and existing non-CRM/system policy remain. BEFORE13:21 failing assertions,
4 controls PASS; inherited archive baseline1 failed. AFTER23/combined270 PASS without
skips; system/migration-drift and syntax/diff PASS. HEAD98925b67 + preserved WIP/five
prior fixes + this patch. Evidence: OFFICIAL-04-20261028 in PRIMARY-SESSION;
output/security-remediation-20261028/notes-linked-object-access/fix-report.md.
Local synthetic SQLite only, no production/live acceptance or publication.

28.10, OFFICIAL-06: outreach использует bounded named-variable render, сохраняет
plain/Unicode/escaped braces и проверяет stored personalized text без повторного
parse. Ordered13/совместно184 без skip, system/drift PASS на 98925b67 + WIP/patch.
Лимиты и совместимость — [operations](../current/operations.md), версия/команды —
OFFICIAL-06-20261028 в [checkpoint](../testing/task-state/PRIMARY-SESSION.md).
Реальных отправок/миграции legacy-данных и production acceptance нет.

28.10, OFFICIAL-08: competitor offer PATCH проверяет effective Business/rule;
recommendation/autopilot observation gate исключают чужие legacy offers. Валидные
create/PUT/PATCH/relink сохранены; focused13/совместно171 без skip и system/drift
PASS на 98925b67 + WIP/patch. Версия/команды — OFFICIAL-08-20261028 в
[checkpoint](../testing/task-state/PRIMARY-SESSION.md). Рабочие данные/провайдеры,
DB constraint и production acceptance не входили в этот scope.

28.10, OFFICIAL-20: readiness/rollout detail использует configured-state flags вместо
raw broker/origin/provider URLs; существующие keys/status/action сохранены. Focused9,
совместно135 без skip, system/drift PASS на 98925b67 + WIP/patch. Это локальный
redaction fix без inspection реальной среды и без production PASS; версия/команды —
OFFICIAL-20-20261028 в [checkpoint](../testing/task-state/PRIMARY-SESSION.md).

28.10, FU-BE-01: invitation token и invite_path доступны только по текущему
TEAM MANAGE конкретного Business, иначе пустые строки. Metadata VIEW и легитимный
share/create/accept/reissue сохранены. Focused11 и совместно174 PASS + 3 PG-only skip,
system/drift PASS на 98925b67 + WIP/patch; публикации нет. Версия/ограничения —
FU-BE-01-20261028 в [checkpoint](../testing/task-state/PRIMARY-SESSION.md).
Старые уже полученные bearer не отозваны; общего security/production PASS нет.

28.10, OFFICIAL-01: generic API не удаляет Business (DELETE 405 для всех actors).
Create/read/update и их audit/tenant guards сохранены. Focused8/affected163 PASS + 3 PG-only skip,
system/drift PASS на локальном 98925b67 + WIP/patch; публикация не выполнялась.
Версия, команды и ограничения — OFFICIAL-01-20261028 в
[checkpoint](../testing/task-state/PRIMARY-SESSION.md). Это узкий fix, не новая
общая сертификация и не реализация lifecycle удаления бизнеса.

23.10: общая UI-политика фокуса разделяет pointer и keyboard, включая auth,
CRM primitives, диалоги и виджет. Scoped browser/build PASS; это не полная
сертификация всех экранов или live deployment. Контракт —
[frontend](../current/frontend.md), evidence — UI-FOCUS-20261023 в
[checkpoint](../testing/task-state/PRIMARY-SESSION.md).

Дельта аудита 17.10 на `56dd124`: прежние scoped PASS не закрывают обнаруженные
обходы generic CRUD/изоляции, offline storage, автоматизации и неполные UI-сценарии.
[Результаты по областям](../testing/project-audit-20261017.md) и
[единственная очередь исправлений AUD](../current/roadmap.md#project-audit-20261017).
AUD-01 реализует изоляцию/очистку offline-данных заявок; AUD-02 — связи/авторство
notes/activity, назначение в формах и серверные журналы отправок. AUD-03 закрывает
выдачу Client.notes через API/карточки/сегменты/CSV по существующей field policy.
Версии и проверки — checkpoint AUD-01-20261017, AUD-02-20261017 и AUD-03-20261017.
AUD-13 закрывает обход UPDATE исходного объекта через PATCH/PUT и проводит
переназначение заявки через сервис; версия и проверки — checkpoint AUD-13-20261017.
AUD-14 защищает неизменяемую историю сообщений, parent scope и server-only delivery
metadata; send/retry сохраняют существующий путь. Версия/проверки — AUD-14 checkpoint.
AUD-15 проверяет связи конфигурации стадий/переходов и сохраняет pipeline существующей
стадии; версия и проверки — checkpoint AUD-15-20261019.
AUD-06 объединяет проверку конфигурации действий в preview/save/activate/execute;
предметная форма и ошибки RU/KK/EN проверены; версия/проверки — AUD-06 checkpoint.
AUD-04 обеспечивает атомарное создание/замену состава и audit/activity, защищает
активный состав при generic CRUD и конкурентных записях. Версия/проверки —
AUD-04-20261019 checkpoint. AUD-05 выполнен полностью в согласованном локальном
scope: редактор существующего правила, preview с UPDATE, атомарное сохранение
и сценарий до реальной Task; версия/проверки — AUD-05-20261019 checkpoint.
AUD-01/02/03/13/14/15/06/04 также выполнены полностью в своих локальных scope.
AUD-16 выполнен полностью в локальном scope: служебные поля ImportJob защищены,
preview/confirm используют row lock, повторную проверку прав, файла и строк.
Проверки112 SQLite +17 PG, system/migration drift; команды и границы — AUD-16 checkpoint.
AUD-20 выполнен полностью в локальном scope: доменное начальное состояние
API/import заявок и сделок, причины потери, серверные metadata, атомарная история
и фильтр активных открытых стадий UI/import/Inbox. Версия/проверки — AUD-20 checkpoint.
На историческом срезе21.10 AUD-10 был частичным; позднее30.10 его локальный
scope закрыт и опубликован8d710f03. Актуальные закрытия AUD-07/08/09/11/12/17/19
и ограниченного AUD-V01 находятся в [roadmap](../current/roadmap.md#project-audit-20261017).
Они не являются полной production-сертификацией. AUD-21: полный локальный критерий concurrent rollback/recovery
проверен в PostgreSQL17, 48 import-проверок PASS без skip; код AUD-16 сохранён.
Версия/evidence — AUD-21-20261021 checkpoint. AUD-22 также выполнен полностью
локально: ZIP/XML bounds, потоковый XLSX reader и cleanup; focused10/affected68,
bounded subprocess и system/drift PASS. Лимиты всех листов и env — operations,
версия/evidence — AUD-22-20261021 checkpoint. Публикация и CI — отдельные
состояния; deployment/live приёмка не заявлены локальным PASS.
Этот исторический перечень не заменяет актуальные строки roadmap;
локальные закрытия не являются общей сертификацией проекта.

Общая карта сверена 16.10.2026 на исходниках `dc1eedf`.
[Покрытие сверки и исправления статусов](../testing/docs-reconciliation-20261016.md).
Сверка статическая: маршруты, сервисы, UI и существующие test/evidence paths.
Новые runtime-тесты в документационной задаче не запускались. «Есть в коде»
не значит полная сертификация, deployment или допуск реальных клиентов.

Backend routes: [config/urls.py](../../config/urls.py).
Reachable UI: [router.tsx](../../frontend/src/app/router.tsx).
API слой: [frontend/src/api](../../frontend/src/api).
Это общая карта, не замена подробным паспортам и не новый backlog.
Предметные описания всех направлений — [реестр паспортов](README.md), порядок
оставшихся результатов и mapping acceptance — [единый roadmap](../current/roadmap.md).
Settings завершён: [реестр UI/API/потребителей](../testing/settings-functional-20261008.md).
Дополнение 08.10: [операционный UI-пакет](../testing/ui-operations-20261008.md)
обновляет шесть экранов и scoped work queues; это отдельная локальная проверка,
не общая сертификация или новая разработка CRM-аналитика.

| Область | Что присутствует в реализации | Источник / граница оставшейся работы |
| --- | --- | --- |
| Доступ сотрудников, ADMIN-04 | Scoped диагностика аккаунта/membership/роли/приглашений и зависимостей; отключение/восстановление, роль, отзыв/перевыпуск; обе platform-роли + MFA/обращение, личное согласие владельца для выдачи доступа, атомарный аудит и идемпотентность | [Сервис](../../apps/businesses/employee_access.py), [панель](../../frontend/src/features/platform/BusinessEmployeeAccessPanel.tsx), Account confirmations; локальные PostgreSQL/concurrency/browser/build PASS — checkpoint. Рабочая businesses0013 отдельно; глобальный unlock исключён, автоматической отправки нет, история ограничена50 последними запросами |
| Восстановление аккаунта, ADMIN-03 | Диагностика смены почты/MFA; обе platform-роли со свежим MFA и обращением, ручная проверка личности, подтверждение владельца для сотрудника, одноразовая новая почта/пароль, атомарный отзыв старых credentials; интерфейс оператора, владельца и получателя | [service](../../apps/accounts/recovery.py), [UI](../../frontend/src/features/platform/BusinessRecoveryPanel.tsx); опубликован dc1eedf, scoped PostgreSQL/concurrency/browser PASS — checkpoint; CI на момент сверки выполняется. Рабочая accounts0011, адрес поддержки/FRONTEND_URL и реальная SMTP-доставка отдельно. Это не автоматическая проверка достоверности документов и не передача Business |
| Административные реквизиты, ADMIN-01 | Отдельные GET/PATCH и вкладка карточки: allowlist, обе platform-роли, MFA, обращение/причина, revision, атомарный аудит и история | [сервис](../../apps/core/platform_details.py), [форма](../../frontend/src/features/platform/BusinessDetailsForm.tsx), [тесты](../../apps/core/tests_platform_details.py); опубликован f7d74d5, scoped PASS и CI success; не owner/recovery/billing и не deployment |
| Передача владельца, ADMIN-02 | Заявка с двумя личными подтверждениями, роль сотрудника или отключение доступа прежнему владельцу; platform_admin + MFA, атомарный аудит и отзыв сессий | [сервис](../../apps/businesses/ownership.py), [интерфейс](../../frontend/src/features/platform/BusinessOwnershipPanel.tsx), [тесты](../../apps/businesses/tests_ownership.py); опубликован cafcea5, локальная API/UI приёмка и CI PASS. Recovery без прежнего владельца и рабочая миграция не входят в эту границу |
| Platform console, PLATFORM-REBUILD-01 | Обзор/клиники/карточка: настройки, записанные ошибки и свежесть фоновых наблюдений разделены; MRR/подписки сохранены; status filter и no-data/403; прежние grant/MFA и журнал | [selectors](../../apps/core/platform_selectors.py), [UI](../../frontend/src/features/platform), [spec](../testing/platform-rebuild-spec-20261014.md); проверки в checkpoint; ручное создание клиники не реализовано; обращения — отдельная строка ниже |
| Филиалы, MB1–MB5 | Branch access, услуги/цены, несколько интервалов/переезды/отсутствие, календарь и AI booking | [Домен](../../apps/branches), [паспорт записи](scheduling.md); b48a822, scoped PASS, рабочая локальная активация 12.10 после backup; live отдельно |
| Операционная Главная | Полные distinct-счётчики, сгруппированные очереди внимания, пять ближайших записей, поступления/возвраты/чистые поступления с источником и состоянием данных | [work queues](../../apps/core/work_queues.py), [UI](../../frontend/src/features/dashboard/OperationalDashboard.tsx), [локальная проверка 18.11](../testing/task-state/PRIMARY-SESSION.md#dashboard-redesign-20261118); target/полный рабочий день отдельно |
| Обзор оператора, PLATFORM-OVERVIEW | Полные счётчики свежих сбоев/непроверенных клиник и активной поддержки с точными переходами; ограниченные очереди, компоненты/эпизоды, связанные обращения, ответственные; финансы сохранены | [read model](../../apps/core/platform_overview.py), [UI](../../frontend/src/features/platform/OverviewAttention.tsx); scoped проверки в checkpoint; подробный CRM read-path — отдельная строка ниже |
| Карточка клиники, PLATFORM-CLINIC-CRM | Пять разделов, постоянный подробный просмотр CRM/переписки/платежей, связанные записи и дочерние списки, scoped поддержка и аудит чтения | [read API](../../apps/core/platform_crm_views.py), [UI](../../frontend/src/features/platform/ClinicCrmBrowser.tsx); GET-only, без экспорта/impersonation/provider secrets; scoped проверки и публикация — checkpoint, live activation отдельно |
| Операции платформы, PLATFORM-OPERATIONS | Текущие фоновые эпизоды, подключения, история ошибок automation/integration/webhook и инфраструктура отдельно; фильтры клиники/компонента/свежести/UTC периода, полные counts, пагинация и обратный контекст | [read API](../../apps/core/platform_worklists.py), [UI](../../frontend/src/features/platform/PlatformOperationsPage.tsx); scoped проверки в checkpoint; журнал всех прошлых эпизодов и новые наблюдения не добавлены |
| Клиенты | Карточки, поиск/связи, история, archive/restore, проверка активных зависимостей | [clients](../../apps/clients), [services](../../apps/clients/services.py); общие edge cases и приёмка FC остаются |
| Заявки | Lifecycle, ответственный, конверсия/связи, lost reason | [leads](../../apps/leads/services.py), [tests](../../apps/leads/tests_crm_light.py); не обходить services |
| Сделки/воронки | Стадии, terminal actions, связи и история | [crm](../../apps/crm/services.py); новые stage-policy сценарии D-08 требуют правила |
| Календарь/специалисты | Resource без обязательного аккаунта, график/исключения, проверки slot/overlap, изменение записи | [scheduling](../../apps/scheduling/services.py), [availability](../../apps/scheduling/availability.py); кресла/оборудование отложены |
| Задачи/напоминания | Lifecycle, роли, назначение, due processing | [tasks](../../apps/tasks/services.py); target workers и follow-up policy отдельно |
| Inbox | Диалоги/сообщения/связи, ручная работа и human handoff; компактный scoped-инспектор клиента/будущих записей/CRM, точные переходы, мобильная панель и сохранение черновика | [conversations](../../apps/conversations), [проверки инспектора](../testing/task-state/PRIMARY-SESSION.md#inbox-inspector-20261008--approved-customer-context-and-action-placement); внешняя доставка не доказана наличием UI |
| Клиентский AI | Настройки/знания/память, публичные источники, контролируемое создание, safety budget, handoff/recovery | [Подробный паспорт](customer-ai-agent.md); 43 real-model сценария08.10 PASS (включая прежние28); реальный канал ещё не принят |
| CRM AI / аналитик | Существующие настройки, инструменты, подтверждённые команды и аналитические запросы; диагностика конфигурации, отключённой аналитики и recovery статуса операций | [ai_core](../../apps/ai_core), [D01 и остаток](crm-ai-agent.md), [срез готовности11.11](../testing/evidence/ai-agents-fixes-20261111.md); ограниченный помощник обязателен в пилоте, расширенная аналитика отложена; полный text/voice PASS не получен |
| Автоматизации | Conditions, 6 действий, WAIT/retry, leases/idempotency/cancel; редактор существующего состава, preview с UPDATE, атомарное сохранение | [engine](../../apps/automations/engine.py); реальная очередь/target recovery отдельно |
| Поддержка, PLATFORM-SUPPORT-20261015 | Клиника создаёт обращения; платформа назначает, отвечает, решает; явное повторное открытие, приватные заметки, read cursor, поиск/пагинация и черновики; employee — свои, owner/admin — все своей клиники | [domain/API](../../apps/support), [UI](../../frontend/src/features/support); scoped evidence в checkpoint. Миграция support0001 применена в локальной рабочей БД после backup/restore и проверки сохранности; вложений, внешних уведомлений, SLA и AI нет |
| Команда/безопасность | Business membership/roles, scoped APIs, сессии/MFA, support grant. MFA пользователей бизнеса добровольная, подтверждённый фактор обязателен при входе; platform MFA сохраняется | [accounts](../../apps/accounts), [core](../../apps/core); локальная проверка MFA-OPTIONAL-20261121 в [checkpoint](../testing/task-state/PRIMARY-SESSION.md#mfa-optional-20261121--implementation); развёртывание целевой среды отдельно |
| Связь эпизода и поддержки, PLATFORM-INCIDENT-LINK | Явное связывание существующего/нового обращения с component/episode той же клиники; неизменяемый снимок, текущая свежесть, обратные переходы, platform-only API | [domain](../../apps/support/incidents.py), [UI](../../frontend/src/features/support/SupportIncidentPage.tsx); изолированные проверки в checkpoint; support0002 применена29.10 к локальной рабочей БД по отдельному поручению после backup; [операционная запись](../current/operations.md); target-активация отдельно; полного журнала всех эпизодов и автосоздания обращений нет |
| Импорт/дубли/архив | CSV/XLSX flow, preview/validation, domain links и работа с архивом | [imports](../../apps/core/import_export.py), [clients](../../apps/clients); не общий импорт произвольных моделей |
| Ручные деньги | Поступления/возвраты, неизменяемый журнал, replay/locks/overrefund защита | [payments](../../apps/payments/services.py), [tests](../../apps/payments/tests.py); не gateway пациента и не ERP |
| Детализация и сравнение аналитики | Списки записей из KPI/статусов/источников/услуг/команды, предыдущий равный период, guarded Decimal разница финансов; прежние права и архив | [read endpoint](../../apps/analytics/workspace_records.py), [comparison](../../apps/analytics/workspace_comparison.py), [локальная проверка](../testing/evidence/analytics-detail-compare-20261111.md); текущие очереди/CSV без сравнения, не полная R01/production-приёмка |
| Финансовая аналитика | Явный manual или один external источник, period/freshness/no-data контракт | [financial_metrics](../../apps/analytics/financial_metrics.py); [external registry](../../apps/integrations/providers/registry.py) пуст, прибыль/долг не утверждены |
| Файлы/AV | Private access, quarantine/scan, leases/recovery, нормализация avatar | [core](../../apps/core), [operations](../current/operations.md); локальный AV работает, облачная приёмка/retention открыты |
| Экспорт | Sync CSV, async ExportJob, current permissions в worker, fingerprint доступа при private download (AUD-18) | [exports](../../apps/core/export_jobs.py); reports_exports/beat нужны в target |
| Состояние сервиса (S03) | Просроченная фоновая работа, начало/восстановление/устаревание инцидента; персональные уведомления owner/admin с защитой от дублей и проверка связи с API. По решению03.11 глобальная полоса и индикатор шапки удалены: временные уведомления используют общий host, постоянная причина остаётся в затронутом отчёте; [текущий UI](../current/frontend.md) | [service status](../../apps/core/service_status.py), [evidence](../testing/task-state/PRIMARY-SESSION.md#crm-s03-20261014--service-state-and-incident-notifications); isolated checks, рабочая миграция/worker/beat и независимый внешний мониторинг отдельно |
| Локальное восстановление (S04) | Реальные PostgreSQL/Redis/Celery/ClamAV в одноразовом стенде; restart/crash/retry/cancel без дублей, восстановление очереди из БД, pg_dump/restore и приватные файлы/тестовый ключ | [runner](../../scripts/verify_recovery_s04.py), [evidence](../testing/task-state/PRIMARY-SESSION.md#crm-s04-20261014--isolated-operations-and-recovery); Windows solo и локальное хранилище, целевая production-среда отдельно |
| Интеграции | Connector/provider services, credential store, webhook/pull/status/recovery foundation | [integrations](../../apps/integrations), [bots](../../apps/bots); Telegram/WhatsApp в подготовке R02, прочие подключения отложены; provider-specific live допуск не заявлен; остаток UI — [паспорт](integrations.md) |
| Billing | Код entitlements/subscription и интерфейсы существуют | [billing](../../apps/billing); коммерческий пакет/цены/процессинг не завершены, развитие отложено |
| Интерфейс | Рабочие маршруты, общие компоненты, RU/KK/EN, neutral/emerald tokens, состояния восстановления | [frontend](../../frontend/src); полная FC/manual/reader приёмка остаётся |
| Эксплуатация | Настройки/скрипты health, workers, monitoring, backup/restore foundation | [scripts](../../scripts), [settings](../../config/settings.py); нет утверждения о развёрнутом paid production |

## Что делать дальше при новом поручении

Сначала выбрать один требуемый результат и [непройденную границу](../current/acceptance.md).
Для актуального Inbox AI [локальный пилот 08.10](../testing/inbox-local-pilot-20261008.md)
прошёл, включая handoff и настройки; следующая отдельная граница — согласованный channel/target flow. Бюджет,
получатели, deployment и следующий этап здесь не утверждаются.
Для остальной CRM использовать существующие слои и проверять конкретный
regression/недостающий критерий; не реализовывать модуль заново по старому плану.

Разделение готовности, Git/CI и среды — [состояние проекта](project-state.md).
Действующие требования — [реестр документов](../README.md).
