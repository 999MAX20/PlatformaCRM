## C10 — очистка записей повторных команд, 04.11.2026

prune_expired_crm_commands повторно проверяет expires_at по исходному cutoff
непосредственно в DELETE. Запись, продлённая после выборки ID посредством
begin/run_idempotent_crm_command, сохраняет claim/успешный результат и replay;
неизменённые просроченные записи удаляются. Порядок, лимит и retention прежние.
SQLite BEFORE3:2FAIL/1PASS; AFTER3 и dependent23 PASS; PostgreSQL8 PASS, включая
разные соединения select→renew/commit→delete и реальный Task без повторного создания.
System/migration drift PASS. No migration/env/UI/workingDB/push/live changes.
[C10 evidence](../testing/evidence/remediation-c10-20261104.md).

## C07 — конфиденциальность URL телеметрии, 04.11.2026

Frontend Sentry/PostHog/Plausible заменяют reset-password, invite и invitation-preview
bearer URLs шаблонами в проверенных payload, включая вложенные/кодированные значения
и автоматически добавленные metadata. Обычные события и URL сохранены. PostHog
replay и неиспользуемые flags/remote-config отключены: эти каналы обходят before_send.
Plausible manual получает явный безопасный URL; при чувствительном referrer tracker
не запускается весь срок жизни документа, поскольку legacy SDK сам читает referrer.
Включение дополнительных SDK-каналов требует отдельной проверки этого ограничения.
Это локальная проверка frontend payload, не backend Sentry/live ingestion или
универсальный PII filter. [Проверки и границы C07](../testing/evidence/remediation-c07-20261104.md).

C04,04.11.2026: source archive uses `bash scripts/make_clean_archive.sh [name.zip]`
on Linux/WSL with rsync and Python3; standard `python3 -m zipfile` replaces Info-ZIP.
Flat filename only, default zani-clean.zip; archive prefix zani/ retained. Private
runtime/output/backup/browser/auth paths, env/DB artifacts and symlinks/special files
are excluded; declared env examples and intended sources/docs remain. Build failure
does not remove the prior archive. This is not a working-data backup or a scanner
for arbitrary secrets embedded in source/templates. Review intended inputs before
distribution; excluded runtime evidence can leave docs links outside the package.
[Synthetic archive evidence](../testing/evidence/remediation-c04-20261104.md).

C03,04.11.2026: paid-beta readiness reports broker configured/TLS/inline state,
never the configured URL. The configured JSON console normalizes and sanitizes
message arguments, exception chains and allowlisted context with the shared
credential-pattern sanitizer; error type/frames/request correlation remain.
Quoted multiword/escaped/newline credential assignments are fully masked.
Do not log raw sensitive payloads: arbitrary unlabeled values cannot be inferred
as secrets. Backend Sentry/other handlers/external pipelines remain unverified sinks;
send_default_pii=False alone is not a redaction proof. No live telemetry sent.
[Local C03 evidence](../testing/evidence/remediation-c03-20261104.md).

# Эксплуатация и допуск окружения

Исходная основа `768b2675`, 09.10.2026; актуальные дельты 16.10 описаны ниже.
Пользовательский результат — работающая CRM с
восстановлением после отказа; операционный владелец должен уметь обнаружить и
устранить проблему. [Operations contract](../current/operations.md) определяет требования.
Последнее поручение владельца на аудит03.11 выбирает Yandex Cloud вместо прежнего
направления14.10. Регион, сервисы и ресурсы ещё не определены; размеры Hoster.kz
не критерий. Прежнее требование размещения данных в Казахстане сохраняется для
сверки выбранной конфигурации. Конкретный production deployment и пригодность
среды не доказаны.

## Существующая основа

