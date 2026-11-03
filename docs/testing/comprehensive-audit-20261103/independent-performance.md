# Independent performance evidence review

04.11.2026; read-only review of existing receipts and harness/source. No additional
load, database or application test runs. Snapshot HEAD0b3348e1 plus preserved WIP.

## Finding supported

The evidence supports a severe Clients list latency/scaling defect on the measured
synthetic datasets. It is not merely a query-count/N+1 finding, SQLite artifact,
HTTP authentication failure or a slow response body download.

- Heavy-client SQLite: same harness/owner/page25,2 warmups+5 measurements at each
  size;25 domain rows:297.435ms median/20SQL;1000:18,412.680ms median/20SQL.
  These are different data volumes, not before/after code revisions.
- Distributed SQLite: a separate single measured request, not a5-sample median:
  17,260.130ms/20SQL/19,384 bytes.1000 added clients each receive one lead/deal/task/
  appointment/conversation; original client retains notes/events. Thus concentration
  of all domain entities on one client is not necessary for the slow SQLite response.
- Exact saved distributed SQL contains large correlated annotated DISTINCT queries:
  slowest four execution timings3.703,3.297,3.297,3.266 seconds (13.563s total),
  each18–19KB and57–60 SELECT occurrences. Their shapes match summary aggregation,
  annotated page selection and repeated annotated counts. Timings identify substantial
  SQL cost; there is no PostgreSQL EXPLAIN/ANALYZE here proving a particular index or
  query-plan fix.
- PostgreSQL real HTTP uses Scale1000 heavy-client fixture, NOT the distributed
  fixture. Authenticated Clients warmup returned HTTP200/19,051 bytes in28,618.226ms
  under a60s diagnostic warmup timeout. Other four routes returned200 in160–467ms.
  This corroborates the issue outside SQLite; it is not a measured PG distributed
  comparison and is one warmup latency, not a latency percentile.
- Both saved HTTP profiles contain50 attempts (10 each on5 routes), at1 and5 client
  threads. Raw http-load.json samples agree with summary: each40HTTP200/10TimeoutError;
  all10 timeouts are Clients, other four routes10 successes each. Original10s request
  deadline remained for measured profiles; overall child resultFAIL is correct.

## Source and reachability

ClientViewSet.list builds a summary from the annotated filtered queryset, executes
super().list (separate pagination count/page), then facets. client_queryset_for_request
adds permission-scoped correlated annotations and DISTINCT; build_client_summary and
build_client_facets aggregate/count these repeatedly. Page25 therefore does not bound
all SQL work to25 clients. No unprotected shortcut or mock selector is used in probes.

The endpoint is a reachable product API: current useClientsWorkspace calls
clientsApi.listFiltered, which issues GET /api/clients/ with business/filter/order/page
parameters. The measured unfiltered owner request exercises its actual list path.
Exact UI-selected ordering/filter variants and role/branch-restricted performance
were not measured. SQL optimization must preserve their existing access semantics.

Fixture construction uses bulk_create, not UI/domain commands. It creates1000 rows
per domain plus1000 extra clients (and the original client), not1000 simultaneous
users;2 tenants are present but the measured owner requests one. These are supported
entity types/relations and plausible accumulated cardinalities, but synthetic state
is not certified as fully reachable through current creation lifecycles: some historical
nullable/default fields and bulk-created times bypass domain validation. This limits
production representativeness; it does not invalidate demonstrated query cost on
persisted relations the read API accepts. Do not describe the fixture as production data.

## Interpretation and priority

P1 is defensible specifically as a readiness blocker for the measured medium-volume
Clients workflow: even a single warmup takes28.6s and every sampled Clients attempt
exceeds10s. P2 is appropriate only if the release explicitly excludes that data envelope
or has an agreed slower SLA; neither exclusion is demonstrated in these receipts.
Do not label this a universal outage or a measured cloud-capacity limit. The exact
readiness classification belongs to the release acceptance decision, not to an
invented backend service-level threshold.

Thread count is client-side; timed-out work continues server-side, including between
profiles. Thus neither profile provides isolated steady-state server concurrency,
maximum RPS or a clean1-versus5 capacity comparison. P95 is deadline-censored attempt
duration;0.420/1.601 attempts/s include failures;0.336/1.280 successful responses/s
are correctly separated. Resource samples cover owned Django processes, excluding
PostgreSQL CPU/RSS. Windows development WSGI, local hardware, synthetic fixture,
query instrumentation (SQLite), finite bursts, no TLS/container/cloud and no full
browser journey are explicit limits. No source-revision baseline establishes when
this performance defect was introduced.

Reviewed receipts: backend/REPORT.md, performance-summary.json,
client-distributed-profile.json, http-load-summary.json, raw http-load.json.
Reviewed harness/source: run_http_load.py, load_fixture.py, audit_performance.py,
audit_client_profile.py, apps/core/tests_b301_performance.py, apps/clients/views.py,
apps/clients/selectors.py, current frontend Clients list API/caller.
