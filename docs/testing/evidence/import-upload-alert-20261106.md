# IMPORT-UPLOAD-ALERT-20261106

## Запрос и причина

Владелец сообщил об ошибке загрузки Excel20 клиентов и потребовал компактный alert
справа снизу без сдвига страницы; выяснить назначение support details/reload.
Источник: текущий пользовательский запрос06.11. Новая работа ограничена upload
мастера, его ошибками и восстановлением существующего локального ClamAV.

Файл `Клиенты_тест_переноса.xlsx` корректен. Реальный scanner_health первоначально
возвращал scanner_unavailable на127.0.0.1:3310. Существующий engine/runtime найден
в output/local-file-antivirus; новых зависимостей/сервисов не установлено.
Сигнатуры обновлены через существующий freshclam, clamd и updater запущены скрыто.
Scanner health ClamAV1.5.4/28174 PASS. Предупреждение NotifyClamd первого обновления
относилось к ещё не запущенному daemon; после запуска health и сканирование PASS.
Проверки безопасности не отключались. Worker/beat и production не затронуты.

## Изменения

- Backend возвращает стабильный503 file_scan_unavailable до чтения/записи источника;
  permission/tenant/upload limits/scan fail-closed сохранены.
- ImportErrorNotice использует общие NotificationHost/StatusNotice:fixed справа снизу,
  ширина до380px, компактные отступы, явное закрытие. Ошибки самого мастера,
  profiles/mapping/rows/references/activation перенесены из потока страницы.
  Строчные ошибки preview остаются данными таблицы, а не отдельными алертами.
- RecoveryDetails имеет opt-in compact: кнопка «Копировать код ошибки» вместо
  большого disclosure. Это реальный request_id, связанный с серверными журналами;
  кнопка не отправляет обращение. Без полезного request_id её нет. Обычный shared
  режим остальных страниц сохранён; copied state сбрасывается при смене request_id.
- «Загрузить актуальную версию» переименовано в «Обновить данные»: только GET
  черновика/истории, не повтор POST. Предлагается для чтения/конфликта/неясного
  результата, но не при scanner outage/permission/validation. При отсутствии draft
  нет ошибочного refetch null. RU/KK/EN синхронизированы.

## Версия, проверки и граница

Canonical root C:/Users/user/Desktop/PlatformaCRM; branch codex/ui-testing-toolkit,
HEAD66101d509cb7642b2928275e48c4b64354abf07b плюс shared dirty tree.
Baseline/PLAN, scripts/spec/logs под output/import-upload-alert-20261106.

- `.../.venv/Scripts/python.exe output/import-upload-alert-20261106/check_backend.py backend apps.core.tests_import_workspace_api apps.core.tests_import_workspace_sources`:25PASS;
  system check/makemigrations --check --dry-run PASS, отдельная disposable DB.
  Новый regression: specific503, неизменная version, нет source/Client при scan outage.
- Local upload API с реальным scanner:HTTP200,20 строк; операция на черновике2
  проверена внутри откатанной транзакции, version/source count пользователя сохранены.
  Это локальный handler/API smoke; полный перенос бизнес-сущностей не запускался.
- Node10PASS: import-workspace-errors + app-error-normalization.
- `run.py --build`: i18n/TypeScript/Vite app/widget PASS.
- `npm run check:bundle` из frontend PASS; прежние большие RU/KK locale warnings,
  app shell ниже400kB. После source правок других изменений в проверенных путях нет.
- Browser runner использует disposable DB/отдельные порты, но настоящий local3310
  scanner, без fake clean. Fault cases инжектируют503/409/403 в браузере.
  Первый запуск: history refresh1PASS;4 случая остановились на неоднозначном locator
  button+file input. Исправлен только тестовый selector, приложение не менялось.

Повторный запуск выявил ошибку кодировки пути в самом тестовом скрипте: Python
default cp1251 исказил имя Excel. Оригинал не менялся; fixture-копия с ASCII-путём
проверена по совпадающему SHA256. Третий запуск четырёх affected cases PASS.
Итого5 различных import browser сценариев PASS по scoped runs: RU/KK/EN upload
503→dismiss→real antivirus upload200/20rows, отсутствие layout shift, width≤380px,
height<225px, clipboard/keyboard; history read retry, version conflict и role denial.
Дополнительно старый shared RecoveryDetails browser-case1PASS (обычный режим,
копирование и clipboard failure, отсутствие технических данных при role denial).
Команда: из frontend `node node_modules/@playwright/test/cli.js test
--config=playwright.alerts.config.ts --grep "support details are meaningful"
--output=../output/import-upload-alert-20261106/shared-support-results`
с ALERT_TEST_PORT=56937. Собственные тестовые серверы завершены.

