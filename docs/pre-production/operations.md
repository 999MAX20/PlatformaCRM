# Эксплуатация и допуск окружения

Срез `768b2675`, 09.10.2026. Пользовательский результат — работающая CRM с
восстановлением после отказа; операционный владелец должен уметь обнаружить и
устранить проблему. [Operations contract](../current/operations.md) определяет требования.
Yandex Cloud выбран как направление, конкретный production deployment не доказан.

## Существующая основа

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
данные. RPO/RTO/retention и оператор выбираются для target, старые числовые предложения
не становятся нормой. Working/staging/prod migration/seed/reset требуют точного scope.
При инциденте сначала impact/environment, безопасное evidence и ограничение ущерба;
слепой replay внешних writes не является восстановлением.

## Карта и фактическая проверка

[Settings](../../config/settings.py), [scripts](../../scripts),
[router health/platform](../../config/urls.py),
[platform API](../../frontend/src/api/platform.ts),
[operations UI](../../frontend/src/features/platform/PlatformOperationsPage.tsx),
[testing](../testing/testing.md). UI `/platform/operations` отделён от merchant Settings.
[CI текущей версии](https://github.com/999MAX20/PlatformaCRM/actions/runs/37832658462)
подтверждает свои backend/frontend jobs, не deployment. Локальные functional reports
сохраняют ограничения среды. Не поднимать PAID_BETA flags ради зелёного readiness.

## Цель и остаток

[R02/R04](../current/roadmap.md): выбранный target, PostgreSQL/Redis recovery,
все task routes, privileged MFA, alerts, backup/restore/rollback, AV/private storage,
оператор и измеренные параметры. BE-GAP-006/007/011 и target FB-008 остаются открыты.
R05/R07 — персонал и финальный кандидат; Git push не означает развёртывание.
09.10 — паспорт основы и условий допуска, без операций с окружениями.
