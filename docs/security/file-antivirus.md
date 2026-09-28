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

## Deployment configuration (not applied to a working environment)

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

## Verification boundary

Unit tests control scanner failures/protocols and storage changes. Browser gates
run a clearly isolated fake ClamD plus scan loop in `frontend/e2e/serve-isolated.py`,
which requires the quality-gate flag and a disposable DB under the OS temp folder.
The production adapter still executes its socket protocol; the fake accepts only
test fixtures. It is not shipped as a production fallback or evidence of detection.
Real-engine evidence uses the official Windows ClamAV distribution and freshly
downloaded signatures in ignored output; exact results belong in the checkpoint.
Docker/cloud deployment, working-DB migration, retention and real customer data
are separate gates and are not claimed by local PASS.