[Desktop](import-upload-alert-20261106-assets/notice-ru.png),
[mobile KK](import-upload-alert-20261106-assets/notice-kk.png),
[успешная загрузка](import-upload-alert-20261106-assets/uploaded-ru.png).
Скриншоты desktop/mobile осмотрены: форма не смещается, уведомление не выходит
за viewport и не перекрывает мобильное меню; выбранные исходные токены сохранены.

В принятом scope нет остатка кода/локальных проверок. Исправление файла не требовалось.
Current frontend/import/operations contracts, integrations/settings/files passports,
registry и checkpoint согласованы. Product/access/AI/README не меняют правил;
roadmap-фаза не открывалась, общего закрытия production/import acceptance нет.
Scoped diff hygiene/registry/новые ссылки/файлы проверены. Existing application gates
не повторялись после docs-only edits; код и входы проверок остались прежними.

## Публикация и процессы

Существующий index.lock от04.11 и17 чужих outgoing commits сохранены: собственные
commit/push/CI/deployment не выполнены. Не требуется новая миграция или env change.
Сервисы scanner/updater остаются запущенными для локального upload; PID/logs в output.
Автозапуск Windows, production broker/scanner и прочие acceptance не подтверждены.


## Новый перенос — выбор файла 06.11.2026

IMPORT-NEW-PICKER-20261106. Владелец сообщил, что «Новый перенос» создаёт пустой
черновик, но не открывает проводник. Исправлено: file input доступен до создания
черновика; кнопка синхронно открывает chooser, после выбора create→upload→mapping.
Отмена выбора ничего не создаёт. Отдельный upload добавляет в текущий draft;
ошибка сохраняет черновик/частично загруженные источники для повторной попытки.
Input сбрасывается после выбора, поэтому повтор того же файла вызывает change.
Синхронный request lock предотвращает повтор операции до обновления React state.
Существующие dirty/pending guards, права, API и подтверждение импорта сохранены.
Существующий дизайн/тексты RU/KK/EN не менялись, новых видимых блоков нет.

Проверено в канонической папке, branch `codex/ui-testing-toolkit`, HEAD `66101d50`
+ task-owned dirty delta; стартовые копии и Git snapshot в
`output/import-new-picker-20261106`. Рабочая БД не менялась.

- `.venv/Scripts/python.exe output/import-new-picker-20261106/run.py --browser`:
  **4 PASS**. Реальное browser filechooser event с клавиатуры, отмена без POST,
  XLSX20rows с действующим локальным scanner; RU1440/KK390/EN768, append без нового
  draft, disabled при dirty,503→повтор того же файла в том же черновике.
- `.venv/Scripts/python.exe scripts/verify_import_workspace.py --grep 'source errors'`:
  **1 PASS**. Исправление строки, несохранённая навигация, preview503→recovery.
  Старые тесты настройки mapping теперь создают пустой draft как API fixture;
  добавление файла проходит через реальную кнопку upload. Новый старт покрыт отдельно.
- `.venv/Scripts/python.exe output/import-new-picker-20261106/run.py --build`:
  **PASS** i18n6902/types/app+widget build; `node scripts/check-bundle.mjs` PASS
  (существующие предупреждения размера RU/KK chunks, app shell в бюджете).
- Из frontend `node --test scripts/tests/import-workspace-errors.test.mjs`: **3 PASS**.
- JS syntax, scoped diff hygiene и новые ссылки PASS. Screenshot desktop/mobile
  осмотрены; экран использует прежние компоненты, горизонтального overflow нет.

Новый regression сохранён в `frontend/e2e/import-file-picker.spec.cjs`; стабильная
synthetic XLSX fixture побайтно совпадает с проверенным файлом. Стандартный runner
теперь включает spec; команда повторного запуска:
`.venv/Scripts/python.exe scripts/verify_import_workspace.py --grep 'new chooser|failed new upload'`.
Новый test selector/config проверен синтаксически; исходный запуск4PASS использовал
тот же spec и отдельный isolated runner. Перенос идентичной fixture не меняет inputs.
Собственные тестовые серверы завершены; ранее восстановленный scanner сохранён.
Backend/миграции/fullE2E не запускались: менялся только frontend workflow.
Contract, integrations passport, testing guide и evidence согласованы. README,
access/AI/product не требуют изменения; отдельная roadmap-фаза не открывалась.
В принятом scope нет остатка кода/локальных проверок. Commit/push/новый CI не
выполнены: существующий `.git/index.lock` и17 foreign outgoing сохранены. Deploy нет.


## Полный перенос исходного Excel — 06.11.2026

