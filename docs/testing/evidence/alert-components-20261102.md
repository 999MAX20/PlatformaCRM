# ALERT-COMPONENTS-20261102 — оформление alert-компонентов

Локальная реализация и scoped-проверка завершены 03.11.2026 по поручению владельца
02.11, ТЗ Market `output/CRM_ALERT_COMPONENTS_SPEC_2026-11-02.md` и согласованным
референсам. Это изменение общих поверхностей и размещения сообщений; отдельный
UI/UX-аудит и его находки не реализовывались этим поручением.

Канонический checkout: `C:\Users\user\Desktop\PlatformaCRM`, ветка
`codex/ui-testing-toolkit`, HEAD `e02a28f550e94a543c3d88acac7c1b19ee48f90b` плюс
сохранённый чужой WIP. [Manifest](alert-components-20261102-manifest.json) фиксирует
22 собственных source/test/config пути, исходные и итоговые SHA256, зависимости,
computed styles, screenshots и хэши локальных логов. Starting snapshot, собственный
patch и подробные логи: `output/alert-components-20261102/`.

## Получившееся поведение

- `StatusNotice` использует отдельные notification-токены: success `#007A59`,
  danger `#A33B35`, warning `#F4C542`, info `#245E8A`; белый foreground, кроме
  warning `#17201E`. Padding16px, radius12px, icon20px, заголовок/описание14/21px,
  gap4px, отдельный крестик32px и действия под сообщением. Глобальные brand/status
  токены и мягкие иконные поверхности вне `StatusNotice` сохранены.
- `NotificationOptions.title/description` совместимы с `message/appError`;
  одинаковые строки не дублируются. Explicit key/request ID сохраняют приоритет,
  текстовая дедупликация учитывает новые поля и тон; actionable-операции не
  объединяются только по тексту. Четыре последних обычных toast остаются лимитом.
- Один host справа снизу: сеть, undo, обычные toast от новых к старым снизу вверх.
  Отдельное существующее сообщение Inbox также перенесено из верхнего угла в этот
  host, выше обычных сообщений; оно не меняет их лимит, источник или условия показа.
  Его6500ms сохранены, добавлена пауза hover/focus. Bell/realtime/sound/recipients
  не перерабатывались; исходный чужой sound-permission diff сохранён.
- Карточка до380px, боковые отступы24px, при≤760px —16px; safe-area и фактическая
  высота MobileNav учитываются также на768px. Зазор над меню равен базовому отступу.
  Переполнение host прокручивается; отсутствующие группы не оставляют промежутков.
- Стабильный DOM-контейнер переносится внутрь верхнего открытого modal/drawer.
  Это сохраняет mounted actions/timers и включает управление в существующий focus
  trap. Появление не перехватывает фокус; закрытие возвращает его доступному opener
  или элементу текущего диалога. Выход200ms добавляется после полного срока чтения;
  уходящие карточки inert. Reduced motion отключает анимацию, forced colors сохраняет
  системные границы/цвета. `aria-atomic`, status/polite и alert/assertive сохранены.
- Обычный toast5000ms, undo10000ms, ошибка undo20000ms. Hover/focus/action/recovery
  delay приостанавливают таймер; затем начинается полный интервал. Ошибка retry
  оставляет действие доступным. Ошибка undo предлагает recovery, не повтор мутации.
- Верхняя sticky-полоса соединения заменена карточкой. Закрытие скрывает текущий
  стабильный эпизод, включая фоновый checking→тот же unavailable; новое состояние
  возвращает карточку. После подтверждённого online обновляются только активные
  read-запросы. `ServiceStatusNotice` и ошибки форм остаются inline.
- Согласованы контраст вложенных recovery/details, field links, permission guidance
  и кнопок. Новые пользовательские строки не добавлялись; существующий RU/KK/EN
  словарь и технические API/DB идентификаторы сохранены.

## Проверки

Команды из корня, кроме явно указанного `frontend/`. Установленные зависимости
переиспользованы; установки пакетов не было.

| Проверка | Команда / результат |
| --- | --- |
| Node policies | `node --test frontend/scripts/tests/notification-dedupe.test.mjs frontend/scripts/tests/action-feedback-policy.test.mjs frontend/scripts/tests/fallback-surface-policy.test.mjs frontend/scripts/tests/app-error-normalization.test.mjs frontend/scripts/tests/notification-header-model.test.mjs` —24 PASS |
| Компоненты и прежние recovery-сценарии | В `frontend/`: `npx playwright test --config=playwright.alerts.config.ts` —29 PASS, `browser-final.log` |
| Сборка | В `frontend/`: `npm run build` —PASS, i18n6650, `tsc -b`, Vite app/widget; остаётся обычное предупреждение о chunk>500kB, не ошибка сборки |
| Изолированный стенд | `.venv/Scripts/python.exe output/alert-components-20261102/runtime.py` —migrate/seed PASS в новом `alerts.sqlite3`, backend58234/frontend58235 |
| Достижимая форма CRM | В `frontend/`, `ALERT_APP_URL=http://127.0.0.1:58235`, `ALERT_APP_ISOLATED=1`: `npx playwright test --config=playwright.alert-app.config.ts` —3 PASS RU/KK/EN, `app-run2.log` |
| Docs/Git | Working/index diff hygiene, JSON, локальные ссылки и review новых файлов —PASS; committed-range check неприменим: собственного коммита нет |

