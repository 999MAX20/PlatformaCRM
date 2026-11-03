# Backend, concurrency, operations and performance audit

Snapshot: canonical PlatformaCRM dirty checkout on HEAD0b3348e1; original product/config/dependency changes retained. Diagnostics only. All data synthetic, disposable databases/Redis/file roots; provider sockets blocked except loopback, dotenv disabled, credential keys synthetic. Windows Python3.12.14/Django5.2.17/DRF3.18.3/Celery5.6.3/psycopg3.3.4/native PostgreSQL17.10/Redis7.4.9. These are not Linux Docker or Yandex production receipts.

## Verification completed

| Boundary | Command or evidence | Result |
|---|---|---|
| System check | `.venv/Scripts/python.exe output/comprehensive-audit-20261103/backend/run_backend.py system check` | PASS; system.json/log |
| Migration drift | same runner migration-drift makemigrations --check --dry-run | PASS; migration-drift.json/log. No working DB migrations |
| All discovered Django tests | same runner default; full-backend.json/log | 2752 discovered:2698PASS,4FAIL,50SQLite skips;1809.4sec,exit1 |
| Independently reproduced failures | focused-failures.json/log |3existingfailures reproduce; additional AI semantic observationPASS:2named suggestions,2logs,0tasks |
| Production W018 fixture | production-fixture-comparison.json | Existing expected missingkeywarning fails with valid synthetic auditkey; passes with local-auditkey sentinel. Guard behavior works; test input assumption, not absence of guard |
| PG-only concurrency | postgres-concurrency-initial.json/log |50assertionsPASS in97.122sec, teardownFAIL due2open sessions blocking DROPtest_audit. Initial gate not green; rerun PASS: 50 tests, exit0,150.33sec including setup; see postgres-concurrency.json/log |
| Automatic booking | booking-contract.log/json |9existingcontrolsPASS; added accepted R01 contract checksFAIL: successful booking lacks responsible_user_id/source_conversation_id. Current manual record path explicitly separate |
| Offer terms after edit | stale-terms.json/log |4diagnostics,2controlsPASS/2contractFAIL; original100/30offer accepted after price200 or duration60 edit on no-branchpath |

## Findings and classifications

- **OPS-QUEUE (P1, high confidence, shipped topology):** docker-compose.yml:32 default worker consumes only default; workers at45/60/99 consume integrations/webhooks_outbound,ai,file_scans. Routed notifications,automations,reports_exports have no consumers. queue-config.json/log records actual Celery queue selection. Consequence if deployed as shipped: reminders, automation and async exports remain pending. No live outage claimed; Render example has different subscriptions. Remedy: explicit consumers/health/backlog acceptance for all routed queues; verify real non-eager flow, replay and downtime recovery.
- **CRM-BOOKING (P1 accepted requirement gap, high confidence):** apps/conversations/booking.py74,105-118,219 legacy automatic path does not populate record responsible/source fields. Manual R01 closure did not authorize pretending this integration was complete. Reproducer booking-contract.log; no product fixes. Remedy integrate approved record command with assignment/provenance contract and tenant/invalid/idempotent checks.
- **CRM-TERMS01 (P1 accepted-offer impact priority, high confidence):** no-branch automatic offers do not bind accepted price/duration to offered terms. User sees100/30, confirmation can create200/30or100/60 after service edit. Independent control/reproducer recorded root and backend stale-terms.log. Remedy carry version/terms fingerprint and reject/reoffer stale offer under accepted policy.
- **PERF-WORKQUEUES (P2, high confidence, measured):** existing B301 limit10legacy workqueues488queries vs58budget. Other sampled surfaces preceding failure remained within their assertions; do not generalize legacy dashboard to current appointments workflow. Scaling and concurrent measurements below. Remedy use shared projections/permission checks/batched related fetches only after query shape evidence; preserve tenant and role boundaries.
- **TEST-S04 (P2 verification tooling, high confidence):** shipped scripts/recovery_scenarios.py27 inserts unsupported `_s04_hold` config; strict validation correctly rejects before crashwindow. Existing invaliduser999999 retry fixture also conflicts with upfrontvalidation. Initial real workerrestart/wait/duplicatePASS then helperFAIL retained recovery-initial*. Audit adapts only output copies to allowedtitle marker and validownerassignment with transient execution injection. Any adaptedPASS will not make shipped helper green.
- **TEST-AI-SUGGESTIONS (P2 gate drift):** apps/ai_core/tests.py554 expects>=3; actual intentionally2 summarize_conversation/create_task, log2, execute0. No identified business requirement for3; semantic guard observationPASS. Existing assertion remainsFAIL, no test weakened.
- **TEST-BELL (P2 gate drift):** apps/core/tests_mixed_membership_scope.py49 calls bell withoutbusiness for actorwith2businesses and expects mergedfeed. Current selected_personal_business requires onebusiness (views.py33-43), returning400. Current UI specifiesbusiness and recipient projection; old mixedfeed expectation needs reconciliation, not silent weakening.
- **TEST-PG-CLEANUP (P2 verification hygiene):** initial50concurrencyassertionspassed but2testconnections blockedDROP; own wrapper must explicitly close only verified disposableDB sessions. No servicePG was stopped. Initial log preserved.