IMPORT-FULL-EXCEL-20261106. Поручение владельца: проверить весь сценарий от выбора
созданного Excel до появления клиентов в CRM, исправить обнаруженные препятствия.
Файл на рабочем столе побайтно совпал с fixture `import-clients.xlsx`, SHA256:
`9e279a80b87bd69f068309b3d00c637cd598fd1372cd082996c37be2116e9b68`.
Ожидаемые20 записей независимо прочитаны штатным XLSX reader из исходного файла;
регрессия сравнивает их с report и сохранёнными Client API данными.

Финальный полный сценарий **PASS**:
1. Реальный filechooser → ClamAV → XLSX parser → источник20 строк.
2. Предложенные поля → сохранение → reload → данные → предпросмотр20 created.
   ФИО, телефон, email и комментарий совпали для всех20. До confirm клиентов нет.
3. Отмена confirm-диалога ничего не записала. Явный confirm создал ровно20 клиентов.
4. Проверены все20 сохранённых Client API записей и все20 строк списка CRM;
   ссылка из результата открыла страницу клиента с контактами/комментарием.
5. Повтор confirm не добавил клиентов. Повторная загрузка исходного файла в новый
   перенос дала20 unchanged/0 created; второй confirm сохранил итоговое число20.
6. Browser pageerror отсутствует. Снимки preview, Clients и страницы клиента осмотрены.

Команда из canonical root:
`.venv/Scripts/python.exe output/import-full-excel-20261106/run.py --grep 'complete original Excel'`.
Финальный log `browser-1793943310585665300.log`:1PASS55s; worker log того же среза
подтверждает4 реальные полученные/завершённые `imports.process_workspace` задачи
(два preview и два confirm), eager=False, отдельные процессы Redis и Celery solo,
отдельная SQLite/порты. Реальный локальный ClamAV1.5.4/28174, внешняя сеть теста
запрещена. `full-result.json` содержит IDs/количества; временные backend/frontend/
Redis и worker завершены, порты закрыты. Рабочая БД не использовалась для импорта;
после проверки в ней0 записей с20 synthetic email из файла.

Сохраняется regression `frontend/e2e/import-file-picker.spec.cjs` и независимая
fixture `frontend/e2e/fixtures/import-clients.expected.json`. Обычный проектный runner
поддерживает `scripts/verify_import_workspace.py --grep 'complete original Excel'`
с его прежним eager/fake-scanner профилем; финальный PASS выше использовал настоящую
очередь и scanner. Это различие не скрывается.

Найденные препятствия и исправления среды:
- Scanner/updater после прежнего запуска уже не работали. Они восстановлены из
  существующего local-file-antivirus, без установки/обхода AV. Первый прогон получил
  upload503, пока scanner ещё загружал базы; ошибка сохранена в первом browser-log.
- Redis localhost6379 и worker отсутствовали. Запущен существующий Redis7.4.9
  (только127.0.0.1/::1, appendonly в `output/local-import-runtime`), пустая очередь
  проверена до запуска worker. Windows IPv6 localhost timeout устранён loopback bind.
  Worker canonical checkout слушает только `reports_exports`; beat/AIworker не запущены.
- Второй прогон доказал создание/поля/replay, но тест ошибочно ждал drawer вместо
  штатной страницы клиента. Исправлен locator. Его попытка real-worker также выявила,
  что safe browser runtime сбрасывал env в eager/memory. Harness исправлен: после
  обязательной safe initialization задаётся только isolated Redis и eager=False;
  итоговый runner требует worker-ready и фактический task success, без fallback.

Проверка локальной среды `local-health.json`: scanner health PASS, Redis PING,
worker PONG; все isolated ports закрыты. Scanner/updater/Redis/import worker намеренно
оставлены для пользовательского переноса. Windows автозапуск не настраивался;
после перезапуска компьютера эти локальные процессы требуется запустить снова.
Рабочие migrations/данные, .env, provider secrets и product code не менялись.
Новые app build/backend suites не требовались: добавлены тест/evidence и восстановлены
службы; ошибки бизнес-логики в данном сценарии не воспроизведены. JS syntax,
scoped whitespace, fixtures, ссылки и документационная согласованность PASS.

Срез: canonical root `C:/Users/user/Desktop/PlatformaCRM`, branch
`codex/ui-testing-toolkit`, HEAD66101d50 + сохранённый dirty snapshot/owned patch.
No scoped code/evidence remainder. Это полная проверка данного XLSX локально,
не production/full-project certification. Commit/push/newCI заблокированы прежними
`.git/index.lock` и17 foreign outgoing; чужая работа сохранена, deployment не выполнялся.

[Предпросмотр](import-upload-alert-20261106-assets/full-preview.png),
[20 клиентов](import-upload-alert-20261106-assets/full-clients.png),
[страница клиента](import-upload-alert-20261106-assets/full-client-card.png).
