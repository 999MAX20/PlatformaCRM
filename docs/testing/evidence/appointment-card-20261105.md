# APPOINTMENT-CARD-20261105 — модальная карточка записи

Локальная реализация и scoped-проверки завершены.17 отдельных браузерных сценариев
прошли в целевых прогонах; это не единый полный E2E/release PASS.
Каноническая папка `C:/Users/user/Desktop/PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, HEAD `66101d509cb7642b2928275e48c4b64354abf07b` плюс
сохранённый чужой WIP. Это следующий разрешённый этап после карточки клиента,
а не реализация всех сущностей. Рабочая БД и обычный dev не менялись.

## Получившееся поведение

- Запись открывается в центральном Dialog без blur из Записей, клиента и Календаря.
  В шапке клиент/интервал/статус, одна основная команда; перенос/редкие действия в меню.
  Слева реальные клиент/контакты, услуга, специалист, ответственный, филиал и источник.
- Обзор: комментарий, связанный план, три последних события. История и задачи отдельно;
  файлы, заметки, дополнительные поля и доступная переписка через вторичную навигацию.
  Вкладка других записей внутри записи отсутствует. Ограниченные заметки обозначаются.
- Подтверждение/перенос/отмена/неявка/завершение сохраняют существующие API, причины
  и expected_updated_at. Конфликт сохраняет причину; повтор возможен после обновления.
  Terminal не переоткрывается; повторная запись ведёт в существующую форму с prefill.
- Client↔Appointment переключаются в одной видимой карточке; Back и закрытие защищены
  от потери черновика. Закрытие возвращает контекст и фокус списка/инспектора.
  Календарный инспектор скрывается на время карточки, его дата/выбор сохраняются.
  Отдельные полноценные страницы и их ссылки остаются доступны.
- Запросы карточки и ресурсов разделены по Business/actor. 403/404 скрывают кэш;
  503 сохраняет черновик. Pending блокирует закрытие и переходы. Вложенные формы
  требуют явного отказа от текста; Escape не закрывает родительскую карточку.
- Сохранён контекстный голосовой вход клиента/записи из последней реализации.
  Архив/restore остаются на существующих рабочих экранах; денежные действия сюда
  не добавлены. Backend-права, доменная политика и модели не менялись.

## Проверки

Все команды из канонической папки. Runtime: `scripts.codex_verify.isolated_runtime`,
одноразовая SQLite, выделенные loopback-порты, синтетические данные, локальные
тестовые файловые операции. Нет рабочих миграций, реальных провайдеров или deploy.
Оригиналы, PLAN, собственный diff/хэши, команды, фикстуры и логи:
`output/appointment-card-20261105/`.

- `node --test frontend/scripts/tests/appointment-cache.test.mjs frontend/scripts/tests/record-filters.test.mjs frontend/scripts/tests/calendar-years.test.mjs`:13 PASS, `node.log`.
- `.venv/Scripts/python.exe output/appointment-card-20261105/records-run.py --browser`:11 PASS, `records-browser-1793889153247630200.log`.
- Тот же runner с `--grep 'modal layout|calendar opens|terminal repeat|client appointments'`:6 PASS/1FAIL, `records-browser-1793889606741620600.log`. Прошли финальные RU/KK/EN, переход клиента и desktop/mobile календарь. Повтор остановился в тестовой подготовке через отдельный импорт API без session token; заменено реальными UI-действиями завершения.
- `--browser --grep 'terminal repeat|related client failure'`:2 PASS, `records-browser-1793890097103464600.log`. Реальный повтор/prefill, возврат из403 клиента, реальные серверные403 для изменения read-only ролью и403/404 для чужой записи.
- `--browser --grep 'appointment related note|appointment attachment'`:2 PASS, `records-browser-1793890348323697000.log`: реальное сохранение заметки/дополнительного поля и загрузка файла, draft/navigation guards.
- `--build`: финальный `records-build-1793890107231770400.log` и `records-bundle-1793890107231770400.log`, exit0. Types/i18n6895/app/widget/bundle PASS. Сохранены предупреждения размеров RU/KK chunks; app-shell в бюджете400kB.

Начальные ошибки не скрыты: первый прогон4FAIL из-за выбора mobile-локатора до
загрузки desktop-таблицы; следующий3PASS/5FAIL из-за отсутствующего ожидания
окончания сохранения, тестирования отключённого refetch-on-focus и неявных
прав тестовой роли. Исправлены ожидания, используется реальный reconnect,
в фикстуре добавлены явные запреты. При расширении foreign-фикстуры один запуск
остановился до браузера на неверном поле Service.price; исправлено на price_from.
Все указанные причины сверены с кодом/логами; утверждение единого чистого полного
прогона не делается. Реальные status/version/role проверки не заменены mock PASS.

## Визуальная и техническая сверка

[Desktop RU](appointment-card-20261105-assets/ru.png),
[Mobile KK](appointment-card-20261105-assets/kk.png) — синтетическая тестовая запись.
Проверены центрирование, no-blur, отсутствие горизонтального overflow, длинное имя,
компоновка390/1440, локализованные дата/время в Business timezone, tab keyboard,
Escape и возврат фокуса. Контраст неизменённых semantic tokens измерен:
primary16.64, secondary6.83, brand-content8.98 на white; white/brand5.35
(`contrast.json`). Это scoped-проверка, не полная WCAG-сертификация приложения.

Taste/AntiSlop: существующий CRM app-screen, ENERGY1/RHYTHM1/MOTION1.
Hard gate PASS в затронутом scope: реальные API/данные, формы/ошибки/права,
keyboard/mobile и сборка проверены. Purpose PASS: sidebar — стабильные сведения,
вкладки — отдельные действия, зелёный акцент — существующая главная команда,
тень/затемнение — иерархия модального слоя. Liveliness PASS: ясный объект и следующий
шаг, существующая идентичность PlatformaCRM без декоративных блоков. Quality PASS:
типографика/токены сохранены, новые тексты взяты из RU/KK/EN словарей, нет новых
ассетов/зависимостей/маркетингового наполнения. React review: feature-компоненты,
условные запросы ресурсов, API-слой, стабильные callback setter и query identity;
без нового глобального CSS или фреймворка прав.

## Документы, остаток и публикация

Обновлены основной текст спецификации entity-cards, frontend-контракт, scheduling
паспорт, registry/index и текущий checkpoint. Существующий roadmap не имеет
отдельной строки этого UI-этапа; последовательность карточек ведётся в entity-cards.
CRM/access/AI/product/README не требуют изменений: модель/права/настройки/домен/
setup не менялись. Исторические клиентские/Records отчёты не переписывались.

Задача и план посещений как новые модальные карточки не начинались; это следующие
отдельные этапы. Полный backend/E2E/release gate не запускался: frontend-only scope,
серверные контракты неизменны; проверены затронутые реальные HTTP/UI сценарии.

Публикация блокирована существующим `.git/index.lock` (пустой,04.11 19:04) и17
чужими исходящими коммитами. Index пуст; ветка/история/lock сохранены. Remote main
readback `0b3348e1ab31121a106badbde830b496ec477aac`. Нет собственного коммита/push,
нового CI или deployment. Старые CI не объявлены зелёными. Изменения других задач
не включались в публикацию. При отсутствии собственного committed range его
проверка неприменима; working/index/new-file/link проверка обязательна отдельно.

Итог: в принятом этапе нет остатка кода или локальных проверок. Остаток среды —
публикация из-за существующих lock/чужого outgoing; deployment не входил в поручение.
Scoped working/index diff, links/registry/new-file и собственный secret/delta review PASS.
Тестовые серверы остановлены runner; обычный dev сохранён.

## Уточнение владельца: убрать нижнюю панель05.11

В ClientCardModal и AppointmentCardModal удалён только footer prop: нижняя кнопка
«Закрыть», разделитель и занимаемая панелью высота отсутствуют. Flex body получает
освободившееся место; viewport cap, верхний крестик, Escape, draft/pending и общий
Dialog сохранены. Новых текстов, зависимостей, API/прав/данных нет.
План/исходники/собственный двухстрочный patch/хэши и журналы:
`output/entity-card-footer-20261105/`, canonical codex/ui-testing-toolkit/66101d50.
Build/types/i18n/app/widget/bundle PASS (`records-build-1793893647144403300.log`,
`records-bundle-1793893647144403300.log`). Повторная сборка после изменения только
тестового ожидания не требуется. Backend/full E2E не запускались: visual-only.
Начальный браузерный прогон4FAIL: прежнее ожидание завершения сохранения по
доступности удалённой нижней кнопки стало выбирать всегда доступный крестик.
В локальной копии harness ожидание заменено на enabled notes/disabled Save;
проверяемые требования не ослаблены. Исходные ошибки сохранены.
Спецификация entity-cards и frontend синхронизированы; roadmap/CRM/access/AI/
паспорт/README не требуют нового этапа или изменения доменного/setup контракта.
Публикация по-прежнему блокирована существующим index.lock/17 чужими outgoing;
своего commit/push/нового CI/deployment нет. Рабочая БД и общий dev сохранены.

Повторный `.venv/Scripts/python.exe output/entity-card-footer-20261105/records-run.py
--browser --grep 'modal layout|draft close'`:4 PASS
(`records-browser-1793893815243717200.log`), RU1440/KK390/EN390, переход
клиент↔запись, keyboard/Escape/focus, draft/recovery/pending. Scoped React review:
удалены только footer props; hooks/API/imports/shared Dialog неизменны.
Taste/AntiSlop: сохранены токены/типографика, убран избыточный блок; desktop/mobile
просмотрены, доступное закрытие сохранено, ассеты/копирайт/новая стилистика не добавлялись.
[Запись desktop](appointment-card-20261105-assets/footer-removed-ru.png),
[запись mobile](appointment-card-20261105-assets/footer-removed-kk.png),
[клиент desktop](appointment-card-20261105-assets/client-footer-removed-ru.png).
В принятом уточнении остатка кода/локальных проверок нет; публикационный блок
сохранён. Scoped whitespace/links/owned patch review PASS; тестовые процессы завершены.

## Перестановка по новому референсу05.11

Владелец после сравнительного анализа разрешил реализацию новой компоновки записи.
Отдельная полноширинная шапка убрана: имя клиента (переход в карточку), дата,
интервал и обычное поле статуса перенесены в левую колонку. Основное действие,
меню и повтор записи перенесены в закреплённую верхнюю строку. На mobile действия
занимают второй ряд, служебные иконки/крестик первый. Вкладки справа начинаются
сразу под строкой окна. Контакты/источник/план/обратный переход и guards сохранены.
Активность выводит текст перед временем, события отмечены точками на линии;
имя автора не выдумывается — текущий ActivityEvent содержит ID, не display name.
Нет демонстрационных событий, новых API/прав/статусов/BusinessEvent/AI эффектов.
Клиентская компоновка не менялась; нижняя панель не возвращалась.

План, originals, owned.patch, SHA256, точные runner/logs:
`output/appointment-layout-20261105/`; canonical codex/ui-testing-toolkit/66101d50
с сохранённым общим WIP. Test source/runtime в canonical, disposable DB/порты.
`.venv/Scripts/python.exe output/appointment-layout-20261105/records-run.py
--browser --grep 'modal layout|draft close|real confirm|reschedule pending|nested reason|terminal repeat'`:
8 PASS (`records-browser-1793894388562915900.log`). RU1440/KK390/EN390,
переключение вкладок/клиент/back, Escape/focus, сохранение/черновик/error recovery,
pending, реальные подтверждение/завершение с причиной/перенос/отмена/повтор.
Первый build остановлен check:i18n на ошибочном ключе contacts; исправлен на
существующий clients.contacts, следующий build/types/i18n6895/bundle PASS.
Скриншот выявил KK месяц M12; применён существующий подход числового месяца.
После него и перехода status badge→text финальный locale/build срез PASS.
Backend/full release gate не требуются: серверные контракты и домен неизменны.

Spec/frontend обновлены; roadmap не имеет отдельного UI этапа, клиент/прочие
карточки не переоткрыты. CRM/access/AI/operations/README без изменений, поскольку
права/данные/схема/setup прежние. Публикация блокирована прежними index.lock/17
чужими outgoing. Lock/history/working DB/dev сохранены; commit/push/CI/deploy нет.

Финальные команды: тот же runner `--browser --grep 'modal layout'`:3 PASS
(`records-browser-1793894575775489700.log`); `--build`:exit0
(`records-build-1793894586254692100.log`, `records-bundle-1793894586254692100.log`).
Три locale-case входят в исходные8, количества не суммируются как уникальные.
[Финальный desktop](appointment-card-20261105-assets/rearranged-ru.png),
[mobile KK](appointment-card-20261105-assets/rearranged-kk.png) просмотрены:
двухколоночная композиция/два ряда mobile, без overflow/blur/footer, KK numeric
month, реальная activity вместо демонстрационного текста. Существующая ширина1080,
колонка240, tokens/fonts/contrast сохранены. Taste/AntiSlop: scoped hard/purpose/
quality PASS; объекты/действия реальные, никаких декоративных или маркетинговых
блоков. React review: один экземпляр action component, прежние hooks/guards/API,
нет изменения shared Overlay. Финальный owned diff/links/whitespace PASS.
Index пуст, lock сохранён, remote main0b3348e1 и17foreign outgoing подтверждены.
Все свои runner завершены. В принятом scope кода/локальных проверок остатка нет;
публикационный блок сохранён, deployment не выполнялся.
