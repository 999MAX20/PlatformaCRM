# Manual security and supply-chain audit

Snapshot: canonical PlatformaCRM, HEAD0b3348e1ab31121a106badbde830b496ec477aac plus starting-hashes.json WIP. Audit date04.11.2026. No product/config/dependency changes. No external exploit traffic. This is a manual contextual review and isolated checks, not a completed Codex Security scan.

## Tool limitation

Codex Security Deep Scan did not start: `Deep Scan cannot safely start a read-only worker: the parent must provide a managed filesystem permission profile.` No scan ID, findings or clean result was returned. No retry/replacement scan was started. Daybreak advisory returned not_granted; protected outputs may not be displayable. Independent local checks continue under the owner's requested audit scope. Resolving plugin permissions is an environment requirement, not evidence of product security.

## Trust boundaries reviewed

| Boundary | Source evidence / protections | Limit |
| --- | --- | --- |
| Anonymous browser → auth cookies | apps/accounts/csrf.py wraps dispatch with csrf_protect; auth_views.py refresh cookie HttpOnly, controlled secure/samesite/path; token endpoint protected before DRF wrapper | Actual production origins/proxy not supplied; test results attached by backend audit |
| JWT → current identity/session | authentication.py checks auth_epoch and device session; session_security.py revokes under transaction and increments epoch | No live session testing |
| Merchant → tenant/object/field | core/permissions.py delegates tenant resolver and current membership; file_attachments resolves referenced entities in Business and asserts current object permission; ClientSerializer masks notes without authorized actor, including public token API | Manual samples plus full test suite; not a proof every endpoint is vulnerability-free |
| File metadata → private bytes | file_views safe_join, exact attachment lookup, current access, open_clean_attachment; attachment API forbids generic PATCH/DELETE and audits downloads | Actual object-store ACL/AV freshness/production key custody remain unverified |
| Untrusted destination → outbound webhook | integrations/webhooks.py rejects local/private resolved addresses, pins validated address, verifies peer/TLS hostname, revalidates each redirect, caps response bytes and timeout | Does not promise exactly-once external delivery; idempotency header requires receiver cooperation |
| Provider → ingress / provider credentials → egress | webhook views call provider secret verification; YCloud client fixed origin, no redirects, bounded response, ambiguous POST result classification | Sandbox/live provider receipts absent; no real message/payment performed |
| API token → Business | public_api validates hash/expiry/scope; clients queryset token.business; absent actor masks Client.notes by explicit access contract | Actor rights deliberately not inherited; do not misreport as field bypass |
| Web build / image context → secrets | .dockerignore excludes .env*, DB/media/output/dependencies; default connector key is outside checkout under local app data; source pattern scan2333 text files found0 credential-pattern candidates | Pattern scan is not entropy/history/ignored working-data audit; no secret values printed |
| Stand edge → app | compose.stand removes DB/Redis/web published ports; Caddy gate/HTTPS/private-media deny; gate11 tests PASS | No Docker/Linux/live stand run; base compose public ports alone are not proven production exposure |
| Historical mobile actorA → actorB | Actual historical session/queue/replay/client code retains A action after logout then sends it with B Authorization | Independently reproduced using synthetic tokens and fetch capture; no server mutation, not current web tenant bypass |

## Findings and measured checks

