# DB-MAINTENANCE-20261106

Owner scope: backup of local CRM DB, branch migration, prevention of duplicate
general working hours, expired-token cleanup, daily scheduling and verification.
Root: `C:/Users/user/Desktop/PlatformaCRM`; branch `codex/ui-testing-toolkit`.
Starting HEAD: `66101d509cb7642b2928275e48c4b64354abf07b`. Evidence covers the
dirty checkout, including pre-existing branch work, not a clean published candidate.

## Local result

- Backup: `output/db-maintenance-20261106/db-before-20261106T135543Z.sqlite3`,
  8,302,592 bytes, SHA256
  `ee151277b890b11936559d77c24eea0b4789b8fe7ba272fd0646bec2af017e59`.
  SQLite online backup API, integrity and FK checks passed. Restored into an
  independent in-memory DB; integrity and all 152 table counts matched. This
  private working-data backup is ignored and must not be staged/published.
- Applied only branches0003 and scheduling0012 to local `db.sqlite3`.
  Branches increased1->16, all16 businesses have a location, ORM reads succeed.
  Migration records189->191, no pending migrations. Full contents of the other
  150 tables matched the backup immediately after migration.
- Conditional unique `(business, weekday)` where resource IS NULL prevents
  duplicate general schedules; per-resource uniqueness remains. Serializer
  savepoints convert stale-validation duplicate writes to validation errors and
  roll back failed writes. Pre-existing duplicates stop migration without deletion.
- Removed3552 expired outstanding tokens and2987 matching blacklist rows.
  Remaining715 tokens and711 revocations exactly matched backup values; zero
  expired tokens remained. Other148 tables matched the backup after cleanup.
- Celery task `accounts.flush_expired_tokens` uses the existing SimpleJWT command
  `flushexpiredtokens`; Beat schedules it every86400 seconds on queue `default`.
  Deployed environments need their own running Beat/worker. No Beat was started.
- Windows task `PlatformaCRM-Local-ExpiredTokens`: daily12:00 Windows local time
  (UTC+05:00 here), current-user interactive principal, limited privileges,
  StartWhenAvailable, IgnoreNew, ten-minute limit, three ten-minute retries.
  Hidden pythonw runs `scripts/cleanup_local_tokens.py`; it rejects production,
  non-SQLite, another DB path and a missing DB. Machine must be on and user logged
  in; StartWhenAvailable handles missed runs. Two explicit launches returned0,
  repeat cleanup had no extra data effect. Next run readback: 07.11.2026 12:00+05.
  Log: `output/local-db-maintenance/tokens.log`; XML export in the task output.

## Verification

Used existing `.venv/Scripts/python.exe` and `scripts.codex_verify.isolated_runtime`.
All tests used disposable DBs, no installs or working-DB synthetic fixtures.

| Command / boundary | Result |
| --- | --- |
| `manage.py check` | PASS |
| `manage.py makemigrations --check --dry-run` | PASS, no drift |
| `manage.py test apps.accounts.tests_token_cleanup -v 2` | 4 PASS |
| `manage.py test apps.scheduling.tests_working_hours_integrity apps.scheduling.tests apps.branches.tests_single_location apps.branches.tests_initial_location_migration apps.accounts.tests_token_cleanup apps.accounts.tests.AuthSecurityBaselineTests --noinput -v 2` | SQLite101 PASS |
| `manage.py test apps.scheduling.tests_working_hours_integrity apps.scheduling.tests_working_hours_concurrency apps.accounts.tests_token_cleanup apps.branches.tests_initial_location_migration --noinput -v 2` | Disposable PostgreSQL17,12 PASS |
| Forward/reverse migrations and existing-duplicate migration failure | SQLite and PostgreSQL PASS |
| Concurrent general schedule inserts | One created, one rejected, one persisted row |
| Schedule API | Create201, duplicate400, foreign-business403; existing preset/bulk/availability PASS |
| Token cleanup | Live refresh remains usable, live revoked refresh denied, repeat safe |
| Working SQLite integrity/FK before/after | `ok`, zero violations |
| Windows task launch/repeat | exit0, success log, next execution read back |

Raw evidence: `output/db-maintenance-20261106/` (starting status/hashes, backup.json,
working-migrations.json/log, cleanup-result.json, completion.log, postgres.log).
No full E2E/frontend suite: backend integrity/local maintenance scope, affected
API and auth covered above. No production migration, cleanup or deployment.

## Corrected attempts and boundaries

Initial migration numbering conflicted with an existing graph leaf; isolated
startup caught it before working mutations. Corrected to0012 dependent on0011.
Initial test fixture duplicated empty user emails; assigned distinct synthetic
emails. Final suites pass. PostgreSQL tests exited0; Windows log-display encoding
failed afterward. Explicit readback confirmed12/OK and owned cluster teardown.
Initial cleanup readback assumed id was first physical column; corrected to named
id columns and reran token/full-table comparisons. No product assertion weakened.

Requested local code, backup, migrations, cleanup and scheduler proof are complete.
Pre-existing branch migration is reused, not authored here. Production is outside
scope. Publication requires a safe outgoing range: current branch contains other
writers' unpublished commits and diverges from origin/main. No force-push,
unrelated staging or history integration is authorized by this maintenance task.