CRM-S02 (14.10.2026): platform list использует `count/next/previous/results`,
серверные `search`, `status`, `page`, `page_size` (1–100, default20).
Сводка учитывает все Business без прежнего ограничения500 и пакетно собирает
операционные показатели. Счётчик ошибок отражает сохранённые failed-записи
automation/notification/integration/export, а не число текущих аварий сервиса.
Прежний support-actions журнал читается постранично; запись support-note требует
admin/grant/MFA. Обращения apps/support и ADMIN-01/02/03 имеют отдельные правила.
Воспроизводимая локальная проверка: `.venv/Scripts/python.exe scripts/verify_platform_s02.py`
(одноразовая БД, собственные порты, desktop/mobile). Это не live/provider/worker
acceptance; точные результаты — в [checkpoint](../testing/task-state/PRIMARY-SESSION.md#crm-s02-20261014--operational-platform-administration).

Django API, React delivery, Celery workers/beat, health/readiness и platform operations
имеют код/config/scripts. Доступная страница и HTTP 200 не доказывают исправную БД,
очередь, провайдера или источник запущенного сервера. Local/staging/prod разделяют
settings/credentials; production не использует debug/demo defaults.
Долгие exports, notifications и file scans имеют service/task boundaries.
Не весь connector sync автоматически является фоновой очередью.

## Операторские действия и безопасность

Проверять source root/build/profile; не останавливать чужие процессы. Наблюдаемость
охватывает queue lag/retries/stale jobs, heartbeat, DB/Redis/provider/AI cost.
Алерт требует threshold, владельца, действия и recovery. Correlation IDs допустимы,
сообщения клиентов/prompts/файлы/auth headers/secrets в логах — нет.
Platform диагностика не даёт неограниченный доступ к tenant-данным.

Backup включает БД, приватные файлы и доступность ключей; restore проверяется в
отдельной цели с tenant-связями/private download. Rollback не должен молча терять
данные. Принятые29.10 цели — RPO обычных данных≤15 минут и RTO основных операций≤4 часов;
они ещё требуют измерения в целевой среде. Retention, оператор и способ достижения
целей определяются для target; старые предложения не заменяют эти требования.
Working/staging/prod migration/seed/reset требуют точного scope.
При инциденте сначала impact/environment, безопасное evidence и ограничение ущерба;
слепой replay внешних writes не является восстановлением.

## Карта и фактическая проверка

[Settings](../../config/settings.py), [scripts](../../scripts),
[router health/platform](../../config/urls.py),
[platform API](../../frontend/src/api/platform.ts),
[operations UI](../../frontend/src/features/platform/PlatformOperationsPage.tsx),
[testing](../testing/testing.md). UI `/platform/operations` отделён от merchant Settings.
[CI исторической основы 09.10](https://github.com/999MAX20/PlatformaCRM/actions/runs/37832658462)
подтверждает свои backend/frontend jobs, не deployment. Локальные functional reports
сохраняют ограничения среды. Не поднимать PAID_BETA flags ради зелёного readiness.

## Цель и остаток

[R02/R04](../current/roadmap.md): выбранный target, PostgreSQL/Redis recovery,
все task routes, privileged MFA, alerts, backup/restore/rollback, AV/private storage,
оператор и измеренные параметры. BE-GAP-006/007/011 и target FB-008 остаются открыты.
R05/R07 — персонал и финальный кандидат; Git push не означает развёртывание.
09.10 — паспорт основы и условий допуска, без операций с окружениями.

Сверка 16.10: S03 добавил состояния/уведомления, S04 — изолированный реальный
recovery, PLATFORM-OPERATIONS/OVERVIEW/CLINIC-CRM — списки и подробное чтение.
ADMIN-01/02/03 опубликованы; ADMIN-04 реализован и локально проверен, его
публикация/CI — checkpoint. Права и рабочие миграции/почта —
[паспорт доступа](identity-access.md). Полный incident ledger, новые наблюдения,
независимый мониторинг и target R04 остаются; локальные receipts не означают
актуальную проверку запущенных служб 16.10.
