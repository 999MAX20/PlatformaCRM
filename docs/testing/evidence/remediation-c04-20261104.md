# C04 — безопасный состав исходного ZIP-архива

**Закрыто локально**, 04.11.2026; ARCHIVE-SENSITIVE-ARTIFACTS. C05 не начат.
Canonical `C:/Users/user/Desktop/PlatformaCRM`, `codex/ui-testing-toolkit`,
base`6a0dab4cce85b839c0a2a4a44c0f87a98c10c306` + сохранённый чужой WIP.
Pre-edit contract: `output/remediation-c04-20261104/CONTRACT.md`.

## Изменение

`scripts/make_clean_archive.sh` сохраняет rsync selection и префикс `zani/`.
Исключены output/backup/log/private-media/browser-profile/auth directories,
вложенные env/SQLite/DB/dump/bak, storage-state/session/cookies/HAR artifacts;
env/DB extensions распознаются также при другом регистре. Прежние исключения
dependencies/build/cache/media остаются. Разрешённые `.env.*.example` шаблоны,
исходники, docs и lockfile сохраняются. Symlinks/devices/special files не копируются.

Упаковка теперь выполняется настоящим Python standard-library ZIP archiver:
`python3 -m zipfile`, вместо отсутствующего Info-ZIP executable. Это поддерживаемая
зависимость самого helper, не тестовый shim. Нужны Bash, rsync, Python3 в Linux/WSL;
default `zani-clean.zip`, flat basename `.zip`, root layout сохранены. Имя с путём,
ведущей точкой/дефисом, destination symlink/directory отклоняется до записи.
Предыдущий архив не удаляется перед подготовкой; при ошибке compression сохраняется.
Helper закреплён с LF через точный `.gitattributes` path, без изменения других файлов.

Это source package, не backup/export рабочей среды: runtime output/evidence могут
не входить, даже если docs на них ссылаются. Фильтры не обнаруживают произвольные
секреты, спрятанные в обычном исходнике/разрешённом шаблоне. Перед распространением
по-прежнему нужен review предназначенных файлов; этот цикл ничего не распространяет.

## Доказательства

Исходный helper был чистым и совпал SHA256 с retained audit reproduction:
`6fd264bbfce5f7042125e11982389bdeefc66629c5ee5e6fed6d93ee8476ff21`.
Повторный запуск старого zip shim не выполнялся; reused baseline selection evidence:
`output/full-audit-20261104/archive-probe.json` (его native zip/CRLF limits сохранены).

Команда текущей проверки:

```powershell
wsl.exe --exec python3 /mnt/c/Users/user/Desktop/PlatformaCRM/scripts/tests/test_clean_archive.py -v
```

Среда WSL: Python3.14.4, rsync3.4.1, настоящий Bash/Python zipfile. Из рабочего
checkout в уникальный `/tmp/crm-c04-archive-*` fixture копируется только код helper;
остальные файлы и все sensitive markers синтетические. Рабочий архив не создавался.

Финально **7 tests PASS**:

- ZIP открывается реальным reader, CRC PASS; exact9-file manifest и содержимое
  побайтно равны expected source/docs/templates/lockfile, Unicode/пробелы сохранены;
  все заданные вложенные sensitive fixtures и marker отсутствуют.
- Внешние/directory/broken symlinks и FIFO отсутствуют; внешний marker неизменен.
- Плохие имена и destination link/directory дают именно ожидаемую ошибку guard.
- Принудительный compression exit17 сохраняет предыдущий архив и очищает temp.
- Повторная сборка не включает предыдущий ZIP; `bash -n` и отсутствие CRLF PASS.

Первый прогон после правки:5 FAIL из7 из-за прежних CRLF; исходный log сохранён.
После явной нормализации canonical helper в LF — focused7 PASS. Затем guards
усилены assertions на конкретные ошибки, добавлены case-variant fixtures и final7 PASS.
`completion.log` содержит реальный manifest, отдельная копия —
`verified-archive-manifest.json`. Точные log.gz и SHA256 входят в локальный пакет.

Backend/DB/browser/build/install/live/release suites не запускались: packaging-only
scope без product/schema/API изменений. Все synthetic temporary trees очищены.
WorkingDB hash неизменна; dev8000/5173 off. Исторические аудиты не переписаны.

## Документы и остаток

Operations contract/passport, README setup, testing command, C04 plan row,
STATUS/checkpoint/registry обновлены. Access/CRM/AI/frontend contracts не меняются:
их правила и workflows не затронуты. Notification/BusinessEvent/permission effects нет.
Код/доказательства/среда/решения владельца C04 без остатка. Только собственный
локальный commit; без push/merge/deploy/newCI. Чужой WIP сохранён.
SHA/paths/checks: `output/remediation-c04-20261104/final-validation.json`.
Следующий отдельный цикл — C05.
