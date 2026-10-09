# SETTINGS-REDESIGN-20261009

Владелец утвердил полный редизайн `/app/settings` по пяти референсам.
Основа — `5434296a7826933617b8a8fde940588b58079490`, canonical checkout
`C:/Users/user/Desktop/PlatformaCRM`, branch `codex/ui-testing-toolkit`.
Предшествующая [функциональная приёмка](settings-functional-20261008.md) сохраняет
свои границы; новая задача меняет представление и взаимодействия всех десяти разделов.
Применяются существующие [дизайн-система](../current/frontend.md),
[права](../current/access.md) и бизнес-правила. Данные/обязательность из изображений
не становятся новыми требованиями. Другие страницы и глобальная оболочка не перерабатываются.

## Итоговый интерфейс

| Раздел | Изменение |
| --- | --- |
| Компания | Четыре группы сохранены; профиль/контакты, рабочие настройки и справочные значения отделены; ошибки раскрывают соответствующую группу и фокусируют поле |
| Сотрудники | Список и поиск; сотрудники, приглашения и отделы во вкладках; редактирование сотрудника и приглашение в drawer; предпросмотр фактических настроек роли |
| Роли и доступ | Каталог ресурсов/действий, поиск, отдельные разрешение и scope; независимое сохранение строки и повтор после ошибки; владелец только для чтения |
| Безопасность | Реальные показатели и отдельные списки событий, входов и поддержки; локальные loading/error/retry/empty |
| Сообщения клиентам | Выбор сценария, один редактор, вставка переменных, предпросмотр без выдуманных данных клиента; независимые черновики |
| Мои уведомления | Список категорий, семантические переключатели, результат/ошибка выбранной строки |
| Быстрые ответы | Поиск и список, drawer создания/редактирования; существующий потребитель Inbox получает черновик без автоматической отправки |
| Тариф | Существующая запись подписки, предпочтение плана и отдельные реквизиты; без нового биллинга или обещания оплаты |
| Лимиты | Реальные значения/лимиты/периоды и единицы; unlimited без декоративного процента |
| Дополнительные поля | Вкладки сущностей, список, drawer редактора, отдельные варианты выбора и матрица view/edit roles |

На компьютере навигация показывает все группы, на телефоне используется общий Select.
Hash и история браузера сохраняют навигацию; черновики разных разделов независимы.
Drawer использует существующий focus trap, Escape и возврат фокуса. Панель сохранения
остаётся в доступной области; на телефоне учитывает нижнюю навигацию.
RU/KK/EN, существующие semantic tokens, типографика и controls переиспользованы.

## Существенные границы

Матрица прав использует существующие PATCH permission и POST отсутствующего override.
Каждая строка сохраняется отдельно: UI не обещает новую batch-транзакцию всей роли.
Изменение scope не меняет соседние действия. Старый visibility API остаётся в backend.
Неопределённое наследование custom role показывается отдельно от запрета; JSON metadata
пользовательской роли не изображается как действующая серверная политика. Предпросмотр
конкретного сотрудника учитывает его реальную membership base role и explicit permissions.
Права на объект, capability и owner bypass сохраняются.

В custom fields пустой список ролей по прежнему backend-контракту означает все роли
в пределах доступа к CRM-сущности. UI не превращает снятие последней выбранной роли
в скрытое расширение доступа: требуется явный выбор роли или «все». Object-based
options сохраняют metadata при переименовании поля; деактивация не удаляет значения.

Единственная серверная правка — транзакция создания RolePermission вместе с audit
и блокировкой той же BusinessRole, что используют соседние операции прав.
Регрессия до исправления: audit exception возвращал 500, но разрешение сохранялось.
После исправления 500 откатывает разрешение. Новых ролей/разрешений/схемы, миграций,
Notification, BusinessEvent или AI-политики эта задача не вводит.

Код: [SettingsPage](../../frontend/src/features/settings/SettingsPage.tsx),
[model](../../frontend/src/features/settings/useSettingsModel.tsx),
[sections](../../frontend/src/features/settings/sections),
[components](../../frontend/src/features/settings/components),
[form](../../frontend/src/components/forms/BusinessSettingsForm.tsx),
[permission API](../../apps/businesses/views.py).