Компонентная матрица: RU/KK/EN ×1440/768/390/320, все четыре тона, длинный текст,
четыре toast+undo+offline, scroll/порядок/геометрия/контраст, лимит очереди,
дедупликация, полные интервалы/exit, hover/focus/recovery delay, pending/rejected
actions, undo/recovery и поздний ответ старой операции, modal/drawer/nested,
недоступный opener, повторные сетевые проверки, подтверждённый reconnect/refetch,
Inbox notice/navigation, reduced motion/forced colors. Базовые пары цветов имеют
контраст5.346/6.493/10.233/6.901:1 соответственно; computed styles совпали с ТЗ.

Реальная страница `/app/services`: вход в синтетический Business, открытие услуги,
редактирование, управляемый503 PATCH, inline-ошибка без дублирующего toast,
сохранённое поле, успешный повтор в изолированный backend, success-toast внутри
диалога, Tab/Enter/возврат фокуса и восстановление исходного поля. RU1440px,
KK/EN390px. Проверка не означает всех форм/страниц или реального провайдера.
Существующий `ServiceStatusNotice` присутствует на этой странице в контенте.

Стенд использует `safe_environment`, отключённое чтение рабочего `.env`, mock AI,
изолированные cookies/SQLite/media и запрет исходящих backend-соединений вне
loopback. Source roots и команды процессов проверены. Работающая БД, staging,
production, внешние каналы и разрешения пользователей не изменялись.

### Обнаруженные сбои и исправление проверки

- Первый Node-run выявил устаревшую source-assertion: искала прежний текст ошибки
  импорта в `ImportPanel`, хотя HEAD уже использует `ImportJobReview → ImportErrors`.
  Эти три исходных файла и исходный тест совпадали с HEAD; это доказанный baseline.
  Исправлена только проверка актуального вызова и локализованного field/message
  rendering, без изменения продукта/импорта и без удаления проверки raw output.
- Первые browser-runs: clock продолжал идти между действиями; затем exit-проверке
  не хватало1ms после фактического React commit. Часы остановлены явно и проверены
  обе стороны полного200ms. Forced-colors проверяется после клавиатурного ввода,
  а не pointer→программного focus. Старый тест ждёт новый200ms exit перед следующим
  toast. Чат-тест прокручивает1ms scheduler уведомлений query cache после обновления.
- Первый RU app-run выбирал скрытую мобильную копию строки таблицы на desktop;
  исправлен selector видимой строки. KK/EN уже проходили; итоговый run всех3 PASS.
  Исходные FAIL-логи сохранены. Незакрытых сбоев в принятой проверке нет.

## Визуальные свидетельства

Все данные синтетические. Stack — проверка на fixture, а не снимок рабочего Business.

- [Desktop, максимальный стек](alert-components-20261102-assets/stack-ru-1440.png)
- [Mobile, стек над навигацией](alert-components-20261102-assets/stack-ru-390.png)
- [Реальная форма CRM: ошибка](alert-components-20261102-assets/app-error-ru.png)
- [Реальная форма CRM: success-toast на mobile](alert-components-20261102-assets/app-success-en.png)
- [Forced colors](alert-components-20261102-assets/forced-colors.png)

## Документация, границы и публикация

Обновлены frontend-контракт, паспорт настроек/уведомлений, STATUS, selected
checkpoint и registry. Roadmap не меняется: это отдельное визуальное поручение,
не закрытие R01/D01/S03/live. CRM/access/AI/integrations/operations/README и
capabilities не требуют изменений: доменные правила, API, настройка и состав
возможностей не изменены. Изменение отображения отражено в профильном паспорте.

Не запускались backend-автотесты, полный E2E/release gate, Storybook/Chromatic и
live-provider проверки: соответствующие контракты не менялись, а выбранная матрица
требует affected frontend flow. Изолированные migrate/seed — подготовка стенда,
не рабочая миграция и не самостоятельная backend-сертификация. Screen reader,
нативная экранная клавиатура и production-performance не сертифицированы.

Код и локальные доказательства в согласованном scope завершены. Публикация
заблокирована существующим нулевым `.git/index.lock` от02.11 17:52:21; index пуст.
Lock не удалялся, чужой WIP не staging'овался. `git fetch origin main`, FETCH_HEAD
и `git ls-remote origin refs/heads/main` подтверждают фактический remote SHA=HEAD
`e02a28f5`; `origin/main` локально устарел из-за ограниченного fetch refspec,
поэтому не используется для вывода о чужом исходящем коммите.
Собственных commit/push/CI/deploy нет. Следующий шаг публикации — устранить причину
lock, повторно проверить состав собственного patch и действующий remote target.
