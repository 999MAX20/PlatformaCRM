# UI-STATE-BEHAVIOR-20261005 — поведение состояний

Локальная проверка завершена 06.10.2026 (Asia/Qyzylorda). Канонический каталог:
`C:/Users/user/Desktop/PlatformaCRM`, ветка `codex/ui-testing-toolkit`, HEAD
`9ff366207e73472cda71ca3b9113ca4f9f305af9` плюс незакоммиченные изменения.
Работа возобновлена по явному указанию владельца после завершения основного
запуска; последующие AI-изменения сохранены. Реестр владельца не менялся.

## Результат

- `ErrorState` использует общую семью fallback и передаёт нормализованные
  метаданные ошибки. У категорий разные заголовки; запрещённый доступ использует
  общий permission-компонент. Технические сообщения сервера не показываются.
- Данные поддержки доступны для технических сбоев с реальным request ID.
  Карточка прямо сообщает, что обращение автоматически не создаётся. Код можно
  скопировать; при отказе clipboard предлагается ручное копирование.
- Уведомления одного запроса/явного события подавляют дубли; одинаковый текст
  разных действий с собственной кнопкой не считается одним событием.
  Ошибка редактирования услуги остаётся один раз внутри формы, сохраняя черновик.
- Таймер toast приостанавливается при наведении, фокусе, выполнении действия и
  ожидании серверного retry delay. Общие inline/toast retry учитывают задержку.
- Ошибка Undo разблокирует карточку и предлагает перечитать данные, если такой
  обработчик предусмотрен, без слепого повторения изменения. Завершение старой
  операции не закрывает более новое уведомление.
- Reconnect проверяет `/health/`; баннер не исчезает по фиксированному таймеру.
  При успехе обновляются активные запросы чтения. При отказе остаётся повторная
  проверка; черновики сохраняются, изменения автоматически не переотправляются.
- Уведомление о непрочитанных сообщениях имеет информационный смысл. Все новые
  подписи и инструкции обновлены в RU/KK/EN.

Каталог сокращён до 27 содержательных примеров без повторения одной карточки
под разными именами. Источник: `frontend/e2e/fixtures/feedback-catalog.tsx`.
Связанный AI-пример получает контекст `MemoryRouter`; это исправление стенда.
Галерея: `output/playwright/state-behavior-20261005/index.html`.
162 основных снимка (27 × 3 локали × 2 размера), дополнительные снимки фокуса
и раскрытых данных поддержки. Это настоящие UI-компоненты на тестовых данных,
не live-проверка внешних провайдеров.

## Проверки

Точные команды из корня, кроме Node policy suites (из `frontend`):

```text
node --test scripts/tests/action-feedback-policy.test.mjs scripts/tests/notification-dedupe.test.mjs scripts/tests/fallback-surface-policy.test.mjs scripts/tests/app-error-normalization.test.mjs scripts/tests/error-boundary-policy.test.mjs
.venv/Scripts/python.exe output/playwright/state-behavior-20261005/verify.py final-flows-diagnostic state-behavior.spec.ts service-error-feedback.spec.ts session-persistence.spec.ts --project=desktop-chromium --grep "one request|inline and toast|failed undo|earlier undo|support details|reconnect waits|service edit failure|temporary startup|startup current-user|refresh 503"
.venv/Scripts/python.exe output/playwright/state-behavior-20261005/verify.py final-mobile state-behavior.spec.ts --config=playwright.action-colors.config.ts --project=mobile-chromium
.venv/Scripts/python.exe output/playwright/state-behavior-20261005/verify.py build
.venv/Scripts/python.exe output/playwright/state-behavior-20261005/verify.py bundle
node output/playwright/state-behavior-20261005/capture.mjs
git diff --check
```

- Policy suites: **20 PASS**.
- Актуальная версия: **10 desktop + 6 mobile PASS**. Проверены dedupe, фокус
  и таймер, rate limit, ошибочная и устаревшая Undo, копирование/отказ clipboard,
  reconnect с задержкой и 503, черновик услуги/повторное успешное сохранение,
  три сценария восстановления сессии. Ранее также прошли 17 browser cases;
  они не прибавляются к итоговым 16 как уникальное покрытие.
- Каталог: **162 снимка PASS**, нет горизонтального переполнения, утечки
  технического текста, неразрешённых ключей или нарушений выбранных axe WCAG
  правил. Визуально просмотрены мобильные RU/KK support details и EN toast.
  Клавиатурное действие и раскрытие поддержки проверены для всех локалей/размеров.
- `npm run build`: **PASS**, включая i18n (5263 ключа), TypeScript, app/widget.
  `npm run check:bundle`: **PASS**. Diff hygiene: **PASS**.

Helper использует `scripts.codex_verify.isolated_runtime`, безопасное окружение,
отдельные порты и временную SQLite. Удалённая основной задачей tracked-страница
вызывала FileNotFoundError штатного inventory: только в локальном helper
инвентаризация заменена на существующие tracked + untracked runtime-файлы;
сравнение с точной safe-env policy сохранено. Общий runner не изменялся.

Зафиксированные неуспешные попытки: первоначальная сборка до паузы остановилась
на переводе из незавершённой AI-задачи; после её завершения сборка PASS.
Каталог исправлен после отсутствия router context и неверного имени router-пакета.
Первый повторный browser run не дождался сервера за 120 секунд. Следующий запуск
с `DEBUG=pw:webserver` показал подготовку isolated migrations/fixtures и прошёл
все сценарии с прежними timeout и assertions. Логи сохранены в том же output.

## Границы

Backend/domain/API contracts, разрешения, BusinessEvent, отправка уведомлений
внешним адресатам и AI-политика не менялись этой задачей. Рабочая `db.sqlite3`
не мигрировалась и не наполнялась. Ожидающая миграция AI-задачи остаётся отдельно.
Полные backend/E2E, live monitoring/provider и release certification не запускались:
для локальных frontend-изменений выбраны целевые проверки.

Публикация **заблокирована прежним dependency CI**:
[run 37312854122](https://github.com/999MAX20/PlatformaCRM/actions/runs/37312854122),
braces/DOMPurify; основания и baseline в [предыдущем отчёте](ui-feedback-20261005.md).
Зависимости не менялись, новый CI не запускался. Commit/push не выполнялись.
Результат реализован и проверен локально, но не опубликован. Автоматическое
ожидание основной задачи приостановлено, повторный запуск не требуется.
