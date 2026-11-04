# C03 — секреты в console logs и paid-beta readiness

**Закрыто локально**, 04.11.2026. Scope: PAID-BETA-BROKER и
EXCEPTION-SECRET-LOGGING; C04 не начат. Canonical PlatformaCRM,
`codex/ui-testing-toolkit`, base`121d5e53b9b2f39bf9b1f42ef8026e613a2e6a81` + сохранённый WIP.
Контракт до правок: `output/remediation-c03-20261104/CONTRACT.md`.

## Поведение

Paid-beta readiness показывает только broker configured/TLS/inline metadata,
не URL, host/path, userinfo/query/fragment. Условие pass/fail и блокировки сохранены.
JSON console formatter нормализует custom значения и применяет существующий
`sanitize_error_payload` к сообщениям, уже подставленным args, traceback/chains
и разрешённым context fields. Type/frames/request correlation, числовые поля и
полный длинный безопасный diagnostic сохранены; исходный LogRecord не изменяется.
Общий sanitizer дополнен обработкой quoted credential assignments: пробелы,
другая кавычка, escaped quote и newline не оставляют хвост секрета.

Охватываются распознаваемые credential forms: URL userinfo, sensitive query/key
assignments, JSON/dict secret keys, Bearer/Basic и существующие Telegram patterns.
Это не обещание распознать произвольную немаркированную строку как секрет. Запрет
логирования сырых customer/provider/auth payload остаётся обязательным для callers.
Никакие реальные credentials не читались для тестов и не отправлялись наружу.

Обновлён существующий connector regression: raw-token expectation заменён
конфиденциальностью именно форматированного output с сохранением RuntimeError,
traceback и generic public reason. `assertLogs` сам устанавливает другой handler;
поэтому отдельные тесты используют **реальный root console handler из settings**,
его RequestContextFilter/JsonLogFormatter, с временным in-memory stream.

## Проверки и пределы

Runner: `.venv/Scripts/python.exe output/remediation-c03-20261104/run_checks.py`.
Он использует isolated_runtime и C01 guarded bootstrap: disposable SQLite,
safe environment, без рабочей dotenv/внешних socket connections.

- `baseline`:8 tests,7 failing methods/8 failing assertions (JSON/text subtests),
  1 positive control PASS. Обе исходные утечки воспроизведены синтетически.
- `focused apps.core.tests_log_redaction
  apps.integrations.tests_connectors.BusinessConnectorFoundationTests.test_provider_exception_is_logged_but_public_reason_is_generic`:
  9 PASS после первого исправления.
- `focused-final` с теми же labels:11 PASS, включая encoded userinfo/IPv6,
  Basic, quoting/escapes/newline и nested payload без mutation.
- `completion`:**105 PASS**; system check/migration drift PASS. Labels:
  `apps.core.tests_log_redaction`, `apps.core.tests_paid_beta_gate`,
  `apps.core.tests_production_audit`, `apps.core.tests_observability`,
  `apps.core.tests_readiness_redaction`, `apps.integrations.tests_connectors`,
  `apps.integrations.tests_public_api.PublicApiAndWebhookTests.test_webhook_delivery_sanitizes_payload_before_storage`,
  `apps.integrations.tests_public_api.PublicApiAndWebhookTests.test_webhook_delivery_sanitizes_error_and_response_body`,
  `apps.core.tests_import_export.ImportExportTests.test_import_job_error_is_sanitized_at_persistence_boundary`,
  `apps.core.tests_b5_performance.BackendPerformanceRegressionTests.test_json_logging_carries_release_and_request_id_without_payload`.

Baseline/focused/focused-final/completion logs сохранены; точные `.log.gz` копии
и hashes входят в локальный пакет. Приёмка относится к текущему snapshot с WIP.
Нет нового UI, схемы, permission/lifecycle/BusinessEvent/notification/AI поведения;
UI/build/full-E2E/full-backend/PG/live/deployment не запускались. Shared sanitizer
проверен зависимыми persistence/API/provider tests; старые general audit/CI failures
не закрываются этим scoped PASS.

Sentry в config/settings.py отдельно инициализирован с send_default_pii=False,
без before_send redaction hook. Он получает exception независимо от console
formatter; эта работа **не доказывает безопасность Sentry**, иных handlers или
внешнего log pipeline. Реальная доставка telemetry не выполнялась. Граница
исходной EXCEPTION-SECRET-LOGGING — configured console — сохранена.

## Документы, сохранение и остаток

Operations contract/passport, C03 plan row, STATUS/checkpoint и registry обновлены.
Access/CRM/AI/frontend contracts и README не меняются: их правила/сценарии/setup
не изменены. Чужие production_audit.py/production_rules.py/config.settings.py
сохранены по hash; собственные target files до начала были чистыми. WorkingDB
SHA256 неизменна, dev8000/5173 остаётся выключенным, test runtime очищен.
Исторические аудиты не переписаны. Код/доказательства/среда/решения владельца
в scope C03 без остатка; внешние sinks не получили blanket PASS.
Только собственный локальный commit; no push/merge/deploy/newCI.
SHA/paths/checks: `output/remediation-c03-20261104/final-validation.json`.
Следующий отдельный цикл — C04.
