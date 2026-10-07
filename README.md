# PlatformaCRM

CRM для малого бизнеса с AI-слоем. Первый целевой пользователь — администратор
стоматологии. Система ведёт обращения, клиентов, сделки, задачи, запись к
специалистам и переписку; клиентский AI помогает обрабатывать обращения поверх
обычной CRM. Медицинские карты и клинические решения в продукт не входят.

На 07.10.2026 текущий фокус — клиентский агент Inbox. Обычная CRM сохраняется;
развитие внутреннего CRM-агента/аналитики приостановлено без удаления runtime.
Внешние интеграции/мессенджеры, gateway и billing отложены. Реализация и локальные
проверки есть; production-допуск и работа реальной клиники не объявлены.

## С чего начать

- [Состояние и текущее поручение](STATUS.md).
- [Карта реализованных возможностей и границ](docs/pre-production/capabilities.md).
- [Паспорта pre-production](docs/pre-production/README.md), включая клиентский AI.
- [Действующая документация](docs/README.md): продукт, CRM, доступ, AI, интерфейс,
  интеграции, эксплуатация и незакрытая приёмка.
- [Правила работы агентов](AGENTS.md) и [проверки](docs/testing/testing.md).

## Устройство репозитория

Backend — Django/DRF с tenant-контекстом Business, domain services/selectors,
Celery для фоновой работы. [Маршруты](config/urls.py), [приложения](apps/README.md).
Frontend — React/TypeScript/Vite, Tailwind 4, общий API/UI слой, RU/KK/EN.
[Frontend и команды](frontend/README.md). Python зависимости фиксируются в
[requirements.txt](requirements.txt), frontend — в [package-lock.json](frontend/package-lock.json).

Единственный writable checkout: `C:/Users/user/Desktop/PlatformaCRM`.
`Desktop/Zani` — junction к нему. Сохраняйте текущую ветку и чужую работу;
не создавайте вторую копию исходников. Один зарегистрированный writer.

## Локальная работа

Используйте существующий согласованный environment. Для чистой установки
Python dependencies устанавливаются с `--require-hashes`, frontend — `npm ci`
из `frontend/`; Node должен соответствовать `engines` в package.json (>=22.22).
Конфигурация описана в [.env.example](.env.example); рабочие secrets не коммитятся.
Не переносите demo/seed в рабочую базу и не применяйте migration автоматически.

Для уже настроенной среды из canonical root:

```powershell
.\.venv\Scripts\python.exe manage.py runserver 127.0.0.1:8000
```

Из `frontend/`: `npm run dev -- --host 127.0.0.1`.
Сначала проверьте владельца процессов/порты и source roots. Фоновые flow требуют
своих workers/beat, AV — scanner; один devserver не доказывает их работу.
Точная изоляция тестов и выбор команд — [testing](docs/testing/testing.md),
эксплуатационные ограничения — [operations](docs/current/operations.md).

## Документация и история

Реестр [docs/documentation-index.json](docs/documentation-index.json) отделяет
действующие контракты от паспортов, процедур и generated evidence. Старые планы,
отчёты и прежний длинный README перенесены в [архив](archive_docs/README.md).
Архив исключён из обычного `rg`; читать его точечно для evidence, не как актуальное
задание или набор требований. Открытые обязательства сохранены в
[acceptance](docs/current/acceptance.md). Эта консолидация не меняет код или БД.
