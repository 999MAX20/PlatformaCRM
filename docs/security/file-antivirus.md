# File antivirus and private quarantine

BE-GAP-011, owner-authorized implementation 2026-09-28. This contract concerns
file scanning, not subscription retention, deletion or cloud deployment.
Execution/gates/publication: [PRIMARY-SESSION](../testing/task-state/PRIMARY-SESSION.md).

## Runtime contract

- Every FileAttachment starts `pending`, including pre-existing rows after core
  migration `0011_file_security_scanning`. There is no trusted legacy exemption.
- Quarantine is a persisted state on the existing private storage object; UUID
  keys stay private throughout. No public or signed object URL is serialized.
  Download still requires the original entity/Business access, then a clean scan.
- The worker streams bytes to internal ClamD with INSTREAM. It never sends
  user-controlled filesystem commands/paths or sends files to an external AV SaaS.
  Only exact `stream: OK` releases the file. FOUND blocks it; errors, limits,
  malformed replies, missing files and stale/unavailable signatures fail closed.
- `clean` records bind a SHA-256 and size to the scanned contents. Downloads
  verify a bounded private snapshot against that fingerprint, so replacement
  bytes cannot inherit an earlier verdict. Integrity failure re-quarantines the
  attachment. API and legacy local-media routes share this enforcement. Responses
  use the validated content type and attachment disposition, including renamed files.
- `pending → scanning → clean | infected | error`. A compare-and-swap lease/token
  prevents duplicate workers or stale completions from overwriting a newer result.
  Error retry starts at 30 seconds, backs off to one hour, and never serves the
  file meanwhile. Expired scanning leases are recovered. Infected files are not
  automatically retried, deleted or downloadable; no merchant override marks clean.
- Scan outcome metadata is audited without raw scanner text, contents, credentials
  or storage URLs. API exposes only status/time and a guarded download route.
  Django admin cannot change attachments or scan verdicts directly; attachment
  and import file widgets are excluded so they cannot mint a direct storage URL.
- CRM attachment panels refresh outstanding states and disable preview/download/
  sharing until clean. Conversation attachments also expose scan state. Existing
  rename/history behavior remains. Scanner failures do not disable ordinary CRM.
- CSV/XLSX imports scan the same bounded bytes that are parsed, including preview
  and confirm of old jobs. Infection refuses parsing; scanner failure returns 503
  and can be retried through the existing preview flow. Import source storage URLs
  are write-only. Generated exports are not untrusted uploaded files.

## Personal account avatars — 2026-09-30

The editor sends the original file and optional normalized `x`, `y`, `size`
coordinates. The server scans the original before decoding, applies EXIF
orientation and validates the square crop bounds before normalization. The zoom control and
drag/keyboard positioning preview this crop; no client-side conversion bypasses scanning.

`/api/auth/me/avatar/` is authenticated and always scoped to request.user; it
accepts no target account ID. GET/POST/DELETE never serialize another user's photo.
Uploads are limited to 5 MiB, JPEG/PNG/WebP, one frame and 16 million pixels.
Existing ClamAV scans the original bytes before Pillow decodes them. Scanner
failure returns a retryable 503; blocked/invalid uploads preserve the previous photo.
Only a newly encoded 256x256 JPEG (at most 128 KiB) is stored in UserAvatar;
original bytes, EXIF/GPS and filenames are not retained. This small personal image
is stored in the database and included in its backups, not in public media.
Responses use private/no-store; frontend shares the authenticated image cache
between Account and header. Upload/remove produce audit events without image data.
The accounts.0008_useravatar migration creates only the new table. Local application
was explicitly authorized and backed up; cloud rollout is not implied.

## Deployment configuration

The local Windows activation below was completed on 2026-09-28. Docker/cloud
deployment remains unapplied; its readiness is not implied by the local result.

`CLAMD_HOST`/`CLAMD_PORT` identify a trusted internal daemon only. Defaults are
127.0.0.1:3310; Docker web/file worker override host to `clamav`. No disable flag
silently releases unscanned files. `FILE_SCAN_TIMEOUT_SECONDS=30` bounds each
scanner interaction; `FILE_SCAN_SIGNATURE_MAX_AGE_HOURS=72` rejects an old loaded
database. Run the daemon in UTC so its VERSION database timestamp is comparable.
Application upload size remains the existing 10 MB; this task does not approve
the proposed 25 MB limit or change commercial quotas.