## Evidence boundaries

Full suite failures are visible; no universal green/security/production claim. SQLite skip coverage must be read with separate PostgreSQL results. Native Windows worker uses solo; no prefork/Linux/container certification. No real messaging/payment/AI provider traffic. No working DB read/write, migration, seed/reset, source/config/dependency edits, push or deploy by this subtask. Historical native/mobile and crossproject requirements belong to other audit reports.

All executable scoped backend checks are complete. Product failures remain findings; initial harness failures and corrected diagnostic receipts are retained. No product fixes or publication performed.


## Real recovery completed

`.venv/Scripts/python.exe output/comprehensive-audit-20261103/backend/run_recovery.py full`: adapted diagnostic PASS, exit0,242.16seconds; original fixture failure retained separately. Real PostgreSQL17/Redis7.4.9/Celerysolo, ClamAV1.5.4/daily28173 signed03Nov06:27UTC. Existing installed signatures untouched; updated own signature copy verified.

Assertions passed: worker restart and wait resume; duplicate dispatch; worker killed inside transaction followed by stale claim recovery and exactly-once durable effects; retry/cancel and invalid role/tenant denial; transient failure resume without duplicating prior action; actual reminder queue replay; actual export queue/replay/revokedaccess; file scanner initially unavailable, locked download423, queued retry toclean, SHA256 integrity; standard EICAR in-memory detection; harmless customsignature quarantine and423; other-tenant404; cleanCSV upload201 -> preview200 -> confirm200(1row), duplicateconfirm400, customsignatureCSV400, scanneroutage503 -> previewretry200 -> confirm200. Real browser counterpart belongs to ui-mobile/import-export-av-result.json and its screenshots.

After deliberate own Redis loss, actual beat recovered DB-backed pending run, produced exactly1task and service sampling rows. PostgreSQL dump and restore to second disposableDB, private/media copies and synthetic key restore passed data counts, content hashes, restored tenant/access/quarantine and wrong-key protection. All owned recovery runtime processes closed normally, PostgreSQL shutdown log confirms. This is a small synthetic recovery drill, not operational RPO15m/RTO4h or cloud disaster proof. Shipped unadapted helper remains failing TEST-S04.


## PostgreSQL rerun and cleanup

Same 20 labels / 50 tests rerun without modifying application/test assertions. Django `--keepdb` deferred removal until the child test process exited. Wrapper verified server `SHOW data_directory` equals its exact temporary path and `SHOW port` equals allocated loopback port, checked/terminated only connections to `test_audit`, then dropped that disposable database. On this run no sessions remained at cleanup. Result50PASS, process exit0; wrapper elapsed150.33seconds before cleanup, normal PostgreSQL shutdown also confirmed. Initial cleanup failure remains in initial receipt; no service PostgreSQL process was stopped. All 50 original SQLite skips now have separate native PG assertions; this does not turn the full SQLite run with4failures green.

## Measured scaling

Synthetic existing B301 distribution:25or1000 leads/deals/tasks/appointments/conversations linked to one heavy client;25or1000 additional clients;2tenants. In-process SQLite, owner, page25,2warmups+5samples; not cloud sizing. Workqueue counters are corrected per-request captures; original legacy50lastcount64 was the9000-query logging cap, not application cache.

| Surface |25rows median ms / SQL|1000rows median ms / SQL|
|---|---:|---:|
|clients|297.435 / 20|18412.68 / 20|
|records|19.255 / 10|14.51 / 10|
|calendar|16.64 / 9|17.239 / 9|
|inbox|24.218 / 11|42.573 / 11|
|tasks|41.43 / 9|93.371 / 9|
|work-queues-appointments-10|191.477 / 381|205.262 / 387|
|work-queues-appointments-50|529.354 / 761|964.014 / 1737|
|work-queues-legacy-10|245.168 / 482|427.536 / 488|
|work-queues-50|587.489 / 1025|1122.367 / 2234|
|owner-dashboard|29.642 / 65|50.281 / 65|
|analytics-report|39.45 / 66|538.289 / 66|
|client-card|185.004 / 184|466.303 / 184|

