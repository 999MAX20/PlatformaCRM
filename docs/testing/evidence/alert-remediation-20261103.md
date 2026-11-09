# ALERT-REMEDIATION-20261103 — постоянные состояния и временные уведомления

## Результат и граница

Поручение: исправить A01–A05 аудита и убрать глобальные полосы, сдвигающие страницу.
Уточнение владельца: долгосрочная причина отсутствия данных должна быть постоянной,
находиться возле соответствующего раздела и вести к реальному способу исправления.

Реализовано локально на canonical `C:/Users/user/Desktop/PlatformaCRM`, branch
`codex/ui-testing-toolkit`, HEAD `e02a28f550e94a543c3d88acac7c1b19ee48f90b` плюс сохранённый
существующий WIP. [Manifest исходников и снимков](alert-remediation-20261103-manifest.json).
Это не проверка чистого опубликованного HEAD и не deployed acceptance.

- ServiceStatusNotice удалён из потока AppLayout. В шапке есть постоянная кнопка
  состояния, открывающая подробности, affected components, обновление и поддержку.
  Loading/unknown/degraded/healthy сохраняют место. Закрытие подробностей не скрывает
  индикатор; новое окно показывает актуальное состояние. API/query isolation сохранены.
- Финансовая причина остаётся внутри FinancialSummary без таймера/закрытия. Используется
  существующий API reason; при подходящей причине есть ссылка «Проверить подключения».
  Disabled module/нет права просмотра дают текст об администраторе. Permission denied,
  ручной источник и неизвестная причина не получают ложную рекомендацию коннектора.
  Это не новый детектор незаполненных настроек и не утверждение, что любой пустой
  отчёт зависит от интеграции. Наличие/отсутствие провайдера не подменяет worker health.
- ClientForm показывает ошибку save внутри формы, сохраняет ввод, повторяет submit.
  Save error больше не попадает в общий pageError с refetch чужих read-запросов.
- Resources: одна ошибка в активной форме; исходный AppError сохранён. В создании
  с филиалом ошибка принадлежит ResourceCreateForm, без филиала — шагу недельного
  графика, который уже обрабатывает отказ. Смена/повторное открытие сбрасывает ошибку.
- Account: несовпадение паролей валидируется локально, связано с полем и переводит
  фокус к подтверждению; API не вызывается. Профиль/пароль подтверждаются общим toast.
- Bell: неизвестные счётчики не представлены нулём; есть повтор загрузки, массовое
  прочтение недоступно при ошибке. Ошибки полей/форм остаются у действия, transient
  toast/undo/network/Inbox используют существующий нижний host.

Пять строк добавлены согласованно в RU/KK/EN. Новых клинических терминов нет.
Backend/API/schema/migration/env/BusinessEvent/AI/permissions changes: none.
Новая отправка email/сообщений или работа с обычной DB не выполнялась.

## Доказательства

Изолированные Django/Vite из canonical root: backend65073, frontend65074,
`output/alert-remediation-20261103/remediation.sqlite3`. Runtime использует
safe_environment, отдельную cookie, synthetic fixtures, запрет внешнего socket connect
и выключенные реальные провайдеры. Источник: `output/alert-remediation-20261103/runtime.py`.
Обычные dev-порты/базы не используются. Локальные mutation-сценарии выполнялись только
с synthetic данными; смена пароля подставлена200, реального изменения пароля нет.

22 уникальных браузерных сценария проверены на итоговом коде:20 PASS в completion
run;2 остановились до форм из-за login HTTP429, затем оба PASS без изменения кода
или ослабления rate limit. Исходный completion run остаётся 20 PASS/2 FAIL; его не
переименовываем в полностью зелёный запуск. Это focused suite, не весь проект.

Проверены RU1440×1000, KK/EN390×1000: Client503→повтор→реальный save, Resource503→save,
password mismatch/no-request/correction, profile toast/new draft; status transitions,
keyboard Enter/Escape/focus return, support link, unknown counters/retry, financial
no-source/reload/link/permission_denied/recovery. Дополнительно: недоступный модуль
подключений, обе формы создания ресурса, offline→online без вертикального сдвига.
Финансовые reason states и role/module boundary подставлены на существующем API;
это UI-проверка, а не новая сертификация серверных денежных прав или расчётов.

