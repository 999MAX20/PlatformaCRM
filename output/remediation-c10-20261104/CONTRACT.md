# C10 — renewal-safe idempotency cleanup

Owner «продолжаем» authorizes C10 IDEMPOTENCY-PRUNE only, not C11.
Implementation/code gap; canonical PlatformaCRM/current codex/ui-testing-toolkit,
base fa8a12b2c964cec98078dba77dfc9a8f10e4ac0d,233 foreign WIP entries retained.
Target core/idempotency.py clean. Reuse current receipt model, bounded prune and
command begin/run/replay; no new model/API/permission or retention policy.
Risk: cleanup races renewal and destroys replay protection, allowing duplicate work.
Recheck expiry at deletion with same cutoff; retain limit/order/return semantics.
Focused BEFORE/AFTER deterministic select→real renew/run→delete, expired control,
boundary/limit and replay preservation. Real PG connections/race; affected command
and representative record idempotency suites, system/migration-drift at completion.
No UI/build/full-project/live provider/workingDB changes; no migrations/env changes.
No notification/BusinessEvent/AI policy changes. Isolated SQLite/native PG only.
Update operations/passport/plan/evidence; own local commit only, no push/deploy.