- SEC-DEP-01, confirmed dependency-policy gap, P2: combined Python runtime+dev lock audit returned14 advisories in3 packages, all pinned in requirements-dev.txt: filelock3.32.0 (12), msgpack1.2.1 (1), setuptools83.0.0 (1). No direct application usage found in apps/config/scripts searches. Package CVSS is not application exploitability. Local/build/shared cache preconditions need threat-specific evaluation; runtime service exposure is not established. Remediation plan: regenerate dev lock with reviewed compatible fixed releases (audit currently lists filelock4.2.1, msgpack1.2.3, setuptools84.1.0), install deterministically in clean CI, rerun lock/audit/build/tooling checks. No dependencies changed here.
- MOB-H01, confirmed historical client defect, high impact/P1 if native release is reused: pending command belongs to actorA, logout clears only session, actorB's actual HTTP client sends it. Affects immutable73482a3bea7f168113c58d8cb928214c97f032d5. Acceptance: actor+Business-bound queue, account switch cannot replay another actor's command; explicit unknown-result reconciliation, same-actor retry maintains idempotency; API authorization still independently required. Root independent evidence mobile-independent.json complements ui-mobile/mobile-logic-results.json.
- OPS-Q01 independently corroborated: default Celery worker consumes default only; compose defines other workers for integrations/webhooks_outbound, ai, file_scans, but none for notifications/automations/reports_exports. This is a shipped deployment-topology defect/P1; not a claim about any running server. See backend queue-config.log. Acceptance: all named queues have verified consumers and end-to-end due-processing/restart delivery without duplicates.

Commands:

```text
npm audit --prefix frontend --package-lock-only --json
.venv/Scripts/python.exe -m pip_audit --no-deps --disable-pip -r requirements.txt -r requirements-dev.txt --format json --output .../pip-audit.json
.venv/Scripts/python.exe output/comprehensive-audit-20261103/security-manual/scan_snapshot.py
node output/comprehensive-audit-20261103/security-manual/mobile-independent.cjs
node --test deploy/stand-access/gate.test.mjs
```

Results: npm exit0,0 advisories/392 dependency total; pip audit exit1,14 advisories/3 dev packages; snapshot pattern scan2333 text files,0 candidates (3 large/missing skipped); independent historical actor confusion reproduced; stand gate11PASS. Exact raw logs/JSON remain in [local audit output](../../../output/comprehensive-audit-20261103/security-manual/); the reviewed [dependency summary](assets/dependency-summary.json) and [independent mobile receipt](assets/mobile-independent.json) are retained with this report. No installs, paid calls or source edits.

Additional artifact scan: isolated app/widget production bundles and owned top-level
audit logs were inspected with the same credential patterns, without printing matched
values. The first scan covered198 files and found0 candidates. Working logs, ignored
working env/data, repository history and remote secret stores are outside that claim.
Final artifact receipt records the exact checked hashes; this is not an entropy scan
or a guarantee that no secret of an unknown format exists.

The complete isolated backend run executed2752 tests:2698PASS,4FAIL,50SQLite skips.
It includes account/MFA/session recovery, tenant/object/file rights, uploads/ZIP limits,
webhook signatures/replay and AI approval/current-permission suites. Three failures
concern changed test expectations/environment; one exposes work-queue query growth.
The original failed result remains failed; focused and PostgreSQL results are tracked
separately. Tests with mocks do not establish real-model prompt-injection resistance,
production proxy configuration or provider delivery. The independently reproduced
stale-price/duration acceptance in automatic booking is CRM-TERMS01 in the register;
it is not a financial transfer or an asserted arbitrary-code/tenant exploit.

Primary advisory checks: [msgpack](https://github.com/advisories/GHSA-j586-36cw-2gc2), [filelock example](https://github.com/advisories/GHSA-v4x8-3wr5-3wq8), [setuptools](https://github.com/advisories/GHSA-xmj3-9gf7-h52w). Each is tied to package conditions; detailed inventory is dependency-summary.json.

## Production/security acceptance still open

Linux image execution/signals/UID and immutable image provenance; actual HTTPS/origins/cookies/proxy trust; PostgreSQL/Redis/private storage topology; key lifecycle; AV signatures/runtime; queue consumers/alerts; backup restoration and external reconciliation; operator responsibility/24h coverage; actual Yandex environment and conditional legal/region requirements. Root-default Docker image and migration-in-web startup are hardening/release risks requiring measured target validation, not newly proven remote exploits.
