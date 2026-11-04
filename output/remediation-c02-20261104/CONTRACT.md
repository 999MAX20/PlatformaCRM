# C02 / TEAM-ANALYTICS

Owner: continue next cycle after C01. Implementation/code gap; no push/merge/deploy.
Canonical PlatformaCRM, codex/ui-testing-toolkit, base704d4663729e288be6c3c8c3ee4897f15031e18a.
233 foreign WIP entries retained. businesses/views.py clean; analytics WIP untouched.
Result: team/performance Lead counts/status/rates/loss reasons intersect current
LEADS VIEW scope and enabled capability before aggregation, retaining report membership
and period/source filters. Existing zero/empty denial contract; no new permissions.
Reuse access.scope_queryset and capabilities.resource_is_enabled. Other source metrics,
UI, lifecycle, money, schema, notifications/BusinessEvent/AI changes are out of scope.
Risk: security projection within one tenant; preserve useful allowed metrics and report
membership boundaries. Tests first: denied/module-off/own/team/business, another Business,
analytics denial/inactive membership and restoration; baseline failure then focused PASS.
Completion: businesses access and core performance dependency tests, isolated system/
migration drift; source/docs/link/range hygiene. No app build/full-E2E or PG concurrency:
read-only queryset change, no frontend or transaction mutation. Dev remains off.
No working DB writes or external traffic; isolated_runtime + guarded bootstrap.
