# Приватные файлы, карантин и антивирус

Срез `768b2675`, 09.10.2026. Сотрудник прикладывает файл к доступной сущности;
доступ открывается после успешной проверки. Контракты — [operations](../current/operations.md)
и [access](../current/access.md). Локальный AV работает; cloud-допуск не подтверждён.

## Реализованный процесс

FileAttachment хранит Business/entity, storage reference, size и scan state:
pending → scanning → clean/infected/error. ClamAV INSTREAM должен вернуть корректный
OK; timeout/неизвестный ответ не разрешают файл. До clean запрещены download,
использование и parsing импорта. Merchant override «считать чистым» отсутствует.
Scan lease/token и fingerprint защищают от устаревшего результата; download
проверяет checksum/size и выдаёт проверенный snapshot, не заменённые байты.

Avatar — отдельный pipeline request.user: исходник JPEG/PNG/WebP до 5MiB,
16M pixels/один frame, scan оригинала, нормализация до JPEG 256px/128KiB без EXIF.
Общий upload default 10MB не заменён старым предложением 25MB.

## Права и восстановление

Чтение/загрузка требуют Business/entity permissions; даже platform доступ не обходит
quarantine. Raw storage URL не заменяет авторизованный download. Scan error сохраняет
безопасный код и retry/backoff; stale lease подбирается due processing.
Изменение целостности возвращает файл в закрытое состояние. Нужны file_scans worker,
beat и актуальные signatures; ClamAV 3310 не публикуется наружу.
Локальный runtime `output/local-file-antivirus` — работающий сервис, не мусор для удаления.

## Код и доказательства

[Scanning](../../apps/core/file_scanning.py), [antivirus](../../apps/core/antivirus.py),
[entity access](../../apps/core/file_attachments.py), [models](../../apps/core/models.py),
[API](../../frontend/src/api/fileAttachments.ts), [private routes](../../config/urls.py).
FileAttachment API и private download используются CRM-карточками; аватар — аккаунтом.
[Operations](../current/operations.md) сохраняет точные параметры и происхождение
локального evidence. Этот паспорт подтверждает статическую карту, новых AV-тестов нет.

## Цель и границы

[R04](../current/roadmap.md), BE-GAP-011: private object storage, cleanup/retention,
cap и backup/restore с ключами, scanner outage/recovery и наблюдаемость на target.
Текущий локальный PASS не доказывает облачное хранение или автозапуск Windows.
09.10 — паспорт без загрузки/сканирования пользовательских файлов.