| Проверка | Команда / результат |
|---|---|
| Focused browser | `node frontend/node_modules/@playwright/test/cli.js test --config=frontend/playwright.alert-remediation.config.ts`, ALERT_APP_URL loopback + ALERT_APP_ISOLATED=1.20 PASS/2 login429; `--grep '(client save\|resource error).*kk'`:2 PASS. Logs browser-completion.log / browser-throttle-recheck.log |
| Shared feedback | `node --test scripts/tests/gate-environment-policy.test.mjs scripts/tests/notification-header-model.test.mjs scripts/tests/notification-dedupe.test.mjs scripts/tests/action-feedback-policy.test.mjs scripts/tests/app-error-normalization.test.mjs` из frontend с safe env:19 PASS |
| Build/types/i18n | `npm run build` из frontend с проверенным safe env: PASS,6655 keys per language; app и widget собраны. Финальный build после исправления контраста и ownership ошибки создания ресурса |
| Bundle | `npm run check:bundle`: PASS shell400kB; warnings ru509.9kB/kk511.3kB сохранены |
| Source/docs | Собственный patch сверён с starting snapshot; scoped diff hygiene, JSON manifest/registry и ссылки проверены. Без установки зависимостей |

[RU финансовая причина](alert-remediation-20261103-assets/financial-prerequisite-ru.png),
[KK](alert-remediation-20261103-assets/financial-prerequisite-kk.png),
[EN/mobile](alert-remediation-20261103-assets/financial-prerequisite-en.png).
[RU состояние сервиса](alert-remediation-20261103-assets/service-details-ru.png),
[KK/mobile](alert-remediation-20261103-assets/service-details-kk.png),
[EN/mobile](alert-remediation-20261103-assets/service-details-en.png).

## Сохранённые падения и открытое ограничение

Во время итерации тесты выявили неверный tab=money вместо finance, нестабильную
индексацию исчезающих retry-кнопок, восстановление языка аккаунта из preferences,
неожидание завершения route.fetch при teardown, скрытый duplicate primary-action и
неизменённый график перед submit. Исправлены именно fixtures/selectors/waits,
не продуктовые ожидания. Визуальный просмотр выявил тёмный текст в новой синей
financial-карточке — исправлен через inNotice без смены остальных потребителей.
Первое размещение ошибки создания ресурса дублировало ошибку шага графика — ownership
разделён; обе ветки теперь проверены. Логи попыток сохранены в ignored output.

Дополнительный существующий `service-s03.spec.ts --grep 'service status shows'`
остаётся **FAIL** на конкретном тексте уведомления о задержке экспорта в bell.
Изолированный fixture создал overdue ExportJob и вызвал observe_business_service;
новый индикатор корректно показал задержку экспорта до проваленной проверки bell.
Диагностика без браузера:2 service notifications,1 owner notification/receipt,
API200 и1 service ID в ответе. Текст в UI — «Рабочее обновление».
`apps/notifications/serializers.py:99–101` в существующем WIP заменяет текст work-event
общим message_key и очищает text. Diff этого файла совпадает с starting snapshot;
backend в этой задаче не изменялся. Тест не ослаблен до generic text. Его последующие
шаги не объявлены выполненными; состояния дополнительно проверены новой focused suite.

A01–A05 и новая схема размещения реализованы и scoped-проверены. Полная S03-приёмка
конкретного текста исторических событий остаётся открытой. Исправление требует
безопасной типизированной проекции service events с сохранением текущей редактуры
приватных полей; возврат произвольного старого text не является допустимым обходом.
Это отдельный серверный остаток, не скрытый PASS frontend-проверки.

## Документы, публикация и остаток

Frontend contract, operations, settings-notifications passport и заметка S03 roadmap
согласованы с этим срезом. README/CRM/access/AI/integration contracts не менялись:
setup, API, доменные правила и права не изменены. Старый аудит остаётся историческим
срезом; его находки не переписаны под новый PASS. Нет полной сертификации всех
маршрутов/ролей, screen reader, всех причин финансового API, backend delivery или live.

Публикация заблокирована существующим `.git/index.lock`; также сохранены dirty
prerequisites общих alerts/personal notifications/Records. Чужой WIP не staged.
Своих commit/push/CI/deploy нет; working DB migrations не выполнялись.
Остаток: код — конкретная серверная проекция service events; доказательства — старый
S03 exact-text FAIL; публикация/среда — index.lock и mixed prerequisites, затем CI/live
в отдельной границе. Новый бизнес-policy вопрос для реализованных UI-исправлений нет.

Own isolated backend22164/frontend3588 stopped after root/port verification.
Source hashes remained unchanged after final checks; ordinary dev servers retained.
