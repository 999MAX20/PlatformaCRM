# PlatformaCRM — текущий статус

07.10.2026. Консолидация документации DOCS-RESET-20261007 выполнена и проверена.
Подготовлены действующие контракты, карта реализации, обновлённые entrypoints
и архив с проверяемым происхождением. Проверки целостности, ссылок и маршрутов
PASS; итоговый commit определяется Git history, SHA/CI фиксируются в ответе задачи;
[checkpoint](docs/testing/task-state/PRIMARY-SESSION.md) содержит scope и evidence.

Продуктовый фокус — клиентский Inbox AI поверх обычной CRM. Последняя safety
версия реализована, локально проверена с mocked provider и опубликована с CI PASS.
Live-проверки предшествуют этой защите; production/каналы/клиническая приёмка
не объявлены. CRM AI/аналитика на паузе разработки без удаления runtime.

[Паспорта](docs/pre-production/README.md) · [что реализовано](docs/pre-production/capabilities.md)
· [действующие требования](docs/README.md) · [открытая приёмка](docs/current/acceptance.md).
Внешние интеграции, gateway и billing отложены. Новый продуктовый этап не назначен.

Canonical root `C:/Users/user/Desktop/PlatformaCRM`; branch `codex/ui-testing-toolkit`.
Generation 4 primary, transition idle — [.codex/project-session.json](.codex/project-session.json).
История перенесена в архив; не продолжать старые задания по прежним записям.
