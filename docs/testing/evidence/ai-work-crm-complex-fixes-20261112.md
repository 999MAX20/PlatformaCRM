# AI-WORK-CRM-COMPLEX-FIXES-20261112

Поручение: исправить C1–C3 и повторить сложные сценарии через Playwright/API
с реальным AI без изменений рабочих данных; сохранить новую заявку→Appointment.
Исходные находки: [аудит](ai-work-crm-complex-20261112.md).

## Результат

- C1: планировщик получает выбранный шаг, исходный запрос остаётся вспомогательным
  контекстом. Разные независимые создания с одинаковыми итоговыми полями требуют
  уточнения до создания предложений. Два независимых создания и разные описания,
  зависимая цепочка, исправление старого предложения и replay проверены.
- C2: read задаёт active/archived/all. Точный ID читается внутри доступного Business/
  role/source scope; отсутствие записи возвращает нейтральный no-data без выдуманного
  отключения источника. Read/update/restore/archive и скрытые/чужие ID проверены.
- C3: серверный review содержит доступные текущие названия связей и timezone бизнеса;
  API/UI не изменяет исполняемый payload/fingerprint. Карточка показывает клиента,
  услугу, специалиста, филиал и локальную дату/время. RU/KK/EN1440/320/390,
  клавиатурный просмотр/подтверждение и отмена проверены в Chromium.
- В повторной сложной цепочке выявлено несогласованное множество ID: модель видела
  запись в разрешённом CRM summary, но router принимал только available_records.
  Обе текущие scoped-выборки теперь согласованы; неизвестный ID по-прежнему
  отвергается, неоднозначное название уточняется. Целевой realAI API и browser PASS.

Новые заявки создают Appointment; исторический Lead сохраняет ID и обновляется
как Lead. Уже присутствовавшая нормализация из другого поручения сохранена,
её авторство/публикация не присваиваются этому изменению.

## Проверки и исходные неуспехи

Канонический checkout `C:/Users/user/Desktop/PlatformaCRM`, текущая ветка
`codex/ui-testing-toolkit`, старт `372ec4f8`; параллельные чужие изменения сохранены.
Все backend-прогоны через `output/ai-work-crm-complex-fixes-20261112/verify.py`,
который использует `scripts.codex_verify.isolated_runtime` и временную SQLite.

- Focused независимые действия3PASS; review+API11PASS. Ранние15/9 прогоны имели
  ошибочные test fixtures/assertions; исходные логи сохранены, соответствующие
  сценарии повторно проверены. Никакие продуктовые assertions не ослаблены.
- Affected44:43PASS/1ERROR в новом schema-тесте без обязательного routing context.
  Исправлена только fixture; далее archive/targets/API/crm_tools/voice_direct/
  voice_identity70PASS. Остальные unchanged44 результаты переиспользованы.
- После согласования ID: complex/targets/execution/requestAppointments32:
  31PASS/1ERROR из-за передачи AIClientResult вместо output_text в новом тесте.
  Исправлен вызов теста; отдельный повтор1PASS (log1794427612377197300).
- `manage.py check`, `makemigrations --check --dry-run`: PASS, миграций нет.
- `node --test scripts/tests/ai-review-value.test.mjs`:2PASS. `npm run build`:
  финальный i18n/types/app/widget PASS; `npm run check:bundle`:PASS.
  Первоначальный build выявил Object.hasOwn под текущим target; исправлен
  совместимый вызов, конфигурация не менялась. Ошибочный путь check-bundle-budget
  отсутствовал; фактическая команда из project runner выполнена успешно.
- RealAI initial API17:15PASS/2FAIL (duplicate ID и archive→transition).
  Extended6:4PASS/2FAIL: общий отказ вместо ожидавшегося partial (нет неразрешённой
  записи), и overlap потребовал уточнить клиента. Fresh recovery3:2PASS/1FAIL:
  archive и overlap/retry восстановились; duplicate ID потребовал описанного fix.
  Финальные targeted5PASS: duplicate, явный dependent partial/access denial,
  missing/foreign/hidden archived lookup. Первичные FAIL не удалены.
- Browser core6PASS; followup3PASS/1FAIL (harness ожидал 1of2 у исходного запроса,
  фактически целиком отклонённого); final2PASS на исправленном duplicate и явно
  зависимом partial. Итого11PASS/1сохранённый harnessFAIL, включая три viewport/locale.
  Снимки review RU/KK/EN просмотрены; raw relation IDs/aiCRM.field.branch отсутствуют.

90 реальных OpenRouter/openai/gpt-4o-mini вызовов,377292 tokens,0provider errors,
0mock. Это не гарантия отсутствия дополнительных вопросов/вариативности модели.
Повторная проверка показывает безопасные отказы и восстановление; исходные
ошибочные планы/уточнения сохранены в evidence, не названы первичным PASS.

## Данные, среда и границы

Полная read-only SQL-сверка пяти CRM entity tables до/после: только2новых Client,
12Task,2Appointment,0новых Lead/Deal/удалений и9ожидаемых обновлённых старых строк.
Все остальные значения равны baseline, foreign records сохранены. Маркеры скрытых
и чужих данных отсутствуют в проверяемых provider inputs/outputs. Нет writes до
подтверждения, дублей replay и изменений отменённой заявки.

Источник первого сервера зафиксирован до запуска, autoreload выключен. После fix
router запущен новый собственный runtime над той же одноразовой БД; повторены
только затронутые цели. Source drift перечислен в audit.json: собственный router/
тесты и чужие speech.py/tests_speech.py/VoicePanel.tsx. Чужие voice изменения
не включены в результат; первая voice-suite подтверждает свой снимок, их новые
изменения этой задачей не сертифицируются. Реальные Work CRM результаты относятся
к указанным двум runtime и их запросам; первоначальные source hashes сохранены.

Рабочая БД, env/provider settings, внешние сообщения и deployment не менялись.
Все собственные runtime остановлены; отсутствие disposable DB проверяется receipt.
FullD01/R01/release, PostgreSQL concurrency, live queue, human STT, другие модели
и production не сертифицировались: это локальная проверка C1–C3.

В scoped коде/локальных доказательствах остатка нет. Публикация только своих
изменений заблокирована 48ранее исходящими чужими коммитами; normal push не выполнен,
нового CI/deployment нет. Только собственные paths/hunks допускаются в local commit.

Контракт AI/frontend, паспорт, D01 roadmap, STATUS/checkpoint и registry согласованы.
CRM/access/integrations/operations/README не требуют изменения этой задачей:
новых правил домена/прав/настроек/миграций/интеграций нет. Исходный аудит сохранён.

Подробные команды, снимки, provider calls, SQL, исходные FAIL и recovery:
`output/playwright/ai-work-crm-complex-fixes`; backend/build логи и ownership baseline:
`output/ai-work-crm-complex-fixes-20261112`. Эти локальные synthetic artifacts не
публикуются вместе с исходниками.