## Проверки

Локальные проверки завершены. Квитанции commit/push и CI записываются
в [checkpoint](task-state/PRIMARY-SESSION.md). Артефакты — `output/settings-redesign/`.
Все команды используют действующую `.venv` и `scripts.codex_verify.isolated_runtime`:
временная SQLite/порты, без seed/reset рабочей БД и без установки зависимостей.

Изолированный `manage.py test apps.businesses.tests_settings_team
apps.businesses.tests_role_visibility apps.businesses.tests_access --noinput -v 1`:
52 PASS (`backend-1791550928615451200.log`). До исправления rollback-регрессия
воспроизведена в 7-test run, после минимальной правки immediate gate 11 PASS.
Покрыты happy path, duplicate/invalid scope, role denial, чужой Business, audit rollback,
сохранение соседних permissions и прежние access/visibility границы.

Browser: [functional](../../frontend/e2e/settings-functional.spec.ts) и
[redesign](../../frontend/e2e/settings-redesign.spec.ts), scoped desktop/mobile.
Адаптация старых locators к новым controls не удаляет API/data assertions.
Проверяются десять разделов RU/KK/EN, ошибки и retry, сохранение черновиков,
клавиатура, поля CRM, приглашения, permissions POST/PATCH и readonly owner.
Начальные прогоны выявили невидимую save bar: существующий `overflow-x: hidden`
создавал scroll container. `overflow-x: clip` применяется только при наличии
Settings workspace; остальные маршруты сохраняют прежний стиль.

Не запускались полная release/E2E-сертификация, live provider, отправка приглашений,
платные AI-вызовы, миграции рабочей БД или deployment. SQLite не доказывает
PostgreSQL contention. Общая клиническая/production-приёмка остаётся открытой.
Commit/push и фактический CI фиксируются отдельно от локальных проверок.

### Финальный локальный результат 09.10

- Полный затронутый набор: desktop 16 PASS (`browser-1791551302988376700.log`),
  mobile 16 PASS (`browser-1791551321467161700.log`). Команды:
  `.venv/Scripts/python.exe output/settings-redesign/verify_ui.py desktop-chromium "settings-(functional|redesign).spec.ts"`
  и тот же запуск с `mobile-chromium`.
- После финальных правок ширины редактора сообщений и раскрытия матрицы:
  desktop 6 PASS (`browser-1791551711277231000.log`), mobile 6 PASS
  (`browser-1791551711279226500.log`), фильтр
  `--grep "ten sections|appointment edits|role action|missing role" --max-failures=2`.
  Это повтор затронутых сценариев, не 12 новых независимых тестов.
- Tablet 1 PASS: все десять разделов RU (`browser-1791551711281234600.log`),
  `verify_ui.py tablet-chromium settings-functional.spec.ts --grep "ten sections.*ru"`.
- `verify_frontend.py`: `npm run build` (i18n + TypeScript + Vite/widgets) и
  `npm run check:bundle` PASS, `frontend-isolated-final.log`.
- `verify_system.py`: `manage.py check` и `makemigrations --check --dry-run` PASS,
  `system-isolated-final.log`; изменений схемы нет.
- Просмотрены изображения всех десяти разделов desktop/mobile, формы с ошибками,
  матрица и предпросмотр приглашения. Форма сообщений после исправления помещается
  в мобильную ширину. Browser assertions проверяют границы controls, доступность
  сохранения, Escape/возврат фокуса и независимость черновиков.

Проверки относятся к основе `5434296a` + итоговому task-owned patch. Скриншоты
полной страницы могут отображать фиксированную нижнюю навигацию посередине
изображения: это viewport overlay, а не второй блок страницы.

### Публикация

Реализация `9ea28fe6ff2d8060ea7c09ce7d1d3754fb06f798` опубликована обычным push
в `origin/main`; удалённый SHA подтверждён. Committed static gate на точной основе
`5434296a7826933617b8a8fde940588b58079490` PASS. Проверка документации: 592 локальные
ссылки, 15 anchors, ошибок нет. [CI реализации](https://github.com/999MAX20/PlatformaCRM/actions/runs/37936423372)
при первичной проверке выполнялся; состояние не приравнивается к PASS.
