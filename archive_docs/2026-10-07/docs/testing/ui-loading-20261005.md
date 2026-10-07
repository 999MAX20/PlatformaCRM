# UI-LOADING-20261005 — единое состояние загрузки

Авторизовано владельцем 05.10.2026: вращающееся кольцо по центру при запуске,
перезагрузке, подготовке рабочего пространства, загрузке модулей и данных.
Корень `C:/Users/user/Desktop/PlatformaCRM`, ветка `codex/ui-testing-toolkit`,
исходный HEAD `9ff366207e73472cda71ca3b9113ca4f9f305af9`.
Четыре локальные квитанции предыдущей UI-задачи сохранены.

## Изменение

Общий `LoadingIndicator` показывает кольцо 32px и существующий перевод
`common.loadingData`. `LoadingState`, прежний `PageSkeleton`, загрузка словаря,
route/auth fallback и страницы используют один вид. Появление задержано на
200ms, чтобы короткие загрузки не мигали; reduced motion отключает анимации.
Страничный индикатор занимает доступную область контента, учитывая существующие
отступы хедера и мобильной навигации. Внутри панелей индикатор остаётся локальным.
После уточнения владельца подписи загрузки панелей также унифицированы.

Условия запросов/доступа, фонового обновления и обработки ошибок не изменены.
Кнопки выполнения действий и статусы доставки не превращаются в экран загрузки.
Backend, разрешения, уведомления/BusinessEvent, AI-решения и миграции не менялись.

## Проверки

Все команды из канонического корня, кроме явно указанного frontend.
Вспомогательные команды используют `scripts.codex_verify.isolated_runtime`
и `validate_vite_environment_policy`, отдельные порты и одноразовую БД.
Зависимости повторно не устанавливались. Рабочая БД не использовалась.

| Команда | Результат |
| --- | --- |
| `.venv/Scripts/python.exe output/playwright/loading-20261005/verify.py browser session-persistence.spec.ts --project=desktop-chromium --grep "temporary startup\|startup current-user\|refresh 503"` | PASS, 3 сценария восстановления сессии |
| В `frontend`: `node --test scripts/tests/error-boundary-policy.test.mjs scripts/tests/fallback-surface-policy.test.mjs` | PASS, 9 проверок |
| `.venv/Scripts/python.exe output/playwright/loading-20261005/verify.py build` | PASS: i18n, TypeScript, app/widget build |
| `.venv/Scripts/python.exe output/playwright/loading-20261005/verify.py bundle` | PASS: bundle и app-shell budgets |
| `.venv/Scripts/python.exe output/playwright/loading-20261005/capture.py` | PASS: 12 состояний/проверок, 11 снимков |
| `git -c core.safecrlf=false diff --check` | PASS; index пуст, HEAD не изменился |

Браузерные снимки и замеры: `output/playwright/loading-20261005/`.
Стенд снимков сначала запускал Vite из неверной рабочей папки, из-за чего
Tailwind не находил content config. После исправления проверена реальная
разметка. Затем исправлена гонка снятия задержки тестового route handler;
это изменения стенда, не production-кода. Замер появления изменён с фиксированных
350ms на ожидание конечной opacity: смена module/data fallback могла попасть
в середину новой анимации. Финальная матрица PASS:

- RU/KK/EN, 1280×900 и 390×844: задержанный ответ clients, центрирование,
  отсутствие горизонтального переполнения, хедер доступен, контент восстановлен.
- RU desktop/mobile: задержанный модуль Tasks и стартовый `/api/auth/me/` при
  перезагрузке; затем успешное восстановление страницы.
- Локальный блок при reduced motion: анимация отключена.
- Короткая загрузка: opacity=0 на старте/100ms и opacity=1 после задержки.

Геометрия и подписи сохранены в `results.json`. Визуально просмотрены снимки
RU desktop/mobile, KK desktop, EN mobile, startup и reduced-motion block.
[Десктоп](../../output/playwright/loading-20261005/ru-desktop-data.png),
[мобильный экран](../../output/playwright/loading-20261005/ru-mobile-data.png).
Все собственные процессы проверки завершены; существующие рабочие серверы
не останавливались. Production-код после успешной сборки не менялся.

Полный E2E и backend suites не запускались: доменное поведение не менялось.
Системные и migration-drift проверки не нужны для этого визуального изменения.

## Уточнение владельца — текстовая плашка dashboard

После первого результата владелец воспроизвёл `dashboard.loadingCoreData`
между загрузкой route и данными. OwnerDashboard/ManagerDashboard возвращали
собственный Surface, обходя общий LoadingState. Эти ветки заменены на page-ring.
Поиск выполнен по feature-компонентам, query-loading условиям и переводам.
Аналогичные текстовые placeholders заменены в AI-помощнике, истории/командах AI,
аккаунте/сессиях/MFA, истории задач, настройках подписки и сообщений записи,
проверке каналов Inbox. Существующие LoadingState используют общий loadingData.
AI-метрики ожидают данные с кольцом внутри своего блока; ошибки, права,
проверки доступности провайдеров, статусы доставки и кнопки действий сохранены.

Повторные проверки после изменения:

- `.venv/Scripts/python.exe output/playwright/loading-20261005/verify.py dashboard dashboard-data-loading.spec.ts --project=desktop-chromium` — **3 PASS**:
  метрики владельца, fallback после 503 и рабочие списки менеджера.
- В `frontend`: `node --test scripts/tests/dashboard-appointment-dedupe.test.mjs scripts/tests/inbox-delivery-policy.test.mjs scripts/tests/fallback-surface-policy.test.mjs` — **9 PASS**.
- `verify.py build` и `verify.py bundle` по пути выше — **PASS** после всех
  production-изменений: i18n/types/app+widget/budgets.
- `.venv/Scripts/python.exe output/playwright/loading-followup-20261005/capture.py` —
  **9 PASS**: reload с удержанием ответа owner-dashboard (RU/KK/EN, два размера),
  reload менеджера с удержанием leads (RU, два размера), история входов mobile.
  Проверены отсутствие прежней строки, единая подпись, центрирование, overflow
  и восстановление контента после release. В первом запуске стенд не раскрыл
  details истории входов и получил timeout скрытого элемента; после реального
  клика summary вся матрица прошла. Это не дефект production-кода.
- Снимки и `results.json`: `output/playwright/loading-followup-20261005/`.
  Визуально просмотрены owner desktop/mobile, manager desktop и account mobile.
  [Dashboard desktop](../../output/playwright/loading-followup-20261005/owner-ru-desktop.png),
  [dashboard mobile](../../output/playwright/loading-followup-20261005/owner-ru-mobile.png).
- Diff hygiene и ссылки отчёта PASS; index пуст; собственные процессы остановлены.
  Полный backend/E2E не требовался; API/домен не менялись. Предыдущие результаты
  общих ring/delay/reduced-motion проверок переиспользованы: их реализация неизменна.

## Публикация

Изменения локальные, не закоммичены и не опубликованы. Сохраняется блокер
предыдущего [CI 37312854122](https://github.com/999MAX20/PlatformaCRM/actions/runs/37312854122):
dependency audit по неизменённому дереву зависимостей. Readback 13:47 UTC:
backend PASS, workflow FAILURE. Доказательство baseline
и подробности — в [предыдущем отчёте](ui-feedback-20261005.md).
Текущая UI-задача не включает обновление зависимостей или исключение из gate.
