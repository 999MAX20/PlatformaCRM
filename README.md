Management UI (12.11.2026): five real-data pages replace the previous Business entry.
The five Management migrations are applied to the owner-authorized local PostgreSQL
with verified backup/restore and preservation checks. Other environments require their
own reviewed migration target. [Behavior and verification](docs/testing/evidence/management-implementation-20261111.md).

## Лендинг CRM

Главная `/` показывает встроенный лендинг, «Войти» открывает существующий `/login`.
Обычная frontend-сборка включает страницы и файлы лендинга; отдельная папка-источник
не нужна. Для production требуется маршрутизация из `deploy/stand-access/Caddyfile`.
Лендинг развёрнут на защищённом [стенде](https://platformacrm.kz/); пароль и
действующая сборка CRM сохранены.
[Обслуживание исходников](frontend/landing/README.md) ·
[Проверки и схема одной VM](docs/testing/evidence/crm-landing-integration-20261106.md).

## Локальный dev в Windows

Из корня `C:\Users\user\Desktop\PlatformaCRM`:

```powershell
.\dev.ps1
```

Одна команда запускает Redis, ClamAV с обновлением баз, worker переноса,
Django и Vite. Уже запущенные проверенные процессы переиспользуются.
Текущая локальная CRM использует PostgreSQL на127.0.0.1:55432; launcher проверяет
и запускает закреплённый кластер до API. Исходная SQLite и проверенные backup
сохранены. [Перенос данных и измерения нагрузки](docs/testing/evidence/postgres-load-20261106.md).
CRM: [http://127.0.0.1:5173](http://127.0.0.1:5173).
Логи: `output/local-dev`. Нужны существующие `.venv`, frontend dependencies
и локальные Redis/ClamAV; команда ничего не скачивает и не устанавливает.
Миграции не применяются: если они ожидают применения, службы запускаются,
но выводится предупреждение и код2. Порядок/ограничения —
[локальный запуск](docs/current/operations.md#единая-команда-local-dev--06112026).

Voice input: microphone in the authenticated header → Send → ordinary permitted
action or clarification → result link, without an intermediate transcript or second
confirmation. Backend permissions, version checks and idempotency remain mandatory.
No created AI agent is required;
voice history belongs to the employee and Business, independently of agent settings. Personal microphone settings:
`/app/settings/voice`. OpenRouter STT uses `VOICE_TRANSCRIPTION_MODEL` separately
from the text model; see `.env.example` and the [voice contract](docs/current/voice-assistant.md).
Audio is transient, without TTS or continuous listening. Local synthetic checks
do not certify broad recognition quality or deployment. The independent voice path requires
`ai_core.0009_interface_voice_conversations`; verified in disposable databases,
applied to the local working database with an owner-authorized backup on05.11.
Default STT is `openai/whisper-large-v3-turbo` with ZDR/no-data-collection policy.
Local dev uses `AI_QUEUE_LIVE_REQUESTS=False` without Redis/AI worker; production
queue defaults are unchanged. Real synthetic-Russian audio→OpenRouter→direct Task
passed browser checks; full language/noise acceptance remains open.
[Verification](docs/testing/evidence/voice-direct-20261105.md).

File transfer workspace: Connections → Data transfer (`/app/integrations/import`).
CSV/XLSX staging supports clients, services, specialists and appointments, editable
rows, custom fields, previews and explicit confirmation. Preview/confirm use the
`reports_exports` worker queue; additive core0014–0017 migrations were tested only
in disposable databases. Import does not send notifications or run automations;
future appointments have a separate activation review. No working migration or
rollout was performed by this task. [Scope and checks](docs/current/import-workspace.md).

C09: для автоматической записи добавлена настройка ответственного в профиле
компании (SETTINGS UPDATE). Миграция businesses0014 оставляет существующим бизнесам
null; пока сотрудник не выбран, запись передаётся сотруднику для ручной обработки.
Миграция проверена только в изоляции, к рабочей БД не применялась.
[Граница локальной проверки](docs/testing/evidence/remediation-c09-20261104.md).

Source archive (Linux/WSL): `bash scripts/make_clean_archive.sh [name.zip]`.
Requires rsync and Python3; no separate zip executable. It packages source/docs
and declared env templates under zani/, excluding runtime/private artifacts and
symlinks. It is not a working-data backup or an arbitrary-secret scanner.
[Packaging rules and checks](docs/testing/evidence/remediation-c04-20261104.md).

Manual booking from Client or Inbox uses one Appointment and a separate booking
coordinator; closed Lead/Deal history is preserved. The UI checks current slots and
terms, supports safe retry, and refreshes calendar/client/Inbox views. Additive
scheduling0010 must be applied through the separately authorized target migration
process. The original package tested it in disposable databases; on02.11 it was
separately applied to the local dev database with backup (UI-REFRESH-20261102).
The later nonmonetary Records/VisitPlan package was published as6349acdf; plan money
and target/live rollout remain open. [Checks and publication](docs/testing/task-state/PRIMARY-SESSION.md#crm-r01-record-first-20261031--single-appointment-package).

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

Клиентский агент Inbox сохраняется. По решениям30.10/02.11 обычная CRM и
ограниченный помощник сотрудника D01 (текст/голос) обязателен в пилоте; расширенная AI-аналитика отложена, runtime сохранён.
Telegram/WhatsApp включены в подготовку пилота R02 решением 14.10; реальная
доставка не принята. Для WhatsApp локально добавлен первый этап YCloud TP Lite:
подключение и текстовый обмен в существующем Inbox; провайдер выключен по умолчанию.
[Настройки и границы](docs/current/operations.md), [контракт](docs/current/integrations.md).
Прочие интеграции, gateway и коммерческий billing отложены. Реализация и локальные
проверки есть; production-допуск и работа реальной клиники не объявлены.

Локально реализованы персональная лента сотрудников и объявления бизнеса с мониторингом
открытия, прочтения и ознакомления. Публикация/мониторинг — владелец и администратор.
[Паспорт и границы проверки](docs/pre-production/settings-notifications.md). Рабочие
миграции персональной ленты отдельно проверены локально. Для мониторинга добавлен
опциональный SSE через Redis и отдельный ASGI: [запуск](docs/current/operations.md#sse-мониторинга-объявлений--локальная-реализация).
SSE выключен по умолчанию; deployment и включение в рабочей среде не выполнены.

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

Local frontend servers use separate Vite dependency caches per port/mode;
parallel test servers must use distinct explicit ports. Builds no longer emit a
JavaScript config beside `vite.config.ts`. Existing-checkout cleanup and restart:
[development cache isolation](docs/current/operations.md#vite-development-cache-isolation-03112026).
