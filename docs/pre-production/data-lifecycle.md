# Импорт, экспорт, дубли, архив и восстановление

Срез `768b2675`, 09.10.2026. Результат — перенести разрешённые данные в CRM,
выгрузить доступные записи и убрать завершённую работу без потери истории.
Контракты: [интеграции](../current/integrations.md), [CRM](../current/crm.md),
[доступ](../current/access.md). Это не универсальный импорт произвольных моделей.

## Реализованные сценарии

ImportJob: CSV/XLSX upload → quarantine/scan → mapping/preview → validation и
duplicate review → подтверждение → результат created/updated/skipped.
Поддержаны clients/leads/deals/sales/catalog; источники sales/catalog нормализуются
существующим connector/event слоем, не создают полную ERP-копию.
Ошибки строк препятствуют подтверждению; бизнес/связи/поля проверяются сервером.
Успешный импорт хранит provenance через sync run и audit. Повтор и частичный
результат нужно оценивать по конкретному режиму, а не обещать общую атомарность
всех импортов и внешних побочных эффектов.

Малый экспорт возвращает CSV; большой создаёт ExportJob/202, polling и private download.
Worker повторно проверяет текущие права/capabilities. Поддержаны entity/report exports
с ограничениями строк/периода. Отключённый модуль или отозванный доступ не обходится
старым заданием. Формульные значения CSV не должны становиться исполняемыми формулами.

## Доступ и восстановление

Merge клиентов имеет preview, сохраняет ledger/связи и архивирует дубль;
подробности в [клиентах](clients.md). Archive критичных объектов сохраняет историю,
restore не является reopen или универсальным undo. Проверяются доменные зависимости
и owner/admin ограничения восстановления по текущему контракту.
Import parsing до clean запрещён. Сбой/зависшее export job видимы как состояние,
а не пустой файл; reports_exports worker и beat нужны для фонового пути.
Рабочую базу не seed/reset ради проверки и не пересоздавать данные при retry вслепую.

## Карта и evidence

[Import/export](../../apps/core/import_export.py), [jobs](../../apps/core/export_jobs.py),
[archive](../../apps/core/archive.py), [tests archive](../../apps/core/tests_archive.py),
[API](../../frontend/src/api/importExport.ts),
[интеграции UI](../../frontend/src/features/integrations/IntegrationsPage.tsx).
API import-jobs/export-jobs и actions; entity UI использует общий API-слой.
Статическая сверка подтверждает наличие слоёв, но не новую runtime-приёмку.
[Аудит подключений](../testing/integrations-functional-review-20261008.md) сохраняет
свои наблюдения/предложения и не является реализацией редизайна.

## Цель и границы

[R01](../current/roadmap.md): D-03/V1-O09 конкретных связей/повторов; R04 — target
worker/storage recovery. Импорт не получает приоритет над ручными изменениями
или automation без правила спорного сценария. 09.10 — паспорт, без импорта/выгрузки данных.
