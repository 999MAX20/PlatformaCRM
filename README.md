Manual booking from Client or Inbox uses one Appointment and a separate booking
coordinator; closed Lead/Deal history is preserved. The UI checks current slots and
terms, supports safe retry, and refreshes calendar/client/Inbox views. Additive
scheduling0010 must be applied through the separately authorized target migration
process; it was tested only in disposable databases. Plans/payments and live rollout
remain outside this package. [Checks and publication](docs/testing/task-state/PRIMARY-SESSION.md#crm-r01-record-first-20261031--single-appointment-package).

# PlatformaCRM

Owner signup starts with the neutral `other` business type; industry selection
is explicit. Invitation bearer links require current TEAM MANAGE, existing role
restrictions survive onboarding, and generic Business DELETE is unavailable.
Invalid MFA codes display correction guidance without claiming session expiry.
Isolated two-business checks and delivery status: [PILOT-ACCESS evidence](docs/testing/task-state/PRIMARY-SESSION.md#pilot-access-20261031--two-business-onboarding-and-access).

Authentication API clients: first GET `/api/auth/csrf/`, retaining cookies;
then send the returned `csrf_token` as `X-CSRFToken` with the same cookie jar for
login, refresh, logout, social login, owner signup, MFA confirm/verify and password
reset confirmation. HTTPS clients must also send their valid Origin/Referer.
Separate frontend origins must be explicitly allowed by CORS and CSRF settings.
The frontend, Playwright `authPost` helper and `scripts/api_load_smoke.py` implement
this flow. Ordinary bearer API authorization is unchanged.


CRM для малого бизнеса с AI-слоем. Первый целевой пользователь — администратор
стоматологии. Система ведёт обращения, клиентов, сделки, задачи, запись к
специалистам и переписку; клиентский AI помогает обрабатывать обращения поверх
обычной CRM. Медицинские карты и клинические решения в продукт не входят.

На 07.10.2026 текущий фокус — клиентский агент Inbox. Обычная CRM сохраняется;
развитие внутреннего CRM-агента/аналитики приостановлено без удаления runtime.
Telegram/WhatsApp включены в подготовку пилота R02 решением 14.10; реальная
доставка не принята. Для WhatsApp локально добавлен первый этап YCloud TP Lite:
подключение и текстовый обмен в существующем Inbox; провайдер выключен по умолчанию.
[Настройки и границы](docs/current/operations.md), [контракт](docs/current/integrations.md).
Прочие интеграции, gateway и коммерческий billing отложены. Реализация и локальные
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
не создавайте вторую копию исходников. Работа выполняется по явному поручению пользователя; межчатовые назначения
writer и обязательные согласования отменены решением 14.10.

## Локальная работа

Используйте существующий согласованный environment. Для чистой установки
Python dependencies устанавливаются с `--require-hashes`, frontend — `npm ci`
из `frontend/`; Node должен соответствовать `engines` в package.json (>=22.22).
Конфигурация описана в [.env.example](.env.example); рабочие secrets не коммитятся.
XLSX импорт ограничен числом строк/столбцов и разжатым ZIP-объёмом; значения
`IMPORT_*` и правила отказа описаны в [operations](docs/current/operations.md#лимиты-xlsx-импорта).
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

### STAND-ACCESS-20261029
Закрытый сетевой стенд: [пароль доступа и Compose overlay](docs/current/operations.md#stand-access-20261029--пароль-доступа-к-сетевому-стенду). Защита не активируется обычным локальным запуском.