Client list18.4seconds median at1000fixture withonly20queries is a separate expensive-query finding, not workqueue N+1. Distributed-client and PostgreSQL comparisons follow below.
Client card184SQL on both datasets (budget40 in existing B301) is a separately confirmed N+1:51Businessfetches+50Clientfetches+25Dealfetches. `apps/core/crm_cards.py:509` timeline queryset lacks eager business/client relations needed by the serializer at573; conversations464omitdeal. Fix should retain projection and actor permissions.
The targeted repeat ran two queue testsPASS but its command exit1 included a typo in distributedtest discovery label; preserved performance-focused.log. Distributedtest rerun uses corrected dotted label; no application assertion failed in these profiles.


## Client list SQL follow-up

Corrected dotted-label focused command `run_backend.py client-distributed test output.comprehensive-audit-20261103.backend.audit_client_profile --noinput -v 2` PASS,1test,58.49sec including migrations. Redistributing1000 domain rows across1000 clients (each1lead/deal/task/appointment/conversation) still yields17,260ms/20SQL/19,384-bytebody. Thus this SQLite finding is not merely the single heavy client distribution. Largest SQL execution times3.703sec (annotated distinct count),3.297sec (summaryaggregate),3.297sec (annotatedlist),3.266sec (anotherannotatedcount). `apps/clients/views.py:37-47` builds summary then list then facets; selectors.py306-326 aggregates/counts expensive annotations repeatedly. `client-distributed-profile.json` holds top4 exact synthetic SQL and timings. Proposed optimization: keep business/role/quickfilter semantics while reusing lean filtered IDs and separating only needed annotations for summary/count/page; prove both distributions and production PostgreSQL. PostgreSQL HTTP comparison follows below.


## PostgreSQL HTTP follow-up

First bounded HTTP attempt failed warmup with10second timeout; initial harness did not serialize per-route statuses and INFO was disabled, so initial failure alone is not attributed. Preserved `http-load-initial*`. Diagnostic repeat serializes every warmup and allows60seconds only there: ClientsHTTP200 in28,618.226ms (19,051bytes), Records159.722ms,Inbox163.878ms,appointments workqueue467.206ms,owner dashboard264.722ms. This PostgreSQL result confirms client list slowness beyond SQLite. Load profiles kept original10secondtimeout and recorded failures. Thread concurrency is client-side: timed-out HTTP requests may continue on development server, so this is burst/error observation, not precise sustainable-server concurrency/capacity. No PostgreSQL configuration/index changes made.


## Final bounded HTTP result

Diagnostic complete, resultFAIL (deadlines not relaxed),250.28seconds overall. Both profiles made50requests across5routes; each yielded40HTTP200 and10TimeoutError, all10timeouts on Clients. No response error on Records,Inbox,appointments workqueues or ownerdashboard in these samples.

| Client threads | Elapsed seconds | Attempt completions/sec | Successful responses/sec | Errors | Median attempt ms | P95attempt ms | Django peak sampled RSS | Django CPU seconds |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
|1|119.087|0.42|0.336|10/50|417.513|10012.374|138514432 bytes|2.609375|
|5|31.238|1.601|1.28|10/50|664.003|10014.014|145842176 bytes|10.015625|

P95 values are censored at the10second client deadline, not server completion latency. Timed-out requests can continue server-side (one logged57563ms before200), so this is not a sustainable throughput claim or precise server concurrency measurement. The reported0.420/1.601attempts/sec include timeouts; successful response throughput is0.336/1.280resp/sec. Resources cover the owned Django process tree only, not PostgreSQLCPU/RSS; an attempted late optional PGsample found the already-cleaned directory and produced no measurement. No additional load run was started after cleanup. No network/TLS/container/cloud sizing conclusion.

Cleanup: owned development server tree stopped, own Redis shut down, own PostgreSQL normal shutdown confirmed in http-load-runtime.log. Disposable cluster directory removed by isolated runtime. All backend test/recovery/load sessions are finished. Safe compact receipts: full-suite-coverage.json,postgres-concurrency.json,recovery-full.json,performance-summary.json,client-distributed-profile.json,http-load-summary.json; original failure logs remain separately named. Do not publish signatureDBs,disposableDBs,runtimekeys or raw runtime environments.


## Canonical register and durable receipts

OPS-QUEUE = OPS-Q01; CRM-BOOKING = REQ03; PERF-WORKQUEUES = PERF01; TEST-S04 = VERIFY02; test expectation findings are grouped under VERIFY01 in the [single register](findings.md). Clients performance is PERF02 (P1 in the measured readiness boundary), client-card N+1 is PERF03. The separate real creation-event probe is CRM-EVENT01; see [independent domain review](independent-review.md) and [independent performance review](independent-performance.md).

[Performance summary](assets/performance-summary.json), [HTTP summary](assets/http-load-summary.json), [full-suite coverage](assets/full-suite-coverage.json), [PG final](assets/postgres-concurrency.json), [recovery final](assets/recovery-full.json). Raw logs/diagnostics remain in [local backend output](../../../output/comprehensive-audit-20261103/backend/). No runtime database, key, environment or signatures database is committed.
