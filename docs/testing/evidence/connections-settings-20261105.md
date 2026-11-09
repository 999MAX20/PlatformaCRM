# CONNECTIONS-SETTINGS-20261105

## Результат и граница

По запросу владельца «Подключения» убраны из desktop/mobile Sidebar и встроены
в существующую навигацию настроек (`/app/settings#integrations`, группа «Общение»).
Переиспользованы SettingsSection и IntegrationsPage с compact embedded layout;
карточки, dialogs и импорт сохранены. Компонент загружается только при открытии
вкладки. Название берётся из существующего nav.integrations для RU/KK/EN.
Старые `/app/integrations` и `/integrations` переводят на вкладку, сохраняя query.

SettingsAccessRoute и Sidebar разрешают вход с settings.update OR integrations.view.
Секции фильтруются прежними собственными правами; integrations.view не открывает
изменение профиля или management-действия. Backend/API/tenant/provider контракты,
уведомления, BusinessEvent/AI, зависимости и миграции не менялись.

## Срез и проверки

Канонический root: `C:/Users/user/Desktop/PlatformaCRM`.
Branch `codex/ui-testing-toolkit`, HEAD `66101d509cb7642b2928275e48c4b64354abf07b`.
Dirty baseline сохранён в `output/connections-settings-20261105/before.diff`
и `before-status.txt`; существующая работа других задач сохранена.
План/runner/spec/logs/screenshots находятся в той же output-папке.

- `.venv/Scripts/python.exe output/connections-settings-20261105/run.py --browser`:
  isolated_runtime, отдельные порты/SQLite, prepare + собственные Django/Vite.
  Первый запуск:4 PASS (RU navigation, integrations-only, settings-only, loading/error/reload).
  Два mobile locale случая остановились на неоднозначном locator скрытых select
  в тесте; исправлен тест на видимый combobox и option. Код приложения не менялся.
- `.../run.py --build`: PASS, i18n, TypeScript, Vite application/widget.
- `npm run check:bundle` из frontend: PASS; прежние предупреждения крупных RU/KK
  chunks, app shell в лимите. Первый вызов из root не нашёл assets; правильный cwd PASS.
- Role cases изменяют frontend auth fixture: это доказательство UI visibility,
  не новая backend сертификация. Backend не менялся. Full E2E/release не требуются
  для этого ограниченного переноса. Рабочая БД, dev-сервера, env и deployment не менялись.

## Публикация

Существующий `.git/index.lock` и17 чужих outgoing commits блокируют безопасный
собственный commit/push. Lock/чужая история сохранены. Собственного commit/push,
нового CI или deployment нет.

Профильный frontend-контракт, паспорта integrations/settings и реестр evidence обновлены. Roadmap/product/access/
AI/integrations API/operations/setup README не требуют изменения: перенос места
в UI не меняет доменные сценарии или API. Итог повторной browser проверки ниже.

## Финальный результат

Повтор `run.py --browser --grep "connections settings navigation"`:3 PASS.
Всего6 различных сценариев PASS по двум запускам. RU1440/KK390/EN768:
старые ссылки/query, переключение разделов (desktop keyboard/mobile combobox),
две карточки, dialog open/Escape, отсутствие horizontal overflow. Screenshot
RU/KK осмотрены: header/navigation/grid соответствуют существующей системе.
Loading/error/reload, integrations-only/settings-only проходят в первом запуске.
Тестовые роли ограничивают frontend profile; backend-авторизация не изменялась.
Scoped diff hygiene PASS; registry parse и новые relative links проверены.
Нет незавершённого кода/локальных проверок принятого scope. Остаток среды:
commit/push/CI из-за ранее существовавшей блокировки. Новых процессов не оставлено;
изолированный runner завершил свои серверы. Не заявляется deployment.