The compose service pins official ClamAV 1.5.4 by image digest, persists signatures,
and runs the image's freshclam updater (12 checks/day). The 3 GB memory cap must
be validated on the target host, including a signature reload. Its local socket
is retained for the official entrypoint startup check and freshclam notification.
The daemon has **no host-published port**:
ClamD TCP has no authentication/encryption. Restrict the network to trusted app/
file workers in the target cloud; never put it behind a public load balancer.
See [official scanning guidance](https://docs.clamav.net/manual/Usage/Scanning.html)
and [INSTREAM protocol](https://docs.clamav.net/manual/Usage/ClamdProtocol.html).

`deploy/clamav/clamd.conf` enforces 10 MB stream/file, 40 MB expanded scan, 20-second
engine time, recursion 16 and 1,000 embedded files; limit hits and encrypted content
are blocking findings because a complete check cannot be established. A blanket
ban on all Office macros/formats remains a separate proposed file policy. Keep daemon limits aligned if the
application limit is explicitly changed. ClamAV protection is not a guarantee
against every malicious document; engine/signature updates remain operational work.

The `celery-files` worker consumes only `file_scans`; the existing beat scheduler
dispatches due batches every 15 seconds. Both must run. Pending rows are the
durable source of truth, so missed dispatches/restarts do not discard uploads.
The default compose beat profile must be enabled in an authorized deployment.

## Readiness and rollout

1. Prepare the private storage and isolated scanner/worker/beat configuration.
   Do not expose `/media` or the bucket publicly. Any old external source-file URLs
   from before this change must expire/be revoked before treating quarantine as
   fully enforced in a previously deployed environment.
2. With an explicitly authorized target, back up and apply the new migration.
   Existing files become pending and temporarily unavailable until processed;
   communicate this rollout window and size the backlog before a pilot cutover.
3. Run `python manage.py file_antivirus` for actual loaded-signature readiness and
   aggregate state counts. It fails safely if the scanner/database is unavailable.
4. Start the dedicated worker and beat. `python manage.py file_antivirus --process
   --limit 10` is an operator recovery alternative that **mutates the target DB**;
   use only with the target authorization. Do not run it against the working DB
   merely to test code. Existing infected files require investigation; no clean override.
5. Exercise a synthetic clean file, harmless standard EICAR test, scanner outage,
   recovery and cross-tenant download denial. Test both upload and actual download,
   plus CSV/XLSX refusal/recovery. Monitor oldest pending/scanning age and error
   counts along with this readiness command; a listening port is insufficient.
6. If scanner/worker fails, restore service and allow due retries. Do not bypass
   quarantine. Rollback must retain download guards and scan state; reverting to
   the old unguarded download code would reopen blocked files.

## Local Windows activation — 2026-09-28

Owner selected the local computer explicitly. Only `core.0011_file_security_scanning`
was applied to canonical `db.sqlite3`, after an SQLite backup with integrity check
and a CRC-checked archive of `media/`. Backup is in the ignored local directory
`output/local-file-antivirus/backups/20260928T184440Z`. There were zero attachment
rows; 81 media files were backed up without importing them into the CRM.

Machine-specific runtime lives in `output/local-file-antivirus/`: verified ClamAV
1.5.4 binaries, signatures, configs, logs, local Python dependencies and `runtime.py`.
Keep this directory: it is active runtime data, not disposable test output.
It is excluded from Git and is not a portable installation or cloud deployment.

The hidden supervisor starts ClamD on **127.0.0.1:3310**, freshclam (12 checks/day),
one Celery solo worker and a beat with **only** the file scan schedule (15 seconds).
An isolated filesystem broker replaces Redis for these local processes only;
application `.env`, its broker and unrelated jobs are unchanged. The supervisor
checks its child processes and restarts a failed child after 15 seconds. It holds
a single-instance lock and refuses a different DB, cloud environment or an occupied
scanner port. This Windows development arrangement does not certify Redis/Linux
production behavior.

From PowerShell in `C:\Users\user\Desktop\PlatformaCRM`:

```powershell
# Read-only state / scanner and database readiness
.\.venv\Scripts\python.exe output/local-file-antivirus/runtime.py status
.\.venv\Scripts\python.exe manage.py file_antivirus

# Start when stopped (for example, after reboot)
.\output\local-file-antivirus\start.ps1

# Stop only this supervisor and its owned processes
.\.venv\Scripts\python.exe output/local-file-antivirus/runtime.py stop
```

No Windows boot/logon task or system service was installed. After reboot, start
the local runtime with the command above. A fresh state heartbeat plus successful
`file_antivirus` and recent successful tasks in `worker.log` are required; an old
state file alone does not prove readiness. Stop/restart was exercised successfully.
If these processes are stopped, files remain quarantined until service recovers.

Evidence: `output/local-file-antivirus/acceptance.log` and
`live-pipeline-result.json` prove clean/EICAR API download behavior, scanner outage,
worker restart and duplicate/expired-lease recovery in a disposable DB against
this real scanner. Working DB has no synthetic fixtures; actual beat dispatch and
worker completion were observed with zero pending rows. `/health/` and `/health/db/`
on the existing local backend returned OK. No other user's processes were stopped.

Unrelated `scheduling.0008` and `tasks.0010` remain unapplied. Their rollout,
Yandex Cloud acceptance and retention are separate remaining work, not a claim
that the entire local CRM schema or pilot is ready.

## Verification boundary

Unit tests control scanner failures/protocols and storage changes. Browser gates
run a clearly isolated fake ClamD plus scan loop in `frontend/e2e/serve-isolated.py`,
which requires the quality-gate flag and a disposable DB under the OS temp folder.
The production adapter still executes its socket protocol; the fake accepts only
test fixtures. It is not shipped as a production fallback or evidence of detection.
Real-engine evidence uses the official Windows ClamAV distribution and freshly
downloaded signatures in ignored output; exact results belong in the checkpoint.
Docker/cloud deployment, retention and real customer data remain separate gates.
The working-DB migration was separately authorized and verified in the local
activation above; isolated test PASS alone would not establish that result.
